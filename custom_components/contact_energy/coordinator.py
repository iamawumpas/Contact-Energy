"""DataUpdateCoordinator for Contact Energy integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ContactEnergyApi, InvalidAuth, CannotConnect
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class ContactEnergyCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Contact Energy data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ContactEnergyApi,
        account_id: str,
        contract_id: str,
        contract_icp: str,
        usage_days: int = 30,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.account_id = account_id
        self.contract_id = contract_id
        self.contract_icp = contract_icp
        self.usage_days = usage_days
        self._account_lock = asyncio.Lock()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Contact Energy."""
        _LOGGER.warning("Starting coordinator _async_update_data")

        try:
            # Ensure we're logged in
            if not self.api._api_token:
                _LOGGER.warning("No API token, attempting login")
                if not await self.api.async_login():
                    raise UpdateFailed("Failed to authenticate with Contact Energy")

            # Fetch account data (for billing, balance, etc.)
            _LOGGER.warning("About to fetch account details")
            async with self._account_lock:
                account_data = await self.api.async_get_account_details()
            
            _LOGGER.warning("Received account_data type: %s", type(account_data))
            if not account_data or not isinstance(account_data, dict):
                _LOGGER.error("Failed to fetch account data: received %s", account_data)
                raise UpdateFailed("Failed to fetch account data")

            _LOGGER.debug("Successfully fetched account data")
            _LOGGER.debug("Account data keys: %s", list(account_data.keys()) if isinstance(account_data, dict) else "Not a dict")
            
            # Log full structure for debugging
            _LOGGER.info("Full account data structure for debugging: %s", account_data)
            
            # Extract accountDetail from response (API returns {'accountDetail': {...}})
            account_details = account_data.get("accountDetail", {})
            _LOGGER.warning("COORDINATOR: Got account_details with %d keys: %s", 
                          len(account_details), list(account_details.keys()) if account_details else "Empty")
            
            # If accountDetail is empty, maybe the structure is different
            if not account_details:
                _LOGGER.error("COORDINATOR: No 'accountDetail' found in API response keys: %s", list(account_data.keys()))
                # Don't fail, just return empty details
                account_details = {}
            
            # Return data structure for coordinator (match what sensors expect)
            coordinator_data = {
                "account_details": account_details,
                "last_update": datetime.utcnow(),  # Use utcnow to avoid timezone issues
                "account_id": self.account_id,
                "contract_id": self.contract_id,
                "contract_icp": self.contract_icp,
            }
            _LOGGER.error("COORDINATOR: Returning coordinator_data with keys: %s", list(coordinator_data.keys()))
            _LOGGER.error("COORDINATOR: account_details size: %d", len(account_details))
            return coordinator_data

        except InvalidAuth as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Failed to connect to Contact Energy: {err}") from err
        except Exception as err:
            _LOGGER.exception("COORDINATOR EXCEPTION: Error fetching data from Contact Energy: %s", err)
            _LOGGER.error("Exception type: %s", type(err).__name__)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
