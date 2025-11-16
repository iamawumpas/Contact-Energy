"""Contact Energy sensor platform."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers.typing import StateType
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_add_external_statistics, get_last_statistics, statistics_during_period
from homeassistant.const import UnitOfEnergy, EVENT_HOMEASSISTANT_STARTED, CONF_EMAIL
import random
import re

from .const import (
    DOMAIN,
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_CONTRACT_ICP,
    CONF_USAGE_DAYS,
    CONF_USAGE_MONTHS,
    months_to_days,
)
from .coordinator import ContactEnergyCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Contact Energy sensor entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    account_id = entry.data[CONF_ACCOUNT_ID]
    contract_id = entry.data[CONF_CONTRACT_ID]
    contract_icp = entry.data[CONF_CONTRACT_ICP]
    # Prefer months setting; fall back to legacy days
    if CONF_USAGE_MONTHS in entry.data:
        usage_days = months_to_days(entry.data.get(CONF_USAGE_MONTHS))
    else:
        usage_days = entry.data.get(CONF_USAGE_DAYS, 30)

    # Create usage sensor for Energy Dashboard with progress tracking
    usage_sensor = ContactEnergyUsageSensor(
        coordinator,
        account_id,
        contract_id,
        contract_icp,
        usage_days,
    )
    
    # Create progress sensor
    progress_sensor = ContactEnergyDownloadProgressSensor(
        coordinator,
        contract_icp,
    )
    
    # Link progress sensor to usage sensor
    usage_sensor.set_progress_sensor(progress_sensor)
    
    entities = [usage_sensor, progress_sensor]

    # Add account information sensors (read from coordinator account_details)
    entities.extend([
        ContactEnergyAccountBalanceSensor(coordinator, contract_icp),
        ContactEnergyNextBillDateSensor(coordinator, contract_icp),
        ContactEnergyCustomerNameSensor(coordinator, contract_icp),
        ContactEnergyPlanNameSensor(coordinator, contract_icp),
        ContactEnergyAccountNumberSensor(coordinator, contract_icp),
        ContactEnergyEmailSensor(coordinator, contract_icp),
        ContactEnergyServiceAddressSensor(coordinator, contract_icp),
        ContactEnergyMeterSerialSensor(coordinator, contract_icp),
        ContactEnergyNextReadDateSensor(coordinator, contract_icp),
        ContactEnergyLastReadDateSensor(coordinator, contract_icp),
        ContactEnergyDailyChargeRateSensor(coordinator, contract_icp),
        ContactEnergyPeakRateSensor(coordinator, contract_icp),
        ContactEnergyOffPeakRateSensor(coordinator, contract_icp),
        ContactEnergyFreeHoursSensor(coordinator, contract_icp),
        ContactEnergyLastPaymentSensor(coordinator, contract_icp),
        ContactEnergyEstimatedNextBillSensor(coordinator, contract_icp),
        # Phase 1: Enhanced sensors
        ContactEnergyPaymentHistorySensor(coordinator, contract_icp),
        ContactEnergyFullAddressSensor(coordinator, contract_icp),
        ContactEnergyMeterRegisterSensor(coordinator, contract_icp),
        ContactEnergyContractDetailsSensor(coordinator, contract_icp),
        # Phase 2: Analytics sensors
        ContactEnergyAverageDailyUsage7DaysSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyAverageDailyUsage30DaysSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyUsageTrendSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyCostPerKwhSensor(coordinator, account_id, contract_id, contract_icp),
        # Phase 3: Forecasting sensor
        ContactEnergyForecastDailyUsageSensor(coordinator, account_id, contract_id, contract_icp),
    ])

    # Add convenience usage/cost sensors
    convenience_entities = [
        ContactEnergyTodayUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyYesterdayUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLast7DaysUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLast30DaysUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyCurrentMonthUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLastMonthUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyTodayCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyYesterdayCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyCurrentMonthCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyLastMonthCostSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyTodayFreeUsageSensor(coordinator, account_id, contract_id, contract_icp),
        ContactEnergyYesterdayFreeUsageSensor(coordinator, account_id, contract_id, contract_icp),
    ]

    # Add charting sensors for ApexCharts
    # Build statistic ID from contract_icp
    safe_icp = re.sub(r'[^a-z0-9_]', '_', contract_icp.lower())
    if re.match(r'^[0-9]', safe_icp):
        safe_icp = f"icp_{safe_icp}"
    kwh_stat_id = f"{DOMAIN}:energy_{safe_icp}"
    free_stat_id = f"{DOMAIN}:free_energy_{safe_icp}"

    chart_entities = [
        ContactEnergyChartHourlySensor(hass, kwh_stat_id, contract_icp),
        ContactEnergyChartDailySensor(hass, kwh_stat_id, contract_icp),
        ContactEnergyChartHourlyFreeSensor(hass, free_stat_id, contract_icp),
        ContactEnergyChartDailyFreeSensor(hass, free_stat_id, contract_icp),
        ContactEnergyChartMonthlySensor(hass, kwh_stat_id, contract_icp),
        ContactEnergyChartMonthlyFreeSensor(hass, free_stat_id, contract_icp),
    ]

    # Register all entities in a single call
    all_entities = entities + convenience_entities + chart_entities
    async_add_entities(all_entities, False)



class ContactEnergyUsageSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Contact Energy usage tracking with Energy Dashboard statistics."""

    def __init__(
        self,
        coordinator: ContactEnergyCoordinator,
        account_id: str,
        contract_id: str,
        contract_icp: str,
        usage_days: int,
    ) -> None:
        """Initialize the usage sensor."""
        super().__init__(coordinator)
        
        self._account_id = account_id
        self._contract_id = contract_id
        self._contract_icp = contract_icp
        self._usage_days = usage_days
        self._state = 0.0
        self._last_usage_update: Optional[datetime] = None
        self._download_task: Optional[asyncio.Task] = None
        self._progress_sensor: Optional["ContactEnergyDownloadProgressSensor"] = None

        # Entity attributes
        self._attr_name = f"Contact Energy Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:meter-electric"

    def set_progress_sensor(self, progress_sensor: "ContactEnergyDownloadProgressSensor") -> None:
        """Set reference to progress sensor for download updates."""
        self._progress_sensor = progress_sensor

    async def trigger_download(self) -> None:
        """Trigger a manual download of usage data."""
        _LOGGER.info("Manual download triggered for %s", self._contract_icp)
        
        # Cancel any existing download task
        if self._download_task and not self._download_task.done():
            _LOGGER.warning("Cancelling existing download task before starting new one")
            self._download_task.cancel()
            try:
                await self._download_task
            except asyncio.CancelledError:
                pass
        
        # Start new download task
        self._download_task = self.hass.async_create_task(self._download_usage_data())

    @property
    def native_value(self) -> float:
        """Return the current total usage."""
        return self._state

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
            "sw_version": "1.0",
        }

    async def async_added_to_hass(self) -> None:
        """Called when entity is added to Home Assistant."""
        await super().async_added_to_hass()

        async def _kickoff_download(_event=None) -> None:
            # Add small delay to allow coordinator to complete initial fetch
            # but start immediately if no prior download has occurred
            delay = 2.0  # 2 seconds to let coordinator initialize
            
            try:
                await asyncio.sleep(delay)
            except Exception:  # noqa: BLE001
                pass
            _LOGGER.info("Starting initial usage data download for %s", self._contract_icp)
            self._download_task = self.hass.async_create_task(self._download_usage_data())

        if getattr(self.hass, "is_running", False):
            await _kickoff_download()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _kickoff_download)
    async def async_will_remove_from_hass(self) -> None:
        """Called when entity is about to be removed from Home Assistant."""
        if self._download_task and not self._download_task.done():
            self._download_task.cancel()
        await super().async_will_remove_from_hass()

    async def async_update(self) -> None:
        """Update usage data and statistics (called every 8 hours)."""
        now = datetime.now()
        
        # Only update if it's been 8+ hours since last update
        if (self._last_usage_update and 
            (now - self._last_usage_update) < timedelta(hours=8)):
            _LOGGER.debug("Skipping usage update, last update was recent")
            return

        _LOGGER.debug("Updating usage data - 8 hour interval update")
        
        try:
            await self._download_usage_data()
            self._last_usage_update = now
        except Exception as error:
            _LOGGER.error("Failed to update usage statistics: %s", error)

    async def _download_usage_data(self) -> None:
        """Download usage data and update Home Assistant statistics."""
        try:
            _LOGGER.info("Starting usage data download for up to %s days (missing only)", self._usage_days)

            # Calculate default date range
            today = datetime.now().date()
            start_date = today - timedelta(days=self._usage_days - 1)
            end_date = today

            # Build statistic IDs and determine last recorded entries
            import re as _re
            safe_icp = _re.sub(r'[^a-z0-9_]', '_', self._contract_icp.lower())
            if _re.match(r'^[0-9]', safe_icp):
                safe_icp = f"icp_{safe_icp}"
            kwh_stat_id = f"{DOMAIN}:energy_{safe_icp}"
            dollar_stat_id = f"{DOMAIN}:cost_{safe_icp}"
            free_stat_id = f"{DOMAIN}:free_energy_{safe_icp}"

            base_kwh_sum = 0.0
            base_dollar_sum = 0.0
            base_free_sum = 0.0

            try:
                # get_last_statistics is synchronous; run in executor
                last_stats = await self.hass.async_add_executor_job(
                    get_last_statistics, self.hass, 1, [kwh_stat_id, dollar_stat_id, free_stat_id]
                )
                # Determine the next start date from kWh series (canonical)
                if isinstance(last_stats, dict) and kwh_stat_id in last_stats and last_stats[kwh_stat_id]:
                    last_entry = last_stats[kwh_stat_id][0]
                    last_start = last_entry.get("start")
                    if isinstance(last_start, datetime):
                        candidate = last_start.date() + timedelta(days=1)
                        if candidate > start_date:
                            start_date = candidate
                    try:
                        base_kwh_sum = float(last_entry.get("sum") or 0.0)
                    except (TypeError, ValueError):
                        base_kwh_sum = 0.0
                if isinstance(last_stats, dict) and dollar_stat_id in last_stats and last_stats[dollar_stat_id]:
                    try:
                        base_dollar_sum = float(last_stats[dollar_stat_id][0].get("sum") or 0.0)
                    except (TypeError, ValueError):
                        base_dollar_sum = 0.0
                if isinstance(last_stats, dict) and free_stat_id in last_stats and last_stats[free_stat_id]:
                    try:
                        base_free_sum = float(last_stats[free_stat_id][0].get("sum") or 0.0)
                    except (TypeError, ValueError):
                        base_free_sum = 0.0
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("Could not determine last statistics entries: %s", e)

            # If nothing to do (already up to date), exit early
            if start_date > end_date:
                _LOGGER.info("Statistics already up to date through %s; no download needed", end_date)
                if self._progress_sensor:
                    self._progress_sensor.update_progress("complete", days_completed=0, days_total=0)
                return

            # Calculate total days to download
            total_days = (end_date - start_date).days + 1
            
            # Initialize progress sensor and notification
            if self._progress_sensor:
                self._progress_sensor.update_progress(
                    "downloading",
                    current_date=start_date,
                    start_date=start_date,
                    end_date=end_date,
                    days_completed=0,
                    days_total=total_days
                )
            
            # Show persistent notification for large downloads (> 365 days)
            notification_id = f"{DOMAIN}_download_{self._contract_icp}"
            if total_days > 365:
                from homeassistant.components.persistent_notification import async_create
                async_create(
                    self.hass,
                    f"Downloading {total_days} days of usage data. This may take 10-15 minutes...\n\n"
                    f"Progress: 0% (0/{total_days} days)\n"
                    f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    title="Contact Energy - Downloading Usage Data",
                    notification_id=notification_id
                )
            
            _LOGGER.info("Downloading %d days of usage data from %s to %s", total_days, start_date, end_date)

            # Initialize statistics lists
            kwh_statistics = []
            dollar_statistics = []
            free_kwh_statistics = []
            
            # Running totals for cumulative statistics
            kwh_running_sum = base_kwh_sum
            dollar_running_sum = base_dollar_sum
            free_kwh_running_sum = base_free_sum
            currency = 'NZD'
            
            # Download data day by day
            current_date = start_date
            while current_date <= end_date:
                try:
                    date_str = current_date.strftime("%Y-%m-%d")
                    _LOGGER.debug("Fetching usage data for %s", date_str)
                    
                    response = await self.coordinator.api.async_get_usage(
                        str(current_date.year),
                        str(current_date.month),
                        str(current_date.day),
                        self._account_id,
                        self._contract_id,
                    )

                    # Only process if we got actual data points
                    if response and isinstance(response, list) and len(response) > 0:
                        for point in response:
                            if point.get('currency') and currency != point['currency']:
                                currency = point['currency']

                            # Safely convert values
                            value_float = self._safe_float(point.get("value"))
                            dollar_value_float = self._safe_float(point.get("dollarValue"))
                            offpeak_value_str = str(point.get("offpeakValue", "0.00"))

                            # If offpeak value is not '0.00', the energy is free
                            if offpeak_value_str == "0.00":
                                kwh_running_sum += value_float
                                dollar_running_sum += dollar_value_float
                            else:
                                free_kwh_running_sum += value_float

                            # Parse date safely
                            try:
                                date_obj = datetime.strptime(point["date"], "%Y-%m-%dT%H:%M:%S.%f%z")
                            except (ValueError, TypeError, KeyError):
                                date_obj = datetime.combine(current_date, datetime.min.time())

                            # Add to statistics (cumulative)
                            kwh_statistics.append(StatisticData(start=date_obj, sum=kwh_running_sum))
                            dollar_statistics.append(StatisticData(start=date_obj, sum=dollar_running_sum))
                            free_kwh_statistics.append(StatisticData(start=date_obj, sum=free_kwh_running_sum))

                    else:
                        _LOGGER.debug("No data available for %s (may not be released yet)", date_str)

                except Exception as error:
                    error_type = type(error).__name__
                    if "timeout" in str(error).lower() or "504" in str(error):
                        _LOGGER.warning("API timeout for %s - Contact Energy servers may be slow: %s", 
                                      current_date.strftime("%Y-%m-%d"), error)
                    else:
                        _LOGGER.warning("Failed to fetch data for %s (%s): %s", 
                                      current_date.strftime("%Y-%m-%d"), error_type, error)
                    # Continue with next date even if this one failed

                # Move to next date
                current_date += timedelta(days=1)
                
                # Update progress every 10 days or on final day
                days_completed = (current_date - start_date).days
                if days_completed % 10 == 0 or current_date > end_date:
                    if self._progress_sensor:
                        self._progress_sensor.update_progress(
                            "downloading",
                            current_date=current_date,
                            start_date=start_date,
                            end_date=end_date,
                            days_completed=min(days_completed, total_days),
                            days_total=total_days
                        )
                    
                    # Update notification for large downloads
                    if total_days > 365 and days_completed % 50 == 0:
                        from homeassistant.components.persistent_notification import async_create
                        progress_pct = int((days_completed / total_days) * 100)
                        async_create(
                            self.hass,
                            f"Downloading {total_days} days of usage data. This may take 10-15 minutes...\n\n"
                            f"Progress: {progress_pct}% ({days_completed}/{total_days} days)\n"
                            f"Current: {current_date.strftime('%Y-%m-%d')}",
                            title="Contact Energy - Downloading Usage Data",
                            notification_id=notification_id
                        )
                
                # Small delay between requests to be nice to the API
                await asyncio.sleep(0.5)

            # Update Home Assistant statistics for missing period (even if partial)
            if kwh_statistics:
                await self._add_statistics(kwh_statistics, dollar_statistics, free_kwh_statistics, currency, free_kwh_running_sum)
                _LOGGER.info("Usage data download completed. Added %d statistics entries, Total kWh: %.2f", 
                           len(kwh_statistics), kwh_running_sum)
            else:
                _LOGGER.warning("No usage data retrieved - all API requests may have failed")
            
            # Mark progress as complete
            if self._progress_sensor:
                self._progress_sensor.update_progress(
                    "complete",
                    current_date=end_date,
                    start_date=start_date,
                    end_date=end_date,
                    days_completed=total_days,
                    days_total=total_days
                )
            
            # Dismiss notification
            if total_days > 365:
                from homeassistant.components.persistent_notification import async_dismiss
                async_dismiss(self.hass, notification_id)
            
            # Update sensor state to latest total
            self._state = kwh_running_sum

        except Exception as error:
            _LOGGER.exception("Usage data download failed: %s", error)
            # Mark progress as failed
            if self._progress_sensor:
                self._progress_sensor.update_progress("error", days_completed=0, days_total=0)

    async def _add_statistics(
        self, 
        kwh_stats: list, 
        dollar_stats: list, 
        free_kwh_stats: list, 
        currency: str,
        free_kwh_total: float = 0
    ) -> None:
        """Add statistics to Home Assistant."""
        if not kwh_stats:
            _LOGGER.debug("No statistics to add")
            return


        import re
        safe_icp = re.sub(r'[^a-z0-9_]', '_', self._contract_icp.lower())
        if re.match(r'^[0-9]', safe_icp):
            safe_icp = f"icp_{safe_icp}"

        # Main electricity consumption for Energy Dashboard
        kwh_stat_id = f"{DOMAIN}:energy_{safe_icp}"
        kwh_metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=f"Contact Energy - Electricity ({self._contract_icp})",
            source=DOMAIN,
            statistic_id=kwh_stat_id,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        )
        async_add_external_statistics(self.hass, kwh_metadata, kwh_stats)

        # Electricity cost
        if dollar_stats:
            dollar_stat_id = f"{DOMAIN}:cost_{safe_icp}"
            dollar_metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"Contact Energy - Electricity Cost ({self._contract_icp})",
                source=DOMAIN,
                statistic_id=dollar_stat_id,
                unit_of_measurement=currency,
            )
            async_add_external_statistics(self.hass, dollar_metadata, dollar_stats)

        # Free electricity (if any) - only add if we have meaningful data
        if free_kwh_stats and free_kwh_total > 0:
            free_stat_id = f"{DOMAIN}:free_energy_{safe_icp}"
            free_kwh_metadata = StatisticMetaData(
                has_mean=False,
                has_sum=True,
                name=f"Contact Energy - Free Electricity ({self._contract_icp})",
                source=DOMAIN,
                statistic_id=free_stat_id,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            )
            async_add_external_statistics(self.hass, free_kwh_metadata, free_kwh_stats)

        _LOGGER.debug("Added statistics to Home Assistant")

    @staticmethod
    def _safe_float(value: Any) -> float:
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0


# -----------------------------
# Download Progress Sensor
# -----------------------------

class ContactEnergyDownloadProgressSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing usage data download progress.
    
    Compatible with timer-bar-card for visual progress tracking.
    """
    
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        """Initialize the progress sensor."""
        super().__init__(coordinator)
        self._contract_icp = contract_icp
        self._state: Optional[str] = "idle"  # State for timer-bar-card: idle/active/paused
        self._status = "idle"  # Internal status
        self._current_date: Optional[str] = None
        self._start_date: Optional[str] = None
        self._end_date: Optional[str] = None
        self._days_completed = 0
        self._days_total = 0
        self._download_start_time: Optional[str] = None  # ISO timestamp when download started
        self._estimated_end_time: Optional[str] = None  # ISO timestamp when download will finish
        
        # Entity attributes
        self._attr_name = f"Contact Energy Download Progress ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_download_progress"
        self._attr_icon = "mdi:download"
        self._attr_native_unit_of_measurement = "%"
    
    @property
    def native_value(self) -> Optional[str]:
        """Return state for timer-bar-card compatibility.
        
        Returns 'idle', 'active', or 'paused' for timer-bar-card.
        """
        if self._status == "downloading":
            return "active"
        elif self._status == "idle":
            return "idle"
        elif self._status == "complete":
            return "idle"
        elif self._status == "error":
            return "idle"
        return "idle"
    
    @property
    def icon(self) -> str:
        """Return icon based on status."""
        if self._status == "downloading":
            return "mdi:download"
        elif self._status == "complete":
            return "mdi:check-circle"
        return "mdi:information"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes for timer-bar-card."""
        attrs = {
            "status": self._status,
            "current_date": self._current_date,
            "start_date": self._start_date,
            "end_date": self._end_date,
            "days_completed": self._days_completed,
            "days_total": self._days_total,
            "percentage": min(100, int((self._days_completed / self._days_total) * 100)) if self._days_total > 0 else 0,
        }
        
        # Add timer-bar-card compatible attributes
        if self._download_start_time:
            attrs["start_time"] = self._download_start_time
        if self._estimated_end_time:
            attrs["end_time"] = self._estimated_end_time
        
        # Calculate duration in seconds for timer-bar-card
        if self._download_start_time and self._estimated_end_time:
            from datetime import datetime
            try:
                start = datetime.fromisoformat(self._download_start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(self._estimated_end_time.replace('Z', '+00:00'))
                duration_seconds = int((end - start).total_seconds())
                attrs["duration"] = f"{duration_seconds // 3600}:{(duration_seconds % 3600) // 60:02d}:{duration_seconds % 60:02d}"
            except (ValueError, AttributeError):
                pass
        
        return attrs
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }
    
    def update_progress(
        self,
        status: str,
        current_date: Optional[date] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days_completed: int = 0,
        days_total: int = 0,
    ) -> None:
        """Update progress sensor state and calculate timer-bar-card attributes."""
        from datetime import datetime, timezone
        
        self._status = status
        self._current_date = current_date.isoformat() if current_date else None
        self._start_date = start_date.isoformat() if start_date else None
        self._end_date = end_date.isoformat() if end_date else None
        self._days_completed = days_completed
        self._days_total = days_total
        
        # Set download start time when download begins
        if status == "downloading" and not self._download_start_time:
            self._download_start_time = datetime.now(timezone.utc).isoformat()
        
        # Calculate estimated end time based on progress
        if status == "downloading" and days_total > 0 and days_completed > 0:
            # Calculate elapsed time and estimate total duration
            if self._download_start_time:
                start_time = datetime.fromisoformat(self._download_start_time.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                elapsed_seconds = (now - start_time).total_seconds()
                
                # Estimate time per day and calculate remaining time
                if elapsed_seconds > 0:
                    seconds_per_day = elapsed_seconds / days_completed
                    remaining_days = days_total - days_completed
                    remaining_seconds = remaining_days * seconds_per_day
                    
                    from datetime import timedelta
                    estimated_end = now + timedelta(seconds=remaining_seconds)
                    self._estimated_end_time = estimated_end.isoformat()
        
        # Clear timestamps when idle or complete
        if status in ("idle", "complete", "error"):
            if status != "downloading":
                self._download_start_time = None
                self._estimated_end_time = None
        
        # Update internal state for compatibility
        if days_total > 0:
            self._state = "active" if status == "downloading" else "idle"
        else:
            self._state = "idle"
        
        # Update HA state
        self.async_write_ha_state()


# -----------------------------
# Account information sensors
# -----------------------------

class ContactEnergyAccountSensorBase(CoordinatorEntity, SensorEntity):
    """Base for account info sensors that read from coordinator data."""

    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator)
        self._contract_icp = contract_icp

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is only available if coordinator has successfully fetched data at least once
        return self.coordinator.last_update_success and self.coordinator.data is not None

    def _get_account_data(self) -> dict[str, Any]:
        # Only try to access data if coordinator has completed at least one update
        if not self.coordinator.last_update_success or self.coordinator.data is None:
            return {}
        
        data = self.coordinator.data
        account_details = data.get("account_details", {}) if isinstance(data, dict) else {}
        return account_details

    def _get_contract_data(self) -> dict[str, Any]:
        account = self._get_account_data()
        contracts = account.get("contracts", []) or []
        
        for c in contracts:
            contract_icp = c.get("icp")
            if contract_icp == self._contract_icp:
                return c
        
        # Only log warning if we have account data but no matching contract
        if account:
            _LOGGER.warning("No matching contract found for ICP %s. Available contracts: %s", 
                           self._contract_icp, [c.get("icp") for c in contracts])
        return {}


class ContactEnergyAccountBalanceSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Account Balance ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_balance"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self) -> float | None:
        account_data = self._get_account_data()
        # API structure: accountDetail.accountBalance.currentBalance
        account_balance = account_data.get("accountBalance", {})
        bal = account_balance.get("currentBalance")
        try:
            return float(bal) if bal is not None else None
        except (ValueError, TypeError):
            return None


class ContactEnergyNextBillDateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Next Bill Date ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_next_bill_date"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> date | None:
        account_data = self._get_account_data()
        next_bill = account_data.get("nextBill", {})
        date_str = next_bill.get("date")
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, "%d %b %Y").date()
                return parsed_date
            except (ValueError, TypeError):
                _LOGGER.warning("Could not parse next bill date: %s", date_str)
                return None
        return None


class ContactEnergyCustomerNameSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Customer Name ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_customer_name"
        self._attr_icon = "mdi:account"

    @property
    def native_value(self) -> str | None:
        account_data = self._get_account_data()
        # API structure: accountDetail.nickname (seems to be the account name)
        return account_data.get("nickname")


class ContactEnergyPlanNameSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Plan Name ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_plan_name"
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> str | None:
        # Plan details don't seem to be in the basic account response
        # May need a separate API call or different endpoint
        contract = self._get_contract_data()
        contract_type = contract.get("contractTypeLabel")  # "Electricity"
        if contract_type:
            return f"{contract_type} Contract"
        return None


class ContactEnergyAccountNumberSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Account Number ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_account_number"
        self._attr_icon = "mdi:identifier"

    @property
    def native_value(self) -> str | None:
        account_data = self._get_account_data()
        # API structure: accountDetail.id (this is the account number)
        return account_data.get("id")


class ContactEnergyEmailSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Email ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_email"
        self._attr_icon = "mdi:email"

    @property
    def native_value(self) -> str | None:
        # Email comes from the config entry (login credentials), not the API
        return self.coordinator.config_entry.data.get(CONF_EMAIL)


class ContactEnergyServiceAddressSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Service Address ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_service_address"
        self._attr_icon = "mdi:home"

    @property
    def native_value(self) -> str | None:
        contract = self._get_contract_data()
        # API structure: contracts[].premise.supplyAddress.shortForm
        premise = contract.get("premise", {})
        supply_address = premise.get("supplyAddress", {})
        return supply_address.get("shortForm")


class ContactEnergyMeterSerialSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Meter Serial ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_meter_serial"
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self) -> str | None:
        contract = self._get_contract_data()
        # API structure: contracts[].devices[0].serialNumber
        devices = contract.get("devices", [])
        if devices:
            return devices[0].get("serialNumber")
        return None


class ContactEnergyNextReadDateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Next Read Date ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_next_read_date"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-arrow-right"

    @property
    def native_value(self) -> date | None:
        contract = self._get_contract_data()
        devices = contract.get("devices", [])
        if devices:
            date_str = devices[0].get("nextMeterReadDate")
            if date_str:
                try:
                    parsed_date = datetime.strptime(date_str, "%d %b %Y").date()
                    return parsed_date
                except (ValueError, TypeError):
                    _LOGGER.warning("Could not parse next read date: %s", date_str)
                    return None
        return None


class ContactEnergyLastReadDateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Last Read Date ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_read_date"
        self._attr_device_class = SensorDeviceClass.DATE
        self._attr_icon = "mdi:calendar-check"

    @property
    def native_value(self) -> date | None:
        contract = self._get_contract_data()
        devices = contract.get("devices", [])
        if devices and devices[0].get("registers"):
            registers = devices[0].get("registers", [])
            if registers:
                date_str = registers[0].get("previousMeterReadingDate")
                if date_str and date_str != "Invalid date":
                    try:
                        parsed_date = datetime.strptime(date_str, "%d %b %Y").date()
                        return parsed_date
                    except (ValueError, TypeError):
                        _LOGGER.warning("Could not parse last read date: %s", date_str)
                        return None
        return None


class ContactEnergyDailyChargeRateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Daily Charge Rate ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_daily_charge_rate"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self) -> float | None:
        daily = self._get_contract_data().get("planDetails", {}).get("dailyCharge")
        try:
            return float(daily) if daily is not None else None
        except (ValueError, TypeError):
            return None


class ContactEnergyPeakRateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Peak Rate ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_peak_rate"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD/kWh"
        self._attr_icon = "mdi:trending-up"

    @property
    def native_value(self) -> float | None:
        peak = self._get_contract_data().get("planDetails", {}).get("unitRates", {}).get("peak")
        try:
            return float(peak) if peak is not None else None
        except (ValueError, TypeError):
            return None


class ContactEnergyOffPeakRateSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Off Peak Rate ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_off_peak_rate"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD/kWh"
        self._attr_icon = "mdi:trending-down"

    @property
    def native_value(self) -> float | None:
        offp = self._get_contract_data().get("planDetails", {}).get("unitRates", {}).get("offPeak")
        try:
            return float(offp) if offp is not None else None
        except (ValueError, TypeError):
            return None


class ContactEnergyFreeHoursSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Free Hours ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_free_hours"
        self._attr_icon = "mdi:clock-time-eight"

    @property
    def native_value(self) -> str | None:
        return self._get_contract_data().get("planDetails", {}).get("unitRates", {}).get("freeHours")


class ContactEnergyLastPaymentSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Last Payment ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_payment"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:credit-card"

    @property
    def native_value(self) -> float | None:
        account_data = self._get_account_data()
        # API structure: accountDetail.payments[0].amount (but it's a string like "$379.18")
        payments = account_data.get("payments", []) or []
        if payments:
            amt_str = payments[0].get("amount", "")
            # Remove $ and convert to float
            try:
                amt_clean = amt_str.replace("$", "").replace(",", "")
                return float(amt_clean) if amt_clean else None
            except (ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        account_data = self._get_account_data()
        payments = account_data.get("payments", []) or []
        if payments:
            return {
                "date": payments[0].get("date"),
                "payment_method": account_data.get("paymentMethod"),
            }
        return {}


class ContactEnergyEstimatedNextBillSensor(ContactEnergyAccountSensorBase):
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Estimated Next Bill ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_estimated_next_bill"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:receipt"

    @property
    def native_value(self) -> float | None:
        account_data = self._get_account_data()
        # API structure: accountDetail.nextBill.amount
        next_bill = account_data.get("nextBill", {})
        amt = next_bill.get("amount")
        try:
            return float(amt) if amt is not None else None
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        account_data = self._get_account_data()
        next_bill = account_data.get("nextBill", {})
        if next_bill:
            return {"bill_date": next_bill.get("date")}
        return {}


# -----------------------------------------
# Phase 1: Enhanced account sensors
# -----------------------------------------

class ContactEnergyPaymentHistorySensor(ContactEnergyAccountSensorBase):
    """Sensor showing payment history with last 5 payments as attributes."""
    
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Payment History ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_payment_history"
        self._attr_icon = "mdi:history"

    @property
    def native_value(self) -> int:
        """Return count of payments in history."""
        account_data = self._get_account_data()
        payments = account_data.get("payments", []) or []
        return len(payments)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return last 5 payments as attributes."""
        account_data = self._get_account_data()
        payments = account_data.get("payments", []) or []
        
        attributes = {
            "payment_method": account_data.get("paymentMethod"),
            "total_payments": len(payments),
        }
        
        # Add last 5 payments
        for idx, payment in enumerate(payments[:5]):
            payment_num = idx + 1
            amt_str = payment.get("amount", "")
            # Clean amount string
            try:
                amt_clean = amt_str.replace("$", "").replace(",", "")
                amount = float(amt_clean) if amt_clean else 0.0
            except (ValueError, TypeError):
                amount = 0.0
            
            attributes[f"payment_{payment_num}_date"] = payment.get("date")
            attributes[f"payment_{payment_num}_amount"] = amount
            attributes[f"payment_{payment_num}_method"] = payment.get("method", account_data.get("paymentMethod"))
        
        return attributes


class ContactEnergyFullAddressSensor(ContactEnergyAccountSensorBase):
    """Sensor showing full address with individual components."""
    
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Full Address ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_full_address"
        self._attr_icon = "mdi:map-marker"

    @property
    def native_value(self) -> str | None:
        """Return full address."""
        contract = self._get_contract_data()
        premise = contract.get("premise", {})
        supply_address = premise.get("supplyAddress", {})
        return supply_address.get("fullForm") or supply_address.get("shortForm")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return address components as attributes."""
        contract = self._get_contract_data()
        premise = contract.get("premise", {})
        supply_address = premise.get("supplyAddress", {})
        
        return {
            "short_form": supply_address.get("shortForm"),
            "full_form": supply_address.get("fullForm"),
            "street_number": supply_address.get("streetNumber"),
            "street_name": supply_address.get("streetName"),
            "street_type": supply_address.get("streetType"),
            "suburb": supply_address.get("suburb"),
            "city": supply_address.get("city"),
            "postcode": supply_address.get("postcode"),
            "region": supply_address.get("region"),
            "premise_type": premise.get("premiseType"),
        }


class ContactEnergyMeterRegisterSensor(ContactEnergyAccountSensorBase):
    """Sensor showing meter register readings."""
    
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Meter Register ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_meter_register"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_icon = "mdi:gauge"

    @property
    def native_value(self) -> float | None:
        """Return current meter reading."""
        contract = self._get_contract_data()
        devices = contract.get("devices", [])
        if devices and devices[0].get("registers"):
            registers = devices[0].get("registers", [])
            if registers:
                current_reading = registers[0].get("currentMeterReading")
                try:
                    return float(current_reading) if current_reading is not None else None
                except (ValueError, TypeError):
                    return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return register details as attributes."""
        contract = self._get_contract_data()
        devices = contract.get("devices", [])
        
        attributes = {}
        
        if devices and devices[0].get("registers"):
            registers = devices[0].get("registers", [])
            
            for idx, register in enumerate(registers[:3]):  # Show up to 3 registers
                reg_num = idx + 1
                attributes[f"register_{reg_num}_type"] = register.get("registerType")
                attributes[f"register_{reg_num}_current"] = register.get("currentMeterReading")
                attributes[f"register_{reg_num}_previous"] = register.get("previousMeterReading")
                attributes[f"register_{reg_num}_reading_date"] = register.get("previousMeterReadingDate")
                attributes[f"register_{reg_num}_multiplier"] = register.get("multiplier")
        
        return attributes


class ContactEnergyContractDetailsSensor(ContactEnergyAccountSensorBase):
    """Sensor showing contract details and status."""
    
    def __init__(self, coordinator: ContactEnergyCoordinator, contract_icp: str) -> None:
        super().__init__(coordinator, contract_icp)
        self._attr_name = f"Contact Energy Contract Details ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_contract_details"
        self._attr_icon = "mdi:file-document"

    @property
    def native_value(self) -> str | None:
        """Return contract status."""
        contract = self._get_contract_data()
        return contract.get("status") or contract.get("contractStatus") or "active"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return contract details as attributes."""
        contract = self._get_contract_data()
        
        return {
            "contract_id": contract.get("id"),
            "contract_type": contract.get("contractType"),
            "contract_type_label": contract.get("contractTypeLabel"),
            "icp": contract.get("icp"),
            "start_date": contract.get("startDate"),
            "end_date": contract.get("endDate"),
            "term_length": contract.get("termLength"),
            "network_provider": contract.get("networkProvider"),
            "meter_type": contract.get("meterType"),
            "plan_code": contract.get("planCode"),
            "plan_name": contract.get("planName"),
        }


# -----------------------------------------
# Convenience Sensor Base Class
# -----------------------------------------

class ContactEnergyConvenienceSensorBase(CoordinatorEntity, SensorEntity):
    """Base for convenience sensors that recompute on coordinator updates."""

    def __init__(self, coordinator: ContactEnergyCoordinator, account_id: str, contract_id: str, contract_icp: str) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._contract_id = contract_id
        self._contract_icp = contract_icp
        self._state = 0.0

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is only available if coordinator has successfully fetched data at least once
        return self.coordinator.last_update_success and self.coordinator.data is not None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # initial compute after HA start - but only after coordinator has data
        async def _delayed_recompute():
            # Wait for coordinator to have data before computing
            if not self.coordinator.last_update_success or self.coordinator.data is None:
                # Wait for coordinator to have data (it's already refreshing from setup)
                max_wait_time = 60  # Maximum wait time in seconds
                wait_interval = 0.5  # Check every 0.5 seconds
                elapsed = 0
                while (not self.coordinator.last_update_success or self.coordinator.data is None) and elapsed < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    elapsed += wait_interval
            
            import hashlib
            icp_hash = int(hashlib.md5(self._contract_icp.encode()).hexdigest()[:8], 16)
            base_delay = (icp_hash % 20) / 10.0  # 0-2 seconds based on ICP
            jitter = random.uniform(0.1, 1.5)  # Additional random jitter
            total_delay = base_delay + jitter
            
            try:
                await asyncio.sleep(total_delay)
            except Exception:  # noqa: BLE001
                pass
            await self._recompute()
        self.hass.async_create_task(_delayed_recompute())

    async def _recompute(self) -> None:
        start, end = self._date_range()
        kwh, cost, free_kwh = await self._get_usage_for_date_range(start, end)
        self._apply_values(kwh, cost, free_kwh)
        self.async_write_ha_state()

    def _apply_values(self, kwh: float, cost: float, free_kwh: float) -> None:
        # To be implemented by subclasses depending on metric
        pass

    def _date_range(self) -> tuple[date, date]:
        # To be implemented by subclasses
        return (datetime.now().date(), datetime.now().date())

    async def _get_usage_for_date_range(self, start_date: date, end_date: date) -> tuple[float, float, float]:
        total_kwh = 0.0
        total_cost = 0.0
        total_free_kwh = 0.0
        current = start_date
        while current <= end_date:
            try:
                resp = await self.coordinator.api.async_get_usage(
                    str(current.year), str(current.month), str(current.day), self._account_id, self._contract_id
                )
                if isinstance(resp, list):
                    for p in resp:
                        val = ContactEnergyUsageSensor._safe_float(p.get("value"))
                        cost = ContactEnergyUsageSensor._safe_float(p.get("dollarValue"))
                        off = str(p.get("offpeakValue", "0.00"))
                        if off == "0.00":
                            total_kwh += val
                            total_cost += cost
                        else:
                            total_free_kwh += val
            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("Convenience fetch failed for %s: %s", current, e)
            current += timedelta(days=1)
            await asyncio.sleep(0)
        return total_kwh, total_cost, total_free_kwh

    def _handle_coordinator_update(self) -> None:
        # Recompute on coordinator refresh
        self.hass.async_create_task(self._recompute())


# -----------------------------------------
# Phase 2: Analytics sensors
# -----------------------------------------

class ContactEnergyAverageDailyUsage7DaysSensor(ContactEnergyConvenienceSensorBase):
    """Sensor showing average daily usage over the last 7 days."""
    
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Average Daily Usage (7 Days) ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_avg_daily_usage_7d"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:chart-line"

    def _date_range(self) -> tuple[date, date]:
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=6)
        return start, end

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        # Calculate average (7 days of data)
        self._state = round(kwh / 7.0, 2) if kwh > 0 else 0.0

    @property
    def native_value(self) -> float:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "period": "7 days",
            "calculation": "Average daily usage over last 7 complete days",
        }


class ContactEnergyAverageDailyUsage30DaysSensor(ContactEnergyConvenienceSensorBase):
    """Sensor showing average daily usage over the last 30 days."""
    
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Average Daily Usage (30 Days) ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_avg_daily_usage_30d"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:chart-line"

    def _date_range(self) -> tuple[date, date]:
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=29)
        return start, end

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        # Calculate average (30 days of data)
        self._state = round(kwh / 30.0, 2) if kwh > 0 else 0.0

    @property
    def native_value(self) -> float:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "period": "30 days",
            "calculation": "Average daily usage over last 30 complete days",
        }


class ContactEnergyUsageTrendSensor(ContactEnergyConvenienceSensorBase):
    """Sensor showing usage trend (comparing last 7 days vs previous 7 days)."""
    
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Usage Trend ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_usage_trend"
        self._attr_icon = "mdi:trending-up"
        self._attr_native_unit_of_measurement = "%"
        self._previous_period_kwh = 0.0
        self._current_period_kwh = 0.0

    def _date_range(self) -> tuple[date, date]:
        # Return last 14 days to get both periods
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=13)
        return start, end

    async def _recompute(self) -> None:
        # Get last 14 days split into two periods
        end = datetime.now().date() - timedelta(days=1)
        
        # Current period: last 7 days
        current_start = end - timedelta(days=6)
        current_end = end
        current_kwh, _, _ = await self._get_usage_for_date_range(current_start, current_end)
        
        # Previous period: 7 days before that
        previous_start = end - timedelta(days=13)
        previous_end = end - timedelta(days=7)
        previous_kwh, _, _ = await self._get_usage_for_date_range(previous_start, previous_end)
        
        self._current_period_kwh = current_kwh
        self._previous_period_kwh = previous_kwh
        
        # Calculate percentage change
        if previous_kwh > 0:
            change = ((current_kwh - previous_kwh) / previous_kwh) * 100
            self._state = round(change, 1)
        else:
            self._state = 0.0
        
        self.async_write_ha_state()

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        # Not used - we override _recompute instead
        pass

    @property
    def native_value(self) -> float:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        trend_direction = "increasing" if self._state > 0 else "decreasing" if self._state < 0 else "stable"
        return {
            "current_period_kwh": round(self._current_period_kwh, 2),
            "previous_period_kwh": round(self._previous_period_kwh, 2),
            "trend_direction": trend_direction,
            "period_comparison": "Last 7 days vs previous 7 days",
        }


class ContactEnergyCostPerKwhSensor(ContactEnergyConvenienceSensorBase):
    """Sensor showing average cost per kWh over the last 30 days."""
    
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Cost Per kWh (30 Days) ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_cost_per_kwh"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD/kWh"
        self._attr_icon = "mdi:cash"
        self._total_kwh = 0.0
        self._total_cost = 0.0

    def _date_range(self) -> tuple[date, date]:
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=29)
        return start, end

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._total_kwh = kwh
        self._total_cost = cost
        # Calculate cost per kWh (excluding free energy)
        if kwh > 0:
            self._state = round(cost / kwh, 4)
        else:
            self._state = 0.0

    @property
    def native_value(self) -> float:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "period": "30 days",
            "total_kwh": round(self._total_kwh, 2),
            "total_cost": round(self._total_cost, 2),
            "calculation": "Total cost / Total kWh (paid usage only)",
        }


# -----------------------------------------
# Phase 3: Forecasting sensor (EMA)
# -----------------------------------------

class ContactEnergyForecastDailyUsageSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Forecast next day's usage using EMA over last 30 complete days."""

    def __init__(self, coordinator: ContactEnergyCoordinator, account_id: str, contract_id: str, contract_icp: str) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._contract_id = contract_id
        self._contract_icp = contract_icp
        self._state: float | None = None
        self._window_days = 30
        # alpha = 2/(N+1)
        self._alpha = round(2.0 / (self._window_days + 1.0), 4)
        self._mean: float | None = None
        self._std: float | None = None
        self._last_observation: float | None = None
        self._last_computed: datetime | None = None

        self._attr_name = f"Contact Energy Forecast Daily Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_forecast_daily_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:chart-timeline-variant"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def native_value(self) -> StateType:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "method": "EMA",
            "window_days": self._window_days,
            "alpha": self._alpha,
            "mean_30d": round(self._mean, 3) if self._mean is not None else None,
            "std_30d": round(self._std, 3) if self._std is not None else None,
            "last_observation": round(self._last_observation, 3) if self._last_observation is not None else None,
            "lower_2sigma": round(max(0.0, (self._mean or 0.0) - 2 * (self._std or 0.0)), 3) if self._mean is not None and self._std is not None else None,
            "upper_2sigma": round((self._mean or 0.0) + 2 * (self._std or 0.0), 3) if self._mean is not None and self._std is not None else None,
            "last_computed": self._last_computed.isoformat() if self._last_computed else None,
            "calculation": "EMA forecast of next day based on last 30 complete days (paid usage only)",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = float(last_state.state)
                attrs = last_state.attributes
                self._mean = attrs.get("mean_30d")
                self._std = attrs.get("std_30d")
                self._last_observation = attrs.get("last_observation")
                last_computed_str = attrs.get("last_computed")
                if last_computed_str:
                    self._last_computed = datetime.fromisoformat(last_computed_str)
                _LOGGER.debug("Restored forecast state from %s", last_computed_str)
            except (ValueError, TypeError) as e:
                _LOGGER.warning("Could not restore forecast state: %s", e)
        
        # Schedule recompute: immediately if never computed or stale (>1 day), else defer
        should_recompute_now = (
            self._last_computed is None or 
            (datetime.now() - self._last_computed) > timedelta(days=1)
        )
        
        if should_recompute_now:
            async def _delayed_recompute() -> None:
                try:
                    await asyncio.sleep(5)
                except Exception:  # noqa: BLE001
                    pass
                await self._recompute()
            self.hass.async_create_task(_delayed_recompute())
        else:
            # Data is fresh, just update display
            self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        # Only recompute if data is stale (>1 day old)
        if self._last_computed is None or (datetime.now() - self._last_computed) > timedelta(days=1):
            self.hass.async_create_task(self._recompute())

    async def _fetch_daily_paid_usage(self, for_date: date) -> float:
        total = 0.0
        try:
            resp = await self.coordinator.api.async_get_usage(
                str(for_date.year), str(for_date.month), str(for_date.day), self._account_id, self._contract_id
            )
            if isinstance(resp, list):
                for p in resp:
                    val = ContactEnergyUsageSensor._safe_float(p.get("value"))
                    off = str(p.get("offpeakValue", "0.00"))
                    if off == "0.00":
                        total += val
        except Exception as e:  # noqa: BLE001
            _LOGGER.debug("Forecast fetch failed for %s: %s", for_date, e)
        return total

    async def _recompute(self) -> None:
        # Build last 30 complete days series (yesterday back)
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=self._window_days - 1)
        series: list[float] = []
        current = start
        while current <= end:
            kwh = await self._fetch_daily_paid_usage(current)
            series.append(kwh)
            current += timedelta(days=1)
            await asyncio.sleep(0)

        if not series:
            self._state = None
            self.async_write_ha_state()
            return

        # Compute mean and std over the window
        n = len(series)
        mean_val = sum(series) / float(n)
        var = sum((x - mean_val) ** 2 for x in series) / float(n)
        std = var ** 0.5

        # Compute EMA forecast: initialize with first observation
        ema = series[0]
        alpha = self._alpha
        for x in series[1:]:
            ema = alpha * x + (1 - alpha) * ema

        self._mean = mean_val
        self._std = std
        self._last_observation = series[-1]
        self._state = round(ema, 3)
        self._last_computed = datetime.now()
        self.async_write_ha_state()


# -----------------------------------------
# Convenience usage and cost sensors
# -----------------------------------------

class ContactEnergyTodayUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Today Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_today_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-today"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        return today, today

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyYesterdayUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Yesterday Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_yesterday_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-minus"

    def _date_range(self) -> tuple[date, date]:
        y = datetime.now().date() - timedelta(days=1)
        return y, y

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLast7DaysUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last 7 Days Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_7_days_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-week"

    def _date_range(self) -> tuple[date, date]:
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=6)
        return start, end

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLast30DaysUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last 30 Days Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_30_days_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-month"

    def _date_range(self) -> tuple[date, date]:
        end = datetime.now().date() - timedelta(days=1)
        start = end - timedelta(days=29)
        return start, end

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyCurrentMonthUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Current Month Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_current_month_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        start = today.replace(day=1)
        return start, today

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLastMonthUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last Month Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_month_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:calendar-arrow-left"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        first_current = today.replace(day=1)
        last_prev = first_current - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev, last_prev

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = kwh

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyTodayCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Today Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_today_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        t = datetime.now().date()
        return t, t

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyYesterdayCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Yesterday Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_yesterday_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        y = datetime.now().date() - timedelta(days=1)
        return y, y

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyCurrentMonthCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Current Month Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_current_month_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        start = today.replace(day=1)
        return start, today

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyLastMonthCostSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Last Month Cost ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_last_month_cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "NZD"
        self._attr_icon = "mdi:currency-usd"

    def _date_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        first_current = today.replace(day=1)
        last_prev = first_current - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return first_prev, last_prev

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = cost

    @property
    def native_value(self) -> float:
        return self._state


class ContactEnergyTodayFreeUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Today Free Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_today_free_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:gift"

    def _date_range(self) -> tuple[date, date]:
        t = datetime.now().date()
        return t, t

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = free_kwh

    @property
    def native_value(self) -> float:
        return self._state


# -----------------------------------------
# Charting sensors for ApexCharts
# -----------------------------------------

class ContactEnergyChartHourlySensor(SensorEntity):
    """Sensor exposing hourly usage data for ApexCharts."""
    
    def __init__(self, hass: HomeAssistant, stat_id: str, contract_icp: str) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._contract_icp = contract_icp
        self._attr_name = f"Contact Energy Chart Hourly ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_chart_hourly"
        self._attr_icon = "mdi:chart-bar"
        self._hourly_data: dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Return the most recent hour's usage
        if self._hourly_data:
            latest = max(self._hourly_data.keys())
            return self._hourly_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "hourly_data": self._hourly_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    async def async_update(self) -> None:
        # Query last 14 days of hourly statistics (bounded to avoid large attributes)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=14)
        recorder = __import__("homeassistant.components.recorder").components.recorder
        stats = await recorder.get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            [self._stat_id],
            "hour",
            None,
            {"sum"}
        )
        self._hourly_data = {}
        if self._stat_id in stats:
            # Sort entries by timestamp to ensure correct delta calculation
            sorted_entries = sorted(stats[self._stat_id], key=lambda x: x.get("start", 0))
            prev_val = None
            
            for entry in sorted_entries:
                start_ts = entry.get("start")
                val = entry.get("sum")
                if start_ts and val is not None:
                    # Convert timestamp to datetime and store as ISO string for ApexCharts
                    dt = datetime.fromtimestamp(start_ts)
                    
                    # Calculate delta from previous value (no negatives, default to 0)
                    if prev_val is not None:
                        delta = float(val) - prev_val
                        delta = max(0.0, delta)  # No negative values
                    else:
                        # First entry: treat as 0 (no prior data to compare)
                        delta = 0.0
                    
                    self._hourly_data[dt.isoformat()] = delta
                    prev_val = float(val)
        self._last_update = datetime.now()


class ContactEnergyChartDailySensor(SensorEntity):
    """Sensor exposing daily usage data for ApexCharts."""
    
    def __init__(self, hass: HomeAssistant, stat_id: str, contract_icp: str) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._contract_icp = contract_icp
        self._attr_name = f"Contact Energy Chart Daily ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_chart_daily"
        self._attr_icon = "mdi:calendar"
        self._daily_data: dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Return the most recent day's usage
        if self._daily_data:
            latest = max(self._daily_data.keys())
            return self._daily_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "daily_data": self._daily_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    async def async_update(self) -> None:
        # Query last 60 days of daily statistics to avoid database attribute size limits
        end_time = datetime.now()
        start_time = end_time - timedelta(days=60)
        recorder = __import__("homeassistant.components.recorder").components.recorder
        stats = await recorder.get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            [self._stat_id],
            "day",
            None,
            {"sum"}
        )
        self._daily_data = {}
        if self._stat_id in stats:
            # Sort entries by timestamp to ensure correct delta calculation
            sorted_entries = sorted(stats[self._stat_id], key=lambda x: x.get("start", 0))
            prev_val = None
            
            for entry in sorted_entries:
                start_ts = entry.get("start")
                val = entry.get("sum")
                if start_ts and val is not None:
                    # Convert timestamp to datetime and set to 23:59:59 (end of day)
                    dt = datetime.fromtimestamp(start_ts)
                    dt_end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)
                    # Format as ISO 8601 with Z suffix
                    iso_key = dt_end_of_day.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    # Calculate delta from previous value (no negatives, default to 0)
                    if prev_val is not None:
                        delta = float(val) - prev_val
                        delta = max(0.0, delta)  # No negative values
                    else:
                        # First entry: treat as 0 (no prior data to compare)
                        delta = 0.0
                    
                    self._daily_data[iso_key] = delta
                    prev_val = float(val)
        self._last_update = datetime.now()


class ContactEnergyChartHourlyFreeSensor(SensorEntity):
    """Sensor exposing hourly free usage data for ApexCharts."""

    def __init__(self, hass: HomeAssistant, stat_id: str, contract_icp: str) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._contract_icp = contract_icp
        self._attr_name = f"Contact Energy Chart Hourly Free ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_chart_hourly_free"
        self._attr_icon = "mdi:gift"
        self._hourly_free_data: dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Return the most recent hour's free usage
        if self._hourly_free_data:
            latest = max(self._hourly_free_data.keys())
            return self._hourly_free_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "hourly_free_data": self._hourly_free_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    async def async_update(self) -> None:
        # Query last 14 days of hourly free statistics (bounded to avoid large attributes)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=14)
        recorder = __import__("homeassistant.components.recorder").components.recorder
        stats = await recorder.get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            [self._stat_id],
            "hour",
            None,
            {"sum"}
        )
        self._hourly_free_data = {}
        if self._stat_id in stats:
            # Sort entries by timestamp to ensure correct delta calculation
            sorted_entries = sorted(stats[self._stat_id], key=lambda x: x.get("start", 0))
            prev_val = None
            
            for entry in sorted_entries:
                start_ts = entry.get("start")
                val = entry.get("sum")
                if start_ts and val is not None:
                    # Robustly handle both float and datetime
                    if isinstance(start_ts, (int, float)):
                        dt = datetime.fromtimestamp(start_ts)
                    elif isinstance(start_ts, datetime):
                        dt = start_ts
                    else:
                        continue
                    
                    # Calculate delta from previous value (no negatives, default to 0)
                    if prev_val is not None:
                        delta = float(val) - prev_val
                        delta = max(0.0, delta)  # No negative values
                    else:
                        # First entry: treat as 0 (no prior data to compare)
                        delta = 0.0
                    
                    self._hourly_free_data[dt.isoformat()] = delta
                    prev_val = float(val)
        self._last_update = datetime.now()


class ContactEnergyChartDailyFreeSensor(SensorEntity):
    """Sensor exposing daily free usage data for ApexCharts."""

    def __init__(self, hass: HomeAssistant, stat_id: str, contract_icp: str) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._contract_icp = contract_icp
        self._attr_name = f"Contact Energy Chart Daily Free ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_chart_daily_free"
        self._attr_icon = "mdi:gift"
        self._daily_free_data: dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Return the most recent day's free usage
        if self._daily_free_data:
            latest = max(self._daily_free_data.keys())
            return self._daily_free_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "daily_free_data": self._daily_free_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    async def async_update(self) -> None:
        # Query last 60 days of daily free statistics to avoid database attribute size limits
        end_time = datetime.now()
        start_time = end_time - timedelta(days=60)
        recorder = __import__("homeassistant.components.recorder").components.recorder
        stats = await recorder.get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            end_time,
            [self._stat_id],
            "day",
            None,
            {"sum"}
        )
        self._daily_free_data = {}
        if self._stat_id in stats:
            # Sort entries by timestamp to ensure correct delta calculation
            sorted_entries = sorted(stats[self._stat_id], key=lambda x: x.get("start", 0))
            prev_val = None
            
            for entry in sorted_entries:
                start_ts = entry.get("start")
                val = entry.get("sum")
                if start_ts and val is not None:
                    # Robustly handle both float and datetime
                    if isinstance(start_ts, (int, float)):
                        dt = datetime.fromtimestamp(start_ts)
                    elif isinstance(start_ts, datetime):
                        dt = start_ts
                    else:
                        continue
                    
                    # Set to 23:59:59 (end of day)
                    dt_end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)
                    # Format as ISO 8601 with Z suffix
                    iso_key = dt_end_of_day.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    # Calculate delta from previous value (no negatives, default to 0)
                    if prev_val is not None:
                        delta = float(val) - prev_val
                        delta = max(0.0, delta)  # No negative values
                    else:
                        # First entry: treat as 0 (no prior data to compare)
                        delta = 0.0
                    
                    self._daily_free_data[iso_key] = delta
                    prev_val = float(val)
        self._last_update = datetime.now()


class ContactEnergyChartMonthlySensor(SensorEntity):
    """Sensor exposing monthly usage data for ApexCharts."""

    def __init__(self, hass: HomeAssistant, stat_id: str, contract_icp: str) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._contract_icp = contract_icp
        self._attr_name = f"Contact Energy Chart Monthly ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_chart_monthly"
        self._attr_icon = "mdi:calendar-month"
        self._monthly_data: dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Return the most recent month's usage
        if self._monthly_data:
            latest = max(self._monthly_data.keys())
            return self._monthly_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "monthly_data": self._monthly_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    async def async_update(self) -> None:
        # Query monthly statistics from the database. Some recorder helpers default to
        # the last 12 months when start_time is None, so explicitly ask from a very
        # early date to ensure we get the full history available for this statistic.
        recorder = __import__("homeassistant.components.recorder").components.recorder
        start_time = datetime(2000, 1, 1)
        stats = await recorder.get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            None,  # up to now
            [self._stat_id],
            "month",
            None,
            {"sum"}
        )
        self._monthly_data = {}
        if self._stat_id in stats:
            for entry in stats[self._stat_id]:
                start_ts = entry.get("start")
                # Prefer the monthly change if provided by the statistics helper; fall back to sum
                val = entry.get("change", entry.get("sum"))
                if start_ts and val is not None:
                    # Convert timestamp to datetime and store as year-month string
                    if isinstance(start_ts, (int, float)):
                        dt = datetime.fromtimestamp(start_ts)
                    elif isinstance(start_ts, datetime):
                        dt = start_ts
                    else:
                        continue
                    # Store as YYYY-MM-15 format for monthly data (mid-month)
                    self._monthly_data[dt.strftime("%Y-%m-15")] = float(val)
        self._last_update = datetime.now()


class ContactEnergyChartMonthlyFreeSensor(SensorEntity):
    """Sensor exposing monthly free usage data for ApexCharts."""

    def __init__(self, hass: HomeAssistant, stat_id: str, contract_icp: str) -> None:
        self.hass = hass
        self._stat_id = stat_id
        self._contract_icp = contract_icp
        self._attr_name = f"Contact Energy Chart Monthly Free ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_chart_monthly_free"
        self._attr_icon = "mdi:gift"
        self._monthly_free_data: dict[str, float] = {}
        self._last_update: Optional[datetime] = None
        self._state = None

    @property
    def state(self) -> Any:
        # Return the most recent month's free usage
        if self._monthly_free_data:
            latest = max(self._monthly_free_data.keys())
            return self._monthly_free_data[latest]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "monthly_free_data": self._monthly_free_data,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._contract_icp)},
            "name": f"Contact Energy ({self._contract_icp})",
            "manufacturer": "Contact Energy",
            "model": "Smart Meter",
        }

    async def async_update(self) -> None:
        # Query monthly free statistics from the database with an explicit early start
        # date to avoid any implicit 12-month limitation.
        recorder = __import__("homeassistant.components.recorder").components.recorder
        start_time = datetime(2000, 1, 1)
        stats = await recorder.get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_time,
            None,  # up to now
            [self._stat_id],
            "month",
            None,
            {"sum"}
        )
        self._monthly_free_data = {}
        if self._stat_id in stats:
            for entry in stats[self._stat_id]:
                start_ts = entry.get("start")
                val = entry.get("change", entry.get("sum"))
                if start_ts and val is not None:
                    # Robustly handle both float and datetime
                    if isinstance(start_ts, (int, float)):
                        dt = datetime.fromtimestamp(start_ts)
                    elif isinstance(start_ts, datetime):
                        dt = start_ts
                    else:
                        continue
                    # Store as YYYY-MM-15 format for monthly data (mid-month)
                    self._monthly_free_data[dt.strftime("%Y-%m-15")] = float(val)
        self._last_update = datetime.now()


class ContactEnergyYesterdayFreeUsageSensor(ContactEnergyConvenienceSensorBase):
    def __init__(self, coordinator, account_id, contract_id, contract_icp) -> None:
        super().__init__(coordinator, account_id, contract_id, contract_icp)
        self._attr_name = f"Contact Energy Yesterday Free Usage ({contract_icp})"
        self._attr_unique_id = f"{DOMAIN}_{contract_icp}_yesterday_free_usage"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:gift"

    def _date_range(self) -> tuple[date, date]:
        y = datetime.now().date() - timedelta(days=1)
        return y, y

    def _apply_values(self, kwh, cost, free_kwh) -> None:
        self._state = free_kwh

    @property
    def native_value(self) -> float:
        return self._state
