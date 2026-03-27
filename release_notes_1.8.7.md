## Fixed
- Fixed critical KeyError 'sync_interval_hours' in usage_coordinator.py that prevented usage data synchronization
- Added missing sync_interval_hours configuration to USAGE_CONFIG for all data types (hourly, daily, monthly)
- Restored proper polling schedule functionality that was broken after v1.8.4 optimizations
- Resolved usage sync failures that occurred when coordinator tried to determine sync intervals

## Changed
- Updated USAGE_CONFIG with appropriate sync intervals: hourly data syncs every hour, daily/monthly data syncs daily