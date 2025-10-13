"""Config flow for Contact Energy."""
from __future__ import annotations

import logging
from typing import Any

# Debug: Print when this module loads
print(f"DEBUG: contact_energy config_flow.py module loading...")
logging.getLogger(__name__).info("Config flow module loaded for contact_energy")

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

try:
    from homeassistant.helpers import selector as sel
    USE_SELECTOR = True
except Exception:
    sel = None
    USE_SELECTOR = False

from .api import ContactEnergyApi, InvalidAuth, CannotConnect, UnknownError
from .const import (
    DOMAIN, 
    CONF_USAGE_DAYS, 
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_CONTRACT_ICP,
    USAGE_DAYS_MIN, 
    USAGE_DAYS_MAX
)

_LOGGER = logging.getLogger(__name__)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    
    if USE_SELECTOR:
        usage_days_field = sel.NumberSelector(
            sel.NumberSelectorConfig(
                min=USAGE_DAYS_MIN,
                max=USAGE_DAYS_MAX,
                step=1,
                mode=sel.NumberSelectorMode.SLIDER,
            )
        )
    else:
        usage_days_field = vol.All(
            cv.positive_int, 
            vol.Range(min=USAGE_DAYS_MIN, max=USAGE_DAYS_MAX)
        )
    
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): cv.string,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): cv.string,
            vol.Required(CONF_USAGE_DAYS, default=defaults.get(CONF_USAGE_DAYS, 10)): usage_days_field,
        }
    )


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Contact Energy."""

    VERSION = 1
    domain = DOMAIN

    def __init__(self) -> None:
        """Initialize config flow."""
        self._email: str = ""
        self._password: str = ""
        self._usage_days: int = 30

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store input for validation
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            self._usage_days = user_input[CONF_USAGE_DAYS]

            try:
                info = await self._validate_input()
                # Use email as unique id to prevent duplicates per account
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                
                # Create entry with all the extracted data
                entry_data = {
                    CONF_EMAIL: user_input[CONF_EMAIL],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_USAGE_DAYS: user_input[CONF_USAGE_DAYS],
                    CONF_ACCOUNT_ID: info["account_id"],
                    CONF_CONTRACT_ID: info["contract_id"],
                    CONF_CONTRACT_ICP: info["contract_icp"],
                }
                
                return self.async_create_entry(title=info["title"], data=entry_data)
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

    async def _validate_input(self) -> dict[str, Any]:
        """Validate account data and return info for entry creation."""
        api = ContactEnergyApi(self.hass, self._email, self._password)

        # Login and validate
        try:
            if not await api.async_login():
                raise InvalidAuth("Invalid credentials")
        except Exception as exc:
            _LOGGER.exception("Validation failed with exception")
            raise UnknownError("Connection failed") from exc

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
            premise_id = contract.get("premiseId")

            # Get ICP from detailed contract info
            detail_contracts = account_detail.get("contracts", [])
            icp = detail_contracts[0].get("icp") if detail_contracts else None

            if not contract_id or not icp:
                raise UnknownError("Unable to extract contract information")

            _LOGGER.debug(
                "Successfully validated account: account_id=%s, contract_id=%s, icp=%s",
                account_id,
                contract_id,
                icp,
            )

            return {
                "title": f"Contact Energy ({self._email})",
                "account_id": account_id,
                "contract_id": contract_id,
                "contract_icp": icp,
                "premise_id": premise_id,
            }

        except InvalidAuth:
            raise InvalidAuth("Invalid credentials")
        except Exception as exc:
            _LOGGER.exception("Account validation failed with exception")
            raise CannotConnect("Unable to connect") from exc


# Backwards compatibility alias
ContactEnergyConfigFlow = ConfigFlow

