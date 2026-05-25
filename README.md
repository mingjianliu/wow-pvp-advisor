# WoW PvP Advisor

Fetches top-50 WoW PvP player data (talents, gear, enchants) and exposes it as an MCP server for AI agents (Claude Code, Gemini CLI, Antigravity, etc.).

## Setup

### 1. Get a Blizzard API key

Go to https://develop.battle.net/access/clients → Create Client → copy Client ID and Secret.

### 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env: add your BNET_CLIENT_ID and BNET_CLIENT_SECRET
```

## MCP Registration

### Claude Code
Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "wow-advisor": {
      "command": "/Users/mingjianliu/code/wow-talent-gear-collector/.venv/bin/python",
      "args": [
        "/Users/mingjianliu/code/wow-talent-gear-collector/mcp_server.py"
      ]
    }
  }
}
```

### Gemini CLI
Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "wow-advisor": {
      "command": "/Users/mingjianliu/code/wow-talent-gear-collector/.venv/bin/python",
      "args": [
        "/Users/mingjianliu/code/wow-talent-gear-collector/mcp_server.py"
      ]
    }
  }
}
```

### Antigravity CLI
Antigravity automatically detects MCP servers if the project is open. Ensure your project is added to Antigravity.

---

Replace `/Users/mingjianliu/code/wow-talent-gear-collector` with your project path if different. Find it with `pwd` inside the project directory.

The `.env` file is loaded by `mcp_server.py` at startup — no need to pass env vars in settings.

### 4. Test manually first

```bash
python cli.py summary "resto shaman" 3v3  # All-in-one report (recommended)
python cli.py fetch "resto shaman" 3v3    # Force a refresh
python cli.py talents "resto shaman" 3v3  # Just talents
python cli.py gear "resto shaman" 3v3     # Just gear
```

### 5. Usage

Once the MCP server is registered, you can use it with any compatible agent (Claude Code, Gemini CLI, etc.).

**Example questions:**
- **"Give me a full summary for Restoration Shaman in 3v3"** (Uses `get_full_summary_tool` for a complete picture)
- "What talents should I run as Restoration Shaman in 3v3?"
- "What trinkets are top Resto Shamans using?"
- "What's the most common gear setup for arms warriors in 3v3?"

## Talent clustering

Top player builds are clustered automatically using **Agglomerative Hierarchical Clustering (HAC)** with Weighted Jaccard Distance. This accounts for both *which* talents are taken and *how many points* are spent in each.

- **Core talents** (≥80% pick rate): everyone takes these — not a decision point
- **Contested talents** (20-80%): these define the build variants
- **Flex talents** (≤20%): rarely taken

The `data/keystone_talents.json` file lets you override the automatic clustering for a specific spec by listing the node IDs that matter most.

## Extending

- **New brackets** (2v2, Solo Shuffle): just pass `bracket="solo shuffle"` or `bracket="2v2"` — no code changes
- **EU region**: add `region="eu"` to any tool call
- **Season update**: change `CURRENT_SEASON_ID` in `wow_advisor/api/client.py`
