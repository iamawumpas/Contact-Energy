"""Base cache class for Contact Energy data managers.

=== WHAT THIS DOES ===
This module provides the shared foundation for every cache manager in the
integration. It handles the common jobs that all cache files need, such as:
- deciding where a cache file lives on disk
- loading saved data from a JSON file
- saving updated data back to a JSON file
- tracking metadata such as when data was last downloaded
- checking timestamps that other classes use to decide when data is old
- preventing two save operations from writing to the same file at once

=== FOR NON-CODERS ===
A "cache" is a saved copy of information so the program does not have to ask
Contact Energy for the same information every single time. That makes things
faster and reduces unnecessary network requests.

A "JSON" file is a plain-text file format used to store structured information.
You can think of it like a labeled storage box where each label has a value.

The "file system" means the folders and files on the computer.

"Serialization" means converting live in-memory data into a format that can be
stored in a file. In this module, serialization means converting Python data
into JSON text before writing it to disk.

Version: 2.0.0
"""

# This line lets us use newer style type hints while still supporting older
# Python behavior. It does not change runtime logic for users.
from __future__ import annotations

# ============================================================================
# IMPORTS
# ============================================================================

# asyncio: Python's built-in toolkit for asynchronous work. We use it for locks
# and for running file work without blocking the rest of Home Assistant.
import asyncio

# json: Converts Python dictionaries/lists to JSON text and back again.
# This is how cache data is stored in files.
import json

# logging: Records what the code is doing so developers can troubleshoot issues.
import logging

# ABC and abstractmethod: Tools for creating a base class that defines required
# methods. Subclasses must fill in the pieces specific to each data type.
from abc import ABC, abstractmethod

# datetime/timezone: Used for timestamps such as "when did we last download?".
# timedelta is imported because some subclasses use this concept and the base
# module describes time-window logic shared by all cache managers.
from datetime import datetime, timezone, timedelta

# Path: A safer, clearer way to work with file and folder paths.
from pathlib import Path

# Any and Optional: Type-hint helpers. "Any" means data can be any shape,
# and "Optional" means a value may either exist or be None.
from typing import Any, Optional

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Create a logger tied to this file so messages can be traced back here.
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# BASE CACHE CLASS
# ============================================================================

class BaseCache(ABC):
    """Abstract base class for all cache managers.

    === WHAT THIS DOES ===
    This class centralizes the repeated cache behavior used by multiple data
    managers. Instead of each manager re-implementing file loading, saving,
    metadata handling, and lock management, they all inherit from this class.

    === FOR NON-CODERS ===
    Think of this as a standard template used by several departments.
    Each department stores different information, but they all follow the same
    filing rules: where to keep files, how to label them, and how to avoid two
    people writing to the same file at the same time.

    Subclasses must provide:
    - a filename for their cache file
    - an empty starter data structure
    - rules for deciding when their data is stale
    - rules for pruning old data
    """

    # This shared dictionary stores one lock per cache file path.
    # A lock is like a "busy" sign on a filing cabinet. If one part of the
    # program is saving a file, another part waits its turn.
    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, address: str, icp: str, cache_dir: Optional[Path] = None):
        """Initialize cache manager.

        === WHAT THIS DOES ===
        This constructor sets up the cache manager with identifiers for the
        account/location, determines where the cache file should live, creates
        an empty in-memory data structure, and prepares a shared file lock.

        === FOR NON-CODERS ===
        This is like setting up a new filing cabinet record:
        1. label it with the customer's address and ICP number
        2. decide which room the cabinet belongs in
        3. create an empty folder for future paperwork
        4. add a rule so only one person can update that folder at a time

        Args:
            address: Sanitized address string used in cache filenames.
            icp: ICP number identifying the connection point.
            cache_dir: Optional custom folder for cache files.
        """
        # Save the identifiers on the object so other methods can reuse them.
        self.address = address
        self.icp = icp

        # ====================================================================
        # DECIDE WHICH FOLDER SHOULD HOLD CACHE FILES
        # ====================================================================
        # If no custom folder was supplied, use the integration's built-in data
        # folder. Otherwise, convert the provided value into a Path object.
        if cache_dir is None:
            # __file__ is the current file's location. parent.parent moves up to
            # the component folder so we can place data in ".../data".
            component_dir = Path(__file__).parent.parent
            self.cache_dir = component_dir / "data"
        else:
            self.cache_dir = Path(cache_dir)

        # ====================================================================
        # BUILD THE FULL CACHE FILE PATH
        # ====================================================================
        # Ask the subclass what filename it wants, then combine that filename
        # with the chosen folder to create the final file path.
        filename = self._get_cache_filename()
        self.cache_path = self.cache_dir / filename

        # ====================================================================
        # CREATE THE IN-MEMORY CACHE STRUCTURE
        # ====================================================================
        # self.data is the live working copy stored in memory while Home
        # Assistant is running. It starts empty until a file is loaded or fresh
        # data is written into it.
        self.data: dict[str, Any] = self._create_empty_cache()

        # ====================================================================
        # GET OR CREATE A SHARED SAVE LOCK FOR THIS EXACT FILE
        # ====================================================================
        # We use the file path string as a unique key. If two objects point at
        # the same file, they should also share the same lock.
        lock_key = str(self.cache_path)

        # If no lock exists yet for this file, create one now.
        if lock_key not in BaseCache._locks:
            BaseCache._locks[lock_key] = asyncio.Lock()

        # Save the lock on this object for future save operations.
        self._save_lock = BaseCache._locks[lock_key]

        # Record that setup finished successfully.
        _LOGGER.debug(
            "Cache initialized: %s (address=%s, icp=%s)",
            filename,
            address,
            icp,
        )

    @abstractmethod
    def _get_cache_filename(self) -> str:
        """Return the cache filename for this data type.

        === WHAT THIS DOES ===
        Forces each subclass to define the exact filename pattern it wants.

        === FOR NON-CODERS ===
        Different kinds of data need differently named folders/files so they do
        not get mixed up.

        Returns:
            The filename to use for this cache type.
        """
        pass

    @abstractmethod
    def _create_empty_cache(self) -> dict[str, Any]:
        """Create and return an empty cache structure with metadata.

        === WHAT THIS DOES ===
        Requires subclasses to define the starter shape of their cache data.

        === FOR NON-CODERS ===
        Before putting papers into a file, we decide what sections the file
        should have. This method defines that blank folder layout.

        Returns:
            A dictionary representing an empty cache.
        """
        pass

    @abstractmethod
    def is_stale(self) -> bool:
        """Check if cached data is stale and needs refresh.

        === WHAT THIS DOES ===
        Requires each subclass to define when its saved data should be
        considered too old to trust.

        === FOR NON-CODERS ===
        Some information goes out of date quickly, some slowly. This method is
        the rulebook for deciding when we should fetch fresh data.

        Returns:
            True if the cache should be refreshed, otherwise False.
        """
        pass

    @abstractmethod
    def prune(self) -> None:
        """Remove old data outside the configured window.

        === WHAT THIS DOES ===
        Requires subclasses to define how they clean out old records.

        === FOR NON-CODERS ===
        This is like cleaning out outdated paperwork so the file only keeps the
        time period we care about.
        """
        pass

    async def load(self) -> bool:
        """Load cache from disk.

        === WHAT THIS DOES ===
        This method checks whether the cache file exists, reads JSON from disk,
        converts it back into Python data, and stores it in memory.

        === FOR NON-CODERS ===
        This is the "open the filing cabinet and read the saved paperwork"
        step. If the paperwork is damaged or missing, we fall back to a fresh,
        empty folder instead of crashing.

        Returns:
            True if loading succeeded, otherwise False.
        """
        # ====================================================================
        # STEP 1: CHECK WHETHER THE CACHE FILE EXISTS
        # ====================================================================
        # If the file does not exist, there is nothing to load yet.
        if not self.cache_path.exists():
            _LOGGER.debug("Cache file does not exist: %s", self.cache_path)
            return False

        # ====================================================================
        # STEP 2: PREPARE A SMALL HELPER THAT READS THE FILE
        # ====================================================================
        # We place the actual file reading code inside a nested function so it
        # can be handed to a background thread executor.
        def _read() -> dict[str, Any]:
            # open(..., "r") means "open for reading".
            # encoding="utf-8" tells Python how to interpret the text.
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                # json.load reads JSON text from the file and turns it back into
                # Python data structures such as dictionaries and lists.
                return json.load(handle)

        try:
            # =================================================================
            # STEP 3: RUN FILE I/O IN AN EXECUTOR
            # =================================================================
            # File reading can block, so we ask the event loop to run it in a
            # worker thread. That lets the rest of the async system keep moving.
            loop = asyncio.get_event_loop()
            self.data = await loop.run_in_executor(None, _read)

            # Record success for debugging.
            _LOGGER.info("Loaded cache from %s", self.cache_path.name)

            # Return True to tell the caller the load succeeded.
            return True
        except json.JSONDecodeError as err:
            # ================================================================
            # HANDLE CORRUPTED JSON CONTENT
            # ================================================================
            # This error means the file exists, but its text is not valid JSON.
            # Instead of keeping broken data, reset to a clean empty structure.
            _LOGGER.error("Cache file is corrupted: %s - %s", self.cache_path, err)
            self.data = self._create_empty_cache()
            return False
        except Exception as err:
            # ================================================================
            # HANDLE ANY OTHER READ FAILURE
            # ================================================================
            # Examples: permission issues, disk problems, or unexpected file
            # content problems. We recover by resetting to an empty cache.
            _LOGGER.error("Failed to load cache: %s - %s", self.cache_path, err)
            self.data = self._create_empty_cache()
            return False

    async def save(self) -> bool:
        """Save cache to disk atomically.

        === WHAT THIS DOES ===
        This method wraps the actual save operation in a lock so only one save
        can happen at a time for the same cache file.

        === FOR NON-CODERS ===
        "Atomically" means we try to make the save appear as one clean action.
        Either the file is updated successfully, or the previous version stays
        in place. This reduces the chance of ending up with a half-written file.

        Returns:
            True if saving succeeded, otherwise False.
        """
        # Wait for exclusive access to this file's save operation.
        async with self._save_lock:
            # Once we hold the lock, hand off to the internal save routine.
            return await self._save_locked()

    async def _save_locked(self) -> bool:
        """Internal save method that assumes the lock is already held.

        === WHAT THIS DOES ===
        Creates the folder if needed, updates metadata, writes JSON to a
        temporary file, then replaces the real cache file with the temporary one.

        === FOR NON-CODERS ===
        This is like writing the new paperwork on a spare sheet first, then
        swapping it into the folder only when the full sheet is ready.

        Returns:
            True if the save finished successfully, otherwise False.
        """
        # ====================================================================
        # STEP 1: MAKE SURE THE CACHE FOLDER EXISTS
        # ====================================================================
        # parents=True means Python can create missing parent folders too.
        # exist_ok=True means "do not error if the folder already exists".
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # ====================================================================
        # STEP 2: UPDATE THE "LAST DOWNLOADED" METADATA
        # ====================================================================
        # We only do this if the data structure has a metadata section.
        if "metadata" in self.data:
            # isoformat turns the datetime into a standard text timestamp that
            # is easy to store in JSON and easy to parse later.
            self.data["metadata"]["last_download"] = datetime.now(timezone.utc).isoformat()

        # ====================================================================
        # STEP 3: CHOOSE A TEMPORARY FILE PATH
        # ====================================================================
        # with_suffix(".tmp") changes the current file extension to .tmp.
        # Example: data.json -> data.tmp
        temp_path = self.cache_path.with_suffix(".tmp")

        # ====================================================================
        # STEP 4: PREPARE THE FILE-WRITING HELPER
        # ====================================================================
        def _write() -> None:
            # Open the temporary file for writing text.
            with open(temp_path, "w", encoding="utf-8") as handle:
                # json.dump serializes self.data into JSON text and writes it.
                # indent=2 makes the file easier for humans to read.
                # ensure_ascii=False preserves readable non-English characters.
                json.dump(self.data, handle, indent=2, ensure_ascii=False)

            # Replace the real cache file with the finished temporary file.
            # This rename step is the atomic part of the save process.
            temp_path.replace(self.cache_path)

        try:
            # Run blocking file I/O in a background executor thread.
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _write)

            # Log success so future troubleshooting can see saves occurred.
            _LOGGER.debug("Saved cache to %s", self.cache_path.name)

            # Return True because the save completed successfully.
            return True
        except Exception as err:
            # Log the failure so developers know what went wrong.
            _LOGGER.error("Failed to save cache: %s - %s", self.cache_path, err)

            # If a temporary file was left behind, remove it so it does not
            # clutter the data folder or confuse future operations.
            if temp_path.exists():
                temp_path.unlink()

            # Return False to signal that saving failed.
            return False

    def get_metadata(self) -> dict[str, Any]:
        """Get cache metadata.

        === WHAT THIS DOES ===
        Returns the metadata section from the in-memory cache.

        === FOR NON-CODERS ===
        Metadata is "information about the information". For example, it stores
        when the data was downloaded, not the customer usage data itself.

        Returns:
            The metadata dictionary, or an empty dictionary if missing.
        """
        # Safely fetch the metadata section. If it is missing, return an empty
        # dictionary so callers always get a predictable result.
        return self.data.get("metadata", {})

    def get_last_download(self) -> Optional[datetime]:
        """Get timestamp of last download.

        === WHAT THIS DOES ===
        Reads the saved text timestamp from metadata and converts it back into a
        datetime object that Python can compare and calculate with.

        === FOR NON-CODERS ===
        When dates are saved into JSON, they must be stored as text because JSON
        does not have a native "datetime" type. This method converts that text
        back into a real time value the program can use.

        Returns:
            Datetime of the last download, or None if unavailable.
        """
        # Pull the raw text value out of the metadata section.
        last_download = self.get_metadata().get("last_download")

        # Only attempt parsing if a value actually exists.
        if last_download:
            try:
                # Convert ISO timestamp text like "2026-07-23T03:00:00+00:00"
                # into a datetime object.
                return datetime.fromisoformat(last_download)
            except (ValueError, TypeError):
                # If the timestamp text is invalid or the wrong type, return
                # None so callers know there is no usable timestamp.
                return None

        # No timestamp was stored, so report that with None.
        return None

    def get_last_data_timestamp(self) -> Optional[datetime]:
        """Get timestamp of most recent data point.

        === WHAT THIS DOES ===
        Retrieves the newest timestamp from the cached dataset metadata.

        === FOR NON-CODERS ===
        This is different from "last download". A download might happen now,
        but the newest data inside that download could still be from earlier.

        Returns:
            Datetime of the newest data point, or None if unavailable.
        """
        # Read the raw saved timestamp text from metadata.
        last_timestamp = self.get_metadata().get("last_data_timestamp")

        # If we have a stored value, try converting it into a usable datetime.
        if last_timestamp:
            try:
                return datetime.fromisoformat(last_timestamp)
            except (ValueError, TypeError):
                # Bad data is treated as missing data to keep the program stable.
                return None

        # If no value existed, return None.
        return None

    def set_last_data_timestamp(self, timestamp: datetime) -> None:
        """Set timestamp of most recent data point.

        === WHAT THIS DOES ===
        Stores the newest known data timestamp in metadata as ISO-formatted text.

        === FOR NON-CODERS ===
        Because JSON files store text, we convert the datetime into a standard
        text representation before saving it.

        Args:
            timestamp: The datetime to store.
        """
        # If metadata does not exist yet, create an empty metadata section first.
        if "metadata" not in self.data:
            self.data["metadata"] = {}

        # Convert the datetime into ISO text and save it in metadata.
        self.data["metadata"]["last_data_timestamp"] = timestamp.isoformat()

    def hours_since_last_download(self) -> float:
        """Calculate hours since last download.

        === WHAT THIS DOES ===
        Figures out how much time has passed since the cache was last saved or
        refreshed.

        === FOR NON-CODERS ===
        This is one of the main ways the program decides whether it should reuse
        saved data or go get newer data from Contact Energy.

        Returns:
            Number of hours since last download, or infinity if never downloaded.
        """
        # Ask the helper method for the saved last-download datetime.
        last_download = self.get_last_download()

        # If there has never been a successful download, pretend the age is
        # infinitely old so the cache is always considered stale.
        if not last_download:
            return float("inf")

        # Subtract the saved timestamp from the current UTC time to get a time
        # difference object.
        elapsed = datetime.now(timezone.utc) - last_download

        # Convert seconds into hours because the staleness rules use hours.
        return elapsed.total_seconds() / 3600
