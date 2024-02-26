"""Support for Monzo sensors."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass, ENTITY_ID_FORMAT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN
)

from .monzo_data import MonzoData
from .models import BalanceModel, PotModel

_LOGGER = logging.getLogger(__name__)

ATTR_NATIVE_BALANCE = "Balance in native currency"

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by Monzo"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monzo sensor platform."""
    instance: MonzoData = hass.data[DOMAIN][config_entry.entry_id]["client"]

    entities: list[SensorEntity] = []

    await instance.async_update()
    for account in instance.accounts:
        entities.append(BalanceSensor(instance, account))
        for pot in instance.pots[account['id']]:
            entities.append(PotSensor(instance, pot))
    async_add_entities(entities)


class MonzoSensor(SensorEntity):
    """Representation of a Monzo sensor."""

    def __init__(self, monzo_data, account):
        """Initialize the sensor."""
        self._monzo_data = monzo_data
        self._account_id = account['id']
        self._mask = account['account_number'][-4:]
        
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_suggested_display_precision = 2

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
            'Mask': self._mask,
        }

    async def async_update(self):
        """Get the latest state of the sensor."""
        await self._monzo_data.async_update()

class BalanceSensor(MonzoSensor):
    """Representation of a Balance sensor."""

    def __init__(self, monzo_data, account):
        """Initialize the sensor."""
        super().__init__(monzo_data, account)
        self._balance: BalanceModel = monzo_data.balances[self._account_id]
        
        self.entity_id = ENTITY_ID_FORMAT.format(f"monzo-{self._mask}-balance")
        self._attr_name = f"Monzo {self._mask} Balance"
        self._attr_unique_id = self.entity_id

        self._state = self._balance.balance/100
        self._unit_of_measurement = self._balance.currency

    async def async_update(self):
        """Get the latest state of the sensor."""
        await super().async_update()
        self._balance = self._monzo_data.balances[self._account_id]

        self._state = self._balance.balance/100
        self._unit_of_measurement = self._balance.currency

class PotSensor(MonzoSensor):
    """Representation of a Pot sensor."""

    def __init__(self, monzo_data, pot: PotModel):
        """Initialize the sensor."""
        account = next(a for a in monzo_data.accounts if a['id'] == pot.account_id)
        super().__init__(monzo_data, account)
        self._pot: PotModel = pot
        
        self.entity_id = ENTITY_ID_FORMAT.format(f"monzo-{self._pot.name}-pot")
        self._attr_name = f"Monzo {self._pot.name} Pot"
        self._attr_unique_id = self.entity_id

        self._state = self._pot.balance/100
        self._unit_of_measurement = self._pot.currency

    async def async_update(self):
        """Get the latest state of the sensor."""
        await super().async_update()
        self._pot: PotModel = next(p for p in self._monzo_data.pots[self._pot.account_id] if p.id == self._pot.id)

        self._state = self._pot.balance/100
        self._unit_of_measurement = self._pot.currency