# GEMINI.md Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `GEMINI.md` file in the project root to guide Gemini CLI agents.

**Architecture:** A markdown file containing mandates, tool mappings, and engineering standards.

**Tech Stack:** Markdown.

---

### Task 1: Create GEMINI.md

**Files:**
- Create: `/Users/mingjianliu/code/wow-talent-gear-collector/GEMINI.md`

- [x] **Step 1: Write the GEMINI.md file**

```markdown
# WoW PvP Advisor - Gemini Mandates

This file provides foundational mandates, tool mappings, and engineering standards for Gemini CLI agents operating in this workspace.

## Foundational Mandates

- **Resolve Talent Names:** Always prioritize tools and workflows that resolve talent node IDs to human-readable names. Use `get_full_summary_tool` instead of `get_talent_distribution_tool` when possible.
- **Primary Entry Point:** Treat `get_full_summary_tool` as the primary tool for spec overviews.
- **Data Freshness:** Be aware of cache TTLs (2 hours for full summaries, 24 hours for others). Use `fetch_top_players_tool` to force refreshes if data seems stale or if the user requests a refresh.
- **Security:** Rigorously protect `.env` and Blizzard API credentials. Never include them in logs or commits.

## Tool Mappings

These mappings align abstract tool names used in project documentation with Gemini CLI's specific tools.

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
- **Static Metadata:** `data/keystone_talents.json` allows overriding automatic clustering by specifying important node IDs.
- **Verification:** Always verify logic changes with existing tests in `tests/` and run the CLI for manual validation.
- **Documentation:** Keep `docs/mcp-tools.md` updated with any changes to the MCP server tools.
```

- [x] **Step 2: Verify the file content**

Run: `cat /Users/mingjianliu/code/wow-talent-gear-collector/GEMINI.md`
Expected: The content matches what was written.

- [x] **Step 3: Commit the change**

```bash
git add /Users/mingjianliu/code/wow-talent-gear-collector/GEMINI.md
git commit -m "docs: add GEMINI.md with agent mandates and tool mappings"
```
