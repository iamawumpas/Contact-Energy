"""Data coordinator for Contact Energy integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from aiohttp import ClientSession
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import ContactEnergyApi, AuthenticationError, ConnectionError as ApiConnectionError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_EMAIL,
    CONF_HISTORY_DAYS,
    CONF_ICP_NUMBER,
    CONF_PASSWORD,
    DATA_ACCOUNT,
    DATA_USAGE_DAILY,
    DATA_USAGE_HOURLY,
    DATA_USAGE_MONTHLY,
    DOMAIN,
    INTERVAL_DAILY,
    INTERVAL_HOURLY,
    INTERVAL_MONTHLY,
    UPDATE_INTERVAL_ACCOUNT,
    UPDATE_INTERVAL_DAILY_USAGE,
    UPDATE_INTERVAL_HOURLY_USAGE,
)

_LOGGER = logging.getLogger(__name__)


class ContactEnergyDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Contact Energy data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        email: str,
        password: str,
        account_id: str,
        contract_id: str,
        icp_number: str,
        history_days: int,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the coordinator.
        
        Args:
            hass: Home Assistant instance
            email: User email
            password: User password
            account_id: Contact Energy account ID
            contract_id: Contact Energy contract ID
            icp_number: ICP number (lowercase)
            history_days: Number of days of history to maintain
            session: Optional aiohttp session
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{icp_number}",
            update_interval=UPDATE_INTERVAL_ACCOUNT,
        )
        
        self._email = email
        self._password = password
        self._account_id = account_id
        self._contract_id = contract_id
        self._icp_number = icp_number
        self._history_days = history_days
        self._session = session
        self._api: ContactEnergyApi | None = None
        self._own_session = session is None
        
        # Last update times for each data type
        self._last_account_update: datetime | None = None
        self._last_hourly_update: datetime | None = None
        self._last_daily_update: datetime | None = None
        self._last_monthly_update: datetime | None = None
        
        # Data cache
        self.data = {
            DATA_ACCOUNT: None,
            DATA_USAGE_HOURLY: {},
            DATA_USAGE_DAILY: {},
            DATA_USAGE_MONTHLY: {},
        }
        
        _LOGGER.debug("ContactEnergyDataUpdateCoordinator initialized for ICP: %s", 
                     icp_number)

    async def async_init(self) -> None:
        """Initialize the coordinator and create API client.
        
        This should be called after __init__ to set up the API session.
        """
        _LOGGER.debug("Initializing coordinator for ICP: %s", self._icp_number)
        
        if self._own_session:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            self._session = async_get_clientsession(self.hass)
            _LOGGER.debug("Retrieved Home Assistant session for coordinator")
        else:
            _LOGGER.debug("Using provided session for coordinator")
        
        self._api = ContactEnergyApi(
            self._email, self._password, self._session
        )
        _LOGGER.info("API client created for coordinator (ICP: %s)", self._icp_number)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Contact Energy API.
        
        This is called periodically by the coordinator.
        
        Returns:
            Updated data dictionary
            
        Raises:
            UpdateFailed: If update fails
        """
        _LOGGER.debug("=" * 60)
        _LOGGER.debug("Starting data update for ICP: %s", self._icp_number)
        _LOGGER.debug("=" * 60)
        
        try:
            if not self._api:
                _LOGGER.error("❌ API client not initialized")
                raise UpdateFailed("API client not initialized")
            
            now = dt_util.now()
            
            # Update account data every 6 hours
            if (
                self._last_account_update is None
                or (now - self._last_account_update) >= UPDATE_INTERVAL_ACCOUNT
            ):
                _LOGGER.info("📋 Updating account data for ICP: %s", self._icp_number)
                try:
                    await self._update_account_data()
                    self._last_account_update = now
                    _LOGGER.info("✓ Account data updated successfully")
                except Exception as err:
                    _LOGGER.error("✗ Account data update failed: %s", err)
                    raise
            else:
                _LOGGER.debug("⊘ Skipping account data update (next update in %s)",
                            UPDATE_INTERVAL_ACCOUNT - (now - self._last_account_update))
            
            # Update daily/monthly usage every 2 hours
            if (
                self._last_daily_update is None
                or (now - self._last_daily_update) >= UPDATE_INTERVAL_DAILY_USAGE
            ):
                _LOGGER.info("📊 Updating daily/monthly usage for ICP: %s", self._icp_number)
                try:
                    await self._update_daily_usage()
                    _LOGGER.info("✓ Daily usage updated successfully")
                except Exception as err:
                    _LOGGER.error("✗ Daily usage update failed: %s", err)
                    raise
                
                try:
                    await self._update_monthly_usage()
                    _LOGGER.info("✓ Monthly usage updated successfully")
                    self._last_daily_update = now
                except Exception as err:
                    _LOGGER.error("✗ Monthly usage update failed: %s", err)
                    raise
            else:
                _LOGGER.debug("⊘ Skipping daily/monthly update (next update in %s)",
                            UPDATE_INTERVAL_DAILY_USAGE - (now - self._last_daily_update))
            
            # Update hourly usage every 30 minutes
            if (
                self._last_hourly_update is None
                or (now - self._last_hourly_update) >= UPDATE_INTERVAL_HOURLY_USAGE
            ):
                _LOGGER.info("⚡ Updating hourly usage for ICP: %s", self._icp_number)
                try:
                    await self._update_hourly_usage()
                    self._last_hourly_update = now
                    _LOGGER.info("✓ Hourly usage updated successfully")
                except Exception as err:
                    _LOGGER.error("✗ Hourly usage update failed: %s", err)
                    raise
            else:
                _LOGGER.debug("⊘ Skipping hourly update (next update in %s)",
                            UPDATE_INTERVAL_HOURLY_USAGE - (now - self._last_hourly_update))
            
            _LOGGER.info("=" * 60)
            _LOGGER.info("✓ Data update completed successfully for ICP: %s", self._icp_number)
            _LOGGER.info("=" * 60)
            return self.data
            
        except (AuthenticationError, ApiConnectionError) as err:
            _LOGGER.error("❌ API error during update for ICP %s: %s", 
                        self._icp_number, err)
            _LOGGER.error("=" * 60)
            raise UpdateFailed(f"Contact Energy API error: {err}") from err
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("❌ Unexpected error during update for ICP %s: %s",
                            self._icp_number, err)
            _LOGGER.error("=" * 60)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _update_account_data(self) -> None:
        """Fetch account data.
        
        Raises:
            AuthenticationError: If authentication fails
            ApiConnectionError: If connection fails
        """
        try:
            _LOGGER.debug("Fetching account data for contract: %s", self._contract_id)
            
            if not self._api.is_authenticated:
                _LOGGER.debug("🔐 API not authenticated, authenticating...")
                await self._api.authenticate()
                _LOGGER.debug("✓ Authentication successful")
            else:
                _LOGGER.debug("✓ API already authenticated")
            
            account_data = await self._api.get_accounts()
            self.data[DATA_ACCOUNT] = account_data
            
            # Extract useful info to log
            account_summary = account_data.get("accountsSummary", [])
            account_detail = account_data.get("accountDetail", {})
            if account_summary:
                _LOGGER.info("✓ Account data updated: %d account(s) found", len(account_summary))
                balance = account_detail.get("accountBalance", {})
                _LOGGER.debug("  - Current balance: %s", balance.get("formattedCurrentBalance"))
                invoice = account_detail.get("invoice", {})
                _LOGGER.debug("  - Amount due: %s", invoice.get("amountDue"))
            
        except Exception as err:
            _LOGGER.error("❌ Failed to update account data: %s", err)
            _LOGGER.exception("Full traceback:")
            raise

    async def _update_hourly_usage(self) -> None:
        """Fetch hourly usage data for the last day.
        
        Raises:
            AuthenticationError: If authentication fails
            ApiConnectionError: If connection fails
        """
        try:
            # Get hourly data for yesterday and today
            now = dt_util.now()
            yesterday = now - timedelta(days=1)
            
            _LOGGER.debug("Fetching hourly usage from %s to %s",
                        yesterday.date(), now.date())
            
            # Fetch hourly for yesterday
            _LOGGER.debug("  📅 Yesterday (%s)...", yesterday.date())
            usage_yesterday = await self._api.get_hourly_usage(
                self._contract_id, self._account_id, yesterday
            )
            _LOGGER.debug("    ✓ Got %d hourly records", len(usage_yesterday))
            
            # Fetch hourly for today
            _LOGGER.debug("  📅 Today (%s)...", now.date())
            usage_today = await self._api.get_hourly_usage(
                self._contract_id, self._account_id, now
            )
            _LOGGER.debug("    ✓ Got %d hourly records", len(usage_today))
            
            # Store by date string as key
            usage_all = usage_yesterday + usage_today
            for record in usage_all:
                date_key = record.get("date", "").split("T")[0]
                if date_key:
                    if date_key not in self.data[DATA_USAGE_HOURLY]:
                        self.data[DATA_USAGE_HOURLY][date_key] = []
                    self.data[DATA_USAGE_HOURLY][date_key].append(record)
            
            _LOGGER.info("✓ Hourly usage updated: %d total records", len(usage_all))
            
        except Exception as err:
            _LOGGER.error("❌ Failed to update hourly usage: %s", err)
            _LOGGER.exception("Full traceback:")
            raise

    async def _update_daily_usage(self) -> None:
        """Fetch daily usage data for configured history period.
        
        Raises:
            AuthenticationError: If authentication fails
            ApiConnectionError: If connection fails
        """
        try:
            now = dt_util.now()
            start_date = now - timedelta(days=self._history_days)
            
            _LOGGER.debug("Fetching daily usage from %s to %s (%d days)",
                        start_date.date(), now.date(), self._history_days)
            
            usage_data = await self._api.get_daily_usage(
                self._contract_id, self._account_id, start_date, now
            )
            
            # Store by date string as key
            for record in usage_data:
                date_key = record.get("date", "").split("T")[0]
                if date_key:
                    self.data[DATA_USAGE_DAILY][date_key] = record
            
            if usage_data:
                today_usage = usage_data[-1]
                _LOGGER.info("✓ Daily usage updated: %d records | Today: %s kWh ($%s)", 
                           len(usage_data),
                           today_usage.get("value", "N/A"),
                           today_usage.get("dollarValue", "N/A"))
            else:
                _LOGGER.info("✓ Daily usage updated: 0 records (no data available)")
            
        except Exception as err:
            _LOGGER.error("❌ Failed to update daily usage: %s", err)
            _LOGGER.exception("Full traceback:")
            raise

    async def _update_monthly_usage(self) -> None:
        """Fetch monthly usage data for configured history period.
        
        Raises:
            AuthenticationError: If authentication fails
            ApiConnectionError: If connection fails
        """
        try:
            now = dt_util.now()
            start_date = now - timedelta(days=self._history_days)
            
            _LOGGER.debug("Fetching monthly usage from %s to %s (%d days)",
                        start_date.date(), now.date(), self._history_days)
            
            usage_data = await self._api.get_monthly_usage(
                self._contract_id, self._account_id, start_date, now
            )
            
            # Store by year-month key
            for record in usage_data:
                year = record.get("year")
                month = record.get("month")
                if year and month:
                    date_key = f"{year}-{month:02d}"
                    self.data[DATA_USAGE_MONTHLY][date_key] = record
            
            if usage_data:
                current_month = usage_data[-1]
                _LOGGER.info("✓ Monthly usage updated: %d records | Current: %s kWh ($%s)", 
                           len(usage_data),
                           current_month.get("value", "N/A"),
                           current_month.get("dollarValue", "N/A"))
            else:
                _LOGGER.info("✓ Monthly usage updated: 0 records (no data available)")
            
        except Exception as err:
            _LOGGER.error("❌ Failed to update monthly usage: %s", err)
            _LOGGER.exception("Full traceback:")
            raise

    def get_today_usage(self) -> dict[str, Any] | None:
        """Get today's usage summary.
        
        Returns:
            Dictionary with today's usage or None
        """
        now = dt_util.now()
        today_key = now.strftime("%Y-%m-%d")
        return self.data[DATA_USAGE_DAILY].get(today_key)

    def get_yesterday_usage(self) -> dict[str, Any] | None:
        """Get yesterday's usage summary.
        
        Returns:
            Dictionary with yesterday's usage or None
        """
        now = dt_util.now()
        yesterday = now - timedelta(days=1)
        yesterday_key = yesterday.strftime("%Y-%m-%d")
        return self.data[DATA_USAGE_DAILY].get(yesterday_key)

    def get_this_month_usage(self) -> dict[str, Any] | None:
        """Get this month's usage summary.
        
        Returns:
            Dictionary with this month's usage or None
        """
        now = dt_util.now()
        month_key = now.strftime("%Y-%m")
        return self.data[DATA_USAGE_MONTHLY].get(month_key)

    def get_last_month_usage(self) -> dict[str, Any] | None:
        """Get last month's usage summary.
        
        Returns:
            Dictionary with last month's usage or None
        """
        now = dt_util.now()
        if now.month == 1:
            last_month = now.replace(year=now.year - 1, month=12)
        else:
            last_month = now.replace(month=now.month - 1)
        
        month_key = last_month.strftime("%Y-%m")
        return self.data[DATA_USAGE_MONTHLY].get(month_key)

    def get_today_hourly_usage(self) -> list[dict[str, Any]]:
        """Get today's hourly usage data.
        
        Returns:
            List of hourly records for today
        """
        now = dt_util.now()
        today_key = now.strftime("%Y-%m-%d")
        return self.data[DATA_USAGE_HOURLY].get(today_key, [])

    @property
    def account_data(self) -> dict[str, Any] | None:
        """Get account data.
        
        Returns:
            Account data dictionary or None
        """
        return self.data.get(DATA_ACCOUNT)

    @property
    def icp_number(self) -> str:
        """Get the ICP number.
        
        Returns:
            ICP number (lowercase)
        """
        return self._icp_number

    @property
    def history_days(self) -> int:
        """Get the history days setting.
        
        Returns:
            Number of days of history
        """
        return self._history_days
