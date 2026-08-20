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
            pvp_talent_ids=[10, 11, 12],
            pvp_talent_names=["PVP 1", "PVP 2", "PVP 3"]
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


def test_build_aggregation_pvp_ids(tmp_path):
    players = [make_char(i) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert "pvp_talents" in result
    # We expect pvp_talents to be a list of dicts with 'id', 'name', 'count', 'pct'
    assert result["pvp_talents"][0]["id"] == 10
    assert result["pvp_talents"][0]["name"] == "PVP 1"


def test_build_aggregation_pvp_mismatch(tmp_path):
    # Test case where names and IDs have different lengths
    player = make_char(0)
    player.talent.pvp_talent_names = ["PVP 1", "PVP 2"]
    player.talent.pvp_talent_ids = [10] # Only one ID
    
    result = build_aggregation(
        players=[player],
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    
    # zip() will truncate to the shortest list
    assert len(result["pvp_talents"]) == 1
    assert result["pvp_talents"][0]["name"] == "PVP 1"
    assert result["pvp_talents"][0]["id"] == 10


def test_build_aggregation_corrupt_keystone_file(tmp_path):
    keystone_file = tmp_path / "corrupt.json"
    keystone_file.write_text("{ corrupt json")
    
    players = [make_char(0)]
    # Should not raise exception, should fall back to non-keystone clustering
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(keystone_file),
    )
    assert result["talents"]["clustering_method"] == "variance+weighted"


def test_clustering_degraded_flag_when_tree_unavailable(tmp_path, monkeypatch):
    # A tree-structure failure leaves every talent with the same clustering
    # weight, which changes the build variants. It must be visible in the
    # output, not silently cached as a sound aggregation.
    monkeypatch.setattr(
        "wow_advisor.processor.aggregator.get_tree_structure",
        lambda spec: {"error": "boom"},
    )
    result = build_aggregation(
        players=[make_char(i) for i in range(10)],
        spec="restoration-shaman", bracket="3v3", region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert result["clustering_degraded"] is True


def test_clustering_not_degraded_when_tree_available(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "wow_advisor.processor.aggregator.get_tree_structure",
        lambda spec: {"trees": [{"nodes": [
            {"id": 201, "row": 5, "type": "choice"},
            {"id": 202, "row": 1, "type": "single"},
        ]}], "heroTrees": {}},
    )
    result = build_aggregation(
        players=[make_char(i) for i in range(10)],
        spec="restoration-shaman", bracket="3v3", region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert result["clustering_degraded"] is False
