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
    )
    assert "head" in result["gear"]
    assert result["gear"]["head"][0]["pct"] > 0



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
    )
    assert result["sample_size"] == 9


def test_build_aggregation_pvp_ids(tmp_path):
    players = [make_char(i) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
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
    )
    
    # zip() will truncate to the shortest list
    assert len(result["pvp_talents"]) == 1
    assert result["pvp_talents"][0]["name"] == "PVP 1"
    assert result["pvp_talents"][0]["id"] == 10



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
    )
    assert result["clustering_degraded"] is False


def _varied_players(n: int = 12) -> list[CharacterData]:
    """Players whose talent picks differ enough to produce several contested nodes."""
    players = []
    for i in range(n):
        spec_nodes = [201, 202]
        # each optional node is taken by a different share of the field
        if i % 2: spec_nodes.append(203)
        if i % 3: spec_nodes.append(204)
        if i % 4: spec_nodes.append(205)
        if i % 5: spec_nodes.append(206)
        players.append(CharacterData(
            name=f"P{i}", realm="area-52", region="us",
            character_class="Shaman", spec="Restoration",
            equipped_ilvl=639, rating=2800 - i,
            talent=TalentData(
                loadout_code=f"code_{i}",
                class_node_ids=[101, 102, 103],
                spec_node_ids=spec_nodes,
                hero_node_ids=[301],
                pvp_talent_ids=[10, 11, 12],
                pvp_talent_names=["PVP 1", "PVP 2", "PVP 3"],
            ),
            gear=[GearSlot(slot="head", item_id=100, item_name="Hood",
                           ilvl=639, enchant_id=7459, enchant_name="Crystalline")],
        ))
    return players


def test_decision_node_cap_labels_builds_without_regrouping_them(monkeypatch):
    """MAX_DECISION_NODES is a labelling knob, not a clustering one.

    Clustering runs on full node sets; decision nodes only pick which talents a
    build is described by. A keystone override used to sit on this same variable
    and was documented as "overriding automatic clustering" — it never could,
    and its test only asserted the method label, so the dead path survived.
    """
    players = _varied_players()

    def cluster_shape(cap):
        monkeypatch.setattr("wow_advisor.processor.talents.MAX_DECISION_NODES", cap)
        agg = build_aggregation(players=players, spec="restoration-shaman",
                                bracket="3v3", region="us")
        return (
            [c["count"] for c in agg["talents"]["clusters"]],
            len(agg["talents"]["contested_nodes"]),
        )

    wide_groups, wide_labels = cluster_shape(8)
    narrow_groups, narrow_labels = cluster_shape(1)

    assert wide_groups == narrow_groups, "grouping must not depend on the label cap"
    assert narrow_labels < wide_labels, "the cap must still narrow what is labelled"
