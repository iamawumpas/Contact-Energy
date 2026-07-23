"""Usage sensor entities for Contact Energy integration.

This module provides sensor entities for usage data (hourly, daily, monthly)
using the v2.0.0 architecture with separate data managers.

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinators.usage_coordinator_v2 import UsageCoordinatorV2
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Maximum attribute size for Home Assistant (to avoid database bloat)
ATTRIBUTE_SIZE_BUDGET = 15000


class UsageDataSensor(SensorEntity):
    """Sensor that exposes cached usage data as attributes.

    This sensor provides access to hourly, daily, and monthly usage data
    through sensor attributes. The state shows the last update timestamp.

    Attributes are formatted for consumption by dashboard cards like ApexCharts.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
        contract_id: str,
    ):
        """Initialize the usage data sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Usage data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            contract_id: Contract ID
        """
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._contract_id = contract_id

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_usage"
        self._attr_name = f"{entity_name} Usage Data"
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def state(self) -> str | None:
        """Return the state (last update timestamp).

        Returns:
            ISO format timestamp of last update
        """
        # Return most recent update timestamp
        last_hourly = self._coordinator._last_hourly_update
        last_daily = self._coordinator._last_daily_update
        last_monthly = self._coordinator._last_monthly_update

        timestamps = [t for t in [last_hourly, last_daily, last_monthly] if t]
        if timestamps:
            most_recent = max(timestamps)
            return most_recent.isoformat()

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with cached usage data.

        Returns:
            Dictionary with hourly, daily, and monthly usage data
        """
        attributes = {}

        # Get hourly usage data
        hourly_data = self._coordinator.get_hourly_usage()
        if hourly_data:
            # Limit size to avoid database bloat
            attributes["hourly_usage"] = self._format_hourly_data(hourly_data[:168])  # 7 days
            attributes["hourly_data_count"] = len(hourly_data)

        # Get daily usage data
        daily_data = self._coordinator.get_daily_usage()
        if daily_data:
            attributes["daily_usage"] = self._format_daily_data(daily_data[:90])  # 90 days
            attributes["daily_data_count"] = len(daily_data)

        # Get monthly usage data
        monthly_data = self._coordinator.get_monthly_usage()
        if monthly_data:
            attributes["monthly_usage"] = self._format_monthly_data(monthly_data[:24])  # 24 months
            attributes["monthly_data_count"] = len(monthly_data)

        # Add metadata
        attributes["contract_id"] = self._contract_id
        attributes["last_hourly_update"] = (
            self._coordinator._last_hourly_update.isoformat()
            if self._coordinator._last_hourly_update
            else None
        )
        attributes["last_daily_update"] = (
            self._coordinator._last_daily_update.isoformat()
            if self._coordinator._last_daily_update
            else None
        )
        attributes["last_monthly_update"] = (
            self._coordinator._last_monthly_update.isoformat()
            if self._coordinator._last_monthly_update
            else None
        )

        return attributes

    def _format_hourly_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format hourly usage data for attributes.

        Args:
            data: Raw hourly usage data

        Returns:
            Formatted hourly data
        """
        formatted = []
        for entry in data:
            formatted.append({
                "timestamp": entry.get("startTime"),
                "paid_kwh": entry.get("paidUsageKwh", 0),
                "free_kwh": entry.get("freeUsageKwh", 0),
                "total_kwh": (
                    entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                ),
                "cost": entry.get("cost", 0),
            })
        return formatted

    def _format_daily_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format daily usage data for attributes.

        Args:
            data: Raw daily usage data

        Returns:
            Formatted daily data
        """
        formatted = []
        for entry in data:
            formatted.append({
                "date": entry.get("startTime"),
                "paid_kwh": entry.get("paidUsageKwh", 0),
                "free_kwh": entry.get("freeUsageKwh", 0),
                "total_kwh": (
                    entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                ),
                "cost": entry.get("cost", 0),
            })
        return formatted

    def _format_monthly_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format monthly usage data for attributes.

        Args:
            data: Raw monthly usage data

        Returns:
            Formatted monthly data
        """
        formatted = []
        for entry in data:
            formatted.append({
                "month": entry.get("startTime"),
                "paid_kwh": entry.get("paidUsageKwh", 0),
                "free_kwh": entry.get("freeUsageKwh", 0),
                "total_kwh": (
                    entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                ),
                "cost": entry.get("cost", 0),
            })
        return formatted

    async def async_update(self) -> None:
        """Update the sensor state.

        Triggers coordinator updates if data is stale.
        """
        await self._coordinator.async_update_if_stale()


class HourlyUsageSensor(SensorEntity):
    """Sensor for hourly usage data.

    Provides today's hourly usage as sensor attributes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
    ):
        """Initialize the hourly usage sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Usage data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
        """
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_hourly_usage"
        self._attr_name = f"{entity_name} Hourly Usage"
        self._attr_icon = "mdi:chart-line"
        self._attr_unit_of_measurement = "kWh"

    @property
    def state(self) -> float | None:
        """Return the state (today's total usage).

        Returns:
            Total kWh for today
        """
        today = date.today()
        hourly_data = self._coordinator.get_hourly_usage_for_date(today)

        if not hourly_data:
            return None

        total = 0.0
        for entry in hourly_data:
            total += entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)

        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with today's hourly data.

        Returns:
            Dictionary with hourly breakdown for today
        """
        today = date.today()
        hourly_data = self._coordinator.get_hourly_usage_for_date(today)

        if not hourly_data:
            return {}

        return {
            "hourly_data": [
                {
                    "hour": entry.get("startTime"),
                    "paid_kwh": entry.get("paidUsageKwh", 0),
                    "free_kwh": entry.get("freeUsageKwh", 0),
                    "total_kwh": (
                        entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                    ),
                }
                for entry in hourly_data
            ],
            "date": today.isoformat(),
        }

    async def async_update(self) -> None:
        """Update the sensor state."""
        await self._coordinator.async_update_if_stale()


class DailyUsageSensor(SensorEntity):
    """Sensor for daily usage data.

    Provides current month's daily usage as sensor attributes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
    ):
        """Initialize the daily usage sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Usage data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
        """
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_daily_usage"
        self._attr_name = f"{entity_name} Daily Usage"
        self._attr_icon = "mdi:calendar"
        self._attr_unit_of_measurement = "kWh"

    @property
    def state(self) -> float | None:
        """Return the state (current month's total usage).

        Returns:
            Total kWh for current month
        """
        today = date.today()
        daily_data = self._coordinator.daily_manager.get_usage_for_month(
            today.year, today.month
        )

        if not daily_data:
            return None

        total = 0.0
        for entry in daily_data:
            total += entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)

        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with current month's daily data.

        Returns:
            Dictionary with daily breakdown for current month
        """
        today = date.today()
        daily_data = self._coordinator.daily_manager.get_usage_for_month(
            today.year, today.month
        )

        if not daily_data:
            return {}

        return {
            "daily_data": [
                {
                    "date": entry.get("startTime"),
                    "paid_kwh": entry.get("paidUsageKwh", 0),
                    "free_kwh": entry.get("freeUsageKwh", 0),
                    "total_kwh": (
                        entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                    ),
                }
                for entry in daily_data
            ],
            "month": f"{today.year}-{today.month:02d}",
        }

    async def async_update(self) -> None:
        """Update the sensor state."""
        await self._coordinator.async_update_if_stale()


class MonthlyUsageSensor(SensorEntity):
    """Sensor for monthly usage data.

    Provides current year's monthly usage as sensor attributes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
    ):
        """Initialize the monthly usage sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Usage data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
        """
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_monthly_usage"
        self._attr_name = f"{entity_name} Monthly Usage"
        self._attr_icon = "mdi:calendar-month"
        self._attr_unit_of_measurement = "kWh"

    @property
    def state(self) -> float | None:
        """Return the state (current year's total usage).

        Returns:
            Total kWh for current year
        """
        today = date.today()
        monthly_data = self._coordinator.monthly_manager.get_usage_for_year(today.year)

        if not monthly_data:
            return None

        total = 0.0
        for entry in monthly_data:
            total += entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)

        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with current year's monthly data.

        Returns:
            Dictionary with monthly breakdown for current year
        """
        today = date.today()
        monthly_data = self._coordinator.monthly_manager.get_usage_for_year(today.year)

        if not monthly_data:
            return {}

        return {
            "monthly_data": [
                {
                    "month": entry.get("startTime"),
                    "paid_kwh": entry.get("paidUsageKwh", 0),
                    "free_kwh": entry.get("freeUsageKwh", 0),
                    "total_kwh": (
                        entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                    ),
                }
                for entry in monthly_data
            ],
            "year": today.year,
        }

    async def async_update(self) -> None:
        """Update the sensor state."""
        await self._coordinator.async_update_if_stale()
