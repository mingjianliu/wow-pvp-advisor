import asyncio
import os
import sys
import time

# Ensure we import from the worktree
sys.path.insert(0, "/Users/mingjianliu/code/wow-talent-gear-collector/.worktrees/cluster")

from wow_advisor.config import load_config
from wow_advisor.normalize import _SPEC_INFO_MAP
from wow_advisor.tools.fetch import fetch_top_players_async

async def fetch_spec(spec, sem):
    async with sem:
        print(f"[{time.strftime('%H:%M:%S')}] Starting fetch for {spec}...")
        try:
            start_time = time.time()
            result = await fetch_top_players_async(spec, "3v3", region="us", limit=50)
            elapsed = time.time() - start_time
            print(f"[{time.strftime('%H:%M:%S')}] Finished {spec} in {elapsed:.1f}s: {result}")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error fetching {spec}: {e}")

async def main():
    load_config()
    specs = sorted(list(_SPEC_INFO_MAP.keys()))
    print(f"Found {len(specs)} specs to fetch: {specs}")
    
    # Limit to 3 concurrent spec fetches to avoid API rate limit blocks
    sem = asyncio.Semaphore(3)
    tasks = [fetch_spec(spec, sem) for spec in specs]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
