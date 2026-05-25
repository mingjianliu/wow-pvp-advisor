import pytest
from unittest.mock import MagicMock, patch
from wow_advisor.tools.summary import get_full_summary

@pytest.fixture
def mock_store():
    with patch("wow_advisor.tools.summary.CacheStore") as mock:
        yield mock.return_value

@pytest.fixture
def mock_fetch():
    with patch("wow_advisor.tools.summary.fetch_top_players") as mock:
        yield mock

@pytest.fixture
def mock_db():
    with patch("wow_advisor.tools.summary.get_default_db") as mock:
        yield mock.return_value

# We need to mock these inside the function scope where they are imported
@pytest.fixture
def mock_name_cache():
    with patch("wow_advisor.processor.talent_names.TalentNameCache") as mock:
        instance = mock.return_value
        instance.resolve.return_value = {
            101: {"name": "Test Talent 1"},
            201: {"name": "Test Talent 2"}
        }
        yield instance

@pytest.fixture
def mock_make_client():
    with patch("wow_advisor.tools.fetch._make_client") as mock:
        mock.return_value = (MagicMock(), MagicMock())
        yield mock

def test_get_full_summary_fresh_cache(mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client):
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = {
        "sample_size": 50,
        "talents": {"core_nodes": [101]},
        "gear": {},
        "enchants": {}
    }
    
    result = get_full_summary("rsham", "3v3")
    
    assert "error" not in result
    assert result["sample_size"] == 50
    assert not mock_fetch.called
    # Check enrichment
    assert result["talents"]["core"][0]["name"] == "Test Talent 1"

def test_get_full_summary_stale_cache(mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client):
    mock_store.is_stale.return_value = True
    mock_fetch.return_value = {"fetched": 50}
    mock_store.get_aggregation.return_value = {"sample_size": 50}
    
    result = get_full_summary("rsham", "3v3")
    
    assert "error" not in result
    assert mock_fetch.called

def test_get_full_summary_fetch_error(mock_store, mock_fetch, mock_db, mock_make_client):
    mock_store.is_stale.return_value = True
    mock_fetch.return_value = {"error": "API Down"}
    
    result = get_full_summary("rsham", "3v3")
    
    assert result == {"error": "API Down"}

def test_get_full_summary_missing_agg(mock_store, mock_fetch, mock_db, mock_make_client):
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = None
    
    result = get_full_summary("rsham", "3v3")
    
    assert "error" in result
    assert "No data" in result["error"]
