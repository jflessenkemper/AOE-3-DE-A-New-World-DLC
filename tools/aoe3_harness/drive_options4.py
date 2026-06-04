#!/usr/bin/env python3
"""
drive_options4.py — Final: map all option tabs + apply lowest graphics settings.
Corrected tab coordinates.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")

def ss(c, name):
    p = str(SS_DIR / name)
    c.screenshot(p)
    print(f"  [screenshot] {name}")

def slp(n=0.9):
    time.sleep(n)

def clk(c, x, y, w=1.0):
    c.click(x, y)
    slp(w)

def esc(c, w=0.8):
    c.key(0x1B)
    slp(w)

def chk(c, label=""):
    s = c.state()
    tag = f"[{label}] " if label else ""
    print(f"  {tag}STATE: pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h}")
    return s

c = HarnessClient(SOCK)
c.connect()
chk(c, "initial")

# ============================================================
# We're in the Options dialog (Game Options tab visible).
# Confirmed coordinates:
#   Tab x = 66 (center of left nav)
#   Game Options y = 176 (confirmed working)
#
# Each tab is approximately 41px tall. So:
#   Graphics Options: y ≈ 176 - 41 = 135
#   Game Options:     y ≈ 176 (confirmed)
#   UI Options:       y ≈ 176 + 41 = 217 (estimate, try 234 as bigger gap)
#   Sound Options:    y ≈ 176 + 82 = 258
#   Accessibility:    y ≈ 176 + 123 = 299
#   Hotkeys:          y ≈ 176 + 164 = 340
#
# But from thumbnail: Game Options appears to be the 2nd item.
# If each item is taller (say 50px), then:
#   Graphics Options: y ≈ 126 → center 138 (thumbnail y≈51 → actual y≈138)
#   Game Options:     y ≈ 176 (confirmed)
#   UI Options:       y ≈ 226 (= 176 + 50)
#   Sound Options:    y ≈ 276 (= 176 + 100)
#   Accessibility:    y ≈ 326 (= 176 + 150)
#   Hotkeys:          y ≈ 376 (= 176 + 200)
#   Restore Defaults: y ≈ 450
#   Back:             y ≈ 500
#
# Let me try y increments of 50 from Game Options (y=176).
# ============================================================

# We're already in Options dialog. Navigate to tabs.

print("=== Testing tab coordinates with larger increments ===")

# Click Graphics Options tab first to reset baseline
clk(c, 66, 135, 1.0)
ss(c, "tab_calibrate_graphics.png")

# Test other tabs
clk(c, 66, 226, 1.0)
ss(c, "tab_calibrate_ui_226.png")

clk(c, 66, 276, 1.0)
ss(c, "tab_calibrate_sound_276.png")

clk(c, 66, 326, 1.0)
ss(c, "tab_calibrate_accessibility_326.png")

clk(c, 66, 376, 1.0)
ss(c, "tab_calibrate_hotkeys_376.png")

chk(c, "tab_calibration")
print("Tab calibration screenshots taken.")
