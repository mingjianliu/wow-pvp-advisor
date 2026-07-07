# Backlog

## Code Review 2026-07-06 — Design & Architecture

### 🔴 Tier 1 — Low effort, high payoff

- [x] **Centralize config into a `settings.py`** — (RESOLVED 2026-07-06) Added `wow_advisor/settings.py` holding TTL, port, concurrency, season ID, clustering thresholds, and jaccard weights; all call sites now import from it. Missing credentials now raise a friendly `MissingCredentialsError` instead of a raw `KeyError`. Remaining: `.env` loading is still per-entry-point (acceptable), and season ID automation is tracked in TODO below.
- [x] **Merge the two copy-pasted HAC functions** — (RESOLVED 2026-07-06) `cluster_talents_hac` now takes `linkage="complete"|"average"`; `cluster_talents_hac_average` kept as a thin wrapper for existing callers.
- [x] **Remove dead branch in `_parse_talents`** — (RESOLVED 2026-07-06) Removed the unreachable third `elif` in `api/client.py`.
- [x] **Stop swallowing talent-name resolution errors** — (RESOLVED 2026-07-06) `tools/summary.py` now logs a warning with traceback instead of `except Exception: pass`.
- [x] **Repo hygiene** — (RESOLVED 2026-07-06) `.gitignore` now covers `node_modules/`, `.coverage`, `.codex/`, `.mcp.json` (logs/`dist`/`build` were already ignored); untracked `.coverage`, deleted `reproduce_issue.py`. Root `cli.py` (developer JSON CLI) and `wow_advisor/cli.py` (`wow-advisor` end-user CLI) turned out to be different tools, not duplicates — docstrings now state the distinction.

### 🟡 Tier 2 — Medium effort

- [x] **Precompute a distance matrix for clustering** — (RESOLVED 2026-07-06) Added `_DistanceCache` (memoized pairwise distances keyed by original player index), shared across both HAC linkages, silhouette scoring, and medoid selection. Also normalized the `node_ranks_list or [...]` default once at the top of `summarize_talent_clusters` and collapsed the duplicated complete/average linkage blocks into one loop. Bonus fix: HAC was looking up `node_ranks` by _position within the pairs list_ instead of the original player index — wrong ranks for every hero group after the first; now uses the original index (regression test added).
- [x] **Hero partition over-fragments clusters** — (RESOLVED 2026-07-06) `aggregator.py` now stamps hero nodes with `hero_tree: "left"/"right"`; `_hero_partition` groups players by tree identity so same-tree players with differing choice-node picks can cluster together. Falls back to exact-set grouping when side info is absent (old behavior, keeps existing tests/fixtures valid). All 18 cached aggregations rebuilt with the new logic.
- [x] **Singleton DB connection** — (RESOLVED 2026-07-06) `get_default_db()` now reuses one connection per thread per path (thread-local cache; sqlite3 connections aren't safe to share across threads), with schema `executescript` run only once per path per process. `api/wowhead.py`'s per-tooltip calls now hit the cache automatically. `init_db()` unchanged for tests/direct use.
- [ ] **Locale-keyed cache double-fetches Blizzard data** — players/aggregations are cached per `locale` (`cache/db.py:38`), but talent node IDs and item IDs are language-independent. Building zh + en pages hits the Blizzard API twice and the two pages are snapshots from different moments. Store IDs once; resolve names at display time per locale (the `TalentNameCache` / wowhead tooltip pattern already does this).
- [ ] **Replace `{"error": ...}` dict convention with exceptions internally** — errors propagate via `if "error" in result` through `fetch.py` → `summary.py` → `ui.py` → `talent_tree.py`; the convention is fragile and easy to skip in middle layers. Raise typed exceptions internally; convert to error dicts only at the MCP tool boundary in `mcp_server.py`.

### 🟠 Tier 2.5 — Quick wins from second review pass (2026-07-07)

- [x] **`wow-advisor` entry point missing** — (RESOLVED 2026-07-07) `pyproject.toml` had no `[project.scripts]`, so the command that `wow_advisor/cli.py` and the docs referenced never existed. Added `wow-advisor = "wow_advisor.cli:main"`.
- [x] **Spec domain table duplicated 3× in Python** — (RESOLVED 2026-07-07) `ui._SPEC_LABELS` and `talent_names.SPEC_IDS` are now derived from `normalize._SPEC_INFO_MAP` (single source). The frontend `app.jsx` `CLASSES` table remains a 4th copy — fold into the Tier 3 frontend-precompile work (generate it at build time).
- [x] **Query-tool TTL was an implicit default** — (RESOLVED 2026-07-07) Added `QUERY_TTL_HOURS = 24` to settings; `get_gear_summary` and `get_talent_distribution` now pass it explicitly instead of relying on `store.is_stale`'s signature default.
- [x] **One-off debug scripts** — (RESOLVED 2026-07-07) Deleted `run_app.py` (PyInstaller smoke test with hardcoded dist path) and `scripts/{debug_clustering,debug_clustering_v2,linkage_comparison,ab_test_batch}.py` (clustering-tuning era leftovers; `linkage_comparison` embedded a stale copy of the average-linkage implementation). Kept `fetch_all_specs`, `fetch_healers`, `get_spec_clusters`.
- [ ] **Keystone mechanism is dead code** — `data/keystone_talents.json` is `{}`; the whole override path (`_load_keystone_nodes`, the `keystone` branch in `summarize_talent_clusters`, docs mentions) has never fired. Decide: populate it for key specs, or remove the mechanism. (User decision pending.)

### 🟢 Tier 3 — Larger refactors

- [ ] **Unify on async end-to-end** — the codebase flip-flops: `fetch_top_players` is a sync `asyncio.run` wrapper; `talent_tree.py:151-172` spawns a thread just to `asyncio.run` when already inside a loop; `build_page` calls `asyncio.run(prefetch_tooltips(...))` twice back-to-back (`ui.py:470-471`), each rebuilding an event loop and `httpx.AsyncClient` with zero TCP reuse. FastMCP supports async tools — make tools `async def`, give `BnetClient` one long-lived `AsyncClient` (currently `_get_static`/`fetch_leaderboard`/`fetch_character_details` create ad-hoc clients while `fetch_character_spec` requires one passed in), and keep `asyncio.run` only at CLI entry points.
- [ ] **Split `tools/ui.py` (518 lines, five responsibilities)** — MCP tool entry, data transform, HTML bundling via regex replacement, an embedded HTTP server + background thread, and browser launching all in one module with import-time side effects (`load_dotenv()` at line 14, mid-file imports at 275/383). Extract a pure `page_builder.py` (data → HTML) and a standalone server module. Server-specific fixes: use `ThreadingHTTPServer` — `DynamicReportHandler.translate_path` triggers a full `build_page` (dozens of API calls) synchronously inside the single-threaded server, blocking all requests; `_ensure_server` treats any process listening on 8080 as its own server (`ui.py:339-348`); the error page at `ui.py:311` interpolates the error string into HTML unescaped.
- [ ] **Precompile the frontend** — `index.html` ships React development builds + Babel standalone from unpkg CDN, recompiling ~2900 lines of JSX in the browser on every page load. "Self-contained" pages actually depend on unpkg/zamimg — offline means a blank page. Add an esbuild/vite build step (vite already exists under `tests/visual`) and switch to React production builds. Also dedupe `_SPEC_LABELS` (40 specs hardcoded in `ui.py:22-62`) against the spec mapping in `normalize.py` — one domain table, two copies today.

## Bugs

- [x] **Talent node IDs are not human-readable** — (RESOLVED) Implemented `TalentNameCache` to map node IDs to names via the Blizzard static API. Integrated with MCP tools and HTML reports.

- [x] **Talent clusters are fragmented** — (RESOLVED) Implemented Agglomerative Hierarchical Clustering (HAC) with weighted Jaccard distance to group similar builds effectively.

- [ ] **`enchant_name` contains "Enchanted: " prefix** — display strings from the Blizzard API always start with "Enchanted: Enchant Slot - Name". Could strip to just "Name" for cleaner output.

## Missing Test Coverage

All four items below turned out to already be covered (verified 2026-07-07):

- [x] `get_player_details` — `tests/test_gear_tools.py` (found + not-found cases)
- [x] 429 retry behavior in `client._get` — `tests/test_client_retries.py` (success, exhausted, timeout)
- [x] `fetch_character_spec` / `fetch_character_details` — `tests/test_client_extra.py`
- [x] `_parse_gear` enchant markup stripping — `tests/test_client_extra.py::test_parse_gear_edge_cases`

## Future Improvements

- [ ] **Per-player cache granularity** — currently cache is per spec+bracket+region (all 50 players lumped together with one TTL). A finer approach: cache each player's gear/talent data individually with their own `fetched_at` timestamp. On the next fetch, only re-fetch players whose data is stale or whose rank has changed significantly, and skip players already fresh. This avoids hammering the API for 50 characters when only a few have changed rankings.

## TODO

- [ ] **Automate `CURRENT_SEASON_ID` detection** — Replace hardcoded `CURRENT_SEASON_ID = 41` in `wow_advisor/api/client.py` with an automated lookup via `/data/wow/pvp-season/index` on startup.
- [ ] **Wire `BNET_REGION` environment variable** — Ensure `wow_advisor/api/client.py` and `tools/fetch.py` respect the `BNET_REGION` env var if no region is explicitly provided via CLI/MCP.
- [ ] **Expose `scan_limit` via CLI and MCP** — currently hardcoded to scan the full leaderboard. For common specs (Warrior, Mage) you hit 50 players quickly; for rare specs you scan everything. A user-configurable limit would help.

- [x] **Talent name lookup** — add `wow_advisor/processor/talent_names.py` that fetches from Blizzard's static API (`/data/wow/playable-specialization/{specId}`) and maps node IDs → names. Cache in `data/talent_names.json`. Makes the MCP output immediately readable.

- [ ] **arenacoach.gg regression comparison** — currently skipped (no public API). Check periodically if they expose one.

- [ ] **pvpq.net regression comparison** — currently skips (no Midnight data). Re-enable once they update to Midnight Season 1.

- [ ] **EU region support** — everything is wired for `region="eu"` but untested. Run a fetch against EU ladder to validate.

- [ ] **Solo Shuffle and 2v2 validation** — fetch at least one spec for each bracket to confirm the season ID and leaderboard parsing work for non-3v3 brackets.

- [ ] **keystone_talents.json for Resto Shaman** — add node IDs for the 3-4 genuinely defining talent choices to produce cleaner clusters. Requires knowing current Midnight S1 Resto Shaman talent tree.

- [ ] **Persistent Report Caching** — currently HTML reports are just files on disk. Add a system to track report freshness in the SQLite DB, allowing the `DynamicReportHandler` to automatically re-generate reports when the underlying Blizzard data becomes stale (e.g. >2 hours old).

## Visualisation & Reporting

- [ ] **Text summary MCP tool (`get_build_summary_tool`)** — new MCP tool returning a human-readable breakdown Claude can narrate directly. Shows mandatory talents (≥80%), per-cluster flexible choices, and top gear per slot. Depends on talent name lookup.

- [x] **Talent tree HTML report** — CLI command `python cli.py report <spec> <bracket>` that generates and opens a local HTML page showing: cluster comparison table (clusters side-by-side, mandatory nodes highlighted green, contested nodes highlighted yellow, flex nodes dimmed), gear table per slot with pick-rate bars. Use the visual companion server already running at localhost.

- [ ] **Slack integration** — after each fetch, optionally post a text summary to a configured Slack channel via the Slack MCP. Good for sharing meta snapshots with teammates.

- [ ] **GitHub Pages publishing** — commit the HTML report to a `gh-pages` branch via the GitHub MCP so the report is accessible as a permanent URL without running anything locally.

- [ ] **Google Drive export** — export the build report as a Google Doc via the Google Drive MCP for annotation and sharing.

## Competitive Analysis TODOs (vs murlok.io / pvpq.net / arenacoach.gg)

### 🔴 High Priority — Quick Wins, High Impact

- [ ] **Gem recommendations** — parse gem data from the equipment API and surface in the gear panel. Murlok.io has this; players expect it alongside enchants.
- [ ] **Stat priority display on web UI** — requires first implementing a `get_stat_distribution` MCP tool (does not exist yet; would need stat parsing from the equipment API), then a visual bar chart component in the frontend showing secondary stat weights (Vers/Haste/Crit/Mastery).
- [ ] **Meta / Tier List landing page** — requires first implementing `get_pvp_tier_list_tool` and `get_meta_snapshot_tool` MCP tools (neither exists yet — the server currently exposes 7 tools, see `docs/mcp-tools.md`), then a landing page showing all specs ranked by representation/rating per bracket. Makes the app a destination, not just a per-spec tool.
- [ ] **Embellishment tracking** — track crafted gear embellishment special effects from top players. Murlok.io shows this; important for gear optimization in TWW.

### 🟡 Medium Priority — Differentiation Features

- [ ] **Public hosting (GitHub Pages / Vercel)** — currently local-only, which severely limits reach. Publish static HTML reports to a public URL. Already mentioned in Visualisation section above.
- [ ] **Landing page with all specs** — a single index page showing all 39 specs with quick-nav links. Currently users need to know the URL pattern or use breadcrumbs.
- [ ] **Race popularity** — aggregate which races top players choose per spec. Murlok.io shows this. Low effort, low-medium impact.
- [ ] **Build comparison mode** — side-by-side diff of two clusters. Visually show which talents differ between Build A and Build B.
- [ ] **Talent change highlights (patch delta)** — when a patch drops, show what changed in the meta since last snapshot. Requires storing historical snapshots.
- [ ] **Multi-region data (EU/KR/TW)** — EU support is wired but untested. KR/TW would add completeness. Murlok.io pulls from all 4 regions.

### 🟢 Ambitious — Unique Value, Higher Effort

- [ ] **Rating-bracket filtering** — show builds from 1800+, 2100+, 2400+, Glad+ separately. Different ratings run different builds. Nobody does this well.
- [ ] **Build win-rate correlation** — correlate build clusters with player rating performance (e.g. "Build A players average 2400 vs Build B at 2100"). Extremely hard but game-changing.
- [ ] **Comp / matchup data** — nobody has good comp win-rate data. Would require match-level data that Blizzard doesn't easily expose. Massive differentiator if solved.
- [ ] **Player search (any player)** — lookup any player's PvP build on-demand via API, not just cached top-50. PvPQ.net's core strength.
- [ ] **Historical season comparison** — archive past season data and show how the meta evolved. Murlok.io does this.
