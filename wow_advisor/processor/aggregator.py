import json
import os
from wow_advisor.api.models import CharacterData
from wow_advisor.processor.talents import summarize_talent_clusters
from wow_advisor.processor.gear import aggregate_gear

_DEFAULT_KEYSTONE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "keystone_talents.json")
)


def _load_keystone_nodes(spec: str, keystone_file: str) -> list[int] | None:
    if not os.path.exists(keystone_file):
        return None
    with open(keystone_file) as f:
        data = json.load(f)
    return data.get(spec)


def build_aggregation(
    players: list[CharacterData],
    spec: str,
    bracket: str,
    region: str,
    keystone_file: str = _DEFAULT_KEYSTONE_FILE,
) -> dict:
    players_with_talent = [p for p in players if p.talent is not None]
    node_sets = [p.talent.all_node_ids for p in players_with_talent]
    loadout_codes = [p.talent.loadout_code for p in players_with_talent]
    keystone_nodes = _load_keystone_nodes(spec, keystone_file)

    talent_summary = summarize_talent_clusters(
        node_sets=node_sets,
        loadout_codes=loadout_codes,
        keystone_nodes=keystone_nodes,
    )

    equipped_ilvls = [p.equipped_ilvl for p in players]
    gear_per_player = [p.gear for p in players]
    gear_summary = aggregate_gear(
        gear_per_player=gear_per_player,
        n_players=len(players),
        equipped_ilvls=equipped_ilvls,
    )

    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": len(players),
        "avg_ilvl": gear_summary["avg_ilvl"],
        "talents": talent_summary,
        "gear": gear_summary["gear"],
        "enchants": gear_summary["enchants"],
    }
