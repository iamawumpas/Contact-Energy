"""Data coordinator for Contact Energy integration.

This module provides the data coordinator that periodically fetches account
information from the Contact Energy API. Updates occur twice per day at 01:00
and 13:00 to keep account balance and billing data current while minimizing
API calls.

Version: 1.8.3
Changes: Custom scheduling for account data (twice daily) and usage coordination
"""

import logging
import random
from datetime import timedelta, datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .contact_api import ContactEnergyApi, ContactEnergyApiError
from .usage_coordinator import UsageCoordinator

_LOGGER = logging.getLogger(__name__)


class ContactEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Contact Energy API data fetching.

    This coordinator handles periodic fetching of account information from the
    Contact Energy API. It's configured to update twice per day at 01:00 and
    13:00 to keep account balance and billing data current while minimizing
    API requests.
    
    Additionally, it triggers usage data synchronization as a background task
    via the UsageCoordinator which handles hourly usage data updates and daily
    usage/monthly data updates.
    """

    def __init__(self, hass: HomeAssistant, api_client: ContactEnergyApi, contract_id: str, config_entry = None):
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            api_client: The Contact Energy API client for data retrieval.
            contract_id: Contract identifier for usage data sync.
            config_entry: Config entry to access ICP and other configuration.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Check hourly for usage updates, but account data only updates twice daily
            update_interval=timedelta(hours=1),
        )
        self.api_client = api_client
        self.contract_id = contract_id
        self.config_entry = config_entry
        # When True, skip spawning the background usage sync on the next refresh
        self._skip_next_usage_sync = False
        
        # Initialize usage coordinator (Phase 1 / v1.4.0)
        # This handles background syncing of hourly/daily/monthly usage data
        icp = config_entry.data.get("icp") if config_entry else None
        self.usage_coordinator = UsageCoordinator(hass, api_client, contract_id, icp)
        
        _LOGGER.debug(
            "ContactEnergyCoordinator initialized with usage sync for contract %s",
            contract_id
        )

    async def _async_update_data(self) -> dict:
        """Fetch account information from Contact Energy API.

        This method is called by the coordinator to refresh account data.
        It retrieves complete account information including balance, invoice
        details, next billing date, and contract information.

        If the stored token is invalid, it will re-authenticate using the stored
        credentials before fetching data.
        
        Additionally, triggers usage data sync as a background task (non-blocking).
        Usage sync failures do not affect account data updates.
        
        NOTE: If account data fetch fails after 2 retries, the integration will
        continue with usage sync using the known contract ID. This allows basic
        functionality when the accounts endpoint is experiencing server issues.

        Returns:
            Dictionary containing the account data, or a minimal dict if fetch fails.

        Raises:
            UpdateFailed: If unable to authenticate or get token.
        """
        # Check if we should fetch account data or just run usage sync
        should_fetch_accounts = self._should_fetch_account_data_now()
        
        _LOGGER.debug(
            "Coordinator update: should_fetch_accounts=%s, contract_id=%s", 
            should_fetch_accounts, self.contract_id
        )
        
        # Always trigger usage sync (usage coordinator handles its own scheduling)
        if not self._skip_next_usage_sync:
            _LOGGER.debug("Triggering background usage sync for contract %s", self.contract_id)
            self.hass.async_create_task(
                self._async_sync_usage(),
                name=f"usage_sync_{self.contract_id}"
            )
        else:
            _LOGGER.debug(
                "Skipping background usage sync for contract %s (skip requested)",
                self.contract_id,
            )
        
        # Only fetch account data if it's scheduled time
        if not should_fetch_accounts:
            _LOGGER.debug("Not scheduled time for account data, returning cached data")
            # Return minimal data to keep coordinator happy
            return self.data or {
                "accountsSummary": [{
                    "id": "",
                    "nickname": "Contact Energy Account",
                    "contracts": [{"contractId": self.contract_id}]
                }]
            }
        
        try:
            _LOGGER.info("Fetching account information from Contact Energy API (scheduled update)")
            
            # Try to get accounts with current token
            try:
                account_data = await self.api_client.get_accounts()
                _LOGGER.debug("Successfully fetched account data")
                return account_data
            
            except Exception as auth_error:
                # If we get a 401/403 or authentication error, re-authenticate
                # This handles cases where the stored token has expired
                error_str = str(auth_error)
                _LOGGER.warning(f"Initial fetch failed, re-authenticating: {error_str}")
                
                # Check if password is available
                if not self.api_client.password:
                    _LOGGER.error("Cannot re-authenticate: password not stored in config entry")
                    raise UpdateFailed("Password not available for re-authentication. Please reconfigure the integration.")
                
                # Re-authenticate to get a fresh token
                try:
                    _LOGGER.debug(f"Attempting to re-authenticate as {self.api_client.email}")
                    await self.api_client.authenticate()
                    _LOGGER.debug("Successfully re-authenticated")
                except Exception as auth_err:
                    _LOGGER.error(f"Re-authentication failed: {str(auth_err)}")
                    raise UpdateFailed(f"Re-authentication failed: {str(auth_err)}") from auth_err
                
                # Retry fetching account data with the new token
                try:
                    account_data = await self.api_client.get_accounts()
                    _LOGGER.debug("Successfully fetched account data after re-authentication")

                    # Trigger usage sync after successful re-auth unless skipped
                    if not self._skip_next_usage_sync:
                        _LOGGER.debug("Triggering background usage sync for contract %s (after re-auth)", self.contract_id)
                        self.hass.async_create_task(
                            self._async_sync_usage(),
                            name=f"usage_sync_{self.contract_id}"
                        )
                    else:
                        _LOGGER.debug(
                            "Skipping background usage sync for contract %s after re-auth (skip requested)",
                            self.contract_id,
                        )
                    
                    return account_data
                    
                except Exception as retry_error:
                    # Account data fetch failed even after re-auth
                    # Log the error but continue with usage sync using known contract ID
                    _LOGGER.warning(
                        f"Account fetch failed after re-authentication: {str(retry_error)}. "
                        f"Proceeding with usage sync only using contract ID {self.contract_id}",
                        exc_info=True
                    )
                    
                    # Still trigger usage sync as it doesn't need account data
                    _LOGGER.debug("Triggering background usage sync for contract %s (fallback mode)", self.contract_id)
                    self.hass.async_create_task(
                        self._async_sync_usage(),
                        name=f"usage_sync_{self.contract_id}"
                    )
                    
                    # Return minimal account data structure to keep coordinator happy
                    # The sensor will still work with usage data even if account info is unavailable
                    return {
                        "accountsSummary": [{
                            "id": "",
                            "nickname": "Unknown Account",
                            "contracts": [{"contractId": self.contract_id}]
                        }]
                    }

        except ContactEnergyApiError as e:
            # API returned an error - convert to UpdateFailed for coordinator handling
            _LOGGER.error(f"API error during data update: {str(e)}")
            raise UpdateFailed(f"API error: {str(e)}") from e

        except Exception as e:
            # Unexpected error - log and raise UpdateFailed
            _LOGGER.exception(f"Unexpected error during data update: {e}")
            raise UpdateFailed(f"Unexpected error: {str(e)}") from e
    
    async def _async_sync_usage(self) -> None:
        """Background task to sync usage data.
        
        This method runs as a background task and syncs hourly/daily/monthly
        usage data via the UsageCoordinator. Errors are caught and logged
        to prevent breaking the main coordinator.
        
        Note: This is a Phase 1 (v1.4.0) feature - usage data download and caching only.
              Sensor exposure will come in Phase 2 (v1.5.0).
        """
        try:
            _LOGGER.debug("Starting background usage sync task for contract %s", self.contract_id)
            await self.usage_coordinator.async_sync_usage()
            _LOGGER.debug("Background usage sync task completed for contract %s", self.contract_id)
        except Exception as e:
            # Log errors but don't propagate - usage sync failures shouldn't break account data
            _LOGGER.error(
                "Background usage sync failed for contract %s: %s",
                self.contract_id, str(e), exc_info=True
            )
    
    def _calculate_next_account_update_interval(self) -> timedelta:
        """Calculate time until next scheduled account update.
        
        Account data updates occur twice daily at 01:00 and 13:00.
        This method calculates how long to wait until the next scheduled time.
        
        Returns:
            timedelta: Time to wait until next update
        """
        now = datetime.now(timezone.utc)
        next_times = []
        
        # Schedule today's updates at 01:00 and 13:00 UTC  
        for hour in [1, 13]:
            next_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if next_time <= now:
                # If past this time today, schedule for tomorrow
                next_time = next_time + timedelta(days=1)
            next_times.append(next_time)
            
        # Choose the earliest next time
        next_update = min(next_times)
        interval = next_update - now
        
        _LOGGER.debug(
            "Next account update scheduled for %s (in %s)",
            next_update.isoformat(), interval
        )
        
        return interval

    def _should_fetch_account_data_now(self) -> bool:  
        """Check if it's time to fetch account data.
        
        Account data is fetched twice daily at 01:00 and 13:00 UTC.
        
        Returns:
            bool: True if it's time to fetch account data
        """
        now = datetime.now(timezone.utc)
        
        # Check if we're within 30 minutes of 01:00 or 13:00
        for target_hour in [1, 13]:
            target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            time_diff = abs((now - target_time).total_seconds())
            
            # If we're within 30 minutes of target time
            if time_diff <= 30 * 60:
                return True
                
        return False
