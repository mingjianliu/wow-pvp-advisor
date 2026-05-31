# Design Spec: Healer Talent Pick Pages

Build and serve talent pick overview pages for all World of Warcraft healer specifications in the Solo Shuffle bracket.

## Healer Specifications
- Restoration Shaman
- Restoration Druid
- Holy Paladin
- Discipline Priest
- Holy Priest
- Mistweaver Monk
- Preservation Evoker

## Configuration
- **Bracket:** Solo Shuffle
- **Region:** us (default)
- **Primary Tool:** `mcp-wow-pvp-advisor` tools (`get_full_summary_tool`, `build_page_tool`)
- **Server:** `serve.py` (hosting `frontend/` on port 8080)

## Workflow
1. **Bulk Processing:** Iteratively call `build_page_tool` for each healer spec. This tool internally handles:
   - Fetching top players from Blizzard API.
   - Clustering talent builds using Weighted HAC.
   - Parsing talent tree structures.
   - Generating a standalone HTML page in `frontend/pages/`.
2. **Server Startup:** Launch the local Python server (`serve.py`) in the background.
3. **Validation:** Verify the existence of generated HTML files and the reachability of the local server.

## Success Criteria
- Standalone HTML files created for all 7 healer specs.
- Local server running and serving the `frontend/` directory.
- All generated pages are viewable via the local server.
