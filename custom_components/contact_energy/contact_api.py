"""Contact Energy API client for authentication and data retrieval.

=== WHAT THIS DOES ===
This legacy module talks directly to Contact Energy's online API. It handles:
1. Logging in with an email address and password.
2. Remembering the temporary access token returned by Contact Energy.
3. Fetching account information for the signed-in customer.
4. Downloading usage data in hourly, daily, or monthly form.
5. Converting raw API responses into a cleaner structure used elsewhere in the integration.

=== FOR NON-CODERS ===
Think of this file as an older office clerk who still knows how to call Contact
Energy's systems and ask for information. Newer code in the integration is more
modern and better organised, but this older clerk is still kept around because
other parts of the project - or old installations - may still depend on it.

A few terms explained simply:
- API: A computer-friendly service that lets one system ask another for data.
- Token: A temporary digital pass that proves the user has logged in.
- JSON: A text format for structured data, similar to labelled boxes of information.
- Interval: How detailed the data should be (hour-by-hour, day-by-day, or month-by-month).

=== LEGACY / COMPATIBILITY NOTE ===
This is a legacy/deprecated file. It is intentionally kept for backward
compatibility and as a teaching resource so readers can understand how the older
integration flow worked before the newer API package structure was introduced.

Version: 1.4.0
Changes: Added get_usage() method for hourly/daily/monthly usage data retrieval
"""

# This import lets the file use newer style type hints safely across Python versions.
from __future__ import annotations

# ============================================================================
# IMPORTS - Every outside tool this legacy module depends on
# ============================================================================

# aiohttp is the asynchronous web-request library used to call Contact Energy's API.
# "Asynchronous" means the program can keep doing other work while it waits.
import aiohttp

# logging records a running commentary for debugging, troubleshooting, and support.
import logging

# time is used for measuring elapsed time and spacing out requests politely.
import time

# date and datetime help represent calendar dates and exact timestamps.
from datetime import date, datetime

# asyncio is Python's built-in library for asynchronous tasks and sleeping.
import asyncio

# Any tells readers that some values may contain many different data shapes.
from typing import Any

# urlencode turns a dictionary of query parameters into URL text like a=1&b=2.
from urllib.parse import urlencode

# ============================================================================
# LOGGER SETUP
# ============================================================================
# A logger acts like an automatic diary for this module.
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# CONTACT ENERGY API CONFIGURATION
# ============================================================================

# BASE_URL is the root internet address for Contact Energy's backend service.
BASE_URL = "https://api.contact-digital-prod.net"

# API_KEY identifies this integration to the backend service.
# This is treated like an application identifier rather than a user password.
API_KEY = "kbIthASA7e1M3NmpMdGrn2Yqe0yHcCjL4QNPSUij"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _redact_sensitive(value: str, prefix_length: int = 3) -> str:
    """Redact sensitive data in logs while keeping a small visible prefix.

    === WHAT THIS DOES ===
    This helper hides most of a secret value before it is written to logs.

    === WHY IT EXISTS ===
    Legacy code often logs useful debugging information. This helper lets the
    old code remain support-friendly without printing full emails, tokens, or
    passwords into logs where they should not appear.

    === STEP-BY-STEP ===
    1. Check whether the input is empty or too short to safely show part of it.
    2. If so, replace the whole value with a generic placeholder.
    3. Otherwise, keep a tiny prefix and hide the rest.
    """
    # If the value is missing or too short, we hide everything for safety.
    if not value or len(value) <= prefix_length:
        return "***redacted***"

    # Keep only the first few characters so support logs remain useful.
    return value[:prefix_length] + "***redacted***"


# ============================================================================
# CUSTOM EXCEPTIONS - Named error types make failures easier to understand
# ============================================================================

class ContactEnergyApiError(Exception):
    """Base exception for Contact Energy API problems.

    === FOR NON-CODERS ===
    An exception is Python's way of saying "something went wrong".
    This parent exception groups all Contact Energy specific failures together.
    """

    pass


class ContactEnergyAuthError(ContactEnergyApiError):
    """Raised when authentication fails.

    === FOR NON-CODERS ===
    This means the login step failed, usually because credentials were rejected
    or the session expired.
    """

    pass


class ContactEnergyConnectionError(ContactEnergyApiError):
    """Raised when the integration cannot talk to the API service.

    === FOR NON-CODERS ===
    This points to network or server trouble rather than a bad password.
    """

    pass


# ============================================================================
# MAIN LEGACY API CLIENT
# ============================================================================

class ContactEnergyApi:
    """Client for interacting with the Contact Energy API.

    === WHAT THIS DOES ===
    This class stores login details, signs in, fetches account information, and
    downloads usage data.

    === WHY IT STILL EXISTS ===
    This is legacy/deprecated code, but it remains in the repository because old
    call paths may still import it. Keeping it documented helps maintainers learn
    the historical design while preserving compatibility.

    === FOR NON-CODERS ===
    You can imagine this class as an older but reliable receptionist:
    - It knows your login details.
    - It signs in to Contact Energy.
    - It asks for your account or power-usage information.
    - It translates the replies into a simpler format for the rest of the app.
    """

    def __init__(self, email: str, password: str):
        """Initialize the API client with credentials.

        === WHAT THIS DOES ===
        This constructor stores the user's login details and prepares blank fields
        that will be filled after authentication succeeds.

        === WHY IT EXISTS ===
        Even deprecated code needs a predictable setup step so older callers can
        build the client in the same way they always have.

        === STEP-BY-STEP ===
        1. Save the provided email and password.
        2. Create empty placeholders for authentication and account details.
        3. Configure simple request throttling.
        4. Define timeouts for different API calls.
        """
        # ====================================================================
        # STORE THE USER'S LOGIN DETAILS
        # ====================================================================
        # These values are reused later when authenticate() performs the login.
        self.email = email
        self.password = password

        # ====================================================================
        # PREPARE EMPTY PLACEHOLDERS FOR DATA WE DO NOT HAVE YET
        # ====================================================================
        # token becomes the temporary access pass returned by Contact Energy.
        self.token: str | None = None

        # segment stores customer segmentation data returned by the login API.
        self.segment: str | None = None

        # bp is Contact Energy's business-partner identifier for the account.
        self.bp: str | None = None

        # account_id is the BA value needed for some account and usage endpoints.
        self.account_id: str | None = None

        # ====================================================================
        # SET UP LIGHT RATE LIMITING
        # ====================================================================
        # This minimum interval reduces the chance of sending bursts of requests.
        self._min_interval_seconds: float = 0.5

        # This remembers when the previous request was sent.
        self._last_request_monotonic: float = 0.0

        # ====================================================================
        # TIMEOUT SETTINGS
        # ====================================================================
        # Authentication and account endpoints are expected to be quick.
        self._auth_timeout: float = 10.0
        self._accounts_timeout: float = 10.0

        # Usage calls can take longer because they may cover larger date ranges.
        self._usage_timeout: float = 30.0

    async def _throttle(self) -> None:
        """Pause briefly if requests are happening too close together.

        === WHAT THIS DOES ===
        This helper enforces a tiny delay between outbound API calls.

        === WHY IT EXISTS ===
        Legacy direct-API integrations can accidentally make back-to-back calls.
        This keeps behaviour polite and reduces transient failures.

        === STEP-BY-STEP ===
        1. Measure the current monotonic clock time.
        2. Work out how long it has been since the last request.
        3. Sleep only if the last request happened too recently.
        4. Record the new send time.
        """
        # Read the current monotonic clock. Monotonic clocks only move forward.
        now = time.monotonic()

        # Calculate how long it has been since the previous request.
        elapsed = now - self._last_request_monotonic

        # If the pause has been too short, wait for the remaining time.
        if elapsed < self._min_interval_seconds:
            await asyncio.sleep(self._min_interval_seconds - elapsed)

        # Record the moment the request is now allowed to proceed.
        self._last_request_monotonic = time.monotonic()

    async def authenticate(self) -> dict[str, Any]:
        """Authenticate with Contact Energy and capture login metadata.

        === WHAT THIS DOES ===
        This method sends the stored email and password to Contact Energy's login
        endpoint and saves the returned token, segment, and business-partner ID.

        === WHY IT EXISTS ===
        All later account and usage calls rely on a valid session token. This is
        the entry point that older code paths still use to obtain that token.

        === STEP-BY-STEP ===
        1. Build HTTP headers and the login payload.
        2. Verify that email and password were provided.
        3. Open an HTTP session and wait for throttle rules.
        4. Send a POST request to the login endpoint.
        5. Inspect the response status and raise clear errors when needed.
        6. Parse the returned JSON and store the important fields.
        7. Return a summary dictionary for the caller.
        """
        # Build the request headers Contact Energy expects for login.
        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json",
        }

        # Build the body of the login request using the stored credentials.
        payload = {
            "username": self.email,
            "password": self.password,
        }

        try:
            # Refuse to proceed if credentials are missing.
            if not self.email or not self.password:
                raise ContactEnergyAuthError("Email and password are required for authentication.")

            # Open a short-lived HTTP session for the login request.
            async with aiohttp.ClientSession() as session:
                # Respect the client-side throttle before sending anything.
                await self._throttle()

                # Send the login request to Contact Energy.
                async with session.post(
                    f"{BASE_URL}/login/v2",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self._auth_timeout),
                ) as resp:
                    # 401 means the username/password combination was rejected.
                    if resp.status == 401:
                        _LOGGER.warning(
                            "Authentication failed for %s: Invalid credentials (401)",
                            _redact_sensitive(self.email),
                        )
                        raise ContactEnergyAuthError(
                            "Invalid email or password. Please check your credentials and try again."
                        )

                    # 403 means the server understood us but will not allow access.
                    if resp.status == 403:
                        _LOGGER.warning(
                            "Authentication forbidden for %s (403)",
                            _redact_sensitive(self.email),
                        )
                        raise ContactEnergyAuthError(
                            "Access denied. Please contact Contact Energy support."
                        )

                    # 400 means the request itself was malformed.
                    if resp.status == 400:
                        _LOGGER.warning(
                            "Authentication request malformed for %s (400)",
                            _redact_sensitive(self.email),
                        )
                        raise ContactEnergyAuthError(
                            "Invalid authentication request. Please reconfigure the integration."
                        )

                    # Any other non-200 status is treated as a service or connection problem.
                    if resp.status != 200:
                        _LOGGER.error(
                            "Authentication failed with status %s for %s",
                            resp.status,
                            _redact_sensitive(self.email),
                        )
                        raise ContactEnergyConnectionError(
                            f"API returned status {resp.status}. Please check your internet connection and try again."
                        )

                    # Read the successful JSON payload from the response body.
                    data = await resp.json()

                    # Save the token and related metadata onto this client instance.
                    self.token = data.get("token")
                    self.segment = data.get("segment")
                    self.bp = data.get("bp")

                    # If the server omitted the token, login is unusable.
                    if not self.token:
                        raise ContactEnergyAuthError("No authentication token received. Please try again.")

                    # Record a success message without exposing the full email address.
                    _LOGGER.debug("Successfully authenticated as %s", _redact_sensitive(self.email))

                    # Return the captured values so older callers can use them immediately.
                    return {
                        "token": self.token,
                        "segment": self.segment,
                        "bp": self.bp,
                    }

        except (asyncio.TimeoutError, TimeoutError) as e:
            # Timeouts on startup or while reconnecting are transient connectivity issues,
            # not authentication problems, so surface them as a connection failure.
            raise ContactEnergyConnectionError(
                f"Timed out while authenticating with Contact Energy API: {str(e)}. Please check your internet connection and try again."
            )
        except aiohttp.ClientError as e:
            # Convert lower-level network issues into the integration's named error type.
            raise ContactEnergyConnectionError(
                f"Unable to connect to Contact Energy API: {str(e)}. Please check your internet connection and try again."
            )
        except ContactEnergyApiError:
            # Re-raise our own known exceptions unchanged so callers can handle them.
            raise
        except Exception as e:
            # Wrap anything unexpected in a connection-style error after logging it.
            _LOGGER.error("Unexpected error during authentication: %s", e)
            raise ContactEnergyConnectionError(f"An unexpected error occurred: {str(e)}")

    async def get_accounts(self) -> dict[str, Any]:
        """Retrieve account information from the API.

        === WHAT THIS DOES ===
        This method downloads the signed-in customer's account payload.

        === WHY IT EXISTS ===
        Older parts of the integration still expect this legacy helper for one-shot
        account retrieval after authentication.

        === STEP-BY-STEP ===
        1. Confirm that a session token is available.
        2. Build authenticated request headers.
        3. Call the accounts endpoint.
        4. Translate important HTTP failures into helpful exceptions.
        5. Return the decoded JSON body.
        """
        # Make sure authenticate() has already stored a session token.
        if not self.token:
            raise ContactEnergyAuthError("Not authenticated. Please authenticate first.")

        # Build headers required for authenticated account requests.
        headers = {
            "x-api-key": API_KEY,
            "session": self.token,
            "authorization": self.token,
        }

        try:
            # Build the endpoint URL. This legacy path intentionally omits query parameters.
            full_url = f"{BASE_URL}/accounts/v2"

            # Log the request target so support can trace failures.
            _LOGGER.debug("Making accounts API request: GET %s", full_url)

            # Open a short-lived HTTP session for the account call.
            async with aiohttp.ClientSession() as session:
                # Respect the throttle before sending the request.
                await self._throttle()

                # Send the GET request to download the account payload.
                async with session.get(
                    full_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self._accounts_timeout),
                ) as resp:
                    # Log high-level response metadata for debugging.
                    _LOGGER.debug(
                        "Accounts API response: status=%s, content_type=%s",
                        resp.status,
                        resp.content_type,
                    )

                    # 401 means the stored token is missing, invalid, or expired.
                    if resp.status == 401:
                        raise ContactEnergyAuthError("Your session has expired. Please re-authenticate.")

                    # 403 means access is forbidden even though the request was understood.
                    if resp.status == 403:
                        raise ContactEnergyAuthError("Access denied. Please contact Contact Energy support.")

                    # Anything other than 200 is logged with as much context as possible.
                    if resp.status != 200:
                        try:
                            # Prefer structured JSON error details when available.
                            error_data = await resp.json()
                            _LOGGER.debug("API error response body: %s", error_data)
                        except Exception:
                            # Fall back to plain text if the response was not JSON.
                            error_text = await resp.text()
                            _LOGGER.debug("API error response text: %s", error_text)

                        raise ContactEnergyConnectionError(
                            f"API returned status {resp.status}. Please check your internet connection and try again."
                        )

                    # Decode and return the successful account payload.
                    data = await resp.json()
                    _LOGGER.debug("Successfully retrieved account data")
                    return data

        except (asyncio.TimeoutError, TimeoutError) as e:
            # A timeout is a temporary network/server issue, not proof that credentials
            # are invalid, so keep the signal specific for the coordinator to handle.
            raise ContactEnergyConnectionError(
                f"Timed out while retrieving accounts from Contact Energy API: {str(e)}. Please check your internet connection and try again."
            )
        except aiohttp.ClientError as e:
            # Convert network-layer failures into a clearer integration error.
            raise ContactEnergyConnectionError(
                f"Unable to connect to Contact Energy API: {str(e)}. Please check your internet connection and try again."
            )
        except ContactEnergyApiError:
            # Preserve the meaning of our custom exceptions.
            raise
        except Exception as e:
            # Log the full traceback for unexpected issues, then raise a stable error type.
            _LOGGER.error("Unexpected error while retrieving accounts: %s", e, exc_info=True)
            raise ContactEnergyConnectionError(f"An unexpected error occurred: {str(e)}")

    async def get_usage(
        self,
        contract_id: str,
        interval: str,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch usage data from Contact Energy API for a chosen date range.

        === WHAT THIS DOES ===
        This method downloads usage records for one contract and one interval
        (hourly, daily, or monthly), then hands the raw payload to the parser.

        === WHY IT EXISTS ===
        Legacy dashboards and caches still rely on this older combined method for
        usage retrieval and normalisation.

        === STEP-BY-STEP ===
        1. Log the request and start a timer.
        2. Validate the interval and date range.
        3. Confirm authentication and required account identifiers exist.
        4. Build query parameters and the final request URL.
        5. Send the POST request.
        6. Interpret HTTP status codes carefully.
        7. Decode JSON and parse it into standard records.
        8. Return the cleaned list.
        """
        # Record the request parameters in a privacy-safe way.
        _LOGGER.debug(
            "get_usage() called: contract_id=%s, interval=%s, from=%s, to=%s",
            _redact_sensitive(contract_id, 2),
            interval,
            from_date,
            to_date,
        )

        # Start a timer so logs can report how long the request took.
        start_time = time.time()

        # Only these three interval values are supported by the legacy implementation.
        valid_intervals = ["hourly", "daily", "monthly"]
        if interval not in valid_intervals:
            error_msg = f"Invalid interval '{interval}'. Must be one of: {valid_intervals}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # The start date cannot be later than the end date.
        if from_date > to_date:
            error_msg = f"Invalid date range: from_date ({from_date}) > to_date ({to_date})"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Usage requests require an authenticated session token.
        if not self.token:
            error_msg = "Not authenticated. Please authenticate first."
            _LOGGER.error(error_msg)
            raise ContactEnergyAuthError(error_msg)

        # The usage endpoint also requires the BA/account identifier.
        if not self.account_id:
            error_msg = "account_id is required for usage API calls but is not set. Please reconfigure the integration."
            _LOGGER.error(error_msg)
            raise ContactEnergyApiError(error_msg)

        # Build the query parameters exactly as the Contact API expects them.
        params = {
            "ba": self.account_id,
            "interval": interval,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        # Legacy note: we build the full query string manually to avoid unwanted mutation.
        query_string = urlencode(params)
        full_url = f"{BASE_URL}/usage/v2/{contract_id}?{query_string}"

        # Build the authenticated headers for the usage request.
        headers = {
            "x-api-key": API_KEY,
            "session": self.token,
            "authorization": self.token,
            "Content-Type": "application/json",
        }

        # Log the target URL without exposing the token.
        _LOGGER.debug("Making usage API request: POST %s", full_url)

        try:
            # Wait if needed so we do not burst requests too quickly.
            await self._throttle()

            # Open an HTTP session dedicated to this usage request.
            async with aiohttp.ClientSession() as session:
                # Send the POST request and wait for the API's reply.
                async with session.post(
                    full_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self._usage_timeout),
                ) as resp:
                    # Log the response status and content type for debugging.
                    _LOGGER.debug(
                        "Usage API response: status=%d, content_type=%s",
                        resp.status,
                        resp.content_type,
                    )

                    # 401 means the session token has likely expired.
                    if resp.status == 401:
                        _LOGGER.warning(
                            "Usage API returned 401 (Unauthorized) for contract %s. Token may have expired.",
                            contract_id,
                        )
                        raise ContactEnergyAuthError("Your session has expired. Please re-authenticate.")

                    # 403 means this user is not allowed to access that contract.
                    if resp.status == 403:
                        _LOGGER.warning(
                            "Usage API returned 403 (Forbidden) for contract %s. No access permission.",
                            contract_id,
                        )
                        raise ContactEnergyAuthError(
                            "Access denied for this contract. Please contact Contact Energy support."
                        )

                    # 404 often means the contract or interval has no matching resource.
                    if resp.status == 404:
                        # Legacy special case: monthly 404 is treated as "no monthly data yet".
                        if interval == "monthly":
                            _LOGGER.warning(
                                "Usage API returned 404 (Not Found) for contract %s on monthly interval. Treating as no monthly data and continuing.",
                                contract_id,
                            )
                            return []

                        _LOGGER.warning(
                            "Usage API returned 404 (Not Found) for contract %s. Contract may not exist.",
                            contract_id,
                        )
                        raise ContactEnergyApiError(
                            f"Contract {contract_id} not found. Please check contract ID."
                        )

                    # 400 means the request parameters were rejected by the server.
                    if resp.status == 400:
                        error_text = await resp.text()
                        _LOGGER.warning(
                            "Usage API returned 400 (Bad Request) for contract %s. Response: %s",
                            contract_id,
                            error_text[:200],
                        )
                        raise ContactEnergyApiError(
                            f"Invalid request parameters for usage API: {error_text[:100]}"
                        )

                    # Any other non-success status is treated as retry-worthy connection trouble.
                    if resp.status != 200:
                        error_text = await resp.text()
                        _LOGGER.debug(
                            "Usage API returned status %d for contract %s (will retry). Response: %s",
                            resp.status,
                            contract_id,
                            error_text[:200],
                        )
                        raise ContactEnergyConnectionError(
                            f"API returned status {resp.status}. Please try again later."
                        )

                    # Decode the JSON body returned by the API.
                    data = await resp.json()

                    # Log only the overall structure, not the full potentially large payload.
                    _LOGGER.debug(
                        "Usage API response structure: keys=%s",
                        list(data.keys()) if isinstance(data, dict) else type(data),
                    )

                    # Convert the raw API payload into a standard internal record list.
                    usage_records = self._parse_usage_response(data, interval, contract_id)

                    # Work out how long the entire fetch-and-parse step took.
                    elapsed = time.time() - start_time

                    # Log a concise success summary.
                    _LOGGER.info(
                        "Retrieved %d usage records (%s interval) in %.2f seconds",
                        len(usage_records),
                        interval,
                        elapsed,
                    )

                    # Return the cleaned records to the caller.
                    return usage_records

        except aiohttp.ClientError as e:
            # Translate network exceptions into a clearer Contact Energy error type.
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Network error while fetching usage after %.2f seconds: %s",
                elapsed,
                str(e),
            )
            raise ContactEnergyConnectionError(
                f"Unable to connect to Contact Energy API: {str(e)}. Please check your internet connection."
            )
        except ContactEnergyApiError:
            # Preserve known domain-specific exceptions.
            raise
        except ValueError:
            # Preserve validation errors without wrapping them.
            raise
        except Exception as e:
            # Catch anything unexpected, log details, and present a stable error type.
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Unexpected error while fetching usage after %.2f seconds: %s",
                elapsed,
                str(e),
                exc_info=True,
            )
            raise ContactEnergyConnectionError(
                f"An unexpected error occurred while fetching usage data: {str(e)}"
            )

    def _parse_usage_response(
        self,
        data: dict[str, Any],
        interval: str,
        contract_id: str,
    ) -> list[dict[str, Any]]:
        """Parse raw API usage data into a standard record structure.

        === WHAT THIS DOES ===
        This helper converts Contact Energy's raw response format into a cleaner,
        predictable list of records containing timestamp, paid usage, free usage,
        peak usage, off-peak usage, and cost.

        === WHY IT EXISTS ===
        The raw API format is not ideal for sensors and caches. Legacy callers use
        this parser so the rest of the integration can work with a stable shape.

        === STEP-BY-STEP ===
        1. Work out whether the API returned a list directly or a dictionary.
        2. Validate that a list of records is available.
        3. Loop through each record one by one.
        4. Extract timestamps and numeric values safely.
        5. Calculate paid/free usage depending on the interval type.
        6. Round values into a consistent format.
        7. Skip bad records but keep processing the rest.
        8. Return the cleaned list.
        """
        # Announce the parsing phase in debug logs.
        _LOGGER.debug("Parsing usage response for %s interval", interval)

        # The API sometimes returns a bare list and sometimes wraps it in a dictionary.
        if isinstance(data, list):
            usage_array = data
        elif isinstance(data, dict):
            usage_array = data.get("usage", [])
        else:
            error_msg = f"Invalid API response type: expected dict or list, got {type(data)}"
            _LOGGER.error("%s Response: %s", error_msg, str(data)[:200])
            raise ContactEnergyApiError(error_msg)

        # Confirm that the extracted usage section is really a list.
        if not isinstance(usage_array, list):
            error_msg = f"Invalid API response: usage data is not a list. Got type: {type(usage_array)}"
            _LOGGER.error("%s Response: %s", error_msg, str(data)[:200])
            raise ContactEnergyApiError(error_msg)

        # Log the total number of raw records before we start converting them.
        _LOGGER.debug("Parsing %d raw usage records from API", len(usage_array))

        # For hourly payloads, log the first record's structure because it is often the trickiest.
        if len(usage_array) > 0 and interval == "hourly":
            first_record = usage_array[0]
            _LOGGER.debug("First hourly record structure - keys: %s", list(first_record.keys()))
            _LOGGER.debug(
                "First hourly record values - date=%s, value=%s, paid=%s, free=%s, offpeakValue=%s, unchargedValue=%s, dollarValue=%s",
                first_record.get("date"),
                first_record.get("value"),
                first_record.get("paid"),
                first_record.get("free"),
                first_record.get("offpeakValue"),
                first_record.get("unchargedValue"),
                first_record.get("dollarValue"),
            )

        # Prepare the output list that will hold the cleaned records.
        parsed_records = []

        # Process each raw usage item one at a time so one bad row does not spoil the rest.
        for idx, record in enumerate(usage_array):
            try:
                # Extract the record's timestamp field.
                timestamp = record.get("date")
                if not timestamp:
                    _LOGGER.warning(
                        "Record %d missing 'date' field for contract %s, skipping",
                        idx,
                        contract_id,
                    )
                    continue

                # Read the total energy used in kilowatt-hours.
                total_kwh = float(record.get("value") or 0.0)

                # Read the off-peak and uncharged/free portions separately.
                offpeak_kwh = float(record.get("offpeakValue") or 0.0)
                unpaid_kwh = float(record.get("unchargedValue") or 0.0)

                # Legacy sanity check: free usage usually appears only on weekends.
                if unpaid_kwh > 0 and interval in ["hourly", "daily"]:
                    try:
                        # Daily values need a made-up midnight time so datetime can parse them cleanly.
                        if interval == "daily":
                            check_date = datetime.fromisoformat(f"{timestamp[:10]}T00:00:00+13:00")
                        else:
                            check_date = datetime.fromisoformat(timestamp)

                        # weekday() returns 0 for Monday through 6 for Sunday.
                        day_of_week = check_date.weekday()
                        is_weekend = day_of_week >= 5

                        # Warn - but do not discard data - if free usage appears on a weekday.
                        if not is_weekend:
                            _LOGGER.warning(
                                "Unexpected free usage on %s (weekday) for contract %s: %.3f kWh. Free hours usually only occur on weekends. Keeping data as-is.",
                                check_date.strftime("%Y-%m-%d %A"),
                                contract_id,
                                unpaid_kwh,
                            )
                    except (ValueError, TypeError) as e:
                        # If the timestamp could not be parsed, we log and keep going.
                        _LOGGER.debug("Could not validate weekend for timestamp %s: %s", timestamp, e)

                # Hourly data uses one business rule; daily/monthly uses another.
                if interval == "hourly":
                    # In hourly mode, a free hour means the whole hour is treated as free.
                    if unpaid_kwh > 0:
                        free_kwh = unpaid_kwh
                        paid_total_kwh = 0.0
                        peak_kwh = 0.0
                        offpeak_kwh = 0.0
                    else:
                        # In normal billed hours, the total is split into peak and off-peak paid usage.
                        free_kwh = 0.0
                        peak_kwh = total_kwh - offpeak_kwh
                        if peak_kwh < 0:
                            _LOGGER.debug(
                                "Capping peak usage at 0 for contract %s at %s: peak calculated negative (total=%.3f, offpeak=%.3f)",
                                contract_id,
                                timestamp,
                                total_kwh,
                                offpeak_kwh,
                            )
                            peak_kwh = 0.0
                        paid_total_kwh = peak_kwh + offpeak_kwh
                else:
                    # In daily/monthly mode, one period can contain both billed and free usage.
                    free_kwh = unpaid_kwh
                    paid_total_kwh = total_kwh - unpaid_kwh
                    peak_kwh = paid_total_kwh - offpeak_kwh
                    if peak_kwh < 0:
                        _LOGGER.debug(
                            "Capping peak usage at 0 for contract %s at %s: peak calculated negative (paid_total=%.3f, offpeak=%.3f)",
                            contract_id,
                            timestamp,
                            paid_total_kwh,
                            offpeak_kwh,
                        )
                        peak_kwh = 0.0

                # Log the calculated values so support can compare parsing decisions.
                _LOGGER.debug(
                    "%s record: timestamp=%s, total=%.3f, paid_total=%.3f, peak=%.3f, offpeak=%.3f, free=%.3f",
                    interval.capitalize(),
                    timestamp,
                    total_kwh,
                    paid_total_kwh,
                    peak_kwh,
                    offpeak_kwh,
                    free_kwh,
                )

                # Read the cost value in New Zealand dollars.
                cost_nzd = float(record.get("dollarValue") or 0.0)

                # Build one standard output record with rounded values.
                parsed_record = {
                    "timestamp": timestamp,
                    "total": round(total_kwh, 3),
                    "paid": round(paid_total_kwh, 3),
                    "peak": round(peak_kwh, 3),
                    "offpeak": round(offpeak_kwh, 3),
                    "free": round(free_kwh, 3),
                    "cost": round(cost_nzd, 2),
                }

                # Store the cleaned record in the output list.
                parsed_records.append(parsed_record)

            except (ValueError, TypeError) as e:
                # If one record contains bad data, log it and move on to the next one.
                _LOGGER.warning(
                    "Failed to parse usage record %d for contract %s: %s. Record: %s",
                    idx,
                    contract_id,
                    str(e),
                    str(record)[:200],
                )
                continue

        # Report how many rows were successfully converted.
        _LOGGER.debug(
            "Successfully parsed %d/%d usage records for contract %s (%s interval)",
            len(parsed_records),
            len(usage_array),
            contract_id,
            interval,
        )

        # Warn if an unusually high share of rows failed to parse.
        if len(usage_array) > 0:
            failure_rate = (len(usage_array) - len(parsed_records)) / len(usage_array)
            if failure_rate > 0.1:
                _LOGGER.warning(
                    "High parse failure rate for contract %s (%s interval): %.1f%% (%d/%d records failed)",
                    contract_id,
                    interval,
                    failure_rate * 100,
                    len(usage_array) - len(parsed_records),
                    len(usage_array),
                )

        # Hand the cleaned list back to the caller.
        return parsed_records
