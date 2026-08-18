"""Automatic PvP season detection.

Midnight Season 1 (id 41) ended 2026-08-11; Season 2 starts the following week.
A hardcoded season id keeps returning the previous season's frozen final ladder
after the rollover, with no error — the leaderboard endpoint stays live.
"""
import httpx
import pytest
import respx
from unittest.mock import AsyncMock

from wow_advisor.api.client import BnetClient
from wow_advisor.settings import FALLBACK_SEASON_ID

INDEX_URL = "https://us.api.blizzard.com/data/wow/pvp-season/index"


def _board_url(season_id, bracket="3v3"):
    return f"https://us.api.blizzard.com/data/wow/pvp-season/{season_id}/pvp-leaderboard/{bracket}"


def _entries(n):
    return {
        "entries": [
            {
                "character": {"name": f"Player{i}", "realm": {"slug": "area-52"}},
                "rating": 3000 - i,
                "rank": i + 1,
            }
            for i in range(n)
        ]
    }


@pytest.fixture
def client():
    auth = AsyncMock()
    auth.get_token.return_value = "test_token"
    return BnetClient(auth=auth, region="us")


@respx.mock
async def test_detects_the_current_season(client):
    respx.get(INDEX_URL).mock(
        return_value=httpx.Response(200, json={"current_season": {"id": 42}})
    )

    assert await client.fetch_current_season_id() == 42


@respx.mock
async def test_detection_returns_none_when_the_api_fails(client):
    respx.get(INDEX_URL).mock(return_value=httpx.Response(500))

    assert await client.fetch_current_season_id() is None


@respx.mock
async def test_leaderboard_uses_the_detected_season(client):
    respx.get(INDEX_URL).mock(
        return_value=httpx.Response(200, json={"current_season": {"id": 42}})
    )
    respx.get(_board_url(42)).mock(return_value=httpx.Response(200, json=_entries(3)))

    page = await client.fetch_leaderboard("3v3")

    assert page.season_id == 42
    assert len(page.entries) == 3
    assert page.is_fallback is False


@respx.mock
async def test_leaderboard_falls_back_to_the_setting_when_detection_fails(client):
    respx.get(INDEX_URL).mock(return_value=httpx.Response(500))
    respx.get(_board_url(FALLBACK_SEASON_ID)).mock(
        return_value=httpx.Response(200, json=_entries(2))
    )

    page = await client.fetch_leaderboard("3v3")

    assert page.season_id == FALLBACK_SEASON_ID


@respx.mock
async def test_empty_new_season_falls_back_to_the_previous_season(client):
    """Day one of a season has no ranked ladder yet — the board exists but is empty.

    Without this the tool returns "no leaderboard data" for every spec until
    enough players have completed their placement games.
    """
    respx.get(INDEX_URL).mock(
        return_value=httpx.Response(200, json={"current_season": {"id": 42}})
    )
    respx.get(_board_url(42)).mock(return_value=httpx.Response(200, json={"entries": []}))
    respx.get(_board_url(41)).mock(return_value=httpx.Response(200, json=_entries(5)))

    page = await client.fetch_leaderboard("3v3")

    assert page.season_id == 41
    assert page.is_fallback is True
    assert len(page.entries) == 5


@respx.mock
async def test_no_fallback_loop_when_the_previous_season_is_also_empty(client):
    respx.get(INDEX_URL).mock(
        return_value=httpx.Response(200, json={"current_season": {"id": 42}})
    )
    respx.get(_board_url(42)).mock(return_value=httpx.Response(200, json={"entries": []}))
    respx.get(_board_url(41)).mock(return_value=httpx.Response(200, json={"entries": []}))

    page = await client.fetch_leaderboard("3v3")

    assert page.entries == []


@respx.mock
async def test_explicit_season_skips_detection(client):
    detection = respx.get(INDEX_URL).mock(
        return_value=httpx.Response(200, json={"current_season": {"id": 42}})
    )
    respx.get(_board_url(37)).mock(return_value=httpx.Response(200, json=_entries(1)))

    page = await client.fetch_leaderboard("3v3", season_id=37)

    assert page.season_id == 37
    assert not detection.called


# --- Contract test: real client through fetch_top_players_async -------------
#
# tests/test_fetch_tools.py mocks fetch_leaderboard wholesale, so a change to its
# return type keeps those green while production raises TypeError on len().

@respx.mock
async def test_fetch_top_players_drives_the_real_leaderboard_contract(tmp_path, monkeypatch):
    from wow_advisor.cache import db as db_module
    from wow_advisor.tools import fetch as fetch_module

    conn = db_module.init_db(str(tmp_path / "t.db"))
    monkeypatch.setattr(fetch_module, "get_default_db", lambda: conn)

    auth = AsyncMock()
    auth.get_token.return_value = "test_token"
    monkeypatch.setattr(
        fetch_module, "_make_client", lambda region: (auth, BnetClient(auth=auth, region=region))
    )

    respx.get(INDEX_URL).mock(
        return_value=httpx.Response(200, json={"current_season": {"id": 42}})
    )
    respx.get(_board_url(42)).mock(return_value=httpx.Response(200, json={"entries": []}))
    respx.get(_board_url(41)).mock(return_value=httpx.Response(200, json=_entries(1)))
    # Phase 1 spec probe: the single leaderboard entry is not the spec we asked for.
    respx.get(url__regex=r".*/profile/wow/character/.*").mock(
        return_value=httpx.Response(404)
    )

    result = await fetch_module.fetch_top_players_async("restoration shaman", "3v3")

    # No crash, and the season actually used is reported rather than assumed.
    assert result["season_id"] == 41
    assert result["season_fallback"] is True
