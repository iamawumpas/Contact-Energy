"""Monthly usage data manager for Contact Energy.

This module manages monthly usage data caching, including automatic pruning
of data older than the configured window.

Cache file: usage_monthly_{address}_{icp}.json
Staleness: Re-download if >6 hours since last download

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Any

from .base_cache import BaseCache

_LOGGER = logging.getLogger(__name__)

# Configuration constants
MONTHLY_STALENESS_HOURS = 6  # Re-download if >6 hours since last download
MONTHLY_WINDOW_MONTHS = 24  # Keep 24 months (2 years) of monthly data


class UsageMonthlyDataManager(BaseCache):
    """Manager for monthly usage data caching.

    Handles caching of:
    - Monthly electricity usage (kWh)
    - Paid vs. free usage breakdown
    - Cost per month
    - Timestamps and interval information

    Cache file: usage_monthly_{address}_{icp}.json
    Staleness: Re-download if >6 hours since last download
    Window: Keep last 24 months of data, prune older entries
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: usage_monthly_{address}_{icp}.json"""
        return f"usage_monthly_{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty monthly usage cache structure."""
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

        Staleness rules:
        - No data exists: STALE
        - Last download >6 hours ago: STALE
        - Otherwise: FRESH

        Monthly data changes slowly, so we use a longer staleness window.

        Returns:
            True if data needs refresh
        """
        # No data = stale
        if not self.data.get("usage"):
            _LOGGER.debug("Monthly usage data is stale: no data")
            return True

        # Check download timestamp
        hours_since_download = self.hours_since_last_download()
        if hours_since_download >= MONTHLY_STALENESS_HOURS:
            _LOGGER.debug(
                "Monthly usage data is stale: %.1f hours since download (limit: %d)",
                hours_since_download,
                MONTHLY_STALENESS_HOURS
            )
            return True

        _LOGGER.debug("Monthly usage data is fresh: %.1f hours since download", hours_since_download)
        return False

    def prune(self) -> None:
        """Remove monthly data older than the configured window.

        Keeps only the last MONTHLY_WINDOW_MONTHS months of data.
        """
        if not self.data.get("usage"):
            return

        # Calculate cutoff date (approximate - 24 months = ~730 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=MONTHLY_WINDOW_MONTHS * 30)
        initial_count = len(self.data["usage"])

        # Filter out old data
        self.data["usage"] = [
            entry for entry in self.data["usage"]
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

        pruned_count = initial_count - len(self.data["usage"])
        if pruned_count > 0:
            _LOGGER.info(
                "Pruned %d monthly usage records older than %d months",
                pruned_count,
                MONTHLY_WINDOW_MONTHS
            )

    def update(self, usage_data: list[dict[str, Any]], contract_id: str) -> None:
        """Update cache with new monthly usage data.

        Merges new data with existing data, removing duplicates based on startTime.
        Updates metadata timestamps.

        Args:
            usage_data: List of monthly usage records from API
            contract_id: Contract ID for this usage data
        """
        if not usage_data:
            _LOGGER.warning("No monthly usage data to update")
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
            "Updated monthly usage cache: added %d new records, total %d records",
            len(new_entries),
            len(self.data["usage"])
        )

    def get_usage(self) -> list[dict[str, Any]]:
        """Get all cached monthly usage data.

        Returns:
            List of monthly usage records, sorted by timestamp (newest first)
        """
        return self.data.get("usage", [])

    def get_usage_for_month(self, year: int, month: int) -> dict[str, Any] | None:
        """Get monthly usage data for a specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            Monthly usage record for the specified month, or None if not found
        """
        usage = self.get_usage()

        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.year == year and timestamp.month == month:
                return entry

        return None

    def get_usage_for_year(self, year: int) -> list[dict[str, Any]]:
        """Get monthly usage data for a specific year.

        Args:
            year: Year (e.g., 2024)

        Returns:
            List of monthly usage records for the specified year
        """
        usage = self.get_usage()
        result = []

        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.year == year:
                result.append(entry)

        # Sort by month (January to December)
        result.sort(key=lambda x: x.get("startTime", ""))
        return result

    def get_latest_usage(self, months: int = 12) -> list[dict[str, Any]]:
        """Get the most recent N months of usage data.

        Args:
            months: Number of months to retrieve (default: 12)

        Returns:
            List of usage records from the last N months
        """
        usage = self.get_usage()
        # Approximate cutoff (months * 30 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

        return [
            entry for entry in usage
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

    def calculate_total_usage(self, months: int = 12) -> dict[str, float]:
        """Calculate total usage for the last N months.

        Args:
            months: Number of months to calculate (default: 12)

        Returns:
            Dictionary with total_kwh, total_paid_kwh, total_free_kwh
        """
        usage = self.get_latest_usage(months)

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

    def calculate_average_usage(self, months: int = 12) -> dict[str, float]:
        """Calculate average monthly usage for the last N months.

        Args:
            months: Number of months to calculate (default: 12)

        Returns:
            Dictionary with average_kwh, average_paid_kwh, average_free_kwh
        """
        usage = self.get_latest_usage(months)
        
        if not usage:
            return {
                "average_kwh": 0.0,
                "average_paid_kwh": 0.0,
                "average_free_kwh": 0.0,
            }

        totals = self.calculate_total_usage(months)
        count = len(usage)

        return {
            "average_kwh": totals["total_kwh"] / count,
            "average_paid_kwh": totals["total_paid_kwh"] / count,
            "average_free_kwh": totals["total_free_kwh"] / count,
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
