import asyncio
import copy
import logging
import time
import httpx
from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.client import BnetClient
from wow_advisor.api.models import CharacterData, LeaderboardPage
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import (
    _SPEC_INFO_MAP, normalize_spec, normalize_bracket, spec_to_class_spec, spec_to_ids,
)
from wow_advisor.processor.aggregator import build_aggregation
from wow_advisor.settings import AGGREGATION_TTL_HOURS, MissingCredentialsError, get_credentials

logger = logging.getLogger(__name__)

# Brackets whose leaderboard is published per spec rather than as one board.
_PER_SPEC_LEADERBOARDS = {"solo-shuffle": "shuffle", "blitz": "blitz"}

_SCAN_BATCH = 50


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


def _api_bracket(bracket: str, spec: str) -> str:
    """Leaderboard slug for a bracket, per-spec where Blizzard publishes it that way."""
    prefix = _PER_SPEC_LEADERBOARDS.get(bracket)
    if not prefix:
        return bracket
    class_spec = spec_to_class_spec(spec)
    if class_spec is None:
        return bracket
    target_class, target_spec = class_spec
    return f"{prefix}-{slugify(target_class)}-{slugify(target_spec)}"


async def _scan_ladder(
    client: BnetClient,
    entries: list,
    targets: dict[tuple[int, int], str],
    limit: int,
    locale: str = "en_US",
) -> dict[str, list[CharacterData]]:
    """One pass over a leaderboard, bucketing entries by the spec they play.

    This phase reads only class_id/spec_id off each character profile, so a
    single pass serves every spec sharing the board. Scanning once per spec
    re-reads the same ~5000 profiles for each one, and a spec too rare to fill
    `limit` forces the full ladder every time.

    Stops as soon as every target bucket holds `limit` players.
    """
    buckets: dict[str, list[CharacterData]] = {spec: [] for spec in targets.values()}
    async with httpx.AsyncClient() as http_client:
        for i in range(0, len(entries), _SCAN_BATCH):
            if all(len(v) >= limit for v in buckets.values()):
                break
            batch = entries[i:i + _SCAN_BATCH]
            results = await asyncio.gather(*[
                client.fetch_character_spec(http_client, e.name, e.realm, e.rating, locale=locale)
                for e in batch
            ])
            for char in results:
                if char is None:
                    continue
                spec = targets.get((char.class_id, char.spec_id))
                if spec is not None and len(buckets[spec]) < limit:
                    buckets[spec].append(char)
    return buckets


async def _collect_spec(
    client: BnetClient,
    conn,
    store: CacheStore,
    spec: str,
    bracket: str,
    region: str,
    matched: list[CharacterData],
    locale: str,
    page: LeaderboardPage,
) -> dict:
    """Phase 2 for one spec in one locale: details, aggregate, cache."""
    collected: list[CharacterData] = await asyncio.gather(*[
        client.fetch_character_details(name=c.name, realm=c.realm, char=c, locale=locale)
        for c in matched
    ])
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
        game_build=_current_game_build(conn, spec, locale),
    )

    return {
        "fetched": len(collected),
        "cached_at": int(time.time()),
        "spec": spec,
        "bracket": bracket,
        "locale": locale,
        "season_id": page.season_id,
        "season_fallback": page.is_fallback,
        "clustering_degraded": aggregation.get("clustering_degraded", False),
    }


async def _localize(
    client: BnetClient, chars: list[CharacterData], spec: str, locale: str,
    scan_locale: str,
) -> list[CharacterData]:
    """Copies of `chars` carrying this locale's class/spec display names.

    Only those two strings are locale-dependent in a scanned profile, and both
    are per-spec constants — one static lookup relabels the whole roster, where
    re-scanning would cost one profile fetch per player per locale. Copies are
    made either way: fetch_character_details mutates the CharacterData it is
    handed, so locales must not share objects.
    """
    chars = [copy.deepcopy(c) for c in chars]
    if locale == scan_locale:
        return chars  # the scan already read these labels in this locale
    ids = spec_to_ids(spec)
    if ids is None:
        return chars
    labels = await client.fetch_spec_labels(ids[1], locale=locale)
    if labels is None:
        # Display names only; keep the scan's labels rather than fail the fetch.
        logger.warning("Spec labels unavailable for %s (%s)", spec, locale)
        return chars
    class_name, spec_name = labels
    for c in chars:
        c.character_class = class_name
        c.spec = spec_name
    return chars


async def fetch_top_players_async(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
    locale: str = "en_US",
) -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)

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

    try:
        _, client = _make_client(region)
    except MissingCredentialsError as e:
        return {"error": str(e)}

    api_bracket = _api_bracket(bracket, spec)
    page = await client.fetch_leaderboard(bracket=api_bracket)
    if not page.entries:
        return {"error": (
            f"No leaderboard data for bracket '{api_bracket}' in season {page.season_id}. "
            "Check the bracket name, or wait for placement games if the season just started."
        )}

    buckets = await _scan_ladder(
        client, page.entries, {(ids[0], ids[1]): spec}, limit, locale=locale
    )
    matched = buckets[spec]
    if not matched:
        return {
            "error": (
                f"Found 0 {spec} players across {len(page.entries)} {bracket} leaderboard "
                f"entries in season {page.season_id}."
            ),
            "season_id": page.season_id,
            "season_fallback": page.is_fallback,
        }

    result = await _collect_spec(
        client, conn, store, spec, bracket, region, matched, locale, page
    )
    result.pop("locale", None)
    return result


def fetch_top_players(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
    locale: str = "en_US",
) -> dict:
    """Synchronous wrapper for MCP tool use."""
    return asyncio.run(fetch_top_players_async(spec=spec, bracket=bracket, region=region, limit=limit, locale=locale))


async def fetch_bracket_async(
    bracket: str,
    region: str = "us",
    limit: int = 50,
    locales: tuple[str, ...] = ("en_US",),
    specs: list[str] | None = None,
    progress=None,
) -> dict:
    """Collect every spec in a bracket, sharing one ladder scan across all of them.

    On a shared board (3v3/2v2/rbg) this is the same sampling `fetch_top_players`
    produces — still the highest-ranked `limit` players of each spec — for one
    pass over the ladder instead of one pass per spec per locale. Per-spec boards
    (solo shuffle, blitz) still need their own board each, but the scan is reused
    across locales.

    `progress` is an optional callable taking a result dict, invoked as each
    (spec, locale) lands, so long runs can report without buffering.
    """
    bracket = normalize_bracket(bracket)
    specs = [normalize_spec(s) for s in specs] if specs else list(_SPEC_INFO_MAP)
    unknown = [s for s in specs if spec_to_ids(s) is None]
    if unknown:
        return {"error": f"Unknown specs: {', '.join(unknown)}"}
    if not locales:
        return {"error": "At least one locale is required."}

    try:
        _, client = _make_client(region)
    except MissingCredentialsError as e:
        return {"error": str(e)}

    conn = get_default_db()
    store = CacheStore(conn)
    scan_locale = locales[0]
    out: dict = {"bracket": bracket, "region": region, "results": [], "scanned": 0}

    if bracket in _PER_SPEC_LEADERBOARDS:
        # One board per spec: nothing to share across specs, but the scan still
        # serves every locale.
        for spec in specs:
            page = await client.fetch_leaderboard(bracket=_api_bracket(bracket, spec))
            out["scanned"] += len(page.entries)
            out.setdefault("season_id", page.season_id)
            out.setdefault("season_fallback", page.is_fallback)
            if not page.entries:
                r = {"spec": spec, "fetched": 0, "note": "no leaderboard entries"}
                out["results"].append(r)
                if progress: progress(r)
                continue
            ids = spec_to_ids(spec)
            matched = (await _scan_ladder(
                client, page.entries, {(ids[0], ids[1]): spec}, limit, locale=scan_locale
            ))[spec]
            await _collect_all_locales(
                client, conn, store, spec, bracket, region, matched, locales,
                scan_locale, page, out, progress,
            )
        return out

    page = await client.fetch_leaderboard(bracket=bracket)
    out["season_id"] = page.season_id
    out["season_fallback"] = page.is_fallback
    out["scanned"] = len(page.entries)
    if not page.entries:
        return {"error": (
            f"No leaderboard data for bracket '{bracket}' in season {page.season_id}. "
            "Check the bracket name, or wait for placement games if the season just started."
        ), "season_id": page.season_id}

    targets = {}
    for spec in specs:
        ids = spec_to_ids(spec)
        targets[(ids[0], ids[1])] = spec
    buckets = await _scan_ladder(client, page.entries, targets, limit, locale=scan_locale)

    for spec in specs:
        matched = buckets.get(spec) or []
        if not matched:
            r = {"spec": spec, "fetched": 0,
                 "note": f"no {spec} players across {len(page.entries)} entries"}
            out["results"].append(r)
            if progress: progress(r)
            continue
        await _collect_all_locales(
            client, conn, store, spec, bracket, region, matched, locales,
            scan_locale, page, out, progress,
        )
    return out


async def _collect_all_locales(
    client, conn, store, spec, bracket, region, matched, locales, scan_locale,
    page, out, progress,
):
    for locale in locales:
        chars = await _localize(client, matched, spec, locale, scan_locale)
        r = await _collect_spec(
            client, conn, store, spec, bracket, region, chars, locale, page
        )
        out["results"].append(r)
        if progress:
            progress(r)


def fetch_bracket(
    bracket: str,
    region: str = "us",
    limit: int = 50,
    locales: tuple[str, ...] = ("en_US",),
    specs: list[str] | None = None,
    progress=None,
) -> dict:
    """Synchronous wrapper for CLI use."""
    return asyncio.run(fetch_bracket_async(
        bracket=bracket, region=region, limit=limit, locales=locales,
        specs=specs, progress=progress,
    ))
