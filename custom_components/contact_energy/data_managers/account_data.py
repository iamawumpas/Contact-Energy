"""Account data manager for Contact Energy.

This module manages account data caching including balance, billing, contracts,
and account settings. Cache file: {address}_{icp}.json

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .base_cache import BaseCache

_LOGGER = logging.getLogger(__name__)

# Staleness configuration for account data
ACCOUNT_STALENESS_HOURS = 6  # Re-download if >6 hours old


class AccountDataManager(BaseCache):
    """Manager for account data caching.

    Handles caching of:
    - Account balance and refund information
    - Invoice details and payment due dates
    - Next bill predictions
    - Contract information
    - Account settings
    - Payment plan status

    Cache file: {address}_{icp}.json
    Staleness: Re-download if >6 hours since last download OR no data exists
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: {address}_{icp}.json

        NOTE: Changed from account_{address}_{icp}.json per user request
        to keep account details less obvious.
        """
        return f"{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty account cache structure."""
        return {
            "metadata": {
                "version": "2.0.0",
                "address": self.address,
                "icp": self.icp,
                "last_download": None,
                "last_api_timestamp": None,
            },
            "account_data": None,
        }

    def is_stale(self) -> bool:
        """Check if account data is stale.

        Staleness rules:
        - No data exists: STALE
        - Last download >6 hours ago: STALE
        - Otherwise: FRESH

        Returns:
            True if data needs refresh
        """
        # No data = stale
        if not self.data.get("account_data"):
            _LOGGER.debug("Account data is stale: no data")
            return True

        # Check download timestamp
        hours_old = self.hours_since_last_download()
        if hours_old >= ACCOUNT_STALENESS_HOURS:
            _LOGGER.debug(
                "Account data is stale: %.1f hours old (limit: %d)",
                hours_old,
                ACCOUNT_STALENESS_HOURS
            )
            return True

        _LOGGER.debug("Account data is fresh: %.1f hours old", hours_old)
        return False

    def prune(self) -> None:
        """Prune old data.

        Account data doesn't accumulate over time, so no pruning needed.
        This method is here for interface compliance.
        """
        pass

    def update(self, account_data: dict[str, Any]) -> None:
        """Update cache with new account data.

        Args:
            account_data: Raw account data from API
        """
        self.data["account_data"] = account_data
        
        # Update metadata
        if "metadata" not in self.data:
            self.data["metadata"] = self._create_empty_cache()["metadata"]
        
        self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()
        
        # Try to extract API timestamp from data if available
        # This would be the timestamp from the API response
        self.data["metadata"]["last_api_timestamp"] = datetime.now(timezone.utc).isoformat()

        _LOGGER.info("Updated account data cache for %s_%s", self.address, self.icp)

    def get_account_data(self) -> dict[str, Any] | None:
        """Get cached account data.

        Returns:
            Account data dictionary, or None if no data cached
        """
        return self.data.get("account_data")

    def get_balance(self) -> dict[str, Any] | None:
        """Get account balance data.

        Returns:
            Balance data, or None if not available
        """
        account_data = self.get_account_data()
        if not account_data:
            return None
        account_detail = account_data.get("accountDetail", {})
        return account_detail.get("accountBalance")

    def get_invoice(self) -> dict[str, Any] | None:
        """Get invoice data.

        Returns:
            Invoice data, or None if not available
        """
        account_data = self.get_account_data()
        if not account_data:
            return None
        account_detail = account_data.get("accountDetail", {})
        return account_detail.get("invoice")

    def get_next_bill(self) -> dict[str, Any] | None:
        """Get next bill data.

        Returns:
            Next bill data, or None if not available
        """
        account_data = self.get_account_data()
        if not account_data:
            return None
        account_detail = account_data.get("accountDetail", {})
        return account_detail.get("nextBill")

    def get_contracts(self) -> list[dict[str, Any]]:
        """Get contracts data.

        Returns:
            List of contracts, or empty list if not available
        """
        account_data = self.get_account_data()
        if not account_data:
            return []
        account_detail = account_data.get("accountDetail", {})
        return account_detail.get("contracts", [])
