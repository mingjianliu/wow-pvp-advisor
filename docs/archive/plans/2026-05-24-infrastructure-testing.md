# Infrastructure Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create comprehensive tests for `wow_advisor/_paths.py` and `wow_advisor/config.py` to ensure robust path resolution and configuration management across different environments (dev/frozen) and operating systems.

**Architecture:** Use `pytest` with extensive mocking of `sys`, `os`, and `pathlib` to simulate different runtime environments. Use `tmp_path` for file-based tests.

**Tech Stack:** Python, pytest, unittest.mock

---

### Task 1: Test `wow_advisor/_paths.py`

**Files:**
- Create: `tests/test_infra_paths.py`

- [ ] **Step 1: Test dev mode path resolution**
Verify paths returned in non-frozen mode are project-relative and absolute.

```python
import sys
from unittest.mock import patch
from pathlib import Path
from wow_advisor._paths import get_frontend_dir, get_data_dir, get_pages_dir, get_config_path, get_db_path

def test_paths_dev_mode():
    with patch("wow_advisor._paths._is_frozen", return_value=False):
        frontend = get_frontend_dir()
        assert frontend.is_absolute()
        assert frontend.name == "frontend"
        
        pages = get_pages_dir()
        assert pages.is_absolute()
        assert pages.parent.name == "frontend"
        assert pages.name == "pages"
        
        config = get_config_path()
        assert config.name == ".env"
        
        db = get_db_path()
        assert db.parent.name == "data"
        assert db.name == "wow_advisor.db"
```

- [ ] **Step 2: Test frozen mode path resolution**
Mock `sys.frozen` and `sys._MEIPASS` to verify paths for PyInstaller bundles.

```python
def test_paths_frozen_mode():
    with patch("wow_advisor._paths._is_frozen", return_value=True), \
         patch("sys._MEIPASS", "/tmp/bundle", create=True):
        frontend = get_frontend_dir()
        assert str(frontend) == "/tmp/bundle/frontend"
        
        # pages_dir in frozen mode goes to Documents
        pages = get_pages_dir()
        assert "Documents" in str(pages)
        assert pages.name == "pages"
```

- [ ] **Step 3: Test OS-specific data directory**
Mock `os.name` to test Windows vs Unix-like path resolution for `get_data_dir`.

```python
def test_get_data_dir_unix():
    with patch("os.name", "posix"), \
         patch("pathlib.Path.home", return_value=Path("/home/user")):
        data_dir = get_data_dir()
        assert str(data_dir) == "/home/user/.local/share/WowAdvisor"

def test_get_data_dir_windows():
    with patch("os.name", "nt"), \
         patch("os.environ.get", return_value="C:\\Users\\user\\AppData\\Roaming"):
        data_dir = get_data_dir()
        assert str(data_dir) == "C:\\Users\\user\\AppData\\Roaming\\WowAdvisor"
```

- [ ] **Step 4: Run tests**
Run: `pytest tests/test_infra_paths.py`
Expected: PASS

### Task 2: Test `wow_advisor/config.py`

**Files:**
- Create: `tests/test_infra_config.py`

- [ ] **Step 1: Test `load_config`**
Verify it correctly parses `.env` style files into `os.environ`.

```python
import os
from unittest.mock import patch
from wow_advisor.config import load_config

def test_load_config(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("KEY1=VAL1\n# Comment\n KEY2 = VAL2 \n")
    
    with patch("wow_advisor.config.get_config_path", return_value=env_file), \
         patch.dict(os.environ, {}, clear=True):
        load_config()
        assert os.environ["KEY1"] == "VAL1"
        assert os.environ["KEY2"] == "VAL2"
```

- [ ] **Step 2: Test `has_credentials`**
Verify it correctly detects presence/absence of Blizzard API keys.

```python
from wow_advisor.config import has_credentials

def test_has_credentials():
    with patch.dict(os.environ, {"BNET_CLIENT_ID": "id", "BNET_CLIENT_SECRET": "secret"}):
        assert has_credentials() is True
        
    with patch.dict(os.environ, {}, clear=True):
        assert has_credentials() is False
```

- [ ] **Step 3: Test `setup_credentials`**
Verify it prompts for input and writes to the config file.

```python
import pytest
from wow_advisor.config import setup_credentials

def test_setup_credentials_success(tmp_path):
    env_file = tmp_path / "config.env"
    with patch("wow_advisor.config.get_config_path", return_value=env_file), \
         patch("builtins.input", side_effect=["my_id", "my_secret"]), \
         patch.dict(os.environ, {}, clear=True):
        setup_credentials()
        assert os.environ["BNET_CLIENT_ID"] == "my_id"
        assert os.environ["BNET_CLIENT_SECRET"] == "my_secret"
        content = env_file.read_text()
        assert "BNET_CLIENT_ID=my_id" in content
        assert "BNET_CLIENT_SECRET=my_secret" in content

def test_setup_credentials_missing_input(tmp_path):
    with patch("builtins.input", side_effect=["", ""]):
        with pytest.raises(SystemExit):
            setup_credentials()
```

- [ ] **Step 4: Run tests**
Run: `pytest tests/test_infra_config.py`
Expected: PASS

### Task 3: Final Verification

- [ ] **Step 1: Run all new tests together**
Run: `pytest tests/test_infra_paths.py tests/test_infra_config.py`
Expected: ALL PASS
