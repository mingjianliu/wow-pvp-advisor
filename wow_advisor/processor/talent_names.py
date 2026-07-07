import asyncio
import json
import sqlite3
import threading
import time

from wow_advisor.api.client import BnetClient
from wow_advisor.normalize import normalize_spec, spec_to_ids

REVALIDATE_INTERVAL = 3600  # 1 hour


class TalentNameCache:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def resolve(self, spec: str, client: BnetClient, locale: str = "en_US") -> dict[int, dict]:
        """
        Returns {node_id: node_metadata} for the given spec.
        Returns {} if spec is unknown or Blizzard API is unavailable.
        """
        ids = spec_to_ids(normalize_spec(spec))
        if ids is None:
            return {}
        spec_id = ids[1]
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is None:
            try:
                return asyncio.run(self._resolve_async(spec, spec_id, client, locale=locale))
            except Exception:
                return {}
        # Called from within an async context (e.g. fastmcp) — run in a thread
        # so asyncio.run() can create its own event loop without conflict.
        result: dict[int, dict] = {}
        def _run() -> None:
            try:
                result.update(asyncio.run(self._resolve_async(spec, spec_id, client, locale=locale)))
            except Exception:
                pass
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join()
        return result

    async def _resolve_async(
        self, spec: str, spec_id: int, client: BnetClient, locale: str = "en_US"
    ) -> dict[int, dict]:
        row = self._conn.execute(
            "SELECT nodes_json, last_modified, checked_at FROM talent_node_cache WHERE spec=? AND locale=?",
            (spec, locale),
        ).fetchone()
        now = int(time.time())

        if row and now - row["checked_at"] < REVALIDATE_INTERVAL:
            return {int(k): v for k, v in json.loads(row["nodes_json"]).items()}

        if row:
            nodes, last_modified, was_modified = await self._fetch(
                spec_id, client, if_modified_since=row["last_modified"], locale=locale
            )
            if not was_modified:
                self._conn.execute(
                    "UPDATE talent_node_cache SET checked_at=? WHERE spec=? AND locale=?", (now, spec, locale)
                )
                self._conn.commit()
                return {int(k): v for k, v in json.loads(row["nodes_json"]).items()}
            self._save(spec, nodes, last_modified, now, locale=locale)
            return nodes

        nodes, last_modified, _ = await self._fetch(spec_id, client, locale=locale)
        self._save(spec, nodes, last_modified, now, locale=locale)
        return nodes

    async def _fetch(
        self,
        spec_id: int,
        client: BnetClient,
        if_modified_since: str | None = None,
        locale: str = "en_US",
    ) -> tuple[dict[int, dict], str | None, bool]:
        tree_id, _ = await client.fetch_talent_tree_id(spec_id, locale=locale)
        return await client.fetch_talent_nodes(tree_id, spec_id, if_modified_since=if_modified_since, locale=locale)

    def _save(
        self, spec: str, nodes: dict[int, dict], last_modified: str | None, now: int, locale: str = "en_US"
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO talent_node_cache (spec, locale, nodes_json, last_modified, checked_at)
               VALUES (?, ?, ?, ?, ?)""",
            (spec, locale, json.dumps({str(k): v for k, v in nodes.items()}), last_modified, now),
        )
        self._conn.commit()
