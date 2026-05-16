# WoW PvP Advisor — Design Spec

**Date:** 2026-05-16  
**Status:** Approved

## Overview

A Python tool that fetches top-50 player data (talents, gear, enchants) for any WoW retail PvP spec/bracket via the Blizzard Battle.net API, stores it in a local SQLite cache, and exposes it as an MCP server so Claude Code can answer questions like "what talents should I run as Resto Shaman in 3v3?" with real meta data.

## Goals

- Query any spec + bracket combination on demand
- Deterministic data layer: fetch, aggregate, cache — no LLM involved
- LLM layer: Claude Code calls MCP tools, interprets aggregated data, gives guidance
- Start with 3v3; extend to Solo Shuffle and 2v2 without restructuring
- Dev mode: run fetch script, paste output into Claude Code session; prod mode: MCP server

## Non-Goals

- No web UI or REST API
- No continuous background update daemon (on-demand with TTL instead)
- No replay analysis or match history
- No support for Mythic+ or PvE content

---

## Architecture

Four layers, each with a single clear purpose:

```
Claude Code  ←→  MCP Server  ←→  Core Python (api / processor / cache)  ←→  Blizzard API
```

1. **Claude Code**: user asks questions; calls MCP tools to pull real data; narrates findings
2. **MCP Server** (`mcp_server.py`): thin fastmcp wrapper; registers 4 tools; no business logic
3. **Core Python** (`wow_advisor/`): API client, data processor, SQLite cache
4. **Blizzard Battle.net API**: OAuth2 client credentials, free dev key, rate-limited

---

## Data Source: Blizzard Battle.net API

Authentication: OAuth2 client credentials flow (no user login required).

```
POST https://oauth.battle.net/token
  grant_type=client_credentials
  client_id={BNET_CLIENT_ID}
  client_secret={BNET_CLIENT_SECRET}
→ { access_token, expires_in }
```

Token is cached in memory and auto-refreshed before expiry.

### Per-fetch sequence (for a given spec + bracket)

**Step 1 — Leaderboard** (1 API call):

```
GET https://{region}.api.blizzard.com/data/wow/pvp-season/{season_id}/pvp-leaderboard/{bracket}
    ?namespace=dynamic-{region}&locale=en_US
```

Returns all ladder entries with name, realm, class, spec, rating. Filter to target spec, take top 50.

**Step 2 — Per-character** (3 concurrent API calls per player, 150 total for 50 players):

```
GET /profile/wow/character/{realm}/{name}                  → class, spec, equipped_item_level
GET /profile/wow/character/{realm}/{name}/specializations  → talent_loadout_code (base64 string)
GET /profile/wow/character/{realm}/{name}/equipment        → per-slot items + enchant IDs
```

All three calls fire concurrently per player via `httpx.AsyncClient`. Rate limited to 100 req/sec.

**Season ID**: hardcoded constant, updated each season (same pattern as pvpqnet's `CURRENT_PVP_SEASON_ID`).

---

## Data Model (SQLite)

Three tables:

### `players`

| Column        | Type       | Notes                        |
| ------------- | ---------- | ---------------------------- |
| id            | INTEGER PK |                              |
| name          | TEXT       |                              |
| realm         | TEXT       |                              |
| class         | TEXT       |                              |
| spec          | TEXT       |                              |
| bracket       | TEXT       | e.g. `3v3`, `2v2`, `shuffle` |
| region        | TEXT       | `us` or `eu`                 |
| rating        | INTEGER    |                              |
| equipped_ilvl | INTEGER    |                              |
| fetched_at    | INTEGER    | Unix timestamp               |

### `player_loadouts`

| Column      | Type       | Notes                                                                      |
| ----------- | ---------- | -------------------------------------------------------------------------- |
| player_id   | INTEGER FK |                                                                            |
| talent_code | TEXT       | raw base64 loadout export string                                           |
| gear        | TEXT       | JSON: list of `{slot, item_id, item_name, ilvl, enchant_id, enchant_name}` |

### `aggregations`

| Column      | Type    | Notes                                    |
| ----------- | ------- | ---------------------------------------- |
| spec        | TEXT    |                                          |
| bracket     | TEXT    |                                          |
| region      | TEXT    |                                          |
| computed_at | INTEGER | Unix timestamp                           |
| data        | TEXT    | JSON blob (see Aggregation Format below) |

Unique index on `(spec, bracket, region)`. New aggregation overwrites old.

---

## Talent Clustering

Exact-match grouping of talent loadout codes is insufficient — two players with 49/50 identical talent choices produce completely different code strings. The following pipeline produces meaningful build clusters automatically.

### Pipeline (A+B)

**Step 1 — Decode**: Each loadout export string (base64) is decoded to a bit vector — one bit per talent node. Community-documented format; Python decoder implemented in `processor/talents.py`.

**Step 2 — Variance analysis (A)**: For each talent node position, compute pick rate across all 50 players:

- **Core talents** (≥80% pick rate): taken by nearly everyone — don't surface as a decision point
- **Flex talents** (≤20% pick rate): rarely taken — also not a decision point
- **Contested talents** (20–80%): these are the real build-defining choices

**Step 3 — Hamming clustering on contested nodes (B)**: Cluster builds by their contested-talent bit vectors using Hamming distance threshold (default: 2 — builds differing in ≤2 contested talents are the same cluster). Each cluster gets a canonical build (most common variant within the cluster).

**Step 4 — Output**: 2–4 meaningful build clusters, each annotated with count, pick rate, and which contested talents it takes vs skips.

### Fallback (C) — Human-labeled keystone talents

If A+B clustering produces noisy or uninterpretable results for a given spec (e.g., too many small clusters, or contested talents turn out to be cosmetic choices), a per-spec JSON override can be added:

```json
// data/keystone_talents.json
{
  "restoration-shaman": [12345, 67890, 11111] // talent node IDs of keystone choices
}
```

When a keystone file exists for a spec, the processor uses only those nodes for clustering instead of the variance-derived contested set. This is maintained manually and updated per patch. The A+B path remains the default for all specs without a keystone file.

### Aggregation Format

The `data` JSON blob stored in `aggregations`:

```json
{
  "spec": "restoration-shaman",
  "bracket": "3v3",
  "region": "us",
  "sample_size": 50,
  "avg_ilvl": 639,
  "talents": {
    "core_nodes": [101, 102, 103],
    "contested_nodes": [201, 202, 203, 204],
    "clusters": [
      {
        "rank": 1,
        "count": 28,
        "pct": 56.0,
        "canonical_code": "BAQAAAAAAAAAAAAkU...",
        "takes": [201, 203],
        "skips": [202, 204]
      },
      {
        "rank": 2,
        "count": 15,
        "pct": 30.0,
        "canonical_code": "BAQAAAAAAAAAAAAmV...",
        "takes": [202, 204],
        "skips": [201, 203]
      }
    ],
    "clustering_method": "variance+hamming"
  },
  "gear": {
    "head": [
      {
        "item_id": 212456,
        "name": "Dawnbreaker's Hood",
        "count": 31,
        "pct": 62.0
      }
    ],
    "trinket1": [],
    "trinket2": []
  },
  "enchants": {
    "chest": [
      {
        "enchant_id": 7459,
        "name": "Crystalline Radiance",
        "count": 40,
        "pct": 80.0
      }
    ]
  }
}
```

Trinkets surfaced separately since they're the highest-impact slot. `clustering_method` is `"variance+hamming"` by default or `"keystone"` when the fallback override is active.

---

## MCP Tools

Registered in `mcp_server.py` via fastmcp:

### `fetch_top_players(spec, bracket, region="us", limit=50)`

Triggers a fresh Blizzard API fetch for the given spec+bracket. Writes raw data to SQLite and recomputes aggregation. Returns `{"fetched": 50, "cached_at": 1747382400}`. Use this to refresh stale data before querying.

### `get_talent_distribution(spec, bracket, region="us")`

Returns the aggregated talent data from cache. If cache is older than 24h, auto-triggers a fetch first. Returns top talent builds sorted by pick rate with human-readable context (rank, count, pct).

### `get_gear_summary(spec, bracket, region="us")`

Returns per-slot most popular items, enchants by slot, and avg item level from cache. Trinkets highlighted separately. Same 24h TTL logic.

### `get_player_details(name, realm, region="us")`

Returns full gear + talent for a single named player from the local cache. Does not trigger a new API call — player must have been fetched as part of a recent `fetch_top_players` run.

---

## Project Structure

```
wow-pvp-advisor/
├── mcp_server.py          # fastmcp entry point; registers all 4 tools
├── cli.py                 # manual: `python cli.py fetch resto-shaman 3v3`
├── pyproject.toml
├── .env.example           # BNET_CLIENT_ID, BNET_CLIENT_SECRET, BNET_REGION
├── wow_advisor/
│   ├── api/
│   │   ├── auth.py        # OAuth2 token fetch + in-memory refresh
│   │   ├── client.py      # async httpx client, rate limiter (100 req/sec)
│   │   └── models.py      # dataclasses: LeaderboardEntry, CharacterData, GearSlot
│   ├── cache/
│   │   ├── db.py          # SQLite connection, schema init
│   │   └── store.py       # read/write players, loadouts, aggregations; TTL check
│   ├── processor/
│   │   ├── talents.py     # decode loadout codes, variance analysis, Hamming clustering
│   │   ├── gear.py        # per-slot item + enchant frequency
│   │   └── aggregator.py  # orchestrate talents + gear → aggregation JSON
│   └── tools/
│       ├── fetch.py       # fetch_top_players implementation
│       ├── talents.py     # get_talent_distribution implementation
│       └── gear.py        # get_gear_summary implementation
└── data/
    ├── wow_advisor.db          # SQLite file (gitignored)
    └── keystone_talents.json   # optional per-spec talent overrides (fallback C)
```

---

## Error Handling

| Scenario                                        | Handling                                                                                    |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Rate limit (429)                                | httpx retry with exponential backoff, max 3 attempts                                        |
| Character not found (404)                       | Skip player, log, continue with rest of top 50                                              |
| Token expiry                                    | Auto-refresh before any request                                                             |
| `/equipment` fails, `/specializations` succeeds | Store partial — talent data saved, gear slot left empty                                     |
| Blizzard API outage                             | Serve last cached aggregation; include `cached_at` in response so Claude can flag staleness |
| Spec not in current season leaderboard          | Return empty with clear error message                                                       |

---

## Spec + Bracket Normalization

Input strings are normalized before any lookup:

- `"resto shaman"` / `"rsham"` / `"restoration shaman"` → `"restoration-shaman"`
- `"3v3"` / `"3V3"` / `"three"` → `"3v3"`
- `"solo"` / `"solo shuffle"` / `"shuffle"` → `"shuffle"`

Normalization lives in a single `normalize.py` module, extended as new aliases come up.

---

## Claude Code Setup

After installing:

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "wow-advisor": {
      "command": "python",
      "args": ["/path/to/wow-pvp-advisor/mcp_server.py"],
      "env": {
        "BNET_CLIENT_ID": "...",
        "BNET_CLIENT_SECRET": "..."
      }
    }
  }
}
```

---

## Dependencies

```toml
[project]
dependencies = [
  "fastmcp>=2.0",
  "httpx>=0.27",
  "python-dotenv>=1.0",
]
```

`sqlite3` is Python stdlib — no extra dependency.

---

## Extensibility

- **New brackets** (2v2, Solo Shuffle): no code changes — bracket is a parameter
- **EU region**: pass `region="eu"` to any tool
- **New aggregations** (e.g. stat priority, gem choices): add a new processor function + new MCP tool
- **Talent code decoding**: the loadout code is a standard WoW export string; a decoder can be added to `talents.py` to show human-readable talent names instead of the raw code
