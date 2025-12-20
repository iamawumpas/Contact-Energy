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
    _LOGGER.info("=" * 70)
    _LOGGER.info("🔧 Setting up Contact Energy integration")
    _LOGGER.info("=" * 70)
    _LOGGER.debug("Entry ID: %s, Title: %s", entry.entry_id, entry.title)
    
    # Initialize hass.data[DOMAIN] if not already done
    if DOMAIN not in hass.data:
        _LOGGER.debug("Initializing hass.data[DOMAIN]")
        hass.data[DOMAIN] = {}

    # Store the config entry
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": None,
    }

    try:
        # Create API instance using email and password from config
        email = entry.data.get(CONF_EMAIL)
        password = entry.data.get(CONF_PASSWORD)
        _LOGGER.debug("👤 Email: %s, Password length: %d", email, len(password) if password else 0)

        # Get the Home Assistant aiohttp session
        _LOGGER.debug("🌐 Getting aiohttp session")
        session = async_get_clientsession(hass)
        _LOGGER.debug("  ✓ Session obtained: %s", type(session).__name__)

        # Get config values for coordinator
        account_id = entry.data.get(CONF_ACCOUNT_ID)
        contract_id = entry.data.get(CONF_CONTRACT_ID)
        icp_number = entry.data.get(CONF_ICP_NUMBER)
        _LOGGER.info("📋 Configuration loaded:")
        _LOGGER.info("  - Account ID: %s", account_id)
        _LOGGER.info("  - Contract ID: %s", contract_id)
        _LOGGER.info("  - ICP: %s", icp_number)
        
        # Determine history days - prefer months if available
        history_days = DEFAULT_HISTORY_DAYS
        if CONF_HISTORY_MONTHS in entry.data:
            months = entry.data.get(CONF_HISTORY_MONTHS)
            history_days = months * 30 if months else DEFAULT_HISTORY_DAYS
            _LOGGER.info("  - History: %d months (%d days)", months, history_days)
        elif CONF_HISTORY_DAYS in entry.data:
            history_days = entry.data.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS)
            _LOGGER.info("  - History: %d days", history_days)

        # Create the data coordinator for this entry
        _LOGGER.debug("Creating ContactEnergyDataUpdateCoordinator...")
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
        _LOGGER.debug("Initializing coordinator...")
        await coordinator.async_init()
        _LOGGER.info("✓ Coordinator initialized for ICP: %s", icp_number)

        # Initial data fetch to populate coordinator
        _LOGGER.info("📡 Starting first data refresh (may take a moment)...")
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.info("✓ First refresh completed successfully")
        except Exception as error:
            _LOGGER.error("=" * 70)
            _LOGGER.error("❌ Failed to refresh data from Contact Energy API")
            _LOGGER.error("=" * 70)
            _LOGGER.error("Error: %s", error)
            _LOGGER.exception("Full traceback:")
            return False

        # Store in hass.data
        _LOGGER.debug("Storing coordinator in hass.data")
        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

        # Forward entry setup to platforms
        _LOGGER.debug("🔌 Forwarding entry setup to platforms: %s", PLATFORMS)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("✓ Platform setup completed")

        # Listen for configuration updates
        _LOGGER.debug("Setting up update listener")
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        # Schedule daily restart at 3:00 AM to refresh account details
        async def _schedule_restart(event: Event = None) -> None:
            """Schedule restart every day at 3:00 AM."""
            _LOGGER.debug("Setting up daily 3:00 AM restart schedule")

            def _restart_at_3am(now: Optional[datetime] = None) -> None:
                """Restart the coordinator daily at 3:00 AM."""
                _LOGGER.info("⏰ Daily restart triggered at 3:00 AM for ICP: %s", 
                           icp_number)
                # Force a refresh of account details
                hass.async_create_task(coordinator._async_update_data())

            # Schedule to run at 3:00 AM every day
            async_track_time_change(
                hass, _restart_at_3am, hour=3, minute=0, second=0
            )
            _LOGGER.debug("✓ Daily restart schedule configured")

        # If HA is already running, schedule restart immediately
        if getattr(hass, "is_running", False):
            _LOGGER.debug("Home Assistant is running, scheduling restart now")
            await _schedule_restart(None)
        else:
            # Otherwise wait for HA to start
            _LOGGER.debug("Home Assistant not running yet, will schedule on start")
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _schedule_restart)

        _LOGGER.info("=" * 70)
        _LOGGER.info("✓ Contact Energy setup COMPLETED for %s", entry.title)
        _LOGGER.info("=" * 70)
        return True

    except Exception as error:
        _LOGGER.error("=" * 70)
        _LOGGER.error("❌ Unexpected error during setup")
        _LOGGER.error("=" * 70)
        _LOGGER.exception("Error details: %s", error)
        return False


# Add missing constant
DEFAULT_HISTORY_DAYS = 90


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry: %s", entry.title)
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug("Platform unload result: %s", unload_ok)

    if unload_ok:
        # Remove from hass.data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.debug("Removed entry from hass.data")

        # Clean up if no more entries
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            _LOGGER.debug("Removed DOMAIN from hass.data (no more entries)")

    _LOGGER.info("Entry unloaded: %s (success: %s)", entry.title, unload_ok)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry when the user modifies options."""
    _LOGGER.debug("Reloading entry: %s", entry.title)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
