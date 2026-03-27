## Fixed
- Fixed daily usage chart incorrectly displaying free usage on weekdays (e.g., Friday instead of Saturday)
- Replaced timezone-dependent date parsing with explicit UTC-based parsing using Date.UTC() in chart data generators
- Added weekend-only filter to free usage series to prevent API anomalies from showing on incorrect days
- Removed datetimeUTC configuration that caused inconsistent date shifting across different browser environments

## Changed
- Updated daily usage ApexCharts template with timezone-safe date handling
- Updated wiki Dashboards page with corrected chart configuration and explanation of the timezone fix
- Added weekend validation logging to contact_api.py to detect unexpected free usage on weekdays from the API