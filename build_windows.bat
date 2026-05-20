@echo off
:: WoW Advisor — Windows build script
:: Run this from the repo root on a Windows machine (or in Wine/cross-compile env)
:: Requires: pip install pyinstaller

echo === WoW Advisor Windows Build ===
echo.

:: Install/upgrade build dependencies
pip install pyinstaller --quiet

:: Clean previous build
if exist dist\wow-advisor.exe del /f dist\wow-advisor.exe
if exist build rmdir /s /q build

:: Build
pyinstaller build.spec --clean --noconfirm

echo.
if exist dist\wow-advisor.exe (
    echo BUILD SUCCESSFUL
    echo Output: dist\wow-advisor.exe
    echo.
    echo Usage:
    echo   wow-advisor.exe "restoration shaman" 3v3
    echo   wow-advisor.exe holy-paladin 2v2 --region eu
    echo   wow-advisor.exe rsham 3v3 --refresh
) else (
    echo BUILD FAILED — check output above
    exit /b 1
)
