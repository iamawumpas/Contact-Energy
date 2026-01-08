# Changelog

All notable changes to the Contact Energy integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Changelog

All notable changes to the Contact Energy integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [ 1.7.6 ]

### Fixed
- Energy sensor start_date now persists correctly to cache file instead of remaining in memory only
- Fixed timing issue where start_date was set after coordinator had already saved cache

## [ 1.7.5 ]

### Fixed
- Fixed race condition where energy sensor and usage coordinator attempted simultaneous cache file writes
- Energy sensor now defers cache saves to coordinator, eliminating FileNotFoundError during initialization

## [ 1.7.4 ]

### Fixed
- Energy Dashboard sensors now only track new data after sensor creation, preventing historical cache data from appearing as a large spike
- Energy sensors initialize with start_date set to today, ignoring existing cached historical data
- Cumulative energy totals now filter by sensor start date to maintain accurate statistics

## [ 1.7.3 ]

### Changed
- Reduced usage sensor attribute size to fit under 16KB database limit
- Removed alias attributes (hourly_usage, hourly_data, hourly_free_data)
- Reduced decimal precision from 3 to 2 decimals (e.g., 1.23 kWh instead of 1.234 kWh)
- Sensor state now shows total record count instead of last sync timestamp
- Removed version and last_updated metadata from sensor attributes

## [ 1.7.2 ]

### Fixed
- Energy dashboard sensors now use `UnitOfEnergy.KILO_WATT_HOUR` and are no longer nested, restoring platform import on Home Assistant.

## [ 1.7.1 ]

### Added
- Added cumulative paid and free energy sensors for Home Assistant's Energy dashboard using total_increasing statistics.
- Usage cache now carries forward pruned history into cumulative baselines so Energy sensors stay monotonic.

## [ 1.7.0 ]

### Changed
- version bump.

## [ 1.6.28 ]

### Fixed
- Restored hourly electricity usage attribute names (`hourly_paid_usage`, `hourly_free_usage`, `hourly_usage`) and kept legacy aliases so ApexCharts dashboards can load hourly data again.

## [ 1.6.27 ]

### Changed
- Trimmed usage sensor attributes to paid and free series only while keeping full history windows (10 days hourly, 35 days daily, 18 months monthly) so charts stay gap-free but attributes stay under Home Assistant's size limits.
- Dropped zero/null values from exposed attributes to further reduce payload size without losing meaningful data.

## [ 1.6.26 ]

### Fixed
- Fixed TypeError in usage sensor when comparing datetime objects: "can't compare offset-naive and offset-aware datetimes"
  - Now uses timezone-aware datetime (UTC) for 7-day hourly attribute cutoff calculation

## [ 1.6.25 ]

### Changed
- Hourly data now downloads in 1-day chunks (reduced from 2-day) for maximum API stability.
- Fallback chunking for hourly data also uses 1-day chunks instead of 2-day chunks.

### Fixed
- Fixed state attributes size exceeding Home Assistant's 16KB database limit:
  - Hourly data in sensor attributes now limited to last 7 days (was all 14 days).
  - Daily data in sensor attributes now limited to last 30 days (was all 35 days).
  - Full data still cached and accessible via usage_cache_*.json files.
  - Added `hourly_displayed_count` and `daily_displayed_count` attributes showing records visible in attributes.
  - Statistics and summaries continue to use all cached data regardless of attribute limits.

## [ 1.6.24 ]

### Changed
- Hourly usage data window increased from 9 to 14 days for better historical coverage.
- Hourly data now downloads in 2-day chunks proactively to avoid API 502 errors on large date ranges.
- Empty responses from API chunks are handled gracefully without failing the entire sync.

## [ 1.6.23 ]

### Fixed
- Manual refresh now quietly skips when a sync is active or just finished, logging an info message instead of raising an error to avoid user-facing UI errors.

## [ 1.6.22 ]

### Fixed
- Corrected manual refresh handler indentation so the integration loads without import errors after adding the background-sync skip flag.

## [ 1.6.21 ]

### Fixed
- Manual refresh now suppresses the coordinator’s automatic background usage sync, ensuring only one forced sync runs and preventing overlapping calls.
- Monthly usage 404 responses are treated as no data available, avoiding repeated retry loops and noisy warnings.

## [ 1.6.20 ]

### Fixed
- Manual refresh now blocks when a sync is active or just finished, showing a clear dialog to retry after ~60s to avoid overlapping syncs and API 404s.

## [ 1.6.19 ]

### Fixed
- Manual refresh now re-authenticates with stored credentials before fetching data to avoid expired session tokens, skipping the refresh if login fails.

## [ 1.6.18 ]

### Fixed
- Daily and monthly usage now aggregate paid and free hours together instead of enforcing hourly mutual exclusivity, so both appear and stack correctly in charts.
- Peak/off-peak components for daily and monthly records are recalculated from the paid portion with safeguards against negative peak values.

## [ 1.6.17 ]

### Fixed
- **CRITICAL**: Fixed paid_usage and free_usage overlapping at same timestamps
- Enforced mutual exclusivity: when unpaid > 0, paid/peak/offpeak = 0; when unpaid = 0, free = 0
- Charts will now correctly show either paid OR free usage at each timestamp, never both

## [ 1.6.16 ]

### Fixed
- Clarified that `paid_usage` and `free_usage` are mutually exclusive (when paid > 0, free = 0 and vice versa)

### Added
- Comprehensive yearly statistics:
  - Calendar year totals and averages (total, paid, peak, offpeak, free, cost)
  - Rolling 365-day totals and averages
- Seasonal averages for NZ seasons (kWh per day):
  - Spring (Sep-Nov), Summer (Dec-Feb), Autumn (Mar-Jun), Winter (Jul-Aug)
- Daily averages in kWh per hour (total, paid, free, offpeak)
- Monthly averages in kWh per day (total, paid, free, offpeak)
- Additional monthly breakdown attributes:
  - `monthly_peak_usage` - peak usage by month
  - `monthly_offpeak_usage` - off-peak usage by month

### Changed
- **BREAKING**: Renamed sensor attributes for clarity:
  - `hourly_usage` → `hourly_total_usage`
  - `daily_usage` → `daily_total_usage`
  - `monthly_usage` → `monthly_total_usage`
- ApexCharts YAML must update attribute names to `*_total_usage` or use specific breakdowns (`*_paid_usage`, `*_free_usage`)
- Summary statistics now include comprehensive breakdowns and averages for all time periods

## [ 1.6.15 ]

### Fixed
- Authenticate on startup instead of reusing stored tokens to avoid 502 errors from expired tokens after HA restarts
- Fail setup early with a clear log if authentication fails during startup

### Changed
- Removed loading cached token/segment/bp from config entry; fresh token is always fetched on startup

## [ 1.6.14 ]

### Fixed
- Fixed sensor attributes exceeding Home Assistant's 16384 byte database storage limit
- Attributes now stay well under size limit while maintaining full graphing capability

### Changed
- Renamed attribute keys from `_data` to `_usage` for clarity (e.g., `hourly_usage` instead of `hourly_data`)
- Attributes now use dictionaries keyed by timestamp/date/month instead of duplicate list arrays
- Removed redundant detailed record lists (hourly_usage list, daily_usage list, monthly_usage list)
- Added `summary` attribute with aggregated totals for quick reference:
  - daily_total_kwh, daily_peak_kwh, daily_offpeak_kwh, daily_free_kwh, daily_cost_nzd
  - monthly_total_kwh, monthly_cost_nzd
- Each interval (hourly/daily/monthly) now has paid, free, peak, and offpeak usage dicts for ApexCharts

### Technical Details
- Attributes optimized for Home Assistant database (typically <6KB vs 16KB+ before)
- ApexCharts cards can still consume hourly_usage, daily_usage, monthly_usage dicts directly
- All usage breakdown data (peak/offpeak/paid/free) preserved in dictionaries
- Summary statistics accessible at a glance without expanding attributes in UI
- Added byte size logging for monitoring attribute payload growth

## [ 1.6.13 ]

### Fixed
- Fixed critical bug where account_id was not being passed to API client, causing 502/404 errors
- API now correctly uses account_id (ba parameter) instead of Business Partner ID for all requests
- Usage data now includes cost/dollarValue in responses (was null due to missing ba parameter)

### Changed
- Usage calculation now correctly treats off-peak hours as billed usage (not free)
- Free usage is now limited to promotional/uncharged hours only
- New usage breakdown fields: peak (peak rate), offpeak (off-peak rate), paid (peak + off-peak), free (promotional)
- All sync intervals changed to hourly (from daily) for faster testing and development
- Sensor attributes now expose peak and off-peak data separately for ApexCharts graphing

### Technical Details
- Formulas now match actual billing:
  - TOTAL = peak + offpeak + free
  - PAID = peak + offpeak
  - FREE = unpaid/promotional only
  - PEAK = consumed at peak rate
  - OFFPEAK = consumed at off-peak rate
- New ApexCharts-ready attributes: hourly_peak_data, hourly_offpeak_data (in addition to existing hourly_data, hourly_free_data)
- All usage records now include peak and offpeak fields for completeness

## [ 1.6.12 ]

### Fixed
- Added check to prevent concurrent usage syncs when refresh_data service is called
- Service now skips refresh if a sync is already in progress to avoid duplicate API calls
- Prevents issues when service is called immediately after Home Assistant restart

## [ 1.6.11 ]

### Fixed
- Fixed force_sync implementation to properly bypass time thresholds using a flag-based approach
- Service now correctly forces data download regardless of when last sync occurred
- Previous implementation was incorrectly manipulating cache metadata which got overwritten on cache reload

## [ 1.6.10 ]

### Fixed
- Fixed AttributeError in refresh_data service when accessing cache metadata
- Fixed incorrect method name in force_sync (should call async_sync_usage not sync_usage_data)
- Service now correctly accesses cache.data["metadata"] instead of cache.metadata

## [ 1.6.9 ]

### Added
- New `contact_energy.refresh_data` service to manually trigger data downloads
- Service forces immediate refresh of both account data and usage data, bypassing the normal 24-hour sync interval
- Useful for on-demand updates without waiting for scheduled syncs
- Can be called from Developer Tools, automations, scripts, or button cards

## [ 1.6.8 ]

### Fixed
- Fixed hourly sensor showing paid=0 and free=0 by using correct API fields
- Hourly data now calculates free energy from offpeakValue and unchargedValue (same as daily/monthly)
- Applied unified calculation across all intervals: free = offpeak + uncharged, paid = total - free
- This matches how daily/monthly data is properly calculated and aligns with Contact Energy API structure

## [ 1.6.7 ]

### Fixed
- Integration now continues with usage sync even if account data fetch fails
- When accounts endpoint returns server errors, integration falls back to minimal account data
- This allows usage data collection to work even when Contact Energy's accounts API is experiencing issues
- Usage sensor will populate correctly while account details may be unavailable

## [ 1.6.6 ]

### Fixed
- Removed Content-Type header from accounts API GET request (may cause 502 on some API servers)
- GET requests typically should not include Content-Type header
- Removed ba parameter from accounts endpoint URL

## [ 1.6.5 ]

### Fixed
- Added detailed error response logging for 502 errors from accounts API endpoint
- Now logs the actual error response body to help diagnose API issues

## [ 1.6.4 ]

### Fixed
- Fixed accounts endpoint by using urlencode for query parameters to avoid Home Assistant session mutation
- Added ba parameter back with empty value (required by API) using proper URL encoding
- Added debugging logs to track accounts API requests

## [ 1.6.3 ]

### Fixed
- Fixed account information API endpoint by removing malformed empty `ba` parameter that was causing 502 errors
- Account data fetch now uses correct endpoint format without query parameters

## [ 1.6.2 ]

### Fixed
- Fixed duplicate code in API response parser that was corrupting hourly/daily data logic
- Removed stray comments and duplicate paid_kwh calculation that was overwriting interval-specific logic

## [ 1.6.1 ]

### Fixed
- Fixed hourly usage data parsing to correctly handle mutually exclusive paid/free data
- Hourly intervals now use API paid/free values directly instead of calculating from components
- Daily/monthly intervals continue to calculate paid as total - free (complementary breakdown)
- Added timezone-aware datetime matching in ApexCharts data_generator for reliable data lookup
- Chart now properly fills missing dates with 0.0 values for continuous timeline display

## [ 1.6.0 ]

### Added
- **ApexCharts Hourly Usage Chart** - New sensor attributes for ApexCharts visualization
- Added `hourly_data` attribute: Dictionary of paid usage keyed by ISO datetime timestamps
- Added `hourly_free_data` attribute: Dictionary of free usage keyed by ISO datetime timestamps
- Created `assets/chart_hourly_usage.yaml` dashboard example with working ApexCharts configuration
- Updated Dashboards wiki with ApexCharts setup guides and step-by-step configuration

### Features
- View hourly usage for the last 10 days with separate series for free (blue) and paid (yellow) consumption
- Integrated with Home Assistant's ApexCharts Card custom component
- Supports template variables for single-point configuration across multiple accounts
- Automatic datetime parsing and axis formatting
- Gradient fill effects and responsive design

## [ 1.5.9 ]

### Changed
- Reduced logging severity for transient API errors (502) from ERROR/WARNING to DEBUG since retry and chunking logic handles them automatically
- Usage sync now runs quietly without alarming log messages when temporary API errors occur and are successfully recovered

## [ 1.5.8 ]

### Fixed
- Fixed race condition where usage sensor state was written before cache reload completed, causing sensor to show 0 records despite successful data sync
- Usage sensor now waits for cache reload to finish before updating Home Assistant state, ensuring hourly/daily/monthly attributes populate immediately with correct counts

## [ 1.5.7 ]

### Fixed
- Usage sensor now listens for dispatcher signals and reloads the usage cache immediately after sync, so hourly/daily/monthly attributes populate reliably

## [ 1.5.6 ]

### Fixed
- Usage sensor now registers with the sensor platform so its hourly/daily/monthly attributes populate for dashboards

## [ 1.5.5 ]

### Fixed
- Hourly usage sync now retries with brief backoff and, if needed, splits the window into 5-day chunks to avoid transient 502 errors
- Daily and monthly usage sync share the same retry helper to smooth over intermittent API hiccups

## [ 1.5.4 ]

### Fixed
- Hourly usage sync now builds the exact usage API URL (matching test_api.py) to prevent Home Assistant from mutating query params, avoiding the 502 responses that stopped hourly downloads

## [ 1.5.3 ]

### Fixed
- Usage sensor unique_id reverted to contract-based naming so entity_id matches account/billing schema without suffixes
- Hourly sync now logs a warning when skipped due to API errors (e.g., 502) for visibility

## [ 1.5.2 ]

### Fixed
- Reload cache before writing usage sensor state so attributes populate immediately after sync
- Align usage sensor unique_id schema with account/billing sensors for multi-account clarity

## [ 1.5.1 ]

### Fixed
- Notify sensors immediately after usage sync so cached usage attributes refresh without waiting for the next daily coordinator run

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
