from aiohttp import ClientSession, ClientResponse, FormData
from abc import abstractmethod
import logging

from .models import AccountModel, BalanceModel, PotModel

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
        accountModels = [AccountModel(a) for a in data['accounts'] if 'account_number' in a]
        return accountModels

    async def get_balance(self, account_id):
        resp = await self.make_request("GET", f"balance?account_id={account_id}")
        data = await resp.json()
        balanceModel = BalanceModel(account_id, data)
        return balanceModel

    async def get_pots(self, account_id):
        resp = await self.make_request("GET", f"pots?current_account_id={account_id}")
        data = await resp.json()
        potsModel = [PotModel(account_id, pot) for pot in data['pots']]
        return potsModel

    async def register_webhook(self, account_id, url):
        _LOGGER.debug("Registering Monzo account webhook: %s : %s", account_id, url)
        postData = { 'account_id': account_id, 'url': url}
        resp = await self.make_request("POST", f"webhooks", data=FormData(postData))
        data = await resp.json()
        _LOGGER.debug("Registered Monzo account webhook using form data: %s", str(data))
        return data

