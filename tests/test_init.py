"""Tests for the Contact Energy integration."""
import pytest
from unittest.mock import patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.contact_energy.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Contact Energy",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "testpassword",
        },
        source="user",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_api():
    """Create a mock API client."""
    with patch("custom_components.contact_energy.api.ContactEnergyApi") as mock:
        api_instance = mock.return_value
        api_instance.login.return_value = True
        api_instance.get_accounts.return_value = [
            {
                "icp": "0000000966TR348",
                "address": "123 Test St",
                "account_number": "123456",
            }
        ]
        yield api_instance


async def test_setup_entry(hass: HomeAssistant, mock_config_entry, mock_api):
    """Test successful setup of config entry."""
    from custom_components.contact_energy import async_setup_entry
    
    assert await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()
    
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_unload_entry(hass: HomeAssistant, mock_config_entry, mock_api):
    """Test unloading a config entry."""
    from custom_components.contact_energy import async_setup_entry, async_unload_entry
    
    # Setup
    await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()
    
    # Unload
    assert await async_unload_entry(hass, mock_config_entry)
    await hass.async_block_till_done()
    
    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_api_authentication_failure(hass: HomeAssistant, mock_config_entry):
    """Test handling of authentication failure."""
    from custom_components.contact_energy import async_setup_entry
    
    with patch("custom_components.contact_energy.api.ContactEnergyApi") as mock:
        api_instance = mock.return_value
        api_instance.login.return_value = False
        
        result = await async_setup_entry(hass, mock_config_entry)
        assert result is False
