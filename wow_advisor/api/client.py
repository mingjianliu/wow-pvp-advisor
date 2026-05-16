import asyncio
import httpx
from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.models import LeaderboardEntry, CharacterData, TalentData, GearSlot

CURRENT_SEASON_ID = 40
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
        enchant_name = enchants[0].get("display_string") if enchants else None
        slots.append(GearSlot(
            slot=slot_type,
            item_id=item_data.get("id", 0),
            item_name=item_data.get("name", ""),
            ilvl=level,
            enchant_id=enchant_id,
            enchant_name=enchant_name,
        ))
    return slots


def _parse_talents(spec_data: dict, active_spec: str) -> TalentData | None:
    for spec in spec_data.get("specializations", []):
        if spec.get("specialization", {}).get("name") != active_spec:
            continue
        for loadout in spec.get("loadouts", []):
            if not loadout.get("is_active"):
                continue
            return TalentData(
                loadout_code=loadout.get("talent_loadout_code", ""),
                class_node_ids=[t["id"] for t in loadout.get("selected_class_talents", [])],
                spec_node_ids=[t["id"] for t in loadout.get("selected_spec_talents", [])],
                hero_node_ids=[t["id"] for t in loadout.get("selected_hero_talents", [])],
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
