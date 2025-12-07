"""Contact Energy integration for Home Assistant."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from .api import ContactEnergyApi
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_CONTRACT_ICP,
    CONF_USAGE_DAYS,
    CONF_USAGE_MONTHS,
    DATA_ACCOUNT,
    DOMAIN,
)
from .coordinator import ContactEnergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Contact Energy from a config entry."""
    # Initialize hass.data[DOMAIN] if not already done
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Store the config entry
    hass.data[DOMAIN][entry.entry_id] = {
        "api": None,
        "coordinator": None,
    }

    try:
        # Create API instance using email and password from config
        email = entry.data.get(CONF_EMAIL)
        password = entry.data.get(CONF_PASSWORD)

        api = ContactEnergyApi(email, password)

        # Test the connection by trying to authenticate
        try:
            await api.authenticate()
        except Exception as error:
            _LOGGER.error("Failed to authenticate with Contact Energy API: %s", error)
            return False

        # Create the data coordinator for this entry
        coordinator = ContactEnergyDataUpdateCoordinator(hass, api, entry)

        # Initial data fetch to populate coordinator
        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception as error:
            _LOGGER.error("Failed to refresh data from Contact Energy API: %s", error)
            return False

        # Store in hass.data
        hass.data[DOMAIN][entry.entry_id]["api"] = api
        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

        # Forward entry setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Listen for configuration updates
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        # Schedule daily restart at 3:00 AM to refresh account details
        async def _schedule_restart(event: Event) -> None:
            """Schedule restart every day at 3:00 AM."""

            @callback
            def _restart_at_3am(now: Optional[datetime] = None) -> None:
                """Restart the coordinator daily at 3:00 AM."""
                _LOGGER.debug(
                    "Daily restart triggered at 3:00 AM for entry %s", entry.entry_id
                )
                # Force a refresh of account details
                hass.async_create_task(coordinator._async_update_data())

            # Schedule to run at 3:00 AM every day
            async_track_time_change(
                hass, _restart_at_3am, hour=3, minute=0, second=0
            )

        # If HA is already running, schedule restart immediately
        if getattr(hass, "is_running", False):
            await _schedule_restart(None)
        else:
            # Otherwise wait for HA to start
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _schedule_restart)

        return True

    except Exception as error:
        _LOGGER.exception("Unexpected error during setup: %s", error)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove from hass.data
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Clean up if no more entries
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry when the user modifies options."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
