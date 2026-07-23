"""Daily usage data manager for Contact Energy.

This module manages daily usage data caching, including automatic pruning
of data older than the configured window.

Cache file: usage_daily_{address}_{icp}.json
Staleness: Re-download if >2 hours since last download

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Any

from .base_cache import BaseCache

_LOGGER = logging.getLogger(__name__)

# Configuration constants
DAILY_STALENESS_HOURS = 2  # Re-download if >2 hours since last download
DAILY_WINDOW_DAYS = 90  # Keep 90 days (3 months) of daily data


class UsageDailyDataManager(BaseCache):
    """Manager for daily usage data caching.

    Handles caching of:
    - Daily electricity usage (kWh)
    - Paid vs. free usage breakdown
    - Cost per day
    - Timestamps and interval information

    Cache file: usage_daily_{address}_{icp}.json
    Staleness: Re-download if >2 hours since last download OR last_data_timestamp >36 hours old
    Window: Keep last 90 days of data, prune older entries
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: usage_daily_{address}_{icp}.json"""
        return f"usage_daily_{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty daily usage cache structure."""
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

        Staleness rules:
        - No data exists: STALE
        - Last download >2 hours ago: STALE
        - Last data timestamp >36 hours ago: STALE (data is likely incomplete)
        - Otherwise: FRESH

        Returns:
            True if data needs refresh
        """
        # No data = stale
        if not self.data.get("usage"):
            _LOGGER.debug("Daily usage data is stale: no data")
            return True

        # Check download timestamp
        hours_since_download = self.hours_since_last_download()
        if hours_since_download >= DAILY_STALENESS_HOURS:
            _LOGGER.debug(
                "Daily usage data is stale: %.1f hours since download (limit: %d)",
                hours_since_download,
                DAILY_STALENESS_HOURS
            )
            return True

        # Check if last data point is too old (>36 hours)
        # This catches cases where API has new data but we haven't downloaded it
        last_data = self.get_last_data_timestamp()
        if last_data:
            hours_since_data = (datetime.now(timezone.utc) - last_data).total_seconds() / 3600
            if hours_since_data > 36:
                _LOGGER.debug(
                    "Daily usage data is stale: last data is %.1f hours old",
                    hours_since_data
                )
                return True

        _LOGGER.debug("Daily usage data is fresh: %.1f hours since download", hours_since_download)
        return False

    def prune(self) -> None:
        """Remove daily data older than the configured window.

        Keeps only the last DAILY_WINDOW_DAYS days of data.
        """
        if not self.data.get("usage"):
            return

        # Calculate cutoff date
        cutoff = datetime.now(timezone.utc) - timedelta(days=DAILY_WINDOW_DAYS)
        initial_count = len(self.data["usage"])

        # Filter out old data
        self.data["usage"] = [
            entry for entry in self.data["usage"]
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

        pruned_count = initial_count - len(self.data["usage"])
        if pruned_count > 0:
            _LOGGER.info(
                "Pruned %d daily usage records older than %d days",
                pruned_count,
                DAILY_WINDOW_DAYS
            )

    def update(self, usage_data: list[dict[str, Any]], contract_id: str) -> None:
        """Update cache with new daily usage data.

        Merges new data with existing data, removing duplicates based on startTime.
        Updates metadata timestamps.

        Args:
            usage_data: List of daily usage records from API
            contract_id: Contract ID for this usage data
        """
        if not usage_data:
            _LOGGER.warning("No daily usage data to update")
            return

        # Ensure data structure exists
        if "usage" not in self.data:
            self.data = self._create_empty_cache()

        # Store contract_id in metadata
        if "metadata" not in self.data:
            self.data["metadata"] = self._create_empty_cache()["metadata"]
        self.data["metadata"]["contract_id"] = contract_id

        # Merge new data with existing data (avoid duplicates)
        existing_timestamps = {
            entry.get("startTime") for entry in self.data["usage"]
        }

        new_entries = [
            entry for entry in usage_data
            if entry.get("startTime") not in existing_timestamps
        ]

        self.data["usage"].extend(new_entries)

        # Sort by timestamp (newest first)
        self.data["usage"].sort(
            key=lambda x: x.get("startTime", ""),
            reverse=True
        )

        # Update metadata timestamps
        if self.data["usage"]:
            # Find most recent timestamp
            most_recent = max(
                self.data["usage"],
                key=lambda x: x.get("startTime", "")
            )
            timestamp = self._parse_timestamp(most_recent.get("startTime"))
            if timestamp:
                self.set_last_data_timestamp(timestamp)

        self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()

        _LOGGER.info(
            "Updated daily usage cache: added %d new records, total %d records",
            len(new_entries),
            len(self.data["usage"])
        )

    def get_usage(self) -> list[dict[str, Any]]:
        """Get all cached daily usage data.

        Returns:
            List of daily usage records, sorted by timestamp (newest first)
        """
        return self.data.get("usage", [])

    def get_usage_for_date(self, target_date: date) -> dict[str, Any] | None:
        """Get daily usage data for a specific date.

        Args:
            target_date: Date to retrieve usage for

        Returns:
            Daily usage record for the specified date, or None if not found
        """
        usage = self.get_usage()

        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.date() == target_date:
                return entry

        return None

    def get_usage_for_month(self, year: int, month: int) -> list[dict[str, Any]]:
        """Get daily usage data for a specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            List of daily usage records for the specified month
        """
        usage = self.get_usage()
        result = []

        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.year == year and timestamp.month == month:
                result.append(entry)

        # Sort by date (oldest first for month view)
        result.sort(key=lambda x: x.get("startTime", ""))
        return result

    def get_latest_usage(self, days: int = 30) -> list[dict[str, Any]]:
        """Get the most recent N days of usage data.

        Args:
            days: Number of days to retrieve (default: 30)

        Returns:
            List of usage records from the last N days
        """
        usage = self.get_usage()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        return [
            entry for entry in usage
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

    def calculate_total_usage(self, days: int = 30) -> dict[str, float]:
        """Calculate total usage for the last N days.

        Args:
            days: Number of days to calculate (default: 30)

        Returns:
            Dictionary with total_kwh, total_paid_kwh, total_free_kwh
        """
        usage = self.get_latest_usage(days)

        total_paid = 0.0
        total_free = 0.0

        for entry in usage:
            # Sum paid usage
            paid = entry.get("paidUsageKwh", 0) or 0
            if isinstance(paid, (int, float)):
                total_paid += paid

            # Sum free usage
            free = entry.get("freeUsageKwh", 0) or 0
            if isinstance(free, (int, float)):
                total_free += free

        return {
            "total_kwh": total_paid + total_free,
            "total_paid_kwh": total_paid,
            "total_free_kwh": total_free,
        }

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse ISO timestamp string to datetime.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            Datetime object, or None if parsing fails
        """
        if not timestamp_str:
            return None

        try:
            # Handle different timestamp formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Failed to parse timestamp '%s': %s", timestamp_str, err)
            return None
