import os
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    realm TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'us',
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
    gear TEXT
);

CREATE TABLE IF NOT EXISTS aggregations (
    spec TEXT NOT NULL,
    bracket TEXT NOT NULL,
    region TEXT NOT NULL,
    computed_at INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (spec, bracket, region)
);
"""


def init_db(path: str) -> sqlite3.Connection:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def get_default_db() -> sqlite3.Connection:
    db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "wow_advisor.db")
    )
    return init_db(db_path)
