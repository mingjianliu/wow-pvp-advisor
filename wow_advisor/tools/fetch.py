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
    scan_limit: int = 500,
) -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)

    class_spec = spec_to_class_spec(spec)
    if class_spec is None:
        return {"error": f"Unknown spec: {spec}. Check spelling or add it to normalize.py."}

    target_class, target_spec = class_spec
    _, client = _make_client(region)

    leaderboard = await client.fetch_leaderboard(bracket=bracket)
    if not leaderboard:
        return {"error": f"No leaderboard data for bracket '{bracket}'. Check bracket name and season ID."}

    candidates = leaderboard[:scan_limit]

    collected: list[CharacterData] = []
    batch_size = 20

    for i in range(0, len(candidates), batch_size):
        if len(collected) >= limit:
            break
        batch = candidates[i:i + batch_size]
        results = await asyncio.gather(*[
            client.fetch_character(name=e.name, realm=e.realm, rating=e.rating)
            for e in batch
        ])
        for char in results:
            if char is None:
                continue
            if char.character_class == target_class and char.spec == target_spec:
                collected.append(char)
            if len(collected) >= limit:
                break

    if not collected:
        return {
            "error": (
                f"Found 0 {spec} players in the top {min(scan_limit, len(leaderboard))} "
                f"{bracket} leaderboard entries. Try increasing scan_limit or check spec name."
            )
        }

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
