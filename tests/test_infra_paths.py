import sys
import os
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

def test_paths_frozen_mode():
    with patch("wow_advisor._paths._is_frozen", return_value=True), \
         patch("sys._MEIPASS", "/tmp/bundle", create=True):
        frontend = get_frontend_dir()
        assert str(frontend) == "/tmp/bundle/frontend"
        
        # pages_dir in frozen mode goes to Documents
        pages = get_pages_dir()
        assert "Documents" in str(pages)
        assert pages.name == "pages"

def test_get_data_dir_unix():
    with patch("os.name", "posix"), \
         patch("pathlib.Path.home", return_value=Path("/home/user")), \
         patch("pathlib.Path.mkdir"):
        data_dir = get_data_dir()
        assert str(data_dir) == "/home/user/.local/share/WowAdvisor"

def test_get_data_dir_windows():
    from unittest.mock import MagicMock
    with patch("os.name", "nt"), \
         patch("os.environ.get", return_value="C:\\Users\\user\\AppData\\Roaming"), \
         patch("wow_advisor._paths.Path") as mock_path:
        
        # mock_path("...") returns mock_base
        mock_base = MagicMock()
        mock_path.return_value = mock_base
        
        # mock_base / "WowAdvisor" returns mock_d
        mock_d = MagicMock()
        mock_base.__truediv__.return_value = mock_d
        
        data_dir = get_data_dir()
        
        mock_path.assert_called_with("C:\\Users\\user\\AppData\\Roaming")
        mock_base.__truediv__.assert_called_with("WowAdvisor")
        mock_d.mkdir.assert_called_once()
        assert data_dir == mock_d
