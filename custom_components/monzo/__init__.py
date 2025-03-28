"""The Monzo integration."""
from __future__ import annotations

from aiohttp import web
import secrets
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow
from homeassistant.components import webhook
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api.models.transaction import TransactionWrapper

from .const import DOMAIN, WEBHOOK_UPDATE
from .monzo import AsyncConfigEntryAuth
from .monzo_data import MonzoData
from .monzo_update_coordinator import MonzoUpdateCoordinator
from .monzo_category_update_coordinator import MonzoCategoryUpdateCoordinator
from .services import setup_services

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.EVENT]

_LOGGER = logging.getLogger(__name__)

async def handle_webhook(hass, webhook_id, request):
    """Handle incoming webhook with Monzo Client request."""
    data = await request.json()
    transaction_wrapper = TransactionWrapper(**data)
    account_id = transaction_wrapper.data.account_id

    async_dispatcher_send(
        hass,
        f"{WEBHOOK_UPDATE}-{account_id}",
        transaction_wrapper.type,
        transaction_wrapper.data,
    )
    _LOGGER.info("Received Monzo webhook: %s", account_id)
    return web.Response(text="Logged")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Monzo from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    # If using an aiohttp-based API lib
    auth = AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(hass), session
    )

    client = MonzoData(auth)

    coordinator = MonzoUpdateCoordinator(hass, client)

    await coordinator.async_config_entry_first_refresh()

    account_ids = [idx for idx, ent in coordinator.data.items() if idx.startswith("acc")]
    
    category_coordinator = MonzoCategoryUpdateCoordinator(hass, client, account_ids)

    await category_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "category_coordinator": category_coordinator
    }

    if CONF_WEBHOOK_ID not in entry.data:
        data = {**entry.data, CONF_WEBHOOK_ID: secrets.token_hex()}
        hass.config_entries.async_update_entry(entry, data=data)

    webhook_url = webhook.async_generate_url(hass, entry.data[CONF_WEBHOOK_ID])
    webhook.async_register(
        hass, DOMAIN, "Monzo", entry.data[CONF_WEBHOOK_ID], handle_webhook
    )
    
    for idx in account_ids:
        await coordinator.register_webhook(idx, webhook_url)
        _LOGGER.info("Registered Monzo account webhook: %s : %s", idx, webhook_url)
    _LOGGER.info("Registered HASS Monzo webhook: %s", webhook_url)

    setup_services(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        config = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator = config["coordinator"]
        for idx, ent in coordinator.data.items():
            if idx.startswith("webhook"):
                await coordinator.unregister_webhook(idx)

    return unload_ok