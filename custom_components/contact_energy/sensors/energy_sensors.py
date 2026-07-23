"""Energy sensor entities for Contact Energy integration.

This module provides sensor entities for the Home Assistant Energy Dashboard
using the v2.0.0 architecture. These sensors track cumulative energy consumption
and are compatible with long-term statistics.

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant

from ..coordinators.usage_coordinator_v2 import UsageCoordinatorV2
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EnergySensor(SensorEntity):
    """Sensor for cumulative energy consumption.

    This sensor is designed for the Home Assistant Energy Dashboard and tracks
    cumulative energy usage. It supports both paid and free energy separately.

    The sensor calculates cumulative totals from daily usage data and is
    compatible with long-term statistics.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
        contract_id: str,
        energy_kind: str,
    ):
        """Initialize the energy sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Usage data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            contract_id: Contract ID
            energy_kind: Type of energy ("paid" or "free")
        """
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._contract_id = contract_id
        self._energy_kind = energy_kind

        kind_label = "Paid Energy" if energy_kind == "paid" else "Free Energy"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_energy_{energy_kind}"
        self._attr_name = f"{entity_name} {kind_label}"
        self._attr_icon = "mdi:lightning-bolt"

        # Track cumulative total
        self._cumulative_total: float = 0.0
        self._last_reset: datetime | None = None

    @property
    def state(self) -> float | None:
        """Return the cumulative energy consumption.

        Returns:
            Total kWh consumed (cumulative)
        """
        # Calculate cumulative total from daily data
        daily_data = self._coordinator.get_daily_usage()

        if not daily_data:
            return self._cumulative_total if self._cumulative_total > 0 else None

        # Sum up all energy consumption
        total = 0.0
        for entry in daily_data:
            if self._energy_kind == "paid":
                total += entry.get("paidUsageKwh", 0)
            else:  # free
                total += entry.get("freeUsageKwh", 0)

        self._cumulative_total = round(total, 2)
        return self._cumulative_total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes.

        Returns:
            Dictionary with metadata
        """
        return {
            "energy_kind": self._energy_kind,
            "contract_id": self._contract_id,
            "last_reset": (
                self._last_reset.isoformat() if self._last_reset else None
            ),
        }

    async def async_update(self) -> None:
        """Update the sensor state."""
        await self._coordinator.async_update_if_stale()


class DailyEnergySensor(SensorEntity):
    """Sensor for daily energy consumption.

    This sensor resets daily and shows energy consumption for the current day.
    Useful for tracking daily usage patterns.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
        energy_kind: str,
    ):
        """Initialize the daily energy sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Usage data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            energy_kind: Type of energy ("paid" or "free")
        """
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._energy_kind = energy_kind

        kind_label = "Paid" if energy_kind == "paid" else "Free"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_daily_energy_{energy_kind}"
        self._attr_name = f"{entity_name} Daily {kind_label} Energy"
        self._attr_icon = "mdi:calendar-today"

        self._last_date: date | None = None

    @property
    def state(self) -> float | None:
        """Return today's energy consumption.

        Returns:
            Total kWh consumed today
        """
        today = date.today()

        # Check if we need to reset (new day)
        if self._last_date != today:
            self._last_date = today

        # Get today's usage from hourly data
        hourly_data = self._coordinator.get_hourly_usage_for_date(today)

        if not hourly_data:
            return 0.0

        total = 0.0
        for entry in hourly_data:
            if self._energy_kind == "paid":
                total += entry.get("paidUsageKwh", 0)
            else:  # free
                total += entry.get("freeUsageKwh", 0)

        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes.

        Returns:
            Dictionary with metadata
        """
        return {
            "energy_kind": self._energy_kind,
            "date": self._last_date.isoformat() if self._last_date else None,
        }

    @property
    def last_reset(self) -> datetime | None:
        """Return the last reset time (midnight today).

        Returns:
            Datetime of last reset
        """
        if self._last_date:
            return datetime.combine(
                self._last_date,
                datetime.min.time(),
                tzinfo=timezone.utc
            )
        return None

    async def async_update(self) -> None:
        """Update the sensor state."""
        await self._coordinator.async_update_if_stale()


class MonthlyEnergySensor(SensorEntity):
    """Sensor for monthly energy consumption.

    This sensor resets monthly and shows energy consumption for the current month.
    Useful for tracking monthly usage patterns.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
        energy_kind: str,
    ):
        """Initialize the monthly energy sensor.

        Args:
            hass: Home Assistant instance
            coordinator: Usage data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            energy_kind: Type of energy ("paid" or "free")
        """
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._energy_kind = energy_kind

        kind_label = "Paid" if energy_kind == "paid" else "Free"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_monthly_energy_{energy_kind}"
        self._attr_name = f"{entity_name} Monthly {kind_label} Energy"
        self._attr_icon = "mdi:calendar-month"

        self._last_month: tuple[int, int] | None = None  # (year, month)

    @property
    def state(self) -> float | None:
        """Return this month's energy consumption.

        Returns:
            Total kWh consumed this month
        """
        today = date.today()
        current_month = (today.year, today.month)

        # Check if we need to reset (new month)
        if self._last_month != current_month:
            self._last_month = current_month

        # Get this month's usage from daily data
        daily_data = self._coordinator.daily_manager.get_usage_for_month(
            today.year, today.month
        )

        if not daily_data:
            return 0.0

        total = 0.0
        for entry in daily_data:
            if self._energy_kind == "paid":
                total += entry.get("paidUsageKwh", 0)
            else:  # free
                total += entry.get("freeUsageKwh", 0)

        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes.

        Returns:
            Dictionary with metadata
        """
        return {
            "energy_kind": self._energy_kind,
            "year": self._last_month[0] if self._last_month else None,
            "month": self._last_month[1] if self._last_month else None,
        }

    @property
    def last_reset(self) -> datetime | None:
        """Return the last reset time (first day of month).

        Returns:
            Datetime of last reset
        """
        if self._last_month:
            year, month = self._last_month
            return datetime(year, month, 1, tzinfo=timezone.utc)
        return None

    async def async_update(self) -> None:
        """Update the sensor state."""
        await self._coordinator.async_update_if_stale()
