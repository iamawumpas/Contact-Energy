"""Contact Energy integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .api import ContactEnergyApi
from .const import DOMAIN, CONF_USAGE_DAYS, CONF_ACCOUNT_ID, CONF_CONTRACT_ID, CONF_CONTRACT_ICP
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Contact Energy from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Extract configuration
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    usage_days = entry.data.get(CONF_USAGE_DAYS, 30)
    account_id = entry.data[CONF_ACCOUNT_ID]
    contract_id = entry.data[CONF_CONTRACT_ID]
    contract_icp = entry.data[CONF_CONTRACT_ICP]

    # Create API client
    api = ContactEnergyApi(hass, email, password)

    # Create and set up coordinator
    coordinator = ContactEnergyCoordinator(
        hass=hass,
        api=api,
        email=email,
        usage_days=usage_days,
        account_id=account_id,
        contract_id=contract_id,
        contract_icp=contract_icp,
    )

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and API
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Contact Energy integration set up successfully for %s (%s)",
        contract_icp,
        email
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Contact Energy integration unloaded successfully")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)