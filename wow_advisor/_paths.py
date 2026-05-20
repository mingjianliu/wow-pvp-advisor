"""
Runtime path resolution — works in both dev and PyInstaller bundles.

Dev mode  : uses project-relative paths (existing data/db, frontend/pages)
Frozen exe: uses user home/appdata so data survives upgrades
"""
import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _project_root() -> Path:
    return Path(__file__).parent.parent


def get_frontend_dir() -> Path:
    if _is_frozen():
        return Path(sys._MEIPASS) / "frontend"  # type: ignore[attr-defined]
    return _project_root() / "frontend"


def get_data_dir() -> Path:
    """Persistent user data (SQLite, config). Only used in frozen mode."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    d = base / "WowAdvisor"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_pages_dir() -> Path:
    if _is_frozen():
        d = Path.home() / "Documents" / "WowAdvisor" / "pages"
    else:
        d = _project_root() / "frontend" / "pages"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_config_path() -> Path:
    if _is_frozen():
        return get_data_dir() / "config.env"
    return _project_root() / ".env"


def get_db_path() -> Path:
    if _is_frozen():
        return get_data_dir() / "wow_advisor.db"
    return _project_root() / "data" / "wow_advisor.db"
