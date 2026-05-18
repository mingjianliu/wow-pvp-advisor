# Talent tree structure for each spec.
# Node ids must match the WoW talent IDs returned by summarize_talent_clusters()
# so deriveNodeMap() on the frontend can color the tree correctly.

_SHAMAN_CLASS_TREE = {
    "id": "class",
    "label": "Class Tree",
    "nodes": [
        {"id": 103615, "name": "Wind Shear",             "type": "circle",   "maxPoints": 1, "col": 2, "row": 0},
        {"id": 103617, "name": "Nature's Fury",          "type": "circle",   "maxPoints": 1, "col": 1, "row": 1},
        {"id": 103598, "name": "Lava Burst",             "type": "circle",   "maxPoints": 1, "col": 3, "row": 1},
        {"id": 103622, "name": "Earthgrab Totem",        "type": "circle",   "maxPoints": 1, "col": 0, "row": 2},
        {"id": 103623, "name": "Hex",                    "type": "diamond",  "maxPoints": 1, "col": 2, "row": 2},
        {"id": 103618, "name": "Static Charge",          "type": "circle",   "maxPoints": 1, "col": 4, "row": 2},
        {"id": 103613, "name": "Nature's Guardian",      "type": "circle",   "maxPoints": 1, "col": 1, "row": 3},
        {"id": 103585, "name": "Earth Elemental",        "type": "circle",   "maxPoints": 1, "col": 3, "row": 3},
        {"id": 103584, "name": "Spiritwalker's Grace",   "type": "circle",   "maxPoints": 1, "col": 0, "row": 4},
        {"id": 103579, "name": "Capacitor Totem",        "type": "diamond",  "maxPoints": 1, "col": 2, "row": 4},
        {"id": 103600, "name": "Voodoo Mastery",         "type": "circle",   "maxPoints": 1, "col": 4, "row": 4},
        {"id": 103625, "name": "Totemic Focus",          "type": "circle",   "maxPoints": 1, "col": 1, "row": 5},
        {"id": 103627, "name": "Wind Rush Totem",        "type": "circle",   "maxPoints": 1, "col": 3, "row": 5},
        {"id": 110403, "name": "Stormstream Totem",      "type": "capstone", "maxPoints": 1, "col": 2, "row": 6},
        {"id": 109387, "name": "Instinctive Imbuements", "type": "circle",   "maxPoints": 1, "col": 1, "row": 7},
        {"id": 109386, "name": "Totemic Projection",     "type": "circle",   "maxPoints": 1, "col": 3, "row": 7},
    ],
    "edges": [
        [103615, 103617], [103615, 103598],
        [103617, 103622], [103617, 103623],
        [103598, 103623], [103598, 103618],
        [103622, 103613], [103623, 103613], [103623, 103585], [103618, 103585],
        [103613, 103584], [103613, 103579], [103585, 103579], [103585, 103600],
        [103584, 103625], [103579, 103625], [103579, 103627], [103600, 103627],
        [103625, 110403], [103627, 110403],
        [110403, 109387], [110403, 109386],
    ],
}

_FARSEER_HERO_TREE = {
    "id": "hero",
    "label": "Hero - Farseer",
    "nodes": [
        {"id": "h01", "name": "Ancestral Swiftness",  "type": "circle",   "maxPoints": 1, "col": 1, "row": 0},
        {"id": "h02", "name": "Latent Wisdom",        "type": "circle",   "maxPoints": 1, "col": 3, "row": 0},
        {"id": "h03", "name": "Ancient Fellowship",   "type": "circle",   "maxPoints": 1, "col": 1, "row": 1},
        {"id": "h04", "name": "Routine Communion",    "type": "circle",   "maxPoints": 1, "col": 3, "row": 1},
        {"id": "h05", "name": "Heed My Call",         "type": "diamond",  "maxPoints": 1, "col": 2, "row": 2},
        {"id": "h06", "name": "Offering from Beyond", "type": "circle",   "maxPoints": 1, "col": 1, "row": 3},
        {"id": "h07", "name": "Primordial Capacity",  "type": "circle",   "maxPoints": 1, "col": 3, "row": 3},
        {"id": "h08", "name": "Maelstrom Supremacy",  "type": "circle",   "maxPoints": 1, "col": 1, "row": 4},
        {"id": "h09", "name": "Final Calling",        "type": "circle",   "maxPoints": 1, "col": 3, "row": 4},
        {"id": "h10", "name": "Earthen Communion",    "type": "capstone", "maxPoints": 1, "col": 2, "row": 5},
    ],
    "edges": [
        ["h01", "h03"], ["h02", "h04"],
        ["h03", "h05"], ["h04", "h05"],
        ["h05", "h06"], ["h05", "h07"],
        ["h06", "h08"], ["h07", "h09"],
        ["h08", "h10"], ["h09", "h10"],
    ],
}

_RESTO_SHAMAN_SPEC_TREE = {
    "id": "spec",
    "label": "Spec Tree",
    "nodes": [
        {"id": 81027,  "name": "Riptide",               "type": "circle",   "maxPoints": 1, "col": 2, "row": 0},
        {"id": 81044,  "name": "Tidal Waves",            "type": "circle",   "maxPoints": 1, "col": 1, "row": 1},
        {"id": 103588, "name": "Chain Heal",             "type": "circle",   "maxPoints": 1, "col": 3, "row": 1},
        {"id": 103432, "name": "Torrent",                "type": "circle",   "maxPoints": 1, "col": 0, "row": 2},
        {"id": 81049,  "name": "Earthliving Weapon",     "type": "diamond",  "maxPoints": 1, "col": 2, "row": 2},
        {"id": 81024,  "name": "Resurgence",             "type": "circle",   "maxPoints": 1, "col": 4, "row": 2},
        {"id": 81022,  "name": "Healing Stream Totem",   "type": "circle",   "maxPoints": 1, "col": 1, "row": 3},
        {"id": 81041,  "name": "Spirit Link Totem",      "type": "circle",   "maxPoints": 1, "col": 3, "row": 3},
        {"id": 81040,  "name": "Healing Rain",           "type": "circle",   "maxPoints": 1, "col": 0, "row": 4},
        {"id": 81052,  "name": "Undercurrent",           "type": "diamond",  "maxPoints": 1, "col": 2, "row": 4},
        {"id": 103594, "name": "Refreshing Waters",      "type": "circle",   "maxPoints": 1, "col": 4, "row": 4},
        {"id": 81039,  "name": "Acid Rain",              "type": "circle",   "maxPoints": 1, "col": 1, "row": 5},
        {"id": 103582, "name": "Brimming with Life",     "type": "circle",   "maxPoints": 1, "col": 3, "row": 5},
        {"id": 81051,  "name": "Deeply Rooted Elements", "type": "capstone", "maxPoints": 1, "col": 2, "row": 6},
        {"id": 103628, "name": "Windveil",               "type": "circle",   "maxPoints": 1, "col": 1, "row": 7},
        {"id": 103428, "name": "Soothing Rain",          "type": "circle",   "maxPoints": 1, "col": 3, "row": 7},
    ],
    "edges": [
        [81027, 81044], [81027, 103588],
        [81044, 103432], [81044, 81049],
        [103588, 81049], [103588, 81024],
        [103432, 81022], [81049, 81022], [81049, 81041], [81024, 81041],
        [81022, 81040], [81022, 81052], [81041, 81052], [81041, 103594],
        [81040, 81039], [81052, 81039], [81052, 103582], [103594, 103582],
        [81039, 81051], [103582, 81051],
        [81051, 103628], [81051, 103428],
    ],
}

_SPEC_TREES = {
    "restoration-shaman": {
        "trees": [
            _SHAMAN_CLASS_TREE,
            _FARSEER_HERO_TREE,
            _RESTO_SHAMAN_SPEC_TREE,
        ]
    },
}


def get_tree_structure(spec: str) -> dict:
    """Return talent tree layout (nodes + edges + positions) for a spec.

    The tree ids are real WoW talent IDs matching summarize_talent_clusters() output,
    so the frontend can color nodes automatically from cluster data.
    Returns {"trees": [...]} or {"error": "..."}.
    """
    from wow_advisor.normalize import normalize_spec
    spec_key = normalize_spec(spec)
    if spec_key not in _SPEC_TREES:
        return {"error": f"No tree layout for '{spec_key}'. Available: {list(_SPEC_TREES.keys())}"}
    return _SPEC_TREES[spec_key]
