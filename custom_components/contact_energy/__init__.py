"""Contact Energy integration for Home Assistant.

This integration enables communication with the Contact Energy API to retrieve
energy consumption data and account information.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Define the unique domain identifier for this integration
DOMAIN = "contact_energy"

# List of platforms (sensors, binary_sensors, etc.) that this integration supports.
# Platforms are added here as they are implemented.
PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Contact Energy from a config entry.

    This function is called when a user adds a Contact Energy integration through
    the Home Assistant UI. It initializes the integration and sets up any required
    platforms (sensors, switches, etc.).

    Args:
        hass: The Home Assistant instance.
        entry: The config entry created by the user during configuration.

    Returns:
        True if setup was successful, False otherwise.
    """
    # Initialize the data dictionary for this domain if it doesn't exist
    hass.data.setdefault(DOMAIN, {})
    # Create an entry for this specific config instance
    hass.data[DOMAIN][entry.entry_id] = {}

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
