# Contact Energy Integration Tests

This directory contains automated tests for the Contact Energy Home Assistant integration.

## Running Tests Locally

### Install Test Dependencies
```bash
pip install -r requirements_test.txt
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=custom_components/contact_energy --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_config_flow.py -v
```

## Test Structure

- `conftest.py` - Shared fixtures and configuration
- `test_init.py` - Integration setup/teardown tests
- `test_config_flow.py` - Config flow and options flow tests
- `test_sensor.py` - Sensor entity tests (including forecast and anomaly detection)

## GitHub Actions

Tests run automatically on:
- Push to `main` branch
- Pull requests to `main` branch
- Manual workflow dispatch

The workflow tests against:
- Python 3.11 and 3.12
- Home Assistant 2024.11.0 and 2024.12.0

## Mocking

Tests use mocked API responses to avoid hitting the real Contact Energy API. The `mock_api` fixture in `conftest.py` provides sample data for all API endpoints.

## Adding New Tests

1. Create test functions prefixed with `test_`
2. Use async/await for async functions
3. Use fixtures from `conftest.py` for common setup
4. Mock external dependencies (API calls, database queries)

Example:
```python
async def test_my_feature(hass, mock_config_entry, mock_api):
    \"\"\"Test my new feature.\"\"\"
    # Test implementation
    assert True
```
