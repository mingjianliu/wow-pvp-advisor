import json
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.settings import QUERY_TTL_HOURS
from wow_advisor.tools.fetch import _current_game_build, fetch_top_players


def get_gear_summary(spec: str, bracket: str, region: str = "us", locale: str = "en_US") -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)
    conn = get_default_db()
    store = CacheStore(conn)
    if store.is_stale(
        spec, bracket, region, ttl_hours=QUERY_TTL_HOURS, locale=locale,
        game_build=_current_game_build(conn, spec, locale),
    ):
        result = fetch_top_players(spec=spec, bracket=bracket, region=region, locale=locale)
        if "error" in result:
            return result
    agg = store.get_aggregation(spec, bracket, region, locale=locale)
    if agg is None:
        return {"error": f"No data for {spec} in {bracket}. Try calling fetch_top_players first."}
    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": agg.get("sample_size", 0),
        "avg_ilvl": agg.get("avg_ilvl", 0),
        "cached_at": agg.get("cached_at"),
        "gear": agg.get("gear", {}),
        "enchants": agg.get("enchants", {}),
    }


def get_player_details(name: str, realm: str, region: str = "us") -> dict:
    conn = get_default_db()
    rows = conn.execute(
        """SELECT p.name, p.realm, p.region, p.character_class, p.spec,
                  p.bracket, p.rating, p.equipped_ilvl,
                  l.talent_code, l.class_node_ids, l.spec_node_ids, l.hero_node_ids, l.gear
           FROM players p LEFT JOIN player_loadouts l ON p.id = l.player_id
           WHERE LOWER(p.name)=LOWER(?) AND LOWER(p.realm)=LOWER(?) AND p.region=?
           ORDER BY p.rating DESC LIMIT 1""",
        (name, realm, region),
    ).fetchall()
    if not rows:
        return {"error": f"Player {name}-{realm} not found in cache. Fetch their spec first."}
    r = rows[0]
    return {
        "name": r["name"],
        "realm": r["realm"],
        "spec": r["spec"],
        "class": r["character_class"],
        "rating": r["rating"],
        "equipped_ilvl": r["equipped_ilvl"],
        "talent_code": r["talent_code"],
        "class_node_ids": json.loads(r["class_node_ids"] or "[]"),
        "spec_node_ids": json.loads(r["spec_node_ids"] or "[]"),
        "hero_node_ids": json.loads(r["hero_node_ids"] or "[]"),
        "gear": json.loads(r["gear"] or "[]"),
    }
