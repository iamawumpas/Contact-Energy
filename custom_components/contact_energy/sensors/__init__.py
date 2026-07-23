"""Sensor entities for Contact Energy integration.

=== WHAT THIS DOES ===
This is a "package __init__.py file" that organizes all the sensor classes for
the Contact Energy integration. It imports sensors from multiple files and makes
them easily accessible to other parts of the code.

This file acts as a central catalog that lists all available sensor types:
- Account sensors (balance, invoices, billing dates)
- Usage sensors (hourly, daily, monthly consumption)
- Energy sensors (Home Assistant Energy Dashboard integration)

=== FOR NON-CODERS ===
Think of this as a library catalog:
- The library (sensors/) has different sections (account_sensors.py, usage_sensors.py, energy_sensors.py)
- Each section has different books (sensor classes)
- This catalog lists all available books in one place
- Instead of searching through each section, you check the catalog first

This package provides sensor entities for account data, usage data, and
energy dashboard integration using the v2.0.0 architecture.

A "sensor entity" in Home Assistant is like a digital meter that displays
information. For example:
- A temperature sensor shows the current temperature
- A balance sensor shows your account balance
- A usage sensor shows your electricity consumption

Version: 2.0.0
"""

# ============================================================================
# IMPORTS - Organize sensors by category
# ============================================================================

# ----------------------------------------------------------------------------
# ACCOUNT SENSORS - Display account information
# ----------------------------------------------------------------------------
# These sensors show account-related information like balance, bills, and dates
from .account_sensors import (
    AccountBalanceSensor,      # Shows current account balance
    InvoiceSensor,             # Shows invoice details and payment info
    NextBillSensor,            # Shows next billing date information
    AccountDetailSensor,       # Shows general account details
)

# ----------------------------------------------------------------------------
# USAGE SENSORS - Display electricity consumption
# ----------------------------------------------------------------------------
# These sensors show how much electricity has been used over different time periods
from .usage_sensors import (
    UsageDataSensor,           # Base sensor for usage data
    HourlyUsageSensor,         # Shows electricity used each hour
    DailyUsageSensor,          # Shows electricity used each day
    MonthlyUsageSensor,        # Shows electricity used each month
)

# ----------------------------------------------------------------------------
# ENERGY SENSORS - Home Assistant Energy Dashboard integration
# ----------------------------------------------------------------------------
# These sensors format usage data specifically for Home Assistant's Energy Dashboard
from .energy_sensors import (
    EnergySensor,              # Base energy sensor
    DailyEnergySensor,         # Daily energy for dashboard
    MonthlyEnergySensor,       # Monthly energy for dashboard
)

# ============================================================================
# PUBLIC API - Define what's available when importing from this package
# ============================================================================

# __all__ is a special Python list that defines the "public API" of this package
# When someone writes "from .sensors import *", Python only imports these items
#
# Why we organize it this way:
# - Makes it clear which sensors are available
# - Groups related sensors together (account, usage, energy)
# - Provides better documentation
# - Helps IDEs provide better auto-completion
__all__ = [
    # ========================================================================
    # Account sensors - Show account balance, billing, and payment information
    # ========================================================================
    "AccountBalanceSensor",
    "InvoiceSensor",
    "NextBillSensor",
    "AccountDetailSensor",
    
    # ========================================================================
    # Usage sensors - Show electricity consumption over time
    # ========================================================================
    "UsageDataSensor",
    "HourlyUsageSensor",
    "DailyUsageSensor",
    "MonthlyUsageSensor",
    
    # ========================================================================
    # Energy sensors - Integrate with Home Assistant Energy Dashboard
    # ========================================================================
    "EnergySensor",
    "DailyEnergySensor",
    "MonthlyEnergySensor",
]
