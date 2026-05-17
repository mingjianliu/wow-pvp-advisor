from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.tools.fetch import fetch_top_players


def get_full_summary(spec: str, bracket: str, region: str = "us") -> dict:
    """Single-call summary: auto-fetches if stale, returns gear + talents + PvP talents."""
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)
    conn = get_default_db()
    store = CacheStore(conn)

    if store.is_stale(spec, bracket, region, ttl_hours=2):
        result = fetch_top_players(spec=spec, bracket=bracket, region=region)
        if "error" in result:
            return result

    agg = store.get_aggregation(spec, bracket, region)
    if agg is None:
        return {"error": f"No data for {spec} in {bracket}. Fetch failed."}

    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": agg.get("sample_size", 0),
        "avg_ilvl": agg.get("avg_ilvl", 0),
        "cached_at": agg.get("cached_at"),
        "pvp_talents": agg.get("pvp_talents", []),
        "talents": agg.get("talents", {}),
        "gear": agg.get("gear", {}),
        "enchants": agg.get("enchants", {}),
    }
