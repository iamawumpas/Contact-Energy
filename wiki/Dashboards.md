# Dashboards

This page provides examples for displaying your Contact Energy data in Home Assistant dashboards.

## Quick Links

- [Markdown Card - Sidebar Layout](#markdown-card---sidebar-layout)
- [Entity Cards](#entity-cards)
- [Custom Cards](#custom-cards)
- [Automations Using Sensors](#automations-using-sensors)

---

## Markdown Card - Sidebar Layout

A comprehensive card displaying all your account information in a compact, organized table. Perfect for sidebar placement.

### Features

- ✅ Currency formatting for dollar amounts
- ✅ Date formatting
- ✅ Grouped sensor display by category
- ✅ Countdown displays for upcoming dates
- ✅ **Programmatic calculation** of "Days Until Next Bill" from Next Bill Date sensor
- ✅ Responsive design
- ✅ Scrollable for long lists

### Static Preview

This is a visual representation of how the card appears in Lovelace:

<div style="border: 1px solid #d0d7de; border-radius: 8px; background: #0d1117; color: #e6edf3; font-family: 'Segoe UI', sans-serif; font-size: 13px; padding: 12px;">
<div style="text-align: center; margin-bottom: 10px; font-weight: 600;">My Address • ICP123</div>
<table style="width: 100%; border-collapse: collapse;">
<tbody>
<tr><td colspan="2" style="padding: 6px 4px; font-weight: 600; background: rgba(255,255,255,0.05);">Account Balance</td></tr>
<tr><td style="padding: 4px 4px;">Current Balance</td><td style="padding: 4px 4px; text-align: right;">$-45.27</td></tr>
<tr><td style="padding: 4px 4px;">Prepay Debt Balance</td><td style="padding: 4px 4px; text-align: right;">$0.00</td></tr>
<tr><td style="padding: 4px 4px;">Refund Eligible</td><td style="padding: 4px 4px; text-align: right;">Yes</td></tr>
<tr><td style="padding: 4px 4px;">Maximum Refund</td><td style="padding: 4px 4px; text-align: right;">$10.00</td></tr>
<tr><td colspan="2" style="padding: 6px 4px; font-weight: 600; background: rgba(255,255,255,0.05);">Billing Information</td></tr>
<tr><td style="padding: 4px 4px;">Amount Due</td><td style="padding: 4px 4px; text-align: right;">$123.45</td></tr>
<tr><td style="padding: 4px 4px;">Amount Paid</td><td style="padding: 4px 4px; text-align: right;">$80.00</td></tr>
<tr><td style="padding: 4px 4px;">Discount Total</td><td style="padding: 4px 4px; text-align: right;">$5.00</td></tr>
<tr><td style="padding: 4px 4px;">Payment Due Date</td><td style="padding: 4px 4px; text-align: right;">2025-01-05</td></tr>
<tr><td style="padding: 4px 4px;">Days Until Overdue</td><td style="padding: 4px 4px; text-align: right;">6 days</td></tr>
<tr><td colspan="2" style="padding: 6px 4px; font-weight: 600; background: rgba(255,255,255,0.05);">Next Bill</td></tr>
<tr><td style="padding: 4px 4px;">Next Bill Date</td><td style="padding: 4px 4px; text-align: right;">2025-02-01</td></tr>
<tr><td style="padding: 4px 4px;">Days Until Next Bill</td><td style="padding: 4px 4px; text-align: right;">33 days</td></tr>
<tr><td colspan="2" style="padding: 4px 4px;"><em style="font-size: 11px; opacity: 0.7;">* Calculated from Next Bill Date</em></td></tr>
<tr><td colspan="2" style="padding: 6px 4px; font-weight: 600; background: rgba(255,255,255,0.05);"><em>(Additional sections: Account Settings, Contract Details, Payment Plans below in full card)</em></td></tr>
</tbody>
</table>
</div>

> **Note:** The card is fully scrollable in Lovelace when configured with the `card_mod` styling. This preview shows the first few sections.

### YAML Configuration

```yaml
type: markdown
content: >+

  {# CONFIGURATION: Set your entity base name here (change this to match your sensors) #}
  {% set address_icp = 'my_address_icp123' %}


  {# Define all entity names that should be formatted as currency ($X.XX) #}
  {% set currency_names = [
    'Current Balance',
    'Prepay Debt Balance',
    'Maximum Refund',
    'Amount Due',
    'Amount Paid',
    'Discount Total'
  ] %}


  {# Define all entity names that should be formatted as a human-readable date #}
  {% set date_names = [
    'Payment Due Date',
    'Next Bill Date'
  ] %}


  {# Define groups and their entities - Uses address_icp variable #}
  {% set groups = [
    ('Account Balance', [
      ('Current Balance', 'sensor.' + address_icp + '_current_balance'),
      ('Prepay Debt Balance', 'sensor.' + address_icp + '_prepay_debt_balance'),
      ('Refund Eligible', 'sensor.' + address_icp + '_refund_eligible'),
      ('Maximum Refund', 'sensor.' + address_icp + '_maximum_refund')
    ]),
    ('Billing Information', [
      ('Amount Due', 'sensor.' + address_icp + '_amount_due'),
      ('Amount Paid', 'sensor.' + address_icp + '_amount_paid'),
      ('Discount Total', 'sensor.' + address_icp + '_discount_total'),
      ('Payment Due Date', 'sensor.' + address_icp + '_payment_due_date'),
      ('Days Until Overdue', 'sensor.' + address_icp + '_days_until_overdue')
    ]),
    ('Next Bill', [
      ('Next Bill Date', 'sensor.' + address_icp + '_next_bill_date'),
      ('Days Until Next Bill', '__CALCULATED__')
    ]),
    ('Account Settings', [
      ('Correspondence Preference', 'sensor.' + address_icp + '_correspondence_preference'),
      ('Payment Method', 'sensor.' + address_icp + '_payment_method'),
      ('Billing Frequency', 'sensor.' + address_icp + '_billing_frequency')
    ]),
    ('Contract Details', [
      ('Account Nickname', 'sensor.' + address_icp + '_account_nickname'),
      ('ICP', 'sensor.' + address_icp + '_icp'),
      ('Address', 'sensor.' + address_icp + '_address'),
      ('Product Name', 'sensor.' + address_icp + '_product_name'),
      ('Contract Type', 'sensor.' + address_icp + '_contract_type'),
      ('Contract Status', 'sensor.' + address_icp + '_contract_status')
    ]),
    ('Payment Plans', [
      ('Direct Debit', 'sensor.' + address_icp + '_is_direct_debit'),
      ('Smooth Pay', 'sensor.' + address_icp + '_is_smooth_pay'),
      ('Prepay', 'sensor.' + address_icp + '_is_prepay')
    ])
  ] %}

  {% set content_html = namespace(rows="") %}


  {# Iterate over groups and their entities #}
  {% for group_name, entities in groups %}
    
    {# Add an empty row for separation, but skip it for the very first group #}
    {% if not loop.first %}
      {% set content_html.rows = content_html.rows + '<tr><td colspan="2" style="padding: 0px 8px;"><br></td></tr>' %}
    {% endif %}

    {# Insert a full-width header row for the group name #}
    {% set header_style = 'text-align: left; padding: 6px 8px; font-weight: bold; background-color: rgba(120, 120, 120, 0.1);' %}
    {% set content_html.rows = content_html.rows + '<tr><td colspan="2" style="' + header_style + '"><strong>' + group_name + '</strong></td></tr>' %}
    
    {# Iterate over the entities within the current group #}
    {% for name, entity_id in entities %}
      {# Special handling for calculated Days Until Next Bill #}
      {% if entity_id == '__CALCULATED__' and name == 'Days Until Next Bill' %}
        {% set next_bill_date_entity = 'sensor.' + address_icp + '_next_bill_date' %}
        {% set next_bill_date_str = states(next_bill_date_entity) %}
        {% if next_bill_date_str not in ['unknown', 'unavailable', 'none'] and next_bill_date_str %}
          {# Parse the date and calculate using as_timestamp filter #}
          {% set next_bill_datetime = strptime(next_bill_date_str, '%d %b %Y') %}
          {% set bill_ts = as_timestamp(next_bill_datetime) | float %}
          {% set now_ts = as_timestamp(now()) | float %}
          {% set days_until = ((bill_ts - now_ts) / 86400) | round(0, 'floor') | int %}
          {% if days_until < 0 %}
            {% set value = (days_until | abs | string) + ' days overdue' %}
          {% elif days_until == 0 %}
            {% set value = 'Today' %}
          {% else %}
            {% set value = days_until | string + ' days' %}
          {% endif %}
        {% else %}
          {% set value = '—' %}
        {% endif %}
      {% else %}
        {% set value = states(entity_id) %}
      {% endif %}
      
      {% set formatted_value = value %}

      {# Special Formatting Logic #}
      {% if value not in ['unknown', 'unavailable', 'none'] and value is not none %}
        {# Handle Currency Formatting ($X.XX) #}
        {% if name in currency_names %}
          {% set formatted_value = ('$%.2f' | format(value | float(0))) %}
        
        {# Handle Date Formatting #}
        {% elif name in date_names %}
          {% set formatted_value = value %}
        
        {# Handle Boolean values for Refund Eligible #}
        {% elif name == 'Refund Eligible' %}
          {% set formatted_value = 'Yes' if value | lower == 'true' or value == True else 'No' %}
        
        {# Handle Days Until values #}
        {% elif 'Days Until' in name %}
          {% set num = value | int(0) %}
          {% if num < 0 %}
            {% set formatted_value = (num | abs | string) + ' days overdue' %}
          {% else %}
            {% set formatted_value = num | string + ' days' %}
          {% endif %}
        {% endif %}
      {% else %}
        {% set formatted_value = '—' %}
      {% endif %}
      
      {# Build table rows #}
      {% set content_html.rows = content_html.rows + '<tr><td style="text-align: left; padding: 4px 8px;"><small>&nbsp;&nbsp;&nbsp;' + name + '</small></td><td align="right" style="padding: 4px 8px;"><small>' + formatted_value + '</small></td></tr>' %}
    {% endfor %}
  {% endfor %}


  <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
    <colgroup>
      <col style="width: 60%;">
      <col style="width: 40%;">
    </colgroup>
    <tr>
      <th colspan="2" align="center"><h3>My Address<br>ICP123</h3></th>
    </tr>
    <tbody>
      {{ content_html.rows }}
    </tbody>
  </table>

text_only: true
view_layout:
  position: sidebar
card_mod:
  style:
    .: |
      ha-card {
        height: 500px !important;
        overflow-y: auto !important;
      }
```

</div>

### Customization

1. **Set your address_icp variable**: Change the `address_icp` value at the top (line 4) from `'my_address_icp123'` to match your actual sensor base name
   - Example: `{% set address_icp = '71_oroua_st_0000000966tr348' %}`
   - This single change updates all sensor references throughout the card
2. **Update header**: Change `My Address<br>ICP123` to your property address and ICP
3. **Adjust height**: Modify `height: 500px` to fit your sidebar
4. **Add/Remove groups**: Modify the `groups` list to show only sensors you want

**Note:** This card requires the [card-mod](https://github.com/thomasloven/lovelace-card-mod) custom component for styling.

---

## Entity Cards

### Simple Balance Card

Display just your current balance:

<table>
  <tr>
    <td style="vertical-align: top; padding-right: 12px;">
      <strong>Preview</strong><br>
      <img src="https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/assets/simple_account_balance_card.png" alt="Simple Balance Card" style="max-width: 220px; height: auto;">
    </td>
    <td style="vertical-align: top;">
      <strong>YAML</strong>
      <pre><code>type: entity
entity: sensor.my_address_icp123_current_balance
name: Account Balance
icon: mdi:currency-usd</code></pre>
    </td>
  </tr>
</table>

### Payment Due Card

Show upcoming payment information:

<table>
  <tr>
    <td style="vertical-align: top; padding-right: 12px;">
      <strong>Preview</strong><br>
      <img src="https://raw.githubusercontent.com/iamawumpas/Contact-Energy/main/assets/payment_due_card.png" alt="Payment Due Card" style="max-width: 220px; height: auto;">
    </td>
    <td style="vertical-align: top;">
      <strong>YAML</strong>
      <pre><code>type: entities
title: Payment Due
entities:
  - entity: sensor.my_address_icp123_amount_due
    name: Amount Due
  - entity: sensor.my_address_icp123_payment_due_date
    name: Due Date
  - entity: sensor.my_address_icp123_days_until_overdue
    name: Days Remaining
    icon: mdi:calendar-clock</code></pre>
    </td>
  </tr>
</table>

### Contract Information Card

Display your contract details:

```yaml
type: entities
title: Contract Details
entities:
  - entity: sensor.my_address_icp123_address
    name: Address
  - entity: sensor.my_address_icp123_icp
    name: ICP Number
  - entity: sensor.my_address_icp123_product_name
    name: Plan
  - entity: sensor.my_address_icp123_contract_status
    name: Status
```

---

## Custom Cards

### Gauge Card - Days Until Payment

Visual countdown to payment due date:

```yaml
type: gauge
entity: sensor.my_address_icp123_days_until_overdue
name: Days Until Payment Due
min: 0
max: 30
severity:
  green: 10
  yellow: 5
  red: 0
needle: true
```

### Conditional Card - Overdue Warning

Show a warning only when payment is overdue:

```yaml
type: conditional
conditions:
  - entity: sensor.my_address_icp123_days_until_overdue
    state_not: unavailable
  - entity: sensor.my_address_icp123_days_until_overdue
    state_not: unknown
  - condition: numeric_state
    entity: sensor.my_address_icp123_days_until_overdue
    below: 0
card:
  type: markdown
  content: |
    ## ⚠️ Payment Overdue!
    Your payment is **{{ states('sensor.my_address_icp123_days_until_overdue') | int | abs }} days** overdue.
    
    Amount due: **${{ states('sensor.my_address_icp123_amount_due') }}**
```

### Statistics Card - Balance History

Track balance changes over time:

```yaml
type: statistics-graph
entities:
  - sensor.my_address_icp123_current_balance
stat_types:
  - mean
  - min
  - max
period:
  calendar:
    period: month
```

---

## ApexCharts Examples

⚠️ **Usage sensors not yet implemented** - These examples are placeholders for future functionality.

### Daily Usage Chart

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Daily Energy Usage
graph_span: 7d
series:
  - entity: sensor.my_address_icp123_daily_usage
    name: Usage
    type: column
    group_by:
      func: max
      duration: 1d
yaxis:
  - decimals: 2
    apex_config:
      title:
        text: kWh
```

### Cost vs Usage Chart

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Energy Cost & Usage
graph_span: 30d
series:
  - entity: sensor.my_address_icp123_daily_usage
    name: Usage (kWh)
    type: column
    group_by:
      func: sum
      duration: 1d
  - entity: sensor.my_address_icp123_daily_cost
    name: Cost (NZD)
    type: line
    group_by:
      func: sum
      duration: 1d
    yaxis_id: cost
yaxis:
  - id: usage
    apex_config:
      title:
        text: kWh
  - id: cost
    opposite: true
    apex_config:
      title:
        text: NZD
```

---

## Automations Using Sensors

### Payment Reminder

Get notified 3 days before payment is due:

```yaml
automation:
  - alias: "Contact Energy - Payment Reminder"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_address_icp123_days_until_overdue
        below: 4
        above: 2
    action:
      - service: notify.mobile_app
        data:
          title: "Payment Due Soon"
          message: >
            Your Contact Energy payment of ${{ states('sensor.my_address_icp123_amount_due') }}
            is due in {{ states('sensor.my_address_icp123_days_until_overdue') }} days.
```

### Overdue Payment Alert

Get an urgent notification when payment is overdue:

```yaml
automation:
  - alias: "Contact Energy - Overdue Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_address_icp123_days_until_overdue
        below: 0
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Payment Overdue!"
          message: >
            Your Contact Energy payment is {{ states('sensor.my_address_icp123_days_until_overdue') | int | abs }} days overdue!
            Amount: ${{ states('sensor.my_address_icp123_amount_due') }}
          data:
            priority: high
```

### Credit Balance Notification

Get notified when you have a credit balance above a threshold:

```yaml
automation:
  - alias: "Contact Energy - Credit Available"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_address_icp123_current_balance
        above: 50
    condition:
      - condition: state
        entity_id: sensor.my_address_icp123_refund_eligible
        state: "True"
    action:
      - service: notify.mobile_app
        data:
          title: "Refund Available"
          message: >
            You have ${{ states('sensor.my_address_icp123_maximum_refund') }} available for refund!
```

### Next Bill Reminder

Get notified 5 days before next bill:

```yaml
automation:
  - alias: "Contact Energy - Next Bill Soon"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_address_icp123_days_until_next_bill
        below: 6
        above: 4
    action:
      - service: notify.mobile_app
        data:
          title: "Next Bill Coming"
          message: >
            Your next Contact Energy bill will be issued in
            {{ states('sensor.my_address_icp123_days_until_next_bill') }} days
            on {{ states('sensor.my_address_icp123_next_bill_date') }}.
```

---

## Tips & Best Practices

### Naming Conventions

When creating template sensors or referencing entities:
- Use consistent, descriptive names
- Include the property identifier if you have multiple accounts
- Follow Home Assistant naming guidelines

### Dashboard Organization

- Group related sensors together (balance, billing, contract)
- Use conditional cards to show warnings only when needed
- Consider using tabs for multiple properties
- Place frequently-viewed cards at the top

### Performance

- Markdown cards with many sensors may take a moment to render
- Consider splitting very large dashboards into multiple views
- Use conditional cards to reduce entity updates

### Mobile Optimization

- Test dashboard on mobile devices
- Use `view_layout: position: sidebar` for compact displays
- Consider separate mobile-optimized views

---

**Next:** [Configure Multiple Accounts →](Multiple-Accounts)
