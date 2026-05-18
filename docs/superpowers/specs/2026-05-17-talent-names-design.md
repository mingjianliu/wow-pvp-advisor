# Talent Name Resolution — Design Spec

**Date:** 2026-05-17
**Goal:** Replace raw node IDs in `get_full_summary_tool` output with human-readable talent names, while storing full node metadata for future HTML tree rendering.

---

## Problem

`get_full_summary_tool` currently returns talent data as raw numeric node IDs (e.g. `[81039, 81073]`). Claude has to interpret these without names. PvP talents already have names; only regular talents need lookup.

---

## Approach

Lazy name resolution with patch-version keyed cache invalidation:

1. `get_full_summary` fetches the aggregation (existing)
2. `TalentNameCache.resolve()` returns full node metadata from cache (new)
3. Cache is re-validated via conditional GET (`If-Modified-Since`) at most once per hour
4. If Blizzard returns 304 → serve from cache; if 200 → refresh cache
5. Names are applied to the aggregation dict before returning

---

## Architecture

```
wow_advisor/
  processor/
    talent_names.py        ← NEW: TalentNameCache
  api/
    client.py              ← add fetch_talent_tree_id() + fetch_talent_nodes()
  tools/
    summary.py             ← resolve IDs → names before returning
  cache/
    db.py                  ← add talent_node_cache table to schema
mcp_server.py              ← no changes
```

---

## SQLite Schema

New table added to `db.py`:

```sql
CREATE TABLE IF NOT EXISTS talent_node_cache (
    spec         TEXT PRIMARY KEY,
    nodes_json   TEXT NOT NULL,     -- {node_id: {name, row, col, type, max_rank, icon, children}}
    last_modified TEXT,             -- Blizzard Last-Modified header value
    checked_at   INTEGER NOT NULL   -- unix timestamp of last re-validation
)
```

Node metadata shape (stored per node in `nodes_json`):

```json
{
  "81039": {
    "name": "Lightning Bolt",
    "row": 1,
    "col": 3,
    "type": "single",
    "max_rank": 1,
    "icon": "spell_nature_lightning",
    "children": [81041, 81045]
  }
}
```

---

## TalentNameCache (`talent_names.py`)

```python
SPEC_IDS: dict[str, int] = {
    "restoration shaman": 264,
    "arms warrior": 71,
    # ... expand as needed
}

REVALIDATE_INTERVAL = 3600  # 1 hour

class TalentNameCache:
    def resolve(self, spec: str, client: BnetClient) -> dict[int, dict]:
        """
        Returns {node_id: node_metadata} for the given spec.
        Returns {} if spec is unknown or API is unavailable (caller falls back gracefully).
        """
        # 1. Load row from talent_node_cache
        # 2. If exists and checked_at < 1h ago → return cached nodes
        # 3. If exists but stale → conditional GET with If-Modified-Since
        #      304 → update checked_at, return cached nodes
        #      200 → refresh cache from response, return new nodes
        # 4. If no cache → full fetch (tree index + tree nodes), store, return
        # 5. On any error → return {} (graceful degradation)
```

---

## Blizzard API Additions (`client.py`)

```python
async def fetch_talent_tree_id(self, spec_id: int) -> tuple[int, str | None]:
    # GET /data/wow/talent-tree/index (static namespace)
    # Returns (tree_id, last_modified) for the given spec_id

async def fetch_talent_nodes(
    self,
    tree_id: int,
    spec_id: int,
    if_modified_since: str | None = None,
) -> tuple[dict[int, dict], str | None, bool]:
    # GET /data/wow/talent-tree/{tree_id}/playable-specialization/{spec_id}
    # Passes If-Modified-Since header when provided
    # Returns (nodes, last_modified, was_modified)
    # was_modified=False on 304 → caller skips cache write
    #
    # Extracts from response:
    #   class_talent_nodes + spec_talent_nodes arrays
    #   Per node: id, ranks[0].tooltip.talent.name, display_row, display_col,
    #             node_type.type, ranks length (max_rank),
    #             ranks[0].tooltip.spell_tooltip.spell.id (for icon lookup),
    #             child_ids
```

---

## get_full_summary Output Shape (revised)

Talent section changes from raw integer lists to `{id, name}` objects. Both are included so Claude can read names and future UI can use IDs for icon rendering and Wowhead links. Gear and enchants are unchanged (already name-based).

```python
# Before
"talents": {
    "core_nodes": [81039, 81073],
    "clusters": [{"takes": [81050], "skips": [81055], ...}]
}

# After
"talents": {
    "core": [{"id": 81039, "name": "Lightning Bolt"}, {"id": 81073, "name": "Chain Lightning"}],
    "flex": [{"id": 81100, "name": "Ancestral Swiftness"}],
    "contested": [{"id": 81050, "name": "Stormkeeper"}],
    "clusters": [
        {
            "rank": 1, "pct": 72,
            "takes": [{"id": 81050, "name": "Stormkeeper"}],
            "skips": [{"id": 81055, "name": "Tempest"}],
            "canonical_code": "..."
        }
    ]
}
```

Keys renamed: `core_nodes` → `core`, `flex_nodes` → `flex`, `contested_nodes` → `contested`.

If name resolution fails for a node, `name` is `null` (not a synthetic string), so callers can detect degraded output cleanly.

Full node metadata (position, connections, icon, type) is stored in `talent_node_cache` and available for future HTML tree rendering but is not surfaced in the MCP response (keeps it lean).

---

## Error Handling

| Scenario                 | Behaviour                                                   |
| ------------------------ | ----------------------------------------------------------- |
| Spec not in `SPEC_IDS`   | `resolve()` returns `{}`, node `name` fields are `null`     |
| Blizzard API unreachable | `resolve()` returns `{}`, graceful degradation              |
| Conditional GET throws   | Treat as 304, retry next revalidation interval              |
| 304 response             | Update `checked_at`, skip cache write                       |
| 200 response             | Rebuild `nodes_json`, update `last_modified` + `checked_at` |

---

## Testing

- `tests/test_talent_names.py` (new):
  - Mock `BnetClient`; verify 304 path skips cache write and updates `checked_at`
  - Verify 200 path refreshes `nodes_json` and `last_modified`
  - Verify unknown spec returns `{}`
  - Verify network error returns `{}` without raising
- `tests/test_summary.py` (update):
  - Assert `core` key contains `{id, name}` objects, not raw integers
  - Assert graceful fallback when `TalentNameCache.resolve()` returns `{}`
