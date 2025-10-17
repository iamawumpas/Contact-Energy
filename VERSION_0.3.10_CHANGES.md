# Version 0.3.10 - Bug Fixes

## Issues Fixed

### 1. **API Error Handling** (Critical)
**Problem:** The `async_get_account_details()` method was catching all exceptions and returning `None`, which caused the coordinator to fail with unhelpful error messages.

**Errors Seen:**
```
Failed to fetch account details: Unexpected error
Failed to fetch account data: received None
```

**Solution:** 
- Changed the method to properly propagate specific exceptions (`InvalidAuth`, `CannotConnect`, `UnknownError`)
- Now raises `CannotConnect` if initial authentication fails instead of returning `None`
- Re-raises authentication errors instead of swallowing them
- Provides better error context when failures occur

### 2. **Database Attribute Size Limits** (Critical)
**Problem:** Chart sensors were storing too much historical data in their state attributes, exceeding Home Assistant's 16KB limit for database storage.

**Errors Seen:**
```
State attributes for sensor.contact_energy_chart_hourly_0000000966tr348 exceed maximum size of 16384 bytes
State attributes for sensor.contact_energy_chart_hourly_free_0000000966tr348 exceed maximum size of 16384 bytes
```

**Solution:**
- **Hourly chart sensors:** Reduced from 30 days to **7 days** of data
- **Daily chart sensors:** Reduced from 90 days to **30 days** of data
- **Hourly free chart sensors:** Reduced from 30 days to **7 days** of data

This should keep attribute sizes well under the 16KB limit while still providing useful charting data.

### 3. **Improved Error Messages**
**Problem:** When account data fetch failed, the error message didn't provide enough context about what was received.

**Solution:**
- Added type information to error messages
- Now logs: `"Failed to fetch account data: received {type} (type: {typename})"`
- Makes debugging much easier

## Files Modified

1. **`api.py`** - Fixed `async_get_account_details()` error handling
2. **`coordinator.py`** - Improved error messaging
3. **`sensor.py`** - Reduced data retention in chart sensors (3 changes)
4. **`manifest.json`** - Updated version to 0.3.10
5. **`hacs.json`** - Updated version to 0.3.10
6. **`CHANGELOG.md`** - Added version 0.3.10 entry

## Testing Recommendations

After deploying this update:

1. **Restart Home Assistant** to load the new version
2. **Monitor logs** for the next coordinator update (happens every 8 hours, or you can trigger manually)
3. **Check that chart sensors** no longer show database warnings
4. **Verify account sensors** are updating correctly with balance, billing info, etc.

## Next Steps

If you still see issues after this update, please check:
- Whether the Contact Energy API is having connectivity issues
- Your authentication credentials are still valid
- Network connectivity to `api.contact-digital-prod.net`

You can test the API connection manually using the `debug_api.py` script in the repository root (remember to add your credentials first).
