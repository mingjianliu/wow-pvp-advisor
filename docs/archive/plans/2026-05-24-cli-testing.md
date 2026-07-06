# CLI Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create comprehensive unit tests for both `wow_advisor/cli.py` and the root `cli.py`.

**Architecture:** Use `unittest.mock.patch` to isolate the CLI from side effects (API calls, DB changes, browser opening) and `pytest`'s `capsys` fixture to verify output.

**Tech Stack:** Python, pytest, unittest.mock

---

### Task 1: Test Root cli.py

**Files:**
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for root cli.py commands**

```python
import sys
import json
from unittest.mock import patch, MagicMock
import pytest
from cli import main as root_main

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
            assert json.loads(captured.out.split("\n")[1]) == ["player1"]
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
```

- [ ] **Step 2: Run test to verify it fails (if any issues or imports missing)**

Run: `pytest tests/test_cli.py -v`

- [ ] **Step 3: Run test to verify it passes**

- [ ] **Step 4: Commit**

### Task 2: Test wow_advisor/cli.py

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write tests for wow_advisor/cli.py**

Focus on:
- Normal execution flow
- `--no-open` flag
- `--refresh` flag (mocking DB)
- Error handling (build_page returns error)

```python
from wow_advisor.cli import main as advisor_main

@patch("wow_advisor.cli.build_page")
@patch("wow_advisor.cli.has_credentials")
@patch("wow_advisor.cli.load_config")
def test_advisor_cli_basic(mock_load, mock_has_creds, mock_build, capsys):
    mock_has_creds.return_value = True
    mock_build.return_value = {
        "spec": "Restoration Shaman",
        "bracket": "3v3",
        "sample_size": 50,
        "clusters": 3,
        "path": "/tmp/test.html",
        "url": "http://localhost:8080/pages/test.html"
    }
    
    with patch("sys.argv", ["wow-advisor", "rsham", "3v3", "--no-open"]):
        advisor_main()
        captured = capsys.readouterr()
        assert "Building page for 'rsham' / 3v3 [us] ..." in captured.out
        assert "Spec:     Restoration Shaman" in captured.out
        assert "Open manually: http://localhost:8080/pages/test.html" in captured.out
        mock_build.assert_called_once_with("rsham", "3v3", "us")

@patch("wow_advisor.cli.get_default_db")
@patch("wow_advisor.cli.CacheStore")
@patch("wow_advisor.cli.build_page")
@patch("wow_advisor.cli.has_credentials")
@patch("wow_advisor.cli.load_config")
def test_advisor_cli_refresh(mock_load, mock_has_creds, mock_build, mock_store, mock_db, capsys):
    mock_has_creds.return_value = True
    mock_build.return_value = {"path": "...", "spec": "...", "bracket": "...", "sample_size": 1, "clusters": 1, "url": "..."}
    
    mock_conn = MagicMock()
    mock_db.return_value = mock_conn
    
    with patch("sys.argv", ["wow-advisor", "rsham", "3v3", "--refresh", "--no-open"]):
        advisor_main()
        captured = capsys.readouterr()
        assert "Cache cleared for restoration-shaman/3v3 — will re-fetch." in captured.out
        mock_conn.execute.assert_called()
        # Verify it called DELETE FROM aggregations
        call_args = mock_conn.execute.call_args[0]
        assert "DELETE FROM aggregations" in call_args[0]

@patch("wow_advisor.cli.build_page")
@patch("wow_advisor.cli.has_credentials")
@patch("wow_advisor.cli.load_config")
def test_advisor_cli_error(mock_load, mock_has_creds, mock_build, capsys):
    mock_has_creds.return_value = True
    mock_build.return_value = {"error": "Something went wrong"}
    
    with patch("sys.argv", ["wow-advisor", "invalid", "3v3"]):
        with pytest.raises(SystemExit) as excinfo:
            advisor_main()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Something went wrong" in captured.err

@patch("wow_advisor.cli.setup_credentials")
@patch("wow_advisor.cli.has_credentials")
@patch("wow_advisor.cli.load_config")
def test_advisor_cli_no_creds_exit(mock_load, mock_has_creds, mock_setup, capsys):
    mock_has_creds.return_value = False
    
    with patch("sys.argv", ["wow-advisor", "rsham", "3v3"]):
        with pytest.raises(SystemExit) as excinfo:
            advisor_main()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Blizzard API credentials not configured." in captured.err
        mock_setup.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`

- [ ] **Step 3: Commit**

### Task 3: Final verification

- [ ] **Step 1: Run all tests in the project to ensure no regressions**

Run: `pytest`

- [ ] **Step 2: Cleanup any temporary files if created**
