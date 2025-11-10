# Changelog

## 0.4.1

## [0.4.1] - 2025-11-10

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


