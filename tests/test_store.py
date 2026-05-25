import pytest
from wow_advisor.cache.db import init_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.api.models import CharacterData, TalentData, GearSlot


@pytest.fixture
def store(tmp_db):
    conn = init_db(tmp_db)
    return CacheStore(conn)


def make_char(name="Healbot", spec="Restoration", cls="Shaman", rating=2800):
    return CharacterData(
        name=name,
        realm="area-52",
        region="us",
        character_class=cls,
        spec=spec,
        equipped_ilvl=639,
        rating=rating,
        talent=TalentData(
            loadout_code="BAQAAAAAAAAAAAAkU",
            class_node_ids=[101, 102],
            spec_node_ids=[201, 202],
            hero_node_ids=[301],
        ),
        gear=[
            GearSlot(
                slot="head",
                item_id=212456,
                item_name="Hood",
                ilvl=639,
                enchant_id=7459,
                enchant_name="Crystalline",
            )
        ],
    )


def test_save_and_get_players(store):
    chars = [make_char("Player1"), make_char("Player2")]
    store.save_players(chars, spec="restoration-shaman", bracket="3v3")
    players = store.get_players(spec="restoration-shaman", bracket="3v3")
    assert len(players) == 2
    names = {p.name for p in players}
    assert "Player1" in names
    assert "Player2" in names


def test_get_players_empty(store):
    assert store.get_players(spec="arms-warrior", bracket="3v3") == []


def test_saved_talent_roundtrips(store):
    store.save_players([make_char()], spec="restoration-shaman", bracket="3v3")
    players = store.get_players(spec="restoration-shaman", bracket="3v3")
    assert players[0].talent is not None
    assert players[0].talent.loadout_code == "BAQAAAAAAAAAAAAkU"
    assert 101 in players[0].talent.class_node_ids
    assert 201 in players[0].talent.spec_node_ids


def test_saved_gear_roundtrips(store):
    store.save_players([make_char()], spec="restoration-shaman", bracket="3v3")
    players = store.get_players(spec="restoration-shaman", bracket="3v3")
    assert len(players[0].gear) == 1
    assert players[0].gear[0].slot == "head"
    assert players[0].gear[0].enchant_id == 7459


def test_save_aggregation_and_get(store):
    data = {"spec": "restoration-shaman", "sample_size": 50}
    store.save_aggregation(spec="restoration-shaman", bracket="3v3", region="us", data=data)
    result = store.get_aggregation(spec="restoration-shaman", bracket="3v3", region="us")
    assert result is not None
    assert result["sample_size"] == 50


def test_aggregation_overwrite(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {"v": 1})
    store.save_aggregation("restoration-shaman", "3v3", "us", {"v": 2})
    assert store.get_aggregation("restoration-shaman", "3v3", "us")["v"] == 2


def test_is_stale_fresh(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {})
    assert not store.is_stale("restoration-shaman", "3v3", "us", ttl_hours=24)


def test_is_stale_missing(store):
    assert store.is_stale("arms-warrior", "3v3", "us", ttl_hours=24)
