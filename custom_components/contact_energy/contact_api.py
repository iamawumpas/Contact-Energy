"""Contact Energy API client for authentication and data retrieval.

This module handles all communication with the Contact Energy API, including
authentication, account data retrieval, and token management.
"""
from __future__ import annotations

import aiohttp
import logging
from typing import Any

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


class ContactEnergyApi:
    """Client for interacting with the Contact Energy API.

    This class manages authentication with Contact Energy and provides methods
    to retrieve account and usage data. It handles token refresh automatically.
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

    async def authenticate(self) -> dict[str, Any]:
        """Authenticate with Contact Energy API.

        Exchanges email and password for an authentication token.

        Returns:
            Dictionary containing token, segment, and bp (business partner ID).

        Raises:
            ContactEnergyAuthError: If authentication fails (invalid credentials)
            ContactEnergyConnectionError: If unable to connect to API
        """
        # Set up headers with API key for authentication request
        headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

        # Prepare authentication request payload
        payload = {"username": self.email, "password": self.password}

        try:
            # Validate we have credentials before attempting authentication
            if not self.email or not self.password:
                raise ContactEnergyAuthError("Email and password are required for authentication.")
            
            # Attempt to connect to the authentication endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BASE_URL}/login/v2", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    # Handle authentication response
                    if resp.status == 401:
                        _LOGGER.warning(f"Authentication failed for {self.email}: Invalid credentials (401)")
                        raise ContactEnergyAuthError("Invalid email or password. Please check your credentials and try again.")
                    if resp.status == 403:
                        _LOGGER.warning(f"Authentication forbidden for {self.email} (403)")
                        raise ContactEnergyAuthError("Access denied. Please contact Contact Energy support.")
                    if resp.status == 400:
                        _LOGGER.warning(f"Authentication request malformed for {self.email} (400)")
                        raise ContactEnergyAuthError("Invalid authentication request. Please reconfigure the integration.")
                    if resp.status != 200:
                        _LOGGER.error(f"Authentication failed with status {resp.status} for {self.email}")
                        raise ContactEnergyConnectionError(
                            f"API returned status {resp.status}. Please check your internet connection and try again."
                        )

                    # Extract authentication data from successful response
                    data = await resp.json()
                    self.token = data.get("token")
                    self.segment = data.get("segment")
                    self.bp = data.get("bp")

                    if not self.token:
                        raise ContactEnergyAuthError("No authentication token received. Please try again.")

                    _LOGGER.debug(f"Successfully authenticated as {self.email}")
                    return {"token": self.token, "segment": self.segment, "bp": self.bp}

        except aiohttp.ClientError as e:
            raise ContactEnergyConnectionError(
                f"Unable to connect to Contact Energy API: {str(e)}. Please check your internet connection and try again."
            )
        except ContactEnergyApiError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            _LOGGER.error(f"Unexpected error during authentication: {e}")
            raise ContactEnergyConnectionError(f"An unexpected error occurred: {str(e)}")

    async def get_accounts(self) -> dict[str, Any]:
        """Retrieve account information from the API.

        Fetches the authenticated user's account details including account summary,
        balance information, and available contracts/ICPs.

        Returns:
            Dictionary containing full account data from the API.

        Raises:
            ContactEnergyConnectionError: If unable to retrieve account data
            ContactEnergyAuthError: If token is invalid or missing
        """
        # Ensure we have a valid authentication token
        if not self.token:
            raise ContactEnergyAuthError("Not authenticated. Please authenticate first.")

        # Set up headers with authentication token for API request
        headers = {
            "x-api-key": API_KEY,
            "session": self.token,
            "authorization": self.token,
            "Content-Type": "application/json",
        }

        try:
            # Request account information from the API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BASE_URL}/accounts/v2?ba=", headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    # Handle account retrieval response
                    if resp.status == 401:
                        raise ContactEnergyAuthError("Your session has expired. Please re-authenticate.")
                    if resp.status == 403:
                        raise ContactEnergyAuthError("Access denied. Please contact Contact Energy support.")
                    if resp.status != 200:
                        raise ContactEnergyConnectionError(
                            f"API returned status {resp.status}. Please check your internet connection and try again."
                        )

                    # Extract account data from successful response
                    data = await resp.json()
                    _LOGGER.debug(f"Successfully retrieved account data for {self.email}")
                    return data

        except aiohttp.ClientError as e:
            raise ContactEnergyConnectionError(
                f"Unable to connect to Contact Energy API: {str(e)}. Please check your internet connection and try again."
            )
        except ContactEnergyApiError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            _LOGGER.error(f"Unexpected error while retrieving accounts: {e}")
            raise ContactEnergyConnectionError(f"An unexpected error occurred: {str(e)}")
