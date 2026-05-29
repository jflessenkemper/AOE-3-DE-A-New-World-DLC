#!/usr/bin/env python3
"""Launch AoE3 DE with ANW mod ready for testing."""
import subprocess
import sys
import time
from pathlib import Path

# Create developer mode config
STEAM_ID = "76561198170207043"
GAME_DIR = Path.home() / ".local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE" / STEAM_ID
STARTUP_DIR = GAME_DIR / "Startup"

STARTUP_DIR.mkdir(parents=True, exist_ok=True)

# Enable developer mode
user_cfg = STARTUP_DIR / "user.cfg"
user_cfg.write_text("developer\n")
print(f"[*] Developer mode enabled: {user_cfg}")

# Launch game via Steam
print("[*] Launching Age of Empires III: Definitive Edition...")
result = subprocess.run(
    ["steam", "steam://run/933110"],
    timeout=10,
)

print("[*] Game launched. Waiting for it to reach main menu...")
time.sleep(25)  # Wait for game to fully load

print("[*] Game should be ready. Navigate to Skirmish mode, then automated tests can begin.")
print("[*] Run: matrix_runner_anw_live.py --skip-launch")

