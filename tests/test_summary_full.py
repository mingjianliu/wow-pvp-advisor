import pytest
from unittest.mock import MagicMock, patch
from wow_advisor.tools.summary import get_full_summary

@pytest.fixture
def mock_store():
    with patch("wow_advisor.tools.summary.CacheStore") as mock:
        store = mock.return_value
        store.aggregation_game_build.return_value = None
        yield store

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
        instance.game_build.return_value = None
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


# --- Cross-build safety net -------------------------------------------------
#
# Aggregations store raw node IDs; Blizzard reassigns talents across node IDs
# between client builds (12.1 swapped Battlelord and Master Tactician on Arms).
# Applying current names to node IDs captured under an older build produces
# confidently wrong talent names, so names are withheld instead.

def _agg():
    return {
        "sample_size": 50,
        "talents": {"core_nodes": [101]},
        "gear": {},
        "enchants": {},
    }


def test_names_withheld_when_aggregation_predates_current_build(
    mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client
):
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = _agg()
    mock_store.aggregation_game_build.return_value = "12.0.5_67000"
    mock_name_cache.game_build.return_value = "12.1.0_68914"

    result = get_full_summary("rsham", "3v3")

    assert result["talents"]["core"][0]["name"] is None


def test_build_mismatch_is_reported(
    mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client
):
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = _agg()
    mock_store.aggregation_game_build.return_value = "12.0.5_67000"
    mock_name_cache.game_build.return_value = "12.1.0_68914"

    result = get_full_summary("rsham", "3v3")

    assert result["stale_build"] == {
        "aggregation": "12.0.5_67000",
        "current": "12.1.0_68914",
    }


def test_names_applied_when_builds_match(
    mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client
):
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = _agg()
    mock_store.aggregation_game_build.return_value = "12.1.0_68914"
    mock_name_cache.game_build.return_value = "12.1.0_68914"

    result = get_full_summary("rsham", "3v3")

    assert result["talents"]["core"][0]["name"] == "Test Talent 1"
    assert "stale_build" not in result


def test_names_applied_when_build_is_unknown(
    mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client
):
    """Nothing to compare against — degrade to the old behaviour, not to blanks."""
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = _agg()
    mock_store.aggregation_game_build.return_value = None
    mock_name_cache.game_build.return_value = None

    result = get_full_summary("rsham", "3v3")

    assert result["talents"]["core"][0]["name"] == "Test Talent 1"


def test_staleness_check_is_build_aware(
    mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client
):
    """A build change must reach is_stale so the normal refresh path repairs it."""
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = _agg()
    mock_store.aggregation_game_build.return_value = "12.1.0_68914"
    mock_name_cache.game_build.return_value = "12.1.0_68914"

    get_full_summary("rsham", "3v3")

    assert mock_store.is_stale.call_args.kwargs["game_build"] == "12.1.0_68914"


# --- Which ladder the sample came from --------------------------------------

def test_summary_reports_the_season_the_sample_came_from(
    mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client
):
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = {**_agg(), "season_id": 42, "season_fallback": False}

    result = get_full_summary("rsham", "3v3")

    assert result["season_id"] == 42
    assert "season_fallback" not in result


def test_summary_flags_a_previous_season_sample(
    mock_store, mock_fetch, mock_db, mock_name_cache, mock_make_client
):
    """A new season's ladder is empty on day one, so the sample may be last season's."""
    mock_store.is_stale.return_value = False
    mock_store.get_aggregation.return_value = {**_agg(), "season_id": 41, "season_fallback": True}

    result = get_full_summary("rsham", "3v3")

    assert result["season_id"] == 41
    assert result["season_fallback"] is True
