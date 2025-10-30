# Changelog

## 0.3.17

### Changes

• Added assets folder with ApexCharts example configurations and chart images
• Updated README.md with comprehensive ApexCharts Card Examples section
• Fixed logo image URL to display correctly from GitHub repository
• Fixed YAML configuration file links to open properly in GitHub web interface
• Improved documentation formatting and consistency
• Fixed spelling and grammar issues throughout README
• Corrected sensor data storage information (daily sensors store 30 days, not 400)


## 0.3.16

### Changes

• Added automatic daily restart at 3:00 AM (±30 minutes) to maintain reliable API connections
• Removed unused Python scripts (debug_api.py, sensor_usage.py)
• Cleaned up CHANGELOG.md - removed duplicate entries and generic metadata references
• Updated README.md with comprehensive documentation of all features
• Added documentation for chart sensors (hourly, daily, monthly)
• Added documentation for options flow to modify settings after installation
• Improved consistency and fixed spelling errors throughout documentation


## 0.3.15

### Changes

• Hourly chart sensors now fetch the last 14 days of data (previously 7) for better context in charts
• Updated ApexCharts examples to reflect the 14-day hourly window (graph_span and notes)


## 0.3.14

### Changes

• Documentation and changelog updates
• API client enhancements and authentication improvements
• DataUpdateCoordinator implementation with 8-hour polling
• Energy Dashboard sensor implementation and statistics integration
• Fixed critical config flow registration bug (domain attribute fix)
• User interface strings and translations updated

**Note**: This release includes uncommitted changes from the working directory.


## 0.3.13

### Changes

• Documentation and changelog updates
• API client enhancements and authentication improvements
• DataUpdateCoordinator implementation with 8-hour polling
• Energy Dashboard sensor implementation and statistics integration

**Note**: This release includes uncommitted changes from the working directory.


## 0.3.12

### Changes

• Documentation and changelog updates
• API client enhancements and authentication improvements
• DataUpdateCoordinator implementation with 8-hour polling
• Energy Dashboard sensor implementation and statistics integration

**Note**: This release includes uncommitted changes from the working directory.


## 0.3.11

### Changes

• Documentation and changelog updates
• API client enhancements and authentication improvements
• DataUpdateCoordinator implementation with 8-hour polling
• Energy Dashboard sensor implementation and statistics integration

**Note**: This release includes uncommitted changes from the working directory.


## 0.3.10

### Changes

• Documentation and changelog updates
• API client enhancements and authentication improvements
• DataUpdateCoordinator implementation with 8-hour polling
• Energy Dashboard sensor implementation and statistics integration

**Note**: This release includes uncommitted changes from the working directory.


## 0.3.9

### Changes

• Added cloud_polling IoT class designation

## 0.3.8

### Changes

• Added cloud_polling IoT class designation

## 0.3.7

### Changes

• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation

## 0.3.6

### Changes

• Added cloud_polling IoT class designation

## 0.3.5

### Changes

• Added retry logic and exponential backoff for API requests
• Added custom exception classes for better error handling
• Added cloud_polling IoT class designation


## 0.3.4

### Changes

• Added retry logic and exponential backoff for API requests
• Implemented working Contact Energy usage data endpoint
• Added custom exception classes for better error handling
• Implemented Energy Dashboard integration with Statistics database
• Enhanced integration setup and unload procedures
• Added cloud_polling IoT class designation

## 0.3.3

### Changes

• Enhanced integration setup and unload procedures
• Added cloud_polling IoT class designation

## 0.3.2

### Changes

• Added cloud_polling IoT class designation

## 0.3.1

### Changes

• Added retry logic and exponential backoff for API requests
• Added custom exception classes for better error handling
• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation

## 0.3.0

### Changes

• Added cloud_polling IoT class designation


## 0.2.8

### Changes

• Added cloud_polling IoT class designation

## 0.2.7

### Changes

• Added cloud_polling IoT class designation

## 0.2.6

### Changes

• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation

## 0.2.5

### Changes

• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation


## 0.2.4

### Changes

• Added custom exception classes for better error handling
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation

## 0.2.3

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation

## 0.2.2

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Enhanced integration setup and unload procedures
• Implemented proper coordinator and platform initialization
• Added cloud_polling IoT class designation

## 0.2.1

### Changes

• Added cloud_polling IoT class designation

## 0.2.0

### Changes

• Added cloud_polling IoT class designation


## 0.1.12

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation

## 0.1.11

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation

## 0.1.10

### Changes

• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cloud_polling IoT class designation

## 0.1.9

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation

## 0.1.8

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation


## 0.1.7

### Changes

• Updated config flow validation schema and UI selectors
• Added cloud_polling IoT class designation

## 0.1.6

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Added cloud_polling IoT class designation

## 0.1.5

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Added cloud_polling IoT class designation

## 0.1.4

### Changes

• Added cloud_polling IoT class designation

## 0.1.3

### Changes

• Added cloud_polling IoT class designation


## 0.1.2

### Changes

• Fixed critical config flow registration bug (changed DOMAIN class attribute to domain)
• Removed duplicate import statements in config flow
• Enhanced error handling and user-friendly error messages
• Added cloud_polling IoT class designation

## 0.1.1

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Implemented working Contact Energy usage data endpoint
• Added custom exception classes for better error handling
• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Implemented 8-hour polling DataUpdateCoordinator
• Enhanced integration setup and unload procedures
• Implemented proper coordinator and platform initialization
• Updated user interface strings and translations
• Added cloud_polling IoT class designation

## 0.1.0

### Changes

• Added cloud_polling IoT class designation


## 0.0.4

### Changes

• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added cloud_polling IoT class designation

## 0.0.3

### Changes

• Removed duplicate import statements in config flow
• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added custom exception classes for better error handling
• Added cloud_polling IoT class designation

## 0.0.2

### Changes

• Updated config flow validation schema and UI selectors
• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added custom exception classes for better error handling
• Enhanced integration setup and unload procedures
• Implemented proper coordinator and platform initialization
• Updated user interface strings and translations
• Added cloud_polling IoT class designation

## 0.0.1

### Changes

• Updated user interface strings and translations
• Added cloud_polling IoT class designation


