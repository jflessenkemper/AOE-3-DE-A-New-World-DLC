#!/usr/bin/env python3
"""get_graphics_post_proc.py — Scroll graphics panel and properly apply settings."""
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

# We should be at main menu. Reopen options.
c.key(0x1B)
slp(1.0)
clk(c, 130, 710, 2.0)
ss(c, "10_options_root.png")
chk(c, "options_open")

# Take BEFORE screenshot
ss(c, "11_options_graphics_BEFORE.png")

# ============================================================
# SCROLL DOWN to see Post Processing settings
# The content area scroll: we need to find where the scrollbar is
# or use keyboard arrow keys to scroll
# Try PageDown key inside content area
# ============================================================
print("Checking Post Processing section (scroll down)...")

# Click in content area first to give it focus
clk(c, 700, 500, 0.5)

# Try Page Down
c.key(0x22)  # VK_NEXT (Page Down)
slp(0.5)
ss(c, "11_graphics_pagedown.png")

c.key(0x22)
slp(0.5)
ss(c, "11_graphics_pagedown2.png")

# Try End key
c.key(0x23)  # VK_END
slp(0.5)
ss(c, "11_graphics_end.png")

# Back to top
c.key(0x21)  # VK_PRIOR (Page Up)
slp(0.3)
c.key(0x21)
slp(0.3)
c.key(0x24)  # VK_HOME
slp(0.5)
ss(c, "11_graphics_top.png")

# ============================================================
# Now try to properly find and click the APPLY button
# From screenshots: buttons are at very bottom of dialog (y≈1026)
# Let me try a few y values for the Apply button
# ============================================================

# From thumbnail at 640x400 scale:
# The bottom button row at thumbnail y≈378 → actual y = 378 * (1080/400) = 1021
# Apply button center appears at thumbnail x≈212 → actual x = 212 * (1920/640) = 636

print("\nClicking Apply button at (636, 1021)...")
clk(c, 636, 1021, 2.0)
ss(c, "11_apply1.png")
chk(c, "apply1")

# Check if keep settings dialog appeared
slp(0.5)
ss(c, "11_apply1_check.png")

# If keep dialog appeared: click KEEP button (centered in dialog)
# Typical keep dialog has buttons at center: yes/keep ≈ (770, 640)
clk(c, 770, 640, 1.5)
ss(c, "12_options_graphics_AFTER.png")
chk(c, "after_apply")

# Final state check
s = chk(c, "final")
print(f"Game {'ALIVE' if s.ready else 'DEAD'}: ready={s.ready}")
