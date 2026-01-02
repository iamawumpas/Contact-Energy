"""Usage data sensor platform for Contact Energy integration.

This module creates sensor entities that expose cached usage data (hourly, daily, monthly)
from the Contact Energy API. The data is stored in sensor attributes for consumption
by custom cards like ApexCharts.

Copyright (c) 2025
License: MIT
"""

import logging
from datetime import datetime, timedelta
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
        """Return sensor attributes containing usage data optimized for Home Assistant.

        Attributes include:
            - summary: Comprehensive statistics including daily/monthly/yearly/seasonal averages and totals
            - hourly_total_usage: Dict of TOTAL usage keyed by ISO datetime
            - hourly_paid_usage: Dict of paid usage (peak + off-peak) keyed by ISO datetime
            - hourly_free_usage: Dict of free usage keyed by ISO datetime (mutually exclusive with paid)
            - hourly_peak_usage: Dict of peak usage keyed by ISO datetime
            - hourly_offpeak_usage: Dict of off-peak usage keyed by ISO datetime
            - daily_total_usage: Dict of TOTAL usage keyed by date string
            - daily_paid_usage: Dict of paid usage keyed by date string
            - daily_free_usage: Dict of free usage keyed by date string (mutually exclusive with paid)
            - daily_peak_usage: Dict of peak usage keyed by date string
            - daily_offpeak_usage: Dict of off-peak usage keyed by date string
            - monthly_total_usage: Dict of TOTAL usage keyed by month string
            - monthly_paid_usage: Dict of paid usage keyed by month string
            - monthly_free_usage: Dict of free usage keyed by month string (mutually exclusive with paid)
            - monthly_peak_usage: Dict of peak usage keyed by month string
            - monthly_offpeak_usage: Dict of off-peak usage keyed by month string
            - hourly_count/daily_count/monthly_count: Total records in cache
            - last_updated: Cache last sync timestamp
            - version: Cache format version

        Note: paid_usage and free_usage are mutually exclusive - when paid > 0, free = 0 and vice versa.

        Returns:
            Dictionary of sensor attributes (optimized for Home Assistant database)
        """
        # Initialize attributes with empty data structures and summaries
        attributes = {
            "last_updated": None,
            "version": "1.6.17",
            "summary": {
                # Daily totals (all cached daily data)
                "daily_total_kwh": 0.0,
                "daily_paid_kwh": 0.0,
                "daily_peak_kwh": 0.0,
                "daily_offpeak_kwh": 0.0,
                "daily_free_kwh": 0.0,
                "daily_cost_nzd": 0.0,
                "daily_count": 0,
                # Daily averages (kWh per hour)
                "daily_average_usage": 0.0,
                "daily_average_paid_usage": 0.0,
                "daily_average_free_usage": 0.0,
                "daily_average_offpeak_usage": 0.0,
                # Monthly totals (all cached monthly data)
                "monthly_total_kwh": 0.0,
                "monthly_paid_kwh": 0.0,
                "monthly_peak_kwh": 0.0,
                "monthly_offpeak_kwh": 0.0,
                "monthly_free_kwh": 0.0,
                "monthly_cost_nzd": 0.0,
                "monthly_count": 0,
                # Monthly averages (kWh per day)
                "monthly_average_usage": 0.0,
                "monthly_average_paid_usage": 0.0,
                "monthly_average_free_usage": 0.0,
                "monthly_average_offpeak_usage": 0.0,
                # Yearly statistics (calendar year)
                "year_calendar_total_kwh": 0.0,
                "year_calendar_paid_kwh": 0.0,
                "year_calendar_peak_kwh": 0.0,
                "year_calendar_offpeak_kwh": 0.0,
                "year_calendar_free_kwh": 0.0,
                "year_calendar_cost_nzd": 0.0,
                "year_calendar_average_per_day": 0.0,
                # Yearly statistics (rolling 365 days)
                "year_rolling_total_kwh": 0.0,
                "year_rolling_paid_kwh": 0.0,
                "year_rolling_peak_kwh": 0.0,
                "year_rolling_offpeak_kwh": 0.0,
                "year_rolling_free_kwh": 0.0,
                "year_rolling_cost_nzd": 0.0,
                "year_rolling_average_per_day": 0.0,
                # Seasonal averages (NZ seasons, kWh per day)
                "season_spring_avg_per_day": 0.0,  # Sep-Nov
                "season_summer_avg_per_day": 0.0,  # Dec-Feb
                "season_autumn_avg_per_day": 0.0,  # Mar-Jun
                "season_winter_avg_per_day": 0.0,  # Jul-Aug
            },
            "hourly_count": 0,
            "daily_count": 0,
            "monthly_count": 0,
            # Hourly usage dicts keyed by ISO datetime for ApexCharts
            "hourly_total_usage": {},  # TOTAL usage (paid + free)
            "hourly_paid_usage": {},  # paid usage (peak + off-peak) - mutually exclusive with free
            "hourly_free_usage": {},  # free/unpaid usage - mutually exclusive with paid
            "hourly_peak_usage": {},  # peak rate usage
            "hourly_offpeak_usage": {},  # off-peak rate usage
            # Daily usage dicts keyed by date string for ApexCharts
            "daily_total_usage": {},  # TOTAL usage (paid + free)
            "daily_paid_usage": {},  # paid usage (peak + off-peak) - mutually exclusive with free
            "daily_free_usage": {},  # free/unpaid usage - mutually exclusive with paid
            "daily_peak_usage": {},  # peak rate usage
            "daily_offpeak_usage": {},  # off-peak rate usage
            # Monthly usage dicts keyed by month string for ApexCharts
            "monthly_total_usage": {},  # TOTAL usage (paid + free)
            "monthly_paid_usage": {},  # paid usage (peak + off-peak) - mutually exclusive with free
            "monthly_free_usage": {},  # free/unpaid usage - mutually exclusive with paid
            "monthly_peak_usage": {},  # peak rate usage
            "monthly_offpeak_usage": {},  # off-peak rate usage
        }

        # Check if cache has data loaded
        if not hasattr(self._cache, 'data') or not self._cache.data:
            _LOGGER.debug("No cache data available for contract %s", self._contract_id)
            return attributes

        try:
            # Extract metadata
            metadata = self._cache.data.get("metadata", {})
            attributes["last_updated"] = metadata.get("last_synced")

            # Extract hourly usage data - populate ApexCharts dicts keyed by ISO datetime
            # This allows ApexCharts cards to directly consume the data for graphing
            hourly_dict = self._cache.data.get("hourly", {})
            hourly_total_usage = {}  # TOTAL usage (paid + free)
            hourly_paid_usage = {}  # paid usage (peak + off-peak)
            hourly_free_usage = {}  # free/unpaid usage
            hourly_peak_usage = {}  # peak rate usage
            hourly_offpeak_usage = {}  # off-peak rate usage
            
            for timestamp, record in sorted(hourly_dict.items()):
                # Use ISO datetime as key for ApexCharts compatibility
                ts_key = record.get("timestamp", timestamp)
                hourly_total_usage[ts_key] = record.get("total", 0.0)  # total = paid + free
                hourly_paid_usage[ts_key] = record.get("paid", 0.0)  # paid = peak + off-peak
                hourly_free_usage[ts_key] = record.get("free", 0.0)  # free/unpaid
                hourly_peak_usage[ts_key] = record.get("peak", 0.0)  # peak rate
                hourly_offpeak_usage[ts_key] = record.get("offpeak", 0.0)  # off-peak rate
                
            attributes["hourly_total_usage"] = hourly_total_usage
            attributes["hourly_paid_usage"] = hourly_paid_usage
            attributes["hourly_free_usage"] = hourly_free_usage
            attributes["hourly_peak_usage"] = hourly_peak_usage
            attributes["hourly_offpeak_usage"] = hourly_offpeak_usage
            attributes["hourly_count"] = len(hourly_dict)

            # Extract daily usage data - populate ApexCharts dicts keyed by date string
            daily_dict = self._cache.data.get("daily", {})
            daily_total_usage = {}  # TOTAL usage (paid + free)
            daily_paid_usage = {}  # paid usage (peak + off-peak)
            daily_free_usage = {}  # free/unpaid usage
            daily_peak_usage = {}  # peak rate usage
            daily_offpeak_usage = {}  # off-peak rate usage
            
            # Accumulators for summary statistics
            daily_total_kwh = 0.0
            daily_paid_kwh = 0.0
            daily_peak_kwh = 0.0
            daily_offpeak_kwh = 0.0
            daily_free_kwh = 0.0
            daily_total_cost = 0.0
            
            # Yearly and seasonal statistics
            current_year = datetime.now().year
            rolling_365_start = datetime.now() - timedelta(days=365)
            
            year_calendar_total = 0.0
            year_calendar_paid = 0.0
            year_calendar_peak = 0.0
            year_calendar_offpeak = 0.0
            year_calendar_free = 0.0
            year_calendar_cost = 0.0
            year_calendar_days = 0
            
            year_rolling_total = 0.0
            year_rolling_paid = 0.0
            year_rolling_peak = 0.0
            year_rolling_offpeak = 0.0
            year_rolling_free = 0.0
            year_rolling_cost = 0.0
            year_rolling_days = 0
            
            # NZ Seasons: Spring (Sep-Nov), Summer (Dec-Feb), Autumn (Mar-Jun), Winter (Jul-Aug)
            spring_total = 0.0
            spring_days = 0
            summer_total = 0.0
            summer_days = 0
            autumn_total = 0.0
            autumn_days = 0
            winter_total = 0.0
            winter_days = 0
            
            for date_key, record in sorted(daily_dict.items()):
                try:
                    date_obj = datetime.strptime(date_key, "%Y-%m-%d")
                except ValueError:
                    continue
                    
                total = record.get("total", 0.0)
                paid = record.get("paid", 0.0)
                peak = record.get("peak", 0.0)
                offpeak = record.get("offpeak", 0.0)
                free = record.get("free", 0.0)
                cost = record.get("cost", 0.0)
                
                daily_total_usage[date_key] = total
                daily_paid_usage[date_key] = paid
                daily_free_usage[date_key] = free
                daily_peak_usage[date_key] = peak
                daily_offpeak_usage[date_key] = offpeak
                
                # Accumulate totals for all cached daily data
                daily_total_kwh += total
                daily_paid_kwh += paid
                daily_peak_kwh += peak
                daily_offpeak_kwh += offpeak
                daily_free_kwh += free
                daily_total_cost += cost
                
                # Calendar year statistics
                if date_obj.year == current_year:
                    year_calendar_total += total
                    year_calendar_paid += paid
                    year_calendar_peak += peak
                    year_calendar_offpeak += offpeak
                    year_calendar_free += free
                    year_calendar_cost += cost
                    year_calendar_days += 1
                
                # Rolling 365 days statistics
                if date_obj >= rolling_365_start:
                    year_rolling_total += total
                    year_rolling_paid += paid
                    year_rolling_peak += peak
                    year_rolling_offpeak += offpeak
                    year_rolling_free += free
                    year_rolling_cost += cost
                    year_rolling_days += 1
                
                # Seasonal statistics (NZ seasons)
                month = date_obj.month
                if month in [9, 10, 11]:  # Spring: Sep-Nov
                    spring_total += total
                    spring_days += 1
                elif month in [12, 1, 2]:  # Summer: Dec-Feb
                    summer_total += total
                    summer_days += 1
                elif month in [3, 4, 5, 6]:  # Autumn: Mar-Jun
                    autumn_total += total
                    autumn_days += 1
                elif month in [7, 8]:  # Winter: Jul-Aug
                    winter_total += total
                    winter_days += 1
                
            attributes["daily_total_usage"] = daily_total_usage
            attributes["daily_paid_usage"] = daily_paid_usage
            attributes["daily_free_usage"] = daily_free_usage
            attributes["daily_peak_usage"] = daily_peak_usage
            attributes["daily_offpeak_usage"] = daily_offpeak_usage
            attributes["daily_count"] = len(daily_dict)

            # Extract monthly usage data - populate ApexCharts dicts keyed by month string
            monthly_dict = self._cache.data.get("monthly", {})
            monthly_total_usage = {}  # TOTAL usage (paid + free)
            monthly_paid_usage = {}  # paid usage (peak + off-peak)
            monthly_free_usage = {}  # free/unpaid usage
            monthly_peak_usage = {}  # peak rate usage
            monthly_offpeak_usage = {}  # off-peak rate usage
            
            monthly_total_kwh = 0.0
            monthly_paid_kwh = 0.0
            monthly_peak_kwh = 0.0
            monthly_offpeak_kwh = 0.0
            monthly_free_kwh = 0.0
            monthly_total_cost = 0.0
            monthly_total_days = 0  # Sum of days in each month for averaging
            
            for month_key, record in sorted(monthly_dict.items()):
                total = record.get("total", 0.0)
                paid = record.get("paid", 0.0)
                peak = record.get("peak", 0.0)
                offpeak = record.get("offpeak", 0.0)
                free = record.get("free", 0.0)
                cost = record.get("cost", 0.0)
                
                monthly_total_usage[month_key] = total
                monthly_paid_usage[month_key] = paid
                monthly_free_usage[month_key] = free
                monthly_peak_usage[month_key] = peak
                monthly_offpeak_usage[month_key] = offpeak
                
                # Accumulate totals for summary statistics
                monthly_total_kwh += total
                monthly_paid_kwh += paid
                monthly_peak_kwh += peak
                monthly_offpeak_kwh += offpeak
                monthly_free_kwh += free
                monthly_total_cost += cost
                
                # Calculate days in this month for averaging
                try:
                    year, month = map(int, month_key.split("-"))
                    days_in_month = monthrange(year, month)[1]
                    monthly_total_days += days_in_month
                except (ValueError, IndexError):
                    pass
                
            attributes["monthly_total_usage"] = monthly_total_usage
            attributes["monthly_paid_usage"] = monthly_paid_usage
            attributes["monthly_free_usage"] = monthly_free_usage
            attributes["monthly_peak_usage"] = monthly_peak_usage
            attributes["monthly_offpeak_usage"] = monthly_offpeak_usage
            attributes["monthly_count"] = len(monthly_dict)

            # Update summary statistics for quick reference without expanding attributes
            attributes["summary"] = {
                # Daily totals (all cached daily data)
                "daily_total_kwh": round(daily_total_kwh, 2),
                "daily_paid_kwh": round(daily_paid_kwh, 2),
                "daily_peak_kwh": round(daily_peak_kwh, 2),
                "daily_offpeak_kwh": round(daily_offpeak_kwh, 2),
                "daily_free_kwh": round(daily_free_kwh, 2),
                "daily_cost_nzd": round(daily_total_cost, 2),
                "daily_count": len(daily_dict),
                # Daily averages (kWh per hour) - divide by 24
                "daily_average_usage": round(daily_total_kwh / 24, 3) if daily_total_kwh > 0 else 0.0,
                "daily_average_paid_usage": round(daily_paid_kwh / 24, 3) if daily_paid_kwh > 0 else 0.0,
                "daily_average_free_usage": round(daily_free_kwh / 24, 3) if daily_free_kwh > 0 else 0.0,
                "daily_average_offpeak_usage": round(daily_offpeak_kwh / 24, 3) if daily_offpeak_kwh > 0 else 0.0,
                # Monthly totals (all cached monthly data)
                "monthly_total_kwh": round(monthly_total_kwh, 2),
                "monthly_paid_kwh": round(monthly_paid_kwh, 2),
                "monthly_peak_kwh": round(monthly_peak_kwh, 2),
                "monthly_offpeak_kwh": round(monthly_offpeak_kwh, 2),
                "monthly_free_kwh": round(monthly_free_kwh, 2),
                "monthly_cost_nzd": round(monthly_total_cost, 2),
                "monthly_count": len(monthly_dict),
                # Monthly averages (kWh per day) - divide by total days in all months
                "monthly_average_usage": round(monthly_total_kwh / monthly_total_days, 2) if monthly_total_days > 0 else 0.0,
                "monthly_average_paid_usage": round(monthly_paid_kwh / monthly_total_days, 2) if monthly_total_days > 0 else 0.0,
                "monthly_average_free_usage": round(monthly_free_kwh / monthly_total_days, 2) if monthly_total_days > 0 else 0.0,
                "monthly_average_offpeak_usage": round(monthly_offpeak_kwh / monthly_total_days, 2) if monthly_total_days > 0 else 0.0,
                # Yearly statistics (calendar year)
                "year_calendar_total_kwh": round(year_calendar_total, 2),
                "year_calendar_paid_kwh": round(year_calendar_paid, 2),
                "year_calendar_peak_kwh": round(year_calendar_peak, 2),
                "year_calendar_offpeak_kwh": round(year_calendar_offpeak, 2),
                "year_calendar_free_kwh": round(year_calendar_free, 2),
                "year_calendar_cost_nzd": round(year_calendar_cost, 2),
                "year_calendar_average_per_day": round(year_calendar_total / year_calendar_days, 2) if year_calendar_days > 0 else 0.0,
                # Yearly statistics (rolling 365 days)
                "year_rolling_total_kwh": round(year_rolling_total, 2),
                "year_rolling_paid_kwh": round(year_rolling_paid, 2),
                "year_rolling_peak_kwh": round(year_rolling_peak, 2),
                "year_rolling_offpeak_kwh": round(year_rolling_offpeak, 2),
                "year_rolling_free_kwh": round(year_rolling_free, 2),
                "year_rolling_cost_nzd": round(year_rolling_cost, 2),
                "year_rolling_average_per_day": round(year_rolling_total / year_rolling_days, 2) if year_rolling_days > 0 else 0.0,
                # Seasonal averages (NZ seasons, kWh per day)
                "season_spring_avg_per_day": round(spring_total / spring_days, 2) if spring_days > 0 else 0.0,  # Sep-Nov
                "season_summer_avg_per_day": round(summer_total / summer_days, 2) if summer_days > 0 else 0.0,  # Dec-Feb
                "season_autumn_avg_per_day": round(autumn_total / autumn_days, 2) if autumn_days > 0 else 0.0,  # Mar-Jun
                "season_winter_avg_per_day": round(winter_total / winter_days, 2) if winter_days > 0 else 0.0,  # Jul-Aug
            }

            _LOGGER.debug(
                "Loaded usage data for contract %s: hourly=%d, daily=%d, monthly=%d (size=%d bytes)",
                self._contract_id,
                attributes["hourly_count"],
                attributes["daily_count"],
                attributes["monthly_count"],
                len(str(attributes))
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
