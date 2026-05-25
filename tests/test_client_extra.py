import pytest
import respx
import httpx
from wow_advisor.api.models import CharacterData
from wow_advisor.api.client import BnetClient

@pytest.fixture
def mock_auth():
    from unittest.mock import AsyncMock
    auth = AsyncMock()
    auth.get_token.return_value = "test_token"
    return auth

@pytest.fixture
def client(mock_auth):
    return BnetClient(auth=mock_auth, region="us")

@respx.mock
async def test_fetch_character_spec(client):
    # Phase 1 calls _get for profile index, then specializations
    respx.get("https://us.api.blizzard.com/profile/wow/character/area-52/healbot").mock(
        return_value=httpx.Response(200, json={
            "character_class": {"name": "Shaman"},
            "active_spec": {"id": 264, "name": "Restoration"}
        })
    )
    respx.get("https://us.api.blizzard.com/profile/wow/character/area-52/healbot/specializations").mock(
        return_value=httpx.Response(200, json={
            "specializations": [{
                "specialization": {"id": 264, "name": "Restoration"},
                "loadouts": [{"is_active": True, "talent_loadout_code": "code"}]
            }]
        })
    )
    
    char = CharacterData(
        name="healbot", 
        realm="area-52", 
        rating=2800,
        region="us",
        character_class="Shaman",
        spec="Restoration",
        equipped_ilvl=639
    )
    async with httpx.AsyncClient() as http_client:
        updated = await client.fetch_character_spec(http_client, "healbot", "area-52", 2800)
    
    assert updated is not None
    assert updated.spec_id == 264
    assert updated.spec == "Restoration"

@respx.mock
async def test_fetch_character_details(client):
    respx.get("https://us.api.blizzard.com/profile/wow/character/area-52/healbot/specializations").mock(
        return_value=httpx.Response(200, json={
            "specializations": [{
                "specialization": {"id": 264, "name": "Restoration"},
                "loadouts": [{"is_active": True, "talent_loadout_code": "code", "selected_class_talents": [{"id": 1}]}]
            }]
        })
    )
    respx.get("https://us.api.blizzard.com/profile/wow/character/area-52/healbot/equipment").mock(
        return_value=httpx.Response(200, json={"equipped_items": []})
    )
    
    char = CharacterData(
        name="healbot", 
        realm="area-52", 
        rating=2800, 
        spec_id=264,
        region="us",
        character_class="Shaman",
        spec="Restoration",
        equipped_ilvl=639
    )
    updated = await client.fetch_character_details(name="healbot", realm="area-52", char=char)
    
    assert updated.talent is not None
    assert 1 in updated.talent.class_node_ids

def test_parse_gear_edge_cases():
    from wow_advisor.api.client import _parse_gear
    # Test with no enchants
    items = [{
        "slot": {"type": "HEAD"},
        "item": {"id": 123},
        "name": "Test Item",
        "level": {"value": 100}
    }]
    slots = _parse_gear(items)
    assert len(slots) == 1
    assert slots[0].enchant_id is None
    
    # Test with icon embedding in enchant name
    items_with_icon = [{
        "slot": {"type": "HEAD"},
        "item": {"id": 123},
        "name": "Test Item",
        "level": {"value": 100},
        "enchantments": [{"enchantment_id": 1, "display_string": "|A:icon:0|a Enchant Name"}]
    }]
    slots = _parse_gear(items_with_icon)
    assert slots[0].enchant_name == "Enchant Name"
