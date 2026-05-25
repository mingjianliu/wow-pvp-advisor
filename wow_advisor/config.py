"""
First-run credential setup and config loading.

Blizzard API keys are stored in get_config_path() so they survive
across sessions and don't need to be re-entered each run.
"""
import os

from wow_advisor._paths import get_config_path


def load_config() -> None:
    """Load config.env into os.environ. Silent if file doesn't exist."""
    cfg = get_config_path()
    if not cfg.exists():
        return
    for line in cfg.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def setup_credentials() -> None:
    """Interactive first-run credential setup. Saves to config.env."""
    cfg = get_config_path()

    # Already configured
    if os.environ.get("BNET_CLIENT_ID") and os.environ.get("BNET_CLIENT_SECRET"):
        return

    print("WoW Advisor — first-time setup")
    print("You need a Blizzard API client. Create one free at:")
    print("  https://develop.battle.net/access/clients")
    print()
    client_id = input("BNET_CLIENT_ID: ").strip()
    client_secret = input("BNET_CLIENT_SECRET: ").strip()

    if not client_id or not client_secret:
        raise SystemExit("Credentials required. Exiting.")

    cfg.write_text(f"BNET_CLIENT_ID={client_id}\nBNET_CLIENT_SECRET={client_secret}\n")
    os.environ["BNET_CLIENT_ID"] = client_id
    os.environ["BNET_CLIENT_SECRET"] = client_secret
    print(f"Saved to {cfg}\n")


def has_credentials() -> bool:
    load_config()
    return bool(os.environ.get("BNET_CLIENT_ID") and os.environ.get("BNET_CLIENT_SECRET"))
