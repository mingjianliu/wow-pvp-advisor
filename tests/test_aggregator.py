import pytest
from wow_advisor.api.models import CharacterData, TalentData, GearSlot
from wow_advisor.processor.aggregator import build_aggregation


def make_char(i: int, spec_node_extra: int | None = None) -> CharacterData:
    class_nodes = [101, 102, 103]
    spec_nodes = [201, 202]
    if spec_node_extra is not None:
        spec_nodes = [spec_node_extra]
    return CharacterData(
        name=f"Player{i}", realm="area-52", region="us",
        character_class="Shaman", spec="Restoration",
        equipped_ilvl=639, rating=2800 - i,
        talent=TalentData(
            loadout_code=f"code_{i}",
            class_node_ids=class_nodes,
            spec_node_ids=spec_nodes,
            hero_node_ids=[301],
        ),
        gear=[GearSlot(slot="head", item_id=100 + (i % 2), item_name=f"Hood{i%2}",
                       ilvl=639, enchant_id=7459, enchant_name="Crystalline")],
    )


def test_build_aggregation_structure(tmp_path):
    players = [make_char(i) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert result["spec"] == "restoration-shaman"
    assert result["bracket"] == "3v3"
    assert result["region"] == "us"
    assert result["sample_size"] == 10
    assert "avg_ilvl" in result
    assert "talents" in result
    assert "gear" in result
    assert "enchants" in result
    assert "clusters" in result["talents"]


def test_build_aggregation_gear_present(tmp_path):
    players = [make_char(i) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert "head" in result["gear"]
    assert result["gear"]["head"][0]["pct"] > 0


def test_build_aggregation_keystone_fallback(tmp_path):
    import json
    keystone_file = tmp_path / "keystone_talents.json"
    keystone_file.write_text(json.dumps({"restoration-shaman": [201, 202]}))
    players = [make_char(i, spec_node_extra=201 if i < 7 else 202) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(keystone_file),
    )
    assert result["talents"]["clustering_method"] == "keystone"


def test_build_aggregation_skips_players_without_talent(tmp_path):
    players = [make_char(i) for i in range(8)]
    no_talent = CharacterData(
        name="NoTalent", realm="area-52", region="us",
        character_class="Shaman", spec="Restoration",
        equipped_ilvl=630, rating=2600, talent=None, gear=[],
    )
    players.append(no_talent)
    result = build_aggregation(
        players=players, spec="restoration-shaman", bracket="3v3", region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert result["sample_size"] == 9
