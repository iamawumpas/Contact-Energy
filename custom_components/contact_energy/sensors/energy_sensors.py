"""Energy sensor entities for Contact Energy integration.

=== WHAT THIS DOES ===
This module defines Home Assistant energy sensors that convert Contact Energy
usage data into cumulative values suitable for dashboards and statistics.

The sensors in this file provide three kinds of energy views:
- cumulative energy totals across all known history
- today's energy total
- this month's energy total

Each sensor can be created for either paid energy or free energy so the
integration can track those categories separately.

=== FOR NON-CODERS ===
Important terms explained simply:
- Home Assistant: the smart-home platform showing these entities.
- sensor: a read-only item that reports information.
- entity: any item Home Assistant knows how to track.
- state: the main value shown for the entity.
- attributes: extra descriptive fields attached to that entity.

These sensors are built for Home Assistant's Energy Dashboard, which expects
energy readings in a format that behaves like a meter total or rolling daily /
monthly figure.

Version: 2.0.0
"""
# This import enables modern type-hint syntax while keeping compatibility tidy.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging lets this module record diagnostic details during troubleshooting.
import logging

# date handles calendar comparisons, datetime handles timestamps, timedelta is
# imported for date/time math, and timezone lets reset times be timezone-aware.
from datetime import date, datetime, timedelta, timezone

# Any supports type hints for attribute dictionaries containing mixed values.
from typing import Any

# SensorEntity is the base class for sensors, SensorDeviceClass tells Home
# Assistant the sensor measures energy, and SensorStateClass describes how the
# numeric value behaves over time.
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

# UnitOfEnergy provides Home Assistant's standard energy unit constants.
from homeassistant.const import UnitOfEnergy

# HomeAssistant represents the running Home Assistant application instance.
from homeassistant.core import HomeAssistant

# UsageCoordinatorV2 is the shared data source that supplies usage history.
from ..coordinators.usage_coordinator_v2 import UsageCoordinatorV2

# DOMAIN is the integration's identifier used for stable unique entity IDs.
from ..const import DOMAIN

# ============================================================================
# LOGGER SETUP
# ============================================================================
# Create a logger that tags messages with this module's name.
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# CUMULATIVE ENERGY SENSOR
# ============================================================================
class EnergySensor(SensorEntity):
    """Sensor for cumulative energy consumption.

    === WHAT THIS DOES ===
    This sensor sums all available daily usage data and reports one cumulative
    total suitable for Home Assistant's Energy Dashboard and long-term statistics.

    === FOR NON-CODERS ===
    Think of this like a running odometer for energy. It keeps increasing as more
    total usage is included.
    """

    # Mark this entity as an energy sensor so Home Assistant treats it correctly.
    _attr_device_class = SensorDeviceClass.ENERGY

    # Tell Home Assistant this is a running total that normally only increases.
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    # Report energy in kilowatt-hours, the standard unit expected by dashboards.
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

        === WHAT THIS DOES ===
        This constructor prepares a cumulative energy sensor for either paid or
        free energy and assigns its identity and display settings.
        """
        # Store the Home Assistant instance for integration context.
        self.hass = hass

        # Store the shared coordinator that supplies usage history.
        self._coordinator = coordinator

        # Store identity values and configuration choices for this entity.
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._contract_id = contract_id
        self._energy_kind = energy_kind

        # Choose a human-readable label based on whether this sensor tracks paid
        # energy or free promotional energy.
        kind_label = "Paid Energy" if energy_kind == "paid" else "Free Energy"

        # Build the unique ID Home Assistant uses to persist the entity.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_energy_{energy_kind}"

        # Set the display name users will see in the UI.
        self._attr_name = f"{entity_name} {kind_label}"

        # Use a lightning icon because the sensor represents electricity usage.
        self._attr_icon = "mdi:lightning-bolt"

        # Store the most recently calculated cumulative total so we can reuse it
        # if fresh daily data is temporarily unavailable.
        self._cumulative_total: float = 0.0

        # Track a reset timestamp field for metadata compatibility, even though
        # total-increasing sensors typically do not reset in normal operation.
        self._last_reset: datetime | None = None

    @property
    def state(self) -> float | None:
        """Return the cumulative energy consumption.

        === WHAT THIS DOES ===
        This property recalculates the cumulative total from daily usage data and
        returns that number as the sensor's main state.
        """
        # Ask the coordinator for all cached daily usage data.
        daily_data = self._coordinator.get_daily_usage()

        # If daily data is unavailable, fall back to the last known positive
        # cumulative total; otherwise show unknown.
        if not daily_data:
            return self._cumulative_total if self._cumulative_total > 0 else None

        # Start a fresh running total at zero.
        total = 0.0

        # Walk through each daily entry and add either the paid or free portion,
        # depending on how this sensor was configured.
        for entry in daily_data:
            if self._energy_kind == "paid":
                total += entry.get("paidUsageKwh", 0)
            else:
                total += entry.get("freeUsageKwh", 0)

        # Store the rounded total on the instance so it can be reused later.
        self._cumulative_total = round(total, 2)

        # Return the cumulative total Home Assistant should display and record.
        return self._cumulative_total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes.

        === WHAT THIS DOES ===
        This property attaches metadata explaining what kind of energy this is
        and which contract it belongs to.
        """
        # Return a small metadata dictionary that helps identify the sensor.
        return {
            "energy_kind": self._energy_kind,
            "contract_id": self._contract_id,
            "last_reset": (
                self._last_reset.isoformat() if self._last_reset else None
            ),
        }

    async def async_update(self) -> None:
        """Update the sensor state.

        === WHAT THIS DOES ===
        Ask the shared coordinator to refresh stale usage data if needed.
        """
        # Delegate refresh responsibility to the coordinator.
        await self._coordinator.async_update_if_stale()


# ============================================================================
# DAILY ENERGY SENSOR
# ============================================================================
class DailyEnergySensor(SensorEntity):
    """Sensor for daily energy consumption.

    === WHAT THIS DOES ===
    This sensor shows today's total energy usage and conceptually resets when a
    new day begins.

    === FOR NON-CODERS ===
    This behaves like a "today so far" energy counter.
    """

    # Tell Home Assistant this entity measures energy.
    _attr_device_class = SensorDeviceClass.ENERGY

    # Mark the value as a total that increases during the day.
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    # Use Home Assistant's standard kilowatt-hour unit.
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

        === WHAT THIS DOES ===
        This constructor prepares a "today" energy sensor for either paid or
        free energy.
        """
        # Store the integration context and shared data source.
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._energy_kind = energy_kind

        # Choose a shorter label fragment based on the configured energy kind.
        kind_label = "Paid" if energy_kind == "paid" else "Free"

        # Define the entity's stable unique ID and display settings.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_daily_energy_{energy_kind}"
        self._attr_name = f"{entity_name} Daily {kind_label} Energy"
        self._attr_icon = "mdi:calendar-today"

        # Remember which date this sensor last considered "today" so resets can
        # be represented consistently.
        self._last_date: date | None = None

    @property
    def state(self) -> float | None:
        """Return today's energy consumption.

        === WHAT THIS DOES ===
        This property sums the hourly usage entries that belong to today.
        """
        # Get today's calendar date.
        today = date.today()

        # If the stored date no longer matches today, update it so metadata and
        # reset calculations track the new day.
        if self._last_date != today:
            self._last_date = today

        # Fetch only the hourly entries for today.
        hourly_data = self._coordinator.get_hourly_usage_for_date(today)

        # If there is no hourly data yet, return 0.0 to represent no recorded
        # usage for today so far.
        if not hourly_data:
            return 0.0

        # Start the running total for today's energy at zero.
        total = 0.0

        # Add either paid or free usage from each hourly entry.
        for entry in hourly_data:
            if self._energy_kind == "paid":
                total += entry.get("paidUsageKwh", 0)
            else:
                total += entry.get("freeUsageKwh", 0)

        # Return a rounded total for a cleaner dashboard display.
        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes.

        === WHAT THIS DOES ===
        This property exposes metadata describing the energy kind and date.
        """
        # Return metadata that helps identify what this daily value represents.
        return {
            "energy_kind": self._energy_kind,
            "date": self._last_date.isoformat() if self._last_date else None,
        }

    @property
    def last_reset(self) -> datetime | None:
        """Return the last reset time (midnight today).

        === WHAT THIS DOES ===
        This property reports midnight of the currently tracked day so Home
        Assistant can understand the daily reset boundary.
        """
        # If we know which date is being tracked, combine it with midnight time
        # and mark it as UTC for a timezone-aware reset timestamp.
        if self._last_date:
            return datetime.combine(
                self._last_date,
                datetime.min.time(),
                tzinfo=timezone.utc
            )

        # Without a known date, there is no reset timestamp to report.
        return None

    async def async_update(self) -> None:
        """Update the sensor state.

        === WHAT THIS DOES ===
        Ask the coordinator to refresh stale usage data when needed.
        """
        # Delegate refresh work to the shared coordinator.
        await self._coordinator.async_update_if_stale()


# ============================================================================
# MONTHLY ENERGY SENSOR
# ============================================================================
class MonthlyEnergySensor(SensorEntity):
    """Sensor for monthly energy consumption.

    === WHAT THIS DOES ===
    This sensor shows the total energy usage for the current month and updates
    its internal reset boundary when the month changes.

    === FOR NON-CODERS ===
    This behaves like a "this month so far" energy counter.
    """

    # Tell Home Assistant this entity measures energy.
    _attr_device_class = SensorDeviceClass.ENERGY

    # Mark the value as a total that increases during the month.
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    # Use the standard kilowatt-hour unit expected by Energy Dashboard features.
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

        === WHAT THIS DOES ===
        This constructor prepares a current-month energy sensor for either paid
        or free energy.
        """
        # Store the integration context and coordinator reference.
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._energy_kind = energy_kind

        # Choose a shorter label fragment based on energy type.
        kind_label = "Paid" if energy_kind == "paid" else "Free"

        # Define the entity's unique ID and UI-facing label/icon.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_monthly_energy_{energy_kind}"
        self._attr_name = f"{entity_name} Monthly {kind_label} Energy"
        self._attr_icon = "mdi:calendar-month"

        # Store the currently tracked month as a (year, month) tuple so the
        # sensor can detect when a new month begins.
        self._last_month: tuple[int, int] | None = None

    @property
    def state(self) -> float | None:
        """Return this month's energy consumption.

        === WHAT THIS DOES ===
        This property sums the current month's daily records for either paid or
        free energy, depending on configuration.
        """
        # Determine today's date so we know which month to summarize.
        today = date.today()

        # Create a compact tuple that uniquely represents the current month.
        current_month = (today.year, today.month)

        # If the stored month is different, update it so reset metadata tracks
        # the new month.
        if self._last_month != current_month:
            self._last_month = current_month

        # Ask the daily manager for all daily usage records in the current month.
        daily_data = self._coordinator.daily_manager.get_usage_for_month(
            today.year, today.month
        )

        # If there is no current-month data, return 0.0 to represent no recorded
        # usage so far this month.
        if not daily_data:
            return 0.0

        # Start a running total at zero for this month's energy.
        total = 0.0

        # Add either paid or free energy from every day in the month.
        for entry in daily_data:
            if self._energy_kind == "paid":
                total += entry.get("paidUsageKwh", 0)
            else:
                total += entry.get("freeUsageKwh", 0)

        # Return a rounded monthly total.
        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes.

        === WHAT THIS DOES ===
        This property exposes metadata describing the energy kind and currently
        tracked year/month.
        """
        # Return a small metadata dictionary for dashboards and debugging.
        return {
            "energy_kind": self._energy_kind,
            "year": self._last_month[0] if self._last_month else None,
            "month": self._last_month[1] if self._last_month else None,
        }

    @property
    def last_reset(self) -> datetime | None:
        """Return the last reset time (first day of month).

        === WHAT THIS DOES ===
        This property reports the first moment of the tracked month so Home
        Assistant can understand the monthly reset boundary.
        """
        # If a month is being tracked, unpack the saved year/month and construct
        # a timezone-aware datetime for the first day of that month.
        if self._last_month:
            year, month = self._last_month
            return datetime(year, month, 1, tzinfo=timezone.utc)

        # Without a tracked month, there is no reset timestamp to report.
        return None

    async def async_update(self) -> None:
        """Update the sensor state.

        === WHAT THIS DOES ===
        Ask the coordinator to refresh stale usage data when necessary.
        """
        # Delegate refresh behavior to the shared coordinator.
        await self._coordinator.async_update_if_stale()
