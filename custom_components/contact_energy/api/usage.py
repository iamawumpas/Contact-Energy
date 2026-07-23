"""Usage API endpoints for Contact Energy.

=== WHAT THIS DOES ===
This module provides methods for retrieving electricity usage data from the
Contact Energy API at different time intervals.

It knows how to ask Contact Energy for:
1. Hourly usage (one reading per hour)
2. Daily usage (one reading per day)
3. Monthly usage (one reading per month)

Each method prepares the correct API request, sends it to Contact Energy's
servers, and returns the usage data in a format the rest of the integration can
use.

=== FOR NON-CODERS ===
Think of this file as a specialist assistant whose only job is to answer the
question: "How much power was used, and when was it used?"

It does not log in by itself and it does not handle all account features.
Instead, it builds on the base API client and focuses only on usage history.

Helpful concepts:
- "API" = a way for one computer program to ask another program for data
- "async" = the code can wait for internet responses without freezing everything
- "await" = pause here until the network reply comes back
- "parameters" = extra details sent with a request, like date range and account ID
- "JSON" = a common data format used by web services; Python turns it into lists
  and dictionaries so this code can work with it easily

Version: 2.0.0
"""
# This line allows us to use modern Python type hints even in older Python versions.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: Used to record what this module is doing so developers can debug
# problems and understand what requests were made.
import logging

# typing.Any: Used in type hints when returned dictionary values may contain
# different kinds of data (numbers, text, true/false values, nested objects, etc.).
from typing import Any

# datetime.date: Used to represent calendar dates like 2026-07-23 without a time.
# We use date objects so callers pass clear, structured start/end dates.
from datetime import date

# ContactEnergyApiClient: The base client that already knows how to log in,
# make authenticated API requests, handle errors, and enforce timeouts.
from .client import ContactEnergyApiClient

# ============================================================================
# LOGGER SETUP
# ============================================================================
# Create a logger specific to this module.
# A logger is like an internal diary that records what the code is doing.
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# USAGE API CLASS
# ============================================================================

class ContactEnergyUsageApi(ContactEnergyApiClient):
    """API client for Contact Energy usage endpoints.

    === WHAT THIS CLASS DOES ===
    This class adds usage-specific API methods on top of the shared base client.
    It inherits authentication, request handling, rate limiting, and timeout
    support from ContactEnergyApiClient, then adds the exact requests needed for
    usage history.

    === WHY THIS EXISTS ===
    Keeping usage-related logic in its own class makes the code easier to read,
    maintain, and extend. Account details and usage history are different kinds
    of information, so they are separated into different modules.

    === FOR NON-CODERS ===
    Inheritance means this class starts with all the skills of the base client,
    then adds a new specialty: fetching usage data.

    Think of it like this:
    - The base client knows how to talk to Contact Energy safely
    - This class knows which usage questions to ask

    This class provides methods to retrieve:
    - Hourly usage data
    - Daily usage data
    - Monthly usage data
    """

    async def get_hourly_usage(
        self,
        contract_id: str,
        from_date: date,
        to_date: date,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve hourly usage data from Contact Energy API.

        === WHAT THIS DOES ===
        This method asks Contact Energy for electricity usage broken down by
        hour for a specific contract and date range.

        === WHY THIS EXISTS ===
        Hourly data is useful when the integration wants the most detailed view
        of energy usage, such as seeing patterns throughout the day.

        === FOR NON-CODERS ===
        This is like asking for a highly detailed timesheet of power usage where
        every hour gets its own entry.

        "async" means this method performs network work in a non-blocking way.
        While waiting for Contact Energy's servers to respond, Python can let
        other tasks continue.

        "await" means "pause at this line until the reply comes back."

        Args:
            contract_id: The specific contract whose usage we want to look up.
            from_date: The first day to include in the request.
            to_date: The last day to include in the request.
            account_id: Optional account ID (BA number). If not supplied, the
                method falls back to the account ID already stored on the client.

        Returns:
            A list of usage records.

            In Python, a "list" is an ordered collection of items.
            Each item in the list is a "dictionary" (a label/value structure)
            containing one usage record.

            The Contact Energy server likely sends this back as JSON, and the
            base API client converts that JSON into normal Python data.

        Raises:
            ContactEnergyAuthError: If login is missing or expired.
            ContactEnergyApiError: If the request fails.
        """
        # ====================================================================
        # STEP 1: Decide which account ID (BA number) to send
        # ====================================================================
        # We try values in this order:
        # 1. Use the account_id passed into this method
        # 2. If that is missing, use self.account_id already stored on the client
        # 3. If both are missing, use an empty string so the request still has a value
        #
        # The "or" operator here means "use the first non-empty / non-None value".
        ba = account_id or self.account_id or ""

        # ====================================================================
        # STEP 2: Record what request we are about to make
        # ====================================================================
        # This debug log helps developers trace which usage request was made.
        # Logging is useful when diagnosing issues with dates, contracts, or API behavior.
        _LOGGER.debug(
            "Fetching hourly usage for contract %s from %s to %s",
            contract_id,
            from_date,
            to_date,
        )

        # ====================================================================
        # STEP 3: Build the API endpoint URL path
        # ====================================================================
        # An endpoint is the specific address on the server for one kind of data.
        # Here we insert the contract ID into the URL path so Contact Energy knows
        # exactly which contract's usage history we are requesting.
        endpoint = f"/usage/v2/{contract_id}"

        # ====================================================================
        # STEP 4: Build the request parameters
        # ====================================================================
        # Parameters are extra details sent with the request.
        # They tell Contact Energy:
        # - which account (ba)
        # - which grouping interval we want (hourly)
        # - the start date (from)
        # - the end date (to)
        #
        # strftime("%Y-%m-%d") converts a Python date object into plain text like
        # "2026-07-23", which is the format the API expects.
        params = {
            "ba": ba,
            "interval": "hourly",
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        # ====================================================================
        # STEP 5: Make the API call
        # ====================================================================
        # We call the shared _make_request method provided by the base client.
        # That method handles the lower-level work such as authentication,
        # timeouts, and interpreting the server's JSON response.
        #
        # method="POST": This API expects a POST request for usage queries.
        # endpoint=endpoint: The usage URL path we built above.
        # params=params: The details describing what data we want.
        # timeout=self._usage_timeout: Allow extra time because usage requests
        # can involve a lot of data.
        response = await self._make_request(
            method="POST",
            endpoint=endpoint,
            params=params,
            timeout=self._usage_timeout,
        )

        # ====================================================================
        # STEP 6: Check whether the server returned the format we expected
        # ====================================================================
        # We expect usage data to come back as a list.
        # If it is a list, that means the structure looks correct.
        if isinstance(response, list):
            # Log how many hourly records we received.
            # len(response) counts the number of items in the list.
            _LOGGER.debug("Retrieved %d hourly usage records", len(response))

            # Return the usage records to the caller.
            # The caller can then display or process the hourly data.
            return response
        else:
            # If the response is not a list, the API returned something unexpected.
            # We log a warning so developers know the data shape was unusual.
            _LOGGER.warning("Unexpected response format for hourly usage")

            # Return an empty list instead of failing here.
            # This gives the rest of the integration a safe, predictable result.
            return []

    async def get_daily_usage(
        self,
        contract_id: str,
        from_date: date,
        to_date: date,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve daily usage data from Contact Energy API.

        === WHAT THIS DOES ===
        This method asks Contact Energy for electricity usage grouped by day.

        === WHY THIS EXISTS ===
        Daily data provides a middle ground between highly detailed hourly data
        and high-level monthly summaries. It is useful for charts, comparisons,
        and daily trend tracking.

        === FOR NON-CODERS ===
        Instead of getting one record for every hour, this asks for one record
        for every day. That makes the result easier to summarize.

        Args:
            contract_id: The contract whose daily usage we want.
            from_date: The first date to include.
            to_date: The last date to include.
            account_id: Optional BA number override.

        Returns:
            A list of daily usage records, with JSON data already converted into
            normal Python objects by the base client.

        Raises:
            ContactEnergyAuthError: If login is missing or expired.
            ContactEnergyApiError: If the request fails.
        """
        # ====================================================================
        # STEP 1: Choose the account ID to use
        # ====================================================================
        # Fallback order:
        # - explicit account_id parameter
        # - stored self.account_id value
        # - empty string if neither is available
        ba = account_id or self.account_id or ""

        # ====================================================================
        # STEP 2: Log the request details for debugging
        # ====================================================================
        _LOGGER.debug(
            "Fetching daily usage for contract %s from %s to %s",
            contract_id,
            from_date,
            to_date,
        )

        # ====================================================================
        # STEP 3: Build the endpoint for this contract
        # ====================================================================
        endpoint = f"/usage/v2/{contract_id}"

        # ====================================================================
        # STEP 4: Build the parameters for a daily usage request
        # ====================================================================
        # The only difference from hourly usage is interval="daily".
        params = {
            "ba": ba,
            "interval": "daily",
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        # ====================================================================
        # STEP 5: Send the request and wait for the response
        # ====================================================================
        response = await self._make_request(
            method="POST",
            endpoint=endpoint,
            params=params,
            timeout=self._usage_timeout,
        )

        # ====================================================================
        # STEP 6: Validate the response shape and return safe output
        # ====================================================================
        if isinstance(response, list):
            # Record how many daily entries were returned.
            _LOGGER.debug("Retrieved %d daily usage records", len(response))

            # Return the correctly formatted list of daily usage records.
            return response
        else:
            # Warn if the API returned something other than the expected list.
            _LOGGER.warning("Unexpected response format for daily usage")

            # Return an empty list so calling code does not break.
            return []

    async def get_monthly_usage(
        self,
        contract_id: str,
        from_date: date,
        to_date: date,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve monthly usage data from Contact Energy API.

        === WHAT THIS DOES ===
        This method asks Contact Energy for electricity usage grouped by month.

        === WHY THIS EXISTS ===
        Monthly data is useful for long-term summaries, billing-style views, and
        higher-level comparisons across long time periods.

        === FOR NON-CODERS ===
        This is the most summarized version of usage in this file. Instead of
        showing every hour or every day, it groups usage into monthly totals.

        Args:
            contract_id: The contract whose monthly usage we want.
            from_date: The first date to include.
            to_date: The last date to include.
            account_id: Optional BA number override.

        Returns:
            A list of monthly usage records.

        Raises:
            ContactEnergyAuthError: If login is missing or expired.
            ContactEnergyApiError: If the request fails.
        """
        # ====================================================================
        # STEP 1: Decide which BA number to send with the request
        # ====================================================================
        ba = account_id or self.account_id or ""

        # ====================================================================
        # STEP 2: Log the planned monthly usage lookup
        # ====================================================================
        _LOGGER.debug(
            "Fetching monthly usage for contract %s from %s to %s",
            contract_id,
            from_date,
            to_date,
        )

        # ====================================================================
        # STEP 3: Build the endpoint path for this contract
        # ====================================================================
        endpoint = f"/usage/v2/{contract_id}"

        # ====================================================================
        # STEP 4: Build the request parameters for monthly data
        # ====================================================================
        # The key difference here is interval="monthly".
        params = {
            "ba": ba,
            "interval": "monthly",
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        # ====================================================================
        # STEP 5: Ask the base client to perform the API request
        # ====================================================================
        response = await self._make_request(
            method="POST",
            endpoint=endpoint,
            params=params,
            timeout=self._usage_timeout,
        )

        # ====================================================================
        # STEP 6: Return valid results, or a safe fallback if format is unexpected
        # ====================================================================
        if isinstance(response, list):
            # Log the number of monthly records returned.
            _LOGGER.debug("Retrieved %d monthly usage records", len(response))

            # Pass the monthly data back to the caller.
            return response
        else:
            # Warn developers that the response shape was not what this method expects.
            _LOGGER.warning("Unexpected response format for monthly usage")

            # Return an empty list as a defensive fallback.
            return []
