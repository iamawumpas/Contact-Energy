"""Config flow for Contact Energy."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

try:
    from homeassistant.helpers import selector as sel
    USE_SELECTOR = True
except ImportError:
    sel = None
    USE_SELECTOR = False

from .api import ContactEnergyApi, InvalidAuth, CannotConnect, UnknownError
from .const import (
    DOMAIN,
    CONF_USAGE_DAYS,
    CONF_USAGE_MONTHS,
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_CONTRACT_ICP,
    USAGE_MONTHS_MIN,
    USAGE_MONTHS_MAX,
    days_to_months,
)

_LOGGER = logging.getLogger(__name__)


def _build_usage_months_field():
    """Build the usage months field based on available selector."""
    if USE_SELECTOR:
        return sel.NumberSelector(
            sel.NumberSelectorConfig(
                min=USAGE_MONTHS_MIN,
                max=USAGE_MONTHS_MAX,
                step=1,
                mode=sel.NumberSelectorMode.SLIDER,
            )
        )
    return vol.All(cv.positive_int, vol.Range(min=USAGE_MONTHS_MIN, max=USAGE_MONTHS_MAX))


def _get_default_months(defaults: dict[str, Any]) -> int:
    """Get default months value from config."""
    default_months = defaults.get(CONF_USAGE_MONTHS)
    if default_months is None:
        raw_days = defaults.get(CONF_USAGE_DAYS, 30)
        try:
            raw_days_int = int(raw_days)
        except Exception:  # noqa: BLE001
            raw_days_int = 30
        default_months = days_to_months(raw_days_int)
    return default_months or 1


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build user input schema."""
    defaults = defaults or {}
    default_months = _get_default_months(defaults)

    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): cv.string,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): cv.string,
            vol.Required(CONF_USAGE_MONTHS, default=default_months): _build_usage_months_field(),
        }
    )


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Contact Energy."""

    VERSION = 1
    domain = DOMAIN

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    def __init__(self) -> None:
        """Initialize config flow."""
        pass


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Contact Energy."""

    VERSION = 1
    domain = DOMAIN

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await self._validate_and_extract_info(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_USAGE_MONTHS]
                )
                
                # Use email as unique id to prevent duplicates per account
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                
                # Create entry with all the extracted data
                entry_data = {
                    CONF_EMAIL: user_input[CONF_EMAIL],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_USAGE_MONTHS: user_input[CONF_USAGE_MONTHS],
                    CONF_ACCOUNT_ID: info["account_id"],
                    CONF_CONTRACT_ID: info["contract_id"],
                    CONF_CONTRACT_ICP: info["contract_icp"],
                }
                
                return self.async_create_entry(title=info["title"], data=entry_data)
                
            except ValueError as e:
                errors["base"] = "invalid_auth" if str(e) == "invalid_auth" else "unknown"
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

    async def _validate_and_extract_info(self, email: str, password: str, usage_months: int) -> dict[str, Any]:
        """Validate account data and return info for entry creation."""
        api = ContactEnergyApi(self.hass, email, password)

        # Login and validate
        if not await api.async_login():
            raise InvalidAuth("Invalid credentials")

        # Get account data to extract IDs and contracts
        try:
            account_data = await api._request(
                "GET",
                f"{api._url_base}/accounts/v2",
                headers=api._headers(),
            )
            if not isinstance(account_data, dict) or not account_data.get("accountDetail"):
                raise UnknownError("Unable to access account")

            # Extract account and contract information
            account_summary = account_data.get("accountsSummary", [{}])[0]
            account_detail = account_data.get("accountDetail", {})

            account_id = account_summary.get("id")
            contracts = account_summary.get("contracts", [])

            if not account_id or not contracts:
                raise UnknownError("No electricity contracts found")

            # Get first electricity contract
            contract = contracts[0]
            contract_id = contract.get("contractId")

            # Get ICP from detailed contract info
            detail_contracts = account_detail.get("contracts", [])
            icp = detail_contracts[0].get("icp") if detail_contracts else None

            if not contract_id or not icp:
                raise UnknownError("Unable to extract contract information")

            _LOGGER.debug(
                "Successfully validated account: account_id=%s, contract_id=%s, icp=%s",
                account_id, contract_id, icp,
            )

            return {
                "title": f"Contact Energy ({email})",
                "account_id": account_id,
                "contract_id": contract_id,
                "contract_icp": icp,
            }

        except InvalidAuth:
            raise
        except Exception as exc:
            _LOGGER.exception("Account validation failed")
            raise CannotConnect("Unable to connect") from exc


# Backwards compatibility alias
ContactEnergyConfigFlow = ConfigFlow


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Contact Energy."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry with new values
            updated_data = dict(self.config_entry.data)
            updated_data[CONF_USAGE_MONTHS] = user_input[CONF_USAGE_MONTHS]
            # Remove legacy days if present
            updated_data.pop(CONF_USAGE_DAYS, None)
            
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=updated_data,
            )
            
            return self.async_create_entry(title="", data={})

        # Create schema with current values
        current_months = self.config_entry.data.get(CONF_USAGE_MONTHS)
        if current_months is None:
            current_months = days_to_months(self.config_entry.data.get(CONF_USAGE_DAYS, 30))

        options_schema = vol.Schema(
            {
                vol.Required(CONF_USAGE_MONTHS, default=current_months): _build_usage_months_field(),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
