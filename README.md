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
  <strong>version:</strong> 0.4.3
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

The integration creates three groups of entities:

### 1. Energy Usage Statistics
The ***energy usage*** and ***free energy usage*** sensors (if you take advantage of the free energy option). This data is stored in the Home Assistant statistics database and is visualized in the Energy Dashboard.

### 2. Account & Billing Information Sensors
These sensors expose the following information to dashboard cards:
  - Current bill amount
  - Current bill due date
  - Next bill amount
  - Next bill due date
  - Next reading date
  - Account balance
  - Contract details

### 3. Chart Sensors for ApexCharts
These sensors provide pre-formatted data for charting with ApexCharts card:
  - **Hourly sensors**: Last 14 days of hourly usage (paid and free energy)
  - **Daily sensors**: Last 30 days of daily usage (paid and free energy)
  - **Monthly sensors**: Last 12 months of usage totals (paid and free energy)
  
These sensors store data in their attributes for easy use with the ApexCharts custom card. See the ApexCharts Card Examples section below for configuration examples.


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

This card shows the daily usage and free usage over the last 35 days. The integration creates two sensors that store up to 30 days' worth of data. This example displays the last 31 days of data and excludes the most recent two days of missing data.

This chart is a WIP as I am not fully happy with the layout.

**TO DO:**
- Remove the empty space between the y-axis and displayed data
- Add the first letter of each weekday in the correct space as well as the day
[![Daily Usage Chart](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/image-1.png)](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/ApexCharts%20Card%20-%20Daily%20usage%20example.yaml)

## Monthly Usage and Monthly Free Usage

This card shows the monthly usage and monthly free usage. The integration creates two sensors that fetch all available monthly statistics from your Home Assistant database. The total data displayed will depend on how much historical data exists in your statistics database.
 
 
[![Monthly Usage Chart](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/image-2.png)](https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/custom_components/contact_energy/assets/ApexCharts%20Card%20-%20Monthly%20usage%20exaple.yaml)


# Changelog

For a detailed list of changes in each version, see the <a href="https://github.com/iamawumpas/Contact-Energy/blob/main/CHANGELOG.md" target="_blank">CHANGELOG.md</a> file.

# Attribution and Acknowledgments

- Original project by [codyc1515](https://github.com/codyc1515/ha-contact-energy)
- Fork by [notf0und](https://github.com/notf0und/ha-contact-energy)
