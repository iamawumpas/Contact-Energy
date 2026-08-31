"""Contact Energy integration for Home Assistant.

====== WHAT THIS FILE DOES ======
This file is the main entry point for the Contact Energy integration.
In Home Assistant, the "entry point" is the first integration file that gets
called when Home Assistant needs to start, load, or remove the integration.

This module is responsible for:
1. Setting up the integration when a user adds it in Home Assistant.
2. Creating shared objects such as the API client and data coordinator.
3. Registering Home Assistant services that users can call manually.
4. Loading supported platforms, such as sensors.
5. Cleaning everything up when the integration is unloaded or removed.

====== FOR NON-CODERS ======
A few Home Assistant words used in this file:
- "Config entry": A saved integration setup created by the user in the UI.
  Think of it as Home Assistant's saved record for one Contact Energy account.
- "Platform": A feature area inside an integration, such as sensors,
  binary sensors, switches, or buttons. This integration currently loads only
  the sensor platform.
- "Service": A named action Home Assistant can run on demand.
  In this file, the service lets a user manually request a data refresh.
- "Coordinator": A helper object that fetches data and shares it with all
  related entities, so each sensor does not need to fetch data on its own.
- "Unload": Home Assistant's word for shutting down an integration cleanly,
  removing its entities, and releasing the memory and background tasks it used.

This file focuses on orchestration. In other words, it does not do the detailed
API work itself. Instead, it connects the major pieces together so the rest of
Home Assistant knows how to use this integration.
"""

# This enables modern type hints to behave consistently across Python versions.
# In simple terms, it lets us write clearer type information without worrying
# about exactly when Python evaluates those type names.
from __future__ import annotations

# logging records what this file is doing so developers and advanced users can
# understand setup, refresh, and cleanup activity in Home Assistant logs.
import logging

# datetime, timedelta, and timezone are used to track current UTC time,
# build a short cool-down window after manual refreshes, and compare times in a
# timezone-safe way.
from datetime import datetime, timedelta, timezone

# ConfigEntry represents one saved integration setup in Home Assistant.
# We use it to read the stored login details and identify the specific account
# being set up or unloaded.
from homeassistant.config_entries import ConfigEntry

# Platform is Home Assistant's enum for supported feature types like sensors.
# We use it to declare which parts of this integration should be loaded.
from homeassistant.const import Platform

# HomeAssistant is the main application object that holds global state.
# ServiceCall represents a call to a Home Assistant service and gives us access
# to any data passed into that service.
from homeassistant.core import HomeAssistant, ServiceCall

# ConfigEntryNotReady tells Home Assistant a setup failure is temporary, so it
# retries setup later instead of marking the integration as permanently failed.
from homeassistant.exceptions import ConfigEntryNotReady

# voluptuous validates the shape of service input data.
# Here we use an empty schema because the refresh service takes no arguments.
import voluptuous as vol

# DOMAIN is the integration's unique internal name used as a shared key inside
# Home Assistant, especially in hass.data and service registration.
from .const import DOMAIN

# ContactEnergyApi is the integration's API client.
# It knows how to log in to Contact Energy and retrieve data from the remote
# service using the user's saved credentials.
# ContactEnergyConnectionError distinguishes temporary network/timeout issues
# from genuine invalid-credential failures.
from .contact_api import ContactEnergyApi, ContactEnergyConnectionError

# ContactEnergyCoordinator is the shared data manager for this integration.
# It handles fetching and refreshing data once, then distributing that data to
# all entities that depend on it.
from .coordinator import ContactEnergyCoordinator

# Create a module-specific logger so messages from this file are clearly labeled
# in Home Assistant's logs.
_LOGGER = logging.getLogger(__name__)

# ====== SUPPORTED PLATFORMS ======
# Home Assistant loads integrations in pieces called "platforms".
# This list tells Home Assistant which platform modules belong to this
# integration for each config entry.
#
# Right now we only load Platform.SENSOR, which means this integration creates
# sensor entities such as account or usage-related readings.
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Home Assistant services for this integration.

    ====== WHAT THIS FUNCTION DOES ======
    A Home Assistant "service" is a named action that can be triggered manually
    by the user, by an automation, or by another part of Home Assistant.

    This function registers the Contact Energy service named:
    - contact_energy.refresh_data

    When called, that service asks every configured Contact Energy account to:
    1. Log in again using the saved username and password.
    2. Refresh normal account data through the main coordinator.
    3. Force a usage-data sync immediately.

    ====== FOR NON-CODERS ======
    Think of a service like a button with a published name.
    Even if no visible button exists on screen, Home Assistant still exposes a
    reusable action that automations or users can call.

    This service exists for situations where someone does not want to wait for
    the next scheduled refresh and wants new data right away.
    """

    async def handle_refresh_data(call: ServiceCall) -> None:
        """Handle a manual request to refresh Contact Energy data.

        ====== WHAT THIS NESTED FUNCTION DOES ======
        This inner function is the code that actually runs when the user calls
        the refresh_data service.

        It is defined inside async_setup_services because it belongs only to
        this specific service registration and does not need to exist anywhere
        else in the integration.

        The `call` argument contains service-call details from Home Assistant.
        This service currently does not expect any parameters, but Home
        Assistant still passes a ServiceCall object whenever the service runs.
        """
        # Record that a user or automation explicitly asked for fresh data.
        _LOGGER.info("Manual data refresh requested via service call")

        # Loop through every configured Contact Energy account stored under this
        # integration's domain data. Each item represents one config entry.
        for entry_id, entry_data in hass.data[DOMAIN].items():
            # Pull the shared coordinator out of stored entry data.
            # The coordinator handles the normal account refresh process.
            coordinator = entry_data.get("coordinator")

            # Pull the API client out of stored entry data.
            # The API client handles login and remote API communication.
            api_client = entry_data.get("api_client")

            # Only continue if we actually have a coordinator for this entry.
            # Without it, there is nothing to refresh.
            if coordinator:
                # Capture the current UTC time once so all time comparisons in
                # this refresh attempt use a consistent timestamp.
                now = datetime.now(timezone.utc)

                # Read the time until which manual refreshes should remain
                # temporarily blocked after a recent sync.
                lock_until = entry_data.get("sync_lock_until")

                # Read whether a sync is already actively running right now.
                sync_in_progress = entry_data.get("sync_in_progress", False)

                # ====== SYNC LOCKING AND COOL-DOWN ======
                # Two protections are used here to prevent repeated overlap:
                # 1. sync_in_progress stops a second manual refresh from starting
                #    while one is already running.
                # 2. sync_lock_until adds a short cool-down window after a refresh
                #    begins, which reduces back-to-back requests and API churn.
                #
                # This matters because manual refresh can trigger login, account
                # refresh, and usage sync work. Running that many operations over
                # and over too quickly could cause duplicate work, race conditions,
                # or unnecessary load on the Contact Energy API.
                if (lock_until and now < lock_until) or sync_in_progress:
                    # This value is part of the user-facing message below.
                    # The lock itself is set for 30 seconds, but the message is a
                    # simple friendly suggestion to wait roughly a minute.
                    wait_seconds = 60

                    # Build a gentle explanation for logs and for maintainers.
                    message = (
                        "Manual refresh cannot run right now because a sync is active "
                        f"or just finished. Please try again in {wait_seconds}s."
                    )

                    # Log the reason we refused the refresh.
                    # We intentionally do not raise an exception here because a
                    # noisy UI error would be less helpful than a quiet refusal.
                    _LOGGER.info("%s (entry=%s)", message, entry_id)

                    # Stop processing this service call immediately.
                    # Returning here means: do not start another refresh while the
                    # current one is still protected by the lock/cool-down logic.
                    return

                # Mark this entry as actively syncing so another manual refresh
                # cannot begin at the same time.
                entry_data["sync_in_progress"] = True

                # Set a short cool-down expiry time starting from right now.
                # Until this timestamp has passed, new manual refresh requests for
                # this entry will be temporarily blocked.
                entry_data["sync_lock_until"] = now + timedelta(seconds=30)

                # Log which config entry is being refreshed for easier debugging.
                _LOGGER.info("Forcing data refresh for entry %s", entry_id)

                # Tell the coordinator not to launch its normal background usage
                # sync behavior during this cycle because we are about to run a
                # dedicated forced usage sync ourselves.
                coordinator._skip_next_usage_sync = True

                try:
                    # ====== STEP-BY-STEP MANUAL REFRESH LOGIC ======
                    # Step 1: Re-authenticate with the saved email and password.
                    # We do this before the manual refresh so we do not rely on a
                    # short-lived token that may already be expired.
                    if api_client:
                        try:
                            # Log which account is attempting login again.
                            _LOGGER.debug(
                                "Manual refresh re-authenticating as %s for entry %s",
                                api_client.email,
                                entry_id,
                            )

                            # Perform the actual login to get a fresh session/token.
                            await api_client.authenticate()
                        except Exception as err:
                            # If login fails, record the reason in the log.
                            _LOGGER.error(
                                "Manual refresh re-authentication failed for entry %s: %s",
                                entry_id,
                                err,
                            )

                            # Skip the rest of the refresh for this one entry.
                            # `continue` means move on to the next configured
                            # Contact Energy account instead of crashing the
                            # whole service call.
                            continue

                    # Step 2: Ask the main coordinator to refresh its shared data.
                    # This updates the integration's normal account-level state.
                    await coordinator.async_request_refresh()

                    # Step 3: If a dedicated usage coordinator exists, force it to
                    # sync immediately, even if its normal timing rules would have
                    # delayed that work.
                    if hasattr(coordinator, "usage_coordinator"):
                        await coordinator.usage_coordinator.force_sync()
                finally:
                    # Always restore the coordinator flag, even if login or
                    # refresh work failed midway through.
                    coordinator._skip_next_usage_sync = False

                    # Clear the active-sync marker so future manual refreshes can
                    # run once the cool-down window has expired.
                    entry_data["sync_in_progress"] = False

    # ====== SERVICE REGISTRATION ======
    # Register the service only once for the whole integration domain.
    # Home Assistant may set up multiple config entries, but the service name
    # itself should still be created just one time.
    if not hass.services.has_service(DOMAIN, "refresh_data"):
        # Register `contact_energy.refresh_data` with an empty schema because it
        # takes no parameters from the caller.
        hass.services.async_register(
            DOMAIN,
            "refresh_data",
            handle_refresh_data,
            schema=vol.Schema({}),
        )

        # Log that the service is now available to Home Assistant.
        _LOGGER.info("Registered refresh_data service")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Contact Energy from one saved Home Assistant config entry.

    ====== WHAT THIS FUNCTION DOES ======
    This is the main integration setup function.
    Home Assistant calls it when one Contact Energy config entry needs to start.

    In practical terms, this function:
    1. Prepares a storage area in hass.data for this integration.
    2. Validates that the saved credentials contain what startup requires.
    3. Creates the API client used to talk to Contact Energy.
    4. Authenticates immediately to confirm the credentials still work.
    5. Creates the coordinator that manages shared data updates.
    6. Performs the first refresh so entities start with real data.
    7. Stores shared objects in hass.data[DOMAIN][entry.entry_id].
    8. Loads the integration's platforms, such as sensors.
    9. Registers services if they are not already registered.

    ====== FOR NON-CODERS ======
    This function is like opening a shop for business each time a Contact Energy
    account is loaded. It unlocks the door, checks the login works, creates the
    manager objects, fills the shelves with the first batch of data, then tells
    Home Assistant which sensors to put on display.

    Returns:
        True if setup succeeded and Home Assistant can use the integration.
        False if setup failed and Home Assistant should treat the entry as not
        ready or not usable.
    """
    # Make sure Home Assistant has a top-level storage dictionary for this
    # integration domain. `setdefault` creates it only if it does not yet exist.
    hass.data.setdefault(DOMAIN, {})

    # ====== CREDENTIAL VALIDATION ======
    # Older config entries may not contain a saved password.
    # This integration now needs the password so it can log in again and refresh
    # tokens reliably, especially during startup and manual refreshes.
    if "password" not in entry.data:
        # Record a clear warning so the missing credential is visible in logs.
        _LOGGER.warning(
            "Contact Energy config entry %s is missing password. "
            "This is required for token refresh. Please reconfigure the integration.",
            entry.entry_id,
        )

        # Start a Home Assistant config flow to help the user repair or
        # re-create the integration entry with complete credentials.
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import", "title_placeholders": {"name": entry.title}},
                data=entry.data,
            )
        )

        # Stop setup because the integration cannot authenticate safely without
        # the missing password.
        return False

    # ====== API CLIENT CREATION ======
    # Build the Contact Energy API client from the credentials stored inside the
    # config entry. Home Assistant stores sensitive config-entry data securely.
    api_client = ContactEnergyApi(
        email=entry.data.get("email"),
        password=entry.data.get("password"),
    )

    # Save the selected account ID onto the client instance so any later API
    # queries use the correct Contact Energy account instead of some other ID.
    api_client.account_id = entry.data.get("account_id")

    # ====== STARTUP AUTHENTICATION ======
    # Validate the saved credentials immediately on startup instead of waiting
    # for a later request to fail. This gives faster, clearer feedback if the
    # login no longer works.
    try:
        await api_client.authenticate()
    except ContactEnergyConnectionError as err:
        # Timeouts and network hiccups are temporary, so ask Home Assistant to
        # retry setup later instead of marking the entry as permanently failed.
        _LOGGER.warning(
            "Temporary connection error during setup for %s: %s. Will retry.",
            entry.title, err,
        )
        raise ConfigEntryNotReady(str(err)) from err
    except Exception as err:  # pragma: no cover - defensive guard
        # Any other failure (e.g. invalid credentials) is treated as permanent.
        _LOGGER.error("Authentication failed during setup for %s: %s", entry.title, err)
        return False

    # Read the contract ID needed for usage-data synchronization.
    # This is stored separately from email/account details because the usage
    # APIs need a contract-specific identifier.
    contract_id = entry.data.get("contract_id")

    # If the contract ID is missing, the integration can still start, but usage
    # synchronization will not be able to run normally.
    if not contract_id:
        _LOGGER.warning(
            "No contract_id found in config entry for %s. Usage sync will be disabled.",
            entry.title,
        )

        # Use a harmless fallback string so downstream code does not crash on a
        # missing value, even though usage sync is effectively unavailable.
        contract_id = "unknown"

    # ====== COORDINATOR CREATION ======
    # Create the shared coordinator object.
    # The coordinator is important because it centralizes update logic: instead
    # of every sensor calling the API separately, they all read from this one
    # shared manager.
    coordinator = ContactEnergyCoordinator(hass, api_client, contract_id, entry)

    # Perform the first refresh right away so the integration has real data
    # before Home Assistant finishes creating entities.
    await coordinator.async_config_entry_first_refresh()

    # ====== hass.data STORAGE ======
    # `hass.data` is Home Assistant's shared in-memory storage area.
    # The structure used here is:
    # hass.data[DOMAIN][entry.entry_id] = {
    #     "coordinator": <shared coordinator>,
    #     "api_client": <authenticated API client>,
    # }
    #
    # Why this matters:
    # - DOMAIN keeps Contact Energy data separate from other integrations.
    # - entry.entry_id keeps each configured account separate from other Contact
    #   Energy accounts.
    # - Storing these objects here lets sensors, services, and unload logic all
    #   find the same shared objects later.
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
    }

    # ====== PLATFORM LOADING ======
    # Ask Home Assistant to load every platform listed in PLATFORMS for this
    # config entry. In this integration that means loading the sensor platform,
    # which creates the actual entities visible in Home Assistant.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Ensure services are registered for this integration domain.
    # This is safe to call during each setup because async_setup_services checks
    # whether the service already exists before registering it again.
    await async_setup_services(hass)

    # Return True to tell Home Assistant the integration finished setup
    # successfully and is ready to use.
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one saved Contact Energy config entry.

    ====== WHAT UNLOADING MEANS ======
    In Home Assistant, "unloading" means shutting down an integration instance
    without shutting down Home Assistant itself.

    This happens when a user removes, disables, or reloads the config entry.
    The goal is to cleanly remove everything that was created during setup so no
    stale entities, background tasks, or stored references are left behind.

    ====== ENTITY CLEANUP OVERVIEW ======
    This function:
    1. Asks Home Assistant to unload all platforms for this config entry.
    2. Looks through the entity registry for entities created by that entry.
    3. Removes those entities from the registry.
    4. Deletes the integration's stored objects from hass.data.
    """
    # Import the entity registry helper here because it is only needed during
    # unload. The entity registry is Home Assistant's record of known entities.
    from homeassistant.helpers import entity_registry as er

    # Ask Home Assistant to unload all platforms tied to this config entry.
    # The walrus operator (`:=`) both stores the result in `unload_ok` and uses
    # it immediately in the condition below.
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Get the entity registry so we can inspect and remove entities created
        # by this specific Contact Energy config entry.
        entity_reg = er.async_get(hass)

        # Build a list of entity IDs that belong to this config entry.
        # We loop through the full registry and keep only entries whose
        # config_entry_id matches the entry currently being unloaded.
        entities_to_remove = [
            entity_id
            for entity_id, entry_obj in entity_reg.entities.items()
            if entry_obj.config_entry_id == entry.entry_id
        ]

        # Remove each entity one by one from the registry.
        # This cleanup prevents old entities from lingering after the
        # integration has been removed or reloaded.
        for entity_id in entities_to_remove:
            entity_reg.async_remove(entity_id)

        # Remove this config entry's shared objects from hass.data now that the
        # platforms and entities tied to them have been cleaned up.
        hass.data[DOMAIN].pop(entry.entry_id)

    # Return the unload result so Home Assistant knows whether cleanup succeeded.
    return unload_ok
