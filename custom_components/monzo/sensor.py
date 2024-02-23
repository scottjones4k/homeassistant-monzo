"""Support for Plaid sensors."""
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

from .monzo import MonzoClient

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
    instance: MonzoClient = hass.data[DOMAIN][config_entry.entry_id]["client"]

    entities: list[SensorEntity] = []

    for account in await instance.get_accounts():
        if 'account_number' in account:
            balance = await instance.get_balance(account['id'])
            entities.append(BalanceSensor(instance, account, balance))
    async_add_entities(entities)


class BalanceSensor(SensorEntity):
    """Representation of a Monzo sensor."""

    def __init__(self, monzo_client, account, balance):
        """Initialize the sensor."""
        self._monzo_client = monzo_client
        self._account = account
        self._balance = balance
        self._mask = account['account_number'][-5:]
        
        self.entity_id = ENTITY_ID_FORMAT.format(f"monzo-{self._mask}-balance")
        self._attr_name = f"{self._mask} Balance"
        self._attr_unique_id = self.entity_id
        self._attr_state_class = SensorStateClass.TOTAL

        self._state = self._balance['balance']/100
        self._unit_of_measurement = self._balance['currency']

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
        self._balance = await self._monzo_client.get_balance(self._account['id'])

        self._state = self._balance['balance']/100
        self._unit_of_measurement = self._balance['currency']