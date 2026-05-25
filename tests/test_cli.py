import sys
import json
from unittest.mock import patch, MagicMock
import pytest
from cli import main as root_main
from wow_advisor.cli import main as advisor_main

def test_root_cli_summary(capsys):
    with patch("cli.get_full_summary") as mock_summary:
        mock_summary.return_value = {"mock": "data"}
        with patch("sys.argv", ["cli.py", "summary", "rsham", "3v3"]):
            root_main()
            captured = capsys.readouterr()
            assert json.loads(captured.out) == {"mock": "data"}
            mock_summary.assert_called_once_with(spec="rsham", bracket="3v3", region="us")

def test_root_cli_fetch(capsys):
    with patch("cli.fetch_top_players") as mock_fetch:
        mock_fetch.return_value = ["player1"]
        with patch("sys.argv", ["cli.py", "fetch", "rsham", "3v3", "--limit", "10"]):
            root_main()
            captured = capsys.readouterr()
            assert "Fetching top 10 rsham players" in captured.out
            # The JSON starts after the first line and might be multi-line due to indent=2
            json_str = "\n".join(captured.out.split("\n")[1:])
            assert json.loads(json_str) == ["player1"]
            mock_fetch.assert_called_once_with(spec="rsham", bracket="3v3", region="us", limit=10)

def test_root_cli_talents(capsys):
    with patch("cli.get_talent_distribution") as mock_talents:
        mock_talents.return_value = {"talents": []}
        with patch("sys.argv", ["cli.py", "talents", "rsham", "3v3"]):
            root_main()
            captured = capsys.readouterr()
            assert json.loads(captured.out) == {"talents": []}
            mock_talents.assert_called_once_with(spec="rsham", bracket="3v3", region="us")

def test_root_cli_gear(capsys):
    with patch("cli.get_gear_summary") as mock_gear:
        mock_gear.return_value = {"gear": []}
        with patch("sys.argv", ["cli.py", "gear", "rsham", "3v3"]):
            root_main()
            captured = capsys.readouterr()
            assert json.loads(captured.out) == {"gear": []}
            mock_gear.assert_called_once_with(spec="rsham", bracket="3v3", region="us")

def test_root_cli_player(capsys):
    with patch("cli.get_player_details") as mock_player:
        mock_player.return_value = {"name": "Test"}
        with patch("sys.argv", ["cli.py", "player", "Test", "Realm"]):
            root_main()
            captured = capsys.readouterr()
            assert json.loads(captured.out) == {"name": "Test"}
            mock_player.assert_called_once_with(name="Test", realm="Realm", region="us")

def test_advisor_cli_normal(capsys):
    with patch("wow_advisor.config.has_credentials", return_value=True), \
         patch("wow_advisor.config.load_config"), \
         patch("wow_advisor.tools.ui.build_page") as mock_build:
        
        mock_build.return_value = {
            "spec": "restoration shaman",
            "bracket": "3v3",
            "sample_size": 50,
            "clusters": 3,
            "path": "/tmp/test.html",
            "url": "http://localhost:8080/pages/test.html"
        }
        
        with patch("sys.argv", ["wow-advisor", "rsham", "3v3"]):
            advisor_main()
            captured = capsys.readouterr()
            assert "Building page for 'rsham' / 3v3 [us] ..." in captured.out
            assert "Spec:     restoration shaman" in captured.out
            assert "Browser opened." in captured.out
            mock_build.assert_called_once_with("rsham", "3v3", "us")

def test_advisor_cli_no_open(capsys):
    with patch("wow_advisor.config.has_credentials", return_value=True), \
         patch("wow_advisor.config.load_config"), \
         patch("wow_advisor.tools.ui.build_page") as mock_build:
        
        mock_build.return_value = {
            "spec": "restoration shaman",
            "bracket": "3v3",
            "sample_size": 50,
            "clusters": 3,
            "path": "/tmp/test.html",
            "url": "http://localhost:8080/pages/test.html"
        }
        
        with patch("sys.argv", ["wow-advisor", "rsham", "3v3", "--no-open"]):
            advisor_main()
            captured = capsys.readouterr()
            assert "Open manually: http://localhost:8080/pages/test.html" in captured.out
            assert "Browser opened." not in captured.out

def test_advisor_cli_refresh(capsys):
    mock_db = MagicMock()
    # Mocking normalize so we don't depend on internal data
    with patch("wow_advisor.config.has_credentials", return_value=True), \
         patch("wow_advisor.config.load_config"), \
         patch("wow_advisor.cache.db.get_default_db", return_value=mock_db), \
         patch("wow_advisor.tools.ui.build_page") as mock_build, \
         patch("wow_advisor.normalize.normalize_spec", return_value="restoration-shaman"), \
         patch("wow_advisor.normalize.normalize_bracket", return_value="3v3"):
        
        mock_build.return_value = {
            "spec": "restoration shaman",
            "bracket": "3v3",
            "sample_size": 50,
            "clusters": 3,
            "path": "/tmp/test.html",
            "url": "http://localhost:8080/pages/test.html"
        }
        
        with patch("sys.argv", ["wow-advisor", "rsham", "3v3", "--refresh"]):
            advisor_main()
            captured = capsys.readouterr()
            assert "Cache cleared for restoration-shaman/3v3 — will re-fetch." in captured.out
            
            # Verify the DELETE query was called
            delete_call = None
            for call in mock_db.execute.call_args_list:
                if "DELETE FROM aggregations" in call[0][0]:
                    delete_call = call
                    break
            
            assert delete_call is not None
            assert delete_call[0][1] == ("restoration-shaman", "3v3", "us")
            mock_db.commit.assert_called()
