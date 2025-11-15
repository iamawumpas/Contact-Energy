"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import patch, MagicMock
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.contact_energy.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_config_entry():
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
        unique_id="test_unique_id",
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
                "address": "123 Test St, Auckland",
                "account_number": "123456",
            }
        ]
        api_instance.get_account_details.return_value = {
            "account_number": "123456",
            "balance": 150.50,
            "plan_name": "Good Nights",
            "customer_name": "Test User",
            "email": "test@example.com",
        }
        api_instance.get_usage_data.return_value = {
            "daily": [
                {"date": "2025-11-14", "paid": 15.5, "free": 2.3},
                {"date": "2025-11-13", "paid": 14.2, "free": 2.1},
            ],
            "hourly": [
                {"datetime": "2025-11-14T10:00:00", "paid": 0.8, "free": 0.2},
            ],
        }
        yield api_instance


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    with patch("custom_components.contact_energy.coordinator.ContactEnergyDataUpdateCoordinator") as mock:
        coordinator = MagicMock()
        coordinator.data = {
            "account_details": {
                "account_number": "123456",
                "balance": 150.50,
            },
            "usage": {
                "today": {"paid": 15.5, "free": 2.3},
                "yesterday": {"paid": 14.2, "free": 2.1},
            },
        }
        coordinator.last_update_success = True
        mock.return_value = coordinator
        yield coordinator
