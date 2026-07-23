"""Usage data coordinator for Contact Energy integration v2.0.0.

=== WHAT THIS DOES ===
This module contains ``UsageCoordinatorV2``, a coordinator that manages three
different kinds of electricity-usage history:
- hourly usage,
- daily usage, and
- monthly usage.

Each kind of usage data has its own cache, its own freshness rules, and its
own refresh schedule. The coordinator loads cached data, schedules timed
updates, fetches fresh usage when needed, and keeps the cache trimmed.

=== FOR NON-CODERS ===
Think of this file as a three-drawer filing system:
- one drawer for hourly usage,
- one drawer for daily usage,
- one drawer for monthly usage.

The coordinator checks each drawer on its own schedule. If a drawer contains
old information, it asks Contact Energy for a newer copy and replaces it.

Helpful terms:
- "Coordinator": one shared organiser that fetches data for many sensors.
- "Polling": checking again later on a timer.
- "Update interval": the waiting time between scheduled checks.
- "Data refresh": updating old stored information with newer information.

Version: 2.0.0
"""

# This future import keeps modern type hints available everywhere in the file.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: records normal activity, skips, and failures for troubleshooting.
import logging

# datetime/date/timezone/timedelta: used for schedules, date ranges, and UTC timestamps.
from datetime import date, datetime, timedelta, timezone

# Any: used when usage records can contain mixed value types.
from typing import Any

# HomeAssistant: the core Home Assistant object this coordinator belongs to.
from homeassistant.core import HomeAssistant

# async_track_time_interval: Home Assistant helper for "run this function every X time units".
from homeassistant.helpers.event import async_track_time_interval

# ContactEnergyUsageApi: API helper that downloads usage data from Contact Energy.
from ..api.usage import ContactEnergyUsageApi

# UsageHourlyDataManager: handles caching and stale checks for hourly usage.
from ..data_managers.usage_hourly import UsageHourlyDataManager

# UsageDailyDataManager: handles caching and stale checks for daily usage.
from ..data_managers.usage_daily import UsageDailyDataManager

# UsageMonthlyDataManager: handles caching and stale checks for monthly usage.
from ..data_managers.usage_monthly import UsageMonthlyDataManager

# DOMAIN: the integration's unique Home Assistant name prefix.
from ..const import DOMAIN

# ============================================================================
# LOGGER AND INTERVAL CONFIGURATION
# ============================================================================

# Create a logger dedicated to this module.
_LOGGER = logging.getLogger(__name__)

# These timedeltas describe how frequently each usage type is allowed to poll.
HOURLY_UPDATE_INTERVAL = timedelta(hours=1)
DAILY_UPDATE_INTERVAL = timedelta(hours=6)
MONTHLY_UPDATE_INTERVAL = timedelta(hours=24)


# ============================================================================
# USAGE COORDINATOR V2
# ============================================================================

class UsageCoordinatorV2:
    """Coordinator for Contact Energy usage data.

    === WHAT THIS DOES ===
    This class coordinates three independent usage-data refresh workflows. It
    knows when each cache is stale, when each update should run, how to fetch
    the corresponding usage history, and how to save the refreshed results.

    === FOR NON-CODERS ===
    This class is like a scheduler managing three recurring chores.
    - Hourly usage gets checked often.
    - Daily usage gets checked less often.
    - Monthly usage gets checked least often.

    Keeping them separate matters because each data type changes at a different
    speed and covers a different amount of history.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: ContactEnergyUsageApi,
        contract_id: str,
        address: str,
        icp: str,
    ):
        """Initialize usage coordinator.

        === WHAT THIS DOES ===
        This constructor stores the dependencies and identifiers the
        coordinator needs, then creates one cache/data-manager object for each
        usage interval.

        === FOR NON-CODERS ===
        This is the setup checklist. It gives the coordinator:
        - the Home Assistant system,
        - the API helper used to fetch live usage,
        - the contract being tracked, and
        - the property identifiers used for caching.
        """
        # ====================================================================
        # STEP 1: Store the objects and identifiers we will reuse later.
        # ====================================================================
        self.hass = hass
        self.api = api
        self.contract_id = contract_id
        self.address = address
        self.icp = icp

        # ====================================================================
        # STEP 2: Create one dedicated data manager per usage interval.
        # ====================================================================
        # Each manager stores data separately because hourly, daily, and
        # monthly records have different cache windows and stale rules.
        self.hourly_manager = UsageHourlyDataManager(address, icp)
        self.daily_manager = UsageDailyDataManager(address, icp)
        self.monthly_manager = UsageMonthlyDataManager(address, icp)

        # ====================================================================
        # STEP 3: Prepare bookkeeping fields for last-update tracking.
        # ====================================================================
        # These timestamps are useful for diagnostics and future decisions.
        self._last_hourly_update: datetime | None = None
        self._last_daily_update: datetime | None = None
        self._last_monthly_update: datetime | None = None

        # Store cleanup callbacks here so we can stop scheduled timers later.
        self._cleanup_trackers: list = []

        _LOGGER.debug(
            "UsageCoordinatorV2 initialized for %s via %s tracker (%s_%s)",
            f"{DOMAIN}:{contract_id}",
            "usage",
            address,
            icp,
        )

    async def async_setup(self) -> None:
        """Load caches and start scheduled update timers.

        === WHAT THIS DOES ===
        This method prepares the coordinator for normal operation. It loads all
        saved caches from disk, registers timed callbacks for each data type,
        and then performs an initial stale-data check.

        === FOR NON-CODERS ===
        Think of this as opening the office for the day:
        1. Pull yesterday's files out of storage.
        2. Set the alarm clock for each recurring task.
        3. Immediately check whether any drawer already needs attention.
        """
        # ====================================================================
        # STEP 1: Load any previously saved usage history into memory.
        # ====================================================================
        await self.hourly_manager.load()
        await self.daily_manager.load()
        await self.monthly_manager.load()

        # ====================================================================
        # STEP 2: Register timed callbacks for each usage category.
        # ====================================================================
        # Home Assistant returns a cleanup function for each scheduled timer.
        # We save those functions so async_shutdown() can stop them later.
        self._cleanup_trackers.append(
            async_track_time_interval(
                self.hass,
                self._async_update_hourly,
                HOURLY_UPDATE_INTERVAL,
            )
        )
        self._cleanup_trackers.append(
            async_track_time_interval(
                self.hass,
                self._async_update_daily,
                DAILY_UPDATE_INTERVAL,
            )
        )
        self._cleanup_trackers.append(
            async_track_time_interval(
                self.hass,
                self._async_update_monthly,
                MONTHLY_UPDATE_INTERVAL,
            )
        )

        # Log that recurring timers are now active.
        _LOGGER.info("UsageCoordinatorV2 setup complete for contract %s", self.contract_id)

        # ====================================================================
        # STEP 3: Run an immediate stale-data check.
        # ====================================================================
        # This avoids waiting for the first timer if data is already out of date.
        await self.async_update_if_stale()

    async def async_shutdown(self) -> None:
        """Stop scheduled timers and release coordinator resources.

        === WHAT THIS DOES ===
        This method cancels all registered periodic update callbacks.

        === FOR NON-CODERS ===
        If async_setup() is opening the office and setting alarm clocks,
        async_shutdown() is closing the office and turning those alarms off.
        """
        # Call each stored cleanup callback to cancel its scheduled timer.
        for cleanup in self._cleanup_trackers:
            cleanup()

        # Clear the list so the coordinator no longer holds stale callbacks.
        self._cleanup_trackers.clear()

        _LOGGER.debug("UsageCoordinatorV2 shut down for contract %s", self.contract_id)

    async def async_update_if_stale(self) -> None:
        """Refresh only the caches that currently look stale.

        === WHAT THIS DOES ===
        This method asks each data manager whether its cache is stale and then
        updates only the data types that need attention.

        === FOR NON-CODERS ===
        Instead of replacing every file drawer every time, this method checks
        each drawer's date label and refreshes only the drawers that are old.
        """
        # Check the hourly cache first because it changes the most frequently.
        if self.hourly_manager.is_stale():
            await self._async_update_hourly(None)

        # Check the daily cache next.
        if self.daily_manager.is_stale():
            await self._async_update_daily(None)

        # Check the monthly cache last because it changes the least often.
        if self.monthly_manager.is_stale():
            await self._async_update_monthly(None)

    async def _async_update_hourly(self, now: datetime | None) -> None:
        """Refresh hourly usage history when needed.

        === WHAT THIS DOES ===
        This method fetches roughly the last week of hourly usage data when the
        hourly cache is stale, then saves the refreshed result.

        === FOR NON-CODERS ===
        Hourly data is the most detailed timeline. This method says,
        "If the hour-by-hour history is old, ask for a fresh copy."

        Args:
            now: The scheduler-provided current time. It is accepted because
                Home Assistant passes it in when the timer fires.
        """
        # If the cache is still fresh, leave it alone and stop immediately.
        if not self.hourly_manager.is_stale():
            _LOGGER.debug("Hourly usage data is fresh, skipping update")
            return

        try:
            # Record that an hourly refresh is starting for this contract.
            _LOGGER.info("Updating hourly usage data for contract %s", self.contract_id)

            # Build the date window we want from the API.
            # end_date is today, and start_date reaches 7 days into the past.
            end_date = date.today()
            start_date = end_date - timedelta(days=7)

            # Download the requested hourly records from Contact Energy.
            usage_data = await self.api.get_hourly_usage(
                contract_id=self.contract_id,
                from_date=start_date,
                to_date=end_date,
            )

            # Replace/update the cached hourly data with the new download.
            self.hourly_manager.update(usage_data, self.contract_id)

            # Trim away any old rows the manager no longer wants to keep.
            self.hourly_manager.prune()

            # Persist the refreshed hourly cache to disk.
            await self.hourly_manager.save()

            # Store the exact UTC moment this hourly update finished.
            self._last_hourly_update = datetime.now(timezone.utc)

            # Log how many hourly records were processed.
            _LOGGER.info("Hourly usage data updated: %d records", len(usage_data))

        except Exception as err:
            # Log the failure. This version of the coordinator keeps running
            # even if one scheduled refresh fails.
            _LOGGER.error("Failed to update hourly usage data: %s", err)

    async def _async_update_daily(self, now: datetime | None) -> None:
        """Refresh daily usage history when needed.

        === WHAT THIS DOES ===
        This method fetches about 90 days of day-by-day usage data when the
        daily cache is stale, then saves the refreshed result.

        === FOR NON-CODERS ===
        Daily data answers questions like "How much power was used on each
        day?" This method refreshes that summary when the saved copy is old.

        Args:
            now: The scheduler-provided current time.
        """
        # Reuse the current cache if it is still considered fresh.
        if not self.daily_manager.is_stale():
            _LOGGER.debug("Daily usage data is fresh, skipping update")
            return

        try:
            # Announce that the daily refresh cycle is starting.
            _LOGGER.info("Updating daily usage data for contract %s", self.contract_id)

            # Define the date window for the API request.
            end_date = date.today()
            start_date = end_date - timedelta(days=90)

            # Request the daily usage summary from Contact Energy.
            usage_data = await self.api.get_daily_usage(
                contract_id=self.contract_id,
                from_date=start_date,
                to_date=end_date,
            )

            # Update the cached daily records.
            self.daily_manager.update(usage_data, self.contract_id)

            # Remove daily records that sit outside the kept history window.
            self.daily_manager.prune()

            # Save the refreshed daily cache to disk.
            await self.daily_manager.save()

            # Store when this successful daily update finished.
            self._last_daily_update = datetime.now(timezone.utc)

            # Record the number of daily rows processed.
            _LOGGER.info("Daily usage data updated: %d records", len(usage_data))

        except Exception as err:
            # Log the error and keep the coordinator alive for future cycles.
            _LOGGER.error("Failed to update daily usage data: %s", err)

    async def _async_update_monthly(self, now: datetime | None) -> None:
        """Refresh monthly usage history when needed.

        === WHAT THIS DOES ===
        This method fetches about two years of month-by-month usage data when
        the monthly cache is stale, then saves the refreshed result.

        === FOR NON-CODERS ===
        Monthly data is the broadest summary. It is used for long-term trends,
        so it does not need to be refreshed as often as hourly data.

        Args:
            now: The scheduler-provided current time.
        """
        # Skip the API call entirely if the monthly cache is still fresh.
        if not self.monthly_manager.is_stale():
            _LOGGER.debug("Monthly usage data is fresh, skipping update")
            return

        try:
            # Announce that a monthly-history refresh is starting.
            _LOGGER.info("Updating monthly usage data for contract %s", self.contract_id)

            # Build the approximate 24-month request range.
            end_date = date.today()
            start_date = end_date - timedelta(days=730)

            # Ask Contact Energy for monthly usage records in that range.
            usage_data = await self.api.get_monthly_usage(
                contract_id=self.contract_id,
                from_date=start_date,
                to_date=end_date,
            )

            # Update the cached monthly records with the new payload.
            self.monthly_manager.update(usage_data, self.contract_id)

            # Trim away months that are older than the kept history window.
            self.monthly_manager.prune()

            # Persist the refreshed monthly cache to disk.
            await self.monthly_manager.save()

            # Remember the UTC time when monthly refresh succeeded.
            self._last_monthly_update = datetime.now(timezone.utc)

            # Record how many monthly rows were processed.
            _LOGGER.info("Monthly usage data updated: %d records", len(usage_data))

        except Exception as err:
            # Log the failure instead of crashing the scheduler callback.
            _LOGGER.error("Failed to update monthly usage data: %s", err)

    async def force_update_all(self) -> None:
        """Run all three refresh methods immediately.

        === WHAT THIS DOES ===
        This helper manually triggers hourly, daily, and monthly refresh logic.

        === FOR NON-CODERS ===
        This is the "refresh every drawer now" action.
        """
        # Log that a full manual refresh was requested for this contract.
        _LOGGER.info("Forcing update of all usage data for contract %s", self.contract_id)

        # Run the refresh methods one after another so each cache gets checked.
        await self._async_update_hourly(None)
        await self._async_update_daily(None)
        await self._async_update_monthly(None)

    def get_hourly_usage(self) -> list[dict[str, Any]]:
        """Return cached hourly usage records.

        === WHAT THIS DOES ===
        This helper returns the current in-memory hourly usage list.

        === FOR NON-CODERS ===
        It opens the hourly drawer and hands back the contents as they are now.
        """
        # Return the hourly cache exactly as maintained by the hourly manager.
        return self.hourly_manager.get_usage()

    def get_daily_usage(self) -> list[dict[str, Any]]:
        """Return cached daily usage records.

        === WHAT THIS DOES ===
        This helper returns the current in-memory daily usage list.

        === FOR NON-CODERS ===
        It opens the daily drawer and hands back the saved day-by-day history.
        """
        # Return the daily cache exactly as maintained by the daily manager.
        return self.daily_manager.get_usage()

    def get_monthly_usage(self) -> list[dict[str, Any]]:
        """Return cached monthly usage records.

        === WHAT THIS DOES ===
        This helper returns the current in-memory monthly usage list.

        === FOR NON-CODERS ===
        It opens the monthly drawer and hands back the saved month-by-month history.
        """
        # Return the monthly cache exactly as maintained by the monthly manager.
        return self.monthly_manager.get_usage()

    def get_hourly_usage_for_date(self, target_date: date) -> list[dict[str, Any]]:
        """Return hourly usage for one specific day.

        === WHAT THIS DOES ===
        This helper filters the cached hourly records down to one calendar date.

        === FOR NON-CODERS ===
        Instead of returning every hour ever cached, it answers the narrower
        question, "Show me just the hourly entries for this one day."
        """
        # Ask the hourly manager to perform the date-based filtering for us.
        return self.hourly_manager.get_usage_for_date(target_date)

    def get_daily_usage_for_date(self, target_date: date) -> dict[str, Any] | None:
        """Return daily usage for one specific day.

        === WHAT THIS DOES ===
        This helper looks up one daily usage record by date.

        === FOR NON-CODERS ===
        This is like finding one named page in the daily drawer instead of
        pulling out the entire stack.
        """
        # Return the one matching daily record, or None if that date is absent.
        return self.daily_manager.get_usage_for_date(target_date)

    def get_monthly_usage_for_month(self, year: int, month: int) -> dict[str, Any] | None:
        """Return monthly usage for one specific month.

        === WHAT THIS DOES ===
        This helper looks up one monthly record using a year and month.

        === FOR NON-CODERS ===
        It answers the question, "What usage summary do we have for this month?"
        without returning the rest of the history.
        """
        # Return the matching month entry, or None if the cache does not contain it.
        return self.monthly_manager.get_usage_for_month(year, month)
