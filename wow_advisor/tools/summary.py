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

    if store.is_stale(spec, bracket, region, ttl_hours=AGGREGATION_TTL_HOURS, locale=locale):
        result = fetch_top_players(spec=spec, bracket=bracket, region=region, locale=locale)
        if "error" in result:
            return result

    agg = store.get_aggregation(spec, bracket, region, locale=locale)
    if agg is None:
        return {"error": f"No data for {spec} in {bracket}. Fetch failed."}

    node_map: dict[int, dict] = {}
    try:
        from wow_advisor.processor.talent_names import TalentNameCache
        from wow_advisor.tools.fetch import _make_client
        _, client = _make_client(region)
        node_map = TalentNameCache(conn).resolve(spec, client, locale=locale)
    except Exception:
        # Names are an enrichment, not a hard dependency — degrade to raw IDs,
        # but leave a trace so all-null names are debuggable.
        logger.warning("Talent name resolution failed for %s (%s)", spec, locale, exc_info=True)

    return {
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
