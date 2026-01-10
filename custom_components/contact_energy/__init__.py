"""Contact Energy integration for Home Assistant.

This integration enables communication with the Contact Energy API to retrieve
energy consumption data and account information.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .contact_api import ContactEnergyApi
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

# List of platforms (sensors, binary_sensors, etc.) that this integration supports.
# Add sensor platform for account information sensors
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Contact Energy integration."""
    
    async def handle_refresh_data(call: ServiceCall) -> None:
        """Handle the refresh_data service call."""
        _LOGGER.info("Manual data refresh requested via service call")
        
        # Refresh all configured entries
        for entry_id, entry_data in hass.data[DOMAIN].items():
            coordinator = entry_data.get("coordinator")
            api_client = entry_data.get("api_client")
            if coordinator:
                now = datetime.now(timezone.utc)
                lock_until = entry_data.get("sync_lock_until")
                sync_in_progress = entry_data.get("sync_in_progress", False)

                # Block manual refresh if a sync is active or within cool-down
                if (lock_until and now < lock_until) or sync_in_progress:
                    wait_seconds = 60
                    message = (
                        "Manual refresh cannot run right now because a sync is active "
                        "or just finished. Please try again in 60s."
                    )
                    # Surface a gentle notice without raising to avoid UI errors
                    _LOGGER.info("%s (entry=%s)", message, entry_id)
                    return

                # Mark sync as in-progress and set cool-down window
                entry_data["sync_in_progress"] = True
                entry_data["sync_lock_until"] = now + timedelta(seconds=30)
                
                _LOGGER.info(f"Forcing data refresh for entry {entry_id}")

                # Ensure the coordinator does not start a background usage sync; we'll run one explicitly
                coordinator._skip_next_usage_sync = True

                # Always re-authenticate with username/password before a manual refresh
                # to avoid relying on short-lived/expired tokens.
                if api_client:
                    try:
                        _LOGGER.debug(
                            "Manual refresh re-authenticating as %s for entry %s",
                            api_client.email,
                            entry_id,
                        )
                        await api_client.authenticate()
                    except Exception as err:
                        _LOGGER.error(
                            "Manual refresh re-authentication failed for entry %s: %s",
                            entry_id,
                            err,
                        )
                        # Skip the refresh for this entry if we cannot log in
                        continue

                try:
                    # Force account data refresh
                    await coordinator.async_request_refresh()
                    # Force usage sync (bypass time thresholds) - single run
                    if hasattr(coordinator, 'usage_coordinator'):
                        await coordinator.usage_coordinator.force_sync()
                finally:
                    coordinator._skip_next_usage_sync = False
                    # Release the in-progress flag but keep the cool-down until expiry
                    entry_data["sync_in_progress"] = False
    
    # Register the service only once
    if not hass.services.has_service(DOMAIN, "refresh_data"):
        hass.services.async_register(
            DOMAIN,
            "refresh_data",
            handle_refresh_data,
            schema=vol.Schema({}),
        )
        _LOGGER.info("Registered refresh_data service")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Contact Energy from a config entry.

    This function is called when a user adds a Contact Energy integration through
    the Home Assistant UI. It initializes the integration, creates the API client,
    sets up the data coordinator, and loads all required platforms.

    The coordinator fetches account information once per day at approximately 01:00 AM
    to minimize API requests while keeping data reasonably current.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry created by the user during configuration.

    Returns:
        True if setup was successful, False otherwise.
    """
    # Initialize the data dictionary for this domain if it doesn't exist
    hass.data.setdefault(DOMAIN, {})
    
    # Check if password is present (needed for token refresh)
    # Configs from v1.0.0 and earlier may not have password stored
    if "password" not in entry.data:
        _LOGGER.warning(
            f"Contact Energy config entry {entry.entry_id} is missing password. "
            "This is required for token refresh. Please reconfigure the integration."
        )
        # Show a repair notification for the user
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import", "title_placeholders": {"name": entry.title}},
                data=entry.data,
            )
        )
        return False
    
    # Create API client with stored credentials
    # Home Assistant automatically encrypts sensitive data in config entries
    api_client = ContactEnergyApi(
        email=entry.data.get("email"),
        password=entry.data.get("password"),
    )
    # Keep the account_id on the client so ba queries use the correct value (not BP)
    api_client.account_id = entry.data.get("account_id")

    # Always authenticate on startup to avoid reusing expired tokens from config entry
    try:
        await api_client.authenticate()
    except Exception as err:  # pragma: no cover - defensive guard
        _LOGGER.error("Authentication failed during setup for %s: %s", entry.title, err)
        return False

    # Get contract_id for usage data sync (Phase 1 / v1.4.0)
    contract_id = entry.data.get("contract_id")
    if not contract_id:
        _LOGGER.warning(
            "No contract_id found in config entry for %s. Usage sync will be disabled.",
            entry.title
        )
        contract_id = "unknown"  # Fallback to prevent crashes

    # Create data coordinator for fetching account information
    # Updates once per day - Home Assistant schedules at the closest possible time to 01:00
    coordinator = ContactEnergyCoordinator(hass, api_client, contract_id, entry)
    
    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and API client in the domain data
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
    }

    # Load all platforms defined in PLATFORMS for this config entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await async_setup_services(hass)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    This function is called when a user removes a Contact Energy integration from
    Home Assistant. It cleans up all platforms and resources associated with the
    config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being removed.

    Returns:
        True if unload was successful, False otherwise.
    """
    from homeassistant.helpers import entity_registry as er
    
    # Unload all platforms associated with this config entry
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Get the entity registry and remove all entities for this config entry
        entity_reg = er.async_get(hass)
        entities_to_remove = [
            entity_id for entity_id, entry_obj in entity_reg.entities.items()
            if entry_obj.config_entry_id == entry.entry_id
        ]
        for entity_id in entities_to_remove:
            entity_reg.async_remove(entity_id)
        
        # If unloading was successful, remove the entry's data from the domain
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
