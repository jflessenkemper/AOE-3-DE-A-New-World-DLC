#!/usr/bin/env python3
"""drive_options8.py — Fresh open of Options and careful tab mapping."""
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

def clk(c, x, y, w=1.0):
    c.click(x, y)
    slp(w)

c = HarnessClient(SOCK)
c.connect()
print(f"State: ready={c.state().ready}")

# Close current Options dialog and reopen fresh
print("Pressing Escape to close Options and Back...")
c.key(0x1B)  # ESC
slp(1.5)
ss(c, "after_close1.png")

# We should be at main menu now. Reopen Options.
print("Reopening Options...")
clk(c, 130, 710, 2.0)
ss(c, "options_fresh_open.png")

# We are on Graphics Options tab (default).
# Now let's try clicking tabs with SLOWER delay and a LEFT BUTTON click (explicit button=1)
# The harness CLICK command defaults to left button. Let me use explicit button.

# Try Game Options - confirmed x=66, y=176
# But also try clicking just the TEXT by using exact center of the nav item

# From thumbnail analysis (image is 1920x1080):
# In thumbnail (640x400) the nav items are at:
# In actual pixels (1920x1080):
# The dialog left nav panel spans x=0 to x≈103/400*1920 = wait...
# The 1920x1080 image displays at 640x400 in the viewer.
# Scale: x_actual = x_viewer * (1920/640) = x_viewer * 3.0
#        y_actual = y_viewer * (1080/400) = y_viewer * 2.7

# From careful observation of viewer coords for each nav item:
# Note: I need to estimate viewer pixel positions from the image rendering

# In the viewer at 640x400, the nav items appear at approximately:
# (all in viewer pixels, left side of screen)
# "OPTIONS" header:    x=50, y=37 → actual (150, 100)
# "GRAPHICS OPTIONS":  x=50, y=50 → actual (150, 135)
# "GAME OPTIONS":      x=50, y=62 → actual (150, 167)
# "UI OPTIONS":        x=50, y=74 → actual (150, 200)
# "SOUND OPTIONS":     x=50, y=86 → actual (150, 232)
# "ACCESSIBILITY":     x=50, y=98 → actual (150, 265)
# "HOTKEYS":           x=50, y=110 → actual (150, 297)
# (gap)
# "RESTORE DEFAULTS":  x=50, y=140 → actual (150, 378)
# "BACK":              x=50, y=152 → actual (150, 411)

# Let me try x=150 and the y values estimated above
print("Testing tabs at x=150 (center of nav)...")
clk(c, 150, 167, 1.2)  # GAME OPTIONS
ss(c, "tab_x150_y167_game.png")

clk(c, 150, 200, 1.2)  # UI OPTIONS
ss(c, "tab_x150_y200_ui.png")

clk(c, 150, 232, 1.2)  # SOUND OPTIONS
ss(c, "tab_x150_y232_sound.png")

clk(c, 150, 265, 1.2)  # ACCESSIBILITY
ss(c, "tab_x150_y265_access.png")

clk(c, 150, 297, 1.2)  # HOTKEYS
ss(c, "tab_x150_y297_hotkeys.png")

# Also try going back to Graphics Options
clk(c, 150, 135, 1.2)  # GRAPHICS OPTIONS
ss(c, "tab_x150_y135_graphics.png")

s = c.state()
print(f"Final state: ready={s.ready}")
