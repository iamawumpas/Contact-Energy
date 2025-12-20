<table>
  <tr>
    <td style="vertical-align: top;">
  <img src="https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/logo.svg" alt="Contact Energy Logo" width="auto" height="50px" style="vertical-align: top; display: inline-block;">
    </td>
    <td >
      <h1>Contact Energy</h1>
      <h4>Let's do the energy thing<img width="400"/></h4>
    </td>
  </tr>
  <tr>
    <td colspan="2" style="border: none; vertical-align: top;">
  <strong>version:</strong> 0.0.6
    </td>
  </tr>
</table>

## Quick Links

- 📚 **[Full Documentation](https://github.com/iamawumpas/Contact-Energy/wiki)** - Complete guides and setup instructions
- 🚀 **[Getting Started](https://github.com/iamawumpas/Contact-Energy/wiki/Getting-Started)** - Installation and configuration
- 📊 **[Charts & Dashboards](https://github.com/iamawumpas/Contact-Energy/wiki/Charts-and-Dashboards)** - ApexCharts examples and card configurations
- ⚙️ **[Multiple Instances](https://github.com/iamawumpas/Contact-Energy/wiki/Multiple-Instances)** - Monitor multiple properties or accounts
- ❓ **[FAQ & Limitations](https://github.com/iamawumpas/Contact-Energy/wiki/FAQ-and-Limitations)** - Common questions and constraints
- 📝 **[Changelog](CHANGELOG.md)** - Version history and changes

---

## About This Integration

A **Home Assistant** integration for Contact Energy (New Zealand electricity supplier) that fetches your energy usage and billing information from your Contact Energy account, making it available in Home Assistant for monitoring and automation.

This is a custom implementation created to fix bugs and improve functionality for personal use.

## What Does It Do?

The integration connects to your Contact Energy account and creates sensors for:

- **Energy Usage** - Hourly, daily, and monthly usage statistics
- **Free Energy** - Tracking of free energy allocations (if applicable to your plan)
- **Account Information** - Billing details, account balance, contract information, and more
- **Chart Data** - Pre-formatted sensor data for visualization with ApexCharts cards

All data is stored in Home Assistant's statistics database and can be viewed in the Energy Dashboard or custom dashboard cards.

> **Note:** Contact Energy provides data with a 24-72 hour delay. This integration cannot provide real-time monitoring.

## Installation

> **Compatibility:** Requires Home Assistant **2023.1 or later**.

### HACS (Recommended)

1. Ensure [HACS is installed](https://hacs.xyz/docs/setup/download)
2. [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=iamawumpas&repository=contact_energy&category=integration)
3. Install **Contact Energy**
4. Restart Home Assistant

### Manual Installation

See [Installation Guide](https://github.com/iamawumpas/Contact-Energy/wiki/Installation) on the wiki.

## Getting Started

1. Go to **Settings → Devices & Services → + Create Integration**
2. Search for **Contact Energy**
3. Enter your Contact Energy credentials and preferences

📖 For detailed setup instructions, see the [Getting Started Guide](https://github.com/iamawumpas/Contact-Energy/wiki/Getting-Started).

## Documentation

For comprehensive documentation on all features, configuration options, and troubleshooting, visit the **[Wiki](https://github.com/iamawumpas/Contact-Energy/wiki)**.

Key topics:
- [Energy Dashboard Integration](https://github.com/iamawumpas/Contact-Energy/wiki/Energy-Dashboard)
- [ApexCharts Card Examples](https://github.com/iamawumpas/Contact-Energy/wiki/Charts-and-Dashboards)
- [Markdown Card Examples](https://github.com/iamawumpas/Contact-Energy/wiki/Charts-and-Dashboards)
- [Multiple Properties/Accounts](https://github.com/iamawumpas/Contact-Energy/wiki/Multiple-Instances)
- [How It Works & Limitations](https://github.com/iamawumpas/Contact-Energy/wiki/FAQ-and-Limitations)

## Free to Use

This code is provided as-is with no warranties. It works for my Home Assistant setup and is shared freely for anyone who finds it useful.

## Attribution

- Original project by [codyc1515](https://github.com/codyc1515/ha-contact-energy)
- Fork by [notf0und](https://github.com/notf0und/ha-contact-energy)
