"""Usage data cache management for Contact Energy integration.

This module provides the UsageCache class which handles persistent storage
of usage data (hourly, daily, monthly) for Contact Energy contracts. It manages:
- Loading and saving usage data from/to JSON files on disk
- Incremental updates with metadata tracking
- Automatic pruning to maintain fixed time windows
- Atomic file operations to prevent corruption

Cache files are stored in: custom_components/contact_energy/data/
File naming: usage_cache_{contract_id}.json

Architecture:
- One cache file per contract
- Separate sections for hourly, daily, monthly data
- Metadata tracks sync times and date ranges
- Atomic writes prevent partial/corrupted saves

Version: 1.4.0
Author: Contact Energy Integration
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


class UsageCache:
    """Manages persistent storage of usage data for a single contract.

    This class handles all disk I/O operations for usage data caching,
    including metadata tracking, incremental updates, and pruning logic.
    All file operations are atomic to prevent data corruption.

    The cache structure maintains three separate time-series datasets:
    - Hourly: 24 records per day, typically last 9 days
    - Daily: 1 record per day, typically last 35 days
    - Monthly: 1 record per month, typically last 18 months

    Attributes:
        contract_id (str): Unique contract identifier
        cache_dir (Path): Directory containing cache files
        cache_path (Path): Full path to this contract's cache file
        data (dict): In-memory cache data structure

    Example:
        cache = UsageCache("123456")
        await cache.load()
        cache.update_daily(new_data)
        cache.prune_daily(window_days=35)
        await cache.save()
    """
    
    # Class-level dictionary of locks, one per contract ID
    # Shared across all UsageCache instances to prevent concurrent saves
    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, contract_id: str, cache_dir: Optional[Path] = None):
        """Initialize cache manager for a specific contract.

        Args:
            contract_id: Contract identifier (e.g., "123456")
            cache_dir: Directory for cache files (defaults to component data dir)

        Note: Does not load cache immediately. Call load() separately.
        """
        self.contract_id = contract_id

        # Determine cache directory (default to component's data/ subdirectory)
        if cache_dir is None:
            # Get the directory containing this module
            component_dir = Path(__file__).parent
            self.cache_dir = component_dir / "data"
        else:
            self.cache_dir = Path(cache_dir)

        # Build cache file path: data/usage_cache_{contract_id}.json
        self.cache_path = self.cache_dir / f"usage_cache_{contract_id}.json"

        # Initialize empty data structure
        # This will be populated by load() or remain empty for new cache
        self.data: dict[str, Any] = self._create_empty_cache()

        # Get or create shared lock for this contract ID
        # All UsageCache instances for the same contract share this lock
        if contract_id not in UsageCache._locks:
            UsageCache._locks[contract_id] = asyncio.Lock()
        self._save_lock = UsageCache._locks[contract_id]

        _LOGGER.debug(
            "UsageCache initialized for contract %s: cache_path=%s",
            contract_id, self.cache_path
        )

    def _create_empty_cache(self) -> dict[str, Any]:
        """Create an empty cache structure with metadata.

        Returns:
            Empty cache dictionary with initial metadata
        """
        return {
            "contract_id": self.contract_id,
            "metadata": {
                "version": "1.4.0",
                "created": datetime.now(timezone.utc).isoformat(),
                "last_synced": None,
                "cumulative": {
                    "paid_kwh": 0.0,
                    "free_kwh": 0.0,
                },
                "energy_sensor": {
                    "start_date": None,
                },
                "hourly": {
                    "from": None,
                    "to": None,
                    "record_count": 0
                },
                "daily": {
                    "from": None,
                    "to": None,
                    "record_count": 0
                },
                "monthly": {
                    "from": None,
                    "to": None,
                    "record_count": 0
                }
            },
            "hourly": {},
            "daily": {},
            "monthly": {}
        }

    async def load(self) -> bool:
        """Load cache from disk if it exists.

        Reads the JSON cache file and populates self.data. If the file doesn't
        exist, initializes with an empty cache structure. Handles corrupted
        JSON gracefully by logging error and starting fresh.

        Returns:
            bool: True if cache was loaded from disk, False if starting fresh

        Note: Always succeeds - creates new cache if load fails
        """
        start_time = time.time()

        _LOGGER.debug("Loading cache for contract %s from %s", self.contract_id, self.cache_path)

        # Check if cache file exists
        if not self.cache_path.exists():
            _LOGGER.info(
                "No existing cache found for contract %s at %s. Starting with empty cache.",
                self.contract_id, self.cache_path
            )
            self.data = self._create_empty_cache()
            return False

        try:
            # Read cache file
            # Use synchronous read in executor to avoid blocking event loop
            def _read_cache():
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            import asyncio
            loop = asyncio.get_event_loop()
            self.data = await loop.run_in_executor(None, _read_cache)

            # Validate basic structure
            if not isinstance(self.data, dict):
                raise ValueError("Cache file does not contain a dictionary")

            if "metadata" not in self.data:
                raise ValueError("Cache file missing 'metadata' section")

            # Ensure cumulative metadata exists for newer features
            self._ensure_cumulative_metadata()

            # Log cache statistics
            metadata = self.data.get("metadata", {})
            last_synced = metadata.get("last_synced", "never")
            hourly_count = len(self.data.get("hourly", {}))
            daily_count = len(self.data.get("daily", {}))
            monthly_count = len(self.data.get("monthly", {}))

            elapsed = time.time() - start_time

            _LOGGER.info(
                "Loaded cache for contract %s: last_synced=%s, "
                "records=(hourly=%d, daily=%d, monthly=%d) in %.3f seconds",
                self.contract_id, last_synced,
                hourly_count, daily_count, monthly_count, elapsed
            )

            return True

        except json.JSONDecodeError as e:
            # Handle corrupted JSON
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Corrupted cache file for contract %s at %s: %s. "
                "Creating new cache. (Loaded in %.3f seconds)",
                self.contract_id, self.cache_path, str(e), elapsed
            )
            self.data = self._create_empty_cache()
            return False

        except (ValueError, KeyError) as e:
            # Handle invalid cache structure
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Invalid cache structure for contract %s: %s. "
                "Creating new cache. (Loaded in %.3f seconds)",
                self.contract_id, str(e), elapsed
            )
            self.data = self._create_empty_cache()
            return False

        except Exception as e:
            # Handle unexpected errors
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Unexpected error loading cache for contract %s: %s. "
                "Creating new cache. (Loaded in %.3f seconds)",
                self.contract_id, str(e), elapsed, exc_info=True
            )
            self.data = self._create_empty_cache()
            return False

    async def save(self) -> None:
        """Save cache to disk atomically.

        Writes cache data to a temporary file, then renames it to the actual
        cache file. This ensures the cache file is never partially written
        or corrupted, even if the process is interrupted.

        Updates metadata (last_synced, record counts, date ranges) before saving.
        Protected by asyncio lock to prevent concurrent writes from multiple sensors.

        Raises:
            OSError: If unable to create directory or write file
        """
        async with self._save_lock:
            await self._do_save()

    async def _do_save(self) -> None:
        """Internal save implementation (called within lock)."""
        start_time = time.time()

        _LOGGER.debug("Saving cache for contract %s to %s", self.contract_id, self.cache_path)

        try:
            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Update metadata before saving
            self._update_metadata()

            # Create temporary file path (same directory for atomic rename)
            temp_path = self.cache_path.with_suffix(".tmp")

            # Write to temporary file first (atomic operation)
            # Use synchronous write in executor to avoid blocking event loop
            def _write_cache():
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
                # Atomically rename temp file to actual cache file
                temp_path.replace(self.cache_path)
            
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _write_cache)

            elapsed = time.time() - start_time

            # Log save statistics
            hourly_count = len(self.data.get("hourly", {}))
            daily_count = len(self.data.get("daily", {}))
            monthly_count = len(self.data.get("monthly", {}))

            _LOGGER.info(
                "Saved cache for contract %s: records=(hourly=%d, daily=%d, monthly=%d) "
                "in %.3f seconds",
                self.contract_id, hourly_count, daily_count, monthly_count, elapsed
            )

        except OSError as e:
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Failed to save cache for contract %s after %.3f seconds: %s",
                self.contract_id, elapsed, str(e), exc_info=True
            )
            raise

        except Exception as e:
            elapsed = time.time() - start_time
            _LOGGER.error(
                "Unexpected error saving cache for contract %s after %.3f seconds: %s",
                self.contract_id, elapsed, str(e), exc_info=True
            )
            raise

    def _update_metadata(self) -> None:
        """Update cache metadata with current state.

        Recalculates:
        - last_synced timestamp
        - record counts for each interval
        - date ranges (from/to) for each interval
        """
        metadata = self.data["metadata"]
        cumulative = self._ensure_cumulative_metadata()

        # Update sync timestamp
        metadata["last_synced"] = datetime.now(timezone.utc).isoformat()

        # Update hourly metadata
        hourly_records = self.data.get("hourly", {})
        if hourly_records:
            hourly_dates = sorted(hourly_records.keys())
            metadata["hourly"]["from"] = hourly_dates[0][:10]  # Extract YYYY-MM-DD
            metadata["hourly"]["to"] = hourly_dates[-1][:10]
            metadata["hourly"]["record_count"] = len(hourly_records)
        else:
            metadata["hourly"]["from"] = None
            metadata["hourly"]["to"] = None
            metadata["hourly"]["record_count"] = 0

        # Update daily metadata
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

        # Update monthly metadata
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

        _LOGGER.debug(
            "Updated metadata for contract %s: hourly=(%s to %s, %d records), "
            "daily=(%s to %s, %d records), monthly=(%s to %s, %d records), "
            "cumulative_paid=%.3f, cumulative_free=%.3f",
            self.contract_id,
            metadata["hourly"]["from"], metadata["hourly"]["to"], metadata["hourly"]["record_count"],
            metadata["daily"]["from"], metadata["daily"]["to"], metadata["daily"]["record_count"],
            metadata["monthly"]["from"], metadata["monthly"]["to"], metadata["monthly"]["record_count"],
            cumulative.get("paid_kwh", 0.0), cumulative.get("free_kwh", 0.0)
        )

    def update_hourly(self, records: list[dict[str, Any]]) -> int:
        """Add or update hourly usage records in cache.

        Merges new records with existing cache. If a record for the same
        timestamp already exists, it will be overwritten with the new data.

        Args:
            records: List of hourly records from API, each with 'timestamp' key

        Returns:
            int: Number of records added/updated
        """
        _LOGGER.debug("Updating hourly cache for contract %s with %d records", self.contract_id, len(records))

        count = 0
        for record in records:
            # Use timestamp as key (e.g., "2025-12-31T23:00:00+13:00")
            timestamp = record.get("timestamp")
            if timestamp:
                self.data["hourly"][timestamp] = record
                count += 1
            else:
                _LOGGER.warning("Hourly record missing timestamp for contract %s, skipping", self.contract_id)

        _LOGGER.debug("Updated %d hourly records for contract %s", count, self.contract_id)
        return count

    def update_daily(self, records: list[dict[str, Any]]) -> int:
        """Add or update daily usage records in cache.

        Merges new records with existing cache. Extracts date from timestamp
        and uses it as the key (YYYY-MM-DD format).

        Args:
            records: List of daily records from API, each with 'timestamp' key

        Returns:
            int: Number of records added/updated
        """
        _LOGGER.debug("Updating daily cache for contract %s with %d records", self.contract_id, len(records))

        count = 0
        for record in records:
            # Extract date portion from timestamp (YYYY-MM-DD)
            timestamp = record.get("timestamp")
            if timestamp:
                # Extract just the date part (first 10 chars: YYYY-MM-DD)
                date_key = timestamp[:10]
                self.data["daily"][date_key] = record
                count += 1
            else:
                _LOGGER.warning("Daily record missing timestamp for contract %s, skipping", self.contract_id)

        _LOGGER.debug("Updated %d daily records for contract %s", count, self.contract_id)
        return count

    def update_monthly(self, records: list[dict[str, Any]]) -> int:
        """Add or update monthly usage records in cache.

        Merges new records with existing cache. Extracts year-month from
        timestamp and uses it as the key (YYYY-MM format).

        Args:
            records: List of monthly records from API, each with 'timestamp' key

        Returns:
            int: Number of records added/updated
        """
        _LOGGER.debug("Updating monthly cache for contract %s with %d records", self.contract_id, len(records))

        count = 0
        for record in records:
            # Extract year-month portion from timestamp (YYYY-MM)
            timestamp = record.get("timestamp")
            if timestamp:
                # Extract just the year-month part (first 7 chars: YYYY-MM)
                month_key = timestamp[:7]
                self.data["monthly"][month_key] = record
                count += 1
            else:
                _LOGGER.warning("Monthly record missing timestamp for contract %s, skipping", self.contract_id)

        _LOGGER.debug("Updated %d monthly records for contract %s", count, self.contract_id)
        return count

    def prune_hourly(self, window_days: int = 9) -> tuple[int, int]:
        """Remove hourly records older than the specified window.

        Keeps only the most recent window_days worth of hourly data.
        This prevents the cache from growing unbounded.

        Args:
            window_days: Number of days to keep (default: 9)

        Returns:
            tuple[int, int]: (records_before, records_after) for logging
        """
        before_count = len(self.data.get("hourly", {}))

        # Calculate cutoff date (today - window_days)
        cutoff_date = date.today() - timedelta(days=window_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        _LOGGER.debug(
            "Pruning hourly data for contract %s: keeping records >= %s (window=%d days)",
            self.contract_id, cutoff_str, window_days
        )

        # Filter records: keep only those >= cutoff date
        # Timestamp format: "2025-12-31T23:00:00+13:00"
        # Compare first 10 chars (YYYY-MM-DD) with cutoff
        self.data["hourly"] = {
            timestamp: record
            for timestamp, record in self.data.get("hourly", {}).items()
            if timestamp[:10] >= cutoff_str
        }

        after_count = len(self.data["hourly"])
        removed_count = before_count - after_count

        if removed_count > 0:
            _LOGGER.info(
                "Pruned %d old hourly records for contract %s (kept %d records)",
                removed_count, self.contract_id, after_count
            )
        else:
            _LOGGER.debug("No hourly records to prune for contract %s", self.contract_id)

        return (before_count, after_count)

    def prune_daily(self, window_days: int = 35) -> tuple[int, int]:
        """Remove daily records older than the specified window.

        Keeps only the most recent window_days worth of daily data.

        Args:
            window_days: Number of days to keep (default: 35)

        Returns:
            tuple[int, int]: (records_before, records_after) for logging
        """
        before_count = len(self.data.get("daily", {}))

        # Calculate cutoff date
        cutoff_date = date.today() - timedelta(days=window_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        _LOGGER.debug(
            "Pruning daily data for contract %s: keeping records >= %s (window=%d days)",
            self.contract_id, cutoff_str, window_days
        )

        # Filter records: keep only those >= cutoff date
        # Date key format: "2025-12-31"
        removed_paid = 0.0
        removed_free = 0.0
        filtered_daily: dict[str, Any] = {}

        for date_key, record in self.data.get("daily", {}).items():
            if date_key >= cutoff_str:
                filtered_daily[date_key] = record
            else:
                removed_paid += float(record.get("paid") or 0.0)
                removed_free += float(record.get("free") or 0.0)

        # Persist cumulative totals so pruning does not break total_increasing sensors
        if removed_paid or removed_free:
            cumulative = self._ensure_cumulative_metadata()
            cumulative["paid_kwh"] = round(cumulative.get("paid_kwh", 0.0) + removed_paid, 3)
            cumulative["free_kwh"] = round(cumulative.get("free_kwh", 0.0) + removed_free, 3)

        self.data["daily"] = filtered_daily

        after_count = len(self.data["daily"])
        removed_count = before_count - after_count

        if removed_count > 0:
            _LOGGER.info(
                "Pruned %d old daily records for contract %s (kept %d records)",
                removed_count, self.contract_id, after_count
            )
        else:
            _LOGGER.debug("No daily records to prune for contract %s", self.contract_id)

        return (before_count, after_count)

    def get_cumulative_totals(self, sensor_start_date: Optional[date] = None) -> dict[str, float]:
        """Get cumulative paid/free totals for energy sensors.

        Only counts energy consumed on or after the sensor_start_date to prevent
        historical data from appearing as a spike in the Energy Dashboard.

        Args:
            sensor_start_date: Only count records from this date forward.
                              If None, counts all records (legacy behavior).

        Returns:
            dict: Mapping with 'paid' and 'free' cumulative kWh totals.
        """
        cumulative = self._ensure_cumulative_metadata()

        baseline_paid = float(cumulative.get("paid_kwh") or 0.0)
        baseline_free = float(cumulative.get("free_kwh") or 0.0)

        paid_sum = 0.0
        free_sum = 0.0

        # Only sum daily records on or after sensor start date
        for date_str, record in self.data.get("daily", {}).items():
            if sensor_start_date is not None:
                record_date = date.fromisoformat(date_str)
                if record_date < sensor_start_date:
                    continue
            paid_sum += float(record.get("paid") or 0.0)
            free_sum += float(record.get("free") or 0.0)

        return {
            "paid": round(baseline_paid + paid_sum, 3),
            "free": round(baseline_free + free_sum, 3),
        }

    def _ensure_cumulative_metadata(self) -> dict[str, float]:
        """Ensure cumulative metadata exists and return it."""
        metadata = self.data.setdefault("metadata", {})
        return metadata.setdefault("cumulative", {"paid_kwh": 0.0, "free_kwh": 0.0})

    def get_energy_sensor_start_date(self) -> Optional[date]:
        """Get the energy sensor start date from cache metadata.

        Returns:
            date: The date when energy sensor tracking began, or None if not set.
        """
        metadata = self.data.get("metadata", {})
        energy_sensor = metadata.get("energy_sensor", {})
        start_date_str = energy_sensor.get("start_date")
        if start_date_str:
            return date.fromisoformat(start_date_str)
        return None

    def set_energy_sensor_start_date(self, start_date: date) -> None:
        """Set the energy sensor start date in cache metadata.

        Args:
            start_date: The date when energy sensor tracking should begin.
        """
        metadata = self.data.setdefault("metadata", {})
        energy_sensor = metadata.setdefault("energy_sensor", {})
        energy_sensor["start_date"] = start_date.isoformat()

    def prune_monthly(self, window_months: int = 18) -> tuple[int, int]:
        """Remove monthly records older than the specified window.

        Keeps only the most recent window_months worth of monthly data.

        Args:
            window_months: Number of months to keep (default: 18)

        Returns:
            tuple[int, int]: (records_before, records_after) for logging
        """
        before_count = len(self.data.get("monthly", {}))

        # Calculate cutoff month (approximate: window_months * 30 days ago)
        cutoff_date = date.today() - timedelta(days=window_months * 30)
        cutoff_str = cutoff_date.strftime("%Y-%m")

        _LOGGER.debug(
            "Pruning monthly data for contract %s: keeping records >= %s (window=%d months)",
            self.contract_id, cutoff_str, window_months
        )

        # Filter records: keep only those >= cutoff month
        # Month key format: "2025-12"
        self.data["monthly"] = {
            month_key: record
            for month_key, record in self.data.get("monthly", {}).items()
            if month_key >= cutoff_str
        }

        after_count = len(self.data["monthly"])
        removed_count = before_count - after_count

        if removed_count > 0:
            _LOGGER.info(
                "Pruned %d old monthly records for contract %s (kept %d records)",
                removed_count, self.contract_id, after_count
            )
        else:
            _LOGGER.debug("No monthly records to prune for contract %s", self.contract_id)

        return (before_count, after_count)

    def get_hourly_range(self) -> tuple[Optional[date], Optional[date]]:
        """Get the date range of cached hourly data.

        Returns:
            tuple: (from_date, to_date) or (None, None) if no data
        """
        metadata = self.data.get("metadata", {}).get("hourly", {})
        from_str = metadata.get("from")
        to_str = metadata.get("to")

        if from_str and to_str:
            from_date = date.fromisoformat(from_str)
            to_date = date.fromisoformat(to_str)
            return (from_date, to_date)

        return (None, None)

    def get_daily_range(self) -> tuple[Optional[date], Optional[date]]:
        """Get the date range of cached daily data.

        Returns:
            tuple: (from_date, to_date) or (None, None) if no data
        """
        metadata = self.data.get("metadata", {}).get("daily", {})
        from_str = metadata.get("from")
        to_str = metadata.get("to")

        if from_str and to_str:
            from_date = date.fromisoformat(from_str)
            to_date = date.fromisoformat(to_str)
            return (from_date, to_date)

        return (None, None)

    def get_monthly_range(self) -> tuple[Optional[date], Optional[date]]:
        """Get the date range of cached monthly data.

        Returns:
            tuple: (from_date, to_date) or (None, None) if no data
        """
        metadata = self.data.get("metadata", {}).get("monthly", {})
        from_str = metadata.get("from")
        to_str = metadata.get("to")

        if from_str and to_str:
            # Monthly format is YYYY-MM, convert to first day of month
            from_date = date.fromisoformat(from_str + "-01")
            to_date = date.fromisoformat(to_str + "-01")
            return (from_date, to_date)

        return (None, None)

    def get_last_synced(self) -> Optional[datetime]:
        """Get the timestamp of the last successful sync.

        Returns:
            datetime: Last sync time in UTC, or None if never synced
        """
        last_synced_str = self.data.get("metadata", {}).get("last_synced")
        if last_synced_str:
            return datetime.fromisoformat(last_synced_str)
        return None
