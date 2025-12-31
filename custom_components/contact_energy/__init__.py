"""Contact Energy integration for Home Assistant.

This integration enables communication with the Contact Energy API to retrieve
energy consumption data and account information.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .contact_api import ContactEnergyApi
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

# List of platforms (sensors, binary_sensors, etc.) that this integration supports.
# Add sensor platform for account information sensors
PLATFORMS: list[Platform] = [Platform.SENSOR]


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
    # Set token from stored config entry to avoid re-authentication on first load
    api_client.token = entry.data.get("token")
    api_client.segment = entry.data.get("segment")
    api_client.bp = entry.data.get("bp")

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
    coordinator = ContactEnergyCoordinator(hass, api_client, contract_id)
    
    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and API client in the domain data
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api_client": api_client,
    }

    # Load all platforms defined in PLATFORMS for this config entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
    # Unload all platforms associated with this config entry
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # If unloading was successful, remove the entry's data from the domain
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
