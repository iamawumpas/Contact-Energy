"""Usage data synchronization coordinator for Contact Energy integration.

=== WHAT THIS DOES ===
This module contains the legacy ``UsageCoordinator`` class. Its job is to keep
local usage-history caches up to date by downloading hourly, daily, and monthly
usage information from Contact Energy only when those datasets actually need a
refresh.

The coordinator handles several responsibilities at once:
- deciding whether each usage interval needs syncing,
- calculating the safest date range to request,
- retrying after temporary API or network failures,
- splitting large requests into smaller chunks when needed,
- pruning old cache entries outside the supported history window, and
- importing daily usage into Home Assistant statistics for the Energy Dashboard.

=== FOR NON-CODERS ===
Think of this as an archive manager for electricity-usage history.
- One shelf stores hour-by-hour data.
- Another shelf stores day-by-day data.
- Another shelf stores month-by-month data.

The coordinator checks whether each shelf is out of date, requests only the
missing pages, files them neatly, throws away pages that are too old to keep,
and then tells the rest of Home Assistant that fresh usage data is available.

Helpful terms:
- "Coordinator": a shared organiser that fetches once for many listeners.
- "Polling": checking again later on a timer.
- "Update interval": how long to wait between allowed syncs.
- "Data refresh": replacing older cached history with newer history.

Sync windows (hard-coded for this legacy flow):
- Hourly: keep the last 14 days
- Daily: keep roughly the last 18 months
- Monthly: keep the last 18 months

Version: 1.8.3
Author: Contact Energy Integration
"""
# This future import keeps modern type-hint syntax available throughout the file.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: records normal activity, retries, skips, and errors for diagnostics.
import logging

# asyncio: provides async sleep for retry backoff delays.
import asyncio

# time: used for measuring total sync duration.
import time


# date/datetime/timedelta/timezone: used for scheduling decisions and request windows.
from datetime import date, datetime, timedelta, timezone

# TYPE_CHECKING: allows type-only imports without causing runtime import cycles.
from typing import TYPE_CHECKING

# async_dispatcher_send: notifies Home Assistant listeners that usage data changed.
from homeassistant.helpers.dispatcher import async_dispatcher_send

# Statistics helpers: used to import usage history into the Energy Dashboard database.
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    StatisticData,
    StatisticMetaData,
)

# UsageCache: reads, writes, and prunes the cached usage-history files.
from .usage_cache import UsageCache

# DOMAIN: the integration's identifier used in signals and statistic IDs.
from .const import DOMAIN

# ContactEnergyApi: legacy API client that downloads usage data.
# ContactEnergyApiError: API-specific failure.
# ContactEnergyAuthError: authentication-specific failure that should bubble up.
# ContactEnergyConnectionError: network/connection-specific failure that may be retried.
from .contact_api import ContactEnergyApi, ContactEnergyApiError, ContactEnergyAuthError, ContactEnergyConnectionError

if TYPE_CHECKING:
    # HomeAssistant is imported only for type hints so runtime imports stay light.
    from homeassistant.core import HomeAssistant

# ============================================================================
# LOGGER AND CONFIGURATION
# ============================================================================

# Create a logger dedicated to messages from this module.
_LOGGER = logging.getLogger(__name__)

# Usage sync configuration (hard-coded for v1.8.3)
# These windows define how much historical data to keep in cache
USAGE_CONFIG = {
    "hourly": {
        "window_days": 14,  # Keep last 14 days of hourly data
        "max_lookback_days": 14,  # API limit (Contact Energy provides ~2 weeks)
        "sync_interval_hours": 1,  # Sync every hour
    },
    "daily": {
        "window_days": 548,  # Keep last 18 months of daily data for statistics
        "max_lookback_days": 548,  # Request 18 months of historical data (API may limit)
        "sync_interval_hours": 24,  # Sync daily
    },
    "monthly": {
        "window_months": 18,  # Keep last 18 months of monthly data
        "max_lookback_months": 24,  # API limit (Contact Energy provides ~2 years)
        "sync_interval_hours": 24,  # Sync daily
    },
}

# By design, Contact Energy's API can take 24-72 hours to publish smart-meter
# data, so requesting recent dates for hourly/daily reliably returns a 502.
# Stay this many days behind "today" to avoid hammering the API for data
# that doesn't exist yet.
DATA_AVAILABILITY_LAG_DAYS = 3


class UsageCoordinator:
    """Manages usage data synchronization for a single contract.

    === WHAT THIS DOES ===
    This class is the archive manager for one Contact Energy contract. It loads
    cached usage history, decides whether hourly/daily/monthly data needs to be
    refreshed, downloads missing history, saves the refreshed cache, and signals
    other Home Assistant components when new usage data is ready.

    === FOR NON-CODERS ===
    Imagine one staff member looking after the usage-history records for a single
    home or account. That staff member checks whether each record book is old,
    requests missing pages, files them, and lets everyone know the archive is now
    current enough to read from.

    This class exists so many sensors can share one carefully managed source of
    usage history instead of each sensor downloading its own copy.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: ContactEnergyApi,
        contract_id: str,
        icp: str = None,
    ):
        """Initialize the usage coordinator.

        === WHAT THIS DOES ===
        This constructor stores the main objects the coordinator needs and prepares
        the cache/state fields used by later sync operations.

        === FOR NON-CODERS ===
        This is the setup step for the usage archive manager. It gives the manager
        the Home Assistant system, the API helper, the contract being tracked, and
        the property identifier used when creating statistics IDs.
        """
        # ====================================================================
        # STEP 1: Store the shared objects and contract identifiers.
        # ====================================================================
        self.hass = hass
        self.api = api
        self.contract_id = contract_id

        # Use the ICP if available; otherwise fall back to the contract ID so we
        # still have a stable identifier for statistics and cache naming.
        self.icp = icp or contract_id

        # Convert the ICP/contract identifier into a statistics-safe format.
        self.icp_sanitized = self._sanitize_statistic_id(self.icp)

        # Create the cache manager that handles disk persistence and pruning.
        self.cache = UsageCache(contract_id)

        # This flag temporarily bypasses normal timing rules during force syncs.
        self._force_sync_mode = False

        _LOGGER.debug(
            "UsageCoordinator initialized for contract %s (ICP: %s, sanitized: %s)",
            contract_id, self.icp, self.icp_sanitized
        )

    async def async_sync_usage(self) -> None:
        """Synchronize usage data with intelligent incremental downloads.

        === WHAT THIS DOES ===
        This is the coordinator's main sync entry point. It loads the cache, checks
        which usage intervals are due for refresh, runs the required sync steps,
        saves the updated cache, and broadcasts that fresh usage data is available.

        === FOR NON-CODERS ===
        This is the full archive-update routine. It answers:
        - Do we need new hourly history?
        - Do we need new daily history?
        - Do we need new monthly history?

        Then it updates only the books that need work and leaves the others alone.
        """
        # Record the wall-clock start time so we can log total duration later.
        overall_start_time = time.time()

        _LOGGER.info(
            "Starting usage sync for contract %s",
            self.contract_id
        )

        try:
            # =================================================================
            # STEP 1: Load the existing usage cache from disk.
            # =================================================================
            # This means the coordinator starts with the most recent saved state
            # before deciding whether any new API requests are necessary.
            await self.cache.load()

            _LOGGER.debug(
                "Usage sync timing state for %s: hourly_last_sync=%s, daily_last_sync=%s, monthly_last_sync=%s, global_last_synced=%s",
                self.contract_id,
                self.cache.get_interval_last_sync("hourly"),
                self.cache.get_interval_last_sync("daily"),
                self.cache.get_interval_last_sync("monthly"),
                self.cache.get_last_synced(),
            )

            # =================================================================
            # STEP 2: Decide which usage intervals are due for work.
            # =================================================================
            # Hourly data has its own schedule, and daily/monthly share another.
            should_sync_hourly = self.should_sync_hourly_now() or self._force_sync_mode
            should_sync_daily_monthly = self.should_sync_daily_monthly_now() or self._force_sync_mode

            if not should_sync_hourly and not should_sync_daily_monthly:
                _LOGGER.debug(
                    "No sync needed for contract %s at this time (hourly: %s, daily/monthly: %s)",
                    self.contract_id, should_sync_hourly, should_sync_daily_monthly
                )
                return

            _LOGGER.info(
                "Contract %s sync schedule: hourly=%s, daily/monthly=%s",
                self.contract_id, should_sync_hourly, should_sync_daily_monthly
            )

            # =================================================================
            # STEP 3: Run only the sync jobs that were judged necessary.
            # =================================================================
            if should_sync_hourly:
                await self._sync_hourly()

            if should_sync_daily_monthly:
                await self._sync_daily()
                await self._sync_monthly()

            # =================================================================
            # STEP 4: Save the refreshed cache back to disk.
            # =================================================================
            await self.cache.save()

            # =================================================================
            # STEP 5: Tell any listening entities that new usage data is ready.
            # =================================================================
            async_dispatcher_send(
                self.hass,
                f"{DOMAIN}_usage_updated_{self.contract_id}",
            )

            overall_elapsed = time.time() - overall_start_time
            _LOGGER.info(
                "Usage sync completed for contract %s in %.2f seconds",
                self.contract_id, overall_elapsed
            )

        except Exception as e:
            # Log unexpected errors but don't raise to prevent breaking main coordinator
            overall_elapsed = time.time() - overall_start_time
            _LOGGER.error(
                "Usage sync failed for contract %s after %.2f seconds: %s",
                self.contract_id, overall_elapsed, str(e), exc_info=True
            )

    async def force_sync(self) -> None:
        """Force a usage data sync, bypassing time thresholds.

        === WHAT THIS DOES ===
        This method temporarily enables a special mode that ignores the normal
        "too soon to sync again" checks, then runs the main sync routine.

        === FOR NON-CODERS ===
        Normally the coordinator waits for the right time window. This method is
        the manual override that says, "Refresh now even if the timer says wait."
        """
        _LOGGER.info("Force sync requested for contract %s", self.contract_id)
        
        # Set flag to bypass time threshold checks
        self._force_sync_mode = True
        
        try:
            # Perform sync (will bypass time checks due to force flag)
            await self.async_sync_usage()
        finally:
            # Reset flag
            self._force_sync_mode = False

    async def _sync_hourly(self) -> None:
        """Sync hourly usage data with incremental download logic.

        === WHAT THIS DOES ===
        This method refreshes the detailed hour-by-hour usage history. It checks
        whether hourly syncing is due, calculates the missing date range, downloads
        that range, updates the cache, marks the interval as synced, and prunes
        history that is older than the supported retention window.

        === FOR NON-CODERS ===
        This is the most detailed ledger update. It fills in missing hourly pages
        rather than re-downloading the whole book every time.
        """
        interval = "hourly"
        config = USAGE_CONFIG[interval]

        _LOGGER.debug("Starting hourly sync for contract %s", self.contract_id)

        # Check if sync is needed based on last sync time
        if not self._should_sync(interval):
            _LOGGER.info(
                "Skipping hourly sync for contract %s: last sync was < %d hours ago",
                self.contract_id, config["sync_interval_hours"]
            )
            return

        try:
            # Determine date range to download
            from_date, to_date = self._calculate_sync_range(interval)

            if from_date > to_date:
                _LOGGER.debug(
                    "No new hourly data to sync for contract %s (from=%s > to=%s)",
                    self.contract_id, from_date, to_date
                )
                return

            _LOGGER.info(
                "Syncing hourly data for contract %s: from=%s, to=%s (%d days)",
                self.contract_id, from_date, to_date, (to_date - from_date).days + 1
            )

            # =================================================================
            # STEP 3: Download the required hourly window.
            # =================================================================
            # Hourly requests are intentionally broken into 1-day chunks because
            # the upstream API has historically been more reliable with smaller
            # hourly windows than with one large multi-day request.
            span_days = (to_date - from_date).days + 1
            if span_days > 1:
                _LOGGER.debug(
                    "Splitting hourly sync for contract %s into 1-day chunks",
                    self.contract_id
                )
                chunk_size = 1
                hourly_data: list[dict] = []
                cursor = from_date
                while cursor <= to_date:
                    chunk_end = min(cursor + timedelta(days=chunk_size - 1), to_date)
                    _LOGGER.debug(
                        "Fetching hourly chunk for contract %s: %s to %s",
                        self.contract_id, cursor, chunk_end
                    )
                    try:
                        chunk_data = await self._fetch_usage_with_resilience(
                            interval="hourly",
                            from_date=cursor,
                            to_date=chunk_end,
                            allow_split=False,
                        )
                        if chunk_data:
                            hourly_data.extend(chunk_data)
                            _LOGGER.debug(
                                "Retrieved %d hourly records for chunk %s to %s",
                                len(chunk_data), cursor, chunk_end
                            )
                        else:
                            _LOGGER.debug(
                                "No hourly data returned for chunk %s to %s, continuing",
                                cursor, chunk_end
                            )
                    except Exception as chunk_err:
                        _LOGGER.warning(
                            "Failed to fetch hourly chunk %s to %s: %s. Skipping chunk.",
                            cursor, chunk_end, str(chunk_err)
                        )
                    cursor = chunk_end + timedelta(days=1)
            else:
                # Small range, fetch directly
                hourly_data = await self._fetch_usage_with_resilience(
                    interval="hourly",
                    from_date=from_date,
                    to_date=to_date,
                )

            # Update cache with new data
            added_count = self.cache.update_hourly(hourly_data)
            _LOGGER.info(
                "Added/updated %d hourly records for contract %s",
                added_count, self.contract_id
            )

            # Mark hourly interval as synced even if no new rows were returned.
            self.cache.set_interval_last_sync(interval)

            # Prune old data outside window
            before, after = self.cache.prune_hourly(window_days=config["window_days"])
            if before != after:
                _LOGGER.info(
                    "Pruned hourly cache for contract %s: %d -> %d records",
                    self.contract_id, before, after
                )

            # Import daily history and current hourly usage for the Energy Dashboard.
            await self._async_import_statistics_for_usage_data()

        except ContactEnergyAuthError as e:
            # Authentication errors should propagate to trigger re-auth in main coordinator
            _LOGGER.error(
                "Authentication error during hourly sync for contract %s: %s",
                self.contract_id, str(e)
            )
            raise

        except ContactEnergyApiError as e:
            # API errors are logged but don't block other syncs
            _LOGGER.error(
                "API error during hourly sync for contract %s: %s. Skipping hourly sync.",
                self.contract_id, str(e)
            )

        except Exception as e:
            # Unexpected errors are logged but don't block other syncs
            _LOGGER.error(
                "Unexpected error during hourly sync for contract %s: %s. Skipping hourly sync.",
                self.contract_id, str(e), exc_info=True
            )

    async def _sync_daily(self) -> None:
        """Sync daily usage data with incremental download logic.

        === WHAT THIS DOES ===
        This method refreshes day-by-day usage history. It decides whether daily
        syncing is due, calculates the needed range, downloads the data, updates
        the cache, prunes old rows, and imports daily totals into Home Assistant
        statistics so the Energy Dashboard can use them.

        === FOR NON-CODERS ===
        This is the daily summary-book update. It also copies the final totals
        into Home Assistant's long-term reporting system.
        """
        interval = "daily"
        config = USAGE_CONFIG[interval]

        _LOGGER.debug("Starting daily sync for contract %s", self.contract_id)

        # Check if sync is needed based on last sync time
        if not self._should_sync(interval):
            _LOGGER.info(
                "Skipping daily sync for contract %s: last sync was < %d hours ago",
                self.contract_id, config["sync_interval_hours"]
            )
            return

        try:
            # Determine date range to download
            from_date, to_date = self._calculate_sync_range(interval)

            if from_date > to_date:
                _LOGGER.debug(
                    "No new daily data to sync for contract %s (from=%s > to=%s)",
                    self.contract_id, from_date, to_date
                )
                return

            _LOGGER.info(
                "Syncing daily data for contract %s: from=%s, to=%s (%d days)",
                self.contract_id, from_date, to_date, (to_date - from_date).days + 1
            )

            # Download daily data with basic retry (shared helper) in case of intermittent errors
            daily_data = await self._fetch_usage_with_resilience(
                interval="daily",
                from_date=from_date,
                to_date=to_date,
            )

            # Update cache with new data
            added_count = self.cache.update_daily(daily_data)
            _LOGGER.info(
                "Added/updated %d daily records for contract %s",
                added_count, self.contract_id
            )

            # Mark daily interval as synced even if no new rows were returned.
            self.cache.set_interval_last_sync(interval)

            # Prune old data outside window
            before, after = self.cache.prune_daily(window_days=config["window_days"])
            if before != after:
                _LOGGER.info(
                    "Pruned daily cache for contract %s: %d -> %d records",
                    self.contract_id, before, after
                )


        except ContactEnergyAuthError as e:
            # Authentication errors should propagate to trigger re-auth in main coordinator
            _LOGGER.error(
                "Authentication error during daily sync for contract %s: %s",
                self.contract_id, str(e)
            )
            raise

        except ContactEnergyApiError as e:
            # API errors are logged but don't block other syncs
            _LOGGER.error(
                "API error during daily sync for contract %s: %s. Skipping daily sync.",
                self.contract_id, str(e)
            )

        except Exception as e:
            # Unexpected errors are logged but don't block other syncs
            _LOGGER.error(
                "Unexpected error during daily sync for contract %s: %s. Skipping daily sync.",
                self.contract_id, str(e), exc_info=True
            )

    async def _async_import_statistics_for_usage_data(self) -> None:
        """Import daily history and recent hourly usage for the Energy Dashboard."""
        try:
            daily_records = self.cache.data.get("daily", {})
            hourly_records = self.cache.data.get("hourly", {})
            if not daily_records and not hourly_records:
                return

            parsed_hourly = []
            for timestamp_text, record in hourly_records.items():
                try:
                    timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    else:
                        timestamp = timestamp.astimezone(timezone.utc)
                    parsed_hourly.append((timestamp, record))
                except (TypeError, ValueError):
                    _LOGGER.warning(
                        "Skipping hourly statistic with invalid timestamp %s for contract %s",
                        timestamp_text,
                        self.contract_id,
                    )

            parsed_hourly.sort(key=lambda item: item[0])
            first_hourly_date = parsed_hourly[0][0].date() if parsed_hourly else None
            parsed_daily = []
            for date_text, record in daily_records.items():
                try:
                    record_date = date.fromisoformat(date_text)
                except (TypeError, ValueError):
                    continue
                if first_hourly_date is None or record_date < first_hourly_date:
                    parsed_daily.append((record_date, record))
            parsed_daily.sort(key=lambda item: item[0])

            for energy_kind in ("paid", "free"):
                cumulative_sum = 0.0
                statistics = []

                for record_date, record in parsed_daily:
                    cumulative_sum += float(record.get(energy_kind, 0.0))
                    statistics.append(
                        StatisticData(
                            start=datetime.combine(record_date, datetime.min.time(), tzinfo=timezone.utc),
                            state=cumulative_sum,
                            sum=cumulative_sum,
                        )
                    )

                for timestamp, record in parsed_hourly:
                    cumulative_sum += float(record.get(energy_kind, 0.0))
                    statistics.append(
                        StatisticData(
                            start=timestamp,
                            state=cumulative_sum,
                            sum=cumulative_sum,
                        )
                    )

                if not statistics:
                    continue

                stat_id = (
                    f"{DOMAIN}:paid_usage_{self.icp_sanitized}"
                    if energy_kind == "paid"
                    else f"{DOMAIN}:free_usage_{self.icp_sanitized}"
                )
                stat_name = (
                    f"Contact Energy Paid Usage {self.icp}"
                    if energy_kind == "paid"
                    else f"Contact Energy Free Usage {self.icp}"
                )
                metadata = StatisticMetaData(
                    mean_type=StatisticMeanType.NONE,
                    has_mean=False,
                    has_sum=True,
                    name=stat_name,
                    source=DOMAIN,
                    statistic_id=stat_id,
                    unit_of_measurement="kWh",
                    unit_class="energy",
                )
                async_add_external_statistics(self.hass, metadata, statistics)
        except Exception as err:
            _LOGGER.error(
                "Failed to import energy statistics for contract %s: %s",
                self.contract_id,
                err,
                exc_info=True,
            )

    async def _sync_monthly(self) -> None:
        """Sync monthly usage data with incremental download logic.

        === WHAT THIS DOES ===
        This method refreshes the month-by-month usage history. It calculates the
        correct complete-month range to request, downloads the needed data, updates
        the monthly cache, and removes months that fall outside the retention rule.

        === FOR NON-CODERS ===
        Monthly data is the long-view summary. This method makes sure the archive
        contains complete months only, because incomplete current-month data would
        be misleading.
        """
        interval = "monthly"
        config = USAGE_CONFIG[interval]

        _LOGGER.debug("Starting monthly sync for contract %s", self.contract_id)

        # Check if sync is needed based on last sync time
        if not self._should_sync(interval):
            _LOGGER.info(
                "Skipping monthly sync for contract %s: last sync was < %d hours ago",
                self.contract_id, config["sync_interval_hours"]
            )
            return

        try:
            # Determine date range to download
            from_date, to_date = self._calculate_sync_range(interval)

            if from_date > to_date:
                _LOGGER.debug(
                    "No new monthly data to sync for contract %s (from=%s > to=%s)",
                    self.contract_id, from_date, to_date
                )
                return

            _LOGGER.info(
                "Syncing monthly data for contract %s: from=%s, to=%s (%d months approx)",
                self.contract_id, from_date, to_date, 
                ((to_date.year - from_date.year) * 12 + (to_date.month - from_date.month))
            )

            # Download monthly data with basic retry (shared helper)
            monthly_data = await self._fetch_usage_with_resilience(
                interval="monthly",
                from_date=from_date,
                to_date=to_date,
            )

            # Update cache with new data
            added_count = self.cache.update_monthly(monthly_data)
            _LOGGER.info(
                "Added/updated %d monthly records for contract %s",
                added_count, self.contract_id
            )

            # Mark monthly interval as synced even if no new rows were returned.
            self.cache.set_interval_last_sync(interval)

            # Prune old data outside window
            before, after = self.cache.prune_monthly(window_months=config["window_months"])
            if before != after:
                _LOGGER.info(
                    "Pruned monthly cache for contract %s: %d -> %d records",
                    self.contract_id, before, after
                )

        except ContactEnergyAuthError as e:
            # Authentication errors should propagate to trigger re-auth in main coordinator
            _LOGGER.error(
                "Authentication error during monthly sync for contract %s: %s",
                self.contract_id, str(e)
            )
            raise

        except ContactEnergyApiError as e:
            # API errors are logged but don't block other syncs
            _LOGGER.error(
                "API error during monthly sync for contract %s: %s. Skipping monthly sync.",
                self.contract_id, str(e)
            )

        except Exception as e:
            # Unexpected errors are logged but don't block other syncs
            _LOGGER.error(
                "Unexpected error during monthly sync for contract %s: %s. Skipping monthly sync.",
                self.contract_id, str(e), exc_info=True
            )

    async def _fetch_usage_with_resilience(
        self,
        interval: str,
        from_date: date,
        to_date: date,
        *,
        allow_split: bool = True,
        max_attempts: int = 3,
    ) -> list[dict]:
        """Fetch usage with retries and optional chunking.

        === WHAT THIS DOES ===
        This helper wraps usage downloads in resilience logic. It retries after
        temporary API or connection failures, waits a little longer after each
        failed attempt, and optionally breaks a large request into smaller chunks
        when repeated attempts still fail.

        === FOR NON-CODERS ===
        If the first phone call to the utility fails, this method tries again a
        few times. If a big request keeps failing, it asks the same question in
        smaller pieces instead.
        """

        # ====================================================================
        # STEP 1: Try the request a few times with small waiting periods between tries.
        # ====================================================================
        for attempt in range(1, max_attempts + 1):
            try:
                return await self.api.get_usage(
                    self.contract_id,
                    interval=interval,
                    from_date=from_date,
                    to_date=to_date,
                )
            except (ContactEnergyApiError, ContactEnergyConnectionError) as err:
                if attempt >= max_attempts:
                    last_error = err
                    break

                backoff = attempt  # simple linear backoff keeps it fast but polite
                _LOGGER.debug(
                    "Retrying %s usage for contract %s after error (%s). attempt=%d/%d, backoff=%ds",
                    interval, self.contract_id, str(err), attempt, max_attempts, backoff
                )
                await asyncio.sleep(backoff)

        # ====================================================================
        # STEP 2: If full-range retries still failed, optionally split the job into
        # smaller chunks that are often easier for the upstream API to handle.
        # ====================================================================
        if allow_split:
            span_days = (to_date - from_date).days + 1
            
            # Determine chunk size based on interval
            if interval == "hourly":
                chunk_size_days = 1  # 1 day chunks for hourly data
                min_span_for_split = 1
            elif interval == "daily":
                chunk_size_days = 90  # 90 day chunks (~3 months) for daily data
                min_span_for_split = 90
            else:
                # Monthly doesn't need chunking typically
                raise last_error
            
            if span_days > min_span_for_split:
                _LOGGER.debug(
                    "Splitting %s sync for contract %s into %d-day chunks after repeated errors",
                    interval, self.contract_id, chunk_size_days
                )
                merged: list[dict] = []
                cursor = from_date
                while cursor <= to_date:
                    chunk_end = min(cursor + timedelta(days=chunk_size_days - 1), to_date)
                    _LOGGER.debug(
                        "Fetching %s chunk for contract %s: %s to %s",
                        interval, self.contract_id, cursor, chunk_end
                    )
                    try:
                        chunk_data = await self._fetch_usage_with_resilience(
                            interval=interval,
                            from_date=cursor,
                            to_date=chunk_end,
                            allow_split=False,
                            max_attempts=max_attempts,
                        )
                        if chunk_data:
                            merged.extend(chunk_data)
                            _LOGGER.debug(
                                "Retrieved %d %s records for chunk %s to %s",
                                len(chunk_data), interval, cursor, chunk_end
                            )
                        else:
                            _LOGGER.debug(
                                "No %s data returned for chunk %s to %s, continuing",
                                interval, cursor, chunk_end
                            )
                    except Exception as chunk_err:
                        _LOGGER.warning(
                            "Failed to fetch %s chunk %s to %s: %s. Skipping chunk.",
                            interval, cursor, chunk_end, str(chunk_err)
                        )
                    cursor = chunk_end + timedelta(days=1)
                return merged

        # ====================================================================
        # STEP 3: If retries and chunking both failed, surface the last error so
        # the caller can decide how to handle the failed sync.
        # ====================================================================
        raise last_error

    def _should_sync(self, interval: str) -> bool:
        """Determine if a specific interval needs syncing.

        === WHAT THIS DOES ===
        This helper compares the last successful sync time for one interval with
        the configured minimum wait time for that interval.

        === FOR NON-CODERS ===
        This is the "Is it too soon to refresh again?" check. It prevents the
        coordinator from repeatedly downloading the same data too often.
        """
        # Check if force sync mode is enabled
        if self._force_sync_mode:
            _LOGGER.debug(
                "Force sync mode enabled for %s (contract %s)",
                interval, self.contract_id
            )
            return True

        config = USAGE_CONFIG[interval]
        sync_interval = timedelta(hours=config["sync_interval_hours"])

        # Get per-interval sync timestamp from cache metadata.
        last_synced = self.cache.get_interval_last_sync(interval)

        if last_synced is None:
            # Never synced before - need to sync
            _LOGGER.debug(
                "Sync needed for %s (contract %s): never synced before",
                interval, self.contract_id
            )
            return True

        # Calculate time elapsed since last sync
        now = datetime.now(timezone.utc)
        elapsed = now - last_synced

        # Check if enough time has passed since last sync
        if elapsed >= sync_interval:
            _LOGGER.debug(
                "Sync needed for %s (contract %s): elapsed=%.1f hours, threshold=%.1f hours",
                interval, self.contract_id,
                elapsed.total_seconds() / 3600,
                sync_interval.total_seconds() / 3600
            )
            return True

        # Cache is still fresh
        _LOGGER.debug(
            "Sync not needed for %s (contract %s): elapsed=%.1f hours < threshold=%.1f hours",
            interval, self.contract_id,
            elapsed.total_seconds() / 3600,
            sync_interval.total_seconds() / 3600
        )
        return False

    def _calculate_sync_range(self, interval: str) -> tuple[date, date]:
        """Calculate the safest date range to request for one interval.

        === WHAT THIS DOES ===
        This helper works out exactly which dates still need downloading. It looks
        at what is already cached, respects the retention window, and avoids
        requesting more history than the Contact Energy API is likely to provide.

        === FOR NON-CODERS ===
        Rather than ordering the entire history every time, this method figures out
        which pages are missing from the book and requests only those pages.
        """
        config = USAGE_CONFIG[interval]
        today = date.today()

        # Get existing cache range
        if interval == "hourly":
            cached_from, cached_to = self.cache.get_hourly_range()
            window_days = config["window_days"]
            max_lookback = config["max_lookback_days"]
        elif interval == "daily":
            cached_from, cached_to = self.cache.get_daily_range()
            window_days = config["window_days"]
            max_lookback = config["max_lookback_days"]
        else:  # monthly
            cached_from, cached_to = self.cache.get_monthly_range()
            window_months = config["window_months"]
            max_lookback = config["max_lookback_months"]
            
            # For monthly data, we need to calculate based on complete months only
            # The API expects requests for full months (from 1st to end of month)
            # Don't request the current incomplete month
            
            # Calculate the last complete month (previous month)
            last_complete_month_date = date(today.year, today.month, 1) - timedelta(days=1)
            last_complete_month = date(last_complete_month_date.year, last_complete_month_date.month, 1)
            
            if cached_to is None:
                # First sync: download full window of complete months
                from_month_date = last_complete_month
                for _ in range(window_months - 1):
                    if from_month_date.month == 1:
                        from_month_date = date(from_month_date.year - 1, 12, 1)
                    else:
                        from_month_date = date(from_month_date.year, from_month_date.month - 1, 1)
                from_date = from_month_date
                _LOGGER.debug(
                    "First sync for %s (contract %s): downloading full window from %s",
                    interval, self.contract_id, from_date
                )
            else:
                # Incremental sync: download from month after last cached month
                # Only if there's a new complete month available
                if cached_to >= last_complete_month:
                    # No new complete month to download
                    _LOGGER.debug(
                        "No new complete month to sync for %s (contract %s): last cached month %s is current or future",
                        interval, self.contract_id, cached_to
                    )
                    # Return invalid range to skip sync
                    return (today, today - timedelta(days=1))
                
                # Download from the month after the last cached month
                if cached_to.month == 12:
                    from_date = date(cached_to.year + 1, 1, 1)
                else:
                    from_date = date(cached_to.year, cached_to.month + 1, 1)
                    
                _LOGGER.debug(
                    "Incremental sync for %s (contract %s): downloading from %s (last cached: %s)",
                    interval, self.contract_id, from_date, cached_to
                )
            
            # For monthly, to_date is the last day of the last complete month
            to_date = last_complete_month
            
            # Ensure we don't exceed API's max lookback limit (in months)
            months_back = ((to_date.year - from_date.year) * 12 + (to_date.month - from_date.month))
            if months_back > max_lookback:
                _LOGGER.warning(
                    "Requested range spans %d months, exceeding API limit (%d months) for %s.",
                    months_back, max_lookback, interval
                )
                # Adjust from_date to stay within limit
                from_month = to_date.month - max_lookback
                from_year = to_date.year
                while from_month <= 0:
                    from_month += 12
                    from_year -= 1
                from_date = date(from_year, from_month, 1)
                _LOGGER.warning(
                    "Adjusted from_date to %s (max lookback: %d months)",
                    from_date, max_lookback
                )
            
            _LOGGER.debug(
                "Calculated sync range for %s (contract %s): from=%s, to=%s (%d months)",
                interval, self.contract_id, from_date, to_date,
                ((to_date.year - from_date.year) * 12 + (to_date.month - from_date.month) + 1)
            )
            
            return (from_date, to_date)

        # Determine from_date (for hourly and daily)
        if cached_to is None:
            # First sync: download full window
            from_date = today - timedelta(days=window_days)
            _LOGGER.debug(
                "First sync for %s (contract %s): downloading full window from %s",
                interval, self.contract_id, from_date
            )
        else:
            # Incremental sync: download from day after last cached date
            from_date = cached_to + timedelta(days=1)
            _LOGGER.debug(
                "Incremental sync for %s (contract %s): downloading from %s (last cached: %s)",
                interval, self.contract_id, from_date, cached_to
            )

        # Determine to_date. Stay a day behind "today" since the API doesn't
        # publish hourly/daily data for the current day until it has passed.
        to_date = today - timedelta(days=DATA_AVAILABILITY_LAG_DAYS)

        # Ensure we don't exceed API's max lookback limit
        earliest_allowed = today - timedelta(days=max_lookback)
        if from_date < earliest_allowed:
            _LOGGER.warning(
                "Requested from_date %s is beyond API limit (%s) for %s. "
                "Adjusting to %s (max lookback: %d days)",
                from_date, earliest_allowed, interval, earliest_allowed, max_lookback
            )
            from_date = earliest_allowed

        _LOGGER.debug(
            "Calculated sync range for %s (contract %s): from=%s, to=%s (%d days)",
            interval, self.contract_id, from_date, to_date,
            (to_date - from_date).days + 1
        )

        return (from_date, to_date)

    def should_sync_hourly_now(self) -> bool:
        """Check whether the hourly sync window is currently open.

        === WHAT THIS DOES ===
        This method decides whether hourly usage should be refreshed right now. It
        avoids back-to-back syncs and spreads contracts across slightly different
        minutes within the hour.

        === FOR NON-CODERS ===
        Instead of every account asking the API at the exact same minute, this
        method staggers requests a little so the system behaves more politely.
        """
        # Capture the current UTC time once so all checks use one reference.
        now = datetime.now(timezone.utc)
        
        # Read the last successful hourly-sync timestamp from cache metadata.
        if not hasattr(self.cache, 'data') or not self.cache.data:
            # Cache not loaded or empty, sync now
            return True
            
        last_sync = self.cache.get_interval_last_sync("hourly")

        if not last_sync:
            # Never synced before, do it now
            return True
            
        # Check if it's been at least 50 minutes since last sync (to avoid double-syncing)
        if (now - last_sync).total_seconds() < 50 * 60:
            return False
            
        # Build a deterministic per-hour offset so not every contract hits
        # the upstream API at the same minute. The offset stays stable for the
        # whole hour because it is derived from the contract ID and current hour.
        import hashlib

        # seed_str is the unique hourly fingerprint for this contract.
        seed_str = f"{self.contract_id}_{now.year}_{now.month}_{now.day}_{now.hour}"

        # Convert the fingerprint into a repeatable integer we can map to minutes.
        hash_val = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)

        # random_offset spreads contracts from 17 minutes early to 17 minutes late.
        random_offset = (hash_val % 35) - 17

        # target_min is the minute within the hour when this contract should sync.
        target_min = 25 + random_offset

        # current_min is the actual current minute that we compare against target_min.
        current_min = now.minute
        
        # If we're at or past the target time this hour
        return current_min >= target_min

    def should_sync_daily_monthly_now(self) -> bool:
        """Check whether the shared daily/monthly sync window is open.

        === WHAT THIS DOES ===
        This method decides whether daily and monthly syncing should happen now by
        checking the last successful sync times and the 03:00 UTC target window.

        === FOR NON-CODERS ===
        Daily and monthly summary books are only meant to refresh once per day.
        This method checks whether today's scheduled summary update is due yet.
        """
        # Capture the current UTC time once for consistent comparisons.
        now = datetime.now(timezone.utc)
        
        # Read the most recent daily and monthly sync timestamps from the cache.
        if not hasattr(self.cache, 'data') or not self.cache.data:
            # Cache not loaded or empty, sync now
            return True
            
        last_daily = self.cache.get_interval_last_sync("daily")
        last_monthly = self.cache.get_interval_last_sync("monthly")
        
        # Check if either has never been synced
        if not last_daily or not last_monthly:
            return True

        last_sync = max(last_daily, last_monthly)
            
        # Check if it's been at least 20 hours since last sync (avoid double-syncing)
        if (now - last_sync).total_seconds() < 20 * 3600:
            return False
            
        # Check if we're at or past 03:00 UTC today and haven't synced today
        today_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= today_3am and last_sync < today_3am:
            return True
            
        return False

    def _sanitize_statistic_id(self, value: str) -> str:
        """Convert an identifier into a Home Assistant-safe statistics ID fragment.

        === WHAT THIS DOES ===
        This helper rewrites an ICP or contract ID so it contains only lowercase
        letters, numbers, and underscores, which matches Home Assistant's rules
        for statistic identifiers.

        === FOR NON-CODERS ===
        Some IDs contain spaces or special characters. This method tidies them up
        into a safe label format that Home Assistant accepts.
        """
        # Import regular-expression support locally because it is only needed here.
        import re

        # First make the text lowercase, then replace unsupported characters with _.
        sanitized = re.sub(r'[^a-z0-9_]', '_', value.lower())

        # Collapse repeated underscores so the result stays neat and readable.
        sanitized = re.sub(r'_+', '_', sanitized)

        # Remove underscores from the beginning or end of the final string.
        sanitized = sanitized.strip('_')

        # Return the cleaned identifier fragment to the caller.
        return sanitized
