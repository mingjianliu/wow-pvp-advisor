import asyncio
import re
import httpx
from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.models import LeaderboardEntry, CharacterData, TalentData, GearSlot

CURRENT_SEASON_ID = 41
_API_BASE = "https://{region}.api.blizzard.com"
_CONCURRENCY = 10


def _headers(token: str, namespace: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Battlenet-Namespace": namespace,
    }


def _parse_gear(equipped_items: list) -> list[GearSlot]:
    slots = []
    for item in equipped_items:
        slot_type = item.get("slot", {}).get("type", "").lower()
        item_data = item.get("item", {})
        level = item.get("level", {}).get("value", 0)
        enchants = item.get("enchantments", [])
        enchant_id = enchants[0].get("enchantment_id") if enchants else None
        raw_enchant = enchants[0].get("display_string", "") if enchants else ""
        # Strip Blizzard UI icon embedding syntax e.g. "|A:...|a"
        enchant_name = re.sub(r'\|A:[^|]+\|a', '', raw_enchant).strip() if raw_enchant else None
        slots.append(GearSlot(
            slot=slot_type,
            item_id=item_data.get("id", 0),
            item_name=item.get("name", ""),  # name is top-level, not inside item{}
            ilvl=level,
            enchant_id=enchant_id,
            enchant_name=enchant_name,
        ))
    return slots


def _parse_talents(spec_data: dict, active_spec: str) -> TalentData | None:
    for spec in spec_data.get("specializations", []):
        if spec.get("specialization", {}).get("name") != active_spec:
            continue
        # PvP talents live at the spec level, not inside the loadout
        pvp_ids, pvp_names = [], []
        for slot in spec.get("pvp_talent_slots", []):
            selected = slot.get("selected", {})
            talent = selected.get("talent", {})
            if talent.get("id"):
                pvp_ids.append(talent["id"])
                pvp_names.append(talent.get("name", ""))
        for loadout in spec.get("loadouts", []):
            if not loadout.get("is_active"):
                continue
            return TalentData(
                loadout_code=loadout.get("talent_loadout_code", ""),
                class_node_ids=[t["id"] for t in loadout.get("selected_class_talents", [])],
                spec_node_ids=[t["id"] for t in loadout.get("selected_spec_talents", [])],
                hero_node_ids=[t["id"] for t in loadout.get("selected_hero_talents", [])],
                pvp_talent_ids=pvp_ids,
                pvp_talent_names=pvp_names,
            )
    return None


class BnetClient:
    def __init__(self, auth: BnetAuth, region: str = "us"):
        self._auth = auth
        self._region = region
        self._base = _API_BASE.format(region=region)
        self._semaphore = asyncio.Semaphore(_CONCURRENCY)

    async def _get(self, client: httpx.AsyncClient, url: str, namespace: str) -> dict | None:
        token = await self._auth.get_token()
        for attempt in range(3):
            try:
                async with self._semaphore:
                    resp = await client.get(
                        url,
                        headers=_headers(token, namespace),
                        params={"locale": "en_US"},
                        timeout=10.0,
                    )
                if resp.status_code == 404:
                    return None
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                if attempt == 2:
                    return None
                await asyncio.sleep(1)
        return None

    async def _get_static(
        self, url: str, namespace: str, if_modified_since: str | None = None
    ) -> httpx.Response:
        """GET for static game data. Returns the raw Response (caller handles 304)."""
        token = await self._auth.get_token()
        headers = _headers(token, namespace)
        if if_modified_since:
            headers["If-Modified-Since"] = if_modified_since
        async with httpx.AsyncClient() as client:
            return await client.get(
                url,
                headers=headers,
                params={"locale": "en_US"},
                timeout=10.0,
            )

    async def fetch_talent_tree_id(self, spec_id: int) -> tuple[int, str | None]:
        """Returns (tree_id, last_modified) for the given spec_id."""
        url = f"{self._base}/data/wow/talent-tree/index"
        resp = await self._get_static(url, f"static-{self._region}")
        resp.raise_for_status()
        last_modified = resp.headers.get("Last-Modified")
        for entry in resp.json().get("spec_talent_trees", []):
            href = entry.get("key", {}).get("href", "")
            m = re.search(r"/talent-tree/(\d+)/playable-specialization/(\d+)", href)
            if m and int(m.group(2)) == spec_id:
                return int(m.group(1)), last_modified
        raise ValueError(f"spec_id {spec_id} not found in talent-tree index")

    async def fetch_talent_nodes(
        self,
        tree_id: int,
        spec_id: int,
        if_modified_since: str | None = None,
    ) -> tuple[dict[int, dict], str | None, bool]:
        """
        Returns (nodes, last_modified, was_modified).
        was_modified=False on 304 — caller skips cache write.
        nodes maps node_id → {name, row, col, type, max_rank, icon, children}.
        """
        url = f"{self._base}/data/wow/talent-tree/{tree_id}/playable-specialization/{spec_id}"
        resp = await self._get_static(url, f"static-{self._region}", if_modified_since=if_modified_since)
        if resp.status_code == 304:
            return {}, None, False
        resp.raise_for_status()
        last_modified = resp.headers.get("Last-Modified")
        data = resp.json()
        nodes: dict[int, dict] = {}
        for node in data.get("class_talent_nodes", []) + data.get("spec_talent_nodes", []):
            node_id = node["id"]
            ranks = node.get("ranks", [])
            name = None
            icon = None
            if ranks:
                tooltip = ranks[0].get("tooltip", {})
                name = tooltip.get("talent", {}).get("name")
                spell = tooltip.get("spell_tooltip", {}).get("spell", {})
                icon = str(spell["id"]) if spell.get("id") else None
            nodes[node_id] = {
                "name": name,
                "row": node.get("display_row"),
                "col": node.get("display_col"),
                "type": node.get("node_type", {}).get("type"),
                "max_rank": len(ranks),
                "icon": icon,
                "children": node.get("child_ids", []),
            }
        return nodes, last_modified, True

    async def fetch_leaderboard(
        self, bracket: str, season_id: int = CURRENT_SEASON_ID
    ) -> list[LeaderboardEntry]:
        url = f"{self._base}/data/wow/pvp-season/{season_id}/pvp-leaderboard/{bracket}"
        namespace = f"dynamic-{self._region}"
        async with httpx.AsyncClient() as client:
            data = await self._get(client, url, namespace)
        if data is None:
            return []
        entries = []
        for e in data.get("entries", []):
            char = e.get("character", {})
            entries.append(LeaderboardEntry(
                name=char.get("name", "").lower(),
                realm=char.get("realm", {}).get("slug", ""),
                rating=e.get("rating", 0),
                rank=e.get("rank", 0),
            ))
        return entries

    async def fetch_character_spec(
        self, client: httpx.AsyncClient, name: str, realm: str, rating: int
    ) -> CharacterData | None:
        """Cheap spec-only fetch: profile endpoint only (no talents/gear)."""
        namespace = f"profile-{self._region}"
        base_url = f"{self._base}/profile/wow/character/{realm}/{name.lower()}"
        profile = await self._get(client, base_url, namespace)
        if profile is None:
            return None
        return CharacterData(
            name=profile.get("name", name),
            realm=realm,
            region=self._region,
            character_class=profile.get("character_class", {}).get("name", ""),
            spec=profile.get("active_spec", {}).get("name", ""),
            equipped_ilvl=profile.get("equipped_item_level", 0),
            rating=rating,
        )

    async def fetch_character_details(
        self, name: str, realm: str, char: CharacterData
    ) -> CharacterData:
        """Fetch talents + gear for a character whose spec is already known."""
        namespace = f"profile-{self._region}"
        base_url = f"{self._base}/profile/wow/character/{realm}/{name.lower()}"
        async with httpx.AsyncClient() as client:
            spec_data, equip_data = await asyncio.gather(
                self._get(client, f"{base_url}/specializations", namespace),
                self._get(client, f"{base_url}/equipment", namespace),
            )
        char.talent = _parse_talents(spec_data or {}, char.spec) if spec_data else None
        char.gear = _parse_gear((equip_data or {}).get("equipped_items", []))
        return char

    async def fetch_character(
        self, name: str, realm: str, rating: int
    ) -> CharacterData | None:
        namespace = f"profile-{self._region}"
        base_url = f"{self._base}/profile/wow/character/{realm}/{name.lower()}"
        async with httpx.AsyncClient() as client:
            profile, spec_data, equip_data = await asyncio.gather(
                self._get(client, base_url, namespace),
                self._get(client, f"{base_url}/specializations", namespace),
                self._get(client, f"{base_url}/equipment", namespace),
            )
        if profile is None:
            return None
        active_spec = profile.get("active_spec", {}).get("name", "")
        talent = _parse_talents(spec_data or {}, active_spec) if spec_data else None
        gear = _parse_gear((equip_data or {}).get("equipped_items", []))
        return CharacterData(
            name=profile.get("name", name),
            realm=realm,
            region=self._region,
            character_class=profile.get("character_class", {}).get("name", ""),
            spec=active_spec,
            equipped_ilvl=profile.get("equipped_item_level", 0),
            rating=rating,
            talent=talent,
            gear=gear,
        )
