"""Contact Energy API client."""
import asyncio
import logging
from datetime import datetime, date
from typing import Any, Optional, Dict, List
import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE_URL, API_KEY

_LOGGER = logging.getLogger(__name__)


class ContactEnergyApiError(HomeAssistantError):
    """Base API error."""


class AuthenticationError(ContactEnergyApiError):
    """Authentication failed."""


class ConnectionError(ContactEnergyApiError):
    """Connection failed."""


class ContactEnergyApi:
    """Contact Energy API client."""

    def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
        """Initialize the API client."""
        self._hass = hass
        self._email = email
        self._password = password
        self._session = async_get_clientsession(hass)
        self._token = None
        self._account_id = None
        self._contract_id = None
        self._contract_icp = None
        
    @property
    def account_id(self) -> str:
        """Return account ID."""
        return self._account_id
        
    @property
    def contract_id(self) -> str:
        """Return contract ID."""
        return self._contract_id
        
    @property 
    def contract_icp(self) -> str:
        """Return contract ICP."""
        return self._contract_icp

    def _get_headers(self, include_token: bool = True) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"x-api-key": API_KEY}
        if include_token and self._token:
            headers["session"] = self._token
        return headers

    async def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make an API request with error handling."""
        try:
            async with async_timeout.timeout(30):
                async with self._session.request(method, url, **kwargs) as response:
                    _LOGGER.debug("API request to %s returned status %s", url, response.status)
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        self._token = None  # Clear invalid token
                        raise AuthenticationError("Authentication failed")
                    else:
                        _LOGGER.error("API request failed with status %s", response.status)
                        return None
                        
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout during API request to %s", url)
            raise ConnectionError("Request timeout") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Client error during API request: %s", err)
            raise ConnectionError(f"Client error: {err}") from err

    async def authenticate(self) -> bool:
        """Authenticate with Contact Energy API."""
        _LOGGER.debug("Attempting authentication for %s", self._email)
        
        data = {"username": self._email, "password": self._password}
        
        try:
            result = await self._make_request(
                "POST",
                f"{API_BASE_URL}/login/v2",
                json=data,
                headers=self._get_headers(include_token=False)
            )
            
            if result and "token" in result:
                self._token = result["token"]
                _LOGGER.debug("Authentication successful")
                return True
                
            _LOGGER.error("Authentication failed: invalid response")
            return False
            
        except ContactEnergyApiError:
            _LOGGER.error("Authentication failed")
            return False

    async def get_accounts(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        if not self._token and not await self.authenticate():
            raise AuthenticationError("Failed to authenticate")

        try:
            data = await self._make_request(
                "GET",
                f"{API_BASE_URL}/accounts/v2",
                headers=self._get_headers()
            )
            
            if data and "accountDetail" in data:
                # Extract and store account/contract details
                account_detail = data["accountDetail"]
                self._account_id = account_detail["id"]
                
                # Find electricity contract
                contracts = account_detail.get("contracts", [])
                for contract in contracts:
                    if contract.get("contractType") == 1:  # Electricity
                        self._contract_id = contract["id"]
                        self._contract_icp = contract["icp"]
                        break
                        
                _LOGGER.debug("Account details loaded: account_id=%s, contract_id=%s, icp=%s", 
                            self._account_id, self._contract_id, self._contract_icp)
                return data
                
            return None
            
        except AuthenticationError:
            # Try re-authenticating once
            if await self.authenticate():
                return await self.get_accounts()
            raise

    async def get_usage_data(self, target_date: date) -> Optional[List[Dict[str, Any]]]:
        """Get usage data for a specific date."""
        if not self._token and not await self.authenticate():
            raise AuthenticationError("Failed to authenticate")
            
        if not self._contract_id or not self._account_id:
            _LOGGER.error("Missing contract or account ID")
            return None

        date_str = target_date.strftime("%Y-%m-%d")
        url = f"{API_BASE_URL}/usage/v2/{self._contract_id}"
        params = {
            "ba": self._account_id,
            "interval": "hourly", 
            "from": date_str,
            "to": date_str
        }
        
        _LOGGER.debug("Fetching usage data for %s", date_str)
        
        try:
            data = await self._make_request(
                "POST",
                url,
                params=params,
                headers=self._get_headers()
            )
            
            if data:
                _LOGGER.debug("Successfully fetched usage data for %s", date_str)
                return data
            else:
                _LOGGER.debug("No usage data available for %s", date_str)
                return None
                
        except AuthenticationError:
            # Try re-authenticating once
            if await self.authenticate():
                return await self.get_usage_data(target_date)
            raise
        except Exception as err:
            _LOGGER.error("Failed to fetch usage data for %s: %s", date_str, err)
            return None