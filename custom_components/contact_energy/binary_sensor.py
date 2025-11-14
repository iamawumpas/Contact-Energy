"""Contact Energy anomaly detection binary sensor."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Any, Optional

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ACCOUNT_ID, CONF_CONTRACT_ID, CONF_CONTRACT_ICP
from .coordinator import ContactEnergyCoordinator
from .sensor import ContactEnergyUsageSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Contact Energy binary sensors from a config entry."""
    coordinator: ContactEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    account_id = entry.data[CONF_ACCOUNT_ID]
    contract_id = entry.data[CONF_CONTRACT_ID]
    contract_icp = entry.data[CONF_CONTRACT_ICP]

    entities: list[BinarySensorEntity] = [
        ContactEnergyUsageAnomalyBinarySensor(coordinator, account_id, contract_id, contract_icp)
    ]

    async_add_entities(entities, False)


class ContactEnergyUsageAnomalyBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that flags today's usage as anomalous using a z-score."""

    def __init__(self, coordinator: ContactEnergyCoordinator, account_id: str, contract_id: str, contract_icp: str) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._contract_id = contract_id
        self._contract_icp = contract_icp
        self._is_on: Optional[bool] = None
        self._z_score: Optional[float] = None
        self._threshold: float = 2.5  # default per Phase 3
        self._baseline_days: int = 30
        self._baseline_mean: Optional[float] = None
        self._baseline_std: Optional[float] = None
        self._today_usage: Optional[float] = None

        self._attr_name = f"Contact Energy Usage Anomaly ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_usage_anomaly"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert"

    @property
    def is_on(self) -> bool | None:
        return self._is_on

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "z_score": round(self._z_score, 3) if self._z_score is not None else None,
            "threshold": self._threshold,
            "baseline_days": self._baseline_days,
            "baseline_mean": round(self._baseline_mean, 3) if self._baseline_mean is not None else None,
            "baseline_std": round(self._baseline_std, 3) if self._baseline_std is not None else None,
            "today_usage": round(self._today_usage, 3) if self._today_usage is not None else None,
            "calculation": "Anomaly detected if today's paid usage z-score exceeds threshold vs last 30 complete days",
        }

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._recompute()

    def _handle_coordinator_update(self) -> None:
        self.hass.async_create_task(self._recompute())

    async def _fetch_daily_paid_usage(self, for_date: date) -> float:
        total = 0.0
        try:
            resp = await self.coordinator.api.async_get_usage(
                str(for_date.year), str(for_date.month), str(for_date.day), self._account_id, self._contract_id
            )
            if isinstance(resp, list):
                for p in resp:
                    val = ContactEnergyUsageSensor._safe_float(p.get("value"))
                    off = str(p.get("offpeakValue", "0.00"))
                    if off == "0.00":
                        total += val
        except Exception as e:  # noqa: BLE001
            _LOGGER.debug("Anomaly fetch failed for %s: %s", for_date, e)
        return total

    async def _recompute(self) -> None:
        # Baseline: last 30 complete days (yesterday back)
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=self._baseline_days - 1)
        series: list[float] = []
        current = start
        while current <= end:
            kwh = await self._fetch_daily_paid_usage(current)
            series.append(kwh)
            current += timedelta(days=1)
            await asyncio.sleep(0)

        # Today's partial usage
        today = datetime.now().date()
        today_usage = await self._fetch_daily_paid_usage(today)
        self._today_usage = today_usage

        if not series:
            self._is_on = None
            self._z_score = None
            self.async_write_ha_state()
            return

        n = len(series)
        mean_val = sum(series) / float(n)
        var = sum((x - mean_val) ** 2 for x in series) / float(n)
        std = var ** 0.5
        self._baseline_mean = mean_val
        self._baseline_std = std

        if std > 0:
            z = (today_usage - mean_val) / std
        else:
            z = 0.0
        self._z_score = z
        self._is_on = z > self._threshold
        self.async_write_ha_state()
