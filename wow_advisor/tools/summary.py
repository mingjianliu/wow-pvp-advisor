import logging

from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.settings import AGGREGATION_TTL_HOURS
from wow_advisor.tools.fetch import fetch_top_players

logger = logging.getLogger(__name__)


def _enrich_talents(talents: dict, node_map: dict[int, dict]) -> dict:
    """Transform raw talent node IDs into {id, name, pct} objects."""
    pick_rates = {int(k): v for k, v in talents.get("pick_rates", {}).items()}
    rank_dists = talents.get("rank_distributions", {})

    def enrich(ids_or_objs: list) -> list[dict]:
        enriched = []
        for item in ids_or_objs:
            nid = item["id"] if isinstance(item, dict) else item
            # Cluster takes carry their own cluster-specific pct; preserve it so
            # the displayed pct matches the pickers/count ratio. Global lists
            # (core/flex/contested) carry only an id, so fall back to the global
            # pick rate.
            item_pct = item.get("pct") if isinstance(item, dict) else None
            entry = {
                "id": nid,
                "name": (node_map.get(nid) or {}).get("name"),
                "pct": item_pct if item_pct is not None else pick_rates.get(nid),
            }
            if isinstance(item, dict) and "rank" in item:
                entry["pts"] = item["rank"]
            if isinstance(item, dict) and "pickers" in item:
                entry["pickers"] = item["pickers"]
            
            dist = rank_dists.get(str(nid))
            if dist:
                entry["rankDist"] = dist
            
            enriched.append(entry)
        
        # Sort by pick rate descending, but keep items with same pick rate in ID order
        return sorted(enriched, key=lambda x: (-(x["pct"] or 0), x["id"]))

    return {
        "core": enrich(talents.get("core_nodes", [])),
        "flex": enrich(talents.get("flex_nodes", [])),
        "contested": enrich(talents.get("contested_nodes", [])),
        "clusters": [
            {**c, "takes": enrich(c.get("takes", [])), "skips": enrich(c.get("skips", []))}
            for c in talents.get("clusters", [])
        ],
        "clustering_method": talents.get("clustering_method"),
    }


def get_full_summary(spec: str, bracket: str, region: str = "us", locale: str = "en_US") -> dict:
    """Single-call summary: auto-fetches if stale, returns gear + named talents + PvP talents."""
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)
    conn = get_default_db()
    store = CacheStore(conn)

    # Resolve names before the staleness check: doing so refreshes the talent
    # node cache and, with it, the record of which client build the current node
    # IDs belong to. That build then drives both the refresh decision and the
    # cross-build guard below.
    node_map, current_build = _resolve_node_names(conn, spec, region, locale)

    if store.is_stale(
        spec, bracket, region, ttl_hours=AGGREGATION_TTL_HOURS, locale=locale,
        game_build=current_build,
    ):
        result = fetch_top_players(spec=spec, bracket=bracket, region=region, locale=locale)
        if "error" in result:
            return result

    agg = store.get_aggregation(spec, bracket, region, locale=locale)
    if agg is None:
        return {"error": f"No data for {spec} in {bracket}. Fetch failed."}

    # Aggregations hold raw node IDs, and Blizzard reassigns talents across node
    # IDs between builds (12.1 swapped Battlelord and Master Tactician on Arms
    # Warrior). Labelling old IDs with current names yields confidently wrong
    # talent names, so withhold names instead and say why.
    agg_build = store.aggregation_game_build(spec, bracket, region, locale=locale)
    stale_build = None
    if current_build and agg_build and agg_build != current_build:
        stale_build = {"aggregation": agg_build, "current": current_build}
        node_map = {}
        logger.warning(
            "Talent names withheld for %s %s: aggregation built under %s, current build is %s",
            spec, bracket, agg_build, current_build,
        )

    out = {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": agg.get("sample_size", 0),
        "avg_ilvl": agg.get("avg_ilvl", 0),
        "cached_at": agg.get("cached_at"),
        "pvp_talents": agg.get("pvp_talents", []),
        "talents": _enrich_talents(agg.get("talents", {}), node_map),
        "gear": agg.get("gear", {}),
        "enchants": agg.get("enchants", {}),
    }
    if stale_build:
        out["stale_build"] = stale_build
    # Which ladder produced this sample. Only flagged when it is not the current
    # season — a fallback that nobody can see is the same bug as a wrong name.
    if agg.get("season_id") is not None:
        out["season_id"] = agg["season_id"]
    if agg.get("season_fallback"):
        out["season_fallback"] = True
    # Same rule as season_fallback: an aggregation clustered without node
    # metadata has different build variants, and a caller that cannot see that
    # will present them as the meta.
    if agg.get("clustering_degraded"):
        out["clustering_degraded"] = True
    return out


def _resolve_node_names(
    conn, spec: str, region: str, locale: str
) -> tuple[dict[int, dict], str | None]:
    """Returns (node_id -> metadata, client build those IDs belong to)."""
    try:
        from wow_advisor.processor.talent_names import TalentNameCache
        from wow_advisor.tools.fetch import _make_client
        _, client = _make_client(region)
        cache = TalentNameCache(conn)
        node_map = cache.resolve(spec, client, locale=locale)
        return node_map, cache.game_build(spec, locale=locale)
    except Exception:
        # Names are an enrichment, not a hard dependency — degrade to raw IDs,
        # but leave a trace so all-null names are debuggable.
        logger.warning("Talent name resolution failed for %s (%s)", spec, locale, exc_info=True)
        return {}, None
