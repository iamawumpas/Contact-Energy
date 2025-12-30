# Sensors Reference

This page documents all 24 sensors provided by the Contact Energy integration.

## Sensor Naming Convention

All sensors follow this naming pattern:
```
sensor.{address}_{icp}_{attribute}
```

**Example:**
```
sensor.123_main_st_0000012345abc_current_balance
sensor.123_main_st_0000012345abc_next_bill_date
```

## Sensor Categories

- [Account Balance](#account-balance-4-sensors) - Balance and refund information
- [Billing Information](#billing-information-5-sensors) - Invoices and payment tracking
- [Next Bill](#next-bill-2-sensors) - Upcoming bill predictions
- [Account Settings](#account-settings-3-sensors) - Preferences and configurations
- [Contract Details](#contract-details-6-sensors) - Property and plan information
- [Payment Plans](#payment-plans-3-sensors) - Direct debit, smooth pay, prepay status
- [Usage Data](#usage-data-placeholders) - ⚠️ Not yet implemented

---

## Account Balance (4 sensors)

### Current Balance

- **Sensor ID**: `sensor.{address}_{icp}_current_balance`
- **Unit**: NZD (New Zealand Dollars)
- **State Class**: Measurement
- **Description**: Your current account balance. Positive values indicate credit, negative values indicate debt.
- **Example Value**: `-125.50` (you owe $125.50) or `45.00` (you have $45 credit)

### Prepay Debt Balance

- **Sensor ID**: `sensor.{address}_{icp}_prepay_debt_balance`
- **Unit**: NZD
- **State Class**: Measurement
- **Description**: Outstanding prepay debt amount (only applicable if you have a prepay meter).
- **Example Value**: `0.00` (no prepay debt)

### Refund Eligible

- **Sensor ID**: `sensor.{address}_{icp}_refund_eligible`
- **Unit**: None
- **Description**: Indicates whether you're eligible to request a refund for credit on your account.
- **Possible Values**: `True` or `False`

### Maximum Refund

- **Sensor ID**: `sensor.{address}_{icp}_maximum_refund`
- **Unit**: NZD
- **State Class**: Measurement
- **Description**: The maximum amount you can request as a refund (if eligible).
- **Example Value**: `125.00`

---

## Billing Information (5 sensors)

### Amount Due

- **Sensor ID**: `sensor.{address}_{icp}_amount_due`
- **Unit**: NZD
- **State Class**: Measurement
- **Description**: Total amount due on your most recent invoice.
- **Example Value**: `235.67`

### Amount Paid

- **Sensor ID**: `sensor.{address}_{icp}_amount_paid`
- **Unit**: NZD
- **State Class**: Measurement
- **Description**: Amount already paid toward your most recent invoice.
- **Example Value**: `100.00`

### Discount Total

- **Sensor ID**: `sensor.{address}_{icp}_discount_total`
- **Unit**: NZD
- **State Class**: Measurement
- **Description**: Total discounts applied to your most recent invoice (e.g., prompt payment discounts, plan discounts).
- **Example Value**: `23.45`

### Payment Due Date

- **Sensor ID**: `sensor.{address}_{icp}_payment_due_date`
- **Unit**: None
- **Device Class**: Date
- **Description**: The date your payment is due.
- **Example Value**: `2025-01-15`

### Days Until Overdue

- **Sensor ID**: `sensor.{address}_{icp}_days_until_overdue`
- **Unit**: days
- **State Class**: Measurement
- **Description**: Number of days until your payment becomes overdue. Negative values indicate the payment is already overdue.
- **Example Value**: `5` (5 days remaining) or `-2` (2 days overdue)

---

## Next Bill (2 sensors)

### Next Bill Date

- **Sensor ID**: `sensor.{address}_{icp}_next_bill_date`
- **Unit**: None
- **Device Class**: Date
- **Description**: Expected date of your next bill/invoice.
- **Example Value**: `2025-02-10`

### Days Until Next Bill

- **Sensor ID**: `sensor.{address}_{icp}_days_until_next_bill`
- **Unit**: days
- **State Class**: Measurement
- **Description**: Number of days until your next bill is issued.
- **Example Value**: `15`

---

## Account Settings (3 sensors)

### Correspondence Preference

- **Sensor ID**: `sensor.{address}_{icp}_correspondence_preference`
- **Unit**: None
- **Description**: How you prefer to receive correspondence from Contact Energy.
- **Possible Values**: `Email`, `Post`, `Both`

### Payment Method

- **Sensor ID**: `sensor.{address}_{icp}_payment_method`
- **Unit**: None
- **Description**: Your current payment method.
- **Possible Values**: `Direct Debit`, `Manual Payment`, `Credit Card`, etc.

### Billing Frequency

- **Sensor ID**: `sensor.{address}_{icp}_billing_frequency`
- **Unit**: None
- **Description**: How often you receive bills.
- **Possible Values**: `Monthly`, `Fortnightly`, `Quarterly`

---

## Contract Details (6 sensors)

### Account Nickname

- **Sensor ID**: `sensor.{address}_{icp}_account_nickname`
- **Unit**: None
- **Description**: Custom nickname for your account (if set in your Contact Energy account).
- **Example Value**: `Home`, `Rental Property`, `Main House`

### ICP

- **Sensor ID**: `sensor.{address}_{icp}_icp`
- **Unit**: None
- **Description**: Your Installation Control Point (ICP) number - the unique identifier for your electricity connection.
- **Example Value**: `0000012345ABC123`

### Address

- **Sensor ID**: `sensor.{address}_{icp}_address`
- **Unit**: None
- **Description**: The full street address for this property/contract.
- **Example Value**: `123 Main Street, Auckland 1010`

### Product Name

- **Sensor ID**: `sensor.{address}_{icp}_product_name`
- **Unit**: None
- **Description**: The name of your current power plan/product.
- **Example Value**: `Good Nights`, `Broadband Bundle`, `Online Plus`

### Contract Type

- **Sensor ID**: `sensor.{address}_{icp}_contract_type`
- **Unit**: None
- **Description**: The type of contract you have.
- **Possible Values**: `Standard`, `Fixed Term`, `Prepay`

### Contract Status

- **Sensor ID**: `sensor.{address}_{icp}_contract_status`
- **Unit**: None
- **Description**: Current status of your contract.
- **Possible Values**: `Active`, `Pending`, `Cancelled`, `Expired`

---

## Payment Plans (3 sensors)

### Direct Debit

- **Sensor ID**: `sensor.{address}_{icp}_is_direct_debit`
- **Unit**: None
- **Description**: Indicates whether automatic direct debit payments are enabled.
- **Possible Values**: `Yes`, `No`

### Smooth Pay

- **Sensor ID**: `sensor.{address}_{icp}_is_smooth_pay`
- **Unit**: None
- **Description**: Indicates whether Smooth Pay (fixed weekly/fortnightly payments) is enabled.
- **Possible Values**: `Yes`, `No`

### Prepay

- **Sensor ID**: `sensor.{address}_{icp}_is_prepay`
- **Unit**: None
- **Description**: Indicates whether you have a prepay meter.
- **Possible Values**: `Yes`, `No`

---

## Usage Data (Placeholders)

⚠️ **Not Yet Implemented** - The following sensors are planned for future releases:

### Daily Usage

- **Sensor ID**: `sensor.{address}_{icp}_daily_usage`
- **Unit**: kWh
- **State Class**: Total Increasing
- **Description**: Total energy usage for the current day.
- **Status**: 🚧 Planned

### Monthly Usage

- **Sensor ID**: `sensor.{address}_{icp}_monthly_usage`
- **Unit**: kWh
- **State Class**: Total
- **Description**: Total energy usage for the current month.
- **Status**: 🚧 Planned

### Hourly Usage

- **Sensor ID**: `sensor.{address}_{icp}_hourly_usage`
- **Unit**: kWh
- **State Class**: Measurement
- **Description**: Energy usage for the current hour.
- **Status**: 🚧 Planned

### Daily Cost

- **Sensor ID**: `sensor.{address}_{icp}_daily_cost`
- **Unit**: NZD
- **State Class**: Total Increasing
- **Description**: Total cost of energy used today.
- **Status**: 🚧 Planned

### Monthly Cost

- **Sensor ID**: `sensor.{address}_{icp}_monthly_cost`
- **Unit**: NZD
- **State Class**: Total
- **Description**: Total cost of energy used this month.
- **Status**: 🚧 Planned

### Peak Rate

- **Sensor ID**: `sensor.{address}_{icp}_peak_rate`
- **Unit**: NZD/kWh
- **State Class**: Measurement
- **Description**: Current peak rate charge.
- **Status**: 🚧 Planned

### Off-Peak Rate

- **Sensor ID**: `sensor.{address}_{icp}_off_peak_rate`
- **Unit**: NZD/kWh
- **State Class**: Measurement
- **Description**: Current off-peak rate charge.
- **Status**: 🚧 Planned

### Daily Charge

- **Sensor ID**: `sensor.{address}_{icp}_daily_charge`
- **Unit**: NZD
- **State Class**: Measurement
- **Description**: Fixed daily connection charge.
- **Status**: 🚧 Planned

---

## Update Schedule

All sensors update **once per day**, scheduled closest to **01:00 AM**.

**Note:** Contact Energy provides data with a delay. Historical usage data may be 24-72 hours behind real-time.

## Using Sensors

### In Automations

Example: Get notified when payment is due soon
```yaml
automation:
  - alias: "Payment Due Soon"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_address_icp123_days_until_overdue
        below: 3
    action:
      - service: notify.mobile_app
        data:
          message: "Your Contact Energy payment is due in {{ states('sensor.my_address_icp123_days_until_overdue') }} days!"
```

### In Dashboard Cards

See the [Dashboards](Dashboards) page for complete examples.

### In Template Sensors

Example: Calculate remaining balance after payment
```yaml
template:
  - sensor:
      - name: "Balance After Payment"
        unit_of_measurement: "NZD"
        state: >
          {{ states('sensor.my_address_icp123_current_balance') | float + 
             states('sensor.my_address_icp123_amount_due') | float }}
```

---

**Next:** [Create Dashboards →](Dashboards)
