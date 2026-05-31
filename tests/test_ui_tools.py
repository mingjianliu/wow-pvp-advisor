import pytest
import json
import re
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, AsyncMock
from wow_advisor.tools.ui import build_page, _make_cluster_data, _bundle_html, DynamicReportHandler

def test_dynamic_report_handler_translate_path():
    # We need to mock get_pages_dir and get_frontend_dir
    with patch("wow_advisor.tools.ui.get_pages_dir") as mock_pages_dir, \
         patch("wow_advisor.tools.ui.get_frontend_dir") as mock_frontend_dir, \
         patch("wow_advisor.tools.ui.build_page") as mock_build:
        
        mock_pages_dir.return_value = Path("/tmp/pages")
        mock_frontend_dir.return_value = Path("/tmp/frontend")
        mock_build.return_value = {"path": "/tmp/pages/restoration-shaman_3v3.html"}
        
        handler = MagicMock(spec=DynamicReportHandler)
        handler.directory = "/tmp/frontend"
        
        # Scenario: File does not exist
        with patch("pathlib.Path.exists", return_value=False):
            # Calling the real method logic manually since we can't easily instantiate a full handler
            result = DynamicReportHandler.translate_path(handler, "/pages/restoration-shaman_3v3.html")
            assert "restoration-shaman_3v3.html" in result
            # It should have triggered build_page
            mock_build.assert_called_once()
        
        mock_build.reset_mock()
        
        # Scenario: File is too old
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 0 # Epoch
            result = DynamicReportHandler.translate_path(handler, "/pages/restoration-shaman_3v3.html")
            assert "restoration-shaman_3v3.html" in result
            mock_build.assert_called_once()

@pytest.fixture
def mock_summary_data():
    return {
        "spec": "restoration-shaman",
        "bracket": "3v3",
        "sample_size": 100,
        "avg_ilvl": 630.5,
        "pvp_talents": [{"id": 123, "name": "PvP Talent 1", "pct": 95.0}],
        "talents": {
            "core": [{"id": 1, "name": "Talent 1", "pct": 100.0, "pts": 1}],
            "flex": [],
            "contested": [],
            "clusters": [
                {
                    "rank": 1, "pct": 80.0, "count": 80, "canonical_code": "code1",
                    "takes": [{"id": 1, "pct": 100.0}], "skips": [], "flex_takes": [],
                    "pickers": [{"n": "Alice", "r": "kelthuzad"}, {"n": "Bob", "r": "tichondrius"}]
                }
            ]
        },
        "gear": {
            "head": [{"item_id": 1001, "name": "Cool Hat", "pct": 90.0}]
        },
        "enchants": {
            "head": [{"enchant_id": 2001, "name": "Enchanted Int", "pct": 80.0}]
        }
    }

@pytest.fixture
def mock_tree_data():
    return {
        "trees": [
            {
                "nodes": [
                    {"id": 1, "name": "Talent 1", "spellId": 101}
                ]
            }
        ],
        "heroTrees": {
            "left": {"nodes": [{"id": 50, "name": "Hero 1", "spellId": 501}]},
            "right": {"nodes": [{"id": 60, "name": "Hero 2", "spellId": 601}]}
        }
    }

def test_make_cluster_data(mock_summary_data, mock_tree_data):
    result = _make_cluster_data(mock_summary_data, mock_tree_data)
    
    assert result["spec"] == "restoration-shaman"
    assert result["sample_size"] == 100
    assert result["gear"]["slots"][0]["slot"] == "Head"
    assert result["gear"]["slots"][0]["item"]["name"] == "Cool Hat"
    # Enchant name "Enchanted Int" should be stripped to "Int"
    assert result["gear"]["slots"][0]["enchant"]["name"] == "Int"
    assert len(result["clusters"]) == 1
    assert result["clusters"][0]["takes"][0]["name"] == "Talent 1"
    # The cluster member list must propagate to the frontend so cluster-aware
    # pick-rate ratios can be computed. Regression guard for dropped `pickers`.
    assert result["clusters"][0]["pickers"] == [
        {"n": "Alice", "r": "kelthuzad"},
        {"n": "Bob", "r": "tichondrius"},
    ]

@patch("pathlib.Path.read_text")
def test_bundle_html(mock_read, mock_tree_data):
    def side_effect(encoding=None):
        if mock_read.call_count == 1:
            return '<html><link rel="stylesheet" href="styles.css"/><script src="tree-data.js"></script><script src="data.js"></script><script type="text/babel" src="app.jsx"></script></html>'
        if mock_read.call_count == 2:
            return "body { color: red; }"
        return "const App = () => <div>Hi</div>;"

    mock_read.side_effect = side_effect
    
    cluster_data = {"spec": "test-spec", "clusters": []}
    html = _bundle_html(cluster_data, mock_tree_data)
    
    assert "<style>\nbody { color: red; }\n</style>" in html
    assert "window.CLUSTER_DATA =" in html
    assert "const App = () => <div>Hi</div>;" in html
    assert 'src="app.jsx"' not in html

@patch("wow_advisor.tools.ui.get_full_summary")
@patch("wow_advisor.tools.ui.get_tree_structure")
@patch("wow_advisor.tools.ui._bundle_html")
@patch("wow_advisor.tools.ui._ensure_server")
@patch("wow_advisor.tools.ui._open_browser")
@patch("wow_advisor.tools.ui.prefetch_tooltips")
@patch("wow_advisor.cache.store.CacheStore.get_players")
@patch("pathlib.Path.write_text")
@patch("wow_advisor.tools.ui.get_pages_dir")
@patch("wow_advisor.cache.db.get_default_db")
def test_build_page_success(mock_db, mock_pages_dir, mock_write, mock_get_players, 
                            mock_prefetch, mock_open_browser, mock_ensure_server, 
                            mock_bundle, mock_tree, mock_summary, 
                            mock_summary_data, mock_tree_data):
    
    mock_pages_dir.return_value = Path("/tmp/pages")
    mock_summary.return_value = mock_summary_data
    mock_tree.return_value = mock_tree_data
    mock_bundle.return_value = "<html>test</html>"
    mock_prefetch.side_effect = AsyncMock(return_value={})
    mock_get_players.return_value = []
    
    result = build_page("restoration-shaman", "3v3", open_browser=False)
    
    assert result["spec"] == "restoration-shaman"
    assert result["bracket"] == "3v3"
    assert "url" in result
    assert "restoration-shaman_3v3.html" in result["path"]
    
    # We call write_text once in build_page
    mock_write.assert_called_once_with("<html>test</html>", encoding="utf-8")
    mock_ensure_server.assert_called_once()
    mock_open_browser.assert_not_called()

@patch("wow_advisor.tools.ui.get_full_summary")
def test_build_page_error(mock_summary):
    mock_summary.return_value = {"error": "Not Found"}
    result = build_page("invalid", "3v3")
    assert result == {"error": "Not Found"}

@patch("wow_advisor.tools.ui.get_full_summary")
@patch("wow_advisor.tools.ui.get_tree_structure")
@patch("wow_advisor.tools.ui._bundle_html")
@patch("wow_advisor.tools.ui._ensure_server")
@patch("wow_advisor.tools.ui._open_browser")
@patch("wow_advisor.tools.ui.prefetch_tooltips")
@patch("wow_advisor.cache.store.CacheStore.get_players")
@patch("pathlib.Path.write_text")
@patch("wow_advisor.tools.ui.get_pages_dir")
@patch("wow_advisor.cache.db.get_default_db")
def test_build_page_with_players(mock_db, mock_pages_dir, mock_write, mock_get_players,
                                 mock_prefetch, mock_open_browser, mock_ensure_server, 
                                 mock_bundle, mock_tree, mock_summary, 
                                 mock_summary_data, mock_tree_data):
    mock_pages_dir.return_value = Path("/tmp/pages")
    mock_summary.return_value = mock_summary_data
    mock_tree.return_value = mock_tree_data
    mock_bundle.return_value = "<html>test</html>"
    mock_prefetch.side_effect = AsyncMock(return_value={})
    
    # Mock player objects
    mock_player = MagicMock()
    mock_player.name = "PlayerOne"
    mock_player.realm = "RealmOne"
    mock_player.region = "us"
    mock_player.character_class = "Shaman"
    mock_player.spec = "restoration-shaman"
    mock_player.equipped_ilvl = 630
    mock_player.rating = 2400
    mock_player.talent = None
    mock_player.gear = []
    
    mock_get_players.return_value = [mock_player]
    
    result = build_page("restoration-shaman", "3v3", open_browser=False)
    
    # Verify that _bundle_html was called with cluster_data containing players
    args, kwargs = mock_bundle.call_args
    cluster_data = args[0]
    assert "players" in cluster_data
    assert len(cluster_data["players"]) == 1
    assert cluster_data["players"][0]["name"] == "PlayerOne"

@patch("wow_advisor.tools.ui.get_full_summary")
@patch("wow_advisor.tools.ui.get_tree_structure")
@patch("wow_advisor.tools.ui._bundle_html")
@patch("wow_advisor.tools.ui._ensure_server")
@patch("wow_advisor.tools.ui._open_browser")
@patch("wow_advisor.tools.ui.prefetch_tooltips")
@patch("wow_advisor.cache.store.CacheStore.get_players")
@patch("pathlib.Path.write_text")
@patch("wow_advisor.tools.ui.get_pages_dir")
@patch("wow_advisor.cache.db.get_default_db")
def test_build_page_localization(mock_db, mock_pages_dir, mock_write, mock_get_players,
                                 mock_prefetch, mock_open_browser, mock_ensure_server, 
                                 mock_bundle, mock_tree, mock_summary, 
                                 mock_summary_data, mock_tree_data):
    mock_pages_dir.return_value = Path("/tmp/pages")
    mock_summary.return_value = mock_summary_data
    mock_tree.return_value = mock_tree_data
    mock_bundle.return_value = "<html>test</html>"
    mock_prefetch.side_effect = AsyncMock(return_value={})
    mock_get_players.return_value = []
    
    # Check zh_CN suffix and bracket mapping for solo shuffle
    build_page("restoration-shaman", "solo shuffle", locale="zh_CN", open_browser=False)
    
    expected_path = Path("/tmp/pages") / "restoration-shaman_solo-shuffle_zh.html"
    
    # Find the write_text call that matches our expected path
    # Path objects comparison might be tricky with mocks, so we check the parent call
    found = False
    for call in mock_write.call_args_list:
        # The call is on the Path object returned by Path / filename
        # In our case, mock_pages_dir.return_value / filename
        pass
    
    # Instead, let's check the result path
    result = build_page("restoration-shaman", "solo shuffle", locale="zh_CN", open_browser=False)
    assert "restoration-shaman_solo-shuffle_zh.html" in result["path"]

    # Check blitz
    result = build_page("restoration-shaman", "rated blitz", open_browser=False)
    assert "restoration-shaman_blitz.html" in result["path"]
