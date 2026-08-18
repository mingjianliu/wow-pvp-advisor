import os
import sqlite3
import threading

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
    game_build TEXT,
    PRIMARY KEY (spec, bracket, region, locale)
);

CREATE TABLE IF NOT EXISTS talent_node_cache (
    spec          TEXT NOT NULL,
    locale        TEXT NOT NULL DEFAULT 'en_US',
    nodes_json    TEXT NOT NULL,
    last_modified TEXT,
    checked_at    INTEGER NOT NULL,
    game_build    TEXT,
    PRIMARY KEY (spec, locale)
);

CREATE TABLE IF NOT EXISTS pvp_talent_pool (
    spec         TEXT NOT NULL,
    locale       TEXT NOT NULL DEFAULT 'en_US',
    talents_json TEXT NOT NULL,
    game_build   TEXT,
    fetched_at   INTEGER NOT NULL,
    PRIMARY KEY (spec, locale)
);

CREATE TABLE IF NOT EXISTS tooltips (
    type       TEXT NOT NULL,
    id         INTEGER NOT NULL,
    locale_id  INTEGER NOT NULL,
    data_json  TEXT NOT NULL,
    fetched_at INTEGER NOT NULL,
    PRIMARY KEY (type, id, locale_id)
);

CREATE INDEX IF NOT EXISTS idx_players_spec_bracket_region ON players(spec, bracket, region);
CREATE INDEX IF NOT EXISTS idx_loadouts_player_id ON player_loadouts(player_id);
"""


# CREATE TABLE IF NOT EXISTS never alters an existing table, so columns added
# after a database was first created need an explicit ALTER. Each entry is
# (table, column, ddl) and is applied only when the column is absent.
_MIGRATIONS = [
    ("talent_node_cache", "game_build", "ALTER TABLE talent_node_cache ADD COLUMN game_build TEXT"),
    ("aggregations", "game_build", "ALTER TABLE aggregations ADD COLUMN game_build TEXT"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    for table, column, ddl in _MIGRATIONS:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if cols and column not in cols:
            conn.execute(ddl)
    conn.commit()


def _connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> sqlite3.Connection:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = _connect(path)
    conn.executescript(_SCHEMA)
    conn.commit()
    _migrate(conn)
    return conn


# Default-DB connections are reused: one per thread per path (sqlite3
# connections are not safe to share across threads without locking), with
# the schema initialized only once per path per process.
_local = threading.local()
_initialized_paths: set[str] = set()
_init_lock = threading.Lock()


def get_default_db() -> sqlite3.Connection:
    from wow_advisor._paths import get_db_path
    path = str(get_db_path())

    conns: dict[str, sqlite3.Connection] = getattr(_local, "conns", None)
    if conns is None:
        conns = _local.conns = {}
    conn = conns.get(path)
    if conn is None:
        with _init_lock:
            if path in _initialized_paths:
                conn = _connect(path)
            else:
                conn = init_db(path)
                _initialized_paths.add(path)
        conns[path] = conn
    return conn
