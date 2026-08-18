"""Bring every non-player cache to the live game build.

Player data (leaderboards, gear, loadouts, aggregations) is deliberately NOT
touched: those are refetched lazily per spec, gated by the game_build stamp on
each aggregation. This script covers the static game data those aggregations are
interpreted against:

  1. talent_node_cache  — node id -> name/row/col/type, per spec and locale
  2. pvp_talent_pool    — the full PvP talent pool per spec, the diff baseline
  3. tooltips           — Wowhead spell descriptions used for hovers

Run it after a patch lands:

    python scripts/refresh_static_data.py
    python scripts/refresh_static_data.py --locales en_US zh_CN
    python scripts/refresh_static_data.py --skip-tooltips
"""
import argparse
import asyncio
import sys

from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.client import BnetClient
from wow_advisor.api.wowhead import prefetch_tooltips
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.config import load_config
from wow_advisor.normalize import _SPEC_INFO_MAP
from wow_advisor.processor.pvp_talents import refresh_pvp_talent_pools
from wow_advisor.processor.talent_names import TalentNameCache
from wow_advisor.settings import MissingCredentialsError, get_credentials


def refresh_talent_trees(conn, client, specs, locale):
    """Re-resolve every spec's talent nodes, restamping each with the live build."""
    cache = TalentNameCache(conn)
    spell_ids, failed = set(), []
    for spec in specs:
        nodes = cache.resolve(spec, client, locale=locale)
        if not nodes:
            failed.append(spec)
            continue
        for node in nodes.values():
            if node.get("icon"):
                spell_ids.add(int(node["icon"]))
    builds = {cache.game_build(s, locale=locale) for s in specs}
    builds.discard(None)
    print(f"  talent trees: {len(specs) - len(failed)}/{len(specs)} specs, "
          f"build {'/'.join(sorted(builds)) or 'unknown'}, {len(spell_ids)} spell ids referenced")
    if failed:
        print(f"    FAILED: {', '.join(failed)}")
    return spell_ids


async def refresh_tooltips(conn, spell_ids, locale, force):
    if force:
        deleted = conn.execute(
            "DELETE FROM tooltips WHERE type='spell' AND locale_id=?",
            (0 if locale == "en_US" else 4,),
        ).rowcount
        conn.commit()
        print(f"  tooltips: cleared {deleted} cached spell rows")

    known = {
        r[0] for r in conn.execute(
            "SELECT id FROM tooltips WHERE type='spell' AND locale_id=?",
            (0 if locale == "en_US" else 4,),
        )
    }
    targets = sorted(spell_ids | known)
    print(f"  tooltips: refreshing {len(targets)} spell ids "
          f"({len(spell_ids)} from trees, {len(known - spell_ids)} previously cached only)")
    result = await prefetch_tooltips(targets, type_str="spell", locale=locale)
    print(f"  tooltips: {len(result)}/{len(targets)} returned data")


async def main(locales, skip_tooltips, force_tooltips) -> int:
    load_config()
    try:
        client_id, client_secret = get_credentials()
    except MissingCredentialsError as e:
        print(e, file=sys.stderr)
        return 1

    client = BnetClient(auth=BnetAuth(client_id, client_secret), region="us")
    conn = get_default_db()
    store = CacheStore(conn)
    specs = sorted(_SPEC_INFO_MAP)

    for locale in locales:
        print(f"\n=== {locale} ({len(specs)} specs) ===")
        spell_ids = refresh_talent_trees(conn, client, specs, locale)

        report = await refresh_pvp_talent_pools(store, client, specs, locale=locale, save=True)
        counts = {}
        for entry in report.values():
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
        print(f"  pvp talent pools: " + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
        for spec in sorted(report):
            if report[spec]["status"] == "changed":
                d = report[spec]["diff"]
                for t in d["added"]:
                    print(f"    {spec}: + {t['name']} ({t['id']})")
                for t in d["removed"]:
                    print(f"    {spec}: - {t['name']} ({t['id']})")
                for t in d["renamed"]:
                    print(f"    {spec}: ~ {t['id']}: {t['from']} -> {t['to']}")

        if skip_tooltips:
            print("  tooltips: skipped")
        else:
            await refresh_tooltips(conn, spell_ids, locale, force_tooltips)

    print("\nPlayer data untouched — each aggregation refetches on first access "
          "because its game_build no longer matches.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--locales", nargs="+", default=["en_US", "zh_CN"])
    ap.add_argument("--skip-tooltips", action="store_true")
    ap.add_argument("--force-tooltips", action="store_true",
                    help="clear cached spell tooltips first instead of relying on their 30-day TTL")
    raise SystemExit(asyncio.run(main(**vars(ap.parse_args()))))
