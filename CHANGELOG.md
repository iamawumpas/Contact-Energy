# Changelog

## 0.0.5

### Changes

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities


## 0.0.4

### Changes

#### config_flow.py - Configuration Flow Updates
  - Configuration flow improvements

#### api.py - Simplified API Client
  - Updated authentication headers and session management
  - Improved code readability and maintainability

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### __init__.py - Cleaner Restart Logic
  - Significant expansion: +32 net lines (added 34, deleted 2)
  - Added automatic daily restart at 3:00 AM (±30 minutes) for reliable API connections
  - Simplified daily restart scheduling logic


