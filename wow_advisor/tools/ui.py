"""
Build a self-contained HTML page for a spec+bracket and write it to frontend/pages/.

Entry point: build_page(spec, bracket, region) -> {"path": str, "url": str}
"""

import json
import platform
import re
import socket
import subprocess
import time
from pathlib import Path

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
            {**t, "name": t.get("name") or id_to_name.get(t["id"])}
            for t in talent_list
            if (t.get("name") or id_to_name.get(t["id"])) and t["id"] not in hero_ids
        ]

    def strip_hero(lst: list[dict]) -> list[dict]:
        return [t for t in lst if t["id"] not in hero_ids]

    def _hero_core_nodes() -> list[dict]:
        """Return the dominant hero tree's nodes as core entries.

        Hero talents are all-or-nothing tree selections, not individual choices.
        We classify the higher-pick-rate tree as core so the frontend can render
        its nodes green and selectHeroTree() can identify it via overlap.
        """
        all_raw = raw["talents"]["core"] + raw["talents"]["flex"] + raw["talents"]["contested"]
        rate: dict[int, float] = {t["id"]: t["pct"] for t in all_raw if t["id"] in hero_ids}
        left_ids  = {n["id"] for n in tree["heroTrees"]["left"]["nodes"]}
        right_ids = {n["id"] for n in tree["heroTrees"]["right"]["nodes"]}
        left_avg  = sum(rate.get(i, 0) for i in left_ids)  / max(len(left_ids), 1)
        right_avg = sum(rate.get(i, 0) for i in right_ids) / max(len(right_ids), 1)
        dominant  = left_ids if left_avg >= right_avg else right_ids
        return [
            {"id": hid, "name": id_to_name[hid], "pct": rate.get(hid, 0)}
            for hid in dominant
            if hid in id_to_name
        ]

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


def _bundle_html(cluster_data: dict, tree: dict) -> str:
    """Inline all frontend assets into a single self-contained HTML page."""
    template = (get_frontend_dir() / "index.html").read_text()
    styles_css = (get_frontend_dir() / "styles.css").read_text()

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
    for jsx_file in ["talent-meta.js", "tweaks-panel.jsx", "tree.jsx", "sidebar.jsx", "app.jsx"]:
        src = (get_frontend_dir() / jsx_file).read_text()
        html = html.replace(
            f'<script type="text/babel" src="{jsx_file}"></script>',
            f'<script type="text/babel">\n{src}\n</script>',
        )
    return html


import http.server
import threading


class DynamicReportHandler(http.server.SimpleHTTPRequestHandler):
    """Handler that generates reports on-demand if they are missing."""

    def do_GET(self):
        # We serve from the 'frontend' directory, so /pages/... is relative to that.
        path = self.path.split("?")[0]
        if path.startswith("/pages/") and path.endswith(".html"):
            filename = path.split("/")[-1]
            match = re.match(r"^([a-z0-9-]+)_([a-z0-9-]+)\.html$", filename)
            if match:
                spec, bracket = match.groups()
                pages_dir = get_pages_dir()
                full_path = pages_dir / filename
                
                needs_build = not full_path.exists()
                if not needs_build:
                    import time
                    age = time.time() - full_path.stat().st_mtime
                    if age > 2 * 3600:
                        print(f"[Server] {filename} is {age/3600:.1f} hours old. Rebuilding...")
                        needs_build = True

                if needs_build:
                    try:
                        # Ensure we don't open browser during on-demand generation
                        build_page(spec, bracket, open_browser=False)
                        print(f"[Server] Successfully rebuilt {filename}")
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        print(f"[Server] Failed to build {filename}: {e}")

        return super().do_GET()


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


def build_page(spec: str, bracket: str, region: str = "us", open_browser: bool = True) -> dict:
    """Build a self-contained HTML page for a spec+bracket.

    Fetches summary + tree structure, bundles everything inline, and writes
    frontend/pages/{spec}_{bracket}.html.

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

    pages_dir = get_pages_dir()
    filename = f"{spec}_{bracket}.html"
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
