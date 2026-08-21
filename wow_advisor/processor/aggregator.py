import logging
from collections import Counter
from wow_advisor.api.models import CharacterData
from wow_advisor.processor.talents import summarize_talent_clusters
from wow_advisor.processor.gear import aggregate_gear
from wow_advisor.talent_tree import get_tree_structure

logger = logging.getLogger(__name__)

def _aggregate_pvp_talents(players_with_talent: list[CharacterData]) -> list[dict]:
    """Calculate frequency of PvP talents across players with talent data."""
    pvp_counts: Counter = Counter()
    pvp_pickers: dict[tuple[str, int], list[dict]] = {}
    valid_pvp_player_count = 0

    for player in players_with_talent:
        talent = player.talent
        if talent and talent.pvp_talent_names and talent.pvp_talent_ids:
            valid_pvp_player_count += 1
            p_obj = {"n": player.name, "r": player.realm}
            # zip() truncates to the shortest list if lengths happen to mismatch
            for name, tid in zip(talent.pvp_talent_names, talent.pvp_talent_ids):
                key = (name, tid)
                pvp_counts[key] += 1
                if key not in pvp_pickers:
                    pvp_pickers[key] = []
                pvp_pickers[key].append(p_obj)

    denominator = valid_pvp_player_count or 1
    pvp_summary = [
        {
            "name": name,
            "id": tid,
            "count": count,
            "pct": round(count / denominator * 100, 1),
            "pickers": pvp_pickers[(name, tid)],
        }
        for (name, tid), count in pvp_counts.items()
    ]

    return sorted(pvp_summary, key=lambda x: x["count"], reverse=True)


def build_aggregation(
    players: list[CharacterData],
    spec: str,
    bracket: str,
    region: str,
) -> dict:
    """
    Build a comprehensive summary of talents, gear, and PvP talents from a list of players.

    Args:
        players: List of CharacterData objects to aggregate.
        spec: The specialization name.
        bracket: PvP bracket (e.g., '3v3').
        region: Region code (e.g., 'us').

    Returns:
        A dictionary containing the aggregated data.
    """
    players_with_talent = [p for p in players if p.talent is not None]

    # Talent clustering
    node_sets = [p.talent.all_node_ids for p in players_with_talent]
    node_ranks_list = [p.talent.node_ranks for p in players_with_talent]
    loadout_codes = [p.talent.loadout_code for p in players_with_talent]

    # Fetch tree structure to get node metadata (row, type) for clustering weights
    tree_data = get_tree_structure(spec)
    node_meta = {}
    # get_tree_structure swallows every failure into an error dict. Without node
    # metadata each talent carries the same clustering weight, so the build
    # variants come out genuinely different — silently, and cached as sound for
    # the full TTL. Record it so a degraded run is identifiable and rebuildable.
    tree_error = tree_data.get("error")
    if tree_error:
        logger.warning(
            "Talent tree structure unavailable for %s (%s) — clustering weights "
            "degraded to uniform for this aggregation.", spec, tree_error,
        )
    else:
        # Extract from main trees (class, spec)
        for tree in tree_data.get("trees", []):
            for node in tree.get("nodes", []):
                node_meta[node["id"]] = {
                    "row": node["row"],
                    "type": node["type"],
                    "is_hero": False,
                }
        # Extract from hero trees. "hero_tree" records which tree the node
        # belongs to so clustering can partition players by tree identity
        # rather than by exact node picks (hero trees contain choice nodes).
        hero_trees = tree_data.get("heroTrees", {})
        for side in ["left", "right"]:
            hero_tree = hero_trees.get(side, {})
            for node in hero_tree.get("nodes", []):
                node_meta[node["id"]] = {
                    "row": node["row"],
                    "type": node["type"],
                    "is_hero": True,
                    "hero_tree": side,
                }

    player_info = [{"name": p.name, "realm": p.realm, "region": p.region} for p in players_with_talent]

    talent_summary = summarize_talent_clusters(
        node_sets=node_sets,
        loadout_codes=loadout_codes,
        node_ranks_list=node_ranks_list,
        node_meta=node_meta,
        player_info=player_info,
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
        # True when node metadata was missing, so clustering ran unweighted.
        "clustering_degraded": bool(tree_error),
        "pvp_talents": pvp_summary,
        "gear": gear_summary["gear"],
        "enchants": gear_summary["enchants"],
    }
