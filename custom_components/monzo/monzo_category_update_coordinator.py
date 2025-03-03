"""Example integration using DataUpdateCoordinator."""

from datetime import timedelta, date
import logging
import asyncio
from functools import reduce
from typing import Any, AsyncIterator

import async_timeout
from .api.models.transaction import Transaction

from .monzo_data import MonzoData
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api.models.pot import Pot

_LOGGER = logging.getLogger(__name__)

sem = asyncio.Semaphore(1)

def reduce_transactions(a: dict[str, int], b: Transaction) -> dict[str, int]:
    if b.category in a:
        a[b.category] += b.amount
    else:
        a[b.category] = b.amount
    return a

class MonzoCategoryUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, client: MonzoData, accountIds):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Monzo Transactions",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(hours=6),
        )
        self._monzo_client = client
        self._accountIds = accountIds

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
            twenty_eighth = date.today().replace(day=28)
            if date.today() < twenty_eighth:
                twenty_eighth = twenty_eighth.replace(month=twenty_eighth.month-1)
            data = self._monzo_client.async_get_transactions(self._accountIds[0], twenty_eighth)
            categories = {}
            async for transaction in data:
                for category, amount in transaction.categories.items():
                    if category not in categories:
                        categories[category] = 0
                    categories[category] += amount
            return categories
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")

    async def async_force_update(self):
        if not sem.locked():
            async with sem:
                data = await self._async_update_data()
                await self.async_set_updated_data(data)