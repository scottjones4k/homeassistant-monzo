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
        self.webhooks = {}

    async def async_update(self):
        await self.async_update_accounts()
        await self.async_update_balances()
        await self.async_update_pots()
        await self.async_update_webhooks()

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

    @Throttle(MIN_TIME_BETWEEN_ACCOUNT_UPDATES)
    async def async_update_webhooks(self):
        for account in self.accounts:
            self.webhooks[account.id] = await self._monzo_client.get_webhooks(account.id)

    async def register_webhook(self, account_id, url):
        self.webhooks[account_id] = await self._monzo_client.register_webhook(account_id, url)

    async def unregister_webhook(self, account_id):
        webhook_id = self.webhooks[account_id].id
        await self._monzo_client.unregister_webhook(webhook_id)

    async def deposit_pot(self, account_id: str, pot_id: str, amount: int):
        new_pot = await self._monzo_client.deposit_pot(account_id, pot_id, amount)
        pot = next(a for a in self.pots[account_id] if a.id == pot.id)
        pot.balance = new_pot.balance
        return new_pot
