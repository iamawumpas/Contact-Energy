"""Daily usage data manager for Contact Energy.

=== WHAT THIS DOES ===
This module manages cached daily electricity usage data. It stores a rolling
history of daily records, merges new data safely, removes duplicate dates,
updates metadata, and provides helper methods for date ranges and totals.

=== FOR NON-CODERS ===
This file is like a clerk keeping a day-by-day electricity logbook. New pages
can be added, duplicate pages are avoided, old pages beyond the retention
window are removed, and summary calculations can be produced from the logbook.

Version: 2.0.0
"""

# This line enables postponed evaluation of annotations for compatibility.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: Used for debug, info, and warning messages.
import logging

# datetime/timezone/timedelta/date: Used for current time, date filtering,
# timestamp comparisons, and rolling-window calculations.
from datetime import datetime, timezone, timedelta, date

# Any: Type-hint helper for flexible API record structures.
from typing import Any

# BaseCache: Shared parent class providing file, metadata, and lock behavior.
from .base_cache import BaseCache

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Create a logger for this module.
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Daily usage should be refreshed if the last download is at least two hours old.
DAILY_STALENESS_HOURS = 2

# Keep roughly the last three months of daily data.
DAILY_WINDOW_DAYS = 90


# ============================================================================
# DAILY USAGE MANAGER CLASS
# ============================================================================

class UsageDailyDataManager(BaseCache):
    """Manager for daily usage data caching.

    === WHAT THIS DOES ===
    Stores and manages day-by-day usage history, including freshness checks,
    retention pruning, duplicate removal, and summary calculations.

    === FOR NON-CODERS ===
    This class maintains a daily usage journal and offers easy ways to retrieve
    one day, one month, a recent range, or total usage across recent days.
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: usage_daily_{address}_{icp}.json.

        === WHAT THIS DOES ===
        Builds the filename used for the daily usage cache file.

        === FOR NON-CODERS ===
        This is the label placed on the daily usage file.

        Returns:
            The daily cache filename.
        """
        # Combine the interval, address, and ICP into one descriptive filename.
        return f"usage_daily_{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty daily usage cache structure.

        === WHAT THIS DOES ===
        Creates the default dictionary shape for an empty daily usage cache.

        === FOR NON-CODERS ===
        This is a blank day-by-day logbook with a metadata cover page and an
        empty list ready for daily records.

        Returns:
            A dictionary with metadata and an empty usage list.
        """
        # Return the expected starter structure for the daily manager.
        return {
            "metadata": {
                "version": "2.0.0",
                "address": self.address,
                "icp": self.icp,
                "interval": "daily",
                "last_download": None,
                "last_data_timestamp": None,
                "window_days": DAILY_WINDOW_DAYS,
            },
            "usage": [],
        }

    def is_stale(self) -> bool:
        """Check if daily usage data is stale.

        === WHAT THIS DOES ===
        Determines whether the current daily usage cache should be refreshed.

        === FOR NON-CODERS ===
        This method checks three things:
        1. Do we have any saved daily data at all?
        2. Was the saved copy downloaded too long ago?
        3. Is the newest actual daily record still too old?

        Returns:
            True if new daily data should be fetched, otherwise False.
        """
        # If there are no daily usage records, the cache cannot be considered fresh.
        if not self.data.get("usage"):
            _LOGGER.debug("Daily usage data is stale: no data")
            return True

        # Check how long it has been since the last successful download.
        hours_since_download = self.hours_since_last_download()
        if hours_since_download >= DAILY_STALENESS_HOURS:
            _LOGGER.debug(
                "Daily usage data is stale: %.1f hours since download (limit: %d)",
                hours_since_download,
                DAILY_STALENESS_HOURS,
            )
            return True

        # Even if the download itself was recent, the newest daily record might
        # still be too old to trust, which suggests newer API data may exist.
        last_data = self.get_last_data_timestamp()
        if last_data:
            hours_since_data = (datetime.now(timezone.utc) - last_data).total_seconds() / 3600
            if hours_since_data > 36:
                _LOGGER.debug(
                    "Daily usage data is stale: last data is %.1f hours old",
                    hours_since_data,
                )
                return True

        # None of the stale conditions matched, so the cache is still usable.
        _LOGGER.debug(
            "Daily usage data is fresh: %.1f hours since download",
            hours_since_download,
        )
        return False

    def prune(self) -> None:
        """Remove daily data older than the configured window.

        === WHAT THIS DOES ===
        Removes daily records older than the configured 90-day retention window.

        === FOR NON-CODERS ===
        This keeps the logbook focused on recent history instead of growing
        forever with very old daily pages.
        """
        # If there are no usage records, there is nothing to remove.
        if not self.data.get("usage"):
            return

        # Calculate the oldest timestamp we still want to keep.
        cutoff = datetime.now(timezone.utc) - timedelta(days=DAILY_WINDOW_DAYS)

        # Count entries before pruning so we can report the number removed.
        initial_count = len(self.data["usage"])

        # Rebuild the usage list using only entries whose startTime parses to a
        # timestamp newer than the cutoff date.
        self.data["usage"] = [
            entry
            for entry in self.data["usage"]
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

        # Calculate how many records were trimmed away.
        pruned_count = initial_count - len(self.data["usage"])

        # Log only when pruning actually removed something.
        if pruned_count > 0:
            _LOGGER.info(
                "Pruned %d daily usage records older than %d days",
                pruned_count,
                DAILY_WINDOW_DAYS,
            )

    def update(self, usage_data: list[dict[str, Any]], contract_id: str) -> None:
        """Update cache with new daily usage data.

        === WHAT THIS DOES ===
        Merges a newly downloaded batch of daily records into the cache while
        avoiding duplicates, sorting the results, and refreshing metadata.

        === FOR NON-CODERS ===
        When new daily log pages arrive, this method checks which pages are
        already filed, adds only the missing ones, reorders the journal by date,
        and updates the "last refreshed" notes.

        Args:
            usage_data: New daily usage records from the API.
            contract_id: The contract these records belong to.
        """
        # If the new batch is empty, there is nothing useful to add.
        if not usage_data:
            _LOGGER.warning("No daily usage data to update")
            return

        # Ensure the expected usage list exists before merging data into it.
        if "usage" not in self.data:
            self.data = self._create_empty_cache()

        # Ensure metadata exists, then attach the contract ID to that metadata.
        if "metadata" not in self.data:
            self.data["metadata"] = self._create_empty_cache()["metadata"]
        self.data["metadata"]["contract_id"] = contract_id

        # Build a fast-lookup set of timestamps already stored in the cache.
        existing_timestamps = {
            entry.get("startTime") for entry in self.data["usage"]
        }

        # From the newly downloaded batch, keep only entries whose startTime is
        # not already present in the cache.
        new_entries = [
            entry
            for entry in usage_data
            if entry.get("startTime") not in existing_timestamps
        ]

        # Append just the genuinely new entries to the cached usage list.
        self.data["usage"].extend(new_entries)

        # Sort the complete usage list from newest date to oldest date.
        self.data["usage"].sort(
            key=lambda x: x.get("startTime", ""),
            reverse=True,
        )

        # If we now have any usage records, update metadata to reflect the most
        # recent actual data point contained in the cache.
        if self.data["usage"]:
            most_recent = max(
                self.data["usage"],
                key=lambda x: x.get("startTime", ""),
            )
            timestamp = self._parse_timestamp(most_recent.get("startTime"))
            if timestamp:
                self.set_last_data_timestamp(timestamp)

        # Record when this cache update happened.
        self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()

        # Log how many new records were added and the new total count.
        _LOGGER.info(
            "Updated daily usage cache: added %d new records, total %d records",
            len(new_entries),
            len(self.data["usage"]),
        )

    def get_usage(self) -> list[dict[str, Any]]:
        """Get all cached daily usage data.

        === WHAT THIS DOES ===
        Returns the full list of daily usage records.

        === FOR NON-CODERS ===
        This is the "give me the whole daily journal" method.

        Returns:
            A list of daily records, newest first.
        """
        # Safely return the cached usage list, defaulting to an empty list.
        return self.data.get("usage", [])

    def get_usage_for_date(self, target_date: date) -> dict[str, Any] | None:
        """Get daily usage data for a specific date.

        === WHAT THIS DOES ===
        Searches the cached daily records for the entry matching one date.

        === FOR NON-CODERS ===
        This is used when someone wants the usage for one exact day and not the
        whole history.

        Args:
            target_date: The date to search for.

        Returns:
            The matching daily record, or None if not found.
        """
        # Start with the full cached daily history.
        usage = self.get_usage()

        # Loop over each daily record one by one.
        for entry in usage:
            # Parse the stored text timestamp into a datetime object.
            timestamp = self._parse_timestamp(entry.get("startTime"))

            # If parsing succeeded and the calendar date matches, immediately
            # return that record because we found what we wanted.
            if timestamp and timestamp.date() == target_date:
                return entry

        # If the loop finishes with no match, return None.
        return None

    def get_usage_for_month(self, year: int, month: int) -> list[dict[str, Any]]:
        """Get daily usage data for a specific month.

        === WHAT THIS DOES ===
        Filters daily records down to those that belong to one month and year.

        === FOR NON-CODERS ===
        This is like asking for all diary pages from a single month.

        Args:
            year: Calendar year to match.
            month: Calendar month to match (1 through 12).

        Returns:
            A list of daily records for that month, oldest first.
        """
        # Load the full cached daily history.
        usage = self.get_usage()

        # Prepare a list to collect matching entries.
        result = []

        # Check each daily record to see whether it belongs to the requested month.
        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.year == year and timestamp.month == month:
                result.append(entry)

        # Sort month results from oldest to newest because month views are often
        # easier to read in forward time order.
        result.sort(key=lambda x: x.get("startTime", ""))

        # Return the filtered and sorted list.
        return result

    def get_latest_usage(self, days: int = 30) -> list[dict[str, Any]]:
        """Get the most recent N days of usage data.

        === WHAT THIS DOES ===
        Returns daily records newer than the chosen day-based cutoff.

        === FOR NON-CODERS ===
        This answers questions like "Show the last 30 days".

        Args:
            days: Number of recent days to include.

        Returns:
            A list of recent daily records.
        """
        # Load the full usage list.
        usage = self.get_usage()

        # Calculate the oldest timestamp that should still be included.
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Return only records newer than the cutoff.
        return [
            entry
            for entry in usage
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

    def calculate_total_usage(self, days: int = 30) -> dict[str, float]:
        """Calculate total usage for the last N days.

        === WHAT THIS DOES ===
        Sums paid and free usage values across a recent day range.

        === FOR NON-CODERS ===
        Instead of showing each day's usage separately, this method adds the
        recent daily numbers together and produces a simple summary.

        Args:
            days: Number of recent days to include in the total.

        Returns:
            A dictionary containing combined total, paid total, and free total.
        """
        # First, get only the recent daily records within the requested window.
        usage = self.get_latest_usage(days)

        # Prepare running totals. Floating-point numbers are used because usage
        # values may include decimals such as 12.5 kWh.
        total_paid = 0.0
        total_free = 0.0

        # Loop through each recent daily record and add its values into the totals.
        for entry in usage:
            # Read the paid usage value. The fallback of 0 prevents missing or
            # None values from breaking the calculation.
            paid = entry.get("paidUsageKwh", 0) or 0

            # Only add the value if it is a real number.
            if isinstance(paid, (int, float)):
                total_paid += paid

            # Read the free usage value using the same safe fallback pattern.
            free = entry.get("freeUsageKwh", 0) or 0

            # Only add numeric free-usage values.
            if isinstance(free, (int, float)):
                total_free += free

        # Return a summary dictionary with combined and separated totals.
        return {
            "total_kwh": total_paid + total_free,
            "total_paid_kwh": total_paid,
            "total_free_kwh": total_free,
        }

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse ISO timestamp string to datetime.

        === WHAT THIS DOES ===
        Converts text timestamps from cached/API data into datetime objects.

        === FOR NON-CODERS ===
        JSON stores timestamps as text, but calculations need real date/time
        objects. This helper performs that translation.

        Args:
            timestamp_str: Timestamp text to parse.

        Returns:
            A datetime object, or None if parsing fails.
        """
        # If there is no timestamp text, return None immediately.
        if not timestamp_str:
            return None

        try:
            # Convert trailing "Z" to "+00:00" so Python recognizes it as UTC.
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"

            # Parse the cleaned text into a datetime object.
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError) as err:
            # Log invalid timestamp data and safely return None.
            _LOGGER.warning("Failed to parse timestamp '%s': %s", timestamp_str, err)
            return None
