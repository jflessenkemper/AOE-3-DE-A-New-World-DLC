#!/usr/bin/env python3
"""Capture missing British surfaces for the release-readiness site.

Target surfaces:
  1. scoreboard        -> 03_scoreboard.png
  2. ally home city    -> 06b_ai_homecity_via_diplo.png
  3. abandon screen    -> 07a_abandon_screen.png
  4. Age-Up II         -> 08_ageup_age2.png
  5. Age-Up III        -> 08_ageup_age3.png
  6. Age-Up IV         -> 08_ageup_age4.png
  7. Age-Up V          -> 08_ageup_age5.png

Run in-game (British skirmish already running).
"""

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.aoe3_automation import lobby_driver
from tools.aoe3_automation.in_game_driver import (
    _click, _key, _focus_window, _screenshot_raw,
    GEARS_BTN, ESC_RESIGN, RESIGN_YES,
    DIPLOMACY_BTN, DIPLOMACY_FLAG_X, DIPLOMACY_ALLY_X, DIPLOMACY_APPLY, DIPLOMACY_CLOSE,
    diplomacy_row_y,
)

OUT = REPO / "artifacts/validation/visual_art/ANWBritish/full"
OUT.mkdir(parents=True, exist_ok=True)


def shot(name: str) -> Path:
    p = OUT / name
    lobby_driver.screenshot(p)
    print(f"  captured -> {p.name} ({p.stat().st_size // 1024}KB)")
    return p


def close_any_menus():
    """Press Escape a couple times to get back to HUD."""
    _focus_window()
    _key("Escape")
    time.sleep(0.5)
    _key("Escape")
    time.sleep(0.5)


print("=== British missing surfaces capture ===")
print()

# Step 0: ensure we start from clean HUD (close ESC menu if open)
print("[0] Closing any open menus...")
close_any_menus()
time.sleep(0.5)

# ─────────────────────────────────────────────
# 1. SCOREBOARD
# ─────────────────────────────────────────────
print("[1] Scoreboard - opening diplomacy panel for full score view...")
_focus_window()
_click(*DIPLOMACY_BTN, delay=1.5)
time.sleep(1.5)
p1 = shot("03_scoreboard.png")
# close diplomacy
_click(*DIPLOMACY_CLOSE, delay=0.5)
time.sleep(0.8)

# ─────────────────────────────────────────────
# 2. ALLY HOME CITY via diplomacy
# ─────────────────────────────────────────────
print("[2] Ally Home City via diplomacy...")
_focus_window()
_click(*DIPLOMACY_BTN, delay=1.5)
time.sleep(1.5)
# First ally player P2 (y=425)
row_y = diplomacy_row_y(2)
print(f"    clicking ALLY radio for P2 at ({DIPLOMACY_ALLY_X}, {row_y})")
_click(DIPLOMACY_ALLY_X, row_y, delay=0.5)
time.sleep(0.4)
_click(*DIPLOMACY_APPLY, delay=0.8)
time.sleep(1.0)
# Close and reopen diplomacy
_click(*DIPLOMACY_CLOSE, delay=0.5)
time.sleep(0.8)
_click(*DIPLOMACY_BTN, delay=1.5)
time.sleep(1.5)
# Click P2 name to open their HC
print(f"    clicking P2 name at ({DIPLOMACY_FLAG_X}, {row_y})")
_click(DIPLOMACY_FLAG_X, row_y, delay=2.5)
time.sleep(3.0)  # HC scene render
p2 = shot("06b_ai_homecity_via_diplo.png")
# Back to game
_key("Escape")
time.sleep(0.8)

# ─────────────────────────────────────────────
# 3. SCOREBOARD (better pass) — take another while in clean HUD
# ─────────────────────────────────────────────
# Already captured above; skip.

# ─────────────────────────────────────────────
# 4. ABANDON SCREEN
# ─────────────────────────────────────────────
# NOTE: We open ESC menu, capture it BEFORE clicking Resign (that's the
# abandon/resign state). Then we will click resign for a real abandon.
print("[3] Abandon screen - opening ESC menu + clicking Resign...")
_focus_window()
_click(*GEARS_BTN, delay=1.2)
time.sleep(1.2)
# Capture ESC menu with Resign option visible
# Now click Resign
_click(*ESC_RESIGN, delay=1.0)
time.sleep(1.5)
# Now the resign confirmation dialog is shown
p3_confirm = shot("07a_abandon_screen_confirm.png")
# Capture this - it's the resign confirmation.
# This IS the "abandon screen" (resign confirmation dialog).
import shutil
shutil.copy(p3_confirm, OUT / "07a_abandon_screen.png")
print("    07a_abandon_screen.png saved (resign confirmation dialog)")
# NOW click YES to actually resign and proceed to postgame
_click(*RESIGN_YES, delay=1.5)
time.sleep(3.0)
# Post-resign screen
p3b = shot("07a_post_resign.png")
print("    07a_post_resign.png captured for inspection")

print()
print("=== Phase 1 captures done (scoreboard, ally HC, abandon) ===")
print("    Age-up captures require starting a new game with cheats.")
print()
