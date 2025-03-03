"""Support for Monzo sensors."""
from __future__ import annotations

import logging

from typing import Any

from homeassistant.components.event import EventEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .api.models.transaction import Transaction

from .monzo_update_coordinator import MonzoUpdateCoordinator
from .const import (
    DOMAIN,
    WEBHOOK_UPDATE
)

from homeassistant.components.event import (
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

    def __init__(self, coordinator: MonzoUpdateCoordinator, idx):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.idx = idx

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
    async def _async_receive_data(self, event_type: str, transaction: Transaction) -> None:
        _LOGGER.debug("Transaction event received %s: %s", event_type, str(transaction))
        if transaction.account_id == self.idx and event_type == 'transaction.created':
            self._trigger_event(event_type, map_transaction(self.coordinator, transaction))
            self.schedule_update_ha_state()
            await self.coordinator.async_force_update()

def map_transaction(coordinator: MonzoUpdateCoordinator, transaction: Transaction):
    pot_id = transaction.metadata.pot_id
    pot_name = None
    counterparty = {}
    match transaction.scheme:
        case 'mastercard':
            if transaction.atm_fee_detailed is not None and transaction.atm_fee_detailed.withdrawal_amount is not None:
                transaction_type = 'ATM Withdrawal'
            else:
                transaction_type = 'Card Payment'
        case 'payport_faster_payments':
            transaction_type = 'Faster Payment'
            counterparty = {
                'account_number': transaction.counterparty.account_number,
                'name': transaction.counterparty.name,
                'sort_code': transaction.counterparty.sort_code
            }
        case 'uk_retail_pot':
            transaction_type = 'Pot Deposit'
            pot_name = coordinator.data[pot_id].name
        case 'monzo_paid':
            transaction_type = 'Monzo Fee'
        case 'bacs':
            transaction_type = 'Direct Debit'
            counterparty = {
                'account_number': transaction.counterparty.account_number,
                'name': transaction.counterparty.name,
                'sort_code': transaction.counterparty.sort_code
            }
            if transaction.metadata.bills_pot_id is not None:
                pot_id = transaction.metadata.bills_pot_id
                pot_name = coordinator.data[pot_id].name
        case _:
            _LOGGER.warn("Unknown transaction scheme: %s", transaction.scheme)
            transaction_type = 'Unknown'
    return {
        'Incoming': transaction.amount > 0,
        'Amount': abs(transaction.amount/100),
        'Description': transaction.description,
        'Currency': transaction.currency,
        'Date Time': transaction.created,
        'Transaction Id': transaction.id,
        'Account Id': transaction.account_id,
        'Notes': transaction.metadata.notes,
        'Triggered By': transaction.metadata.triggered_by,
        'Android Pay': transaction.metadata.tokenization_method == 'android_pay',
        'Transaction Type': transaction_type,
        'Is Roundup': transaction.metadata.triggered_by == 'coin_jar',
        'Is Bill Payment': transaction.metadata.trigger == 'committed_spending',
        'Pot Id': pot_id,
        'Pot Name': pot_name,
        'Counterparty': counterparty,
        'Declined': transaction.decline_reason is not None,
        'Decline Reason': transaction.decline_reason,
        'Categories': transaction.categories
    }