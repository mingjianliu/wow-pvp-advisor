"""
Build a self-contained HTML page for a spec+bracket and write it to frontend/pages/.

Entry point: build_page(spec, bracket, region) -> {"path": str, "url": str}
"""

import json
import re
from pathlib import Path

from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.tools.summary import get_full_summary
from wow_advisor.talent_tree import get_tree_structure

_FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
_PAGES_DIR = _FRONTEND_DIR / "pages"
_SERVER_BASE = "http://localhost:8080"

_SPEC_LABELS: dict[str, dict[str, str]] = {
    "affliction-warlock":      {"class": "Warlock",      "spec": "Affliction"},
    "arcane-mage":             {"class": "Mage",         "spec": "Arcane"},
    "arms-warrior":            {"class": "Warrior",      "spec": "Arms"},
    "assassination-rogue":     {"class": "Rogue",        "spec": "Assassination"},
    "augmentation-evoker":     {"class": "Evoker",       "spec": "Augmentation"},
    "balance-druid":           {"class": "Druid",        "spec": "Balance"},
    "beast-mastery-hunter":    {"class": "Hunter",       "spec": "Beast Mastery"},
    "blood-death-knight":      {"class": "Death Knight", "spec": "Blood"},
    "brewmaster-monk":         {"class": "Monk",         "spec": "Brewmaster"},
    "demonology-warlock":      {"class": "Warlock",      "spec": "Demonology"},
    "destruction-warlock":     {"class": "Warlock",      "spec": "Destruction"},
    "devastation-evoker":      {"class": "Evoker",       "spec": "Devastation"},
    "discipline-priest":       {"class": "Priest",       "spec": "Discipline"},
    "elemental-shaman":        {"class": "Shaman",       "spec": "Elemental"},
    "enhancement-shaman":      {"class": "Shaman",       "spec": "Enhancement"},
    "feral-druid":             {"class": "Druid",        "spec": "Feral"},
    "fire-mage":               {"class": "Mage",         "spec": "Fire"},
    "frost-death-knight":      {"class": "Death Knight", "spec": "Frost"},
    "frost-mage":              {"class": "Mage",         "spec": "Frost"},
    "fury-warrior":            {"class": "Warrior",      "spec": "Fury"},
    "guardian-druid":          {"class": "Druid",        "spec": "Guardian"},
    "havoc-demon-hunter":      {"class": "Demon Hunter", "spec": "Havoc"},
    "holy-paladin":            {"class": "Paladin",      "spec": "Holy"},
    "holy-priest":             {"class": "Priest",       "spec": "Holy"},
    "marksmanship-hunter":     {"class": "Hunter",       "spec": "Marksmanship"},
    "mistweaver-monk":         {"class": "Monk",         "spec": "Mistweaver"},
    "outlaw-rogue":            {"class": "Rogue",        "spec": "Outlaw"},
    "preservation-evoker":     {"class": "Evoker",       "spec": "Preservation"},
    "protection-paladin":      {"class": "Paladin",      "spec": "Protection"},
    "protection-warrior":      {"class": "Warrior",      "spec": "Protection"},
    "restoration-druid":       {"class": "Druid",        "spec": "Restoration"},
    "restoration-shaman":      {"class": "Shaman",       "spec": "Restoration"},
    "retribution-paladin":     {"class": "Paladin",      "spec": "Retribution"},
    "shadow-priest":           {"class": "Priest",       "spec": "Shadow"},
    "subtlety-rogue":          {"class": "Rogue",        "spec": "Subtlety"},
    "survival-hunter":         {"class": "Hunter",       "spec": "Survival"},
    "unholy-death-knight":     {"class": "Death Knight", "spec": "Unholy"},
    "vengeance-demon-hunter":  {"class": "Demon Hunter", "spec": "Vengeance"},
    "windwalker-monk":         {"class": "Monk",         "spec": "Windwalker"},
}

_GEAR_SLOT_LABELS: dict[str, str] = {
    "head": "Head", "neck": "Neck", "shoulder": "Shoulder", "back": "Back",
    "chest": "Chest", "wrist": "Wrist", "hands": "Hands", "waist": "Waist",
    "legs": "Legs", "feet": "Feet", "finger_1": "Ring 1", "finger_2": "Ring 2",
    "trinket_1": "Trinket 1", "trinket_2": "Trinket 2",
    "main_hand": "Weapon", "off_hand": "Off-hand",
}


def _make_cluster_data(raw: dict, tree: dict) -> dict:
    """Transform get_full_summary + get_tree_structure output into CLUSTER_DATA shape."""
    spec = raw["spec"]

    id_to_name: dict[int, str] = {}
    for sub in tree["trees"] + [tree["heroTrees"]["left"], tree["heroTrees"]["right"]]:
        for n in sub["nodes"]:
            if n.get("name"):
                id_to_name[n["id"]] = n["name"]

    hero_ids: set[int] = (
        {n["id"] for n in tree["heroTrees"]["left"]["nodes"]}
        | {n["id"] for n in tree["heroTrees"]["right"]["nodes"]}
    )

    def enrich(talent_list: list[dict]) -> list[dict]:
        return [
            {"id": t["id"], "name": t.get("name") or id_to_name.get(t["id"]), "pct": t["pct"]}
            for t in talent_list
            if t.get("name") or id_to_name.get(t["id"])
        ]

    def strip_hero(lst: list[dict]) -> list[dict]:
        return [t for t in lst if t["id"] not in hero_ids]

    clusters = []
    for c in raw["talents"]["clusters"]:
        takes = [
            {"id": t["id"], "name": id_to_name.get(t["id"], t.get("name") or ""), "pct": t["pct"]}
            for t in strip_hero(c["takes"])
            if id_to_name.get(t["id"], t.get("name"))
        ]
        skips = [
            {"id": t["id"], "name": id_to_name.get(t["id"], t.get("name") or ""), "pct": t["pct"]}
            for t in strip_hero(c["skips"])
            if id_to_name.get(t["id"], t.get("name"))
        ]
        clusters.append({
            "rank": c["rank"],
            "pct": c["pct"],
            "count": c["count"],
            "canonical_code": c["canonical_code"],
            "takes": takes,
            "skips": skips,
        })

    enchants_raw = raw.get("enchants", {})
    gear_slots = []
    for slot_key, label in _GEAR_SLOT_LABELS.items():
        items = raw["gear"].get(slot_key, [])
        if not items:
            continue
        top = items[0]
        entry: dict = {"slot": label, "item": {"id": top["item_id"], "name": top["name"], "pct": top["pct"]}}
        enc_list = enchants_raw.get(slot_key, [])
        if enc_list:
            ename = re.sub(r"^Enchanted:\s*Enchant [^-]+ - ", "", enc_list[0]["name"])
            ename = re.sub(r"^Enchanted:\s*", "", ename)
            entry["enchant"] = {"name": ename, "pct": enc_list[0]["pct"]}
        gear_slots.append(entry)

    return {
        "spec": spec,
        "specLabel": _SPEC_LABELS.get(spec, {"class": "", "spec": spec}),
        "bracket": raw["bracket"],
        "sample_size": raw["sample_size"],
        "avg_ilvl": raw["avg_ilvl"],
        "pvp_talents": [
            {"id": f"p{i + 1}", "name": p["name"], "pct": p["pct"]}
            for i, p in enumerate(raw["pvp_talents"])
        ],
        "talents": {
            "core": enrich(raw["talents"]["core"]),
            "flex": enrich(raw["talents"]["flex"]),
            "contested": enrich(raw["talents"]["contested"]),
        },
        "clusters": clusters,
        "gear": {"avg_ilvl": raw["avg_ilvl"], "slots": gear_slots},
    }


def _bundle_html(cluster_data: dict, tree: dict) -> str:
    """Inline all frontend assets into a single self-contained HTML page."""
    template = (_FRONTEND_DIR / "index.html").read_text()
    styles_css = (_FRONTEND_DIR / "styles.css").read_text()

    data_js = (
        "// Auto-generated by build_page — do not edit manually\n\n"
        "window.CLUSTER_DATA = " + json.dumps(cluster_data, indent=2) + ";\n\n"
        "window.CLUSTER_DATA.tree = " + json.dumps(tree, indent=2) + ";\n"
    )

    html = template
    html = html.replace(
        '<link rel="stylesheet" href="styles.css" />',
        f"<style>\n{styles_css}\n</style>",
    )
    html = html.replace(
        '<script src="tree-data.js"></script>\n  <script src="data.js"></script>',
        f"<script>\n{data_js}\n</script>",
    )
    for jsx_file in ["tweaks-panel.jsx", "tree.jsx", "sidebar.jsx", "app.jsx"]:
        src = (_FRONTEND_DIR / jsx_file).read_text()
        html = re.sub(
            rf'<script type="text/babel" src="{re.escape(jsx_file)}"></script>',
            f'<script type="text/babel">\n{src}\n</script>',
            html,
        )
    return html


def build_page(spec: str, bracket: str, region: str = "us") -> dict:
    """Build a self-contained HTML page for a spec+bracket.

    Fetches summary + tree structure, bundles everything inline, and writes
    frontend/pages/{spec}_{bracket}.html.  The file is immediately accessible
    via the local HTTP server at localhost:8080.

    Returns:
        {"path": str, "url": str, "spec": str, "bracket": str,
         "sample_size": int, "clusters": int}
    """
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)

    raw = get_full_summary(spec=spec, bracket=bracket, region=region)
    if "error" in raw:
        return raw

    tree = get_tree_structure(spec=spec)
    if "error" in tree:
        return tree

    cluster_data = _make_cluster_data(raw, tree)
    html = _bundle_html(cluster_data, tree)

    _PAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{spec}_{bracket}.html"
    out_path = _PAGES_DIR / filename
    out_path.write_text(html)

    return {
        "path": str(out_path),
        "url": f"{_SERVER_BASE}/pages/{filename}",
        "spec": spec,
        "bracket": bracket,
        "sample_size": raw["sample_size"],
        "clusters": len(cluster_data["clusters"]),
    }
