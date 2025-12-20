# Changelog

## 0.0.6

### Changes

#### api.py - Simplified API Client
  - Added retry logic and exponential backoff for API requests
  - Updated authentication headers and session management
  - Improved code readability and maintainability

#### coordinator.py - Streamlined Data Flow
  - Significant expansion: +51 net lines (added 84, deleted 33)
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### __init__.py - Cleaner Restart Logic
  - Enhanced integration setup and unload procedures
  - Improved coordinator and platform initialization
  - Simplified daily restart scheduling logic


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


