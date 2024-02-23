from aiohttp import ClientSession, ClientResponse
from abc import abstractmethod

class AbstractAuth:
    def __init__(self, websession: ClientSession, host: str):
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

        access_token = await self.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        return await self._websession.request(
            method, f"{self._host}/{url}", **kwargs, headers=headers,
        )

    async def get_accounts(self):
        resp = await self.make_request("GET", "accounts")
        data = await resp.json()
        return data['accounts']

    async def get_balance(self, account_id):
        resp = await self.make_request("GET", f"balance?account_id={account_id}")
        balance = await resp.json()
        return balance
