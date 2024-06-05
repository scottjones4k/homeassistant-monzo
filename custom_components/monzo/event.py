"""Support for Monzo sensors."""
from __future__ import annotations

import logging

from typing import Any

from homeassistant.components.event import EventDeviceClass, EventEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from .monzo_update_coordinator import MonzoUpdateCoordinator

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
    coordinator: MonzoUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_add_entities(
        MonzoTransactionEventEntity(coordinator, idx) for idx, ent in coordinator.data.items() if idx.startswith("acc")
    )


class MonzoTransactionEventEntity(EventEntity):
    """Representation of a Monzo Event Entity."""

    def __init__(self, coordinator, idx):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.idx = idx

        self._mask = self.coordinator.data[self.idx].mask

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, str(self.idx))},
            manufacturer="Monzo",
            model=self.data.name,
            name=self.data.name,
        )
        self.entity_description = EventEntityDescription(
            key="last_transaction", 
            translation_key="last_transaction",
            device_class=EventDeviceClass.MONETARY,
            event_types=['transaction.created', 'transaction.updated']
        )
        self._attr_unique_id = f"{self.idx}_{self.entity_description.key}"
        self._attr_has_entity_name = True

    @property
    def data(self) -> dict[str, Any]:
        """Shortcut to access coordinator data for the entity."""
        return self.coordinator.data[self.idx]

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, f"{WEBHOOK_UPDATE}-{self.idx}", self._async_receive_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up after entity before removal."""
        await super().async_will_remove_from_hass()
        self._unsub_dispatcher()

    @callback
    async def _async_receive_data(self, event_type, transaction) -> None:
        _LOGGER.debug("Transaction event received %s: %s", event_type, str(transaction))
        if transaction['account_id'] == self.idx and event_type == 'transaction.created':
            self._trigger_event(event_type, map_transaction(self.coordinator, transaction))
            self.schedule_update_ha_state()

def map_transaction(coordinator,transaction):
    pot_id = transaction['metadata'].get('pot_id')
    pot_name = None
    counterparty = {}
    match transaction['scheme']:
        case 'mastercard':
            if transaction.get('atm_fee_detailed') is not None and 'withdrawal_amount' in transaction['atm_fee_detailed']:
                transaction_type = 'ATM Withdrawal'
            else:
                transaction_type = 'Card Payment'
        case 'payport_faster_payments':
            transaction_type = 'Faster Payment'
            counterparty = {
                'account_number': transaction['counterparty']['account_number'],
                'name': transaction['counterparty']['name'],
                'sort_code': transaction['counterparty']['sort_code']
            }
        case 'uk_retail_pot':
            transaction_type = 'Pot Deposit'
            pot_name = coordinator.data[pot_id].name
        case 'monzo_paid':
            transaction_type = 'Monzo Fee'
        case 'bacs':
            transaction_type = 'Direct Debit'
            counterparty = {
                'account_number': transaction['counterparty']['account_number'],
                'name': transaction['counterparty']['name'],
                'sort_code': transaction['counterparty']['sort_code']
            }
            if 'bills_pot_id' in transaction['metadata']:
                pot_id = transaction['metadata'].get('bills_pot_id')
                pot_name = coordinator.data[pot_id].name
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
        'Android Pay': transaction['metadata'].get('tokenization_method') == 'android_pay',
        'Transaction Type': transaction_type,
        'Is Roundup': transaction['metadata'].get('trigger') == 'coin_jar',
        'Is Bill Payment': transaction['metadata'].get('trigger') == 'committed_spending',
        'Pot Id': pot_id,
        'Pot Name': pot_name,
        'Counterparty': counterparty
    }