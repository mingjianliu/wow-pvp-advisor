#!/usr/bin/env python3
"""Developer/debug CLI: fetches and prints raw JSON for inspection.

For the end-user CLI that builds the visual report page, use `wow-advisor`
(wow_advisor/cli.py) instead.

Usage:
    python cli.py summary <spec> <bracket> [--region us]   # single-command full report
    python cli.py fetch <spec> <bracket> [--region us] [--limit 50]
    python cli.py fetch-all <bracket> [--locales en_US,zh_CN] [--specs a,b]
    python cli.py talents <spec> <bracket> [--region us]
    python cli.py gear <spec> <bracket> [--region us]
    python cli.py player <name> <realm> [--region us]
"""
import argparse
import json
import sys
from dotenv import load_dotenv
load_dotenv()

from wow_advisor.tools.fetch import fetch_top_players, fetch_bracket
from wow_advisor.tools.talents import get_talent_distribution
from wow_advisor.tools.gear import get_gear_summary, get_player_details
from wow_advisor.tools.summary import get_full_summary


def cmd_summary(args):
    result = get_full_summary(spec=args.spec, bracket=args.bracket, region=args.region)
    print(json.dumps(result, indent=2))


def cmd_fetch(args):
    print(f"Fetching top {args.limit} {args.spec} players in {args.bracket} ({args.region})...")
    result = fetch_top_players(spec=args.spec, bracket=args.bracket, region=args.region, limit=args.limit)
    print(json.dumps(result, indent=2))


def cmd_fetch_all(args):
    locales = tuple(l.strip() for l in args.locales.split(",") if l.strip())
    specs = [s.strip() for s in args.specs.split(",")] if args.specs else None
    print(f"Collecting {args.bracket} ({args.region}) for "
          f"{len(specs) if specs else 'all'} specs x {len(locales)} locale(s)...")

    def progress(r):
        if r.get("note"):
            print(f"  {r['spec']:26s} -- {r['note']}")
        else:
            print(f"  {r['spec']:26s} {r['locale']} n={r['fetched']}"
                  + ("  [clustering degraded]" if r.get("clustering_degraded") else ""))

    result = fetch_bracket(bracket=args.bracket, region=args.region, limit=args.limit,
                           locales=locales, specs=specs, progress=progress)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, indent=2))


def cmd_talents(args):
    result = get_talent_distribution(spec=args.spec, bracket=args.bracket, region=args.region)
    print(json.dumps(result, indent=2))


def cmd_gear(args):
    result = get_gear_summary(spec=args.spec, bracket=args.bracket, region=args.region)
    print(json.dumps(result, indent=2))


def cmd_player(args):
    result = get_player_details(name=args.name, realm=args.realm, region=args.region)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="WoW PvP Advisor CLI")
    sub = parser.add_subparsers(dest="command")

    p_summary = sub.add_parser("summary", help="Full report: gear + talents + PvP talents (auto-fetches)")
    p_summary.add_argument("spec")
    p_summary.add_argument("bracket")
    p_summary.add_argument("--region", default="us")

    p_fetch = sub.add_parser("fetch", help="Fetch top players for a spec+bracket")
    p_fetch.add_argument("spec")
    p_fetch.add_argument("bracket")
    p_fetch.add_argument("--region", default="us")
    p_fetch.add_argument("--limit", type=int, default=50)

    p_fetch_all = sub.add_parser(
        "fetch-all",
        help="Fetch every spec in a bracket from one shared ladder scan")
    p_fetch_all.add_argument("bracket")
    p_fetch_all.add_argument("--region", default="us")
    p_fetch_all.add_argument("--limit", type=int, default=50)
    p_fetch_all.add_argument("--locales", default="en_US",
                             help="comma-separated, e.g. en_US,zh_CN")
    p_fetch_all.add_argument("--specs", default=None,
                             help="comma-separated spec slugs (default: all)")

    p_talents = sub.add_parser("talents", help="Show talent distribution")
    p_talents.add_argument("spec")
    p_talents.add_argument("bracket")
    p_talents.add_argument("--region", default="us")

    p_gear = sub.add_parser("gear", help="Show gear summary")
    p_gear.add_argument("spec")
    p_gear.add_argument("bracket")
    p_gear.add_argument("--region", default="us")

    p_player = sub.add_parser("player", help="Show a specific player's details")
    p_player.add_argument("name")
    p_player.add_argument("realm")
    p_player.add_argument("--region", default="us")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    dispatch = {"summary": cmd_summary, "fetch": cmd_fetch, "fetch-all": cmd_fetch_all,
                "talents": cmd_talents, "gear": cmd_gear, "player": cmd_player}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
