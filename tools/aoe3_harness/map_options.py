#!/usr/bin/env python3
"""
map_options.py — Drive AoE3 DE to:
  1. Open Options → Graphics tab
  2. Set quality preset to LOWEST + resolution to 1920x1080
  3. Apply settings
  4. Map all other Options tabs (Audio, Gameplay, Interface, Hotkeys)
  5. Map remaining top-level menus (Campaign, Historical Battles, Multiplayer, Home City, Load Game)

Screenshots go to artifacts/validation/ui_calibration/
"""
import sys
import os
import time
import json
from pathlib import Path

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient, HarnessConnectionError

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")
CAL_FILE = SS_DIR / "ui_calibration.json"

def ss(c, name):
    """Take a screenshot and return the path."""
    p = str(SS_DIR / name)
    c.screenshot(p)
    print(f"  [screenshot] {name}")
    return p

def pause(secs=0.8):
    time.sleep(secs)

def check_state(c):
    s = c.state()
    print(f"  [state] pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h}")
    return s

def esc(c):
    c.key(0x1B)  # VK_ESCAPE
    pause()

def click_and_wait(c, x, y, wait=1.0):
    c.click(x, y)
    pause(wait)

log = {}

def main():
    c = HarnessClient(SOCK)
    c.connect()
    print("Connected to harness")

    # Verify initial state
    s = check_state(c)
    if not s.ready:
        print("ERROR: harness not ready")
        return

    # -------------------------------------------------------------------------
    # TASK 1: Options → Graphics
    # -------------------------------------------------------------------------
    print("\n=== TASK 1: Options > Graphics ===")

    # Take main menu screenshot first to confirm position
    ss(c, "09_main_menu_verify.png")
    pause(0.5)

    # Click Options button [130, 710]
    print("Clicking Options button at (130, 710)")
    click_and_wait(c, 130, 710, 1.5)
    ss(c, "10_options_root.png")

    # Check state after opening options
    check_state(c)

    # The options menu should now be open. Take a screenshot to see tab bar.
    # Based on typical AoE3 DE layout, tabs are near top of the options panel.
    # We need to identify Graphics/Video tab.
    # First let's record what we see, then click Graphics tab.

    # AoE3 DE options tabs are typically at top of the options dialog
    # Common positions (we'll verify from screenshot):
    # - Graphics/Video tab ~ (280, 100) or similar
    # We'll try clicking various expected tab positions and screenshot

    # Try clicking the Graphics/Video tab - typically first or second tab
    # Let's screenshot first to identify tab positions
    pause(0.5)

    # In AoE3 DE, options tabs are usually in a row near top-center
    # Based on 1920x1080 layout, the tab bar is typically around y=85-95
    # and tabs are spread horizontally starting around x=200
    # Tab order is usually: Graphics, Audio, Gameplay, Interface, Hotkeys

    # Click the first tab (Graphics/Video) - typical position
    print("Clicking Graphics tab (attempting ~250, 90)")
    click_and_wait(c, 250, 90, 0.8)
    ss(c, "11_options_graphics_BEFORE.png")

    # Record coordinates for options root
    log["options_root"] = {
        "screenshot": "10_options_root.png",
        "reached_by": "main_menu → click Options (130, 710)",
    }

    log["options_graphics_before"] = {
        "screenshot": "11_options_graphics_BEFORE.png",
        "reached_by": "options_root → click Graphics tab",
    }

    print("Options graphics screenshot taken - will analyze positions from image")

    # Now we need to:
    # 1. Find the Quality Preset dropdown
    # 2. Set it to Low/Very Low
    # 3. Set resolution to 1920x1080
    # 4. Click Apply

    # In AoE3 DE Graphics settings, controls are typically:
    # - Quality Preset dropdown: upper portion of settings area
    # - Resolution dropdown: below that
    # - Various quality sliders below
    # The settings panel content area is typically x=200-1700, y=150-950

    # Let's screenshot carefully to read positions
    # We'll attempt to click where quality preset dropdown typically is
    # Based on prior knowledge of AoE3 DE 1920x1080 layout:
    # Quality Preset is usually around (960, 200) or (700, 200)

    # First screenshot the graphics page to read it
    # (already done as 11_options_graphics_BEFORE.png)

    # We'll attempt systematic approach:
    # Look for a "Preset" or "Quality" dropdown near the top of content area
    # Typical AoE3 DE graphics layout:
    #   Quality Preset:    value around x=700-900, y=190-230
    #   Resolution:        value around x=700-900, y=250-290
    #   Display mode:      value around x=700-900, y=310-350

    # Let's try clicking where quality preset dropdown should be
    # AoE3 DE typically has dropdown labels on left and values on right
    # In 1920x1080 the right-side dropdown value would be around x=800-1000

    print("Attempting to find and click Quality Preset dropdown...")
    # Try the preset area - center of content for quality preset
    # AoE3 DE Graphics tab layout (estimated from 1920x1080):
    # Row 1: Quality Preset ~ y=195, dropdown right side ~ x=900
    click_and_wait(c, 900, 195, 0.8)
    ss(c, "11a_preset_click_attempt.png")

    # If a dropdown opened, we need to select the lowest option
    # The lowest quality preset in AoE3 DE is typically "Low" or at the bottom of list
    # Dropdown items typically appear below the dropdown widget
    # Try clicking the bottom/first item which should be lowest quality
    # If dropdown didn't open, we'll try other positions

    # Let's try a few positions to find the preset dropdown
    esc(c)  # close any accidental dropdown
    pause(0.5)
    ss(c, "11b_after_esc.png")

    return c, log

if __name__ == "__main__":
    result = main()
    print("Initial exploration complete")
