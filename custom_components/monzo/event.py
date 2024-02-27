"""Support for Monzo sensors."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN
)

from homeassistant.components.event import (
    ENTITY_ID_FORMAT,
    EventDeviceClass,
    EventEntity,
)

_LOGGER = logging.getLogger(__name__)

ATTR_NATIVE_BALANCE = "Balance in native currency"

DEFAULT_COIN_ICON = "mdi:cash"

ATTRIBUTION = "Data provided by Monzo"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Monzo event entities."""
    instance = hass.data[DOMAIN][entry.entry_id]

    entities: list[MonzoTransactionEventEntity] = []

    for account in instance.accounts:
        entities.append(MonzoTransactionEventEntity(instance, account))
    async_add_entities(entities)


class MonzoTransactionEventEntity(EventEntity):
    """Representation of a Monzo Event Entity."""

    def __init__(self, monzo_data, account):
        """Initialize the sensor."""
        self._monzo_data = monzo_data
        self._account_id = account.id
        self._mask = account.mask

        self.entity_id = ENTITY_ID_FORMAT.format(f"monzo-{account.mask}-transactions")

        self._attr_name = f"Monzo {account.mask} Transactions"
        self._attr_event_types = ['transaction.created']
        self._attr_unique_id = self.entity_id

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, f"{WEBHOOK_UPDATE}-{self._account_id}", self._async_receive_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up after entity before removal."""
        await super().async_will_remove_from_hass()
        self._unsub_dispatcher()

    @callback
    async def _async_receive_data(self, event_type, transaction) -> None:
        _LOGGER.info("Transaction event fired %s: %s", event_type, self._account_id)
        if transaction.account_id == self._account_id:
            self._trigger_event(event_type, map_transaction(transaction))
            self.schedule_update_ha_state()

def map_transaction(transaction):
    return {
        'Amount': transaction['amount'],
        'Description': transaction['description'],
        'Currency': transaction['currency'],
        'Date Time': transaction['created'],
        'Transaction Id': transaction['id']
    }