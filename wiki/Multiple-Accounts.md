# Multiple Accounts

This guide explains how to monitor multiple Contact Energy properties or accounts in Home Assistant.

## Overview

The Contact Energy integration supports monitoring multiple properties/accounts under the same or different email addresses. Each configured account creates its own set of 26 sensors.

## Use Cases

- **Multiple Properties**: Own several properties with separate electricity connections
- **Rental Properties**: Monitor power usage for properties you rent out
- **Family Accounts**: Track separate accounts for family members
- **Business + Personal**: Keep business and personal electricity separate

## How It Works

### Single Email, Multiple Accounts

If you have multiple properties under one Contact Energy account (one email login):

1. Add the integration once with your credentials
2. During setup, you'll see all properties listed
3. Select the accounts you want to monitor
4. Each selected account creates 26 sensors

### Multiple Email Accounts

If you have accounts under different email addresses:

1. Add the integration for the first email address
2. Configure the accounts for that email
3. Add the integration again with the second email address
4. Configure accounts for that email
5. Repeat for additional email addresses

Each integration instance is independent.

## Configuration Steps

### Adding Multiple Accounts (Same Email)

**Step 1:** Go to Settings → Devices & Services

**Step 2:** Click **+ Add Integration**

**Step 3:** Search for "Contact Energy"

**Step 4:** Enter your credentials
```
Email: your.email@example.com
Password: ••••••••
```

**Step 5:** Select accounts

The integration will show all properties associated with your email:

```
☐ 123 Main Street (ICP: 0000012345ABC)
☐ 456 Oak Avenue (ICP: 0000067890DEF)
☐ 789 Pine Road (ICP: 0000011111GHI)
```

Select the checkboxes for accounts you want to monitor, then click **Submit**.

**Step 6:** Repeat for additional accounts

To add more accounts later:
- Add the integration again with the same email
- Only unconfigured accounts will be shown
- Select additional accounts to monitor

### Adding Multiple Email Accounts

**Step 1:** Add first email account
- Follow the steps above for your first Contact Energy login

**Step 2:** Add integration again
- Click **+ Add Integration** again
- Search for "Contact Energy"

**Step 3:** Enter different credentials
```
Email: second.email@example.com
Password: ••••••••
```

**Step 4:** Configure second account
- Select properties for this email
- Complete setup

**Result:** You now have two separate integrations, each with their own accounts.

## Sensor Organization

### Sensor Naming

Each account creates sensors with unique names:

**Format:** `sensor.{address}_{icp}_{attribute}`

**Example:**
```
# Property 1
sensor.123_main_st_0000012345abc_current_balance
sensor.123_main_st_0000012345abc_next_bill_date

# Property 2
sensor.456_oak_ave_0000067890def_current_balance
sensor.456_oak_ave_0000067890def_next_bill_date
```

The address and ICP ensure sensors are unique for each property.

### Device Organization

In **Settings → Devices & Services → Contact Energy**, you'll see:
- One integration per email address
- One device per property/account
- 24 entities per device

## Dashboard Tips

### Separate Tabs for Each Property

Create a tab for each property in your dashboard:

**Tab 1: Main Street**
```yaml
# Cards showing sensor.123_main_st_* sensors
```

**Tab 2: Oak Avenue**
```yaml
# Cards showing sensor.456_oak_ave_* sensors
```

### Combined Overview

Create a summary showing key metrics from all properties:

```yaml
type: entities
title: All Properties - Balance Summary
entities:
  - entity: sensor.123_main_st_0000012345abc_current_balance
    name: "Main Street"
  - entity: sensor.456_oak_ave_0000067890def_current_balance
    name: "Oak Avenue"
  - entity: sensor.789_pine_rd_0000011111ghi_current_balance
    name: "Pine Road"
```

### Total Balance Template

Calculate total balance across all properties:

```yaml
template:
  - sensor:
      - name: "Total Contact Energy Balance"
        unit_of_measurement: "NZD"
        state: >
          {{
            states('sensor.123_main_st_0000012345abc_current_balance') | float(0) +
            states('sensor.456_oak_ave_0000067890def_current_balance') | float(0) +
            states('sensor.789_pine_rd_0000011111ghi_current_balance') | float(0)
          }}
```

### Multi-Property Payment Reminder

Automation that checks all properties:

```yaml
automation:
  - alias: "All Properties - Payment Check"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - repeat:
          count: 3
          sequence:
            - choose:
                - conditions:
                    - condition: numeric_state
                      entity_id: >
                        {% set entities = [
                          'sensor.123_main_st_0000012345abc_days_until_overdue',
                          'sensor.456_oak_ave_0000067890def_days_until_overdue',
                          'sensor.789_pine_rd_0000011111ghi_days_until_overdue'
                        ] %}
                        {{ entities[repeat.index - 1] }}
                      below: 3
                  sequence:
                    - service: notify.mobile_app
                      data:
                        message: >
                          Payment due soon for property {{ repeat.index }}
```

## Managing Multiple Accounts

### Viewing All Integrations

1. Go to **Settings** → **Devices & Services**
2. Find "Contact Energy" entries (one per email)
3. Click to expand and see configured accounts

### Adding More Accounts

To add accounts to an existing email:
1. Click **+ Add Integration**
2. Enter the same email and password
3. Only unconfigured accounts will be shown
4. Select additional accounts

### Removing an Account

1. Go to **Settings** → **Devices & Services**
2. Find the Contact Energy integration
3. Click on the device (property) you want to remove
4. Click **Delete** (trash icon)

**Note:** This removes only that property, not the entire integration.

### Removing an Email Integration

To remove all properties under an email:
1. Go to **Settings** → **Devices & Services**
2. Find the Contact Energy integration for that email
3. Click the three dots (⋮)
4. Click **Delete**

This removes all devices and sensors for that email address.

## Limitations

### Duplicate Prevention

The integration prevents adding the same account twice:
- Uses ICP number to identify accounts
- Already-configured accounts are hidden from selection
- You cannot add the same property multiple times

### Account Filtering

When adding the integration with the same email:
- Only shows accounts not yet configured
- If all accounts are already added, you'll see "No new accounts available"

### Update Timing

All accounts update at the same time (01:00 AM), regardless of how many you have configured.

## Troubleshooting

### Can't See My Second Property

**Problem:** Only one property shows during setup, but I have multiple

**Solutions:**
- Verify both properties are under the same email login on Contact Energy's website
- Check that the second property has an active contract
- Try removing and re-adding the integration

### Duplicate Sensor Names

**Problem:** Sensor names are conflicting between properties

**Solution:**
- This shouldn't happen as sensors include the address and ICP
- If it does occur, the properties likely have identical addresses
- Contact support on GitHub

### Account Already Configured

**Problem:** "This account is already configured" error

**Solution:**
- The ICP is already added to Home Assistant
- Check **Settings** → **Devices & Services** → **Contact Energy**
- Remove the existing device if you want to reconfigure it

### Mixed Email Accounts

**Problem:** I have properties under different Contact Energy emails

**Solution:**
- You need to add the integration multiple times
- Each email requires a separate integration instance
- Each integration can have multiple properties

---

## Examples

### Example 1: Landlord with 3 Properties

**Setup:**
- All properties under one Contact Energy account (one email)
- Add integration once
- Select all 3 properties during setup
- Result: 72 sensors total (24 per property)

**Dashboard:**
- Create 3 tabs, one per property
- Create a 4th "Overview" tab showing key metrics from all properties

### Example 2: Personal + Rental (Different Emails)

**Setup:**
- Personal property: personal@email.com
- Rental property: rental@email.com
- Add integration twice with different emails
- Result: 2 integration instances, 48 sensors total

**Dashboard:**
- Tab 1: Personal property
- Tab 2: Rental property
- Use different colored themes per tab for visual separation

### Example 3: Family with Separate Accounts

**Setup:**
- Your account: you@email.com (Your house)
- Partner's account: partner@email.com (Parents' house)
- Add integration twice
- Result: 2 separate accounts, independently managed

**Automations:**
- Create separate automations for each property
- Use different notification targets for each account

---

**Next:** [FAQ & Troubleshooting →](FAQ)
