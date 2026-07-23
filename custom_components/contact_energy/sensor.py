"""Sensor platform for Contact Energy integration.

This module creates sensor entities for Contact Energy data including account
information, usage data, and energy dashboard sensors.

Version: 2.0.0 - Uses modular sensor classes from sensors/ package
"""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .sensors import (
    AccountBalanceSensor,
    InvoiceSensor,
    NextBillSensor,
    AccountDetailSensor,
    UsageDataSensor,
    HourlyUsageSensor,
    DailyUsageSensor,
    MonthlyUsageSensor,
    EnergySensor,
    DailyEnergySensor,
    MonthlyEnergySensor,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Set up Contact Energy sensor entities.

    Creates sensor entities for account information, usage data, and energy
    dashboard integration using the v2.0.0 architecture.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry for this integration.
        async_add_entities: Callback to add entities.
        discovery_info: Additional discovery information (unused).
    """
    # Get coordinators from domain data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    account_coordinator = entry_data["account_coordinator"]
    usage_coordinator = entry_data.get("usage_coordinator")
    
    # Get account information from the config entry
    entry_id = config_entry.entry_id
    account_nickname = config_entry.data.get("account_nickname", "Unknown")
    icp = config_entry.data.get("icp", "Unknown")
    contract_id = config_entry.data.get("contract_id", "unknown")

    # Create a friendly entity name for the sensors
    # Format: Account Nickname (ICP)
    entity_name = f"{account_nickname} ({icp})"

    # Build list of sensor entities
    entities = []

    # Account Balance Sensors
    entities.extend([
        AccountBalanceSensor(account_coordinator, entry_id, entity_name, "current_balance"),
        AccountBalanceSensor(account_coordinator, entry_id, entity_name, "prepay_debt_balance"),
        AccountBalanceSensor(account_coordinator, entry_id, entity_name, "refund_eligible"),
        AccountBalanceSensor(account_coordinator, entry_id, entity_name, "refund_max"),
    ])

    # Invoice Sensors
    entities.extend([
        InvoiceSensor(account_coordinator, entry_id, entity_name, "amount_due"),
        InvoiceSensor(account_coordinator, entry_id, entity_name, "amount_paid"),
        InvoiceSensor(account_coordinator, entry_id, entity_name, "payment_due_date"),
        InvoiceSensor(account_coordinator, entry_id, entity_name, "days_til_overdue"),
        InvoiceSensor(account_coordinator, entry_id, entity_name, "discount_total"),
    ])

    # Next Bill Sensors
    entities.extend([
        NextBillSensor(account_coordinator, entry_id, entity_name, "next_bill_date"),
        NextBillSensor(account_coordinator, entry_id, entity_name, "days_until_bill"),
    ])

    # Account Detail Sensors
    entities.extend([
        AccountDetailSensor(account_coordinator, entry_id, entity_name, "account_number"),
        AccountDetailSensor(account_coordinator, entry_id, entity_name, "account_status"),
        AccountDetailSensor(account_coordinator, entry_id, entity_name, "payment_method"),
        AccountDetailSensor(account_coordinator, entry_id, entity_name, "contract_name"),
        AccountDetailSensor(account_coordinator, entry_id, entity_name, "property_address"),
        AccountDetailSensor(account_coordinator, entry_id, entity_name, "supply_address"),
        AccountDetailSensor(account_coordinator, entry_id, entity_name, "icp_number"),
    ])

    # Usage and Energy Sensors (only if usage coordinator is available)
    if usage_coordinator:
        # Main usage data sensor with all attributes
        entities.append(
            UsageDataSensor(hass, usage_coordinator, entry_id, entity_name, contract_id)
        )

        # Separate hourly/daily/monthly sensors for individual access
        entities.extend([
            HourlyUsageSensor(hass, usage_coordinator, entry_id, entity_name, contract_id),
            DailyUsageSensor(hass, usage_coordinator, entry_id, entity_name, contract_id),
            MonthlyUsageSensor(hass, usage_coordinator, entry_id, entity_name, contract_id),
        ])

        # Energy Dashboard sensors
        entities.extend([
            EnergySensor(hass, usage_coordinator, entry_id, entity_name, contract_id, "paid"),
            EnergySensor(hass, usage_coordinator, entry_id, entity_name, contract_id, "free"),
            DailyEnergySensor(hass, usage_coordinator, entry_id, entity_name, contract_id, "paid"),
            DailyEnergySensor(hass, usage_coordinator, entry_id, entity_name, contract_id, "free"),
            MonthlyEnergySensor(hass, usage_coordinator, entry_id, entity_name, contract_id, "paid"),
            MonthlyEnergySensor(hass, usage_coordinator, entry_id, entity_name, contract_id, "free"),
        ])

        _LOGGER.info(
            "Created %d account sensors and %d usage/energy sensors for %s",
            17,  # Account sensors count
            10,  # Usage/energy sensors count
            entity_name,
        )
    else:
        _LOGGER.warning(
            "Usage coordinator not available for %s - only account sensors will be created",
            entity_name,
        )
        _LOGGER.info("Created %d account sensors for %s", len(entities), entity_name)

    # Add all entities to Home Assistant
    async_add_entities(entities, True)
