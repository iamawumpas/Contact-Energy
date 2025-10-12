"""Contact Energy integration bootstrap (minimal)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Set up Contact Energy from a config entry. No platforms yet."""
	hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}
	return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Unload a config entry."""
	hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
	return True
