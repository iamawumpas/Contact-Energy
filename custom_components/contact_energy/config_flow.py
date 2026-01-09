"""Config flow for Contact Energy integration.

This module handles the user interaction when adding a Contact Energy integration
to Home Assistant. It presents configuration forms and validates user input such
as account credentials.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .contact_api import ContactEnergyApi, ContactEnergyApiError, ContactEnergyAuthError, ContactEnergyConnectionError

_LOGGER = logging.getLogger(__name__)


class ContactEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Contact Energy.

    This class manages the step-by-step configuration process when users add the
    Contact Energy integration to their Home Assistant instance. It validates input
    and creates the configuration entry.
    """

    # Increment this when you make changes to the config flow structure
    VERSION = 1

    def __init__(self):
        """Initialize the config flow.

        Sets up variables to store the API client and discovered accounts during
        the multi-step configuration process.
        """
        self.api_client: ContactEnergyApi | None = None
        self.accounts_data: dict[str, Any] | None = None
        self.previous_email: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - ask for credentials.

        This is the first step shown to the user when adding the integration.
        If a previous Contact Energy config entry exists, the user can choose to
        reuse that email or enter new credentials. If no previous entry exists,
        the user is asked to enter their email and password.

        Args:
            user_input: Dictionary containing user-provided values from the form.

        Returns:
            A FlowResult containing either a form to display or the next step.
        """
        # Check if there's a previous Contact Energy config entry to get the email
        self._get_previous_email()

        # If user has submitted the credentials form
        if user_input is not None:
            # Determine which email/password to use
            if self.previous_email and user_input.get("use_previous_email"):
                # User chose to reuse previous email
                email = self.previous_email
                password = user_input.get("password", "")
            else:
                # User provided new email and password
                email = user_input.get("email", "").strip()
                password = user_input.get("password", "")

            # Attempt to authenticate and retrieve account information
            result = await self._async_validate_and_get_accounts(email, password)

            # If validation succeeded, move to account selection step
            if result.get("valid"):
                return await self.async_step_select_account()

            # If validation failed, show error and re-display form with error message
            return self.async_show_form(
                step_id="user",
                data_schema=self._get_user_form_schema(self.previous_email),
                errors={"base": result.get("error_code", "unknown")},
                description_placeholders={"error_message": result.get("error_message", "Unknown error")},
            )

        # Show the credentials form to the user for the first time
        return self.async_show_form(
            step_id="user", data_schema=self._get_user_form_schema(self.previous_email)
        )

    async def async_step_select_account(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle account selection or confirmation.

        If the user has one available account, show a confirmation dialog.
        If the user has multiple available accounts, show a selection dialog.
        If no accounts are available (all previously configured), show an error.

        Args:
            user_input: Dictionary containing the selected or confirmed account.

        Returns:
            A FlowResult containing either a form or the created entry.
        """
        # If user has submitted account selection/confirmation
        if user_input is not None:
            selected_icp = user_input.get("account_icp") or user_input.get("confirmed_icp")
            return await self._async_create_config_entry(selected_icp)

        # Get filtered list of available accounts (excluding already configured)
        available_contracts = await self._async_get_available_accounts()

        # No accounts available
        if not available_contracts:
            return self.async_show_form(
                step_id="select_account",
                errors={"base": "no_available_accounts"},
            )

        # Single account available - show confirmation dialog with account details
        if len(available_contracts) == 1:
            contract = available_contracts[0]
            account_summary = self.accounts_data.get("accountsSummary", [{}])[0]
            
            return self.async_show_form(
                step_id="select_account",
                data_schema=self._get_single_account_confirmation_schema(contract),
                description_placeholders={
                    "account_nickname": account_summary.get("nickname", "Unknown"),
                    "icp": contract.get("icp", "Unknown"),
                },
            )

        # Multiple accounts available - show selection dialog
        account_summary = self.accounts_data.get("accountsSummary", [{}])[0]
        choices = [
            {
                "value": contract.get("icp"),
                "label": f"{contract.get('icp', 'Unknown')} - {contract.get('address') or account_summary.get('nickname') or 'Unknown'}",
            }
            for contract in available_contracts
        ]

        return self.async_show_form(
            step_id="select_account",
            data_schema=self._get_account_selection_schema(choices),
        )

    async def _async_create_config_entry(self, selected_icp: str) -> FlowResult:
        """Create the config entry with the selected account.

        Args:
            selected_icp: The ICP of the selected account.

        Returns:
            A FlowResult with the created config entry.
        """
        if self.accounts_data:
            account_detail = self.accounts_data.get("accountDetail", {})
            contracts = account_detail.get("contracts", [])
            account_summary = self.accounts_data.get("accountsSummary", [{}])[0]

            # Find the selected contract
            selected_contract = None
            for contract in contracts:
                if contract.get("icp") == selected_icp:
                    selected_contract = contract
                    break

            if selected_contract:
                # Use address if available, otherwise use account nickname
                display_name = selected_contract.get("address") or account_summary.get("nickname") or "Unknown"
                
                # Extract account_id from accountDetail.id (required for ba parameter in usage API)
                # This is the Contact Energy account ID, not the Business Partner (bp) ID
                account_id = account_detail.get("id")
                
                # Validate that we have account_id - critical for usage API calls
                if not account_id:
                    _LOGGER.error("No account ID found in accountDetail. Cannot create config entry.")
                    return self.async_abort(reason="no_account_id")
                
                # Prepare the config entry data with all required information
                # Note: Password is stored encrypted by Home Assistant's internal encryption
                config_data = {
                    "email": self.api_client.email,
                    "password": self.api_client.password,
                    "token": self.api_client.token,
                    "segment": self.api_client.segment,
                    "bp": self.api_client.bp,
                    "account_id": account_id,
                    "account_nickname": account_summary.get("nickname"),
                    "icp": selected_contract.get("icp"),
                    "address": selected_contract.get("address"),
                    "contract_id": selected_contract.get("id"),
                    "premise_id": selected_contract.get("premiseId"),
                }

                # Create the config entry with a descriptive title (ICP - Address/Nickname)
                return self.async_create_entry(
                    title=f"{selected_contract.get('icp')} - {display_name}", 
                    data=config_data
                )

        return await self.async_step_select_account()

    async def _async_get_available_accounts(self) -> list[dict[str, Any]]:
        """Get list of accounts not already configured in Home Assistant.

        Filters out any Contact Energy accounts that are already set up as
        config entries to prevent duplicate integrations.

        Returns:
            List of available contracts that can be configured.
        """
        if not self.accounts_data:
            return []

        account_detail = self.accounts_data.get("accountDetail", {})
        contracts = account_detail.get("contracts", [])

        # Get list of already configured ICPs from existing config entries
        configured_icps = set()
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            configured_icps.add(entry.data.get("icp"))

        # Filter out already configured accounts
        available = [c for c in contracts if c.get("icp") not in configured_icps]
        return available

    def _get_previous_email(self) -> None:
        """Extract the previous email from the most recent Contact Energy config entry.

        Stores the email in self.previous_email if found, otherwise leaves it None.
        """
        # Get the most recent Contact Energy config entry
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            # Use the most recent entry
            most_recent = entries[-1]
            self.previous_email = most_recent.data.get("email")

    async def _async_validate_and_get_accounts(self, email: str, password: str) -> dict[str, Any]:
        """Validate credentials and retrieve available accounts.

        This method authenticates with the Contact Energy API using the provided
        email and password, then retrieves the list of available accounts/ICPs.

        Args:
            email: Contact Energy account email address.
            password: Contact Energy account password.

        Returns:
            Dictionary with validation result containing:
            - valid: Boolean indicating if validation succeeded
            - error_code: Error code for the UI (if validation failed)
            - error_message: Human-friendly error message (if validation failed)
        """
        try:
            # Create API client with provided credentials
            self.api_client = ContactEnergyApi(email, password)

            # Authenticate with Contact Energy API
            _LOGGER.debug(f"Attempting to authenticate {email}")
            await self.api_client.authenticate()

            # Retrieve account information after successful authentication
            self.accounts_data = await self.api_client.get_accounts()

            # Verify we retrieved account data
            account_detail = self.accounts_data.get("accountDetail", {})
            contracts = account_detail.get("contracts", [])

            if not contracts:
                return {
                    "valid": False,
                    "error_code": "no_accounts",
                    "error_message": "No accounts found for this Contact Energy user. Please check your account status.",
                }

            _LOGGER.debug(f"Successfully retrieved {len(contracts)} account(s) for {email}")
            return {"valid": True}

        except ContactEnergyAuthError as e:
            # Authentication failed - invalid credentials or access denied
            _LOGGER.warning(f"Authentication failed for {email}: {str(e)}")
            return {
                "valid": False,
                "error_code": "invalid_auth",
                "error_message": str(e),
            }

        except ContactEnergyConnectionError as e:
            # Connection error - network issue or API unavailable
            _LOGGER.error(f"Connection error: {str(e)}")
            return {
                "valid": False,
                "error_code": "connection_error",
                "error_message": str(e),
            }

        except ContactEnergyApiError as e:
            # Generic API error
            _LOGGER.error(f"API error: {str(e)}")
            return {
                "valid": False,
                "error_code": "api_error",
                "error_message": str(e),
            }

        except Exception as e:
            # Unexpected error
            _LOGGER.exception(f"Unexpected error during validation: {e}")
            return {
                "valid": False,
                "error_code": "unknown",
                "error_message": f"An unexpected error occurred: {str(e)}",
            }

    def _get_user_form_schema(self, previous_email: str | None = None):
        """Get the form schema for credential entry.

        If a previous email is available, offers user choice to reuse it or enter new.
        Otherwise, requests new email and password.

        Args:
            previous_email: Email from a previous Contact Energy config entry, if any.

        Returns:
            A vol.Schema object defining the form fields.
        """
        import voluptuous as vol

        if previous_email:
            # Offer choice to reuse previous email or enter new credentials
            return vol.Schema(
                {
                    vol.Required("use_previous_email", default=True): bool,
                    vol.Optional("email"): str,
                    vol.Required("password"): str,
                }
            )
        else:
            # Request new email and password
            return vol.Schema(
                {
                    vol.Required("email"): str,
                    vol.Required("password"): str,
                }
            )

    def _get_account_selection_schema(self, choices: list[dict[str, str]]):
        """Get the form schema for selecting from multiple accounts.

        Returns a HomeAssistant form schema for selecting one account from
        multiple available Contact Energy accounts/ICPs.

        Args:
            choices: List of account choices for the radio button list.

        Returns:
            A vol.Schema object defining the account selection field.
        """
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Required("account_icp"): vol.In({choice["value"]: choice["label"] for choice in choices}),
            }
        )

    def _get_single_account_confirmation_schema(self, contract: dict[str, Any]):
        """Get the form schema for confirming a single account.

        Returns a HomeAssistant form schema for confirming the single available
        account with the account nickname and ICP number displayed.

        Args:
            contract: The contract/account data to display for confirmation.

        Returns:
            A vol.Schema object with a hidden field to store the confirmed ICP.
        """
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Required("confirmed_icp", default=contract.get("icp")): str,
            }
        )
