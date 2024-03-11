"""Support for Monzo sensors."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity, SensorStateClass, ENTITY_ID_FORMAT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from abc import abstractmethod
from .const import (
    DOMAIN,
    SERVICE_POT_DEPOSIT,
    SERVICE_POT_WITHDRAW
)

from .monzo_data import MonzoData
from .models import AccountModel, BalanceModel, PotModel
from .monzo_update_coordinator import MonzoUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTR_NATIVE_BALANCE = "Balance in native currency"

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by Monzo"

POT_SERVICE_SCHEMA = {
    vol.Required('amount_in_minor_units'): vol.All(vol.Coerce(int), vol.Range(0, 65535)),
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monzo sensor platform."""
    coordinator: MonzoUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        BalanceSensor(coordinator, idx) for idx, ent in coordinator.data.items()
    )

    async_add_entities(
        SpendTodaySensor(coordinator, idx) for idx, ent in coordinator.data.items() if idx.startswith("acc")
    )

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

class MonzoSensor(SensorEntity):
    """Representation of a Monzo sensor."""

    def __init__(self, monzo_data, account):
        """Initialize the sensor."""
        self._monzo_data = monzo_data
        self._account_id = account.id
        self._mask = account.mask
        
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_suggested_display_precision = 2
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account.id)}, name=f"Monzo Account {self._mask}"
        )
        self._attr_has_entity_name = True

    @property
    def available(self):
        """Return the availability of the sensor."""
        return True

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return DEFAULT_COIN_ICON

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            'Account Mask': self._mask,
        }

    async def async_update(self):
        """Get the latest state of the sensor."""
        await self._monzo_data.async_update()
        self.update_balance()
        self._state = self._balance.balance

    @abstractmethod
    def update_balance(self):
        """Updates self._balance"""

    @abstractmethod
    async def pot_deposit(self, amount_in_minor_units: int | None = None):
        """Deposit into pot"""

class BalanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Balance sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        idx
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        data = self.coordinator.data[self.idx]

        if isinstance(data, BalanceModel):
            self._balance_type = "account"
            self.entity_id = ENTITY_ID_FORMAT.format(f"monzo-{data.mask}-balance")
            self._attr_name = f"Balance"
        else:
            self._balance_type = "pot"
            self.entity_id = ENTITY_ID_FORMAT.format(f"monzo-{data.name}-pot")
            self._attr_name = f"{data.name} Pot"   

        self._attr_unique_id = self.entity_id
        self._unit_of_measurement = data.currency

        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_suggested_display_precision = 2
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.account_id)}, name=f"Monzo Account {data.mask}"
        )
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self.idx].balance

    async def pot_deposit(self, amount_in_minor_units: int | None = None):
        if self._balance_type == "account":
            raise HomeAssistantError("supported only on Pot sensors")
        data = self.coordinator.data[self.idx]
        await self.coordinator._monzo_client.deposit_pot(data.account_id, data.id, amount_in_minor_units)

    async def pot_withdraw(self, amount_in_minor_units: int | None = None):
        if self._balance_type == "account":
            raise HomeAssistantError("supported only on Pot sensors")
        data = self.coordinator.data[self.idx]
        await self.coordinator._monzo_client.withdraw_pot(data.account_id, data.id, amount_in_minor_units)

class SpendTodaySensor(BalanceSensor):
    """Representation of a SpendToday sensor."""

    def __init__(self, coordinator, idx):
        """Initialize the sensor."""
        super().__init__(coordinator, idx)
        data = self.coordinator.data[self.idx]
        
        self.entity_id = ENTITY_ID_FORMAT.format(f"monzo-{data.mask}-spend-today")
        self._attr_name = f"Spend Today"
        self._attr_unique_id = self.entity_id

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self.idx].spend_today