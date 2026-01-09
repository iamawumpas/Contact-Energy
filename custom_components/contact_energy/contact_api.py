"""Contact Energy API client for authentication and data retrieval.

This module handles all communication with the Contact Energy API, including
authentication, account data retrieval, usage data downloads, and token management.

Version: 1.4.0
Changes: Added get_usage() method for hourly/daily/monthly usage data retrieval
"""
from __future__ import annotations

import aiohttp
import logging
import time
from datetime import date
from typing import Any
from urllib.parse import urlencode

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
        # Human-friendly note: account_id is the BA value required by usage/accounts calls.
        self.account_id: str | None = None

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
        # Note: GET requests typically don't include Content-Type header
        headers = {
            "x-api-key": API_KEY,
            "session": self.token,
            "authorization": self.token,
        }

        try:
            # Build URL without query parameters (ba parameter may be causing 502 errors)
            full_url = f"{BASE_URL}/accounts/v2"
            
            _LOGGER.debug(f"Making accounts API request: GET {full_url}")
            
            # Request account information from the API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    full_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    _LOGGER.debug(f"Accounts API response: status={resp.status}, content_type={resp.content_type}")
                    
                    # Handle account retrieval response
                    if resp.status == 401:
                        raise ContactEnergyAuthError("Your session has expired. Please re-authenticate.")
                    if resp.status == 403:
                        raise ContactEnergyAuthError("Access denied. Please contact Contact Energy support.")
                    if resp.status != 200:
                        # Try to get error details from response body
                        try:
                            error_data = await resp.json()
                            _LOGGER.debug(f"API error response body: {error_data}")
                        except Exception:
                            error_text = await resp.text()
                            _LOGGER.debug(f"API error response text: {error_text}")
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
            # Log full exception details for debugging
            _LOGGER.error(f"Unexpected error while retrieving accounts: {e}", exc_info=True)
            raise ContactEnergyConnectionError(f"An unexpected error occurred: {str(e)}")

    async def get_usage(
        self,
        contract_id: str,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch usage data from Contact Energy API for specified date range.

        Makes a POST request to /usage/v2/{contract_id} endpoint with the
        specified interval and date range. Automatically handles authentication,
        retries on transient failures, and parses response into structured format.

        This method supports three intervals:
        - 'hourly': Returns 24 records per day (hour-by-hour breakdown)
        - 'daily': Returns 1 record per day (daily totals)
        - 'monthly': Returns 1 record per month (monthly totals)

        Each record contains:
        - Total energy consumed (kWh)
        - Paid energy (charged kWh)
        - Free energy (off-peak + promotional kWh)
        - Total cost (NZD)

        Args:
            contract_id: Contract identifier from account data (e.g., "123456")
            interval: Data granularity - must be 'hourly', 'daily', or 'monthly'
            from_date: Start of date range (inclusive), format YYYY-MM-DD
            to_date: End of date range (inclusive), format YYYY-MM-DD

        Returns:
            List of usage records, each containing:
                - timestamp: ISO 8601 datetime string with timezone
                - total: Total energy consumed (kWh)
                - paid: Charged energy (kWh)
                - free: Off-peak/uncharged energy (kWh)
                - cost: Total cost (NZD)

        Raises:
            ContactEnergyAuthError: If token expired (triggers re-auth externally)
            ContactEnergyApiError: If API returns error status
            ContactEnergyConnectionError: If network request fails
            ValueError: If interval is invalid or date range is malformed

        Example:
            usage = await api.get_usage(
                "123456", "daily",
                date(2025, 12, 1), date(2025, 12, 31)
            )

        API Endpoint:
            POST /usage/v2/{contract_id}?ba={account_id}&interval={interval}
                 &from={from_date}&to={to_date}

        Note: Contact Energy has a 24-72 hour delay on usage data availability.
        """
        # Log entry with parameters for debugging
        _LOGGER.debug(
            "get_usage() called: contract_id=%s, interval=%s, from=%s, to=%s",
            contract_id, interval, from_date, to_date
        )

        # Start performance timer
        start_time = time.time()

        # Validate interval parameter (must be one of three supported values)
        valid_intervals = ['hourly', 'daily', 'monthly']
        if interval not in valid_intervals:
            error_msg = f"Invalid interval '{interval}'. Must be one of: {valid_intervals}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Validate date range (from_date must be before or equal to to_date)
        if from_date > to_date:
            error_msg = f"Invalid date range: from_date ({from_date}) > to_date ({to_date})"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Ensure we have a valid authentication token before making request
        if not self.token:
            error_msg = "Not authenticated. Please authenticate first."
            _LOGGER.error(error_msg)
            raise ContactEnergyAuthError(error_msg)

        # Validate that we have account_id for the ba parameter
        # Without this, the API returns 404 errors
        if not self.account_id:
            error_msg = "account_id is required for usage API calls but is not set. Please reconfigure the integration."
            _LOGGER.error(error_msg)
            raise ContactEnergyApiError(error_msg)
        
        # Build query parameters for API request
        # Format dates as YYYY-MM-DD strings required by API
        params = {
            # Use the Contact account_id for the required ba parameter (not the BP id)
            "ba": self.account_id,
            "interval": interval,  # hourly, daily, or monthly
            "from": from_date.strftime("%Y-%m-%d"),  # Start date
            "to": to_date.strftime("%Y-%m-%d"),  # End date
        }

        # Home Assistant sometimes mutates aiohttp params when proxying through its
        # internal session, which the Contact Energy API can reject (502). To avoid
        # any HA-side rewriting, build the full query string manually exactly as the
        # API expects (matches test_api.py behaviour).
        query_string = urlencode(params)
        full_url = f"{BASE_URL}/usage/v2/{contract_id}?{query_string}"

        # Set up headers with authentication token and API key
        headers = {
            "x-api-key": API_KEY,
            "session": self.token,
            "authorization": self.token,
            "Content-Type": "application/json",
        }

        # Log the API request details for debugging (without sensitive token)
        _LOGGER.debug(
            "Making usage API request: POST %s", full_url
        )

        try:
            # Make POST request to usage endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    full_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)  # Longer timeout for potentially large data
                ) as resp:
                    # Log response status for debugging
                    _LOGGER.debug(
                        "Usage API response: status=%d, content_type=%s",
                        resp.status, resp.content_type
                    )

                    # Handle authentication errors (token expired)
                    if resp.status == 401:
                        _LOGGER.warning(
                            "Usage API returned 401 (Unauthorized) for contract %s. Token may have expired.",
                            contract_id
                        )
                        raise ContactEnergyAuthError(
                            "Your session has expired. Please re-authenticate."
                        )

                    # Handle authorization errors (no access to this contract)
                    if resp.status == 403:
                        _LOGGER.warning(
                            "Usage API returned 403 (Forbidden) for contract %s. No access permission.",
                            contract_id
                        )
                        raise ContactEnergyAuthError(
                            "Access denied for this contract. Please contact Contact Energy support."
                        )

                    # Handle not found errors (invalid contract ID)
                    if resp.status == 404:
                        # For monthly, treat 404 as “no data currently available” to avoid noisy retries
                        if interval == "monthly":
                            _LOGGER.warning(
                                "Usage API returned 404 (Not Found) for contract %s on monthly interval. Treating as no monthly data and continuing.",
                                contract_id,
                            )
                            return []

                        _LOGGER.warning(
                            "Usage API returned 404 (Not Found) for contract %s. Contract may not exist.",
                            contract_id
                        )
                        raise ContactEnergyApiError(
                            f"Contract {contract_id} not found. Please check contract ID."
                        )

                    # Handle bad request errors (invalid parameters)
                        error_text = await resp.text()
                        _LOGGER.warning(
                            "Usage API returned 400 (Bad Request) for contract %s. Response: %s",
                            contract_id, error_text[:200]  # First 200 chars to avoid log spam
                        )
                        raise ContactEnergyApiError(
                            f"Invalid request parameters for usage API: {error_text[:100]}"
                        )

                    # Handle other non-success status codes
                    if resp.status != 200:
                        error_text = await resp.text()
                        # Log as debug since retries/chunking handle transient errors automatically
                        _LOGGER.debug(
                            "Usage API returned status %d for contract %s (will retry). Response: %s",
                            resp.status, contract_id, error_text[:200]
                        )
                        raise ContactEnergyConnectionError(
                            f"API returned status {resp.status}. Please try again later."
                        )

                    # Parse JSON response
                    data = await resp.json()

                    # Log raw response structure for debugging (without full data)
                    _LOGGER.debug(
                        "Usage API response structure: keys=%s",
                        list(data.keys()) if isinstance(data, dict) else type(data)
                    )

                    # Parse and transform the usage data
                    usage_records = self._parse_usage_response(data, interval, contract_id)

                    # Calculate elapsed time for performance tracking
                    elapsed = time.time() - start_time

                    # Log success with metrics
                    _LOGGER.info(
                        "Retrieved %d usage records for contract %s (%s interval) in %.2f seconds",
                        len(usage_records), contract_id, interval, elapsed
                    )

                    return usage_records

        except aiohttp.ClientError as e:
            # Log network-related errors with full context
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Network error while fetching usage for contract %s after %.2f seconds: %s",
                contract_id, elapsed, str(e)
            )
            raise ContactEnergyConnectionError(
                f"Unable to connect to Contact Energy API: {str(e)}. Please check your internet connection."
            )
        except ContactEnergyApiError:
            # Re-raise our custom API exceptions without wrapping
            raise
        except ValueError:
            # Re-raise validation errors without wrapping
            raise
        except Exception as e:
            # Log unexpected errors with full context for debugging
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Unexpected error while fetching usage for contract %s after %.2f seconds: %s",
                contract_id, elapsed, str(e), exc_info=True
            )
            raise ContactEnergyConnectionError(
                f"An unexpected error occurred while fetching usage data: {str(e)}"
            )

    def _parse_usage_response(
        self,
        data: dict[str, Any],
        interval: str,
        contract_id: str
    ) -> list[dict[str, Any]]:
        """Parse raw API response into standardized usage records.

        Transforms Contact Energy API response format into a clean, consistent
        structure for caching and sensor exposure. Handles missing fields,
        calculates paid/free breakdown, and validates data integrity.

        Args:
            data: Raw JSON response from /usage/v2 endpoint
            interval: Interval type ('hourly', 'daily', 'monthly') for logging
            contract_id: Contract ID for error logging context

        Returns:
            List of parsed usage records with standardized field names:
                - timestamp: ISO 8601 datetime string with timezone (Pacific/Auckland)
                - total: Total energy consumed (kWh) - from API 'value' field
                - paid: Charged/paid energy (kWh) - calculated as total - free
                - free: Free energy (kWh) - sum of offpeak + uncharged
                - cost: Total cost in NZD - from API 'dollarValue' field

        Raises:
            ContactEnergyApiError: If response structure is invalid or missing required fields

        Note: Paid usage = total - (off-peak free hours) - (promotional/uncharged).
              We ensure paid never goes negative due to data inconsistencies.
        """
        _LOGGER.debug("Parsing usage response for contract %s (%s interval)", contract_id, interval)

        # Extract usage array from response
        # API can return either:
        # - {"usage": [...records...]} (dict format)
        # - [...records...] (list format - direct array)
        if isinstance(data, list):
            # Direct list response
            usage_array = data
        elif isinstance(data, dict):
            # Dict with 'usage' key
            usage_array = data.get("usage", [])
        else:
            error_msg = f"Invalid API response type: expected dict or list, got {type(data)}"
            _LOGGER.error("%s Response: %s", error_msg, str(data)[:200])
            raise ContactEnergyApiError(error_msg)

        # Validate response structure
        if not isinstance(usage_array, list):
            error_msg = f"Invalid API response: usage data is not a list. Got type: {type(usage_array)}"
            _LOGGER.error("%s Response: %s", error_msg, str(data)[:200])
            raise ContactEnergyApiError(error_msg)

        # Log record count before parsing
        _LOGGER.debug("Parsing %d raw usage records from API", len(usage_array))

        # Log first record structure for debugging (especially for hourly data)
        if len(usage_array) > 0 and interval == "hourly":
            first_record = usage_array[0]
            _LOGGER.debug(
                "First hourly record structure - keys: %s",
                list(first_record.keys())
            )
            _LOGGER.debug(
                "First hourly record values - date=%s, value=%s, paid=%s, free=%s, offpeakValue=%s, unchargedValue=%s, dollarValue=%s",
                first_record.get("date"),
                first_record.get("value"),
                first_record.get("paid"),
                first_record.get("free"),
                first_record.get("offpeakValue"),
                first_record.get("unchargedValue"),
                first_record.get("dollarValue")
            )

        parsed_records = []

        # Process each usage record from API
        for idx, record in enumerate(usage_array):
            try:
                # Extract timestamp (ISO 8601 with timezone, e.g., "2025-12-31T23:00:00+13:00")
                timestamp = record.get("date")
                if not timestamp:
                    _LOGGER.warning(
                        "Record %d missing 'date' field for contract %s, skipping",
                        idx, contract_id
                    )
                    continue

                # Extract total energy consumed (kWh)
                # API field: 'value'
                # Use 'or 0.0' to handle None values (API returns None for some fields)
                total_kwh = float(record.get("value") or 0.0)

                # Extract energy components
                offpeak_kwh = float(record.get("offpeakValue") or 0.0)
                unpaid_kwh = float(record.get("unchargedValue") or 0.0)

                # For hourly data: paid and free are mutually exclusive within a single hour
                # When unpaid > 0, it's a free power hour - all usage is free, nothing is paid
                # When unpaid = 0, it's normal billing - usage is either peak or off-peak (both paid)
                #
                # For daily/monthly data: paid and free can coexist
                # A single day can have both paid hours (peak + offpeak) and free hours (uncharged)
                if interval == "hourly":
                    # Hourly: mutual exclusivity applies
                    if unpaid_kwh > 0:
                        # Free power hours: all usage is free/unpaid
                        free_kwh = unpaid_kwh
                        paid_total_kwh = 0.0
                        peak_kwh = 0.0
                        offpeak_kwh = 0.0
                    else:
                        # Normal billing: usage is either peak or off-peak (both paid)
                        free_kwh = 0.0
                        # Peak (paid at normal rate) excludes off-peak component
                        peak_kwh = total_kwh - offpeak_kwh
                        if peak_kwh < 0:
                            _LOGGER.debug(
                                "Capping peak usage at 0 for contract %s at %s: peak calculated negative (total=%.3f, offpeak=%.3f)",
                                contract_id, timestamp, total_kwh, offpeak_kwh
                            )
                            peak_kwh = 0.0
                        # Paid usage includes both peak and off-peak (off-peak is still billed at a reduced rate)
                        paid_total_kwh = peak_kwh + offpeak_kwh
                else:
                    # Daily/Monthly: both paid and free can exist on same day
                    # Free is the uncharged component
                    free_kwh = unpaid_kwh
                    # Off-peak is the off-peak billed component
                    # Peak is calculated as total minus off-peak, but only if unpaid is not part of total
                    # If total includes uncharged, we need paid = total - free
                    paid_total_kwh = total_kwh - unpaid_kwh
                    # For peak/offpeak breakdown of the paid portion
                    peak_kwh = paid_total_kwh - offpeak_kwh
                    if peak_kwh < 0:
                        _LOGGER.debug(
                            "Capping peak usage at 0 for contract %s at %s: peak calculated negative (paid_total=%.3f, offpeak=%.3f)",
                            contract_id, timestamp, paid_total_kwh, offpeak_kwh
                        )
                        peak_kwh = 0.0


                _LOGGER.debug(
                    "%s record: timestamp=%s, total=%.3f, paid_total=%.3f, peak=%.3f, offpeak=%.3f, free=%.3f",
                    interval.capitalize(), timestamp, total_kwh, paid_total_kwh, peak_kwh, offpeak_kwh, free_kwh
                )

                # Extract cost in NZD
                # API field: 'dollarValue'
                # Note: API returns None for historical data where cost is not available
                cost_nzd = float(record.get("dollarValue") or 0.0)

                # Build standardized record structure
                parsed_record = {
                    "timestamp": timestamp,  # ISO 8601 with timezone
                    "total": round(total_kwh, 3),  # Round to 3 decimal places (Wh precision)
                    "paid": round(paid_total_kwh, 3),  # Total billed kWh (peak + off-peak)
                    "peak": round(peak_kwh, 3),  # Billed at peak rate
                    "offpeak": round(offpeak_kwh, 3),  # Billed at off-peak rate
                    "free": round(free_kwh, 3),  # Unpaid/uncharged kWh (promotions)
                    "cost": round(cost_nzd, 2),  # Round to 2 decimal places (cents precision)
                }

                parsed_records.append(parsed_record)

            except (ValueError, TypeError) as e:
                # Log parse errors but continue processing other records
                _LOGGER.warning(
                    "Failed to parse usage record %d for contract %s: %s. Record: %s",
                    idx, contract_id, str(e), str(record)[:200]
                )
                continue

        # Log parsing results
        _LOGGER.debug(
            "Successfully parsed %d/%d usage records for contract %s (%s interval)",
            len(parsed_records), len(usage_array), contract_id, interval
        )

        # Warn if many records failed to parse (>10% failure rate)
        if len(usage_array) > 0:
            failure_rate = (len(usage_array) - len(parsed_records)) / len(usage_array)
            if failure_rate > 0.1:
                _LOGGER.warning(
                    "High parse failure rate for contract %s (%s interval): %.1f%% (%d/%d records failed)",
                    contract_id, interval, failure_rate * 100,
                    len(usage_array) - len(parsed_records), len(usage_array)
                )

        return parsed_records
