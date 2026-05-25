You are implementing Task 1: Test Root cli.py

## Task Description

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

## Context

The root `cli.py` is a simple sub-parser dispatcher for manual debugging. It uses tools from `wow_advisor.tools`.

## Your Job

Once you're clear on requirements:
1. Implement exactly what the task specifies
2. Write tests (following TDD if task says to)
3. Verify implementation works
4. Commit your work
5. Self-review
6. Report back

Work from: /Users/mingjianliu/code/wow-talent-gear-collector

## Report Format

When done, report:
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- What you implemented
- What you tested and test results
- Files changed
- Self-review findings
- Any issues or concerns
