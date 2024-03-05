"""Support for Monzo sensors."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DOMAIN,
    WEBHOOK_UPDATE
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
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Monzo event entities."""
    instance: MonzoData = hass.data[DOMAIN][config_entry.entry_id]["client"]

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
        self._attr_event_types = ['transaction.created', 'transaction.updated']
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
        _LOGGER.debug("Transaction event received %s: %s", event_type, str(transaction))
        if transaction['account_id'] == self._account_id and event_type == 'transaction.created':
            self._trigger_event(event_type, map_transaction(self._monzo_data, transaction))
            self.schedule_update_ha_state()

def map_transaction(monzo_data,transaction):
    pot_id = transaction['metadata'].get('pot_id')
    pot_name = None
    counterparty = {}
    match transaction['scheme']:
        case 'mastercard':
            transaction_type = 'Card Payment'
        case 'payport_faster_payments':
            transaction_type = 'Faster Payment'
            counterparty = {
                'account_number': transaction['counterparty']['account_number']
                'name': transaction['counterparty']['name']
                'sort_code': transaction['counterparty']['sort_code']
            }
        case 'uk_retail_pot':
            transaction_type = 'Pot Deposit'
            pot = next(p for p in monzo_data.pots[transaction['account_id']] if p.id == pot_id)
            pot_name = pot.name
        case _:
            _LOGGER.warn("Unknown transaction scheme: %s", transaction['scheme'])
            transaction_type = 'Unknown'
    return {
        'Incoming': transaction['amount'] > 0,
        'Amount': abs(transaction['amount']/100),
        'Description': transaction['description'],
        'Currency': transaction['currency'],
        'Date Time': transaction['created'],
        'Transaction Id': transaction['id'],
        'Account Id': transaction['account_id'],
        'Notes': transaction['metadata'].get('notes'),
        'Triggered By': transaction['metadata'].get('triggered_by'),
        'Android Pay': transaction['metadata'].get('tokenization_method') == 'android_pay'
        'Transaction Type': transaction_type,
        'Is Roundup': transaction['metadata'].get('trigger') == 'coin_jar',
        'Pot Id': pot_id,
        'Pot Name': pot_name,
        'Counterparty': counterparty
    }