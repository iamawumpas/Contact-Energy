"""Account sensor entities for Contact Energy integration.

This module provides sensor entities for account data including balance,
invoices, next bill, and account details using the v2.0.0 architecture.

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..coordinators.account_coordinator import AccountCoordinator
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Currency unit for New Zealand Dollar
CURRENCY_NZD = "NZD"


class AccountBalanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account balance information.

    Provides access to balance data such as current balance, prepay debt,
    and refund eligibility from the AccountCoordinator.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the balance sensor.

        Args:
            coordinator: Account data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            attribute: Balance attribute to expose
        """
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Map attributes to display names
        attribute_names = {
            "current_balance": "Current Balance",
            "prepay_debt_balance": "Prepay Debt Balance",
            "refund_eligible": "Refund Eligible",
            "refund_max": "Maximum Refund",
        }
        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"
        self._attr_unit_of_measurement = CURRENCY_NZD
        self._attr_icon = "mdi:currency-usd"

    @property
    def state(self) -> float | bool | None:
        """Return the current state.

        Returns:
            Balance value or None if not available
        """
        if not self.coordinator.data:
            return None

        balance = self.coordinator.get_balance()
        if not balance:
            return None

        # Map attribute names to dictionary keys
        if self._attribute == "current_balance":
            return float(balance.get("currentBalance", 0))
        elif self._attribute == "prepay_debt_balance":
            return float(balance.get("prepayDebtBalance", 0))
        elif self._attribute == "refund_eligible":
            return balance.get("refundEligible", False)
        elif self._attribute == "refund_max":
            return float(balance.get("refundMax", 0))

        return None


class InvoiceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for invoice information.

    Provides access to invoice data such as amount due, amount paid,
    payment due date, and days until overdue.
    """

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the invoice sensor.

        Args:
            coordinator: Account data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            attribute: Invoice attribute to expose
        """
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Map attributes to display names and units
        attribute_config = {
            "amount_due": {
                "name": "Amount Due",
                "unit": CURRENCY_NZD,
                "state_class": SensorStateClass.MEASUREMENT,
                "icon": "mdi:currency-usd",
            },
            "amount_paid": {
                "name": "Amount Paid",
                "unit": CURRENCY_NZD,
                "state_class": SensorStateClass.MEASUREMENT,
                "icon": "mdi:currency-usd",
            },
            "discount_total": {
                "name": "Discount Total",
                "unit": CURRENCY_NZD,
                "state_class": SensorStateClass.MEASUREMENT,
                "icon": "mdi:currency-usd",
            },
            "payment_due_date": {
                "name": "Payment Due Date",
                "unit": None,
                "state_class": None,
                "icon": "mdi:calendar",
            },
            "days_til_overdue": {
                "name": "Days Until Overdue",
                "unit": "days",
                "state_class": SensorStateClass.MEASUREMENT,
                "icon": "mdi:calendar-clock",
            },
        }

        config = attribute_config.get(attribute, {})
        self._attr_name = f"{entity_name} {config.get('name', attribute)}"
        self._attr_unit_of_measurement = config.get("unit")
        self._attr_icon = config.get("icon", "mdi:file-document")
        if config.get("state_class"):
            self._attr_state_class = config.get("state_class")

    @property
    def state(self) -> float | str | int | None:
        """Return the current state.

        Returns:
            Invoice value or None if not available
        """
        if not self.coordinator.data:
            return None

        invoice = self.coordinator.get_invoice()
        if not invoice:
            return None

        if self._attribute == "amount_due":
            return float(invoice.get("amountDue", 0))
        elif self._attribute == "amount_paid":
            return float(invoice.get("amountPaid", 0))
        elif self._attribute == "discount_total":
            return float(invoice.get("discountTotal", 0))
        elif self._attribute == "payment_due_date":
            return invoice.get("paymentDueDate")
        elif self._attribute == "days_til_overdue":
            due_date_str = invoice.get("paymentDueDate")
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                    now = datetime.now(due_date.tzinfo)
                    delta = (due_date - now).days
                    return max(0, delta)
                except (ValueError, TypeError):
                    return None
            return None

        return None


class NextBillSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next bill information.

    Provides access to next bill data such as next bill date and days until bill.
    """

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the next bill sensor.

        Args:
            coordinator: Account data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            attribute: Next bill attribute to expose
        """
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Map attributes to display names
        attribute_config = {
            "next_bill_date": {
                "name": "Next Bill Date",
                "unit": None,
                "state_class": None,
                "icon": "mdi:calendar",
            },
            "days_until_bill": {
                "name": "Days Until Bill",
                "unit": "days",
                "state_class": SensorStateClass.MEASUREMENT,
                "icon": "mdi:calendar-clock",
            },
        }

        config = attribute_config.get(attribute, {})
        self._attr_name = f"{entity_name} {config.get('name', attribute)}"
        self._attr_unit_of_measurement = config.get("unit")
        self._attr_icon = config.get("icon", "mdi:calendar")
        if config.get("state_class"):
            self._attr_state_class = config.get("state_class")

    @property
    def state(self) -> str | int | None:
        """Return the current state.

        Returns:
            Next bill value or None if not available
        """
        if not self.coordinator.data:
            return None

        next_bill = self.coordinator.get_next_bill()
        if not next_bill:
            return None

        if self._attribute == "next_bill_date":
            return next_bill.get("nextBillDate")
        elif self._attribute == "days_until_bill":
            bill_date_str = next_bill.get("nextBillDate")
            if bill_date_str:
                try:
                    bill_date = datetime.fromisoformat(bill_date_str.replace("Z", "+00:00"))
                    now = datetime.now(bill_date.tzinfo)
                    delta = (bill_date - now).days
                    return max(0, delta)
                except (ValueError, TypeError):
                    return None
            return None

        return None


class AccountDetailSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account detail information.

    Provides access to account details such as correspondence preference,
    payment method, billing frequency, and contract information.
    """

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the account detail sensor.

        Args:
            coordinator: Account data coordinator
            entry_id: Config entry ID
            entity_name: Friendly name for the entity
            attribute: Account detail attribute to expose
        """
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._attribute = attribute
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Map attributes to display names
        attribute_names = {
            "correspondence_preference": "Correspondence Preference",
            "payment_method": "Payment Method",
            "billing_frequency": "Billing Frequency",
            "account_nickname": "Account Nickname",
            "icp": "ICP",
            "address": "Address",
            "product_name": "Product Name",
            "contract_type": "Contract Type",
            "contract_status": "Contract Status",
            "is_direct_debit": "Direct Debit",
            "is_smooth_pay": "Smooth Pay",
            "is_prepay": "Prepay",
        }

        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"
        self._attr_icon = "mdi:information"

    @property
    def state(self) -> str | bool | None:
        """Return the current state.

        Returns:
            Account detail value or None if not available
        """
        if not self.coordinator.data:
            return None

        account_data = self.coordinator.data
        account_detail = account_data.get("accountDetail", {})
        contracts = self.coordinator.get_contracts()

        # Handle simple account detail fields
        if self._attribute == "correspondence_preference":
            return account_detail.get("correspondencePreference")
        elif self._attribute == "payment_method":
            return account_detail.get("paymentMethod")
        elif self._attribute == "billing_frequency":
            return account_detail.get("billingFrequency")
        elif self._attribute == "account_nickname":
            return account_detail.get("nickname")

        # Handle contract-related fields
        if contracts:
            contract = contracts[0]  # Use first contract
            if self._attribute == "icp":
                return contract.get("icp")
            elif self._attribute == "address":
                return contract.get("address")
            elif self._attribute == "product_name":
                return contract.get("productName")
            elif self._attribute == "contract_type":
                return contract.get("contractType")
            elif self._attribute == "contract_status":
                return contract.get("status")
            elif self._attribute == "is_direct_debit":
                return contract.get("isDirectDebit", False)
            elif self._attribute == "is_smooth_pay":
                return contract.get("isSmoothPay", False)
            elif self._attribute == "is_prepay":
                return contract.get("isPrepay", False)

        return None
