import time
import sys
import os

# Add the project root to sys.path so we can import wow_advisor
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from wow_advisor.tools.ui import _ensure_server
from wow_advisor.settings import SERVER_PORT

print(f"Starting WoW PvP Advisor frontend server on http://localhost:{SERVER_PORT}...")
_ensure_server(SERVER_PORT)

print("Server is running. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping server...")
