import time
import pytest
import respx
import httpx
from wow_advisor.api.auth import BnetAuth


@pytest.fixture
def auth():
    return BnetAuth(client_id="test_id", client_secret="test_secret", region="us")


@respx.mock
async def test_fetch_token(auth):
    respx.post("https://oauth.battle.net/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "abc123",
            "expires_in": 86400,
            "token_type": "bearer",
        })
    )
    token = await auth.get_token()
    assert token == "abc123"


@respx.mock
async def test_token_cached(auth):
    route = respx.post("https://oauth.battle.net/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "abc123",
            "expires_in": 86400,
            "token_type": "bearer",
        })
    )
    await auth.get_token()
    await auth.get_token()
    assert route.call_count == 1


@respx.mock
async def test_token_refreshed_when_expired(auth):
    route = respx.post("https://oauth.battle.net/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "fresh_token",
            "expires_in": 86400,
            "token_type": "bearer",
        })
    )
    auth._token = "old_token"
    auth._expires_at = time.time() - 1  # already expired
    token = await auth.get_token()
    assert token == "fresh_token"
    assert route.call_count == 1
