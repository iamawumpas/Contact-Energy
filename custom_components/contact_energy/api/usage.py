"""Usage API endpoints for Contact Energy.

This module provides methods for retrieving usage data (hourly, daily, monthly)
from the Contact Energy API. It extends the base API client.

Version: 2.0.0
"""
from __future__ import annotations

import logging
from typing import Any
from datetime import date

from .client import ContactEnergyApiClient

_LOGGER = logging.getLogger(__name__)


class ContactEnergyUsageApi(ContactEnergyApiClient):
    """API client for Contact Energy usage endpoints.

    This class provides methods to retrieve usage data at different intervals:
    - Hourly usage (kWh per hour)
    - Daily usage (kWh per day)
    - Monthly usage (kWh per month)
    
    Each method returns both paid and free/off-peak usage data.
    """

    async def get_hourly_usage(
        self,
        contract_id: str,
        from_date: date,
        to_date: date,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve hourly usage data from Contact Energy API.

        Fetches hourly electricity usage for the specified date range.
        Each hour includes paid usage, free usage, and cost information.

        Args:
            contract_id: Contract ID for the account
            from_date: Start date for usage data
            to_date: End date for usage data
            account_id: Account ID (BA number). If None, uses self.account_id.

        Returns:
            List of hourly usage records

        Raises:
            ContactEnergyAuthError: If not authenticated or token expired
            ContactEnergyApiError: If API request fails
        """
        ba = account_id or self.account_id or ""
        
        _LOGGER.debug(
            "Fetching hourly usage for contract %s from %s to %s",
            contract_id,
            from_date,
            to_date
        )

        endpoint = f"/usage/v2/{contract_id}"
        params = {
            "ba": ba,
            "interval": "hourly",
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        response = await self._make_request(
            method="POST",
            endpoint=endpoint,
            params=params,
            timeout=self._usage_timeout,
        )

        if isinstance(response, list):
            _LOGGER.debug("Retrieved %d hourly usage records", len(response))
            return response
        else:
            _LOGGER.warning("Unexpected response format for hourly usage")
            return []

    async def get_daily_usage(
        self,
        contract_id: str,
        from_date: date,
        to_date: date,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve daily usage data from Contact Energy API.

        Fetches daily electricity usage for the specified date range.
        Each day includes paid usage, free usage, and cost information.

        Args:
            contract_id: Contract ID for the account
            from_date: Start date for usage data
            to_date: End date for usage data
            account_id: Account ID (BA number). If None, uses self.account_id.

        Returns:
            List of daily usage records

        Raises:
            ContactEnergyAuthError: If not authenticated or token expired
            ContactEnergyApiError: If API request fails
        """
        ba = account_id or self.account_id or ""
        
        _LOGGER.debug(
            "Fetching daily usage for contract %s from %s to %s",
            contract_id,
            from_date,
            to_date
        )

        endpoint = f"/usage/v2/{contract_id}"
        params = {
            "ba": ba,
            "interval": "daily",
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        response = await self._make_request(
            method="POST",
            endpoint=endpoint,
            params=params,
            timeout=self._usage_timeout,
        )

        if isinstance(response, list):
            _LOGGER.debug("Retrieved %d daily usage records", len(response))
            return response
        else:
            _LOGGER.warning("Unexpected response format for daily usage")
            return []

    async def get_monthly_usage(
        self,
        contract_id: str,
        from_date: date,
        to_date: date,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve monthly usage data from Contact Energy API.

        Fetches monthly electricity usage for the specified date range.
        Each month includes paid usage, free usage, and cost information.

        Args:
            contract_id: Contract ID for the account
            from_date: Start date for usage data
            to_date: End date for usage data
            account_id: Account ID (BA number). If None, uses self.account_id.

        Returns:
            List of monthly usage records

        Raises:
            ContactEnergyAuthError: If not authenticated or token expired
            ContactEnergyApiError: If API request fails
        """
        ba = account_id or self.account_id or ""
        
        _LOGGER.debug(
            "Fetching monthly usage for contract %s from %s to %s",
            contract_id,
            from_date,
            to_date
        )

        endpoint = f"/usage/v2/{contract_id}"
        params = {
            "ba": ba,
            "interval": "monthly",
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
        }

        response = await self._make_request(
            method="POST",
            endpoint=endpoint,
            params=params,
            timeout=self._usage_timeout,
        )

        if isinstance(response, list):
            _LOGGER.debug("Retrieved %d monthly usage records", len(response))
            return response
        else:
            _LOGGER.warning("Unexpected response format for monthly usage")
            return []
