"""
WoW Advisor CLI

Usage:
  wow-advisor <spec> <bracket> [--region us|eu] [--refresh] [--no-open]

Examples:
  wow-advisor "restoration shaman" 3v3
  wow-advisor rsham 3v3 --region eu
  wow-advisor holy-paladin 2v2 --refresh
"""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wow-advisor",
        description="WoW PvP talent cluster advisor — builds a visual page for any spec+bracket.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("spec",    help='Spec name, e.g. "restoration shaman", rsham, holy-paladin')
    parser.add_argument("bracket", help="PvP bracket, e.g. 3v3, 2v2, solo")
    parser.add_argument("--region",   default="us", choices=["us", "eu"], help="Region (default: us)")
    parser.add_argument("--refresh",  action="store_true", help="Force re-fetch from Blizzard API even if cached")
    parser.add_argument("--no-open",  action="store_true", help="Build page without opening the browser")
    parser.add_argument("--setup",    action="store_true", help="Re-run credential setup")

    args = parser.parse_args()

    # Load + optionally set up credentials
    from wow_advisor.config import load_config, setup_credentials, has_credentials
    load_config()
    if args.setup or not has_credentials():
        setup_credentials()

    if not has_credentials():
        print("Error: Blizzard API credentials not configured.", file=sys.stderr)
        print("Run with --setup to enter them.", file=sys.stderr)
        sys.exit(1)

    # Force cache refresh if requested
    if args.refresh:
        from wow_advisor.normalize import normalize_spec, normalize_bracket
        from wow_advisor.cache.db import get_default_db
        from wow_advisor.cache.store import CacheStore
        spec = normalize_spec(args.spec)
        bracket = normalize_bracket(args.bracket)
        conn = get_default_db()
        store = CacheStore(conn)
        # Delete aggregation so next call re-fetches
        conn.execute(
            "DELETE FROM aggregations WHERE spec=? AND bracket=? AND region=?",
            (spec, bracket, args.region),
        )
        conn.commit()
        print(f"Cache cleared for {spec}/{bracket} — will re-fetch.")

    print(f"Building page for {args.spec!r} / {args.bracket} [{args.region}] ...")

    from wow_advisor.tools.ui import build_page, _open_browser
    result = build_page(args.spec, args.bracket, args.region)

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"  Spec:     {result['spec']}")
    print(f"  Bracket:  {result['bracket']}")
    print(f"  Players:  {result['sample_size']}")
    print(f"  Clusters: {result['clusters']}")
    print(f"  File:     {result['path']}")

    if args.no_open:
        print(f"\nOpen manually: {result['url']}")
    else:
        print(f"\nOpening browser...")
        # build_page already opens the browser; nothing extra needed


if __name__ == "__main__":
    main()
