# WoW PvP Advisor — Agent Instructions

Instructions for any AI agent (Claude Code, Antigravity, Codex, etc.) working in this repo.

## Foundational Mandates

- **Resolve Talent Names:** Always prioritize tools and workflows that resolve talent node IDs to human-readable names. Use `get_full_summary_tool` instead of `get_talent_distribution_tool` when possible.
- **Primary Entry Point:** Treat `get_full_summary_tool` as the primary tool for spec overviews.
- **Data Freshness:** Be aware of cache TTLs (2 hours for full summaries, 24 hours for others). Use `fetch_top_players_tool` to force refreshes if data seems stale or if the user requests a refresh.
- **Security:** Rigorously protect `.env` and Blizzard API credentials. Never include them in logs or commits.

## Engineering Standards

- **Clustering Context:** Builds are grouped using Agglomerative Hierarchical Clustering (HAC) with Weighted Jaccard Distance.
- **Static Metadata:** `data/keystone_talents.json` allows overriding automatic clustering by specifying important node IDs.
- **Verification:** Always verify logic changes with existing tests in `tests/` and run the CLI for manual validation.
- **Documentation:** Tool docstrings in `mcp_server.py` are the canonical reference for purpose and parameters — keep them accurate, MCP clients read them. `docs/mcp-tools.md` only holds what docstrings can't: output schemas, internal mechanics, known limitations, and future work. Update it when those change.
