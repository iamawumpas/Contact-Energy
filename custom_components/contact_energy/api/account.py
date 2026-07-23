"""Account API endpoints for Contact Energy.

=== WHAT THIS FILE DOES ===
This module provides methods specifically for retrieving account information
from the Contact Energy API. It builds upon the base API client to add
account-specific functionality.

Think of this as a specialized department that handles account-related requests:
- Balance inquiries
- Billing information
- Contract details
- Payment information

=== FOR NON-CODERS ===
This file extends (builds upon) the base API client by adding methods that
understand how to ask Contact Energy for account-specific information.

If the base client is like a general mail service, this is like the department
that specifically handles account inquiries - it knows exactly what to ask for
and how to format those requests.

Version: 2.0.0
"""
# This line allows us to use modern Python type hints even in older Python versions
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: Used to record what's happening (for debugging and monitoring)
import logging

# typing.Any: Used to indicate "any type of data" in type hints
from typing import Any

# Import the base API client that this class extends
from .client import ContactEnergyApiClient

# ============================================================================
# LOGGER SETUP
# ============================================================================
# Create a logger specific to this module for tracking what happens
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# ACCOUNT API CLASS
# ============================================================================

class ContactEnergyAccountApi(ContactEnergyApiClient):
    """API client for Contact Energy account endpoints.
    
    === WHAT THIS CLASS DOES ===
    This class specializes in retrieving account information from Contact Energy.
    It inherits from (extends) ContactEnergyApiClient, which means it has all
    the base functionality (authentication, rate limiting, error handling) plus
    account-specific methods.

    === FOR NON-CODERS ===
    Inheritance (extending a class) is like being a specialist who also has
    general skills:
    - A heart surgeon (this class) is also a doctor (base class)
    - They have all the general medical knowledge (inherited methods)
    - Plus specialized heart surgery skills (account-specific methods)
    
    This class provides methods to retrieve:
    - Account balance and refund information
    - Invoice details and payment due dates
    - Next bill predictions
    - Contract information (your electricity/gas agreements)
    - Account settings and preferences
    - Payment plan status
    """

    async def get_account_data(self, account_id: str | None = None) -> dict[str, Any]:
        """Retrieve account information from Contact Energy API.
        
        === WHAT THIS DOES ===
        This method fetches complete account information for a Contact Energy
        account. It retrieves everything Contact Energy knows about your account:
        billing, payments, contracts, balances, etc.

        === FOR NON-CODERS ===
        Think of this like calling your bank and asking for a complete account
        statement. You give them your account number, and they tell you:
        - Your current balance
        - Upcoming payments
        - Past invoices
        - Your service agreements
        - Any special payment arrangements

        Fetches complete account information including:
        - Account balance and refund information
        - Invoice details and payment due dates
        - Next bill predictions
        - Contract information
        - Account settings and preferences
        - Payment plan status

        Args:
            account_id: Account ID (BA number) from Contact Energy
                       BA = "Business Account" number
                       If None, uses the account_id stored in the client
                       If that's also None, uses empty string

        Returns:
            Dictionary containing complete account data
            A dictionary is like a filing cabinet with labeled folders
            Each piece of information has a label (key) and value

        Raises:
            ContactEnergyAuthError: If not authenticated or token expired
            ContactEnergyApiError: If API request fails
        """
        # ====================================================================
        # STEP 1: Determine which account ID to use
        # ====================================================================
        # The "or" operator provides fallback values:
        # Try account_id parameter first
        # If that's None/empty, try self.account_id
        # If that's also None/empty, use empty string ""
        # 
        # Example:
        # - If account_id = "12345", ba = "12345"
        # - If account_id = None and self.account_id = "67890", ba = "67890"
        # - If both are None, ba = ""
        ba = account_id or self.account_id or ""
        
        # ====================================================================
        # STEP 2: Log what we're about to do
        # ====================================================================
        # Record this operation for debugging
        # If ba is empty, show "default" in the log instead of empty string
        _LOGGER.debug("Fetching account data for BA: %s", ba or "default")

        # ====================================================================
        # STEP 3: Make the API request
        # ====================================================================
        # Call the _make_request method (inherited from the base class)
        # to fetch account data from Contact Energy
        #
        # Parameters explained:
        # - method="GET": We're retrieving (GETting) data, not sending data
        # - endpoint="/accounts/v2": The specific API address for account data
        #   "v2" means version 2 of this API endpoint
        # - params={"ba": ba}: URL parameter - adds "?ba=12345" to the URL
        #   This tells Contact Energy which account we want info about
        # - timeout=self._accounts_timeout: Use account-specific timeout (10 seconds)
        #   Different endpoints have different timeout settings
        #
        # "await" means: pause here until the request completes, but let other
        # code run in the meantime (asynchronous operation)
        response = await self._make_request(
            method="GET",
            endpoint="/accounts/v2",
            params={"ba": ba},
            timeout=self._accounts_timeout,
        )

        # ====================================================================
        # STEP 4: Log success and return the data
        # ====================================================================
        # Record that we successfully got the data
        _LOGGER.debug("Successfully retrieved account data")
        
        # Return the response to the caller
        # response is a dictionary containing all the account information
        return response

