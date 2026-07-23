"""Account data coordinator for Contact Energy integration.

=== WHAT THIS DOES ===
This module contains the ``AccountCoordinator`` class. A coordinator is a
Home Assistant helper whose job is to fetch shared data once and then hand
that same fresh result to multiple sensors. In this file, the shared data is
Contact Energy account information such as balance details, invoice details,
next bill information, and contract details.

The coordinator follows a simple cycle:
1. Load any saved account data from the local cache.
2. Check whether that saved data is still fresh enough to reuse.
3. If the data is old or missing, ask the Contact Energy API for new data.
4. Save the new result back to the cache on disk.
5. Tell Home Assistant entities that fresh account data is available.

=== FOR NON-CODERS ===
Think of a coordinator like a receptionist in an office.
- Instead of every employee calling the power company separately,
  the receptionist makes one call.
- The receptionist writes down the answer.
- Everyone else reads from that one shared note.

That saves time, avoids duplicated work, and reduces unnecessary traffic to
the Contact Energy servers.

Helpful terms:
- "Coordinator": the shared organiser that fetches and distributes data.
- "Polling": checking again on a timer to see if anything changed.
- "Update interval": how often that timer is allowed to run.
- "Data refresh": replacing old stored information with newer information.

Version: 2.0.0
"""

# This future import lets the file use modern type-hint syntax cleanly.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: records progress, warnings, and errors for troubleshooting.
import logging

# timedelta: represents "wait this long before the next allowed update".
from datetime import timedelta

# Any: used in type hints when the returned dictionary can contain mixed values.
from typing import Any

# HomeAssistant: the main Home Assistant object passed into integrations.
from homeassistant.core import HomeAssistant

# DataUpdateCoordinator: Home Assistant's shared polling helper.
# UpdateFailed: the standard error type used when a refresh cannot complete.
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# ContactEnergyAccountApi: the API helper responsible for fetching live account data.
from ..api.account import ContactEnergyAccountApi

# AccountDataManager: handles cached account data on disk and stale-data checks.
from ..data_managers.account_data import AccountDataManager

# DOMAIN: the integration's unique Home Assistant identifier.
from ..const import DOMAIN

# ============================================================================
# LOGGER AND CONFIGURATION
# ============================================================================

# Create a module-specific logger so messages from this file are easy to find.
_LOGGER = logging.getLogger(__name__)

# This is the maximum amount of time we allow account data to age before a
# scheduled refresh is permitted to fetch newer data.
ACCOUNT_UPDATE_INTERVAL = timedelta(hours=6)


# ============================================================================
# ACCOUNT COORDINATOR
# ============================================================================

class AccountCoordinator(DataUpdateCoordinator):
    """Coordinator for Contact Energy account data.

    === WHAT THIS DOES ===
    This class centralises account-data fetching for the integration. It asks
    the data manager whether cached data is still usable. If the cache is too
    old, it fetches fresh account information from Contact Energy, updates the
    cache, and lets Home Assistant know the shared data changed.

    === FOR NON-CODERS ===
    Imagine a noticeboard in a building lobby.
    - The noticeboard stores the latest account information.
    - If the note is still recent, everyone reads the existing note.
    - If the note is old, the coordinator replaces it with a fresh note.

    This design exists so multiple sensors can share one trusted source of
    truth instead of each sensor making its own internet request.
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

        === WHAT THIS DOES ===
        This constructor stores the objects and identifiers the coordinator
        needs for future refreshes, then prepares a matching cache manager.

        === FOR NON-CODERS ===
        This is the setup step. It gives the coordinator:
        - the Home Assistant system it belongs to,
        - the Contact Energy API helper it should call,
        - the property/address identifiers used for cache naming, and
        - an optional account number.

        Why this exists:
        The coordinator needs all of these pieces ready before the first
        refresh happens so later updates can run automatically on schedule.
        """
        # ====================================================================
        # STEP 1: Register this object as a Home Assistant data coordinator.
        # ====================================================================
        # DataUpdateCoordinator handles the shared refresh pattern for us.
        # The update interval means Home Assistant may ask this object to poll
        # for fresh account data roughly every 6 hours.
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_account",
            update_interval=ACCOUNT_UPDATE_INTERVAL,
        )

        # ====================================================================
        # STEP 2: Store the live API client and identifiers we will reuse.
        # ====================================================================
        # self.api is the object that knows how to talk to Contact Energy.
        self.api = api

        # self.account_id stores the optional BA/account number if one is known.
        self.account_id = account_id

        # self.address is a cleaned-up version of the address for cache naming.
        self.address = address

        # self.icp identifies the installation point for this property.
        self.icp = icp

        # ====================================================================
        # STEP 3: Create the cache manager for account data.
        # ====================================================================
        # The data manager hides the file-storage details and also knows how to
        # decide whether saved data is stale.
        self.data_manager = AccountDataManager(address, icp)

        # Record that setup completed so debugging later is easier.
        _LOGGER.debug(
            "AccountCoordinator initialized for %s_%s",
            address,
            icp,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch account data from cache or API.

        === WHAT THIS DOES ===
        This is the coordinator's main refresh method. Home Assistant calls it
        whenever the shared account data should be checked. The method first
        loads saved cache data, then decides whether that cached data is still
        fresh enough to keep using. If not, it fetches live data from the API.

        === FOR NON-CODERS ===
        Think of this as:
        1. Open the filing cabinet.
        2. Check the date on the document.
        3. If the document is still recent, reuse it.
        4. If the document is old, phone Contact Energy for a new copy.
        5. If the phone call fails, fall back to the old copy if one exists.

        Why this exists:
        It balances reliability and efficiency. It avoids unnecessary network
        calls while still keeping the displayed account information current.

        Returns:
            The account data dictionary that sensors should read from.

        Raises:
            UpdateFailed: Raised only when no live data and no fallback cache
                are available.
        """
        # ====================================================================
        # STEP 1: Load any previously saved account data from disk.
        # ====================================================================
        # This makes sure the data manager is working with the latest cached
        # state before we decide whether an internet request is necessary.
        await self.data_manager.load()

        # ====================================================================
        # STEP 2: Reuse cached data when it is still fresh.
        # ====================================================================
        # "Stale" means old enough that we should refresh it. If the cache is
        # not stale, reusing it is faster and avoids an unnecessary API call.
        if not self.data_manager.is_stale():
            _LOGGER.debug("Account data is fresh, using cache")

            # Read the cached account payload from the data manager.
            cached_data = self.data_manager.get_account_data()

            # Only return the cached payload if it actually contains data.
            if cached_data:
                return cached_data

        # ====================================================================
        # STEP 3: Fetch live data because the cache is stale or empty.
        # ====================================================================
        try:
            # Log that we are moving from cached data to a live API request.
            _LOGGER.info("Fetching account data from API (stale or missing)")

            # Ask the Contact Energy API helper for the latest account payload.
            account_data = await self.api.get_accounts()

            # Store the newly downloaded data in memory inside the manager.
            self.data_manager.update(account_data)

            # Run the manager's prune step. For account data this is currently
            # a no-op, but calling it keeps the workflow consistent.
            self.data_manager.prune()

            # Persist the refreshed data to disk so it survives restarts.
            await self.data_manager.save()

            # Announce success and hand the fresh payload back to the caller.
            _LOGGER.info("Account data updated successfully")
            return account_data

        except Exception as err:
            # =================================================================
            # STEP 4: Handle failures gracefully.
            # =================================================================
            # We log the failure first so the reason is visible in diagnostics.
            _LOGGER.error("Failed to fetch account data: %s", err)

            # Try to rescue the situation by returning old cache data anyway.
            cached_data = self.data_manager.get_account_data()
            if cached_data:
                _LOGGER.warning("API fetch failed, returning stale cache")
                return cached_data

            # If there is no live data and no cached fallback, tell Home
            # Assistant the coordinator update genuinely failed.
            raise UpdateFailed(f"Failed to fetch account data: {err}") from err

    async def force_refresh(self) -> None:
        """Force a refresh even if the cache looks fresh.

        === WHAT THIS DOES ===
        This method bypasses the normal stale-data check and immediately asks
        Contact Energy for live account data.

        === FOR NON-CODERS ===
        Normally the coordinator waits until the saved data looks old before it
        refreshes. This method is the "refresh right now" button.

        Why this exists:
        Some service calls or manual refresh actions need the newest possible
        data immediately, even if the normal timer would have waited longer.
        """
        try:
            # Tell the logs that this refresh was manually forced.
            _LOGGER.info("Forcing account data refresh")

            # Fetch a brand-new account payload directly from the API.
            account_data = await self.api.get_accounts()

            # Update the in-memory cache representation with the fresh payload.
            self.data_manager.update(account_data)

            # Save that fresh payload to disk for future restarts.
            await self.data_manager.save()

            # Push the new data into Home Assistant immediately so listeners do
            # not have to wait for the next scheduled poll.
            self.async_set_updated_data(account_data)

            # Log the successful completion of the manual refresh.
            _LOGGER.info("Forced account data refresh successful")

        except Exception as err:
            # Convert any problem into Home Assistant's expected failure type.
            _LOGGER.error("Forced refresh failed: %s", err)
            raise UpdateFailed(f"Forced refresh failed: {err}") from err

    def get_balance(self) -> dict[str, Any] | None:
        """Return cached balance information.

        === WHAT THIS DOES ===
        This helper pulls just the balance portion out of the cached account
        payload.

        === FOR NON-CODERS ===
        Instead of handing back the whole account document, this method picks
        out only the balance section that balance-related sensors care about.
        """
        # Ask the data manager for the balance-only subsection and return it.
        return self.data_manager.get_balance()

    def get_invoice(self) -> dict[str, Any] | None:
        """Return cached invoice information.

        === WHAT THIS DOES ===
        This helper extracts invoice details from the cached account payload.

        === FOR NON-CODERS ===
        Think of this as opening the account folder and handing someone only
        the invoice page instead of the whole stack of paperwork.
        """
        # Return the cached invoice subsection for invoice-related entities.
        return self.data_manager.get_invoice()

    def get_next_bill(self) -> dict[str, Any] | None:
        """Return cached next-bill information.

        === WHAT THIS DOES ===
        This helper extracts the cached prediction or summary for the next bill.

        === FOR NON-CODERS ===
        It answers the question, "What does the integration currently know
        about the next bill?" without exposing unrelated account details.
        """
        # Return the next-bill subsection exactly as stored in the cache.
        return self.data_manager.get_next_bill()

    def get_contracts(self) -> list[dict[str, Any]]:
        """Return cached contract information.

        === WHAT THIS DOES ===
        This helper returns the list of contracts from the saved account data.

        === FOR NON-CODERS ===
        A contract here means a service agreement for the property. This method
        provides that list directly to anything that only needs contract data.
        """
        # Return the list of cached contracts, or an empty list if none exist.
        return self.data_manager.get_contracts()
