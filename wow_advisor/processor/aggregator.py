import json
import os
from collections import Counter
from wow_advisor.api.models import CharacterData
from wow_advisor.processor.talents import summarize_talent_clusters
from wow_advisor.processor.gear import aggregate_gear

_DEFAULT_KEYSTONE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "keystone_talents.json")
)


def _load_keystone_nodes(spec: str, keystone_file: str) -> list[int] | None:
    """Load keystone node IDs for a given spec from a JSON file."""
    if not os.path.exists(keystone_file):
        return None
    try:
        with open(keystone_file) as f:
            data = json.load(f)
        return data.get(spec)
    except (json.JSONDecodeError, IOError):
        # Fall back to default behavior if file is corrupt or unreadable
        return None


def _aggregate_pvp_talents(players_with_talent: list[CharacterData]) -> list[dict]:
    """Calculate frequency of PvP talents across players with talent data."""
    pvp_counts: Counter = Counter()
    valid_pvp_player_count = 0

    for player in players_with_talent:
        talent = player.talent
        if talent and talent.pvp_talent_names and talent.pvp_talent_ids:
            valid_pvp_player_count += 1
            # zip() truncates to the shortest list if lengths happen to mismatch
            for name, tid in zip(talent.pvp_talent_names, talent.pvp_talent_ids):
                pvp_counts[(name, tid)] += 1

    denominator = valid_pvp_player_count or 1
    pvp_summary = [
        {
            "name": name,
            "id": tid,
            "count": count,
            "pct": round(count / denominator * 100, 1),
        }
        for (name, tid), count in pvp_counts.items()
    ]

    return sorted(pvp_summary, key=lambda x: x["count"], reverse=True)


def build_aggregation(
    players: list[CharacterData],
    spec: str,
    bracket: str,
    region: str,
    keystone_file: str = _DEFAULT_KEYSTONE_FILE,
) -> dict:
    """
    Build a comprehensive summary of talents, gear, and PvP talents from a list of players.

    Args:
        players: List of CharacterData objects to aggregate.
        spec: The specialization name.
        bracket: PvP bracket (e.g., '3v3').
        region: Region code (e.g., 'us').
        keystone_file: Path to the JSON file containing keystone talent nodes.

    Returns:
        A dictionary containing the aggregated data.
    """
    players_with_talent = [p for p in players if p.talent is not None]

    # Talent clustering
    node_sets = [p.talent.all_node_ids for p in players_with_talent]
    loadout_codes = [p.talent.loadout_code for p in players_with_talent]
    keystone_nodes = _load_keystone_nodes(spec, keystone_file)

    talent_summary = summarize_talent_clusters(
        node_sets=node_sets,
        loadout_codes=loadout_codes,
        keystone_nodes=keystone_nodes,
    )

    # Gear and item level aggregation
    equipped_ilvls = [p.equipped_ilvl for p in players]
    gear_per_player = [p.gear for p in players]
    gear_summary = aggregate_gear(
        gear_per_player=gear_per_player,
        n_players=len(players),
        equipped_ilvls=equipped_ilvls,
    )

    # PvP talent aggregation
    pvp_summary = _aggregate_pvp_talents(players_with_talent)

    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": len(players),
        "avg_ilvl": gear_summary["avg_ilvl"],
        "talents": talent_summary,
        "pvp_talents": pvp_summary,
        "gear": gear_summary["gear"],
        "enchants": gear_summary["enchants"],
    }
