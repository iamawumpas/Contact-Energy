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
  <strong>version:</strong> 0.7.2
    </td>
  </tr>
</table>

## Table of Contents

- [About This Integration](#about-this-integration)
- [Why Make My Own Version](#why-make-my-own-version)
- [What Does the Integration Do?](#what-does-the-integration-do)
  - [Energy Usage Statistics](#1-energy-usage-statistics)
  - [Account & Billing Information](#2-account--billing-information-sensors)
  - [Chart Sensors for ApexCharts](#3-chart-sensors-for-apexcharts)
  - [Phase 3: Forecasts & Alerts](#phase-3-forecasts--alerts)
- [Limitations](#limitations)
- [Free to Use](#free-to-use)
- [Installation](#installation)
  - [HACS (Recommended)](#hacs-recommended)
  - [Manual Installation](#manual-installation)
- [Getting Started](#getting-started)
  - [Modifying Settings After Installation](#modifying-settings-after-installation)
- [Viewing Usage Data in Energy Dashboard](#viewing-usage-data-and-costs-in-home-assistant)
- [ApexCharts Card Examples](#apexcharts-card-examples)
  - [Hourly Usage Chart](#hourly-usage-and-free-usage)
  - [Daily Usage Chart](#daily-usage-and-daily-free-usage)
  - [Monthly Usage Chart](#monthly-usage-and-monthly-free-usage)
- [Changelog](#changelog)
- [Attribution and Acknowledgments](#attribution-and-acknowledgments)

---

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

---

## Sensors Overview

### 1. Energy Usage Statistics (Energy Dashboard Integration)

**Primary Usage Sensor:**
- `sensor.contact_energy_usage_[ICP]` - Total electricity consumption (kWh)
  - **Purpose:** Tracks cumulative paid electricity usage for the Energy Dashboard
  - **Dashboard Use:** Automatically integrated with Home Assistant Energy Dashboard
  - **Automation Use:** Track total consumption, compare periods, trigger on usage thresholds
  - **Data Source:** Statistics database with hourly granularity

**Free Energy Sensor (if applicable):**
- `sensor.contact_energy_free_usage_[ICP]` - Free electricity consumption (kWh)
  - **Purpose:** Tracks cumulative free electricity usage (e.g., off-peak hours, free weekends)
  - **Dashboard Use:** Add to Energy Dashboard as separate consumption source
  - **Automation Use:** Monitor free energy utilization, optimize usage during free periods
  - **Data Source:** Statistics database with hourly granularity

**How to Use:**
1. Go to **Settings → Dashboards → Energy**
2. Click **"Add Consumption"** and select the usage sensor(s)
3. Optionally track costs with static or dynamic pricing

---

### 2. Account & Billing Information Sensors

These sensors display account details and are ideal for dashboard cards showing billing status:

**Financial Sensors:**
- `sensor.contact_energy_account_balance_[ICP]` - Current account balance (NZD)
- `sensor.contact_energy_estimated_next_bill_[ICP]` - Estimated next bill amount (NZD)
- `sensor.contact_energy_last_payment_[ICP]` - Last payment amount (NZD)

**Date Sensors:**
- `sensor.contact_energy_next_bill_date_[ICP]` - Next billing date
- `sensor.contact_energy_next_read_date_[ICP]` - Next meter reading date
- `sensor.contact_energy_last_read_date_[ICP]` - Last meter reading date

**Account Details:**
- `sensor.contact_energy_customer_name_[ICP]` - Account holder name
- `sensor.contact_energy_email_[ICP]` - Account email address
- `sensor.contact_energy_account_number_[ICP]` - Account number
- `sensor.contact_energy_plan_name_[ICP]` - Current plan type

**Rates & Charges:**
- `sensor.contact_energy_daily_charge_rate_[ICP]` - Daily fixed charge (NZD)
- `sensor.contact_energy_peak_rate_[ICP]` - Peak electricity rate (NZD/kWh)
- `sensor.contact_energy_off_peak_rate_[ICP]` - Off-peak rate (NZD/kWh)
- `sensor.contact_energy_free_hours_[ICP]` - Free power hours schedule

**Property & Meter:**
- `sensor.contact_energy_service_address_[ICP]` - Service address (short form)
- `sensor.contact_energy_full_address_[ICP]` - Complete address with attributes
- `sensor.contact_energy_meter_serial_[ICP]` - Meter serial number
- `sensor.contact_energy_meter_register_[ICP]` - Current meter reading (kWh)

**Enhanced Details:**
- `sensor.contact_energy_payment_history_[ICP]` - Payment count (with last 5 payments in attributes)
- `sensor.contact_energy_contract_details_[ICP]` - Contract status and details

**Dashboard Use:**
- Add to entity cards, markdown cards, or custom dashboards
- Group related sensors (billing, rates, property info) into sections
- Use in conditional cards to highlight overdue balances or upcoming dates

**Automation Use:**
- Trigger notifications before bill due dates
- Alert when account balance exceeds threshold
- Track payment history and schedule reminders

See the [Markdown Card Example](#markdown-card-example) section for a comprehensive account summary card.

---

### 3. Convenience Usage & Cost Sensors

These sensors provide quick access to common usage periods without querying the statistics database:

**Usage Sensors (kWh):**
- `sensor.contact_energy_today_usage_[ICP]` - Today's paid usage
- `sensor.contact_energy_yesterday_usage_[ICP]` - Yesterday's paid usage
- `sensor.contact_energy_last_7_days_usage_[ICP]` - Last 7 days total
- `sensor.contact_energy_last_30_days_usage_[ICP]` - Last 30 days total
- `sensor.contact_energy_current_month_usage_[ICP]` - Current month total
- `sensor.contact_energy_last_month_usage_[ICP]` - Last month total

**Free Usage Sensors (kWh):**
- `sensor.contact_energy_today_free_usage_[ICP]` - Today's free usage
- `sensor.contact_energy_yesterday_free_usage_[ICP]` - Yesterday's free usage

**Cost Sensors (NZD):**
- `sensor.contact_energy_today_cost_[ICP]` - Today's electricity cost
- `sensor.contact_energy_yesterday_cost_[ICP]` - Yesterday's cost
- `sensor.contact_energy_current_month_cost_[ICP]` - Current month cost
- `sensor.contact_energy_last_month_cost_[ICP]` - Last month cost

**Dashboard Use:**
- Display in gauge cards to show daily/weekly/monthly consumption at a glance
- Add to entity cards or picture-elements cards
- Create conditional cards that change color based on usage thresholds
- Show cost breakdowns in markdown tables

**Automation Use:**
- Trigger notifications when daily usage exceeds typical amounts
- Send weekly/monthly usage summaries
- Compare current vs previous periods for usage alerts

---

### 4. Analytics & Insights Sensors

These sensors provide intelligent analysis to help you understand consumption patterns:

**Average Usage Sensors:**
- `sensor.contact_energy_average_daily_usage_7_days_[ICP]` - 7-day daily average (kWh)
  - **Purpose:** Short-term usage pattern analysis
  - **Dashboard Use:** Display in gauge or history graph to track recent trends
  - **Automation Use:** Alert when current usage deviates from 7-day average
  
- `sensor.contact_energy_average_daily_usage_30_days_[ICP]` - 30-day daily average (kWh)
  - **Purpose:** Monthly usage baseline for comparison
  - **Dashboard Use:** Compare against shorter periods to identify changes
  - **Automation Use:** Set baseline thresholds for anomaly detection

**Trend Analysis:**
- `sensor.contact_energy_usage_trend_[ICP]` - Usage trend percentage (%)
  - **Purpose:** Compares last 7 days vs previous 7 days
  - **State:** Positive % = increasing usage, Negative % = decreasing usage
  - **Attributes:** `current_period_kwh`, `previous_period_kwh`, `trend_direction`
  - **Dashboard Use:** Display in entity card with color coding (red for increase, green for decrease)
  - **Automation Use:** Alert on significant increases (e.g., trend > 20%)

**Cost Efficiency:**
- `sensor.contact_energy_cost_per_kwh_[ICP]` - Actual cost per kWh (NZD/kWh)
  - **Purpose:** Shows real average cost including all charges over 30 days
  - **Attributes:** `total_kwh`, `total_cost`, `period` (30 days)
  - **Dashboard Use:** Compare against advertised rates to see actual cost efficiency
  - **Automation Use:** Alert if cost per kWh exceeds expected rate

**Dashboard Use Examples:**
```yaml
# Gauge showing 7-day average
type: gauge
entity: sensor.contact_energy_average_daily_usage_7_days_[ICP]
min: 0
max: 50
needle: true
segments:
  - from: 0
    color: green
  - from: 30
    color: orange
  - from: 40
    color: red

# Trend card with conditional color
type: entity
entity: sensor.contact_energy_usage_trend_[ICP]
card_mod:
  style: |
    :host {
      --card-mod-icon-color: {% if states('sensor.contact_energy_usage_trend_[ICP]')|float > 0 %}red{% else %}green{% endif %};
    }
```

---

### 5. Forecasting & Anomaly Detection (Phase 3)

**Forecast Sensor:**
- `sensor.contact_energy_forecast_daily_usage_[ICP]` - Predicted next-day usage (kWh)
  - **Purpose:** Forecasts next day's paid usage using EMA (Exponential Moving Average)
  - **Method:** 30-day window with alpha = 2/(N+1)
  - **Attributes:**
    - `method`: "EMA"
    - `window_days`: 30
    - `alpha`: Smoothing factor (~0.065)
    - `mean_30d`: Average over baseline period
    - `std_30d`: Standard deviation
    - `last_observation`: Most recent daily usage
    - `lower_2sigma`: Lower confidence band (mean - 2σ)
    - `upper_2sigma`: Upper confidence band (mean + 2σ)
  
  **Dashboard Use:**
  - Display forecast value in entity card or gauge
  - Add to history graph alongside actual usage for comparison
  - Show confidence bands (2-sigma) in mini-graph card
  - Use in markdown card to display "Expected tomorrow: X kWh"
  
  **Automation Use:**
  - Send daily forecast notifications
  - Pre-heat/pre-cool based on predicted high usage days
  - Adjust smart device schedules to stay within forecast

**Historical Anomaly Binary Sensor:**
- `binary_sensor.contact_energy_historical_usage_anomaly_[ICP]` - Anomaly detection (on/off)
  - **Purpose:** Flags unusual usage when delayed data arrives (not real time)
  - **Detection:** Z-score > 2.5 vs last 30 days baseline
  - **State:** `on` = anomaly detected, `off` = normal usage
  - **Device Class:** problem
  - **Attributes:**
    - `z_score`: How many standard deviations from baseline
    - `threshold`: Detection threshold (default 2.5)
    - `baseline_days`: 30
    - `baseline_mean`: Average usage over baseline
    - `baseline_std`: Standard deviation
    - `today_usage`: Latest usage value that triggered check
  
  **Dashboard Use:**
  - Add to entity card or badge to show current status
  - Use in conditional cards to highlight when anomaly is detected
  - Display z-score value in markdown for technical users
  - Show historical anomaly trend in history graph
  
  **Automation Use (Primary Purpose):**
  - Trigger alerts when state changes to `on`
  - Send notifications with z-score and usage details
  - Create persistent notifications for investigation
  - Log anomalies to file or external system
  
  **Example Automation:**
  ```yaml
  trigger:
    - platform: state
      entity_id: binary_sensor.contact_energy_historical_usage_anomaly_[ICP]
      to: 'on'
  action:
    - service: notify.mobile_app_your_phone
      data:
        title: "⚠️ Usage Anomaly Detected"
        message: >
          Unusual usage: {{ state_attr('binary_sensor.contact_energy_historical_usage_anomaly_[ICP]', 'today_usage')|round(1) }} kWh
          ({{ state_attr('binary_sensor.contact_energy_historical_usage_anomaly_[ICP]', 'z_score')|round(1) }}σ above normal)
  ```

**Important Note:** Contact Energy data is delayed by 24–72 hours. These sensors detect anomalies as soon as new historical data is released—not in real time. They're useful for:
- Spotting billing errors after data arrives
- Identifying appliance faults or unusual consumption patterns
- Catching unexpected usage spikes for investigation
- Retrospective analysis rather than live monitoring

**Alerting Options:**
- Persistent notification (built-in): `persistent_notification.create`
- Mobile app: `notify.mobile_app_your_phone`
- Email: `notify.email`
- Other notify services: See Home Assistant notify documentation

See the example in `custom_components/contact_energy/assets/Automation - Usage Anomaly Alert.yaml` for a complete automation template.

---

### 6. Chart Sensors for ApexCharts

These sensors store pre-formatted historical data in attributes for easy charting:

**Hourly Chart Sensors:**
- `sensor.contact_energy_chart_hourly_[ICP]` - Last 14 days hourly paid usage
- `sensor.contact_energy_chart_hourly_free_[ICP]` - Last 14 days hourly free usage
  - **Data Format:** Hourly delta values (kWh per hour)
  - **Attribute:** `hourly_data` or `hourly_free_data` (ISO timestamp → kWh)

**Daily Chart Sensors:**
- `sensor.contact_energy_chart_daily_[ICP]` - Last 60 days daily paid usage
- `sensor.contact_energy_chart_daily_free_[ICP]` - Last 60 days daily free usage
  - **Data Format:** Daily delta values (kWh per day at 23:59:59)
  - **Attribute:** `daily_data` or `daily_free_data` (ISO date → kWh)

**Monthly Chart Sensors:**
- `sensor.contact_energy_chart_monthly_[ICP]` - All available monthly paid usage
- `sensor.contact_energy_chart_monthly_free_[ICP]` - All available monthly free usage
  - **Data Format:** Monthly totals (kWh per month)
  - **Attribute:** `monthly_data` or `monthly_free_data` (YYYY-MM-15 → kWh)

**Dashboard Use:**
- **Primary Purpose:** Used with ApexCharts custom card for advanced visualizations
- Data is stored in attributes and accessed via `data_generator` in ApexCharts config
- See [ApexCharts Card Examples](#apexcharts-card-examples) section for complete configurations

**Why These Exist:**
- Home Assistant statistics can be slow to query for large date ranges
- Pre-formatted data in attributes provides instant charting without database queries
- Allows complex visualizations (stacked columns, mixed series, custom formatting)

---

### Summary: Which Sensors to Use

**For Energy Dashboard:**
- `sensor.contact_energy_usage_[ICP]` (paid usage)
- `sensor.contact_energy_free_usage_[ICP]` (free usage)

**For Quick Dashboard Cards:**
- Convenience sensors (today, yesterday, last 7 days, etc.)
- Account & billing sensors (balance, next bill, rates)

**For Analysis & Insights:**
- Analytics sensors (averages, trends, cost per kWh)
- Forecast sensor (predicted usage)

**For Alerts & Automations:**
- Historical anomaly binary sensor (unusual usage detection)
- Usage trend sensor (increasing/decreasing patterns)
- Convenience sensors with threshold triggers

**For Advanced Charts:**
- Chart sensors with ApexCharts card (hourly, daily, monthly visualizations)


## Limitations

The data provided by Contact Energy is significantly limited, and so there are caveats to the usefulness of this integration.

### No Real-Time Monitoring
**This is the most important limitation.** Contact Energy makes your energy usage available to download anywhere between 24-72 hours after the day of use. So, you will only ever be looking at your **historical usage**. You will be able to see monthly, daily and hourly statistics once the data has been downloaded.

**Some context:** The Genesis smart meters installed in most NZ homes since the 1990s report back to their host using the cellular network once a day (<https://www.ea.govt.nz/your-power/meters/>)

### Automatic Daily Restart
To maintain reliable operation, the integration automatically restarts itself once per day at approximately 3:00 AM (±30 minutes random variance). This helps ensure fresh API connections and clears any accumulated state issues. The restart is seamless and does not require manual intervention.

# Free to Use

If anyone finds this repository, you are free to use the code as is - no warranties are provided. It works for me. I may, in the future, modify the functionality to get more information for my HA instance.


# **Installation**  

> **Compatibility:** This integration requires Home Assistant version **2023.1 or later**.

## **HACS (Recommended)**  

1. Ensure [HACS is installed](https://hacs.xyz/docs/setup/download).  
2. Click the button below to open the repository in HACS:  
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=iamawumpas&repository=contact_energy&category=integration)  
3. Install the **Contact Energy** integration.  
4. Restart Home Assistant.  

## **Manual Installation**  

1. Download the integration files from the repository.  
2. Copy all files from `custom_components/contact_energy` to your Home Assistant folder `config/custom_components/contact_energy`.
3. Restart Home Assistant.

## Getting Started

1. Open Home Assistant and navigate to: **Settings → Devices & Services → + Add Integration**
2. Search for **Contact Energy** and select it.
3. Enter the required details:
   - **Email & Password**: Use the credentials for your Contact Energy account
   - **Usage Months**: Number of months of historical data to fetch (1–36 months; backend uses calendar months to compute the exact number of days for API downloads)

Once configured, the integration will begin fetching and displaying your account and usage data.

### Multiple Properties or Accounts

**The integration fully supports multiple instances** - you can monitor multiple properties or accounts simultaneously. All sensors are dynamically created with unique IDs based on the ICP number.

#### Option 1: Multiple ICPs on Same Account
If you have multiple properties under one Contact Energy account:
1. Add the integration again (**Settings → Devices & Services → + Add Integration**)
2. Enter the same email and password
3. Select a different ICP number
4. Each instance creates separate sensors: `sensor.contact_energy_usage_<icp1>`, `sensor.contact_energy_usage_<icp2>`, etc.

#### Option 2: Different Accounts
If you manage multiple Contact Energy accounts (e.g., rental properties, family members):
1. Add the integration again
2. Enter different email credentials for each account
3. Select the ICP for that account
4. All sensors remain completely independent

**All sensors are uniquely identified by ICP number**, so there are no conflicts between multiple instances. You'll get a complete set of account, billing, usage, and chart sensors for each property.

### Modifying Settings After Installation

You can change the **Usage Months** setting after installation:

1. Go to **Settings → Devices & Services**.
2. Find the **Contact Energy** integration.
3. Click the three dots (⋮) and select **Configure**.
4. Adjust the usage months as needed.

## Viewing Usage Data and Costs in Home Assistant

To see your electricity usage and costs in Home Assistant's Energy Dashboard, follow these steps:

1. Go to **Settings → Dashboards → Energy**.
2. Click **"Add Consumption"** and select:
   - **Contact Energy - Electricity (xxx)** where **xxx** represents your ICP number.
   - Select how Home Assistant should keep track of costs:
     - **Do not track costs** - If you're only interested in kWh usage.
     - **Use a static price** - If you want to track costs.
     - This cost tracking feature is from cody1515's original implementation.

3. If you have Free Energy services on your account (e.g., 9pm-midnight or free weekends):
   - Click **"Add Consumption"** again.
   - Select **Contact Energy - Free Electricity (xxx)** where **xxx** is your ICP number.
   - Make sure you select the same ICP number as Step 2 if monitoring multiple properties.


# ApexCharts Card Examples

These examples are what is currently on my desktop. Feel free to use them as templates to display your electricity usage in the format that you want. These charts are not perfect due to the limitations of the <a href="https://community.home-assistant.io/t/apexcharts-card-a-highly-customizable-graph-card/272877" target="_blank">ApexChart-card</a> implementation of ApexCharts.js.

**Click on any chart image below to view the underlying YAML configuration file.**

## Hourly Usage and Free Usage

This card shows the hourly usage and hourly free usage. The integration creates two sensors that store up to 14 days' worth of data. This example displays the last 8 days of data and excludes the most recent two days of missing data.
[![Hourly Usage Chart](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/image.png)](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/ApexCharts%20Card%20-%20Hourly%20usage%20example.yaml)

## Daily Usage and Daily Free Usage

This card shows the daily usage and free usage over the last 35 days. The integration creates two sensors that store up to 60 days' worth of data. This example displays the last 35 days of data and excludes the most recent two days of missing data.

**TO DO:**
- Add the first letter of each weekday in the correct space as well as the day
[![Daily Usage Chart](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/image-1.png)](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/ApexCharts%20Card%20-%20Daily%20usage%20example.yaml)

## Monthly Usage and Monthly Free Usage

This card shows the monthly usage and monthly free usage. The integration creates two sensors that fetch all available monthly statistics from your Home Assistant database. The total data displayed will depend on how much historical data exists in your statistics database.
 
 
[![Monthly Usage Chart](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/image-2.png)](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/ApexCharts%20Card%20-%20Monthly%20usage%20exaple.yaml)


# Markdown Card Example

The integration includes a comprehensive account details summary card that displays all your Contact Energy account information in a clean, organized format. This markdown card provides an at-a-glance view of:

- **Account Details**: Customer name, email, account number, plan, meter details, full address, and contract information
- **Billing Information**: Outstanding balance, estimated next bill, payment dates, reading schedules, and payment history
- **Current Rates**: Daily charges, peak/off-peak rates, and free hours
- **Usage Summary**: Current month costs and usage, daily statistics, historical data, and meter readings

The card automatically formats currency values, dates, and usage units (kWh) for easy reading. New sensors added in recent versions are highlighted for quick identification. The template includes custom styling with scrollable content and grouped sections for better organization.

**Click the image below to view the YAML configuration:**

[![Account Details Summary Card](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/image-4.png)](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/Account%20Details%20Summary%20Example.yaml)


# Changelog

For a detailed list of changes in each version, see the <a href="https://github.com/iamawumpas/Contact-Energy/blob/main/CHANGELOG.md" target="_blank">CHANGELOG.md</a> file.

# Attribution and Acknowledgments

- Original project by [codyc1515](https://github.com/codyc1515/ha-contact-energy)
- Fork by [notf0und](https://github.com/notf0und/ha-contact-energy)
