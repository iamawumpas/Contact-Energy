# Changelog

## 0.3.8

### Changes

• Documentation and changelog updates
• Documentation and changelog updates
• API client enhancements and authentication improvements
• DataUpdateCoordinator implementation with 8-hour polling
• Integration metadata and version updates
• Energy Dashboard sensor implementation and statistics integration
• Integration metadata and version updates
• Energy Dashboard sensor implementation and statistics integration

### Commits

• Release 0.3.7 (fd082c5)
• Release 0.3.6 (d4f9c29)
• Release 0.3.5 (08dd21d)
• fix: remove erroneous 0.3.5 entry from CHANGELOG.md (c22e55c)
• refactor: remove file lists from changelog and release notes (04c848f)
• Release 0.3.4 (fc08659)
• feat: integrate charting sensors and reduce API error log spam (98eab8e)
• Release 0.3.3 (b359402)
• Release 0.3.2 (d7dd439)
• Release 0.3.1 (0fa7e9b)
• Improve release.sh: Add error handling and GitHub release creation checks (c58bccc)

**Note**: This release includes uncommitted changes from the working directory.


## 0.3.7

### Changes

• Documentation and changelog updates
• Documentation and changelog updates
• API client enhancements and authentication improvements
• DataUpdateCoordinator implementation with 8-hour polling
• Integration metadata and version updates
• Energy Dashboard sensor implementation and statistics integration
• Integration metadata and version updates
• Energy Dashboard sensor implementation and statistics integration

### Commits

• Release 0.3.6 (d4f9c29)
• Release 0.3.5 (08dd21d)
• fix: remove erroneous 0.3.5 entry from CHANGELOG.md (c22e55c)
• refactor: remove file lists from changelog and release notes (04c848f)
• Release 0.3.4 (fc08659)
• feat: integrate charting sensors and reduce API error log spam (98eab8e)
• Release 0.3.3 (b359402)
• Release 0.3.2 (d7dd439)
• Release 0.3.1 (0fa7e9b)
• Improve release.sh: Add error handling and GitHub release creation checks (c58bccc)

**Note**: This release includes uncommitted changes from the working directory.


## 0.3.6

### Changes

• Chart sensors now use the recommended Home Assistant database executor for statistics queries
• Fixes warning: 'Detected code that accesses the database without the database executor'

### Technical Details
- Replaced hass.async_add_executor_job(statistics_during_period, ...) with recorder.get_instance(hass).async_add_executor_job(...)
- Ensures async safety and performance for database access

### User Impact
- No more Home Assistant warnings about unsafe database access
- Improved reliability and compatibility for future Home Assistant versions


## 0.3.5

### Changes

• Fixed AttributeError in chart sensors - timestamps now properly converted to datetime objects
• Reduced 502 API error logging from WARNING to DEBUG level (these errors are common and expected)
• Chart sensors now correctly handle statistics database timestamps

### Technical Details

**Chart Sensor Fixes:**
- Fixed `ContactEnergyChartHourlySensor.async_update()` to convert timestamp floats to datetime before calling `.isoformat()`
- Fixed `ContactEnergyChartDailySensor.async_update()` to convert timestamp floats to datetime before calling `.date().isoformat()`
- Resolves `AttributeError: 'float' object has no attribute 'isoformat'` and `'float' object has no attribute 'date'`

**API Error Logging:**
- 502 errors now logged at DEBUG level after retry exhaustion (was WARNING)
- Added specific handling for UnknownError exceptions in `async_get_usage()` to log at DEBUG level
- Only non-502 errors are logged at WARNING level after retries exhausted
- Reduces log spam from Contact Energy API's frequent temporary unavailability

### User Impact

- Chart sensors now work correctly without errors
- Much cleaner logs - 502 errors only visible when debug logging is enabled
- Better reliability for ApexCharts integration


## 0.3.4

### Changes

• Added retry logic and exponential backoff for API requests
• Implemented working Contact Energy usage data endpoint
• Added custom exception classes for better error handling
• Implemented Energy Dashboard integration with Statistics database
• Enhanced integration setup and unload procedures
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.3.4 (fc08659)
• feat: integrate charting sensors and reduce API error log spam (98eab8e)
• Release 0.3.3 (b359402)


## 0.3.3

### Changes

• Enhanced integration setup and unload procedures
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.3.3 (ed64865)
• Release 0.3.2 (d7dd439)


## 0.3.2

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.3.2 (1c2b7dc)


## 0.3.1

### Changes

• Added retry logic and exponential backoff for API requests
• Added custom exception classes for better error handling
• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.3.1 (0fa7e9b)
• Improve release.sh: Add error handling and GitHub release creation checks (c58bccc)


## 0.3.0

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.3.0 (cd3580b)


## 0.2.8

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.8 (a5d210f)


## 0.2.7

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.7 (4f68a04)


## 0.2.6

### Changes

• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.6 (332aab2)


## 0.2.5

### Changes

• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.5 (7dad28f)


## 0.2.4

### Changes

• Added custom exception classes for better error handling
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.4 (3732868)


## 0.2.3

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Implemented 8-hour polling DataUpdateCoordinator
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.3 (cb9839a)


## 0.2.2

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Enhanced integration setup and unload procedures
• Implemented proper coordinator and platform initialization
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.2 (6c20cc2)


## 0.2.1

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.1 (7696f70)


## 0.2.0

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.2.0 (cc4db5b)


## 0.1.12

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.12 (5fbd6c9)


## 0.1.11

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.11 (9bb7ab5)


## 0.1.10

### Changes

• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.10 (bc8a638)


## 0.1.9

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.9 (15cfb3b)


## 0.1.8

### Changes

• Implemented Energy Dashboard integration with Statistics database
• Added energy consumption tracking for Home Assistant Energy Dashboard
• Added cost tracking and energy cost statistics
• Added free/off-peak energy tracking
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.8 (fbdc51c)


## 0.1.7

### Changes

• Updated config flow validation schema and UI selectors
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.7 (b0a9dae)
• fix(config_flow): add explicit handler registration decorator for HA discovery (71e7c63)


## 0.1.6

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.6 (7a8d5a5)
• debug: add logging to trace config flow module loading (aab8572)
• fix(config_flow): use canonical ConfigFlow class name and add selector compatibility fallback (bd2545d)


## 0.1.5

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.5 (7522e3b)
• fix(config_flow): register handler correctly and move validation into class; set domain attribute (1fc037d)


## 0.1.4

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.4 (e816f99)
• chore: rebuild changelog and release notes (111ed6e)
• docs(changelog): clean headings and remove artifacts; align with release notes (b99a81f)


## 0.1.3

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.3 (6aff2eb)
• chore: rebuild changelog and release notes (3e659b8)


## 0.1.2

### Changes

• Fixed critical config flow registration bug (changed DOMAIN class attribute to domain)
• Removed duplicate import statements in config flow
• Enhanced error handling and user-friendly error messages
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.2 (80a5e4e)
• chore: rebuild changelog and release notes (2825f9e)


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
• Updated integration version metadata

### Commits

• Release 0.1.1 (2e974b5)
• docs: improve 0.1.0 changelog with milestone details (a6c2caa)


## 0.1.0

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.1.0 (ffa2ee3)


## 0.0.4

### Changes

• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.0.4 (b7ace34)
• chore: rebuild changelog and release notes (4610db2)


## 0.0.3

### Changes

• Removed duplicate import statements in config flow
• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages
• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added custom exception classes for better error handling
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.0.3 (d6aae04)


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
• Updated integration version metadata

### Commits

• Release 0.0.2 (eae721b)


## 0.0.1

### Changes

• Updated user interface strings and translations
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Commits

• Release 0.0.1 (3739439)
• Initial commit (cef2939)


