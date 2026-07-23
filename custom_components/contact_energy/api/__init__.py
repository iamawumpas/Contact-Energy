"""API layer for Contact Energy integration.

=== WHAT THIS DOES ===
This is a "package __init__.py file" that tells Python this folder (api/) is
a package containing related modules. It also defines which classes from this
package should be easily accessible to other parts of the integration.

This file makes the API classes available without having to know which specific
file they're in. Instead of:
    from .api.client import ContactEnergyApiClient
You can simply write:
    from .api import ContactEnergyApiClient

=== FOR NON-CODERS ===
Think of this as the front desk directory of an office building:
- The building (api/) has multiple departments (client.py, account.py, usage.py)
- This directory lists which departments are available
- It makes it easy to find and access those departments

This package provides isolated API communication components for the Contact Energy
integration. All API interactions are handled through these modules:
- client.py: Base API client (authentication, rate limiting, error handling)
- account.py: Account-specific API requests (balance, billing, contracts)
- usage.py: Usage-specific API requests (hourly, daily, monthly consumption)

Version: 2.0.0
"""

# ============================================================================
# IMPORTS - Make API classes available from this package
# ============================================================================

# Import the base API client that handles authentication and core requests
from .client import ContactEnergyApiClient

# Import the account-specific API client that fetches account information
from .account import ContactEnergyAccountApi

# Import the usage-specific API client that fetches consumption data
from .usage import ContactEnergyUsageApi

# ============================================================================
# PUBLIC API - Define what's available when importing from this package
# ============================================================================

# __all__ is a special Python variable that lists the "public" classes/functions
# This means: "When someone imports from this package, these are what they get"
#
# Why this matters:
# - Makes the API clear and explicit
# - Prevents accidental imports of internal/private code
# - Tools like IDEs use this to provide better auto-completion
__all__ = [
    "ContactEnergyApiClient",
    "ContactEnergyAccountApi",
    "ContactEnergyUsageApi",
]
