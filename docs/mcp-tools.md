# MCP Tools Design Reference

These are the 4 tools exposed by `mcp_server.py`. Each section covers purpose, inputs, outputs, behavior, known limitations, and future work.

---

## 1. `fetch_top_players_tool`

### Purpose

The data entry point. Hits the Blizzard Battle.net API to find and cache the top players of a given spec and bracket. Must be called before any query tool can return data. Also acts as a manual refresh trigger.

### When it's called automatically

`get_talent_distribution_tool` and `get_gear_summary_tool` auto-call this if their cache is older than 2 hours.

### Inputs

| Parameter | Type | Default  | Description                                                                     |
| --------- | ---- | -------- | ------------------------------------------------------------------------------- |
| `spec`    | str  | required | Spec name. Accepts aliases: `"rsham"`, `"resto shaman"`, `"restoration-shaman"` |
| `bracket` | str  | required | PvP bracket. Accepts: `"3v3"`, `"2v2"`, `"solo shuffle"`, `"shuffle"`           |
| `region`  | str  | `"us"`   | `"us"` or `"eu"`                                                                |
| `limit`   | int  | `50`     | How many matching players to collect                                            |

### What it does (two phases)

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

`skipped: true` means the 2-hour cache guard fired and no API calls were made.

### Output (error)

```json
{
  "error": "Found 0 restoration-shaman players across 5026 3v3 leaderboard entries."
}
```

Other error cases: unknown spec, no leaderboard data for the bracket.

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

### Purpose

Returns how top players are distributing their talent points — which talents are universal (core), which vary between players (contested), and how builds cluster into distinct variants.

### Inputs

| Parameter | Type | Default  | Description                       |
| --------- | ---- | -------- | --------------------------------- |
| `spec`    | str  | required | Spec name (same aliases as fetch) |
| `bracket` | str  | required | PvP bracket                       |
| `region`  | str  | `"us"`   | `"us"` or `"eu"`                  |

### What it does

Checks `is_stale(spec, bracket, region, ttl_hours=2)`. If stale, calls `fetch_top_players` first. Returns the `talents` section of the cached aggregation.

### Output

```json
{
  "spec": "restoration-shaman",
  "bracket": "3v3",
  "region": "us",
  "sample_size": 50,
  "cached_at": 1779046010,
  "talents": {
    "core_nodes": [81018, 81021, ...],
    "flex_nodes": [81019, 103427, ...],
    "contested_nodes": [81039, 81073, ...],
    "clusters": [
      {
        "rank": 1,
        "count": 8,
        "pct": 16.0,
        "canonical_code": "BAQAAAAAAAAAAAAkU...",
        "takes": [81039, 81073],
        "skips": [81038, 81043]
      }
    ],
    "clustering_method": "variance+hamming"
  }
}
```

**Node classifications:**

- `core_nodes` — picked by ≥80% of players. Not a meaningful decision point.
- `flex_nodes` — picked by ≤20% of players. Situational or unpopular.
- `contested_nodes` — picked by 20–80% of players. These are the actual build-defining choices.

**Clusters:** Builds are grouped using greedy Hamming distance clustering (threshold=1) on the contested node set only. Each cluster has a canonical talent export code that can be imported into the game client.

**`clustering_method`:** `"variance+hamming"` (automatic) or `"keystone"` (if `data/keystone_talents.json` has an override for this spec).

### Known limitations

- **Node IDs, not names**: output is numeric node IDs. Claude must infer talent names from context. See BACKLOG: talent node name lookup.
- **Fragmented clusters**: with threshold=1 and many contested nodes, clusters can be small (top cluster 8% in early Midnight S1). This is partly a data-sparsity issue (50 players, high build diversity in early season) and partly a tuning issue.
- **Clustering is greedy and order-dependent**: a "bridge" build equidistant between two clusters gets absorbed into whichever it encounters first.

### Future work

- Map node IDs → human-readable talent names via Blizzard static API
- Add `data/keystone_talents.json` entries for common specs to force cleaner clusters
- Expose clustering threshold as a parameter
- Return the talent export code in a format directly importable to WoW (already present as `canonical_code`)

---

## 3. `get_gear_summary_tool`

### Purpose

Returns what items and enchants top players are using, aggregated by slot. Answers questions like "what trinkets should I use?", "what's the best weapon enchant?", "what ilvl are top players at?"

### Inputs

| Parameter | Type | Default  | Description      |
| --------- | ---- | -------- | ---------------- |
| `spec`    | str  | required | Spec name        |
| `bracket` | str  | required | PvP bracket      |
| `region`  | str  | `"us"`   | `"us"` or `"eu"` |

### What it does

Same stale-check pattern as `get_talent_distribution_tool`. Returns the `gear` and `enchants` sections of the cached aggregation.

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

## 4. `get_player_details_tool`

### Purpose

Returns the full talent loadout and gear for a single specific player by name. Useful for inspecting a top player's exact build, or comparing two players.

### Inputs

| Parameter | Type | Default  | Description                                 |
| --------- | ---- | -------- | ------------------------------------------- |
| `name`    | str  | required | Character name (case-insensitive)           |
| `realm`   | str  | required | Realm slug, e.g. `"area-52"`, `"stormrage"` |
| `region`  | str  | `"us"`   | `"us"` or `"eu"`                            |

### What it does

Queries the local SQLite cache directly. Does **not** hit the Blizzard API. The player must have been included in a previous `fetch_top_players` call for their spec and bracket.

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

### Output (not found)

```json
{
  "error": "Player Healbot-area-52 not found in cache. Fetch their spec first."
}
```

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
