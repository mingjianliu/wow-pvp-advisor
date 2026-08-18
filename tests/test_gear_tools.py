import pytest
from unittest.mock import MagicMock, patch
from wow_advisor.tools.gear import get_gear_summary, get_player_details

def test_get_gear_summary_cached_success():
    mock_agg = {
        "sample_size": 100,
        "avg_ilvl": 630.5,
        "cached_at": 123456789,
        "gear": {"head": [{"item_id": 1001, "name": "Cool Hat", "pct": 90.0}]},
        "enchants": {"head": [{"enchant_id": 2001, "name": "Enchanted Int", "pct": 80.0}]}
    }
    
    with patch("wow_advisor.tools.gear.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.gear.CacheStore") as mock_store_class:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = False
        mock_store.get_aggregation.return_value = mock_agg
        mock_store_class.return_value = mock_store
        
        result = get_gear_summary("restoration shaman", "3v3")
        
        assert result["spec"] == "restoration-shaman"
        assert result["bracket"] == "3v3"
        assert result["sample_size"] == 100
        assert result["avg_ilvl"] == 630.5
        assert result["gear"]["head"][0]["name"] == "Cool Hat"
        mock_store.is_stale.assert_called_once()

def test_get_gear_summary_trigger_fetch():
    mock_agg = {
        "sample_size": 50,
        "avg_ilvl": 625.0,
        "gear": {},
        "enchants": {}
    }
    
    with patch("wow_advisor.tools.gear.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.gear.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.gear.fetch_top_players") as mock_fetch:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = True
        mock_store.get_aggregation.return_value = mock_agg
        mock_store_class.return_value = mock_store
        
        mock_fetch.return_value = {"fetched": 50}
        
        result = get_gear_summary("restoration shaman", "3v3")
        
        assert result["spec"] == "restoration-shaman"
        assert result["sample_size"] == 50
        mock_fetch.assert_called_once_with(spec="restoration-shaman", bracket="3v3", region="us", locale="en_US")

def test_get_gear_summary_fetch_error():
    with patch("wow_advisor.tools.gear.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.gear.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.gear.fetch_top_players") as mock_fetch:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = True
        mock_store_class.return_value = mock_store
        
        mock_fetch.return_value = {"error": "API rate limited"}
        
        result = get_gear_summary("restoration shaman", "3v3")
        
        assert "error" in result
        assert result["error"] == "API rate limited"

def test_get_gear_summary_missing_data():
    with patch("wow_advisor.tools.gear.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.gear.CacheStore") as mock_store_class:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = False
        mock_store.get_aggregation.return_value = None
        mock_store_class.return_value = mock_store
        
        result = get_gear_summary("restoration shaman", "3v3")
        
        assert "error" in result
        assert "No data for" in result["error"]

def test_get_player_details_found():
    mock_row = {
        "name": "Testplayer",
        "realm": "Sargeras",
        "spec": "restoration-shaman",
        "character_class": "Shaman",
        "rating": 2400,
        "equipped_ilvl": 630,
        "talent_code": "mockcode",
        "class_node_ids": "[1, 2]",
        "spec_node_ids": "[3, 4]",
        "hero_node_ids": "[5]",
        "gear": '[{"slot": "Head", "item_id": 1001}]'
    }
    
    with patch("wow_advisor.tools.gear.get_default_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.execute().fetchall.return_value = [mock_row]
        
        result = get_player_details("Testplayer", "Sargeras")
        
        assert result["name"] == "Testplayer"
        assert result["realm"] == "Sargeras"
        assert result["class_node_ids"] == [1, 2]
        assert result["gear"][0]["slot"] == "Head"

def test_get_player_details_not_found():
    with patch("wow_advisor.tools.gear.get_default_db") as mock_get_db:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.execute().fetchall.return_value = []
        
        result = get_player_details("Nonexistent", "Realm")
        
        assert "error" in result
        assert "not found in cache" in result["error"]


def test_gear_summary_staleness_is_build_aware():
    """Gear rides along on the same aggregation row as talents.

    The row is refreshed as a unit, so it has to be invalidated as a unit —
    otherwise a build change leaves gear pinned to a pre-patch sample.
    """
    from unittest.mock import MagicMock, patch
    from wow_advisor.tools.gear import get_gear_summary

    with patch("wow_advisor.tools.gear.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.gear.CacheStore") as mock_store_class, \
         patch("wow_advisor.processor.talent_names.TalentNameCache") as mock_cache_class:

        mock_get_db.return_value = MagicMock()
        mock_store = MagicMock()
        mock_store.is_stale.return_value = False
        mock_store.get_aggregation.return_value = {"sample_size": 1}
        mock_store_class.return_value = mock_store
        mock_cache_class.return_value.game_build.return_value = "12.1.0_68914"

        get_gear_summary("restoration shaman", "3v3")

        assert mock_store.is_stale.call_args.kwargs["game_build"] == "12.1.0_68914"
