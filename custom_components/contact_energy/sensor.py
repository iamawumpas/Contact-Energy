"""Contact Energy sensor platform."""
import logging
from datetime import datetime, date
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_DOLLAR,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics

from .const import (
    DOMAIN,
    NAME,
    CONF_CONTRACT_ICP,
    SENSOR_ACCOUNT_BALANCE_NAME,
    SENSOR_NEXT_BILL_AMOUNT_NAME,
    SENSOR_NEXT_BILL_DATE_NAME,
    SENSOR_PAYMENT_DUE_NAME,
    SENSOR_PAYMENT_DUE_DATE_NAME,
    SENSOR_PREVIOUS_READING_DATE_NAME,
    SENSOR_NEXT_READING_DATE_NAME,
    SENSOR_ENERGY_CONSUMPTION_NAME,
    SENSOR_ENERGY_COST_NAME,
    SENSOR_FREE_ENERGY_CONSUMPTION_NAME,
)
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Contact Energy sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    icp = entry.data[CONF_CONTRACT_ICP]

    # Account sensors
    account_sensors = [
        ContactEnergyAccountSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_ACCOUNT_BALANCE_NAME,
            value_key="accountBalance",
            device_class=SensorDeviceClass.MONETARY,
            unit="NZD",
        ),
        ContactEnergyAccountSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_NEXT_BILL_AMOUNT_NAME,
            value_key="nextBillAmount",
            device_class=SensorDeviceClass.MONETARY,
            unit="NZD",
        ),
        ContactEnergyAccountSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_NEXT_BILL_DATE_NAME,
            value_key="nextBillDate",
            device_class=SensorDeviceClass.DATE,
        ),
        ContactEnergyAccountSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_PAYMENT_DUE_NAME,
            value_key="paymentDue",
            device_class=SensorDeviceClass.MONETARY,
            unit="NZD",
        ),
        ContactEnergyAccountSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_PAYMENT_DUE_DATE_NAME,
            value_key="paymentDueDate",
            device_class=SensorDeviceClass.DATE,
        ),
        ContactEnergyAccountSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_PREVIOUS_READING_DATE_NAME,
            value_key="previousReadingDate",
            device_class=SensorDeviceClass.DATE,
        ),
        ContactEnergyAccountSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_NEXT_READING_DATE_NAME,
            value_key="nextReadingDate",
            device_class=SensorDeviceClass.DATE,
        ),
    ]

    # Usage sensors (with statistics)
    usage_sensors = [
        ContactEnergyUsageSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_ENERGY_CONSUMPTION_NAME,
            statistics_type="energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        ContactEnergyUsageSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_ENERGY_COST_NAME,
            statistics_type="cost",
            unit="NZD",
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        ContactEnergyUsageSensor(
            coordinator=coordinator,
            icp=icp,
            name=SENSOR_FREE_ENERGY_CONSUMPTION_NAME,
            statistics_type="free_energy",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
    ]

    async_add_entities(account_sensors + usage_sensors, True)


class ContactEnergyBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Contact Energy sensors."""

    def __init__(self, coordinator: ContactEnergyCoordinator, icp: str, name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._icp = icp
        self._attr_name = f"{NAME} {name} ({icp})"
        self._attr_unique_id = f"{DOMAIN}_{icp}_{name.lower().replace(' ', '_')}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._icp)},
            "name": f"{NAME} ({self._icp})",
            "manufacturer": NAME,
            "model": "Smart Meter",
            "sw_version": "1.0.0",
        }


class ContactEnergyAccountSensor(ContactEnergyBaseSensor):
    """Sensor for Contact Energy account information."""

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        icp: str,
        name: str,
        value_key: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
    ) -> None:
        """Initialize the account sensor."""
        super().__init__(coordinator, icp, name)
        self._value_key = value_key
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data or "account" not in self.coordinator.data:
            return None

        account_data = self.coordinator.data["account"]
        
        # Extract value from nested account structure
        try:
            account_detail = account_data.get("accountDetail", {})
            
            # Handle different value paths
            if self._value_key == "accountBalance":
                return account_detail.get("accountBalance")
            elif self._value_key in ["nextBillAmount", "paymentDue"]:
                billing = account_detail.get("billing", {})
                return billing.get(self._value_key)
            elif self._value_key in ["nextBillDate", "paymentDueDate"]:
                billing = account_detail.get("billing", {})
                date_str = billing.get(self._value_key)
                return self._parse_date(date_str)
            elif self._value_key in ["previousReadingDate", "nextReadingDate"]:
                contracts = account_detail.get("contracts", [])
                if contracts and contracts[0].get("devices"):
                    devices = contracts[0]["devices"]
                    if devices and devices[0].get("registers"):
                        registers = devices[0]["registers"]
                        if registers:
                            date_str = registers[0].get(self._value_key)
                            return self._parse_date(date_str)
            
            return None
            
        except (KeyError, TypeError, IndexError):
            return None

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date string from Contact Energy API."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%d %b %Y").date()
        except (ValueError, TypeError):
            return None


class ContactEnergyUsageSensor(ContactEnergyBaseSensor):
    """Sensor for Contact Energy usage with statistics support."""

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        icp: str,
        name: str,
        statistics_type: str,
        unit: str,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
    ) -> None:
        """Initialize the usage sensor."""
        super().__init__(coordinator, icp, name)
        self._statistics_type = statistics_type
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._statistics_metadata = None
        self._last_statistics_update = None

    @property
    def native_value(self) -> float | None:
        """Return current period value."""
        if not self.coordinator.data or "usage" not in self.coordinator.data:
            return None

        usage_data = self.coordinator.data["usage"]
        
        if self._statistics_type == "energy":
            return usage_data.get("current_energy", 0.0)
        elif self._statistics_type == "cost":
            return usage_data.get("current_cost", 0.0)
        elif self._statistics_type == "free_energy":
            return usage_data.get("current_free_energy", 0.0)
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or "usage" not in self.coordinator.data:
            return {}

        usage_data = self.coordinator.data["usage"]
        
        attrs = {
            "last_updated": usage_data.get("last_updated"),
            "integration_version": "1.0.0",
        }
        
        # Add total values for reference
        if self._statistics_type == "energy":
            attrs.update({
                "total_energy": usage_data.get("total_energy", 0.0),
                "data_points": len(usage_data.get("new_data_points", [])),
            })
        elif self._statistics_type == "cost":
            attrs.update({
                "total_cost": usage_data.get("total_cost", 0.0),
                "currency": "NZD",
            })
        elif self._statistics_type == "free_energy":
            attrs.update({
                "total_free_energy": usage_data.get("total_free_energy", 0.0),
                "data_points": len([p for p in usage_data.get("new_data_points", []) if p["type"] == "free"]),
            })

        return attrs

    @callback
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Set up statistics metadata
        self._statistics_metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=f"{NAME} - {self._attr_name}",
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:{self._statistics_type}_{self._icp}",
            unit_of_measurement=self._attr_native_unit_of_measurement,
        )

    async def async_update(self) -> None:
        """Update the sensor and statistics."""
        await super().async_update()
        
        # Update statistics if we have new data
        if (self.coordinator.data and 
            "usage" in self.coordinator.data and 
            self._statistics_metadata):
            
            await self._async_update_statistics()

    async def _async_update_statistics(self) -> None:
        """Update Home Assistant statistics."""
        usage_data = self.coordinator.data["usage"]
        new_data_points = usage_data.get("new_data_points", [])
        
        if not new_data_points:
            return

        # Check if we've already processed this data
        last_updated = usage_data.get("last_updated")
        if (self._last_statistics_update and 
            last_updated == self._last_statistics_update):
            return

        # Filter data points for this sensor type
        if self._statistics_type == "energy":
            filtered_points = [p for p in new_data_points if p["type"] == "regular"]
            value_key = "energy"
        elif self._statistics_type == "cost":
            filtered_points = [p for p in new_data_points if p["type"] == "regular"]
            value_key = "cost"
        elif self._statistics_type == "free_energy":
            filtered_points = [p for p in new_data_points if p["type"] == "free"]
            value_key = "free_energy"
        else:
            return

        if not filtered_points:
            return

        # Convert to Home Assistant statistics format
        statistics = []
        running_sum = 0.0
        
        for point in filtered_points:
            running_sum += point.get(value_key, 0.0)
            
            # Create statistic data point
            stat_point = StatisticData(
                start=point["timestamp"],
                sum=running_sum,
            )
            statistics.append(stat_point)

        if statistics:
            # Add statistics to Home Assistant
            async_add_external_statistics(
                self.hass, 
                self._statistics_metadata, 
                statistics
            )
            
            self._last_statistics_update = last_updated
            
            _LOGGER.debug(
                "Added %s statistics points for %s (%s)",
                len(statistics),
                self._attr_name,
                self._statistics_type
            )