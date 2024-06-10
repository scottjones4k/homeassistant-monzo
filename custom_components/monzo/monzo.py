from aiohttp import ClientSession, ClientResponse
from abc import abstractmethod
import logging
import secrets

from .models import AccountModel, BalanceModel, PotModel, WebhookModel

_LOGGER = logging.getLogger(__name__)

TOKEN_EXPIRY_CODE = "unauthorized.bad_access_token.expired"
TOKEN_INSUFFICIENT_PERMISSIONS = "forbidden.insufficient_permissions"
CODE = "code"

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

        response = await self._auth._websession.request(
            method, f"{self._host}/{url}", **kwargs, headers=headers,
        )
        return await response.json()

    async def get_accounts(self):
        data = await self.make_request("GET", "accounts")
        try:
            accounts = [AccountModel(a) for a in data['accounts'] if 'account_number' in a]
        except KeyError:
            _LOGGER.error("Failed to get accounts from Monzo API: %s", str(data))
            _raise_auth_or_response_error(data)
        return accounts

    async def get_balance(self, account_id, account_mask, account_name):
        data = await self.make_request("GET", f"balance?account_id={account_id}")
        try:
            balance =  BalanceModel(account_id, account_mask, account_name, data)
        except KeyError:
            _LOGGER.error("Failed to get balance from Monzo API: %s", str(data))
            _raise_auth_or_response_error(data)
        return balance

    async def get_pots(self, account_id, account_mask):
        data = await self.make_request("GET", f"pots?current_account_id={account_id}")
        try:
            pots = [PotModel(account_id, account_mask, pot) for pot in data['pots'] if not pot['deleted']]
        except KeyError:
            _LOGGER.error("Failed to get pots from Monzo API: %s", str(data))
            _raise_auth_or_response_error(data)
        return pots

    async def get_webhooks(self, account_id):
        data = await self.make_request("GET", f"webhooks?account_id={account_id}")
        try:
            webhooks = [WebhookModel(hook) for hook in data['webhooks']]
        except KeyError:
            _LOGGER.error("Failed to get webhooks from Monzo API: %s", str(data))
            _raise_auth_or_response_error(data)
        return webhooks

    async def register_webhook(self, account_id, url):
        existing = await self.get_webhooks(account_id)
        found_hooks = [w for w in existing if w.account_id == account_id and w.url == url]
        if any(found_hooks):
            _LOGGER.debug("Found existing Monzo account webhook: %s : %s", account_id, url)
            return found_hooks[0]
        _LOGGER.debug("Registering Monzo account webhook: %s : %s", account_id, url)
        post_data = { 'account_id': account_id, 'url': url}
        data = await self.make_request("POST", "webhooks", data=post_data)
        _LOGGER.debug("Registered Monzo account webhook using data: %s", str(data))
        return WebhookModel(data['webhook'])

    async def unregister_webhook(self, webhook_id):
        _LOGGER.debug("Unregistering Monzo account webhook: %s", webhook_id)
        data = await self.make_request("DELETE", f"webhooks/{webhook_id}")
        _LOGGER.debug("Unregistered Monzo account webhook using data: %s", str(data))
        return data

    async def deposit_pot(self, pot: PotModel, amount: int):
        _LOGGER.debug("Depositing into pot: %s", pot.id)
        post_data = { 'source_account_id': pot.account_id, 'amount': amount, 'dedupe_id': secrets.token_hex()}
        data = await self.make_request("PUT", f"pots/{pot.id}/deposit", data=post_data)
        _LOGGER.debug("Deposit success: %s", str(data))
        return PotModel(pot.account_id, pot.mask, data)

    async def withdraw_pot(self, pot: PotModel, amount: int):
        _LOGGER.debug("Depositing into pot: %s", pot.id)
        post_data = { 'destination_account_id': pot.account_id, 'amount': amount, 'dedupe_id': secrets.token_hex()}
        data = await self.make_request("PUT", f"pots/{pot.id}/withdraw", data=post_data)
        _LOGGER.debug("Deposit success: %s", str(data))
        return PotModel(pot.account_id, pot.mask, data)

async def _authorisation_expired(response: dict[str, Any]) -> bool:
    return CODE in response and response[CODE] == TOKEN_EXPIRY_CODE

async def _insufficient_permissions(response: dict[str, Any]) -> bool:
    return CODE in response and response[CODE] == TOKEN_INSUFFICIENT_PERMISSIONS

async def _raise_auth_or_response_error(response: dict[str, Any]) -> None:
    if _authorisation_expired(response):
        raise AuthorisationExpiredError
    elif _insufficient_permissions(response):
        raise InsufficientPermissionsError
    raise InvalidMonzoAPIResponseError

class InvalidMonzoAPIResponseError(Exception):
    """Error thrown when the external Monzo API returns an invalid response."""

    def __init__(self, *args: object) -> None:
        """Initialise error."""
        super().__init__(*args)

class AuthorisationExpiredError(Exception):
    """Error thrown when the external Monzo API authentication has expired."""

    def __init__(self, *args: object) -> None:
        """Initialise error."""
        super().__init__(*args)

class InsufficientPermissionsError(Exception):
    """Error thrown when the external Monzo API authentication has expired."""

    def __init__(self, *args: object) -> None:
        """Initialise error."""
        super().__init__(*args)