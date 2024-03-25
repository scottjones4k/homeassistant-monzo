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

    async def async_update_coordinated(self, _listening_idx):
        lookup_table = {}
        accounts = await self.async_update_accounts_list()
        for account in accounts:
            balance = await self.async_update_balance_for_account(account.id, account.mask)
            pots = await self.async_update_pots_for_account(account.id, account.mask)
            webhooks = await self.async_update_webhooks_for_account(account.id)
            lookup_table[account.id] = balance
            for pot in pots:
                lookup_table[pot.id] = pot
            for webhook in webhooks:
                lookup_table[webhook.id] = webhook
        return lookup_table

    async def async_update(self):
        await self.async_update_accounts()
        await self.async_update_balances()
        await self.async_update_pots()
        await self.async_update_webhooks()
        return self.accounts

    @Throttle(MIN_TIME_BETWEEN_ACCOUNT_UPDATES)
    async def async_update_accounts(self):
        accounts = await self._monzo_client.get_accounts()
        self.accounts = accounts
        return accounts

    async def async_update_accounts_list(self):
        accounts = await self._monzo_client.get_accounts()
        return accounts

    @Throttle(MIN_TIME_BETWEEN_BALANCE_UPDATES)
    async def async_update_balances(self):
        for account in self.accounts:
            self.balances[account.id] = await self._monzo_client.get_balance(account.id, account.mask)

    async def async_update_balance_for_account(self, account_id, account_mask):
        return await self._monzo_client.get_balance(account_id, account_mask)

    @Throttle(MIN_TIME_BETWEEN_BALANCE_UPDATES)
    async def async_update_pots(self):
        for account in self.accounts:
            pots = await self._monzo_client.get_pots(account.id, account.mask)
            self.pots[account.id] = pots

    async def async_update_pots_for_account(self, account_id, account_mask):
        return await self._monzo_client.get_pots(account_id, account_mask)

    @Throttle(MIN_TIME_BETWEEN_ACCOUNT_UPDATES)
    async def async_update_webhooks(self):
        for account in self.accounts:
            self.webhooks[account.id] = await self._monzo_client.get_webhooks(account.id)

    async def async_update_webhooks_for_account(self, account_id):
        return await self._monzo_client.get_webhooks(account_id)

    async def register_webhook(self, account_id, url):
        self.webhooks[account_id] = await self._monzo_client.register_webhook(account_id, url)

    async def unregister_webhook(self, webhook_id):
        await self._monzo_client.unregister_webhook(webhook_id)

    async def deposit_pot(self, account_id: str, pot_id: str, amount: int):
        new_pot = await self._monzo_client.deposit_pot(account_id, pot_id, amount)
        pot = next(a for a in self.pots[account_id] if a.id == new_pot.id)
        pot.balance = new_pot.balance
        return new_pot

    async def withdraw_pot(self, account_id: str, pot_id: str, amount: int):
        new_pot = await self._monzo_client.withdraw_pot(account_id, pot_id, amount)
        pot = next(a for a in self.pots[account_id] if a.id == new_pot.id)
        pot.balance = new_pot.balance
        return new_pot
