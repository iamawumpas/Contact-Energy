"""Usage data sensor platform for Contact Energy integration.

=== WHAT THIS DOES ===
This legacy module creates a Home Assistant sensor entity that exposes cached
Contact Energy usage data. The sensor stores most of its useful information in
attributes so dashboards can graph hourly, daily, and monthly usage.

=== FOR NON-CODERS ===
A Home Assistant "sensor" is like a labelled display tile in a smart-home app.
This file builds one such tile for electricity usage. The main number on the
sensor is a count of cached records, while the detailed charts are stored in
extra attributes attached to that sensor.

Important plain-language ideas:
- Cache: Saved data kept locally so the app still has something to show later.
- Attribute: Extra information attached to a sensor besides its main value.
- Coordinator: A shared manager that fetches fresh data for multiple entities.
- Callback: A function Home Assistant calls automatically when something changes.

=== LEGACY / COMPATIBILITY NOTE ===
This is a legacy/deprecated file. It remains in place for backward
compatibility and as a teaching resource showing how earlier versions exposed
usage data directly from cache files into Home Assistant sensor attributes.

Copyright (c) 2025
License: MIT
"""

# ============================================================================
# IMPORTS - Every dependency is annotated for teaching purposes
# ============================================================================

# asyncio lets this module schedule background reload tasks without blocking Home Assistant.
import asyncio

# logging records debug and error messages so maintainers can see what happened.
import logging

# json is used only to estimate the serialized size of sensor attributes.
import json

# datetime, timedelta, and timezone help us compare timestamps and create cutoffs.
from datetime import datetime, timedelta, timezone

# These typing helpers describe expected dictionary/list/optional value shapes.
from typing import Any, Dict, List, Optional

# monthrange was used by older iterations of this legacy sensor and is kept here
# as part of the teaching history of the file, even though the current logic no
# longer calls it directly.
from calendar import monthrange

# SensorEntity is Home Assistant's base class for sensor-like entities.
from homeassistant.components.sensor import SensorEntity

# HomeAssistant is the running app object; callback marks fast, event-driven methods.
from homeassistant.core import HomeAssistant, callback

# async_dispatcher_connect subscribes this sensor to in-app update signals.
from homeassistant.helpers.dispatcher import async_dispatcher_connect

# AddEntitiesCallback is the helper type for registering entities with HA.
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# ConfigType describes the config entry data structure used during setup.
from homeassistant.helpers.typing import ConfigType

# CoordinatorEntity links this sensor to a shared update coordinator.
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# DOMAIN is the integration's unique identifier inside Home Assistant.
from .const import DOMAIN

# ContactEnergyCoordinator is the shared data manager used by this integration.
from .coordinator import ContactEnergyCoordinator

# UsageCache loads saved usage data from disk so this sensor can expose it.
from .usage_cache import UsageCache

# ============================================================================
# MODULE CONSTANTS AND LOGGER
# ============================================================================

# Logger for this legacy sensor module.
_LOGGER = logging.getLogger(__name__)

# Home Assistant attributes must stay under a practical size limit.
# This budget keeps Recorder and the state machine happy.
ATTRIBUTE_SIZE_BUDGET = 15000


# ============================================================================
# PLATFORM SETUP
# ============================================================================

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Contact Energy usage sensor entities.

    === WHAT THIS DOES ===
    This Home Assistant entry-point creates one usage sensor for the configured
    Contact Energy contract.

    === WHY IT EXISTS ===
    Home Assistant calls this function when the integration is loaded. Legacy
    installations still depend on this older sensor-based setup flow.

    === STEP-BY-STEP ===
    1. Read the shared coordinator from Home Assistant's stored integration data.
    2. Read identifying details from the config entry.
    3. Build a user-friendly sensor name.
    4. Create the sensor object.
    5. Hand that sensor back to Home Assistant so it becomes active.
    """
    # ====================================================================
    # STEP 1: FIND THE COORDINATOR ALREADY STORED BY THE INTEGRATION
    # ====================================================================
    # hass.data is Home Assistant's shared storage area for runtime objects.
    coordinator: ContactEnergyCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    # ====================================================================
    # STEP 2: READ FRIENDLY DETAILS FROM THE CONFIG ENTRY
    # ====================================================================
    # These fallbacks keep the code safe even if old entries are incomplete.
    account_nickname = config_entry.data.get("account_nickname", "Unknown")
    icp = config_entry.data.get("icp", "Unknown")
    contract_id = config_entry.data.get("contract_id", "unknown")

    # ====================================================================
    # STEP 3: BUILD A HUMAN-READABLE ENTITY NAME
    # ====================================================================
    # Example result: "Home (1234567890)"
    entity_name = f"{account_nickname} ({icp})"

    # Log the setup action for troubleshooting.
    _LOGGER.info(
        "Setting up usage sensor for contract %s (%s)",
        contract_id,
        entity_name,
    )

    # ====================================================================
    # STEP 4: CREATE THE SENSOR ENTITY INSTANCE
    # ====================================================================
    entities = [
        ContactEnergyUsageSensor(
            coordinator,
            config_entry,
            entity_name,
            contract_id,
        )
    ]

    # ====================================================================
    # STEP 5: REGISTER THE ENTITY WITH HOME ASSISTANT
    # ====================================================================
    # The second argument requests an immediate first refresh.
    async_add_entities(entities, True)


# ============================================================================
# SENSOR ENTITY
# ============================================================================

class ContactEnergyUsageSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity that exposes cached usage data.

    === WHAT THIS DOES ===
    This entity presents a single sensor whose main state is a record count and
    whose attributes contain recent usage data series for charts.

    === WHY IT STILL EXISTS ===
    This is legacy/deprecated code. It remains because older dashboards and card
    setups may still expect usage data to be exposed this way.

    === FOR NON-CODERS ===
    Think of this class as the display board that reads a saved spreadsheet of
    usage history and turns it into chart-ready information for the smart-home UI.
    """

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        config_entry: ConfigType,
        entity_name: str,
        contract_id: str,
    ) -> None:
        """Initialize the usage sensor.

        === WHAT THIS DOES ===
        This constructor stores the key identifiers and prepares a UsageCache
        helper so the sensor can read previously saved data.

        === WHY IT EXISTS ===
        Each sensor instance needs its own identity and contract link, even in
        legacy code, so Home Assistant can track it correctly.

        === STEP-BY-STEP ===
        1. Initialize the CoordinatorEntity parent class.
        2. Save references to config and contract details.
        3. Create a cache helper for this contract.
        4. Build the sensor's name, unique ID, and icon.
        """
        # Let the parent class store the coordinator reference.
        super().__init__(coordinator)

        # Save the config entry so other methods can inspect setup data later.
        self.config_entry = config_entry

        # Save the friendly entity name used in UI labels.
        self._entity_name = entity_name

        # Save the contract ID so the sensor knows which cache file to read.
        self._contract_id = contract_id

        # Create the cache helper that reads usage history from disk.
        self._cache = UsageCache(contract_id)

        # This legacy variable shows how a slug-like friendly name was derived.
        # It is kept as a teaching artifact even though the current code does not reuse it.
        friendly_name = (
            f"{entity_name} Usage".replace(" ", "_").replace("(", "").replace(")", "").lower()
        )

        # Store the display name Home Assistant shows in the UI.
        self._attr_name = f"{entity_name} Usage"

        # Store the unique entity ID so HA can distinguish this sensor forever.
        self._attr_unique_id = f"contact_energy_usage_{contract_id}"

        # Pick a lightning icon because the sensor represents electricity usage.
        self._attr_icon = "mdi:lightning-bolt"

        # Log the finished setup values for debugging.
        _LOGGER.debug(
            "Initialized usage sensor: name=%s, unique_id=%s, contract=%s, friendly_name=%s",
            self._attr_name,
            self._attr_unique_id,
            contract_id,
            friendly_name,
        )

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information for grouping related sensors.

        === WHAT THIS DOES ===
        This property tells Home Assistant which logical device this sensor belongs to.

        === WHY IT EXISTS ===
        Grouping account and usage entities under one device makes the UI easier to
        understand and preserves the older integration behaviour users expect.

        === STEP-BY-STEP ===
        1. Use the contract ID as a stable device identifier.
        2. Build a friendly device name.
        3. Return manufacturer and model labels.
        """
        # Return a dictionary that Home Assistant uses to build the device entry.
        return {
            "identifiers": {(DOMAIN, self._contract_id)},
            "name": f"Contact Energy {self._entity_name}",
            "manufacturer": "Contact Energy",
            "model": "Energy Account",
        }

    @property
    def native_value(self) -> int:
        """Return the main state value of the sensor.

        === WHAT THIS DOES ===
        The sensor's main numeric state is the total number of cached records.

        === WHY IT EXISTS ===
        Legacy sensors needed a compact numeric state even though the real value is
        carried in attributes. A record count is a simple, safe state to expose.

        === STEP-BY-STEP ===
        1. Check whether cache data has been loaded.
        2. Count hourly, daily, and monthly record groups separately.
        3. Add the three counts together.
        4. Return zero if nothing has been loaded yet.
        """
        # Only count records if the cache helper has loaded a non-empty data structure.
        if hasattr(self._cache, "data") and self._cache.data:
            # Count hourly records saved in the cache.
            hourly_count = len(self._cache.data.get("hourly", {}))

            # Count daily records saved in the cache.
            daily_count = len(self._cache.data.get("daily", {}))

            # Count monthly records saved in the cache.
            monthly_count = len(self._cache.data.get("monthly", {}))

            # Return the grand total as the sensor's visible state.
            return hourly_count + daily_count + monthly_count

        # If no cache exists yet, show zero instead of failing.
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return chart-friendly usage attributes while staying under size limits.

        === WHAT THIS DOES ===
        This property extracts recent cached usage records and places them into a
        compact set of dictionaries ready for Home Assistant dashboards.

        === WHY IT EXISTS ===
        Older dashboard cards expect usage history in sensor attributes. This code
        keeps that behaviour while trimming data so Home Assistant can store it.

        === STEP-BY-STEP ===
        1. Prepare an empty attribute structure.
        2. Exit early if no cache has been loaded.
        3. Define tiny helper functions for adding values and trimming payload size.
        4. Copy over recent hourly, daily, and monthly data.
        5. Remove empty and zero-value records to save space.
        6. Trim oldest entries until the total serialized payload fits the budget.
        7. Return the final attribute dictionary.
        """
        # Start with empty attribute buckets for each time series we expose.
        attributes = {
            "hourly_paid_usage": {},
            "hourly_free_usage": {},
            "daily_paid_usage": {},
            "daily_free_usage": {},
            "daily_cost_usage": {},
            "monthly_paid_usage": {},
            "monthly_free_usage": {},
            "monthly_cost_usage": {},
        }

        # If no cache data is available yet, return the empty structure immediately.
        if not hasattr(self._cache, "data") or not self._cache.data:
            _LOGGER.debug("No cache data available for contract %s", self._contract_id)
            return attributes

        def _add_non_zero(target: Dict[str, float], key: str, value: Any) -> None:
            """Add a rounded numeric value only when it is meaningful.

            === WHY THIS HELPER EXISTS ===
            Many chart points would otherwise be zeros or invalid values. Skipping
            them keeps the payload smaller and easier for dashboards to use.
            """
            # Try to convert the incoming value into a number.
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                # If conversion fails, silently ignore this point.
                return

            # Skip exact zero values because they add size without useful detail.
            if numeric == 0:
                return

            # Store the number rounded to two decimal places.
            target[key] = round(numeric, 2)

        def _serialized_size(payload: Dict[str, Any]) -> int:
            """Estimate the JSON size of the attribute payload.

            === FOR NON-CODERS ===
            Home Assistant ultimately stores attributes as JSON-like text. Measuring
            that text size tells us whether the payload is getting too large.
            """
            return len(json.dumps(payload, separators=(",", ":"), ensure_ascii=True))

        def _trim_oldest_entries(target: Dict[str, float], keep_at_least: int = 0) -> bool:
            """Remove the oldest entry from one series unless it is already too small.

            === WHY THIS HELPER EXISTS ===
            When attributes become too large, we discard the oldest chart point first
            because recent data is usually the most valuable to users.
            """
            # Do not trim below the minimum amount of data we promised to keep.
            if len(target) <= keep_at_least:
                return False

            # Keys are sortable dates/timestamps, so the first sorted key is oldest.
            oldest_key = sorted(target.keys())[0]

            # Remove that oldest point and report success.
            target.pop(oldest_key, None)
            return True

        try:
            # ================================================================
            # HOURLY DATA - KEEP A RECENT WINDOW OF GRANULAR POINTS
            # ================================================================
            hourly_records = self._cache.data.get("hourly", {})
            hourly_cutoff = datetime.now(timezone.utc) - timedelta(days=10)
            for timestamp, record in sorted(hourly_records.items()):
                try:
                    # Convert the ISO timestamp into a datetime so we can compare ages.
                    record_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if record_time < hourly_cutoff:
                        # Skip old hourly points outside the chart window.
                        continue
                except (ValueError, TypeError):
                    # Ignore malformed timestamps rather than breaking the whole sensor.
                    continue

                # Copy paid usage into the hourly chart payload if it is meaningful.
                _add_non_zero(attributes["hourly_paid_usage"], timestamp, record.get("paid"))

                # Copy free usage into the hourly chart payload if it is meaningful.
                _add_non_zero(attributes["hourly_free_usage"], timestamp, record.get("free"))

            # ================================================================
            # DAILY DATA - KEEP A MEDIUM-SIZED WINDOW FOR DASHBOARDS
            # ================================================================
            daily_records = self._cache.data.get("daily", {})
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=35)).date()
            for date_key, record in sorted(daily_records.items()):
                try:
                    # Convert the YYYY-MM-DD key into a date for comparison.
                    record_date = datetime.strptime(date_key, "%Y-%m-%d").date()
                    if record_date < cutoff_date:
                        # Skip older daily records to keep the payload smaller.
                        continue
                except (ValueError, TypeError):
                    # Ignore malformed date keys.
                    continue

                # Copy paid, free, and cost values only when non-zero.
                _add_non_zero(attributes["daily_paid_usage"], date_key, record.get("paid"))
                _add_non_zero(attributes["daily_free_usage"], date_key, record.get("free"))
                _add_non_zero(attributes["daily_cost_usage"], date_key, record.get("cost"))

            # ================================================================
            # MONTHLY DATA - KEEP THE MOST RECENT 18 MONTHS
            # ================================================================
            monthly_records = self._cache.data.get("monthly", {})
            if monthly_records:
                # Sort month keys newest-first and keep only the first 18 entries.
                sorted_months = sorted(monthly_records.keys(), reverse=True)[:18]

                for month_key in sorted_months:
                    # Pull out this month's stored usage record.
                    record = monthly_records[month_key]

                    # Copy non-zero monthly values into the sensor attributes.
                    _add_non_zero(attributes["monthly_paid_usage"], month_key, record.get("paid"))
                    _add_non_zero(attributes["monthly_free_usage"], month_key, record.get("free"))
                    _add_non_zero(attributes["monthly_cost_usage"], month_key, record.get("cost"))

            # ================================================================
            # FINAL SIZE ENFORCEMENT - TRIM OLDEST POINTS UNTIL WE FIT
            # ================================================================
            while _serialized_size(attributes) > ATTRIBUTE_SIZE_BUDGET:
                trimmed = False

                # Prefer trimming the least critical oldest points first.
                for key, floor in (
                    ("hourly_paid_usage", 72),
                    ("hourly_free_usage", 24),
                    ("daily_cost_usage", 21),
                    ("daily_paid_usage", 21),
                    ("daily_free_usage", 21),
                ):
                    if _trim_oldest_entries(attributes[key], keep_at_least=floor):
                        trimmed = True
                        break

                # If nothing could be trimmed safely, stop and warn.
                if not trimmed:
                    _LOGGER.warning(
                        "Unable to trim usage attributes further for contract %s without dropping below minimum chart windows",
                        self._contract_id,
                    )
                    break

            # Log a summary of the final payload sizes for support visibility.
            _LOGGER.debug(
                "Loaded usage data for contract %s: hourly=%d, daily=%d, monthly=%d, serialized_size=%d",
                self._contract_id,
                len(attributes["hourly_paid_usage"]) + len(attributes["hourly_free_usage"]),
                len(attributes["daily_paid_usage"]) + len(attributes["daily_free_usage"]) + len(attributes["daily_cost_usage"]),
                len(attributes["monthly_paid_usage"]) + len(attributes["monthly_free_usage"]) + len(attributes["monthly_cost_usage"]),
                _serialized_size(attributes),
            )

        except Exception as e:
            # If anything unexpected goes wrong, log it and still return what we have.
            _LOGGER.error(
                "Error loading usage data attributes for contract %s: %s",
                self._contract_id,
                str(e),
                exc_info=True,
            )

        # Return the final chart-friendly attribute dictionary.
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle a coordinator refresh notification.

        === WHAT THIS DOES ===
        This callback reacts when the shared coordinator says underlying data changed.

        === WHY IT EXISTS ===
        Even though this legacy sensor reads from disk cache, it still needs to wake
        up when the coordinator reports that new data may now be available.

        === STEP-BY-STEP ===
        1. Log that an update arrived.
        2. Ask asyncio for the active event loop.
        3. Schedule an asynchronous cache reload and state update.
        """
        # Record that the coordinator triggered this sensor.
        _LOGGER.debug("Coordinator update received for usage sensor (contract %s)", self._contract_id)

        # Schedule an async reload instead of blocking this quick callback.
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._async_reload_cache_and_update())
        except Exception as e:
            _LOGGER.error(
                "Error reloading cache for contract %s: %s",
                self._contract_id,
                str(e),
            )

    async def _async_reload_cache(self) -> None:
        """Reload cache data from disk asynchronously.

        === WHAT THIS DOES ===
        This helper asks UsageCache to re-read the saved JSON file from disk.

        === WHY IT EXISTS ===
        The sensor's attributes come from the cache file, so the file must be
        reloaded before the sensor writes a fresh Home Assistant state.

        === STEP-BY-STEP ===
        1. Log the reload attempt.
        2. Await the cache helper's load operation.
        3. Log whether the load produced existing data or a fresh empty cache.
        """
        try:
            _LOGGER.debug("Reloading cache for usage sensor (contract %s)", self._contract_id)

            # Ask the cache helper to load from its JSON file.
            loaded = await self._cache.load()

            # Log whether a real cache file was found and loaded.
            if loaded:
                _LOGGER.debug("Cache reloaded successfully for contract %s", self._contract_id)
            else:
                _LOGGER.debug(
                    "Cache load returned False for contract %s (may be first run)",
                    self._contract_id,
                )
        except Exception as e:
            _LOGGER.error(
                "Failed to reload cache for contract %s: %s",
                self._contract_id,
                str(e),
                exc_info=True,
            )

    async def async_added_to_hass(self) -> None:
        """Run when the entity is added to Home Assistant.

        === WHAT THIS DOES ===
        This lifecycle method subscribes the sensor to update signals and loads the
        initial cache contents.

        === WHY IT EXISTS ===
        Home Assistant calls this when the entity becomes active. Legacy entities
        must use this hook to finish runtime setup.

        === STEP-BY-STEP ===
        1. Let the parent class perform its own startup work.
        2. Subscribe to dispatcher signals for usage updates.
        3. Load cache data so the sensor has immediate content.
        """
        # First let the parent classes complete their startup tasks.
        await super().async_added_to_hass()

        # Subscribe to the integration's usage-updated dispatcher signal.
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{DOMAIN}_usage_updated_{self._contract_id}",
            self._handle_usage_update,
        )

        # Log successful subscription.
        _LOGGER.debug("Usage sensor added to HA for contract %s", self._contract_id)

        # Load the initial cache from disk so the sensor has data immediately after startup.
        try:
            await self._cache.load()
            _LOGGER.debug("Initial cache loaded for usage sensor (contract %s)", self._contract_id)
        except Exception as e:
            _LOGGER.warning(
                "Could not load initial cache for contract %s: %s",
                self._contract_id,
                str(e),
            )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up subscriptions when the entity is removed.

        === WHAT THIS DOES ===
        This lifecycle method unsubscribes the sensor from dispatcher signals.

        === WHY IT EXISTS ===
        Legacy listeners must be detached cleanly so they do not continue reacting
        after the entity has been removed.

        === STEP-BY-STEP ===
        1. Check whether a dispatcher unsubscribe callback was stored.
        2. Call it if present.
        3. Let the parent class finish its own removal work.
        """
        # If we subscribed earlier, call the stored unsubscribe function now.
        if hasattr(self, "_unsub_dispatcher") and self._unsub_dispatcher:
            self._unsub_dispatcher()

        # Let the parent classes perform their cleanup steps too.
        await super().async_will_remove_from_hass()

    @callback
    def _handle_usage_update(self) -> None:
        """Handle usage-specific dispatcher updates.

        === WHAT THIS DOES ===
        This callback reacts to the explicit usage-updated signal sent by the
        integration when fresh usage data has been cached.

        === WHY IT EXISTS ===
        The legacy sensor receives both coordinator-style and dispatcher-style
        nudges, so it needs a dedicated handler for this older signal path.

        === STEP-BY-STEP ===
        1. Ask for the active asyncio event loop.
        2. Schedule a cache reload.
        3. Schedule a Home Assistant state write after reload finishes.
        """
        try:
            # Use the running event loop to schedule asynchronous follow-up work.
            loop = asyncio.get_event_loop()

            # Queue the reload-and-update task without blocking the callback.
            loop.create_task(self._async_reload_cache_and_update())
        except Exception as e:
            _LOGGER.error(
                "Error reloading cache on usage update for contract %s: %s",
                self._contract_id,
                str(e),
            )

    async def _async_reload_cache_and_update(self) -> None:
        """Reload cache data and then push a fresh state to Home Assistant.

        === WHAT THIS DOES ===
        This helper chains together the two actions needed after new usage data is
        available: reload the cache and write a fresh state.

        === WHY IT EXISTS ===
        Writing state before the cache reload finishes would expose stale data.
        This helper keeps the sequence correct in one place.

        === STEP-BY-STEP ===
        1. Await the disk-cache reload helper.
        2. Ask Home Assistant to write the entity's new state and attributes.
        3. Log any unexpected failure.
        """
        try:
            # First refresh the in-memory cache data from disk.
            await self._async_reload_cache()

            # Then tell Home Assistant to publish the updated state and attributes.
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(
                "Error in cache reload and update for contract %s: %s",
                self._contract_id,
                str(e),
                exc_info=True,
            )
