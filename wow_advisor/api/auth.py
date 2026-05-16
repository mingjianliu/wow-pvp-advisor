import asyncio
import time
import httpx


class BnetAuth:
    _TOKEN_URL = "https://oauth.battle.net/token"

    def __init__(self, client_id: str, client_secret: str, region: str = "us"):
        self._client_id = client_id
        self._client_secret = client_secret
        self._region = region
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        async with self._lock:
            # double-check after acquiring lock
            if self._token and time.time() < self._expires_at - 60:
                return self._token
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._TOKEN_URL,
                    data={"grant_type": "client_credentials"},
                    auth=(self._client_id, self._client_secret),
                )
                resp.raise_for_status()
                data = resp.json()
                self._token = data["access_token"]
                self._expires_at = time.time() + data["expires_in"]
                return self._token
