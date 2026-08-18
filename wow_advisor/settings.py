"""Central configuration: tunable constants and credential access.

Every magic number that governs runtime behavior lives here so a change
lands in exactly one place.
"""
import os

# --- Blizzard API ---
# The season is detected per request from /data/wow/pvp-season/index. This is
# only the fallback for when that lookup fails, so it may lag reality — a wrong
# value here surfaces as "no leaderboard data", never as silently stale data.
FALLBACK_SEASON_ID = 41
API_CONCURRENCY = 10

# --- Wowhead (third-party, no published quota) ---
WOWHEAD_CONCURRENCY = 8

# --- Cache ---
AGGREGATION_TTL_HOURS = 2   # full summary / page builds refresh at this age
QUERY_TTL_HOURS = 24        # talent/gear query tools tolerate older data

# --- Frontend HTTP server ---
SERVER_PORT = 8080

# --- Talent analysis / clustering ---
CORE_PICK_RATE = 0.8   # picked by >= this share of players => core talent
FLEX_PICK_RATE = 0.2   # picked by <= this share of players => flex talent
HAC_THRESHOLD = 0.3    # stop merging HAC clusters beyond this distance
MAX_DECISION_NODES = 8 # cap on contested nodes used to define build variants

# Weighted Jaccard node weights
WEIGHT_CHOICE_NODE = 20.0   # diamond (choice) nodes dominate build identity
WEIGHT_MAJOR_NODE = 5.0     # deep-row (row >= 5) talents
WEIGHT_UTILITY_NODE = 0.1   # shallow utility filler


class MissingCredentialsError(RuntimeError):
    """Raised when Blizzard API credentials are not configured."""


def get_credentials() -> tuple[str, str]:
    """Return (client_id, client_secret) or raise a friendly error."""
    client_id = os.environ.get("BNET_CLIENT_ID")
    client_secret = os.environ.get("BNET_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise MissingCredentialsError(
            "Blizzard API credentials not configured. Set BNET_CLIENT_ID and "
            "BNET_CLIENT_SECRET in .env (see README), or run `wow-advisor --setup`."
        )
    return client_id, client_secret
