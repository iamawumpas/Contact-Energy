"""Account data coordinator for Contact Energy integration.

This module provides the AccountCoordinator that manages account data
using the v2.0.0 architecture with separate API client and data manager.

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..api.account import ContactEnergyAccountApi
from ..data_managers.account_data import AccountDataManager
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Update interval for account data (check every 6 hours)
ACCOUNT_UPDATE_INTERVAL = timedelta(hours=6)


class AccountCoordinator(DataUpdateCoordinator):
    """Coordinator for Contact Energy account data.

    This coordinator manages the lifecycle of account data:
    1. Check if cached data is stale
    2. If stale, fetch fresh data from API
    3. Update cache with new data
    4. Save cache to disk
    5. Notify sensors of updates

    The coordinator uses:
    - ContactEnergyAccountApi: For fetching data from API
    - AccountDataManager: For caching and staleness logic

    Attributes:
        hass: Home Assistant instance
        api: Account API client
        data_manager: Account data manager
        account_id: Account ID (BA number)
        icp: ICP number
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api: ContactEnergyAccountApi,
        address: str,
        icp: str,
        account_id: str | None = None,
    ):
        """Initialize account coordinator.

        Args:
            hass: Home Assistant instance
            api: Account API client
            address: Sanitized address for cache naming
            icp: ICP number
            account_id: Account ID (BA number), optional
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_account",
            update_interval=ACCOUNT_UPDATE_INTERVAL,
        )

        self.api = api
        self.account_id = account_id
        self.address = address
        self.icp = icp

        # Initialize data manager
        self.data_manager = AccountDataManager(address, icp)

        _LOGGER.debug(
            "AccountCoordinator initialized for %s_%s",
            address,
            icp
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch account data from API if stale.

        Returns:
            Dictionary containing account data

        Raises:
            UpdateFailed: If API request fails
        """
        # Load existing cache
        await self.data_manager.load()

        # Check if data is stale
        if not self.data_manager.is_stale():
            _LOGGER.debug("Account data is fresh, using cache")
            cached_data = self.data_manager.get_account_data()
            if cached_data:
                return cached_data

        # Data is stale or missing, fetch from API
        try:
            _LOGGER.info("Fetching account data from API (stale or missing)")
            account_data = await self.api.get_accounts()

            # Update cache
            self.data_manager.update(account_data)

            # Prune old data (no-op for account data)
            self.data_manager.prune()

            # Save cache
            await self.data_manager.save()

            _LOGGER.info("Account data updated successfully")
            return account_data

        except Exception as err:
            _LOGGER.error("Failed to fetch account data: %s", err)
            
            # Try to return cached data even if stale
            cached_data = self.data_manager.get_account_data()
            if cached_data:
                _LOGGER.warning("API fetch failed, returning stale cache")
                return cached_data
            
            raise UpdateFailed(f"Failed to fetch account data: {err}") from err

    async def force_refresh(self) -> None:
        """Force a refresh of account data regardless of staleness."""
        try:
            _LOGGER.info("Forcing account data refresh")
            account_data = await self.api.get_accounts()

            # Update cache
            self.data_manager.update(account_data)

            # Save cache
            await self.data_manager.save()

            # Update coordinator data
            self.async_set_updated_data(account_data)

            _LOGGER.info("Forced account data refresh successful")

        except Exception as err:
            _LOGGER.error("Forced refresh failed: %s", err)
            raise UpdateFailed(f"Forced refresh failed: {err}") from err

    def get_balance(self) -> dict[str, Any] | None:
        """Get account balance data from cache.

        Returns:
            Balance data dictionary, or None if not available
        """
        return self.data_manager.get_balance()

    def get_invoice(self) -> dict[str, Any] | None:
        """Get invoice data from cache.

        Returns:
            Invoice data dictionary, or None if not available
        """
        return self.data_manager.get_invoice()

    def get_next_bill(self) -> dict[str, Any] | None:
        """Get next bill data from cache.

        Returns:
            Next bill data dictionary, or None if not available
        """
        return self.data_manager.get_next_bill()

    def get_contracts(self) -> list[dict[str, Any]]:
        """Get contracts data from cache.

        Returns:
            List of contract dictionaries
        """
        return self.data_manager.get_contracts()
