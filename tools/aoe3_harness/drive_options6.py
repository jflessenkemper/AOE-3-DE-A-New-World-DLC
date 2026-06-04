#!/usr/bin/env python3
"""drive_options6.py — Find correct coordinates for all option tabs."""
import sys, time
from pathlib import Path

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")

def ss(c, name):
    c.screenshot(str(SS_DIR / name))
    print(f"  [ss] {name}")

def slp(n=0.7):
    time.sleep(n)

def clk(c, x, y, w=0.8):
    c.click(x, y)
    slp(w)

c = HarnessClient(SOCK)
c.connect()
s = c.state()
print(f"State: ready={s.ready}")

# We are stuck on Graphics Options tab (Restore Defaults was triggered at y=350, reset to defaults)
# The graphics settings may have been reset to default values.
# Let me verify current state.
ss(c, "current_state.png")

# The nav panel may start at a larger x than I thought.
# From the thumbnails, the "OPTIONS" label and items seem to be in the leftmost 103px of thumbnail
# → leftmost 309px of actual.
# The text centers would be at ~50% of 309 = x≈155 actual.
# Let me try x=50 (even more left) and x=100, x=130, x=150, x=180

# Test with multiple x values at y=200 (should hit UI OPTIONS)
print("X-scan at y=200:")
for test_x in [30, 50, 66, 80, 100, 120, 140, 160, 180]:
    clk(c, test_x, 200, 0.5)
    ss(c, f"xscan_x{test_x}_y200.png")

# Test y scan at x=130 (the main menu button x which we know works)
print("Y-scan at x=130:")
for test_y in [140, 155, 170, 185, 200, 215, 230, 245, 260, 280, 300, 320, 340]:
    clk(c, 130, test_y, 0.5)
    ss(c, f"yscan_x130_y{test_y}.png")

print("Done")
