"""Hourly usage data manager for Contact Energy.

This module manages hourly usage data caching, including automatic pruning
of data older than the configured window.

Cache file: usage_hourly_{address}_{icp}.json
Staleness: Re-download if >1 hour since last download

Version: 2.0.0
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Any

from .base_cache import BaseCache

_LOGGER = logging.getLogger(__name__)

# Configuration constants
HOURLY_STALENESS_HOURS = 1  # Re-download if >1 hour since last download
HOURLY_WINDOW_DAYS = 7  # Keep 7 days of hourly data


class UsageHourlyDataManager(BaseCache):
    """Manager for hourly usage data caching.

    Handles caching of:
    - Hourly electricity usage (kWh)
    - Paid vs. free usage breakdown
    - Cost per hour
    - Timestamps and interval information

    Cache file: usage_hourly_{address}_{icp}.json
    Staleness: Re-download if >1 hour since last download OR last_data_timestamp >6 hours old
    Window: Keep last 7 days of data, prune older entries
    """

    def _get_cache_filename(self) -> str:
        """Return cache filename: usage_hourly_{address}_{icp}.json"""
        return f"usage_hourly_{self.address}_{self.icp}.json"

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create empty hourly usage cache structure."""
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

        Staleness rules:
        - No data exists: STALE
        - Last download >1 hour ago: STALE
        - Last data timestamp >6 hours ago: STALE (data is likely incomplete)
        - Otherwise: FRESH

        Returns:
            True if data needs refresh
        """
        # No data = stale
        if not self.data.get("usage"):
            _LOGGER.debug("Hourly usage data is stale: no data")
            return True

        # Check download timestamp
        hours_since_download = self.hours_since_last_download()
        if hours_since_download >= HOURLY_STALENESS_HOURS:
            _LOGGER.debug(
                "Hourly usage data is stale: %.1f hours since download (limit: %d)",
                hours_since_download,
                HOURLY_STALENESS_HOURS
            )
            return True

        # Check if last data point is too old (>6 hours)
        # This catches cases where API has new data but we haven't downloaded it
        last_data = self.get_last_data_timestamp()
        if last_data:
            hours_since_data = (datetime.now(timezone.utc) - last_data).total_seconds() / 3600
            if hours_since_data > 6:
                _LOGGER.debug(
                    "Hourly usage data is stale: last data is %.1f hours old",
                    hours_since_data
                )
                return True

        _LOGGER.debug("Hourly usage data is fresh: %.1f hours since download", hours_since_download)
        return False

    def prune(self) -> None:
        """Remove hourly data older than the configured window.

        Keeps only the last HOURLY_WINDOW_DAYS days of data.
        """
        if not self.data.get("usage"):
            return

        # Calculate cutoff date
        cutoff = datetime.now(timezone.utc) - timedelta(days=HOURLY_WINDOW_DAYS)
        initial_count = len(self.data["usage"])

        # Filter out old data
        self.data["usage"] = [
            entry for entry in self.data["usage"]
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

        pruned_count = initial_count - len(self.data["usage"])
        if pruned_count > 0:
            _LOGGER.info(
                "Pruned %d hourly usage records older than %d days",
                pruned_count,
                HOURLY_WINDOW_DAYS
            )

    def update(self, usage_data: list[dict[str, Any]], contract_id: str) -> None:
        """Update cache with new hourly usage data.

        Merges new data with existing data, removing duplicates based on startTime.
        Updates metadata timestamps.

        Args:
            usage_data: List of hourly usage records from API
            contract_id: Contract ID for this usage data
        """
        if not usage_data:
            _LOGGER.warning("No hourly usage data to update")
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
            "Updated hourly usage cache: added %d new records, total %d records",
            len(new_entries),
            len(self.data["usage"])
        )

    def get_usage(self) -> list[dict[str, Any]]:
        """Get all cached hourly usage data.

        Returns:
            List of hourly usage records, sorted by timestamp (newest first)
        """
        return self.data.get("usage", [])

    def get_usage_for_date(self, target_date: date) -> list[dict[str, Any]]:
        """Get hourly usage data for a specific date.

        Args:
            target_date: Date to retrieve usage for

        Returns:
            List of hourly usage records for the specified date
        """
        usage = self.get_usage()
        result = []

        for entry in usage:
            timestamp = self._parse_timestamp(entry.get("startTime"))
            if timestamp and timestamp.date() == target_date:
                result.append(entry)

        return result

    def get_latest_usage(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get the most recent N hours of usage data.

        Args:
            hours: Number of hours to retrieve (default: 24)

        Returns:
            List of usage records from the last N hours
        """
        usage = self.get_usage()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        return [
            entry for entry in usage
            if self._parse_timestamp(entry.get("startTime")) > cutoff
        ]

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
