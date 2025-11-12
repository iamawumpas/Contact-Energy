"""Contact Energy sensor platform - Refactored for efficiency."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime, timedelta, date
from typing import Any, Optional, Callable

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
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.const import UnitOfEnergy, EVENT_HOMEASSISTANT_STARTED

from .const import (
    DOMAIN,
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_CONTRACT_ICP,
    CONF_USAGE_DAYS,
    CONF_USAGE_MONTHS,
    months_to_days,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DEVICE_SW_VERSION,
    CHART_HOURLY_DAYS,
    CHART_DAILY_DAYS,
    CHART_MONTHLY_START_YEAR,
    STARTUP_DELAY_BASE_MAX,
    STARTUP_DELAY_JITTER_MIN,
    STARTUP_DELAY_JITTER_MAX,
    CONVENIENCE_DELAY_BASE_MAX,
    CONVENIENCE_DELAY_JITTER_MIN,
    CONVENIENCE_DELAY_JITTER_MAX,
)
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def safe_float(value: Any) -> float:
    """Safely convert value to float."""
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def sanitize_icp_for_statistic_id(icp: str) -> str:
    """Convert ICP to a valid statistic ID component."""
    safe_icp = re.sub(r'[^a-z0-9_]', '_', icp.lower())
    if re.match(r'^[0-9]', safe_icp):
        safe_icp = f"icp_{safe_icp}"
    return safe_icp


def get_statistic_ids(contract_icp: str) -> tuple[str, str, str]:
    """Generate statistic IDs for a contract ICP."""
    safe_icp = sanitize_icp_for_statistic_id(contract_icp)
    return (
        f"{DOMAIN}:energy_{safe_icp}",
        f"{DOMAIN}:cost_{safe_icp}",
        f"{DOMAIN}:free_energy_{safe_icp}",
    )


def calculate_startup_delay(contract_icp: str, is_convenience: bool = False) -> float:
    """Calculate consistent startup delay based on ICP hash."""
    icp_hash = int(hashlib.md5(contract_icp.encode()).hexdigest()[:8], 16)
    if is_convenience:
        base_delay = (icp_hash % CONVENIENCE_DELAY_BASE_MAX) / 10.0
        jitter = random.uniform(CONVENIENCE_DELAY_JITTER_MIN, CONVENIENCE_DELAY_JITTER_MAX)
    else:
        base_delay = (icp_hash % STARTUP_DELAY_BASE_MAX) / 10.0
        jitter = random.uniform(STARTUP_DELAY_JITTER_MIN, STARTUP_DELAY_JITTER_MAX)
    return base_delay + jitter


def get_device_info(contract_icp: str) -> dict[str, Any]:
    """Get standardized device information."""
    return {
        "identifiers": {(DOMAIN, contract_icp)},
        "name": f"{DEVICE_MANUFACTURER} ({contract_icp})",
        "manufacturer": DEVICE_MANUFACTURER,
        "model": DEVICE_MODEL,
        "sw_version": DEVICE_SW_VERSION,
    }


# ============================================================================
# SENSOR SETUP
# ============================================================================

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
    
    # Prefer months setting; fall back to legacy days
    if CONF_USAGE_MONTHS in entry.data:
        usage_days = months_to_days(entry.data.get(CONF_USAGE_MONTHS))
    else:
        usage_days = entry.data.get(CONF_USAGE_DAYS, 30)

    # Generate statistic IDs once
    kwh_stat_id, dollar_stat_id, free_stat_id = get_statistic_ids(contract_icp)

    # Create all entities
    entities = []
    
    # Main usage sensor for Energy Dashboard
    entities.append(ContactEnergyUsageSensor(
        coordinator, account_id, contract_id, contract_icp, usage_days
    ))

    # Account information sensors
    account_sensors = [
        ("balance", "Account Balance", SensorDeviceClass.MONETARY, "NZD", "mdi:currency-usd"),
        ("next_bill_date", "Next Bill Date", SensorDeviceClass.DATE, None, "mdi:calendar-clock"),
        ("customer_name", "Customer Name", None, None, "mdi:account"),
        ("plan_name", "Plan Name", None, None, "mdi:lightning-bolt"),
        ("account_number", "Account Number", None, None, "mdi:identifier"),
        ("service_address", "Service Address", None, None, "mdi:home"),
        ("meter_serial", "Meter Serial", None, None, "mdi:counter"),
        ("next_read_date", "Next Read Date", SensorDeviceClass.DATE, None, "mdi:calendar-arrow-right"),
        ("last_read_date", "Last Read Date", SensorDeviceClass.DATE, None, "mdi:calendar-check"),
        ("daily_charge_rate", "Daily Charge Rate", SensorDeviceClass.MONETARY, "NZD", "mdi:currency-usd"),
        ("peak_rate", "Peak Rate", SensorDeviceClass.MONETARY, "NZD/kWh", "mdi:trending-up"),
        ("off_peak_rate", "Off Peak Rate", SensorDeviceClass.MONETARY, "NZD/kWh", "mdi:trending-down"),
        ("free_hours", "Free Hours", None, None, "mdi:clock-time-eight"),
        ("last_payment", "Last Payment", SensorDeviceClass.MONETARY, "NZD", "mdi:credit-card"),
        ("estimated_next_bill", "Estimated Next Bill", SensorDeviceClass.MONETARY, "NZD", "mdi:receipt"),
    ]
    
    for sensor_type, name, device_class, unit, icon in account_sensors:
        entities.append(ContactEnergyAccountSensor(
            coordinator, contract_icp, sensor_type, name, device_class, unit, icon
        ))

    # Convenience usage/cost sensors
    convenience_sensors = [
        ("today_usage", "Today Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar-today", "usage"),
        ("yesterday_usage", "Yesterday Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar-minus", "usage"),
        ("last_7_days_usage", "Last 7 Days Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar-week", "usage"),
        ("last_30_days_usage", "Last 30 Days Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar-month", "usage"),
        ("current_month_usage", "Current Month Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar", "usage"),
        ("last_month_usage", "Last Month Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar-arrow-left", "usage"),
        ("today_cost", "Today Cost", SensorDeviceClass.MONETARY, "NZD", "mdi:currency-usd", "cost"),
        ("yesterday_cost", "Yesterday Cost", SensorDeviceClass.MONETARY, "NZD", "mdi:currency-usd", "cost"),
        ("current_month_cost", "Current Month Cost", SensorDeviceClass.MONETARY, "NZD", "mdi:currency-usd", "cost"),
        ("last_month_cost", "Last Month Cost", SensorDeviceClass.MONETARY, "NZD", "mdi:currency-usd", "cost"),
        ("today_free_usage", "Today Free Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:gift", "free"),
        ("yesterday_free_usage", "Yesterday Free Usage", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, "mdi:gift", "free"),
    ]
    
    for sensor_type, name, device_class, unit, icon, metric in convenience_sensors:
        entities.append(ContactEnergyConvenienceSensor(
            coordinator, account_id, contract_id, contract_icp, sensor_type, name, device_class, unit, icon, metric
        ))

    # Chart sensors for ApexCharts
    chart_sensors = [
        (kwh_stat_id, "hourly", "Chart Hourly", "hour", CHART_HOURLY_DAYS, "mdi:chart-bar"),
        (kwh_stat_id, "daily", "Chart Daily", "day", CHART_DAILY_DAYS, "mdi:calendar"),
        (free_stat_id, "hourly_free", "Chart Hourly Free", "hour", CHART_HOURLY_DAYS, "mdi:gift"),
        (free_stat_id, "daily_free", "Chart Daily Free", "day", CHART_DAILY_DAYS, "mdi:gift"),
        (kwh_stat_id, "monthly", "Chart Monthly", "month", None, "mdi:calendar-month"),
        (free_stat_id, "monthly_free", "Chart Monthly Free", "month", None, "mdi:gift"),
    ]
    
    for stat_id, sensor_type, name, period, days, icon in chart_sensors:
        entities.append(ContactEnergyChartSensor(
            hass, contract_icp, stat_id, sensor_type, name, period, days, icon
        ))

    async_add_entities(entities, False)


# ============================================================================
# MAIN USAGE SENSOR (Energy Dashboard Integration)
# ============================================================================

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
        return get_device_info(self._contract_icp)

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        async def _kickoff_download(_event=None) -> None:
            total_delay = calculate_startup_delay(self._contract_icp, is_convenience=False)
            try:
                await asyncio.sleep(total_delay)
            except Exception:  # noqa: BLE001
                pass
            _LOGGER.info("Starting initial usage data download for %s (delay: %.1fs)", self._contract_icp, total_delay)
            self._download_task = self.hass.async_create_task(self._download_usage_data())

        if getattr(self.hass, "is_running", False):
            await _kickoff_download()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _kickoff_download)

    async def async_will_remove_from_hass(self) -> None:
        """Called when entity is about to be removed from Home Assistant."""
        if self._download_task and not self._download_task.done():
            self._download_task.cancel()
        await super().async_will_remove_from_hass()

    async def async_update(self) -> None:
        """Update usage data and statistics (called every 8 hours)."""
        now = datetime.now()
        
        # Only update if it's been 8+ hours since last update
        if self._last_usage_update and (now - self._last_usage_update) < timedelta(hours=8):
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
            _LOGGER.info("Starting usage data download for up to %s days (missing only)", self._usage_days)

            # Calculate default date range
            today = datetime.now().date()
            start_date = today - timedelta(days=self._usage_days - 1)
            end_date = today

            # Build statistic IDs
            kwh_stat_id, dollar_stat_id, free_stat_id = get_statistic_ids(self._contract_icp)

            # Initialize base sums
            base_kwh_sum = 0.0
            base_dollar_sum = 0.0
            base_free_sum = 0.0

            # Determine where to continue from
            try:
                last_stats = await self.hass.async_add_executor_job(
                    get_last_statistics, self.hass, 1, [kwh_stat_id, dollar_stat_id, free_stat_id]
                )
                
                if isinstance(last_stats, dict) and kwh_stat_id in last_stats and last_stats[kwh_stat_id]:
                    last_entry = last_stats[kwh_stat_id][0]
                    last_start = last_entry.get("start")
                    if isinstance(last_start, datetime):
                        candidate = last_start.date() + timedelta(days=1)
                        if candidate > start_date:
                            start_date = candidate
                    base_kwh_sum = safe_float(last_entry.get("sum"))
                    
                if isinstance(last_stats, dict) and dollar_stat_id in last_stats and last_stats[dollar_stat_id]:
                    base_dollar_sum = safe_float(last_stats[dollar_stat_id][0].get("sum"))
                    
                if isinstance(last_stats, dict) and free_stat_id in last_stats and last_stats[free_stat_id]:
                    base_free_sum = safe_float(last_stats[free_stat_id][0].get("sum"))
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("Could not determine last statistics entries: %s", e)

            # If nothing to do, exit early
            if start_date > end_date:
                _LOGGER.info("Statistics already up to date through %s; no download needed", end_date)
                return

            # Initialize statistics lists and running totals
            kwh_statistics = []
            dollar_statistics = []
            free_kwh_statistics = []
            kwh_running_sum = base_kwh_sum
            dollar_running_sum = base_dollar_sum
            free_kwh_running_sum = base_free_sum
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

                    # Only process if we got actual data points
                    if response and isinstance(response, list) and len(response) > 0:
                        for point in response:
                            if point.get('currency') and currency != point['currency']:
                                currency = point['currency']

                            value_float = safe_float(point.get("value"))
                            dollar_value_float = safe_float(point.get("dollarValue"))
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
                        _LOGGER.debug("No data available for %s (may not be released yet)", date_str)

                except Exception as error:
                    error_type = type(error).__name__
                    if "timeout" in str(error).lower() or "504" in str(error):
                        _LOGGER.warning("API timeout for %s - Contact Energy servers may be slow: %s", date_str, error)
                    else:
                        _LOGGER.warning("Failed to fetch data for %s (%s): %s", date_str, error_type, error)

                current_date += timedelta(days=1)
                await asyncio.sleep(0.5)

            # Update Home Assistant statistics
            if kwh_statistics:
                await self._add_statistics(kwh_statistics, dollar_statistics, free_kwh_statistics, currency, free_kwh_running_sum)
                _LOGGER.info("Usage data download completed. Added %d statistics entries, Total kWh: %.2f", 
                           len(kwh_statistics), kwh_running_sum)
            else:
                _LOGGER.warning("No usage data retrieved - all API requests may have failed")
            
            self._state = kwh_running_sum

        except Exception as error:
            _LOGGER.exception("Usage data download failed: %s", error)

    async def _add_statistics(
        self,
        kwh_stats: list,
        dollar_stats: list,
        free_kwh_stats: list,
        currency: str,
        free_kwh_total: float = 0
    ) -> None:
        """Add statistics to Home Assistant."""
        if not kwh_stats:
            _LOGGER.debug("No statistics to add")
            return

        kwh_stat_id, dollar_stat_id, free_stat_id = get_statistic_ids(self._contract_icp)

        # Main electricity consumption for Energy Dashboard
        kwh_metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=f"Contact Energy - Electricity ({self._contract_icp})",
            source=DOMAIN,
            statistic_id=kwh_stat_id,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            unit_class="energy",
            mean_type="arithmetic",
        )
        async_add_external_statistics(self.hass, kwh_metadata, kwh_stats)

        # Electricity cost
        if dollar_stats:
            dollar_metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"Contact Energy - Electricity Cost ({self._contract_icp})",
                source=DOMAIN,
                statistic_id=dollar_stat_id,
                unit_of_measurement=currency,
                unit_class="monetary",
                mean_type="arithmetic",
            )
            async_add_external_statistics(self.hass, dollar_metadata, dollar_stats)

        # Free electricity (if any)
        if free_kwh_stats and free_kwh_total > 0:
            free_kwh_metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"Contact Energy - Free Electricity ({self._contract_icp})",
                source=DOMAIN,
                statistic_id=free_stat_id,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                unit_class="energy",
                mean_type="arithmetic",
            )
            async_add_external_statistics(self.hass, free_kwh_metadata, free_kwh_stats)

        _LOGGER.debug("Added statistics to Home Assistant")


# ============================================================================
# ACCOUNT INFORMATION SENSORS (Consolidated)
# ============================================================================

class ContactEnergyAccountSensor(CoordinatorEntity, SensorEntity):
    """Consolidated account information sensor."""

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        contract_icp: str,
        sensor_type: str,
        name: str,
        device_class: Optional[SensorDeviceClass],
        unit: Optional[str],
        icon: str,
    ) -> None:
        """Initialize account sensor."""
        super().__init__(coordinator)
        self._contract_icp = contract_icp
        self._sensor_type = sensor_type
        
        self._attr_name = f"Contact Energy {name} ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_{sensor_type}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return get_device_info(self._contract_icp)

    @property
    def should_poll(self) -> bool:
        """Entity doesn't poll."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def native_value(self) -> Any:
        """Return sensor value based on type."""
        if not self.available:
            return None
            
        account_data = self.coordinator.data.get("account_details", {})
        contracts = account_data.get("contracts", [])
        contract_data = next((c for c in contracts if c.get("icp") == self._contract_icp), {})
        
        # Map sensor types to data extraction
        value_map = {
            "balance": lambda: safe_float(account_data.get("accountBalance", {}).get("currentBalance")),
            "next_bill_date": lambda: self._parse_date(account_data.get("nextBill", {}).get("date")),
            "customer_name": lambda: account_data.get("nickname"),
            "plan_name": lambda: f"{contract_data.get('contractTypeLabel', 'Electricity')} Contract" if contract_data.get("contractTypeLabel") else None,
            "account_number": lambda: account_data.get("id"),
            "service_address": lambda: contract_data.get("premise", {}).get("supplyAddress", {}).get("shortForm"),
            "meter_serial": lambda: contract_data.get("devices", [{}])[0].get("serialNumber") if contract_data.get("devices") else None,
            "next_read_date": lambda: self._parse_date(contract_data.get("devices", [{}])[0].get("nextMeterReadDate")) if contract_data.get("devices") else None,
            "last_read_date": lambda: self._parse_date_safe(contract_data),
            "daily_charge_rate": lambda: safe_float(contract_data.get("planDetails", {}).get("dailyCharge")),
            "peak_rate": lambda: safe_float(contract_data.get("planDetails", {}).get("unitRates", {}).get("peak")),
            "off_peak_rate": lambda: safe_float(contract_data.get("planDetails", {}).get("unitRates", {}).get("offPeak")),
            "free_hours": lambda: contract_data.get("planDetails", {}).get("unitRates", {}).get("freeHours"),
            "last_payment": lambda: self._parse_payment(account_data),
            "estimated_next_bill": lambda: safe_float(account_data.get("nextBill", {}).get("amount")),
        }
        
        extractor = value_map.get(self._sensor_type)
        return extractor() if extractor else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes for specific sensors."""
        if self._sensor_type == "last_payment":
            account_data = self.coordinator.data.get("account_details", {})
            payments = account_data.get("payments", [])
            if payments:
                return {
                    "date": payments[0].get("date"),
                    "payment_method": account_data.get("paymentMethod"),
                }
        elif self._sensor_type == "estimated_next_bill":
            account_data = self.coordinator.data.get("account_details", {})
            next_bill = account_data.get("nextBill", {})
            if next_bill:
                return {"bill_date": next_bill.get("date")}
        return {}

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%d %b %Y").date()
        except (ValueError, TypeError):
            _LOGGER.warning("Could not parse date: %s", date_str)
            return None

    def _parse_date_safe(self, contract_data: dict) -> Optional[date]:
        """Parse last read date with additional safety."""
        devices = contract_data.get("devices", [])
        if devices and devices[0].get("registers"):
            registers = devices[0].get("registers", [])
            if registers:
                date_str = registers[0].get("previousMeterReadingDate")
                if date_str and date_str != "Invalid date":
                    return self._parse_date(date_str)
        return None

    def _parse_payment(self, account_data: dict) -> Optional[float]:
        """Parse payment amount from string."""
        payments = account_data.get("payments", [])
        if payments:
            amt_str = payments[0].get("amount", "")
            try:
                amt_clean = amt_str.replace("$", "").replace(",", "")
                return float(amt_clean) if amt_clean else None
            except (ValueError, TypeError):
                return None
        return None


# ============================================================================
# CONVENIENCE SENSORS (Consolidated)
# ============================================================================

class ContactEnergyConvenienceSensor(CoordinatorEntity, SensorEntity):
    """Consolidated convenience sensor for usage/cost calculations."""

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        account_id: str,
        contract_id: str,
        contract_icp: str,
        sensor_type: str,
        name: str,
        device_class: SensorDeviceClass,
        unit: str,
        icon: str,
        metric: str,  # "usage", "cost", or "free"
    ) -> None:
        """Initialize convenience sensor."""
        super().__init__(coordinator)
        self._account_id = account_id
        self._contract_id = contract_id
        self._contract_icp = contract_icp
        self._sensor_type = sensor_type
        self._metric = metric
        self._state = 0.0

        self._attr_name = f"Contact Energy {name} ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_{sensor_type}"
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.TOTAL if "usage" in metric or "free" in metric else None
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return get_device_info(self._contract_icp)

    @property
    def should_poll(self) -> bool:
        """Entity doesn't poll."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def native_value(self) -> float:
        """Return current state."""
        return self._state

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to hass."""
        await super().async_added_to_hass()

        async def _delayed_recompute():
            # Wait for coordinator to have data
            if not self.coordinator.last_update_success or self.coordinator.data is None:
                max_wait_time = 60
                wait_interval = 0.5
                elapsed = 0
                while (not self.coordinator.last_update_success or self.coordinator.data is None) and elapsed < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    elapsed += wait_interval
            
            total_delay = calculate_startup_delay(self._contract_icp, is_convenience=True)
            try:
                await asyncio.sleep(total_delay)
            except Exception:  # noqa: BLE001
                pass
            await self._recompute()

        self.hass.async_create_task(_delayed_recompute())

    def _handle_coordinator_update(self) -> None:
        """Recompute on coordinator refresh."""
        self.hass.async_create_task(self._recompute())

    async def _recompute(self) -> None:
        """Recompute sensor value."""
        start, end = self._get_date_range()
        kwh, cost, free_kwh = await self._fetch_usage_data(start, end)
        
        # Apply appropriate metric
        if self._metric == "usage":
            self._state = kwh
        elif self._metric == "cost":
            self._state = cost
        elif self._metric == "free":
            self._state = free_kwh
            
        self.async_write_ha_state()

    def _get_date_range(self) -> tuple[date, date]:
        """Get date range for sensor type."""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        range_map = {
            "today_usage": (today, today),
            "today_cost": (today, today),
            "today_free_usage": (today, today),
            "yesterday_usage": (yesterday, yesterday),
            "yesterday_cost": (yesterday, yesterday),
            "yesterday_free_usage": (yesterday, yesterday),
            "last_7_days_usage": (yesterday - timedelta(days=6), yesterday),
            "last_30_days_usage": (yesterday - timedelta(days=29), yesterday),
            "current_month_usage": (today.replace(day=1), today),
            "current_month_cost": (today.replace(day=1), today),
            "last_month_usage": self._last_month_range(),
            "last_month_cost": self._last_month_range(),
        }
        
        return range_map.get(self._sensor_type, (today, today))

    def _last_month_range(self) -> tuple[date, date]:
        """Calculate last month's date range."""
        today = datetime.now().date()
        first_current = today.replace(day=1)
        last_prev = first_current - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev, last_prev

    async def _fetch_usage_data(self, start_date: date, end_date: date) -> tuple[float, float, float]:
        """Fetch usage data for date range."""
        total_kwh = 0.0
        total_cost = 0.0
        total_free_kwh = 0.0
        
        current = start_date
        while current <= end_date:
            try:
                resp = await self.coordinator.api.async_get_usage(
                    str(current.year), str(current.month), str(current.day),
                    self._account_id, self._contract_id
                )
                if isinstance(resp, list):
                    for p in resp:
                        val = safe_float(p.get("value"))
                        cost = safe_float(p.get("dollarValue"))
                        off = str(p.get("offpeakValue", "0.00"))
                        if off == "0.00":
                            total_kwh += val
                            total_cost += cost
                        else:
                            total_free_kwh += val
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("Convenience fetch failed for %s: %s", current, e)
            
            current += timedelta(days=1)
            await asyncio.sleep(0)
        
        return total_kwh, total_cost, total_free_kwh


# ============================================================================
# CHART SENSORS (Consolidated)
# ============================================================================

class ContactEnergyChartSensor(SensorEntity):
    """Consolidated chart sensor for ApexCharts."""

    def __init__(
        self,
        hass: HomeAssistant,
        contract_icp: str,
        stat_id: str,
        sensor_type: str,
        name: str,
        period: str,  # "hour", "day", or "month"
        days: Optional[int],  # Days to query (None for monthly)
        icon: str,
    ) -> None:
        """Initialize chart sensor."""
        self.hass = hass
        self._contract_icp = contract_icp
        self._stat_id = stat_id
        self._sensor_type = sensor_type
        self._period = period
        self._days = days
        self._data: dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._recorder_instance = None

        self._attr_name = f"Contact Energy {name} ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_{sensor_type}"
        self._attr_icon = icon

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return get_device_info(self._contract_icp)

    @property
    def state(self) -> Any:
        """Return most recent value."""
        if self._data:
            latest = max(self._data.keys())
            return self._data[latest]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return data as attributes."""
        attr_name = f"{self._period}ly_data" if self._period != "month" else "monthly_data"
        if "free" in self._sensor_type:
            attr_name = attr_name.replace("_data", "_free_data")
        
        return {
            attr_name: self._data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def async_update(self) -> None:
        """Update chart data from statistics."""
        # Cache recorder instance
        if not self._recorder_instance:
            recorder = __import__("homeassistant.components.recorder").components.recorder
            self._recorder_instance = recorder.get_instance(self.hass)

        # Calculate time range
        end_time = datetime.now()
        if self._period == "month":
            start_time = datetime(CHART_MONTHLY_START_YEAR, 1, 1)
        else:
            start_time = end_time - timedelta(days=self._days)

        # Fetch statistics
        stats = await self._recorder_instance.async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time if self._period != "month" else None,
            [self._stat_id],
            self._period,
            None,
            {"sum"}
        )

        self._data = {}
        if self._stat_id in stats:
            if self._period == "day":
                self._process_daily_stats(stats[self._stat_id])
            elif self._period == "month":
                self._process_monthly_stats(stats[self._stat_id])
            else:  # hour
                self._process_hourly_stats(stats[self._stat_id])

        self._last_update = datetime.now()

    def _process_daily_stats(self, entries: list) -> None:
        """Process daily statistics with delta calculation."""
        sorted_entries = sorted(entries, key=lambda x: x.get("start", 0))
        prev_val = None
        
        for entry in sorted_entries:
            start_ts = entry.get("start")
            val = entry.get("sum")
            if start_ts and val is not None:
                dt = self._timestamp_to_datetime(start_ts)
                if dt:
                    dt_end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)
                    iso_key = dt_end_of_day.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    if prev_val is not None:
                        delta = abs(float(val) - prev_val)
                    else:
                        delta = float(val)
                    
                    self._data[iso_key] = delta
                    prev_val = float(val)

    def _process_monthly_stats(self, entries: list) -> None:
        """Process monthly statistics."""
        for entry in entries:
            start_ts = entry.get("start")
            val = entry.get("change", entry.get("sum"))
            if start_ts and val is not None:
                dt = self._timestamp_to_datetime(start_ts)
                if dt:
                    self._data[dt.strftime("%Y-%m-15")] = float(val)

    def _process_hourly_stats(self, entries: list) -> None:
        """Process hourly statistics."""
        for entry in entries:
            start_ts = entry.get("start")
            val = entry.get("sum")
            if start_ts and val is not None:
                dt = self._timestamp_to_datetime(start_ts)
                if dt:
                    self._data[dt.isoformat()] = float(val)

    def _timestamp_to_datetime(self, start_ts: Any) -> Optional[datetime]:
        """Convert timestamp to datetime robustly."""
        if isinstance(start_ts, (int, float)):
            return datetime.fromtimestamp(start_ts)
        elif isinstance(start_ts, datetime):
            return start_ts
        return None
