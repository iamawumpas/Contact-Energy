<div align="center">
  <h1>Contact Energy Integration for Home Assistant</h1>
  <p><i>Let's do the 'monitor your Contact Energy account' thing</i></p>

  ![Version](https://img.shields.io/badge/version-2.0.6-blue.svg)
  [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
  ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1+-blue.svg)
</div>

---

## Quick Links
- 📚 [**Full Documentation**](https://github.com/iamawumpas/Contact-Energy/wiki/Home) - Complete guides and setup instructions
- 🚀 [**Getting Started**](https://github.com/iamawumpas/Contact-Energy/wiki/Getting-Started) - Installation and configuration
- 📊 [**Sensor Reference**](https://github.com/iamawumpas/Contact-Energy/wiki/Sensors) - Complete list of all 27 sensors
- 📈 [**Charts & Dashboards**](https://github.com/iamawumpas/Contact-Energy/wiki/Dashboards) - Dashboard examples and card configurations
- ⚙️ [**Multiple Instances**](https://github.com/iamawumpas/Contact-Energy/wiki/Multiple-Accounts) - Monitor multiple properties or accounts
- ❓ [**FAQ & Limitations**](https://github.com/iamawumpas/Contact-Energy/wiki/FAQ) - Common questions and constraints
- 📝 [**Changelog**](Changelog.md) - Version history and changes

## 🎉 Version 2.0.0 - Complete Architecture Overhaul

Version 2.0.0 represents a complete rewrite with a modern, modular architecture:

- **Modular Design** - Separated into logical layers: API, Data Managers, Coordinators, and Sensors
- **Independent Caching** - Each data type has its own cache with appropriate staleness rules
- **Better Performance** - Optimized update schedules per data type (hourly, 6h, 24h)
- **Improved Maintainability** - Clear separation of concerns makes updates easier
- **27 Sensors** - Comprehensive monitoring of account, billing, and usage data

For full details, see the [v2.0.0 Changelog](Changelog.md) and [Architecture Documentation](V2_REFACTORING_COMPLETE.md).

## About This Integration

A Home Assistant integration for Contact Energy (New Zealand electricity supplier) that fetches your account and billing information from your Contact Energy account, making it available in Home Assistant for monitoring and automation.

This custom implementation provides comprehensive account monitoring with **27 sensors** covering balance, billing, contracts, payment information, usage attributes for charting, and Energy Dashboard-ready totals.

## Architecture Overview

Version 2.0.0 introduces a clean, layered architecture:

```
contact_energy/
├── api/                    # Phase 1: API Layer
│   ├── client.py           # Base API client with auth & rate limiting
│   ├── account.py          # Account endpoints
│   └── usage.py            # Usage endpoints
│
├── data_managers/          # Phase 2: Data Managers
│   ├── base_cache.py       # Base caching logic
│   ├── account_data.py     # Account caching (>6h staleness)
│   ├── usage_hourly.py     # Hourly usage caching (1-6h)
│   ├── usage_daily.py      # Daily usage caching (1-6h)
│   └── usage_monthly.py    # Monthly usage caching (1-6h)
│
├── coordinators/           # Phase 3: Coordinators
│   ├── account_coordinator.py      # Account updates (6h)
│   └── usage_coordinator_v2.py     # Usage updates (1h/6h/24h)
│
├── sensors/                # Phase 4: Sensors
│   ├── account_sensors.py  # 17 account sensors
│   ├── usage_sensors.py    # 4 usage sensors
│   └── energy_sensors.py   # 6 Energy Dashboard sensors
│
├── __init__.py             # Phase 5: Integration setup
└── sensor.py               # Sensor platform setup
```

### Key Benefits
- **Clear Separation of Concerns** - Each layer has a single responsibility
- **Independent Testing** - Components can be tested in isolation
- **Efficient Caching** - Data-specific staleness rules reduce API calls
- **Flexible Updates** - Different data types update on optimal schedules
- **Easy Maintenance** - Localized changes don't affect other components

## Why did I create this version?
I have used [codyc1515's](https://github.com/codyc1515) original Home Assistant Contact Energy integration and [notf0und's](https://github.com/notf0und) recent fork for a couple of years, when suddenly I started having issues downloading my usage statistics. Wondering if the API had changed I thought I would "experiment" to see if I could get it to work again. I'm not much of a coder but I am a problem solver, so I took advantage of the AI revolution at the moment and explored what can be done with various AI Agents (I make no apologies for using AI as a tool to do the hard part of actually writing code) and it has been an interesting journey, if frustrating time banging my head against AI "stupidity". Long-story-short: this is what has come about. 

## What Does It Do?

The integration connects to your Contact Energy account and creates sensors for:

- **Account Balance** - Current balance, prepay debt, refund eligibility
- **Billing Information** - Amount due, payment dates, discounts, days until overdue (resets to 0 once balance is paid)
- **Next Bill** - Next bill date and countdown
- **Account Settings** - Correspondence preference, payment method, billing frequency
- **Contract Details** - ICP, address, product name, contract type and status
- **Payment Plans** - Direct debit, smooth pay, and prepay status indicators
- **Usage & Energy**
  - Usage sensor attributes with hourly/daily/monthly paid/free kWh plus monthly cost for charts
  - Paid/Free energy sensors (total_increasing) ready for Home Assistant Energy Dashboard

All data updates automatically with optimized polling schedules and can be viewed in custom dashboard cards or used in automations:

- **Account data** (balance, billing): Updates every 6 hours
- **Hourly usage data**: Updates every hour
- **Daily usage data**: Updates every 6 hours
- **Monthly usage data**: Updates every 24 hours

**Note:** This integration provides account and billing information only. For detailed sensor descriptions, see the [Sensor Reference](../../wiki/Sensors) in the wiki.

## Installation

**Compatibility:** Requires Home Assistant 2023.1 or later.

### HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed
2. Open HACS in Home Assistant
3. Click on **Integrations**
4. Click the **three dots** in the top right corner
5. Select **Custom repositories**
6. Add repository URL: `https://github.com/iamawumpas/Contact-Energy`
7. Select category: **Integration**
8. Click **Add**
9. Find "Contact Energy" in HACS and click **Download**
10. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [Releases page](https://github.com/iamawumpas/Contact-Energy/releases)
2. Extract the `contact_energy` folder to your `custom_components` directory
3. Restart Home Assistant

## Getting Started

1. Go to **Settings** → **Devices & Services** → **+ Add Integration**
2. Search for **Contact Energy**
3. Enter your Contact Energy credentials (email and password)
4. Select which account(s) you want to monitor (if you have multiple)
5. Done! Sensors will appear and update automatically

📖 For detailed setup instructions and multi-account configuration, see the [Getting Started Guide](https://github.com/iamawumpas/Contact-Energy/wiki/Getting-Started).

## Documentation

For comprehensive documentation on all features, configuration options, and troubleshooting, visit the **[Wiki](https://github.com/iamawumpas/Contact-Energy/wiki)**.

**Key topics:**
- [Sensor Reference](https://github.com/iamawumpas/Contact-Energy/wiki/Sensors) - Complete list of all 27 sensors
- [Dashboard Examples](https://github.com/iamawumpas/Contact-Energy/wiki/Dashboards) - Markdown card examples and [sample dashboard YAML](assets/dashboard.yaml)
- [Multiple Properties/Accounts](https://github.com/iamawumpas/Contact-Energy/wiki/Multiple-Accounts) - Managing multiple accounts
- [How It Works & Limitations](https://github.com/iamawumpas/Contact-Energy/wiki/FAQ) - Technical details and constraints

## Free to Use

This code is provided as-is with no warranties. It works for my Home Assistant setup and is shared freely for anyone who finds it useful.

## Attribution

Original project by [codyc1515](https://github.com/codyc1515)  
Fork by [notf0und](https://github.com/notf0und)

---

<div align="center">
  <p>If you find this integration useful, consider giving it a ⭐ on GitHub!</p>
</div>
