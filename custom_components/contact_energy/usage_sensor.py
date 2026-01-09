"""Usage data sensor platform for Contact Energy integration.

This module creates sensor entities that expose cached usage data (hourly, daily, monthly)
from the Contact Energy API. The data is stored in sensor attributes for consumption
by custom cards like ApexCharts.

Copyright (c) 2025
License: MIT
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from calendar import monthrange

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
    def native_value(self) -> int:
        """Return the current state of the sensor.

        State shows total number of usage records cached.

        Returns:
            Total count of hourly, daily, and monthly records
        """
        if hasattr(self._cache, 'data') and self._cache.data:
            hourly_count = len(self._cache.data.get("hourly", {}))
            daily_count = len(self._cache.data.get("daily", {}))
            monthly_count = len(self._cache.data.get("monthly", {}))
            return hourly_count + daily_count + monthly_count
        
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return lean usage attributes sized for Home Assistant limits.

        We expose only recent data to stay under the 16KB attribute limit:
        - Hourly: Last 14 days (full cache window)
        - Daily: Last 90 days (reduced from 548 to fit limit)
        - Monthly: Last 18 months (full cache window)
        
        Empty/zero values are skipped to keep the payload compact.
        Full historical data remains available via statistics database.
        """
        attributes = {
            "hourly_paid_usage": {},  # paid kWh by ISO timestamp
            "hourly_free_usage": {},  # free kWh by ISO timestamp
            "daily_paid_usage": {},  # paid kWh by YYYY-MM-DD
            "daily_free_usage": {},  # free kWh by YYYY-MM-DD
            "monthly_paid_usage": {},  # paid kWh by YYYY-MM
            "monthly_free_usage": {},  # free kWh by YYYY-MM
        }

        # No cache loaded yet
        if not hasattr(self._cache, "data") or not self._cache.data:
            _LOGGER.debug("No cache data available for contract %s", self._contract_id)
            return attributes

        def _add_non_zero(target: Dict[str, float], key: str, value: Any) -> None:
            """Store only meaningful values to keep attributes small."""
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return

            if numeric == 0:
                return

            target[key] = round(numeric, 2)

        try:
            # Hourly: retain full cached window (14 days) but drop zeroes
            hourly_records = self._cache.data.get("hourly", {})
            for timestamp, record in hourly_records.items():
                _add_non_zero(attributes["hourly_paid_usage"], timestamp, record.get("paid"))
                _add_non_zero(attributes["hourly_free_usage"], timestamp, record.get("free"))

            # Daily: most recent 90 days only to stay under 16KB attribute limit
            daily_records = self._cache.data.get("daily", {})
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=90)).date()
            for date_key, record in daily_records.items():
                # Filter to recent 90 days only
                try:
                    record_date = datetime.strptime(date_key, "%Y-%m-%d").date()
                    if record_date < cutoff_date:
                        continue
                except (ValueError, TypeError):
                    continue
                    
                _add_non_zero(attributes["daily_paid_usage"], date_key, record.get("paid"))
                _add_non_zero(attributes["daily_free_usage"], date_key, record.get("free"))

            # Monthly: most recent 18 months (full cache window)
            monthly_records = self._cache.data.get("monthly", {})
            # Sort by date and take the most recent 18 months
            if monthly_records:
                # Sort month keys by date (YYYY-MM format sorts correctly)
                sorted_months = sorted(monthly_records.keys(), reverse=True)[:18]
                
                for month_key in sorted_months:
                    record = monthly_records[month_key]
                    _add_non_zero(attributes["monthly_paid_usage"], month_key, record.get("paid"))
                    _add_non_zero(attributes["monthly_free_usage"], month_key, record.get("free"))

            _LOGGER.debug(
                "Loaded usage data for contract %s: hourly=%d, daily=%d, monthly=%d",
                self._contract_id,
                len(attributes["hourly_paid_usage"]) + len(attributes["hourly_free_usage"]),
                len(attributes["daily_paid_usage"]) + len(attributes["daily_free_usage"]),
                len(attributes["monthly_paid_usage"]) + len(attributes["monthly_free_usage"]),
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
            # Create task to reload cache and update state after it completes
            loop.create_task(self._async_reload_cache_and_update())
        except Exception as e:
            _LOGGER.error(
                "Error reloading cache for contract %s: %s",
                self._contract_id, str(e)
            )

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
            # Create task to reload cache and update state after it completes
            loop.create_task(self._async_reload_cache_and_update())
        except Exception as e:
            _LOGGER.error(
                "Error reloading cache on usage update for contract %s: %s",
                self._contract_id, str(e)
            )
    
    async def _async_reload_cache_and_update(self) -> None:
        """Reload cache from disk and update Home Assistant state.
        
        Called when usage coordinator signals that new data is available.
        This ensures state is updated AFTER cache has been reloaded.
        """
        try:
            await self._async_reload_cache()
            # Now that cache is reloaded, update HA state with new attributes
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(
                "Error in cache reload and update for contract %s: %s",
                self._contract_id, str(e), exc_info=True
            )
