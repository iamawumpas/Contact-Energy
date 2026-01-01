"""Data coordinator for Contact Energy integration.

This module provides the data coordinator that periodically fetches account
information from the Contact Energy API. Updates occur once per day at 01:00 AM
to minimize API calls while keeping account data current.

Version: 1.4.0
Changes: Added usage data synchronization via UsageCoordinator
"""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .contact_api import ContactEnergyApi, ContactEnergyApiError
from .usage_coordinator import UsageCoordinator

_LOGGER = logging.getLogger(__name__)


class ContactEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Contact Energy API data fetching.

    This coordinator handles periodic fetching of account information from the
    Contact Energy API. It's configured to update once per day at 01:00 AM to
    minimize API requests while keeping account data reasonably current.
    
    Additionally, it triggers usage data synchronization as a background task
    via the UsageCoordinator (Phase 1 / v1.4.0).
    """

    def __init__(self, hass: HomeAssistant, api_client: ContactEnergyApi, contract_id: str):
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            api_client: The Contact Energy API client for data retrieval.
            contract_id: Contract identifier for usage data sync.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Update once per day - Home Assistant will schedule this at the
            # earliest possible time after 01:00 AM
            update_interval=timedelta(days=1),
        )
        self.api_client = api_client
        self.contract_id = contract_id
        
        # Initialize usage coordinator (Phase 1 / v1.4.0)
        # This handles background syncing of hourly/daily/monthly usage data
        self.usage_coordinator = UsageCoordinator(hass, api_client, contract_id)
        
        _LOGGER.debug(
            "ContactEnergyCoordinator initialized with usage sync for contract %s",
            contract_id
        )

    async def _async_update_data(self) -> dict:
        """Fetch account information from Contact Energy API.

        This method is called by the coordinator to refresh account data.
        It retrieves complete account information including balance, invoice
        details, next billing date, and contract information.

        If the stored token is invalid, it will re-authenticate using the stored
        credentials before fetching data.
        
        Additionally, triggers usage data sync as a background task (non-blocking).
        Usage sync failures do not affect account data updates.
        
        NOTE: If account data fetch fails after 2 retries, the integration will
        continue with usage sync using the known contract ID. This allows basic
        functionality when the accounts endpoint is experiencing server issues.

        Returns:
            Dictionary containing the account data, or a minimal dict if fetch fails.

        Raises:
            UpdateFailed: If unable to authenticate or get token.
        """
        try:
            _LOGGER.debug("Fetching account information from Contact Energy API")
            
            # Try to get accounts with current token
            try:
                account_data = await self.api_client.get_accounts()
                _LOGGER.debug("Successfully fetched account data")
                
                # Trigger usage sync as background task (Phase 1 / v1.4.0)
                # This runs independently and doesn't block account data updates
                # Usage sync errors are logged but don't fail the coordinator
                _LOGGER.debug("Triggering background usage sync for contract %s", self.contract_id)
                self.hass.async_create_task(
                    self._async_sync_usage(),
                    name=f"usage_sync_{self.contract_id}"
                )
                
                return account_data
            
            except Exception as auth_error:
                # If we get a 401/403 or authentication error, re-authenticate
                # This handles cases where the stored token has expired
                error_str = str(auth_error)
                _LOGGER.warning(f"Initial fetch failed, re-authenticating: {error_str}")
                
                # Check if password is available
                if not self.api_client.password:
                    _LOGGER.error("Cannot re-authenticate: password not stored in config entry")
                    raise UpdateFailed("Password not available for re-authentication. Please reconfigure the integration.")
                
                # Re-authenticate to get a fresh token
                try:
                    _LOGGER.debug(f"Attempting to re-authenticate as {self.api_client.email}")
                    await self.api_client.authenticate()
                    _LOGGER.debug("Successfully re-authenticated")
                except Exception as auth_err:
                    _LOGGER.error(f"Re-authentication failed: {str(auth_err)}")
                    raise UpdateFailed(f"Re-authentication failed: {str(auth_err)}") from auth_err
                
                # Retry fetching account data with the new token
                try:
                    account_data = await self.api_client.get_accounts()
                    _LOGGER.debug("Successfully fetched account data after re-authentication")
                    
                    # Trigger usage sync after successful re-auth (Phase 1 / v1.4.0)
                    _LOGGER.debug("Triggering background usage sync for contract %s (after re-auth)", self.contract_id)
                    self.hass.async_create_task(
                        self._async_sync_usage(),
                        name=f"usage_sync_{self.contract_id}"
                    )
                    
                    return account_data
                    
                except Exception as retry_error:
                    # Account data fetch failed even after re-auth
                    # Log the error but continue with usage sync using known contract ID
                    _LOGGER.warning(
                        f"Account fetch failed after re-authentication: {str(retry_error)}. "
                        "Proceeding with usage sync only using contract ID {self.contract_id}"
                    )
                    
                    # Still trigger usage sync as it doesn't need account data
                    _LOGGER.debug("Triggering background usage sync for contract %s (fallback mode)", self.contract_id)
                    self.hass.async_create_task(
                        self._async_sync_usage(),
                        name=f"usage_sync_{self.contract_id}"
                    )
                    
                    # Return minimal account data structure to keep coordinator happy
                    # The sensor will still work with usage data even if account info is unavailable
                    return {
                        "accountsSummary": [{
                            "id": "",
                            "nickname": "Unknown Account",
                            "contracts": [{"contractId": self.contract_id}]
                        }]
                    }

        except ContactEnergyApiError as e:
            # API returned an error - convert to UpdateFailed for coordinator handling
            _LOGGER.error(f"API error during data update: {str(e)}")
            raise UpdateFailed(f"API error: {str(e)}") from e

        except Exception as e:
            # Unexpected error - log and raise UpdateFailed
            _LOGGER.exception(f"Unexpected error during data update: {e}")
            raise UpdateFailed(f"Unexpected error: {str(e)}") from e
    
    async def _async_sync_usage(self) -> None:
        """Background task to sync usage data.
        
        This method runs as a background task and syncs hourly/daily/monthly
        usage data via the UsageCoordinator. Errors are caught and logged
        to prevent breaking the main coordinator.
        
        Note: This is a Phase 1 (v1.4.0) feature - usage data download and caching only.
              Sensor exposure will come in Phase 2 (v1.5.0).
        """
        try:
            _LOGGER.debug("Starting background usage sync task for contract %s", self.contract_id)
            await self.usage_coordinator.async_sync_usage()
            _LOGGER.debug("Background usage sync task completed for contract %s", self.contract_id)
        except Exception as e:
            # Log errors but don't propagate - usage sync failures shouldn't break account data
            _LOGGER.error(
                "Background usage sync failed for contract %s: %s",
                self.contract_id, str(e), exc_info=True
            )
