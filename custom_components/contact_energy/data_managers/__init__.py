"""Data managers for Contact Energy integration.

=== WHAT THIS DOES ===
This is a "package __init__.py file" that organizes all the data manager classes
for the Contact Energy integration. Data managers are responsible for:
- Saving data to disk (caching)
- Loading data from disk
- Checking if saved data is still fresh or too old
- Managing different types of data (account info, hourly usage, daily usage, etc.)

This file acts as a central directory that makes all data managers easy to access.

=== FOR NON-CODERS ===
Think of this as a filing system in an office:
- The office (data_managers/) has different filing cabinets
- Each cabinet (manager) handles one type of document:
  * base_cache.py = The system that all cabinets use (shared rules)
  * account_data.py = Cabinet for account information
  * usage_hourly.py = Cabinet for hourly electricity readings
  * usage_daily.py = Cabinet for daily electricity readings
  * usage_monthly.py = Cabinet for monthly electricity readings
- This directory lists where each cabinet is located

This package provides data management and caching for Contact Energy data.
Each manager handles a specific data type with independent caching.

Why do we need data managers?
- They save API data locally so we don't need to download it repeatedly
- They track when saved data becomes too old and needs refreshing
- They prevent race conditions (two processes trying to save at once)
- They organize data in a structured, consistent way

Version: 2.0.0
"""

# ============================================================================
# IMPORTS - Make data manager classes available from this package
# ============================================================================

# ----------------------------------------------------------------------------
# BASE CACHE - The foundation that all other managers build upon
# ----------------------------------------------------------------------------
# BaseCache defines the common behavior that all data managers share:
# - Where to store files
# - How to load/save JSON data
# - How to track timestamps
# - How to check if data is stale
from .base_cache import BaseCache

# ----------------------------------------------------------------------------
# ACCOUNT DATA MANAGER - Handles account information caching
# ----------------------------------------------------------------------------
# Manages cached account data like balance, invoices, contracts, and billing dates
from .account_data import AccountDataManager

# ----------------------------------------------------------------------------
# USAGE DATA MANAGERS - Handle electricity consumption data at different intervals
# ----------------------------------------------------------------------------
# Each manager handles a different time granularity (hour, day, month)

# UsageHourlyDataManager: Saves/loads hourly electricity readings
# Example: "At 2pm on July 23, you used 1.5 kWh"
from .usage_hourly import UsageHourlyDataManager

# UsageDailyDataManager: Saves/loads daily electricity readings
# Example: "On July 23, you used 24.3 kWh total"
from .usage_daily import UsageDailyDataManager

# UsageMonthlyDataManager: Saves/loads monthly electricity readings
# Example: "In July, you used 732.5 kWh total"
from .usage_monthly import UsageMonthlyDataManager

# ============================================================================
# PUBLIC API - Define what's available when importing from this package
# ============================================================================

# __all__ is a special Python list that defines the "public API" of this package
# When other code imports from this package, these are the classes they can use
#
# Why this matters:
# - Makes it clear which classes are meant to be used externally
# - Provides better documentation
# - Helps development tools provide better auto-completion
# - Prevents accidental use of internal/private classes
__all__ = [
    # Base class that all managers inherit from
    "BaseCache",
    
    # Manager for account information (balance, billing, contracts)
    "AccountDataManager",
    
    # Managers for usage data at different time granularities
    "UsageHourlyDataManager",     # Hour-by-hour readings
    "UsageDailyDataManager",      # Day-by-day readings
    "UsageMonthlyDataManager",    # Month-by-month readings
]
