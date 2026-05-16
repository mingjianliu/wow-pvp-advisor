# WoW PvP Advisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server that fetches top-50 WoW PvP player data (talents, gear, enchants) via the Blizzard API, clusters builds intelligently, and exposes the data as Claude-queryable tools.

**Architecture:** Blizzard OAuth2 client credentials → async httpx fetches leaderboard + per-character data → SQLite cache with 24h TTL → talent clustering via variance analysis + Hamming distance → fastmcp MCP server with 4 tools.

**Tech Stack:** Python 3.11+, httpx (async HTTP), fastmcp (MCP), sqlite3 (stdlib), python-dotenv, pytest + respx (tests)

---

## File Map

| File                                  | Responsibility                                                      |
| ------------------------------------- | ------------------------------------------------------------------- |
| `pyproject.toml`                      | Project metadata + deps                                             |
| `.env.example`                        | API key template                                                    |
| `.gitignore`                          | Ignore .env, data/\*.db, .venv/                                     |
| `mcp_server.py`                       | fastmcp entry point, registers 4 tools                              |
| `cli.py`                              | Manual `python cli.py fetch resto-shaman 3v3`                       |
| `wow_advisor/normalize.py`            | Spec/bracket string normalization + class mapping                   |
| `wow_advisor/api/models.py`           | Dataclasses: LeaderboardEntry, CharacterData, GearSlot, TalentData  |
| `wow_advisor/api/auth.py`             | BnetAuth: OAuth2 token + auto-refresh                               |
| `wow_advisor/api/client.py`           | BnetClient: async httpx, semaphore, retry                           |
| `wow_advisor/cache/db.py`             | SQLite schema init                                                  |
| `wow_advisor/cache/store.py`          | CacheStore: read/write players, loadouts, aggregations, TTL         |
| `wow_advisor/processor/talents.py`    | TalentAnalysis, analyze_talents, cluster_talents, summarize         |
| `wow_advisor/processor/gear.py`       | per-slot item + enchant frequency tables                            |
| `wow_advisor/processor/aggregator.py` | Orchestrate talent + gear into final aggregation JSON               |
| `wow_advisor/tools/fetch.py`          | fetch_top_players: leaderboard → filter by spec → cache → aggregate |
| `wow_advisor/tools/talents.py`        | get_talent_distribution: cache lookup with TTL auto-refresh         |
| `wow_advisor/tools/gear.py`           | get_gear_summary + get_player_details: cache lookups                |
| `data/keystone_talents.json`          | Per-spec keystone overrides for fallback C (starts as `{}`)         |
| `tests/conftest.py`                   | tmp_db fixture                                                      |
| `tests/test_normalize.py`             |                                                                     |
| `tests/test_auth.py`                  |                                                                     |
| `tests/test_client.py`                |                                                                     |
| `tests/test_store.py`                 |                                                                     |
| `tests/test_talents.py`               |                                                                     |
| `tests/test_gear.py`                  |                                                                     |
| `tests/test_aggregator.py`            |                                                                     |

---

## Task 1: Project scaffold

**Files:**

- Create: `pyproject.toml`, `.env.example`, `.gitignore`
- Create: `data/keystone_talents.json`
- Create: `tests/conftest.py`
- Create: all `__init__.py` files

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "wow-pvp-advisor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "httpx>=0.27",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create .env.example**

```
BNET_CLIENT_ID=your_client_id_here
BNET_CLIENT_SECRET=your_client_secret_here
BNET_REGION=us
```

- [ ] **Step 3: Create .gitignore**

```
.env
data/wow_advisor.db
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.superpowers/
```

- [ ] **Step 4: Create package structure**

Create these empty files:

- `wow_advisor/__init__.py`
- `wow_advisor/api/__init__.py`
- `wow_advisor/cache/__init__.py`
- `wow_advisor/processor/__init__.py`
- `wow_advisor/tools/__init__.py`
- `tests/__init__.py`

Create `data/keystone_talents.json`:

```json
{}
```

- [ ] **Step 5: Create tests/conftest.py**

```python
import pytest
import sqlite3


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")
```

- [ ] **Step 6: Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: all packages install cleanly, `pip show fastmcp httpx` shows versions.

- [ ] **Step 7: Smoke-test pytest runs**

```bash
pytest tests/ -v
```

Expected: `no tests ran` (0 collected). No errors.

- [ ] **Step 8: Commit**

```bash
git init
git add pyproject.toml .env.example .gitignore wow_advisor/ tests/ data/
git commit -m "chore: project scaffold"
```

---

## Task 2: Spec + bracket normalization

**Files:**

- Create: `wow_advisor/normalize.py`
- Create: `tests/test_normalize.py`

The leaderboard API returns `character_class.name` (e.g. `"Shaman"`) and `active_spec.name` (e.g. `"Restoration"`) separately. We need to map our normalized spec slug back to those two strings for filtering.

- [ ] **Step 1: Write failing tests**

`tests/test_normalize.py`:

```python
from wow_advisor.normalize import normalize_spec, normalize_bracket, spec_to_class_spec


def test_normalize_spec_exact():
    assert normalize_spec("restoration-shaman") == "restoration-shaman"


def test_normalize_spec_spaces():
    assert normalize_spec("restoration shaman") == "restoration-shaman"


def test_normalize_spec_alias_rsham():
    assert normalize_spec("rsham") == "restoration-shaman"


def test_normalize_spec_alias_resto():
    assert normalize_spec("resto shaman") == "restoration-shaman"


def test_normalize_spec_case():
    assert normalize_spec("Restoration Shaman") == "restoration-shaman"


def test_normalize_spec_unknown_passthrough():
    assert normalize_spec("arms warrior") == "arms-warrior"


def test_normalize_bracket_3v3():
    assert normalize_bracket("3v3") == "3v3"
    assert normalize_bracket("3V3") == "3v3"


def test_normalize_bracket_solo():
    assert normalize_bracket("solo") == "shuffle"
    assert normalize_bracket("solo shuffle") == "shuffle"


def test_normalize_bracket_2v2():
    assert normalize_bracket("2v2") == "2v2"


def test_spec_to_class_spec_shaman():
    cls, spec = spec_to_class_spec("restoration-shaman")
    assert cls == "Shaman"
    assert spec == "Restoration"


def test_spec_to_class_spec_rogue():
    cls, spec = spec_to_class_spec("subtlety-rogue")
    assert cls == "Rogue"
    assert spec == "Subtlety"


def test_spec_to_class_spec_unknown_returns_none():
    result = spec_to_class_spec("unknown-spec")
    assert result is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_normalize.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Implement wow_advisor/normalize.py**

```python
_SPEC_ALIASES: dict[str, str] = {
    "rsham": "restoration-shaman",
    "resto shaman": "restoration-shaman",
    "resto-shaman": "restoration-shaman",
    "rdruid": "restoration-druid",
    "resto druid": "restoration-druid",
    "hpal": "holy-paladin",
    "holy pal": "holy-paladin",
    "disc": "discipline-priest",
    "disc priest": "discipline-priest",
    "hpriest": "holy-priest",
    "mw": "mistweaver-monk",
    "mistweaver": "mistweaver-monk",
    "arms": "arms-warrior",
    "fury": "fury-warrior",
    "ret": "retribution-paladin",
    "rets": "retribution-paladin",
    "bm": "beast-mastery-hunter",
    "mm": "marksmanship-hunter",
    "surv": "survival-hunter",
    "sv": "survival-hunter",
    "aff": "affliction-warlock",
    "demo": "demonology-warlock",
    "destro": "destruction-warlock",
    "feral": "feral-druid",
    "balance": "balance-druid",
    "boom": "balance-druid",
    "boomkin": "balance-druid",
    "uh": "unholy-death-knight",
    "unholy": "unholy-death-knight",
    "unholy dk": "unholy-death-knight",
    "frost dk": "frost-death-knight",
    "frost": "frost-death-knight",
    "blood": "blood-death-knight",
    "blood dk": "blood-death-knight",
    "havoc": "havoc-demon-hunter",
    "veng": "vengeance-demon-hunter",
    "ele": "elemental-shaman",
    "enhance": "enhancement-shaman",
    "enh": "enhancement-shaman",
    "arcane": "arcane-mage",
    "fire": "fire-mage",
    "frost mage": "frost-mage",
    "sub": "subtlety-rogue",
    "sin": "assassination-rogue",
    "outlaw": "outlaw-rogue",
    "sp": "shadow-priest",
    "shadow": "shadow-priest",
    "aug": "augmentation-evoker",
    "dev": "devastation-evoker",
    "pres": "preservation-evoker",
    "ww": "windwalker-monk",
    "brew": "brewmaster-monk",
    "guardian": "guardian-druid",
    "prot warrior": "protection-warrior",
    "prot pally": "protection-paladin",
    "prot paladin": "protection-paladin",
}

_BRACKET_ALIASES: dict[str, str] = {
    "3v3": "3v3",
    "3vs3": "3v3",
    "2v2": "2v2",
    "2vs2": "2v2",
    "solo": "shuffle",
    "solo shuffle": "shuffle",
    "solo-shuffle": "shuffle",
    "shuffle": "shuffle",
    "rbg": "rbg",
    "blitz": "battlegrounds/blitz",
}

# Maps normalized spec slug → (WoW class name, WoW spec name) as returned by Blizzard API
_SPEC_CLASS_MAP: dict[str, tuple[str, str]] = {
    "restoration-shaman": ("Shaman", "Restoration"),
    "elemental-shaman": ("Shaman", "Elemental"),
    "enhancement-shaman": ("Shaman", "Enhancement"),
    "restoration-druid": ("Druid", "Restoration"),
    "balance-druid": ("Druid", "Balance"),
    "feral-druid": ("Druid", "Feral"),
    "guardian-druid": ("Druid", "Guardian"),
    "holy-paladin": ("Paladin", "Holy"),
    "retribution-paladin": ("Paladin", "Retribution"),
    "protection-paladin": ("Paladin", "Protection"),
    "discipline-priest": ("Priest", "Discipline"),
    "holy-priest": ("Priest", "Holy"),
    "shadow-priest": ("Priest", "Shadow"),
    "mistweaver-monk": ("Monk", "Mistweaver"),
    "windwalker-monk": ("Monk", "Windwalker"),
    "brewmaster-monk": ("Monk", "Brewmaster"),
    "arms-warrior": ("Warrior", "Arms"),
    "fury-warrior": ("Warrior", "Fury"),
    "protection-warrior": ("Warrior", "Protection"),
    "beast-mastery-hunter": ("Hunter", "Beast Mastery"),
    "marksmanship-hunter": ("Hunter", "Marksmanship"),
    "survival-hunter": ("Hunter", "Survival"),
    "affliction-warlock": ("Warlock", "Affliction"),
    "demonology-warlock": ("Warlock", "Demonology"),
    "destruction-warlock": ("Warlock", "Destruction"),
    "unholy-death-knight": ("Death Knight", "Unholy"),
    "frost-death-knight": ("Death Knight", "Frost"),
    "blood-death-knight": ("Death Knight", "Blood"),
    "havoc-demon-hunter": ("Demon Hunter", "Havoc"),
    "vengeance-demon-hunter": ("Demon Hunter", "Vengeance"),
    "arcane-mage": ("Mage", "Arcane"),
    "fire-mage": ("Mage", "Fire"),
    "frost-mage": ("Mage", "Frost"),
    "subtlety-rogue": ("Rogue", "Subtlety"),
    "assassination-rogue": ("Rogue", "Assassination"),
    "outlaw-rogue": ("Rogue", "Outlaw"),
    "augmentation-evoker": ("Evoker", "Augmentation"),
    "devastation-evoker": ("Evoker", "Devastation"),
    "preservation-evoker": ("Evoker", "Preservation"),
}


def normalize_spec(raw: str) -> str:
    key = raw.strip().lower()
    if key in _SPEC_ALIASES:
        return _SPEC_ALIASES[key]
    return key.replace(" ", "-")


def normalize_bracket(raw: str) -> str:
    key = raw.strip().lower()
    return _BRACKET_ALIASES.get(key, key)


def spec_to_class_spec(spec: str) -> tuple[str, str] | None:
    """Return (class_name, spec_name) as Blizzard API returns them, or None if unknown."""
    return _SPEC_CLASS_MAP.get(spec)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_normalize.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wow_advisor/normalize.py tests/test_normalize.py
git commit -m "feat: spec and bracket normalization with class mapping"
```

---

## Task 3: Data models

**Files:**

- Create: `wow_advisor/api/models.py`

- [ ] **Step 1: Create wow_advisor/api/models.py**

```python
from dataclasses import dataclass, field


@dataclass
class LeaderboardEntry:
    name: str
    realm: str
    rating: int
    rank: int


@dataclass
class GearSlot:
    slot: str
    item_id: int
    item_name: str
    ilvl: int
    enchant_id: int | None = None
    enchant_name: str | None = None


@dataclass
class TalentData:
    loadout_code: str
    class_node_ids: list[int] = field(default_factory=list)
    spec_node_ids: list[int] = field(default_factory=list)
    hero_node_ids: list[int] = field(default_factory=list)

    @property
    def all_node_ids(self) -> set[int]:
        return set(self.class_node_ids + self.spec_node_ids + self.hero_node_ids)


@dataclass
class CharacterData:
    name: str
    realm: str
    region: str
    character_class: str
    spec: str
    equipped_ilvl: int
    rating: int
    talent: TalentData | None = None
    gear: list[GearSlot] = field(default_factory=list)
```

- [ ] **Step 2: Verify import**

```bash
python -c "from wow_advisor.api.models import CharacterData, TalentData, GearSlot, LeaderboardEntry; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add wow_advisor/api/models.py
git commit -m "feat: data models"
```

---

## Task 4: Blizzard OAuth2 auth

**Files:**

- Create: `wow_advisor/api/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

`tests/test_auth.py`:

```python
import time
import pytest
import respx
import httpx
from wow_advisor.api.auth import BnetAuth


@pytest.fixture
def auth():
    return BnetAuth(client_id="test_id", client_secret="test_secret", region="us")


@respx.mock
async def test_fetch_token(auth):
    respx.post("https://oauth.battle.net/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "abc123",
            "expires_in": 86400,
            "token_type": "bearer",
        })
    )
    token = await auth.get_token()
    assert token == "abc123"


@respx.mock
async def test_token_cached(auth):
    route = respx.post("https://oauth.battle.net/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "abc123",
            "expires_in": 86400,
            "token_type": "bearer",
        })
    )
    await auth.get_token()
    await auth.get_token()
    assert route.call_count == 1


@respx.mock
async def test_token_refreshed_when_expired(auth):
    route = respx.post("https://oauth.battle.net/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "fresh_token",
            "expires_in": 86400,
            "token_type": "bearer",
        })
    )
    auth._token = "old_token"
    auth._expires_at = time.time() - 1  # already expired
    token = await auth.get_token()
    assert token == "fresh_token"
    assert route.call_count == 1
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Implement wow_advisor/api/auth.py**

```python
import time
import httpx


class BnetAuth:
    _TOKEN_URL = "https://oauth.battle.net/token"

    def __init__(self, client_id: str, client_secret: str, region: str = "us"):
        self._client_id = client_id
        self._client_secret = client_secret
        self._region = region
        self._token: str | None = None
        self._expires_at: float = 0.0

    async def get_token(self) -> str:
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(self._client_id, self._client_secret),
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._expires_at = time.time() + data["expires_in"]
            return self._token
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wow_advisor/api/auth.py tests/test_auth.py
git commit -m "feat: Blizzard OAuth2 auth with token caching"
```

---

## Task 5: Blizzard API client

**Files:**

- Create: `wow_advisor/api/client.py`
- Create: `tests/test_client.py`

The leaderboard API does NOT include spec — we get name/realm/rating only, then fetch each character's profile to get their class and active spec. Three calls fire concurrently per player: profile, specializations, equipment.

- [ ] **Step 1: Write failing tests**

`tests/test_client.py`:

```python
import pytest
import respx
import httpx
from unittest.mock import AsyncMock
from wow_advisor.api.client import BnetClient
from wow_advisor.api.models import LeaderboardEntry, CharacterData


@pytest.fixture
def mock_auth():
    auth = AsyncMock()
    auth.get_token.return_value = "test_token"
    return auth


@pytest.fixture
def client(mock_auth):
    return BnetClient(auth=mock_auth, region="us")


LEADERBOARD_RESPONSE = {
    "entries": [
        {
            "character": {"name": "Healbot", "realm": {"slug": "area-52"}},
            "rank": 1,
            "rating": 2800,
        },
        {
            "character": {"name": "Healer2", "realm": {"slug": "stormrage"}},
            "rank": 2,
            "rating": 2750,
        },
    ]
}


@respx.mock
async def test_fetch_leaderboard(client):
    respx.get(
        "https://us.api.blizzard.com/data/wow/pvp-season/40/pvp-leaderboard/3v3"
    ).mock(return_value=httpx.Response(200, json=LEADERBOARD_RESPONSE))

    entries = await client.fetch_leaderboard(bracket="3v3", season_id=40)
    assert len(entries) == 2
    assert entries[0].name == "healbot"
    assert entries[0].realm == "area-52"
    assert entries[0].rating == 2800
    assert entries[0].rank == 1


CHARACTER_RESPONSE = {
    "name": "Healbot",
    "realm": {"slug": "area-52"},
    "character_class": {"name": "Shaman"},
    "active_spec": {"name": "Restoration"},
    "equipped_item_level": 639,
}

SPEC_RESPONSE = {
    "specializations": [
        {
            "specialization": {"name": "Restoration"},
            "loadouts": [
                {
                    "is_active": True,
                    "talent_loadout_code": "BAQAAAAAAAAAAAAkU",
                    "selected_class_talents": [{"id": 101}, {"id": 102}],
                    "selected_spec_talents": [{"id": 201}, {"id": 202}],
                    "selected_hero_talents": [{"id": 301}],
                }
            ],
        }
    ]
}

EQUIPMENT_RESPONSE = {
    "equipped_items": [
        {
            "slot": {"type": "HEAD"},
            "item": {"id": 212456, "name": "Dawnbreaker's Hood"},
            "level": {"value": 639},
            "enchantments": [
                {
                    "enchantment_id": 7459,
                    "display_string": "Enchanted with Crystalline Radiance",
                }
            ],
        },
        {
            "slot": {"type": "CHEST"},
            "item": {"id": 212457, "name": "Dawnbreaker's Chestplate"},
            "level": {"value": 636},
        },
    ]
}


@respx.mock
async def test_fetch_character(client):
    respx.get(
        "https://us.api.blizzard.com/profile/wow/character/area-52/healbot"
    ).mock(return_value=httpx.Response(200, json=CHARACTER_RESPONSE))
    respx.get(
        "https://us.api.blizzard.com/profile/wow/character/area-52/healbot/specializations"
    ).mock(return_value=httpx.Response(200, json=SPEC_RESPONSE))
    respx.get(
        "https://us.api.blizzard.com/profile/wow/character/area-52/healbot/equipment"
    ).mock(return_value=httpx.Response(200, json=EQUIPMENT_RESPONSE))

    char = await client.fetch_character(name="healbot", realm="area-52", rating=2800)
    assert char is not None
    assert char.spec == "Restoration"
    assert char.character_class == "Shaman"
    assert char.equipped_ilvl == 639
    assert char.talent is not None
    assert char.talent.loadout_code == "BAQAAAAAAAAAAAAkU"
    assert 101 in char.talent.class_node_ids
    assert 201 in char.talent.spec_node_ids
    assert 301 in char.talent.hero_node_ids
    assert len(char.gear) == 2
    assert char.gear[0].slot == "head"
    assert char.gear[0].item_id == 212456
    assert char.gear[0].enchant_id == 7459


@respx.mock
async def test_fetch_character_404_returns_none(client):
    respx.get(
        "https://us.api.blizzard.com/profile/wow/character/area-52/deleted"
    ).mock(return_value=httpx.Response(404, json={"code": 404}))
    respx.get(
        "https://us.api.blizzard.com/profile/wow/character/area-52/deleted/specializations"
    ).mock(return_value=httpx.Response(404))
    respx.get(
        "https://us.api.blizzard.com/profile/wow/character/area-52/deleted/equipment"
    ).mock(return_value=httpx.Response(404))

    char = await client.fetch_character(name="deleted", realm="area-52", rating=2000)
    assert char is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_client.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement wow_advisor/api/client.py**

```python
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
        async with self._semaphore:
            for attempt in range(3):
                try:
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
        if not data:
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_client.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wow_advisor/api/client.py tests/test_client.py
git commit -m "feat: Blizzard API client with concurrent character fetch and retry"
```

---

## Task 6: SQLite cache

**Files:**

- Create: `wow_advisor/cache/db.py`
- Create: `wow_advisor/cache/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: Write failing tests**

`tests/test_store.py`:

```python
import time
import pytest
from wow_advisor.cache.db import init_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.api.models import CharacterData, TalentData, GearSlot


@pytest.fixture
def store(tmp_db):
    conn = init_db(tmp_db)
    return CacheStore(conn)


def make_char(name="Healbot", spec="Restoration", cls="Shaman", rating=2800):
    return CharacterData(
        name=name,
        realm="area-52",
        region="us",
        character_class=cls,
        spec=spec,
        equipped_ilvl=639,
        rating=rating,
        talent=TalentData(
            loadout_code="BAQAAAAAAAAAAAAkU",
            class_node_ids=[101, 102],
            spec_node_ids=[201, 202],
            hero_node_ids=[301],
        ),
        gear=[
            GearSlot(
                slot="head",
                item_id=212456,
                item_name="Hood",
                ilvl=639,
                enchant_id=7459,
                enchant_name="Crystalline",
            )
        ],
    )


def test_save_and_get_players(store):
    chars = [make_char("Player1"), make_char("Player2")]
    store.save_players(chars, spec="restoration-shaman", bracket="3v3")
    players = store.get_players(spec="restoration-shaman", bracket="3v3")
    assert len(players) == 2
    names = {p.name for p in players}
    assert "Player1" in names
    assert "Player2" in names


def test_get_players_empty(store):
    assert store.get_players(spec="arms-warrior", bracket="3v3") == []


def test_saved_talent_roundtrips(store):
    store.save_players([make_char()], spec="restoration-shaman", bracket="3v3")
    players = store.get_players(spec="restoration-shaman", bracket="3v3")
    assert players[0].talent is not None
    assert players[0].talent.loadout_code == "BAQAAAAAAAAAAAAkU"
    assert 101 in players[0].talent.class_node_ids
    assert 201 in players[0].talent.spec_node_ids


def test_saved_gear_roundtrips(store):
    store.save_players([make_char()], spec="restoration-shaman", bracket="3v3")
    players = store.get_players(spec="restoration-shaman", bracket="3v3")
    assert len(players[0].gear) == 1
    assert players[0].gear[0].slot == "head"
    assert players[0].gear[0].enchant_id == 7459


def test_save_aggregation_and_get(store):
    data = {"spec": "restoration-shaman", "sample_size": 50}
    store.save_aggregation(spec="restoration-shaman", bracket="3v3", region="us", data=data)
    result = store.get_aggregation(spec="restoration-shaman", bracket="3v3", region="us")
    assert result is not None
    assert result["sample_size"] == 50


def test_aggregation_overwrite(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {"v": 1})
    store.save_aggregation("restoration-shaman", "3v3", "us", {"v": 2})
    assert store.get_aggregation("restoration-shaman", "3v3", "us")["v"] == 2


def test_is_stale_fresh(store):
    store.save_aggregation("restoration-shaman", "3v3", "us", {})
    assert not store.is_stale("restoration-shaman", "3v3", "us", ttl_hours=24)


def test_is_stale_missing(store):
    assert store.is_stale("arms-warrior", "3v3", "us", ttl_hours=24)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_store.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement wow_advisor/cache/db.py**

```python
import os
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    realm TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'us',
    character_class TEXT,
    spec TEXT,
    bracket TEXT,
    rating INTEGER,
    equipped_ilvl INTEGER,
    fetched_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS player_loadouts (
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    talent_code TEXT,
    class_node_ids TEXT,
    spec_node_ids TEXT,
    hero_node_ids TEXT,
    gear TEXT
);

CREATE TABLE IF NOT EXISTS aggregations (
    spec TEXT NOT NULL,
    bracket TEXT NOT NULL,
    region TEXT NOT NULL,
    computed_at INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (spec, bracket, region)
);
"""


def init_db(path: str) -> sqlite3.Connection:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def get_default_db() -> sqlite3.Connection:
    db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "wow_advisor.db")
    )
    return init_db(db_path)
```

- [ ] **Step 4: Implement wow_advisor/cache/store.py**

```python
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
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_store.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add wow_advisor/cache/db.py wow_advisor/cache/store.py tests/test_store.py
git commit -m "feat: SQLite cache with player + aggregation store"
```

---

## Task 7: Talent processor

**Files:**

- Create: `wow_advisor/processor/talents.py`
- Create: `tests/test_talents.py`

Uses talent node IDs extracted from the Blizzard API's `selected_class_talents` / `selected_spec_talents` / `selected_hero_talents` — no binary decoding needed.

- [ ] **Step 1: Write failing tests**

`tests/test_talents.py`:

```python
import pytest
from wow_advisor.processor.talents import (
    TalentAnalysis,
    analyze_talents,
    cluster_talents,
    summarize_talent_clusters,
)


def make_node_sets(count: int, base: list[int], contested: dict[int, list[int]]) -> list[set[int]]:
    """Build `count` talent node sets. contested maps node_id → indices of players who take it."""
    result = [set(base) for _ in range(count)]
    for node_id, takers in contested.items():
        for i in takers:
            result[i].add(node_id)
    return result


def test_analyze_identifies_core_nodes():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(5)), 20: [0]})
    analysis = analyze_talents(node_sets)
    assert 1 in analysis.core_nodes
    assert 2 in analysis.core_nodes
    assert 3 in analysis.core_nodes


def test_analyze_identifies_contested_nodes():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(5)), 20: [0]})
    analysis = analyze_talents(node_sets)
    assert 10 in analysis.contested_nodes


def test_analyze_identifies_flex_nodes():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(5)), 20: [0]})
    analysis = analyze_talents(node_sets)
    assert 20 in analysis.flex_nodes


def test_analyze_empty_input():
    analysis = analyze_talents([])
    assert analysis.core_nodes == set()
    assert analysis.contested_nodes == set()
    assert analysis.flex_nodes == set()


def test_cluster_splits_distinct_builds():
    # 5 players take node 100, 5 take node 101 — hamming distance = 2, threshold = 1 → 2 clusters
    pairs = [({100}, i) for i in range(5)] + [({101}, i + 5) for i in range(5)]
    clusters = cluster_talents(pairs, threshold=1)
    assert len(clusters) == 2
    assert sorted(len(c) for c in clusters) == [5, 5]


def test_cluster_merges_near_identical():
    # {100} vs {100, 101} differ by 1 node — within threshold=2 → 1 cluster
    pairs = [({100}, i) for i in range(5)] + [({100, 101}, i + 5) for i in range(5)]
    clusters = cluster_talents(pairs, threshold=2)
    assert len(clusters) == 1


def test_cluster_sorted_by_size_descending():
    # 7 players take {100}, 3 take {101}
    pairs = [({100}, i) for i in range(7)] + [({101}, i + 7) for i in range(3)]
    clusters = cluster_talents(pairs, threshold=1)
    assert len(clusters[0]) >= len(clusters[1])


def test_full_pipeline_two_builds():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(7)), 11: list(range(7, 10))})
    analysis = analyze_talents(node_sets)
    contested_pairs = [(node_sets[i] & analysis.contested_nodes, i) for i in range(10)]
    clusters = cluster_talents(contested_pairs, threshold=1)
    assert len(clusters) == 2
    sizes = sorted([len(c) for c in clusters], reverse=True)
    assert sizes == [7, 3]


def test_summarize_returns_expected_shape():
    node_sets = make_node_sets(10, [1, 2, 3], {10: list(range(7)), 11: list(range(7, 10))})
    codes = [f"code_{i}" for i in range(10)]
    result = summarize_talent_clusters(node_sets, codes, keystone_nodes=None)
    assert "core_nodes" in result
    assert "contested_nodes" in result
    assert "clusters" in result
    assert result["clustering_method"] in ("variance+hamming", "keystone")
    assert len(result["clusters"]) == 2
    assert result["clusters"][0]["pct"] == 70.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_talents.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement wow_advisor/processor/talents.py**

```python
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class TalentAnalysis:
    core_nodes: set[int] = field(default_factory=set)
    flex_nodes: set[int] = field(default_factory=set)
    contested_nodes: set[int] = field(default_factory=set)
    pick_rates: dict[int, float] = field(default_factory=dict)


def analyze_talents(
    node_sets: list[set[int]],
    core_threshold: float = 0.8,
    flex_threshold: float = 0.2,
) -> TalentAnalysis:
    if not node_sets:
        return TalentAnalysis()
    n = len(node_sets)
    all_nodes: set[int] = set().union(*node_sets)
    pick_counts: dict[int, int] = {node: 0 for node in all_nodes}
    for nodes in node_sets:
        for node in nodes:
            pick_counts[node] += 1
    pick_rates = {node: count / n for node, count in pick_counts.items()}
    core = {node for node, rate in pick_rates.items() if rate >= core_threshold}
    flex = {node for node, rate in pick_rates.items() if rate <= flex_threshold}
    contested = all_nodes - core - flex
    return TalentAnalysis(
        core_nodes=core,
        flex_nodes=flex,
        contested_nodes=contested,
        pick_rates=pick_rates,
    )


def _hamming(a: set[int], b: set[int]) -> int:
    return len(a.symmetric_difference(b))


def cluster_talents(
    contested_pairs: list[tuple[set[int], int]],
    threshold: int = 2,
) -> list[list[tuple[set[int], int]]]:
    """Greedy Hamming clustering. Returns clusters sorted by size descending."""
    assigned = [False] * len(contested_pairs)
    clusters: list[list[tuple[set[int], int]]] = []
    for i, (nodes_i, idx_i) in enumerate(contested_pairs):
        if assigned[i]:
            continue
        cluster = [(nodes_i, idx_i)]
        assigned[i] = True
        for j in range(i + 1, len(contested_pairs)):
            if assigned[j]:
                continue
            if _hamming(nodes_i, contested_pairs[j][0]) <= threshold:
                cluster.append(contested_pairs[j])
                assigned[j] = True
        clusters.append(cluster)
    return sorted(clusters, key=len, reverse=True)


def summarize_talent_clusters(
    node_sets: list[set[int]],
    loadout_codes: list[str],
    keystone_nodes: list[int] | None = None,
) -> dict:
    """Full pipeline: analyze → cluster → summarize."""
    n = len(node_sets)
    if n == 0:
        return {"core_nodes": [], "flex_nodes": [], "contested_nodes": [],
                "clusters": [], "clustering_method": "variance+hamming"}

    analysis = analyze_talents(node_sets)

    if keystone_nodes is not None:
        decision_nodes = set(keystone_nodes)
        method = "keystone"
    else:
        decision_nodes = analysis.contested_nodes
        method = "variance+hamming"

    contested_pairs = [(node_sets[i] & decision_nodes, i) for i in range(n)]
    clusters = cluster_talents(contested_pairs, threshold=2)

    cluster_summaries = []
    for rank, cluster in enumerate(clusters, 1):
        counts = Counter(frozenset(nodes) for nodes, _ in cluster)
        canonical_set = set(counts.most_common(1)[0][0])
        canonical_idx = next(
            (idx for nodes, idx in cluster if set(nodes) == canonical_set),
            cluster[0][1],
        )
        canonical_code = loadout_codes[canonical_idx] if canonical_idx < len(loadout_codes) else ""
        cluster_summaries.append({
            "rank": rank,
            "count": len(cluster),
            "pct": round(len(cluster) / n * 100, 1),
            "canonical_code": canonical_code,
            "takes": sorted(canonical_set),
            "skips": sorted(decision_nodes - canonical_set),
        })

    return {
        "core_nodes": sorted(analysis.core_nodes),
        "flex_nodes": sorted(analysis.flex_nodes),
        "contested_nodes": sorted(decision_nodes),
        "clusters": cluster_summaries,
        "clustering_method": method,
    }
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_talents.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wow_advisor/processor/talents.py tests/test_talents.py
git commit -m "feat: talent processor with variance analysis and Hamming clustering"
```

---

## Task 8: Gear processor

**Files:**

- Create: `wow_advisor/processor/gear.py`
- Create: `tests/test_gear.py`

- [ ] **Step 1: Write failing tests**

`tests/test_gear.py`:

```python
import pytest
from wow_advisor.api.models import GearSlot
from wow_advisor.processor.gear import aggregate_gear


def make_slot(slot: str, item_id: int, item_name: str, ilvl: int,
              enchant_id: int | None = None, enchant_name: str | None = None) -> GearSlot:
    return GearSlot(slot=slot, item_id=item_id, item_name=item_name, ilvl=ilvl,
                    enchant_id=enchant_id, enchant_name=enchant_name)


def test_aggregate_item_frequency():
    all_gear = [
        [make_slot("head", 100, "Hood A", 639)] * 3 + [make_slot("head", 101, "Hood B", 636)],
    ]
    # flatten: 4 players, 3 have Hood A, 1 has Hood B
    players_gear = all_gear[0]
    result = aggregate_gear([players_gear], n_players=4)
    head_items = result["gear"]["head"]
    assert head_items[0]["item_id"] == 100
    assert head_items[0]["count"] == 3
    assert head_items[0]["pct"] == 75.0


def test_aggregate_enchant_frequency():
    gear_per_player = [
        [make_slot("chest", 200, "Chest", 639, enchant_id=7459, enchant_name="Crystalline")],
        [make_slot("chest", 200, "Chest", 639, enchant_id=7459, enchant_name="Crystalline")],
        [make_slot("chest", 200, "Chest", 639)],
    ]
    result = aggregate_gear(gear_per_player, n_players=3)
    enchants = result["enchants"].get("chest", [])
    assert len(enchants) == 1
    assert enchants[0]["enchant_id"] == 7459
    assert enchants[0]["count"] == 2
    assert round(enchants[0]["pct"], 1) == 66.7


def test_aggregate_avg_ilvl():
    gear_per_player = [
        [make_slot("head", 100, "Hood", ilvl) for ilvl in [639, 636, 633]],
    ]
    # one player with 3 slots of varying ilvl — but avg_ilvl is per-player equipped_ilvl
    # we pass equipped_ilvls separately
    result = aggregate_gear(gear_per_player, n_players=3, equipped_ilvls=[639, 636, 633])
    assert result["avg_ilvl"] == 636


def test_aggregate_empty():
    result = aggregate_gear([], n_players=0)
    assert result["gear"] == {}
    assert result["enchants"] == {}
    assert result["avg_ilvl"] == 0


def test_aggregate_trinkets_surfaced():
    gear_per_player = [
        [
            make_slot("trinket_1", 300, "Trinket A", 639),
            make_slot("trinket_2", 301, "Trinket B", 639),
        ]
        for _ in range(5)
    ]
    result = aggregate_gear(gear_per_player, n_players=5)
    assert "trinket_1" in result["gear"]
    assert result["gear"]["trinket_1"][0]["item_id"] == 300
    assert result["gear"]["trinket_1"][0]["pct"] == 100.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_gear.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement wow_advisor/processor/gear.py**

```python
from collections import Counter, defaultdict
from wow_advisor.api.models import GearSlot


def aggregate_gear(
    gear_per_player: list[list[GearSlot]],
    n_players: int,
    equipped_ilvls: list[int] | None = None,
) -> dict:
    if n_players == 0:
        return {"gear": {}, "enchants": {}, "avg_ilvl": 0}

    slot_items: dict[str, list[tuple[int, str]]] = defaultdict(list)
    slot_enchants: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for player_gear in gear_per_player:
        for g in player_gear:
            slot_items[g.slot].append((g.item_id, g.item_name))
            if g.enchant_id is not None:
                slot_enchants[g.slot].append((g.enchant_id, g.enchant_name or ""))

    gear_summary: dict[str, list[dict]] = {}
    for slot, items in slot_items.items():
        counts = Counter(items)
        gear_summary[slot] = sorted(
            [
                {
                    "item_id": item_id,
                    "name": item_name,
                    "count": count,
                    "pct": round(count / n_players * 100, 1),
                }
                for (item_id, item_name), count in counts.items()
            ],
            key=lambda x: -x["count"],
        )

    enchant_summary: dict[str, list[dict]] = {}
    for slot, enchants in slot_enchants.items():
        counts = Counter(enchants)
        enchant_summary[slot] = sorted(
            [
                {
                    "enchant_id": eid,
                    "name": ename,
                    "count": count,
                    "pct": round(count / n_players * 100, 1),
                }
                for (eid, ename), count in counts.items()
            ],
            key=lambda x: -x["count"],
        )

    if equipped_ilvls:
        avg_ilvl = round(sum(equipped_ilvls) / len(equipped_ilvls))
    else:
        avg_ilvl = 0

    return {"gear": gear_summary, "enchants": enchant_summary, "avg_ilvl": avg_ilvl}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_gear.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wow_advisor/processor/gear.py tests/test_gear.py
git commit -m "feat: gear processor with per-slot item and enchant frequency"
```

---

## Task 9: Aggregator

**Files:**

- Create: `wow_advisor/processor/aggregator.py`
- Create: `tests/test_aggregator.py`

Reads `data/keystone_talents.json` to decide whether to use variance+Hamming or keystone fallback.

- [ ] **Step 1: Write failing tests**

`tests/test_aggregator.py`:

```python
import pytest
from wow_advisor.api.models import CharacterData, TalentData, GearSlot
from wow_advisor.processor.aggregator import build_aggregation


def make_char(i: int, class_node_extra: int | None = None) -> CharacterData:
    class_nodes = [101, 102, 103]
    spec_nodes = [201, 202]
    if class_node_extra:
        spec_nodes = [class_node_extra]
    return CharacterData(
        name=f"Player{i}", realm="area-52", region="us",
        character_class="Shaman", spec="Restoration",
        equipped_ilvl=639, rating=2800 - i,
        talent=TalentData(
            loadout_code=f"code_{i}",
            class_node_ids=class_nodes,
            spec_node_ids=spec_nodes,
            hero_node_ids=[301],
        ),
        gear=[GearSlot(slot="head", item_id=100 + (i % 2), item_name=f"Hood{i%2}",
                       ilvl=639, enchant_id=7459, enchant_name="Crystalline")],
    )


def test_build_aggregation_structure(tmp_path):
    players = [make_char(i) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert result["spec"] == "restoration-shaman"
    assert result["bracket"] == "3v3"
    assert result["region"] == "us"
    assert result["sample_size"] == 10
    assert "avg_ilvl" in result
    assert "talents" in result
    assert "gear" in result
    assert "enchants" in result
    assert "clusters" in result["talents"]


def test_build_aggregation_gear_present(tmp_path):
    players = [make_char(i) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert "head" in result["gear"]
    assert result["gear"]["head"][0]["pct"] > 0


def test_build_aggregation_keystone_fallback(tmp_path):
    import json
    keystone_file = tmp_path / "keystone_talents.json"
    keystone_file.write_text(json.dumps({"restoration-shaman": [201, 202]}))
    players = [make_char(i, class_node_extra=201 if i < 7 else 202) for i in range(10)]
    result = build_aggregation(
        players=players,
        spec="restoration-shaman",
        bracket="3v3",
        region="us",
        keystone_file=str(keystone_file),
    )
    assert result["talents"]["clustering_method"] == "keystone"


def test_build_aggregation_skips_players_without_talent(tmp_path):
    players = [make_char(i) for i in range(8)]
    no_talent = CharacterData(
        name="NoTalent", realm="area-52", region="us",
        character_class="Shaman", spec="Restoration",
        equipped_ilvl=630, rating=2600, talent=None, gear=[],
    )
    players.append(no_talent)
    result = build_aggregation(
        players=players, spec="restoration-shaman", bracket="3v3", region="us",
        keystone_file=str(tmp_path / "keystone_talents.json"),
    )
    assert result["sample_size"] == 9
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_aggregator.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement wow_advisor/processor/aggregator.py**

```python
import json
import os
from wow_advisor.api.models import CharacterData
from wow_advisor.processor.talents import summarize_talent_clusters
from wow_advisor.processor.gear import aggregate_gear

_DEFAULT_KEYSTONE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "keystone_talents.json")
)


def _load_keystone_nodes(spec: str, keystone_file: str) -> list[int] | None:
    if not os.path.exists(keystone_file):
        return None
    with open(keystone_file) as f:
        data = json.load(f)
    return data.get(spec)


def build_aggregation(
    players: list[CharacterData],
    spec: str,
    bracket: str,
    region: str,
    keystone_file: str = _DEFAULT_KEYSTONE_FILE,
) -> dict:
    players_with_talent = [p for p in players if p.talent is not None]
    node_sets = [p.talent.all_node_ids for p in players_with_talent]
    loadout_codes = [p.talent.loadout_code for p in players_with_talent]
    keystone_nodes = _load_keystone_nodes(spec, keystone_file)

    talent_summary = summarize_talent_clusters(
        node_sets=node_sets,
        loadout_codes=loadout_codes,
        keystone_nodes=keystone_nodes,
    )

    equipped_ilvls = [p.equipped_ilvl for p in players]
    gear_per_player = [p.gear for p in players]
    gear_summary = aggregate_gear(
        gear_per_player=gear_per_player,
        n_players=len(players),
        equipped_ilvls=equipped_ilvls,
    )

    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": len(players),
        "avg_ilvl": gear_summary["avg_ilvl"],
        "talents": talent_summary,
        "gear": gear_summary["gear"],
        "enchants": gear_summary["enchants"],
    }
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_aggregator.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests across all modules PASS.

- [ ] **Step 6: Commit**

```bash
git add wow_advisor/processor/aggregator.py tests/test_aggregator.py
git commit -m "feat: aggregator orchestrating talent and gear summaries"
```

---

## Task 10: Fetch orchestration

**Files:**

- Create: `wow_advisor/tools/fetch.py`

This is the core pipeline: leaderboard → filter by spec → fetch characters concurrently → store → aggregate. The leaderboard does not include spec, so we fetch character profiles to filter. We scan up to `scan_limit` (default 500) leaderboard entries to find `limit` (default 50) players of the target spec.

- [ ] **Step 1: Create wow_advisor/tools/fetch.py**

```python
import asyncio
import os
from wow_advisor.api.auth import BnetAuth
from wow_advisor.api.client import BnetClient
from wow_advisor.api.models import CharacterData
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket, spec_to_class_spec
from wow_advisor.processor.aggregator import build_aggregation


def _make_client(region: str) -> tuple[BnetAuth, BnetClient]:
    client_id = os.environ["BNET_CLIENT_ID"]
    client_secret = os.environ["BNET_CLIENT_SECRET"]
    auth = BnetAuth(client_id=client_id, client_secret=client_secret, region=region)
    return auth, BnetClient(auth=auth, region=region)


async def fetch_top_players_async(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
    scan_limit: int = 500,
) -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)

    class_spec = spec_to_class_spec(spec)
    if class_spec is None:
        return {"error": f"Unknown spec: {spec}. Check spelling or add it to normalize.py."}

    target_class, target_spec = class_spec
    _, client = _make_client(region)

    leaderboard = await client.fetch_leaderboard(bracket=bracket)
    if not leaderboard:
        return {"error": f"No leaderboard data for bracket '{bracket}'. Check bracket name and season ID."}

    candidates = leaderboard[:scan_limit]

    collected: list[CharacterData] = []
    batch_size = 20

    for i in range(0, len(candidates), batch_size):
        if len(collected) >= limit:
            break
        batch = candidates[i:i + batch_size]
        results = await asyncio.gather(*[
            client.fetch_character(name=e.name, realm=e.realm, rating=e.rating)
            for e in batch
        ])
        for char in results:
            if char is None:
                continue
            if char.character_class == target_class and char.spec == target_spec:
                collected.append(char)
            if len(collected) >= limit:
                break

    if not collected:
        return {
            "error": (
                f"Found 0 {spec} players in the top {min(scan_limit, len(leaderboard))} "
                f"{bracket} leaderboard entries. Try increasing scan_limit or check spec name."
            )
        }

    conn = get_default_db()
    store = CacheStore(conn)
    store.save_players(collected, spec=spec, bracket=bracket)

    aggregation = build_aggregation(
        players=collected,
        spec=spec,
        bracket=bracket,
        region=region,
    )
    store.save_aggregation(spec=spec, bracket=bracket, region=region, data=aggregation)

    import time
    return {"fetched": len(collected), "cached_at": int(time.time()), "spec": spec, "bracket": bracket}


def fetch_top_players(
    spec: str,
    bracket: str,
    region: str = "us",
    limit: int = 50,
) -> dict:
    """Synchronous wrapper for MCP tool use."""
    return asyncio.run(fetch_top_players_async(spec=spec, bracket=bracket, region=region, limit=limit))
```

- [ ] **Step 2: Verify import**

```bash
python -c "from wow_advisor.tools.fetch import fetch_top_players; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add wow_advisor/tools/fetch.py
git commit -m "feat: fetch orchestration pipeline with spec filtering"
```

---

## Task 11: MCP query tools

**Files:**

- Create: `wow_advisor/tools/talents.py`
- Create: `wow_advisor/tools/gear.py`

These tools read from cache (auto-refreshing if stale) and return structured data.

- [ ] **Step 1: Create wow_advisor/tools/talents.py**

```python
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.tools.fetch import fetch_top_players


def get_talent_distribution(spec: str, bracket: str, region: str = "us") -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)
    conn = get_default_db()
    store = CacheStore(conn)
    if store.is_stale(spec, bracket, region):
        result = fetch_top_players(spec=spec, bracket=bracket, region=region)
        if "error" in result:
            return result
    agg = store.get_aggregation(spec, bracket, region)
    if agg is None:
        return {"error": f"No data for {spec} in {bracket}. Try calling fetch_top_players first."}
    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": agg.get("sample_size", 0),
        "cached_at": agg.get("cached_at"),
        "talents": agg.get("talents", {}),
    }
```

- [ ] **Step 2: Create wow_advisor/tools/gear.py**

```python
from wow_advisor.cache.db import get_default_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.normalize import normalize_spec, normalize_bracket
from wow_advisor.tools.fetch import fetch_top_players


def get_gear_summary(spec: str, bracket: str, region: str = "us") -> dict:
    spec = normalize_spec(spec)
    bracket = normalize_bracket(bracket)
    conn = get_default_db()
    store = CacheStore(conn)
    if store.is_stale(spec, bracket, region):
        result = fetch_top_players(spec=spec, bracket=bracket, region=region)
        if "error" in result:
            return result
    agg = store.get_aggregation(spec, bracket, region)
    if agg is None:
        return {"error": f"No data for {spec} in {bracket}. Try calling fetch_top_players first."}
    return {
        "spec": spec,
        "bracket": bracket,
        "region": region,
        "sample_size": agg.get("sample_size", 0),
        "avg_ilvl": agg.get("avg_ilvl", 0),
        "cached_at": agg.get("cached_at"),
        "gear": agg.get("gear", {}),
        "enchants": agg.get("enchants", {}),
    }


def get_player_details(name: str, realm: str, region: str = "us") -> dict:
    conn = get_default_db()
    store = CacheStore(conn)
    # Search across all cached specs/brackets for this player
    rows = conn.execute(
        """SELECT p.name, p.realm, p.region, p.character_class, p.spec,
                  p.bracket, p.rating, p.equipped_ilvl,
                  l.talent_code, l.class_node_ids, l.spec_node_ids, l.hero_node_ids, l.gear
           FROM players p LEFT JOIN player_loadouts l ON p.id = l.player_id
           WHERE LOWER(p.name)=LOWER(?) AND LOWER(p.realm)=LOWER(?) AND p.region=?
           ORDER BY p.rating DESC LIMIT 1""",
        (name, realm, region),
    ).fetchall()
    if not rows:
        return {"error": f"Player {name}-{realm} not found in cache. Fetch their spec first."}
    import json
    r = rows[0]
    return {
        "name": r["name"],
        "realm": r["realm"],
        "spec": r["spec"],
        "class": r["character_class"],
        "rating": r["rating"],
        "equipped_ilvl": r["equipped_ilvl"],
        "talent_code": r["talent_code"],
        "class_node_ids": json.loads(r["class_node_ids"] or "[]"),
        "spec_node_ids": json.loads(r["spec_node_ids"] or "[]"),
        "hero_node_ids": json.loads(r["hero_node_ids"] or "[]"),
        "gear": json.loads(r["gear"] or "[]"),
    }
```

- [ ] **Step 3: Verify imports**

```bash
python -c "from wow_advisor.tools.talents import get_talent_distribution; from wow_advisor.tools.gear import get_gear_summary, get_player_details; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add wow_advisor/tools/talents.py wow_advisor/tools/gear.py
git commit -m "feat: MCP query tools for talent distribution, gear summary, player details"
```

---

## Task 12: MCP server entry point

**Files:**

- Create: `mcp_server.py`

- [ ] **Step 1: Create mcp_server.py**

```python
from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from wow_advisor.tools.fetch import fetch_top_players
from wow_advisor.tools.talents import get_talent_distribution
from wow_advisor.tools.gear import get_gear_summary, get_player_details

mcp = FastMCP("wow-pvp-advisor")


@mcp.tool()
def fetch_top_players_tool(spec: str, bracket: str, region: str = "us", limit: int = 50) -> dict:
    """Fetch and cache top players for a spec+bracket. Call this first or to refresh stale data.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham', 'arms warrior'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle'
        region: 'us' or 'eu' (default: 'us')
        limit: Number of top players to fetch (default: 50)
    """
    return fetch_top_players(spec=spec, bracket=bracket, region=region, limit=limit)


@mcp.tool()
def get_talent_distribution_tool(spec: str, bracket: str, region: str = "us") -> dict:
    """Get talent build distribution for a spec+bracket from top players.

    Returns talent clusters ranked by pick rate, with core/contested/flex node breakdown.
    Auto-fetches if cache is older than 24 hours.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle'
        region: 'us' or 'eu' (default: 'us')
    """
    return get_talent_distribution(spec=spec, bracket=bracket, region=region)


@mcp.tool()
def get_gear_summary_tool(spec: str, bracket: str, region: str = "us") -> dict:
    """Get gear and enchant summary for a spec+bracket from top players.

    Returns most popular items per slot, enchant frequencies, avg item level.
    Trinkets highlighted. Auto-fetches if cache is older than 24 hours.

    Args:
        spec: Spec name, e.g. 'restoration shaman', 'rsham'
        bracket: PvP bracket, e.g. '3v3', '2v2', 'solo shuffle'
        region: 'us' or 'eu' (default: 'us')
    """
    return get_gear_summary(spec=spec, bracket=bracket, region=region)


@mcp.tool()
def get_player_details_tool(name: str, realm: str, region: str = "us") -> dict:
    """Get full gear and talent details for a specific player from the local cache.

    Player must have been included in a recent fetch_top_players call.

    Args:
        name: Character name
        realm: Realm slug, e.g. 'area-52', 'stormrage'
        region: 'us' or 'eu' (default: 'us')
    """
    return get_player_details(name=name, realm=realm, region=region)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Verify MCP server starts**

```bash
python mcp_server.py --help 2>&1 | head -5
```

Expected: fastmcp help output, no import errors.

- [ ] **Step 3: Commit**

```bash
git add mcp_server.py
git commit -m "feat: MCP server entry point with 4 tools"
```

---

## Task 13: CLI for manual use and dev mode

**Files:**

- Create: `cli.py`

- [ ] **Step 1: Create cli.py**

```python
#!/usr/bin/env python3
"""Manual CLI for fetching and inspecting WoW PvP data.

Usage:
    python cli.py fetch <spec> <bracket> [--region us] [--limit 50]
    python cli.py talents <spec> <bracket> [--region us]
    python cli.py gear <spec> <bracket> [--region us]
    python cli.py player <name> <realm> [--region us]
"""
import argparse
import json
import sys
from dotenv import load_dotenv
load_dotenv()

from wow_advisor.tools.fetch import fetch_top_players
from wow_advisor.tools.talents import get_talent_distribution
from wow_advisor.tools.gear import get_gear_summary, get_player_details


def cmd_fetch(args):
    print(f"Fetching top {args.limit} {args.spec} players in {args.bracket} ({args.region})...")
    result = fetch_top_players(spec=args.spec, bracket=args.bracket, region=args.region, limit=args.limit)
    print(json.dumps(result, indent=2))


def cmd_talents(args):
    result = get_talent_distribution(spec=args.spec, bracket=args.bracket, region=args.region)
    print(json.dumps(result, indent=2))


def cmd_gear(args):
    result = get_gear_summary(spec=args.spec, bracket=args.bracket, region=args.region)
    print(json.dumps(result, indent=2))


def cmd_player(args):
    result = get_player_details(name=args.name, realm=args.realm, region=args.region)
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="WoW PvP Advisor CLI")
    sub = parser.add_subparsers(dest="command")

    p_fetch = sub.add_parser("fetch", help="Fetch top players for a spec+bracket")
    p_fetch.add_argument("spec")
    p_fetch.add_argument("bracket")
    p_fetch.add_argument("--region", default="us")
    p_fetch.add_argument("--limit", type=int, default=50)

    p_talents = sub.add_parser("talents", help="Show talent distribution")
    p_talents.add_argument("spec")
    p_talents.add_argument("bracket")
    p_talents.add_argument("--region", default="us")

    p_gear = sub.add_parser("gear", help="Show gear summary")
    p_gear.add_argument("spec")
    p_gear.add_argument("bracket")
    p_gear.add_argument("--region", default="us")

    p_player = sub.add_parser("player", help="Show a specific player's details")
    p_player.add_argument("name")
    p_player.add_argument("realm")
    p_player.add_argument("--region", default="us")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    dispatch = {"fetch": cmd_fetch, "talents": cmd_talents, "gear": cmd_gear, "player": cmd_player}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI help works**

```bash
python cli.py --help
```

Expected: prints usage with fetch/talents/gear/player subcommands.

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "feat: CLI for manual fetch and dev mode inspection"
```

---

## Task 14: Claude Code MCP setup + smoke test

**Files:**

- Modify: `~/.claude/settings.json` (user's local config, not committed)
- Create: `README.md` (setup instructions)

- [ ] **Step 1: Add README.md with setup instructions**

Create `README.md`:

````markdown
# WoW PvP Advisor

Fetches top-50 WoW PvP player data (talents, gear, enchants) and exposes it as an MCP server for Claude Code.

## Setup

### 1. Get a Blizzard API key

Go to https://develop.battle.net/access/clients → Create Client → copy Client ID and Secret.

### 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env: add your BNET_CLIENT_ID and BNET_CLIENT_SECRET
```
````

### 3. Register MCP server in Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "wow-advisor": {
      "command": "/path/to/wow-pvp-advisor/.venv/bin/python",
      "args": ["/path/to/wow-pvp-advisor/mcp_server.py"]
    }
  }
}
```

(The `.env` file is loaded by `mcp_server.py` at startup, so no need to pass env vars in settings.)

### 4. Test manually first

```bash
python cli.py fetch "resto shaman" 3v3
python cli.py talents "resto shaman" 3v3
python cli.py gear "resto shaman" 3v3
```

### 5. Ask Claude

Once the MCP server is registered, open Claude Code and ask:

- "What talents should I run as Restoration Shaman in 3v3?"
- "What trinkets are top Resto Shamans using?"
- "What's the most common gear setup for arms warriors in 3v3?"

````

- [ ] **Step 2: Register MCP server**

Edit `~/.claude/settings.json` (create if it doesn't exist):

```json
{
  "mcpServers": {
    "wow-advisor": {
      "command": "/absolute/path/to/wow-pvp-advisor/.venv/bin/python",
      "args": ["/absolute/path/to/wow-pvp-advisor/mcp_server.py"]
    }
  }
}
````

Replace `/absolute/path/to/wow-pvp-advisor` with the actual path. Find it with `pwd`.

- [ ] **Step 3: Verify MCP server is visible**

Start a new Claude Code session and run:

```
/mcp
```

Expected: `wow-advisor` listed as a connected server with 4 tools: `fetch_top_players_tool`, `get_talent_distribution_tool`, `get_gear_summary_tool`, `get_player_details_tool`.

- [ ] **Step 4: Smoke test end-to-end**

In Claude Code, ask:

> "Fetch and summarize the top Restoration Shaman talent builds for 3v3."

Expected: Claude calls `fetch_top_players_tool` then `get_talent_distribution_tool`, returns a summary with 2-3 talent clusters and their pick rates.

- [ ] **Step 5: Final commit**

```bash
git add README.md
git commit -m "docs: setup instructions and Claude Code MCP registration"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement                                        | Task                                            |
| ------------------------------------------------------- | ----------------------------------------------- |
| Blizzard OAuth2 client credentials                      | Task 4 (auth.py)                                |
| PvP leaderboard fetch                                   | Task 5 (client.py fetch_leaderboard)            |
| Per-character: profile + specializations + equipment    | Task 5 (client.py fetch_character)              |
| Rate limit handling (429 retry)                         | Task 5 (client.py \_get)                        |
| 404 character skip                                      | Task 5 (client.py fetch_character returns None) |
| SQLite schema (players, player_loadouts, aggregations)  | Task 6 (db.py)                                  |
| 24h TTL + stale check                                   | Task 6 (store.py is_stale)                      |
| Talent node ID extraction from specializations API      | Task 5 (client.py \_parse_talents)              |
| Variance analysis (core/contested/flex)                 | Task 7 (talents.py analyze_talents)             |
| Hamming clustering on contested nodes                   | Task 7 (talents.py cluster_talents)             |
| Keystone fallback (data/keystone_talents.json)          | Task 9 (aggregator.py \_load_keystone_nodes)    |
| Per-slot item + enchant frequency                       | Task 8 (gear.py)                                |
| `fetch_top_players` MCP tool                            | Tasks 10, 12                                    |
| `get_talent_distribution` MCP tool                      | Tasks 11, 12                                    |
| `get_gear_summary` MCP tool                             | Tasks 11, 12                                    |
| `get_player_details` MCP tool                           | Tasks 11, 12                                    |
| Spec normalization (rsham → restoration-shaman)         | Task 2                                          |
| Bracket normalization (solo → shuffle)                  | Task 2                                          |
| Class+spec filtering from leaderboard                   | Task 10 (fetch.py, spec_to_class_spec)          |
| Serve stale cache on API outage (cached_at in response) | Task 6 (store.py get_aggregation)               |
| CLI for dev mode                                        | Task 13                                         |
| Claude Code MCP registration                            | Task 14                                         |

All spec requirements covered. No gaps.
