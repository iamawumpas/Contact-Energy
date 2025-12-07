"""Constants for the Contact Energy integration."""
from datetime import timedelta
from typing import Final

# Integration domain
DOMAIN: Final = "contact_energy"

# API Configuration
API_BASE_URL: Final = "https://api.contact-digital-prod.net"
API_KEY: Final = "kbIthASA7e1M3NmpMdGrn2Yqe0yHcCjL4QNPSUij"
API_TIMEOUT: Final = 30

# API Endpoints
ENDPOINT_LOGIN: Final = "/login/v2"
ENDPOINT_ACCOUNTS: Final = "/accounts/v2"
ENDPOINT_USAGE: Final = "/usage/v2/{contract_id}"

# Configuration Keys
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_ACCOUNT_ID: Final = "account_id"
CONF_CONTRACT_ID: Final = "contract_id"
CONF_ICP_NUMBER: Final = "icp_number"
CONF_ACCOUNT_NICKNAME: Final = "account_nickname"
CONF_ACCOUNT_ADDRESS: Final = "account_address"
CONF_HISTORY_DAYS: Final = "history_days"
CONF_HISTORY_MONTHS: Final = "history_months"

# Default Values
DEFAULT_HISTORY_MONTHS: Final = 3
DEFAULT_HISTORY_DAYS: Final = 90
MIN_HISTORY_MONTHS: Final = 1
MAX_HISTORY_MONTHS: Final = 24

# Update Intervals (recommended from API research)
UPDATE_INTERVAL_ACCOUNT: Final = timedelta(hours=6)  # Slow-changing data
UPDATE_INTERVAL_DAILY_USAGE: Final = timedelta(hours=2)  # Daily/monthly usage
UPDATE_INTERVAL_HOURLY_USAGE: Final = timedelta(minutes=30)  # Hourly usage

# Restart Schedule
RESTART_TIME: Final = "03:00:00"  # 3 AM daily restart

# Platforms
PLATFORMS: Final = ["sensor"]

# Sensor Types - Account Information
SENSOR_ACCOUNT_BALANCE: Final = "account_balance"
SENSOR_AMOUNT_DUE: Final = "amount_due"
SENSOR_PAYMENT_DUE_DATE: Final = "payment_due_date"
SENSOR_DAYS_UNTIL_OVERDUE: Final = "days_until_overdue"
SENSOR_NEXT_BILL_DATE: Final = "next_bill_date"
SENSOR_PAYMENT_METHOD: Final = "payment_method"
SENSOR_PRODUCT_NAME: Final = "product_name"
SENSOR_BILLING_FREQUENCY: Final = "billing_frequency"

# Sensor Types - Usage Data
SENSOR_TODAY_USAGE: Final = "today_usage"
SENSOR_TODAY_COST: Final = "today_cost"
SENSOR_YESTERDAY_USAGE: Final = "yesterday_usage"
SENSOR_YESTERDAY_COST: Final = "yesterday_cost"
SENSOR_THIS_MONTH_USAGE: Final = "this_month_usage"
SENSOR_THIS_MONTH_COST: Final = "this_month_cost"
SENSOR_LAST_MONTH_USAGE: Final = "last_month_usage"
SENSOR_LAST_MONTH_COST: Final = "last_month_cost"
SENSOR_FREE_USAGE_TODAY: Final = "free_usage_today"
SENSOR_OFFPEAK_USAGE_TODAY: Final = "offpeak_usage_today"

# Statistic Types - Historical Data
STATISTIC_HOURLY_USAGE: Final = "hourly_usage"
STATISTIC_HOURLY_COST: Final = "hourly_cost"
STATISTIC_DAILY_USAGE: Final = "daily_usage"
STATISTIC_DAILY_COST: Final = "daily_cost"
STATISTIC_MONTHLY_USAGE: Final = "monthly_usage"
STATISTIC_MONTHLY_COST: Final = "monthly_cost"

# Unit of Measurement
ENERGY_KILO_WATT_HOUR: Final = "kWh"
CURRENCY_DOLLAR: Final = "NZD"

# Device Class
DEVICE_CLASS_ENERGY: Final = "energy"
DEVICE_CLASS_MONETARY: Final = "monetary"

# State Class
STATE_CLASS_TOTAL: Final = "total"
STATE_CLASS_MEASUREMENT: Final = "measurement"

# Icons
ICON_ACCOUNT: Final = "mdi:account"
ICON_CURRENCY: Final = "mdi:currency-usd"
ICON_CALENDAR: Final = "mdi:calendar"
ICON_LIGHTNING_BOLT: Final = "mdi:lightning-bolt"
ICON_CHART_LINE: Final = "mdi:chart-line"
ICON_HOME_LIGHTNING_BOLT: Final = "mdi:home-lightning-bolt"

# Error Messages
ERROR_AUTH_FAILED: Final = "auth_failed"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_INVALID_AUTH: Final = "invalid_auth"
ERROR_UNKNOWN: Final = "unknown"
ERROR_NO_ACCOUNTS: Final = "no_accounts"
ERROR_ACCOUNT_IN_USE: Final = "account_in_use"

# Success Messages
SUCCESS_AUTH: Final = "auth_success"

# Coordinator Data Keys
DATA_ACCOUNT: Final = "account"
DATA_USAGE_HOURLY: Final = "usage_hourly"
DATA_USAGE_DAILY: Final = "usage_daily"
DATA_USAGE_MONTHLY: Final = "usage_monthly"

# Storage Keys
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.statistics"

# Data Intervals
INTERVAL_HOURLY: Final = "hourly"
INTERVAL_DAILY: Final = "daily"
INTERVAL_MONTHLY: Final = "monthly"

# Retry Configuration
MAX_RETRIES: Final = 3
RETRY_DELAY: Final = 5  # seconds
