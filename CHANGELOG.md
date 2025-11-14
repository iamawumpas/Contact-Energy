# Changelog

## 0.7.2

### Changes

#### sensor.py - Major Consolidation
  - Code expansion: +39 net lines (added 42, deleted 3)


## 0.7.1

### Changes

#### Clarification: Historical vs Real-Time Anomaly Detection
  - **Sensor renamed:** `ContactEnergyUsageAnomalyBinarySensor` → `ContactEnergyHistoricalAnomalyBinarySensor` to clarify that detection occurs when delayed data arrives (24-72 hours), not in real time.
  - **Entity ID updated:** `binary_sensor.contact_energy_usage_anomaly_[ICP]` → `binary_sensor.contact_energy_historical_usage_anomaly_[ICP]`
  - **Documentation clarification:** Added explicit note in README explaining Contact Energy data delay and that anomaly detection is retrospective (useful for billing errors, appliance faults, pattern analysis after data release).
  - **Translations updated:** Updated `strings.json` and `translations/en.json` to reflect "Historical Usage Anomaly" naming and clarified description: "Detects anomalies when new delayed data arrives (not real time)".
  - **Automation example updated:** Updated `Automation - Usage Anomaly Alert.yaml` with corrected entity IDs matching the historical anomaly sensor.
  
This release improves clarity around data delay limitations and sets accurate expectations for anomaly detection timing.


## 0.7.0

### Changes

#### Phase 3: Forecasting, Anomaly Detection, Alerts
  - **New forecast sensor:** Added `ContactEnergyForecastDailyUsageSensor` (EMA-based, 30-day window, alpha=2/(N+1)) to predict next day's paid usage. Attributes include method, window, alpha, mean, stddev, and 2-sigma band.
  - **New anomaly binary sensor:** Added `ContactEnergyUsageAnomalyBinarySensor` to flag today's paid usage as anomalous if z-score > 2.5 vs last 30 days. Attributes: z_score, threshold, baseline stats, today_usage.
  - **Alert automation example:** Added `Automation - Usage Anomaly Alert.yaml` showing both persistent_notification and mobile notify options. Users can choose their preferred alert method.
  - **Platform update:** Enabled binary_sensor platform in `__init__.py` to support anomaly detection.
  - **Documentation:** Updated README with a new "Phase 3: Forecasts & Alerts" section, describing new sensors, attributes, and alerting options.
  - **Entity docs:** Added clear descriptions for new sensors in `strings.json` and `translations/en.json`.

#### ApexCharts Card & Asset Updates
  - **Automation example added:** `Automation - Usage Anomaly Alert.yaml` in assets folder.

#### Why these changes?
  - These additions provide proactive insights (forecasting) and real-time anomaly detection, helping users spot unusual usage and receive alerts. The documentation and entity descriptions clarify how to use and customize these features.


## 0.6.2

### Changes

#### Bug Fix: Phase 2 Sensor State Class Warnings
  - Fixed Home Assistant warnings for Phase 2 analytics sensors using incompatible `state_class='measurement'`
  - Removed `state_class` from Average Daily Usage (7 Days) sensor
  - Removed `state_class` from Average Daily Usage (30 Days) sensor
  - Removed `state_class` from Usage Trend sensor
  - Removed `state_class` from Cost Per kWh (30 Days) sensor
  - These sensors represent computed averages and ratios, not cumulative measurements
  - Home Assistant requires `state_class='total'` or `'total_increasing'` for energy/monetary device classes, or no state_class for calculated values
  - Resolves warnings: "Entity is using state class 'measurement' which is impossible considering device class"


## 0.6.1

### Changes

#### Bug Fix: Phase 2 Sensors NameError
  - Fixed critical bug where Phase 2 analytics sensors failed to load with `NameError: name 'ContactEnergyConvenienceSensorBase' is not defined`
  - Moved `ContactEnergyConvenienceSensorBase` class definition before Phase 2 sensor classes that inherit from it
  - Python requires base classes to be defined before subclasses can reference them
  - All Phase 2 sensors now load correctly: Average Daily Usage (7/30 days), Usage Trend, Cost Per kWh
  - Integration now starts successfully without import errors


## 0.6.0

### Changes

#### Phase 2: Usage Analytics & Insights Sensors
  - Added **Average Daily Usage (7 Days)** sensor calculating mean daily consumption over the last week
  - Added **Average Daily Usage (30 Days)** sensor for monthly usage patterns
  - Added **Usage Trend** sensor comparing last 7 days vs previous 7 days with percentage change
  - Added **Cost Per kWh (30 Days)** sensor showing actual average cost efficiency over time

#### Technical Details
  - All analytics sensors leverage existing statistics data (no additional API calls)
  - Sensors automatically recalculate on coordinator updates
  - Provide actionable insights through state attributes (period comparisons, trend direction, calculations)
  - Support multi-property setups with unique ICP identification
  - Foundation for future Phase 3 features (forecasting, anomaly detection, alerts)

#### Benefits
  - ✅ **Usage Insights:** Understand daily consumption patterns and trends
  - ✅ **Cost Analysis:** Track actual cost per kWh to verify pricing and identify savings opportunities
  - ✅ **Trend Detection:** Automatically detect increasing or decreasing usage patterns
  - ✅ **Data-Driven Decisions:** Rich attributes provide context for energy management decisions


## 0.5.2

### Changes

#### Documentation
  - Added new Markdown Card Example section to README demonstrating Account Details Summary card
  - Card displays comprehensive account information: customer details, billing, rates, and usage statistics
  - Documentation includes feature highlights: automatic formatting, highlighted sensors, custom styling

#### Assets
  - Added Account Details Summary Example.yaml template file for markdown card configuration
  - Created image-4.png screenshot showing part of the Account Details Summary card 


## 0.5.1

### Changes

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts


## 0.5.0

### Changes

#### Phase 1: Enhanced Account Information Sensors
  - Added **Payment History** sensor displaying total payment count with last 5 payments as attributes (dates, amounts, methods)
  - Added **Full Address** sensor with complete property address breakdown (street number/name/type, suburb, city, postcode, region, premise type)
  - Added **Meter Register** sensor showing current meter reading with up to 3 register details (current/previous readings, types, multipliers, dates)
  - Added **Contract Details** sensor displaying contract status with comprehensive attributes (contract ID, dates, term length, network provider, meter type, plan information)

#### Technical Details
  - All new sensors extract data from existing `/accounts/v2` API response (zero additional API calls)
  - Maintains backward compatibility with existing sensors
  - Foundation for Phase 2 analytics features


## 0.4.17

### Changes

#### Assets
  - Added legend marker configuration to hourly usage chart example (square markers with inverseOrder)


## 0.4.16

### Changes

#### Assets
  - Fixed hourly usage chart example to use delta values directly (removed incorrect delta calculation)
  - Added date filtering to optimize y-axis auto-scaling for visible data range
  - Swapped series order so Paid usage displays on top of Free usage
  - Added explicit color mapping: Paid (orange), Free (blue)
  - Changed update interval from 12h to 6h for more frequent updates


## 0.4.15

### Changes

#### Bug Fix: Email Sensor
  - Fixed email sensor to use login email from config entry instead of API
  - Contact Energy API does not return email address in account details
  - Sensor now displays the email address used to log in to the integration


## 0.4.14

### Changes

#### Documentation
  - Added documentation for multiple properties and accounts support
  - Documented sensor naming with ICP suffixes for multi-instance setups
  - Added use case examples (rental properties, holiday homes, family accounts)


## 0.4.13

### Changes

#### sensor.py - Major Consolidation
  - Added new sensor(s): ContactEnergyEmailSensor
  - New sensor displays account email address from API
  - Email sensor available for use in templates and UI dashboards


## 0.4.12

### Changes

#### sensor.py - Major Consolidation
  - Added mean_type parameter to StatisticMetaData for Home Assistant 2026.11+ compatibility
  - Added unit_class to StatisticMetaData (energy / monetary) for HA 2026.11+ compatibility

#### __init__.py - Cleaner Restart Logic
  - Removed async_config_entry_first_refresh() call during setup to avoid LOADED-state warning; entities handle initial fetch
  - Simplified daily restart scheduling logic


## 0.4.11

### Changes

#### sensor.py - Major Consolidation
  - Changed daily chart sensors to use ISO 8601 datetime format with timestamps at 23:59:59
  - Converted chart sensor values from cumulative totals to delta values (daily usage)
  - Delta values use absolute values (no negative numbers)

#### Documentation
  - Documentation updates and improvements

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.10

### Changes

#### Documentation
  - Documentation updates and improvements

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.9

### Changes

#### Documentation
  - Documentation updates and improvements

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.8

### Changes

#### sensor.py - Major Consolidation
  - Added validation to only process API responses containing actual data points
  - Statistics entries now only created when Contact Energy has released data for that date

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.7

### Changes

#### sensor.py - Major Consolidation
  - Added mean_type parameter to StatisticMetaData for Home Assistant 2026.11+ compatibility

#### __init__.py - Cleaner Restart Logic
  - Fixed async thread safety issue with hass.async_create_task in daily restart scheduler
  - Replaced lambda function with proper async wrapper to prevent RuntimeError
  - Simplified daily restart scheduling logic

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.6

### Changes

#### Documentation
  - Updated documentation to reflect 60-day data collection capability
  - Removed work-in-progress notes from documentation
  - Updated daily usage chart screenshot with current visualization
  - Improved consistency and fixed spelling errors

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.5

### Changes

#### Documentation
  - Updated documentation to reflect 60-day data collection capability
  - Removed work-in-progress notes from documentation
  - Updated daily usage chart screenshot with current visualization
  - Improved consistency and fixed spelling errors

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.4

### Changes

#### sensor.py - Major Consolidation
  - Increased daily chart sensor data collection period from 30 to 60 days

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.3

### Changes

#### sensor.py - Major Consolidation
  - Changed daily chart sensors to use ISO 8601 datetime format with timestamps at 23:59:59
  - Converted chart sensor values from cumulative totals to delta values (daily usage)
  - Delta values use absolute values (no negative numbers)

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.2

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.4.1

### Changes

#### sensor.py - Major Consolidation
  - Fixed Home Assistant 2025.11 deprecation warning for async_config_entry_first_refresh()
  - Replaced with polling loop that waits for coordinator data
  - **Performance optimizations**:
    - Optimized startup delays using consistent MD5 hashing


#### Documentation
  - Removed work-in-progress notes from documentation
  - Improved consistency and fixed spelling errors


## 0.4.0

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.25

### Changes

#### Documentation
  - Removed work-in-progress notes from documentation
  - Updated daily usage chart screenshot with current visualization
  - Added comprehensive ApexCharts Card Examples section
  - Improved consistency and fixed spelling errors

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.24

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.23

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.22

### Changes

#### config_flow.py - Simplified Validation
  - Streamlined options flow with consistent schema generation
  - Enhanced error handling and user-friendly error messages
  - Improved code organization and readability

#### __init__.py - Cleaner Restart Logic
  - Enhanced integration setup and unload procedures
  - Improved coordinator and platform initialization
  - Simplified daily restart scheduling logic

#### Translations
  - Updated user interface strings and translations

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.21

### Changes

#### config_flow.py - Simplified Validation
  - Streamlined options flow with consistent schema generation
  - Improved code organization and readability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.20

### Changes

#### Documentation
  - Added comprehensive Table of Contents navigation
  - Added comprehensive ApexCharts Card Examples section
  - Improved consistency and fixed spelling errors

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.19

### Changes

#### Documentation
  - Documentation updates and improvements

#### Changelog
  - Fixed CHANGELOG.md bullet point formatting for GitHub compatibility
  - Updated all bullet points to use standard Markdown dashes

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.18

### Changes

#### Documentation
  - Removed work-in-progress notes from documentation
  - Improved consistency and fixed spelling errors

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.17

### Changes

#### Documentation
  - Removed work-in-progress notes from documentation
  - Added comprehensive ApexCharts Card Examples section
  - Improved consistency and fixed spelling errors

#### Assets
  - Updated ApexCharts card configuration examples
  - Added example configurations for hourly, daily, and monthly charts

#### Visual Assets
  - Updated integration screenshots and visual assets

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.16

### Changes

#### __init__.py - Cleaner Restart Logic
  - Added automatic daily restart at 3:00 AM (±30 minutes) for reliable API connections
  - Simplified daily restart scheduling logic

#### Documentation
  - Updated hourly chart documentation for 14-day retention
  - Improved consistency and fixed spelling errors

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.15

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.14

### Changes

#### config_flow.py - Simplified Validation
  - Fixed critical config flow registration bug (changed DOMAIN class attribute to domain)
  - Streamlined options flow with consistent schema generation
  - Improved code organization and readability

#### Translations
  - Updated user interface strings and translations

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.13

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.12

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.11

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.10

### Changes

#### api.py - Simplified API Client
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.9

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.8

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.7

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.6

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.5

### Changes

#### api.py - Simplified API Client
  - Added retry logic and exponential backoff for API requests
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.4

### Changes

#### api.py - Simplified API Client
  - Added retry logic and exponential backoff for API requests
  - Implemented working Contact Energy usage data endpoint
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### sensor.py - Major Consolidation
  - Energy Dashboard sensor implementation and statistics integration

#### __init__.py - Cleaner Restart Logic
  - Enhanced integration setup and unload procedures
  - Improved coordinator and platform initialization
  - Simplified daily restart scheduling logic

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.3

### Changes

#### __init__.py - Cleaner Restart Logic
  - Enhanced integration setup and unload procedures
  - Improved coordinator and platform initialization
  - Simplified daily restart scheduling logic

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.2

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.1

### Changes

#### api.py - Simplified API Client
  - Added retry logic and exponential backoff for API requests
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### sensor.py - Major Consolidation
  - Fixed Home Assistant 2025.11 deprecation warning for async_config_entry_first_refresh()
  - Replaced with polling loop that waits for coordinator data
  - **Performance optimizations**:
    - Optimized startup delays using consistent MD5 hashing


#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.3.0

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.8

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.7

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.6

### Changes

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.5

### Changes

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.4

### Changes

#### api.py - Simplified API Client
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.3

### Changes

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### sensor.py - Major Consolidation
  - **Performance optimizations**:
    - Optimized startup delays using consistent MD5 hashing


#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.2

### Changes

#### sensor.py - Major Consolidation
  - Energy Dashboard sensor implementation and statistics integration

#### __init__.py - Cleaner Restart Logic
  - Removed async_config_entry_first_refresh() call during setup to avoid LOADED-state warning; entities handle initial fetch
  - Simplified daily restart scheduling logic

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.1

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.2.0

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.12

### Changes

#### sensor.py - Major Consolidation
  - Energy Dashboard sensor implementation and statistics integration

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.11

### Changes

#### sensor.py - Major Consolidation
  - Energy Dashboard sensor implementation and statistics integration

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.10

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.9

### Changes

#### sensor.py - Major Consolidation
  - Energy Dashboard sensor implementation and statistics integration

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.8

### Changes

#### sensor.py - Major Consolidation
  - Energy Dashboard sensor implementation and statistics integration

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.7

### Changes

#### config_flow.py - Simplified Validation
  - Streamlined options flow with consistent schema generation
  - Improved code organization and readability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.6

### Changes

#### config_flow.py - Simplified Validation
  - Streamlined options flow with consistent schema generation
  - Enhanced error handling and user-friendly error messages
  - Improved code organization and readability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.5

### Changes

#### config_flow.py - Simplified Validation
  - Streamlined options flow with consistent schema generation
  - Enhanced error handling and user-friendly error messages
  - Improved code organization and readability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.4

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.3

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.2

### Changes

#### config_flow.py - Simplified Validation
  - Fixed critical config flow registration bug (changed DOMAIN class attribute to domain)
  - Removed duplicate import statements in config flow
  - Enhanced error handling and user-friendly error messages
  - Improved code organization and readability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.1

### Changes

#### config_flow.py - Simplified Validation
  - Streamlined options flow with consistent schema generation
  - Enhanced error handling and user-friendly error messages
  - Improved code organization and readability

#### api.py - Simplified API Client
  - Implemented working Contact Energy usage data endpoint
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### coordinator.py - Streamlined Data Flow
  - Implemented 8-hour polling DataUpdateCoordinator
  - Cleaner, more predictable data flow to all sensor entities

#### sensor.py - Major Consolidation
  - Energy Dashboard sensor implementation and statistics integration

#### __init__.py - Cleaner Restart Logic
  - Enhanced integration setup and unload procedures
  - Improved coordinator and platform initialization
  - Simplified daily restart scheduling logic

#### Translations
  - Updated user interface strings and translations

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.1.0

### Changes

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.0.4

### Changes

#### api.py - Simplified API Client
  - Added retry logic and exponential backoff for API requests
  - Updated authentication headers and session management
  - Improved code readability and maintainability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.0.3

### Changes

#### config_flow.py - Simplified Validation
  - Removed duplicate import statements in config flow
  - Streamlined options flow with consistent schema generation
  - Enhanced error handling and user-friendly error messages
  - Improved code organization and readability

#### api.py - Simplified API Client
  - Added retry logic and exponential backoff for API requests
  - Updated authentication headers and session management
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.0.2

### Changes

#### config_flow.py - Simplified Validation
  - Streamlined options flow with consistent schema generation
  - Improved code organization and readability

#### api.py - Simplified API Client
  - Added retry logic and exponential backoff for API requests
  - Updated authentication headers and session management
  - Added custom exception classes for better error handling
  - Improved code readability and maintainability

#### __init__.py - Cleaner Restart Logic
  - Enhanced integration setup and unload procedures
  - Improved coordinator and platform initialization
  - Simplified daily restart scheduling logic

#### Translations
  - Updated user interface strings and translations

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


## 0.0.1

### Changes

#### Translations
  - Updated user interface strings and translations

#### Documentation
  - Documentation updates and improvements

#### Metadata
  - Added cloud_polling IoT class designation


