"""Base cache class for Contact Energy data managers.

This module provides an abstract base class for all data caching operations,
including JSON file I/O, metadata tracking, and staleness checking.

Version: 2.0.0
"""
from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


class BaseCache(ABC):
    """Abstract base class for all cache managers.

    This class provides common functionality for:
    - Loading and saving JSON cache files
    - Atomic file operations
    - Metadata tracking (last_download, last_data_timestamp)
    - Staleness checking based on configurable rules
    - Thread-safe file operations

    Subclasses must implement:
    - _get_cache_filename(): Return the cache filename
    - _create_empty_cache(): Return an empty cache structure
    - is_stale(): Determine if data needs refresh
    - prune(): Remove old data outside the window
    """

    # Class-level locks dictionary for thread-safe operations
    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, address: str, icp: str, cache_dir: Optional[Path] = None):
        """Initialize cache manager.

        Args:
            address: Sanitized address (e.g., "71_oroua_st")
            icp: ICP number (e.g., "00000000561")
            cache_dir: Directory for cache files (defaults to component data dir)
        """
        self.address = address
        self.icp = icp

        # Determine cache directory
        if cache_dir is None:
            component_dir = Path(__file__).parent.parent
            self.cache_dir = component_dir / "data"
        else:
            self.cache_dir = Path(cache_dir)

        # Build cache file path
        filename = self._get_cache_filename()
        self.cache_path = self.cache_dir / filename

        # Initialize in-memory cache
        self.data: dict[str, Any] = self._create_empty_cache()

        # Get or create lock for this cache file
        lock_key = str(self.cache_path)
        if lock_key not in BaseCache._locks:
            BaseCache._locks[lock_key] = asyncio.Lock()
        self._save_lock = BaseCache._locks[lock_key]

        _LOGGER.debug(
            "Cache initialized: %s (address=%s, icp=%s)",
            filename,
            address,
            icp
        )

    @abstractmethod
    def _get_cache_filename(self) -> str:
        """Return the cache filename for this data type.

        Returns:
            Cache filename (e.g., "usage_hourly_71_oroua_st_00000000561.json")
        """
        pass

    @abstractmethod
    def _create_empty_cache(self) -> dict[str, Any]:
        """Create and return an empty cache structure with metadata.

        Returns:
            Dictionary with empty cache structure including metadata
        """
        pass

    @abstractmethod
    def is_stale(self) -> bool:
        """Check if cached data is stale and needs refresh.

        Each data type implements its own staleness rules.

        Returns:
            True if data needs refresh, False otherwise
        """
        pass

    @abstractmethod
    def prune(self) -> None:
        """Remove old data outside the configured window.

        Each data type implements its own pruning logic.
        """
        pass

    async def load(self) -> bool:
        """Load cache from disk.

        Returns:
            True if cache was loaded successfully, False otherwise
        """
        if not self.cache_path.exists():
            _LOGGER.debug("Cache file does not exist: %s", self.cache_path)
            return False

        def _read() -> dict[str, Any]:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                return json.load(handle)

        try:
            loop = asyncio.get_event_loop()
            self.data = await loop.run_in_executor(None, _read)
            _LOGGER.info("Loaded cache from %s", self.cache_path.name)
            return True
        except json.JSONDecodeError as err:
            _LOGGER.error("Cache file is corrupted: %s - %s", self.cache_path, err)
            self.data = self._create_empty_cache()
            return False
        except Exception as err:
            _LOGGER.error("Failed to load cache: %s - %s", self.cache_path, err)
            self.data = self._create_empty_cache()
            return False

    async def save(self) -> bool:
        """Save cache to disk atomically.

        Uses atomic write (write to temp file, then rename) to prevent corruption.

        Returns:
            True if save was successful, False otherwise
        """
        async with self._save_lock:
            return await self._save_locked()

    async def _save_locked(self) -> bool:
        """Internal save method (assumes lock is held)."""
        # Ensure directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Update metadata timestamp
        if "metadata" in self.data:
            self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()

        # Write to temporary file first
        temp_path = self.cache_path.with_suffix(".tmp")

        def _write() -> None:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2, ensure_ascii=False)
            # Atomic rename
            temp_path.replace(self.cache_path)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _write)
            _LOGGER.debug("Saved cache to %s", self.cache_path.name)
            return True
        except Exception as err:
            _LOGGER.error("Failed to save cache: %s - %s", self.cache_path, err)
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            return False

    def get_metadata(self) -> dict[str, Any]:
        """Get cache metadata.

        Returns:
            Dictionary containing metadata (version, timestamps, etc.)
        """
        return self.data.get("metadata", {})

    def get_last_download(self) -> Optional[datetime]:
        """Get timestamp of last download.

        Returns:
            Datetime of last download, or None if never downloaded
        """
        last_download = self.get_metadata().get("last_download")
        if last_download:
            try:
                return datetime.fromisoformat(last_download)
            except (ValueError, TypeError):
                return None
        return None

    def get_last_data_timestamp(self) -> Optional[datetime]:
        """Get timestamp of most recent data point.

        Returns:
            Datetime of most recent data, or None if no data
        """
        last_timestamp = self.get_metadata().get("last_data_timestamp")
        if last_timestamp:
            try:
                return datetime.fromisoformat(last_timestamp)
            except (ValueError, TypeError):
                return None
        return None

    def set_last_data_timestamp(self, timestamp: datetime) -> None:
        """Set timestamp of most recent data point.

        Args:
            timestamp: Datetime of most recent data
        """
        if "metadata" not in self.data:
            self.data["metadata"] = {}
        self.data["metadata"]["last_data_timestamp"] = timestamp.isoformat()

    def hours_since_last_download(self) -> float:
        """Calculate hours since last download.

        Returns:
            Hours since last download, or float('inf') if never downloaded
        """
        last_download = self.get_last_download()
        if not last_download:
            return float('inf')
        elapsed = datetime.now(timezone.utc) - last_download
        return elapsed.total_seconds() / 3600
