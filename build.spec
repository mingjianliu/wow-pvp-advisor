# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for wow-advisor.exe

Build with:
  pyinstaller build.spec

Or use build_windows.bat which handles everything.
"""
import sys
from pathlib import Path

ROOT = Path(SPECPATH)
FRONTEND = ROOT / "frontend"

# Collect frontend assets to bundle alongside the exe
frontend_datas = [
    (str(FRONTEND / "index.html"),    "frontend"),
    (str(FRONTEND / "styles.css"),    "frontend"),
    (str(FRONTEND / "app.jsx"),       "frontend"),
    (str(FRONTEND / "tree.jsx"),      "frontend"),
    (str(FRONTEND / "sidebar.jsx"),   "frontend"),
    (str(FRONTEND / "tweaks-panel.jsx"), "frontend"),
    (str(FRONTEND / "talent-meta.js"), "frontend"),
]

a = Analysis(
    ["wow_advisor/cli.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=frontend_datas,
    hiddenimports=[
        "wow_advisor",
        "wow_advisor._paths",
        "wow_advisor.config",
        "wow_advisor.normalize",
        "wow_advisor.cache",
        "wow_advisor.cache.db",
        "wow_advisor.cache.store",
        "wow_advisor.api",
        "wow_advisor.api.auth",
        "wow_advisor.api.client",
        "wow_advisor.api.models",
        "wow_advisor.processor",
        "wow_advisor.processor.aggregator",
        "wow_advisor.processor.talents",
        "wow_advisor.processor.talent_names",
        "wow_advisor.processor.gear",
        "wow_advisor.tools",
        "wow_advisor.tools.fetch",
        "wow_advisor.tools.summary",
        "wow_advisor.tools.ui",
        "wow_advisor.talent_tree",
        "httpx",
        "httpcore",
        "anyio",
        "sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["fastmcp", "tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="wow-advisor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # keep console so users see progress/errors
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,      # add an .ico file here if you have one
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='WoW Advisor.app',
        icon=None,
        bundle_identifier='com.wowadvisor.app',
    )
