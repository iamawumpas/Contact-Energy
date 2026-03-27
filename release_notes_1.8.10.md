## Fixed
- Fixed daily/monthly usage refresh starvation caused by shared sync timing state with hourly syncs
- Added interval-specific last_sync tracking for hourly, daily, and monthly usage intervals
- Fixed manual refresh flow to always clear usage sync skip/lock state even when re-authentication fails

## Changed
- Usage sync scheduling now runs independently from account polling windows, while interval-level decisions remain inside usage coordinator
- Added debug logging for usage sync timing state (hourly/daily/monthly last sync plus global cache sync timestamp)
