"""Concurrency bound on Wowhead tooltip prefetching.

Wowhead is a third-party site, not an API with a published quota. A full static
refresh asks for a few thousand tooltips at once, and an unbounded asyncio.gather
opens all of them simultaneously.
"""
import asyncio

import httpx
import pytest
import respx

from wow_advisor.api.wowhead import prefetch_tooltips
from wow_advisor.settings import WOWHEAD_CONCURRENCY


@pytest.fixture
def no_tooltip_cache(tmp_path, monkeypatch):
    """Point the tooltip cache at an empty DB so every id is a real fetch."""
    from wow_advisor.cache import db as db_module
    conn = db_module.init_db(str(tmp_path / "tooltips.db"))
    monkeypatch.setattr("wow_advisor.api.wowhead.get_default_db", lambda: conn)
    return conn


@respx.mock
async def test_prefetch_never_exceeds_the_concurrency_bound(no_tooltip_cache):
    in_flight = 0
    peak = 0

    async def slow_response(request):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return httpx.Response(200, json={"name": "x", "tooltip": "y"})

    respx.get(url__regex=r"https://nether\.wowhead\.com/tooltip/.*").mock(
        side_effect=slow_response
    )

    await prefetch_tooltips(list(range(60)), type_str="spell")

    assert peak <= WOWHEAD_CONCURRENCY


@respx.mock
async def test_prefetch_still_returns_every_requested_id(no_tooltip_cache):
    respx.get(url__regex=r"https://nether\.wowhead\.com/tooltip/.*").mock(
        return_value=httpx.Response(200, json={"name": "x"})
    )

    result = await prefetch_tooltips(list(range(30)), type_str="spell")

    assert sorted(result) == list(range(30))
