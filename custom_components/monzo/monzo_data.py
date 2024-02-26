from datetime import timedelta

from homeassistant.util import Throttle

from .const import DOMAIN, API_ENDPOINT
from .monzo import MonzoClient
from .models import BalanceModel, PotModel

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
        self.accounts = [a for a in await self._monzo_client.get_accounts() if 'account_number' in a]

    @Throttle(MIN_TIME_BETWEEN_BALANCE_UPDATES)
    async def async_update_balances(self):
        for account in self.accounts:
            self.balances[account['id']] = BalanceModel(account, await self._monzo_client.get_balance(account['id']))

    @Throttle(MIN_TIME_BETWEEN_BALANCE_UPDATES)
    async def async_update_pots(self):
        for account in self.accounts:
            pots = await self._monzo_client.get_pots(account['id'])
            self.pots[account['id']] = list(map(lambda pot: PotModel(account, pot), pots))