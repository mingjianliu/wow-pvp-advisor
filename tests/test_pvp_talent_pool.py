"""PvP talent pool snapshots.

The project only ever saw PvP talents through player profiles, so when 12.1
landed there was no baseline to diff against — a removal like Balance Druid's
Dying Stars was only detectable by reading patch notes. Snapshotting the pool
makes the next patch a real diff.
"""
import httpx
import pytest
import respx
from unittest.mock import AsyncMock

from wow_advisor.api.client import BnetClient
from wow_advisor.cache.db import init_db
from wow_advisor.cache.store import CacheStore
from wow_advisor.processor.pvp_talents import diff_pvp_talent_pool

SPEC_URL = "https://us.api.blizzard.com/data/wow/playable-specialization/264"
NAMESPACE = "static-12.1.0_68914-us"

SPEC_PAYLOAD = {
    "id": 264,
    "name": "Restoration",
    "pvp_talents": [
        {
            "talent": {"name": "Grounding Totem", "id": 715},
            "spell_tooltip": {"description": "Redirects harmful spells."},
        },
        {
            "talent": {"name": "Counterstrike Totem", "id": 708},
            "spell_tooltip": {"description": "Reflects damage."},
        },
    ],
}


@pytest.fixture
def client():
    auth = AsyncMock()
    auth.get_token.return_value = "test_token"
    return BnetClient(auth=auth, region="us")


@pytest.fixture
def store(tmp_db):
    return CacheStore(init_db(tmp_db))


@respx.mock
async def test_fetch_pvp_talents_returns_id_name_pairs(client):
    respx.get(SPEC_URL).mock(
        return_value=httpx.Response(
            200, json=SPEC_PAYLOAD, headers={"Battlenet-Namespace": NAMESPACE}
        )
    )

    talents, _ = await client.fetch_pvp_talents(264)

    assert talents == [
        {"id": 708, "name": "Counterstrike Totem"},
        {"id": 715, "name": "Grounding Totem"},
    ]


@respx.mock
async def test_fetch_pvp_talents_reports_game_build(client):
    respx.get(SPEC_URL).mock(
        return_value=httpx.Response(
            200, json=SPEC_PAYLOAD, headers={"Battlenet-Namespace": NAMESPACE}
        )
    )

    _, game_build = await client.fetch_pvp_talents(264)

    assert game_build == "12.1.0_68914"


def test_pool_roundtrips_through_the_store(store):
    talents = [{"id": 708, "name": "Counterstrike Totem"}]
    store.save_pvp_talent_pool("restoration-shaman", talents, game_build="12.1.0_68914")

    assert store.get_pvp_talent_pool("restoration-shaman") == talents


def test_missing_pool_reads_as_none(store):
    assert store.get_pvp_talent_pool("arms-warrior") is None


def test_pool_records_game_build(store):
    store.save_pvp_talent_pool("restoration-shaman", [], game_build="12.1.0_68914")

    assert store.pvp_talent_pool_game_build("restoration-shaman") == "12.1.0_68914"


def test_diff_reports_removed_talent():
    old = [{"id": 5407, "name": "Dying Stars"}, {"id": 184, "name": "Moon and Stars"}]
    new = [{"id": 184, "name": "Moon and Stars"}]

    assert diff_pvp_talent_pool(old, new)["removed"] == [
        {"id": 5407, "name": "Dying Stars"}
    ]


def test_diff_reports_added_talent():
    old = [{"id": 184, "name": "Moon and Stars"}]
    new = [{"id": 184, "name": "Moon and Stars"}, {"id": 5646, "name": "Tireless Pursuit"}]

    assert diff_pvp_talent_pool(old, new)["added"] == [
        {"id": 5646, "name": "Tireless Pursuit"}
    ]


def test_diff_reports_rename_under_a_stable_id():
    old = [{"id": 184, "name": "Moon and Stars"}]
    new = [{"id": 184, "name": "Sun and Stars"}]

    assert diff_pvp_talent_pool(old, new)["renamed"] == [
        {"id": 184, "from": "Moon and Stars", "to": "Sun and Stars"}
    ]


def test_identical_pools_diff_empty():
    pool = [{"id": 184, "name": "Moon and Stars"}]

    assert diff_pvp_talent_pool(pool, pool) == {"added": [], "removed": [], "renamed": []}


# --- Shared refresh routine -------------------------------------------------
#
# Both scripts/snapshot_pvp_talents.py and scripts/refresh_static_data.py drive
# this, so the fetch/diff/save sequence lives in one tested place.

from unittest.mock import MagicMock
from wow_advisor.processor.pvp_talents import refresh_pvp_talent_pools


class _FakeClient:
    """Returns a fixed pool per spec id, recording which ids were asked for."""

    def __init__(self, pools, game_build="12.1.0_68914"):
        self._pools = pools
        self._game_build = game_build
        self.requested = []

    async def fetch_pvp_talents(self, spec_id, locale="en_US"):
        self.requested.append(spec_id)
        return self._pools[spec_id], self._game_build


async def test_refresh_reports_new_baseline_for_unseen_spec(store):
    client = _FakeClient({264: [{"id": 715, "name": "Grounding Totem"}]})

    report = await refresh_pvp_talent_pools(
        store, client, ["restoration-shaman"], save=True
    )

    assert report["restoration-shaman"]["status"] == "new"


async def test_refresh_persists_only_when_asked(store):
    client = _FakeClient({264: [{"id": 715, "name": "Grounding Totem"}]})

    await refresh_pvp_talent_pools(store, client, ["restoration-shaman"], save=False)

    assert store.get_pvp_talent_pool("restoration-shaman") is None


async def test_refresh_reports_diff_against_stored_pool(store):
    store.save_pvp_talent_pool(
        "restoration-shaman",
        [{"id": 715, "name": "Grounding Totem"}, {"id": 999, "name": "Gone"}],
        game_build="12.0.5_67000",
    )
    client = _FakeClient({264: [{"id": 715, "name": "Grounding Totem"}]})

    report = await refresh_pvp_talent_pools(
        store, client, ["restoration-shaman"], save=True
    )

    entry = report["restoration-shaman"]
    assert entry["status"] == "changed"
    assert entry["diff"]["removed"] == [{"id": 999, "name": "Gone"}]


async def test_refresh_reports_unchanged(store):
    pool = [{"id": 715, "name": "Grounding Totem"}]
    store.save_pvp_talent_pool("restoration-shaman", pool, game_build="12.1.0_68914")
    client = _FakeClient({264: pool})

    report = await refresh_pvp_talent_pools(
        store, client, ["restoration-shaman"], save=True
    )

    assert report["restoration-shaman"]["status"] == "unchanged"


async def test_refresh_skips_specs_missing_from_the_spec_map(store):
    client = _FakeClient({})

    report = await refresh_pvp_talent_pools(store, client, ["not-a-real-spec"], save=True)

    assert report["not-a-real-spec"]["status"] == "unknown-spec"
    assert client.requested == []
