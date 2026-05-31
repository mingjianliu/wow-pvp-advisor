import asyncio
import os
import sys
import time

# Ensure we import from the local project root
sys.path.append(os.getcwd())

from wow_advisor.tools.fetch import fetch_top_players_async

HEALERS = [
    "restoration-shaman",
    "restoration-druid",
    "holy-priest",
    "discipline-priest",
    "holy-paladin",
    "mistweaver-monk",
    "preservation-evoker"
]

async def fetch_spec(spec, sem):
    async with sem:
        print(f"[{time.strftime('%H:%M:%S')}] Starting fetch for {spec}...")
        try:
            start_time = time.time()
            # Fetch for 3v3 and Solo Shuffle (common brackets)
            for bracket in ["3v3", "solo-shuffle"]:
                print(f"  Fetching {bracket}...")
                await fetch_top_players_async(spec, bracket, region="us", limit=50)
            elapsed = time.time() - start_time
            print(f"[{time.strftime('%H:%M:%S')}] Finished {spec} in {elapsed:.1f}s")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error fetching {spec}: {e}")

async def main():
    print(f"Initiating background fetch for {len(HEALERS)} healer specs...")
    
    # Limit to 2 concurrent spec fetches to be gentle on the API
    sem = asyncio.Semaphore(2)
    tasks = [fetch_spec(spec, sem) for spec in HEALERS]
    await asyncio.gather(*tasks)
    print("All healer fetches completed.")

if __name__ == "__main__":
    asyncio.run(main())
