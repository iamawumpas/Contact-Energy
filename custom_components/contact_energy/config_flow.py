"""Config flow for Contact Energy."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import selector as sel

from .const import DOMAIN, CONF_USAGE_DAYS, USAGE_DAYS_MIN, USAGE_DAYS_MAX
from .api import ContactEnergyApi, CannotConnect, InvalidAuth, UnknownError

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): cv.string,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): cv.string,
            # Slider selector for usage days 1-100
            vol.Required(CONF_USAGE_DAYS, default=defaults.get(CONF_USAGE_DAYS, 10)):
                sel.NumberSelector(
                    sel.NumberSelectorConfig(
                        min=USAGE_DAYS_MIN,
                        max=USAGE_DAYS_MAX,
                        step=1,
                        mode=sel.NumberSelectorMode.SLIDER,
                    )
                ),
        }
    )


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    _LOGGER.debug(
        "Validating Contact Energy credentials for %s with %s days",
        data.get(CONF_EMAIL),
        data.get(CONF_USAGE_DAYS),
    )
    api = ContactEnergyApi(hass, data[CONF_EMAIL], data[CONF_PASSWORD])
    ok = await api.async_validate_account()
    if not ok:
        raise ValueError("invalid_auth")
    return {"title": f"Contact Energy ({data[CONF_EMAIL]})"}


class ContactEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Contact Energy."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
                # Use email as unique id to prevent duplicates per account
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)
            except ValueError as e:
                # Validation returned a known code string
                if str(e) == "invalid_auth":
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "unknown"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except UnknownError:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error in config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

