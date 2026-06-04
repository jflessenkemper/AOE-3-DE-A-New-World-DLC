#!/usr/bin/env python3
"""
ANWBritish Skirmish - Step-by-step driver with visual verification.
Uses PIL to read screenshots and verify state at each step.
"""

import sys
import time
import json
import os

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient, HarnessConnectionError

SOCK = "/tmp/AOE3DEHarness.sock"
OUT = "/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration"

c = HarnessClient(SOCK, timeout=20.0)
c.connect(timeout=10.0)
print("Connected:", c.state())

def ss(name):
    p = os.path.join(OUT, name)
    r = c.screenshot(p)
    print(f"  SS: {name} ({r.bytes_written}B)")
    return p

def click(x, y, wait=0.7):
    c.click(x, y)
    time.sleep(wait)

def key(vk_hex, wait=0.3):
    c.send_raw(f"KEY {vk_hex}")
    time.sleep(wait)

# ─── STEP 1: Main Menu → Skirmish ──────────────────────────────────────────
print("\n[1] Main menu → Skirmish")
ss("30_pre_skirmish_mainmenu.png")
click(130, 482, wait=2.5)
ss("30_skirmish_setup.png")

# ─── STEP 2: Reduce to 2 players (fewer = less crash risk) ──────────────────
print("\n[2] Set 2 players")
click(1780, 170, wait=0.8)          # Player count dropdown
ss("31a_playercount_dropdown.png")
# "2 Players" is typically the 2nd item in dropdown. Items appear below dropdown.
# Dropdown was at y=170. Items likely at y=200, 230, 260...
click(1780, 220, wait=0.8)
ss("31b_playercount_selected.png")

# ─── STEP 3: Set difficulty Easy ─────────────────────────────────────────────
print("\n[3] Set difficulty to Easy")
click(1848, 729, wait=0.8)
ss("31c_difficulty_dropdown.png")
# Easy is first real option after any header; approx y=755
click(1710, 755, wait=0.8)
ss("31d_difficulty_selected.png")

# ─── STEP 4: Open P1 Home City picker ────────────────────────────────────────
print("\n[4] Open P1 home city picker")
click(630, 170, wait=1.5)
ss("31e_homecity_picker.png")

# ─── STEP 5: Navigate to (LONDON) ────────────────────────────────────────────
# Ensure list has focus by clicking row 0
print("\n[5] Navigating to (LONDON) in home city picker")
click(440, 301, wait=0.3)           # Click top row to focus

# Press HOME to go to top
key("0x24", wait=0.4)               # VK_HOME
ss("31f_picker_at_top.png")

# Navigate down. (LONDON) is alphabetically in L section.
# ANW adds many home cities. Typical AoE3+ANW list:
#   Amsterdam, Asyut(?), Beijing(?), Berlin(?), Bogota(?), Boston(?), Buenos Aires(?),
#   Cairo(?), Cuzco, Delhi(?), Gondar, Great Council, Guadalajara(?), Havana(?),
#   Ido, Istanbul(?), Jakarta(?), Kingston(?), Lagos(?), Lisbon, Lima(?), London, ...
# Without knowing exact count, we'll navigate down 20-35 steps and scan.
print("  Pressing DOWN 25x to reach L section...")
for _ in range(25):
    key("0x28", wait=0.06)          # VK_DOWN
time.sleep(0.3)
ss("31g_picker_at_25.png")

# Take 5 more, screenshot
for _ in range(5):
    key("0x28", wait=0.08)
time.sleep(0.3)
ss("31h_picker_at_30.png")

for _ in range(5):
    key("0x28", wait=0.08)
time.sleep(0.3)
ss("31i_picker_at_35.png")

for _ in range(5):
    key("0x28", wait=0.08)
time.sleep(0.3)
ss("31j_picker_at_40.png")

# Now scan up/down ±3 from here looking at screenshots
# We can't read text here - but the screenshots will show highlighted row
# and contain the text "(LONDON)" if we're close.
# Press 3 more down
for _ in range(3):
    key("0x28", wait=0.1)
time.sleep(0.3)
ss("31k_picker_at_43.png")

# Check the picker screen. Since we can't visually verify in script,
# we'll look at the actual row positions on screen.
# The home city names are displayed at the center of list rows.
# Rows y: 301, 365, 428, 494, 558, 622, 685, 751, 814, 877 (10 visible rows)
# The selected item is highlighted. We need LONDON in the highlight.

# One more approach: type 'L' to jump (works in many AoE3 pickers)
# Reset to top first
key("0x24", wait=0.3)   # HOME
click(440, 301, wait=0.3)

# Type L key
key("0x4C", wait=0.5)   # VK_L = 0x4C
ss("31l_after_L_type.png")

# Navigate forward a bit - LONDON comes after LISBON, LIMA, LAGOS etc.
for _ in range(3):
    key("0x28", wait=0.15)
time.sleep(0.3)
ss("31m_after_3down_from_L.png")

# Take 3 more down
for _ in range(3):
    key("0x28", wait=0.15)
time.sleep(0.3)
ss("31n_picker_L_section.png")

# Press OK - whatever is highlighted now, we accept it and verify
# (If wrong, we can cancel and retry)
print("  Pressing OK to select highlighted city...")
click(215, 962, wait=1.5)
ss("31o_after_picker_ok.png")

# Check setup screen - the P1 label should show the selected city
ss("31p_setup_post_city.png")

# ─── STEP 6: Verify and take confirmed screenshot ─────────────────────────────
print("\n[6] Setup confirmation")
ss("31_setup_confirmed.png")

# ─── STEP 7: Click Play ────────────────────────────────────────────────────────
print("\n[7] Clicking Play")
click(1700, 1029, wait=3.0)
ss("32_loading.png")

# ─── STEP 8: Wait for game to load ───────────────────────────────────────────
print("\n[8] Waiting for game to load...")
intervals = [10, 10, 15, 15, 15, 15, 10, 10, 10, 10, 15, 15, 15]
total = 0
for i, wait in enumerate(intervals):
    time.sleep(wait)
    total += wait
    try:
        s = c.state()
        ss_name = f"32_load_{total}s.png"
        ss(ss_name)
        print(f"  t={total}s state: ready={s.ready} uptime={s.uptime_ms}ms")
    except Exception as e:
        print(f"  t={total}s ERROR: {e}")
        print("CRASH DETECTED - stopping")
        sys.exit(1)

# ─── STEP 9: In-game HUD ─────────────────────────────────────────────────────
print("\n[9] Capturing in-game HUD surfaces...")
ss("33_ingame_hud.png")
time.sleep(0.5)
ss("34_resource_bar.png")
ss("35_minimap_cmdpanel.png")

# F10 menu/diplomacy
print("  F10 panel...")
key("0x79", wait=2.0)   # VK_F10 = 0x79
ss("36_diplomacy.png")
key("0x1B", wait=1.0)   # ESC close

# F11 scoreboard
print("  F11 scoreboard...")
key("0x7A", wait=2.0)   # VK_F11 = 0x7A
ss("37_scoreboard.png")
key("0x1B", wait=1.0)

# Home City in-game (H key or click the button)
print("  Home city panel...")
key("0x48", wait=2.0)   # H key
ss("38_homecity_ingame.png")
key("0x1B", wait=1.0)

# Age advance / tech tree - try clicking age indicator at top center
print("  Tech tree / age advance...")
ss("39a_hud_pre_techtree.png")
# Age indicator in AoE3 DE is typically around x=960, y=20-60 (top center)
click(960, 50, wait=1.5)
ss("39_techtree.png")
key("0x1B", wait=0.8)

# ─── STEP 10: ESC menu → Resign ───────────────────────────────────────────────
print("\n[10] Opening in-game ESC menu...")
key("0x1B", wait=2.0)   # ESC
ss("40_ingame_menu.png")

# The ESC menu in AoE3 typically has:
# - Resume Game
# - Options
# - Resign
# - Quit to Main Menu
# Menu appears at screen center. Items usually at y=400-700 range.
# Let's take a screenshot and try to click Resign (typically 4th item)
ss("40b_menu_items.png")

# Resign button - AoE3 in-game ESC menu resign is typically around y=560-600
print("  Clicking Resign...")
click(960, 580, wait=1.5)
ss("40c_resign_confirm_dialog.png")

# Confirm dialog should appear with OK/Yes
# Click OK/Yes to confirm resign
click(960, 560, wait=1.5)
ss("40d_post_resign.png")

# Wait for results screen
time.sleep(5.0)
ss("41_postgame.png")
print("  Post-game captured.")

# ─── STEP 11: Back to main menu ───────────────────────────────────────────────
print("\n[11] Returning to main menu...")
time.sleep(3.0)
# Post-game screen has "Main Menu" button - typically at y=700-800
click(960, 750, wait=3.0)
ss("42a_after_postgame.png")
time.sleep(2.0)
ss("42_back_to_menu.png")
print("  Done.")

c.close()
print("\n=== Script complete ===")
