#!/usr/bin/env python3
"""
drive_options3.py — Final pass: correct tab coords, scroll graphics, apply lowest settings.
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

# The game is at main menu. Let me re-open options and carefully calibrate tabs.
# From 10_options_root.png screenshot, the left nav panel occupies roughly x=0-103 (thumbnail)
# → actual x=0-309
# The tabs (clickable areas) appear at:
#   "GRAPHICS OPTIONS": thumbnail y≈52 → actual y≈140; x≈50 thumb → x≈150 actual
#   "GAME OPTIONS":     thumbnail y≈64 → actual y≈173; x≈50 → x≈150
#   "UI OPTIONS":       thumbnail y≈76 → actual y≈205; x≈50 → x≈150
#   "SOUND OPTIONS":    thumbnail y≈88 → actual y≈238; x≈50 → x≈150
#   "ACCESSIBILITY":    thumbnail y≈101 → actual y≈273; x≈50 → x≈150
#   "HOTKEYS":          thumbnail y≈113 → actual y≈305; x≈50 → x≈150
#
# Wait - but the thumbnail is 640x400 and the game outputs 1920x1080.
# Scale factors: x_scale = 1920/640 = 3.0, y_scale = 1080/400 = 2.7
#
# But I notice the options dialog itself might not fill the full 1920x1080 window.
# The dialog appears to be inside the main game window.
# Looking at the screenshot: the background shows the 3D game world (London dock scene),
# and the dialog is overlaid on the left portion.
#
# The dialog spans (from thumbnail visual inspection):
#   Left edge: x≈0 (dialog starts at left screen edge)
#   Right edge: x≈380 thumbnail → x≈1140 actual
#   Top: y≈0 (dialog starts at top)
#   Bottom: y≈400 thumbnail → y≈1080 actual (full height)
#
# Within dialog:
#   Left nav panel right edge: x≈103 thumbnail → x≈309 actual
#   Left nav items center: x≈52 thumbnail → x≈156 actual
#
# The tab y positions (measured from thumbnail more carefully):
# The "OPTIONS" header at y≈38 → y≈103 actual
# "GRAPHICS OPTIONS" tab: y≈51 → y≈138 actual
# "GAME OPTIONS" tab:     y≈63 → y≈170 actual
# "UI OPTIONS" tab:       y≈76 → y≈205 actual
# "SOUND OPTIONS" tab:    y≈88 → y≈238 actual
# "ACCESSIBILITY" tab:    y≈100 → y≈270 actual
# "HOTKEYS" tab:          y≈113 → y≈305 actual
# (blank space)
# "RESTORE DEFAULTS":     y≈141 → y≈381 actual
# "BACK":                 y≈153 → y≈413 actual
#
# So the tab centers for clicking should be approximately:
TAB_X = 66   # Center x of left nav panel (actual coords: approximately x=66 based on dialog left third)

# Actually I need to reconsider. The nav panel in the THUMBNAIL appears to span x=0-103.
# In ACTUAL coords: x=0-309. Center = x=154.
# But the game coordinates match the harness which is 1920x1080 output.
# My earlier clicks at x=198 may have been in the correct x range but wrong y.

# Let me try being more precise. The dialog left nav buttons appear to be buttons with
# text centered horizontally. The text seems to be around x=50-100 in the thumbnail.
# In actual coords: x=150-300.
# Center of left nav: x=155 actual.

# But wait: my previous script clicked at x=198 (close to 155-300 range) and it showed
# the same content... Could the tabs just not have registered?
# Let me try clicking with slightly longer delay to confirm registration.

# Open Options
print("Opening Options...")
clk(c, 130, 710, 2.0)
ss(c, "10_options_root.png")

# The left nav items. From the original screenshot (thumbnail display 640x400):
# The left nav takes up approximately 1/6 of screen width (about 320px actual)
# Let's try a range of x values and very precise y values.

# Based on careful measurement of thumbnail:
# "GAME OPTIONS" should be at approximately y=173 actual. Let's try several x values.

print("\n--- Testing Game Options tab click precision ---")
# Try clicking the middle of the "GAME OPTIONS" text area
clk(c, 66, 176, 1.0)
ss(c, "tab_test_game_x66.png")

clk(c, 66, 209, 1.0)
ss(c, "tab_test_ui_x66.png")

clk(c, 66, 242, 1.0)
ss(c, "tab_test_sound_x66.png")

print("\nTesting complete. Reading tab_test screenshots.")
chk(c, "tab_test_done")
