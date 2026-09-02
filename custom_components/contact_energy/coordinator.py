"""Main data coordinator for the Contact Energy integration.

=== WHAT THIS DOES ===
This module contains ``ContactEnergyCoordinator``, the primary coordinator for
the legacy integration flow. It refreshes account information on a schedule,
keeps a saved account snapshot for restart resilience, and starts background
usage-data synchronisation when appropriate.

The account side and usage side are deliberately linked but independent:
- account refreshes keep balance and billing sensors current,
- usage refreshes keep historical consumption caches current,
- failures in usage syncing should not break account updates,
- and some failures in account fetching still allow usage syncing to continue.

=== FOR NON-CODERS ===
Think of this file as the shift manager for the integration.
It decides:
- when to check Contact Energy for new account information,
- when to reuse the last saved copy instead,
- when to ask a background helper to refresh usage history,
- and how to keep the system running even when the API misbehaves.

Helpful terms:
- "Coordinator": a shared manager that fetches data once for many entities.
- "Polling": checking for updates on a repeating timer.
- "Update interval": how often the repeating timer is allowed to fire.
- "Data refresh": replacing older saved information with newer data.

Version: 1.8.3
Changes: Custom scheduling for account data (twice daily) and usage coordination
"""

# ============================================================================
# IMPORTS
# ============================================================================

# logging: records normal operation, warnings, and errors for troubleshooting.
import logging

# datetime/timezone/timedelta: used for scheduling account refresh windows.
from datetime import datetime, timedelta, timezone

# HomeAssistant: the running Home Assistant instance that owns this coordinator.
from homeassistant.core import HomeAssistant

# DataUpdateCoordinator: Home Assistant helper for shared polling.
# UpdateFailed: the standard coordinator error type for refresh failures.
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# DOMAIN: the integration's Home Assistant identifier.
from .const import DOMAIN

# ContactEnergyApi: legacy API client used to fetch account information.
# ContactEnergyApiError: custom API exception that gets converted for Home Assistant.
# ContactEnergyAuthError: raised specifically for expired/invalid auth tokens.
# ContactEnergyConnectionError: raised for temporary network/timeout/5xx failures.
from .contact_api import (
    ContactEnergyApi,
    ContactEnergyApiError,
    ContactEnergyAuthError,
    ContactEnergyConnectionError,
)

# UsageCoordinator: background helper that syncs usage caches independently.
from .usage_coordinator import UsageCoordinator

# AccountSnapshotCache: stores the last known account payload on disk for restart recovery.
from .account_snapshot_cache import AccountSnapshotCache

# ============================================================================
# LOGGER SETUP
# ============================================================================

# Create a logger dedicated to messages from this module.
_LOGGER = logging.getLogger(__name__)


# ============================================================================
# MAIN COORDINATOR CLASS
# ============================================================================

class ContactEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator that manages account refreshes and usage sync triggers.

    === WHAT THIS DOES ===
    This class is the main shared data manager for the legacy Contact Energy
    integration flow. It refreshes account information, preserves a fallback
    snapshot for restarts, and triggers the separate usage coordinator in the
    background whenever usage data should be brought up to date.

    === FOR NON-CODERS ===
    Imagine one supervisor handling two related jobs:
    1. Keep the latest account letter on the desk.
    2. Ask another worker to keep the usage history archive up to date.

    The supervisor focuses on the account letter first, but still tries to
    keep the archive refreshed whenever possible.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: ContactEnergyApi,
        contract_id: str,
        config_entry=None,
    ):
        """Initialize the coordinator.

        === WHAT THIS DOES ===
        This constructor stores the integration dependencies, sets up helper
        objects for usage syncing and snapshot caching, and configures the base
        Home Assistant coordinator timer.

        === FOR NON-CODERS ===
        This is the coordinator's setup checklist. It wires together the main
        Contact Energy API helper, the contract being tracked, optional setup
        information from Home Assistant, and the background usage-sync helper.
        """
        # ====================================================================
        # STEP 1: Register with Home Assistant as a shared polling coordinator.
        # ====================================================================
        # The timer fires hourly so usage checks can happen often, while the
        # account data itself still decides internally whether it should fetch.
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )

        # ====================================================================
        # STEP 2: Store the core objects and state flags used by later refreshes.
        # ====================================================================
        # The API client is the object that talks to Contact Energy.
        self.api_client = api_client

        # The contract ID lets usage syncing continue even if account calls fail.
        self.contract_id = contract_id

        # The config entry contains setup values such as the ICP identifier.
        self.config_entry = config_entry

        # When True, the next refresh will avoid starting an extra usage sync.
        self._skip_next_usage_sync = False

        # This flag prevents the saved snapshot from being loaded more than once.
        self._has_loaded_account_snapshot = False

        # This flag forces one immediate live fetch after setup completes.
        self._is_first_refresh = True

        # ====================================================================
        # STEP 3: Create helper objects used by the coordinator.
        # ====================================================================
        # The ICP helps the usage coordinator identify the correct property.
        icp = config_entry.data.get("icp") if config_entry else None

        # Create the background usage-sync helper for hourly/daily/monthly data.
        self.usage_coordinator = UsageCoordinator(hass, api_client, contract_id, icp)

        # Create the restart-safe snapshot cache for account payloads.
        self.account_snapshot_cache = AccountSnapshotCache(contract_id)

        _LOGGER.debug(
            "ContactEnergyCoordinator initialized with usage sync for contract %s",
            contract_id,
        )

    async def _async_update_data(self) -> dict:
        """Fetch account data and trigger usage sync when appropriate.

        === WHAT THIS DOES ===
        This is the main coordinator refresh method. It restores a saved account
        snapshot on first run, decides whether usage syncing should start in the
        background, decides whether account data should be fetched right now,
        retries account fetching after re-authentication if needed, and falls
        back to saved data when Contact Energy is unavailable.

        === FOR NON-CODERS ===
        Think of this as a careful office routine:
        1. If a saved copy exists from before a restart, read it first.
        2. Decide whether the usage-history assistant should start working.
        3. Decide whether it is time to phone Contact Energy for account data.
        4. If the first phone call fails because the login expired, sign in again.
        5. If the system still cannot fetch data, use the last saved copy if possible.

        Why this exists:
        The integration needs to stay useful even when part of the API fails.
        This method is the resilience layer that keeps sensors populated.
        """
        # ====================================================================
        # STEP 1: On the very first run, try to restore the saved account snapshot.
        # ====================================================================
        # This keeps account sensors populated after Home Assistant restarts,
        # even before the next live API request has succeeded.
        if self.data is None and not self._has_loaded_account_snapshot:
            snapshot = await self.account_snapshot_cache.load()
            self._has_loaded_account_snapshot = True
            if snapshot:
                self.data = snapshot
                _LOGGER.info(
                    "Loaded persisted account snapshot for contract %s",
                    self.contract_id,
                )

        # ====================================================================
        # STEP 2: Decide whether we are on a first run and whether a live
        # account fetch is scheduled for the current time window.
        # ====================================================================
        is_first_run = self.data is None
        should_fetch_accounts = self._should_fetch_account_data_now()

        # Start with the assumption that no reusable usage cache is available.
        cache_available = False

        # ====================================================================
        # STEP 3: If needed, inspect the usage cache before deciding how urgent
        # the next background usage sync should be.
        # ====================================================================
        if not should_fetch_accounts or is_first_run:
            try:
                _LOGGER.debug(
                    "Checking for existing usage cache for contract %s",
                    self.contract_id,
                )

                # Load the usage cache so we can see whether real data already exists.
                cache_loaded = await self.usage_coordinator.cache.load()
                if cache_loaded:
                    cache_data = self.usage_coordinator.cache.data

                    # Count all cached hourly, daily, and monthly records.
                    total_records = (
                        len(cache_data.get("hourly", {}))
                        + len(cache_data.get("daily", {}))
                        + len(cache_data.get("monthly", {}))
                    )

                    # If at least one real record exists, the cache is usable.
                    if total_records > 0:
                        cache_available = True
                        _LOGGER.info(
                            "Found existing usage cache for contract %s with %d records, using cached data",
                            self.contract_id,
                            total_records,
                        )
                    else:
                        _LOGGER.debug(
                            "Usage cache exists but is empty for contract %s",
                            self.contract_id,
                        )
                else:
                    _LOGGER.debug(
                        "No existing usage cache found for contract %s",
                        self.contract_id,
                    )
            except Exception as cache_error:
                # If cache inspection fails, treat the cache as unavailable so a
                # stronger usage sync can be triggered safely.
                _LOGGER.warning(
                    "Cache load failed for contract %s, will force sync: %s",
                    self.contract_id,
                    cache_error,
                )
                cache_available = False

        # ====================================================================
        # STEP 4: Decide whether to schedule a forced or normal usage sync.
        # ====================================================================
        # force_usage_sync means we either have no usable cache yet or we are on
        # the very first refresh after setup and want to seed data immediately.
        force_usage_sync = (is_first_run and not cache_available) or self._is_first_refresh

        # normal_usage_sync means the background sync can proceed as part of the
        # ordinary hourly cadence, provided no temporary skip has been requested.
        normal_usage_sync = not force_usage_sync and not self._skip_next_usage_sync

        if force_usage_sync:
            reason = "first refresh after setup" if self._is_first_refresh else "first run, no cache"
            _LOGGER.info(
                "Forcing initial usage sync for contract %s (%s)",
                self.contract_id,
                reason,
            )

            # Start usage sync in the background so account fetching is not blocked.
            self.hass.async_create_task(
                self._async_sync_usage(),
                name=f"usage_sync_{self.contract_id}_initial",
            )
        elif normal_usage_sync:
            _LOGGER.info(
                "Triggering scheduled usage sync for contract %s (updating cache with fresh data)",
                self.contract_id,
            )
            self.hass.async_create_task(
                self._async_sync_usage(),
                name=f"usage_sync_{self.contract_id}_scheduled",
            )
        elif self._skip_next_usage_sync:
            # Honour the explicit one-time skip request when present.
            _LOGGER.debug("Skipping usage sync for contract %s (skip requested)", self.contract_id)
        else:
            # This final branch makes it obvious that no background sync was queued.
            _LOGGER.debug("Usage sync not scheduled for contract %s", self.contract_id)

        # ====================================================================
        # STEP 5: Force one live account fetch if we still have no data or if
        # this is the first refresh after setup.
        # ====================================================================
        if self.data is None or self._is_first_refresh:
            should_fetch_accounts = True
            if self._is_first_refresh:
                _LOGGER.info(
                    "First refresh after setup for contract %s - forcing immediate data fetch",
                    self.contract_id,
                )
                self._is_first_refresh = False

        # ====================================================================
        # STEP 6: If this is not an account-fetch window, reuse current data.
        # ====================================================================
        if not should_fetch_accounts:
            _LOGGER.debug("Not scheduled time for account data, returning cached data")

            # Return current data if we have it; otherwise return a tiny fallback
            # structure so Home Assistant still receives a valid dictionary.
            return self.data or {
                "accountsSummary": [
                    {
                        "id": "",
                        "nickname": "Contact Energy Account",
                        "contracts": [{"contractId": self.contract_id}],
                    }
                ]
            }

        # ====================================================================
        # STEP 7: Attempt the live account refresh.
        # ====================================================================
        try:
            _LOGGER.info("Fetching account information from Contact Energy API (scheduled update)")

            try:
                # First attempt: use the current stored authentication token.
                account_data = await self.api_client.get_accounts()

                # Save the successful payload so restarts can restore it later.
                await self.account_snapshot_cache.save(account_data)

                _LOGGER.debug("Successfully fetched account data")
                return account_data

            except ContactEnergyAuthError as auth_error:
                # =============================================================
                # STEP 7A: Recover from expired or invalid auth tokens only.
                # =============================================================
                error_str = str(auth_error)
                _LOGGER.warning("Initial fetch failed due to auth expiry, re-authenticating: %s", error_str)

                # Without a stored password, re-authentication is impossible.
                if not self.api_client.password:
                    _LOGGER.error("Cannot re-authenticate: password not stored in config entry")
                    raise UpdateFailed(
                        "Password not available for re-authentication. Please reconfigure the integration."
                    )

                try:
                    # Ask the API client to log in again and obtain a fresh token.
                    _LOGGER.debug("Attempting to re-authenticate as %s", self.api_client.email)
                    await self.api_client.authenticate()
                    _LOGGER.debug("Successfully re-authenticated")
                except Exception as auth_err:
                    # If sign-in fails, surface that as a coordinator failure.
                    _LOGGER.error("Re-authentication failed: %s", auth_err)
                    raise UpdateFailed(f"Re-authentication failed: {auth_err}") from auth_err

                try:
                    # Retry the account fetch using the new token.
                    account_data = await self.api_client.get_accounts()
                    await self.account_snapshot_cache.save(account_data)
                    _LOGGER.debug("Successfully fetched account data after re-authentication")

                    # After a successful retry, optionally queue usage sync too.
                    if not self._skip_next_usage_sync:
                        _LOGGER.debug(
                            "Triggering background usage sync for contract %s (after re-auth)",
                            self.contract_id,
                        )
                        self.hass.async_create_task(
                            self._async_sync_usage(),
                            name=f"usage_sync_{self.contract_id}",
                        )
                    else:
                        _LOGGER.debug(
                            "Skipping background usage sync for contract %s after re-auth (skip requested)",
                            self.contract_id,
                        )

                    return account_data

                except Exception as retry_error:
                    # =========================================================
                    # STEP 7B: If account fetch still fails, keep the integration
                    # alive by falling back to usage sync and saved account data.
                    # =========================================================
                    _LOGGER.warning(
                        "Account fetch failed after re-authentication: %s. Proceeding with usage sync only using contract ID %s",
                        retry_error,
                        self.contract_id,
                        exc_info=True,
                    )

                    # Usage syncing can continue because it only needs the contract ID.
                    _LOGGER.debug(
                        "Triggering background usage sync for contract %s (fallback mode)",
                        self.contract_id,
                    )
                    self.hass.async_create_task(
                        self._async_sync_usage(),
                        name=f"usage_sync_{self.contract_id}",
                    )

                    # Prefer returning the last known good account snapshot.
                    if self.data:
                        _LOGGER.warning(
                            "Returning persisted account snapshot for contract %s after API failure",
                            self.contract_id,
                        )
                        return self.data

                    # If nothing valid is saved, return the smallest structure
                    # needed to keep the coordinator and dependent entities alive.
                    return {
                        "accountsSummary": [
                            {
                                "id": "",
                                "nickname": "Unknown Account",
                                "contracts": [{"contractId": self.contract_id}],
                            }
                        ]
                    }

            except ContactEnergyConnectionError as connection_error:
                # Temporary network or timeout issues should not trigger a forced
                # re-authentication loop during Home Assistant startup.
                _LOGGER.warning(
                    "Temporary connection failure fetching accounts for contract %s: %s",
                    self.contract_id,
                    connection_error,
                )

                if self.data:
                    _LOGGER.warning(
                        "Returning persisted account snapshot for contract %s after connection failure",
                        self.contract_id,
                    )
                    return self.data

                return {
                    "accountsSummary": [
                        {
                            "id": "",
                            "nickname": "Unknown Account",
                            "contracts": [{"contractId": self.contract_id}],
                        }
                    ]
                }

        except ContactEnergyApiError as e:
            # Convert integration-specific API errors into Home Assistant's
            # standard coordinator failure type.
            _LOGGER.error(f"API error during data update: {str(e)}")
            raise UpdateFailed(f"API error: {str(e)}") from e

        except Exception as e:
            # Catch anything unexpected so the logs include a full traceback.
            _LOGGER.exception(f"Unexpected error during data update: {e}")
            raise UpdateFailed(f"Unexpected error: {str(e)}") from e

    async def _async_sync_usage(self) -> None:
        """Run usage synchronisation as a background task.

        === WHAT THIS DOES ===
        This helper starts the usage coordinator's sync process and catches any
        exceptions so usage problems do not break account refreshes.

        === FOR NON-CODERS ===
        The account manager asks a second worker to update usage history in the
        background. If that second worker has trouble, the main account update
        still stays alive.
        """
        try:
            # Log the start of the background usage-sync task.
            _LOGGER.debug("Starting background usage sync task for contract %s", self.contract_id)

            # Delegate the actual usage refresh work to the usage coordinator.
            await self.usage_coordinator.async_sync_usage()

            # Record that the background task finished normally.
            _LOGGER.debug("Background usage sync task completed for contract %s", self.contract_id)
        except Exception as e:
            # Log usage-sync failures but do not re-raise them into the account flow.
            _LOGGER.error(
                "Background usage sync failed for contract %s: %s",
                self.contract_id,
                str(e),
                exc_info=True,
            )

    def _calculate_next_account_update_interval(self) -> timedelta:
        """Calculate how long until the next scheduled account-fetch window.

        === WHAT THIS DOES ===
        Account refreshes are meant to happen around 01:00 UTC and 13:00 UTC.
        This method figures out which of those two times comes next and returns
        the time difference from now.

        === FOR NON-CODERS ===
        Imagine checking a timetable with two departures each day. This method
        answers, "How long until the next departure?"
        """
        # Capture the current UTC time so all later comparisons use one reference.
        now = datetime.now(timezone.utc)

        # We'll build a list of candidate future update times here.
        next_times = []

        # Check both scheduled update hours for today.
        for hour in [1, 13]:
            next_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)

            # If today's scheduled time already passed, move that candidate to tomorrow.
            if next_time <= now:
                next_time = next_time + timedelta(days=1)

            # Store each candidate so we can choose the earliest one later.
            next_times.append(next_time)

        # Pick whichever future candidate occurs first.
        next_update = min(next_times)

        # Convert that future moment into a wait duration.
        interval = next_update - now

        _LOGGER.debug(
            "Next account update scheduled for %s (in %s)",
            next_update.isoformat(),
            interval,
        )

        # Return the computed wait time to the caller.
        return interval

    def _should_fetch_account_data_now(self) -> bool:
        """Decide whether the current time is inside an account-fetch window.

        === WHAT THIS DOES ===
        This method checks whether the current UTC time is within 30 minutes of
        the two preferred daily account-refresh times: 01:00 and 13:00.

        === FOR NON-CODERS ===
        Instead of allowing account refreshes at every hourly tick, the system
        keeps account calls focused around two expected windows each day.
        This helps avoid unnecessary API calls.
        """
        # Use the current UTC time as the comparison point.
        now = datetime.now(timezone.utc)

        # Check each allowed target hour one at a time.
        for target_hour in [1, 13]:
            # Build today's version of the target time, such as 01:00 UTC.
            target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

            # Measure the absolute time gap between now and that target time.
            time_diff = abs((now - target_time).total_seconds())

            # If we are inside the 30-minute window, a fetch is allowed now.
            if time_diff <= 30 * 60:
                return True

        # If neither target window matched, account data should not be fetched now.
        return False
