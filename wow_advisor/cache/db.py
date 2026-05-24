import os
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    realm TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'us',
    locale TEXT NOT NULL DEFAULT 'en_US',
    character_class TEXT,
    spec TEXT,
    bracket TEXT,
    rating INTEGER,
    equipped_ilvl INTEGER,
    fetched_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS player_loadouts (
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    talent_code TEXT,
    class_node_ids TEXT,
    spec_node_ids TEXT,
    hero_node_ids TEXT,
    node_ranks TEXT,
    pvp_talent_ids TEXT,
    pvp_talent_names TEXT,
    gear TEXT
);

CREATE TABLE IF NOT EXISTS aggregations (
    spec TEXT NOT NULL,
    bracket TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'us',
    locale TEXT NOT NULL DEFAULT 'en_US',
    computed_at INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (spec, bracket, region, locale)
);

CREATE TABLE IF NOT EXISTS talent_node_cache (
    spec          TEXT NOT NULL,
    locale        TEXT NOT NULL DEFAULT 'en_US',
    nodes_json    TEXT NOT NULL,
    last_modified TEXT,
    checked_at    INTEGER NOT NULL,
    PRIMARY KEY (spec, locale)
);

CREATE INDEX IF NOT EXISTS idx_players_spec_bracket_region ON players(spec, bracket, region);
CREATE INDEX IF NOT EXISTS idx_loadouts_player_id ON player_loadouts(player_id);
"""


def init_db(path: str) -> sqlite3.Connection:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def get_default_db() -> sqlite3.Connection:
    from wow_advisor._paths import get_db_path
    return init_db(str(get_db_path()))
