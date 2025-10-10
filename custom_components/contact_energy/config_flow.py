"""Config flow for Contact Energy integration."""
import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .api import ContactEnergyApi, AuthenticationError, ConnectionError
from .const import DOMAIN, CONF_USAGE_DAYS, CONF_ACCOUNT_ID, CONF_CONTRACT_ID, CONF_CONTRACT_ICP

_LOGGER = logging.getLogger(__name__)


class ContactEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Contact Energy."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input = {}
        self._contracts = []

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validate credentials and get contracts
                api = ContactEnergyApi(
                    self.hass, 
                    user_input[CONF_EMAIL], 
                    user_input[CONF_PASSWORD]
                )
                
                if not await api.authenticate():
                    errors["base"] = "invalid_auth"
                else:
                    account_data = await api.get_accounts()
                    if not account_data:
                        errors["base"] = "no_accounts"
                    else:
                        # Store user input and proceed
                        self._user_input = user_input
                        
                        # Extract contracts
                        account_detail = account_data["accountDetail"]
                        self._contracts = []
                        
                        for contract in account_detail.get("contracts", []):
                            if contract.get("contractType") == 1:  # Electricity only
                                self._contracts.append({
                                    "id": contract["id"],
                                    "icp": contract["icp"],
                                    "address": contract["premise"]["supplyAddress"]["shortForm"]
                                })
                        
                        if not self._contracts:
                            errors["base"] = "no_electricity_contracts"
                        elif len(self._contracts) == 1:
                            # Only one contract, create entry directly
                            contract = self._contracts[0]
                            return self._create_entry(
                                account_detail["id"],
                                contract["id"], 
                                contract["icp"],
                                contract["address"]
                            )
                        else:
                            # Multiple contracts, show selection
                            return await self.async_step_contract()
                            
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during validation: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_USAGE_DAYS, default=30): vol.All(
                    cv.positive_int, vol.Range(min=1, max=100)
                ),
            }),
            errors=errors,
            description_placeholders={
                "email_description": "Your Contact Energy account email address",
                "password_description": "Your Contact Energy account password", 
                "usage_days_description": "Number of days of historical data to download initially (1-100)"
            }
        )

    async def async_step_contract(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle contract selection step."""
        errors = {}

        if user_input is not None:
            contract_id = user_input["contract_id"]
            
            # Find selected contract
            selected_contract = None
            for contract in self._contracts:
                if contract["id"] == contract_id:
                    selected_contract = contract
                    break
                    
            if selected_contract:
                # Get account ID from previous step
                api = ContactEnergyApi(
                    self.hass,
                    self._user_input[CONF_EMAIL],
                    self._user_input[CONF_PASSWORD]
                )
                
                await api.authenticate()
                account_data = await api.get_accounts()
                account_id = account_data["accountDetail"]["id"]
                
                return self._create_entry(
                    account_id,
                    selected_contract["id"],
                    selected_contract["icp"], 
                    selected_contract["address"]
                )
            else:
                errors["base"] = "invalid_contract"

        # Create contract selection schema
        contract_options = {
            contract["id"]: f"{contract['icp']} - {contract['address']}"
            for contract in self._contracts
        }

        return self.async_show_form(
            step_id="contract",
            data_schema=vol.Schema({
                vol.Required("contract_id"): vol.In(contract_options),
            }),
            errors=errors,
        )

    async def _create_entry(self, account_id: str, contract_id: str, icp: str, address: str) -> FlowResult:
        """Create the config entry."""
        # Set unique ID to prevent duplicates
        unique_id = f"{account_id}_{contract_id}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        data = {
            **self._user_input,
            CONF_ACCOUNT_ID: account_id,
            CONF_CONTRACT_ID: contract_id,
            CONF_CONTRACT_ICP: icp,
        }

        return self.async_create_entry(
            title=f"Contact Energy - {icp} ({address})",
            data=data,
        )