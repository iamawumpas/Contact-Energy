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
        "window_days": 9,  # Keep last 9 days of hourly data
        "sync_interval_hours": 24,  # Sync once per day
        "max_lookback_days": 14,  # API limit (Contact Energy provides ~2 weeks)
    },
    "daily": {
        "window_days": 35,  # Keep last 35 days of daily data
        "sync_interval_hours": 24,  # Sync once per day
        "max_lookback_days": 60,  # API limit (Contact Energy provides ~2 months)
    },
    "monthly": {
        "window_months": 18,  # Keep last 18 months of monthly data
        "sync_interval_hours": 168,  # Sync once per week (7 days * 24 hours)
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
        sync regardless of when the last sync occurred. It temporarily disables
        the time threshold checks by clearing the last sync timestamp.
        """
        _LOGGER.info("Force sync requested for contract %s", self.contract_id)
        
        # Temporarily clear last sync time to bypass threshold checks
        await self.cache.load()
        original_last_synced = self.cache.data.get("metadata", {}).get("last_synced")
        self.cache.data["metadata"]["last_synced"] = None
        
        try:
            # Perform sync (will bypass time checks due to None last_synced)
            await self.async_sync_usage()
        finally:
            # Restore original timestamp if sync failed
            # (successful sync will set a new timestamp anyway)
            if self.cache.data.get("metadata", {}).get("last_synced") is None:
                self.cache.data["metadata"]["last_synced"] = original_last_synced

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

            # Download hourly data with retry and optional range splitting to dodge transient 502s
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

        # If hourly still fails and splitting is allowed, break the window into 5-day slices
        if interval == "hourly" and allow_split:
            span_days = (to_date - from_date).days + 1
            if span_days > 1:
                _LOGGER.debug(
                    "Splitting hourly sync for contract %s into smaller windows after repeated errors",
                    self.contract_id
                )
                chunk_size = 5
                merged: list[dict] = []
                cursor = from_date
                while cursor <= to_date:
                    chunk_end = min(cursor + timedelta(days=chunk_size - 1), to_date)
                    _LOGGER.debug(
                        "Hourly chunk fetch for contract %s: %s to %s",
                        self.contract_id, cursor, chunk_end
                    )
                    merged.extend(
                        await self._fetch_usage_with_resilience(
                            interval=interval,
                            from_date=cursor,
                            to_date=chunk_end,
                            allow_split=False,
                            max_attempts=max_attempts,
                        )
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
            - If never synced before: return True (first sync)
            - If last_synced + sync_interval < now: return True (time for refresh)
            - Otherwise: return False (cache is still fresh)
        """
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
            window_days = config["window_months"] * 30  # Approximate
            max_lookback = config["max_lookback_months"] * 30  # Approximate

        # Determine from_date
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
