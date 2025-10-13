"""Contact Energy integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

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

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    # Set up sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Contact Energy integration setup complete for account %s (ICP: %s)",
        account_id,
        contract_icp,
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
