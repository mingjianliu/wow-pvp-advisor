"""Schema migrations for databases created before a column existed.

The real data/wow_advisor.db predates game_build tracking; CREATE TABLE IF NOT
EXISTS never adds columns to an existing table, so an explicit migration runs.
"""
import sqlite3

from wow_advisor.cache.db import init_db

_PRE_BUILD_SCHEMA = """
CREATE TABLE talent_node_cache (
    spec          TEXT NOT NULL,
    locale        TEXT NOT NULL DEFAULT 'en_US',
    nodes_json    TEXT NOT NULL,
    last_modified TEXT,
    checked_at    INTEGER NOT NULL,
    PRIMARY KEY (spec, locale)
);

CREATE TABLE aggregations (
    spec TEXT NOT NULL,
    bracket TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'us',
    locale TEXT NOT NULL DEFAULT 'en_US',
    computed_at INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (spec, bracket, region, locale)
);
"""


def _columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_init_db_adds_game_build_to_legacy_talent_node_cache(tmp_db):
    legacy = sqlite3.connect(tmp_db)
    legacy.executescript(_PRE_BUILD_SCHEMA)
    legacy.commit()
    legacy.close()

    conn = init_db(tmp_db)

    assert "game_build" in _columns(conn, "talent_node_cache")


def test_init_db_adds_game_build_to_legacy_aggregations(tmp_db):
    legacy = sqlite3.connect(tmp_db)
    legacy.executescript(_PRE_BUILD_SCHEMA)
    legacy.commit()
    legacy.close()

    conn = init_db(tmp_db)

    assert "game_build" in _columns(conn, "aggregations")


def test_migration_preserves_existing_rows(tmp_db):
    legacy = sqlite3.connect(tmp_db)
    legacy.executescript(_PRE_BUILD_SCHEMA)
    legacy.execute(
        "INSERT INTO talent_node_cache (spec, locale, nodes_json, last_modified, checked_at)"
        " VALUES ('arms-warrior', 'en_US', '{\"1\": {}}', 'Sun, 24 May 2026 17:06:36 GMT', 1779655030)"
    )
    legacy.commit()
    legacy.close()

    conn = init_db(tmp_db)

    row = conn.execute(
        "SELECT nodes_json, game_build FROM talent_node_cache WHERE spec='arms-warrior'"
    ).fetchone()
    assert row["nodes_json"] == '{"1": {}}'
    assert row["game_build"] is None


def test_init_db_is_idempotent(tmp_db):
    init_db(tmp_db).close()
    conn = init_db(tmp_db)

    assert "game_build" in _columns(conn, "talent_node_cache")
