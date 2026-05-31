import pytest
from unittest.mock import MagicMock, patch
from wow_advisor.tools.talents import get_talent_distribution

def test_get_talent_distribution_cached_success():
    mock_agg = {
        "sample_size": 100,
        "cached_at": 123456789,
        "talents": {"core": [{"id": 1, "pct": 100.0}]},
        "pvp_talents": [{"id": 10, "pct": 90.0}]
    }
    
    with patch("wow_advisor.tools.talents.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.talents.CacheStore") as mock_store_class:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = False
        mock_store.get_aggregation.return_value = mock_agg
        mock_store_class.return_value = mock_store
        
        result = get_talent_distribution("restoration shaman", "3v3")
        
        assert result["spec"] == "restoration-shaman"
        assert result["bracket"] == "3v3"
        assert result["sample_size"] == 100
        assert result["talents"]["core"][0]["id"] == 1
        assert result["pvp_talents"][0]["id"] == 10
        mock_store.is_stale.assert_called_once()

def test_get_talent_distribution_trigger_fetch():
    mock_agg = {
        "sample_size": 50,
        "talents": {},
        "pvp_talents": []
    }
    
    with patch("wow_advisor.tools.talents.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.talents.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.talents.fetch_top_players") as mock_fetch:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = True
        mock_store.get_aggregation.return_value = mock_agg
        mock_store_class.return_value = mock_store
        
        mock_fetch.return_value = {"fetched": 50}
        
        result = get_talent_distribution("restoration shaman", "3v3")
        
        assert result["spec"] == "restoration-shaman"
        assert result["sample_size"] == 50
        mock_fetch.assert_called_once_with(spec="restoration-shaman", bracket="3v3", region="us", locale="en_US")

def test_get_talent_distribution_fetch_error():
    with patch("wow_advisor.tools.talents.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.talents.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.talents.fetch_top_players") as mock_fetch:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = True
        mock_store_class.return_value = mock_store
        
        mock_fetch.return_value = {"error": "API rate limited"}
        
        result = get_talent_distribution("restoration shaman", "3v3")
        
        assert "error" in result
        assert result["error"] == "API rate limited"

def test_get_talent_distribution_missing_data():
    with patch("wow_advisor.tools.talents.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.talents.CacheStore") as mock_store_class:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store.is_stale.return_value = False
        mock_store.get_aggregation.return_value = None
        mock_store_class.return_value = mock_store
        
        result = get_talent_distribution("restoration shaman", "3v3")
        
        assert "error" in result
        assert "No data for" in result["error"]
