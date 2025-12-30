"""Config flow for Contact Energy integration.

This module handles the user interaction when adding a Contact Energy integration
to Home Assistant. It presents configuration forms and validates user input such
as account credentials.
"""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class ContactEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Contact Energy.

    This class manages the step-by-step configuration process when users add the
    Contact Energy integration to their Home Assistant instance. It validates input
    and creates the configuration entry.
    """

    # Increment this when you make changes to the config flow structure
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step.

        This is the first step shown to the user when adding the integration.
        If user_input is provided, it means the user has filled in the form and
        we should create the config entry. Otherwise, show the form for user input.

        Args:
            user_input: Dictionary containing user-provided values from the form,
                       or None if this is the first call to show the form.

        Returns:
            A FlowResult containing either a form to display or the created entry.
        """
        # If user has already submitted the form with their data
        if user_input is not None:
            # Create and return the config entry with user's data
            return self.async_create_entry(title="Contact Energy", data=user_input)

        # Show the configuration form to the user for the first time
        return self.async_show_form(step_id="user")
