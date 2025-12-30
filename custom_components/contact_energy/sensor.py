"""Sensor platform for Contact Energy integration.

This module creates sensor entities for Contact Energy account information such as
current balance, amount due, and next billing date. Each sensor updates once per
day at approximately 01:00 AM.

Sensor naming follows the pattern: sensor.{entity_friendly_name}.{attribute_name}
"""

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

# Currency unit for New Zealand Dollar
CURRENCY_NZD = "NZD"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Set up Contact Energy sensor entities.

    Creates sensor entities for account information retrieved from the coordinator.
    Sensors include account balance, invoice details, and next billing information.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry for this integration.
        async_add_entities: Callback to add entities.
        discovery_info: Additional discovery information (unused).
    """
    coordinator: ContactEnergyCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    # Get account information from the config entry
    account_nickname = config_entry.data.get("account_nickname", "Unknown")
    icp = config_entry.data.get("icp", "Unknown")

    # Create a friendly entity name for the sensors
    # Format: Account Nickname (ICP)
    entity_name = f"{account_nickname} ({icp})"

    entities = [
        # Account Balance Sensors
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "current_balance"
        ),
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "prepay_debt_balance"
        ),
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "refund_eligible"
        ),
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "refund_max"
        ),
        # Invoice Sensors
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "amount_due"
        ),
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "amount_paid"
        ),
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "payment_due_date"
        ),
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "days_til_overdue"
        ),
        # Next Bill Sensors
        ContactEnergyNextBillSensor(
            coordinator, config_entry, entity_name, "next_bill_date"
        ),
        ContactEnergyNextBillSensor(
            coordinator, config_entry, entity_name, "days_until_bill"
        ),
        # Account Detail Sensors
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "correspondence_preference"
        ),
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "payment_method"
        ),
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "billing_frequency"
        ),
    ]

    async_add_entities(entities)


class ContactEnergyAccountBalanceSensor(CoordinatorEntity, SensorEntity):
    """Represents a Contact Energy account balance sensor.

    Provides access to account balance information such as current balance,
    prepay debt, and refund eligibility.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the balance sensor.

        Args:
            coordinator: The data coordinator.
            config_entry: The config entry.
            entity_name: The friendly name for the entity.
            attribute: The attribute to expose (current_balance, prepay_debt_balance, etc).
        """
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.entity_name = entity_name
        self.attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Map attributes to display names
        attribute_names = {
            "current_balance": "Current Balance",
            "prepay_debt_balance": "Prepay Debt Balance",
            "refund_eligible": "Refund Eligible",
            "refund_max": "Maximum Refund",
        }
        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"
        self._attr_unit_of_measurement = CURRENCY_NZD

    @property
    def state(self):
        """Return the current state (sensor value).

        Returns the account balance value for the specified attribute from the
        coordinator data.
        """
        if not self.coordinator.data:
            return None

        account_detail = self.coordinator.data.get("accountDetail", {})
        account_balance = account_detail.get("accountBalance", {})

        # Map attribute names to dictionary keys
        if self.attribute == "current_balance":
            # Return numeric value for math operations
            return float(account_balance.get("currentBalance", 0))
        elif self.attribute == "prepay_debt_balance":
            return float(account_balance.get("prepayDebtBalance", 0))
        elif self.attribute == "refund_eligible":
            # Boolean value
            return account_balance.get("refundEligible", False)
        elif self.attribute == "refund_max":
            return float(account_balance.get("refundMax", 0))

        return None


class ContactEnergyInvoiceSensor(CoordinatorEntity, SensorEntity):
    """Represents a Contact Energy invoice sensor.

    Provides access to invoice information such as amount due, amount paid,
    payment due date, and days until overdue.
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the invoice sensor.

        Args:
            coordinator: The data coordinator.
            config_entry: The config entry.
            entity_name: The friendly name for the entity.
            attribute: The attribute to expose (amount_due, amount_paid, etc).
        """
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.entity_name = entity_name
        self.attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Map attributes to display names and units
        attribute_config = {
            "amount_due": {
                "name": "Amount Due",
                "unit": CURRENCY_NZD,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            "amount_paid": {
                "name": "Amount Paid",
                "unit": CURRENCY_NZD,
                "state_class": SensorStateClass.MEASUREMENT,
            },
            "payment_due_date": {
                "name": "Payment Due Date",
                "unit": None,
                "state_class": None,
            },
            "days_til_overdue": {
                "name": "Days Until Overdue",
                "unit": None,
                "state_class": SensorStateClass.MEASUREMENT,
            },
        }

        config = attribute_config.get(attribute, {})
        self._attr_name = f"{entity_name} {config.get('name', attribute)}"
        self._attr_unit_of_measurement = config.get("unit")
        if config.get("state_class"):
            self._attr_state_class = config.get("state_class")

    @property
    def state(self):
        """Return the current state (sensor value).

        Returns the invoice information for the specified attribute.
        """
        if not self.coordinator.data:
            return None

        account_detail = self.coordinator.data.get("accountDetail", {})
        invoice = account_detail.get("invoice", {})

        if self.attribute == "amount_due":
            return float(invoice.get("amountDue", 0))
        elif self.attribute == "amount_paid":
            return float(invoice.get("amountPaid", 0))
        elif self.attribute == "payment_due_date":
            return invoice.get("paymentDueDate")
        elif self.attribute == "days_til_overdue":
            return invoice.get("daysTilOverdue")

        return None


class ContactEnergyNextBillSensor(CoordinatorEntity, SensorEntity):
    """Represents a Contact Energy next bill sensor.

    Provides access to next billing date and days until the next bill.
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the next bill sensor.

        Args:
            coordinator: The data coordinator.
            config_entry: The config entry.
            entity_name: The friendly name for the entity.
            attribute: The attribute to expose (next_bill_date, days_until_bill).
        """
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.entity_name = entity_name
        self.attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Map attributes to display names
        attribute_names = {
            "next_bill_date": "Next Bill Date",
            "days_until_bill": "Days Until Next Bill",
        }
        name = attribute_names.get(attribute, attribute)
        self._attr_name = f"{entity_name} {name}"

        if attribute == "days_until_bill":
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self):
        """Return the current state (sensor value).

        Returns the next bill information for the specified attribute.
        """
        if not self.coordinator.data:
            return None

        account_detail = self.coordinator.data.get("accountDetail", {})
        next_bill = account_detail.get("nextBill", {})

        if self.attribute == "next_bill_date":
            return next_bill.get("date")
        elif self.attribute == "days_until_bill":
            return next_bill.get("daysUntilBill")

        return None


class ContactEnergyAccountDetailSensor(CoordinatorEntity, SensorEntity):
    """Represents a Contact Energy account detail sensor.

    Provides access to account settings such as correspondence preference,
    payment method, and billing frequency.
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the account detail sensor.

        Args:
            coordinator: The data coordinator.
            config_entry: The config entry.
            entity_name: The friendly name for the entity.
            attribute: The attribute to expose (correspondence_preference, payment_method, etc).
        """
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.entity_name = entity_name
        self.attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Map attributes to display names
        attribute_names = {
            "correspondence_preference": "Correspondence Preference",
            "payment_method": "Payment Method",
            "billing_frequency": "Billing Frequency",
        }
        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"

    @property
    def state(self):
        """Return the current state (sensor value).

        Returns the account detail for the specified attribute.
        """
        if not self.coordinator.data:
            return None

        account_detail = self.coordinator.data.get("accountDetail", {})

        if self.attribute == "correspondence_preference":
            return account_detail.get("correspondencePreference")
        elif self.attribute == "payment_method":
            return account_detail.get("paymentMethod")
        elif self.attribute == "billing_frequency":
            return account_detail.get("billingFrequency")

        return None
