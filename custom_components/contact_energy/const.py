"""Constants for the Contact Energy integration."""

DOMAIN = "contact_energy"
NAME = "Contact Energy"
VERSION = "0.0.1"
DEFAULT_SCAN_INTERVAL = 28800  # 8 hours in seconds

# Configuration
CONF_ACCOUNT_ID = "account_id"
CONF_CONTRACT_ID = "contract_id"
CONF_CONTRACT_ICP = "contract_icp"
CONF_USAGE_DAYS = "usage_days"

# API Configuration
API_BASE_URL = "https://api.contact-digital-prod.net"
API_KEY = "z840P4lQCH9TqcjC9L2pP157DZcZJMcr5tVQCvyx"

# Account sensor names
SENSOR_ACCOUNT_BALANCE_NAME = "Account Balance"
SENSOR_NEXT_BILL_AMOUNT_NAME = "Next Bill Amount" 
SENSOR_NEXT_BILL_DATE_NAME = "Next Bill Date"
SENSOR_PAYMENT_DUE_NAME = "Payment Due"
SENSOR_PAYMENT_DUE_DATE_NAME = "Payment Due Date"
SENSOR_PREVIOUS_READING_DATE_NAME = "Previous Reading Date"
SENSOR_NEXT_READING_DATE_NAME = "Next Reading Date"

# Usage sensor names (for statistics)
SENSOR_ENERGY_CONSUMPTION_NAME = "Energy Consumption"
SENSOR_ENERGY_COST_NAME = "Energy Cost" 
SENSOR_FREE_ENERGY_CONSUMPTION_NAME = "Free Energy Consumption"

# Storage keys for tracking downloaded data
STORAGE_KEY_LAST_DOWNLOAD = "last_download_date"
STORAGE_VERSION = 1