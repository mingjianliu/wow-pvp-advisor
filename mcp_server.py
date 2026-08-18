import os as _os
from dotenv import load_dotenv
load_dotenv(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".env"))

from fastmcp import FastMCP
from wow_advisor.tools.fetch import fetch_top_players
from wow_advisor.tools.talents import get_talent_distribution
from wow_advisor.tools.gear import get_gear_summary, get_player_details
from wow_advisor.tools.summary import get_full_summary
from wow_advisor.tools.ui import build_page
from wow_advisor.talent_tree import get_tree_structure

mcp = FastMCP("wow-pvp-advisor")


@mcp.tool()
def fetch_top_players_tool(spec: str, bracket: str, region: str = "us", limit: int = 50) -> dict:
    """Fetch and cache top players for a spec+bracket. Call this first or to refresh stale data.

    The PvP season is detected from the Blizzard API, so a season rollover needs
    no code change. While a brand-new season's ladder is still empty, results
    come from the previous season and the response carries
    "season_fallback": true alongside the "season_id" actually used.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham', 'arms warrior'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle', 'blitz', 'rbg'
        region: 'us' or 'eu' (default: 'us')
        limit: Number of top players to fetch (default: 50)
    """
    return fetch_top_players(spec=spec, bracket=bracket, region=region, limit=limit)


@mcp.tool()
def get_talent_distribution_tool(spec: str, bracket: str, region: str = "us") -> dict:
    """Get talent build distribution for a spec+bracket from top players.

    Returns talent clusters ranked by pick rate, with core/contested/flex node breakdown.
    Auto-fetches if cache is older than 24 hours.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle'
        region: 'us' or 'eu' (default: 'us')
    """
    return get_talent_distribution(spec=spec, bracket=bracket, region=region)


@mcp.tool()
def get_gear_summary_tool(spec: str, bracket: str, region: str = "us") -> dict:
    """Get gear and enchant summary for a spec+bracket from top players.

    Returns most popular items per slot, enchant frequencies, avg item level.
    Trinkets highlighted. Auto-fetches if cache is older than 24 hours.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle'
        region: 'us' or 'eu' (default: 'us')
    """
    return get_gear_summary(spec=spec, bracket=bracket, region=region)


@mcp.tool()
def get_full_summary_tool(spec: str, bracket: str, region: str = "us") -> dict:
    """Complete PvP meta summary for a spec+bracket in one call.

    Returns everything: regular talent clusters, PvP talent pick rates,
    gear per slot, and enchants. Auto-fetches from Blizzard API if the cache is
    older than 2 hours, or if the game build changed since it was computed.
    Use this as the default starting point.

    Blizzard reassigns talents across node IDs between client builds, so cached
    data is only interpretable against the build it was captured under. If a
    refresh could not repair a build mismatch, talent names are withheld rather
    than guessed and a "stale_build" field reports {aggregation, current}.

    "season_id" reports which ladder the sample came from; "season_fallback": true
    appears when that is not the current season (a season that has just started
    has no ranked ladder yet).

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham', 'arms warrior'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle', 'blitz', 'rbg'
        region: 'us' or 'eu' (default: 'us')
    """
    return get_full_summary(spec=spec, bracket=bracket, region=region)


@mcp.tool()
def get_tree_structure_tool(spec: str) -> dict:
    """Return the talent tree layout (nodes, positions, edges) for a spec.

    Node IDs match what get_full_summary_tool returns in talents.core/flex/contested,
    so the frontend can color the tree based on cluster data. Hero trees are correctly
    split using the Blizzard API's hero_talent_nodes — works for all 39 specs.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham'
    """
    return get_tree_structure(spec=spec)


@mcp.tool()
def build_page_tool(spec: str, bracket: str, region: str = "us") -> dict:
    """Build a self-contained HTML page for a spec+bracket and return its URL.

    Fetches the full summary, builds the talent tree layout, and writes a
    standalone HTML file to frontend/pages/{spec}_{bracket}.html.
    The page is immediately accessible at the returned URL (requires the
    local HTTP server to be running on port 8080).

    Call this as the final step after fetching data to produce a visual output.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham', 'arms warrior'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle'
        region: 'us' or 'eu' (default: 'us')
    """
    return build_page(spec=spec, bracket=bracket, region=region)


@mcp.tool()
def get_player_details_tool(name: str, realm: str, region: str = "us") -> dict:
    """Get full gear and talent details for a specific player from the local cache.

    Player must have been included in a recent fetch_top_players call.

    Args:
        name: Character name
        realm: Realm slug, e.g. 'area-52', 'stormrage'
        region: 'us' or 'eu' (default: 'us')
    """
    return get_player_details(name=name, realm=realm, region=region)


if __name__ == "__main__":
    mcp.run()
