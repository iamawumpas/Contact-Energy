<div align="center">
  <h1>Contact Energy Integration for Home Assistant</h1>
  <p><i>Let's do the 'monitor your Contact Energy account' thing</i></p>

  ![Version](https://img.shields.io/badge/version-1.8.0-blue.svg)
  [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
  ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.12.5+-blue.svg)
</div>

---

## Quick Links
- 📚 [**Full Documentation**](https://github.com/iamawumpas/Contact-Energy/wiki/Home) - Complete guides and setup instructions
- 🚀 [**Getting Started**](https://github.com/iamawumpas/Contact-Energy/wiki/Getting-Started) - Installation and configuration
- 📊 [**Sensor Reference**](https://github.com/iamawumpas/Contact-Energy/wiki/Sensors) - Complete list of all 24 sensors
- 📈 [**Charts & Dashboards**](https://github.com/iamawumpas/Contact-Energy/wiki/Dashboards) - Dashboard examples and card configurations
- ⚙️ [**Multiple Instances**](https://github.com/iamawumpas/Contact-Energy/wiki/Multiple-Accounts) - Monitor multiple properties or accounts
- ❓ [**FAQ & Limitations**](https://github.com/iamawumpas/Contact-Energy/wiki/FAQ) - Common questions and constraints
- 📝 [**Changelog**](Changelog.md) - Version history and changes

## About This Integration

A Home Assistant integration for Contact Energy (New Zealand electricity supplier) that fetches your account and billing information from your Contact Energy account, making it available in Home Assistant for monitoring and automation.

This custom implementation provides comprehensive account monitoring with 26 sensors covering balance, billing, contracts, payment information, usage attributes for charting, and Energy Dashboard-ready totals.

## What Does It Do?

The integration connects to your Contact Energy account and creates sensors for:

- **Account Balance** - Current balance, prepay debt, refund eligibility
- **Billing Information** - Amount due, payment dates, discounts, days until overdue
- **Next Bill** - Next bill date and countdown
- **Account Settings** - Correspondence preference, payment method, billing frequency
- **Contract Details** - ICP, address, product name, contract type and status
- **Payment Plans** - Direct debit, smooth pay, and prepay status indicators
- **Usage & Energy**
  - Usage sensor attributes with hourly/daily/monthly paid/free kWh for charts
  - Paid/Free energy sensors (total_increasing) ready for Home Assistant Energy Dashboard

All data updates automatically once per day at 01:00 AM and can be viewed in custom dashboard cards or used in automations.

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
5. Done! Sensors will appear and update daily at 01:00 AM

📖 For detailed setup instructions and multi-account configuration, see the [Getting Started Guide](https://github.com/iamawumpas/Contact-Energy/wiki/Getting-Started).

## Documentation

For comprehensive documentation on all features, configuration options, and troubleshooting, visit the **[Wiki](https://github.com/iamawumpas/Contact-Energy/wiki)**.

**Key topics:**
- [Sensor Reference](https://github.com/iamawumpas/Contact-Energy/wiki/Sensors) - Complete list of all 26 sensors
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
