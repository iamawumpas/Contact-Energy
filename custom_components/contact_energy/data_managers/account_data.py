"""Account data manager for Contact Energy.

=== WHAT THIS DOES ===
This module manages cached account-level information such as account balance,
invoice details, contract information, payment settings, and other account
fields returned by the Contact Energy API.

It decides:
- what the account cache file should be called
- what an empty account cache looks like
- when account data is considered too old
- how newly downloaded account data should be stored
- how specific sections like balance or invoice can be retrieved later

=== FOR NON-CODERS ===
This file is like the office clerk responsible for a customer's account folder.
The clerk keeps a saved copy of account information so the system can read it
quickly later without repeatedly asking Contact Energy for the same details.

A "cache" is that saved copy.
A "JSON" file is the text-based storage format used for that saved copy.

Version: 2.0.0
"""

# This line enables modern type hints without forcing runtime evaluation.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: Used to write helpful debug/info messages about cache behavior.
import logging

# datetime/timezone: Used to create accurate UTC timestamps for metadata.
from datetime import datetime, timezone

# Any: Type-hint helper used because API data may contain many different shapes
# and nested values.
from typing import Any

# BaseCache: The shared parent class that provides loading, saving, metadata,
# and file-lock behavior used by all cache managers.
from .base_cache import BaseCache

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Create a logger dedicated to this module.
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# STALENESS CONFIGURATION
# ============================================================================

# Account data is refreshed if it is six or more hours old.
# This data changes sometimes, but usually not minute-by-minute.
ACCOUNT_STALENESS_HOURS = 6


# ============================================================================
# ACCOUNT DATA MANAGER CLASS
# ============================================================================

class AccountDataManager(BaseCache):
    """Manager for account data caching.

    === WHAT THIS DOES ===
    This class stores and retrieves the account-wide data payload returned by
    Contact Energy. Unlike usage history, account data behaves more like a
    single snapshot of the current account state.

    === FOR NON-CODERS ===
    Think of this class as the person who maintains the "account summary" file.
    Instead of storing one row per hour or day, it mainly stores one big bundle
    of account facts: balance, invoice, contracts, and settings.
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: {address}_{icp}.json.

        === WHAT THIS DOES ===
        Builds the filename used to store account cache data on disk.

        === FOR NON-CODERS ===
        Filenames are labels on folders. This label uses the address and ICP so
        the system knows which account the file belongs to.

        Returns:
            The filename for this account cache.
        """
        # Build a less-obvious filename containing the address and ICP.
        return f"{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty account cache structure.

        === WHAT THIS DOES ===
        Returns the starter data structure for account caching.

        === FOR NON-CODERS ===
        This creates a blank folder with labeled sections ready to be filled in.
        The metadata section tracks information about the cache itself, while the
        account_data section will later hold the actual account information.

        Returns:
            A dictionary containing empty metadata and no account data yet.
        """
        # Return a fresh dictionary that contains:
        # 1. metadata about the cache file itself
        # 2. a placeholder for the real account payload
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

        === WHAT THIS DOES ===
        Decides whether the saved account snapshot is too old to trust.

        === FOR NON-CODERS ===
        "Stale" means the saved copy may no longer match the latest data from
        Contact Energy. If data is stale, the integration should fetch a fresh
        copy instead of relying on the old one.

        Returns:
            True when account data should be refreshed, otherwise False.
        """
        # ====================================================================
        # RULE 1: IF THERE IS NO ACCOUNT DATA, IT IS DEFINITELY STALE
        # ====================================================================
        if not self.data.get("account_data"):
            _LOGGER.debug("Account data is stale: no data")
            return True

        # ====================================================================
        # RULE 2: CHECK HOW MANY HOURS HAVE PASSED SINCE THE LAST DOWNLOAD
        # ====================================================================
        hours_old = self.hours_since_last_download()

        # If the saved copy is at or beyond the staleness limit, refresh it.
        if hours_old >= ACCOUNT_STALENESS_HOURS:
            _LOGGER.debug(
                "Account data is stale: %.1f hours old (limit: %d)",
                hours_old,
                ACCOUNT_STALENESS_HOURS,
            )
            return True

        # If neither stale rule triggered, the cache is still fresh enough.
        _LOGGER.debug("Account data is fresh: %.1f hours old", hours_old)
        return False

    def prune(self) -> None:
        """Prune old data.

        === WHAT THIS DOES ===
        Satisfies the shared cache interface, but intentionally does nothing.

        === FOR NON-CODERS ===
        Account data is a current snapshot, not a long timeline of records.
        Because old account snapshots are not stored side-by-side here, there is
        nothing to trim away.
        """
        # No action is needed because this cache stores one current account
        # snapshot instead of an ever-growing history list.
        pass

    def update(self, account_data: dict[str, Any]) -> None:
        """Update cache with new account data.

        === WHAT THIS DOES ===
        Replaces the currently cached account payload with the newest API data
        and updates metadata timestamps.

        === FOR NON-CODERS ===
        When a fresh account response arrives from Contact Energy, this method
        places that new paperwork into the account folder and updates the note
        saying when the folder was last refreshed.

        Args:
            account_data: Raw account data returned from the API.
        """
        # ====================================================================
        # STEP 1: STORE THE NEW ACCOUNT PAYLOAD
        # ====================================================================
        # This replaces the previous snapshot with the newest full snapshot.
        self.data["account_data"] = account_data

        # ====================================================================
        # STEP 2: MAKE SURE A METADATA SECTION EXISTS
        # ====================================================================
        if "metadata" not in self.data:
            # If metadata was missing for any reason, rebuild the default
            # metadata structure from a fresh empty cache template.
            self.data["metadata"] = self._create_empty_cache()["metadata"]

        # ====================================================================
        # STEP 3: RECORD WHEN THIS CACHE WAS UPDATED
        # ====================================================================
        # Store the current UTC time as the last successful refresh time.
        self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()

        # ====================================================================
        # STEP 4: STORE AN API TIMESTAMP PLACEHOLDER
        # ====================================================================
        # This currently uses "now" because the API response does not appear to
        # provide a dedicated source timestamp here.
        self.data["metadata"]["last_api_timestamp"] = datetime.now(timezone.utc).isoformat()

        # Record the update for debugging and operational visibility.
        _LOGGER.info("Updated account data cache for %s_%s", self.address, self.icp)

    def get_account_data(self) -> dict[str, Any] | None:
        """Get cached account data.

        === WHAT THIS DOES ===
        Returns the full saved account payload.

        === FOR NON-CODERS ===
        This is the simplest way to ask, "Give me the whole account folder."

        Returns:
            The cached account data dictionary, or None if empty.
        """
        # Safely return the stored account payload if it exists.
        return self.data.get("account_data")

    def get_balance(self) -> dict[str, Any] | None:
        """Get account balance data.

        === WHAT THIS DOES ===
        Extracts just the balance section from the larger account payload.

        === FOR NON-CODERS ===
        Instead of handing back the whole account folder, this method pulls out
        only the balance page.

        Returns:
            The account balance section, or None if unavailable.
        """
        # Start by retrieving the full account payload.
        account_data = self.get_account_data()

        # If there is no payload at all, there can be no balance section.
        if not account_data:
            return None

        # accountDetail is the nested section where several key account fields
        # live. Use an empty dictionary as a safe fallback.
        account_detail = account_data.get("accountDetail", {})

        # Return the balance subsection if present.
        return account_detail.get("accountBalance")

    def get_invoice(self) -> dict[str, Any] | None:
        """Get invoice data.

        === WHAT THIS DOES ===
        Extracts the invoice section from the cached account payload.

        === FOR NON-CODERS ===
        This is like opening the account folder directly to the invoice page.

        Returns:
            The invoice section, or None if unavailable.
        """
        # Retrieve the full account payload first.
        account_data = self.get_account_data()

        # If nothing is cached, we cannot return invoice information.
        if not account_data:
            return None

        # Safely access the nested detail section.
        account_detail = account_data.get("accountDetail", {})

        # Return the invoice subsection from that nested detail data.
        return account_detail.get("invoice")

    def get_next_bill(self) -> dict[str, Any] | None:
        """Get next bill data.

        === WHAT THIS DOES ===
        Extracts the predicted/next bill information from account data.

        === FOR NON-CODERS ===
        This is the method for asking, "What does the system say the next bill
        will be?"

        Returns:
            The next bill section, or None if unavailable.
        """
        # Retrieve the full cached account data snapshot.
        account_data = self.get_account_data()

        # Stop early if no account data has been cached yet.
        if not account_data:
            return None

        # Access the nested account detail block safely.
        account_detail = account_data.get("accountDetail", {})

        # Return the next bill subsection if it exists.
        return account_detail.get("nextBill")

    def get_contracts(self) -> list[dict[str, Any]]:
        """Get contracts data.

        === WHAT THIS DOES ===
        Extracts the list of contracts from the cached account payload.

        === FOR NON-CODERS ===
        Contracts are the service agreements attached to the account. This
        method returns that list while safely falling back to an empty list when
        no contracts are available.

        Returns:
            A list of contracts, or an empty list if unavailable.
        """
        # Load the full account payload first.
        account_data = self.get_account_data()

        # If there is no account data, return an empty list instead of None so
        # callers can still safely loop over the result.
        if not account_data:
            return []

        # Safely access the nested account detail section.
        account_detail = account_data.get("accountDetail", {})

        # Return the contract list if present, otherwise return an empty list.
        return account_detail.get("contracts", [])
