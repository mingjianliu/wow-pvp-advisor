import asyncio
import re
import httpx
from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.models import LeaderboardEntry, LeaderboardPage, CharacterData, TalentData, GearSlot
from wow_advisor.settings import FALLBACK_SEASON_ID, API_CONCURRENCY

_API_BASE = "https://{region}.api.blizzard.com"


def _game_build_from_namespace(namespace: str | None) -> str | None:
    """'static-12.1.0_68914-us' -> '12.1.0_68914'.

    Region is stripped so a build captured in one region compares equal to the
    same build in another.
    """
    if not namespace:
        return None
    m = re.match(r"^static-(.+)-[a-z]{2}$", namespace)
    return m.group(1) if m else None


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


def _parse_talents(spec_data: dict, spec_id: int, spec_name: str | None = None) -> TalentData | None:
    for spec in spec_data.get("specializations", []):
        s_info = spec.get("specialization", {})
        matched = False
        if s_info.get("id") and spec_id and s_info.get("id") == spec_id:
            matched = True
        elif s_info.get("name") and spec_name and s_info.get("name").lower() == spec_name.lower():
            matched = True

        if not matched:
            continue
        # PvP talents live at the spec level, not inside the loadout
        pvp_ids, pvp_names = [], []
        for slot in spec.get("pvp_talent_slots", []):
            selected = slot.get("selected", {})
            talent = selected.get("talent", {})
            # Spell ID is inside spell_tooltip.spell.id
            spell_tooltip = selected.get("spell_tooltip", {})
            spell = spell_tooltip.get("spell", {})
            tid = spell.get("id") or talent.get("id")
            if tid:
                pvp_ids.append(tid)
                pvp_names.append(talent.get("name", ""))
        for loadout in spec.get("loadouts", []):
            if not loadout.get("is_active"):
                continue
            
            node_ranks = {}
            def add_ranks(talents):
                for t in talents:
                    node_ranks[t["id"]] = node_ranks.get(t["id"], 0) + t.get("rank", 1)

            add_ranks(loadout.get("selected_class_talents", []))
            add_ranks(loadout.get("selected_spec_talents", []))
            add_ranks(loadout.get("selected_hero_talents", []))

            return TalentData(
                loadout_code=loadout.get("talent_loadout_code", ""),
                class_node_ids=sorted({t["id"] for t in loadout.get("selected_class_talents", [])}),
                spec_node_ids=sorted({t["id"] for t in loadout.get("selected_spec_talents", [])}),
                hero_node_ids=sorted({t["id"] for t in loadout.get("selected_hero_talents", [])}),
                pvp_talent_ids=pvp_ids,
                pvp_talent_names=pvp_names,
                node_ranks=node_ranks,
            )
    return None


class BnetClient:
    def __init__(self, auth: BnetAuth, region: str = "us"):
        self._auth = auth
        self._region = region
        self._base = _API_BASE.format(region=region)
        self._semaphore = asyncio.Semaphore(API_CONCURRENCY)

    async def _get(self, client: httpx.AsyncClient, url: str, namespace: str, locale: str = "en_US") -> dict | None:
        token = await self._auth.get_token()
        for attempt in range(3):
            try:
                async with self._semaphore:
                    resp = await client.get(
                        url,
                        headers=_headers(token, namespace),
                        params={"locale": locale},
                        timeout=10.0,
                    )
                if resp.status_code == 404:
                    return None
                # 429 and 5xx are transient. Raising here would propagate out of
                # the asyncio.gather that fans out over a whole roster, so one
                # flaky character profile sank an entire 50-player spec fetch.
                # Back off instead, and give up as None — callers already treat
                # a missing profile as a player to skip.
                if resp.status_code == 429 or resp.status_code >= 500:
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
        self, url: str, namespace: str, if_modified_since: str | None = None, locale: str = "en_US"
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
                params={"locale": locale},
                timeout=10.0,
            )

    async def fetch_talent_tree_id(self, spec_id: int, locale: str = "en_US") -> tuple[int, str | None]:
        """Returns (tree_id, last_modified) for the given spec_id."""
        url = f"{self._base}/data/wow/talent-tree/index"
        resp = await self._get_static(url, f"static-{self._region}", locale=locale)
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
        locale: str = "en_US",
    ) -> tuple[dict[int, dict], str | None, bool, str | None]:
        """
        Returns (nodes, last_modified, was_modified, game_build).
        was_modified=False on 304 — caller skips cache write.
        nodes maps node_id → {name, row, col, type, max_rank, icon, choices, children}.
        game_build stamps which client build the node IDs belong to; Blizzard
        reassigns talents across node IDs between builds, so cached data keyed by
        node ID is only interpretable against the build it was captured under.
        """
        url = f"{self._base}/data/wow/talent-tree/{tree_id}/playable-specialization/{spec_id}"
        resp = await self._get_static(url, f"static-{self._region}", if_modified_since=if_modified_since, locale=locale)
        game_build = _game_build_from_namespace(resp.headers.get("Battlenet-Namespace"))
        if resp.status_code == 304:
            return {}, None, False, game_build
        resp.raise_for_status()
        last_modified = resp.headers.get("Last-Modified")
        data = resp.json()
        nodes: dict[int, dict] = {}
        for node in data.get("class_talent_nodes", []) + data.get("spec_talent_nodes", []):
            node_id = node["id"]
            ranks = node.get("ranks", [])
            name = None
            icon = None
            choices: list[str] = []
            if ranks:
                first = ranks[0]
                tooltip = first.get("tooltip", {})
                name = tooltip.get("talent", {}).get("name")
                spell = tooltip.get("spell_tooltip", {}).get("spell", {})
                icon = str(spell["id"]) if spell.get("id") else None
                # Choice ("diamond") nodes have no ranks[].tooltip at all — both
                # options live in choice_of_tooltips, which sits either on the
                # rank itself or nested inside tooltip. Without this branch every
                # choice node resolved to name=None, and callers that filter on a
                # present name dropped the highest-weight nodes in the tree.
                cot = first.get("choice_of_tooltips") or tooltip.get("choice_of_tooltips") or []
                choices = [c.get("talent", {}).get("name") for c in cot]
                choices = [c for c in choices if c]
                if choices:
                    name = " / ".join(choices)
                    first_spell = cot[0].get("spell_tooltip", {}).get("spell", {})
                    if first_spell.get("id"):
                        icon = str(first_spell["id"])
            nodes[node_id] = {
                "name": name,
                "row": node.get("display_row"),
                "col": node.get("display_col"),
                "type": node.get("node_type", {}).get("type"),
                "max_rank": len(ranks),
                "icon": icon,
                "choices": choices,
                "children": node.get("child_ids", []),
            }
        return nodes, last_modified, True, game_build

    async def fetch_pvp_talents(
        self, spec_id: int, locale: str = "en_US"
    ) -> tuple[list[dict], str | None]:
        """Full PvP talent pool available to a spec, as [{"id", "name"}] by id.

        Returns (talents, game_build). This is the whole pool, not the subset
        players happened to pick, so it can serve as a baseline for diffing a
        later patch.
        """
        url = f"{self._base}/data/wow/playable-specialization/{spec_id}"
        resp = await self._get_static(url, f"static-{self._region}", locale=locale)
        resp.raise_for_status()
        game_build = _game_build_from_namespace(resp.headers.get("Battlenet-Namespace"))
        talents = []
        for entry in resp.json().get("pvp_talents", []):
            talent = entry.get("talent", {})
            if talent.get("id") and talent.get("name"):
                talents.append({"id": talent["id"], "name": talent["name"]})
        return sorted(talents, key=lambda t: t["id"]), game_build

    async def fetch_spec_labels(
        self, spec_id: int, locale: str = "en_US"
    ) -> tuple[str, str] | None:
        """Localized (class name, spec name) for a spec, or None if unavailable.

        These two strings are per-spec constants, not per-character data. They
        reach the UI via CharacterData, which otherwise only gets them from a
        character profile — so localizing a roster used to mean re-fetching every
        profile in the target locale just to read the same two strings back.
        """
        url = f"{self._base}/data/wow/playable-specialization/{spec_id}"
        try:
            resp = await self._get_static(url, f"static-{self._region}", locale=locale)
            resp.raise_for_status()
        except httpx.HTTPError:
            return None
        data = resp.json()
        class_name = (data.get("playable_class") or {}).get("name")
        spec_name = data.get("name")
        if not class_name or not spec_name:
            return None
        return class_name, spec_name

    async def fetch_current_season_id(self) -> int | None:
        """Current PvP season per Blizzard, or None if the lookup fails."""
        url = f"{self._base}/data/wow/pvp-season/index"
        try:
            async with httpx.AsyncClient() as client:
                data = await self._get(client, url, f"dynamic-{self._region}")
        except httpx.HTTPError:
            # Detection is best-effort: the caller falls back to the configured
            # season rather than failing the whole fetch.
            return None
        if not data:
            return None
        return data.get("current_season", {}).get("id")

    async def _fetch_leaderboard_entries(self, bracket: str, season_id: int) -> list[LeaderboardEntry]:
        url = f"{self._base}/data/wow/pvp-season/{season_id}/pvp-leaderboard/{bracket}"
        async with httpx.AsyncClient() as client:
            data = await self._get(client, url, f"dynamic-{self._region}")
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

    async def fetch_leaderboard(
        self, bracket: str, season_id: int | None = None
    ) -> LeaderboardPage:
        """Leaderboard for a bracket, defaulting to the season Blizzard reports as current.

        A season that has just started has no ranked ladder yet — the endpoint
        answers 200 with zero entries. Rather than report "no data" for every
        spec until placements finish, fall back one season and flag it, so the
        caller can say which ladder the sample actually came from.
        """
        explicit = season_id is not None
        if not explicit:
            season_id = await self.fetch_current_season_id() or FALLBACK_SEASON_ID

        entries = await self._fetch_leaderboard_entries(bracket, season_id)
        if entries or explicit or season_id <= 1:
            return LeaderboardPage(entries=entries, season_id=season_id)

        previous = season_id - 1
        entries = await self._fetch_leaderboard_entries(bracket, previous)
        if not entries:
            return LeaderboardPage(entries=[], season_id=season_id)
        return LeaderboardPage(entries=entries, season_id=previous, is_fallback=True)

    async def fetch_character_spec(
        self, client: httpx.AsyncClient, name: str, realm: str, rating: int, locale: str = "en_US"
    ) -> CharacterData | None:
        """Cheap spec-only fetch: profile endpoint only (no talents/gear)."""
        namespace = f"profile-{self._region}"
        base_url = f"{self._base}/profile/wow/character/{realm}/{name.lower()}"
        profile = await self._get(client, base_url, namespace, locale=locale)
        if profile is None:
            return None
        return CharacterData(
            name=profile.get("name", name),
            realm=realm,
            region=self._region,
            character_class=profile.get("character_class", {}).get("name", ""),
            spec=profile.get("active_spec", {}).get("name", ""),
            class_id=profile.get("character_class", {}).get("id", 0),
            spec_id=profile.get("active_spec", {}).get("id", 0),
            equipped_ilvl=profile.get("equipped_item_level", 0),
            rating=rating,
        )

    async def fetch_character_details(
        self, name: str, realm: str, char: CharacterData, locale: str = "en_US"
    ) -> CharacterData:
        """Fetch talents + gear for a character whose spec is already known."""
        namespace = f"profile-{self._region}"
        base_url = f"{self._base}/profile/wow/character/{realm}/{name.lower()}"
        async with httpx.AsyncClient() as client:
            spec_data, equip_data = await asyncio.gather(
                self._get(client, f"{base_url}/specializations", namespace, locale=locale),
                self._get(client, f"{base_url}/equipment", namespace, locale=locale),
            )
        char.talent = _parse_talents(spec_data or {}, char.spec_id, char.spec) if spec_data else None
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
        active_spec_id = profile.get("active_spec", {}).get("id", 0)
        talent = _parse_talents(spec_data or {}, active_spec_id, active_spec) if spec_data else None
        gear = _parse_gear((equip_data or {}).get("equipped_items", []))
        return CharacterData(
            name=profile.get("name", name),
            realm=realm,
            region=self._region,
            character_class=profile.get("character_class", {}).get("name", ""),
            spec=active_spec,
            class_id=profile.get("character_class", {}).get("id", 0),
            spec_id=active_spec_id,
            equipped_ilvl=profile.get("equipped_item_level", 0),
            rating=rating,
            talent=talent,
            gear=gear,
        )
