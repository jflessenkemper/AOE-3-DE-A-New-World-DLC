#!/usr/bin/env python3
"""drive_options7.py — Final targeted approach to map all tabs."""
import sys, time
from pathlib import Path

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")

def ss(c, name):
    c.screenshot(str(SS_DIR / name))
    print(f"  [ss] {name}")

def slp(n=0.8):
    time.sleep(n)

def clk(c, x, y, w=0.8):
    c.click(x, y)
    slp(w)

c = HarnessClient(SOCK)
c.connect()
print(f"State: ready={c.state().ready}")

# ============================================================
# From current_state.png and all analysis, we're on Graphics Options.
# We know:
#   - x=66 IS the correct nav panel x (worked once for Game Options at y=176)
#   - The nav panel has 6 tabs (Graphics, Game, UI, Sound, Accessibility, Hotkeys)
#   - Each tab is approximately 30-35px tall in actual coords
#   - Graphics Options tab is at y≈130-165
#   - Game Options tab is at y≈165-200 (y=176 worked!)
#   - But clicking at y=115, 125, 145 all gave Game Options, not Graphics...
#
# NEW HYPOTHESIS: The Restore Defaults (y=350 click) triggered a different state
# where the order of tabs changed, or the nav scrolled to show a different order.
# In "current_state.png" the nav shows GRAPHICS OPTIONS first (highlighted),
# then GAME OPTIONS, then UI OPTIONS etc.
#
# BUT in that screenshot, GRAPHICS OPTIONS is the active one (highlighted gold).
# So the order is unchanged.
#
# Let me try a different approach: use the KEYBOARD to navigate tabs.
# In AoE3 DE, TAB key might cycle through controls.
# Or use mouse to click precisely on each nav item one at a time.
#
# Actually, I realize I should look at the screenshots that DID show Game Options.
# In my very first run (drive_options.py), it said:
#   "clk(c, 260, 190, 1.2)" then ss(..., "13_options_audio.png") - showed Game Options
# In drive_options2.py: clk(c, 198, 176, 1.2) showed Game Options
# In drive_options3.py: clk(c, 66, 176, 1.0) showed Game Options
#
# So x=66, y=176 confirmed working for Game Options.
# The issue is UI Options and others don't respond.
#
# RESOLUTION: Perhaps UI Options, Sound Options, etc. require clicking on a DIFFERENT
# area of the tab. The nav items may have scroll arrows or the panel is scrollable.
# OR: The game uses a TAB component where you must scroll the nav panel itself.
#
# Let me look at this from the CONTENT panel perspective:
# In the "current_state.png", after looking carefully I can see:
# Left nav has: OPTIONS header, then GRAPHICS OPTIONS (bold/active), GAME OPTIONS,
# UI OPTIONS, SOUND OPTIONS, ACCESSIBILITY, HOTKEYS, RESTORE DEFAULTS, BACK
# ALL items are visible in the nav without scrolling.
#
# The nav panel appears to be about 103px wide (in 640px thumbnail) = 309px actual.
# Item text centers at approximately x=50 (thumb) = x=150 actual.
#
# But wait - in the screenshots the left sidebar items show at a smaller x.
# If the dialog is NOT full-screen but centered, the actual coordinates would be different.
#
# The game runs in 1920x1080. The dialog appears to overlay the left side.
# Looking at "current_state.png":
# - Left edge of dialog: x=0 (at screen left edge)
# - Right edge of nav panel: x≈103 thumb = x≈309 actual
# - Left of content panel: x≈103 thumb = x≈309 actual
# - Right edge of content: x≈380 thumb = x≈1140 actual
# So x=66 actual IS within the nav panel (0-309 actual).
# The text center of nav items would be at x≈154 actual (50% of 309).
# But x=66 also works (tested).
#
# Let me try clicking directly at x=154 (center of nav panel) for the other tabs.
# ============================================================

print("Trying x=154 (nav panel center) for each tab...")
# Game Options (confirmed at y=176)
clk(c, 154, 176, 1.0)
ss(c, "nav_x154_game.png")

# UI Options (estimated y=211)
clk(c, 154, 211, 1.0)
ss(c, "nav_x154_ui.png")

# Sound Options (estimated y=246)
clk(c, 154, 246, 1.0)
ss(c, "nav_x154_sound.png")

# Accessibility (estimated y=281)
clk(c, 154, 281, 1.0)
ss(c, "nav_x154_access.png")

# Hotkeys (estimated y=316)
clk(c, 154, 316, 1.0)
ss(c, "nav_x154_hotkeys.png")

print("Done x=154 scan")
s = c.state()
print(f"State: ready={s.ready}")
