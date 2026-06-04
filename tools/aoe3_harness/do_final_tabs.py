#!/usr/bin/env python3
"""do_final_tabs.py — Clean final tab screenshots."""
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

def slp(n=0.9):
    time.sleep(n)

def clk(c, x, y, w=1.0):
    c.click(x, y)
    slp(w)

def chk(c, label=""):
    s = c.state()
    print(f"  [{label}] pid={s.pid} ready={s.ready}")
    return s

c = HarnessClient(SOCK)
c.connect()
chk(c, "start")

# Ensure at main menu
c.key(0x1B)
slp(1.5)
# Also try Back button coord (from confirmed: Back exits dialog at y=830)
# Actually ESC should be enough

# Open Options
clk(c, 130, 710, 2.0)
ss(c, "10_options_root.png")

# ============================================================
# GRAPHICS OPTIONS (already open by default)
# From prior screenshots: settings are Resolution=1920x1080, Particle Quality=Low
# ============================================================
ss(c, "11_options_graphics_BEFORE.png")

# ============================================================
# APPLY: Click APPLY button to save graphics settings
# The Apply button is at the bottom of the dialog.
# From thumbnail analysis: bottom row of dialog at y≈1020-1040
# Apply button appears to be at approximately x=636, y=1026
# ============================================================
print("Clicking Apply to save graphics settings...")
clk(c, 636, 1026, 2.0)
ss(c, "11_apply_clicked.png")
chk(c, "after_apply")

# Check for "Keep Settings?" dialog (should appear with 15s countdown)
slp(0.5)
ss(c, "11_keep_dialog_check.png")

# If Keep dialog appears, click Keep/Yes
# The dialog buttons are centered around (770, 640) or similar
clk(c, 770, 640, 1.5)
slp(0.5)

# If no dialog or already dismissed, take AFTER screenshot
ss(c, "12_options_graphics_AFTER.png")
chk(c, "after_graphics_apply")

# ============================================================
# MAP GAME OPTIONS (y=420 at x=66)
# ============================================================
print("\nMapping Game Options...")
clk(c, 66, 420, 1.2)
ss(c, "14_options_gameplay.png")
chk(c, "game_options")

# ============================================================
# MAP UI OPTIONS (y=475)
# ============================================================
print("Mapping UI Options...")
clk(c, 66, 475, 1.2)
ss(c, "15_options_interface.png")
chk(c, "ui_options")

# ============================================================
# MAP SOUND OPTIONS (y=530)
# ============================================================
print("Mapping Sound Options...")
clk(c, 66, 530, 1.2)
ss(c, "13_options_audio.png")
chk(c, "sound_options")

# ============================================================
# MAP ACCESSIBILITY (y=585)
# ============================================================
print("Mapping Accessibility...")
clk(c, 66, 585, 1.2)
ss(c, "15b_options_accessibility.png")
chk(c, "accessibility")

# ============================================================
# MAP HOTKEYS (y=620 confirmed from background scan)
# ============================================================
print("Mapping Hotkeys...")
clk(c, 66, 620, 1.2)
ss(c, "16_options_hotkeys.png")
chk(c, "hotkeys")

# ============================================================
# Back to Graphics Options
# ============================================================
print("Back to Graphics Options...")
clk(c, 66, 355, 1.2)  # Graphics Options at y=355
ss(c, "11_options_graphics_BEFORE.png")

# ============================================================
# Close Options via Back button
# The Back button from tabscan: at y≈830 exits the dialog
# ============================================================
print("Closing options (Back button)...")
clk(c, 66, 830, 1.5)
ss(c, "19_back_to_main_menu.png")
chk(c, "back_at_main_menu")

print("\nFinal state check:")
s = chk(c, "final")
if s.ready:
    print("Game is alive: ready=1")
