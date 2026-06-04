#!/usr/bin/env python3
"""get_hotkeys_screenshot.py — Get proper Hotkeys tab screenshot."""
import sys, time
from pathlib import Path

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")

def ss(c, name):
    p = str(SS_DIR / name)
    c.screenshot(p)
    print(f"  [ss] {name}")
    return p

def slp(n=0.8):
    time.sleep(n)

def clk(c, x, y, w=0.9):
    c.click(x, y)
    slp(w)

def chk(c, label=""):
    s = c.state()
    print(f"  [{label}] ready={s.ready}")
    return s

c = HarnessClient(SOCK)
c.connect()
chk(c, "start")

# Get a complete graphics screenshot (scrolled + full)
# First take screenshot of current state
ss(c, "current_graphics.png")

# Now navigate to Accessibility first
print("Navigating to Accessibility...")
clk(c, 66, 585, 1.0)
ss(c, "15b_options_accessibility.png")

# Now try to click Hotkeys at several nearby y values
print("Trying Hotkeys at various y positions...")
# From the background scan: y=620-795 showed Hotkeys content
# But after navigating other tabs, let me try from Accessibility:
# The Hotkeys tab should be BELOW Accessibility in the nav

# Try y=617 (just below the exit point at 615)
clk(c, 66, 617, 1.0)
ss(c, "hotkeys_y617.png")
chk(c, "y617")

# Try y=618-622 range
clk(c, 66, 618, 1.0)
ss(c, "hotkeys_y618.png")

clk(c, 66, 619, 1.0)
ss(c, "hotkeys_y619.png")

clk(c, 66, 621, 1.0)
ss(c, "hotkeys_y621.png")

clk(c, 66, 622, 1.0)
ss(c, "hotkeys_y622.png")

# Take the screenshot of one of these - it might work
ss(c, "16_options_hotkeys.png")
chk(c, "hotkeys_check")

# Also try the scroll position - use End key in the nav panel
# First click in the nav panel area
clk(c, 50, 620, 0.5)
c.key(0x23)  # End key
slp(0.5)
ss(c, "hotkeys_end_key.png")

print(f"Done. State: ready={c.state().ready}")
