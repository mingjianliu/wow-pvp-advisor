import asyncio
import time
from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.client import BnetClient
from wow_advisor.api.models import CharacterData
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket, spec_to_class_spec
from wow_advisor.processor.aggregator import build_aggregation
from wow_advisor.settings import AGGREGATION_TTL_HOURS, MissingCredentialsError, get_credentials


# Brackets whose leaderboard is published per spec rather than as one board.
_PER_SPEC_LEADERBOARDS = {"solo-shuffle": "shuffle", "blitz": "blitz"}


def slugify(s: str) -> str:
    """Class/spec name as it appears in a Blizzard leaderboard slug.

    Spaces are removed rather than hyphenated: "Demon Hunter" -> "demonhunter",
    "Beast Mastery" -> "beastmastery". Hyphenating 404s, which silently disabled
    solo shuffle for every Death Knight and Demon Hunter spec plus Beast Mastery.
    """
    return s.lower().replace(" ", "")


def _current_game_build(conn, spec: str, locale: str) -> str | None:
    """Client build the cached talent node IDs for this spec belong to.

    Reads only what the talent node cache already recorded, so this never hits
    the network and never needs credentials.
    """
    from wow_advisor.processor.talent_names import TalentNameCache
    try:
        return TalentNameCache(conn).game_build(spec, locale=locale)
    except Exception:
        return None


def _make_client(region: str) -> tuple[BnetAuth, BnetClient]:
    client_id, client_secret = get_credentials()
    auth = BnetAuth(client_id=client_id, client_secret=client_secret, region=region)
    return auth, BnetClient(auth=auth, region=region)


async def fetch_top_players_async(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
    locale: str = "en_US",
) -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)

    from wow_advisor.normalize import spec_to_ids
    ids = spec_to_ids(spec)
    if ids is None:
        return {"error": f"Unknown spec: {spec}. Check spelling or add it to normalize.py."}

    # Skip API fetch if data is fresher than the TTL and was built under the same
    # client build. The build stamp is a plain DB read of whatever the talent node
    # cache last recorded — no HTTP, no credentials — so cache hits still work
    # offline. Node IDs get reassigned between builds, so an aggregation from
    # another build has to be rebuilt no matter how recent it is.
    conn = get_default_db()
    store = CacheStore(conn)
    game_build = _current_game_build(conn, spec, locale)
    if not store.is_stale(
        spec, bracket, region, ttl_hours=AGGREGATION_TTL_HOURS, locale=locale,
        game_build=game_build,
    ):
        agg = store.get_aggregation(spec, bracket, region, locale=locale)
        return {"fetched": agg.get("sample_size", 0), "cached_at": agg.get("cached_at"), "spec": spec, "bracket": bracket, "skipped": True}

    target_class_id, target_spec_id = ids
    # Also get names for Solo Shuffle slug
    class_spec = spec_to_class_spec(spec)
    target_class, target_spec = class_spec

    try:
        _, client = _make_client(region)
    except MissingCredentialsError as e:
        return {"error": str(e)}

    # Solo Shuffle and Blitz publish one leaderboard per spec.
    api_bracket = bracket
    prefix = _PER_SPEC_LEADERBOARDS.get(bracket)
    if prefix:
        api_bracket = f"{prefix}-{slugify(target_class)}-{slugify(target_spec)}"

    page = await client.fetch_leaderboard(bracket=api_bracket)
    leaderboard = page.entries
    if not leaderboard:
        return {"error": (
            f"No leaderboard data for bracket '{api_bracket}' in season {page.season_id}. "
            "Check the bracket name, or wait for placement games if the season just started."
        )}

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
                client.fetch_character_spec(http_client, e.name, e.realm, e.rating, locale=locale)
                for e in batch
            ])
            for char in results:
                if char is None:
                    continue
                if char.class_id == target_class_id and char.spec_id == target_spec_id:
                    matched.append(char)
                    if len(matched) >= limit:
                        break

    if not matched:
        return {
            "error": (
                f"Found 0 {spec} players across {len(leaderboard)} {bracket} leaderboard "
                f"entries in season {page.season_id}."
            ),
            "season_id": page.season_id,
            "season_fallback": page.is_fallback,
        }

    # Phase 2: fetch full talent + gear for matched players only (2 API calls each).
    collected: list[CharacterData] = await asyncio.gather(*[
        client.fetch_character_details(name=c.name, realm=c.realm, char=c, locale=locale)
        for c in matched
    ])

    conn = get_default_db()
    store = CacheStore(conn)
    store.save_players(collected, spec=spec, bracket=bracket, locale=locale)

    aggregation = build_aggregation(
        players=collected,
        spec=spec,
        bracket=bracket,
        region=region,
    )
    # Record which ladder the sample came from — it is not always the current
    # season (see LeaderboardPage), and a summary built off last season's ladder
    # has to say so.
    aggregation["season_id"] = page.season_id
    aggregation["season_fallback"] = page.is_fallback
    store.save_aggregation(
        spec=spec, bracket=bracket, region=region, data=aggregation, locale=locale,
        game_build=game_build,
    )

    return {
        "fetched": len(collected),
        "cached_at": int(time.time()),
        "spec": spec,
        "bracket": bracket,
        "season_id": page.season_id,
        "season_fallback": page.is_fallback,
    }


def fetch_top_players(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
    locale: str = "en_US",
) -> dict:
    """Synchronous wrapper for MCP tool use."""
    return asyncio.run(fetch_top_players_async(spec=spec, bracket=bracket, region=region, limit=limit, locale=locale))


