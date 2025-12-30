"""Data coordinator for Contact Energy integration.

This module provides the data coordinator that periodically fetches account
information from the Contact Energy API. Updates occur once per day at 01:00 AM
to minimize API calls while keeping account data current.
"""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .contact_api import ContactEnergyApi, ContactEnergyApiError

_LOGGER = logging.getLogger(__name__)


class ContactEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Contact Energy API data fetching.

    This coordinator handles periodic fetching of account information from the
    Contact Energy API. It's configured to update once per day at 01:00 AM to
    minimize API requests while keeping account data reasonably current.
    """

    def __init__(self, hass: HomeAssistant, api_client: ContactEnergyApi):
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            api_client: The Contact Energy API client for data retrieval.
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

    async def _async_update_data(self) -> dict:
        """Fetch account information from Contact Energy API.

        This method is called by the coordinator to refresh account data.
        It retrieves complete account information including balance, invoice
        details, next billing date, and contract information.

        If the stored token is invalid, it will re-authenticate using the stored
        credentials before fetching data.

        Returns:
            Dictionary containing the account data.

        Raises:
            UpdateFailed: If the API request fails.
        """
        try:
            _LOGGER.debug("Fetching account information from Contact Energy API")
            
            # Try to get accounts with current token
            try:
                account_data = await self.api_client.get_accounts()
                _LOGGER.debug("Successfully fetched account data")
                return account_data
            
            except Exception as auth_error:
                # If we get a 401/403 or authentication error, re-authenticate
                # This handles cases where the stored token has expired
                _LOGGER.warning(f"Initial fetch failed, re-authenticating: {str(auth_error)}")
                
                # Re-authenticate to get a fresh token
                await self.api_client.authenticate()
                
                # Retry fetching account data with the new token
                account_data = await self.api_client.get_accounts()
                _LOGGER.debug("Successfully fetched account data after re-authentication")
                return account_data

        except ContactEnergyApiError as e:
            # API returned an error - convert to UpdateFailed for coordinator handling
            _LOGGER.error(f"API error during data update: {str(e)}")
            raise UpdateFailed(f"API error: {str(e)}") from e

        except Exception as e:
            # Unexpected error - log and raise UpdateFailed
            _LOGGER.exception(f"Unexpected error during data update: {e}")
            raise UpdateFailed(f"Unexpected error: {str(e)}") from e
