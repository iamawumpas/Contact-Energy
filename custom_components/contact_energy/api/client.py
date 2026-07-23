"""Base API client for Contact Energy.

This module provides the base API client with authentication, token management,
rate limiting, and error handling. All specific API endpoints extend this base.

Version: 2.0.0
"""
from __future__ import annotations

import aiohttp
import asyncio
import logging
import time
from typing import Any
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

# Contact Energy API configuration
BASE_URL = "https://api.contact-digital-prod.net"
API_KEY = "kbIthASA7e1M3NmpMdGrn2Yqe0yHcCjL4QNPSUij"


class ContactEnergyApiError(Exception):
    """Base exception for Contact Energy API errors."""
    pass


class ContactEnergyAuthError(ContactEnergyApiError):
    """Raised when authentication fails."""
    pass


class ContactEnergyConnectionError(ContactEnergyApiError):
    """Raised when connection to API fails."""
    pass


def _redact_sensitive(value: str, prefix_length: int = 3) -> str:
    """Redact sensitive data in logs while keeping prefix for debugging.
    
    Args:
        value: The sensitive value to redact
        prefix_length: How many characters to keep at the start
        
    Returns:
        Redacted string like "abc***redacted***" for "abcdefgh"
    """
    if not value or len(value) <= prefix_length:
        return "***redacted***"
    return value[:prefix_length] + "***redacted***"


class ContactEnergyApiClient:
    """Base API client for Contact Energy.

    This class manages authentication with Contact Energy and provides methods
    for making API requests with rate limiting, error handling, and token management.
    
    All specific API endpoints should extend this class.
    """

    def __init__(self, email: str, password: str):
        """Initialize the API client with credentials.

        Args:
            email: Contact Energy account email address
            password: Contact Energy account password
        """
        self.email = email
        self.password = password
        self.token: str | None = None
        self.segment: str | None = None
        self.bp: str | None = None
        self.account_id: str | None = None
        
        # Rate limiting to avoid rapid consecutive requests
        self._min_interval_seconds: float = 0.5
        self._last_request_monotonic: float = 0.0
        
        # Timeout configurations for different endpoints
        self._auth_timeout: float = 10.0  # Quick timeout for auth
        self._accounts_timeout: float = 10.0  # Quick timeout for accounts
        self._usage_timeout: float = 30.0  # Longer timeout for usage data
        
        # Token expiry tracking
        self._token_expires_at: datetime | None = None

    async def _throttle(self) -> None:
        """Enforce a minimal interval between outbound API calls.

        Keeps traffic polite and reduces transient 4xx/5xx due to bursts.
        """
        now = time.monotonic()
        elapsed = now - self._last_request_monotonic
        if elapsed < self._min_interval_seconds:
            await asyncio.sleep(self._min_interval_seconds - elapsed)
        self._last_request_monotonic = time.monotonic()

    async def authenticate(self) -> dict[str, Any]:
        """Authenticate with Contact Energy API and retrieve token.

        This method should be called before making any API requests to obtain
        a valid authentication token. The token is stored internally and used
        for subsequent requests.

        Returns:
            Dictionary containing authentication response with token, segment, and BP.

        Raises:
            ContactEnergyAuthError: If authentication fails.
            ContactEnergyConnectionError: If unable to connect to API.
        """
        await self._throttle()
        
        url = f"{BASE_URL}/login/v2"
        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "username": self.email,
            "password": self.password,
        }

        _LOGGER.debug(
            "Authenticating with Contact Energy API as %s",
            _redact_sensitive(self.email)
        )

        try:
            timeout = aiohttp.ClientTimeout(total=self._auth_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 401:
                        raise ContactEnergyAuthError("Invalid email or password")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error(
                            "Authentication failed with status %d: %s",
                            response.status,
                            error_text
                        )
                        raise ContactEnergyAuthError(
                            f"Authentication failed with status {response.status}"
                        )

                    data = await response.json()

                    # Store authentication details
                    self.token = data.get("token")
                    self.segment = data.get("segment")
                    self.bp = data.get("bp")
                    
                    # Token typically expires after 24 hours
                    self._token_expires_at = datetime.now() + timedelta(hours=23)

                    if not self.token:
                        raise ContactEnergyAuthError("No token in authentication response")

                    _LOGGER.info("Successfully authenticated with Contact Energy API")
                    return data

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error during authentication: %s", err)
            raise ContactEnergyConnectionError(
                f"Failed to connect to Contact Energy API: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout during authentication")
            raise ContactEnergyConnectionError(
                "Timeout connecting to Contact Energy API"
            ) from err

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        timeout: float = 10.0,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make an authenticated API request.

        This method handles rate limiting, authentication headers, and error handling
        for all API requests.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/accounts/v2")
            timeout: Request timeout in seconds
            params: Query parameters
            json: JSON body for POST requests

        Returns:
            JSON response from API

        Raises:
            ContactEnergyAuthError: If authentication token is missing or invalid
            ContactEnergyConnectionError: If request fails
        """
        if not self.token:
            raise ContactEnergyAuthError("Not authenticated - call authenticate() first")

        await self._throttle()

        url = f"{BASE_URL}{endpoint}"
        headers = {
            "x-api-key": API_KEY,
            "session": self.token,
            "authorization": self.token,
            "Content-Type": "application/json",
        }

        _LOGGER.debug("Making %s request to %s", method, endpoint)

        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.request(
                    method, url, headers=headers, params=params, json=json
                ) as response:
                    if response.status == 401 or response.status == 403:
                        _LOGGER.warning(
                            "Authentication token expired or invalid (status %d)",
                            response.status
                        )
                        raise ContactEnergyAuthError("Token expired or invalid")

                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error(
                            "API request failed with status %d: %s",
                            response.status,
                            error_text
                        )
                        raise ContactEnergyApiError(
                            f"API request failed with status {response.status}"
                        )

                    return await response.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error during API request: %s", err)
            raise ContactEnergyConnectionError(
                f"Failed to connect to Contact Energy API: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout during API request to %s", endpoint)
            raise ContactEnergyConnectionError(
                f"Timeout during API request to {endpoint}"
            ) from err

    def is_token_expired(self) -> bool:
        """Check if the authentication token is expired or about to expire.

        Returns:
            True if token is expired or will expire in next 5 minutes
        """
        if not self._token_expires_at:
            return True
        return datetime.now() >= (self._token_expires_at - timedelta(minutes=5))
