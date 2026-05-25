import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from wow_advisor.tools.fetch import fetch_top_players_async

@pytest.mark.asyncio
async def test_fetch_top_players_async_cache_hit():
    """Test fetch_top_players_async returns cached data when not stale."""
    spec = "restoration shaman"
    bracket = "3v3"
    region = "us"
    locale = "en_US"
    
    # Mock data to return from store
    cached_agg = {
        "sample_size": 50,
        "cached_at": 123456789,
        "spec": "restoration shaman",
        "bracket": "3v3"
    }

    with patch("wow_advisor.tools.fetch.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.fetch.CacheStore") as mock_store_class:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store
        
        # Mock CacheStore.is_stale to return False (cache hit)
        mock_store.is_stale.return_value = False
        mock_store.get_aggregation.return_value = cached_agg
        
        result = await fetch_top_players_async(spec, bracket, region=region, locale=locale)
        
        assert result["fetched"] == 50
        assert result["cached_at"] == 123456789
        assert result["spec"] == "restoration-shaman"
        assert result["bracket"] == "3v3"
        assert result["skipped"] is True
        
        mock_store.is_stale.assert_called_once_with(
            "restoration-shaman", "3v3", "us", ttl_hours=2, locale=locale
        )
        mock_store.get_aggregation.assert_called_once_with(
            "restoration-shaman", "3v3", "us", locale=locale
        )

@pytest.mark.asyncio
async def test_fetch_top_players_async_full_success():
    """Test full success flow when cache is stale."""
    spec = "restoration shaman"
    bracket = "3v3"
    region = "us"
    locale = "en_US"
    limit = 2
    
    from wow_advisor.api.models import CharacterData, LeaderboardEntry, TalentData

    mock_leaderboard = [
        LeaderboardEntry(rank=1, rating=3000, name="Player1", realm="Realm1"),
        LeaderboardEntry(rank=2, rating=2900, name="Player2", realm="Realm2"),
    ]
    
    # Mock character data for Phase 1 (spec-only)
    # Shaman = 7, Restoration = 264
    char1_phase1 = CharacterData(
        name="Player1", realm="Realm1", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=3000, class_id=7, spec_id=264
    )
    char2_phase1 = CharacterData(
        name="Player2", realm="Realm2", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=2900, class_id=7, spec_id=264
    )
    
    # Mock character data for Phase 2 (full details)
    char1_full = CharacterData(
        name="Player1", realm="Realm1", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=3000, class_id=7, spec_id=264, 
        talent=TalentData(loadout_code="abc", spec_node_ids=[1, 2, 3])
    )
    char2_full = CharacterData(
        name="Player2", realm="Realm2", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=2900, class_id=7, spec_id=264, 
        talent=TalentData(loadout_code="def", spec_node_ids=[4, 5, 6])
    )

    mock_agg = {"sample_size": 2, "spec": "restoration-shaman"}

    with patch("wow_advisor.tools.fetch.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.fetch.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.fetch._make_client") as mock_make_client, \
         patch("wow_advisor.tools.fetch.build_aggregation") as mock_build_agg:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store
        mock_store.is_stale.return_value = True
        
        mock_client = MagicMock()
        mock_client.fetch_leaderboard = AsyncMock(return_value=mock_leaderboard)
        mock_client.fetch_character_spec = AsyncMock(side_effect=[char1_phase1, char2_phase1])
        mock_client.fetch_character_details = AsyncMock(side_effect=[char1_full, char2_full])
        
        mock_make_client.return_value = (MagicMock(), mock_client)
        mock_build_agg.return_value = mock_agg
        
        result = await fetch_top_players_async(spec, bracket, region=region, limit=limit, locale=locale)
        
        assert result["fetched"] == 2
        assert result["spec"] == "restoration-shaman"
        assert "cached_at" in result
        
        # Verify store calls
        mock_store.save_players.assert_called_once()
        mock_store.save_aggregation.assert_called_once_with(
            spec="restoration-shaman",
            bracket="3v3",
            region="us",
            data=mock_agg,
            locale=locale
        )
        
        # Verify client calls
        mock_client.fetch_leaderboard.assert_called_once_with(bracket="3v3")
        assert mock_client.fetch_character_spec.call_count == 2
        assert mock_client.fetch_character_details.call_count == 2

@pytest.mark.asyncio
async def test_fetch_top_players_async_partial_results():
    """Test when fewer than 'limit' players are found matching the spec."""
    spec = "restoration shaman"
    bracket = "3v3"
    region = "us"
    locale = "en_US"
    limit = 10 # Request 10
    
    from wow_advisor.api.models import CharacterData, LeaderboardEntry, TalentData

    # Leaderboard has only 3 entries
    mock_leaderboard = [
        LeaderboardEntry(rank=1, rating=3000, name="Shaman1", realm="Realm1"),
        LeaderboardEntry(rank=2, rating=2900, name="Warrior1", realm="Realm2"),
        LeaderboardEntry(rank=3, rating=2800, name="Shaman2", realm="Realm3"),
    ]
    
    # Mock character data for Phase 1
    char1_match = CharacterData(
        name="Shaman1", realm="Realm1", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=3000, class_id=7, spec_id=264
    )
    char2_mismatch = CharacterData(
        name="Warrior1", realm="Realm2", region="us", character_class="Warrior", 
        spec="Arms", equipped_ilvl=630, rating=2900, class_id=1, spec_id=71
    )
    char3_match = CharacterData(
        name="Shaman2", realm="Realm3", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=2800, class_id=7, spec_id=264
    )
    
    # Mock character data for Phase 2
    char1_full = CharacterData(
        name="Shaman1", realm="Realm1", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=3000, class_id=7, spec_id=264, 
        talent=TalentData(loadout_code="abc", spec_node_ids=[1])
    )
    char3_full = CharacterData(
        name="Shaman2", realm="Realm3", region="us", character_class="Shaman", 
        spec="Restoration", equipped_ilvl=630, rating=2800, class_id=7, spec_id=264, 
        talent=TalentData(loadout_code="def", spec_node_ids=[2])
    )

    mock_agg = {"sample_size": 2, "spec": "restoration-shaman"}

    with patch("wow_advisor.tools.fetch.get_default_db") as mock_get_db, \
         patch("wow_advisor.tools.fetch.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.fetch._make_client") as mock_make_client, \
         patch("wow_advisor.tools.fetch.build_aggregation") as mock_build_agg:
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store
        mock_store.is_stale.return_value = True
        
        mock_client = MagicMock()
        mock_client.fetch_leaderboard = AsyncMock(return_value=mock_leaderboard)
        mock_client.fetch_character_spec = AsyncMock(side_effect=[char1_match, char2_mismatch, char3_match])
        mock_client.fetch_character_details = AsyncMock(side_effect=[char1_full, char3_full])
        
        mock_make_client.return_value = (MagicMock(), mock_client)
        mock_build_agg.return_value = mock_agg
        
        result = await fetch_top_players_async(spec, bracket, region=region, limit=limit, locale=locale)
        
        assert result["fetched"] == 2 # Only 2 found
        assert result["spec"] == "restoration-shaman"
        
        # Verify store calls
        mock_store.save_players.assert_called_once()
        assert len(mock_store.save_players.call_args[0][0]) == 2
        
        # Verify client calls
        assert mock_client.fetch_character_spec.call_count == 3
        assert mock_client.fetch_character_details.call_count == 2

@pytest.mark.asyncio
async def test_fetch_top_players_async_empty_leaderboard():
    """Test error handling when leaderboard is empty."""
    spec = "restoration shaman"
    bracket = "3v3"
    
    with patch("wow_advisor.tools.fetch.get_default_db"), \
         patch("wow_advisor.tools.fetch.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.fetch._make_client") as mock_make_client:
        
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store
        mock_store.is_stale.return_value = True
        
        mock_client = MagicMock()
        mock_client.fetch_leaderboard = AsyncMock(return_value=[]) # Empty
        mock_make_client.return_value = (MagicMock(), mock_client)
        
        result = await fetch_top_players_async(spec, bracket)
        
        assert "error" in result
        assert "No leaderboard data" in result["error"]

@pytest.mark.asyncio
async def test_fetch_top_players_async_no_matches():
    """Test error handling when no players of the spec are found."""
    spec = "restoration shaman"
    bracket = "3v3"
    
    from wow_advisor.api.models import CharacterData, LeaderboardEntry
    mock_leaderboard = [LeaderboardEntry(rank=1, rating=3000, name="Warrior1", realm="Realm1")]
    char_mismatch = CharacterData(
        name="Warrior1", realm="Realm1", region="us", character_class="Warrior", 
        spec="Arms", equipped_ilvl=630, rating=3000, class_id=1, spec_id=71
    )

    with patch("wow_advisor.tools.fetch.get_default_db"), \
         patch("wow_advisor.tools.fetch.CacheStore") as mock_store_class, \
         patch("wow_advisor.tools.fetch._make_client") as mock_make_client:
        
        mock_store = MagicMock()
        mock_store_class.return_value = mock_store
        mock_store.is_stale.return_value = True
        
        mock_client = MagicMock()
        mock_client.fetch_leaderboard = AsyncMock(return_value=mock_leaderboard)
        mock_client.fetch_character_spec = AsyncMock(return_value=char_mismatch)
        mock_make_client.return_value = (MagicMock(), mock_client)
        
        result = await fetch_top_players_async(spec, bracket)
        
        assert "error" in result
        assert "Found 0" in result["error"]
