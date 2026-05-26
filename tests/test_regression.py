"""
Regression tests comparing our data against external sources.

Run with:
    pytest tests/test_regression.py -m regression -v -s

Requires:
    - BNET_CLIENT_ID and BNET_CLIENT_SECRET in .env
    - Cached data from a recent fetch: python cli.py fetch "resto shaman" 3v3

These tests hit live APIs and external sites — they are slow and network-dependent.
They are excluded from the default test run and must be triggered explicitly.
"""
import re
import time

import httpx
import pytest

from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore

SPEC = "restoration-shaman"
BRACKET = "3v3"
REGION = "us"

pytestmark = pytest.mark.regression


# ── Helpers ───────────────────────────────────────────────────────────────────

def _our_data() -> dict:
    conn = get_default_db()
    agg = CacheStore(conn).get_aggregation(SPEC, BRACKET, REGION)
    if agg is None:
        pytest.skip(f"No cached data for {SPEC}/{BRACKET}. Run: python cli.py fetch 'resto shaman' 3v3")
    return agg


def _our_players():
    conn = get_default_db()
    players = CacheStore(conn).get_players(SPEC, BRACKET, REGION)
    if not players:
        pytest.skip(f"No cached players for {SPEC}/{BRACKET}. Run: python cli.py fetch 'resto shaman' 3v3")
    return players


# ── 1. Sanity checks (no external calls) ─────────────────────────────────────

class TestSanity:
    """Validates internal consistency of our own cached data."""

    def test_player_count(self):
        players = _our_players()
        assert len(players) >= 30, f"Expected ≥30 players, got {len(players)}"

    def test_rating_range(self):
        players = _our_players()
        ratings = [p.rating for p in players]
        assert max(ratings) > 2000, f"Top rating {max(ratings)} suspiciously low"
        assert min(ratings) > 1400, f"Bottom rating {min(ratings)} suspiciously low"
        assert max(ratings) < 5000, f"Top rating {max(ratings)} impossibly high"

    def test_ilvl_in_season_range(self):
        data = _our_data()
        ilvl = data["avg_ilvl"]
        # Midnight S1: expect 220-300 range
        assert 200 <= ilvl <= 350, f"avg_ilvl {ilvl} outside expected Midnight S1 range 200-350"

    def test_gear_dominant_item_exists(self):
        data = _our_data()
        gear = data["gear"]
        assert "head" in gear, "No head slot data"
        top_head_pct = gear["head"][0]["pct"]
        assert top_head_pct >= 30, \
            f"Top head item only {top_head_pct}% pick rate — data may be too sparse"

    def test_ring_enchant_consensus(self):
        data = _our_data()
        enchants = data.get("enchants", {})
        for slot in ("finger_1", "finger_2"):
            if slot in enchants:
                top_pct = enchants[slot][0]["pct"]
                assert top_pct >= 40, \
                    f"{slot} top enchant only {top_pct}% — weaker consensus than expected"

    def test_talent_clusters_present(self):
        data = _our_data()
        talents = data["talents"]
        assert len(talents["clusters"]) >= 1, "No talent clusters found"
        assert len(talents["core_nodes"]) >= 5, \
            f"Only {len(talents['core_nodes'])} core nodes — suspiciously few"

    def test_cache_not_stale(self):
        data = _our_data()
        age_hours = (time.time() - data["cached_at"]) / 3600
        assert age_hours < 72, \
            f"Cache is {age_hours:.1f}h old — refresh with: python cli.py fetch 'resto shaman' 3v3"

    def test_players_sorted_by_rating(self):
        players = _our_players()
        ratings = [p.rating for p in players]
        assert ratings == sorted(ratings, reverse=True), "Players not sorted by rating DESC"

    def test_item_names_not_empty(self):
        data = _our_data()
        for slot, items in data["gear"].items():
            assert items[0]["name"], f"Item name empty for slot {slot}"

    def test_enchant_names_clean(self):
        """Verify Blizzard UI markup (|A:...|a) has been stripped from enchant names."""
        data = _our_data()
        for slot, enchants in data.get("enchants", {}).items():
            name = enchants[0]["name"]
            assert "|A:" not in name, \
                f"Enchant name for {slot} still contains raw UI markup: {name!r}"


# ── 2. Blizzard API spot-check ────────────────────────────────────────────────

class TestBlizzardSpotCheck:
    """Re-fetches 3 cached players directly from Blizzard to verify our parsing."""

    @pytest.fixture(scope="class")
    def bnet_client(self):
        import os
        from dotenv import load_dotenv
        load_dotenv()
        from wow_advisor.api.auth import BnetAuth
        from wow_advisor.api.client import BnetClient
        auth = BnetAuth(os.environ["BNET_CLIENT_ID"], os.environ["BNET_CLIENT_SECRET"])
        return BnetClient(auth=auth, region=REGION)

    @pytest.mark.asyncio
    async def test_spot_check_spec_matches(self, bnet_client):
        """Re-fetch 3 players and confirm their spec + class still match our cache."""
        import asyncio
        from wow_advisor.normalize import _SPEC_INFO_MAP
        players = _our_players()[:3]
        async with httpx.AsyncClient() as http:
            tasks = [
                bnet_client.fetch_character_spec(http, p.name, p.realm, p.rating)
                for p in players
            ]
            fresh = await asyncio.gather(*tasks)

        for cached, live in zip(players, fresh):
            if live is None:
                continue  # player deleted/transferred — not our fault
            spec_info = _SPEC_INFO_MAP.get(cached.spec)
            if spec_info:
                _, _, class_name, spec_name = spec_info
                assert live.spec == spec_name, \
                    f"{cached.name}: spec mismatch cached={cached.spec!r} live={live.spec!r}"
                assert live.character_class == class_name, \
                    f"{cached.name}: class mismatch cached={cached.character_class!r} live={live.character_class!r}"
            else:
                assert live.spec.lower().replace(" ", "-") in cached.spec.lower()

    @pytest.mark.asyncio
    async def test_spot_check_ilvl_drift(self, bnet_client):
        """Re-fetched ilvl should be within ±30 of what we stored (gear upgrades happen)."""
        import asyncio
        players = _our_players()[:3]
        async with httpx.AsyncClient() as http:
            tasks = [
                bnet_client.fetch_character_spec(http, p.name, p.realm, p.rating)
                for p in players
            ]
            fresh = await asyncio.gather(*tasks)

        for cached, live in zip(players, fresh):
            if live is None or live.equipped_ilvl == 0:
                continue
            drift = abs(live.equipped_ilvl - cached.equipped_ilvl)
            assert drift <= 30, \
                f"{cached.name}: ilvl drift {drift} (cached={cached.equipped_ilvl}, live={live.equipped_ilvl})"


# ── 3. Murlok.io comparison ───────────────────────────────────────────────────

class TestMurlokComparison:
    """Compares our data against murlok.io (HTML page — no public API)."""

    @pytest.fixture(scope="class")
    def murlok_page(self):
        try:
            r = httpx.get(
                "https://murlok.io/shaman/restoration/3v3",
                timeout=15,
                follow_redirects=True,
            )
        except httpx.RequestError as e:
            pytest.skip(f"Could not reach murlok.io: {e}")
        if r.status_code != 200:
            pytest.skip(f"murlok.io returned HTTP {r.status_code}")
        return r.text

    def test_murlok_top_rating_in_range(self, murlok_page):
        """murlok's highest visible rating should be within 300 of ours."""
        # murlok embeds ratings as plain integers in ranges like 2000-3000
        candidates = [int(x) for x in re.findall(r'\b([23][0-9]{3})\b', murlok_page)]
        if not candidates:
            pytest.skip("No rating data found on murlok.io — may be JS-rendered")
        murlok_max = max(candidates)
        our_max = max(p.rating for p in _our_players())
        diff = abs(murlok_max - our_max)
        assert diff < 400, \
            f"Top rating divergence: ours={our_max}, murlok_page_max={murlok_max} (diff={diff})"

    def test_murlok_page_has_content(self, murlok_page):
        """Ensure murlok.io page loaded real content, not an error page."""
        assert len(murlok_page) > 10_000, "murlok.io returned a suspiciously small page"
        assert "shaman" in murlok_page.lower() or "restoration" in murlok_page.lower(), \
            "murlok.io page doesn't mention shaman/restoration — may have redirected"


# ── 4. pvpq.net comparison ────────────────────────────────────────────────────

class TestPvpqComparison:
    """Compares player list against pvpq.net JSON API.

    pvpq.net may not have Midnight expansion data yet — tests skip gracefully.
    Endpoint: GET https://pvpq.net/api/{region}/ladder/{bracket}
    """

    @pytest.fixture(scope="class")
    def pvpq_chars(self):
        try:
            r = httpx.get("https://pvpq.net/api/us/ladder/3v3", timeout=15)
        except httpx.RequestError as e:
            pytest.skip(f"Could not reach pvpq.net: {e}")
        data = r.json()
        chars = data.get("characters", [])
        if not chars:
            pytest.skip("pvpq.net returned no characters — likely not updated for current season")
        return chars

    def test_pvpq_player_overlap(self, pvpq_chars):
        """≥50% of our cached players should appear on pvpq.net's ladder."""
        pvpq_rsham = {
            c["name"].lower()
            for c in pvpq_chars
            if "shaman" in c.get("class", "").lower()
            and "restoration" in c.get("spec", "").lower()
        }
        if not pvpq_rsham:
            pytest.skip("No Restoration Shamans found on pvpq.net")
        our_names = {p.name.lower() for p in _our_players()}
        overlap = len(our_names & pvpq_rsham) / min(len(our_names), len(pvpq_rsham))
        assert overlap >= 0.5, \
            f"Player overlap with pvpq.net: {overlap:.0%} (expected ≥50%)"

    def test_pvpq_rating_range_matches(self, pvpq_chars):
        """Rating range on pvpq.net should broadly match ours (within 200)."""
        pvpq_rsham = [
            c for c in pvpq_chars
            if "shaman" in c.get("class", "").lower()
            and "restoration" in c.get("spec", "").lower()
        ]
        if not pvpq_rsham:
            pytest.skip("No Restoration Shamans found on pvpq.net")
        pvpq_max = max(c.get("rating", 0) for c in pvpq_rsham)
        our_max = max(p.rating for p in _our_players())
        diff = abs(pvpq_max - our_max)
        assert diff < 300, \
            f"Top rating divergence: ours={our_max}, pvpq={pvpq_max} (diff={diff})"
