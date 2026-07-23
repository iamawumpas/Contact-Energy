"""Usage sensor entities for Contact Energy integration.

=== WHAT THIS DOES ===
This module defines several Home Assistant sensors that expose electricity usage
information gathered by the Contact Energy usage coordinator.

The sensors in this file provide different views of the same underlying usage data:
- a "data dump" sensor with hourly, daily, and monthly attributes
- a sensor summarizing today's hourly usage
- a sensor summarizing this month's daily usage
- a sensor summarizing this year's monthly usage

These sensors are designed to make the stored usage information easy to use in
Home Assistant dashboards, graphs, and automations.

=== FOR NON-CODERS ===
Important words explained simply:
- Home Assistant: the smart-home system showing these values.
- sensor: a read-only dashboard item that reports information.
- entity: Home Assistant's name for any item it can track.
- state: the sensor's main headline value.
- attributes: extra supporting details attached to that sensor.

Think of these sensors like different report views over the same meter data:
- one view gives you a big data package for charts
- one view focuses on today
- one view focuses on this month
- one view focuses on this year

Version: 2.0.0
"""
# This import allows modern type-hint syntax to work cleanly across Python versions.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging lets the module record diagnostic messages if needed.
import logging

# date helps us work with calendar days, datetime handles timestamps, and
# timezone provides timezone-aware values when needed.
from datetime import date, datetime, timezone

# Any is used for dictionaries that may contain mixed kinds of values.
from typing import Any

# SensorEntity is the base Home Assistant class for read-only sensor entities.
from homeassistant.components.sensor import SensorEntity

# HomeAssistant represents the running app instance, and callback marks small
# functions that Home Assistant may call efficiently inside its event loop.
from homeassistant.core import HomeAssistant, callback

# CoordinatorEntity is imported to match Home Assistant coordinator patterns.
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# UsageCoordinatorV2 is this integration's shared manager for usage data.
from ..coordinators.usage_coordinator_v2 import UsageCoordinatorV2

# DOMAIN is the integration's unique identifier for building stable IDs.
from ..const import DOMAIN

# ============================================================================
# LOGGER SETUP
# ============================================================================
# Create a file-specific logger so troubleshooting messages can be traced back here.
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================
# This value documents the intended maximum payload size for attributes so the
# integration avoids putting overly large blobs into Home Assistant's database.
ATTRIBUTE_SIZE_BUDGET = 15000


# ============================================================================
# USAGE DATA SENSOR
# ============================================================================
class UsageDataSensor(SensorEntity):
    """Sensor that exposes cached usage data as attributes.

    === WHAT THIS DOES ===
    This sensor acts as a container for usage history. Its main state is the
    most recent update timestamp, while its attributes hold formatted hourly,
    daily, and monthly usage data.

    === FOR NON-CODERS ===
    This is less like a single number on a screen and more like a small report
    packet attached to one sensor. Dashboards can read the packet to build charts.
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

        === WHAT THIS DOES ===
        This constructor stores the Home Assistant instance, usage coordinator,
        and identity details needed for a reusable "usage report" sensor.
        """
        # Store the Home Assistant application instance for future integration use.
        self.hass = hass

        # Store the coordinator that owns the cached usage data.
        self._coordinator = coordinator

        # Store identifiers used to keep the entity unique and readable.
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._contract_id = contract_id

        # Build the unique ID Home Assistant uses to remember this exact sensor.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_usage"

        # Set the friendly name visible in dashboards and entity lists.
        self._attr_name = f"{entity_name} Usage Data"

        # Choose an icon that visually suggests electricity/usage information.
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def state(self) -> str | None:
        """Return the state (last update timestamp).

        === WHAT THIS DOES ===
        This property reports when the freshest usage data was last updated.

        === FOR NON-CODERS ===
        The attributes hold the big report. The state simply answers,
        "How recent is this report?"
        """
        # Read the last update timestamp for each cached dataset.
        last_hourly = self._coordinator._last_hourly_update
        last_daily = self._coordinator._last_daily_update
        last_monthly = self._coordinator._last_monthly_update

        # Build a list containing only timestamps that actually exist.
        timestamps = [t for t in [last_hourly, last_daily, last_monthly] if t]

        # If at least one timestamp exists, return the most recent one.
        if timestamps:
            most_recent = max(timestamps)
            return most_recent.isoformat()

        # If nothing has ever been updated yet, the state is unknown.
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with cached usage data.

        === WHAT THIS DOES ===
        This property packages usage history into structured attributes for use
        by dashboards and other Home Assistant features.

        === FOR NON-CODERS ===
        If the state is the headline, attributes are the detail page underneath.
        They hold the actual chart data.
        """
        # Start with an empty attribute dictionary that we will fill step by step.
        attributes = {}

        # Ask the coordinator for the cached hourly usage history.
        hourly_data = self._coordinator.get_hourly_usage()

        # Only attach hourly data if any exists.
        if hourly_data:
            # Keep only the first 168 entries (7 days of hours) to avoid making
            # the entity attributes too large for Home Assistant's recorder.
            attributes["hourly_usage"] = self._format_hourly_data(hourly_data[:168])

            # Also report how many hourly records exist in total, even if we only
            # expose a shortened list in the attributes.
            attributes["hourly_data_count"] = len(hourly_data)

        # Ask the coordinator for the cached daily usage history.
        daily_data = self._coordinator.get_daily_usage()

        # Only attach daily data when available.
        if daily_data:
            # Limit the exposed daily list to 90 records to control attribute size.
            attributes["daily_usage"] = self._format_daily_data(daily_data[:90])

            # Report the full count so users know whether data was trimmed.
            attributes["daily_data_count"] = len(daily_data)

        # Ask the coordinator for the cached monthly usage history.
        monthly_data = self._coordinator.get_monthly_usage()

        # Only attach monthly data when available.
        if monthly_data:
            # Limit the exposed monthly list to 24 records (roughly 2 years).
            attributes["monthly_usage"] = self._format_monthly_data(monthly_data[:24])

            # Report how many monthly records exist in the underlying cache.
            attributes["monthly_data_count"] = len(monthly_data)

        # Attach contract metadata so dashboards know which contract produced the data.
        attributes["contract_id"] = self._contract_id

        # Store the last hourly refresh time as plain text if it exists.
        attributes["last_hourly_update"] = (
            self._coordinator._last_hourly_update.isoformat()
            if self._coordinator._last_hourly_update
            else None
        )

        # Store the last daily refresh time as plain text if it exists.
        attributes["last_daily_update"] = (
            self._coordinator._last_daily_update.isoformat()
            if self._coordinator._last_daily_update
            else None
        )

        # Store the last monthly refresh time as plain text if it exists.
        attributes["last_monthly_update"] = (
            self._coordinator._last_monthly_update.isoformat()
            if self._coordinator._last_monthly_update
            else None
        )

        # Return the finished attribute package to Home Assistant.
        return attributes

    def _format_hourly_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format hourly usage data for attributes.

        === WHAT THIS DOES ===
        This helper converts raw hourly API entries into a cleaner structure for
        Home Assistant attributes and dashboard charting.

        === FOR NON-CODERS ===
        Raw API data can be messy or inconsistent. This method repacks each row
        into a simpler shape with clearer field names.
        """
        # Start an empty list that will hold one cleaned dictionary per hour.
        formatted = []

        # Loop through every raw hourly entry we want to expose.
        for entry in data:
            # Build a cleaner dictionary for this one hour and append it to the list.
            formatted.append({
                # Copy the API timestamp into a clearer attribute name.
                "timestamp": entry.get("startTime"),

                # Copy the paid-usage energy amount, defaulting to 0 if missing.
                "paid_kwh": entry.get("paidUsageKwh", 0),

                # Copy the free-usage energy amount, defaulting to 0 if missing.
                "free_kwh": entry.get("freeUsageKwh", 0),

                # Combine paid and free energy so dashboards do not need to do the math.
                "total_kwh": (
                    entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                ),

                # Copy the cost figure for that hour when provided by the API.
                "cost": entry.get("cost", 0),
            })

        # Return the fully formatted hourly list.
        return formatted

    def _format_daily_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format daily usage data for attributes.

        === WHAT THIS DOES ===
        This helper repackages raw daily usage rows into chart-friendly dictionaries.
        """
        # Create an output list for cleaned daily records.
        formatted = []

        # Process each raw daily usage entry one at a time.
        for entry in data:
            # Append a cleaned dictionary with easier-to-understand field names.
            formatted.append({
                "date": entry.get("startTime"),
                "paid_kwh": entry.get("paidUsageKwh", 0),
                "free_kwh": entry.get("freeUsageKwh", 0),
                "total_kwh": (
                    entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                ),
                "cost": entry.get("cost", 0),
            })

        # Return the cleaned daily list.
        return formatted

    def _format_monthly_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format monthly usage data for attributes.

        === WHAT THIS DOES ===
        This helper repackages raw monthly usage rows into a simpler and more
        predictable structure for attributes.
        """
        # Create an output list for cleaned monthly records.
        formatted = []

        # Loop through every raw monthly entry provided.
        for entry in data:
            # Append a cleaned monthly record with consistent field names.
            formatted.append({
                "month": entry.get("startTime"),
                "paid_kwh": entry.get("paidUsageKwh", 0),
                "free_kwh": entry.get("freeUsageKwh", 0),
                "total_kwh": (
                    entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                ),
                "cost": entry.get("cost", 0),
            })

        # Return the cleaned monthly list.
        return formatted

    async def async_update(self) -> None:
        """Update the sensor state.

        === WHAT THIS DOES ===
        This tells the coordinator to refresh usage data if the cached data is
        considered stale.

        === FOR NON-CODERS ===
        The sensor does not fetch data directly. It asks the shared coordinator,
        "Please refresh if needed," so all sensors can reuse the same data.
        """
        # Delegate refresh responsibility to the shared coordinator.
        await self._coordinator.async_update_if_stale()


# ============================================================================
# HOURLY USAGE SENSOR
# ============================================================================
class HourlyUsageSensor(SensorEntity):
    """Sensor for hourly usage data.

    === WHAT THIS DOES ===
    This sensor reports today's total electricity usage as its main state and
    exposes today's hour-by-hour breakdown as attributes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
    ):
        """Initialize the hourly usage sensor.

        === WHAT THIS DOES ===
        This constructor prepares a sensor focused specifically on today's hourly data.
        """
        # Store references and identifiers needed by this sensor instance.
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name

        # Define the unique ID, display name, icon, and measurement unit.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_hourly_usage"
        self._attr_name = f"{entity_name} Hourly Usage"
        self._attr_icon = "mdi:chart-line"
        self._attr_unit_of_measurement = "kWh"

    @property
    def state(self) -> float | None:
        """Return the state (today's total usage).

        === WHAT THIS DOES ===
        This property adds up today's hourly usage entries and returns the total kWh.
        """
        # Determine today's calendar date.
        today = date.today()

        # Ask the coordinator for hourly usage entries that belong to today.
        hourly_data = self._coordinator.get_hourly_usage_for_date(today)

        # If there is no hourly data for today yet, show the state as unknown.
        if not hourly_data:
            return None

        # Start a running total at zero.
        total = 0.0

        # Add both paid and free energy from each hourly entry.
        for entry in hourly_data:
            total += entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)

        # Round to two decimal places for a cleaner display.
        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with today's hourly data.

        === WHAT THIS DOES ===
        This property exposes the hour-by-hour breakdown that supports graphs or
        detailed inspection for the current day.
        """
        # Work out today's date so we can filter the correct dataset.
        today = date.today()

        # Fetch only the hourly entries for today.
        hourly_data = self._coordinator.get_hourly_usage_for_date(today)

        # If there is nothing to expose, return an empty attribute dictionary.
        if not hourly_data:
            return {}

        # Return a compact breakdown list plus the date it belongs to.
        return {
            "hourly_data": [
                {
                    # Copy the start time for this hour block.
                    "hour": entry.get("startTime"),

                    # Copy paid and free usage separately.
                    "paid_kwh": entry.get("paidUsageKwh", 0),
                    "free_kwh": entry.get("freeUsageKwh", 0),

                    # Provide a combined total so the consumer does not need to sum it.
                    "total_kwh": (
                        entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)
                    ),
                }
                for entry in hourly_data
            ],
            "date": today.isoformat(),
        }

    async def async_update(self) -> None:
        """Update the sensor state.

        === WHAT THIS DOES ===
        Ask the shared usage coordinator to refresh stale data when necessary.
        """
        # Delegate data-refresh logic to the coordinator.
        await self._coordinator.async_update_if_stale()


# ============================================================================
# DAILY USAGE SENSOR
# ============================================================================
class DailyUsageSensor(SensorEntity):
    """Sensor for daily usage data.

    === WHAT THIS DOES ===
    This sensor reports the current month's total energy usage as its state and
    exposes a per-day breakdown for the same month in its attributes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
    ):
        """Initialize the daily usage sensor.

        === WHAT THIS DOES ===
        This constructor sets up a month-focused daily-usage summary sensor.
        """
        # Store references used later by the sensor.
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name

        # Define the sensor's persistent identity and UI presentation.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_daily_usage"
        self._attr_name = f"{entity_name} Daily Usage"
        self._attr_icon = "mdi:calendar"
        self._attr_unit_of_measurement = "kWh"

    @property
    def state(self) -> float | None:
        """Return the state (current month's total usage).

        === WHAT THIS DOES ===
        Sum the current month's daily records and return the total kWh.
        """
        # Identify the current date so we know which month to query.
        today = date.today()

        # Ask the daily manager for records belonging to the current year and month.
        daily_data = self._coordinator.daily_manager.get_usage_for_month(
            today.year, today.month
        )

        # If there are no daily records for the month yet, show unknown.
        if not daily_data:
            return None

        # Start a running total at zero.
        total = 0.0

        # Add paid and free usage from each day together.
        for entry in daily_data:
            total += entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)

        # Round for a clean dashboard-friendly value.
        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with current month's daily data.

        === WHAT THIS DOES ===
        Provide a day-by-day breakdown for the current month.
        """
        # Capture today's date so we can identify the current month.
        today = date.today()

        # Fetch daily usage rows for the current month.
        daily_data = self._coordinator.daily_manager.get_usage_for_month(
            today.year, today.month
        )

        # If no data exists, expose an empty attribute set.
        if not daily_data:
            return {}

        # Return the daily breakdown plus a simple year-month label.
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
        """Update the sensor state.

        === WHAT THIS DOES ===
        Ask the usage coordinator to refresh shared data if it is stale.
        """
        # Delegate refresh work to the coordinator.
        await self._coordinator.async_update_if_stale()


# ============================================================================
# MONTHLY USAGE SENSOR
# ============================================================================
class MonthlyUsageSensor(SensorEntity):
    """Sensor for monthly usage data.

    === WHAT THIS DOES ===
    This sensor reports the current year's total usage as its main state and
    exposes a month-by-month breakdown in its attributes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: UsageCoordinatorV2,
        entry_id: str,
        entity_name: str,
    ):
        """Initialize the monthly usage sensor.

        === WHAT THIS DOES ===
        This constructor sets up a year-focused monthly-usage summary sensor.
        """
        # Store references used by this entity.
        self.hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._entity_name = entity_name

        # Define the entity's identity and how it should appear in the UI.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_monthly_usage"
        self._attr_name = f"{entity_name} Monthly Usage"
        self._attr_icon = "mdi:calendar-month"
        self._attr_unit_of_measurement = "kWh"

    @property
    def state(self) -> float | None:
        """Return the state (current year's total usage).

        === WHAT THIS DOES ===
        Sum the current year's monthly usage records and return the total kWh.
        """
        # Determine the current date so we know which year to summarize.
        today = date.today()

        # Ask the monthly manager for all monthly records belonging to this year.
        monthly_data = self._coordinator.monthly_manager.get_usage_for_year(today.year)

        # If no records exist, the state should be unknown.
        if not monthly_data:
            return None

        # Start the yearly running total at zero.
        total = 0.0

        # Add paid and free usage for every month together.
        for entry in monthly_data:
            total += entry.get("paidUsageKwh", 0) + entry.get("freeUsageKwh", 0)

        # Return a rounded total for cleaner display.
        return round(total, 2)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes with current year's monthly data.

        === WHAT THIS DOES ===
        Provide a month-by-month usage breakdown for the current year.
        """
        # Identify the current year.
        today = date.today()

        # Fetch monthly records for the current year.
        monthly_data = self._coordinator.monthly_manager.get_usage_for_year(today.year)

        # If there is no data, expose no extra attributes.
        if not monthly_data:
            return {}

        # Return the breakdown list plus the year it belongs to.
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
        """Update the sensor state.

        === WHAT THIS DOES ===
        Ask the shared usage coordinator to refresh stale data.
        """
        # Delegate shared refresh logic to the coordinator.
        await self._coordinator.async_update_if_stale()
