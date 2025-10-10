"""Data update coordinator for Contact Energy."""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

from .api import ContactEnergyApi, ContactEnergyApiError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, STORAGE_KEY_LAST_DOWNLOAD, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class ContactEnergyCoordinator(DataUpdateCoordinator):
    """Contact Energy data update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ContactEnergyApi,
        email: str,
        usage_days: int,
        account_id: str,
        contract_id: str,
        contract_icp: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        
        self.api = api
        self.email = email
        self.usage_days = usage_days
        self.account_id = account_id
        self.contract_id = contract_id
        self.contract_icp = contract_icp
        
        # Storage for tracking downloaded data
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{contract_id}")
        self._last_download_date: Optional[date] = None
        self._storage_data: Dict[str, Any] = {}

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        # Load storage data
        self._storage_data = await self._store.async_load() or {}
        
        # Get last download date
        last_download_str = self._storage_data.get(STORAGE_KEY_LAST_DOWNLOAD)
        if last_download_str:
            try:
                self._last_download_date = datetime.fromisoformat(last_download_str).date()
                _LOGGER.debug("Last download date loaded: %s", self._last_download_date)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid last download date format, resetting")
                self._last_download_date = None

    async def _save_last_download_date(self, download_date: date) -> None:
        """Save the last download date to storage."""
        self._last_download_date = download_date
        self._storage_data[STORAGE_KEY_LAST_DOWNLOAD] = download_date.isoformat()
        await self._store.async_save(self._storage_data)
        _LOGGER.debug("Saved last download date: %s", download_date)

    def _get_missing_date_range(self) -> tuple[date, date]:
        """Calculate the date range that needs to be downloaded."""
        end_date = date.today() - timedelta(days=1)  # Yesterday (data delay)
        
        if self._last_download_date is None:
            # First run - download initial usage_days
            start_date = end_date - timedelta(days=self.usage_days - 1)
            _LOGGER.info("First run: downloading %s days from %s to %s", 
                        self.usage_days, start_date, end_date)
        else:
            # Subsequent runs - only download missing days
            start_date = self._last_download_date + timedelta(days=1)
            if start_date > end_date:
                # No new data to download
                _LOGGER.debug("No new data to download (last: %s, available: %s)", 
                            self._last_download_date, end_date)
                return start_date, start_date - timedelta(days=1)  # Invalid range
            
            days_to_download = (end_date - start_date).days + 1
            _LOGGER.info("Incremental download: %s days from %s to %s", 
                        days_to_download, start_date, end_date)
        
        return start_date, end_date

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Contact Energy."""
        try:
            # Ensure coordinator setup is complete
            if self._last_download_date is None and not hasattr(self, '_setup_complete'):
                await self._async_setup()
                self._setup_complete = True

            # Get account data
            account_data = await self.api.get_accounts()
            if not account_data:
                raise UpdateFailed("Failed to fetch account data")

            # Calculate date range for usage data
            start_date, end_date = self._get_missing_date_range()
            
            # Initialize usage data structure
            usage_data = {
                "total_energy": 0.0,        # Total kWh (cumulative)
                "total_cost": 0.0,          # Total cost (cumulative) 
                "total_free_energy": 0.0,   # Total free kWh (cumulative)
                "current_energy": 0.0,      # Current period kWh 
                "current_cost": 0.0,        # Current period cost
                "current_free_energy": 0.0, # Current period free kWh
                "new_data_points": [],      # New hourly data for statistics
                "last_updated": datetime.now(),
            }

            # Only fetch usage data if there are missing days
            if start_date <= end_date:
                _LOGGER.info("Fetching usage data from %s to %s", start_date, end_date)
                
                current_date = start_date
                total_energy = 0.0
                total_cost = 0.0 
                total_free_energy = 0.0
                new_data_points = []
                
                while current_date <= end_date:
                    try:
                        daily_data = await self.api.get_usage_data(current_date)
                        
                        if daily_data and isinstance(daily_data, list):
                            for point in daily_data:
                                try:
                                    energy = float(point.get("value", 0))
                                    cost = float(point.get("dollarValue", 0))
                                    offpeak_value = str(point.get("offpeakValue", "0.00"))
                                    
                                    # Parse timestamp
                                    timestamp_str = point.get("date", "")
                                    try:
                                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                    except ValueError:
                                        timestamp = datetime.combine(current_date, datetime.min.time())
                                    
                                    # Classify as free or regular energy
                                    if offpeak_value != "0.00":
                                        # Free energy
                                        total_free_energy += energy
                                        new_data_points.append({
                                            "timestamp": timestamp,
                                            "energy": 0.0,
                                            "cost": 0.0,
                                            "free_energy": energy,
                                            "type": "free"
                                        })
                                    else:
                                        # Regular energy
                                        total_energy += energy
                                        total_cost += cost
                                        new_data_points.append({
                                            "timestamp": timestamp,
                                            "energy": energy,
                                            "cost": cost,
                                            "free_energy": 0.0,
                                            "type": "regular"
                                        })
                                        
                                except (ValueError, TypeError, KeyError) as err:
                                    _LOGGER.warning("Error parsing usage point: %s", err)
                                    continue
                                    
                        else:
                            _LOGGER.debug("No usage data for %s", current_date)
                            
                    except ContactEnergyApiError as err:
                        _LOGGER.warning("Failed to fetch data for %s: %s", current_date, err)
                        
                    current_date += timedelta(days=1)
                
                # Update usage data
                usage_data.update({
                    "current_energy": total_energy,
                    "current_cost": total_cost,
                    "current_free_energy": total_free_energy,
                    "new_data_points": new_data_points,
                })
                
                # Save progress if we got new data
                if new_data_points:
                    await self._save_last_download_date(end_date)
                    _LOGGER.info("Successfully downloaded %s new data points", len(new_data_points))
            
            return {
                "account": account_data,
                "usage": usage_data,
                "last_update": datetime.now(),
            }
            
        except ContactEnergyApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during data update")
            raise UpdateFailed(f"Unexpected error: {err}") from err