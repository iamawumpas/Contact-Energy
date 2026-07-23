"""Contact Energy integration for Home Assistant.

This integration enables communication with the Contact Energy API to retrieve
energy consumption data and account information.

Version: 2.0.0 - Refactored modular architecture
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .api import ContactEnergyApiClient, ContactEnergyAccountApi, ContactEnergyUsageApi
from .coordinators import AccountCoordinator, UsageCoordinatorV2

_LOGGER = logging.getLogger(__name__)

# List of platforms (sensors, binary_sensors, etc.) that this integration supports.
# Add sensor platform for account information sensors
PLATFORMS: list[Platform] = [Platform.SENSOR]


def _sanitize_address(address: str) -> str:
    """Sanitize address for use in cache file names.
    
    Removes special characters and spaces, keeping only alphanumeric characters,
    hyphens, and underscores. Used for cache file naming.
    
    Args:
        address: Raw address string from user
        
    Returns:
        Sanitized address string safe for file names
    """
    # Remove special characters, keep alphanumeric, hyphens, underscores
    sanitized = re.sub(r'[^\w\-]', '_', address)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    return sanitized.strip('_').lower()


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Contact Energy integration."""
    
    async def handle_refresh_data(call: ServiceCall) -> None:
        """Handle the refresh_data service call."""
        _LOGGER.info("Manual data refresh requested via service call")
        
        # Refresh all configured entries
        for entry_id, entry_data in hass.data[DOMAIN].items():
            account_coordinator = entry_data.get("account_coordinator")
            usage_coordinator = entry_data.get("usage_coordinator")
            api_client = entry_data.get("api_client")
            
            if account_coordinator:
                now = datetime.now(timezone.utc)
                lock_until = entry_data.get("sync_lock_until")
                sync_in_progress = entry_data.get("sync_in_progress", False)

                # Block manual refresh if a sync is active or within cool-down
                if (lock_until and now < lock_until) or sync_in_progress:
                    message = (
                        "Manual refresh cannot run right now because a sync is active "
                        "or just finished. Please try again in 60s."
                    )
                    _LOGGER.info("%s (entry=%s)", message, entry_id)
                    return

                # Mark sync as in-progress and set cool-down window
                entry_data["sync_in_progress"] = True
                entry_data["sync_lock_until"] = now + timedelta(seconds=30)
                
                _LOGGER.info(f"Forcing data refresh for entry {entry_id}")

                try:
                    # Always re-authenticate with username/password before a manual refresh
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
                            continue

                    # Force account data refresh
                    await account_coordinator.async_request_refresh()
                    
                    # Force usage data refresh
                    if usage_coordinator:
                        await usage_coordinator.force_sync()
                finally:
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
    the Home Assistant UI. It initializes the integration, creates the API clients,
    sets up the data coordinators, and loads all required platforms.
    
    Version: 2.0.0 - Uses modular architecture with separate API, data managers,
    and coordinators.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry created by the user during configuration.

    Returns:
        True if setup was successful, False otherwise.
    """
    # Initialize the data dictionary for this domain if it doesn't exist
    hass.data.setdefault(DOMAIN, {})
    
    # Check if password is present (needed for token refresh)
    if "password" not in entry.data:
        _LOGGER.warning(
            f"Contact Energy config entry {entry.entry_id} is missing password. "
            "This is required for token refresh. Please reconfigure the integration."
        )
        return False
    
    # Get configuration data
    email = entry.data.get("email")
    password = entry.data.get("password")
    account_id = entry.data.get("account_id")
    contract_id = entry.data.get("contract_id")
    icp = entry.data.get("icp", "unknown")
    account_nickname = entry.data.get("account_nickname", "Unknown")
    
    # Sanitize address for cache file naming
    address = _sanitize_address(account_nickname)
    
    # Create base API client
    api_client = ContactEnergyApiClient(email, password)
    api_client.account_id = account_id
    
    # Always authenticate on startup to avoid reusing expired tokens
    try:
        await api_client.authenticate()
        _LOGGER.info("Successfully authenticated for %s", account_nickname)
    except Exception as err:
        _LOGGER.error("Authentication failed during setup for %s: %s", entry.title, err)
        return False

    # Create specialized API clients
    account_api = ContactEnergyAccountApi(email, password)
    account_api.account_id = account_id
    account_api.token = api_client.token
    account_api.segment = api_client.segment
    account_api.bp = api_client.bp
    
    usage_api = ContactEnergyUsageApi(email, password)
    usage_api.account_id = account_id
    usage_api.token = api_client.token
    usage_api.segment = api_client.segment
    usage_api.bp = api_client.bp
    
    # Create account coordinator
    account_coordinator = AccountCoordinator(
        hass,
        account_api,
        address,
        icp,
        account_id,
    )
    
    # Perform initial account data fetch
    await account_coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Account coordinator initialized for %s", account_nickname)
    
    # Create usage coordinator if contract_id is available
    usage_coordinator = None
    if contract_id and contract_id != "unknown":
        usage_coordinator = UsageCoordinatorV2(
            hass,
            usage_api,
            contract_id,
            address,
            icp,
        )
        
        # Set up usage coordinator and load caches
        await usage_coordinator.async_setup()
        
        # Perform initial usage data sync
        await usage_coordinator.force_sync()
        _LOGGER.info("Usage coordinator initialized for contract %s", contract_id)
    else:
        _LOGGER.warning(
            "No contract_id found in config entry for %s. Usage data will be unavailable.",
            entry.title
        )

    # Store coordinators and API clients in the domain data
    hass.data[DOMAIN][entry.entry_id] = {
        "account_coordinator": account_coordinator,
        "usage_coordinator": usage_coordinator,
        "api_client": api_client,
        "account_api": account_api,
        "usage_api": usage_api,
        "address": address,
        "icp": icp,
        "contract_id": contract_id,
    }

    # Load all platforms defined in PLATFORMS for this config entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await async_setup_services(hass)
    
    _LOGGER.info("Contact Energy integration v2.0.0 setup complete for %s", entry.title)
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
