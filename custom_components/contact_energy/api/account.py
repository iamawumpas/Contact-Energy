"""Account API endpoints for Contact Energy.

This module provides methods for retrieving account information from the
Contact Energy API. It extends the base API client.

Version: 2.0.0
"""
from __future__ import annotations

import logging
from typing import Any

from .client import ContactEnergyApiClient

_LOGGER = logging.getLogger(__name__)


class ContactEnergyAccountApi(ContactEnergyApiClient):
    """API client for Contact Energy account endpoints.

    This class provides methods to retrieve account data including balance,
    billing information, contracts, and payment details.
    """

    async def get_account_data(self, account_id: str | None = None) -> dict[str, Any]:
        """Retrieve account information from Contact Energy API.

        Fetches complete account information including:
        - Account balance and refund information
        - Invoice details and payment due dates
        - Next bill predictions
        - Contract information
        - Account settings and preferences
        - Payment plan status

        Args:
            account_id: Account ID (BA number). If None, uses self.account_id or empty string.

        Returns:
            Dictionary containing complete account data

        Raises:
            ContactEnergyAuthError: If not authenticated or token expired
            ContactEnergyApiError: If API request fails
        """
        ba = account_id or self.account_id or ""
        
        _LOGGER.debug("Fetching account data for BA: %s", ba or "default")

        response = await self._make_request(
            method="GET",
            endpoint="/accounts/v2",
            params={"ba": ba},
            timeout=self._accounts_timeout,
        )

        _LOGGER.debug("Successfully retrieved account data")
        return response
