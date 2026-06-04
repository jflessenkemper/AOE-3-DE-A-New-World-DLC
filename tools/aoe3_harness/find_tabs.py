#!/usr/bin/env python3
"""find_tabs.py — Precisely find all option tab click coords."""
import sys, time
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")

def ss(c, name):
    path = str(SS_DIR / name)
    c.screenshot(path)
    return path

def slp(n=0.7):
    time.sleep(n)

def clk(c, x, y, w=0.7):
    c.click(x, y)
    slp(w)

def is_different_from(path1, path2, x1=300, x2=1100, y1=100, y2=800, threshold=10):
    """Check if two screenshots show different content in the specified area."""
    img1 = Image.open(path1)
    img2 = Image.open(path2)
    arr1 = np.array(img1)[y1:y2, x1:x2, :3].astype(float)
    arr2 = np.array(img2)[y1:y2, x1:x2, :3].astype(float)
    diff = float(np.mean(np.abs(arr1 - arr2)))
    return diff, diff > threshold

c = HarnessClient(SOCK)
c.connect()
print(f"State: ready={c.state().ready}")

# Ensure we're on Graphics Options (baseline)
graphics_path = ss(c, "baseline_graphics.png")
print(f"Baseline (should be Graphics Options): {graphics_path}")

# Now scan y values from 100 to 400 at x=66, 100, 130 looking for tab changes
print("\nScanning y values from 100 to 400 at multiple x values...")
print("Will detect any screenshot that differs significantly from baseline...")

tab_hits = {}

for x in [66, 100, 130]:
    prev_path = graphics_path
    for test_y in range(100, 420, 5):
        clk(c, x, test_y, 0.5)
        p = ss(c, f"fscan_x{x}_y{test_y}.png")

        diff, is_diff = is_different_from(p, graphics_path)
        if is_diff:
            print(f"  DIFFERENT at x={x}, y={test_y}: diff={diff:.1f}")
            tab_hits.setdefault(x, []).append((test_y, diff))

    # Reset to graphics options (Escape + reopen)
    c.key(0x1B)  # ESC out of options
    slp(1.5)
    c.click(130, 710)  # Click Options button
    slp(2.0)
    graphics_path = ss(c, f"reset_after_x{x}.png")
    print(f"  Reset after x={x} scan")

print("\n=== Tab hit summary ===")
for x, hits in tab_hits.items():
    print(f"x={x}: {hits}")

print(f"Final state: ready={c.state().ready}")
