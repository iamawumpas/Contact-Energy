# ApexCharts Card Examples for Contact Energy

## Available Chart Sensors (v0.3.11+)

The integration now provides the following chart sensors that expose data in their attributes for easy use with ApexCharts:

### Hourly Sensors
- `sensor.contact_energy_chart_hourly_{icp}` - Last 7 days of hourly paid usage
- `sensor.contact_energy_chart_hourly_free_{icp}` - Last 7 days of hourly free usage

### Daily Sensors
- `sensor.contact_energy_chart_daily_{icp}` - Last 30 days of daily paid usage
- `sensor.contact_energy_chart_daily_free_{icp}` - Last 30 days of daily free usage

### Monthly Sensors
- `sensor.contact_energy_chart_monthly_{icp}` - Last 12 months of monthly paid usage
- `sensor.contact_energy_chart_monthly_free_{icp}` - Last 12 months of monthly free usage

## Example 1: Stacked Bar Chart - Daily Usage (Paid + Free)

This shows daily usage with free usage at the bottom (green) and paid usage stacked on top (blue):

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Daily Energy Usage
  show_states: true
  colorize_states: true
graph_span: 30d
stacked: true
apex_config:
  chart:
    type: bar
  plotOptions:
    bar:
      columnWidth: 90%
  dataLabels:
    enabled: false
  legend:
    show: true
    position: top
  yaxis:
    labels:
      formatter: |
        EVAL:function(value) {
          return value.toFixed(1) + ' kWh';
        }
series:
  # Free usage (bottom of stack - green)
  - entity: sensor.contact_energy_chart_daily_free_0000000966tr348
    name: Free Usage
    type: column
    color: '#4caf50'
    show:
      in_header: true
    data_generator: |
      const data = entity.attributes.daily_free_data || {};
      const result = [];
      let prevSum = 0;
      for (const [dateStr, cumSum] of Object.entries(data).sort()) {
        const dailyValue = cumSum - prevSum;
        result.push([new Date(dateStr).getTime(), dailyValue]);
        prevSum = cumSum;
      }
      return result;
    
  # Paid usage (top of stack - blue)
  - entity: sensor.contact_energy_chart_daily_0000000966tr348
    name: Paid Usage
    type: column
    color: '#2196f3'
    show:
      in_header: true
    data_generator: |
      const data = entity.attributes.daily_data || {};
      const result = [];
      let prevSum = 0;
      for (const [dateStr, cumSum] of Object.entries(data).sort()) {
        const dailyValue = cumSum - prevSum;
        result.push([new Date(dateStr).getTime(), dailyValue]);
        prevSum = cumSum;
      }
      return result;
```

## Example 2: Hourly Usage Chart

This shows hourly usage for the last 7 days:

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Hourly Energy Usage (Last 7 Days)
graph_span: 7d
apex_config:
  chart:
    type: area
  stroke:
    curve: smooth
  dataLabels:
    enabled: false
  yaxis:
    labels:
      formatter: |
        EVAL:function(value) {
          return value.toFixed(2) + ' kWh';
        }
series:
  - entity: sensor.contact_energy_chart_hourly_0000000966tr348
    name: Hourly Usage
    type: area
    color: '#2196f3'
    data_generator: |
      const data = entity.attributes.hourly_data || {};
      const result = [];
      let prevSum = 0;
      for (const [dateStr, cumSum] of Object.entries(data).sort()) {
        const hourlyValue = cumSum - prevSum;
        result.push([new Date(dateStr).getTime(), hourlyValue]);
        prevSum = cumSum;
      }
      return result;
```

## Example 3: Monthly Usage Comparison (Paid vs Free)

This shows monthly totals as grouped bars:

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Monthly Energy Usage
graph_span: 12month
apex_config:
  chart:
    type: bar
  plotOptions:
    bar:
      columnWidth: 70%
      dataLabels:
        position: top
  dataLabels:
    enabled: true
    formatter: |
      EVAL:function(value) {
        return value.toFixed(0);
      }
    offsetY: -20
    style:
      fontSize: 12px
  legend:
    show: true
    position: top
  yaxis:
    labels:
      formatter: |
        EVAL:function(value) {
          return value.toFixed(0) + ' kWh';
        }
series:
  - entity: sensor.contact_energy_chart_monthly_0000000966tr348
    name: Paid Usage
    type: column
    color: '#2196f3'
    data_generator: |
      const data = entity.attributes.monthly_data || {};
      const result = [];
      let prevSum = 0;
      for (const [monthStr, cumSum] of Object.entries(data).sort()) {
        const monthlyValue = cumSum - prevSum;
        // Parse YYYY-MM and create date at start of month
        const [year, month] = monthStr.split('-');
        const date = new Date(year, month - 1, 1);
        result.push([date.getTime(), monthlyValue]);
        prevSum = cumSum;
      }
      return result;
      
  - entity: sensor.contact_energy_chart_monthly_free_0000000966tr348
    name: Free Usage
    type: column
    color: '#4caf50'
    data_generator: |
      const data = entity.attributes.monthly_free_data || {};
      const result = [];
      let prevSum = 0;
      for (const [monthStr, cumSum] of Object.entries(data).sort()) {
        const monthlyValue = cumSum - prevSum;
        // Parse YYYY-MM and create date at start of month
        const [year, month] = monthStr.split('-');
        const date = new Date(year, month - 1, 1);
        result.push([date.getTime(), monthlyValue]);
        prevSum = cumSum;
      }
      return result;
```

## Important Notes

### Replace ICP Number
In all examples above, replace `0000000966tr348` with your actual ICP number (in lowercase with special characters replaced by underscores).

### Data Structure
All chart sensors store **cumulative** statistics in their attributes. The `data_generator` code calculates the difference between consecutive entries to get the actual usage for each period.

### Attribute Names
- Hourly: `hourly_data` (paid), `hourly_free_data` (free)
- Daily: `daily_data` (paid), `daily_free_data` (free)
- Monthly: `monthly_data` (paid), `monthly_free_data` (free)

### Time Ranges
- Hourly charts: Last 7 days
- Daily charts: Last 30 days
- Monthly charts: Last 12 months

These limits prevent the sensor attributes from exceeding Home Assistant's 16KB database limit.

### Customization
- Change colors by modifying the `color` property
- Adjust chart types: `bar`, `column`, `area`, `line`
- Modify time ranges with `graph_span`
- Enable/disable data labels with `dataLabels.enabled`
