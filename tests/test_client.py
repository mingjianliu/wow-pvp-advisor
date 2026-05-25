import pytest
import respx
import httpx
from unittest.mock import AsyncMock
from wow_advisor.api.client import BnetClient


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
