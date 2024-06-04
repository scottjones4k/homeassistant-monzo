"""Example integration using DataUpdateCoordinator."""

from datetime import timedelta
import logging

import async_timeout

from homeassistant.components.light import LightEntity
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .models import PotModel

_LOGGER = logging.getLogger(__name__)

class MonzoUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, client):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Monzo",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(minutes=5),
        )
        self._monzo_client = client

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # try:
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        async with async_timeout.timeout(10):
            # Grab active context variables to limit data required to be fetched from API
            # Note: using context is not required if there is no need or ability to limit
            # data retrieved from API.
            listening_idx = set(self.async_contexts())
            return await self._monzo_client.async_update_coordinated(listening_idx)
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")
    
    async def register_webhook(self, account_id, url):
        await self._monzo_client.register_webhook(account_id, url)

    async def unregister_webhook(self, webhook_id):
        await self._monzo_client.unregister_webhook(webhook_id)

    async def deposit_pot(self, pot: PotModel, amount: int):
        return await self._monzo_client.deposit_pot(pot, amount)

    async def withdraw_pot(self, pot: PotModel, amount: int):
        return await self._monzo_client.withdraw_pot(pot, amount)