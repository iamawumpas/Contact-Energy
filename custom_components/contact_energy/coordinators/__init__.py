"""Coordinators for Contact Energy integration.

=== WHAT THIS DOES ===
This is a "package __init__.py file" that organizes the coordinator classes
for the Contact Energy integration. Coordinators are responsible for:
- Fetching data from the API or cache on a schedule
- Sharing that data with multiple sensors (avoiding duplicate requests)
- Telling sensors when new data is available
- Managing update timing and intervals

This file acts as a central access point for all coordinators.

=== FOR NON-CODERS ===
Think of coordinators like news broadcasters:
- Instead of everyone calling the weather station separately,
  one broadcaster calls and gets the forecast
- The broadcaster then announces it to everyone at once
- Everyone hears the same information at the same time
- This is more efficient than thousands of individual phone calls

This package provides coordinators for managing data updates from the
Contact Energy API. Each coordinator is responsible for a specific data type:
- AccountCoordinator: Manages account data (balance, billing, contracts)
- UsageCoordinatorV2: Manages usage data (hourly, daily, monthly consumption)

Why use coordinators?
- Efficiency: One API request serves many sensors
- Consistency: All sensors see the same data snapshot
- Reliability: Centralized error handling and retry logic
- Performance: Reduces load on Contact Energy's servers

Version: 2.0.0
"""

# ============================================================================
# IMPORTS - Make coordinator classes available from this package
# ============================================================================

# ----------------------------------------------------------------------------
# ACCOUNT COORDINATOR - Manages account data updates
# ----------------------------------------------------------------------------
# AccountCoordinator handles fetching and distributing account information
# (balance, invoices, billing dates, contracts) to all account-related sensors.
#
# Update frequency: Every 6 hours
# Data cached: Yes (account_data.json)
from .account_coordinator import AccountCoordinator

# ----------------------------------------------------------------------------
# USAGE COORDINATOR V2 - Manages usage data updates
# ----------------------------------------------------------------------------
# UsageCoordinatorV2 handles fetching and distributing electricity consumption
# data at multiple time granularities (hourly, daily, monthly) to usage sensors.
#
# Update frequency: Varies by data type (1-6 hours)
# Data cached: Yes (separate files for hourly, daily, monthly)
from .usage_coordinator_v2 import UsageCoordinatorV2

# ============================================================================
# PUBLIC API - Define what's available when importing from this package
# ============================================================================

# __all__ is a special Python list that defines the "public API" of this package
# When other code imports from this package, these are the classes they can access
#
# Why this list exists:
# - Makes it clear which coordinators are available
# - Documents the public interface
# - Helps development tools provide auto-completion
# - Prevents accidental use of internal/private classes
#
# Note: The main coordinator (coordinator.py) and legacy usage coordinator
# (usage_coordinator.py) are not exported here because they're accessed
# differently (imported directly where needed rather than through this package).
__all__ = [
    # Coordinator for account data (balance, billing, contracts)
    "AccountCoordinator",
    
    # Coordinator for usage data (hourly, daily, monthly consumption)
    "UsageCoordinatorV2",
]
