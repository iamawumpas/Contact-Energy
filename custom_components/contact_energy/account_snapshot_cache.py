"""Persistent account snapshot cache for Contact Energy integration.

=== WHAT THIS DOES ===
This legacy module saves the last successful account API payload to disk and can
load it back later. It gives the integration a fallback copy of account details
when Home Assistant restarts or when Contact Energy's API is temporarily failing.

=== FOR NON-CODERS ===
Think of this file as an emergency photocopy machine for account data.
When a fresh API response arrives, it stores a copy in a local file. If the live
service is unavailable later, the integration can reopen that saved copy instead
of showing nothing.

Helpful simple terms:
- Snapshot: A saved copy of data taken at one moment in time.
- Cache: A local saved copy kept for reuse.
- Atomic save: Write a new file first, then swap it into place so partial writes
  are less likely to leave a broken file behind.

=== LEGACY / COMPATIBILITY NOTE ===
This is a legacy/deprecated file. It remains for backward compatibility and as a
teaching resource documenting the older account-snapshot persistence approach.
"""

# This import keeps modern type hints working consistently across Python versions.
from __future__ import annotations

# ============================================================================
# IMPORTS - Every dependency explained in plain language
# ============================================================================

# asyncio provides asynchronous locks and background-thread helpers.
import asyncio

# json converts account payload dictionaries into JSON text and back again.
import json

# logging records what happened during load/save operations.
import logging

# datetime and timezone create timestamp metadata for saved snapshots.
from datetime import datetime, timezone

# Path provides safer file and folder path handling.
from pathlib import Path

# Any and Optional describe flexible and possibly-missing values in type hints.
from typing import Any, Optional

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Module logger for this legacy snapshot cache helper.
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# LEGACY SNAPSHOT CACHE CLASS
# ============================================================================

class AccountSnapshotCache:
    """Persist and load the last-known account API payload per contract.

    === WHAT THIS DOES ===
    This class stores one JSON snapshot file per contract and can later read that
    file back into memory.

    === WHY IT STILL EXISTS ===
    This is legacy/deprecated code, but older compatibility paths still rely on
    this exact snapshot behaviour. The detailed comments also make it a useful
    teaching example of a small file-backed cache.

    === FOR NON-CODERS ===
    Think of this class as a safe-deposit clerk for one account snapshot file.
    It knows where the file should live and how to open or replace it safely.
    """

    # Shared per-contract locks stop two concurrent saves from colliding.
    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, contract_id: str, cache_dir: Optional[Path] = None) -> None:
        """Initialize snapshot caching for one contract.

        === WHAT THIS DOES ===
        This constructor decides where the snapshot file should live and attaches
        a shared async lock for safe saving.

        === WHY IT EXISTS ===
        Each contract needs its own filename and locking scope, even in this small
        legacy helper.

        === STEP-BY-STEP ===
        1. Save the contract ID.
        2. Choose the cache directory.
        3. Build the final JSON file path.
        4. Reuse or create the per-contract save lock.
        """
        # Store the contract ID for file naming and logging.
        self.contract_id = contract_id

        # Decide which directory will hold snapshot files.
        if cache_dir is None:
            # Default to the integration's built-in data folder.
            component_dir = Path(__file__).parent
            self.cache_dir = component_dir / "data"
        else:
            # Allow callers such as tests to override the storage location.
            self.cache_dir = Path(cache_dir)

        # Build the final snapshot filename for this contract.
        self.cache_path = self.cache_dir / f"account_snapshot_{contract_id}.json"

        # Ensure all instances for the same contract share one save lock.
        if contract_id not in AccountSnapshotCache._locks:
            AccountSnapshotCache._locks[contract_id] = asyncio.Lock()
        self._lock = AccountSnapshotCache._locks[contract_id]

    async def load(self) -> Optional[dict[str, Any]]:
        """Load a saved account snapshot from disk.

        === WHAT THIS DOES ===
        This method opens the snapshot file, reads JSON, and returns the saved
        account_data section when it is valid.

        === WHY IT EXISTS ===
        Legacy account sensors use this as a fallback whenever a fresh API payload
        is not immediately available.

        === STEP-BY-STEP ===
        1. Check whether the snapshot file exists.
        2. If not, return None.
        3. Read the JSON in a background thread.
        4. Pull out the account_data section.
        5. Return it only if it is a dictionary.
        6. Log and return None on any failure.
        """
        # If there is no snapshot file yet, there is nothing to load.
        if not self.cache_path.exists():
            return None

        # This nested helper performs the blocking file read.
        def _read() -> dict[str, Any]:
            # Open the saved JSON snapshot file using UTF-8 text encoding.
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                # Convert JSON text into a Python dictionary.
                return json.load(handle)

        try:
            # Ask asyncio for the current event loop.
            loop = asyncio.get_event_loop()

            # Run the blocking file read in a worker thread.
            payload = await loop.run_in_executor(None, _read)

            # Extract the actual account payload from the wrapper structure.
            account_data = payload.get("account_data")

            # Return the payload only if it has the expected dictionary shape.
            if isinstance(account_data, dict):
                return account_data

            # Any other shape is treated as invalid or unusable.
            return None
        except Exception as err:
            # Log failures and fall back to None so callers can continue gracefully.
            _LOGGER.warning(
                "Failed loading account snapshot for contract %s: %s",
                self.contract_id,
                err,
            )
            return None

    async def save(self, account_data: dict[str, Any]) -> None:
        """Persist the latest account payload while holding the shared save lock.

        === WHAT THIS DOES ===
        This public method ensures only one save per contract runs at a time.

        === WHY IT EXISTS ===
        Even a small legacy cache can be corrupted if two writers overlap. The
        lock keeps the file writes orderly.

        === STEP-BY-STEP ===
        1. Acquire the per-contract lock.
        2. Delegate to the real save helper.
        3. Release the lock automatically afterward.
        """
        # Hold the shared lock so concurrent callers cannot write together.
        async with self._lock:
            await self._save_locked(account_data)

    async def _save_locked(self, account_data: dict[str, Any]) -> None:
        """Write the snapshot file while the caller already holds the lock.

        === WHAT THIS DOES ===
        This helper creates the directory, wraps the payload with metadata, writes
        a temporary file, and atomically replaces the final file.

        === WHY IT EXISTS ===
        Keeping the low-level file-write steps in a dedicated helper makes the
        public save method easier to read.

        === STEP-BY-STEP ===
        1. Ensure the cache directory exists.
        2. Build the JSON payload wrapper.
        3. Pick a temporary filename in the same folder.
        4. Write the JSON to the temporary file.
        5. Replace the final snapshot file atomically.
        """
        # Make sure the target directory exists before attempting to write a file.
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Build the wrapped payload containing metadata plus the actual account data.
        payload = {
            "contract_id": self.contract_id,
            "metadata": {
                "version": "1.0.0",
                "updated": datetime.now(timezone.utc).isoformat(),
            },
            "account_data": account_data,
        }

        # Build a temporary filename in the same directory for safe replacement.
        temp_path = self.cache_path.with_suffix(".tmp")

        # This nested helper performs the blocking write operation.
        def _write() -> None:
            # Write the new snapshot contents to the temporary file first.
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)

            # Atomically swap the temporary file into the final file location.
            temp_path.replace(self.cache_path)

        # Ask asyncio for the current event loop.
        loop = asyncio.get_event_loop()

        # Run the blocking file-write step in a worker thread.
        await loop.run_in_executor(None, _write)
