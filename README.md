# Contact Energy Integration for Home Assistant

**Version:** 0.0.3

A streamlined, memory-efficient Home Assistant integration for Contact Energy (New Zealand) that downloads your electricity usage and account data for use with the Energy Dashboard and ApexCharts.

## 🚀 Key Features

- **Energy Dashboard Integration**: Usage data is written directly to Home Assistant's statistics database
- **ApexCharts Support**: Historical data available for monthly/daily/hourly charts
- **Smart Data Downloads**: Only downloads missing data after initial setup (no memory waste)
- **Account Information**: Balance, bill dates, payment information sensors  
- **Free Energy Tracking**: Separate tracking for free electricity plans
- **8-Hour Polling**: Efficient data updates every 8 hours
- **Memory Efficient**: Designed to be smaller and lighter than existing solutions

## 📋 Requirements

- Home Assistant 2023.1.0 or later
- Contact Energy account (New Zealand customers only)
- Email and password for your Contact Energy account

## 🔧 Installation

### HACS (Recommended)

1. Ensure [HACS is installed](https://hacs.xyz/docs/setup/download)
2. Add this repository to HACS as a custom repository:
   - Go to HACS → Integrations → ⋮ → Custom repositories
   - Repository: `https://github.com/iamawumpas/contact-energy`
   - Category: Integration
3. Install the **Contact Energy** integration
4. Restart Home Assistant

### Manual Installation

1. Download the integration files from this repository
2. Copy the `custom_components/contact_energy` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## ⚙️ Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Contact Energy" and select it
3. Enter your configuration:
   - **Email**: Your Contact Energy account email
   - **Password**: Your Contact Energy account password  
   - **Usage Days**: Number of days to download initially (1-100, recommended: 30)

4. If you have multiple electricity contracts, select the one you want to monitor
5. The integration will start downloading your data

## 📊 Energy Dashboard Setup

To view your data in Home Assistant's Energy Dashboard:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **Add Consumption** and select:
   - **Contact Energy - Energy Consumption (xxx)** (where xxx is your ICP number)
3. For costs, select **"Do not track costs"** or configure as needed
4. If you have free energy periods, add:
   - **Contact Energy - Free Energy Consumption (xxx)**

## 📈 ApexCharts Integration

The usage data is stored in Home Assistant's statistics database, making it compatible with ApexCharts for advanced visualizations:

```yaml
type: custom:apexcharts-card
header:
  title: Daily Energy Usage
  show: true
graph_span: 30d
span:
  start: month
series:
  - entity: sensor.contact_energy_energy_consumption_xxx
    type: column
    group_by:
      func: diff
      duration: 1d
```

## 🔍 Available Sensors

### Account Sensors

- Account Balance
- Next Bill Amount & Date
- Payment Due Amount & Date  
- Previous/Next Reading Dates

### Usage Sensors (Statistics)

- Energy Consumption (kWh) - *for Energy Dashboard*
- Energy Cost (NZD) - *for cost tracking*
- Free Energy Consumption (kWh) - *for free power plans*

## ⚠️ Important Limitations

- **No Real-Time Data**: Contact Energy provides usage data 24-72 hours after consumption
- **Historical Data Only**: You're viewing past usage, not current consumption
- **NZ Genesis Smart Meters**: Data is uploaded once daily via cellular network

## 🔄 How It Works

1. **Initial Setup**: Downloads your specified number of days (1-100)
2. **Smart Updates**: Only downloads missing days on subsequent runs
3. **8-Hour Polling**: Checks for new data every 8 hours
4. **Statistics Storage**: Writes directly to HA statistics database (memory efficient)
5. **Energy Dashboard**: Automatically available for energy tracking
6. **ApexCharts**: Historical data accessible via statistics queries

## 🛠️ Troubleshooting

### Integration Not Loading
- Check that Home Assistant version is 2023.1.0 or later
- Verify your Contact Energy credentials are correct
- Check logs for authentication errors

### No Usage Data
- Wait 24-72 hours after initial setup (Contact Energy data delay)
- Check that you have an active electricity contract
- Verify your ICP number in the device information

### ApexCharts Not Showing Data
- Ensure you're querying the statistics, not the sensor state
- Use the correct sensor entity names with your ICP number
- Try different `group_by` functions (sum, diff, mean)

## 🔧 Development

This is a clean, streamlined implementation focused on:
- Memory efficiency 
- Smart data downloading
- Statistics database integration
- ApexCharts compatibility

Built for Home Assistant 2023.1+ with modern best practices.

## 📄 License

Free to use - no warranties provided. Use at your own risk.

## 🙏 Attribution

Inspired by the original Contact Energy integrations:
- [codyc1515](https://github.com/codyc1515/ha-contact-energy) - Original implementation
- [notf0und](https://github.com/notf0und/ha-contact-energy) - Community fork

---

**Contact Energy Integration v1.0.0** - A memory-efficient solution for New Zealand Home Assistant users.
