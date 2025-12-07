"""Contact Energy integration for Home Assistant."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from .api import ContactEnergyApi
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_ICP_NUMBER,
    CONF_USAGE_DAYS,
    CONF_USAGE_MONTHS,
    CONF_HISTORY_DAYS,
    CONF_HISTORY_MONTHS,
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
        "coordinator": None,
    }

    try:
        # Create API instance using email and password from config
        email = entry.data.get(CONF_EMAIL)
        password = entry.data.get(CONF_PASSWORD)

        # Get the Home Assistant aiohttp session
        session = async_get_clientsession(hass)

        # Get config values for coordinator
        account_id = entry.data.get(CONF_ACCOUNT_ID)
        contract_id = entry.data.get(CONF_CONTRACT_ID)
        icp_number = entry.data.get(CONF_ICP_NUMBER)
        
        # Determine history days - prefer months if available
        history_days = DEFAULT_HISTORY_DAYS
        if CONF_HISTORY_MONTHS in entry.data:
            months = entry.data.get(CONF_HISTORY_MONTHS)
            history_days = months * 30 if months else DEFAULT_HISTORY_DAYS
        elif CONF_HISTORY_DAYS in entry.data:
            history_days = entry.data.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS)

        # Create the data coordinator for this entry
        coordinator = ContactEnergyDataUpdateCoordinator(
            hass,
            email,
            password,
            account_id,
            contract_id,
            icp_number,
            history_days,
            session,  # Pass the session to the coordinator
        )
        
        # Initialize the coordinator (sets up API with session)
        await coordinator.async_init()
        
        _LOGGER.debug("Coordinator initialized for ICP: %s", icp_number)

        # Initial data fetch to populate coordinator
        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception as error:
            _LOGGER.error("Failed to refresh data from Contact Energy API: %s", error)
            _LOGGER.exception("Full traceback:")
            return False

        # Store in hass.data
        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

        # Forward entry setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Listen for configuration updates
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        # Schedule daily restart at 3:00 AM to refresh account details
        async def _schedule_restart(event: Event = None) -> None:
            """Schedule restart every day at 3:00 AM."""

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


# Add missing constant
DEFAULT_HISTORY_DAYS = 90


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
