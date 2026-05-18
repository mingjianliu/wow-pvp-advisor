import asyncio
import json
import sqlite3
import threading
import time

from wow_advisor.api.client import BnetClient

SPEC_IDS: dict[str, int] = {
    "restoration shaman": 264,
    "elemental shaman": 262,
    "enhancement shaman": 263,
    "arms warrior": 71,
    "fury warrior": 72,
    "protection warrior": 73,
    "assassination rogue": 259,
    "outlaw rogue": 260,
    "subtlety rogue": 261,
    "arcane mage": 62,
    "fire mage": 63,
    "frost mage": 64,
    "balance druid": 102,
    "feral druid": 103,
    "guardian druid": 104,
    "restoration druid": 105,
    "holy paladin": 65,
    "protection paladin": 66,
    "retribution paladin": 70,
    "discipline priest": 256,
    "holy priest": 257,
    "shadow priest": 258,
    "beast mastery hunter": 253,
    "marksmanship hunter": 254,
    "survival hunter": 255,
    "affliction warlock": 265,
    "demonology warlock": 266,
    "destruction warlock": 267,
    "frost death knight": 251,
    "unholy death knight": 252,
    "blood death knight": 250,
    "windwalker monk": 269,
    "brewmaster monk": 268,
    "mistweaver monk": 270,
    "havoc demon hunter": 577,
    "vengeance demon hunter": 581,
    "devastation evoker": 1467,
    "preservation evoker": 1468,
    "augmentation evoker": 1473,
}

REVALIDATE_INTERVAL = 3600  # 1 hour


class TalentNameCache:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def resolve(self, spec: str, client: BnetClient) -> dict[int, dict]:
        """
        Returns {node_id: node_metadata} for the given spec.
        Returns {} if spec is unknown or Blizzard API is unavailable.
        """
        spec_id = SPEC_IDS.get(spec)
        if spec_id is None:
            return {}
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is None:
            try:
                return asyncio.run(self._resolve_async(spec, spec_id, client))
            except Exception:
                return {}
        # Called from within an async context (e.g. fastmcp) — run in a thread
        # so asyncio.run() can create its own event loop without conflict.
        result: dict[int, dict] = {}
        def _run() -> None:
            try:
                result.update(asyncio.run(self._resolve_async(spec, spec_id, client)))
            except Exception:
                pass
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join()
        return result

    async def _resolve_async(
        self, spec: str, spec_id: int, client: BnetClient
    ) -> dict[int, dict]:
        row = self._conn.execute(
            "SELECT nodes_json, last_modified, checked_at FROM talent_node_cache WHERE spec=?",
            (spec,),
        ).fetchone()
        now = int(time.time())

        if row and now - row["checked_at"] < REVALIDATE_INTERVAL:
            return {int(k): v for k, v in json.loads(row["nodes_json"]).items()}

        if row:
            nodes, last_modified, was_modified = await self._fetch(
                spec_id, client, if_modified_since=row["last_modified"]
            )
            if not was_modified:
                self._conn.execute(
                    "UPDATE talent_node_cache SET checked_at=? WHERE spec=?", (now, spec)
                )
                self._conn.commit()
                return {int(k): v for k, v in json.loads(row["nodes_json"]).items()}
            self._save(spec, nodes, last_modified, now)
            return nodes

        nodes, last_modified, _ = await self._fetch(spec_id, client)
        self._save(spec, nodes, last_modified, now)
        return nodes

    async def _fetch(
        self,
        spec_id: int,
        client: BnetClient,
        if_modified_since: str | None = None,
    ) -> tuple[dict[int, dict], str | None, bool]:
        tree_id, _ = await client.fetch_talent_tree_id(spec_id)
        return await client.fetch_talent_nodes(tree_id, spec_id, if_modified_since=if_modified_since)

    def _save(
        self, spec: str, nodes: dict[int, dict], last_modified: str | None, now: int
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO talent_node_cache (spec, nodes_json, last_modified, checked_at)
               VALUES (?, ?, ?, ?)""",
            (spec, json.dumps({str(k): v for k, v in nodes.items()}), last_modified, now),
        )
        self._conn.commit()
