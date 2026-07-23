"""Usage data coordinator for Contact Energy integration v2.0.0.

This module provides the UsageCoordinatorV2 that manages usage data
using the v2.0.0 architecture with separate API client and data managers.

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, date, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from ..api.usage import ContactEnergyUsageApi
from ..data_managers.usage_hourly import UsageHourlyDataManager
from ..data_managers.usage_daily import UsageDailyDataManager
from ..data_managers.usage_monthly import UsageMonthlyDataManager
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Update intervals for different usage types
HOURLY_UPDATE_INTERVAL = timedelta(hours=1)
DAILY_UPDATE_INTERVAL = timedelta(hours=6)
MONTHLY_UPDATE_INTERVAL = timedelta(hours=24)


class UsageCoordinatorV2:
    """Coordinator for Contact Energy usage data (v2.0.0 architecture).

    This coordinator manages three types of usage data independently:
    - Hourly: Updated every hour
    - Daily: Updated every 6 hours
    - Monthly: Updated daily

    Each data type has its own:
    - Data manager (with cache)
    - Staleness rules
    - Update schedule

    The coordinator uses:
    - ContactEnergyUsageApi: For fetching data from API
    - UsageHourlyDataManager: For hourly data caching
    - UsageDailyDataManager: For daily data caching
    - UsageMonthlyDataManager: For monthly data caching

    Attributes:
        hass: Home Assistant instance
        api: Usage API client
        contract_id: Contract ID for usage data
        address: Sanitized address for cache naming
        icp: ICP number
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

        Args:
            hass: Home Assistant instance
            api: Usage API client
            contract_id: Contract ID
            address: Sanitized address for cache naming
            icp: ICP number
        """
        self.hass = hass
        self.api = api
        self.contract_id = contract_id
        self.address = address
        self.icp = icp

        # Initialize data managers
        self.hourly_manager = UsageHourlyDataManager(address, icp)
        self.daily_manager = UsageDailyDataManager(address, icp)
        self.monthly_manager = UsageMonthlyDataManager(address, icp)

        # Track last update times
        self._last_hourly_update: datetime | None = None
        self._last_daily_update: datetime | None = None
        self._last_monthly_update: datetime | None = None

        # Cleanup trackers
        self._cleanup_trackers: list = []

        _LOGGER.debug(
            "UsageCoordinatorV2 initialized for contract %s (%s_%s)",
            contract_id,
            address,
            icp
        )

    async def async_setup(self) -> None:
        """Set up the coordinator and load cached data."""
        # Load existing caches
        await self.hourly_manager.load()
        await self.daily_manager.load()
        await self.monthly_manager.load()

        # Schedule periodic updates
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

        _LOGGER.info("UsageCoordinatorV2 setup complete for contract %s", self.contract_id)

        # Trigger initial update if data is stale
        await self.async_update_if_stale()

    async def async_shutdown(self) -> None:
        """Shut down the coordinator and clean up resources."""
        # Cancel all scheduled updates
        for cleanup in self._cleanup_trackers:
            cleanup()
        self._cleanup_trackers.clear()

        _LOGGER.debug("UsageCoordinatorV2 shut down for contract %s", self.contract_id)

    async def async_update_if_stale(self) -> None:
        """Update data if any cache is stale."""
        if self.hourly_manager.is_stale():
            await self._async_update_hourly(None)

        if self.daily_manager.is_stale():
            await self._async_update_daily(None)

        if self.monthly_manager.is_stale():
            await self._async_update_monthly(None)

    async def _async_update_hourly(self, now: datetime | None) -> None:
        """Update hourly usage data.

        Args:
            now: Current time (from event tracker)
        """
        # Check if update is needed
        if not self.hourly_manager.is_stale():
            _LOGGER.debug("Hourly usage data is fresh, skipping update")
            return

        try:
            _LOGGER.info("Updating hourly usage data for contract %s", self.contract_id)

            # Calculate date range (last 7 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=7)

            # Fetch data from API
            usage_data = await self.api.get_hourly_usage(
                contract_id=self.contract_id,
                from_date=start_date,
                to_date=end_date,
            )

            # Update cache
            self.hourly_manager.update(usage_data, self.contract_id)

            # Prune old data
            self.hourly_manager.prune()

            # Save cache
            await self.hourly_manager.save()

            self._last_hourly_update = datetime.now(timezone.utc)
            _LOGGER.info(
                "Hourly usage data updated: %d records",
                len(usage_data)
            )

        except Exception as err:
            _LOGGER.error("Failed to update hourly usage data: %s", err)

    async def _async_update_daily(self, now: datetime | None) -> None:
        """Update daily usage data.

        Args:
            now: Current time (from event tracker)
        """
        # Check if update is needed
        if not self.daily_manager.is_stale():
            _LOGGER.debug("Daily usage data is fresh, skipping update")
            return

        try:
            _LOGGER.info("Updating daily usage data for contract %s", self.contract_id)

            # Calculate date range (last 90 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=90)

            # Fetch data from API
            usage_data = await self.api.get_daily_usage(
                contract_id=self.contract_id,
                from_date=start_date,
                to_date=end_date,
            )

            # Update cache
            self.daily_manager.update(usage_data, self.contract_id)

            # Prune old data
            self.daily_manager.prune()

            # Save cache
            await self.daily_manager.save()

            self._last_daily_update = datetime.now(timezone.utc)
            _LOGGER.info(
                "Daily usage data updated: %d records",
                len(usage_data)
            )

        except Exception as err:
            _LOGGER.error("Failed to update daily usage data: %s", err)

    async def _async_update_monthly(self, now: datetime | None) -> None:
        """Update monthly usage data.

        Args:
            now: Current time (from event tracker)
        """
        # Check if update is needed
        if not self.monthly_manager.is_stale():
            _LOGGER.debug("Monthly usage data is fresh, skipping update")
            return

        try:
            _LOGGER.info("Updating monthly usage data for contract %s", self.contract_id)

            # Calculate date range (last 24 months)
            end_date = date.today()
            start_date = end_date - timedelta(days=730)  # Approximately 24 months

            # Fetch data from API
            usage_data = await self.api.get_monthly_usage(
                contract_id=self.contract_id,
                from_date=start_date,
                to_date=end_date,
            )

            # Update cache
            self.monthly_manager.update(usage_data, self.contract_id)

            # Prune old data
            self.monthly_manager.prune()

            # Save cache
            await self.monthly_manager.save()

            self._last_monthly_update = datetime.now(timezone.utc)
            _LOGGER.info(
                "Monthly usage data updated: %d records",
                len(usage_data)
            )

        except Exception as err:
            _LOGGER.error("Failed to update monthly usage data: %s", err)

    async def force_update_all(self) -> None:
        """Force update of all usage data types."""
        _LOGGER.info("Forcing update of all usage data for contract %s", self.contract_id)

        await self._async_update_hourly(None)
        await self._async_update_daily(None)
        await self._async_update_monthly(None)

    def get_hourly_usage(self) -> list[dict[str, Any]]:
        """Get cached hourly usage data.

        Returns:
            List of hourly usage records
        """
        return self.hourly_manager.get_usage()

    def get_daily_usage(self) -> list[dict[str, Any]]:
        """Get cached daily usage data.

        Returns:
            List of daily usage records
        """
        return self.daily_manager.get_usage()

    def get_monthly_usage(self) -> list[dict[str, Any]]:
        """Get cached monthly usage data.

        Returns:
            List of monthly usage records
        """
        return self.monthly_manager.get_usage()

    def get_hourly_usage_for_date(self, target_date: date) -> list[dict[str, Any]]:
        """Get hourly usage for a specific date.

        Args:
            target_date: Date to retrieve usage for

        Returns:
            List of hourly usage records for the date
        """
        return self.hourly_manager.get_usage_for_date(target_date)

    def get_daily_usage_for_date(self, target_date: date) -> dict[str, Any] | None:
        """Get daily usage for a specific date.

        Args:
            target_date: Date to retrieve usage for

        Returns:
            Daily usage record for the date, or None if not found
        """
        return self.daily_manager.get_usage_for_date(target_date)

    def get_monthly_usage_for_month(self, year: int, month: int) -> dict[str, Any] | None:
        """Get monthly usage for a specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            Monthly usage record for the month, or None if not found
        """
        return self.monthly_manager.get_usage_for_month(year, month)
