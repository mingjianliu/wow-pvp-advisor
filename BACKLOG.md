# Backlog

## Bugs

- [ ] **Talent node IDs are not human-readable** — the MCP tool returns raw numeric node IDs (e.g. `[81039, 81073]`). Claude has to interpret them without names. Consider adding a talent node name lookup via the Blizzard static API (`/data/wow/playable-specialization/{specId}`) and caching the mapping in SQLite.

- [ ] **Talent clusters are fragmented** — with threshold=1 in `summarize_talent_clusters`, builds differing by just 1 node are in separate clusters, producing many small groups (top cluster 8%). Consider tuning the threshold or implementing the keystone fallback for known specs.

- [ ] **`BNET_REGION` env var is documented but not wired** — `.env.example` lists it but `_make_client` in `tools/fetch.py` uses the `region` parameter passed by the caller (defaulting to `"us"`). Should fall back to `os.environ.get("BNET_REGION", "us")` so the env var actually does something.

- [ ] **`enchant_name` contains "Enchanted: " prefix** — display strings from the Blizzard API always start with "Enchanted: Enchant Slot - Name". Could strip to just "Name" for cleaner output.

## Missing Test Coverage

- [ ] `get_player_details` in `tools/gear.py` — no test. Should save players via `CacheStore`, then verify `get_player_details` returns correct talent code and gear.
- [ ] 429 retry behavior in `client._get` — the exponential backoff path has zero coverage. Add a `respx` test that returns two 429s then a 200.
- [ ] `fetch_character_spec` and `fetch_character_details` — the two new Phase 1/2 methods added in the two-phase fetch refactor have no unit tests.
- [ ] `_parse_gear` enchant markup stripping — should have a unit test for the `|A:...|a` regex.

## TODO

- [ ] **Season ID auto-detection** — `CURRENT_SEASON_ID = 41` is hardcoded in `client.py`. Should query `/data/wow/pvp-season/index` on startup and use `current_season.id` automatically, so it doesn't break at each new season.

- [ ] **Expose `scan_limit` via CLI and MCP** — currently hardcoded to scan the full leaderboard. For common specs (Warrior, Mage) you hit 50 players quickly; for rare specs you scan everything. A user-configurable limit would help.

- [ ] **Talent name lookup** — add `wow_advisor/processor/talent_names.py` that fetches from Blizzard's static API (`/data/wow/playable-specialization/{specId}`) and maps node IDs → names. Cache in `data/talent_names.json`. Makes the MCP output immediately readable.

- [ ] **arenacoach.gg regression comparison** — currently skipped (no public API). Check periodically if they expose one.

- [ ] **pvpq.net regression comparison** — currently skips (no Midnight data). Re-enable once they update to Midnight Season 1.

- [ ] **EU region support** — everything is wired for `region="eu"` but untested. Run a fetch against EU ladder to validate.

- [ ] **Solo Shuffle and 2v2 validation** — fetch at least one spec for each bracket to confirm the season ID and leaderboard parsing work for non-3v3 brackets.

- [ ] **keystone_talents.json for Resto Shaman** — add node IDs for the 3-4 genuinely defining talent choices to produce cleaner clusters. Requires knowing current Midnight S1 Resto Shaman talent tree.
