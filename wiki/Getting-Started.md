# Getting Started

This guide will walk you through installing and configuring the Contact Energy integration in Home Assistant.

## Prerequisites

- Home Assistant 2023.1 or later
- A Contact Energy account (New Zealand)
- Your Contact Energy login credentials (email and password)

## Installation

### Method 1: HACS (Recommended)

1. **Install HACS** (if not already installed)
   - Follow the [HACS installation guide](https://hacs.xyz/docs/setup/download)

2. **Add Custom Repository**
   - Open HACS in Home Assistant
   - Click on **Integrations**
   - Click the **three dots** (⋮) in the top right corner
   - Select **Custom repositories**

3. **Add Contact Energy**
   - Repository URL: `https://github.com/iamawumpas/Contact-Energy`
   - Category: **Integration**
   - Click **Add**

4. **Install the Integration**
   - Search for "Contact Energy" in HACS
   - Click **Download**
   - Restart Home Assistant

### Method 2: Manual Installation

1. **Download the Integration**
   - Go to the [Releases page](https://github.com/iamawumpas/Contact-Energy/releases)
   - Download the latest release ZIP file

2. **Extract Files**
   - Unzip the downloaded file
   - Copy the `contact_energy` folder

3. **Install to Home Assistant**
   - Navigate to your Home Assistant `config` directory
   - Create a `custom_components` folder if it doesn't exist
   - Paste the `contact_energy` folder inside `custom_components`
   
   Final structure:
   ```
   config/
   └── custom_components/
       └── contact_energy/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           ├── coordinator.py
           ├── sensor.py
           └── ...
   ```

4. **Restart Home Assistant**

## Configuration

### Adding Your First Account

1. **Open Integrations**
   - Go to **Settings** → **Devices & Services**
   - Click **+ Add Integration** (bottom right)

2. **Find Contact Energy**
   - Search for "Contact Energy"
   - Click on it to start setup

3. **Enter Credentials**
   - **Email**: Your Contact Energy account email
   - **Password**: Your Contact Energy account password
   - Click **Submit**

4. **Select Account**
   - If you have multiple properties/accounts, you'll see a list
   - Select the account(s) you want to monitor
   - For a single account, click **Submit** to confirm

5. **Complete Setup**
   - The integration will create sensors for your account
   - Sensors will appear in Home Assistant with names like:
     ```
     sensor.{address}_{icp}_{attribute}
     ```

### First Data Update

- Sensors will show "Unknown" or "Unavailable" initially
- The first update occurs at the next scheduled time (01:00 AM)
- **To force an immediate update**, use the `contact_energy.refresh_data` service:
  1. Go to **Developer Tools** → **Actions**
  2. Select action: `contact_energy.refresh_data`
  3. Click **Perform Action**
- Alternatively, restart Home Assistant or reload the integration

## Verifying Installation

### Check Integration Status

1. Go to **Settings** → **Devices & Services**
2. Find **Contact Energy** in the list
3. You should see:
   - Integration name
   - Number of devices (1 per account)
   - Number of entities (24 per account)

### Check Sensors

1. Go to **Developer Tools** → **States**
2. Search for your account name or ICP number
3. You should see 24 sensors with names like:
   ```
   sensor.my_address_icp123_current_balance
   sensor.my_address_icp123_next_bill_date
   sensor.my_address_icp123_payment_method
   ```

## Common Setup Issues

### Integration Not Found

**Problem**: Can't find "Contact Energy" when adding integration

**Solution**:
- Ensure you've restarted Home Assistant after installation
- Clear your browser cache (Ctrl+F5 or Cmd+Shift+R)
- Check that the `contact_energy` folder is in `custom_components`

### Authentication Failed

**Problem**: "Invalid credentials" or "Authentication failed" error

**Solution**:
- Verify your email and password are correct
- Try logging into the [Contact Energy website](https://www.contact.co.nz/) to confirm
- Ensure your account is active and not suspended

### No Accounts Available

**Problem**: "No accounts found" message during setup

**Solution**:
- Ensure you have an active contract with Contact Energy
- Check that your account has a property with a valid ICP number
- Wait a few minutes and try again (API may be temporarily unavailable)

### Sensors Show "Unknown"

**Problem**: All sensors show "Unknown" or "Unavailable"

**Solution**:
- This is normal for the first few hours after setup
- **Force an immediate update** using the `contact_energy.refresh_data` service (see below)
- Wait for the next scheduled update (01:00 AM)
- Check **Settings** → **System** → **Logs** for any error messages
- Restart Home Assistant or reload the integration

**To force an immediate data refresh:**
1. Go to **Developer Tools** → **Actions**
2. Select action: `contact_energy.refresh_data`
3. Click **Perform Action**
4. Wait 5-10 seconds for data to download

## Next Steps

- [View All Sensors](Sensors) - Complete list of available sensors
- [Create Dashboards](Dashboards) - Display your energy data
- [Add Multiple Accounts](Multiple-Accounts) - Monitor multiple properties

---

**Having trouble?** Check the [FAQ & Troubleshooting](FAQ) page.
