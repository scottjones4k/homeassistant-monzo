from aiohttp import ClientSession
from abc import abstractmethod


class AbstractAuth:
    def __init__(self, websession: ClientSession):
        """Initialize the auth."""
        self._websession = websession

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""