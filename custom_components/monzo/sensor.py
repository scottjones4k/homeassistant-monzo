"""Support for Monzo sensors."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any, Optional
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.typing import StateType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util
from .const import (
    DOMAIN,
    SERVICE_POT_DEPOSIT,
    SERVICE_POT_WITHDRAW
)

from .api.models.balance import Balance
from .monzo_update_coordinator import MonzoUpdateCoordinator
from .monzo_category_update_coordinator import Category, MonzoCategoryUpdateCoordinator
from .entity import MonzoBaseEntity

_LOGGER = logging.getLogger(__name__)

ATTR_NATIVE_BALANCE = "Balance in native currency"

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by Monzo"

POT_SERVICE_SCHEMA = {
    vol.Required('amount_in_minor_units'): vol.All(vol.Coerce(int), vol.Range(0, 200000)),
}

@dataclass(frozen=True, kw_only=True)
class MonzoSensorEntityDescription(SensorEntityDescription):
    """Describes Monzo sensor entity."""

    value_fn: Callable[[dict[str, Any]], StateType]
    resets_daily: bool

ACCOUNT_SENSORS = (
    MonzoSensorEntityDescription(
        key="balance",
        translation_key="balance",
        value_fn=lambda data: data.balance / 100,
        resets_daily=False,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
    ),
    MonzoSensorEntityDescription(
        key="total_balance",
        translation_key="total_balance",
        value_fn=lambda data: data.total_balance / 100,
        resets_daily=False,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
    ),
    MonzoSensorEntityDescription(
        key="spend_today",
        translation_key="spend_today",
        value_fn=lambda data: data.spend_today / 100,
        resets_daily=True,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
    ),
)

POT_SENSORS = (
    MonzoSensorEntityDescription(
        key="pot_balance",
        translation_key="pot_balance",
        value_fn=lambda data: data.balance / 100,
        resets_daily=False,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
    ),
)

CATEGORY_SENSORS = (
    MonzoSensorEntityDescription(
        key="category_spend",
        translation_key="category_spend",
        value_fn=lambda data: data.amount / -100,
        resets_daily=False,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
    ),
    MonzoSensorEntityDescription(
        key="category_remaining",
        translation_key="category_remaining",
        value_fn=lambda data: data.target - data.amount / 100,
        resets_daily=False,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monzo sensor platform."""
    coordinator: MonzoUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    category_coordinator: MonzoCategoryUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["category_coordinator"]

    await coordinator.async_config_entry_first_refresh()

    # async_add_entities(
    #     BalanceSensor(coordinator, idx) for idx, ent in coordinator.data.items() if not idx.startswith("webhook")
    # )

    accounts = [
        MonzoSensor(
            coordinator,
            entity_description,
            index,
            account.name
        )
        for entity_description in ACCOUNT_SENSORS
        for index, account in coordinator.data.items() if index.startswith("acc")
    ]

    pots = [
        MonzoSensor(coordinator, entity_description, index, "Pot")
        for entity_description in POT_SENSORS
        for index, _pot in coordinator.data.items() if index.startswith("pot")
    ]

    categories = [
        MonzoSensor(category_coordinator, entity_description, category, "Category")
        for entity_description in CATEGORY_SENSORS
        for category in category_coordinator.data
    ]
    # async_add_entities(
    #     SpendTodaySensor(coordinator, idx) for idx, ent in coordinator.data.items() if idx.startswith("acc")
    # )

    async_add_entities(accounts + pots + categories) 
    
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_POT_DEPOSIT,
        POT_SERVICE_SCHEMA,
        "pot_deposit",
    )

    platform.async_register_entity_service(
        SERVICE_POT_WITHDRAW,
        POT_SERVICE_SCHEMA,
        "pot_withdraw",
    )

class MonzoSensor(MonzoBaseEntity, SensorEntity):
    """Representation of a Balance sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entity_description,
        idx,
        device_model: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, idx, device_model)

        self._attr_state_class = SensorStateClass.TOTAL

        self.entity_description = entity_description

        self._attr_unique_id = f"{self.idx}_{self.entity_description.key}"

    @property
    def native_value(self) -> StateType:
        """Return the state."""

        try:
            state = self.entity_description.value_fn(self.data)
        except (KeyError, ValueError):
            return None

        return state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        if isinstance(self.data, Balance):
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
            }
        elif isinstance(self.data, Category):
            return {
                ATTR_ATTRIBUTION: ATTRIBUTION,
                'target': self.data.target,
            }
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            'goal_amount': (self.data.goal_amount or 0)/100,
            'deleted': self.data.deleted,
            'locked': self.data.locked,
            'pot_type': self.data.type,
            'cover_image_url': self.data.cover_image_url
        }
    
    @property
    def last_reset(self) -> Optional[datetime]:
        """These values reset every day."""
        if self.entity_description.resets_daily:
            return dt_util.start_of_local_day()
        return None

    async def pot_deposit(self, amount_in_minor_units: int | None = None):
        if not self.idx.startswith("pot"):
            raise HomeAssistantError("supported only on Pot sensors")
        await self.coordinator.deposit_pot(self.data, amount_in_minor_units)

    async def pot_withdraw(self, amount_in_minor_units: int | None = None):
        if not self.idx.startswith("pot"):
            raise HomeAssistantError("supported only on Pot sensors")
        await self.coordinator.withdraw_pot(self.data, amount_in_minor_units)