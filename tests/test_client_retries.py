import pytest
import respx
import httpx
import asyncio
from unittest.mock import AsyncMock, patch
from wow_advisor.api.client import BnetClient

@pytest.fixture
def mock_auth():
    auth = AsyncMock()
    auth.get_token.return_value = "test_token"
    return auth

@pytest.fixture
def client(mock_auth):
    return BnetClient(auth=mock_auth, region="us")

@respx.mock
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_429_success(mock_sleep, client):
    # Case 1: 429 followed by 200
    route = respx.get("https://us.api.blizzard.com/test-url").side_effect = [
        httpx.Response(429),
        httpx.Response(200, json={"status": "ok"})
    ]
    
    async with httpx.AsyncClient() as http_client:
        result = await client._get(http_client, "https://us.api.blizzard.com/test-url", "test-namespace")
        
    assert result == {"status": "ok"}
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_with(2 ** 0) # First attempt is 0, sleep is 2^0 = 1

@respx.mock
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_429_exhausted(mock_sleep, client):
    # Case 2: Three consecutive 429s
    route = respx.get("https://us.api.blizzard.com/test-url").side_effect = [
        httpx.Response(429),
        httpx.Response(429),
        httpx.Response(429)
    ]
    
    async with httpx.AsyncClient() as http_client:
        result = await client._get(http_client, "https://us.api.blizzard.com/test-url", "test-namespace")
        
    assert result is None
    assert mock_sleep.call_count == 3
    # Attempts are 0, 1, 2. Sleeps are 2^0=1, 2^1=2, 2^2=4
    assert mock_sleep.call_args_list[0].args[0] == 1
    assert mock_sleep.call_args_list[1].args[0] == 2
    assert mock_sleep.call_args_list[2].args[0] == 4

@respx.mock
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_timeout(mock_sleep, client):
    # Verification of timeout retry logic
    respx.get("https://us.api.blizzard.com/test-url").side_effect = [
        httpx.TimeoutException("timeout"),
        httpx.Response(200, json={"status": "ok"})
    ]
    
    async with httpx.AsyncClient() as http_client:
        result = await client._get(http_client, "https://us.api.blizzard.com/test-url", "test-namespace")
        
    assert result == {"status": "ok"}
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_with(1) # Timeout sleep is constant 1


@respx.mock
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_500_success(mock_sleep, client):
    # A transient server error must not escape _get: it propagates out of the
    # asyncio.gather over a full roster and aborts the whole spec fetch.
    respx.get("https://us.api.blizzard.com/test-url").side_effect = [
        httpx.Response(500),
        httpx.Response(200, json={"status": "ok"}),
    ]

    async with httpx.AsyncClient() as http_client:
        result = await client._get(http_client, "https://us.api.blizzard.com/test-url", "test-namespace")

    assert result == {"status": "ok"}
    assert mock_sleep.call_count == 1


@respx.mock
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_500_exhausted_returns_none(mock_sleep, client):
    respx.get("https://us.api.blizzard.com/test-url").side_effect = [
        httpx.Response(500),
        httpx.Response(503),
        httpx.Response(502),
    ]

    async with httpx.AsyncClient() as http_client:
        result = await client._get(http_client, "https://us.api.blizzard.com/test-url", "test-namespace")

    assert result is None
    assert mock_sleep.call_count == 3


@respx.mock
async def test_client_error_still_raises(client):
    # 4xx that is not 404/429 is a real bug (bad namespace, revoked token) and
    # must stay loud rather than being retried into a silent None.
    respx.get("https://us.api.blizzard.com/test-url").mock(return_value=httpx.Response(403))

    async with httpx.AsyncClient() as http_client:
        with pytest.raises(httpx.HTTPStatusError):
            await client._get(http_client, "https://us.api.blizzard.com/test-url", "test-namespace")
