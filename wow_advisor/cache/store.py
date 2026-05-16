import json
import sqlite3
import time
from wow_advisor.api.models import CharacterData, TalentData, GearSlot


class CacheStore:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_players(
        self, players: list[CharacterData], spec: str, bracket: str
    ) -> None:
        region = players[0].region if players else "us"
        self._conn.execute(
            "DELETE FROM players WHERE spec=? AND bracket=? AND region=?",
            (spec, bracket, region),
        )
        now = int(time.time())
        for p in players:
            cur = self._conn.execute(
                """INSERT INTO players
                   (name, realm, region, character_class, spec, bracket, rating, equipped_ilvl, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (p.name, p.realm, p.region, p.character_class, spec, bracket,
                 p.rating, p.equipped_ilvl, now),
            )
            pid = cur.lastrowid
            self._conn.execute(
                """INSERT INTO player_loadouts
                   (player_id, talent_code, class_node_ids, spec_node_ids, hero_node_ids, gear)
                   VALUES (?,?,?,?,?,?)""",
                (
                    pid,
                    p.talent.loadout_code if p.talent else None,
                    json.dumps(p.talent.class_node_ids if p.talent else []),
                    json.dumps(p.talent.spec_node_ids if p.talent else []),
                    json.dumps(p.talent.hero_node_ids if p.talent else []),
                    json.dumps([
                        {
                            "slot": g.slot,
                            "item_id": g.item_id,
                            "item_name": g.item_name,
                            "ilvl": g.ilvl,
                            "enchant_id": g.enchant_id,
                            "enchant_name": g.enchant_name,
                        }
                        for g in p.gear
                    ]),
                ),
            )
        self._conn.commit()

    def get_players(
        self, spec: str, bracket: str, region: str = "us"
    ) -> list[CharacterData]:
        rows = self._conn.execute(
            """SELECT p.name, p.realm, p.region, p.character_class, p.spec,
                      p.rating, p.equipped_ilvl,
                      l.talent_code, l.class_node_ids, l.spec_node_ids,
                      l.hero_node_ids, l.gear
               FROM players p
               LEFT JOIN player_loadouts l ON p.id = l.player_id
               WHERE p.spec=? AND p.bracket=? AND p.region=?
               ORDER BY p.rating DESC""",
            (spec, bracket, region),
        ).fetchall()
        result = []
        for r in rows:
            talent = None
            if r["talent_code"]:
                talent = TalentData(
                    loadout_code=r["talent_code"],
                    class_node_ids=json.loads(r["class_node_ids"] or "[]"),
                    spec_node_ids=json.loads(r["spec_node_ids"] or "[]"),
                    hero_node_ids=json.loads(r["hero_node_ids"] or "[]"),
                )
            gear_raw = json.loads(r["gear"] or "[]")
            gear = [GearSlot(**g) for g in gear_raw]
            result.append(CharacterData(
                name=r["name"],
                realm=r["realm"],
                region=r["region"],
                character_class=r["character_class"] or "",
                spec=r["spec"] or "",
                equipped_ilvl=r["equipped_ilvl"] or 0,
                rating=r["rating"] or 0,
                talent=talent,
                gear=gear,
            ))
        return result

    def save_aggregation(
        self, spec: str, bracket: str, region: str, data: dict
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO aggregations (spec, bracket, region, computed_at, data)
               VALUES (?,?,?,?,?)""",
            (spec, bracket, region, int(time.time()), json.dumps(data)),
        )
        self._conn.commit()

    def get_aggregation(
        self, spec: str, bracket: str, region: str
    ) -> dict | None:
        row = self._conn.execute(
            "SELECT data, computed_at FROM aggregations WHERE spec=? AND bracket=? AND region=?",
            (spec, bracket, region),
        ).fetchone()
        if not row:
            return None
        result = json.loads(row["data"])
        result["cached_at"] = row["computed_at"]
        return result

    def is_stale(
        self, spec: str, bracket: str, region: str, ttl_hours: int = 24
    ) -> bool:
        row = self._conn.execute(
            "SELECT computed_at FROM aggregations WHERE spec=? AND bracket=? AND region=?",
            (spec, bracket, region),
        ).fetchone()
        if not row:
            return True
        return time.time() - row["computed_at"] > ttl_hours * 3600
