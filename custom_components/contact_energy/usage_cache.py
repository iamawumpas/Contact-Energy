"""Usage data cache management for Contact Energy integration.

=== WHAT THIS DOES ===
This legacy module stores Contact Energy usage history on disk in JSON files.
It knows how to:
- Create an empty cache structure for a contract.
- Load saved hourly, daily, and monthly usage data.
- Save updates safely using atomic file replacement.
- Prune old records so cache files do not grow forever.
- Track metadata such as last sync time and cumulative totals.

=== FOR NON-CODERS ===
Think of this file as an old filing cabinet manager.
- The cabinet is a JSON file on disk.
- Each contract gets its own drawer.
- The manager can open the drawer, add new papers, discard very old papers,
  and note when the drawer was last updated.

Helpful plain-language ideas:
- Cache: A saved local copy of data so the app can reuse it later.
- Atomic save: A safer write method where a new file is written first and then
  swapped into place, reducing the chance of a half-written broken file.
- Metadata: Extra notes about the data, such as when it was updated.
- Pruning: Removing older data that is no longer needed.

=== LEGACY / COMPATIBILITY NOTE ===
This is a legacy/deprecated file. It is retained for backward compatibility and
as a teaching resource so maintainers can understand the older disk-cache design
that predates newer abstractions.

Cache files are stored in: custom_components/contact_energy/data/
File naming: usage_cache_{contract_id}.json

Version: 1.4.0
Author: Contact Energy Integration
"""

# This import allows modern type-hint syntax to work consistently.
from __future__ import annotations

# ============================================================================
# IMPORTS - Every dependency is described for non-coders
# ============================================================================

# asyncio provides asynchronous locks and background execution helpers.
import asyncio

# json converts Python dictionaries to and from JSON text files.
import json

# logging records what happens so support and developers can investigate issues.
import logging

# time measures how long load/save operations take.
import time

# These date/time helpers support pruning windows and metadata timestamps.
from datetime import datetime, date, timedelta, timezone

# Path makes file and folder paths easier and safer to manipulate.
from pathlib import Path

# Any and Optional describe flexible or possibly-missing values in type hints.
from typing import Any, Optional

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Module-level logger for this legacy cache manager.
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# LEGACY USAGE CACHE CLASS
# ============================================================================

class UsageCache:
    """Manage persistent usage-data storage for one Contact Energy contract.

    === WHAT THIS DOES ===
    This class owns one cache file per contract and provides helper methods for
    reading, updating, pruning, and saving that file.

    === WHY IT STILL EXISTS ===
    This is legacy/deprecated code, but existing integration flows still depend on
    this file-based cache shape. The detailed comments also make it useful as a
    historical teaching example.

    === FOR NON-CODERS ===
    You can think of an instance of this class as a dedicated records clerk for a
    single contract. The clerk knows where the file lives, what sections belong in
    it, and how to safely update it without damaging existing records.
    """

    # This class-level dictionary stores one async lock per contract ID.
    # A lock is like a "do not disturb" sign that stops two saves happening at once.
    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, contract_id: str, cache_dir: Optional[Path] = None):
        """Initialize cache management for a specific contract.

        === WHAT THIS DOES ===
        This constructor decides where the cache file lives, creates the initial
        in-memory data structure, and attaches a shared save lock.

        === WHY IT EXISTS ===
        Each contract needs a separate cache location and separate data store, even
        in the older architecture.

        === STEP-BY-STEP ===
        1. Save the contract ID.
        2. Decide which folder should hold the cache file.
        3. Build the full file path.
        4. Create an empty in-memory cache structure.
        5. Reuse or create a shared lock for this contract.
        """
        # Save the contract identifier for later file naming and logging.
        self.contract_id = contract_id

        # Decide where cache files should live.
        if cache_dir is None:
            # Default to the integration's built-in data folder.
            component_dir = Path(__file__).parent
            self.cache_dir = component_dir / "data"
        else:
            # Allow tests or special callers to override the cache directory.
            self.cache_dir = Path(cache_dir)

        # Build the full filename for this contract's JSON cache.
        self.cache_path = self.cache_dir / f"usage_cache_{contract_id}.json"

        # Start with a brand-new empty cache structure in memory.
        self.data: dict[str, Any] = self._create_empty_cache()

        # Ensure all instances for the same contract share one save lock.
        if contract_id not in UsageCache._locks:
            UsageCache._locks[contract_id] = asyncio.Lock()
        self._save_lock = UsageCache._locks[contract_id]

        # Log the initialized cache path for troubleshooting.
        _LOGGER.debug(
            "UsageCache initialized for contract %s: cache_path=%s",
            contract_id,
            self.cache_path,
        )

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create the initial empty cache structure.

        === WHAT THIS DOES ===
        This helper builds the complete default dictionary structure expected by
        the rest of the legacy cache code.

        === WHY IT EXISTS ===
        Starting from a consistent shape prevents many key-missing errors and keeps
        both new caches and repaired caches predictable.

        === STEP-BY-STEP ===
        1. Record the contract ID.
        2. Create metadata placeholders.
        3. Create empty hourly, daily, and monthly data buckets.
        4. Return the finished dictionary.
        """
        # Return a full default cache structure ready for immediate use.
        return {
            "contract_id": self.contract_id,
            "metadata": {
                # Version helps future code understand which cache format this is.
                "version": "1.4.0",

                # created records when this cache structure was first generated.
                "created": datetime.now(timezone.utc).isoformat(),

                # last_synced will be filled each time the cache is saved.
                "last_synced": None,

                # cumulative keeps running totals for pruned-away daily data.
                "cumulative": {
                    "paid_kwh": 0.0,
                    "free_kwh": 0.0,
                },

                # energy_sensor stores the date from which dashboard totals should count.
                "energy_sensor": {
                    "start_date": None,
                },

                # Each interval gets its own metadata about date range and last sync time.
                "hourly": {
                    "from": None,
                    "to": None,
                    "last_sync": None,
                    "record_count": 0,
                },
                "daily": {
                    "from": None,
                    "to": None,
                    "last_sync": None,
                    "record_count": 0,
                },
                "monthly": {
                    "from": None,
                    "to": None,
                    "last_sync": None,
                    "record_count": 0,
                },
            },

            # These three buckets hold the actual time-series usage records.
            "hourly": {},
            "daily": {},
            "monthly": {},
        }

    async def load(self) -> bool:
        """Load cache data from disk if a cache file exists.

        === WHAT THIS DOES ===
        This method reads the JSON cache file, validates its basic structure, and
        stores the result in memory.

        === WHY IT EXISTS ===
        Legacy sensors and coordinators need a local copy of earlier usage data so
        Home Assistant can survive restarts and temporary API outages.

        === STEP-BY-STEP ===
        1. Start a timer for logging.
        2. Check whether the cache file exists.
        3. If not, create a fresh empty cache and return False.
        4. If it exists, read the JSON in a background thread.
        5. Validate the basic shape of the loaded data.
        6. Ensure newer metadata sections exist.
        7. Log summary statistics and return True.
        8. If anything goes wrong, log it, reset to an empty cache, and return False.
        """
        # Start timing so logs can show how expensive the load was.
        start_time = time.time()

        # Log the file path we are about to inspect.
        _LOGGER.debug("Loading cache for contract %s from %s", self.contract_id, self.cache_path)

        # If the cache file does not exist yet, start cleanly with an empty structure.
        if not self.cache_path.exists():
            _LOGGER.info(
                "No existing cache found for contract %s at %s. Starting with empty cache.",
                self.contract_id,
                self.cache_path,
            )
            self.data = self._create_empty_cache()
            return False

        try:
            # This nested function performs the actual file read synchronously.
            def _read_cache() -> dict[str, Any]:
                # Open the JSON file using UTF-8 text encoding.
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    # Convert JSON text into a Python dictionary.
                    return json.load(f)

            # Ask asyncio for the current event loop.
            loop = asyncio.get_event_loop()

            # Run the blocking file read in a worker thread so the event loop stays responsive.
            self.data = await loop.run_in_executor(None, _read_cache)

            # Validate that the outermost loaded structure is a dictionary.
            if not isinstance(self.data, dict):
                raise ValueError("Cache file does not contain a dictionary")

            # Validate that the expected metadata section exists.
            if "metadata" not in self.data:
                raise ValueError("Cache file missing 'metadata' section")

            # Make sure newer cumulative metadata exists even in older cache files.
            self._ensure_cumulative_metadata()

            # Extract a few summary values for logging.
            metadata = self.data.get("metadata", {})
            last_synced = metadata.get("last_synced", "never")
            hourly_count = len(self.data.get("hourly", {}))
            daily_count = len(self.data.get("daily", {}))
            monthly_count = len(self.data.get("monthly", {}))

            # Calculate elapsed load time for diagnostics.
            elapsed = time.time() - start_time

            # Log the successful load summary.
            _LOGGER.info(
                "Loaded cache for contract %s: last_synced=%s, records=(hourly=%d, daily=%d, monthly=%d) in %.3f seconds",
                self.contract_id,
                last_synced,
                hourly_count,
                daily_count,
                monthly_count,
                elapsed,
            )

            # Report success so callers know an existing file was used.
            return True

        except json.JSONDecodeError as e:
            # If the JSON is corrupt, log it and reset to a clean empty cache.
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Corrupted cache file for contract %s at %s: %s. Creating new cache. (Loaded in %.3f seconds)",
                self.contract_id,
                self.cache_path,
                str(e),
                elapsed,
            )
            self.data = self._create_empty_cache()
            return False

        except (ValueError, KeyError) as e:
            # If required structure is missing, discard the bad file contents in memory.
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Invalid cache structure for contract %s: %s. Creating new cache. (Loaded in %.3f seconds)",
                self.contract_id,
                str(e),
                elapsed,
            )
            self.data = self._create_empty_cache()
            return False

        except Exception as e:
            # Any unexpected failure also falls back to a new empty cache.
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Unexpected error loading cache for contract %s: %s. Creating new cache. (Loaded in %.3f seconds)",
                self.contract_id,
                str(e),
                elapsed,
                exc_info=True,
            )
            self.data = self._create_empty_cache()
            return False

    async def save(self) -> None:
        """Save the current cache to disk using a shared lock.

        === WHAT THIS DOES ===
        This method guards the actual save so only one write per contract happens
        at a time.

        === WHY IT EXISTS ===
        Multiple parts of the legacy integration may try to save near the same
        moment. The lock prevents file corruption and race conditions.

        === STEP-BY-STEP ===
        1. Acquire the per-contract async lock.
        2. Call the real save implementation.
        3. Release the lock automatically when finished.
        """
        # Hold the contract-specific lock so only one save runs at once.
        async with self._save_lock:
            await self._do_save()

    async def _do_save(self) -> None:
        """Perform the actual disk save while the caller already holds the lock.

        === WHAT THIS DOES ===
        This helper updates metadata, writes to a temporary file, and atomically
        replaces the old cache file.

        === WHY IT EXISTS ===
        Splitting the real save logic into a helper keeps the lock-handling method
        small and makes the sequencing easier to understand.

        === STEP-BY-STEP ===
        1. Start a timer.
        2. Ensure the cache directory exists.
        3. Refresh metadata.
        4. Write JSON to a temporary file in a background thread.
        5. Replace the real cache file atomically.
        6. Log summary statistics.
        """
        # Start a timer for detailed save-performance logging.
        start_time = time.time()

        # Log the save target before we begin writing.
        _LOGGER.debug("Saving cache for contract %s to %s", self.contract_id, self.cache_path)

        try:
            # Make sure the parent directory exists before writing the file.
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Refresh record counts, ranges, and timestamps before persisting.
            self._update_metadata()

            # Build a temporary filename in the same folder for atomic replacement.
            temp_path = self.cache_path.with_suffix(".tmp")

            # This nested function performs the blocking file-write work.
            def _write_cache():
                # Write the complete cache data to the temporary JSON file.
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)

                # Replace the real cache file in one filesystem operation.
                temp_path.replace(self.cache_path)

            # Get the active event loop.
            loop = asyncio.get_event_loop()

            # Run the blocking write in a worker thread.
            await loop.run_in_executor(None, _write_cache)

            # Calculate total save duration.
            elapsed = time.time() - start_time

            # Count records for the save summary log line.
            hourly_count = len(self.data.get("hourly", {}))
            daily_count = len(self.data.get("daily", {}))
            monthly_count = len(self.data.get("monthly", {}))

            # Log a concise summary of what was saved.
            _LOGGER.info(
                "Saved cache for contract %s: records=(hourly=%d, daily=%d, monthly=%d) in %.3f seconds",
                self.contract_id,
                hourly_count,
                daily_count,
                monthly_count,
                elapsed,
            )

        except OSError as e:
            # File-system problems are logged and re-raised so callers know save failed.
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Failed to save cache for contract %s after %.3f seconds: %s",
                self.contract_id,
                elapsed,
                str(e),
                exc_info=True,
            )
            raise

        except Exception as e:
            # Unexpected failures are also logged and re-raised.
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Unexpected error saving cache for contract %s after %.3f seconds: %s",
                self.contract_id,
                elapsed,
                str(e),
                exc_info=True,
            )
            raise

    def _update_metadata(self) -> None:
        """Refresh metadata so it matches the current in-memory cache content.

        === WHAT THIS DOES ===
        This helper updates timestamps, record counts, and date ranges for all
        three usage intervals.

        === WHY IT EXISTS ===
        Metadata lets the rest of the integration quickly understand what the cache
        contains without scanning every record from scratch.

        === STEP-BY-STEP ===
        1. Grab the metadata dictionary.
        2. Ensure cumulative metadata exists.
        3. Stamp the current sync time.
        4. Recalculate hourly, daily, and monthly ranges and counts.
        5. Log the final summary.
        """
        # Grab the metadata section once for easier repeated updates.
        metadata = self.data["metadata"]

        # Ensure cumulative totals metadata exists, even in older cache shapes.
        cumulative = self._ensure_cumulative_metadata()

        # Record the latest overall sync time in UTC.
        metadata["last_synced"] = datetime.now(timezone.utc).isoformat()

        # ------------------------------
        # Update hourly metadata
        # ------------------------------
        hourly_records = self.data.get("hourly", {})
        if hourly_records:
            # Sort timestamp keys so the first is oldest and the last is newest.
            hourly_dates = sorted(hourly_records.keys())
            metadata["hourly"]["from"] = hourly_dates[0][:10]
            metadata["hourly"]["to"] = hourly_dates[-1][:10]
            metadata["hourly"]["record_count"] = len(hourly_records)
        else:
            # If no hourly data exists, clear the metadata placeholders.
            metadata["hourly"]["from"] = None
            metadata["hourly"]["to"] = None
            metadata["hourly"]["record_count"] = 0

        # ------------------------------
        # Update daily metadata
        # ------------------------------
        daily_records = self.data.get("daily", {})
        if daily_records:
            daily_dates = sorted(daily_records.keys())
            metadata["daily"]["from"] = daily_dates[0]
            metadata["daily"]["to"] = daily_dates[-1]
            metadata["daily"]["record_count"] = len(daily_records)
        else:
            metadata["daily"]["from"] = None
            metadata["daily"]["to"] = None
            metadata["daily"]["record_count"] = 0

        # ------------------------------
        # Update monthly metadata
        # ------------------------------
        monthly_records = self.data.get("monthly", {})
        if monthly_records:
            monthly_dates = sorted(monthly_records.keys())
            metadata["monthly"]["from"] = monthly_dates[0]
            metadata["monthly"]["to"] = monthly_dates[-1]
            metadata["monthly"]["record_count"] = len(monthly_records)
        else:
            metadata["monthly"]["from"] = None
            metadata["monthly"]["to"] = None
            metadata["monthly"]["record_count"] = 0

        # Log the refreshed metadata so maintainers can trace cache evolution.
        _LOGGER.debug(
            "Updated metadata for contract %s: hourly=(%s to %s, %d records), daily=(%s to %s, %d records), monthly=(%s to %s, %d records), cumulative_paid=%.3f, cumulative_free=%.3f",
            self.contract_id,
            metadata["hourly"]["from"],
            metadata["hourly"]["to"],
            metadata["hourly"]["record_count"],
            metadata["daily"]["from"],
            metadata["daily"]["to"],
            metadata["daily"]["record_count"],
            metadata["monthly"]["from"],
            metadata["monthly"]["to"],
            metadata["monthly"]["record_count"],
            cumulative.get("paid_kwh", 0.0),
            cumulative.get("free_kwh", 0.0),
        )

    def set_interval_last_sync(self, interval: str, sync_time: Optional[datetime] = None) -> None:
        """Record the last successful sync time for one interval.

        === WHAT THIS DOES ===
        This helper stores a timestamp for hourly, daily, or monthly sync activity.

        === WHY IT EXISTS ===
        Some parts of the integration need interval-specific freshness tracking,
        not just one overall cache timestamp.

        === STEP-BY-STEP ===
        1. Validate the interval name.
        2. Use the current UTC time if no explicit time was provided.
        3. Create missing metadata sections if necessary.
        4. Save the ISO timestamp string.
        """
        # Reject unknown interval names early to avoid corrupting metadata.
        if interval not in ("hourly", "daily", "monthly"):
            raise ValueError(f"Invalid interval '{interval}'")

        # If the caller did not provide a time, use the current UTC time.
        if sync_time is None:
            sync_time = datetime.now(timezone.utc)

        # Ensure the required metadata dictionaries exist.
        metadata = self.data.setdefault("metadata", {})
        interval_meta = metadata.setdefault(interval, {})

        # Store the timestamp in text form so it survives JSON serialization.
        interval_meta["last_sync"] = sync_time.isoformat()

    def get_interval_last_sync(self, interval: str) -> Optional[datetime]:
        """Return the last successful sync time for one interval.

        === WHAT THIS DOES ===
        This helper reads interval metadata and converts the stored timestamp back
        into a datetime object.

        === WHY IT EXISTS ===
        Callers need an easy way to decide whether hourly, daily, or monthly data
        is stale without manually parsing metadata strings.

        === STEP-BY-STEP ===
        1. Validate the interval name.
        2. Read the stored timestamp string.
        3. Return None if there is no stored timestamp.
        4. Parse and return the timestamp when possible.
        5. Return None if parsing fails.
        """
        # Unknown interval names simply return no timestamp.
        if interval not in ("hourly", "daily", "monthly"):
            return None

        # Read the nested metadata for the requested interval.
        interval_meta = self.data.get("metadata", {}).get(interval, {})
        last_sync_str = interval_meta.get("last_sync")

        # If nothing has been recorded yet, return None.
        if not last_sync_str:
            return None

        try:
            # Convert the stored ISO text back into a datetime object.
            return datetime.fromisoformat(last_sync_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            # If the timestamp text is invalid, treat it as unavailable.
            return None

    def update_hourly(self, records: list[dict[str, Any]]) -> int:
        """Add or replace hourly usage records in the in-memory cache.

        === WHAT THIS DOES ===
        Each hourly record is stored using its timestamp as the dictionary key.

        === WHY IT EXISTS ===
        Legacy callers fetch hourly data in batches and need a simple merge method
        that overwrites older copies of the same timestamp.

        === STEP-BY-STEP ===
        1. Log how many incoming records were supplied.
        2. Loop through each record.
        3. Read the timestamp key.
        4. Save the record if the timestamp exists.
        5. Warn and skip records missing a timestamp.
        6. Return the count of saved records.
        """
        # Log the batch size before merging records.
        _LOGGER.debug("Updating hourly cache for contract %s with %d records", self.contract_id, len(records))

        # Track how many valid records were actually stored.
        count = 0

        # Process each incoming record one by one.
        for record in records:
            # The timestamp string becomes the dictionary key for hourly data.
            timestamp = record.get("timestamp")
            if timestamp:
                # Save or replace the record under that timestamp.
                self.data["hourly"][timestamp] = record
                count += 1
            else:
                # Warn when a record cannot be stored because its key is missing.
                _LOGGER.warning("Hourly record missing timestamp for contract %s, skipping", self.contract_id)

        # Log the number of successful saves.
        _LOGGER.debug("Updated %d hourly records for contract %s", count, self.contract_id)

        # Return the number of saved records.
        return count

    def update_daily(self, records: list[dict[str, Any]]) -> int:
        """Add or replace daily usage records in the in-memory cache.

        === WHAT THIS DOES ===
        This method stores daily records using the YYYY-MM-DD date portion of each
        timestamp as the dictionary key.

        === WHY IT EXISTS ===
        Daily data is easier to query and merge when one date maps to one record.

        === STEP-BY-STEP ===
        1. Log the incoming batch size.
        2. Loop through the records.
        3. Extract the timestamp.
        4. Slice out the date portion.
        5. Save the record under that date key.
        6. Warn about malformed records.
        7. Return the saved count.
        """
        # Log the number of incoming daily records.
        _LOGGER.debug("Updating daily cache for contract %s with %d records", self.contract_id, len(records))

        # Track how many records are successfully merged.
        count = 0

        for record in records:
            # Read the timestamp field from the incoming record.
            timestamp = record.get("timestamp")
            if timestamp:
                # Daily keys use only the first 10 characters: YYYY-MM-DD.
                date_key = timestamp[:10]

                # Save or replace the record for that date.
                self.data["daily"][date_key] = record
                count += 1
            else:
                # Warn when a daily record cannot be keyed correctly.
                _LOGGER.warning("Daily record missing timestamp for contract %s, skipping", self.contract_id)

        # Log the merge result.
        _LOGGER.debug("Updated %d daily records for contract %s", count, self.contract_id)

        # Return how many records were written into the cache.
        return count

    def update_monthly(self, records: list[dict[str, Any]]) -> int:
        """Add or replace monthly usage records in the in-memory cache.

        === WHAT THIS DOES ===
        This method stores monthly records using the YYYY-MM month portion of the
        timestamp as the dictionary key.

        === WHY IT EXISTS ===
        Monthly charts and summaries naturally use one record per month, so month
        keys are the simplest stable shape for the legacy cache.

        === STEP-BY-STEP ===
        1. Log the incoming batch size.
        2. Loop through the records.
        3. Extract the timestamp.
        4. Slice out the year-month key.
        5. Save the record or warn if the key is missing.
        6. Return the saved count.
        """
        # Log the number of incoming monthly records.
        _LOGGER.debug("Updating monthly cache for contract %s with %d records", self.contract_id, len(records))

        # Track how many records were actually stored.
        count = 0

        for record in records:
            # Read the timestamp field from the incoming record.
            timestamp = record.get("timestamp")
            if timestamp:
                # Monthly keys use the first 7 characters: YYYY-MM.
                month_key = timestamp[:7]

                # Save or replace the month's record.
                self.data["monthly"][month_key] = record
                count += 1
            else:
                # Warn when a monthly record lacks the needed key field.
                _LOGGER.warning("Monthly record missing timestamp for contract %s, skipping", self.contract_id)

        # Log the merge result.
        _LOGGER.debug("Updated %d monthly records for contract %s", count, self.contract_id)

        # Return how many records were stored.
        return count

    def prune_hourly(self, window_days: int = 14) -> tuple[int, int]:
        """Discard hourly records older than the retention window.

        === WHAT THIS DOES ===
        This method keeps only recent hourly records and drops older ones.

        === WHY IT EXISTS ===
        Hourly data grows very quickly. Without pruning, cache files would become
        unnecessarily large and slower to load.

        === STEP-BY-STEP ===
        1. Count the current hourly records.
        2. Calculate the cutoff date.
        3. Rebuild the hourly dictionary using only recent timestamps.
        4. Count what remains.
        5. Log how much was removed.
        6. Return before/after counts.
        """
        # Count the number of hourly records before pruning.
        before_count = len(self.data.get("hourly", {}))

        # Work out the oldest date we still want to keep.
        cutoff_date = date.today() - timedelta(days=window_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        # Log the retention threshold being applied.
        _LOGGER.debug(
            "Pruning hourly data for contract %s: keeping records >= %s (window=%d days)",
            self.contract_id,
            cutoff_str,
            window_days,
        )

        # Rebuild the hourly dictionary with only records on or after the cutoff date.
        self.data["hourly"] = {
            timestamp: record
            for timestamp, record in self.data.get("hourly", {}).items()
            if timestamp[:10] >= cutoff_str
        }

        # Count how many records remain after pruning.
        after_count = len(self.data["hourly"])
        removed_count = before_count - after_count

        # Log whether any data was actually removed.
        if removed_count > 0:
            _LOGGER.info(
                "Pruned %d old hourly records for contract %s (kept %d records)",
                removed_count,
                self.contract_id,
                after_count,
            )
        else:
            _LOGGER.debug("No hourly records to prune for contract %s", self.contract_id)

        # Return a tuple so callers can inspect before/after totals.
        return (before_count, after_count)

    def prune_daily(self, window_days: int = 35) -> tuple[int, int]:
        """Discard daily records older than the retention window.

        === WHAT THIS DOES ===
        This method removes old daily records while preserving their totals in
        cumulative metadata.

        === WHY IT EXISTS ===
        Daily cache files must stay small, but total-increasing energy sensors still
        need the value of removed historical data.

        === STEP-BY-STEP ===
        1. Count the current daily records.
        2. Compute the cutoff date.
        3. Loop through all daily records.
        4. Keep recent records and total the removed paid/free values.
        5. Add removed totals into cumulative metadata.
        6. Replace the daily dataset and return counts.
        """
        # Count the number of daily records before pruning.
        before_count = len(self.data.get("daily", {}))

        # Work out the oldest date that should still remain.
        cutoff_date = date.today() - timedelta(days=window_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        # Log the chosen cutoff threshold.
        _LOGGER.debug(
            "Pruning daily data for contract %s: keeping records >= %s (window=%d days)",
            self.contract_id,
            cutoff_str,
            window_days,
        )

        # Prepare running totals for data that will be removed.
        removed_paid = 0.0
        removed_free = 0.0

        # Build a fresh dictionary containing only records we decide to keep.
        filtered_daily: dict[str, Any] = {}

        # Inspect each stored daily record.
        for date_key, record in self.data.get("daily", {}).items():
            if date_key >= cutoff_str:
                # Keep recent records unchanged.
                filtered_daily[date_key] = record
            else:
                # Add older removed values into the cumulative totals.
                removed_paid += float(record.get("paid") or 0.0)
                removed_free += float(record.get("free") or 0.0)

        # Preserve removed totals so long-running energy counters remain accurate.
        if removed_paid or removed_free:
            cumulative = self._ensure_cumulative_metadata()
            cumulative["paid_kwh"] = round(cumulative.get("paid_kwh", 0.0) + removed_paid, 3)
            cumulative["free_kwh"] = round(cumulative.get("free_kwh", 0.0) + removed_free, 3)

        # Replace the old daily dataset with the filtered version.
        self.data["daily"] = filtered_daily

        # Count the remaining records and calculate how many were removed.
        after_count = len(self.data["daily"])
        removed_count = before_count - after_count

        # Log the result of pruning.
        if removed_count > 0:
            _LOGGER.info(
                "Pruned %d old daily records for contract %s (kept %d records)",
                removed_count,
                self.contract_id,
                after_count,
            )
        else:
            _LOGGER.debug("No daily records to prune for contract %s", self.contract_id)

        # Return before/after totals for callers and logs.
        return (before_count, after_count)

    def get_cumulative_totals(self, sensor_start_date: Optional[date] = None) -> dict[str, float]:
        """Return cumulative paid/free totals for energy sensors.

        === WHAT THIS DOES ===
        This method combines preserved historical totals with current daily records
        to produce overall paid and free energy usage totals.

        === WHY IT EXISTS ===
        Some energy dashboards need steadily increasing totals. Pruning removes old
        rows, so this helper reconstructs a continuous total across both kept and
        removed history.

        === STEP-BY-STEP ===
        1. Read baseline cumulative totals from metadata.
        2. Loop through daily records.
        3. Optionally skip records before the sensor start date.
        4. Add paid and free values into running sums.
        5. Return rounded totals that include both baseline and current sums.
        """
        # Ensure cumulative metadata exists and read its baseline values.
        cumulative = self._ensure_cumulative_metadata()
        baseline_paid = float(cumulative.get("paid_kwh") or 0.0)
        baseline_free = float(cumulative.get("free_kwh") or 0.0)

        # Start fresh running totals for the currently stored daily records.
        paid_sum = 0.0
        free_sum = 0.0
        record_count = 0

        # Only sum daily records that fall within the requested date range.
        for date_str, record in self.data.get("daily", {}).items():
            if sensor_start_date is not None:
                record_date = date.fromisoformat(date_str)
                if record_date < sensor_start_date:
                    continue

            # Convert stored values into floats before adding them.
            paid_val = float(record.get("paid") or 0.0)
            free_val = float(record.get("free") or 0.0)
            paid_sum += paid_val
            free_sum += free_val
            record_count += 1

            # Log only the first few records to keep debug output readable.
            if record_count <= 3:
                _LOGGER.debug(
                    "Cumulative calc for %s: date=%s, paid=%.3f, free=%.3f",
                    self.contract_id,
                    date_str,
                    paid_val,
                    free_val,
                )

        # Log the totals used to form the final answer.
        _LOGGER.debug(
            "Cumulative totals for %s: counted %d records, paid_sum=%.3f, free_sum=%.3f, baseline_paid=%.3f, baseline_free=%.3f",
            self.contract_id,
            record_count,
            paid_sum,
            free_sum,
            baseline_paid,
            baseline_free,
        )

        # Return the combined historical-plus-current totals.
        return {
            "paid": round(baseline_paid + paid_sum, 3),
            "free": round(baseline_free + free_sum, 3),
        }

    def _ensure_cumulative_metadata(self) -> dict[str, float]:
        """Ensure cumulative metadata exists and return that dictionary.

        === WHAT THIS DOES ===
        This helper guarantees the nested cumulative section is present.

        === WHY IT EXISTS ===
        Old cache files may predate this metadata field, so callers need a safe,
        central way to create it on demand.
        """
        # Ensure the outer metadata dictionary exists.
        metadata = self.data.setdefault("metadata", {})

        # Ensure the cumulative dictionary exists and return it.
        return metadata.setdefault("cumulative", {"paid_kwh": 0.0, "free_kwh": 0.0})

    def get_energy_sensor_start_date(self) -> Optional[date]:
        """Return the stored energy-sensor start date, if any.

        === WHAT THIS DOES ===
        This helper reads the date from which dashboard totals should begin.

        === WHY IT EXISTS ===
        Starting totals from a chosen date prevents a huge historical spike from
        appearing when an energy dashboard is first connected.

        === STEP-BY-STEP ===
        1. Read metadata.
        2. Look inside the energy_sensor subsection.
        3. Parse the stored ISO date if one exists.
        4. Return None otherwise.
        """
        # Read the metadata sections that may contain the configured start date.
        metadata = self.data.get("metadata", {})
        energy_sensor = metadata.get("energy_sensor", {})
        start_date_str = energy_sensor.get("start_date")

        # Convert the stored text into a date object when present.
        if start_date_str:
            return date.fromisoformat(start_date_str)

        # Return None when no start date has been stored yet.
        return None

    def set_energy_sensor_start_date(self, start_date: date) -> None:
        """Store the date from which energy totals should begin.

        === WHAT THIS DOES ===
        This helper writes the chosen start date into cache metadata.

        === WHY IT EXISTS ===
        The legacy energy-dashboard flow needs a durable marker telling it where
        cumulative counting should start.

        === STEP-BY-STEP ===
        1. Ensure the metadata dictionaries exist.
        2. Convert the date to ISO text.
        3. Save it under energy_sensor.start_date.
        """
        # Ensure the outer metadata dictionary exists.
        metadata = self.data.setdefault("metadata", {})

        # Ensure the energy_sensor subsection exists.
        energy_sensor = metadata.setdefault("energy_sensor", {})

        # Store the date as text so it survives JSON serialization.
        energy_sensor["start_date"] = start_date.isoformat()

    def prune_monthly(self, window_months: int = 18) -> tuple[int, int]:
        """Discard monthly records older than the retention window.

        === WHAT THIS DOES ===
        This method keeps only recent monthly records in the cache.

        === WHY IT EXISTS ===
        Monthly data grows more slowly than hourly or daily data, but it still
        benefits from a retention window to keep files compact.

        === STEP-BY-STEP ===
        1. Count existing monthly records.
        2. Approximate a cutoff month.
        3. Rebuild the monthly dictionary with only recent entries.
        4. Log the result and return before/after counts.
        """
        # Count the number of monthly records before pruning.
        before_count = len(self.data.get("monthly", {}))

        # Approximate the cutoff month by moving backward window_months * 30 days.
        cutoff_date = date.today() - timedelta(days=window_months * 30)
        cutoff_str = cutoff_date.strftime("%Y-%m")

        # Log the retention threshold.
        _LOGGER.debug(
            "Pruning monthly data for contract %s: keeping records >= %s (window=%d months)",
            self.contract_id,
            cutoff_str,
            window_months,
        )

        # Keep only month keys on or after the cutoff.
        self.data["monthly"] = {
            month_key: record
            for month_key, record in self.data.get("monthly", {}).items()
            if month_key >= cutoff_str
        }

        # Count the remaining records and calculate removals.
        after_count = len(self.data["monthly"])
        removed_count = before_count - after_count

        # Log whether anything changed.
        if removed_count > 0:
            _LOGGER.info(
                "Pruned %d old monthly records for contract %s (kept %d records)",
                removed_count,
                self.contract_id,
                after_count,
            )
        else:
            _LOGGER.debug("No monthly records to prune for contract %s", self.contract_id)

        # Return the before/after counts.
        return (before_count, after_count)

    def get_hourly_range(self) -> tuple[Optional[date], Optional[date]]:
        """Return the cached hourly date range.

        === WHAT THIS DOES ===
        This helper reads hourly metadata and converts the stored range into date objects.

        === WHY IT EXISTS ===
        Callers often need to know what date window is already cached before they
        decide whether a new fetch is necessary.
        """
        # Read the hourly metadata subsection.
        metadata = self.data.get("metadata", {}).get("hourly", {})
        from_str = metadata.get("from")
        to_str = metadata.get("to")

        # Convert both endpoints into date objects when both are available.
        if from_str and to_str:
            from_date = date.fromisoformat(from_str)
            to_date = date.fromisoformat(to_str)
            return (from_date, to_date)

        # Return explicit empty values when the range is unknown.
        return (None, None)

    def get_daily_range(self) -> tuple[Optional[date], Optional[date]]:
        """Return the cached daily date range.

        === WHAT THIS DOES ===
        This helper reads daily metadata and returns start/end date objects.

        === WHY IT EXISTS ===
        Legacy refresh logic can compare wanted dates against this cached range.
        """
        # Read the daily metadata subsection.
        metadata = self.data.get("metadata", {}).get("daily", {})
        from_str = metadata.get("from")
        to_str = metadata.get("to")

        # Convert both endpoints into date objects when possible.
        if from_str and to_str:
            from_date = date.fromisoformat(from_str)
            to_date = date.fromisoformat(to_str)
            return (from_date, to_date)

        # Return no range when metadata is incomplete.
        return (None, None)

    def get_monthly_range(self) -> tuple[Optional[date], Optional[date]]:
        """Return the cached monthly date range.

        === WHAT THIS DOES ===
        This helper reads monthly metadata and turns stored YYYY-MM values into
        first-of-month date objects.

        === WHY IT EXISTS ===
        Month keys omit the day, so this method provides a normalized date range
        shape for callers that expect date objects.
        """
        # Read the monthly metadata subsection.
        metadata = self.data.get("metadata", {}).get("monthly", {})
        from_str = metadata.get("from")
        to_str = metadata.get("to")

        # Convert YYYY-MM strings into first-day-of-month dates when available.
        if from_str and to_str:
            from_date = date.fromisoformat(from_str + "-01")
            to_date = date.fromisoformat(to_str + "-01")
            return (from_date, to_date)

        # Return no range when metadata is incomplete.
        return (None, None)

    def get_last_synced(self) -> Optional[datetime]:
        """Return the overall last-sync timestamp for the cache.

        === WHAT THIS DOES ===
        This helper reads metadata.last_synced and converts it into a datetime.

        === WHY IT EXISTS ===
        Callers use this quick summary timestamp to judge overall cache freshness.
        """
        # Read the overall last_synced text value from metadata.
        last_synced_str = self.data.get("metadata", {}).get("last_synced")

        # Convert the text into a datetime when present.
        if last_synced_str:
            return datetime.fromisoformat(last_synced_str)

        # Return None if the cache has never been synced or saved.
        return None
