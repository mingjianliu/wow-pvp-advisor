#!/usr/bin/env bash
set -e
echo "=== WoW Advisor local build ==="

pip install pyinstaller -q

rm -rf build dist/wow-advisor

pyinstaller build.spec --clean --noconfirm

if [ -f dist/wow-advisor ]; then
    echo ""
    echo "BUILD SUCCESSFUL — dist/wow-advisor"
    echo "Test: ./dist/wow-advisor \"restoration shaman\" 3v3 --no-open"
else
    echo "BUILD FAILED"
    exit 1
fi
