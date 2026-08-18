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


def test_get_default_db_reuses_connection_within_thread(tmp_path, monkeypatch):
    import wow_advisor._paths as paths
    from wow_advisor.cache.db import get_default_db
    monkeypatch.setattr(paths, "get_db_path", lambda: tmp_path / "reuse.db")
    c1 = get_default_db()
    c2 = get_default_db()
    assert c1 is c2


def test_get_default_db_separate_connection_per_thread(tmp_path, monkeypatch):
    import threading
    import wow_advisor._paths as paths
    from wow_advisor.cache.db import get_default_db
    monkeypatch.setattr(paths, "get_db_path", lambda: tmp_path / "threads.db")
    main_conn = get_default_db()
    other = {}
    t = threading.Thread(target=lambda: other.setdefault("conn", get_default_db()))
    t.start()
    t.join()
    assert other["conn"] is not main_conn
    # Both connections see the same schema
    tables = {r[0] for r in other["conn"].execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert "players" in tables and "aggregations" in tables


# --- Game build stamping ----------------------------------------------------
#
# Blizzard reassigns talents across node IDs between client builds (12.1 swapped
# Battlelord and Master Tactician on Arms Warrior). An aggregation stores raw
# node IDs, so it is only interpretable against the build it was computed under.

def test_save_aggregation_records_game_build(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {"v": 1}, game_build="12.1.0_68914")
    assert store.aggregation_game_build("restoration-shaman", "3v3", "us") == "12.1.0_68914"


def test_aggregation_game_build_is_none_when_unstamped(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {"v": 1})
    assert store.aggregation_game_build("restoration-shaman", "3v3", "us") is None


def test_fresh_aggregation_is_stale_when_game_build_changed(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {}, game_build="12.0.5_67000")
    assert store.is_stale(
        "restoration-shaman", "3v3", "us", ttl_hours=24, game_build="12.1.0_68914"
    )


def test_fresh_aggregation_is_not_stale_when_game_build_matches(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {}, game_build="12.1.0_68914")
    assert not store.is_stale(
        "restoration-shaman", "3v3", "us", ttl_hours=24, game_build="12.1.0_68914"
    )


def test_unstamped_aggregation_is_stale_once_a_build_is_known(store):
    """Pre-existing rows carry no build, so they cannot be proven current."""
    store.save_aggregation("restoration-shaman", "3v3", "us", {})
    assert store.is_stale(
        "restoration-shaman", "3v3", "us", ttl_hours=24, game_build="12.1.0_68914"
    )


def test_game_build_unknown_falls_back_to_ttl_only(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {}, game_build="12.0.5_67000")
    assert not store.is_stale("restoration-shaman", "3v3", "us", ttl_hours=24, game_build=None)
