from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.tools.fetch import fetch_top_players


def _enrich_talents(talents: dict, node_map: dict[int, dict]) -> dict:
    """Transform raw talent node IDs into {id, name} objects."""
    def enrich(ids: list[int]) -> list[dict]:
        return [{"id": nid, "name": (node_map.get(nid) or {}).get("name")} for nid in ids]

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


def get_full_summary(spec: str, bracket: str, region: str = "us") -> dict:
    """Single-call summary: auto-fetches if stale, returns gear + named talents + PvP talents."""
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

    node_map: dict[int, dict] = {}
    try:
        from wow_advisor.processor.talent_names import TalentNameCache
        from wow_advisor.tools.fetch import _make_client
        _, client = _make_client(region)
        node_map = TalentNameCache(conn).resolve(spec, client)
    except Exception:
        pass

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
