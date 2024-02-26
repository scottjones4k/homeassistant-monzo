from datetime import timedelta

from homeassistant.util import Throttle

from .const import DOMAIN, API_ENDPOINT
from .monzo import MonzoClient

MIN_TIME_BETWEEN_ACCOUNT_UPDATES = timedelta(minutes=30)
MIN_TIME_BETWEEN_BALANCE_UPDATES = timedelta(minutes=5)

class MonzoData:
    def __init__(self, auth):
        self._monzo_client = MonzoClient(auth, API_ENDPOINT)
        self.accounts = []
        self.balances = {}
        self.pots = {}

    async def async_update(self):
        await self.async_update_accounts()
        await self.async_update_balances()
        await self.async_update_pots()
        pass

    @Throttle(MIN_TIME_BETWEEN_ACCOUNT_UPDATES)
    async def async_update_accounts(self):
        self.accounts = await self._monzo_client.get_accounts()

    @Throttle(MIN_TIME_BETWEEN_BALANCE_UPDATES)
    async def async_update_balances(self):
        for account in self.accounts:
            self.balances[account.id] = await self._monzo_client.get_balance(account.id)

    @Throttle(MIN_TIME_BETWEEN_BALANCE_UPDATES)
    async def async_update_pots(self):
        for account in self.accounts:
            self.pots[account.id] = await self._monzo_client.get_pots(account.id)