from .const import API_ENDPOINT
from .monzo import AbstractAuth
from .api.client import MonzoClient
from .api.models import PotModel

class MonzoData:
    def __init__(self, auth: AbstractAuth):
        self._monzo_client = MonzoClient(auth, API_ENDPOINT)
        self.webhooks = {}

    async def async_update_coordinated(self, _listening_idx):
        lookup_table = {}
        accounts = await self.async_update_accounts_list()
        for account in accounts:
            balance = await self.async_update_balance_for_account(account.id)
            balance.name = account.name
            pots = await self.async_update_pots_for_account(account.id)
            webhooks = await self.async_update_webhooks_for_account(account.id)
            lookup_table[account.id] = balance
            for pot in pots:
                lookup_table[pot.id] = pot
            for webhook in webhooks:
                lookup_table[webhook.id] = webhook
        return lookup_table

    async def async_update_accounts_list(self):
        accounts = await self._monzo_client.get_accounts()
        return accounts

    async def async_update_balance_for_account(self, account_id):
        return await self._monzo_client.get_balance(account_id)

    async def async_update_pots_for_account(self, account_id):
        return await self._monzo_client.get_pots(account_id)

    async def async_update_webhooks_for_account(self, account_id):
        return await self._monzo_client.get_webhooks(account_id)

    async def register_webhook(self, account_id, url):
        self.webhooks[account_id] = await self._monzo_client.register_webhook(account_id, url)

    async def unregister_webhook(self, webhook_id):
        await self._monzo_client.unregister_webhook(webhook_id)

    async def deposit_pot(self, pot: PotModel, amount: int):
        new_pot = await self._monzo_client.deposit_pot(pot, amount)
        pot.balance = new_pot.balance
        return new_pot

    async def withdraw_pot(self, pot: PotModel, amount: int):
        new_pot = await self._monzo_client.withdraw_pot(pot, amount)
        pot.balance = new_pot.balance
        return new_pot
