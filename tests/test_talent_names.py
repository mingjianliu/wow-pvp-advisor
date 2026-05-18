import json
import time
from unittest.mock import AsyncMock

import pytest

from wow_advisor.cache.db import init_db
from wow_advisor.processor.talent_names import TalentNameCache


SAMPLE_NODES = {
    100: {"name": "Lightning Bolt", "row": 1, "col": 3, "type": "single",
          "max_rank": 1, "icon": "123", "children": []},
    101: {"name": "Chain Lightning", "row": 2, "col": 3, "type": "single",
          "max_rank": 1, "icon": "124", "children": []},
}
LAST_MODIFIED = "Mon, 01 Jan 2026 00:00:00 GMT"


@pytest.fixture
def db(tmp_db):
    return init_db(tmp_db)


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.fetch_talent_tree_id = AsyncMock(return_value=(786, LAST_MODIFIED))
    client.fetch_talent_nodes = AsyncMock(return_value=(SAMPLE_NODES, LAST_MODIFIED, True))
    return client


def test_fresh_fetch_returns_nodes(db, mock_client):
    result = TalentNameCache(db).resolve("restoration shaman", mock_client)
    assert result[100]["name"] == "Lightning Bolt"
    assert result[101]["name"] == "Chain Lightning"


def test_fresh_fetch_persists_to_db(db, mock_client):
    TalentNameCache(db).resolve("restoration shaman", mock_client)
    row = db.execute(
        "SELECT nodes_json FROM talent_node_cache WHERE spec=?", ("restoration shaman",)
    ).fetchone()
    assert row is not None
    assert "100" in json.loads(row["nodes_json"])


def test_cache_hit_within_1h_makes_no_api_calls(db, mock_client):
    cache = TalentNameCache(db)
    cache.resolve("restoration shaman", mock_client)
    mock_client.reset_mock()
    cache.resolve("restoration shaman", mock_client)
    mock_client.fetch_talent_tree_id.assert_not_called()
    mock_client.fetch_talent_nodes.assert_not_called()


def test_stale_cache_304_updates_checked_at_only(db, mock_client):
    cache = TalentNameCache(db)
    cache.resolve("restoration shaman", mock_client)
    old_time = int(time.time()) - 7200
    db.execute(
        "UPDATE talent_node_cache SET checked_at=? WHERE spec=?", (old_time, "restoration shaman")
    )
    db.commit()
    mock_client.reset_mock()
    mock_client.fetch_talent_nodes = AsyncMock(return_value=({}, None, False))
    result = cache.resolve("restoration shaman", mock_client)
    assert result[100]["name"] == "Lightning Bolt"
    row = db.execute(
        "SELECT nodes_json, checked_at FROM talent_node_cache WHERE spec=?", ("restoration shaman",)
    ).fetchone()
    assert row["checked_at"] > old_time
    assert "100" in json.loads(row["nodes_json"])


def test_stale_cache_200_refreshes_nodes(db, mock_client):
    cache = TalentNameCache(db)
    cache.resolve("restoration shaman", mock_client)
    old_time = int(time.time()) - 7200
    db.execute(
        "UPDATE talent_node_cache SET checked_at=? WHERE spec=?", (old_time, "restoration shaman")
    )
    db.commit()
    mock_client.reset_mock()
    new_nodes = {
        200: {"name": "New Talent", "row": 1, "col": 1, "type": "single",
              "max_rank": 1, "icon": None, "children": []}
    }
    mock_client.fetch_talent_nodes = AsyncMock(
        return_value=(new_nodes, "Mon, 02 Feb 2026 00:00:00 GMT", True)
    )
    result = cache.resolve("restoration shaman", mock_client)
    assert 200 in result
    assert 100 not in result


def test_unknown_spec_returns_empty(db, mock_client):
    result = TalentNameCache(db).resolve("nonexistent spec xyzzy", mock_client)
    assert result == {}
    mock_client.fetch_talent_tree_id.assert_not_called()


def test_api_error_returns_empty(db, mock_client):
    mock_client.fetch_talent_tree_id = AsyncMock(side_effect=RuntimeError("API down"))
    result = TalentNameCache(db).resolve("restoration shaman", mock_client)
    assert result == {}
