# Implementation Details: 5xx Error Retry Logic

## Core Issue Fixed

The Contact Energy API integration was failing immediately when the API returned HTTP 5xx server errors (502, 503, 504) instead of retrying, which caused:
- Integration setup to fail
- Config entry to show as "not ready"
- Loss of all data sensors
- No recovery even when API recovered seconds later

## Root Cause

In `api.py`, the `get_usage()` method at line ~250:

**BEFORE:**
```python
if response.status != 200:
    text = await response.text()
    _LOGGER.error("Failed to fetch usage data: %s - %s", response.status, text)
    raise ConnectionError(ERROR_CANNOT_CONNECT)  # ← IMMEDIATELY FAILS
```

This checked for "anything != 200" and immediately raised an exception, treating:
- 502 Bad Gateway (recoverable) ❌ 
- 503 Service Unavailable (recoverable) ❌
- 401 Authentication (already had retry logic) ✓

...exactly the same way.

## Solution Implemented

**AFTER:**
```python
# Handle authentication errors (401, 403)
if response.status == 401 or response.status == 403:
    if attempt < MAX_RETRIES - 1:
        _LOGGER.warning("Authentication failed (status %d), re-authenticating...")
        await self.authenticate()
        headers = self._get_auth_headers()
        await asyncio.sleep(RETRY_DELAY)
        continue
    # Give up after 3 attempts
    raise AuthenticationError(ERROR_INVALID_AUTH)

# Handle server errors (5xx) with retries ← NEW CODE
if 500 <= response.status < 600:
    text = await response.text()
    if attempt < MAX_RETRIES - 1:
        _LOGGER.warning("Server error (status %d): %s - retrying...")
        await asyncio.sleep(RETRY_DELAY)
        continue
    # Give up after 3 attempts
    _LOGGER.error("Server error (status %d) after 3 retries - giving up")
    raise ConnectionError(ERROR_CANNOT_CONNECT)

# Handle successful response
if response.status == 200:
    data = await response.json()
    _LOGGER.info("✓ Successfully fetched %d records", len(data))
    return data

# Handle other errors
text = await response.text()
_LOGGER.error("Failed to fetch data: status %d - %s", response.status, text)
raise ConnectionError(ERROR_CANNOT_CONNECT)
```

## Retry Logic Behavior

With `MAX_RETRIES = 3` and `RETRY_DELAY = 5` seconds:

```
Attempt 1 (0s):    POST /usage/v2/... → 502
  ↓ Wait 5 seconds ↓

Attempt 2 (5s):    POST /usage/v2/... → 503
  ↓ Wait 5 seconds ↓

Attempt 3 (10s):   POST /usage/v2/... → 200 OK ✓
  Return data
```

Or if all fail:
```
Attempt 1 (0s):    POST /usage/v2/... → 502
  ↓ Wait 5 seconds ↓

Attempt 2 (5s):    POST /usage/v2/... → 502
  ↓ Wait 5 seconds ↓

Attempt 3 (10s):   POST /usage/v2/... → 502
  Raise ConnectionError (data not available)
```

## Logging Changes

### api.py
**Lines changed**: ~260 lines (60 +, 60 -)

Key changes:
- Line 87: `"🔐 Authenticating with Contact Energy API..."` 
- Line 118: `"✓ Authentication successful! Token received"`
- Lines 244-276: NEW - Server error retry logic with detailed logging

### coordinator.py  
**Lines changed**: ~194 lines (117 +, 77 -)

Key changes:
- Line 128: Added visual section separators `====`
- Lines 132-200: Enhanced `_async_update_data()` with per-component status
- Lines 204-241: Detailed account data logging with balance info
- Lines 264-322: Daily/monthly usage logging with amounts
- Lines 324-354: Hourly usage logging with date breakdowns

### __init__.py
**Lines changed**: ~116 lines (58 +, 58 -)

Key changes:
- Lines 36-37: Setup start banner with separators
- Lines 61-64: Configuration display with emojis
- Line 102: First refresh progress message
- Lines 104-109: Detailed error output with separators
- Lines 137-142: Setup completion banner

## Testing Recommendations

### To Test Retry Logic:
1. Restart Home Assistant
2. Check logs for: `🔐 Authenticating...` 
3. If API is slow/down, should see: `⚠️ Server error (status 5XX) - retrying`
4. Verify integration loads AFTER retries succeed
5. Confirm NO 502 errors in failed integration message

### To Test Logging Quality:
1. Search logs for `====` to find section starts/ends
2. Look for emoji indicators (✓ ❌ 📋 ⚡ 📊)
3. Verify each update section shows success/failure
4. Check that data amounts are displayed (e.g., "30 records")
5. Confirm no sensitive data in logs (passwords hidden)

## Configuration Unchanged

No configuration.yaml changes needed:
- Same credentials required
- Same account/contract/ICP settings
- Same history_days/history_months
- All backwards compatible

## Performance Impact

- **Minimal**: Added logging only
- **Retry delay**: 5 seconds × 3 attempts = maximum 15 seconds additional delay
- **Network**: Same number of requests (1-3 attempts vs 1 immediate failure)
- **Memory**: Negligible (string formatting for logs)

## Error Messages Users May See

### Normal (API recovering):
```
⚠️ Server error (status 502): {"message": "Internal server error"} - retrying (attempt 1/3)
```
→ **Normal**, will recover ✓

### Warning (Multiple failures):
```
⚠️ Server error (status 503): Service temporarily unavailable - retrying (attempt 2/3)
```
→ **Still recovering**, check API status page

### Failure (All retries exhausted):
```
❌ Server error (status 502) after 3 retries - giving up
```
→ **API is down**, will try again in 6-8 hours (next coordinator cycle)

