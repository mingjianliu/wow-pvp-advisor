"""
Fetch real talent tree structure from the Blizzard API for any spec.

Hero trees come from tree.hero_talent_trees[].hero_talent_nodes (authoritative).
We filter to the 2 trees available to the spec using spec_data.hero_talent_trees.
Works correctly for all 39 specs.
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
        # Choice nodes: choice_of_tooltips sits directly on rank (no tooltip wrapper)
        cot = rank.get("choice_of_tooltips") or tt.get("choice_of_tooltips")
        if cot:
            c = cot[0]
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

    # The spec endpoint lists the 2 hero trees valid for THIS spec (by id).
    spec_hero_ids = {ht["id"] for ht in spec_data.get("hero_talent_trees", [])}

    # The tree endpoint has all class hero trees with full node data — filter to spec's 2.
    hero_trees_meta = tree.get("hero_talent_trees", [])
    all_hero_ids: set[int] = set()
    unique_heroes: list[dict] = []
    seen_names: set[str] = set()
    for ht in hero_trees_meta:
        if spec_hero_ids and ht["id"] not in spec_hero_ids:
            continue  # skip hero trees not available to this spec
        nodes = [_parse_node(n) for n in ht.get("hero_talent_nodes", [])]
        nodes = [n for n in nodes if n]
        if not nodes or ht["name"] in seen_names:
            continue
        seen_names.add(ht["name"])
        all_hero_ids |= {n["id"] for n in nodes}
        unique_heroes.append({"name": ht["name"], "id": ht["id"], "nodes": nodes})

    # Spec-only nodes = spec_talent_nodes minus all hero nodes
    spec_all = [_parse_node(n) for n in tree.get("spec_talent_nodes", [])]
    spec_raw = [n for n in spec_all if n and n["id"] not in all_hero_ids]

    class_raw = [_parse_node(n) for n in tree.get("class_talent_nodes", [])]
    class_raw = [n for n in class_raw if n]

    class_built = _build(class_raw)
    spec_built  = _build(spec_raw)
    left_built  = _build(unique_heroes[0]["nodes"]) if len(unique_heroes) > 0 else {"nodes": [], "edges": []}
    right_built = _build(unique_heroes[1]["nodes"]) if len(unique_heroes) > 1 else {"nodes": [], "edges": []}
    left_name   = unique_heroes[0]["name"] if len(unique_heroes) > 0 else "Hero A"
    right_name  = unique_heroes[1]["name"] if len(unique_heroes) > 1 else "Hero B"

    return {
        "trees": [
            {"id": "class", "label": "Class Tree", **class_built},
            {"id": "spec",  "label": "Spec Tree",  **spec_built},
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

    Hero trees are the 2 available to this spec, taken from the tree API's
    hero_talent_nodes arrays — no ID-range heuristics. Correct for all 39 specs.
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
