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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - ask for credentials.

        This is the first step shown to the user when adding the integration.
        The user enters their Contact Energy email and password. If submitted,
        we authenticate with the API to verify the credentials and retrieve
        available accounts.

        Args:
            user_input: Dictionary containing user-provided values from the form,
                       or None if this is the first call to show the form.

        Returns:
            A FlowResult containing either a form to display or the next step.
        """
        # If user has already submitted the form with their credentials
        if user_input is not None:
            # Attempt to authenticate and retrieve account information
            result = await self._async_validate_and_get_accounts(user_input)

            # If validation succeeded, move to account selection step
            if result.get("valid"):
                return await self.async_step_select_account()

            # If validation failed, show error and re-display form with error message
            return self.async_show_form(
                step_id="user",
                data_schema=self._get_user_form_schema(),
                errors={"base": result.get("error_code", "unknown")},
                description_placeholders={"error_message": result.get("error_message", "Unknown error")},
            )

        # Show the credentials form to the user for the first time
        return self.async_show_form(step_id="user", data_schema=self._get_user_form_schema())

    async def async_step_select_account(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle account selection when multiple ICPs are available.

        If the user has multiple Contact Energy accounts/ICPs, this step displays
        them as radio button options for the user to select which one to integrate.

        Args:
            user_input: Dictionary containing the selected account ID.

        Returns:
            A FlowResult containing either a form to display or the created entry.
        """
        # If user has selected an account
        if user_input is not None:
            # Extract the selected account ID from user input
            selected_account_id = user_input.get("account_id")

            # Find the selected account in our stored accounts data
            if self.accounts_data:
                account_summary = self.accounts_data.get("accountsSummary", [{}])[0]
                account_detail = self.accounts_data.get("accountDetail", {})
                contracts = account_detail.get("contracts", [])

                # Find the contract/account that matches the selection
                selected_contract = None
                for contract in contracts:
                    if contract.get("id") == selected_account_id:
                        selected_contract = contract
                        break

                if selected_contract:
                    # Prepare the config entry data with all required information
                    config_data = {
                        "email": self.api_client.email,
                        "token": self.api_client.token,
                        "segment": self.api_client.segment,
                        "bp": self.api_client.bp,
                        "account_id": account_summary.get("id"),
                        "account_nickname": account_summary.get("nickname"),
                        "icp": selected_contract.get("id"),
                        "address": selected_contract.get("address"),
                        "contract_id": selected_contract.get("premiseId"),
                    }

                    # Create the config entry with the selected account
                    return self.async_create_entry(title=f"Contact Energy - {selected_contract.get('address', 'Unknown')}", data=config_data)

        # Build the account selection form if we have multiple accounts
        if self.accounts_data:
            account_detail = self.accounts_data.get("accountDetail", {})
            contracts = account_detail.get("contracts", [])

            if contracts:
                # Create choices for the radio button list from available contracts
                choices = [
                    {
                        "value": contract.get("id"),
                        "label": f"{contract.get('id')} - {contract.get('address', 'Unknown')}",
                    }
                    for contract in contracts
                ]

                # Show account selection form
                return self.async_show_form(
                    step_id="select_account",
                    data_schema=self._get_account_selection_schema(choices),
                )

        # If we somehow don't have account data, return to user step
        return await self.async_step_user()

    async def _async_validate_and_get_accounts(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate credentials and retrieve available accounts.

        This method authenticates with the Contact Energy API using the provided
        email and password, then retrieves the list of available accounts/ICPs.

        Args:
            user_input: Dictionary containing email and password from the form.

        Returns:
            Dictionary with validation result containing:
            - valid: Boolean indicating if validation succeeded
            - error_code: Error code for the UI (if validation failed)
            - error_message: Human-friendly error message (if validation failed)
        """
        email = user_input.get("email", "").strip()
        password = user_input.get("password", "")

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

    def _get_user_form_schema(self):
        """Get the form schema for credential entry.

        Returns a HomeAssistant form schema for requesting the user's Contact
        Energy email address and password.

        Returns:
            A vol.Schema object defining the form fields.
        """
        import voluptuous as vol

        return vol.Schema(
            {
                vol.Required("email"): str,
                vol.Required("password"): str,
            }
        )

    def _get_account_selection_schema(self, choices: list[dict[str, str]]):
        """Get the form schema for account selection.

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
                vol.Required("account_id"): vol.In({choice["value"]: choice["label"] for choice in choices}),
            }
        )
