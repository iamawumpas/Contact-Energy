"""Config flow for Contact Energy integration."""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientSession
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    AuthenticationError,
    ConnectionError as ApiConnectionError,
    ContactEnergyApi,
)
from .const import (
    CONF_ACCOUNT_ADDRESS,
    CONF_ACCOUNT_ID,
    CONF_ACCOUNT_NICKNAME,
    CONF_CONTRACT_ID,
    CONF_HISTORY_DAYS,
    CONF_HISTORY_MONTHS,
    CONF_ICP_NUMBER,
    DEFAULT_HISTORY_MONTHS,
    DOMAIN,
    ERROR_ACCOUNT_IN_USE,
    ERROR_AUTH_FAILED,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_AUTH,
    ERROR_NO_ACCOUNTS,
    ERROR_UNKNOWN,
    MAX_HISTORY_MONTHS,
    MIN_HISTORY_MONTHS,
)

_LOGGER = logging.getLogger(__name__)


async def validate_auth(
    hass: HomeAssistant, email: str, password: str
) -> dict[str, Any]:
    """Validate the user credentials and fetch account data.
    
    Args:
        hass: Home Assistant instance
        email: User email
        password: User password
        
    Returns:
        Dictionary containing account data
        
    Raises:
        AuthenticationError: If authentication fails
        ApiConnectionError: If connection fails
    """
    _LOGGER.debug("Validating credentials for email: %s", email)
    
    session = async_get_clientsession(hass)
    
    async with ContactEnergyApi(email, password, session) as api:
        await api.authenticate()
        account_data = await api.get_accounts()
        
        _LOGGER.debug("Validation successful, fetched account data")
        return account_data


def get_account_list(account_data: dict[str, Any]) -> list[dict[str, str]]:
    """Extract account list from API response.
    
    Args:
        account_data: Raw account data from API
        
    Returns:
        List of account dictionaries with id, nickname, address, icp
    """
    accounts = []
    accounts_summary = account_data.get("accountsSummary", [])
    account_detail = account_data.get("accountDetail", {})
    
    for summary in accounts_summary:
        account_id = summary.get("id")
        nickname = summary.get("nickname", "Unknown")
        
        # Get contract info
        contracts = summary.get("contracts", [])
        if not contracts:
            _LOGGER.warning("No contracts found for account %s", account_id)
            continue
            
        for contract in contracts:
            contract_id = contract.get("contractId")
            address = contract.get("address", "Unknown Address")
            
            # Get ICP from detailed contracts
            icp_number = None
            if account_detail:
                detail_contracts = account_detail.get("contracts", [])
                for detail_contract in detail_contracts:
                    if detail_contract.get("id") == contract_id:
                        icp_number = detail_contract.get("icp")
                        break
            
            if not icp_number:
                _LOGGER.warning("No ICP found for contract %s", contract_id)
                icp_number = "unknown"
            
            accounts.append({
                "account_id": account_id,
                "contract_id": contract_id,
                "nickname": nickname,
                "address": address,
                "icp_number": icp_number.lower(),  # Lowercase ICP
            })
    
    _LOGGER.debug("Extracted %d account(s) from API data", len(accounts))
    return accounts


def is_account_configured(hass: HomeAssistant, icp_number: str) -> bool:
    """Check if an account with this ICP is already configured.
    
    Args:
        hass: Home Assistant instance
        icp_number: ICP number to check (lowercase)
        
    Returns:
        True if account is already configured
    """
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_ICP_NUMBER) == icp_number:
            _LOGGER.debug("Account with ICP %s is already configured", icp_number)
            return True
    return False


class ContactEnergyConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Contact Energy."""

    VERSION = 1
    DOMAIN = DOMAIN

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str | None = None
        self._password: str | None = None
        self._account_data: dict[str, Any] | None = None
        self._accounts: list[dict[str, str]] = []
        self._selected_account: dict[str, str] | None = None
        
        _LOGGER.debug("ContactEnergyConfigFlow initialized")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - email and password input.
        
        Args:
            user_input: User provided data
            
        Returns:
            FlowResult for next step or errors
        """
        _LOGGER.debug("async_step_user called with input: %s", bool(user_input))
        
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            
            _LOGGER.info("Attempting authentication for email: %s", self._email)
            
            try:
                # Type narrowing: at this point we know these are not None
                email = self._email or ""
                password = self._password or ""
                
                self._account_data = await validate_auth(
                    self.hass, email, password
                )
                
                # Extract accounts
                self._accounts = get_account_list(self._account_data)
                
                if not self._accounts:
                    _LOGGER.error("No accounts found for email: %s", self._email)
                    errors["base"] = ERROR_NO_ACCOUNTS
                else:
                    # Filter out already configured accounts
                    available_accounts = [
                        acc for acc in self._accounts
                        if not is_account_configured(self.hass, acc["icp_number"])
                    ]
                    
                    if not available_accounts:
                        _LOGGER.error("All accounts already configured for email: %s", 
                                    self._email)
                        return self.async_abort(reason="already_configured")
                    
                    self._accounts = available_accounts
                    
                    # If only one account, select it automatically
                    if len(self._accounts) == 1:
                        _LOGGER.info("Only one account available, auto-selecting")
                        self._selected_account = self._accounts[0]
                        return await self.async_step_configure_history()
                    
                    # Multiple accounts - show selection
                    _LOGGER.info("Multiple accounts found, showing selection")
                    return await self.async_step_select_account()
                    
            except AuthenticationError as err:
                _LOGGER.error("Authentication error: %s", err)
                if "invalid" in str(err).lower():
                    errors["base"] = ERROR_INVALID_AUTH
                else:
                    errors["base"] = ERROR_AUTH_FAILED
            except ApiConnectionError as err:
                _LOGGER.error("Connection error: %s", err)
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during authentication: %s", err)
                errors["base"] = ERROR_UNKNOWN

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_account(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle account selection when multiple accounts exist.
        
        Args:
            user_input: User provided data
            
        Returns:
            FlowResult for next step or errors
        """
        _LOGGER.debug("async_step_select_account called with input: %s", bool(user_input))
        
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_icp = user_input["account_selection"]
            
            # Find the selected account
            for account in self._accounts:
                if account["icp_number"] == selected_icp:
                    self._selected_account = account
                    _LOGGER.info("Account selected: %s (%s)", 
                               account["nickname"], selected_icp)
                    break
            
            if not self._selected_account:
                _LOGGER.error("Selected account not found: %s", selected_icp)
                errors["base"] = ERROR_UNKNOWN
            else:
                return await self.async_step_configure_history()

        # Create account selection options
        account_options = {
            account["icp_number"]: f"{account['nickname']} - {account['address']} ({account['icp_number']})"
            for account in self._accounts
        }
        
        _LOGGER.debug("Showing %d account options", len(account_options))

        return self.async_show_form(
            step_id="select_account",
            data_schema=vol.Schema(
                {
                    vol.Required("account_selection"): vol.In(account_options),
                }
            ),
            errors=errors,
        )

    async def async_step_configure_history(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle historical data configuration.
        
        Args:
            user_input: User provided data
            
        Returns:
            FlowResult to create the config entry
        """
        _LOGGER.debug("async_step_configure_history called with input: %s", 
                     bool(user_input))
        
        if user_input is not None and self._selected_account is not None:
            history_months = user_input[CONF_HISTORY_MONTHS]
            history_days = history_months * 30  # Approximate conversion
            
            _LOGGER.info("Creating config entry for account: %s with %d months history",
                        self._selected_account["icp_number"], history_months)
            
            # Create the config entry
            return self.async_create_entry(
                title=f"{self._selected_account['nickname']} ({self._selected_account['icp_number']})",
                data={
                    CONF_EMAIL: self._email,
                    CONF_PASSWORD: self._password,
                    CONF_ACCOUNT_ID: self._selected_account["account_id"],
                    CONF_CONTRACT_ID: self._selected_account["contract_id"],
                    CONF_ICP_NUMBER: self._selected_account["icp_number"],
                    CONF_ACCOUNT_NICKNAME: self._selected_account["nickname"],
                    CONF_ACCOUNT_ADDRESS: self._selected_account["address"],
                    CONF_HISTORY_MONTHS: history_months,
                    CONF_HISTORY_DAYS: history_days,
                },
            )

        return self.async_show_form(
            step_id="configure_history",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HISTORY_MONTHS, default=DEFAULT_HISTORY_MONTHS
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_HISTORY_MONTHS, max=MAX_HISTORY_MONTHS),
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ContactEnergyOptionsFlow:
        """Get the options flow for this handler.
        
        Args:
            config_entry: The config entry
            
        Returns:
            Options flow handler
        """
        return ContactEnergyOptionsFlow(config_entry)


class ContactEnergyOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Contact Energy."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.
        
        Args:
            config_entry: The config entry to update
        """
        self._config_entry = config_entry
        _LOGGER.debug("ContactEnergyOptionsFlow initialized for %s", 
                     config_entry.title)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options.
        
        Args:
            user_input: User provided data
            
        Returns:
            FlowResult to update options
        """
        _LOGGER.debug("async_step_init called with input: %s", bool(user_input))
        
        if user_input is not None:
            history_months = user_input[CONF_HISTORY_MONTHS]
            history_days = history_months * 30
            
            _LOGGER.info("Updating history months to %d for %s",
                        history_months, self._config_entry.title)
            
            # Update the config entry data
            new_data = {**self._config_entry.data}
            new_data[CONF_HISTORY_MONTHS] = history_months
            new_data[CONF_HISTORY_DAYS] = history_days
            
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data=new_data,
            )
            
            return self.async_create_entry(title="", data={})

        current_months = self._config_entry.data.get(
            CONF_HISTORY_MONTHS, DEFAULT_HISTORY_MONTHS
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HISTORY_MONTHS, default=current_months
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_HISTORY_MONTHS, max=MAX_HISTORY_MONTHS),
                    ),
                }
            ),
        )
