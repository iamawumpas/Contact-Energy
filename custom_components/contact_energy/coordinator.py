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
        _LOGGER.debug("Fetching data from Contact Energy API")

        try:
            # Ensure we're logged in
            if not self.api._api_token:
                if not await self.api.async_login():
                    raise UpdateFailed("Failed to authenticate with Contact Energy")

            # Fetch account data (for billing, balance, etc.)
            async with self._account_lock:
                account_data = await self.api._request(
                    "GET",
                    f"{self.api._url_base}/accounts/v2",
                    headers=self.api._headers(),
                )
                
            if not account_data or not isinstance(account_data, dict):
                raise UpdateFailed("Failed to fetch account data")

            _LOGGER.debug("Successfully fetched account data")
            _LOGGER.debug("Account data keys: %s", list(account_data.keys()) if isinstance(account_data, dict) else "Not a dict")
            
            # Extract accountDetail from response (API returns {'accountDetail': {...}})
            account_details = account_data.get("accountDetail", {})
            _LOGGER.debug("Account details keys: %s", list(account_details.keys()) if isinstance(account_details, dict) else "Not a dict")
            
            # Return data structure for coordinator (match what sensors expect)
            return {
                "account_details": account_details,
                "last_update": datetime.now(),
                "account_id": self.account_id,
                "contract_id": self.contract_id,
                "contract_icp": self.contract_icp,
            }

        except InvalidAuth as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Failed to connect to Contact Energy: {err}") from err
        except Exception as err:
            _LOGGER.exception("Error fetching data from Contact Energy")
            raise UpdateFailed(f"Error communicating with API: {err}") from err
