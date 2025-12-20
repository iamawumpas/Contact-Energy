# Changelog

## 0.0.6

### Critical Fix: Automatic Retry Logic for Server Errors

**Problem**: HTTP 502, 503, and 504 server errors from the Contact Energy API were causing immediate integration failure, blocking Home Assistant startup.

**Solution**: Implemented automatic retry logic with exponential backoff and comprehensive logging to allow the integration to gracefully recover from temporary API outages.

### Changes

#### api.py - Automatic Retry Logic for Server Errors
  - **NEW**: Added automatic retry logic for HTTP 5xx server errors (502, 503, 504, etc.)
    - Retries up to 3 times with 5-second delays between attempts
    - Allows API to recover from temporary outages without manual intervention
    - Separate handling for authentication errors (401, 403) to re-authenticate
  - **IMPROVED**: Enhanced authentication logging
    - Shows clear success/failure indicators: `✓ Authentication successful!`
    - Includes token length for verification
    - Better error messages with HTTP status codes
  - **IMPROVED**: Enhanced error messages with full context
    - Shows exact HTTP status code and API response text
    - Distinguishes between client errors, server errors, and auth failures
    - Helps with troubleshooting and debugging
  - **IMPROVED**: Added retry attempt logging
    - Each retry attempt is logged with attempt number (e.g., "attempt 1/3")
    - Shows error details on each failure
    - Clear messaging when all retries are exhausted

#### coordinator.py - Comprehensive Data Flow Logging
  - **IMPROVED**: Enhanced `_async_update_data()` main update loop
    - Added visual section separators (`====`) for clear log organization
    - Per-component success/failure tracking with emoji indicators (✓ ❌ 📋 ⚡)
    - Shows next update time for skipped components
    - Better error context with component-specific messages
  - **IMPROVED**: Account data logging with actual values
    - Shows account count: `✓ Account data updated: 1 account(s) found`
    - Displays current balance: `- Current balance: $125.45`
    - Shows amount due: `- Amount due: $95.60`
  - **IMPROVED**: Daily/monthly usage logging with actual consumption data
    - Daily: `✓ Daily usage updated: 30 records | Today: 24.5 kWh ($6.80)`
    - Monthly: `✓ Monthly usage updated: 12 records | Current: 650.2 kWh ($180.50)`
    - Handles empty data gracefully with clear messaging
  - **IMPROVED**: Hourly usage logging with date breakdown
    - Shows yesterday's fetch: `📅 Yesterday (2025-12-19)... ✓ Got 24 hourly records`
    - Shows today's fetch: `📅 Today (2025-12-20)... ✓ Got 15 hourly records`
    - Total record count for verification

#### __init__.py - Setup Progress and Error Visibility
  - **IMPROVED**: Setup progress with clear visual markers
    - Setup start banner with section separators
    - Configuration display showing all settings
    - Progress indicators during initialization
  - **IMPROVED**: Configuration display with formatting
    - Shows email, account ID, contract ID, ICP number
    - Shows history duration in both months and days
    - Easy verification of loaded configuration
  - **IMPROVED**: Enhanced error reporting
    - Detailed error sections with separators
    - Full traceback for debugging
    - Shows exactly which step failed
  - **IMPROVED**: Daily restart scheduling messages
    - Clear indication of 3:00 AM restart trigger
    - ICP number shown for multi-account setups

### Logging Features

#### Visual Indicators (Emoji)
  - `✓` - Success (completed successfully)
  - `❌` - Failure (error occurred)
  - `⚠️` - Warning (retry in progress)
  - `🔐` - Authentication
  - `📋` - Account information
  - `📊` - Daily/monthly data
  - `⚡` - Hourly data
  - `📅` - Date reference
  - `🔧` - Setup/initialization
  - `⏰` - Time/schedule

#### Section Organization
  - `====` separators for clear log section boundaries
  - Makes logs easier to read and parse
  - Helps identify where each operation starts and ends

### Technical Details

- **Lines Changed**: +158 added, -77 removed (net +81 lines)
- **Files Modified**: 3 (api.py, coordinator.py, __init__.py)
- **Breaking Changes**: None
- **New Dependencies**: None
- **Configuration Changes**: None (100% backwards compatible)

### Error Handling Matrix

| HTTP Status | Before | After |
|-------------|--------|-------|
| 200 OK | ✓ Works | ✓ Works (enhanced logging) |
| 401/403 Auth Error | ⚠️ 1 retry | ✅ 3 retries + re-auth |
| 502 Bad Gateway | ❌ Fails | ✅ 3 retries (15s max) |
| 503 Unavailable | ❌ Fails | ✅ 3 retries (15s max) |
| 504 Timeout | ❌ Fails | ✅ 3 retries (15s max) |

### User Impact

- Integration no longer crashes on temporary API outages
- Automatic recovery with up to 3 retry attempts
- Full visibility into what data is being fetched and why operations might fail
- Better troubleshooting with detailed logs showing every step
- No configuration changes needed (drop-in replacement)


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


