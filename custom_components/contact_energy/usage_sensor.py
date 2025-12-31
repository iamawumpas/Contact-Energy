"""Usage data sensor platform for Contact Energy integration.

This module creates sensor entities that expose cached usage data (hourly, daily, monthly)
from the Contact Energy API. The data is stored in sensor attributes for consumption
by custom cards like ApexCharts.

Copyright (c) 2025
License: MIT
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ContactEnergyCoordinator
from .usage_cache import UsageCache

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Contact Energy usage sensor entities.

    Creates a single usage sensor per contract that exposes cached usage data
    (hourly, daily, monthly) as sensor attributes. This data can be consumed
    by custom dashboard cards like ApexCharts.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry for this integration.
        async_add_entities: Callback to add entities.
    """
    # Get coordinator from hass data
    coordinator: ContactEnergyCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    # Get account information from config entry
    account_nickname = config_entry.data.get("account_nickname", "Unknown")
    icp = config_entry.data.get("icp", "Unknown")
    contract_id = config_entry.data.get("contract_id", "unknown")

    # Create friendly entity name: Account Nickname (ICP)
    entity_name = f"{account_nickname} ({icp})"

    _LOGGER.info(
        "Setting up usage sensor for contract %s (%s)",
        contract_id, entity_name
    )

    # Create usage sensor entity
    entities = [
        ContactEnergyUsageSensor(
            coordinator,
            config_entry,
            entity_name,
            contract_id
        )
    ]

    async_add_entities(entities, True)


class ContactEnergyUsageSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity that exposes cached usage data.

    This sensor's state shows the last sync timestamp, and attributes contain
    all cached usage data (hourly, daily, monthly) ready for graphing.

    Attributes:
        coordinator: Data coordinator that manages updates
        config_entry: Configuration entry for this integration
        _entity_name: Base name for the entity (e.g., "Home (123456)")
        _contract_id: Contact Energy contract ID
        _cache: UsageCache instance for loading cached data
        _attr_name: Full sensor name
        _attr_unique_id: Unique identifier for this sensor
        _attr_icon: MDI icon for the sensor
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        contract_id: str,
    ) -> None:
        """Initialize the usage sensor.

        Args:
            coordinator: Data coordinator managing updates
            config_entry: Config entry for this integration
            entity_name: Base entity name (e.g., "Home (123456)")
            contract_id: Contact Energy contract ID
        """
        super().__init__(coordinator)

        self.config_entry = config_entry
        self._entity_name = entity_name
        self._contract_id = contract_id

        # Initialize cache loader (uses same cache as coordinator)
        self._cache = UsageCache(contract_id)

        # Set sensor properties
        # Sensor name: "sensor.contact_energy_usage_home_123456"
        friendly_name = f"{entity_name} Usage".replace(" ", "_").replace("(", "").replace(")", "").lower()
        self._attr_name = f"{entity_name} Usage"
        self._attr_unique_id = f"contact_energy_usage_{contract_id}"
        self._attr_icon = "mdi:lightning-bolt"

        _LOGGER.debug(
            "Initialized usage sensor: name=%s, unique_id=%s, contract=%s",
            self._attr_name, self._attr_unique_id, contract_id
        )

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information for grouping sensors.

        Groups all sensors (account + usage) under the same device based on contract ID.

        Returns:
            Device info dictionary
        """
        return {
            "identifiers": {(DOMAIN, self._contract_id)},
            "name": f"Contact Energy {self._entity_name}",
            "manufacturer": "Contact Energy",
            "model": "Energy Account",
        }

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the sensor.

        State shows when usage data was last synchronized from the API.

        Returns:
            ISO timestamp of last sync, or "No Data" if never synced
        """
        # State = last sync timestamp from cache metadata
        if hasattr(self._cache, 'data') and self._cache.data:
            metadata = self._cache.data.get("metadata", {})
            last_synced = metadata.get("last_synced")
            if last_synced:
                return last_synced
        
        return "No Data"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return sensor attributes containing all usage data.

        Attributes include:
            - hourly_usage: List of hourly records (last 9 days)
            - daily_usage: List of daily records (last 35 days)
            - monthly_usage: List of monthly records (last 18 months)
            - hourly_count: Number of hourly records
            - daily_count: Number of daily records
            - monthly_count: Number of monthly records
            - last_updated: Cache last update timestamp
            - version: Cache format version

        Returns:
            Dictionary of sensor attributes
        """
        attributes = {
            "last_updated": None,
            "version": "1.5.0",
            "hourly_count": 0,
            "daily_count": 0,
            "monthly_count": 0,
            "hourly_usage": [],
            "daily_usage": [],
            "monthly_usage": [],
        }

        # Check if cache has data loaded
        if not hasattr(self._cache, 'data') or not self._cache.data:
            _LOGGER.debug("No cache data available for contract %s", self._contract_id)
            return attributes

        try:
            # Extract metadata
            metadata = self._cache.data.get("metadata", {})
            attributes["last_updated"] = metadata.get("last_synced")

            # Extract hourly usage data
            # Convert from dict keyed by timestamp to list sorted by time
            hourly_dict = self._cache.data.get("hourly", {})
            hourly_list = []
            for timestamp, record in sorted(hourly_dict.items()):
                hourly_list.append({
                    "time": record.get("timestamp", timestamp),
                    "total": record.get("total", 0.0),
                    "paid": record.get("paid", 0.0),
                    "free": record.get("free", 0.0),
                    "cost": record.get("cost", 0.0),
                })
            attributes["hourly_usage"] = hourly_list
            attributes["hourly_count"] = len(hourly_list)

            # Extract daily usage data
            daily_dict = self._cache.data.get("daily", {})
            daily_list = []
            for date_key, record in sorted(daily_dict.items()):
                daily_list.append({
                    "date": date_key,
                    "time": record.get("timestamp", date_key),
                    "total": record.get("total", 0.0),
                    "paid": record.get("paid", 0.0),
                    "free": record.get("free", 0.0),
                    "cost": record.get("cost", 0.0),
                })
            attributes["daily_usage"] = daily_list
            attributes["daily_count"] = len(daily_list)

            # Extract monthly usage data
            monthly_dict = self._cache.data.get("monthly", {})
            monthly_list = []
            for month_key, record in sorted(monthly_dict.items()):
                monthly_list.append({
                    "month": month_key,
                    "time": record.get("timestamp", month_key),
                    "total": record.get("total", 0.0),
                    "paid": record.get("paid", 0.0),
                    "free": record.get("free", 0.0),
                    "cost": record.get("cost", 0.0),
                })
            attributes["monthly_usage"] = monthly_list
            attributes["monthly_count"] = len(monthly_list)

            _LOGGER.debug(
                "Loaded usage data for contract %s: hourly=%d, daily=%d, monthly=%d",
                self._contract_id,
                attributes["hourly_count"],
                attributes["daily_count"],
                attributes["monthly_count"]
            )

        except Exception as e:
            _LOGGER.error(
                "Error loading usage data attributes for contract %s: %s",
                self._contract_id, str(e), exc_info=True
            )

        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        Called when coordinator refreshes data. Reloads cache and updates
        sensor state and attributes.
        """
        _LOGGER.debug("Coordinator update received for usage sensor (contract %s)", self._contract_id)
        
        # Reload cache from disk to get latest synced data
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(self._async_reload_cache())
        except Exception as e:
            _LOGGER.error(
                "Error reloading cache for contract %s: %s",
                self._contract_id, str(e)
            )

        # Notify HA that sensor state/attributes have changed
        self.async_write_ha_state()

    async def _async_reload_cache(self) -> None:
        """Reload cache data from disk asynchronously.

        Called after coordinator updates to refresh sensor with latest cached data.
        """
        try:
            _LOGGER.debug("Reloading cache for usage sensor (contract %s)", self._contract_id)
            loaded = await self._cache.load()
            if loaded:
                _LOGGER.debug("Cache reloaded successfully for contract %s", self._contract_id)
            else:
                _LOGGER.debug("Cache load returned False for contract %s (may be first run)", self._contract_id)
        except Exception as e:
            _LOGGER.error(
                "Failed to reload cache for contract %s: %s",
                self._contract_id, str(e), exc_info=True
            )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to Home Assistant.

        Load initial cache data when sensor is first added.
        """
        await super().async_added_to_hass()

        # Listen for usage refresh signals from the usage coordinator
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_usage_updated_{self._contract_id}",
            self._handle_usage_update,
        )

        _LOGGER.debug("Usage sensor added to HA for contract %s", self._contract_id)
        
        # Load initial cache data
        try:
            await self._cache.load()
            _LOGGER.debug("Initial cache loaded for usage sensor (contract %s)", self._contract_id)
        except Exception as e:
            _LOGGER.warning(
                "Could not load initial cache for contract %s: %s",
                self._contract_id, str(e)
            )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up dispatcher subscription on removal."""
        if hasattr(self, "_unsub_dispatcher") and self._unsub_dispatcher:
            self._unsub_dispatcher()
        await super().async_will_remove_from_hass()

    @callback
    def _handle_usage_update(self) -> None:
        """Handle usage data refreshed by the usage coordinator."""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(self._async_reload_cache())
        except Exception as e:
            _LOGGER.error(
                "Error reloading cache on usage update for contract %s: %s",
                self._contract_id, str(e)
            )
        self.async_write_ha_state()
