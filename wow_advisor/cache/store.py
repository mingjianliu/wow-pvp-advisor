import json
import sqlite3
import time
from wow_advisor.api.models import CharacterData, TalentData, GearSlot


class CacheStore:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def save_players(
        self, players: list[CharacterData], spec: str, bracket: str, locale: str = "en_US"
    ) -> None:
        if not players:
            return
        region = players[0].region if players else "us"
        self._conn.execute(
            "DELETE FROM players WHERE spec=? AND bracket=? AND region=? AND locale=?",
            (spec, bracket, region, locale),
        )
        now = int(time.time())
        for p in players:
            cur = self._conn.execute(
                """INSERT INTO players
                   (name, realm, region, locale, character_class, spec, bracket, rating, equipped_ilvl, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (p.name, p.realm, p.region, locale, p.character_class, spec, bracket,
                 p.rating, p.equipped_ilvl, now),
            )
            pid = cur.lastrowid
            self._conn.execute(
                """INSERT INTO player_loadouts
                   (player_id, talent_code, class_node_ids, spec_node_ids, hero_node_ids, node_ranks, pvp_talent_ids, pvp_talent_names, gear)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    pid,
                    p.talent.loadout_code if p.talent else None,
                    json.dumps(p.talent.class_node_ids if p.talent else []),
                    json.dumps(p.talent.spec_node_ids if p.talent else []),
                    json.dumps(p.talent.hero_node_ids if p.talent else []),
                    json.dumps({str(k): v for k, v in p.talent.node_ranks.items()} if p.talent else {}),
                    json.dumps(p.talent.pvp_talent_ids if p.talent else []),
                    json.dumps(p.talent.pvp_talent_names if p.talent else []),
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
        self, spec: str, bracket: str, region: str = "us", locale: str = "en_US"
    ) -> list[CharacterData]:
        rows = self._conn.execute(
            """SELECT p.name, p.realm, p.region, p.character_class, p.spec,
                      p.rating, p.equipped_ilvl,
                      l.talent_code, l.class_node_ids, l.spec_node_ids,
                      l.hero_node_ids, l.node_ranks, l.pvp_talent_ids, l.pvp_talent_names, l.gear
               FROM players p
               LEFT JOIN player_loadouts l ON p.id = l.player_id
               WHERE p.spec=? AND p.bracket=? AND p.region=? AND p.locale=?
               ORDER BY p.rating DESC""",
            (spec, bracket, region, locale),
        ).fetchall()
        result = []
        for r in rows:
            talent = None
            if r["talent_code"]:
                node_ranks_raw = json.loads(r["node_ranks"] or "{}")
                talent = TalentData(
                    loadout_code=r["talent_code"],
                    class_node_ids=json.loads(r["class_node_ids"] or "[]"),
                    spec_node_ids=json.loads(r["spec_node_ids"] or "[]"),
                    hero_node_ids=json.loads(r["hero_node_ids"] or "[]"),
                    node_ranks={int(k): v for k, v in node_ranks_raw.items()},
                    pvp_talent_ids=json.loads(r["pvp_talent_ids"] or "[]"),
                    pvp_talent_names=json.loads(r["pvp_talent_names"] or "[]"),
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
        self, spec: str, bracket: str, region: str, data: dict, locale: str = "en_US"
    ) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO aggregations (spec, bracket, region, locale, computed_at, data)
               VALUES (?,?,?,?,?,?)""",
            (spec, bracket, region, locale, int(time.time()), json.dumps(data)),
        )
        self._conn.commit()

    def get_aggregation(
        self, spec: str, bracket: str, region: str, locale: str = "en_US"
    ) -> dict | None:
        row = self._conn.execute(
            "SELECT data, computed_at FROM aggregations WHERE spec=? AND bracket=? AND region=? AND locale=?",
            (spec, bracket, region, locale),
        ).fetchone()
        if not row:
            return None
        result = json.loads(row["data"])
        result["cached_at"] = row["computed_at"]
        return result

    def is_stale(
        self, spec: str, bracket: str, region: str, ttl_hours: int = 24, locale: str = "en_US"
    ) -> bool:
        row = self._conn.execute(
            "SELECT computed_at FROM aggregations WHERE spec=? AND bracket=? AND region=? AND locale=?",
            (spec, bracket, region, locale),
        ).fetchone()
        if not row:
            return True
        return time.time() - row["computed_at"] > ttl_hours * 3600
