import aiohttp
from typing import Any, Optional

class VLRClient:
    def __init__(self, base_url: str= "https://vlrggapi.vercel.app"):
        self.base_url = base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get(self, path: str, params: Optional[dict] = None) -> Any:
        """
        Perform a GET to the VLR API. `path` is relative (no leading slash required).
        Example: await client.get("matches/12345")
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        session = await self._get_session()
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()
