"""Usage data synchronization coordinator for Contact Energy integration.

This module provides the UsageCoordinator class which manages the download
and synchronization of usage data from the Contact Energy API. It implements:
- Incremental sync logic (only downloads new/missing data)
- Metadata-driven sync decisions (checks if sync is needed)
- Automatic pruning to maintain fixed time windows
- Error handling and retry logic for transient failures
- Integration with existing coordinator architecture

The coordinator runs as a background task and is triggered by the main
ContactEnergyCoordinator on a schedule (typically daily at 2 AM).

Sync Windows (Hard-coded for Phase 1 / v1.4.0):
- Hourly: Last 9 days
- Daily: Last 35 days  
- Monthly: Last 18 months

Version: 1.4.0
Author: Contact Energy Integration
"""
from __future__ import annotations

import logging
import asyncio
import time
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    StatisticData,
    StatisticMetaData,
)

from .usage_cache import UsageCache
from .const import DOMAIN
from .contact_api import ContactEnergyApi, ContactEnergyApiError, ContactEnergyAuthError, ContactEnergyConnectionError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Usage sync configuration (hard-coded for v1.4.0)
# These windows define how much historical data to keep in cache
USAGE_CONFIG = {
    "hourly": {
        "window_days": 14,  # Keep last 14 days of hourly data
        "sync_interval_hours": 1,  # Sync hourly for testing
        "max_lookback_days": 14,  # API limit (Contact Energy provides ~2 weeks)
    },
    "daily": {
        "window_days": 35,  # Keep last 35 days of daily data
        "sync_interval_hours": 1,  # Sync hourly for testing
        "max_lookback_days": 60,  # API limit (Contact Energy provides ~2 months)
    },
    "monthly": {
        "window_months": 18,  # Keep last 18 months of monthly data
        "sync_interval_hours": 1,  # Sync hourly for testing
        "max_lookback_months": 24,  # API limit (Contact Energy provides ~2 years)
    },
}


class UsageCoordinator:
    """Manages usage data synchronization for a single contract.

    This coordinator handles the lifecycle of usage data:
    1. Load existing cache from disk (if available)
    2. Determine what data is missing or stale
    3. Download only the gaps/new data from API
    4. Update cache with new data
    5. Prune old data outside the window
    6. Save cache back to disk

    The coordinator is designed to be called periodically (e.g., daily) and
    will make intelligent decisions about whether to sync based on metadata.

    Attributes:
        hass: Home Assistant instance
        api: Contact Energy API client
        contract_id: Contract identifier
        cache: Usage cache manager

    Example:
        coordinator = UsageCoordinator(hass, api, "123456")
        await coordinator.async_sync_usage()
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: ContactEnergyApi,
        contract_id: str,
    ):
        """Initialize the usage coordinator.

        Args:
            hass: Home Assistant instance
            api: Authenticated Contact Energy API client
            contract_id: Contract identifier (e.g., "123456")
        """
        self.hass = hass
        self.api = api
        self.contract_id = contract_id
        self.cache = UsageCache(contract_id)
        self._force_sync_mode = False  # Flag to bypass time threshold checks

        _LOGGER.debug(
            "UsageCoordinator initialized for contract %s",
            contract_id
        )

    async def async_sync_usage(self) -> None:
        """Synchronize usage data with intelligent incremental downloads.

        This is the main entry point for usage sync. It:
        1. Loads existing cache
        2. Checks metadata to determine if sync is needed
        3. Downloads only missing/new data for each interval
        4. Updates cache and prunes old data
        5. Saves cache back to disk

        This method is designed to be called on a schedule (e.g., daily).
        It makes intelligent decisions about what to sync based on:
        - Time since last sync (per interval)
        - Existing date ranges in cache
        - Current date

        Raises:
            ContactEnergyApiError: If API requests fail (logged but not raised)

        Note: Errors are caught and logged to prevent breaking the main coordinator.
              Partial failures (e.g., hourly fails but daily succeeds) are handled gracefully.
        """
        overall_start_time = time.time()

        _LOGGER.info(
            "Starting usage sync for contract %s",
            self.contract_id
        )

        try:
            # Load existing cache from disk
            await self.cache.load()

            # Sync each interval type (hourly, daily, monthly)
            # Each sync is independent and failures don't block others
            await self._sync_hourly()
            await self._sync_daily()
            await self._sync_monthly()

            # Save updated cache to disk
            await self.cache.save()

            # Notify listeners (e.g., usage sensor) that fresh usage data is available
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

        This method is called by the refresh_data service to force an immediate
        sync regardless of when the last sync occurred. It sets a flag to bypass
        time threshold checks in _should_sync().
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

        Checks if hourly sync is needed based on metadata, calculates the
        date range to download, fetches data from API, updates cache, and prunes.

        Hourly data is typically only available for the last 1-2 weeks from
        Contact Energy due to their data processing pipeline.
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

            # Download hourly data in 1-day chunks to avoid API 502s
            # Split immediately rather than waiting for failures
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

            # Prune old data outside window
            before, after = self.cache.prune_hourly(window_days=config["window_days"])
            if before != after:
                _LOGGER.info(
                    "Pruned hourly cache for contract %s: %d -> %d records",
                    self.contract_id, before, after
                )

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

        Checks if daily sync is needed based on metadata, calculates the
        date range to download, fetches data from API, updates cache, and prunes.

        Daily data is typically available for the last 30+ days from Contact Energy.
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

            # Prune old data outside window
            before, after = self.cache.prune_daily(window_days=config["window_days"])
            if before != after:
                _LOGGER.info(
                    "Pruned daily cache for contract %s: %d -> %d records",
                    self.contract_id, before, after
                )

            # Import statistics to Home Assistant database for Energy Dashboard
            await self._async_import_statistics_for_daily_data()

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

    async def _async_import_statistics_for_daily_data(self) -> None:
        """Import daily usage data as statistics for the Energy Dashboard.

        This converts cached daily usage data into Home Assistant statistics format
        and imports it into the long-term statistics database. This enables the
        Energy Dashboard to display historical data.

        Called after daily data is synced and saved, so we import fresh data directly
        from the API without timing issues or async method call delays.
        """
        try:
            # Get daily records from cache first (we'll need them anyway)
            daily_records_dict = self.cache.data.get("daily", {})
            if not daily_records_dict:
                _LOGGER.debug(
                    "No daily records available for contract %s, skipping statistics import",
                    self.contract_id,
                )
                return

            # Get sensor start date (when the sensor first started recording)
            sensor_start_date = self.cache.get_energy_sensor_start_date()
            
            # Initialize sensor start date if not set (use earliest date in data)
            if not sensor_start_date:
                # Find the earliest date from the daily records dictionary keys
                # Keys are ISO date strings like "2025-12-05"
                try:
                    earliest_date_str = min(daily_records_dict.keys())
                    sensor_start_date = date.fromisoformat(earliest_date_str)
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(
                        "Failed to determine earliest date from daily records for contract %s: %s",
                        self.contract_id,
                        str(e),
                    )
                    sensor_start_date = date.today()
                
                self.cache.set_energy_sensor_start_date(sensor_start_date)
                _LOGGER.info(
                    "Initialized sensor start date for contract %s from earliest daily record: %s (%d records available)",
                    self.contract_id,
                    sensor_start_date.isoformat(),
                    len(daily_records_dict),
                )

            # Filter records to only include data from sensor start date onward
            filtered_records = []
            for date_str, record in daily_records_dict.items():
                record_date = date.fromisoformat(date_str)
                if record_date >= sensor_start_date:
                    record_with_date = record.copy()
                    record_with_date["_date"] = record_date
                    filtered_records.append(record_with_date)

            if not filtered_records:
                _LOGGER.debug(
                    "No daily records after start date %s for contract %s",
                    sensor_start_date.isoformat(),
                    self.contract_id,
                )
                return

            # Sort by date to ensure proper cumulative calculation
            filtered_records.sort(key=lambda x: x["_date"])

            # Import paid and free energy separately
            for energy_kind in ["paid", "free"]:
                # Build cumulative statistics from daily data
                statistics = []
                cumulative_sum = 0.0

                for record in filtered_records:
                    daily_value = float(record.get(energy_kind, 0.0))
                    cumulative_sum += daily_value

                    # Create timestamp at start of day (00:00:00) in UTC
                    # Home Assistant external statistics requires timestamps at top of hour
                    record_date = record["_date"]
                    timestamp = datetime.combine(
                        record_date,
                        datetime.min.time(),
                        tzinfo=timezone.utc
                    )

                    statistics.append(
                        StatisticData(
                            start=timestamp,
                            state=cumulative_sum,
                            sum=cumulative_sum,
                        )
                    )

                if not statistics:
                    continue

                # Build metadata for this energy kind using external statistics format
                # Home Assistant expects statistic_id in format: domain:identifier
                # (e.g., contact_energy:paid_usage_123456789). This satisfies
                # async_add_external_statistics validation requirements.
                if energy_kind == "paid":
                    stat_id = f"{DOMAIN}:paid_usage_{self.contract_id}"
                    stat_name = f"Contact Energy Paid Usage {self.contract_id}"
                else:
                    stat_id = f"{DOMAIN}:free_usage_{self.contract_id}"
                    stat_name = f"Contact Energy Free Usage {self.contract_id}"

                metadata = StatisticMetaData(
                    has_mean=False,
                    has_sum=True,
                    name=stat_name,
                    source=DOMAIN,
                    statistic_id=stat_id,
                    unit_of_measurement="kWh",
                )

                # Import statistics into Home Assistant database
                _LOGGER.debug(
                    "Importing %d historical statistics for %s energy (contract %s, cumulative=%.3f kWh)",
                    len(statistics),
                    energy_kind,
                    self.contract_id,
                    cumulative_sum,
                )

                async_add_external_statistics(self.hass, metadata, statistics)

        except Exception as e:
            _LOGGER.error(
                "Failed to import statistics for contract %s: %s",
                self.contract_id,
                str(e),
                exc_info=True,
            )

    async def _sync_monthly(self) -> None:
        """Sync monthly usage data with incremental download logic.

        Checks if monthly sync is needed based on metadata, calculates the
        date range to download, fetches data from API, updates cache, and prunes.

        Monthly data is typically available for the last 2+ years from Contact Energy.
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
        """Fetch usage with retry and optional split for transient HTTP errors.

        Human-friendly note: retries soak up brief API hiccups, and splitting the
        hourly window into smaller slices avoids the backend occasionally 502-ing
        on long ranges. Daily/monthly just get the retry layer.
        """

        # Quick retry loop with increasing backoff (1s, 2s, ...)
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

        # If hourly still fails and splitting is allowed, break the window into 1-day slices
        if interval == "hourly" and allow_split:
            span_days = (to_date - from_date).days + 1
            if span_days > 1:
                _LOGGER.debug(
                    "Splitting hourly sync for contract %s into 1-day windows after repeated errors",
                    self.contract_id
                )
                chunk_size = 1
                merged: list[dict] = []
                cursor = from_date
                while cursor <= to_date:
                    chunk_end = min(cursor + timedelta(days=chunk_size - 1), to_date)
                    _LOGGER.debug(
                        "Hourly chunk fetch for contract %s: %s to %s",
                        self.contract_id, cursor, chunk_end
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
                        else:
                            _LOGGER.debug(
                                "No data returned for hourly chunk %s to %s, continuing",
                                cursor, chunk_end
                            )
                    except Exception as chunk_err:
                        _LOGGER.warning(
                            "Failed to fetch hourly chunk %s to %s: %s. Skipping chunk.",
                            cursor, chunk_end, str(chunk_err)
                        )
                    cursor = chunk_end + timedelta(days=1)
                return merged

        # Out of options: surface the last error up to the caller
        raise last_error

    def _should_sync(self, interval: str) -> bool:
        """Determine if sync is needed for an interval based on metadata.

        Checks the last sync timestamp and compares with the configured
        sync interval to decide if a new sync is required.

        Args:
            interval: 'hourly', 'daily', or 'monthly'

        Returns:
            bool: True if sync is needed, False if cache is still fresh

        Logic:
            - If force_sync_mode is True: return True (forced sync)
            - If never synced before: return True (first sync)
            - If last_synced + sync_interval < now: return True (time for refresh)
            - Otherwise: return False (cache is still fresh)
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

        # Get last sync timestamp from cache metadata
        last_synced = self.cache.get_last_synced()

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
        """Calculate the date range to download for an interval.

        Determines what data to download based on:
        1. Existing cache date range
        2. Configured window size
        3. Current date

        For first sync (no cache), downloads full window.
        For incremental sync, downloads only the gap between last cached date and today.

        Args:
            interval: 'hourly', 'daily', or 'monthly'

        Returns:
            tuple[date, date]: (from_date, to_date) inclusive range to download

        Logic:
            - First sync: Download (today - window) to today
            - Incremental: Download (last_cached_date + 1 day) to today
            - Never download more than max_lookback limit
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

        # Determine to_date (always today, but respect API lookback limits)
        to_date = today

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
