# Contact Energy Integration Wiki

Welcome to the Contact Energy integration documentation for Home Assistant!

## 🎉 Version 2.0.0 - New Architecture

Version 2.0.0 introduces a complete architectural overhaul with a modern, modular design. The integration now features:

- **Layered Architecture** - Separated into API, Data Managers, Coordinators, and Sensors
- **Independent Caching** - Each data type has its own cache with appropriate staleness rules
- **Optimized Updates** - Different data types update on optimal schedules (hourly, 6h, 24h)
- **27 Sensors** - Complete monitoring of account, billing, and usage data
- **Better Performance** - Reduced API calls through intelligent caching
- **Improved Maintainability** - Clear separation of concerns makes updates easier

For full details, see the [v2.0.0 Changelog](../Changelog.md) and [Architecture Documentation](../V2_REFACTORING_COMPLETE.md).

## Overview

This integration allows you to monitor your Contact Energy (New Zealand) account directly in Home Assistant. Track account balance, billing information, contract details, usage summaries, and Energy Dashboard totals with 27 sensors that update automatically on optimized schedules.

## Quick Navigation

### Getting Started
- [Installation & Setup](Getting-Started) - Install the integration and configure your first account
- [Multiple Accounts](Multiple-Accounts) - Monitor multiple properties or accounts

### Reference
- [Sensors](Sensors) - Complete list of all 27 available sensors
- [Dashboards](Dashboards) - Dashboard examples and YAML configurations

### Support
- [FAQ & Limitations](FAQ) - Common questions, limitations, and troubleshooting
- [Changelog](../Changelog.md) - Version history and updates

## Features

✅ **27 Sensors** covering:
- Account balance and refund information (4 sensors)
- Billing and invoice details with payment tracking (5 sensors)
- Next bill predictions (2 sensors)
- Contract and product information (6 sensors)
- Usage sensor with hourly/daily/monthly attributes for charting (4 sensors)
- Energy Dashboard-ready paid/free cumulative sensors (6 sensors)

✅ **Optimized Updates** - Smart polling schedules for different data types:
- Account data: Updates every 6 hours
- Hourly usage: Updates every hour
- Daily usage: Updates every 6 hours
- Monthly usage: Updates every 24 hours

✅ **Multi-Account Support** - Monitor multiple properties/accounts

✅ **Secure Authentication** - Token-based authentication with automatic refresh

✅ **Modern Architecture** - v2.0.0 features a modular design with clear separation of concerns

## How It Works

The integration connects to the Contact Energy REST API using your account credentials:

1. Authenticates with your email and password
2. Retrieves account information for your property/properties
3. Creates sensors in Home Assistant for each configured account
4. Updates data on optimized schedules based on data type and change frequency
5. Automatically refreshes authentication tokens as needed
6. Caches data locally to reduce API calls and improve performance

**Note:** Contact Energy provides data with some delay. This integration cannot provide real-time monitoring.

## v2.0.0 Architecture

The new modular architecture consists of five layers:

### Phase 1: API Layer (`api/`)
- Base API client with authentication and rate limiting
- Account endpoints
- Usage endpoints (hourly, daily, monthly)

### Phase 2: Data Managers (`data_managers/`)
- Base caching with JSON persistence
- Account data caching (staleness: >6h)
- Hourly, daily, and monthly usage caching (staleness: 1-6h)

### Phase 3: Coordinators (`coordinators/`)
- Account coordinator (updates every 6h)
- Usage coordinator (independent schedules: 1h/6h/24h)

### Phase 4: Sensors (`sensors/`)
- 17 account sensors across 4 classes
- 4 usage sensors
- 6 Energy Dashboard sensors

### Phase 5: Integration
- Updated integration setup using v2.0.0 components
- Simplified sensor platform setup

## Data Privacy

- Your credentials are stored securely in Home Assistant's configuration
- Authentication tokens are refreshed automatically
- The integration only communicates with Contact Energy's official API
- No data is sent to third parties
- Data is cached locally for performance

## Need Help?

- Check the [FAQ & Limitations](FAQ) page
- Review the [Getting Started](Getting-Started) guide
- Open an [issue on GitHub](https://github.com/iamawumpas/Contact-Energy/issues)

## Contributing

This is a personal project shared freely for community use. Feedback and contributions are welcome via GitHub issues and pull requests.

---

**Next Steps:** [Get Started →](Getting-Started)
