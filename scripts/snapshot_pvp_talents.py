"""Snapshot every spec's full PvP talent pool, and diff against the last snapshot.

The pool is what a spec *can* run, as opposed to what the cached top-50 happened
to pick — so this is the baseline that makes the next patch a real diff instead
of a patch-note reading exercise.

    python scripts/snapshot_pvp_talents.py           # show the diff, change nothing
    python scripts/snapshot_pvp_talents.py --save    # show the diff, then persist

The fetch/diff/save sequence lives in processor/pvp_talents.refresh_pvp_talent_pools;
this script is the reporting shell around it.
"""
import argparse
import asyncio
import sys

from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.client import BnetClient
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.config import load_config
from wow_advisor.normalize import _SPEC_INFO_MAP
from wow_advisor.processor.pvp_talents import refresh_pvp_talent_pools
from wow_advisor.settings import MissingCredentialsError, get_credentials


def print_report(report: dict) -> tuple[int, int, int]:
    new = changed = unchanged = 0
    for spec in sorted(report):
        entry = report[spec]
        status = entry["status"]
        if status == "new":
            new += 1
            print(f"  {spec:24s} NEW BASELINE ({entry['count']} talents)")
        elif status == "changed":
            changed += 1
            was = entry.get("previous_game_build") or "unknown"
            print(f"  {spec:24s} CHANGED since build {was}")
            for t in entry["diff"]["added"]:
                print(f"       + {t['name']} ({t['id']})")
            for t in entry["diff"]["removed"]:
                print(f"       - {t['name']} ({t['id']})")
            for t in entry["diff"]["renamed"]:
                print(f"       ~ {t['id']}: {t['from']} -> {t['to']}")
        elif status == "unknown-spec":
            print(f"  {spec:24s} SKIPPED (not in the spec map)")
        else:
            unchanged += 1
    return new, changed, unchanged


async def main(save: bool, locale: str) -> int:
    load_config()
    try:
        client_id, client_secret = get_credentials()
    except MissingCredentialsError as e:
        print(e, file=sys.stderr)
        return 1

    client = BnetClient(auth=BnetAuth(client_id, client_secret), region="us")
    store = CacheStore(get_default_db())
    specs = sorted(_SPEC_INFO_MAP)

    report = await refresh_pvp_talent_pools(store, client, specs, locale=locale, save=save)
    builds = {e.get("game_build") for e in report.values() if e.get("game_build")}
    print(f"{len(specs)} specs, game build {'/'.join(sorted(builds)) or 'unknown'}, locale {locale}")

    new, changed, unchanged = print_report(report)
    print(f"\n{new} new baselines, {changed} changed, {unchanged} unchanged")
    print("saved" if save else "not saved (re-run with --save to persist)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true", help="persist the fetched pools")
    ap.add_argument("--locale", default="en_US")
    raise SystemExit(asyncio.run(main(**vars(ap.parse_args()))))
