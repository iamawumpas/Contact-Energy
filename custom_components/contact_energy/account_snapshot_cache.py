"""Persistent account snapshot cache for Contact Energy integration.

Stores the last successful account payload on disk so account and billing
sensors can survive Home Assistant restarts or temporary API outages.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


class AccountSnapshotCache:
    """Persist and load last-known account API payload per contract."""

    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, contract_id: str, cache_dir: Optional[Path] = None) -> None:
        self.contract_id = contract_id

        if cache_dir is None:
            component_dir = Path(__file__).parent
            self.cache_dir = component_dir / "data"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_path = self.cache_dir / f"account_snapshot_{contract_id}.json"

        if contract_id not in AccountSnapshotCache._locks:
            AccountSnapshotCache._locks[contract_id] = asyncio.Lock()
        self._lock = AccountSnapshotCache._locks[contract_id]

    async def load(self) -> Optional[dict[str, Any]]:
        """Load snapshot from disk.

        Returns:
            The saved account payload, or None if unavailable/invalid.
        """
        if not self.cache_path.exists():
            return None

        def _read() -> dict[str, Any]:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                return json.load(handle)

        try:
            loop = asyncio.get_event_loop()
            payload = await loop.run_in_executor(None, _read)
            account_data = payload.get("account_data")
            if isinstance(account_data, dict):
                return account_data
            return None
        except Exception as err:
            _LOGGER.warning(
                "Failed loading account snapshot for contract %s: %s",
                self.contract_id,
                err,
            )
            return None

    async def save(self, account_data: dict[str, Any]) -> None:
        """Persist the latest account payload atomically."""
        async with self._lock:
            await self._save_locked(account_data)

    async def _save_locked(self, account_data: dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "contract_id": self.contract_id,
            "metadata": {
                "version": "1.0.0",
                "updated": datetime.now(timezone.utc).isoformat(),
            },
            "account_data": account_data,
        }

        temp_path = self.cache_path.with_suffix(".tmp")

        def _write() -> None:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            temp_path.replace(self.cache_path)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write)
