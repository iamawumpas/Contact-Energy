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
from homeassistant.components.recorder.statistics import async_add_external_statistics, get_last_statistics
from homeassistant.const import UnitOfEnergy, EVENT_HOMEASSISTANT_STARTED
import random

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

    # Add account information sensors (read from coordinator account_details)
    entities.extend([
        ContactEnergyAccountBalanceSensor(coordinator, contract_icp),
        ContactEnergyNextBillDateSensor(coordinator, contract_icp),
        ContactEnergyCustomerNameSensor(coordinator, contract_icp),
        ContactEnergyPlanNameSensor(coordinator, contract_icp),
        ContactEnergyAccountNumberSensor(coordinator, contract_icp),
        ContactEnergyServiceAddressSensor(coordinator, contract_icp),
        ContactEnergyMeterSerialSensor(coordinator, contract_icp),
        ContactEnergyNextReadDateSensor(coordinator, contract_icp),
        ContactEnergyLastReadDateSensor(coordinator, contract_icp),
        ContactEnergyDailyChargeRateSensor(coordinator, contract_icp),
        ContactEnergyPeakRateSensor(coordinator, contract_icp),
        ContactEnergyOffPeakRateSensor(coordinator, contract_icp),
        ContactEnergyFreeHoursSensor(coordinator, contract_icp),
        ContactEnergyLastPaymentSensor(coordinator, contract_icp),
        ContactEnergyEstimatedNextBillSensor(coordinator, contract_icp),
    ])

    async_add_entities(entities, False)

    # Convenience usage/cost sensors
    entities.extend([
        ContactEnergyTodayUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyYesterdayUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLast7DaysUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLast30DaysUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyCurrentMonthUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLastMonthUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyTodayCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyYesterdayCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyCurrentMonthCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLastMonthCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyTodayFreeUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyYesterdayFreeUsageSensor(coordinator, account_id, contract_id, contract_icp),
    ])

    async_add_entities(entities, False)


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

        async def _kickoff_download(_event=None) -> None:
            # Add randomized jitter based on contract ICP to spread out multiple accounts/contracts
            # Use hash of ICP to generate consistent but distributed delays
            import hashlib
            icp_hash = int(hashlib.md5(self._contract_icp.encode()).hexdigest()[:8], 16)
            base_delay = (icp_hash % 30) / 10.0  # 0-3 seconds based on ICP
            jitter = random.uniform(0.5, 2.0)  # Additional random jitter
            total_delay = base_delay + jitter
            
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
            _LOGGER.info("Starting usage data download for up to %s days (missing only)", self._usage_days)

            # Calculate default date range
            today = datetime.now().date()
            start_date = today - timedelta(days=self._usage_days - 1)
            end_date = today

            # Build statistic IDs and determine last recorded entries
            import re as _re
            safe_icp = _re.sub(r'[^a-z0-9_]', '_', self._contract_icp.lower())
            if _re.match(r'^[0-9]', safe_icp):
                safe_icp = f"icp_{safe_icp}"
            kwh_stat_id = f"{DOMAIN}:energy_{safe_icp}"
            dollar_stat_id = f"{DOMAIN}:cost_{safe_icp}"
            free_stat_id = f"{DOMAIN}:free_energy_{safe_icp}"

            base_kwh_sum = 0.0
            base_dollar_sum = 0.0
            base_free_sum = 0.0

            try:
                # get_last_statistics is synchronous; run in executor
                last_stats = await self.hass.async_add_executor_job(
                    get_last_statistics, self.hass, 1, [kwh_stat_id, dollar_stat_id, free_stat_id]
                )
                # Determine the next start date from kWh series (canonical)
                if isinstance(last_stats, dict) and kwh_stat_id in last_stats and last_stats[kwh_stat_id]:
                    last_entry = last_stats[kwh_stat_id][0]
                    last_start = last_entry.get("start")
                    if isinstance(last_start, datetime):
                        candidate = last_start.date() + timedelta(days=1)
                        if candidate > start_date:
                            start_date = candidate
                    try:
                        base_kwh_sum = float(last_entry.get("sum") or 0.0)
                    except (TypeError, ValueError):
                        base_kwh_sum = 0.0
                if isinstance(last_stats, dict) and dollar_stat_id in last_stats and last_stats[dollar_stat_id]:
                    try:
                        base_dollar_sum = float(last_stats[dollar_stat_id][0].get("sum") or 0.0)
                    except (TypeError, ValueError):
                        base_dollar_sum = 0.0
                if isinstance(last_stats, dict) and free_stat_id in last_stats and last_stats[free_stat_id]:
                    try:
                        base_free_sum = float(last_stats[free_stat_id][0].get("sum") or 0.0)
                    except (TypeError, ValueError):
                        base_free_sum = 0.0
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("Could not determine last statistics entries: %s", e)

            # If nothing to do (already up to date), exit early
            if start_date > end_date:
                _LOGGER.info("Statistics already up to date through %s; no download needed", end_date)
                return

            # Initialize statistics lists
            kwh_statistics = []
            dollar_statistics = []
            free_kwh_statistics = []
            
            # Running totals for cumulative statistics
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

            # Update Home Assistant statistics for missing period
            await self._add_statistics(kwh_statistics, dollar_statistics, free_kwh_statistics, currency, free_kwh_running_sum)
            
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
        currency: str,
        free_kwh_total: float = 0
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
        kwh_stat_id = f"{DOMAIN}:energy_{safe_icp}"
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
            dollar_stat_id = f"{DOMAIN}:cost_{safe_icp}"
            dollar_metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"Contact Energy - Electricity Cost ({self._contract_icp})",
                source=DOMAIN,
                statistic_id=dollar_stat_id,
                unit_of_measurement=currency,
            )
            async_add_external_statistics(self.hass, dollar_metadata, dollar_stats)

        # Free electricity (if any) - only add if we have meaningful data
        if free_kwh_stats and free_kwh_total > 0:
            free_stat_id = f"{DOMAIN}:free_energy_{safe_icp}"
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


# -----------------------------
# Account information sensors
# -----------------------------

class ContactEnergyAccountSensorBase(CoordinatorEntity, SensorEntity):
    """Base for account info sensors that read from coordinator data."""

    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator)
        self._contract_icp = contract_icp

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    @property
    def should_poll(self) -> bool:
        return False

    def _get_account_data(self) -> dict[str, Any]:
        data = getattr(self.coordinator, "data", None) or {}
        account_details = data.get("account_details", {}) if isinstance(data, dict) else {}
        if not account_details:
            _LOGGER.debug("No account_details found in coordinator data for %s. Data keys: %s", 
                         self._contract_icp, list(data.keys()) if isinstance(data, dict) else "Not a dict")
        return account_details

    def _get_contract_data(self) -> dict[str, Any]:
        account = self._get_account_data()
        contracts = account.get("contracts", []) or []
        _LOGGER.debug("Found %d contracts in account data for %s", len(contracts), self._contract_icp)
        
        for c in contracts:
            contract_icp = c.get("icp")
            _LOGGER.debug("Checking contract with ICP: %s (looking for %s)", contract_icp, self._contract_icp)
            if contract_icp == self._contract_icp:
                _LOGGER.debug("Found matching contract for %s with keys: %s", self._contract_icp, list(c.keys()))
                return c
        
        _LOGGER.debug("No matching contract found for ICP %s", self._contract_icp)
        return {}


class ContactEnergyAccountBalanceSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Account Balance ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_balance"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self) -> float | None:
        account_data = self._get_account_data()
        bal = account_data.get("accountBalance")
        _LOGGER.debug("Account balance sensor for %s: raw value=%s, account_data_keys=%s", 
                     self._contract_icp, bal, list(account_data.keys()) if account_data else "No data")
        try:
            return float(bal) if bal is not None else None
        except (ValueError, TypeError):
            _LOGGER.debug("Failed to convert account balance to float: %s", bal)
            return None


class ContactEnergyNextBillDateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Next Bill Date ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_next_bill_date"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> str | None:
        return self._get_account_data().get("nextBillDate")


class ContactEnergyCustomerNameSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Customer Name ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_customer_name"
        self._attr_icon = "mdi:account"

    @property
    def native_value(self) -> str | None:
        account_data = self._get_account_data()
        name = account_data.get("customerName")
        _LOGGER.debug("Customer name sensor for %s: value=%s", self._contract_icp, name)
        return name


class ContactEnergyPlanNameSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Plan Name ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_plan_name"
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> str | None:
        val = self._get_account_data().get("planName")
        if not val:
            val = self._get_contract_data().get("planDetails", {}).get("planName")
        return val


class ContactEnergyAccountNumberSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Account Number ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_account_number"
        self._attr_icon = "mdi:identifier"

    @property
    def native_value(self) -> str | None:
        return self._get_account_data().get("accountNumber")


class ContactEnergyServiceAddressSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Service Address ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_service_address"
        self._attr_icon = "mdi:home"

    @property
    def native_value(self) -> str | None:
        c = self._get_contract_data().get("serviceAddress")
        return c or self._get_account_data().get("serviceAddress")


class ContactEnergyMeterSerialSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Meter Serial ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_meter_serial"
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self) -> str | None:
        return self._get_contract_data().get("meterSerial")


class ContactEnergyNextReadDateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Next Read Date ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_next_read_date"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-arrow-right"

    @property
    def native_value(self) -> str | None:
        return self._get_contract_data().get("nextReadDate")


class ContactEnergyLastReadDateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Last Read Date ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_read_date"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-check"

    @property
    def native_value(self) -> str | None:
        return self._get_contract_data().get("lastReadDate")


class ContactEnergyDailyChargeRateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Daily Charge Rate ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_daily_charge_rate"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self) -> float | None:
        daily = self._get_contract_data().get("planDetails", {}).get("dailyCharge")
        try:
            return float(daily) if daily is not None else None
        except (ValueError, TypeError):
            return None


class ContactEnergyPeakRateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Peak Rate ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_peak_rate"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD/kWh"
        self._attr_icon = "mdi:trending-up"

    @property
    def native_value(self) -> float | None:
        peak = self._get_contract_data().get("planDetails", {}).get("unitRates", {}).get("peak")
        try:
            return float(peak) if peak is not None else None
        except (ValueError, TypeError):
            return None


class ContactEnergyOffPeakRateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Off Peak Rate ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_off_peak_rate"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD/kWh"
        self._attr_icon = "mdi:trending-down"

    @property
    def native_value(self) -> float | None:
        offp = self._get_contract_data().get("planDetails", {}).get("unitRates", {}).get("offPeak")
        try:
            return float(offp) if offp is not None else None
        except (ValueError, TypeError):
            return None


class ContactEnergyFreeHoursSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Free Hours ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_free_hours"
        self._attr_icon = "mdi:clock-time-eight"

    @property
    def native_value(self) -> str | None:
        return self._get_contract_data().get("planDetails", {}).get("unitRates", {}).get("freeHours")


class ContactEnergyLastPaymentSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Last Payment ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_payment"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:credit-card"

    @property
    def native_value(self) -> float | None:
        payments = self._get_account_data().get("recentPayments", []) or []
        if payments:
            amt = payments[0].get("amount")
            try:
                return float(amt) if amt is not None else None
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        payments = self._get_account_data().get("recentPayments", []) or []
        if payments:
            return {
                "date": payments[0].get("date"),
                "method": payments[0].get("method"),
            }
        return {}


class ContactEnergyEstimatedNextBillSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Estimated Next Bill ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_estimated_next_bill"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:receipt"

    @property
    def native_value(self) -> float | None:
        bills = self._get_account_data().get("upcomingBills", []) or []
        if bills:
            amt = bills[0].get("estimatedAmount")
            try:
                return float(amt) if amt is not None else None
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        bills = self._get_account_data().get("upcomingBills", []) or []
        if bills:
            return {"bill_date": bills[0].get("billDate")}
        return {}


# -----------------------------------------
# Convenience usage and cost sensors
# -----------------------------------------

class ContactEnergyConvenienceSensorBase(CoordinatorEntity, SensorEntity):
    """Base for convenience sensors that recompute on coordinator updates."""

    def __init__(self, coordinator: ContactEnergyCoordinator, account_id: str, contract_id: str, contract_icp: str) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._contract_id = contract_id
        self._contract_icp = contract_icp
        self._state = 0.0

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # initial compute after HA start (with ICP-based jitter to spread API calls across accounts)
        async def _delayed_recompute():
            import hashlib
            icp_hash = int(hashlib.md5(self._contract_icp.encode()).hexdigest()[:8], 16)
            base_delay = (icp_hash % 20) / 10.0  # 0-2 seconds based on ICP
            jitter = random.uniform(0.1, 1.5)  # Additional random jitter
            total_delay = base_delay + jitter
            
            try:
                await asyncio.sleep(total_delay)
            except Exception:  # noqa: BLE001
                pass
            await self._recompute()
        self.hass.async_create_task(_delayed_recompute())

    async def _recompute(self) -> None:
        start, end = self._date_range()
        kwh, cost, free_kwh = await self._get_usage_for_date_range(start, end)
        self._apply_values(kwh, cost, free_kwh)
        self.async_write_ha_state()

    def _apply_values(self, kwh: float, cost: float, free_kwh: float) -> None:
        # To be implemented by subclasses depending on metric
        pass

    def _date_range(self) -> tuple[date, date]:
        # To be implemented by subclasses
        return (datetime.now().date(), datetime.now().date())

    async def _get_usage_for_date_range(self, start_date: date, end_date: date) -> tuple[float, float, float]:
        total_kwh = 0.0
        total_cost = 0.0
        total_free_kwh = 0.0
        current = start_date
        while current <= end_date:
            try:
                resp = await self.coordinator.api.async_get_usage(
                    str(current.year), str(current.month), str(current.day), self._account_id, self._contract_id
                )
                if isinstance(resp, list):
                    for p in resp:
                        val = ContactEnergyUsageSensor._safe_float(p.get("value"))
                        cost = ContactEnergyUsageSensor._safe_float(p.get("dollarValue"))
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

    def _handle_coordinator_update(self) -> None:
        # Recompute on coordinator refresh
        self.hass.async_create_task(self._recompute())


class ContactEnergyTodayUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Today Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_today_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-today"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        return today, today

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyYesterdayUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Yesterday Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_yesterday_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-minus"

    def _date_range(self) -> tuple[date, date]:
        y = datetime.now().date() - timedelta(days=1)
        return y, y

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLast7DaysUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last 7 Days Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_7_days_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-week"

    def _date_range(self) -> tuple[date, date]:
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=6)
        return start, end

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLast30DaysUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last 30 Days Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_30_days_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-month"

    def _date_range(self) -> tuple[date, date]:
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=29)
        return start, end

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyCurrentMonthUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Current Month Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_current_month_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        start = today.replace(day=1)
        return start, today

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLastMonthUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last Month Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_month_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-arrow-left"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        first_current = today.replace(day=1)
        last_prev = first_current - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev, last_prev

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyTodayCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Today Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_today_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        t = datetime.now().date()
        return t, t

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyYesterdayCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Yesterday Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_yesterday_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        y = datetime.now().date() - timedelta(days=1)
        return y, y

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyCurrentMonthCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Current Month Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_current_month_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        start = today.replace(day=1)
        return start, today

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLastMonthCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last Month Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_month_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        first_current = today.replace(day=1)
        last_prev = first_current - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev, last_prev

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyTodayFreeUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Today Free Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_today_free_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:gift"

    def _date_range(self) -> tuple[date, date]:
        t = datetime.now().date()
        return t, t

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = free_kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyYesterdayFreeUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Yesterday Free Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_yesterday_free_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:gift"

    def _date_range(self) -> tuple[date, date]:
        y = datetime.now().date() - timedelta(days=1)
        return y, y

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = free_kwh

    @property
    def native_value(self) -> float:
        return self._state
