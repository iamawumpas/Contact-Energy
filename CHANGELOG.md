# Changelog

## 0.2.6

### Changes

Critical hotfix for coordinator data flow issue preventing sensors from receiving API data.

Urgent coordinator fixes:
• Enhanced coordinator debugging to track data flow from API to sensors
• Fixed coordinator exception handling that was silently failing and returning empty data
• Changed datetime.now() to datetime.utcnow() to avoid potential timezone issues
• Added comprehensive error logging throughout coordinator execution path
• Made coordinator more robust by continuing even if account details are missing
• Elevated debug messages to warnings/errors for better visibility during troubleshooting

This hotfix addresses the core issue where API calls succeed but sensors receive empty coordinator data, causing persistent "Unknown" values despite successful API responses.


## 0.2.5

### Changes

Fixed sensor data access by mapping to correct Contact Energy API response structure.

Critical fixes:
• Fixed coordinator data flow - sensors were receiving empty data despite successful API calls
• Mapped all sensors to correct Contact Energy API response fields based on actual API structure
• Account Balance: accountDetail.accountBalance.currentBalance  
• Customer Name: accountDetail.nickname
• Account Number: accountDetail.id
• Service Address: contracts[].premise.supplyAddress.shortForm
• Meter Serial: contracts[].devices[0].serialNumber
• Next Read Date: contracts[].devices[0].nextMeterReadDate
• Last Read Date: contracts[].devices[0].registers[0].previousMeterReadingDate
• Next Bill: accountDetail.nextBill.amount and .date
• Last Payment: accountDetail.payments[0].amount (with $ parsing)
• Enhanced debugging and error handling throughout data access paths

This release should resolve the "Unknown" values in account information sensors by properly accessing the Contact Energy API response structure.


## 0.2.4

### Changes

Critical bug fixes for duplicate entities and API timeout handling.

Urgent fixes:
• Fixed critical duplicate entity registration bug causing "cannot be added a second time" errors during integration setup
• Consolidated entity registration into single async_add_entities call to prevent conflicts
• Increased API timeout from 30s to 60s for usage data requests to handle slow Contact Energy servers
• Enhanced error handling for API timeouts and 504 Gateway Timeout errors with better logging
• Added graceful degradation - continue processing even if some days fail to download
• Improved statistics handling to save partial data when some API calls timeout

This release resolves the integration setup failures and provides better resilience against Contact Energy's API performance issues.


## 0.2.3

### Changes

Fixed sensor data access issues that were causing "Unknown" values and implemented smart jitter for multiple accounts.

Key improvements:
• Fixed coordinator data structure mismatch - sensors were looking for 'account_details' but coordinator returned 'account_data'
• Properly extract 'accountDetail' from Contact Energy API response structure
• Added comprehensive debug logging to diagnose sensor data access issues
• Implemented ICP-hash-based jitter system to spread API calls across multiple contracts/accounts
• Usage sensors: 0-3 second base delay + 0.5-2 second random jitter based on contract ICP
• Convenience sensors: 0-2 second base delay + 0.1-1.5 second random jitter based on contract ICP
• Enhanced missing-days-only download logic with proper cumulative sum continuation from last statistics
• Improved error handling and logging throughout sensor platform

This release should resolve the widespread "Unknown" sensor values and provide better performance for users with multiple Contact Energy contracts.


## 0.2.2

### Changes

• Patch release 0.2.1 correcting versioning and introducing additional sensors incrementally.
• Added account info sensors: balance, customer name, account number, service address, plan name, next bill date, estimated next bill, meter serial, next/last read dates, rate info (daily charge, peak/off-peak, free hours), and last payment details.
• Added convenience usage/cost sensors: today, yesterday, last 7/30 days, current/last month, and free usage (today/yesterday).
• Enhanced API and coordinator to fetch detailed account data; Energy Dashboard statistics unaffected.
• No breaking changes; 8-hour refresh interval maintained.


## 0.2.1

### Changes

• Patch release 0.2.1 correcting versioning and introducing additional sensors incrementally.
• Added account info sensors: balance, customer name, account number, service address, plan name, next bill date, estimated next bill, meter serial, next/last read dates, rate info (daily charge, peak/off-peak, free hours), and last payment details.
• Added convenience usage/cost sensors: today, yesterday, last 7/30 days, current/last month, and free usage (today/yesterday).
• Enhanced API and coordinator to fetch detailed account data; Energy Dashboard statistics unaffected.
• No breaking changes; 8-hour refresh interval maintained.


## 0.2.0

### Changes

• version bump to 0.2.0
• integration is now able to download energy usage data without errors and the Energy Dashboard can now display the energy usage and free energy usage


## 0.1.12


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.11


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.10


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.9


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.8


**Note**: This release includes uncommitted changes from the working directory.


## 0.1.7

### Changes

• Updated config flow validation schema and UI selectors

### Modified Files:
• custom_components/contact_energy/config_flow.py

### Commits

• fix(config_flow): add explicit handler registration decorator for HA discovery (71e7c63)


## 0.1.6

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages

### Modified Files:
• custom_components/contact_energy/config_flow.py

### Commits

• debug: add logging to trace config flow module loading (aab8572)
• fix(config_flow): use canonical ConfigFlow class name and add selector compatibility fallback (bd2545d)


## 0.1.5

### Changes

• Updated config flow validation schema and UI selectors
• Enhanced error handling and user-friendly error messages

### Modified Files:
• custom_components/contact_energy/config_flow.py

### Commits

• fix(config_flow): register handler correctly and move validation into class; set domain attribute (1fc037d)


## 0.1.4

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/const.py
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.1.4 (ea72b75)
• chore: rebuild changelog and release notes (1e234a0)


## 0.1.3

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/const.py
• custom_components/contact_energy/manifest.json
• hacs.json

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

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/manifest.json
• hacs.json

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

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/__init__.py
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/const.py
• custom_components/contact_energy/coordinator.py
• custom_components/contact_energy/manifest.json
• custom_components/contact_energy/sensor.py
• custom_components/contact_energy/strings.json
• custom_components/contact_energy/translations/en.json
• hacs.json

### Commits

• Release 0.1.1 (2e974b5)
• docs: improve 0.1.0 changelog with milestone details (a6c2caa)


## 0.1.0

### Changes

• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/manifest.json
• hacs.json

### Commits

• Release 0.1.0 (ffa2ee3)


## 0.0.4

### Changes

• Added retry logic and exponential backoff for API requests
• Updated authentication headers and session management
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/api.py
• custom_components/contact_energy/manifest.json
• hacs.json

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

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/manifest.json
• hacs.json

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

### Modified Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/__init__.py
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/const.py
• custom_components/contact_energy/manifest.json
• custom_components/contact_energy/strings.json
• custom_components/contact_energy/translations/en.json
• hacs.json

### Commits

• Release 0.0.2 (eae721b)


## 0.0.1

### Changes

• Updated user interface strings and translations
• Added cloud_polling IoT class designation
• Updated integration version metadata

### Added Files:
• CHANGELOG.md
• README.md
• custom_components/contact_energy/__init__.py
• custom_components/contact_energy/api.py
• custom_components/contact_energy/config_flow.py
• custom_components/contact_energy/const.py
• custom_components/contact_energy/coordinator.py
• custom_components/contact_energy/manifest.json
• custom_components/contact_energy/sensor.py
• custom_components/contact_energy/services.yaml
• custom_components/contact_energy/strings.json
• custom_components/contact_energy/translations/en.json
• hacs.json

### Commits

• Release 0.0.1 (3739439)
• Initial commit (cef2939)


