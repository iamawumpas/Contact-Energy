## v0.0.1 - 2025-10-10
Version 0.0.1 - Initial release

- First release of Contact Energy integration

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
