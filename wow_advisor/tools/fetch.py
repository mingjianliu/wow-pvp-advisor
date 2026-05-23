import asyncio
import os
import time
from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.client import BnetClient
from wow_advisor.api.models import CharacterData
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket, spec_to_class_spec
from wow_advisor.processor.aggregator import build_aggregation


def slugify(s: str) -> str:
    return s.lower().replace(" ", "-")


def _make_client(region: str) -> tuple[BnetAuth, BnetClient]:
    client_id = os.environ["BNET_CLIENT_ID"]
    client_secret = os.environ["BNET_CLIENT_SECRET"]
    auth = BnetAuth(client_id=client_id, client_secret=client_secret, region=region)
    return auth, BnetClient(auth=auth, region=region)


async def fetch_top_players_async(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
) -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)

    class_spec = spec_to_class_spec(spec)
    if class_spec is None:
        return {"error": f"Unknown spec: {spec}. Check spelling or add it to normalize.py."}

    # Skip API fetch if data is less than 2 hours old
    conn = get_default_db()
    store = CacheStore(conn)
    if not store.is_stale(spec, bracket, region, ttl_hours=2):
        agg = store.get_aggregation(spec, bracket, region)
        return {"fetched": agg.get("sample_size", 0), "cached_at": agg.get("cached_at"), "spec": spec, "bracket": bracket, "skipped": True}

    target_class, target_spec = class_spec
    _, client = _make_client(region)

    # Solo Shuffle leaderboard is spec-specific: shuffle-{class}-{spec}
    api_bracket = bracket
    if bracket == "shuffle":
        api_bracket = f"shuffle-{slugify(target_class)}-{slugify(target_spec)}"

    leaderboard = await client.fetch_leaderboard(bracket=api_bracket)
    if not leaderboard:
        return {"error": f"No leaderboard data for bracket '{api_bracket}'. Check bracket name and season ID."}

    # Phase 1: cheap spec-only scan across full leaderboard (1 API call per player).
    # Stops as soon as we have `limit` matching players.
    import httpx as _httpx
    matched: list[CharacterData] = []
    batch_size = 50

    async with _httpx.AsyncClient() as http_client:
        for i in range(0, len(leaderboard), batch_size):
            if len(matched) >= limit:
                break
            batch = leaderboard[i:i + batch_size]
            results = await asyncio.gather(*[
                client.fetch_character_spec(http_client, e.name, e.realm, e.rating)
                for e in batch
            ])
            for char in results:
                if char is None:
                    continue
                if char.character_class == target_class and char.spec == target_spec:
                    matched.append(char)
                    if len(matched) >= limit:
                        break

    if not matched:
        return {
            "error": f"Found 0 {spec} players across {len(leaderboard)} {bracket} leaderboard entries."
        }

    # Phase 2: fetch full talent + gear for matched players only (2 API calls each).
    collected: list[CharacterData] = await asyncio.gather(*[
        client.fetch_character_details(name=c.name, realm=c.realm, char=c)
        for c in matched
    ])

    conn = get_default_db()
    store = CacheStore(conn)
    store.save_players(collected, spec=spec, bracket=bracket)

    aggregation = build_aggregation(
        players=collected,
        spec=spec,
        bracket=bracket,
        region=region,
    )
    store.save_aggregation(spec=spec, bracket=bracket, region=region, data=aggregation)

    return {"fetched": len(collected), "cached_at": int(time.time()), "spec": spec, "bracket": bracket}


def fetch_top_players(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
) -> dict:
    """Synchronous wrapper for MCP tool use."""
    return asyncio.run(fetch_top_players_async(spec=spec, bracket=bracket, region=region, limit=limit))


async def _scan_full_leaderboard(bracket: str, region: str) -> int:
    """Utility: returns total leaderboard entry count (for debugging)."""
    _, client = _make_client(region)
    leaderboard = await client.fetch_leaderboard(bracket=bracket)
    return len(leaderboard)
