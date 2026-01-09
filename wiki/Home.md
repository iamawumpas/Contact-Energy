# Contact Energy Integration Wiki

Welcome to the Contact Energy integration documentation for Home Assistant!

## Overview

This integration allows you to monitor your Contact Energy (New Zealand) account directly in Home Assistant. Track account balance, billing information, contract details, usage summaries, and Energy Dashboard totals with 26 sensors that update daily.

## Quick Navigation

### Getting Started
- [Installation & Setup](Getting-Started) - Install the integration and configure your first account
- [Multiple Accounts](Multiple-Accounts) - Monitor multiple properties or accounts

### Reference
- [Sensors](Sensors) - Complete list of all 24 available sensors
- [Dashboards](Dashboards) - Dashboard examples and YAML configurations

### Support
- [FAQ & Limitations](FAQ) - Common questions, limitations, and troubleshooting
- [Changelog](../Changelog.md) - Version history and updates

## Features

✅ **26 Sensors** covering:
- Account balance and refund information
- Billing and invoice details with payment tracking
- Next bill predictions
- Contract and product information
- Account settings and preferences
- Payment plan indicators (Direct Debit, Smooth Pay, Prepay)
- Usage sensor attributes (hourly/daily/monthly paid/free kWh) for charting
- Energy Dashboard-ready paid/free cumulative sensors

✅ **Daily Updates** - Automatic data refresh at 01:00 AM (usage cache + Energy Dashboard totals)

✅ **Multi-Account Support** - Monitor multiple properties/accounts

✅ **Secure Authentication** - Token-based authentication with automatic refresh

## How It Works

The integration connects to the Contact Energy REST API using your account credentials:

1. Authenticates with your email and password
2. Retrieves account information for your property/properties
3. Creates sensors in Home Assistant for each configured account
4. Updates sensor data once per day (scheduled closest to 01:00 AM)
5. Automatically refreshes authentication tokens as needed

**Note:** Contact Energy provides data with some delay. This integration cannot provide real-time monitoring.

## Data Privacy

- Your credentials are stored securely in Home Assistant's configuration
- Authentication tokens are refreshed automatically
- The integration only communicates with Contact Energy's official API
- No data is sent to third parties

## Need Help?

- Check the [FAQ & Limitations](FAQ) page
- Review the [Getting Started](Getting-Started) guide
- Open an [issue on GitHub](https://github.com/iamawumpas/Contact-Energy/issues)

## Contributing

This is a personal project shared freely for community use. Feedback and contributions are welcome via GitHub issues and pull requests.

---

**Next Steps:** [Get Started →](Getting-Started)
