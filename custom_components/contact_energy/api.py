"""Contact Energy API Client."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientSession

from .const import (
    API_BASE_URL,
    API_KEY,
    API_TIMEOUT,
    ENDPOINT_ACCOUNTS,
    ENDPOINT_LOGIN,
    ENDPOINT_USAGE,
    ERROR_AUTH_FAILED,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_AUTH,
    INTERVAL_DAILY,
    INTERVAL_HOURLY,
    INTERVAL_MONTHLY,
    MAX_RETRIES,
    RETRY_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class ContactEnergyApiError(Exception):
    """Base exception for Contact Energy API errors."""


class AuthenticationError(ContactEnergyApiError):
    """Exception for authentication errors."""


class ConnectionError(ContactEnergyApiError):
    """Exception for connection errors."""


class ContactEnergyApi:
    """Contact Energy API client."""

    def __init__(self, email: str, password: str, session: ClientSession | None = None) -> None:
        """Initialize the API client.
        
        Args:
            email: User email address
            password: User password
            session: Optional aiohttp ClientSession
        """
        self._email = email
        self._password = password
        self._session = session
        self._token: str | None = None
        self._own_session = session is None
        
        _LOGGER.debug("ContactEnergyApi initialized for email: %s", email)

    async def __aenter__(self) -> ContactEnergyApi:
        """Async enter."""
        if self._own_session:
            self._session = ClientSession()
            _LOGGER.debug("Created new aiohttp session")
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async exit."""
        if self._own_session and self._session:
            await self._session.close()
            _LOGGER.debug("Closed aiohttp session")

    async def authenticate(self) -> bool:
        """Authenticate with the Contact Energy API.
        
        Returns:
            True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection fails
        """
        _LOGGER.info("Authenticating with Contact Energy API")
        
        url = f"{API_BASE_URL}{ENDPOINT_LOGIN}"
        headers = {"x-api-key": API_KEY}
        payload = {
            "username": self._email,
            "password": self._password,
        }
        
        try:
            async with self._session.post(
                url, json=payload, headers=headers, timeout=API_TIMEOUT
            ) as response:
                _LOGGER.debug("Authentication response status: %s", response.status)
                
                if response.status == 401:
                    _LOGGER.error("Authentication failed: Invalid credentials")
                    raise AuthenticationError(ERROR_INVALID_AUTH)
                    
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Authentication failed: %s - %s", response.status, text)
                    raise AuthenticationError(ERROR_AUTH_FAILED)
                
                data = await response.json()
                self._token = data.get("token")
                
                if not self._token:
                    _LOGGER.error("No token received in authentication response")
                    raise AuthenticationError(ERROR_AUTH_FAILED)
                
                _LOGGER.info("Authentication successful, token received")
                return True
                
        except ClientError as err:
            _LOGGER.error("Connection error during authentication: %s", err)
            raise ConnectionError(ERROR_CANNOT_CONNECT) from err

    async def get_accounts(self) -> dict[str, Any]:
        """Fetch all accounts for the authenticated user.
        
        Returns:
            Account data dictionary
            
        Raises:
            AuthenticationError: If not authenticated or auth fails
            ConnectionError: If connection fails
        """
        if not self._token:
            _LOGGER.warning("No token available, authenticating first")
            await self.authenticate()
        
        _LOGGER.info("Fetching account information")
        
        url = f"{API_BASE_URL}{ENDPOINT_ACCOUNTS}?ba="
        headers = self._get_auth_headers()
        
        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.get(
                    url, headers=headers, timeout=API_TIMEOUT
                ) as response:
                    _LOGGER.debug("Account fetch response status: %s", response.status)
                    
                    if response.status == 401 or response.status == 403:
                        if attempt < MAX_RETRIES - 1:
                            _LOGGER.warning("Auth failed, re-authenticating (attempt %d/%d)", 
                                          attempt + 1, MAX_RETRIES)
                            await self.authenticate()
                            headers = self._get_auth_headers()
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        _LOGGER.error("Authentication failed after %d retries", MAX_RETRIES)
                        raise AuthenticationError(ERROR_INVALID_AUTH)
                    
                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("Failed to fetch accounts: %s - %s", response.status, text)
                        raise ConnectionError(ERROR_CANNOT_CONNECT)
                    
                    data = await response.json()
                    accounts_summary = data.get("accountsSummary", [])
                    _LOGGER.info("Successfully fetched %d account(s)", len(accounts_summary))
                    _LOGGER.debug("Account data: %s", data)
                    return data
                    
            except ClientError as err:
                if attempt < MAX_RETRIES - 1:
                    _LOGGER.warning("Connection error, retrying (attempt %d/%d): %s", 
                                  attempt + 1, MAX_RETRIES, err)
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                _LOGGER.error("Connection error after %d retries: %s", MAX_RETRIES, err)
                raise ConnectionError(ERROR_CANNOT_CONNECT) from err
        
        raise ConnectionError(ERROR_CANNOT_CONNECT)

    async def get_usage(
        self,
        contract_id: str,
        account_id: str,
        interval: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch usage data for a contract.
        
        Args:
            contract_id: Contract ID
            account_id: Account ID
            interval: Data interval (hourly, daily, monthly)
            start_date: Start date
            end_date: End date
            
        Returns:
            List of usage data records
            
        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection fails
        """
        if not self._token:
            _LOGGER.warning("No token available, authenticating first")
            await self.authenticate()
        
        _LOGGER.info("Fetching %s usage data from %s to %s", 
                    interval, start_date.date(), end_date.date())
        
        url = (
            f"{API_BASE_URL}{ENDPOINT_USAGE.format(contract_id=contract_id)}"
            f"?ba={account_id}&interval={interval}"
            f"&from={start_date.strftime('%Y-%m-%d')}"
            f"&to={end_date.strftime('%Y-%m-%d')}"
        )
        headers = self._get_auth_headers()
        
        for attempt in range(MAX_RETRIES):
            try:
                async with self._session.post(
                    url, headers=headers, timeout=API_TIMEOUT
                ) as response:
                    _LOGGER.debug("Usage fetch response status: %s", response.status)
                    
                    if response.status == 401 or response.status == 403:
                        if attempt < MAX_RETRIES - 1:
                            _LOGGER.warning("Auth failed, re-authenticating (attempt %d/%d)", 
                                          attempt + 1, MAX_RETRIES)
                            await self.authenticate()
                            headers = self._get_auth_headers()
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        _LOGGER.error("Authentication failed after %d retries", MAX_RETRIES)
                        raise AuthenticationError(ERROR_INVALID_AUTH)
                    
                    if response.status != 200:
                        text = await response.text()
                        _LOGGER.error("Failed to fetch usage data: %s - %s", response.status, text)
                        raise ConnectionError(ERROR_CANNOT_CONNECT)
                    
                    data = await response.json()
                    _LOGGER.info("Successfully fetched %d %s usage record(s)", 
                               len(data), interval)
                    _LOGGER.debug("Usage data sample: %s", data[0] if data else "No data")
                    return data
                    
            except ClientError as err:
                if attempt < MAX_RETRIES - 1:
                    _LOGGER.warning("Connection error, retrying (attempt %d/%d): %s", 
                                  attempt + 1, MAX_RETRIES, err)
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                _LOGGER.error("Connection error after %d retries: %s", MAX_RETRIES, err)
                raise ConnectionError(ERROR_CANNOT_CONNECT) from err
        
        raise ConnectionError(ERROR_CANNOT_CONNECT)

    async def get_hourly_usage(
        self,
        contract_id: str,
        account_id: str,
        date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch hourly usage data for a specific date.
        
        Args:
            contract_id: Contract ID
            account_id: Account ID
            date: Date to fetch hourly data for
            
        Returns:
            List of hourly usage records (24 hours)
        """
        _LOGGER.debug("Fetching hourly usage for date: %s", date.date())
        return await self.get_usage(
            contract_id, account_id, INTERVAL_HOURLY, date, date
        )

    async def get_daily_usage(
        self,
        contract_id: str,
        account_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch daily usage data for a date range.
        
        Args:
            contract_id: Contract ID
            account_id: Account ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of daily usage records
        """
        _LOGGER.debug("Fetching daily usage from %s to %s", start_date.date(), end_date.date())
        return await self.get_usage(
            contract_id, account_id, INTERVAL_DAILY, start_date, end_date
        )

    async def get_monthly_usage(
        self,
        contract_id: str,
        account_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch monthly usage data for a date range.
        
        Args:
            contract_id: Contract ID
            account_id: Account ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of monthly usage records
        """
        _LOGGER.debug("Fetching monthly usage from %s to %s", start_date.date(), end_date.date())
        return await self.get_usage(
            contract_id, account_id, INTERVAL_MONTHLY, start_date, end_date
        )

    def _get_auth_headers(self) -> dict[str, str]:
        """Get headers for authenticated requests.
        
        Returns:
            Headers dictionary with authentication
        """
        if not self._token:
            raise AuthenticationError("Not authenticated")
        
        return {
            "x-api-key": API_KEY,
            "session": self._token,
            "authorization": self._token,
        }

    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated.
        
        Returns:
            True if authenticated
        """
        return self._token is not None
