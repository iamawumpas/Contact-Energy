"""Config flow for Contact Energy integration.

====== WHAT THIS FILE DOES ======
This module controls the step-by-step setup wizard that Home Assistant shows
when someone adds the Contact Energy integration through the user interface.

Its job is to:
1. Ask the user for their Contact Energy login details.
2. Validate those details by talking to the Contact Energy API.
3. Fetch the user's available accounts after login succeeds.
4. Let the user confirm or choose which account to connect.
5. Save the final configuration as a Home Assistant config entry.

In Home Assistant terms, this file defines a "config flow".
A config flow is a guided setup conversation. Home Assistant calls one method,
shows a form, receives the user's answers, then calls the next method until the
integration is fully configured or an error is shown.

====== FOR NON-CODERS ======
If you imagine setting up a new online service in an app, this file is the
wizard behind those screens.

It works like this:
- Screen 1 asks for your email and password.
- The integration checks whether those details are correct.
- If your login is valid, it looks up the electricity account(s) attached to it.
- If there is only one account, it asks you to confirm it.
- If there are multiple accounts, it asks you which one to use.
- Then it saves that choice so Home Assistant can use it later.

Helpful Home Assistant terms:
- Config flow: The setup wizard.
- FlowResult: The instruction we return to Home Assistant telling it what to do
  next, such as "show this form" or "finish setup".
- Schema: The definition of what fields a form should contain.
- Validation: Checking whether the information entered by the user is correct.
"""

# This enables newer Python type-hint syntax while keeping compatibility with
# the Python version Home Assistant expects.
from __future__ import annotations

# ============================================================================
# IMPORTS - the building blocks this file needs
# ============================================================================

# logging lets us record useful debug, warning, and error messages.
# This is important when setup fails and we need to understand why.
import logging

# Any is a flexible type hint used when a value may contain different kinds of
# data, such as API responses made of nested dictionaries and lists.
from typing import Any

# Home Assistant exposes config_entries as the framework used for integration
# setup flows and saved configuration entries.
from homeassistant import config_entries

# FlowResult is the standard return type for config-flow steps.
# It tells Home Assistant whether to show another form, abort, or create an
# entry and finish setup.
from homeassistant.data_entry_flow import FlowResult

# DOMAIN is the integration's unique identifier inside Home Assistant.
# We use it to find existing Contact Energy entries and register new ones.
from .const import DOMAIN

# These imports give us the Contact Energy API client plus the specific error
# types we need to handle gracefully during login and account lookup.
from .contact_api import (
    ContactEnergyApi,
    ContactEnergyApiError,
    ContactEnergyAuthError,
    ContactEnergyConnectionError,
)

# Create a module-specific logger so any messages from this file are clearly
# identified in Home Assistant logs.
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# MAIN CONFIG FLOW CLASS
# ============================================================================
class ContactEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Contact Energy setup wizard inside Home Assistant.

    ====== WHAT A CONFIG FLOW IS ======
    A config flow is Home Assistant's built-in way to guide a user through
    adding an integration. Instead of writing a one-shot setup function, we
    split setup into steps. Each step can:
    - show a form,
    - inspect the user's answers,
    - validate data,
    - move to the next step,
    - or stop with an error.

    ====== THE MULTI-STEP PROCESS IN THIS CLASS ======
    Step 1: async_step_user
        Ask for login credentials. Optionally allow the user to reuse the email
        from a previous Contact Energy setup.

    Step 2: async_step_select_account
        After successful login, show either:
        - a confirmation form if exactly one account is available, or
        - a selection form if multiple accounts are available.

    Final step:
        Create the saved Home Assistant config entry containing the account and
        authentication data needed by the integration.

    ====== FOR NON-CODERS ======
    Think of this class as the script for a customer-service representative.
    It knows:
    - what question to ask first,
    - how to check the answer,
    - what follow-up question to ask next,
    - and what information to save at the end.
    """

    # VERSION tells Home Assistant which stored config-flow structure this code
    # expects. If the flow structure ever changes in a way that affects stored
    # entries, this number can be increased so migrations can be handled.
    VERSION = 1

    def __init__(self):
        """Set up blank state for this config-flow instance.

        ====== WHY WE NEED INSTANCE VARIABLES ======
        A config flow is a conversation that can span multiple screens.
        Information collected in step 1 must still be available in step 2.
        Instance variables (values stored on self) let this one flow object
        remember data between those steps.

        ====== WHAT EACH VARIABLE STORES ======
        self.api_client:
            The logged-in Contact Energy API client created after the user
            enters credentials. We keep it so later steps can reuse the same
            authenticated data.

        self.accounts_data:
            The account details returned by Contact Energy after login. This
            includes contract/account information used to build the account
            selection screen and the final saved entry.

        self.previous_email:
            The email address from the most recent existing Contact Energy setup
            in Home Assistant, if one exists. This allows the UI to offer a
            convenient "reuse previous email" option.
        """
        # Store the authenticated API client once credentials are validated.
        # It starts as None because the user has not logged in yet.
        self.api_client: ContactEnergyApi | None = None

        # Store the raw accounts response from the API after authentication.
        # It also starts empty until we successfully fetch account details.
        self.accounts_data: dict[str, Any] | None = None

        # Store the most recently used email from an existing config entry.
        # This supports the "use previous email" checkbox in step 1.
        self.previous_email: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle setup step 1: collecting Contact Energy credentials.

        ====== STEP 1 OF THE WIZARD ======
        This is the first screen the user sees. Its purpose is to collect the
        login details needed to connect to Contact Energy.

        ====== HOW PREVIOUS EMAIL REUSE WORKS ======
        If Home Assistant already has at least one Contact Energy config entry,
        we read the email from the most recent one and store it in
        self.previous_email.

        Then the form can offer two possibilities:
        - reuse that previous email and only ask for a fresh password, or
        - enter a completely new email and password.

        ====== VALIDATION OVERVIEW ======
        When the form is submitted, we:
        1. Decide which email to use.
        2. Read the password.
        3. Try to log in and fetch accounts.
        4. If successful, move to step 2.
        5. If unsuccessful, show the form again with an error.
        """
        # Before building or processing the credentials form, look for a
        # previously saved Contact Energy email so we can offer the reuse option.
        self._get_previous_email()

        # user_input will be None the first time Home Assistant calls this step,
        # because no form has been submitted yet.
        # If it is not None, it means the user has filled out the form and we
        # should now validate what they entered.
        if user_input is not None:
            # If we found a previous email and the user ticked the
            # "use_previous_email" option, reuse that stored address instead of
            # reading a new one from the form.
            if self.previous_email and user_input.get("use_previous_email"):
                # Reuse the old email for convenience.
                email = self.previous_email

                # Always require the user to provide the password again. We do
                # not assume a previously saved password should be silently reused
                # at this stage of the UI flow.
                password = user_input.get("password", "")
            else:
                # If the user chose not to reuse the previous email—or if there
                # was no previous email available—read the new email from the
                # submitted form.
                email = user_input.get("email", "").strip()

                # Read the submitted password. Default to an empty string if the
                # field is unexpectedly missing, so validation can fail cleanly.
                password = user_input.get("password", "")

            # Validate the credentials and fetch account data in one helper call.
            # This keeps the main step readable and centralizes the API-related
            # error handling logic.
            result = await self._async_validate_and_get_accounts(email, password)

            # If validation succeeded, the helper has already populated
            # self.api_client and self.accounts_data. We can now continue to the
            # second setup screen where the user confirms/selects an account.
            if result.get("valid"):
                return await self.async_step_select_account()

            # If validation failed, ask Home Assistant to show the same form
            # again. We provide:
            # - the same schema (fields to show),
            # - an error code Home Assistant can map to translated text,
            # - and a human-readable error message placeholder for the UI.
            return self.async_show_form(
                step_id="user",
                data_schema=self._get_user_form_schema(self.previous_email),
                errors={"base": result.get("error_code", "unknown")},
                description_placeholders={
                    "error_message": result.get("error_message", "Unknown error")
                },
            )

        # If this is the first visit to step 1, no data has been submitted yet.
        # We simply ask Home Assistant to render the credentials form.
        return self.async_show_form(
            step_id="user",
            data_schema=self._get_user_form_schema(self.previous_email),
        )

    async def async_step_select_account(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle setup step 2: confirming or selecting an account.

        ====== STEP 2 OF THE WIZARD ======
        By the time we reach this step, the user's login has already been
        verified and account data has already been downloaded.

        ====== SINGLE VS MULTIPLE ACCOUNT HANDLING ======
        - If zero unconfigured accounts are available, show an error.
        - If exactly one account is available, show a confirmation form.
        - If more than one account is available, show a selection form.

        ====== CONFIRMATION VS SELECTION ======
        A single available account does not require the user to choose between
        options, but Home Assistant still expects a form/step transition. So we
        show a simple confirmation form containing the ICP value.

        When multiple accounts exist, we build a list of choices and let the
        user explicitly pick one.
        """
        # If user_input exists, the user has already interacted with the account
        # screen. That means we should extract whichever account identifier was
        # submitted and finish setup by creating the config entry.
        if user_input is not None:
            # The submitted field name differs depending on whether we showed a
            # single-account confirmation form or a multi-account selection form.
            selected_icp = user_input.get("account_icp") or user_input.get(
                "confirmed_icp"
            )

            # Hand off to the helper that builds and saves the final entry.
            return await self._async_create_config_entry(selected_icp)

        # Ask the helper for the list of accounts that are still available to be
        # configured. This excludes any ICPs already set up in Home Assistant.
        available_contracts = await self._async_get_available_accounts()

        # If no accounts remain after filtering, there is nothing the user can
        # add from this login. We show an error instead of a selection form.
        if not available_contracts:
            return self.async_show_form(
                step_id="select_account",
                errors={"base": "no_available_accounts"},
            )

        # If there is only one account left, build a lightweight confirmation
        # form instead of a list of choices.
        if len(available_contracts) == 1:
            # Extract the only remaining contract.
            contract = available_contracts[0]

            # accountsSummary is used for friendly display information such as a
            # nickname. We default to an empty dict so missing API data does not
            # crash the flow.
            account_summary = self.accounts_data.get("accountsSummary", [{}])[0]

            # Show a confirmation form for the single available account.
            # description_placeholders provide values that UI text can display,
            # such as the nickname and ICP.
            return self.async_show_form(
                step_id="select_account",
                data_schema=self._get_single_account_confirmation_schema(contract),
                description_placeholders={
                    "account_nickname": account_summary.get("nickname", "Unknown"),
                    "icp": contract.get("icp", "Unknown"),
                },
            )

        # If multiple accounts are available, we need a user-facing choice list.
        # We again use accountsSummary as a friendly fallback if a contract does
        # not include a specific address.
        account_summary = self.accounts_data.get("accountsSummary", [{}])[0]

        # Build the list of options shown in the form.
        # Each option has:
        # - value: the ICP saved if selected
        # - label: human-friendly text shown in the UI
        choices = [
            {
                "value": contract.get("icp"),
                "label": (
                    f"{contract.get('icp', 'Unknown')} - "
                    f"{contract.get('address') or account_summary.get('nickname') or 'Unknown'}"
                ),
            }
            for contract in available_contracts
        ]

        # Ask Home Assistant to show the account-selection form built from those
        # choices.
        return self.async_show_form(
            step_id="select_account",
            data_schema=self._get_account_selection_schema(choices),
        )

    async def _async_create_config_entry(self, selected_icp: str) -> FlowResult:
        """Create and save the final Home Assistant config entry.

        ====== WHAT THIS HELPER DOES ======
        This helper takes the chosen ICP (account identifier), finds the matching
        contract in the downloaded API data, collects all the fields the
        integration needs later, and asks Home Assistant to save them.

        ====== STEP-BY-STEP ======
        1. Confirm that account data exists.
        2. Look up the selected contract by ICP.
        3. Extract extra metadata such as account ID and nickname.
        4. Validate critical fields.
        5. Build the final data dictionary.
        6. Return a FlowResult that creates the saved entry.
        """
        # We can only create an entry if account data was successfully fetched in
        # the earlier validation step.
        if self.accounts_data:
            # accountDetail contains the detailed account record from the API.
            account_detail = self.accounts_data.get("accountDetail", {})

            # contracts is the list of electricity accounts/contract records that
            # the user can potentially configure.
            contracts = account_detail.get("contracts", [])

            # accountsSummary contains friendlier display information, such as a
            # nickname, which is useful for the entry title.
            account_summary = self.accounts_data.get("accountsSummary", [{}])[0]

            # Start with no selected contract found. We will search for the one
            # whose ICP matches the value submitted by the user.
            selected_contract = None

            # Loop through all available contracts until we find the matching ICP.
            for contract in contracts:
                if contract.get("icp") == selected_icp:
                    selected_contract = contract
                    break

            # Only continue if we successfully found the selected contract.
            if selected_contract:
                # Prefer a precise address for display, but fall back to the
                # account nickname if the address is not present.
                display_name = (
                    selected_contract.get("address")
                    or account_summary.get("nickname")
                    or "Unknown"
                )

                # Extract the main Contact Energy account ID from accountDetail.
                # This is critical later for usage API requests.
                account_id = account_detail.get("id")

                # If account_id is missing, we deliberately abort because the
                # integration would not function correctly without it.
                if not account_id:
                    _LOGGER.error(
                        "No account ID found in accountDetail. Cannot create config entry."
                    )
                    return self.async_abort(reason="no_account_id")

                # Gather every field the integration will need after setup.
                # Home Assistant stores this as the config entry's data payload.
                config_data = {
                    # The user's login credentials and authentication state.
                    "email": self.api_client.email,
                    "password": self.api_client.password,
                    "token": self.api_client.token,
                    "segment": self.api_client.segment,
                    "bp": self.api_client.bp,
                    # The main account identifiers required by downstream API calls.
                    "account_id": account_id,
                    "contract_id": selected_contract.get("id"),
                    "premise_id": selected_contract.get("premiseId"),
                    # Friendly display metadata for the integration instance.
                    "account_nickname": account_summary.get("nickname"),
                    "icp": selected_contract.get("icp"),
                    "address": selected_contract.get("address"),
                }

                # Tell Home Assistant to finish the flow and create a saved config
                # entry. The title is what the user sees in the integrations UI.
                return self.async_create_entry(
                    title=f"{selected_contract.get('icp')} - {display_name}",
                    data=config_data,
                )

        # If we could not create the entry—for example because data was missing—
        # restart the account-selection step rather than crashing the flow.
        return await self.async_step_select_account()

    async def _async_get_available_accounts(self) -> list[dict[str, Any]]:
        """Return accounts that are not already configured in Home Assistant.

        ====== WHAT THIS HELPER DOES ======
        Contact Energy may return multiple contracts, but some of them may have
        already been added as existing Home Assistant config entries. This helper
        filters those out so the user only sees accounts that can still be added.

        ====== STEP-BY-STEP ======
        1. Read the contract list from the API response.
        2. Read already configured ICPs from existing config entries.
        3. Remove any matching contracts.
        4. Return only the remaining accounts.
        """
        # If account data is missing, there is nothing to filter, so return an
        # empty list. This avoids attribute errors later.
        if not self.accounts_data:
            return []

        # Pull the detailed account block out of the API response.
        account_detail = self.accounts_data.get("accountDetail", {})

        # Read the full list of contracts returned by Contact Energy.
        contracts = account_detail.get("contracts", [])

        # Build a set of ICPs that are already configured in Home Assistant.
        # A set gives fast membership checks when filtering below.
        configured_icps = set()
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            configured_icps.add(entry.data.get("icp"))

        # Keep only contracts whose ICP is not already in the configured set.
        available = [c for c in contracts if c.get("icp") not in configured_icps]
        return available

    def _get_previous_email(self) -> None:
        """Load the most recently used Contact Energy email from saved entries.

        ====== WHAT THIS HELPER DOES ======
        This helper improves usability. If the user has already set up another
        Contact Energy account, we can pre-offer that email address instead of
        forcing them to type it again.

        ====== STEP-BY-STEP ======
        1. Ask Home Assistant for existing Contact Energy config entries.
        2. If at least one exists, pick the most recent one.
        3. Read its saved email.
        4. Store that email on self.previous_email for step 1 to use.
        """
        # Fetch all existing config entries for this integration domain.
        entries = self.hass.config_entries.async_entries(DOMAIN)

        # Only try to read a previous email if at least one entry exists.
        if entries:
            # The code uses the most recently added entry, which is the last item
            # in the list returned by Home Assistant.
            most_recent = entries[-1]

            # Save the email for later use by the credentials form.
            self.previous_email = most_recent.data.get("email")

    async def _async_validate_and_get_accounts(
        self, email: str, password: str
    ) -> dict[str, Any]:
        """Validate credentials and download the user's account information.

        ====== WHAT THIS HELPER DOES ======
        This is the main validation worker for step 1. It creates the API client,
        attempts login, fetches account data, and converts any failures into
        structured error information that the UI can display.

        ====== ERROR HANDLING STRATEGY ======
        Different failures need different user feedback:
        - Auth error: the login details are wrong or access is denied.
        - Connection error: the network or remote service is unavailable.
        - API error: the service responded unexpectedly.
        - Unknown error: something else went wrong.

        Returning a small result dictionary keeps the UI step simple and makes it
        easy to map backend failures onto user-friendly form errors.
        """
        try:
            # Create a fresh API client using the credentials from the form.
            # We store it on self so later steps can reuse its authenticated state.
            self.api_client = ContactEnergyApi(email, password)

            # Record a debug log that authentication is starting.
            _LOGGER.debug("Attempting to authenticate %s", email)

            # Perform the actual login request. If this fails, one of the custom
            # exceptions below should be raised.
            await self.api_client.authenticate()

            # After successful login, request the user's account information.
            self.accounts_data = await self.api_client.get_accounts()

            # Pull out the contracts list to verify that the login belongs to at
            # least one usable account.
            account_detail = self.accounts_data.get("accountDetail", {})
            contracts = account_detail.get("contracts", [])

            # If authentication succeeded but no contracts were returned, treat
            # that as a setup failure with a dedicated UI message.
            if not contracts:
                return {
                    "valid": False,
                    "error_code": "no_accounts",
                    "error_message": (
                        "No accounts found for this Contact Energy user. "
                        "Please check your account status."
                    ),
                }

            # Log the successful account lookup and report success back to the UI.
            _LOGGER.debug(
                "Successfully retrieved %s account(s) for %s",
                len(contracts),
                email,
            )
            return {"valid": True}

        except ContactEnergyAuthError as err:
            # Authentication problems usually mean incorrect credentials or a
            # login-related access issue. We return an invalid_auth code so the UI
            # can clearly communicate that the login details were rejected.
            _LOGGER.warning("Authentication failed for %s: %s", email, str(err))
            return {
                "valid": False,
                "error_code": "invalid_auth",
                "error_message": str(err),
            }

        except ContactEnergyConnectionError as err:
            # Connection problems indicate the integration could not reach Contact
            # Energy reliably. This is different from bad credentials.
            _LOGGER.error("Connection error: %s", str(err))
            return {
                "valid": False,
                "error_code": "connection_error",
                "error_message": str(err),
            }

        except ContactEnergyApiError as err:
            # Generic API problems represent Contact Energy-specific failures that
            # are not strictly auth or network issues.
            _LOGGER.error("API error: %s", str(err))
            return {
                "valid": False,
                "error_code": "api_error",
                "error_message": str(err),
            }

        except Exception as err:
            # Catch-all protection ensures the config flow shows a graceful error
            # instead of crashing Home Assistant's setup UI.
            _LOGGER.exception("Unexpected error during validation: %s", err)
            return {
                "valid": False,
                "error_code": "unknown",
                "error_message": f"An unexpected error occurred: {str(err)}",
            }

    def _get_user_form_schema(self, previous_email: str | None = None):
        """Build the schema for the credentials form shown in step 1.

        ====== WHAT A SCHEMA IS ======
        In Home Assistant, a schema is the blueprint for a form. It tells the UI
        which fields to show, which ones are required, and what type of value
        each field should accept.

        ====== HOW THIS FORM CHANGES ======
        - If a previous email exists, the form includes a checkbox asking whether
          to reuse it, plus an optional email field and a required password.
        - If no previous email exists, the form simply requires email and
          password.
        """
        # voluptuous is Home Assistant's common validation/schema library.
        # We import it here because it is only needed when building forms.
        import voluptuous as vol

        # If we have a previous email, create a schema that supports the reuse
        # option. The checkbox defaults to True for convenience.
        if previous_email:
            return vol.Schema(
                {
                    vol.Required("use_previous_email", default=True): bool,
                    vol.Optional("email"): str,
                    vol.Required("password"): str,
                }
            )

        # Otherwise require the user to enter both email and password.
        return vol.Schema(
            {
                vol.Required("email"): str,
                vol.Required("password"): str,
            }
        )

    def _get_account_selection_schema(self, choices: list[dict[str, str]]):
        """Build the schema for the multi-account selection form.

        ====== WHAT THIS HELPER DOES ======
        When the user has several available contracts, Home Assistant needs a
        form field listing those choices. This helper converts our Python list of
        choice dictionaries into the validation structure expected by
        voluptuous/Home Assistant.
        """
        # voluptuous defines the selectable field and restricts valid values to
        # the ICPs we provide.
        import voluptuous as vol

        # vol.In({...}) means the submitted value must be one of the provided
        # keys, while the matching labels are shown in the UI.
        return vol.Schema(
            {
                vol.Required("account_icp"): vol.In(
                    {choice["value"]: choice["label"] for choice in choices}
                ),
            }
        )

    def _get_single_account_confirmation_schema(self, contract: dict[str, Any]):
        """Build the schema for the single-account confirmation form.

        ====== WHAT THIS HELPER DOES ======
        If only one account is available, there is nothing meaningful to choose.
        However, the flow still needs a form submission to continue cleanly.
        This helper creates that simple confirmation schema.

        The confirmed_icp field is pre-filled with the only available ICP so that
        when the form is submitted, later code knows exactly which account to
        save.
        """
        # voluptuous is again used to describe the form field Home Assistant
        # should render and validate.
        import voluptuous as vol

        # The default ICP value is inserted into the form so the next step can
        # read it back when the user confirms.
        return vol.Schema(
            {
                vol.Required("confirmed_icp", default=contract.get("icp")): str,
            }
        )
