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
  <strong>version:</strong> 0.7.5
    </td>
  </tr>
</table>

## About This Integration

My implementation of the **Home Assistant** Contact Energy integration in HACS, to fix bugs on my HA instance.

## Why Make My Own Version
I have used ***cody1515's*** original integration, and later, ***notf0und's*** fork, to access my energy usage from Contact Energy (a New Zealand electricity supplier) for several years now.

However, for some reason since August 2025, the integration has refused to download my usage data, while all other Contact Energy data was being updated. I assumed it was a change to Contact Energy's API structure, but then again their app hasn't been updated recently and it works fine. So I decided to see if the integration could be fixed.

The logs showed the integration failing for a number of reasons:
- Timing out
- Not initialising
- Errors calling the ICP number for the account
- Authentication issues

So time for some digging and hopefully patching.

<code style="color : orange;">**THIS IS NOT A FORK**</code> - but a modification for my own use. In time I might discuss forking this project if I can get more out of the integration.

## What Does the Integration Do?

All it does is download the current energy usage and billing information from your Contact Energy account in the same way that the smartphone app gathers your data for you to view.

The integration creates multiple groups of entities, each serving different purposes for monitoring, analysis, and automation.

## 📚 Comprehensive Documentation

For detailed documentation, please visit our **[Wiki](https://github.com/iamawumpas/Contact-Energy/wiki)**:

### Getting Started
- **[Installation Guide](https://github.com/iamawumpas/Contact-Energy/wiki/Installation)** - HACS and manual installation
- **[Configuration](https://github.com/iamawumpas/Contact-Energy/wiki/Configuration)** - Setup and multiple properties
- **[Energy Dashboard Setup](https://github.com/iamawumpas/Contact-Energy/wiki/Energy-Dashboard-Setup)** - Integrate with HA Energy Dashboard

### Sensors & Features
- **[Sensor Reference](https://github.com/iamawumpas/Contact-Energy/wiki/Sensor-Reference)** - Complete guide to all 40+ sensors
- **[Forecasting & Alerts](https://github.com/iamawumpas/Contact-Energy/wiki/Forecasting-and-Alerts)** - Predictive usage forecasting and anomaly detection

### Dashboard & Visualization
- **[Dashboard Examples](https://github.com/iamawumpas/Contact-Energy/wiki/Dashboard-Examples)** - Entity cards, gauges, markdown templates
- **[ApexCharts Examples](https://github.com/iamawumpas/Contact-Energy/wiki/ApexCharts-Examples)** - Advanced charting configurations

### Automation
- **[Automation Examples](https://github.com/iamawumpas/Contact-Energy/wiki/Automation-Examples)** - Templates for notifications, alerts, and triggers

### Help & Support
- **[Limitations](https://github.com/iamawumpas/Contact-Energy/wiki/Limitations)** - Important constraints and data delays
- **[Troubleshooting](https://github.com/iamawumpas/Contact-Energy/wiki/Troubleshooting)** - Common issues and solutions
- **[FAQ](https://github.com/iamawumpas/Contact-Energy/wiki/FAQ)** - Frequently asked questions

## Key Features

- **Energy Dashboard Integration** - Automatic integration with Home Assistant's Energy Dashboard
- **40+ Sensors** - Comprehensive monitoring of usage, billing, analytics, and more
- **Multiple Properties** - Monitor multiple electricity connections simultaneously
- **Usage Forecasting** - EMA-based next-day usage predictions with confidence bands
- **Anomaly Detection** - Automatic flagging of unusual consumption patterns
- **Advanced Charting** - Pre-formatted data for ApexCharts visualizations
- **Smart Performance** - State persistence for instant restarts after initial setup

## Quick Start

1. Install via HACS (recommended) or manual installation - see [Installation Guide](https://github.com/iamawumpas/Contact-Energy/wiki/Installation)
2. Add the integration: **Settings → Devices & Services → + Add Integration** → Search "Contact Energy"
3. Enter your Contact Energy credentials and configure usage months
4. Add sensors to Energy Dashboard: **Settings → Dashboards → Energy**
5. Explore the [Wiki](https://github.com/iamawumpas/Contact-Energy/wiki) for dashboard examples and automations

## Important Limitations

### No Real-Time Monitoring
**This is the most important limitation.** Contact Energy makes your energy usage available to download anywhere between 24-72 hours after the day of use. You will only ever be looking at your **historical usage**.

For full details, see [Limitations](https://github.com/iamawumpas/Contact-Energy/wiki/Limitations).

## Free to Use

If anyone finds this repository, you are free to use the code as is - no warranties are provided. It works for me. I may, in the future, modify the functionality to get more information for my HA instance.

---

## Sensors Overview

The integration provides 40+ sensors organized into the following categories:

### 1. Energy Usage Statistics
- Primary usage sensors for Energy Dashboard integration
- Tracks cumulative paid and free electricity consumption (kWh)
- Hourly granularity stored in statistics database

**→ [Complete Energy Dashboard Setup Guide](https://github.com/iamawumpas/Contact-Energy/wiki/Energy-Dashboard-Setup)**

### 2. Account & Billing Information
- Financial sensors (balance, estimated bill, payments)
- Date sensors (bill dates, meter reading schedules)
- Account details (name, email, plan, meter information)
- Rates & charges (daily charges, peak/off-peak rates, free hours)

### 3. Convenience Usage & Cost Sensors
- Quick access to common periods (today, yesterday, last 7/30 days, monthly)
- Cost sensors for daily and monthly expenses
- No need to query statistics database

### 4. Analytics & Insights
- Average daily usage (7-day and 30-day)
- Usage trend analysis (percentage change)
- Cost per kWh efficiency tracking

### 5. Forecasting & Anomaly Detection
- **Forecast sensor:** EMA-based next-day usage predictions
- **Anomaly sensor:** Z-score detection of unusual consumption
- State persistence for instant restarts

**→ [Forecasting & Alerts Documentation](https://github.com/iamawumpas/Contact-Energy/wiki/Forecasting-and-Alerts)**

### 6. Chart Sensors for ApexCharts
- Pre-formatted hourly, daily, and monthly data
- Instant charting without database queries
- Stacked columns, mixed series, custom formatting

**→ [ApexCharts Examples & Configurations](https://github.com/iamawumpas/Contact-Energy/wiki/ApexCharts-Examples)**

---

**For detailed sensor documentation, usage examples, and automation templates, visit the [Sensor Reference](https://github.com/iamawumpas/Contact-Energy/wiki/Sensor-Reference) in our Wiki.**

---

# Changelog

For a detailed list of changes in each version, see the <a href="https://github.com/iamawumpas/Contact-Energy/blob/main/CHANGELOG.md" target="_blank">CHANGELOG.md</a> file.

# Attribution and Acknowledgments

- Original project by [codyc1515](https://github.com/codyc1515/ha-contact-energy)
- Fork by [notf0und](https://github.com/notf0und/ha-contact-energy)

