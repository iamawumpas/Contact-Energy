
"""
Contact Energy Chart Usage Sensors

Exposes hourly and daily usage data for ApexCharts, using only the Home Assistant statistics database.
No API calls are made from these sensors.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.const import CONF_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

# Configuration: customize these as needed
STAT_ID = "contact_energy:energy_chart"
SENSOR_PREFIX = "contact_energy_chart"

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up chart usage sensors from a config entry."""
    entities = [
        ContactEnergyChartHourlySensor(hass),
        ContactEnergyChartDailySensor(hass),
    ]
    async_add_entities(entities, True)

class ContactEnergyChartHourlySensor(SensorEntity):
    """Sensor exposing hourly usage data for ApexCharts."""
    def __init__(self, hass: HomeAssistant, stat_id: str = STAT_ID) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._attr_name = "Contact Energy Chart Hourly"
        self._attr_unique_id = f"{SENSOR_PREFIX}_hourly"
        self._attr_icon = "mdi:chart-bar"
        self._hourly_data: Dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Optionally, return the most recent hour's usage
        if self._hourly_data:
            latest = max(self._hourly_data.keys())
            return self._hourly_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "hourly_data": self._hourly_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def async_update(self) -> None:
        # Query last 30 days of hourly statistics from the database
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        stats = await self.hass.async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            [self._stat_id],
            "hour",
            None,
            {"sum"}
        )
        self._hourly_data = {}
        if self._stat_id in stats:
            for entry in stats[self._stat_id]:
                dt = entry.get("start")
                val = entry.get("sum")
                if dt and val is not None:
                    # Store as ISO string for ApexCharts
                    self._hourly_data[dt.isoformat()] = float(val)
        self._last_update = datetime.now()

class ContactEnergyChartDailySensor(SensorEntity):
    """Sensor exposing daily usage data for ApexCharts."""
    def __init__(self, hass: HomeAssistant, stat_id: str = STAT_ID) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._attr_name = "Contact Energy Chart Daily"
        self._attr_unique_id = f"{SENSOR_PREFIX}_daily"
        self._attr_icon = "mdi:calendar"
        self._daily_data: Dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Optionally, return the most recent day's usage
        if self._daily_data:
            latest = max(self._daily_data.keys())
            return self._daily_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "daily_data": self._daily_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def async_update(self) -> None:
        # Query last 90 days of daily statistics from the database
        end_time = datetime.now()
        start_time = end_time - timedelta(days=90)
        stats = await self.hass.async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            [self._stat_id],
            "day",
            None,
            {"sum"}
        )
        self._daily_data = {}
        if self._stat_id in stats:
            for entry in stats[self._stat_id]:
                dt = entry.get("start")
                val = entry.get("sum")
                if dt and val is not None:
                    # Store as ISO date string for ApexCharts
                    self._daily_data[dt.date().isoformat()] = float(val)
        self._last_update = datetime.now()
