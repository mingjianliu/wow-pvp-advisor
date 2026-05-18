"""
Fetch real talent tree structure from the Blizzard API for any spec.

The API's spec_talent_nodes contains three sub-trees packed into one array:
  [Left hero, low cols] [spec nodes, middle cols] [Right hero, high cols]

Split strategy:
  1. Largest col gap isolates the left hero tree
  2. ID-range check (94000-95000, 109700-109800 = TWW hero talent IDs) isolates right hero
"""
import asyncio
import httpx
from wow_advisor.api.auth import BnetAuth
import os


def _get_auth():
    return BnetAuth(os.environ["BNET_CLIENT_ID"], os.environ["BNET_CLIENT_SECRET"])


def _parse_node(n: dict) -> dict | None:
    name = None
    spell_id = None
    max_points = max(1, len(n.get("ranks", [])))
    for rank in n.get("ranks", []):
        tt = rank.get("tooltip", {})
        if "talent" in tt:
            name = tt["talent"].get("name")
            spell_id = tt.get("spell_tooltip", {}).get("spell", {}).get("id")
            break
        if "choice_of_tooltips" in tt and tt["choice_of_tooltips"]:
            c = tt["choice_of_tooltips"][0]
            name = c.get("talent", {}).get("name")
            spell_id = c.get("spell_tooltip", {}).get("spell", {}).get("id")
            break
    if not name:
        return None
    ntype = "diamond" if n.get("node_type", {}).get("id") == 2 else "circle"
    return {
        "id": n["id"], "name": name, "type": ntype,
        "maxPoints": max_points,
        "col": n.get("display_col", 0), "row": n.get("display_row", 0),
        "spellId": spell_id,
        "_unlocks": n.get("unlocks", []),
    }


def _is_hero_id(nid) -> bool:
    return isinstance(nid, int) and (94000 <= nid <= 95000 or 109700 <= nid <= 109800)


def _split_spec_nodes(spec_raw: list[dict]) -> tuple:
    """Split spec_talent_nodes into (left_hero, spec_only, right_hero)."""
    if not spec_raw:
        return [], [], []
    cols = sorted({n["col"] for n in spec_raw})
    if len(cols) < 2:
        return [], spec_raw, []
    # Find the largest gap — separates left hero from (spec + right hero)
    max_gap = max(cols[i+1] - cols[i] for i in range(len(cols)-1))
    if max_gap <= 1:
        # No structural gap — fall back to ID-based detection only
        right_hero = [n for n in spec_raw if _is_hero_id(n["id"])]
        right_ids = {n["id"] for n in right_hero}
        return [], [n for n in spec_raw if n["id"] not in right_ids], right_hero

    gap_at = next(
        cols[i] for i in range(len(cols)-1) if cols[i+1] - cols[i] == max_gap
    )
    left_hero = [n for n in spec_raw if n["col"] <= gap_at]
    rest      = [n for n in spec_raw if n["col"] > gap_at]
    right_hero = [n for n in rest if _is_hero_id(n["id"])]
    right_ids  = {n["id"] for n in right_hero}
    spec_only  = [n for n in rest if n["id"] not in right_ids]
    return left_hero, spec_only, right_hero


def _build(nodes: list[dict]) -> dict:
    if not nodes:
        return {"nodes": [], "edges": []}
    valid = {n["id"] for n in nodes}
    min_col = min(n["col"] for n in nodes)
    min_row = min(n["row"] for n in nodes)
    edges = []
    result = []
    for n in nodes:
        for t in n["_unlocks"]:
            if t in valid:
                edges.append([n["id"], t])
        node = {k: v for k, v in n.items() if k != "_unlocks"}
        node["col"] -= min_col
        node["row"] -= min_row
        result.append(node)
    return {"nodes": result, "edges": edges}


async def _fetch(spec_id: int) -> dict:
    auth = _get_auth()
    token = await auth.get_token()
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "static-us"}
    async with httpx.AsyncClient(timeout=30) as client:
        spec_r = await client.get(
            f"https://us.api.blizzard.com/data/wow/playable-specialization/{spec_id}",
            headers=headers, params={"locale": "en_US"},
        )
        spec_data = spec_r.json()
        href = spec_data.get("spec_talent_tree", {}).get("key", {}).get("href", "")
        if not href:
            raise ValueError(f"No talent tree href for spec {spec_id}")
        tree_r = await client.get(href, headers=headers, params={"locale": "en_US"})
        tree = tree_r.json()

    class_raw = [_parse_node(n) for n in tree.get("class_talent_nodes", [])]
    class_raw = [n for n in class_raw if n]
    spec_all  = [_parse_node(n) for n in tree.get("spec_talent_nodes", [])]
    spec_all  = [n for n in spec_all if n]

    hero_meta    = spec_data.get("hero_talent_trees", [])
    left_raw, spec_raw, right_raw = _split_spec_nodes(spec_all)

    # Determine hero names: examine node names to identify Totemic vs Farseer
    # (the API sometimes returns duplicate names in hero_talent_trees)
    def _guess_hero_name(nodes, meta_names, fallback):
        totem_hints = {"totem", "totemic", "communion", "rebound"}
        farseer_hints = {"ancestor", "ancestral", "wisdom", "farseer", "communion"}
        names_lower = " ".join(n["name"].lower() for n in nodes if n.get("name"))
        if any(h in names_lower for h in totem_hints):
            return "Totemic"
        if any(h in names_lower for h in farseer_hints):
            return "Farseer"
        return fallback

    left_name  = _guess_hero_name(left_raw,  [], hero_meta[1]["name"] if len(hero_meta) > 1 else "Hero A")
    right_name = _guess_hero_name(right_raw, [], hero_meta[0]["name"] if len(hero_meta) > 0 else "Hero B")

    class_built = _build(class_raw)
    spec_built  = _build(spec_raw)
    left_built  = _build(left_raw)
    right_built = _build(right_raw)

    return {
        "trees": [
            {"id": "class", "label": "Class Tree",  **class_built},
            {"id": "spec",  "label": "Spec Tree",   **spec_built},
        ],
        "heroTrees": {
            "left":  {"id": "hero_left",  "label": f"Hero · {left_name}",
                      "heroName": left_name,
                      "nodeIds": [n["id"] for n in left_built["nodes"]],
                      **left_built},
            "right": {"id": "hero_right", "label": f"Hero · {right_name}",
                      "heroName": right_name,
                      "nodeIds": [n["id"] for n in right_built["nodes"]],
                      **right_built},
        },
    }


def get_tree_structure(spec: str) -> dict:
    """
    Fetch real talent tree layout from Blizzard API for any spec.

    Returns:
      trees:     [class_tree, spec_tree]
      heroTrees: {left: {..., nodeIds, heroName}, right: {..., nodeIds, heroName}}

    Frontend selects the hero tree per cluster by checking which
    heroTrees nodeIds overlap with the cluster's core+takes node IDs.
    Works for any spec in SPEC_IDS — no hardcoded layouts.
    """
    from wow_advisor.normalize import normalize_spec
    from wow_advisor.processor.talent_names import SPEC_IDS
    spec_key = normalize_spec(spec)
    spec_id  = SPEC_IDS.get(spec_key)
    if not spec_id:
        return {"error": f"Unknown spec '{spec_key}'"}
    try:
        return asyncio.run(_fetch(spec_id))
    except Exception as e:
        return {"error": str(e)}
