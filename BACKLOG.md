# Backlog

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
- [ ] **Stat priority display on web UI** — we already compute `get_stat_distribution` in MCP. Add a visual bar chart component to the frontend showing secondary stat weights (Vers/Haste/Crit/Mastery).
- [ ] **Meta / Tier List landing page** — we have `get_pvp_tier_list_tool` and `get_meta_snapshot_tool` in MCP but no frontend page. Build a landing page showing all specs ranked by representation/rating per bracket. Makes the app a destination, not just a per-spec tool.
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
