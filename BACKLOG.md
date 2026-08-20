# Backlog

## Code Review 2026-07-06 — Design & Architecture

**Commits landed from this review (2026-07-06 → 07-07):**

| Commit    | Summary                                                                                                                                                                                                                                                                               |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `9268c3b` | docs: AGENTS.md as single agent-instruction source (CLAUDE.md symlink), drop Gemini CLI support, delete stale HANDOFF/implementer files, archive completed plans/specs, slim docs/mcp-tools.md (410→290 lines), fix README numbering                                                  |
| `e0e6716` | Tier 1: add `wow_advisor/settings.py` (all tunable constants + friendly `MissingCredentialsError`), merge the two HAC functions behind a `linkage=` param, remove dead `_parse_talents` branch, log swallowed talent-name errors, gitignore/untrack junk, clarify the two CLIs' roles |
| `c565cff` | untrack 182 `tests/visual/node_modules` files that predated the gitignore                                                                                                                                                                                                             |
| `5294840` | Tier 2: `_DistanceCache` shared across HAC/silhouette/medoid; fix HAC rank lookup using pairs-list position instead of original player index; fix hero partition to group by tree identity (`hero_tree: left/right`) instead of exact node sets; rebuilt all 18 cached aggregations   |
| `eca6024` | Tier 2: `get_default_db()` reuses one connection per thread per path; schema init once per path per process                                                                                                                                                                           |
| `060dcbe` | Tier 2.5 quick wins: add missing `wow-advisor` entry point, derive spec tables from `normalize._SPEC_INFO_MAP` (3 copies → 1), explicit `QUERY_TTL_HOURS`, delete 5 one-off debug scripts, mark 4 stale "missing test" items as already covered                                       |

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

## Patch 12.1 pass (2026-08-18)

Game build `12.1.0_68914`, talent trees last modified 2026-08-14. Diffed the 10 specs that had a pre-12.1 (May) talent-tree snapshot against the live static API.

### Landed

- [x] **Choice nodes had no name** — `api/client.py::fetch_talent_nodes` read only `ranks[0].tooltip.talent.name` and ignored `choice_of_tooltips`, so every CHOICE node resolved to `name=None` — 156 of 1017 cached nodes. `tools/ui.py:72` filters out nameless nodes, so the highest-weight build-defining talents were dropped from HTML reports entirely, and `_enrich_talents` emitted `null` names for them. Now resolves to both options joined (`"Ascendance / Healing Tide Totem"`) plus a structured `choices` list. Predates 12.1. Verified live: Restoration Shaman went from 20 unnamed nodes to 1 (a placeholder the API returns with no ranks).
- [x] **Node IDs are reassigned between builds, silently mislabelling cached data** — 12.1 swapped `92615`/`109679` (Battlelord ↔ Master Tactician) on Arms Warrior, rotated six Assassination Rogue IDs and three Feral Druid IDs. All PASSIVE single-rank nodes, so this is genuine reassignment, not a choice-node parsing artifact. Aggregations store raw node IDs and names are resolved at read time, while `TalentNameCache` revalidates hourly — so the next `get_full_summary_tool` call after 12.1 would have refreshed the tree and relabelled May node IDs with 12.1 names, with no error. Now every `talent_node_cache` row and aggregation is stamped with `game_build` (from the `Battlenet-Namespace` header); a build change forces staleness regardless of TTL, and if a refresh cannot repair the mismatch the summary withholds names and reports `stale_build`. Added `cache/db.py::_migrate` since `CREATE TABLE IF NOT EXISTS` never adds columns to an existing database.
- [x] **No PvP talent baseline existed** — the pool was only ever observed through player profiles (what the top 50 picked), so a removal was undetectable locally; Balance Druid's `Dying Stars` removal was confirmed only by cross-checking patch notes against the live API. Added the `pvp_talent_pool` table, `BnetClient.fetch_pvp_talents`, `processor/pvp_talents.diff_pvp_talent_pool`, and `scripts/snapshot_pvp_talents.py`. Baseline saved for all 39 specs at build `12.1.0_68914` (241 unique talents, 8–15 per spec).
- [x] **Stale mocks hid a production break** — `tests/test_talent_names.py` stubbed `fetch_talent_nodes` wholesale, so changing its return contract kept the suite green while `resolve()` swallowed the resulting `ValueError` and returned `{}` (all talent names gone). Added contract tests driving the real `BnetClient` with `respx` at the wire.

### Landed (second pass)

- [x] **Devourer Demon Hunter was missing entirely** — the API lists 40 playable specs; `_SPEC_INFO_MAP` had 39, so spec ID `1480` could not be queried at all despite 5002 entries on the Season 1 solo-shuffle leaderboard. Added to `normalize.py` with `devourer` / `dev dh` aliases, plus the frontend `app.jsx` `CLASSES` table and its zh translation (`噬灭`, taken from the API's `zh_CN` locale rather than guessed). A test now pins `len(_SPEC_INFO_MAP) == 40` so the next added spec fails loudly. Verified live: 50 players, ilvl 250.
- [x] **`blitz` bracket alias was dead** — `_BRACKET_ALIASES` mapped `blitz` to `battlegrounds/blitz`, which 404s. Blitz publishes per-spec boards (`blitz-{class}-{spec}`) exactly like solo shuffle, so `blitz` now normalizes to `blitz` and `tools/fetch.py` routes both brackets through one `_PER_SPEC_LEADERBOARDS` table. The frontend already normalized `Blitz` to `blitz`, so only the backend was wrong. Verified live: 50 players, ilvl 254.
- [x] **Leaderboard slugs were hyphenated instead of collapsed** — `tools/fetch.py::slugify` produced `demon-hunter` / `death-knight` / `beast-mastery`, but Blizzard's slugs remove spaces entirely (`shuffle-demonhunter-havoc`, `shuffle-deathknight-blood`, `shuffle-hunter-beastmastery`). Every affected slug 404s, which had silently disabled solo shuffle for all 3 Death Knight specs, all Demon Hunter specs, and Beast Mastery Hunter — 7 specs, matching the complete absence of solo-shuffle rows for them in the cache. Found while wiring blitz through the same code path. Verified live: Blood Death Knight solo shuffle now returns 50 players.

### Static data refresh (2026-08-18)

- [x] **All non-player caches brought to build `12.1.0_68914`** — added `scripts/refresh_static_data.py`, which re-resolves talent nodes, refreshes PvP talent pools, and re-fetches Wowhead tooltips for every spec and locale in one command. Result: `talent_node_cache` 14 rows (10 specs, May) → **80 rows (40 specs x en_US/zh_CN)**, 0 rows off the current build; `pvp_talent_pool` 39 → **80 rows** (Devourer added, zh_CN baselined); `tooltips` 1163 (May) → **5641 rows** (2826 en_US + 2815 zh_CN), all re-fetched. Player data is deliberately untouched — each aggregation refetches lazily on first access because its `game_build` no longer matches.
- [x] **`prefetch_tooltips` had no concurrency bound** — it gathered every id at once. The static refresh asks for ~2800 tooltips per locale, which would have opened that many simultaneous connections to Wowhead, a third-party site with no published quota. Now bounded by `WOWHEAD_CONCURRENCY = 8` in settings.
- [x] **PvP pool fetch/diff/save deduplicated** — `processor/pvp_talents.refresh_pvp_talent_pools` is now the single tested implementation; `snapshot_pvp_talents.py` and `refresh_static_data.py` are reporting shells over it.

### Found, not yet fixed
- [ ] **Most cached player data predates 12.1** — the original 1412 players were fetched 2026-05-19 to 06-01 with aggregations computed 07-07. Combined with node-ID reassignment that is not merely stale but wrong; the build stamp now forces a refetch per spec on first access, so this repairs itself lazily rather than needing a bulk run. Refetched so far as end-to-end validation (5 of 22 aggregations): `restoration-shaman` 3v3 and blitz, `devourer-demon-hunter` solo-shuffle, `blood-death-knight` solo-shuffle, `arms-warrior` 3v3. The remaining 17 carry `game_build IS NULL`.
- [ ] **Some node IDs cannot be named from Blizzard data** — `102911`, `102912`, `103120`, `103121` appear in Restoration Shaman `class_node_ids` in player profiles but are absent from `class_talent_nodes`/`spec_talent_nodes`/`hero_talent_trees` in the static talent-tree endpoint. Each spec also has one placeholder CHOICE node with no ranks (e.g. `99846`). ~8% of core nodes; predates 12.1. Would need a non-Blizzard source (e.g. wowhead) to resolve.

### 12.1 talent tree changes (specs with a May baseline)

| Spec | Nodes | Added | Removed | ID reassigned | Moved |
| --- | --- | --- | --- | --- | --- |
| marksmanship-hunter | 112→111 | 2 (`Deadeye`, `Eagle's Accuracy`) | 3 (incl. `Double Tap`) | 2 | 10 |
| assassination-rogue | 111→111 | 0 | 0 | 7 | 0 |
| arms-warrior | 106→105 | 0 | 1 (`Mass Execution`, merged into choice node `92614`) | 4 | 1 |
| feral-druid | 123→123 | 0 | 0 | 3 | 0 |
| restoration-shaman | 117→117 | 1 (`Swelling Tides`) | 1 (`Calm Waters`) | 0 | 1 |
| holy-paladin, blood-death-knight, enhancement-shaman, augmentation-evoker | unchanged | – | – | – | – |

Marksmanship `104127` moved from row 5 to row 4, which drops its clustering weight from `WEIGHT_MAJOR_NODE` (5.0) to `WEIGHT_UTILITY_NODE` (0.1). PvP talents: no removals among those the May cache had observed; `Dying Stars` (Balance Druid) confirmed removed pool-wide, matching patch notes.

---

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

- [x] **Automate `CURRENT_SEASON_ID` detection** — (RESOLVED 2026-08-18) `BnetClient.fetch_current_season_id()` reads `current_season.id` from `/data/wow/pvp-season/index` per request; the constant is renamed `FALLBACK_SEASON_ID` and used only when that lookup fails. Season 41 (Midnight Season 1) ended 2026-08-11 while Season 2 starts 2026-08-19, so the rollover would otherwise have served a frozen Season 1 ladder with no error. `fetch_leaderboard` now returns a `LeaderboardPage` carrying `season_id` and `is_fallback`: a season that has just started answers 200 with zero entries, so it falls back exactly one season and flags it, and `get_full_summary_tool` surfaces `season_id` / `season_fallback`. A contract test drives the real client through `fetch_top_players_async` — the existing mocks stubbed `fetch_leaderboard` wholesale and stayed green while production raised `TypeError` on `len()`.
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

## Season 42 collection pass (2026-08-20)

First full collection on the new season's ladder (season 42, opened ~2026-08-18).
Blizzard's `pvp-season/index` reported 42 and its 3v3 board was already populated
(4934→4988 entries), so nothing fell back to season 41 — every row is stamped
`season_id: 42, season_fallback: false`.

### Landed

- [x] **A single 5xx aborted a whole 50-player fetch** — `BnetClient._get` handled
      404/429/timeout but let 5xx through `raise_for_status()`. That exception
      propagates out of the `asyncio.gather` fanning out over the roster, so one
      flaky character profile threw away the entire spec's sample (it killed
      mistweaver-monk/zh_CN mid-run). 5xx now backs off and retries like 429, then
      gives up as `None` — callers already treat a missing profile as a skip.
      Non-404/429 4xx still raises, so a bad namespace or revoked token stays loud.

- [x] **Clustering degraded silently when the talent tree was unavailable** —
      `build_aggregation` gets node metadata (row, type, hero side) from
      `get_tree_structure`, which swallows every failure into `{"error": ...}`. The
      old code just skipped populating `node_meta` on error, leaving every talent
      with the same clustering weight — different build variants, no warning, cached
      as sound for the full 2h TTL. It happened for real: the cached
      restoration-shaman/solo-shuffle/en_US row held the unweighted `[33,12,4,1]`
      split where the weighted answer is `[37,12,1]`. Now logs a warning and stamps
      `clustering_degraded` on the aggregation. The bad row was repaired by
      rebuilding offline from the cached roster; all 29 healer rows re-verified.

- [x] **Page showed the minority hero tree** — (RESOLVED 2026-08-20) `_hero_core_nodes`
      in `tools/ui.py` picked the "dominant" hero tree by averaging pick rates over
      `core + flex + contested`. Hero talents are an all-or-nothing tree choice, so a
      split anywhere near even puts every hero node in the contested band (20-80%),
      which `MAX_DECISION_NODES` truncates — leaving an arbitrary remnant to average.
      On restoration-shaman 3v3 that remnant was 4 of 28 hero nodes and pointed at
      Farseer while 32 of 50 players ran Totemic. **17 of 80 (spec, bracket) pages
      named the minority tree**, including discipline-priest (Oracle 38 shown as
      Voidweaver 12) and restoration-druid (Keeper 39 shown as Wildstalker 11).

      Dominance now comes from cluster member counts, assigned by majority overlap
      rather than presence — a cluster whose members all run one tree can still list
      a stray node from the other (shadow-priest: 14 Voidweaver + 1 Archon), and
      counting presence would credit its players to both trees. Verified against the
      cache: all 40 specs now match the real member split.

      Clustering itself was never wrong — 622 clusters across 81 (spec, bracket)
      combinations each hold members of exactly one hero tree, so `_hero_partition`
      does enforce hero choice as the top-level split. This was display only.

### Open

- [ ] **A page names one hero tree when the field is genuinely split** — even
      corrected, the page presents a single hero tree and `strip_hero` removes hero
      nodes from every cluster, so restoration-shaman 3v3 reads as "Totemic" with no
      sign that 36% run Farseer. Preservation-evoker (28/22) and subtlety-rogue
      (27/23) are near coin flips. Since clusters already partition cleanly by hero
      tree, each cluster could name and render its own.

- [ ] **Hero nodes on the page carry pct 0** — `_hero_core_nodes` reads pct from
      `core/flex/contested`, which holds only the untruncated remnant, so most hero
      nodes render at 0%. Cluster takes carry the real per-cluster rate.

- [x] **`fetch_top_players` rescans the whole shared ladder per spec and per
      locale** — (RESOLVED 2026-08-20) — phase 1 only reads `class_id`/`spec_id` off each profile, so it is
      locale-independent, yet it runs once per (spec, locale). On a shared board
      (3v3/2v2/rbg) a rare spec scans all ~5000 entries to find 14 players, and does
      it twice. Measured: 14 of 66 planned 3v3 fetches took 56 minutes, projecting
      ~3.5h and ~250k API calls for the set; protection-paladin alone cost ~450s per
      locale. Scanning the ladder **once** and bucketing entries by spec gives
      identical sampling (still the highest-ranked 50 per spec) for ~12k calls and
      ~25 minutes. Fixed by extracting phase 1 into `_scan_ladder` (bucketing a
      single pass by spec) and adding `fetch_bracket()` / `python cli.py
      fetch-all`. `fetch_top_players` now runs on the same helpers with a
      one-spec target, so its behavior is unchanged. The locale half is fixed
      too: the scan runs once for all locales, and the only locale-dependent
      fields in a scanned profile (class and spec display names) are per-spec
      constants, so `fetch_spec_labels` relabels a roster with one static lookup
      instead of a profile fetch per player per locale. Measured after: 33 specs
      x 2 locales of 3v3 in 16.3 min (8 of it the single scan) vs ~3.5h.

      Does **not** close the Tier 2 locale item above — players and aggregations
      are still cached per locale, so phase 2 and the stored rows are still
      duplicated. This removes the expensive half.

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
