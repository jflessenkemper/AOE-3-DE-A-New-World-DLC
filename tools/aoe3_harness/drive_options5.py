#!/usr/bin/env python3
"""drive_options5.py — Grid scan to find exact tab coordinates."""
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

# We're in Options dialog. Try clicking at y positions from 200 to 500 to find UI Options, Sound, etc.
# Use x=66 which worked for Game Options.

# First go back to Graphics Options by clicking y=130 (the very first item)
print("Trying Graphics Options at y=115...")
clk(c, 66, 115, 1.0)
ss(c, "scan_y115.png")

print("Trying y=125...")
clk(c, 66, 125, 1.0)
ss(c, "scan_y125.png")

print("Trying y=145...")
clk(c, 66, 145, 1.0)
ss(c, "scan_y145.png")

print("Trying y=160...")
clk(c, 66, 160, 1.0)
ss(c, "scan_y160.png")

# Now try much lower values for UI Options (should be after Game Options)
# Try from 200 downward in smaller increments
for test_y in [200, 215, 230, 245, 260, 275, 290, 305, 320, 335, 350]:
    print(f"Trying y={test_y}...")
    clk(c, 66, test_y, 0.5)
    ss(c, f"scan_y{test_y}.png")

print("Scan complete.")
