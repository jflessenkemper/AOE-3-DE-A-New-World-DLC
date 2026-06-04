"""
ANWBritish UI capture script.

Drives the live AoE3 DE game from main menu through a full ANWBritish
skirmish, capturing every UI surface.  Outputs PNGs into:
  /tmp/anwbritish_capture/  (raw session screenshots)
  artifacts/validation/visual_art/ANWBritish/full/  (canonical copies)

Run from repo root:
  python3 tools/aoe3_harness/run_anwbritish_capture.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.aoe3_harness.harness_client import HarnessClient, HarnessConnectionError

SOCK = "/tmp/AOE3DEHarness.sock"
TMP_DIR = Path("/tmp/anwbritish_capture")
CANONICAL_DIR = Path("artifacts/validation/visual_art/ANWBritish/full")
CAL_JSON = Path("artifacts/validation/ui_calibration/ui_calibration.json")

TMP_DIR.mkdir(exist_ok=True)
CANONICAL_DIR.mkdir(parents=True, exist_ok=True)

c = HarnessClient(SOCK, timeout=15.0)
c.connect()

def ss(name: str) -> Path:
    """Take a screenshot into TMP_DIR, return the path."""
    p = TMP_DIR / name
    c.screenshot(str(p))
    print(f"  [screenshot] {name}")
    return p

def check_state() -> bool:
    """Return True if game is still ready=1."""
    try:
        s = c.state()
        if s.ready != 1:
            print(f"  [WARNING] ready={s.ready}")
            return False
        return True
    except HarnessConnectionError as e:
        print(f"  [CRASH] Connection lost: {e}")
        return False

def sleep(ms: int) -> None:
    time.sleep(ms / 1000.0)

def click(x: int, y: int, delay_ms: int = 300) -> None:
    c.click(x, y)
    sleep(delay_ms)

def key(vk: int, delay_ms: int = 300) -> None:
    c.key(vk)
    sleep(delay_ms)

# VK constants
VK_ESCAPE = 0x1B
VK_DOWN   = 0x28
VK_HOME   = 0x24
VK_F10    = 0x79
VK_TAB    = 0x09

print("=== ANWBritish UI Capture ===")
print(f"Output dir: {TMP_DIR}")

# ──────────────────────────────────────────────────────────────────────────────
# Step 0: take baseline screenshot of current state
# ──────────────────────────────────────────────────────────────────────────────
print("\n[0] Baseline state check")
if not check_state():
    print("ABORT: game not ready")
    sys.exit(1)
ss("step0_baseline.png")

# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Click Skirmish from main menu
# ──────────────────────────────────────────────────────────────────────────────
print("\n[1] Clicking Skirmish button [130, 482]")
click(130, 482, delay_ms=1500)

if not check_state():
    print("ABORT: game crashed after clicking Skirmish")
    sys.exit(1)
ss("step1_skirmish_setup.png")
print("  Skirmish setup screen reached")

# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Set difficulty to Easy (▼ at x=1848, y=729)
# ──────────────────────────────────────────────────────────────────────────────
print("\n[2] Setting difficulty to Easy")
click(1848, 729, delay_ms=600)  # open difficulty dropdown
ss("step2a_difficulty_dropdown_open.png")
# Dropdown options: Easy is typically first real option; HOME then DOWN once
key(VK_HOME, delay_ms=200)
key(VK_DOWN, delay_ms=200)  # Easy (first option after any separator)
ss("step2b_difficulty_easy_selected.png")
# Press Enter to confirm / click the first item visually
# The dropdown is at approximately y=729; after opening the list appears below.
# Items appear around y=760, 810, 860, 910 typically.  Click "Easy" row.
click(1710, 760, delay_ms=400)  # Easy is first item in opened list
ss("step2c_difficulty_easy_confirmed.png")
print("  Difficulty dropdown handled")

# ──────────────────────────────────────────────────────────────────────────────
# Step 3: Open the HOME CITY picker for P1 and navigate to (LONDON)
# ──────────────────────────────────────────────────────────────────────────────
print("\n[3] Opening Home City picker for P1 [630, 170]")
click(630, 170, delay_ms=800)

if not check_state():
    print("ABORT: game crashed opening civ picker")
    sys.exit(1)
ss("step3a_picker_open.png")
print("  Picker open - navigating to LONDON")

# Navigate the picker.  From calibration:
# The HOME CITY picker shows cities alphabetically.  (LONDON) needs scroll.
# Wheel scroll does NOT work — use keyboard DOWN arrow.
# First press HOME to go to top, then DOWN-arrow until we hit LONDON.
# Known entries in picker from calibration (first 10 visible):
#   row0: Random Personality
#   row1: (Cuzco)
#   row2: (Stockholm)
#   row3: (St. Petersburg)
#   row4: (Lisbon)
#   row5: (Valletta)
#   row6: (Great Council)
#   row7: (Amsterdam)
#   row8: (Ido)
#   row9: (Gondar)
# LONDON is not in the first 10. Need to scroll down.
# Click inside picker list area first so it has keyboard focus
click(440, 500, delay_ms=300)  # click middle of list area
key(VK_HOME, delay_ms=300)     # go to top

# We need to find (LONDON). London alphabetically comes after Gondar and
# before many others.  Press DOWN enough times.  The picker has many cities.
# The exact position of LONDON depends on the full list.  Strategy: press DOWN
# and screenshot periodically to see where we are, then decide.
# From the ANW mod context: ANWBritish home city is LONDON.
# We'll press DOWN in batches and screenshot each time.

print("  Navigating DOWN to find (LONDON) ...")
# Press HOME first to reset
key(VK_HOME, delay_ms=500)

# Press DOWN 10 times to see first batch
for i in range(10):
    key(VK_DOWN, delay_ms=80)
ss("step3b_after_10_down.png")

# Press DOWN 10 more (total 20)
for i in range(10):
    key(VK_DOWN, delay_ms=80)
ss("step3c_after_20_down.png")

# Press DOWN 10 more (total 30)
for i in range(10):
    key(VK_DOWN, delay_ms=80)
ss("step3d_after_30_down.png")

# LONDON likely around position 15-25 alphabetically among all AoE3 home cities
# Let's check after 20 presses — we'll visually verify in the screenshots
# For now continue pressing until we've passed enough letters
# L comes after: Athens, Aztlan, Beijing, Berlin, Boston, Caen, Cairo,
# Cape Town, Constantinople, Cusco, Delhi, Dublin, Edo, Frankfurt, Geneva,
# Gondar, Great Council, Havana, Ido, Istanbul, Jerusalem, Jing, Kyoto,
# Lima, Lisbon, LONDON would be around position 25-30

print("  LONDON should be near current position. Capturing and verifying ...")
# We'll capture a few more times to confirm (LONDON) is highlighted
ss("step3e_current_position.png")

# If we've overshot LONDON we'll need to go back. For safety,
# let's try pressing HOME and using a more targeted approach:
# Press DOWN exactly 25 times (estimated position for LONDON)
key(VK_HOME, delay_ms=500)
for i in range(25):
    key(VK_DOWN, delay_ms=60)
ss("step3f_at_25_down.png")

# Continue searching
for i in range(5):
    key(VK_DOWN, delay_ms=100)
ss("step3g_at_30_down.png")

# At this point we have screenshots to analyze visually.
# We need to look at the screenshots to find where LONDON is.
# For now, use the scripted approach: we know the picker is sorted.
# London comes right after Lima/Lisbon in alphabetical city order.
# In the home city picker list from calibration, after row9 (Gondar) we need more down presses.
# Let's be systematic: reset and press exactly the right number.

# First let's check what's visible right now with our current position
ss("step3h_checking_current.png")

print("  Screenshots captured for LONDON search - will analyze and click")
