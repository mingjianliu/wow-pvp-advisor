"""
Build a self-contained HTML page for a spec+bracket and write it to frontend/pages/.

Entry point: build_page(spec, bracket, region) -> {"path": str, "url": str}
"""

import asyncio
import json
import platform
import re
import socket
import subprocess
import time
from dotenv import load_dotenv
load_dotenv()

from wow_advisor._paths import get_frontend_dir, get_pages_dir
from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.tools.summary import get_full_summary
from wow_advisor.talent_tree import get_tree_structure

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

_GEAR_SLOT_LABELS_ZH: dict[str, str] = {
    "head": "头部", "neck": "项链", "shoulder": "肩部", "back": "背部",
    "chest": "胸部", "wrist": "护腕", "hands": "手部", "waist": "腰部",
    "legs": "腿部", "feet": "脚部", "finger_1": "戒指 1", "finger_2": "戒指 2",
    "trinket_1": "饰品 1", "trinket_2": "饰品 2",
    "main_hand": "主手", "off_hand": "副手",
}


def _make_cluster_data(raw: dict, tree: dict, locale: str = "en_US") -> dict:
    """Transform get_full_summary + get_tree_structure output into CLUSTER_DATA shape."""
    spec = raw["spec"]

    id_to_name: dict[int, str] = {}
    id_to_spellid: dict[int, int] = {}
    for sub in tree["trees"] + [tree["heroTrees"]["left"], tree["heroTrees"]["right"]]:
        for n in sub["nodes"]:
            if n.get("name"):
                id_to_name[n["id"]] = n["name"]
            if n.get("spellId"):
                id_to_spellid[n["id"]] = n["spellId"]

    hero_ids: set[int] = (
        {n["id"] for n in tree["heroTrees"]["left"]["nodes"]}
        | {n["id"] for n in tree["heroTrees"]["right"]["nodes"]}
    )

    def enrich(talent_list: list[dict]) -> list[dict]:
        return [
            {
                **t, 
                "name": t.get("name") or id_to_name.get(t["id"])
            }
            for t in talent_list
            if (t.get("name") or id_to_name.get(t["id"])) and t["id"] not in hero_ids
        ]

    def strip_hero(lst: list[dict]) -> list[dict]:
        return [t for t in lst if (t["id"] if isinstance(t, dict) else t) not in hero_ids]

    def _hero_core_nodes() -> list[dict]:
        """Return the dominant hero tree's nodes as core entries.

        Hero talents are all-or-nothing tree selections, not individual choices.
        We classify the higher-pick-rate tree as core so the frontend can render
        its nodes green and selectHeroTree() can identify it via overlap.
        """
        all_raw = raw["talents"]["core"] + raw["talents"]["flex"] + raw["talents"]["contested"]
        rate: dict[int, float] = {t["id"]: t["pct"] for t in all_raw if t["id"] in hero_ids}
        pts: dict[int, int] = {t["id"]: t.get("pts", 1) for t in all_raw if t["id"] in hero_ids}
        dist: dict[int, list] = {t["id"]: t.get("rankDist", []) for t in all_raw if t["id"] in hero_ids}
        
        left_ids  = {n["id"] for n in tree["heroTrees"]["left"]["nodes"]}
        right_ids = {n["id"] for n in tree["heroTrees"]["right"]["nodes"]}
        left_avg  = sum(rate.get(i, 0) for i in left_ids)  / max(len(left_ids), 1)
        right_avg = sum(rate.get(i, 0) for i in right_ids) / max(len(right_ids), 1)
        dominant  = left_ids if left_avg >= right_avg else right_ids
        
        return [
            {
                "id": hid, 
                "name": id_to_name[hid], 
                "pct": rate.get(hid, 0),
                "pts": pts.get(hid, 1),
                "rankDist": dist.get(hid, [])
            }
            for hid in dominant
            if hid in id_to_name
        ]

    clusters = []
    for c in raw["talents"]["clusters"]:
        takes = [
            {
                "id": t["id"], 
                "name": id_to_name.get(t["id"], t.get("name") or ""), 
                "pct": t.get("pct", 100.0),
                "spellId": id_to_spellid.get(t["id"]),
                "pickers": t.get("pickers", [])
            }
            for t in strip_hero(c["takes"])
            if id_to_name.get(t["id"], t.get("name"))
        ]
        skips = [
            {
                "id": t["id"], 
                "name": id_to_name.get(t["id"], t.get("name") or ""), 
                "pct": t.get("pct", 0.0),
                "spellId": id_to_spellid.get(t["id"]),
                "pickers": t.get("pickers", [])
            }
            for t in strip_hero(c["skips"])
            if id_to_name.get(t["id"], t.get("name"))
        ]
        # Enrich flex_takes (internal cluster variance)
        flex_takes = [
            {
                "id": t["id"], 
                "name": id_to_name.get(t["id"], ""), 
                "pct": t["pct"],
                "spellId": id_to_spellid.get(t["id"]),
                "pickers": t.get("pickers", [])
            }
            for t in c.get("flex_takes", [])
            if id_to_name.get(t["id"])
        ]

        clusters.append({
            "rank": c["rank"],
            "pct": c["pct"],
            "count": c["count"],
            "canonical_code": c["canonical_code"],
            "takes": takes,
            "flex_takes": flex_takes,
            "skips": skips,
        })

    enchants_raw = raw.get("enchants", {})
    gear_slots = []
    slot_labels = _GEAR_SLOT_LABELS_ZH if locale == "zh_CN" else _GEAR_SLOT_LABELS
    for slot_key, label in slot_labels.items():
        items = raw["gear"].get(slot_key, [])
        if not items:
            continue
        top = items[0]
        entry: dict = {"slot": label, "item": {"id": top["item_id"], "name": top["name"], "pct": top["pct"]}}
        enc_list = enchants_raw.get(slot_key, [])
        if enc_list:
            ename = enc_list[0]["name"]
            # Strip localized prefixes
            ename = re.sub(r"^(Enchanted|已附魔|附魔)[:：]?\s*", "", ename)
            ename = re.sub(r"^Enchant [^-]+ - ", "", ename)
            entry["enchant"] = {
                "id": enc_list[0].get("enchant_id"),
                "name": ename,
                "pct": enc_list[0]["pct"]
            }
        gear_slots.append(entry)

    hero_core = _hero_core_nodes()

    return {
        "spec": spec,
        "specLabel": _SPEC_LABELS.get(spec, {"class": "", "spec": spec}),
        "bracket": raw["bracket"],
        "sample_size": raw["sample_size"],
        "avg_ilvl": raw["avg_ilvl"],
        "pvp_talents": [
            {"id": p["id"], "name": p["name"], "pct": p["pct"]}
            for p in raw["pvp_talents"]
        ],
        "talents": {
            "core": enrich(raw["talents"]["core"]) + hero_core,
            "flex": enrich(raw["talents"]["flex"]),
            "contested": enrich(raw["talents"]["contested"]),
        },
        "clusters": clusters,
        "gear": {"avg_ilvl": raw["avg_ilvl"], "slots": gear_slots},
    }


def _bundle_html(cluster_data: dict, tree: dict, prefetched_meta: dict | None = None) -> str:
    """Inline all frontend assets into a single self-contained HTML page."""
    template = (get_frontend_dir() / "index.html").read_text()
    styles_css = (get_frontend_dir() / "styles.css").read_text()

    data_js = (
        "// Auto-generated by build_page — do not edit manually\n\n"
        "window.CLUSTER_DATA = " + json.dumps(cluster_data, indent=2) + ";\n\n"
        "window.CLUSTER_DATA.tree = " + json.dumps(tree, indent=2) + ";\n"
    )
    if prefetched_meta:
        data_js += "\nwindow.__talentMetaCache = " + json.dumps(prefetched_meta, indent=2) + ";\n"

    html = template
    
    # Use simple literal replacement for fixed patterns (ignoring leading whitespace)
    def robust_replace(content, pattern, replacement):
        match = re.search(pattern, content, flags=re.DOTALL)
        if match:
            return content.replace(match.group(0), replacement)
        return content

    # Replace CSS
    html = robust_replace(html, r'<link rel="stylesheet" href="styles\.css"\s*/>', f"<style>\n{styles_css}\n</style>")
    
    # Replace data scripts
    html = robust_replace(html, r'<script src="tree-data\.js"></script>\s*<script src="data\.js"></script>', f"<script>\n{data_js}\n</script>")
    
    # Replace JSX components
    for jsx_file in ["talent-meta.js", "tweaks-panel.jsx", "tree.jsx", "sidebar.jsx", "app.jsx"]:
        src = (get_frontend_dir() / jsx_file).read_text()
        pattern = fr'<script type="text/babel" src="{re.escape(jsx_file)}"></script>'
        html = robust_replace(html, pattern, f'<script type="text/babel">\n{src}\n</script>')
        
    return html


import http.server
import threading


class DynamicReportHandler(http.server.SimpleHTTPRequestHandler):
    """Handler that generates reports on-demand if they are missing."""

    def translate_path(self, path):
        parsed_path = path.split("?")[0]
        if parsed_path.startswith("/pages/") and parsed_path.endswith(".html"):
            filename = parsed_path.split("/")[-1]
            print(f"[Server] Translating: {filename}", flush=True)
            
            # expected: spec_bracket.html or spec_bracket_zh.html
            match = re.match(r"^([a-z0-9-]+)_([a-z0-9-]+)(_zh)?\.html$", filename)
            if match:
                spec, bracket, is_zh = match.groups()
                locale = "zh_CN" if is_zh else "en_US"
                pages_dir = get_pages_dir()
                full_path = pages_dir / filename
                
                needs_build = not full_path.exists()
                if not needs_build:
                    age = time.time() - full_path.stat().st_mtime
                    if age > 2 * 3600:
                        print(f"[Server] {filename} is old ({age/3600:.1f}h). Rebuilding...", flush=True)
                        needs_build = True
                
                if needs_build:
                    print(f"[Server] Triggering on-demand build for {filename} (spec={spec}, bracket={bracket})...", flush=True)
                    try:
                        # Ensure we don't open browser during on-demand generation
                        result = build_page(spec, bracket, locale=locale, open_browser=False)
                        if "error" in result:
                            print(f"[Server] build_page failed: {result['error']}", flush=True)
                            # Generate a friendly error page so it's not a raw 404
                            error_html = f"<html><body style='background:#0a0d12;color:#ff6b6b;font-family:sans-serif;padding:40px;'><h2>Build Failed</h2><p>{result['error']}</p><a href='/pages/restoration-shaman_3v3.html' style='color:#fff'>Go Back</a></body></html>"
                            full_path.write_text(error_html, encoding="utf-8")
                        else:
                            print(f"[Server] Successfully generated {filename}", flush=True)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        print(f"[Server] Error building {filename}: {e}", flush=True)
            
            return str(get_pages_dir() / filename)
            
        return super().translate_path(path)

    def do_GET(self):
        # Log all GET requests for debugging
        print(f"[Server] GET {self.path}", flush=True)
        return super().do_GET()

    def do_HEAD(self):
        # Log all HEAD requests for debugging
        print(f"[Server] HEAD {self.path}", flush=True)
        return super().do_HEAD()


_server_started = False


def _ensure_server(port: int = 8080) -> None:
    """Start the frontend HTTP server in a background thread if it is not already listening."""
    global _server_started
    if _server_started:
        return

    # Check if someone else is already listening on the port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) == 0:
            _server_started = True
            return

    def run_server():
        frontend_dir = get_frontend_dir()
        handler = lambda *args, **kwargs: DynamicReportHandler(
            *args, directory=str(frontend_dir), **kwargs
        )
        httpd = http.server.HTTPServer(("localhost", port), handler)
        httpd.serve_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    _server_started = True

    # Wait briefly for the server to accept connections
    deadline = time.time() + 2
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) == 0:
                return
        time.sleep(0.1)


def _open_browser(url: str) -> None:
    """Open *url* in the default browser (cross-platform)."""
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", url])
    elif system == "Windows":
        subprocess.Popen(["start", url], shell=True)
    else:
        subprocess.Popen(["xdg-open", url])


from wow_advisor.api.wowhead import prefetch_tooltips


def build_page(spec: str, bracket: str, region: str = "us", locale: str = "en_US", open_browser: bool = True) -> dict:
    """Build a self-contained HTML page for a spec+bracket.

    Fetches summary + tree structure, bundles everything inline, and writes
    frontend/pages/{spec}_{bracket}.html.

    Returns:
        {"path": str, "url": str, "spec": str, "bracket": str,
         "sample_size": int, "clusters": int}
    """
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)

    raw = get_full_summary(spec=spec, bracket=bracket, region=region, locale=locale)
    if "error" in raw:
        return raw

    tree = get_tree_structure(spec=spec, locale=locale)
    if "error" in tree:
        return tree

    cluster_data = _make_cluster_data(raw, tree, locale=locale)
    
    # Load and embed individual player details for client-side player inspection
    try:
        from wow_advisor.cache.db import get_default_db
        from wow_advisor.cache.store import CacheStore
        conn = get_default_db()
        store = CacheStore(conn)
        players = store.get_players(spec=spec, bracket=bracket, region=region, locale=locale)
        serialized_players = []
        for p in players:
            p_dict = {
                "name": p.name,
                "realm": p.realm,
                "region": p.region,
                "class": p.character_class,
                "spec": p.spec,
                "ilvl": p.equipped_ilvl,
                "rating": p.rating,
            }
            if p.talent:
                p_dict["talent"] = {
                    "loadout_code": p.talent.loadout_code,
                    "node_ranks": p.talent.node_ranks,
                    "class_node_ids": p.talent.class_node_ids,
                    "spec_node_ids": p.talent.spec_node_ids,
                    "hero_node_ids": p.talent.hero_node_ids,
                    "pvp_talent_ids": p.talent.pvp_talent_ids,
                    "pvp_talent_names": p.talent.pvp_talent_names,
                }
            if p.gear:
                p_dict["gear"] = [
                    {
                        "slot": g.slot,
                        "item_id": g.item_id,
                        "item_name": g.item_name,
                        "ilvl": g.ilvl,
                        "enchant_id": g.enchant_id,
                        "enchant_name": g.enchant_name,
                    }
                    for g in p.gear
                ]
            serialized_players.append(p_dict)
        cluster_data["players"] = serialized_players
    except Exception as e:
        print(f"[Warning] Failed to embed players details: {e}")
    
    # Pre-fetch Wowhead tooltips for instant hovers
    spell_ids = set()
    for t in tree.get("trees", []):
        spell_ids.update(n.get("spellId") for n in t.get("nodes", []) if n.get("spellId"))
    for ht in tree.get("heroTrees", {}).values():
        spell_ids.update(n.get("spellId") for n in ht.get("nodes", []) if n.get("spellId"))
    for pvp in raw.get("pvp_talents", []):
        spell_ids.add(pvp.get("id"))
    
    ench_ids = set()
    for slot in raw.get("enchants", {}).values():
        for e in slot:
            if e.get("enchant_id"):
                ench_ids.add(e["enchant_id"])
    
    # Run async fetches synchronously
    tooltips = asyncio.run(prefetch_tooltips(list(spell_ids), type_str="spell", locale=locale))
    ench_tips = asyncio.run(prefetch_tooltips(list(ench_ids), type_str="ench", locale=locale))
    
    # Merge into a single meta cache
    meta_cache = {}
    for sid, data in tooltips.items():
        meta_cache[sid] = {
            "name": data.get("name"),
            "icon": f"https://wow.zamimg.com/images/wow/icons/medium/{data.get('icon')}.jpg" if data.get("icon") else None,
            "descHtml": data.get("tooltip")
        }
    for eid, data in ench_tips.items():
        meta_cache[f"ench-{eid}"] = {
            "name": data.get("name"),
            "icon": f"https://wow.zamimg.com/images/wow/icons/medium/{data.get('icon')}.jpg" if data.get("icon") else None,
            "descHtml": data.get("tooltip")
        }

    html = _bundle_html(cluster_data, tree, prefetched_meta=meta_cache)

    pages_dir = get_pages_dir()
    suffix = "_zh" if locale == "zh_CN" else ""
    
    # Unify bracket naming with frontend (solo-shuffle, blitz)
    bracket_slug = bracket
    if "shuffle" in bracket:
        bracket_slug = "solo-shuffle"
    elif "blitz" in bracket:
        bracket_slug = "blitz"
    
    filename = f"{spec}_{bracket_slug}{suffix}.html"
    out_path = pages_dir / filename
    out_path.write_text(html, encoding="utf-8")

    port = 8080
    _ensure_server(port)

    url = f"http://localhost:{port}/pages/{filename}"
    if open_browser:
        _open_browser(url)

    return {
        "path": str(out_path),
        "url": url,
        "spec": spec,
        "bracket": bracket,
        "sample_size": raw["sample_size"],
        "clusters": len(cluster_data["clusters"]),
    }
