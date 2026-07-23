"""Sensor platform for Contact Energy integration.

=== WHAT THIS DOES ===
This module is the main "sensor registration" file for the Contact Energy
integration. Its job is to create Home Assistant sensor entities that turn raw
Contact Energy account data into readable values such as:
- current account balance
- invoice totals
- next bill timing
- account settings
- energy dashboard totals

The coordinator fetches account data once, stores it in memory, and every sensor
in this file reads the piece of that shared data that it cares about. That keeps
the integration efficient because Home Assistant gets many sensors without making
many duplicate API calls.

=== FOR NON-CODERS ===
If the Contact Energy API is the source of truth, this file is the translator
that turns that raw information into cards and values you can see inside Home
Assistant.

A few Home Assistant terms explained in plain language:
- "entity": one thing Home Assistant can track, show, and automate.
- "sensor": a type of entity whose main purpose is to show information.
- "state": the main value of a sensor, such as "$102.40" or "5 days".
- "attributes": extra details attached to a sensor in addition to its main value.
- "device_class": a label that tells Home Assistant what kind of data a sensor
  represents, such as energy, date, temperature, or money-like measurements.
- "state_class": a label that tells Home Assistant how values behave over time,
  for example whether a value is a point-in-time measurement or a running total.

Sensor names created here follow the pattern:
    <account nickname> (<ICP>) <sensor purpose>

That naming makes it easy for non-coders to tell which Contact Energy account a
sensor belongs to and what it shows.
"""

# ============================================================================
# IMPORTS - Every import below provides a Home Assistant building block or a
# support utility that this file needs in order to create and maintain sensors.
# ============================================================================

# logging records what this module is doing so problems can be diagnosed later.
import logging

# date is used when energy dashboard sensors need a safe fallback start date.
from datetime import date

# SensorDeviceClass tells Home Assistant what type of measurement a sensor holds.
from homeassistant.components.sensor import SensorDeviceClass

# SensorEntity is the base class for creating sensor entities in Home Assistant.
from homeassistant.components.sensor import SensorEntity

# SensorStateClass tells Home Assistant how a sensor's value behaves over time.
from homeassistant.components.sensor import SensorStateClass

# HomeAssistant is the core application object passed into setup functions.
from homeassistant.core import HomeAssistant

# callback marks lightweight functions that Home Assistant can call efficiently.
from homeassistant.core import callback

# UnitOfEnergy provides the official Home Assistant unit constant for kWh.
from homeassistant.const import UnitOfEnergy

# async_dispatcher_connect lets one part of the integration notify another.
from homeassistant.helpers.dispatcher import async_dispatcher_connect

# AddEntitiesCallback is the function Home Assistant gives us to register sensors.
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# ConfigType describes the stored configuration for this integration entry.
from homeassistant.helpers.typing import ConfigType

# DiscoveryInfoType is part of Home Assistant's setup function signature.
from homeassistant.helpers.typing import DiscoveryInfoType

# CoordinatorEntity links a sensor to a shared update coordinator automatically.
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# DOMAIN is the integration's unique identifier inside Home Assistant storage.
from .const import DOMAIN

# ContactEnergyCoordinator holds the latest Contact Energy account data snapshot.
from .coordinator import ContactEnergyCoordinator

# ContactEnergyUsageSensor exposes richer usage history for charts and analysis.
from .usage_sensor import ContactEnergyUsageSensor

# UsageCache stores processed usage totals for the energy dashboard sensors.
from .usage_cache import UsageCache

# ============================================================================
# LOGGER SETUP
# ============================================================================
# Create a logger dedicated to this file so log messages clearly show where they
# came from when a user or developer needs to troubleshoot sensor behaviour.
_LOGGER = logging.getLogger(__name__)

# Currency label used by balance and invoice sensors.
CURRENCY_NZD = "NZD"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Set up Contact Energy sensor entities.

    === WHAT THIS DOES ===
    This function is Home Assistant's entry point for this file. It runs when a
    Contact Energy config entry is loaded and creates every sensor entity that
    should appear for that account.

    === FOR NON-CODERS ===
    Think of this as the "opening checklist" for the integration:
    1. Find the shared account data manager (the coordinator).
    2. Build a human-friendly account name.
    3. Create one sensor object for each value we want to show.
    4. Hand all of those sensor objects to Home Assistant so they appear in the UI.

    Args:
        hass: The main Home Assistant application object.
        config_entry: Saved setup details for this Contact Energy account.
        async_add_entities: Home Assistant callback used to register new sensors.
        discovery_info: Optional discovery payload; unused in this integration.
    """
    # ========================================================================
    # STEP 1: Retrieve the shared coordinator for this specific config entry.
    # ========================================================================
    # The coordinator is the part of the integration that fetches Contact Energy
    # data once and stores the latest result in coordinator.data. Every sensor in
    # this file reads from that same shared snapshot.
    coordinator: ContactEnergyCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    # ========================================================================
    # STEP 2: Extract naming information saved during config flow setup.
    # ========================================================================
    # account_nickname is the user-friendly account label Contact Energy exposes.
    # We fall back to "Unknown" so sensor names remain readable even if the data
    # was not stored for some reason.
    account_nickname = config_entry.data.get("account_nickname", "Unknown")

    # ICP is the installation control point identifier for the property/service.
    # Including it in the name helps distinguish multiple Contact Energy accounts.
    icp = config_entry.data.get("icp", "Unknown")

    # contract_id is reused by usage and energy sensors that need contract-level
    # cache keys. A fallback value prevents crashes if setup data is incomplete.
    contract_id = config_entry.data.get("contract_id", "unknown")

    # ========================================================================
    # STEP 3: Build the shared friendly prefix used by all entities.
    # ========================================================================
    # Example result: "Home (0001234567ICP)".
    # Home Assistant will append each sensor's purpose after this prefix.
    entity_name = f"{account_nickname} ({icp})"

    # ========================================================================
    # STEP 4: Create every sensor entity for this Contact Energy account.
    # ========================================================================
    # Each object below represents one Home Assistant entity. We create separate
    # sensors instead of one giant object because Home Assistant works best when
    # each piece of information has its own searchable, automatable entity.
    entities = [
        # --------------------------------------------------------------------
        # ACCOUNT BALANCE SENSORS
        # These answer money-related questions such as:
        # - "How much is currently owed or in credit?"
        # - "Is a refund allowed?"
        # - "What is the maximum refund amount?"
        # --------------------------------------------------------------------
        # Shows the main live balance for the account.
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "current_balance"
        ),
        # Shows any debt still attached to a prepay account.
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "prepay_debt_balance"
        ),
        # Shows whether the account is currently eligible for a refund.
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "refund_eligible"
        ),
        # Shows the highest refund amount Contact Energy reports as available.
        ContactEnergyAccountBalanceSensor(
            coordinator, config_entry, entity_name, "refund_max"
        ),

        # --------------------------------------------------------------------
        # INVOICE SENSORS
        # These explain the current bill itself: what is due, what has already
        # been paid, when payment is due, and whether it is approaching overdue.
        # --------------------------------------------------------------------
        # Shows the amount still due on the current invoice.
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "amount_due"
        ),
        # Shows how much has already been paid toward the current invoice.
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "amount_paid"
        ),
        # Shows the date the current invoice must be paid by.
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "payment_due_date"
        ),
        # Shows how many days remain before the invoice becomes overdue.
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "days_til_overdue"
        ),
        # Shows the total discounts applied to the invoice.
        ContactEnergyInvoiceSensor(
            coordinator, config_entry, entity_name, "discount_total"
        ),

        # --------------------------------------------------------------------
        # NEXT BILL SENSORS
        # These provide forward-looking information so the user can see when the
        # next bill is expected and how far away it is.
        # --------------------------------------------------------------------
        # Shows the predicted date of the next bill.
        ContactEnergyNextBillSensor(
            coordinator, config_entry, entity_name, "next_bill_date"
        ),
        # Shows the countdown in days until that next bill arrives.
        ContactEnergyNextBillSensor(
            coordinator, config_entry, entity_name, "days_until_bill"
        ),

        # --------------------------------------------------------------------
        # ACCOUNT DETAIL SENSORS
        # These expose descriptive account settings that are useful for checking
        # configuration, contract type, and billing preferences inside HA.
        # --------------------------------------------------------------------
        # Shows how Contact Energy prefers to contact the customer.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "correspondence_preference"
        ),
        # Shows the payment method currently configured on the account.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "payment_method"
        ),
        # Shows whether billing happens weekly, monthly, or on another cadence.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "billing_frequency"
        ),
        # Repeats the account nickname as a visible sensor value.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "account_nickname"
        ),
        # Shows the contract ICP identifier as its own searchable entity.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "icp"
        ),
        # Shows the service address attached to the contract.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "address"
        ),
        # Shows the current Contact Energy product or plan name.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "product_name"
        ),
        # Shows the contract type, such as electricity or other service category.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "contract_type"
        ),
        # Shows whether the contract is active, ended, or in another status.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "contract_status"
        ),
        # Shows whether direct debit is enabled, translated into plain language.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "is_direct_debit"
        ),
        # Shows whether the account is on the SmoothPay billing option.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "is_smooth_pay"
        ),
        # Shows whether the account is a prepay account.
        ContactEnergyAccountDetailSensor(
            coordinator, config_entry, entity_name, "is_prepay"
        ),

        # --------------------------------------------------------------------
        # USAGE SENSOR
        # This exposes richer usage history from cached hourly/daily/monthly data
        # for graphing and deeper inspection in the Home Assistant UI.
        # --------------------------------------------------------------------
        ContactEnergyUsageSensor(
            coordinator,
            config_entry,
            entity_name,
            contract_id=contract_id,
        ),

        # --------------------------------------------------------------------
        # ENERGY DASHBOARD SENSORS
        # Home Assistant's Energy dashboard expects cumulative totals, not just a
        # single day's usage. We therefore create one total for paid energy and a
        # second total for free energy.
        # --------------------------------------------------------------------
        # Total paid kWh consumed since the sensor's established start date.
        ContactEnergyEnergySensor(
            coordinator,
            config_entry,
            entity_name,
            contract_id=contract_id,
            energy_kind="paid",
        ),
        # Total free kWh consumed since the sensor's established start date.
        ContactEnergyEnergySensor(
            coordinator,
            config_entry,
            entity_name,
            contract_id=contract_id,
            energy_kind="free",
        ),
    ]

    # ========================================================================
    # STEP 5: Hand the finished entity list to Home Assistant.
    # ========================================================================
    # After this call, Home Assistant takes responsibility for adding the sensors
    # to its entity registry, state machine, UI, and automation system.
    async_add_entities(entities)


class ContactEnergyAccountBalanceSensor(CoordinatorEntity, SensorEntity):
    """Represent one money-related account balance sensor.

    === WHAT THIS CLASS DOES ===
    This class creates a sensor that reads a single balance-related field from
    coordinator.data["accountDetail"]["accountBalance"]. Different instances of
    the class show different values such as current balance, refund eligibility,
    or prepay debt.

    === WHAT DATA IT DISPLAYS ===
    Depending on the attribute passed in, the sensor displays:
    - current_balance
    - prepay_debt_balance
    - refund_eligible
    - refund_max

    === FOR NON-CODERS ===
    One class can be reused to create several very similar sensors. Think of it
    like one label-maker machine printing different labels depending on which
    text you feed into it.
    """

    # Mark these values as measurements so Home Assistant treats them as current
    # point-in-time readings rather than ever-growing totals.
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize one balance sensor instance.

        === WHAT THIS DOES ===
        This constructor stores the shared dependencies and configures the sensor's
        visible name, unique ID, and currency unit.

        Args:
            coordinator: Shared data manager that keeps the latest API snapshot.
            config_entry: Stored account configuration for this integration entry.
            entity_name: Human-friendly account prefix shown in the entity name.
            attribute: Which balance field this instance should expose.
        """
        # Give CoordinatorEntity the coordinator so automatic updates work.
        super().__init__(coordinator)

        # Save the config entry in case future logic or HA internals need it.
        self.config_entry = config_entry

        # Save the shared display prefix used in the sensor's friendly name.
        self.entity_name = entity_name

        # Save which balance field this specific sensor instance should show.
        self.attribute = attribute

        # Build a stable unique ID so Home Assistant can remember this entity
        # even across restarts, renames, and registry updates.
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Translate internal attribute keys into human-readable sensor labels.
        attribute_names = {
            "current_balance": "Current Balance",
            "prepay_debt_balance": "Prepay Debt Balance",
            "refund_eligible": "Refund Eligible",
            "refund_max": "Maximum Refund",
        }

        # Combine the account prefix with the attribute label to produce names
        # such as "Home (ICP123) Current Balance".
        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"

        # These balance-related sensors are currency values or currency-like flags,
        # so we label them with the New Zealand Dollar unit where appropriate.
        self._attr_unit_of_measurement = CURRENCY_NZD

    @property
    def state(self):
        """Return the current sensor state.

        === WHAT THIS DOES ===
        Reads the latest shared account snapshot and returns the specific balance
        value requested by this sensor instance.

        === FOR NON-CODERS ===
        The "state" is the main value Home Assistant shows for a sensor. This is
        the number or text you see on a dashboard card or use in an automation.
        """
        # If the coordinator has not fetched data yet, there is nothing safe to
        # display, so Home Assistant should treat the sensor as temporarily empty.
        if not self.coordinator.data:
            return None

        # Pull out the top-level account detail section from the shared API data.
        account_detail = self.coordinator.data.get("accountDetail", {})

        # Pull out the nested balance section that contains all money fields.
        account_balance = account_detail.get("accountBalance", {})

        # Return the current balance as a float so Home Assistant can compare,
        # graph, and calculate with it reliably.
        if self.attribute == "current_balance":
            return float(account_balance.get("currentBalance", 0))

        # Return prepay debt as a float for the same numeric reasons.
        if self.attribute == "prepay_debt_balance":
            return float(account_balance.get("prepayDebtBalance", 0))

        # Return refund eligibility exactly as reported by the API.
        # This is a true/false style value rather than a currency amount.
        if self.attribute == "refund_eligible":
            return account_balance.get("refundEligible", False)

        # Return the maximum refund amount as a numeric value in NZD.
        if self.attribute == "refund_max":
            return float(account_balance.get("refundMax", 0))

        # If an unknown attribute key was somehow passed in, return no state
        # instead of risking a misleading value.
        return None


class ContactEnergyInvoiceSensor(CoordinatorEntity, SensorEntity):
    """Represent one current-invoice sensor.

    === WHAT THIS CLASS DOES ===
    This class exposes invoice-specific values from
    coordinator.data["accountDetail"]["invoice"]. Each instance points at one
    invoice field such as amount due, amount paid, due date, or overdue countdown.

    === WHAT DATA IT DISPLAYS ===
    Depending on the attribute passed in, the sensor displays:
    - amount_due
    - amount_paid
    - discount_total
    - payment_due_date
    - days_til_overdue

    === FOR NON-CODERS ===
    These sensors describe the bill you are dealing with right now. Some are
    money amounts, some are dates, and some are simple countdown values.
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize one invoice sensor instance.

        === WHAT THIS DOES ===
        Stores setup information and configures display metadata based on which
        invoice field this sensor will expose.

        Args:
            coordinator: Shared data manager holding the latest API response.
            config_entry: Stored configuration for this Contact Energy account.
            entity_name: Friendly account prefix used in Home Assistant names.
            attribute: Internal key naming the invoice field to expose.
        """
        # Register this sensor with the shared coordinator so it refreshes when
        # the API data changes.
        super().__init__(coordinator)

        # Keep a reference to the config entry for entity lifecycle consistency.
        self.config_entry = config_entry

        # Save the human-readable account prefix used in the display name.
        self.entity_name = entity_name

        # Save which invoice field this specific sensor should show.
        self.attribute = attribute

        # Build the entity's permanent unique identifier.
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Configuration for each invoice sensor variant.
        # - name: friendly label shown in Home Assistant
        # - unit: measurement unit if one applies
        # - state_class: how HA should interpret value behaviour over time
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
            "discount_total": {
                "name": "Discount Total",
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

        # Look up the metadata for the requested attribute, or use an empty
        # fallback dictionary if an unexpected key is provided.
        config = attribute_config.get(attribute, {})

        # Build the visible entity name users will see in the UI.
        self._attr_name = f"{entity_name} {config.get('name', attribute)}"

        # Assign the unit if this invoice field represents a measurable quantity.
        self._attr_unit_of_measurement = config.get("unit")

        # Only assign a state class when one is explicitly configured.
        if config.get("state_class"):
            self._attr_state_class = config.get("state_class")

    @property
    def state(self):
        """Return the current invoice-related state.

        === WHAT THIS DOES ===
        Reads the invoice section of the shared coordinator payload and extracts
        the specific value represented by this sensor instance.

        === FOR NON-CODERS ===
        Even though all these sensors read the same bill, each one returns only
        the single value it was created for.
        """
        # No coordinator data means we have nothing trustworthy to show yet.
        if not self.coordinator.data:
            return None

        # Extract the overall account detail block from the coordinator snapshot.
        account_detail = self.coordinator.data.get("accountDetail", {})

        # Extract just the invoice subsection that contains bill-specific fields.
        invoice = account_detail.get("invoice", {})

        # Convert money strings/numbers to float so HA sees proper numeric states.
        if self.attribute == "amount_due":
            return float(invoice.get("amountDue", 0))

        # Return the amount already paid toward the invoice as a numeric value.
        if self.attribute == "amount_paid":
            return float(invoice.get("amountPaid", 0))

        # Return the total invoice discount as a numeric value.
        if self.attribute == "discount_total":
            return float(invoice.get("discountTotal", 0))

        # Return the due date as provided by the API so it remains human readable.
        if self.attribute == "payment_due_date":
            return invoice.get("paymentDueDate")

        # Return the overdue countdown, with one business rule adjustment:
        # if the account balance is effectively settled, we report 0 days overdue
        # instead of continuing to count down on a bill that is already paid.
        if self.attribute == "days_til_overdue":
            # Read the raw countdown value from the invoice block first.
            raw_days = invoice.get("daysTilOverdue")

            # Read account balance data because whether a bill is still relevant
            # depends on whether money is actually still owed.
            account_balance = account_detail.get("accountBalance", {})

            # Convert to float and allow for empty/None values by falling back to 0.
            current_balance = float(account_balance.get("currentBalance", 0) or 0)

            # Treat tiny near-zero values as settled to avoid noisy rounding issues.
            if current_balance <= 0.01:
                return 0

            # If money is still owed, return the API's raw overdue countdown.
            return raw_days

        # Unknown invoice attribute requests should produce no state.
        return None


class ContactEnergyNextBillSensor(CoordinatorEntity, SensorEntity):
    """Represent one next-bill prediction sensor.

    === WHAT THIS CLASS DOES ===
    This class reads the API's next-bill prediction data so Home Assistant can
    show when the next bill is expected and how many days remain until it arrives.

    === WHAT DATA IT DISPLAYS ===
    Depending on the attribute passed in, the sensor displays:
    - next_bill_date
    - days_until_bill

    === FOR NON-CODERS ===
    These sensors are forward-looking. Instead of describing the bill you have
    now, they describe the bill Contact Energy expects you to receive next.
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize one next-bill sensor instance.

        === WHAT THIS DOES ===
        Stores shared references and sets the visible name based on whether this
        sensor shows a date or a day-countdown.

        Args:
            coordinator: Shared Contact Energy data manager.
            config_entry: Stored integration configuration.
            entity_name: Friendly account prefix shown in entity names.
            attribute: Internal key choosing which next-bill field to expose.
        """
        # Connect the entity to the coordinator-driven update system.
        super().__init__(coordinator)

        # Save core constructor inputs for later use.
        self.config_entry = config_entry
        self.entity_name = entity_name
        self.attribute = attribute

        # Build the permanent unique ID Home Assistant uses internally.
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Translate internal attribute keys into friendly UI labels.
        attribute_names = {
            "next_bill_date": "Next Bill Date",
            "days_until_bill": "Days Until Next Bill",
        }

        # Pick the display name for the chosen attribute.
        name = attribute_names.get(attribute, attribute)

        # Prefix the display name with the account identity.
        self._attr_name = f"{entity_name} {name}"

        # Only the countdown sensor behaves like a live measurement.
        if attribute == "days_until_bill":
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self):
        """Return the current next-bill state.

        === WHAT THIS DOES ===
        Extracts either the next bill date or the number of days until that bill
        from the coordinator's shared API data.
        """
        # If no API payload has been loaded yet, leave the sensor empty.
        if not self.coordinator.data:
            return None

        # Extract the general account detail structure from the coordinator cache.
        account_detail = self.coordinator.data.get("accountDetail", {})

        # Extract the nextBill section that contains future billing predictions.
        next_bill = account_detail.get("nextBill", {})

        # Return the predicted bill date exactly as supplied by the API.
        if self.attribute == "next_bill_date":
            return next_bill.get("date")

        # Return the day countdown as supplied by the API.
        if self.attribute == "days_until_bill":
            return next_bill.get("daysUntilBill")

        # Unknown attribute requests should safely produce no state.
        return None


class ContactEnergyEnergySensor(CoordinatorEntity, SensorEntity):
    """Represent a cumulative energy dashboard sensor.

    === WHAT THIS CLASS DOES ===
    This class creates the special sensors required for Home Assistant's Energy
    dashboard. Unlike ordinary usage sensors that may show point-in-time or daily
    values, these sensors expose running totals that only increase over time.

    === WHAT DATA IT DISPLAYS ===
    Depending on energy_kind, the sensor displays cumulative:
    - paid energy in kWh
    - free energy in kWh

    === FOR NON-CODERS ===
    The Energy dashboard wants a running odometer-style total, not just "today's
    usage". This class maintains that running total by reading cached usage data
    and summing it from a chosen start date.
    """

    # Tell Home Assistant this sensor represents energy data.
    _attr_device_class = SensorDeviceClass.ENERGY

    # Tell Home Assistant the value is a total that should keep increasing.
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    # Tell Home Assistant the measurement unit is kilowatt-hours.
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        contract_id: str,
        energy_kind: str,
    ) -> None:
        """Initialize one cumulative energy sensor.

        === WHAT THIS DOES ===
        Stores identifiers, creates a usage cache helper, and sets up metadata for
        either the paid-energy sensor or the free-energy sensor.

        Args:
            coordinator: Shared account coordinator for API updates.
            config_entry: Stored configuration for this integration entry.
            entity_name: Friendly account prefix used in entity display names.
            contract_id: Contract identifier used to look up cached usage data.
            energy_kind: Which cumulative total to expose: "paid" or "free".
        """
        # Register with CoordinatorEntity so account refreshes propagate here.
        super().__init__(coordinator)

        # Save the config entry for consistency with the rest of the entities.
        self.config_entry = config_entry

        # Save the user-friendly account prefix used in names and device info.
        self._entity_name = entity_name

        # Save the contract ID because cache storage and dispatcher messages use it.
        self._contract_id = contract_id

        # Save whether this instance is the paid-energy sensor or free-energy sensor.
        self._energy_kind = energy_kind

        # Create the helper object that reads and writes cached usage totals.
        self._cache = UsageCache(contract_id)

        # Start with zero totals until the cache is loaded asynchronously.
        self._latest_totals = {"paid": 0.0, "free": 0.0}

        # Choose a friendly suffix based on which cumulative series this sensor shows.
        name_suffix = "Paid Energy" if energy_kind == "paid" else "Free Energy"

        # Build the user-facing entity name.
        self._attr_name = f"{entity_name} {name_suffix}"

        # Build a contract-specific unique ID so each total is stable and distinct.
        self._attr_unique_id = f"contact_energy_{energy_kind}_usage_{contract_id}"

        # Give both energy sensors a lightning icon to signal electricity usage.
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> float:
        """Return the cumulative energy total in kWh.

        === WHAT THIS DOES ===
        Reads the most recently calculated running total for this sensor type.

        === FOR NON-CODERS ===
        "native_value" is Home Assistant's preferred property name for some kinds
        of numeric sensors. It is still the sensor's main displayed value.
        """
        # Read the total for this specific sensor type, defaulting to 0.0 if the
        # cache has not been populated yet.
        value = float(self._latest_totals.get(self._energy_kind, 0.0))

        # Log the value for troubleshooting without changing the returned state.
        _LOGGER.debug(
            "Energy sensor %s native_value for %s: %.3f kWh (all totals: %s)",
            self._attr_unique_id,
            self._energy_kind,
            value,
            self._latest_totals,
        )

        # Return the numeric cumulative kWh total to Home Assistant.
        return value

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional context attached to the energy sensor.

        === WHAT THIS DOES ===
        Adds supporting metadata that is useful for debugging and transparency,
        such as when the cumulative series starts.
        """
        # Start with an empty attribute dictionary and fill it only when data is
        # available, which keeps the entity tidy in the Home Assistant UI.
        attrs = {}

        try:
            # Ask the cache what start date defines the cumulative total window.
            start_date = self._cache.get_energy_sensor_start_date()

            # Only add attributes if the cache knows a valid start date.
            if start_date:
                # Expose the first date included in the cumulative total.
                attrs["data_start_date"] = start_date.isoformat()

                # Expose where the underlying usage values originally came from.
                attrs["data_source"] = "Contact Energy API"
        except Exception as e:  # pragma: no cover - defensive
            # Attribute generation should never crash the entity; logging is safer.
            _LOGGER.debug(
                "Error getting attributes for energy sensor %s: %s",
                self._attr_unique_id,
                str(e),
            )

        # Return the finished attribute dictionary for Home Assistant to attach.
        return attrs

    @property
    def device_info(self):
        """Return grouping information for the Home Assistant device registry.

        === WHAT THIS DOES ===
        Tells Home Assistant that these energy sensors belong to the same logical
        Contact Energy contract device.

        === FOR NON-CODERS ===
        Device info helps Home Assistant group related entities together so the UI
        shows them as parts of one account/device rather than unrelated sensors.
        """
        # Return the metadata Home Assistant uses to group sensors under one device.
        return {
            "identifiers": {(DOMAIN, self._contract_id)},
            "name": f"Contact Energy {self._entity_name}",
            "manufacturer": "Contact Energy",
            "model": "Energy Account",
        }

    async def async_added_to_hass(self) -> None:
        """Run extra setup after Home Assistant adds this entity.

        === WHAT THIS DOES ===
        Subscribes the energy sensor to usage-update notifications, loads cached
        totals immediately, and writes the first state into Home Assistant.
        """
        # Let parent classes perform their standard Home Assistant setup first.
        await super().async_added_to_hass()

        # Listen for usage cache refresh notifications for this contract.
        # When another part of the integration announces new usage data, this
        # sensor reloads its cumulative totals.
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_usage_updated_{self._contract_id}",
            self._handle_usage_update,
        )

        # Load cached totals right away so the entity has meaningful values as
        # soon as it appears in Home Assistant.
        await self._async_reload_cache()

        # Push the freshly loaded value into Home Assistant's state machine.
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners before Home Assistant removes this entity."""
        # If we previously registered a dispatcher listener, unsubscribe now to
        # avoid leaving behind a stale callback after the entity is removed.
        if hasattr(self, "_unsub_dispatcher") and self._unsub_dispatcher:
            self._unsub_dispatcher()

        # Allow parent classes to complete their normal cleanup.
        await super().async_will_remove_from_hass()

    @callback
    def _handle_usage_update(self) -> None:
        """Respond when fresh usage data has been cached.

        === WHAT THIS DOES ===
        Schedules an asynchronous cache reload without blocking the dispatcher.
        """
        try:
            # Import asyncio locally because we only need it when a callback fires.
            import asyncio

            # Get the currently running event loop used by Home Assistant.
            loop = asyncio.get_event_loop()

            # Schedule a background task that reloads totals and writes new state.
            loop.create_task(self._async_reload_cache_and_update())
        except Exception as e:
            # Log scheduling problems rather than crashing the dispatcher system.
            _LOGGER.error(
                "Error scheduling energy cache reload for contract %s: %s",
                self._contract_id,
                str(e),
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond when the main coordinator updates.

        === WHAT THIS DOES ===
        This mirrors the usage-update behaviour so the energy sensor can also
        refresh itself when coordinator-driven updates matter.
        """
        try:
            # Import asyncio locally for the same lightweight callback reason.
            import asyncio

            # Obtain Home Assistant's active event loop.
            loop = asyncio.get_event_loop()

            # Queue the asynchronous reload so this callback stays fast.
            loop.create_task(self._async_reload_cache_and_update())
        except Exception as e:
            # Log any failure so debugging information is preserved.
            _LOGGER.error(
                "Error reloading energy cache on coordinator update for contract %s: %s",
                self._contract_id,
                str(e),
            )

    async def _async_reload_cache(self) -> None:
        """Reload cached usage data and recompute cumulative totals.

        === WHAT THIS DOES ===
        Loads stored usage history, establishes a stable start date if one does
        not exist yet, then recalculates paid and free energy totals.
        """
        try:
            # Load the latest cached usage data from persistent storage.
            await self._cache.load()

            # Ask the cache whether this energy sensor already has a chosen start
            # date for its cumulative series.
            sensor_start_date = self._cache.get_energy_sensor_start_date()

            # If this is the first run, establish a start date now.
            if sensor_start_date is None:
                # Ask the cache for the earliest available daily usage range.
                # Daily data is preferred because it is more stable than rolling
                # hourly windows when building long-running totals.
                from_date, _ = self._cache.get_daily_range()

                # Use the earliest cached day if available; otherwise fall back to
                # today's date so the sensor still has a valid starting point.
                sensor_start_date = from_date if from_date else date.today()

                # Store the chosen start date back into the cache.
                self._cache.set_energy_sensor_start_date(sensor_start_date)

                # Save immediately so the same start date survives restarts and the
                # cumulative total remains stable over time.
                await self._cache.save()

                # Record one-time initialization in the log for traceability.
                _LOGGER.info(
                    "Energy sensor for contract %s initialized with start_date=%s and saved to cache",
                    self._contract_id,
                    sensor_start_date.isoformat(),
                )

            # Ask the cache to compute cumulative paid/free totals beginning from
            # the chosen sensor start date.
            totals = self._cache.get_cumulative_totals(sensor_start_date)

            # Save those totals in memory so native_value can return them quickly.
            self._latest_totals = totals

            # Log the results to help diagnose unexpected energy dashboard values.
            _LOGGER.debug(
                "Energy sensor for contract %s computed totals: paid=%.3f kWh, free=%.3f kWh (start_date=%s)",
                self._contract_id,
                totals.get("paid", 0.0),
                totals.get("free", 0.0),
                sensor_start_date.isoformat(),
            )
        except Exception as e:
            # Reload failures should be visible in logs with stack traces because
            # incorrect cumulative totals are important to diagnose carefully.
            _LOGGER.error(
                "Failed to reload energy cache for contract %s: %s",
                self._contract_id,
                str(e),
                exc_info=True,
            )

    async def _async_reload_cache_and_update(self) -> None:
        """Reload cached totals and immediately publish the new state."""
        try:
            # First recompute the latest cumulative totals from cache.
            await self._async_reload_cache()

            # Then push the recalculated state into Home Assistant.
            self.async_write_ha_state()
        except Exception as e:
            # Keep errors visible without crashing the task that triggered refresh.
            _LOGGER.error(
                "Error updating energy sensor for contract %s: %s",
                self._contract_id,
                str(e),
                exc_info=True,
            )


class ContactEnergyAccountDetailSensor(CoordinatorEntity, SensorEntity):
    """Represent one descriptive account-detail sensor.

    === WHAT THIS CLASS DOES ===
    This class exposes non-usage, non-balance descriptive details about the
    account and its first contract, such as payment method, billing frequency,
    product name, ICP, and contract status.

    === WHAT DATA IT DISPLAYS ===
    Depending on the attribute passed in, the sensor displays:
    - correspondence_preference
    - payment_method
    - billing_frequency
    - account_nickname
    - icp
    - address
    - product_name
    - contract_type
    - contract_status
    - is_direct_debit
    - is_smooth_pay
    - is_prepay

    === FOR NON-CODERS ===
    These sensors are less about numbers and more about account facts. They help
    users confirm how the account is configured without opening the Contact Energy
    website.
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        attribute: str,
    ):
        """Initialize one account-detail sensor instance.

        === WHAT THIS DOES ===
        Stores setup references and configures the display name for whichever
        descriptive account field this sensor should show.

        Args:
            coordinator: Shared coordinator holding the latest API data.
            config_entry: Stored configuration for this account entry.
            entity_name: Friendly account prefix shown in the entity name.
            attribute: Internal key naming the descriptive field to expose.
        """
        # Connect this sensor to the coordinator-based update mechanism.
        super().__init__(coordinator)

        # Save constructor inputs that define this entity instance.
        self.config_entry = config_entry
        self.entity_name = entity_name
        self.attribute = attribute

        # Create a stable unique identifier for the Home Assistant entity registry.
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{attribute}"

        # Translate internal field keys into clear, human-readable names.
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

        # Build the sensor's final visible display name.
        self._attr_name = f"{entity_name} {attribute_names.get(attribute, attribute)}"

    @property
    def state(self):
        """Return the current descriptive account state.

        === WHAT THIS DOES ===
        Extracts a human-meaningful detail from the account or contract section of
        the shared coordinator payload.

        === FOR NON-CODERS ===
        The integration stores many account facts inside one large data structure.
        This method picks out exactly one fact for this sensor.
        """
        # Without coordinator data, it is safer to show no value at all.
        if not self.coordinator.data:
            return None

        # Extract the main account detail block from the shared API response.
        account_detail = self.coordinator.data.get("accountDetail", {})

        # Extract the list of contracts attached to the account.
        contracts = account_detail.get("contracts", [])

        # Most sensors here only need the first contract, so use it if present;
        # otherwise fall back to an empty dictionary to avoid key errors.
        contract = contracts[0] if contracts else {}

        # Return the communication preference used by Contact Energy.
        if self.attribute == "correspondence_preference":
            return account_detail.get("correspondencePreference")

        # Return the configured payment method.
        if self.attribute == "payment_method":
            return account_detail.get("paymentMethod")

        # Return how often billing occurs.
        if self.attribute == "billing_frequency":
            return account_detail.get("billingFrequency")

        # Return the user-facing nickname of the account.
        if self.attribute == "account_nickname":
            return account_detail.get("nickname")

        # Return the ICP identifier from the contract.
        if self.attribute == "icp":
            return contract.get("icp")

        # Return the service address from the contract.
        if self.attribute == "address":
            return contract.get("address")

        # The product name is nested one level deeper inside the contract.
        if self.attribute == "product_name":
            product = contract.get("product", {})
            return product.get("name")

        # Return the contract type label.
        if self.attribute == "contract_type":
            return contract.get("type")

        # Return the current contract status.
        if self.attribute == "contract_status":
            return contract.get("status")

        # Translate the raw boolean into "Yes" or "No" for non-technical users.
        if self.attribute == "is_direct_debit":
            return "Yes" if account_detail.get("isDirectDebit") else "No"

        # Translate SmoothPay status into plain language.
        if self.attribute == "is_smooth_pay":
            return "Yes" if account_detail.get("isSmoothPay") else "No"

        # Translate prepay status into plain language.
        if self.attribute == "is_prepay":
            return "Yes" if account_detail.get("isPrepay") else "No"

        # Unknown attribute requests should safely return no state.
        return None
