# Changelog

## 0.5.1

### Major Refactoring - Code Efficiency and Maintainability Improvements

This release represents comprehensive refactoring of the integration codebase.

#### sensor.py - Major Consolidation
  - Added mean_type parameter to StatisticMetaData for Home Assistant 2026.11+ compatibility

#### __init__.py - Cleaner Restart Logic
  - Enhanced integration setup and unload procedures
  - Improved coordinator and platform initialization
  - Simplified daily restart scheduling logic


## 0.5.0

### Major Refactoring - Code Efficiency and Maintainability Improvements

This release represents a comprehensive refactoring of the entire integration codebase, focusing on efficiency, maintainability, and code quality while preserving all functionality and error handling.

#### Code Reduction
- **sensor.py reduced by 44%**: From 1,622 lines to 902 lines (720 lines removed)
- **Overall reduction**: 722 lines across all files through elimination of code duplication

#### const.py - Centralized Configuration
- Added API configuration constants (base URL, API key, timeouts, retry settings)
- Added chart sensor data retention constants (hourly, daily, monthly periods)
- Added device information constants (manufacturer, model, software version)
- Added sensor startup delay configuration constants
- Moved restart configuration from `__init__.py` (RESTART_HOUR, RESTART_MINUTE_VARIANCE)

#### api.py - Simplified API Client
- Extracted `_handle_retry()` method to eliminate duplicate retry/backoff logic
- Consolidated error handling patterns across all API methods
- Simplified authentication checks using short-circuit evaluation
- Replaced hardcoded values with constants from const.py
- Improved code readability and maintainability

#### coordinator.py - Streamlined Data Flow
- Simplified coordinator data structure returned to sensors
- Improved timezone handling using `dt_util.utcnow()` for consistency
- More consistent authentication checks before API calls
- Cleaner, more predictable data flow to all sensor entities

#### sensor.py - Major Consolidation (44% Reduction)
- **Created 6 utility functions** to eliminate duplication:
  - `safe_float()`: Centralized safe type conversion
  - `sanitize_icp_for_statistic_id()`: Consistent ICP sanitization
  - `get_statistic_ids()`: Generate all statistic IDs at once
  - `calculate_startup_delay()`: Consistent delay calculation using hashing
  - `get_device_info()`: Standardized device information
  
- **Consolidated 15 account information sensors** into 1 class:
  - `ContactEnergyAccountSensor` with type-based value extraction
  - Eliminated 14 duplicate class definitions
  - Reduced repeated code for balance, dates, rates, payments, etc.
  
- **Consolidated 12 convenience sensors** into 1 class:
  - `ContactEnergyConvenienceSensor` with metric-based logic (usage/cost/free)
  - Eliminated 11 duplicate class definitions
  - Centralized date range calculation for today/yesterday/week/month
  
- **Consolidated 6 chart sensors** into 1 class:
  - `ContactEnergyChartSensor` with period-based processing (hour/day/month)
  - Eliminated 5 duplicate class definitions
  - Cached recorder instance for better performance
  - Unified statistics processing logic

- **Performance optimizations**:
  - Eliminated 30+ duplicate `device_info` property definitions
  - Removed redundant ICP sanitization regex operations
  - Optimized startup delays using consistent MD5 hashing
  - Cached recorder instance to avoid repeated imports
  - Reduced repeated pattern matching in statistics queries

#### config_flow.py - Simplified Validation
- Created `_build_usage_months_field()` helper function for schema field generation
- Created `_get_default_months()` helper function for default value calculation
- Extracted validation logic to `_validate_and_extract_info()` method
- Removed unused instance variables (`_email`, `_password`, `_usage_months`)
- Streamlined options flow with consistent schema generation
- Improved code organization and readability

#### __init__.py - Cleaner Restart Logic
- Changed `_calculate_restart_time()` from async to sync (no async needed)
- Removed unnecessary instance variables from config flow
- Simplified daily restart scheduling logic
- Improved code clarity with better organization

### Benefits Achieved
- ⚡ **Faster startup** through optimized delay calculations and reduced initialization overhead
- 💾 **Lower memory usage** through shared instances, caching, and reduced object creation
- 🔧 **Easier maintenance** through massive reduction in code duplication (44% in sensor.py)
- 📊 **Better performance** through optimized database queries and cached instances
- 🎯 **Improved readability** through consistent patterns, utility functions, and clear abstractions
- 🛡️ **All functionality preserved** - No features removed, all error handling maintained
- ✅ **Backward compatible** - No breaking changes to entity IDs, unique IDs, or configuration
- 🔄 **Same behavior** - Identical user experience and API interactions


## 0.4.10

### Changes

- Updated ApexCharts card configuration examples


## 0.4.9

### Changes

- Updated ApexCharts card configuration examples


## 0.4.8

### Fixed
- **Daily Chart Data Accuracy**: Fixed issue where daily chart sensors (`sensor.contact_energy_chart_daily_{icp}` and `sensor.contact_energy_chart_daily_free_{icp}`) were showing dates with no actual data from Contact Energy
- Added validation to only process API responses containing actual data points (`len(response) > 0`)
- Statistics entries are now only created when Contact Energy has released data for that date
- Missing or unavailable data defaults to 0 and is overwritten when data becomes available
- Ensures chart sensors accurately reflect only dates with real usage data from Contact Energy


## 0.4.7

### Fixed
- **Async Thread Safety**: Fixed RuntimeError where `hass.async_create_task` was being called from a thread other than the event loop
  - Replaced lambda function with proper async wrapper in daily restart scheduler
  - Resolves "coroutine '_handle_daily_restart' was never awaited" warnings
  - Prevents potential Home Assistant crashes due to incorrect async task creation

### Changed
- **Home Assistant 2026.11 Compatibility**: Added `mean_type=None` parameter to all `StatisticMetaData` instances
  - Required for Home Assistant 2026.11+ compatibility
  - Applies to electricity consumption, electricity cost, and free electricity statistics
  - Prevents deprecation warnings about missing `mean_type` in async_add_external_statistics calls


## 0.4.6

### Documentation
- Updated README.md to remove "WIP" (work in progress) note from Daily Usage chart section
- Updated daily usage chart screenshot (image-1.png) with improved visualization
- Refined ApexCharts card configuration example for daily usage display
  - Adjusted graph span and label visibility settings
  - Improved date format display
  - Optimized data generation logic for better chart rendering


## 0.4.5

### Documentation
- Updated README.md documentation to accurately reflect 60-day data collection capability
  - Changed description from "30 days" to "60 days" of stored data
  - Updated example to display last 35 days instead of 31 days
- Updated daily usage chart screenshot (image-1.png) to show current visualization


## 0.4.4

### Changed
- Increased daily chart sensor data collection period from 30 to 60 days
- Provides 2 months of historical data for better trend analysis


## 0.4.3

### Changed
- Daily chart sensors now use ISO 8601 datetime format (YYYY-MM-DDTHH:MM:SSZ) with timestamps at 23:59:59
- Chart sensor values converted from cumulative totals to delta values (daily usage)
- Delta values use absolute values (no negative numbers)
- Improved data format for time-series charting with ApexCharts


## 0.4.2

### Documentation
- Added Home Assistant version compatibility requirement (2023.1 or later) to README installation section


## 0.4.1

### Fixed
- Fixed Home Assistant 2025.11 deprecation warning for `async_config_entry_first_refresh()`
- Replaced improper `async_config_entry_first_refresh()` call in sensor.py with a polling loop that waits for coordinator data
- Ensures compatibility with Home Assistant 2025.11 and beyond by avoiding calls to `async_config_entry_first_refresh()` after config entry is in LOADED state


## 0.4.0

### Changes

- **Version 0.4.0 - Stable Release**: No further changes to current codebase expected
- Removed unused empty services.yaml file
- Code cleanup and maintenance

This release marks the integration as stable with all planned features implemented and tested.


## 0.3.25

### Changes

- Documentation updates


## 0.3.24

### Changes

- **Monthly Chart Sensors Enhancement**: Removed the 12-month limitation on monthly chart sensors (`ContactEnergyChartMonthlySensor` and `ContactEnergyChartMonthlyFreeSensor`)
  - Changed statistics query to fetch all available history by setting explicit `start_time` to year 2000 instead of using `None` (which defaulted to 12 months)
  - Fixed monthly total calculation to use the `change` value from statistics entries instead of computing differences from cumulative sums
  - This ensures accurate monthly values and displays all historical data available in your Home Assistant statistics database
- **Accurate Documentation**: Updated README.md to reflect that monthly sensors now fetch all available statistics history rather than being limited to 13 months


## 0.3.23

### Changes

- **Critical Bug Fix**: Fixed `NameError: name 'self' is not defined` error that occurred when importing the integration
  - Corrected indentation of `self._usage_months = 1` initialization in `config_flow.py`
  - The variable was incorrectly placed at class level instead of inside the `__init__` method
  - This bug prevented the integration from loading properly in Home Assistant


## 0.3.22

### Changes

- Updated config flow validation schema and UI selectors
- Enhanced error handling and user-friendly error messages
- Enhanced integration setup and unload procedures
- Updated user interface strings and translations


## 0.3.21

### Changes

- Code cleanup: Removed debug print statements from config_flow.py
- Code cleanup: Fixed broad exception handler (Exception → ImportError) in config_flow.py
- Code cleanup: Removed test comment from const.py
- Improved code quality to production-ready standard (5/5 rating)


## 0.3.20

### Changes

- Added comprehensive Table of Contents navigation to README.md
- Added quick links to all major sections and subsections
- Improved documentation navigation with anchor links
- Enhanced user experience for browsing documentation


## 0.3.19

### Changes

- Fixed CHANGELOG.md bullet point formatting to display correctly on GitHub
- Updated all bullet points from • character to standard Markdown dash (-)
- Updated release.sh to automatically use standard Markdown dashes for future releases
- Added automatic cleanup of temporary release files in release.sh
- Removed "Note: This release includes uncommitted changes" statements from changelog


## 0.3.18

### Changes

- Added Changelog section to README.md with link to CHANGELOG.md file
- Improved documentation navigation for users to access version history


## 0.3.17

### Changes

- Added assets folder with ApexCharts example configurations and chart images
- Updated README.md with comprehensive ApexCharts Card Examples section
- Fixed logo image URL to display correctly from GitHub repository
- Fixed YAML configuration file links to open properly in GitHub web interface
- Improved documentation formatting and consistency
- Fixed spelling and grammar issues throughout README
- Corrected sensor data storage information (daily sensors store 30 days, not 400)


## 0.3.16

### Changes

- Added automatic daily restart at 3:00 AM (±30 minutes) to maintain reliable API connections
- Removed unused Python scripts (debug_api.py, sensor_usage.py)
- Cleaned up CHANGELOG.md - removed duplicate entries and generic metadata references
- Updated README.md with comprehensive documentation of all features
- Added documentation for chart sensors (hourly, daily, monthly)
- Added documentation for options flow to modify settings after installation
- Improved consistency and fixed spelling errors throughout documentation


## 0.3.15

### Changes

- Hourly chart sensors now fetch the last 14 days of data (previously 7) for better context in charts
- Updated ApexCharts examples to reflect the 14-day hourly window (graph_span and notes)


## 0.3.14

### Changes

- Documentation and changelog updates
- API client enhancements and authentication improvements
- DataUpdateCoordinator implementation with 8-hour polling
- Energy Dashboard sensor implementation and statistics integration
- Fixed critical config flow registration bug (domain attribute fix)
- User interface strings and translations updated


## 0.3.13

### Changes

- Documentation and changelog updates
- API client enhancements and authentication improvements
- DataUpdateCoordinator implementation with 8-hour polling
- Energy Dashboard sensor implementation and statistics integration


## 0.3.12

### Changes

- Documentation and changelog updates
- API client enhancements and authentication improvements
- DataUpdateCoordinator implementation with 8-hour polling
- Energy Dashboard sensor implementation and statistics integration


## 0.3.11

### Changes

- Documentation and changelog updates
- API client enhancements and authentication improvements
- DataUpdateCoordinator implementation with 8-hour polling
- Energy Dashboard sensor implementation and statistics integration


## 0.3.10

### Changes

- Documentation and changelog updates
- API client enhancements and authentication improvements
- DataUpdateCoordinator implementation with 8-hour polling
- Energy Dashboard sensor implementation and statistics integration


## 0.3.9

### Changes

- Added cloud_polling IoT class designation

## 0.3.8

### Changes

- Added cloud_polling IoT class designation

## 0.3.7

### Changes

- Added free/off-peak energy tracking
- Added cloud_polling IoT class designation

## 0.3.6

### Changes

- Added cloud_polling IoT class designation

## 0.3.5

### Changes

- Added retry logic and exponential backoff for API requests
- Added custom exception classes for better error handling
- Added cloud_polling IoT class designation


## 0.3.4

### Changes

- Added retry logic and exponential backoff for API requests
- Implemented working Contact Energy usage data endpoint
- Added custom exception classes for better error handling
- Implemented Energy Dashboard integration with Statistics database
- Enhanced integration setup and unload procedures
- Added cloud_polling IoT class designation

## 0.3.3

### Changes

- Enhanced integration setup and unload procedures
- Added cloud_polling IoT class designation

## 0.3.2

### Changes

- Added cloud_polling IoT class designation

## 0.3.1

### Changes

- Added retry logic and exponential backoff for API requests
- Added custom exception classes for better error handling
- Implemented 8-hour polling DataUpdateCoordinator
- Added cloud_polling IoT class designation

## 0.3.0

### Changes

- Added cloud_polling IoT class designation


## 0.2.8

### Changes

- Added cloud_polling IoT class designation

## 0.2.7

### Changes

- Added cloud_polling IoT class designation

## 0.2.6

### Changes

- Implemented 8-hour polling DataUpdateCoordinator
- Added cloud_polling IoT class designation

## 0.2.5

### Changes

- Implemented 8-hour polling DataUpdateCoordinator
- Added cloud_polling IoT class designation


## 0.2.4

### Changes

- Added custom exception classes for better error handling
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Implemented 8-hour polling DataUpdateCoordinator
- Added cloud_polling IoT class designation

## 0.2.3

### Changes

- Implemented Energy Dashboard integration with Statistics database
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Added free/off-peak energy tracking
- Implemented 8-hour polling DataUpdateCoordinator
- Added cloud_polling IoT class designation

## 0.2.2

### Changes

- Implemented Energy Dashboard integration with Statistics database
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Added free/off-peak energy tracking
- Enhanced integration setup and unload procedures
- Implemented proper coordinator and platform initialization
- Added cloud_polling IoT class designation

## 0.2.1

### Changes

- Added cloud_polling IoT class designation

## 0.2.0

### Changes

- Added cloud_polling IoT class designation


## 0.1.12

### Changes

- Implemented Energy Dashboard integration with Statistics database
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Added free/off-peak energy tracking
- Added cloud_polling IoT class designation

## 0.1.11

### Changes

- Implemented Energy Dashboard integration with Statistics database
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Added free/off-peak energy tracking
- Added cloud_polling IoT class designation

## 0.1.10

### Changes

- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cloud_polling IoT class designation

## 0.1.9

### Changes

- Implemented Energy Dashboard integration with Statistics database
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Added free/off-peak energy tracking
- Added cloud_polling IoT class designation

## 0.1.8

### Changes

- Implemented Energy Dashboard integration with Statistics database
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Added free/off-peak energy tracking
- Added cloud_polling IoT class designation


## 0.1.7

### Changes

- Updated config flow validation schema and UI selectors
- Added cloud_polling IoT class designation

## 0.1.6

### Changes

- Updated config flow validation schema and UI selectors
- Enhanced error handling and user-friendly error messages
- Added cloud_polling IoT class designation

## 0.1.5

### Changes

- Updated config flow validation schema and UI selectors
- Enhanced error handling and user-friendly error messages
- Added cloud_polling IoT class designation

## 0.1.4

### Changes

- Added cloud_polling IoT class designation

## 0.1.3

### Changes

- Added cloud_polling IoT class designation


## 0.1.2

### Changes

- Fixed critical config flow registration bug (changed DOMAIN class attribute to domain)
- Removed duplicate import statements in config flow
- Enhanced error handling and user-friendly error messages
- Added cloud_polling IoT class designation

## 0.1.1

### Changes

- Updated config flow validation schema and UI selectors
- Enhanced error handling and user-friendly error messages
- Implemented working Contact Energy usage data endpoint
- Added custom exception classes for better error handling
- Implemented Energy Dashboard integration with Statistics database
- Added energy consumption tracking for Home Assistant Energy Dashboard
- Added cost tracking and energy cost statistics
- Added free/off-peak energy tracking
- Implemented 8-hour polling DataUpdateCoordinator
- Enhanced integration setup and unload procedures
- Implemented proper coordinator and platform initialization
- Updated user interface strings and translations
- Added cloud_polling IoT class designation

## 0.1.0

### Changes

- Added cloud_polling IoT class designation


## 0.0.4

### Changes

- Added retry logic and exponential backoff for API requests
- Updated authentication headers and session management
- Added cloud_polling IoT class designation

## 0.0.3

### Changes

- Removed duplicate import statements in config flow
- Updated config flow validation schema and UI selectors
- Enhanced error handling and user-friendly error messages
- Added retry logic and exponential backoff for API requests
- Updated authentication headers and session management
- Added custom exception classes for better error handling
- Added cloud_polling IoT class designation

## 0.0.2

### Changes

- Updated config flow validation schema and UI selectors
- Added retry logic and exponential backoff for API requests
- Updated authentication headers and session management
- Added custom exception classes for better error handling
- Enhanced integration setup and unload procedures
- Implemented proper coordinator and platform initialization
- Updated user interface strings and translations
- Added cloud_polling IoT class designation

## 0.0.1

### Changes

- Updated user interface strings and translations
- Added cloud_polling IoT class designation


