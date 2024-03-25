from aiohttp import ClientSession, ClientResponse
from abc import abstractmethod
import logging
import secrets

from .models import AccountModel, BalanceModel, PotModel, WebhookModel

_LOGGER = logging.getLogger(__name__)

class AbstractAuth:
    def __init__(self, websession: ClientSession):
        """Initialize the auth."""
        self._websession = websession

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

class MonzoClient:
    def __init__(self, auth: AbstractAuth, host):
        self._auth = auth
        self._host = host
    
    async def make_request(self, method, url, **kwargs) -> ClientResponse:
        """Make a request."""
        headers = kwargs.get("headers")

        if headers is None:
            headers = {}
        else:
            headers = dict(headers)

        access_token = await self._auth.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        return await self._auth._websession.request(
            method, f"{self._host}/{url}", **kwargs, headers=headers,
        )

    async def get_accounts(self):
        resp = await self.make_request("GET", "accounts")
        data = await resp.json()
        return [AccountModel(a) for a in data['accounts'] if 'account_number' in a]

    async def get_balance(self, account_id, account_mask):
        resp = await self.make_request("GET", f"balance?account_id={account_id}")
        data = await resp.json()
        return BalanceModel(account_id, account_mask, data)

    async def get_pots(self, account_id, account_mask):
        resp = await self.make_request("GET", f"pots?current_account_id={account_id}")
        data = await resp.json()
        return [PotModel(account_id, account_mask, pot) for pot in data['pots'] if not pot['deleted']]

    async def get_webhooks(self, account_id):
        resp = await self.make_request("GET", f"webhooks?account_id={account_id}")
        data = await resp.json()
        return [WebhookModel(hook) for hook in data['webhooks']]

    async def register_webhook(self, account_id, url):
        existing = await self.get_webhooks(account_id)
        found_hooks = [w for w in existing if w.account_id == account_id and w.url == url]
        if any(found_hooks):
            _LOGGER.debug("Found existing Monzo account webhook: %s : %s", account_id, url)
            return found_hooks[0]
        _LOGGER.debug("Registering Monzo account webhook: %s : %s", account_id, url)
        post_data = { 'account_id': account_id, 'url': url}
        resp = await self.make_request("POST", "webhooks", data=post_data)
        data = await resp.json()
        _LOGGER.debug("Registered Monzo account webhook using data: %s", str(data))
        return WebhookModel(data['webhook'])

    async def unregister_webhook(self, webhook_id):
        _LOGGER.debug("Unregistering Monzo account webhook: %s", webhook_id)
        resp = await self.make_request("DELETE", f"webhooks/{webhook_id}")
        data = await resp.json()
        _LOGGER.debug("Unregistered Monzo account webhook using data: %s", str(data))
        return data

    async def deposit_pot(self, account_id: str, pot_id: str, amount: int):
        _LOGGER.debug("Depositing into pot: %s", pot_id)
        post_data = { 'source_account_id': account_id, 'amount': amount, 'dedupe_id': secrets.token_hex()}
        resp = await self.make_request("PUT", f"pots/{pot_id}/deposit", data=post_data)
        data = await resp.json()
        _LOGGER.debug("Deposit success: %s", str(data))
        return PotModel(account_id, data)

    async def withdraw_pot(self, account_id: str, pot_id: str, amount: int):
        _LOGGER.debug("Depositing into pot: %s", pot_id)
        post_data = { 'destination_account_id': account_id, 'amount': amount, 'dedupe_id': secrets.token_hex()}
        resp = await self.make_request("PUT", f"pots/{pot_id}/withdraw", data=post_data)
        data = await resp.json()
        _LOGGER.debug("Deposit success: %s", str(data))
        return PotModel(account_id, data)

