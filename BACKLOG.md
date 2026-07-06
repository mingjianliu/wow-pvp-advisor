# Backlog

## Code Review 2026-07-06 — Design & Architecture

### 🔴 Tier 1 — Low effort, high payoff

- [ ] **Centralize config into a `settings.py`** — TTL `2h` is hardcoded in three places (`tools/fetch.py:42`, `tools/summary.py:59`, `tools/ui.py:299` as `2 * 3600`); port 8080, concurrency 10, HAC threshold 0.3, `MAX_DECISION = 8`, and jaccard weights 20/5/0.1 are all magic numbers buried in function bodies. `.env` loading is scattered across three entry points (`mcp_server.py`, `cli.py`, module-level in `tools/ui.py`) while a separate `config.py` `load_config()` mechanism coexists. Also `fetch.py:18` does bare `os.environ["BNET_CLIENT_ID"]` — missing creds raise a raw `KeyError` instead of a friendly error. (Season ID automation is already tracked in TODO below.)
- [ ] **Merge the two copy-pasted HAC functions** — `cluster_talents_hac` and `cluster_talents_hac_average` (`processor/talents.py:134-248`) are ~90% identical, differing only in the linkage formula. Parameterize into one function with a linkage strategy.
- [ ] **Remove dead branch in `_parse_talents`** — the third `elif not spec_id and ...` at `api/client.py:49` is unreachable; the second branch's condition is a superset of it.
- [ ] **Stop swallowing talent-name resolution errors** — `tools/summary.py:74-75` has `except Exception: pass` around `TalentNameCache.resolve`; failures silently produce all-null names with no way to debug. At minimum log the exception.
- [ ] **Repo hygiene** — `tests/visual/node_modules` is not in `.gitignore` (dozens of untracked entries); `.coverage`, `server.log`, `app_output.txt`, `dist/`, `build/`, `reproduce_issue.py` sit in the repo root; root `cli.py` and `wow_advisor/cli.py` are two parallel CLIs.

### 🟡 Tier 2 — Medium effort

- [ ] **Precompute a distance matrix for clustering** — HAC recomputes `_weighted_jaccard_distance` for every point pair on every merge iteration, then `summarize_talent_clusters` runs both complete AND average linkage end-to-end, plus silhouette and medoid passes — the same pair distance is computed hundreds of times. Compute the n×n matrix once up front (as `calculate_silhouette_scores` already does) and reuse it everywhere. Also decompose `summarize_talent_clusters` (analyze → partition → cluster → select → medoid → summarize all in one function) and normalize the `node_ranks_list or [{} for _ in range(n)]` default once at the top instead of 5 times.
- [ ] **Hero partition over-fragments clusters** — `processor/talents.py:410-413` groups players by exact `frozenset(node_set & hero_nodes)`. Hero trees contain choice nodes, so two players on the _same_ hero tree with one differing node land in different partitions and can never cluster together. Partition by hero-tree identity (left/right) instead of exact node set.
- [ ] **Singleton DB connection** — `get_default_db()` opens a fresh connection and re-runs `executescript` on every call (`cache/db.py:64-78`); `api/wowhead.py` opens one per tooltip read and another per write; connections are never closed. Keep one connection per process (or per thread) and initialize schema once.
- [ ] **Locale-keyed cache double-fetches Blizzard data** — players/aggregations are cached per `locale` (`cache/db.py:38`), but talent node IDs and item IDs are language-independent. Building zh + en pages hits the Blizzard API twice and the two pages are snapshots from different moments. Store IDs once; resolve names at display time per locale (the `TalentNameCache` / wowhead tooltip pattern already does this).
- [ ] **Replace `{"error": ...}` dict convention with exceptions internally** — errors propagate via `if "error" in result` through `fetch.py` → `summary.py` → `ui.py` → `talent_tree.py`; the convention is fragile and easy to skip in middle layers. Raise typed exceptions internally; convert to error dicts only at the MCP tool boundary in `mcp_server.py`.

### 🟢 Tier 3 — Larger refactors

- [ ] **Unify on async end-to-end** — the codebase flip-flops: `fetch_top_players` is a sync `asyncio.run` wrapper; `talent_tree.py:151-172` spawns a thread just to `asyncio.run` when already inside a loop; `build_page` calls `asyncio.run(prefetch_tooltips(...))` twice back-to-back (`ui.py:470-471`), each rebuilding an event loop and `httpx.AsyncClient` with zero TCP reuse. FastMCP supports async tools — make tools `async def`, give `BnetClient` one long-lived `AsyncClient` (currently `_get_static`/`fetch_leaderboard`/`fetch_character_details` create ad-hoc clients while `fetch_character_spec` requires one passed in), and keep `asyncio.run` only at CLI entry points.
- [ ] **Split `tools/ui.py` (518 lines, five responsibilities)** — MCP tool entry, data transform, HTML bundling via regex replacement, an embedded HTTP server + background thread, and browser launching all in one module with import-time side effects (`load_dotenv()` at line 14, mid-file imports at 275/383). Extract a pure `page_builder.py` (data → HTML) and a standalone server module. Server-specific fixes: use `ThreadingHTTPServer` — `DynamicReportHandler.translate_path` triggers a full `build_page` (dozens of API calls) synchronously inside the single-threaded server, blocking all requests; `_ensure_server` treats any process listening on 8080 as its own server (`ui.py:339-348`); the error page at `ui.py:311` interpolates the error string into HTML unescaped.
- [ ] **Precompile the frontend** — `index.html` ships React development builds + Babel standalone from unpkg CDN, recompiling ~2900 lines of JSX in the browser on every page load. "Self-contained" pages actually depend on unpkg/zamimg — offline means a blank page. Add an esbuild/vite build step (vite already exists under `tests/visual`) and switch to React production builds. Also dedupe `_SPEC_LABELS` (40 specs hardcoded in `ui.py:22-62`) against the spec mapping in `normalize.py` — one domain table, two copies today.

## Bugs

- [x] **Talent node IDs are not human-readable** — (RESOLVED) Implemented `TalentNameCache` to map node IDs to names via the Blizzard static API. Integrated with MCP tools and HTML reports.

- [x] **Talent clusters are fragmented** — (RESOLVED) Implemented Agglomerative Hierarchical Clustering (HAC) with weighted Jaccard distance to group similar builds effectively.

- [ ] **`enchant_name` contains "Enchanted: " prefix** — display strings from the Blizzard API always start with "Enchanted: Enchant Slot - Name". Could strip to just "Name" for cleaner output.

## Missing Test Coverage

- [ ] `get_player_details` in `tools/gear.py` — no test. Should save players via `CacheStore`, then verify `get_player_details` returns correct talent code and gear.
- [ ] 429 retry behavior in `client._get` — the exponential backoff path has zero coverage. Add a `respx` test that returns two 429s then a 200.
- [ ] `fetch_character_spec` and `fetch_character_details` — the two new Phase 1/2 methods added in the two-phase fetch refactor have no unit tests.
- [ ] `_parse_gear` enchant markup stripping — should have a unit test for the `|A:...|a` regex.

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
