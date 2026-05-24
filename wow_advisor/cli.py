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
    parser.add_argument("spec",    nargs="?", help='Spec name, e.g. "restoration shaman", rsham. Leave blank for a random spec.')
    parser.add_argument("bracket", nargs="?", default="3v3", help="PvP bracket, e.g. 3v3, 2v2, solo (default: 3v3)")
    parser.add_argument("--region",   default="us", choices=["us", "eu"], help="Region (default: us)")
    parser.add_argument("--refresh",  action="store_true", help="Force re-fetch from Blizzard API even if cached")
    parser.add_argument("--no-open",  action="store_true", help="Build page without opening the browser")
    parser.add_argument("--setup",    action="store_true", help="Re-run credential setup")

    args = parser.parse_args()

    # If no spec provided, pick a random one
    is_app_mode = False
    if not args.spec:
        import random
        from wow_advisor.normalize import _SPEC_CLASS_MAP
        args.spec = random.choice(list(_SPEC_CLASS_MAP.keys()))
        args.bracket = "3v3"
        is_app_mode = True
        print(f"No spec provided. Opening random spec: {args.spec} {args.bracket}")

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

    if is_app_mode:
        from wow_advisor.tools.ui import _ensure_server, _open_browser
        
        def slugify(s: str) -> str:
            return s.lower().replace(" ", "-")
            
        port = 8080
        _ensure_server(port)
        
        # We don't have the class name directly without looking it up, but we know it's a valid slug.
        # However, the on-demand server uses the filename.
        from wow_advisor.normalize import spec_to_class_spec
        class_spec = spec_to_class_spec(args.spec)
        if not class_spec:
            print(f"Error: Unknown spec '{args.spec}'", file=sys.stderr)
            sys.exit(1)
        target_class, target_spec = class_spec
        
        filename = f"{slugify(target_spec)}-{slugify(target_class)}_{args.bracket}.html"
        url = f"http://localhost:{port}/pages/{filename}"
        
        print(f"Opening browser to {url} ...")
        _open_browser(url)
        
        import time
        print("\nRunning in App Mode. Server is active. Press Ctrl+C to quit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down.")
            sys.exit(0)

    print(f"Building page for {args.spec!r} / {args.bracket} [{args.region}] ...")

    from wow_advisor.tools.ui import build_page
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
        print(f"\nBrowser opened.")

if __name__ == "__main__":
    main()
