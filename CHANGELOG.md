## v0.0.7 - 2025-10-10
UI Message Positioning

- Moved informational message from top description to appear above submit button\n- Removed problematic newline characters causing translation errors\n- Cleaner form layout with message positioned after all form fields

## v0.0.6 - 2025-10-10
Translation Fix

- Fixed HTML tags in form descriptions causing translation errors\n- Proper spacing now uses newline characters instead of HTML tags\n- Resolved UNCLOSED_TAG errors in setup form

## v0.0.5 - 2025-10-10

UI/UX Improvements

- **Improved Config Flow**: Removed continue button, entity creation happens immediately on Submit
- **Better Form Spacing**: Added spacing between form fields for better readability
- **Clearer Labels**: Changed "Initial download days" to "Initial number of days' usage to download"
- **Streamlined Setup**: Simplified setup process with immediate entity creation

## v0.0.4 - 2025-10-10

Config Flow Enhancements

- **Required Days Field**: Removed checkbox from days slider, made field required
- **User Guidance**: Added informational message about data availability delays
- **Improved UX**: Enhanced config flow with better user expectations

## v0.0.3 - 2025-10-10

Bug Fixes

- **Sensor Fixes**: Fixed monetary sensor state class compatibility
- **Balance Sensor**: Fixed account balance sensor to return numeric values instead of dict
- **Error Resolution**: Resolved "coroutine was never awaited" warnings

## v0.0.2 - 2025-10-10

Config Flow Fixes

- **Async Fix**: Fixed unawaited coroutine in config flow `_create_entry` method
- **Stability**: Improved integration startup reliability

# Changelog

## v0.0.1 - 2025-10-10

Initial release of the streamlined Contact Energy integration

### Features

- **Energy Dashboard Integration**: Direct statistics database writing for efficient memory usage
- **ApexCharts Support**: Historical data accessible via statistics queries
- **Smart Data Downloads**: Only downloads missing data after initial setup
- **Account Information Sensors**: Balance, bill dates, payment information
- **Free Energy Tracking**: Separate tracking for Contact Energy free electricity plans
- **Memory Efficient Design**: Streamlined architecture compared to existing solutions
- **8-Hour Polling**: Configurable update interval for API efficiency

### Technical Details

- Home Assistant 2023.1.0+ compatibility
- Uses Contact Energy API v2 endpoints
- Statistics-based data storage (no memory caching)
- Smart incremental data downloading
- Comprehensive error handling and authentication management
- HACS compatible with proper metadata

### Configuration

- Email and password authentication
- Configurable initial download period (1-100 days)
- Automatic contract detection and selection
- Unique ID management to prevent duplicates

### Sensors

#### Account Sensors

- Account Balance (NZD)
- Next Bill Amount & Date
- Payment Due Amount & Date
- Previous/Next Reading Dates

#### Usage Sensors (Statistics)

- Energy Consumption (kWh) - Energy Dashboard compatible
- Energy Cost (NZD) - Cost tracking
- Free Energy Consumption (kWh) - Free electricity plans

All usage sensors write to Home Assistant's statistics database for optimal memory usage and ApexCharts compatibility.
