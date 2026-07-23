# DEPRECATED - v2.0.0 Architecture

This file has been deprecated and replaced by the v2.0.0 modular architecture.

## Legacy Files (Deprecated)
- `contact_api.py` → Replaced by `api/client.py`, `api/account.py`, `api/usage.py`
- `coordinator.py` → Replaced by `coordinators/account_coordinator.py`
- `usage_coordinator.py` → Replaced by `coordinators/usage_coordinator_v2.py`
- `usage_sensor.py` → Replaced by `sensors/usage_sensors.py`
- `usage_cache.py` → Replaced by `data_managers/usage_*.py`
- `account_snapshot_cache.py` → Replaced by `data_managers/account_data.py`

## New v2.0.0 Architecture
The integration now uses a modular architecture with:
- **API Layer** (`api/`): Isolated API communication
- **Data Managers** (`data_managers/`): Caching and staleness logic
- **Coordinators** (`coordinators/`): Update scheduling and coordination
- **Sensors** (`sensors/`): Entity definitions

## Migration
The legacy files are kept for reference but are not used by the integration.
They can be safely removed in a future version once the v2.0.0 architecture
is proven stable.

## Phase 5 Complete
Phase 5 (Integration) is now complete. The main integration files (`__init__.py`
and `sensor.py`) now use the v2.0.0 architecture.
