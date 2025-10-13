"""Contact Energy sensor platform."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.const import UnitOfEnergy

from .const import DOMAIN, CONF_ACCOUNT_ID, CONF_CONTRACT_ID, CONF_CONTRACT_ICP, CONF_USAGE_DAYS
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Contact Energy sensor entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    account_id = entry.data[CONF_ACCOUNT_ID]
    contract_id = entry.data[CONF_CONTRACT_ID]
    contract_icp = entry.data[CONF_CONTRACT_ICP]
    usage_days = entry.data.get(CONF_USAGE_DAYS, 30)

    # Create usage sensor for Energy Dashboard
    entities = [
        ContactEnergyUsageSensor(
            coordinator,
            account_id,
            contract_id,
            contract_icp,
            usage_days,
        )
    ]

    async_add_entities(entities, True)


class ContactEnergyUsageSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Contact Energy usage tracking with Energy Dashboard statistics."""

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        account_id: str,
        contract_id: str,
        contract_icp: str,
        usage_days: int,
    ) -> None:
        """Initialize the usage sensor."""
        super().__init__(coordinator)
        
        self._account_id = account_id
        self._contract_id = contract_id
        self._contract_icp = contract_icp
        self._usage_days = usage_days
        self._state = 0.0
        self._last_usage_update: Optional[datetime] = None
        self._download_task: Optional[asyncio.Task] = None

        # Entity attributes
        self._attr_name = f"Contact Energy Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:meter-electric"

    @property
    def native_value(self) -> float:
        """Return the current total usage."""
        return self._state

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
            "sw_version": "1.0",
        }

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        
        # Start initial data download
        _LOGGER.info("Starting initial usage data download for %s days", self._usage_days)
        self._download_task = self.hass.async_create_task(
            self._download_usage_data()
        )

    async def async_will_remove_from_hass(self) -> None:
        """Called when entity is about to be removed from Home Assistant."""
        if self._download_task and not self._download_task.done():
            self._download_task.cancel()
        await super().async_will_remove_from_hass()

    async def async_update(self) -> None:
        """Update usage data and statistics (called every 8 hours)."""
        now = datetime.now()
        
        # Only update if it's been 8+ hours since last update
        if (self._last_usage_update and 
            (now - self._last_usage_update) < timedelta(hours=8)):
            _LOGGER.debug("Skipping usage update, last update was recent")
            return

        _LOGGER.debug("Updating usage data - 8 hour interval update")
        
        try:
            await self._download_usage_data()
            self._last_usage_update = now
        except Exception as error:
            _LOGGER.error("Failed to update usage statistics: %s", error)

    async def _download_usage_data(self) -> None:
        """Download usage data and update Home Assistant statistics."""
        try:
            _LOGGER.info("Starting usage data download for %s days", self._usage_days)
            
            # Calculate date range
            today = datetime.now().date()
            start_date = today - timedelta(days=self._usage_days - 1)
            end_date = today
            
            # Initialize statistics lists
            kwh_statistics = []
            dollar_statistics = []
            free_kwh_statistics = []
            
            # Running totals for cumulative statistics
            kwh_running_sum = 0
            dollar_running_sum = 0
            free_kwh_running_sum = 0
            currency = 'NZD'
            
            # Download data day by day
            current_date = start_date
            while current_date <= end_date:
                try:
                    date_str = current_date.strftime("%Y-%m-%d")
                    _LOGGER.debug("Fetching usage data for %s", date_str)
                    
                    response = await self.coordinator.api.async_get_usage(
                        str(current_date.year),
                        str(current_date.month),
                        str(current_date.day),
                        self._account_id,
                        self._contract_id,
                    )

                    if response and isinstance(response, list):
                        for point in response:
                            if point.get('currency') and currency != point['currency']:
                                currency = point['currency']

                            # Safely convert values
                            value_float = self._safe_float(point.get("value"))
                            dollar_value_float = self._safe_float(point.get("dollarValue"))
                            offpeak_value_str = str(point.get("offpeakValue", "0.00"))

                            # If offpeak value is not '0.00', the energy is free
                            if offpeak_value_str == "0.00":
                                kwh_running_sum += value_float
                                dollar_running_sum += dollar_value_float
                            else:
                                free_kwh_running_sum += value_float

                            # Parse date safely
                            try:
                                date_obj = datetime.strptime(point["date"], "%Y-%m-%dT%H:%M:%S.%f%z")
                            except (ValueError, TypeError, KeyError):
                                date_obj = datetime.combine(current_date, datetime.min.time())

                            # Add to statistics (cumulative)
                            kwh_statistics.append(StatisticData(start=date_obj, sum=kwh_running_sum))
                            dollar_statistics.append(StatisticData(start=date_obj, sum=dollar_running_sum))
                            free_kwh_statistics.append(StatisticData(start=date_obj, sum=free_kwh_running_sum))

                    else:
                        _LOGGER.debug("No data available for %s", date_str)

                except Exception as error:
                    _LOGGER.warning("Failed to fetch data for %s: %s", current_date.strftime("%Y-%m-%d"), error)

                # Move to next date
                current_date += timedelta(days=1)
                
                # Small delay between requests to be nice to the API
                await asyncio.sleep(0.5)

            # Update Home Assistant statistics
            await self._add_statistics(kwh_statistics, dollar_statistics, free_kwh_statistics, currency)
            
            # Update sensor state to latest total
            self._state = kwh_running_sum
            
            _LOGGER.info("Usage data download completed. Total kWh: %.2f", kwh_running_sum)

        except Exception as error:
            _LOGGER.exception("Usage data download failed: %s", error)

    async def _add_statistics(
        self, 
        kwh_stats: list, 
        dollar_stats: list, 
        free_kwh_stats: list, 
        currency: str
    ) -> None:
        """Add statistics to Home Assistant."""
        if not kwh_stats:
            _LOGGER.debug("No statistics to add")
            return


        import re
        safe_icp = re.sub(r'[^a-z0-9_]', '_', self._contract_icp.lower())
        if re.match(r'^[0-9]', safe_icp):
            safe_icp = f"icp_{safe_icp}"

        # Main electricity consumption for Energy Dashboard
        kwh_stat_id = f"sensor.contact_energy_{safe_icp}_energy"
        kwh_metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=f"Contact Energy - Electricity ({self._contract_icp})",
            source=DOMAIN,
            statistic_id=kwh_stat_id,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )
        async_add_external_statistics(self.hass, kwh_metadata, kwh_stats)

        # Electricity cost
        if dollar_stats:
            dollar_stat_id = f"sensor.contact_energy_{safe_icp}_cost"
            dollar_metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"Contact Energy - Electricity Cost ({self._contract_icp})",
                source=DOMAIN,
                statistic_id=dollar_stat_id,
                unit_of_measurement=currency,
            )
            async_add_external_statistics(self.hass, dollar_metadata, dollar_stats)

        # Free electricity (if any)
        if free_kwh_stats and any(stat.sum > 0 for stat in free_kwh_stats):
            free_stat_id = f"sensor.contact_energy_{safe_icp}_free_energy"
            free_kwh_metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"Contact Energy - Free Electricity ({self._contract_icp})",
                source=DOMAIN,
                statistic_id=free_stat_id,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            )
            async_add_external_statistics(self.hass, free_kwh_metadata, free_kwh_stats)

        _LOGGER.debug("Added statistics to Home Assistant")

    @staticmethod
    def _safe_float(value: Any) -> float:
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0
