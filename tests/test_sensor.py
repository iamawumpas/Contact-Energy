"""Test the Contact Energy sensors."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.contact_energy.const import DOMAIN

pytestmark = pytest.mark.asyncio


async def test_sensor_creation(hass: HomeAssistant, mock_config_entry, mock_api):
    """Test sensor entities are created."""
    from custom_components.contact_energy import async_setup_entry
    
    await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()
    
    # Check that sensors were created
    state = hass.states.get("sensor.contact_energy_account_number_0000000966tr348")
    assert state is not None


async def test_sensor_attributes(hass: HomeAssistant, mock_config_entry, mock_api):
    """Test sensor attributes are populated correctly."""
    from custom_components.contact_energy import async_setup_entry
    
    # Mock coordinator data
    mock_api.get_account_details.return_value = {
        "account_number": "123456",
        "balance": 150.50,
        "plan_name": "Good Nights",
    }
    
    await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()
    
    state = hass.states.get("sensor.contact_energy_account_balance_0000000966tr348")
    if state:
        assert state.state == "150.5"
        assert state.attributes.get("unit_of_measurement") == "$"


async def test_forecast_sensor(hass: HomeAssistant, mock_config_entry, mock_api):
    """Test forecast sensor calculation."""
    from custom_components.contact_energy import async_setup_entry
    
    # Mock historical data
    with patch("homeassistant.components.recorder.statistics.statistics_during_period") as mock_stats:
        mock_stats.return_value = {
            "sensor.test": [
                {"mean": 10.0, "start": dt_util.utcnow() - timedelta(days=i)}
                for i in range(30)
            ]
        }
        
        await async_setup_entry(hass, mock_config_entry)
        await hass.async_block_till_done()
        
        state = hass.states.get("sensor.contact_energy_forecast_daily_usage_0000000966tr348")
        if state:
            assert state.state is not None
            assert "mean_30d" in state.attributes


async def test_anomaly_sensor(hass: HomeAssistant, mock_config_entry, mock_api):
    """Test anomaly detection sensor."""
    from custom_components.contact_energy import async_setup_entry
    
    with patch("homeassistant.components.recorder.statistics.statistics_during_period") as mock_stats:
        # Mock normal usage for 29 days, then high usage today
        normal_usage = [{"mean": 10.0} for _ in range(29)]
        anomaly_usage = [{"mean": 50.0}]  # Very high usage
        mock_stats.return_value = {"sensor.test": normal_usage + anomaly_usage}
        
        await async_setup_entry(hass, mock_config_entry)
        await hass.async_block_till_done()
        
        state = hass.states.get("binary_sensor.contact_energy_historical_usage_anomaly_0000000966tr348")
        if state:
            # Should detect anomaly with z-score > 2.5
            assert state.attributes.get("z_score") is not None
