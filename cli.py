#!/usr/bin/env python3
"""Developer/debug CLI: fetches and prints raw JSON for inspection.

For the end-user CLI that builds the visual report page, use `wow-advisor`
(wow_advisor/cli.py) instead.

Usage:
    python cli.py summary <spec> <bracket> [--region us]   # single-command full report
    python cli.py fetch <spec> <bracket> [--region us] [--limit 50]
    python cli.py talents <spec> <bracket> [--region us]
    python cli.py gear <spec> <bracket> [--region us]
    python cli.py player <name> <realm> [--region us]
"""
import argparse
import json
import sys
from dotenv import load_dotenv
load_dotenv()

from wow_advisor.tools.fetch import fetch_top_players
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

    dispatch = {"summary": cmd_summary, "fetch": cmd_fetch, "talents": cmd_talents, "gear": cmd_gear, "player": cmd_player}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
