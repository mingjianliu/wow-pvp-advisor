import json
import time
import httpx
import asyncio
from wow_advisor.cache.db import get_default_db
from wow_advisor.settings import WOWHEAD_CONCURRENCY

# Wowhead locale IDs: 0 = en_US, 4 = zh_CN
_LOCALE_MAP = {
    "en_US": 0,
    "zh_CN": 4
}

def _get_tooltip_cached(type_str: str, entry_id: int, locale: str) -> dict | None:
    conn = get_default_db()
    locale_id = _LOCALE_MAP.get(locale, 0)
    # Long TTL for descriptions: 30 days (they rarely change)
    TTL = 30 * 24 * 3600
    now = int(time.time())
    
    row = conn.execute(
        "SELECT data_json, fetched_at FROM tooltips WHERE type=? AND id=? AND locale_id=?",
        (type_str, entry_id, locale_id)
    ).fetchone()
    
    if row:
        if now - row["fetched_at"] < TTL:
            return json.loads(row["data_json"])
    return None

def _save_tooltip(type_str: str, entry_id: int, locale: str, data: dict):
    conn = get_default_db()
    locale_id = _LOCALE_MAP.get(locale, 0)
    conn.execute(
        "INSERT OR REPLACE INTO tooltips (type, id, locale_id, data_json, fetched_at) VALUES (?, ?, ?, ?, ?)",
        (type_str, entry_id, locale_id, json.dumps(data), int(time.time()))
    )
    conn.commit()

async def fetch_tooltip(client: httpx.AsyncClient, type_str: str, entry_id: int, locale: str = "en_US") -> dict | None:
    cached = _get_tooltip_cached(type_str, entry_id, locale)
    if cached:
        return cached

    locale_id = _LOCALE_MAP.get(locale, 0)
    url = f"https://nether.wowhead.com/tooltip/{type_str}/{entry_id}?dataEnv=1&locale={locale_id}"
    
    try:
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            _save_tooltip(type_str, entry_id, locale, data)
            return data
    except Exception as e:
        print(f"Error fetching Wowhead tooltip for {type_str}/{entry_id}: {e}")
    
    return None

async def prefetch_tooltips(ids: list[int], type_str: str = "spell", locale: str = "en_US") -> dict[int, dict]:
    """Fetch multiple tooltips in parallel and return a map.

    Concurrency is bounded: Wowhead is a third-party site rather than an API with
    a published quota, and a full static refresh asks for a few thousand tooltips
    at once.
    """
    results = {}
    sem = asyncio.Semaphore(WOWHEAD_CONCURRENCY)

    async def bounded(client, eid):
        async with sem:
            return await fetch_tooltip(client, type_str, eid, locale)

    async with httpx.AsyncClient() as client:
        responses = await asyncio.gather(*[bounded(client, eid) for eid in ids])
        for eid, data in zip(ids, responses):
            if data:
                results[eid] = data
    return results
