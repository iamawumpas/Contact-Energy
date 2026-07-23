"""Constants for the Contact Energy integration.

=== WHAT THIS FILE DOES ===
This module defines shared constants (fixed values that don't change) used 
throughout the integration. Think of constants as the "configuration settings" 
that are used everywhere in the code.

By keeping all constants in one place, we make the code easier to maintain - 
if we need to change a value, we only need to change it here rather than 
searching through many files.

=== FOR NON-CODERS ===
A "constant" is a value that doesn't change while the program runs. It's like
giving a name to a specific value so we can use that name throughout our code.
For example, instead of writing "contact_energy" hundreds of times, we write
it once here as DOMAIN, and then use DOMAIN everywhere else.
"""

# ============================================================================
# INTEGRATION IDENTIFIER
# ============================================================================
# The unique identifier (or "domain") for this integration within Home Assistant.
# 
# What is a domain?
# - Home Assistant uses "domains" to identify different integrations
# - Think of it like a unique ID card for our integration
# - This string "contact_energy" is used everywhere to:
#   * Store data specific to Contact Energy
#   * Register services (like "refresh_data")
#   * Create config entries
#   * Identify sensors and entities
#
# Why "contact_energy"?
# - It follows Home Assistant's naming convention (lowercase, underscores)
# - It's descriptive and tells you exactly what this integration does
# - It must be unique across all Home Assistant integrations
DOMAIN = "contact_energy"
