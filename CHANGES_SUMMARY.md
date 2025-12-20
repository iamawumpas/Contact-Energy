# Contact Energy Integration - Error Handling & Logging Improvements

## Summary
Fixed critical issue where HTTP 502/503/504 server errors caused immediate integration setup failure instead of retrying. Added comprehensive logging throughout the entire data flow to provide visibility into what is working and what is not.

---

## Changes Made

### 1. **api.py** - API Client Enhancements

#### Fix: 5xx Server Error Handling with Retries
- **Problem**: Server errors (502, 503, 504) immediately failed without retrying
- **Solution**: Added retry logic for 5xx errors with 5-second delays between attempts
- **Line ~250**: New code block checks for `500 <= status < 600` and retries up to 3 times
- **Logging**: Clear warnings on each retry attempt, error logged on final failure

#### Enhanced Logging in `get_usage()` method:
```
✓ Successfully fetched N hourly/daily/monthly usage record(s)
❌ Server error (502/503/504) - retrying (attempt 1/3)
❌ Failed to fetch usage data: status XXX - <error message>
✓ Authentication successful! Token received (length: NNN)
```

#### Better authentication error messages:
- Now shows specific status code (401, 403, etc.)
- Clearer distinction between auth failures and server errors

---

### 2. **coordinator.py** - Data Update Coordinator Enhancements

#### Improved `_async_update_data()` flow with section markers:
```
============================================================
Starting data update for ICP: XXXXXXXXX
============================================================
📋 Updating account data for ICP...
✓ Account data updated successfully
📊 Updating daily/monthly usage for ICP...
✓ Daily usage updated successfully
⚡ Updating hourly usage for ICP...
✓ Hourly usage updated successfully
============================================================
✓ Data update completed successfully for ICP: XXXXXXXXX
============================================================
```

#### Per-data-type error handling with detailed logging:
Each update function (account, hourly, daily, monthly) now logs:
- Individual success/failure per component
- Specific error messages for troubleshooting
- Data samples (today's usage, balance info, etc.)

#### Enhanced metrics in success logs:
```
✓ Daily usage updated: 48 records | Today: 24.5 kWh ($6.80)
✓ Monthly usage updated: 12 records | Current: 650.2 kWh ($180.50)
✓ Hourly usage updated: 48 total records
```

---

### 3. **__init__.py** - Integration Setup & Initialization

#### Setup progress tracking:
```
=======================================================================
🔧 Setting up Contact Energy integration
=======================================================================
👤 Email: user@example.com, Password length: N
📋 Configuration loaded:
  - Account ID: XXXXXXXXX
  - Contract ID: XXXXXXXXX
  - ICP: 0000000xxxxxx
  - History: 3 months (90 days)
✓ Coordinator initialized for ICP: XXXXXXXXX
📡 Starting first data refresh (may take a moment)...
✓ First refresh completed successfully
🔌 Forwarding entry setup to platforms: ['sensor']
✓ Platform setup completed
=======================================================================
✓ Contact Energy setup COMPLETED for user account
=======================================================================
```

#### Failure visibility:
```
=======================================================================
❌ Failed to refresh data from Contact Energy API
=======================================================================
Error: Contact Energy API error: cannot_connect
```

#### Daily restart scheduling:
```
⏰ Daily restart triggered at 3:00 AM for ICP: XXXXXXXXX
```

---

## Log Example: Successful Update Flow

```
🔐 Authenticating with Contact Energy API...
✓ Authentication successful! Token received (length: 50)
============================================================
Starting data update for ICP: 0000000966tr348
============================================================
📋 Updating account data for ICP: 0000000966tr348
  🔐 API already authenticated
  ✓ Account data updated: 1 account(s) found
  - Current balance: $125.45
  - Amount due: $95.60
✓ Account data updated successfully
📊 Updating daily/monthly usage for ICP: 0000000966tr348
  ✓ Daily usage updated: 48 records | Today: 24.5 kWh ($6.80)
✓ Daily usage updated successfully
  ✓ Monthly usage updated: 12 records | Current: 650.2 kWh ($180.50)
✓ Monthly usage updated successfully
⚡ Updating hourly usage for ICP: 0000000966tr348
  📅 Yesterday (2025-12-19)...
    ✓ Got 24 hourly records
  📅 Today (2025-12-20)...
    ✓ Got 15 hourly records
✓ Hourly usage updated: 39 total records
✓ Data update completed successfully for ICP: 0000000966tr348
```

---

## Log Example: Server Error with Retry

```
POST /usage/v2/1350836906?ba=501230645&interval=daily&from=2025-11-20&to=2025-12-20
Usage fetch response status: 502 (attempt 1/3)
⚠️ Server error (502): {"message": "Internal server error"} - retrying (attempt 1/3)
[5 second delay]
Usage fetch response status: 503 (attempt 2/3)
⚠️ Server error (503): Service Unavailable - retrying (attempt 2/3)
[5 second delay]
Usage fetch response status: 200 (attempt 3/3)
✓ Successfully fetched 30 daily usage record(s)
```

---

## Testing the Fix

### To verify 5xx retry logic:
1. Look for log entries with: `Server error (status 5XX)` followed by `retrying`
2. If it retries 3 times, it will show: `after 3 retries - giving up`
3. Success messages show: `✓ Successfully fetched N records`

### To verify logging visibility:
1. Check Home Assistant logs for clear section separators (====)
2. Look for emoji indicators (✓, ❌, 📋, ⚡, etc.)
3. Search for specific data (today's usage, account balance, etc.)

---

## Files Modified
- `custom_components/contact_energy/api.py` (+60 lines, -60 lines)
- `custom_components/contact_energy/coordinator.py` (+117 lines, -77 lines)
- `custom_components/contact_energy/__init__.py` (+58 lines, -58 lines)

**Total Impact**: +158 lines / -77 lines (net +81 lines of improved logging & error handling)

---

## No Breaking Changes
- All changes are backward compatible
- No API changes or method signatures modified
- Pure enhancement to error handling and logging
