"""Base API client for Contact Energy.

=== WHAT THIS FILE DOES ===
This module provides the base API client - think of it as the "communication manager"
that handles all interactions with Contact Energy's online services (API).

It handles:
1. Authentication (logging in securely)
2. Token management (keeping track of your login session)
3. Rate limiting (preventing too many requests too quickly)
4. Error handling (dealing with problems that might occur)

All specific API endpoints (like getting account info or usage data) build upon
this base client.

=== FOR NON-CODERS ===
An "API" (Application Programming Interface) is like a waiter at a restaurant:
- You (the code) tell the waiter (API) what you want
- The waiter goes to the kitchen (Contact Energy's servers)
- The waiter brings back your order (the data you requested)

Version: 2.0.0
"""
# This line allows us to use modern Python type hints even in older Python versions
from __future__ import annotations

# ============================================================================
# IMPORTS - External libraries and tools we need
# ============================================================================

# aiohttp: A library for making web requests asynchronously
# "async" means we can do other things while waiting for responses
import aiohttp

# asyncio: Python's built-in library for running async code
import asyncio

# logging: Used to record what's happening (for debugging and monitoring)
import logging

# time: Used for tracking when things happen (for rate limiting)
import time

# typing: Helps us specify what type of data variables should hold
from typing import Any

# datetime: Used for working with dates and times
from datetime import datetime, timedelta

# ============================================================================
# LOGGER SETUP
# ============================================================================
# Create a logger specific to this module
# Loggers help us track what's happening, find bugs, and monitor the system
# Think of it as a diary that records everything the program does
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# API CONFIGURATION - Connection settings for Contact Energy
# ============================================================================

# BASE_URL: The main web address where Contact Energy's API lives
# Think of this as the street address of the Contact Energy server
# All API requests will start with this URL
BASE_URL = "https://api.contact-digital-prod.net"

# API_KEY: A public key that identifies this application to Contact Energy
# NOTE: This is a public key (not a secret) that Contact Energy provides
# It's like showing an ID card - it tells Contact Energy who is making the request
# This is different from authentication tokens which are private and user-specific
API_KEY = "kbIthASA7e1M3NmpMdGrn2Yqe0yHcCjL4QNPSUij"


# ============================================================================
# CUSTOM EXCEPTIONS - Special error types for different problems
# ============================================================================
# Exceptions are Python's way of signaling that something went wrong.
# By creating custom exception types, we can:
# 1. Identify exactly what kind of problem occurred
# 2. Handle different problems in different ways
# 3. Provide more helpful error messages

class ContactEnergyApiError(Exception):
    """Base exception for Contact Energy API errors.
    
    === FOR NON-CODERS ===
    This is the "parent" exception for all Contact Energy API problems.
    Think of it as the general category "Something went wrong with Contact Energy".
    
    All other Contact Energy errors inherit from this one, creating a hierarchy:
    - ContactEnergyApiError (general)
      ├─ ContactEnergyAuthError (login problems)
      └─ ContactEnergyConnectionError (connection problems)
    """
    pass


class ContactEnergyAuthError(ContactEnergyApiError):
    """Raised when authentication fails.
    
    === FOR NON-CODERS ===
    This specific exception is used when login fails. Reasons might include:
    - Wrong email or password
    - Account locked or suspended
    - Token expired and refresh failed
    
    By having a specific error type, we can tell the user "Your login failed"
    instead of just "Something went wrong".
    """
    pass


class ContactEnergyConnectionError(ContactEnergyApiError):
    """Raised when connection to API fails.
    
    === FOR NON-CODERS ===
    This specific exception is used when we can't reach Contact Energy's servers.
    Reasons might include:
    - No internet connection
    - Contact Energy's servers are down
    - Network timeout (took too long to respond)
    - Firewall blocking the connection
    
    This helps distinguish network problems from authentication problems.
    """
    pass


# ============================================================================
# HELPER FUNCTIONS - Utility functions used throughout this module
# ============================================================================

def _redact_sensitive(value: str, prefix_length: int = 3) -> str:
    """Redact sensitive data in logs while keeping prefix for debugging.
    
    === WHAT THIS DOES ===
    When logging information, we want to avoid exposing sensitive data like
    passwords, tokens, or email addresses in full. This function shows just
    enough to help with debugging (the first few characters) while hiding
    the rest.
    
    === FOR NON-CODERS ===
    Imagine showing a credit card number: instead of "1234-5678-9012-3456",
    you might show "123***************" - enough to identify which card,
    but not enough for someone to use it.
    
    Example:
        _redact_sensitive("mypassword123")  → "myp***redacted***"
        _redact_sensitive("user@email.com") → "use***redacted***"
    
    Args:
        value: The sensitive value to redact (hide)
        prefix_length: How many characters to keep visible at the start
        
    Returns:
        Redacted string like "abc***redacted***" for "abcdefgh"
    """
    # If the value is empty or shorter than the prefix, hide everything
    if not value or len(value) <= prefix_length:
        return "***redacted***"
    
    # Show the first few characters, then hide the rest
    # Example: "password" with prefix_length=3 → "pas***redacted***"
    return value[:prefix_length] + "***redacted***"


# ============================================================================
# MAIN API CLIENT CLASS
# ============================================================================

class ContactEnergyApiClient:
    """Base API client for Contact Energy.

    === WHAT THIS CLASS DOES ===
    This is the main "communication manager" that handles all interactions with
    Contact Energy's servers. It's responsible for:
    
    1. Storing your login credentials securely
    2. Authenticating (logging in) to get access tokens
    3. Making API requests with proper authentication
    4. Rate limiting (preventing too many requests too quickly)
    5. Handling errors and timeouts
    6. Managing token expiration
    
    === FOR NON-CODERS ===
    Think of this class as your personal assistant who:
    - Remembers your username and password
    - Logs you in when needed
    - Makes requests on your behalf
    - Deals with any problems that come up
    - Makes sure you don't overwhelm the server with too many requests
    
    All specific API operations (like getting account data or usage data)
    will use this class as their foundation.
    """

    def __init__(self, email: str, password: str):
        """Initialize the API client with credentials.
        
        === WHAT THIS DOES ===
        This is the "constructor" - it sets up a new API client instance.
        When you create a new ContactEnergyApiClient, this method runs first
        to initialize all the variables and settings.

        === FOR NON-CODERS ===
        __init__ is a special method in Python called a "constructor".
        It's like setting up a new employee's desk on their first day:
        - Give them a name badge (email)
        - Set up their computer (password)
        - Create empty folders for files they'll need later (token, segment, etc.)
        - Configure their work schedule (rate limiting)

        Args:
            email: Contact Energy account email address (used to log in)
            password: Contact Energy account password (used to log in)
        """
        # ====================================================================
        # STORE USER CREDENTIALS
        # ====================================================================
        # Save the email and password so we can use them to authenticate later.
        # These are stored in "instance variables" (self.xxx) which means each
        # API client has its own separate copy of these values.
        self.email = email
        self.password = password
        
        # ====================================================================
        # INITIALIZE AUTHENTICATION DATA (empty for now)
        # ====================================================================
        # These values will be filled in after successful authentication:
        
        # token: The authentication token received after login
        # Think of it as a temporary "access badge" that proves you're logged in
        # Without this, API requests will be rejected
        self.token: str | None = None
        
        # segment: User segment information from Contact Energy
        # This might indicate customer type, plan type, or account status
        self.segment: str | None = None
        
        # bp: Business Partner ID from Contact Energy's system
        # This is Contact Energy's internal ID for your account
        self.bp: str | None = None
        
        # account_id: The specific account ID we're working with
        # Users may have multiple accounts, this tracks which one we're using
        self.account_id: str | None = None
        
        # ====================================================================
        # RATE LIMITING CONFIGURATION
        # ====================================================================
        # Rate limiting prevents us from making requests too quickly.
        # Think of it like a speed limit on a road - it keeps traffic flowing
        # smoothly and prevents overwhelming the server.
        
        # _min_interval_seconds: Minimum time (in seconds) between API requests
        # By waiting 0.5 seconds between requests, we:
        # 1. Avoid triggering rate limit blocks from Contact Energy
        # 2. Reduce server load
        # 3. Prevent transient errors from rapid-fire requests
        self._min_interval_seconds: float = 0.5
        
        # _last_request_monotonic: Timestamp of the last API request we made
        # We use "monotonic" time (time.monotonic()) instead of regular time because:
        # - Monotonic time always moves forward (never goes backward)
        # - It's not affected by system time changes (like daylight saving)
        # - It's perfect for measuring elapsed time
        # Starting at 0.0 means "no requests made yet"
        self._last_request_monotonic: float = 0.0
        
        # ====================================================================
        # TIMEOUT CONFIGURATION
        # ====================================================================
        # Timeouts prevent requests from hanging forever if the server is slow
        # or unresponsive. Different operations have different timeout limits:
        
        # _auth_timeout: How long to wait for authentication (10 seconds)
        # Auth should be quick, so we use a short timeout
        self._auth_timeout: float = 10.0
        
        # _accounts_timeout: How long to wait for account info (10 seconds)
        # Account data is small and should return quickly
        self._accounts_timeout: float = 10.0
        
        # _usage_timeout: How long to wait for usage data (30 seconds)
        # Usage data can be large (months of hourly readings), so we allow
        # more time for the server to process and return the data
        self._usage_timeout: float = 30.0
        
        # ====================================================================
        # TOKEN EXPIRY TRACKING
        # ====================================================================
        # _token_expires_at: When the current authentication token expires
        # Contact Energy tokens typically last 24 hours, after which we need
        # to re-authenticate. By tracking when it expires, we can proactively
        # refresh before it becomes invalid.
        # None means we don't have a token yet
        self._token_expires_at: datetime | None = None

    async def _throttle(self) -> None:
        """Enforce a minimal interval between outbound API calls.
        
        === WHAT THIS DOES ===
        This method implements "rate limiting" - it ensures we don't make
        API requests too quickly. If we called the API too recently, this
        method pauses (sleeps) until enough time has passed.

        === FOR NON-CODERS ===
        Imagine a bouncer at a club who only lets people in every 30 seconds.
        If someone tries to enter too soon after the last person, the bouncer
        says "wait a bit" until the time is right. This prevents overcrowding.
        
        Similarly, this method prevents us from "flooding" Contact Energy's
        servers with too many requests at once, which could:
        - Trigger rate limits (getting blocked)
        - Cause server errors
        - Slow down responses for everyone
        
        The method keeps traffic polite and reduces transient 4xx/5xx errors
        due to bursts of requests.
        """
        # ====================================================================
        # STEP 1: Get the current time
        # ====================================================================
        # time.monotonic() gives us a timestamp that always moves forward
        # Think of it as a stopwatch that can't be reset or adjusted
        now = time.monotonic()
        
        # ====================================================================
        # STEP 2: Calculate how much time has passed since last request
        # ====================================================================
        # elapsed = current time - last request time
        # For example:
        # - If last request was at 100.0 seconds and now is 100.3 seconds
        # - Then elapsed = 0.3 seconds
        elapsed = now - self._last_request_monotonic
        
        # ====================================================================
        # STEP 3: If not enough time has passed, wait (sleep)
        # ====================================================================
        # We want at least _min_interval_seconds (0.5 seconds) between requests
        # If elapsed < 0.5 seconds, we need to wait longer
        if elapsed < self._min_interval_seconds:
            # Calculate how much longer we need to wait
            # For example:
            # - We want 0.5 seconds between requests
            # - Only 0.3 seconds have passed
            # - So we sleep for 0.5 - 0.3 = 0.2 seconds
            sleep_time = self._min_interval_seconds - elapsed
            
            # asyncio.sleep() pauses this function without blocking other tasks
            # "await" means "pause here until sleep is done, but let other code run"
            await asyncio.sleep(sleep_time)
        
        # ====================================================================
        # STEP 4: Update the last request time to now
        # ====================================================================
        # Record when this request happened so the next call knows when to wait
        # We get the time again (instead of using 'now') because we might have
        # slept, so the actual time now is later than 'now' was earlier
        self._last_request_monotonic = time.monotonic()

    async def authenticate(self) -> dict[str, Any]:
        """Authenticate with Contact Energy API and retrieve token.
        
        === WHAT THIS DOES ===
        This method logs into Contact Energy's servers using your email and password.
        If successful, it receives an authentication "token" (like a temporary pass)
        that can be used for subsequent API requests.
        
        === FOR NON-CODERS ===
        Think of this like checking into a hotel:
        1. You show your ID and reservation (email/password)
        2. The hotel verifies who you are
        3. They give you a key card (token) to access your room
        4. You use that key card for the rest of your stay
        
        This method should be called before making any other API requests because
        you need the "token" (key card) to access protected resources.

        Returns:
            Dictionary containing authentication response with:
            - token: The authentication token for subsequent requests
            - segment: User segment information
            - bp: Business Partner ID

        Raises:
            ContactEnergyAuthError: If authentication fails (wrong credentials)
            ContactEnergyConnectionError: If unable to connect to API (network issue)
        """
        # ====================================================================
        # STEP 1: Apply rate limiting
        # ====================================================================
        # Before making any API call, ensure we're not sending requests too quickly
        # This calls our _throttle() method which will sleep if needed
        await self._throttle()
        
        # ====================================================================
        # STEP 2: Prepare the API request
        # ====================================================================
        
        # Build the full URL for the login endpoint
        # f-string (f"...{variable}...") inserts variable values into strings
        # Example: f"{BASE_URL}/login/v2" becomes "https://api.contact-digital-prod.net/login/v2"
        url = f"{BASE_URL}/login/v2"
        
        # Headers are like the "envelope" of a letter - they contain metadata
        # about the request (not the actual data being sent)
        headers = {
            # x-api-key: Identifies this application to Contact Energy
            "x-api-key": API_KEY,
            # Content-Type: Tells the server we're sending JSON data
            "Content-Type": "application/json",
        }
        
        # Payload is the actual data we're sending (the "letter" inside the envelope)
        # This contains the user's credentials
        payload = {
            # "username" is what Contact Energy calls it, even though it's an email
            "username": self.email,
            # The password, sent securely over HTTPS (encrypted)
            "password": self.password,
        }

        # ====================================================================
        # STEP 3: Log what we're about to do (for debugging)
        # ====================================================================
        # Write a debug message to the log file
        # We redact (hide) most of the email for security
        # Example: "user@example.com" becomes "use***redacted***"
        _LOGGER.debug(
            "Authenticating with Contact Energy API as %s",
            _redact_sensitive(self.email)
        )

        # ====================================================================
        # STEP 4: Make the HTTP request with error handling
        # ====================================================================
        # try/except blocks handle errors gracefully
        # "try" means "attempt this code, but be ready for errors"
        try:
            # ------------------------------------------------------------
            # Create a timeout configuration
            # ------------------------------------------------------------
            # This ensures the request won't wait forever
            # If 10 seconds pass with no response, give up
            timeout = aiohttp.ClientTimeout(total=self._auth_timeout)
            
            # ------------------------------------------------------------
            # Create an HTTP session
            # ------------------------------------------------------------
            # "async with" means "use this resource, then clean it up automatically"
            # Think of it like borrowing a book from the library - you use it,
            # then it gets returned automatically when you're done
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # --------------------------------------------------------
                # Make a POST request to the login endpoint
                # --------------------------------------------------------
                # POST means we're sending data to the server (unlike GET which just asks for data)
                # We send: URL, JSON payload, and headers
                async with session.post(url, json=payload, headers=headers) as response:
                    # ====================================================
                    # CHECK 1: Did we get rejected due to bad credentials?
                    # ====================================================
                    # HTTP status code 401 means "Unauthorized" - bad login
                    if response.status == 401:
                        # Raise (throw) an error that will be caught by the except block
                        # This stops execution here and jumps to error handling
                        raise ContactEnergyAuthError("Invalid email or password")
                    
                    # ====================================================
                    # CHECK 2: Did we get any other error?
                    # ====================================================
                    # HTTP status code 200 means "OK" - success
                    # Any other code is an error
                    if response.status != 200:
                        # Get the error message from the response
                        # await means "wait for the text to download"
                        error_text = await response.text()
                        
                        # Log the error for debugging
                        _LOGGER.error(
                            "Authentication failed with status %d: %s",
                            response.status,
                            error_text
                        )
                        
                        # Raise an error with a descriptive message
                        raise ContactEnergyAuthError(
                            f"Authentication failed with status {response.status}"
                        )

                    # ====================================================
                    # SUCCESS: Parse the response data
                    # ====================================================
                    # If we reach here, authentication succeeded!
                    # Parse the JSON response into a Python dictionary
                    # await means "wait for the JSON to be parsed"
                    data = await response.json()

                    # ====================================================
                    # STEP 5: Store authentication details for later use
                    # ====================================================
                    
                    # Extract the token from the response
                    # .get("token") safely retrieves the token, returns None if missing
                    self.token = data.get("token")
                    
                    # Extract segment information
                    self.segment = data.get("segment")
                    
                    # Extract Business Partner ID
                    self.bp = data.get("bp")
                    
                    # ------------------------------------------------
                    # Calculate when the token expires
                    # ------------------------------------------------
                    # Contact Energy tokens typically last 24 hours
                    # We set expiry to 23 hours to refresh before it actually expires
                    # datetime.now() = current date/time
                    # timedelta(hours=23) = 23 hours from now
                    self._token_expires_at = datetime.now() + timedelta(hours=23)

                    # ====================================================
                    # CHECK 3: Verify we got a token
                    # ====================================================
                    # If the response didn't include a token, something is wrong
                    if not self.token:
                        raise ContactEnergyAuthError("No token in authentication response")

                    # ====================================================
                    # SUCCESS: Log and return
                    # ====================================================
                    # Record successful authentication
                    _LOGGER.info("Successfully authenticated with Contact Energy API")
                    
                    # Return the full authentication data to the caller
                    return data

        # ====================================================================
        # ERROR HANDLING: Catch specific network errors
        # ====================================================================
        
        # Catch network/connection errors
        # "except Type as variable" means "if this error type occurs, store it in variable"
        except aiohttp.ClientError as err:
            # Log the connection error
            _LOGGER.error("Connection error during authentication: %s", err)
            
            # Re-raise as our custom exception type
            # "from err" preserves the original error for debugging
            raise ContactEnergyConnectionError(
                f"Failed to connect to Contact Energy API: {err}"
            ) from err
            
        # Catch timeout errors (request took too long)
        except asyncio.TimeoutError as err:
            # Log the timeout
            _LOGGER.error("Timeout during authentication")
            
            # Re-raise as our custom exception type
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
