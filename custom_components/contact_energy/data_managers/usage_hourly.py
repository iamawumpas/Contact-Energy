"""Hourly usage data manager for Contact Energy.

=== WHAT THIS DOES ===
This module manages cached hourly electricity usage data. It stores a rolling
window of hourly records, merges in newly downloaded usage without duplicating
existing hours, tracks timestamps, and removes records that are too old.

=== FOR NON-CODERS ===
This file is like a clerk maintaining an hour-by-hour electricity diary.
Whenever new usage data arrives, the clerk adds missing entries, avoids filing
the same hour twice, keeps the list in time order, and throws away very old
entries outside the allowed history window.

A "cache" is a saved copy of downloaded information.
"Pruning" means trimming away old records that are no longer needed.

Version: 2.0.0
"""

# This line enables postponed evaluation of type hints for compatibility.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: Used to record what this manager is doing for debugging.
import logging

# datetime/timezone/timedelta/date: Used for current time, time comparisons,
# cutoff calculations, and filtering records for specific calendar dates.
from datetime import datetime, timezone, timedelta, date

# Any: Type-hint helper because usage records are dictionaries with mixed values.
from typing import Any

# BaseCache: Shared parent class that supplies JSON loading/saving, metadata,
# and lock handling.
from .base_cache import BaseCache

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Create a logger specific to the hourly usage manager.
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Refresh hourly usage if the cached copy is an hour old or more.
HOURLY_STALENESS_HOURS = 1

# Keep only the last seven days of hourly records.
HOURLY_WINDOW_DAYS = 7


# ============================================================================
# HOURLY USAGE MANAGER CLASS
# ============================================================================

class UsageHourlyDataManager(BaseCache):
    """Manager for hourly usage data caching.

    === WHAT THIS DOES ===
    Stores and manages hour-by-hour usage records, including freshness checks,
    duplicate prevention, sorting, pruning, and filtering helpers.

    === FOR NON-CODERS ===
    This class looks after a timeline made of individual hours. It helps the
    rest of the integration ask questions like "Do we need fresh hourly data?"
    or "Show me the last 24 hours".
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: usage_hourly_{address}_{icp}.json.

        === WHAT THIS DOES ===
        Creates the filename used to store hourly usage on disk.

        === FOR NON-CODERS ===
        This is the label placed on the hourly usage file.

        Returns:
            The hourly cache filename.
        """
        # Combine the data type, address, and ICP into one descriptive filename.
        return f"usage_hourly_{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty hourly usage cache structure.

        === WHAT THIS DOES ===
        Defines the blank starting structure for hourly usage data.

        === FOR NON-CODERS ===
        This creates an empty diary with a metadata cover page and a blank list
        where hourly entries will be stored.

        Returns:
            A dictionary containing metadata and an empty usage list.
        """
        # Return the default structure expected by all hourly-usage methods.
        return {
            "metadata": {
                "version": "2.0.0",
                "address": self.address,
                "icp": self.icp,
                "interval": "hourly",
                "last_download": None,
                "last_data_timestamp": None,
                "window_days": HOURLY_WINDOW_DAYS,
            },
            "usage": [],
        }

    def is_stale(self) -> bool:
        """Check if hourly usage data is stale.

        === WHAT THIS DOES ===
        Decides whether the saved hourly usage should be refreshed.

        === FOR NON-CODERS ===
        Hourly data can become outdated quickly. This method checks whether the
        saved copy is missing, downloaded too long ago, or ends too far in the
        past.

        Returns:
            True if new hourly usage should be downloaded, otherwise False.
        """
        # ====================================================================
        # RULE 1: NO USAGE DATA MEANS THE CACHE IS DEFINITELY STALE
        # ====================================================================
        if not self.data.get("usage"):
            _LOGGER.debug("Hourly usage data is stale: no data")
            return True

        # ====================================================================
        # RULE 2: IF THE LAST DOWNLOAD WAS TOO LONG AGO, REFRESH THE CACHE
        # ====================================================================
        hours_since_download = self.hours_since_last_download()
        if hours_since_download >= HOURLY_STALENESS_HOURS:
            _LOGGER.debug(
                "Hourly usage data is stale: %.1f hours since download (limit: %d)",
                hours_since_download,
                HOURLY_STALENESS_HOURS,
            )
            return True

        # ====================================================================
        # RULE 3: IF THE NEWEST ACTUAL DATA POINT IS TOO OLD, REFRESH THE CACHE
        # ====================================================================
        # This catches the case where a download happened recently, but the data
        # inside that download still does not include recent hours.
        last_data = self.get_last_data_timestamp()
        if last_data:
            # Convert the age difference from seconds into hours.
            hours_since_data = (datetime.now(timezone.utc) - last_data).total_seconds() / 3600
            if hours_since_data > 6:
                _LOGGER.debug(
                    "Hourly usage data is stale: last data is %.1f hours old",
                    hours_since_data,
                )
                return True

        # If none of the stale conditions matched, keep using the current cache.
        _LOGGER.debug(
            "Hourly usage data is fresh: %.1f hours since download",
            hours_since_download,
        )
        return False

    def prune(self) -> None:
        """Remove hourly data older than the configured window.

        === WHAT THIS DOES ===
        Deletes cached hourly records older than the allowed rolling history.

        === FOR NON-CODERS ===
        Without pruning, the hourly diary would grow forever. This method keeps
        only the most recent seven days so the cache stays focused and smaller.
        """
        # If there are no usage records at all, there is nothing to prune.
        if not self.data.get("usage"):
            return

        # ====================================================================
        # STEP 1: CALCULATE THE CUT-OFF TIME
        # ====================================================================
        # Any record older than this timestamp should be removed.
        cutoff = datetime.now(timezone.utc) - timedelta(days=HOURLY_WINDOW_DAYS)

        # Count records before pruning so we can later report how many were cut.
        initial_count = len(self.data["usage"])

        # ====================================================================
        # STEP 2: BUILD A NEW LIST CONTAINING ONLY RECENT ENTRIES
        # ====================================================================
        # This list comprehension loops through each usage entry, parses its
        # startTime, and keeps only entries newer than the cutoff.
        self.data["usage"] = [
            entry
            for entry in self.data["usage"]
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

        # Calculate how many records were removed.
        pruned_count = initial_count - len(self.data["usage"])

        # Only log a prune message if something was actually removed.
        if pruned_count > 0:
            _LOGGER.info(
                "Pruned %d hourly usage records older than %d days",
                pruned_count,
                HOURLY_WINDOW_DAYS,
            )

    def update(self, usage_data: list[dict[str, Any]], contract_id: str) -> None:
        """Update cache with new hourly usage data.

        === WHAT THIS DOES ===
        Merges a newly downloaded batch of hourly usage records into the cache,
        avoids duplicates, sorts the final list, and refreshes metadata.

        === FOR NON-CODERS ===
        Imagine receiving a new stack of hourly diary pages. This method checks
        which pages are new, adds only those, puts the whole diary back in time
        order, then notes when the update happened.

        Args:
            usage_data: New hourly usage records from the API.
            contract_id: The contract these usage records belong to.
        """
        # If the API gave us no records, log a warning and stop immediately.
        if not usage_data:
            _LOGGER.warning("No hourly usage data to update")
            return

        # ====================================================================
        # STEP 1: ENSURE THE EXPECTED DATA STRUCTURE EXISTS
        # ====================================================================
        if "usage" not in self.data:
            # Rebuild the full default cache structure if usage is missing.
            self.data = self._create_empty_cache()

        # ====================================================================
        # STEP 2: ENSURE METADATA EXISTS AND STORE THE CONTRACT ID
        # ====================================================================
        if "metadata" not in self.data:
            self.data["metadata"] = self._create_empty_cache()["metadata"]
        self.data["metadata"]["contract_id"] = contract_id

        # ====================================================================
        # STEP 3: COLLECT TIMESTAMPS ALREADY IN THE CACHE
        # ====================================================================
        # A set is used because membership checks are fast.
        existing_timestamps = {
            entry.get("startTime") for entry in self.data["usage"]
        }

        # ====================================================================
        # STEP 4: FILTER THE NEW BATCH SO ONLY BRAND-NEW HOURS ARE ADDED
        # ====================================================================
        new_entries = [
            entry
            for entry in usage_data
            if entry.get("startTime") not in existing_timestamps
        ]

        # Append the new records to the existing cached records.
        self.data["usage"].extend(new_entries)

        # ====================================================================
        # STEP 5: SORT ALL CACHED HOURLY RECORDS FROM NEWEST TO OLDEST
        # ====================================================================
        self.data["usage"].sort(
            key=lambda x: x.get("startTime", ""),
            reverse=True,
        )

        # ====================================================================
        # STEP 6: UPDATE THE "LAST DATA TIMESTAMP" METADATA
        # ====================================================================
        if self.data["usage"]:
            # Find the record with the newest startTime value.
            most_recent = max(
                self.data["usage"],
                key=lambda x: x.get("startTime", ""),
            )

            # Parse its timestamp text into a datetime object.
            timestamp = self._parse_timestamp(most_recent.get("startTime"))

            # Only store the timestamp if parsing succeeded.
            if timestamp:
                self.set_last_data_timestamp(timestamp)

        # Record the moment this cache refresh happened.
        self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()

        # Log how many entries were added and how many are stored total.
        _LOGGER.info(
            "Updated hourly usage cache: added %d new records, total %d records",
            len(new_entries),
            len(self.data["usage"]),
        )

    def get_usage(self) -> list[dict[str, Any]]:
        """Get all cached hourly usage data.

        === WHAT THIS DOES ===
        Returns the full hourly usage list from the cache.

        === FOR NON-CODERS ===
        This is the easiest way to say, "Give me the whole hourly diary."

        Returns:
            A list of hourly usage records, newest first.
        """
        # Return the usage list, or an empty list if it is missing.
        return self.data.get("usage", [])

    def get_usage_for_date(self, target_date: date) -> list[dict[str, Any]]:
        """Get hourly usage data for a specific date.

        === WHAT THIS DOES ===
        Filters the full hourly history down to records that belong to one day.

        === FOR NON-CODERS ===
        If you only want the hourly entries for a single calendar date, this
        method goes through the diary and picks out those matching pages.

        Args:
            target_date: The calendar date to match.

        Returns:
            A list of hourly records for that day.
        """
        # Start with all cached hourly records.
        usage = self.get_usage()

        # Prepare an empty list where matching entries will be collected.
        result = []

        # Loop through each cached hourly record one by one.
        for entry in usage:
            # Convert the stored timestamp text into a datetime object.
            timestamp = self._parse_timestamp(entry.get("startTime"))

            # Keep the record only if parsing succeeded and the calendar date
            # matches the target date supplied by the caller.
            if timestamp and timestamp.date() == target_date:
                result.append(entry)

        # Return the filtered list for the requested day.
        return result

    def get_latest_usage(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get the most recent N hours of usage data.

        === WHAT THIS DOES ===
        Returns only records newer than the chosen hours-back cutoff.

        === FOR NON-CODERS ===
        This is how the code answers questions like "Show the last 24 hours of
        usage" without manually checking every timestamp elsewhere.

        Args:
            hours: How many recent hours to include.

        Returns:
            A list of records newer than the cutoff time.
        """
        # Load the full cached hourly history.
        usage = self.get_usage()

        # Calculate the oldest time that should still be included.
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Build and return a filtered list containing only records newer than
        # the cutoff. The parsing step converts each text timestamp into a
        # comparable datetime.
        return [
            entry
            for entry in usage
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse ISO timestamp string to datetime.

        === WHAT THIS DOES ===
        Converts stored timestamp text into a datetime object the code can use
        for comparisons, sorting, and age calculations.

        === FOR NON-CODERS ===
        Timestamps are saved as text in JSON files. This helper translates that
        text back into a proper time value the program understands.

        Args:
            timestamp_str: Timestamp text, usually in ISO format.

        Returns:
            A datetime object if parsing succeeds, otherwise None.
        """
        # If no timestamp text was provided, parsing is impossible.
        if not timestamp_str:
            return None

        try:
            # Some API timestamps end with "Z", which is shorthand for UTC.
            # Python's fromisoformat prefers "+00:00", so convert the ending.
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"

            # Convert the cleaned timestamp text into a datetime object.
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError) as err:
            # If parsing fails, log the problem and return None instead of
            # raising an exception that could interrupt the calling code.
            _LOGGER.warning("Failed to parse timestamp '%s': %s", timestamp_str, err)
            return None
