"""Test the Contact Energy config flow."""
import pytest
from unittest.mock import patch, MagicMock
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.contact_energy.const import DOMAIN

pytestmark = pytest.mark.asyncio


async def test_form_user(hass):
    """Test we get the user form."""
    from custom_components.contact_energy.config_flow import ContactEnergyConfigFlow
    
    flow = ContactEnergyConfigFlow()
    flow.hass = hass
    
    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"


async def test_form_user_success(hass):
    """Test successful config flow."""
    from custom_components.contact_energy.config_flow import ContactEnergyConfigFlow
    
    with patch("custom_components.contact_energy.api.ContactEnergyApi") as mock_api:
        api_instance = mock_api.return_value
        api_instance.login.return_value = True
        api_instance.get_accounts.return_value = [
            {"icp": "0000000966TR348", "address": "123 Test St"}
        ]
        
        flow = ContactEnergyConfigFlow()
        flow.hass = hass
        
        result = await flow.async_step_user(
            {
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "testpassword",
            }
        )
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "Contact Energy"
        assert result["data"][CONF_EMAIL] == "test@example.com"


async def test_form_user_invalid_auth(hass):
    """Test invalid authentication."""
    from custom_components.contact_energy.config_flow import ContactEnergyConfigFlow
    
    with patch("custom_components.contact_energy.api.ContactEnergyApi") as mock_api:
        api_instance = mock_api.return_value
        api_instance.login.side_effect = Exception("Invalid credentials")
        
        flow = ContactEnergyConfigFlow()
        flow.hass = hass
        
        result = await flow.async_step_user(
            {
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "wrongpassword",
            }
        )
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert "errors" in result
