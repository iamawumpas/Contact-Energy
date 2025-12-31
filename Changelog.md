# Changelog

All notable changes to the Contact Energy integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [ 1.5.1 ]

### Fixed
- Notify sensors immediately after usage sync so cached usage attributes refresh without waiting for the next daily coordinator run

## [ 1.5.2 ]

### Fixed
- Reload cache before writing usage sensor state so attributes populate immediately after sync
- Align usage sensor unique_id schema with account/billing sensors for multi-account clarity

## [ 1.5.0 ]

### Added
- Usage data sensor `sensor.contact_energy_usage_{contract_id}` exposing cached hourly, daily, and monthly usage arrays
- Sensor state reports last successful sync timestamp
- Attributes include total, paid, free, and cost fields formatted for ApexCharts

### Fixed
- Cache reload on coordinator updates to keep attributes fresh after each sync

## [ 1.4.6 ]

### Fixed
- **Release Scripts**: Fixed release.sh and feature.sh to commit all modified files
  - Changed from staging specific files to `git add -A` 
  - Ensures all code changes are included in release commits
  - Prevents issues where code changes were documented but not committed

## [ 1.4.5 ]

### Fixed
- **v1.4.4 Code Commit**: Actually committed the free usage capping code that was missing from v1.4.4 release
  - Caps free usage at total usage when API reports free > total
  - Changed from WARNING to DEBUG logging for cleaner logs
  - This fix was intended for v1.4.4 but the code wasn't committed properly

## [ 1.4.4 ]

### Fixed
- **Free Usage Capping**: Implemented automatic capping of free usage at total usage
  - When API reports free > total (rare rounding/data quality issues), cap free at total
  - Changed from WARNING to DEBUG logging for cleaner logs
  - Eliminates warning messages for these edge cases
  - Since usage data is estimated (not billing), precision to the nearest decimal is not critical

## [ 1.4.2 ]

### Fixed
- **None Value Handling**: Fixed parsing errors when API returns None for dollarValue field
  - Updated to use `or 0.0` instead of default parameter to properly handle None values
  - Resolves "float() argument must be a string or a real number, not 'NoneType'" errors
  - Applies to all numeric fields: value, offpeakValue, unchargedValue, dollarValue
  
### Improved
- **Business Logic Clarification**: Enhanced usage calculation documentation
  - Free energy is always 0.0 kWh on days/times when free hours are not offered
  - Paid energy is 0.0 kWh when all usage occurs during free hours
  - Negative kWh values should never occur (no solar/PV buy-back in current system)
  - API data inconsistencies (free > total) are now logged as warnings

## [ 1.4.1 ]

### Fixed
- **API Response Parsing**: Handle both dict and list response formats from usage API
  - API can return `{"usage": [...]}` or `[...]` directly
  - Prevents AttributeError when API returns list format
- **Async File Operations**: Fixed blocking I/O warnings
  - File read/write operations now use executor to avoid blocking event loop
  - Resolves Home Assistant warnings about blocking calls in async context

## [ 1.4.0 ]

### Added
- **Phase 1: Usage Data Download & Caching**
  - New `usage_cache.py` module for persistent JSON storage of usage data
  - New `usage_coordinator.py` for orchestrating incremental usage data sync
  - `get_usage()` API method in `contact_api.py` for fetching hourly/daily/monthly usage data
  - Smart caching with metadata-driven incremental sync (downloads only new data after first run)
  - Atomic file operations to prevent cache corruption
  - Comprehensive logging at DEBUG/INFO/WARNING/ERROR levels
  - Performance timing on all I/O operations
  - Background sync runs independently without affecting account sensors

### Technical Details
- Usage data windows: 9 days hourly, 35 days daily, 18 months monthly
- Daily sync at 2 AM with metadata checks to minimize API calls
- Separate cache files per contract: `.usage_cache_<contract_id>.json`
- Paid usage calculated as: total - free (offpeak) - promotional (uncharged)
- Error isolation: usage failures don't break existing account sensors

### Developer Tools
- Added `feature.sh` script for beta/alpha release automation
- Excluded `feature.sh` from HACS package

### Notes
- **Beta Release**: This is Phase 1 of 5 phases leading to v2.0
- No user-facing sensors yet - data collection infrastructure only
- Next phase (v1.5.x) will expose usage data as Home Assistant sensors

## [ 1.3.1 ]

### Documentation
- Edits made to the documentation in the wiki

## [ 1.3.0 ]

### Added
- Comprehensive wiki documentation with 6 pages
  - Getting Started guide with installation and configuration steps
  - Complete sensor reference documentation
  - Dashboard examples with YAML configurations
  - Multiple accounts setup guide
  - FAQ and troubleshooting section
- Assets folder for dashboard examples and resources
- Sample dashboard.yaml with generic placeholder sensor names

### Changed
- README.md restructured with wiki links
- Updated dashboard.yaml to use generic {account}_{icp} placeholders for better usability
- Improved documentation organization with dedicated wiki pages

### Documentation
- All sensor details moved to wiki for better maintainability
- Dashboard examples now include explanations and customization tips
- Added comprehensive troubleshooting guides

## [ 1.2.0 ]

### Added
- Account Nickname sensor
- ICP sensor
- Address sensor
- Product Name sensor (plan name)
- Contract Type sensor
- Contract Status sensor
- Direct Debit status sensor
- Smooth Pay status sensor
- Prepay status sensor
- Discount Total sensor (invoice discounts applied)

### Changed
- Expanded account detail sensors from 3 to 13 sensors total
- Total sensor count increased from 13 to 24 sensors
- All contract and account information now exposed as sensors

## [ 1.1.3 ]

### Fixed
- Fixed import error with UnitOfCurrency from homeassistant.const (Home Assistant version compatibility)
- Replaced UnitOfCurrency.NZD with string constant "NZD" for better compatibility
- Resolved sensor platform import blocking call warning

## [ 1.1.2 ]

### Fixed
- Improved error logging for authentication failures and API errors
- Added validation for missing password in config entry
- Setup will now fail gracefully if password is missing instead of silently failing
- Added more descriptive error messages for 400/401/403 API responses
- Enhanced coordinator logging to help debug re-authentication issues

### Changed
- Integration setup now requires password in config entry for token refresh
- Users with older configs (v1.0.0) must reconfigure integration to store password

## [ 1.1.1 ]

### Fixed
- Store password in config entry to enable token refresh on expiry
- Coordinator now automatically re-authenticates if stored token has expired
- Improved error handling when API token becomes invalid during daily updates
- Sensors will now continue working after token expiry instead of showing API errors

## [ 1.1.0 ]

### Added
- Account information sensor platform with 10 new sensors
- Current Account Balance sensor (NZD)
- Prepay Debt Balance sensor (NZD)
- Amount Due sensor (NZD)
- Amount Paid sensor (NZD)
- Payment Due Date sensor
- Days Until Overdue sensor
- Next Bill Date sensor
- Days Until Next Bill sensor
- Refund Eligible sensor
- Maximum Refund sensor
- Correspondence Preference sensor
- Payment Method sensor
- Billing Frequency sensor
- Data coordinator for efficient API usage (updates once per day at ~01:00 AM)
- Sensors follow naming pattern: sensor.{account_name}.{attribute_name}

## [ 1.0.0 ]

### Added
- Initial stable authentication and configuration flow established
- Full Contact Energy API integration with secure token-based authentication
- Multi-account and multi-ICP support with duplicate prevention
- Single and multiple account configuration handling
- Automatic account discovery and filtering
- Comprehensive error handling with user-friendly messages
- Account nickname and ICP display in configuration dialogs
- Previous email reuse option for seamless multi-account setup
- Release automation with changelog extraction

## [ 0.0.6 ]

### Fixed
- Config entry title now uses account nickname as fallback when address is not available from API
- Multiple account selection now displays account nickname if address field is missing
- Improved handling of incomplete address data from Contact Energy API

## [ 0.0.5 ]

### Fixed
- Single account confirmation dialog no longer displays as multi-account selection
- Form field for single account confirmation now uses proper text input instead of radio button
- Account ICP label changed from "Confirm" to "Account ICP" for clarity
- Single account form now properly defaults to the account ICP value

## [ 0.0.4 ]

### Fixed
- Account nickname display in single account confirmation dialog
- Description placeholders now properly show account name and ICP number
- Confirmation form field label for single account selection

### Changed
- Improved single account confirmation dialog UI with clearer account information display
- Updated form title to "Confirm Account" for better clarity

## [ 0.0.3 ]

### Added
- Single account confirmation dialog showing account nickname and ICP
- Multiple account selection with radio button list (ICP - Address format)
- Automatic filtering of already-configured accounts from selection list
- Smart credential handling with previous email reuse option
- Detection and prevention of duplicate account additions
- Detailed user instructions for each configuration scenario

### Changed
- Enhanced config flow to handle single vs. multiple accounts
- Improved account selection display with ICP and address
- Better error message for when all accounts are already configured
- Credential form now offers choice to reuse previous email or enter new credentials
- Config entry title now shows ICP and address for easy identification

### Fixed
- Incorrect ICP and address display in account selection (was showing contract ID instead of ICP)
- Account filtering logic to properly identify already-configured accounts

## [ 0.0.2 ]

### Added
- Complete authentication flow with Contact Energy API
- Multi-step configuration process with credential validation
- Automatic account discovery and ICP detection
- Account selection for users with multiple ICPs/accounts
- Secure credential handling and token-based authentication
- Comprehensive error handling with user-friendly messages
- New API client module for Contact Energy communication
- Detailed user instructions in English translation files

### Changed
- Enhanced config flow with two-step process (credentials, then account selection)
- Improved error messages with specific guidance for users
- Updated strings.json with new configuration step definitions

## [ 0.0.1 ]

### Added
- Initial release of Contact Energy integration for Home Assistant
- Configuration flow for setting up Contact Energy account credentials
- Support for Contact Energy API integration
- HACS installation support
- Basic Home Assistant integration structure with config entries
