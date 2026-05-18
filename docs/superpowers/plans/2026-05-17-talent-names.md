# Talent Name Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace raw node IDs in `get_full_summary_tool` output with `{id, name}` objects resolved from Blizzard's static talent-tree API, with patch-version keyed caching.

**Architecture:** `TalentNameCache` stores full node metadata (name, position, connections, icon) per spec in a new SQLite table, re-validated at most once per hour via conditional GET. `get_full_summary` calls `TalentNameCache.resolve()` after fetching the aggregation and enriches the talent section before returning.

**Tech Stack:** Python 3.12, httpx, sqlite3 stdlib, pytest, unittest.mock

---

## File Map

| File                                    | Change                                                          |
| --------------------------------------- | --------------------------------------------------------------- |
| `wow_advisor/cache/db.py`               | Add `talent_node_cache` table to `_SCHEMA`                      |
| `wow_advisor/api/client.py`             | Add `_get_static`, `fetch_talent_tree_id`, `fetch_talent_nodes` |
| `wow_advisor/processor/talent_names.py` | **NEW** — `SPEC_IDS`, `TalentNameCache`                         |
| `wow_advisor/tools/summary.py`          | Add `_enrich_talents`, call `TalentNameCache.resolve()`         |
| `tests/test_talent_names.py`            | **NEW** — all `TalentNameCache` tests                           |
| `tests/test_summary.py`                 | **NEW** — `_enrich_talents` unit tests                          |

---

## Task 1: Add talent_node_cache table

**Files:**

- Modify: `wow_advisor/cache/db.py`

- [ ] **Step 1: Add the table to `_SCHEMA`**

Open `wow_advisor/cache/db.py`. The `_SCHEMA` string ends after the two `CREATE INDEX` statements. Append this table definition inside the string, before the closing `"""`:

```python
_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    ...existing tables unchanged...
);

CREATE TABLE IF NOT EXISTS talent_node_cache (
    spec          TEXT PRIMARY KEY,
    nodes_json    TEXT NOT NULL,
    last_modified TEXT,
    checked_at    INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_players_spec_bracket_region ON players(spec, bracket, region);
CREATE INDEX IF NOT EXISTS idx_loadouts_player_id ON player_loadouts(player_id);
"""
```

The full updated `_SCHEMA` value (replace the existing string entirely):

```python
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
    pvp_talent_ids TEXT,
    pvp_talent_names TEXT,
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

CREATE TABLE IF NOT EXISTS talent_node_cache (
    spec          TEXT PRIMARY KEY,
    nodes_json    TEXT NOT NULL,
    last_modified TEXT,
    checked_at    INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_players_spec_bracket_region ON players(spec, bracket, region);
CREATE INDEX IF NOT EXISTS idx_loadouts_player_id ON player_loadouts(player_id);
"""
```

- [ ] **Step 2: Verify the table is created**

```bash
python -c "
from wow_advisor.cache.db import init_db
conn = init_db(':memory:')
row = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='talent_node_cache'\").fetchone()
print('OK' if row else 'MISSING')
"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add wow_advisor/cache/db.py
git commit -m "feat: add talent_node_cache table to schema"
```

---

## Task 2: Add static API methods to BnetClient

**Files:**

- Modify: `wow_advisor/api/client.py`

The existing `_get(self, client, url, namespace)` doesn't support custom headers or 304 responses. Add a new `_get_static` method and two callers for it.

- [ ] **Step 1: Add `_get_static` to `BnetClient`**

Add this method after the existing `_get` method (after line 96 of the current file):

```python
async def _get_static(
    self, url: str, namespace: str, if_modified_since: str | None = None
) -> httpx.Response:
    """GET for static game data. Returns the raw Response (caller handles 304)."""
    token = await self._auth.get_token()
    headers = _headers(token, namespace)
    if if_modified_since:
        headers["If-Modified-Since"] = if_modified_since
    async with httpx.AsyncClient() as client:
        return await client.get(
            url,
            headers=headers,
            params={"locale": "en_US"},
            timeout=10.0,
        )
```

- [ ] **Step 2: Add `fetch_talent_tree_id`**

Add after `_get_static`:

```python
async def fetch_talent_tree_id(self, spec_id: int) -> tuple[int, str | None]:
    """Returns (tree_id, last_modified) for the given spec_id."""
    url = f"{self._base}/data/wow/talent-tree/index"
    resp = await self._get_static(url, f"static-{self._region}")
    resp.raise_for_status()
    last_modified = resp.headers.get("Last-Modified")
    for entry in resp.json().get("spec_talent_trees", []):
        href = entry.get("key", {}).get("href", "")
        m = re.search(r"/talent-tree/(\d+)/playable-specialization/(\d+)", href)
        if m and int(m.group(2)) == spec_id:
            return int(m.group(1)), last_modified
    raise ValueError(f"spec_id {spec_id} not found in talent-tree index")
```

Note: `re` is already imported at the top of `client.py`.

- [ ] **Step 3: Add `fetch_talent_nodes`**

Add after `fetch_talent_tree_id`:

```python
async def fetch_talent_nodes(
    self,
    tree_id: int,
    spec_id: int,
    if_modified_since: str | None = None,
) -> tuple[dict[int, dict], str | None, bool]:
    """
    Returns (nodes, last_modified, was_modified).
    was_modified=False on 304 — caller skips cache write.
    nodes maps node_id → {name, row, col, type, max_rank, icon, children}.
    """
    url = f"{self._base}/data/wow/talent-tree/{tree_id}/playable-specialization/{spec_id}"
    resp = await self._get_static(url, f"static-{self._region}", if_modified_since=if_modified_since)
    if resp.status_code == 304:
        return {}, None, False
    resp.raise_for_status()
    last_modified = resp.headers.get("Last-Modified")
    data = resp.json()
    nodes: dict[int, dict] = {}
    for node in data.get("class_talent_nodes", []) + data.get("spec_talent_nodes", []):
        node_id = node["id"]
        ranks = node.get("ranks", [])
        name = None
        icon = None
        if ranks:
            tooltip = ranks[0].get("tooltip", {})
            name = tooltip.get("talent", {}).get("name")
            spell = tooltip.get("spell_tooltip", {}).get("spell", {})
            icon = str(spell["id"]) if spell.get("id") else None
        nodes[node_id] = {
            "name": name,
            "row": node.get("display_row"),
            "col": node.get("display_col"),
            "type": node.get("node_type", {}).get("type"),
            "max_rank": len(ranks),
            "icon": icon,
            "children": node.get("child_ids", []),
        }
    return nodes, last_modified, True
```

- [ ] **Step 4: Run existing client tests to confirm no regressions**

```bash
pytest tests/test_client.py -v
```

Expected: all existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add wow_advisor/api/client.py
git commit -m "feat: add static API methods for talent tree name lookup"
```

---

## Task 3: Create TalentNameCache

**Files:**

- Create: `wow_advisor/processor/talent_names.py`
- Create: `tests/test_talent_names.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_talent_names.py`:

```python
import json
import time
from unittest.mock import AsyncMock

import pytest

from wow_advisor.cache.db import init_db
from wow_advisor.processor.talent_names import TalentNameCache


SAMPLE_NODES = {
    100: {"name": "Lightning Bolt", "row": 1, "col": 3, "type": "single",
          "max_rank": 1, "icon": "123", "children": []},
    101: {"name": "Chain Lightning", "row": 2, "col": 3, "type": "single",
          "max_rank": 1, "icon": "124", "children": []},
}
LAST_MODIFIED = "Mon, 01 Jan 2026 00:00:00 GMT"


@pytest.fixture
def db(tmp_db):
    return init_db(tmp_db)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.fetch_talent_tree_id = AsyncMock(return_value=(786, LAST_MODIFIED))
    client.fetch_talent_nodes = AsyncMock(return_value=(SAMPLE_NODES, LAST_MODIFIED, True))
    return client


def test_fresh_fetch_returns_nodes(db, mock_client):
    result = TalentNameCache(db).resolve("restoration shaman", mock_client)
    assert result[100]["name"] == "Lightning Bolt"
    assert result[101]["name"] == "Chain Lightning"


def test_fresh_fetch_persists_to_db(db, mock_client):
    TalentNameCache(db).resolve("restoration shaman", mock_client)
    row = db.execute(
        "SELECT nodes_json FROM talent_node_cache WHERE spec=?", ("restoration shaman",)
    ).fetchone()
    assert row is not None
    assert "100" in json.loads(row["nodes_json"])


def test_cache_hit_within_1h_makes_no_api_calls(db, mock_client):
    cache = TalentNameCache(db)
    cache.resolve("restoration shaman", mock_client)
    mock_client.reset_mock()
    cache.resolve("restoration shaman", mock_client)
    mock_client.fetch_talent_tree_id.assert_not_called()
    mock_client.fetch_talent_nodes.assert_not_called()


def test_stale_cache_304_updates_checked_at_only(db, mock_client):
    cache = TalentNameCache(db)
    cache.resolve("restoration shaman", mock_client)
    old_time = int(time.time()) - 7200
    db.execute(
        "UPDATE talent_node_cache SET checked_at=? WHERE spec=?", (old_time, "restoration shaman")
    )
    db.commit()
    mock_client.reset_mock()
    mock_client.fetch_talent_nodes = AsyncMock(return_value=({}, None, False))
    result = cache.resolve("restoration shaman", mock_client)
    assert result[100]["name"] == "Lightning Bolt"
    row = db.execute(
        "SELECT nodes_json, checked_at FROM talent_node_cache WHERE spec=?", ("restoration shaman",)
    ).fetchone()
    assert row["checked_at"] > old_time
    assert "100" in json.loads(row["nodes_json"])


def test_stale_cache_200_refreshes_nodes(db, mock_client):
    cache = TalentNameCache(db)
    cache.resolve("restoration shaman", mock_client)
    old_time = int(time.time()) - 7200
    db.execute(
        "UPDATE talent_node_cache SET checked_at=? WHERE spec=?", (old_time, "restoration shaman")
    )
    db.commit()
    mock_client.reset_mock()
    new_nodes = {
        200: {"name": "New Talent", "row": 1, "col": 1, "type": "single",
              "max_rank": 1, "icon": None, "children": []}
    }
    mock_client.fetch_talent_nodes = AsyncMock(
        return_value=(new_nodes, "Mon, 02 Feb 2026 00:00:00 GMT", True)
    )
    result = cache.resolve("restoration shaman", mock_client)
    assert 200 in result
    assert 100 not in result


def test_unknown_spec_returns_empty(db, mock_client):
    result = TalentNameCache(db).resolve("nonexistent spec xyzzy", mock_client)
    assert result == {}
    mock_client.fetch_talent_tree_id.assert_not_called()


def test_api_error_returns_empty(db, mock_client):
    mock_client.fetch_talent_tree_id = AsyncMock(side_effect=RuntimeError("API down"))
    result = TalentNameCache(db).resolve("restoration shaman", mock_client)
    assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_talent_names.py -v
```

Expected: `ModuleNotFoundError: No module named 'wow_advisor.processor.talent_names'`

- [ ] **Step 3: Create `wow_advisor/processor/talent_names.py`**

```python
import asyncio
import json
import sqlite3
import time

from wow_advisor.api.client import BnetClient

SPEC_IDS: dict[str, int] = {
    "restoration shaman": 264,
    "elemental shaman": 262,
    "enhancement shaman": 263,
    "arms warrior": 71,
    "fury warrior": 72,
    "protection warrior": 73,
    "assassination rogue": 259,
    "outlaw rogue": 260,
    "subtlety rogue": 261,
    "arcane mage": 62,
    "fire mage": 63,
    "frost mage": 64,
    "balance druid": 102,
    "feral druid": 103,
    "guardian druid": 104,
    "restoration druid": 105,
    "holy paladin": 65,
    "protection paladin": 66,
    "retribution paladin": 70,
    "discipline priest": 256,
    "holy priest": 257,
    "shadow priest": 258,
    "beast mastery hunter": 253,
    "marksmanship hunter": 254,
    "survival hunter": 255,
    "affliction warlock": 265,
    "demonology warlock": 266,
    "destruction warlock": 267,
    "frost death knight": 251,
    "unholy death knight": 252,
    "blood death knight": 250,
    "windwalker monk": 269,
    "brewmaster monk": 268,
    "mistweaver monk": 270,
    "havoc demon hunter": 577,
    "vengeance demon hunter": 581,
    "devastation evoker": 1467,
    "preservation evoker": 1468,
    "augmentation evoker": 1473,
}

REVALIDATE_INTERVAL = 3600  # 1 hour


class TalentNameCache:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def resolve(self, spec: str, client: BnetClient) -> dict[int, dict]:
        """
        Returns {node_id: node_metadata} for the given spec.
        Returns {} if spec is unknown or Blizzard API is unavailable.
        """
        spec_id = SPEC_IDS.get(spec)
        if spec_id is None:
            return {}
        try:
            return asyncio.run(self._resolve_async(spec, spec_id, client))
        except Exception:
            return {}

    async def _resolve_async(
        self, spec: str, spec_id: int, client: BnetClient
    ) -> dict[int, dict]:
        row = self._conn.execute(
            "SELECT nodes_json, last_modified, checked_at FROM talent_node_cache WHERE spec=?",
            (spec,),
        ).fetchone()
        now = int(time.time())

        if row and now - row["checked_at"] < REVALIDATE_INTERVAL:
            return {int(k): v for k, v in json.loads(row["nodes_json"]).items()}

        if row:
            nodes, last_modified, was_modified = await self._fetch(
                spec_id, client, if_modified_since=row["last_modified"]
            )
            if not was_modified:
                self._conn.execute(
                    "UPDATE talent_node_cache SET checked_at=? WHERE spec=?", (now, spec)
                )
                self._conn.commit()
                return {int(k): v for k, v in json.loads(row["nodes_json"]).items()}
            self._save(spec, nodes, last_modified, now)
            return nodes

        nodes, last_modified, _ = await self._fetch(spec_id, client)
        self._save(spec, nodes, last_modified, now)
        return nodes

    async def _fetch(
        self,
        spec_id: int,
        client: BnetClient,
        if_modified_since: str | None = None,
    ) -> tuple[dict[int, dict], str | None, bool]:
        tree_id, _ = await client.fetch_talent_tree_id(spec_id)
        return await client.fetch_talent_nodes(tree_id, spec_id, if_modified_since=if_modified_since)

    def _save(
        self, spec: str, nodes: dict[int, dict], last_modified: str | None, now: int
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO talent_node_cache (spec, nodes_json, last_modified, checked_at)
               VALUES (?, ?, ?, ?)""",
            (spec, json.dumps({str(k): v for k, v in nodes.items()}), last_modified, now),
        )
        self._conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_talent_names.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wow_advisor/processor/talent_names.py tests/test_talent_names.py
git commit -m "feat: TalentNameCache with patch-version keyed invalidation"
```

---

## Task 4: Enrich get_full_summary output

**Files:**

- Modify: `wow_advisor/tools/summary.py`
- Create: `tests/test_summary.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_summary.py`:

```python
import pytest
from wow_advisor.tools.summary import _enrich_talents


NODE_MAP = {
    100: {"name": "Lightning Bolt", "row": 1, "col": 3, "type": "single",
          "max_rank": 1, "icon": "123", "children": []},
    101: {"name": "Chain Lightning", "row": 2, "col": 3, "type": "single",
          "max_rank": 1, "icon": "124", "children": []},
    200: {"name": "Stormkeeper", "row": 3, "col": 2, "type": "single",
          "max_rank": 1, "icon": "125", "children": []},
    201: {"name": "Tempest", "row": 3, "col": 4, "type": "single",
          "max_rank": 1, "icon": "126", "children": []},
}

RAW_TALENTS = {
    "core_nodes": [100, 101],
    "flex_nodes": [],
    "contested_nodes": [200],
    "clusters": [
        {"rank": 1, "pct": 72.0, "canonical_code": "abc", "takes": [200], "skips": [201]},
        {"rank": 2, "pct": 28.0, "canonical_code": "def", "takes": [201], "skips": [200]},
    ],
    "clustering_method": "variance+hamming",
}


def test_enrich_renames_keys():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert "core" in result
    assert "flex" in result
    assert "contested" in result
    assert "core_nodes" not in result
    assert "flex_nodes" not in result
    assert "contested_nodes" not in result


def test_enrich_core_contains_id_and_name():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert result["core"] == [
        {"id": 100, "name": "Lightning Bolt"},
        {"id": 101, "name": "Chain Lightning"},
    ]


def test_enrich_cluster_takes_and_skips():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    cluster = result["clusters"][0]
    assert cluster["takes"] == [{"id": 200, "name": "Stormkeeper"}]
    assert cluster["skips"] == [{"id": 201, "name": "Tempest"}]


def test_enrich_preserves_non_talent_cluster_fields():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    cluster = result["clusters"][0]
    assert cluster["rank"] == 1
    assert cluster["pct"] == 72.0
    assert cluster["canonical_code"] == "abc"


def test_enrich_preserves_clustering_method():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert result["clustering_method"] == "variance+hamming"


def test_enrich_null_name_when_node_not_in_map():
    result = _enrich_talents(RAW_TALENTS, {})
    assert result["core"][0] == {"id": 100, "name": None}
    assert result["clusters"][0]["takes"][0] == {"id": 200, "name": None}


def test_enrich_empty_flex():
    result = _enrich_talents(RAW_TALENTS, NODE_MAP)
    assert result["flex"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_summary.py -v
```

Expected: `ImportError: cannot import name '_enrich_talents' from 'wow_advisor.tools.summary'`

- [ ] **Step 3: Add `_enrich_talents` to `summary.py`**

Add this function to `wow_advisor/tools/summary.py` (before `get_full_summary`):

```python
def _enrich_talents(talents: dict, node_map: dict[int, dict]) -> dict:
    def enrich(ids: list[int]) -> list[dict]:
        return [{"id": nid, "name": (node_map.get(nid) or {}).get("name")} for nid in ids]

    return {
        "core": enrich(talents.get("core_nodes", [])),
        "flex": enrich(talents.get("flex_nodes", [])),
        "contested": enrich(talents.get("contested_nodes", [])),
        "clusters": [
            {**c, "takes": enrich(c.get("takes", [])), "skips": enrich(c.get("skips", []))}
            for c in talents.get("clusters", [])
        ],
        "clustering_method": talents.get("clustering_method"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_summary.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Wire `_enrich_talents` into `get_full_summary`**

Replace the current `get_full_summary` function in `wow_advisor/tools/summary.py` with:

```python
def get_full_summary(spec: str, bracket: str, region: str = "us") -> dict:
    """Single-call summary: auto-fetches if stale, returns gear + named talents + PvP talents."""
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)
    conn = get_default_db()
    store = CacheStore(conn)

    if store.is_stale(spec, bracket, region, ttl_hours=2):
        result = fetch_top_players(spec=spec, bracket=bracket, region=region)
        if "error" in result:
            return result

    agg = store.get_aggregation(spec, bracket, region)
    if agg is None:
        return {"error": f"No data for {spec} in {bracket}. Fetch failed."}

    node_map: dict[int, dict] = {}
    try:
        from wow_advisor.processor.talent_names import TalentNameCache
        from wow_advisor.tools.fetch import _make_client
        _, client = _make_client(region)
        node_map = TalentNameCache(conn).resolve(spec, client)
    except Exception:
        pass

    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": agg.get("sample_size", 0),
        "avg_ilvl": agg.get("avg_ilvl", 0),
        "cached_at": agg.get("cached_at"),
        "pvp_talents": agg.get("pvp_talents", []),
        "talents": _enrich_talents(agg.get("talents", {}), node_map),
        "gear": agg.get("gear", {}),
        "enchants": agg.get("enchants", {}),
    }
```

Also add `dict` to the imports at the top of `summary.py` if not already present (it's a builtin, no import needed).

- [ ] **Step 6: Run the full test suite**

```bash
pytest -v
```

Expected: all existing tests pass plus the new summary and talent_names tests.

- [ ] **Step 7: Commit**

```bash
git add wow_advisor/tools/summary.py tests/test_summary.py
git commit -m "feat: enrich get_full_summary talents with node names"
```

---

## Self-Review

**Spec coverage:**

- [x] Lazy name resolution with patch-version keyed cache → Task 3 (`TalentNameCache._resolve_async`)
- [x] Conditional GET with `If-Modified-Since` → Task 2 (`fetch_talent_nodes`) + Task 3 (stale path)
- [x] Re-validate at most once per hour → Task 3 (`REVALIDATE_INTERVAL`)
- [x] 304 → update `checked_at` only, skip cache write → Task 3 (`test_stale_cache_304_updates_checked_at_only`)
- [x] 200 → refresh full cache → Task 3 (`test_stale_cache_200_refreshes_nodes`)
- [x] `talent_node_cache` SQLite table with full node metadata → Task 1
- [x] `{id, name}` output shape → Task 4 (`_enrich_talents`)
- [x] Keys renamed `core_nodes` → `core` etc. → Task 4
- [x] `name: null` on resolution failure → Task 4 (`test_enrich_null_name_when_node_not_in_map`)
- [x] Full node metadata stored (row, col, type, max_rank, icon, children) → Task 2 (`fetch_talent_nodes`) + Task 3 (`_save`)
- [x] Unknown spec returns `{}` → Task 3 (`test_unknown_spec_returns_empty`)
- [x] API error returns `{}` → Task 3 (`test_api_error_returns_empty`)
- [x] `get_full_summary` graceful degradation when name cache fails → Task 4 (outer try/except)
- [x] `mcp_server.py` unchanged → no task needed

**Placeholder scan:** No TBDs, no "similar to Task N", all test code is complete.

**Type consistency:** `node_map: dict[int, dict]` used consistently across Task 3 and Task 4. `_enrich_talents(talents: dict, node_map: dict[int, dict])` matches usage in `get_full_summary`. `TalentNameCache(conn).resolve(spec, client)` matches the class definition.
