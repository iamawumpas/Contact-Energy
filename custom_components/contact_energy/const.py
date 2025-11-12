"""Constants and helpers for the Contact Energy integration."""

from datetime import date

DOMAIN = "contact_energy"
NAME = "Contact Energy"

# Config options
CONF_USAGE_DAYS = "usage_days"  # legacy option kept for backward-compat
CONF_USAGE_MONTHS = "usage_months"
CONF_ACCOUNT_ID = "account_id"
CONF_CONTRACT_ID = "contract_id"
CONF_CONTRACT_ICP = "contract_icp"

# Limits
USAGE_DAYS_MIN = 1
USAGE_DAYS_MAX = 400

# Months-based history window shown in the UI
USAGE_MONTHS_MIN = 1
USAGE_MONTHS_MAX = 36

# Default scan interval - 8 hours as requested
DEFAULT_SCAN_INTERVAL = 28800  # 8 hours in seconds

# Daily restart configuration
RESTART_HOUR = 3
RESTART_MINUTE_VARIANCE = 30

# API Configuration
API_BASE_URL = "https://api.contact-digital-prod.net"
API_KEY = "z840P4lQCH9TqcjC9L2pP157DZcZJMcr5tVQCvyx"
API_TIMEOUT_DEFAULT = 30
API_TIMEOUT_USAGE = 60
API_MAX_RETRIES = 2
API_BACKOFF_INITIAL = 1

# Chart sensor data retention (days)
CHART_HOURLY_DAYS = 14
CHART_DAILY_DAYS = 60
CHART_MONTHLY_START_YEAR = 2000

# Device information
DEVICE_MANUFACTURER = "Contact Energy"
DEVICE_MODEL = "Smart Meter"
DEVICE_SW_VERSION = "1.0"

# Sensor startup delays (seconds)
STARTUP_DELAY_BASE_MAX = 30
STARTUP_DELAY_JITTER_MIN = 0.5
STARTUP_DELAY_JITTER_MAX = 2.0
CONVENIENCE_DELAY_BASE_MAX = 20
CONVENIENCE_DELAY_JITTER_MIN = 0.1
CONVENIENCE_DELAY_JITTER_MAX = 1.5


def _days_in_month(year: int, month: int) -> int:
	"""Return number of days in a given year-month without external deps."""
	month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
	if month == 2:
		is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
		return 29 if is_leap else 28
	return month_lengths[month - 1]


def _subtract_months(d: date, months: int) -> date:
	"""Subtract full calendar months from a date, clamping the day to month length."""
	year = d.year
	month = d.month - months
	while month <= 0:
		month += 12
		year -= 1
	day = min(d.day, _days_in_month(year, month))
	return date(year, month, day)


def months_to_days(months: int, *, base_date: date | None = None) -> int:
	"""Convert months window to calendar-precise number of days (inclusive).

	Example: If today is 2025-11-02 and months=1, the start date is 2025-10-02,
	and the inclusive length is (2025-11-02 - 2025-10-02) + 1 = 32 days.
	"""
	try:
		m = int(months)
	except Exception:
		m = 1
	if m < USAGE_MONTHS_MIN:
		m = USAGE_MONTHS_MIN
	if m > USAGE_MONTHS_MAX:
		m = USAGE_MONTHS_MAX
	end = base_date or date.today()
	start = _subtract_months(end, m)
	days = (end - start).days + 1
	return max(USAGE_DAYS_MIN, days)


def days_to_months(days: int) -> int:
	"""Approximate days to months for defaulting in the options UI.

	Rounds to the nearest month using 30-day months, and clamps to [1, 36].
	"""
	try:
		d = int(days)
	except Exception:
		d = 30
	m = max(USAGE_MONTHS_MIN, min(USAGE_MONTHS_MAX, round(d / 30)))
	if m < 1:
		m = 1
	return m
