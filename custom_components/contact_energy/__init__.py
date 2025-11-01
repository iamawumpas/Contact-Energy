"""Contact Energy integration for Home Assistant."""
from __future__ import annotations

import logging
import random
from datetime import datetime, time, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .api import ContactEnergyApi
from .coordinator import ContactEnergyCoordinator
from .const import (
    DOMAIN,
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_CONTRACT_ICP,
    CONF_USAGE_DAYS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Daily restart time: 3am +/- 30 minutes
RESTART_HOUR = 3
RESTART_MINUTE_VARIANCE = 30

async def _calculate_next_restart_time() -> tuple[int, int]:
    """Calculate the next restart time (hour, minute) with random variance."""
    # Add random variance of +/- 30 minutes to 3am
    variance = random.randint(-RESTART_MINUTE_VARIANCE, RESTART_MINUTE_VARIANCE)
    target_time = datetime.now().replace(hour=RESTART_HOUR, minute=0, second=0, microsecond=0)
    target_time += timedelta(minutes=variance)
    return target_time.hour, target_time.minute

async def _handle_daily_restart(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle the daily restart of the integration."""
    _LOGGER.info("Contact Energy: Starting daily restart at 3am")
    
    # Unload the integration
    await async_unload_entry(hass, entry)
    
    # Wait a moment for cleanup
    await hass.async_add_executor_job(lambda: None)
    
    # Reload the integration
    await async_setup_entry(hass, entry)
    
    _LOGGER.info("Contact Energy: Daily restart complete")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Contact Energy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Extract configuration
    email = entry.data["email"]
    password = entry.data["password"]
    account_id = entry.data[CONF_ACCOUNT_ID]
    contract_id = entry.data[CONF_CONTRACT_ID]
    contract_icp = entry.data[CONF_CONTRACT_ICP]
    usage_days = entry.data.get(CONF_USAGE_DAYS, 30)

    # Create API instance
    api = ContactEnergyApi(hass, email, password)

    # Create coordinator with 8-hour polling interval
    coordinator = ContactEnergyCoordinator(
        hass,
        api,
        account_id,
        contract_id,
        contract_icp,
        usage_days,
    )

    # Perform initial data fetch without blocking setup
    hass.async_create_task(coordinator.async_config_entry_first_refresh())

    # Calculate random restart time around 3am
    restart_hour, restart_minute = await _calculate_next_restart_time()
    
    # Schedule daily restart at 3am +/- 30 minutes
    # Use an async callback to avoid creating tasks from non-event-loop threads
    async def _on_scheduled_restart(now: datetime) -> None:
        await _handle_daily_restart(hass, entry)

    restart_cancel = async_track_time_change(
        hass,
        _on_scheduled_restart,
        hour=restart_hour,
        minute=restart_minute,
        second=0,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "restart_cancel": restart_cancel,
    }

    # Set up sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Contact Energy integration setup complete for account %s (ICP: %s). Daily restart scheduled at %02d:%02d",
        account_id,
        contract_icp,
        restart_hour,
        restart_minute,
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Cancel the daily restart timer if it exists
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    if restart_cancel := entry_data.get("restart_cancel"):
        restart_cancel()
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
