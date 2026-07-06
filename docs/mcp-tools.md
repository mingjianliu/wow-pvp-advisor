# MCP Tools Design Notes

The **canonical reference for each tool's purpose and parameters is its docstring in `mcp_server.py`** — that's what MCP clients see, so it's kept accurate. This file only covers what doesn't fit in a docstring: output schemas, internal mechanics, known limitations, and future work.

All tools accept spec aliases (`"rsham"`, `"resto shaman"`, `"restoration-shaman"`) and bracket aliases (`"3v3"`, `"2v2"`, `"solo shuffle"`, `"shuffle"`) via `normalize.py`.

**Cache TTLs:** `get_full_summary_tool` and `build_page_tool` auto-refresh when the aggregation is older than **2 hours**; `get_talent_distribution_tool` and `get_gear_summary_tool` use **24 hours**.

---

## 1. `fetch_top_players_tool`

### Mechanics (two phases)

**Phase 1 — Spec scan (cheap):** Fetches the full PvP leaderboard (1 API call, ~5000 entries for 3v3). Walks the ladder in batches of 50, fetching each player's character profile (1 API call each) to check their class and spec. Stops as soon as `limit` matching players are found.

**Phase 2 — Detail fetch:** For the matched players only, fetches specializations (talent loadout) and equipment (gear + enchants) concurrently — 2 API calls per player, all fired in parallel.

**Cache guard:** If an aggregation for this spec+bracket+region was computed within the last 2 hours, skips all API calls and returns immediately with `"skipped": true`.

### Output (success)

```json
{
  "fetched": 50,
  "cached_at": 1779046010,
  "spec": "restoration-shaman",
  "bracket": "3v3",
  "skipped": false
}
```

Error cases return `{"error": "..."}`: unknown spec, no leaderboard data for the bracket, or zero matching players on the ladder.

### Side effects

- Writes player rows to `players` and `player_loadouts` tables (replaces previous data for this spec+bracket+region)
- Writes one aggregation row to `aggregations` table

### Known limitations

- **Fetched count < limit**: rare specs may not have `limit` players on the full ladder. The tool returns however many it found.
- **Stale player data**: if a top player transfers realms or changes spec between fetches, Phase 1 will miss them. No fix without a per-player cache (see BACKLOG).
- **Season ID hardcoded** (`CURRENT_SEASON_ID = 41` in `client.py`). Will silently fetch wrong data when Season 42 starts.

### Future work

- Auto-detect current season from Blizzard API on startup
- Per-player cache: skip Phase 2 for players whose detail data is still fresh
- Expose `scan_limit` parameter (currently scans full ladder)

---

## 2. `get_talent_distribution_tool`

Returns the `talents` section of the cached aggregation (raw node IDs, no names).

### Output

```json
{
  "spec": "restoration-shaman",
  "bracket": "3v3",
  "region": "us",
  "sample_size": 50,
  "cached_at": 1779046010,
  "talents": {
    "core_nodes": [{"id": 81018, "pickers": [...]}, ...],
    "flex_nodes": [{"id": 81019, "pickers": [...]}, ...],
    "contested_nodes": [{"id": 81039, "pickers": [...]}, ...],
    "clusters": [
      {
        "rank": 1,
        "count": 22,
        "pct": 44.0,
        "canonical_code": "BAQAAAAAAAAAAAAkU...",
        "takes": [{"id": 81039, "rank": 1, "pickers": [...]}, ...],
        "flex_takes": [{"id": 103427, "pct": 20.0, "pickers": [...]}, ...],
        "skips": [{"id": 81038, "pickers": [...]}, ...],
        "silhouette_score": 0.345
      }
    ],
    "clustering_method": "variance+weighted",
    "mean_silhouette_score": 0.285
  }
}
```

**Node classifications:**

- `core_nodes` — picked by ≥80% of players.
- `flex_nodes` — picked by ≤20% of players.
- `contested_nodes` — picked by 20–80% of players.

**Clusters:** Builds are grouped using **Agglomerative Hierarchical Clustering (HAC)** with Complete Linkage and Weighted Jaccard Distance scaled dynamically by pick-rate variance.

- `takes` — talent choices from this cluster's medoid (representative) build.
- `flex_takes` — internal cluster variance (talents taken by some but not all members of the cluster).
- `skips` — talents NOT taken by this cluster's medoid build.
- `silhouette_score` — cohesion metric for this cluster (higher is better, range -1 to 1).

**`clustering_method`:** `"variance+weighted"` (default HAC) or `"keystone"` (if forced by `data/keystone_talents.json`).

**`mean_silhouette_score`:** overall clustering quality score.

### Known limitations

- **Fragmented clusters**: if build diversity is extremely high, clusters can still be small.
- **Node IDs only**: use `get_full_summary_tool` for a version with human-readable names.

### Future work

- Add more `data/keystone_talents.json` entries to force cleaner clusters
- Expose clustering threshold as a parameter

---

## 3. `get_gear_summary_tool`

Returns the `gear` and `enchants` sections of the cached aggregation.

### Output

```json
{
  "spec": "restoration-shaman",
  "bracket": "3v3",
  "region": "us",
  "sample_size": 50,
  "avg_ilvl": 247,
  "cached_at": 1779046010,
  "gear": {
    "head": [
      { "item_id": 237637, "name": "Locus of the Primal Core", "count": 46, "pct": 92.0 }
    ],
    "trinket_1": [...],
    "trinket_2": [...]
  },
  "enchants": {
    "finger_1": [
      { "enchant_id": 7459, "name": "Enchant Ring - Zul'jin's Mastery", "count": 36, "pct": 72.0 }
    ],
    "main_hand": [...]
  }
}
```

Items within each slot are sorted by pick rate descending. Slots with no players wearing an item are omitted.

### Known limitations

- **Enchant prefix**: enchant names still start with `"Enchanted: "` — cosmetic issue, doesn't affect usability.
- **No gem data**: Blizzard's equipment endpoint returns gem sockets but we don't currently parse or aggregate them.
- **No stat breakdown**: we don't aggregate secondary stats (haste, mastery, crit, vers) from individual items. Murlok.io does this; we don't yet.
- **Trinket slots**: slot names are `"trinket_1"` and `"trinket_2"` from the Blizzard API. A player may have the same trinket in both slots; currently counted separately.

### Future work

- Parse gem sockets and aggregate gem choices per slot
- Aggregate secondary stat distribution across top players
- Strip `"Enchanted: "` prefix from enchant names (BACKLOG)
- Surface trinkets in a combined view (both slots together, deduped)

---

## 4. `get_full_summary_tool`

On top of the cached aggregation, resolves all numeric talent node IDs into names (e.g., `81018` → `"Riptide"`) via the Blizzard static API and enriches the output with pick rates and rank distributions.

### Output

```json
{
  "spec": "restoration-shaman",
  "bracket": "3v3",
  "talents": {
    "core": [{"id": 81018, "name": "Riptide", "pct": 100.0}, ...],
    "flex": [...],
    "contested": [...],
    "clusters": [
      {
        "rank": 1,
        "pct": 44.0,
        "takes": [{"id": 81039, "name": "Healing Stream Totem", "pts": 2, "pct": 98.0}, ...]
      }
    ]
  },
  "gear": { ... },
  "pvp_talents": [{"id": 210, "name": "Grounding Totem", "pct": 85.0}, ...]
}
```

### Known limitations

- **Resolution overhead**: the first time a spec is resolved, it may take 1-2 seconds to fetch name data from Blizzard. Subsequent calls are cached in the `talent_names` table.

---

## 5. `get_tree_structure_tool`

Parses the Blizzard talent tree definition into "Class", "Spec", and "Hero" trees. For Hero trees, it identifies the two sub-trees available to the spec (e.g., Totemic vs Farseer for Restoration Shaman) via `spec_data.hero_talent_trees`.

### Output

```json
{
  "spec": "restoration-shaman",
  "trees": [
    {
      "name": "Shaman",
      "nodes": [{"id": 81018, "pos": {"x": 3000, "y": 400}, "type": "circle", "name": "Riptide", "spellId": 61295}, ...]
    },
    { "name": "Restoration", "nodes": [...] }
  ],
  "heroTrees": {
    "left": { "name": "Totemic", "nodes": [...] },
    "right": { "name": "Farseer", "nodes": [...] }
  }
}
```

---

## 6. `build_page_tool`

Pipeline: calls `get_full_summary` + `get_tree_structure`, bundles the data with the React frontend template, inlines all CSS/JS into a single standalone `.html`, writes it to `frontend/pages/{spec}_{bracket}.html`, and returns the local URL.

### Output

```json
{
  "path": "/.../frontend/pages/restoration-shaman_3v3.html",
  "url": "http://localhost:8080/pages/restoration-shaman_3v3.html",
  "spec": "restoration-shaman",
  "bracket": "3v3",
  "sample_size": 50,
  "clusters": 3
}
```

---

## 7. `get_player_details_tool`

Queries the local SQLite cache directly — does **not** hit the Blizzard API. The player must have been included in a previous `fetch_top_players` call for their spec and bracket.

### Output (found)

```json
{
  "name": "Healbot",
  "realm": "area-52",
  "spec": "Restoration",
  "class": "Shaman",
  "rating": 2715,
  "equipped_ilvl": 254,
  "talent_code": "BAQAAAAAAAAAAAAkU...",
  "class_node_ids": [101, 102, 103],
  "spec_node_ids": [201, 202],
  "hero_node_ids": [301],
  "gear": [
    {
      "slot": "head",
      "item_id": 237637,
      "item_name": "Locus of the Primal Core",
      "ilvl": 258,
      "enchant_id": null,
      "enchant_name": null
    }
  ]
}
```

`talent_code` is the WoW talent export string — can be pasted directly into the in-game talent UI to copy the build.

Not found returns `{"error": "Player Healbot-area-52 not found in cache. Fetch their spec first."}`.

### Known limitations

- **Cache-only**: returns data from the time of the last fetch, not live data. A player's gear may have changed.
- **Bypasses CacheStore**: the implementation issues raw SQL directly rather than going through `CacheStore` methods — a maintenance inconsistency (noted in BACKLOG).
- **No test**: this tool has no unit test. Noted in BACKLOG.
- **Single result**: if a player appears in multiple spec+bracket caches (e.g. they play both Resto and Ele), returns whichever has the highest rating.

### Future work

- Add unit test
- Route through `CacheStore` instead of raw SQL
- Add a `fresh` flag that re-fetches from Blizzard API if the cached data is old
- Support looking up a player by partial name match
