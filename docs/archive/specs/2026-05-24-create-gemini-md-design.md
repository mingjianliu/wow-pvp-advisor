# Design Spec: GEMINI.md for WoW PvP Advisor

Create a `GEMINI.md` file in the project root to provide foundational mandates, tool mappings, and engineering standards for Gemini CLI agents operating in this workspace.

## Goals
- Establish project-specific mandates (e.g., talent name resolution).
- Define tool mappings to align with Gemini CLI's toolset.
- Codify security and engineering standards.

## Foundational Mandates
- **Resolve Talent Names:** Agents must prioritize tools and workflows that resolve talent node IDs to human-readable names.
- **Primary Entry Point:** `get_full_summary_tool` should be treated as the primary tool for spec overviews.
- **Data Freshness:** Agents should be aware of cache TTLs (2 hours for full summaries, 24 hours for others) and use `fetch_top_players_tool` to force refreshes when necessary.

## Tool Mappings
| Abstract Tool | Gemini CLI Equivalent |
|---------------|----------------------|
| `Read`        | `read_file`          |
| `Write`       | `write_file`         |
| `Edit`        | `replace`            |
| `Bash`        | `run_shell_command`  |
| `Grep`        | `grep_search`        |
| `Glob`        | `glob`               |

## Engineering Standards
- **Clustering Context:** Builds are grouped using Agglomerative Hierarchical Clustering (HAC) with Weighted Jaccard Distance.
- **Static Metadata:** `data/keystone_talents.json` allows overriding automatic clustering.
- **Security:** Rigorously protect `.env` and Blizzard API credentials. Never include them in logs or commits.
- **Validation:** Always verify logic changes with existing tests in `tests/` and run the CLI for manual validation.

## Implementation Plan
1. Create `/Users/mingjianliu/code/wow-talent-gear-collector/GEMINI.md` with the defined content.
2. Verify the file content.
3. Commit the file.
