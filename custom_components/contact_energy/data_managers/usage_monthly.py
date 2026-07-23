"""Monthly usage data manager for Contact Energy.

=== WHAT THIS DOES ===
This module manages cached monthly electricity usage data. It keeps a rolling
multi-month history, merges new monthly records, avoids duplicates, updates
metadata, removes old records, and provides helpers for totals and averages.

=== FOR NON-CODERS ===
This file is like the clerk in charge of a month-by-month usage ledger. It
stores each month's usage summary, keeps the ledger tidy, and can calculate
high-level summaries such as total or average monthly usage.

Version: 2.0.0
"""

# This line enables postponed annotation evaluation for compatibility.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# logging: Used to write debug and status information for this manager.
import logging

# datetime/timezone/timedelta/date: Used for current time, rolling cutoffs,
# and date-based filtering of monthly records.
from datetime import datetime, timezone, timedelta, date

# Any: Type-hint helper for flexible usage-record dictionaries.
from typing import Any

# BaseCache: Shared parent class for loading/saving JSON cache files and
# handling metadata and locking behavior.
from .base_cache import BaseCache

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Create a logger for the monthly manager.
_LOGGER = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Monthly data changes more slowly, so refresh only every six hours.
MONTHLY_STALENESS_HOURS = 6

# Keep about two years of monthly history.
MONTHLY_WINDOW_MONTHS = 24


# ============================================================================
# MONTHLY USAGE MANAGER CLASS
# ============================================================================

class UsageMonthlyDataManager(BaseCache):
    """Manager for monthly usage data caching.

    === WHAT THIS DOES ===
    Stores and manages month-by-month usage history with freshness checks,
    retention pruning, duplicate prevention, totals, and averages.

    === FOR NON-CODERS ===
    This class maintains the monthly summary ledger and helps answer questions
    like "Do we need newer monthly data?", "What happened this year?", and
    "What is the average monthly usage?"
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: usage_monthly_{address}_{icp}.json.

        === WHAT THIS DOES ===
        Builds the filename for the monthly usage cache file.

        === FOR NON-CODERS ===
        This is the label used on the monthly ledger file.

        Returns:
            The monthly cache filename.
        """
        # Combine the interval name with the address and ICP identifiers.
        return f"usage_monthly_{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty monthly usage cache structure.

        === WHAT THIS DOES ===
        Defines the default shape of an empty monthly usage cache.

        === FOR NON-CODERS ===
        This is a blank monthly ledger with a metadata section and an empty list
        waiting for monthly records.

        Returns:
            A dictionary with metadata and an empty usage list.
        """
        # Return the starter structure all monthly methods expect to find.
        return {
            "metadata": {
                "version": "2.0.0",
                "address": self.address,
                "icp": self.icp,
                "interval": "monthly",
                "last_download": None,
                "last_data_timestamp": None,
                "window_months": MONTHLY_WINDOW_MONTHS,
            },
            "usage": [],
        }

    def is_stale(self) -> bool:
        """Check if monthly usage data is stale.

        === WHAT THIS DOES ===
        Determines whether the cached monthly data should be refreshed.

        === FOR NON-CODERS ===
        Monthly information changes slowly, so the freshness rule is more
        relaxed than hourly or daily data. This method checks whether the data
        is missing or older than the allowed age.

        Returns:
            True if new monthly data should be fetched, otherwise False.
        """
        # If there are no monthly records at all, the cache is stale.
        if not self.data.get("usage"):
            _LOGGER.debug("Monthly usage data is stale: no data")
            return True

        # Measure how long it has been since the cache was last downloaded.
        hours_since_download = self.hours_since_last_download()
        if hours_since_download >= MONTHLY_STALENESS_HOURS:
            _LOGGER.debug(
                "Monthly usage data is stale: %.1f hours since download (limit: %d)",
                hours_since_download,
                MONTHLY_STALENESS_HOURS,
            )
            return True

        # If the data exists and is still within the age limit, keep using it.
        _LOGGER.debug(
            "Monthly usage data is fresh: %.1f hours since download",
            hours_since_download,
        )
        return False

    def prune(self) -> None:
        """Remove monthly data older than the configured window.

        === WHAT THIS DOES ===
        Trims monthly records older than the configured rolling retention window.

        === FOR NON-CODERS ===
        This prevents the ledger from keeping an unlimited history. Only the
        most recent two years of monthly records are kept.
        """
        # If there are no usage records, there is nothing to prune.
        if not self.data.get("usage"):
            return

        # Calculate an approximate cutoff by treating each month as 30 days.
        cutoff = datetime.now(timezone.utc) - timedelta(days=MONTHLY_WINDOW_MONTHS * 30)

        # Count current records so we can report how many are removed.
        initial_count = len(self.data["usage"])

        # Rebuild the usage list using only records newer than the cutoff.
        self.data["usage"] = [
            entry
            for entry in self.data["usage"]
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

        # Work out how many old records were removed.
        pruned_count = initial_count - len(self.data["usage"])

        # Log only if pruning actually removed records.
        if pruned_count > 0:
            _LOGGER.info(
                "Pruned %d monthly usage records older than %d months",
                pruned_count,
                MONTHLY_WINDOW_MONTHS,
            )

    def update(self, usage_data: list[dict[str, Any]], contract_id: str) -> None:
        """Update cache with new monthly usage data.

        === WHAT THIS DOES ===
        Merges new monthly records into the existing cache, skipping duplicate
        months, sorting the final list, and updating metadata.

        === FOR NON-CODERS ===
        When new monthly summary pages arrive, this method checks which pages
        are already filed, adds only the missing ones, reorders the ledger, and
        updates the notes showing when the cache was refreshed.

        Args:
            usage_data: New monthly usage records from the API.
            contract_id: The contract these monthly records belong to.
        """
        # If the API returned no records, stop here after logging the issue.
        if not usage_data:
            _LOGGER.warning("No monthly usage data to update")
            return

        # Ensure the expected usage list exists before merging new entries.
        if "usage" not in self.data:
            self.data = self._create_empty_cache()

        # Ensure metadata exists so we can record the contract ID and timestamps.
        if "metadata" not in self.data:
            self.data["metadata"] = self._create_empty_cache()["metadata"]
        self.data["metadata"]["contract_id"] = contract_id

        # Create a set of already-known timestamps so duplicate monthly entries
        # can be identified quickly.
        existing_timestamps = {
            entry.get("startTime") for entry in self.data["usage"]
        }

        # Keep only entries whose startTime does not already exist in the cache.
        new_entries = [
            entry
            for entry in usage_data
            if entry.get("startTime") not in existing_timestamps
        ]

        # Append the genuinely new entries to the cached monthly list.
        self.data["usage"].extend(new_entries)

        # Sort the full list from newest month to oldest month.
        self.data["usage"].sort(
            key=lambda x: x.get("startTime", ""),
            reverse=True,
        )

        # If any records exist, update metadata with the timestamp of the newest
        # actual data point currently in the cache.
        if self.data["usage"]:
            most_recent = max(
                self.data["usage"],
                key=lambda x: x.get("startTime", ""),
            )
            timestamp = self._parse_timestamp(most_recent.get("startTime"))
            if timestamp:
                self.set_last_data_timestamp(timestamp)

        # Record when this monthly cache update was performed.
        self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()

        # Log the update summary for debugging and maintenance visibility.
        _LOGGER.info(
            "Updated monthly usage cache: added %d new records, total %d records",
            len(new_entries),
            len(self.data["usage"]),
        )

    def get_usage(self) -> list[dict[str, Any]]:
        """Get all cached monthly usage data.

        === WHAT THIS DOES ===
        Returns the full list of cached monthly records.

        === FOR NON-CODERS ===
        This is the "give me the whole monthly ledger" method.

        Returns:
            A list of monthly records, newest first.
        """
        # Safely return the monthly usage list or an empty list if missing.
        return self.data.get("usage", [])

    def get_usage_for_month(self, year: int, month: int) -> dict[str, Any] | None:
        """Get monthly usage data for a specific month.

        === WHAT THIS DOES ===
        Searches cached monthly records for one exact year/month combination.

        === FOR NON-CODERS ===
        This is used when the caller wants the summary page for one single month.

        Args:
            year: Year to match.
            month: Month to match (1 through 12).

        Returns:
            The matching monthly record, or None if not found.
        """
        # Load the full monthly history.
        usage = self.get_usage()

        # Inspect each record one at a time until a match is found.
        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.year == year and timestamp.month == month:
                return entry

        # Return None if no record matched the requested month.
        return None

    def get_usage_for_year(self, year: int) -> list[dict[str, Any]]:
        """Get monthly usage data for a specific year.

        === WHAT THIS DOES ===
        Filters the monthly history down to entries that belong to one year.

        === FOR NON-CODERS ===
        This is like asking for all monthly summary pages from one calendar year.

        Args:
            year: Year to match.

        Returns:
            A list of monthly records for that year, sorted January to December.
        """
        # Start with the full cached monthly history.
        usage = self.get_usage()

        # Prepare a list where matching records will be collected.
        result = []

        # Review each monthly record and keep it if its year matches.
        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.year == year:
                result.append(entry)

        # Sort results in forward time order so the year reads naturally from
        # earlier months to later months.
        result.sort(key=lambda x: x.get("startTime", ""))

        # Return the filtered yearly list.
        return result

    def get_latest_usage(self, months: int = 12) -> list[dict[str, Any]]:
        """Get the most recent N months of usage data.

        === WHAT THIS DOES ===
        Returns monthly records newer than the requested month-based cutoff.

        === FOR NON-CODERS ===
        This answers questions like "Show me the last 12 months".

        Args:
            months: Number of recent months to include.

        Returns:
            A list of recent monthly records.
        """
        # Load the full monthly history.
        usage = self.get_usage()

        # Approximate the cutoff by treating each month as 30 days.
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

        # Return only records newer than the cutoff.
        return [
            entry
            for entry in usage
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

    def calculate_total_usage(self, months: int = 12) -> dict[str, float]:
        """Calculate total usage for the last N months.

        === WHAT THIS DOES ===
        Adds together paid and free usage values across a recent monthly range.

        === FOR NON-CODERS ===
        Instead of listing each month separately, this method produces a simple
        combined summary for the recent monthly period.

        Args:
            months: Number of recent months to include.

        Returns:
            A dictionary containing total, paid total, and free total usage.
        """
        # Get only the recent monthly records within the requested range.
        usage = self.get_latest_usage(months)

        # Prepare running totals for paid and free usage values.
        total_paid = 0.0
        total_free = 0.0

        # Loop through each record and add numeric values into the totals.
        for entry in usage:
            # Read the paid usage field, falling back to zero if missing or None.
            paid = entry.get("paidUsageKwh", 0) or 0
            if isinstance(paid, (int, float)):
                total_paid += paid

            # Read the free usage field with the same safe numeric pattern.
            free = entry.get("freeUsageKwh", 0) or 0
            if isinstance(free, (int, float)):
                total_free += free

        # Return a summary dictionary containing separate and combined totals.
        return {
            "total_kwh": total_paid + total_free,
            "total_paid_kwh": total_paid,
            "total_free_kwh": total_free,
        }

    def calculate_average_usage(self, months: int = 12) -> dict[str, float]:
        """Calculate average monthly usage for the last N months.

        === WHAT THIS DOES ===
        Computes average total, paid, and free usage across recent monthly data.

        === FOR NON-CODERS ===
        This method first gathers the recent monthly records, then calculates the
        typical monthly usage by dividing totals by the number of months found.

        Args:
            months: Number of recent months to consider.

        Returns:
            A dictionary containing average total, paid, and free usage values.
        """
        # Start by getting the recent monthly records within the requested window.
        usage = self.get_latest_usage(months)

        # If there are no records, return zeros to avoid division by zero and to
        # clearly indicate that no average can be computed from missing data.
        if not usage:
            return {
                "average_kwh": 0.0,
                "average_paid_kwh": 0.0,
                "average_free_kwh": 0.0,
            }

        # Reuse the total-calculation helper so the averaging logic stays simple
        # and consistent with total usage calculations.
        totals = self.calculate_total_usage(months)

        # Count how many monthly records contributed to the average.
        count = len(usage)

        # Divide each total by the number of records to get averages.
        return {
            "average_kwh": totals["total_kwh"] / count,
            "average_paid_kwh": totals["total_paid_kwh"] / count,
            "average_free_kwh": totals["total_free_kwh"] / count,
        }

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse ISO timestamp string to datetime.

        === WHAT THIS DOES ===
        Converts stored timestamp text into a datetime object for comparisons.

        === FOR NON-CODERS ===
        JSON stores dates and times as text, so this helper translates that text
        into a form the program can compare and calculate with.

        Args:
            timestamp_str: Timestamp text to parse.

        Returns:
            A datetime object if parsing succeeds, otherwise None.
        """
        # No text means there is nothing to parse.
        if not timestamp_str:
            return None

        try:
            # Convert trailing "Z" into "+00:00" so Python recognizes UTC.
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"

            # Parse the normalized text into a datetime object.
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError) as err:
            # Log invalid timestamp text and safely return None.
            _LOGGER.warning("Failed to parse timestamp '%s': %s", timestamp_str, err)
            return None
