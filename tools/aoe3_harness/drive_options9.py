#!/usr/bin/env python3
"""drive_options9.py — Binary search for exact tab boundaries near confirmed y=176."""
import sys, time
from pathlib import Path

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")

def ss(c, name):
    c.screenshot(str(SS_DIR / name))
    print(f"  [ss] {name}")
    return str(SS_DIR / name)

def slp(n=0.8):
    time.sleep(n)

def clk(c, x, y, w=0.8):
    c.click(x, y)
    slp(w)

c = HarnessClient(SOCK)
c.connect()
print(f"State: ready={c.state().ready}")

# We know (66, 176) showed Game Options.
# The Nav tabs might be at SMALLER y values (dialog is positioned differently than I assumed).
#
# Let me check what the dialog looks like right now.
ss(c, "debug_current.png")

# From the pixel analysis, Game Options is around y=412 actual pixels.
# If clicking y=176 hit Game Options, then the click coordinate y=176
# must somehow correspond to pixel y≈412.
#
# Let me try clicking at y values MUCH HIGHER to find the other tabs.
# If y=176 → Game Options (at pixel y=412), and each tab is ~60px apart in pixels:
# - Next tab (UI Options) would be at pixel y=472 → harness y = 472 * (176/412) = 201
# - Sound Options: pixel y=532 → harness y = 532 * (176/412) = 227
# - Accessibility: pixel y=592 → harness y = 592 * (176/412) = 253
# - Hotkeys: pixel y=652 → harness y = 652 * (176/412) = 278
#
# This assumes the scale factor is approximately: harness_y = pixel_y * (176/412) = pixel_y * 0.427
# Which would mean: 1 pixel unit in harness = 1/0.427 = 2.34 pixel units in screen
# OR: the harness uses 1920x(1080/2.34) = 1920x461 coordinate space? Very odd.
#
# Let me just try y=200, 225, 250, 275, 300 at x=66:

print("Trying y values from 190 to 310:")
for test_y in [190, 200, 210, 220, 230, 240, 250, 260, 270, 280, 290, 300, 310]:
    clk(c, 66, test_y, 0.6)
    ss(c, f"test_y{test_y}.png")

print("Done")
print(f"State: ready={c.state().ready}")
