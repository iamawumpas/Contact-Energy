"""Account sensor entities for Contact Energy integration.

=== WHAT THIS DOES ===
This module defines Home Assistant sensor entities that turn Contact Energy
account information into readable values inside Home Assistant.

These sensors expose information such as:
- current account balance
- prepay debt balance
- refund eligibility
- invoice amounts and due dates
- next bill timing
- account and contract details

Each sensor reads data from the AccountCoordinator, which is the part of the
integration responsible for fetching and caching account data from the API.

=== FOR NON-CODERS ===
A few important words explained simply:
- Home Assistant: the smart-home platform running this integration.
- entity: one "thing" Home Assistant knows about, such as a light, switch,
  or sensor.
- sensor: an entity whose job is to report information, like a thermometer or
  balance display.
- state: the main value the sensor currently shows.
- attributes: extra details attached to the sensor in addition to the main
  state.

Think of these classes like different labels on a dashboard:
- one label shows your balance
- another shows your invoice amount
- another shows your next bill date
- another shows account details like payment method

Version: 2.0.0
"""
# This import lets us use modern Python type hints without worrying about
# runtime evaluation order in older Python versions.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging records what this module is doing so developers can diagnose issues.
import logging

# datetime is used when calculating how many days remain until a due date or bill date.
from datetime import datetime

# Any is used in type hints when a dictionary may contain mixed value types.
from typing import Any

# SensorEntity is Home Assistant's base class for sensor entities.
# SensorStateClass tells Home Assistant how the sensor's value behaves over time.
from homeassistant.components.sensor import SensorEntity, SensorStateClass

# CoordinatorEntity connects a sensor to a DataUpdateCoordinator so the entity
# automatically stays in sync with shared fetched data.
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# AccountCoordinator is this integration's account-data manager that fetches
# and stores account information from Contact Energy.
from ..coordinators.account_coordinator import AccountCoordinator

# DOMAIN is the integration's unique identifier used for stable entity IDs.
from ..const import DOMAIN

# ============================================================================
# LOGGER SETUP
# ============================================================================
# Create a module-specific logger so messages from this file are easy to find.
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================
# Store the currency code in one place so balance-style sensors stay consistent.
CURRENCY_NZD = "NZD"


# ============================================================================
# ACCOUNT BALANCE SENSOR
# ============================================================================
class AccountBalanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account balance information.

    === WHAT THIS DOES ===
    This sensor exposes a single balance-related value from the account data.
    Different instances of this class are created for different balance fields,
    such as current balance or maximum refund.

    === FOR NON-CODERS ===
    This is like one small dashboard tile. The tile does not hold all account
    information. Instead, each tile picks one specific value to show.

    Why this class exists:
    - to turn raw API balance data into a Home Assistant sensor
    - to give each balance field its own name, unit, and icon
    - to let dashboards, automations, and voice assistants use the value
    """

    # Tell Home Assistant this sensor reports a current measured value.
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the balance sensor.

        === WHAT THIS DOES ===
        This constructor prepares one balance sensor instance and teaches it
        which specific balance field it should show.

        === FOR NON-CODERS ===
        When Home Assistant creates the sensor, this setup method gives the
        sensor its identity card:
        - where to get data from
        - what to call itself
        - which exact balance value it represents

        Step by step:
        1. connect the sensor to the shared coordinator
        2. store identifying information
        3. build a unique ID so Home Assistant can track this sensor forever
        4. choose a friendly display name, unit, and icon
        """
        # Ask the parent CoordinatorEntity class to connect this sensor to the
        # shared account coordinator.
        super().__init__(coordinator)

        # Store the configuration entry ID so the entity stays unique even if a
        # user has multiple integration entries.
        self._entry_id = entry_id

        # Store the friendly device/account name that will appear in UI labels.
        self._entity_name = entity_name

        # Store which balance field this specific sensor instance should expose.
        self._attribute = attribute

        # Build a stable unique ID so Home Assistant can distinguish this sensor
        # from every other entity in the system.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Map internal attribute names to user-friendly labels.
        attribute_names = {
            "current_balance": "Current Balance",
            "prepay_debt_balance": "Prepay Debt Balance",
            "refund_eligible": "Refund Eligible",
            "refund_max": "Maximum Refund",
        }

        # Combine the account name with the field label to create the sensor's
        # visible display name in Home Assistant.
        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"

        # Mark the currency-based unit used by these balance values.
        self._attr_unit_of_measurement = CURRENCY_NZD

        # Choose an icon that visually suggests money/balance information.
        self._attr_icon = "mdi:currency-usd"

    @property
    def state(self) -> float | bool | None:
        """Return the current state.

        === WHAT THIS DOES ===
        This property reads the latest account data and returns the one balance
        value this sensor is responsible for showing.

        === FOR NON-CODERS ===
        Home Assistant repeatedly asks a sensor, "What value should I show right
        now?" This property answers that question.

        Step by step:
        1. make sure coordinator data exists
        2. get the balance section from the coordinator
        3. pick the requested field
        4. convert it into the right Python type
        5. return None if the value cannot be determined
        """
        # If no coordinator data has been fetched yet, there is nothing useful
        # to display, so we tell Home Assistant the sensor is currently unknown.
        if not self.coordinator.data:
            return None

        # Ask the coordinator for just the balance section of the account data.
        balance = self.coordinator.get_balance()

        # If the balance block is missing or empty, we again return unknown.
        if not balance:
            return None

        # If this sensor represents the current balance, read the API field and
        # convert it to float so Home Assistant treats it as a numeric value.
        if self._attribute == "current_balance":
            return float(balance.get("currentBalance", 0))

        # If this sensor represents prepay debt, read that specific field.
        if self._attribute == "prepay_debt_balance":
            return float(balance.get("prepayDebtBalance", 0))

        # If this sensor represents whether a refund is allowed, return a true/
        # false value instead of a number.
        if self._attribute == "refund_eligible":
            return balance.get("refundEligible", False)

        # If this sensor represents the maximum refund amount, return that as money.
        if self._attribute == "refund_max":
            return float(balance.get("refundMax", 0))

        # If the attribute name is not one of the supported options, show unknown.
        return None


# ============================================================================
# INVOICE SENSOR
# ============================================================================
class InvoiceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for invoice information.

    === WHAT THIS DOES ===
    This sensor exposes one invoice-related value, such as amount due, amount
    paid, payment due date, or days until overdue.

    === FOR NON-CODERS ===
    Think of this as one billing tile on a dashboard. One copy of the class may
    show "Amount Due" while another copy shows "Days Until Overdue".

    Why this class exists:
    - to present invoice values as Home Assistant sensors
    - to convert raw API fields into cleaner display values
    - to support automations based on invoice timing and amounts
    """

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the invoice sensor.

        === WHAT THIS DOES ===
        This constructor sets up one invoice sensor and configures how it should
        be shown in Home Assistant.

        === FOR NON-CODERS ===
        This is the setup checklist for an invoice tile:
        - connect to the shared account data
        - remember which invoice fact to show
        - choose the right label, icon, and measurement unit
        """
        # Connect this sensor to the shared account coordinator.
        super().__init__(coordinator)

        # Save the integration entry identifier for uniqueness.
        self._entry_id = entry_id

        # Save the base display name used in the Home Assistant UI.
        self._entity_name = entity_name

        # Save which invoice field this instance should expose.
        self._attribute = attribute

        # Build the entity's stable unique ID.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Describe how each supported invoice attribute should look in the UI.
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

        # Pull the display configuration for the requested attribute.
        config = attribute_config.get(attribute, {})

        # Create the user-visible entity name.
        self._attr_name = f"{entity_name} {config.get('name', attribute)}"

        # Apply the unit, such as NZD or days, when appropriate.
        self._attr_unit_of_measurement = config.get("unit")

        # Apply the icon chosen for this invoice field.
        self._attr_icon = config.get("icon", "mdi:file-document")

        # Only set state_class when the chosen field is a measured numeric value.
        if config.get("state_class"):
            self._attr_state_class = config.get("state_class")

    @property
    def state(self) -> float | str | int | None:
        """Return the current state.

        === WHAT THIS DOES ===
        This property returns the invoice value that matches this sensor's
        configured attribute.

        === FOR NON-CODERS ===
        The same class can represent several invoice facts. This method checks
        which fact this specific sensor was assigned, then returns that value.
        """
        # If the coordinator has no data yet, we cannot show an invoice value.
        if not self.coordinator.data:
            return None

        # Ask the coordinator for the invoice portion of the account response.
        invoice = self.coordinator.get_invoice()

        # If no invoice block exists, show the sensor as unknown.
        if not invoice:
            return None

        # Return the amount currently due, as a numeric currency value.
        if self._attribute == "amount_due":
            return float(invoice.get("amountDue", 0))

        # Return the amount already paid toward the invoice.
        if self._attribute == "amount_paid":
            return float(invoice.get("amountPaid", 0))

        # Return the total discount amount applied to the invoice.
        if self._attribute == "discount_total":
            return float(invoice.get("discountTotal", 0))

        # Return the raw due date string for date-display style sensors.
        if self._attribute == "payment_due_date":
            return invoice.get("paymentDueDate")

        # Calculate how many whole days remain before the invoice becomes overdue.
        if self._attribute == "days_til_overdue":
            # Read the due date string from the invoice block.
            due_date_str = invoice.get("paymentDueDate")

            # Only continue if a due date value actually exists.
            if due_date_str:
                try:
                    # Convert the API's ISO timestamp text into a real datetime.
                    due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))

                    # Get the current time in the same timezone as the due date.
                    now = datetime.now(due_date.tzinfo)

                    # Subtract "now" from the due date to get the remaining days.
                    delta = (due_date - now).days

                    # Never return a negative number; once overdue, show 0 days left.
                    return max(0, delta)
                except (ValueError, TypeError):
                    # If the API returned a malformed date, avoid crashing and show unknown.
                    return None

            # If no due date string exists at all, show unknown.
            return None

        # Any unsupported attribute falls back to unknown.
        return None


# ============================================================================
# NEXT BILL SENSOR
# ============================================================================
class NextBillSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next bill information.

    === WHAT THIS DOES ===
    This sensor exposes data about the next expected bill, including the bill
    date itself or how many days remain until that bill.

    === FOR NON-CODERS ===
    This helps Home Assistant show upcoming billing information in a simple,
    automation-friendly way.
    """

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the next bill sensor.

        === WHAT THIS DOES ===
        This constructor sets up one next-bill sensor and decides whether it
        should display the bill date or countdown value.
        """
        # Connect this entity to the shared account coordinator.
        super().__init__(coordinator)

        # Store identifying information used throughout the entity lifecycle.
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._attribute = attribute

        # Build a unique ID so Home Assistant can persist this entity reliably.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Define the Home Assistant presentation settings for each field type.
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

        # Look up the formatting rules for the chosen field.
        config = attribute_config.get(attribute, {})

        # Set the display name users will see in Home Assistant.
        self._attr_name = f"{entity_name} {config.get('name', attribute)}"

        # Set the unit if the field is numeric.
        self._attr_unit_of_measurement = config.get("unit")

        # Set an icon that matches the bill-date concept.
        self._attr_icon = config.get("icon", "mdi:calendar")

        # Only mark the sensor as a measured value when the config says so.
        if config.get("state_class"):
            self._attr_state_class = config.get("state_class")

    @property
    def state(self) -> str | int | None:
        """Return the current state.

        === WHAT THIS DOES ===
        This property returns either the next bill date string or a calculated
        countdown in days.
        """
        # Without coordinator data there is no next-bill information to show.
        if not self.coordinator.data:
            return None

        # Retrieve the next-bill section from the account coordinator.
        next_bill = self.coordinator.get_next_bill()

        # If Contact Energy did not provide a next-bill block, show unknown.
        if not next_bill:
            return None

        # For the date-style sensor, return the raw bill date value directly.
        if self._attribute == "next_bill_date":
            return next_bill.get("nextBillDate")

        # For the countdown-style sensor, compute days remaining until the bill.
        if self._attribute == "days_until_bill":
            # Read the bill date text from the API response.
            bill_date_str = next_bill.get("nextBillDate")

            # Only attempt date math if the bill date is present.
            if bill_date_str:
                try:
                    # Parse the ISO date string into a datetime object.
                    bill_date = datetime.fromisoformat(bill_date_str.replace("Z", "+00:00"))

                    # Capture the current time in the same timezone for fair comparison.
                    now = datetime.now(bill_date.tzinfo)

                    # Compute whole days remaining until the next bill.
                    delta = (bill_date - now).days

                    # Keep the countdown non-negative for cleaner dashboards.
                    return max(0, delta)
                except (ValueError, TypeError):
                    # If parsing fails, return unknown rather than crashing.
                    return None

            # No bill date means we cannot compute the countdown.
            return None

        # Unknown attribute names should produce an unknown sensor state.
        return None


# ============================================================================
# ACCOUNT DETAIL SENSOR
# ============================================================================
class AccountDetailSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account detail information.

    === WHAT THIS DOES ===
    This sensor exposes account-detail or contract-detail text/boolean values,
    such as correspondence preference, payment method, ICP, address, or plan flags.

    === FOR NON-CODERS ===
    Some account information is not a number like balance or usage. This class
    handles the descriptive facts about the account and contract.
    """

    def __init__(
        self,
        coordinator: AccountCoordinator,
        entry_id: str,
        entity_name: str,
        attribute: str,
    ):
        """Initialize the account detail sensor.

        === WHAT THIS DOES ===
        This constructor prepares a sensor that will expose one descriptive
        account or contract field.
        """
        # Connect the entity to the shared coordinator.
        super().__init__(coordinator)

        # Store the identifiers and field name this sensor represents.
        self._entry_id = entry_id
        self._entity_name = entity_name
        self._attribute = attribute

        # Build the sensor's stable unique ID.
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{attribute}"

        # Map internal attribute identifiers to friendlier labels for the UI.
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

        # Set the visible display name shown in Home Assistant.
        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"

        # Use a general information icon because these sensors show descriptive metadata.
        self._attr_icon = "mdi:information"

    @property
    def state(self) -> str | bool | None:
        """Return the current state.

        === WHAT THIS DOES ===
        This property looks at the latest account response and returns the one
        descriptive detail assigned to this sensor.

        === FOR NON-CODERS ===
        This is the part that answers, "What should this information tile show
        right now?"
        """
        # If the coordinator has not loaded data yet, nothing can be shown.
        if not self.coordinator.data:
            return None

        # Access the full account payload stored by the coordinator.
        account_data = self.coordinator.data

        # Pull out the nested account-detail block, or an empty dictionary if missing.
        account_detail = account_data.get("accountDetail", {})

        # Ask the coordinator for the list of contracts linked to the account.
        contracts = self.coordinator.get_contracts()

        # Handle fields that live directly inside the accountDetail block.
        if self._attribute == "correspondence_preference":
            return account_detail.get("correspondencePreference")
        if self._attribute == "payment_method":
            return account_detail.get("paymentMethod")
        if self._attribute == "billing_frequency":
            return account_detail.get("billingFrequency")
        if self._attribute == "account_nickname":
            return account_detail.get("nickname")

        # Some fields live inside the contract list instead of accountDetail.
        # We use the first contract because the original integration logic expects
        # a primary contract in position 0.
        if contracts:
            contract = contracts[0]

            # Return the installation control point identifier.
            if self._attribute == "icp":
                return contract.get("icp")

            # Return the service address for the contract.
            if self._attribute == "address":
                return contract.get("address")

            # Return the marketing/product plan name.
            if self._attribute == "product_name":
                return contract.get("productName")

            # Return the contract type text.
            if self._attribute == "contract_type":
                return contract.get("contractType")

            # Return the contract status, such as active/inactive.
            if self._attribute == "contract_status":
                return contract.get("status")

            # Return whether direct debit is enabled for the contract.
            if self._attribute == "is_direct_debit":
                return contract.get("isDirectDebit", False)

            # Return whether SmoothPay is enabled.
            if self._attribute == "is_smooth_pay":
                return contract.get("isSmoothPay", False)

            # Return whether the account is a prepay contract.
            if self._attribute == "is_prepay":
                return contract.get("isPrepay", False)

        # If no matching field was found, show the sensor as unknown.
        return None
