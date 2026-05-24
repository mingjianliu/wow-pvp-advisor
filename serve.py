import time
import sys
import os

# Add the project root to sys.path so we can import wow_advisor
sys.path.append(os.getcwd())

from wow_advisor.tools.ui import _ensure_server

print("Starting WoW PvP Advisor frontend server on http://localhost:8080...")
_ensure_server(8080)

print("Server is running. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping server...")
