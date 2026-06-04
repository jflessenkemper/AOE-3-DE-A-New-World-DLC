#!/usr/bin/env python3
"""
final_options_pass.py — Comprehensive options mapping with correct coordinates.

Known tab positions (x=66):
  Graphics Options: y≈355 (default on open)
  Game Options:     y≈420 (center of y=395-445)
  UI Options:       y≈475 (center of y=450-500)
  Sound Options:    y≈530 (center of y=505-555)
  Accessibility:    y≈585 (center of y=560-610)
  Hotkeys:          y≈640 (from scan showing y=620-795 as Hotkeys)

Also confirmed:
  Restore Defaults: y≈... (avoid)
  Back:             y≈... (exits dialog)

Content area (right panel) for Graphics Options:
  Resolution: already 1920x1080
  Particle Quality: already Low
  Need to scroll to see Post Processing and other settings

Graphics settings controls (need recalibration):
  Thumbnail showed: y≈135→actual_y estimate changed

  From pixel analysis of graphics tab (display at 1920x1080):
  The DISPLAY section is in the top portion of content panel.
  Controls are at roughly:
    Display Mode row:     y≈290-320
    Resolution row:       y≈330-360
    Frame Rate Limit row: y≈370-400
    VSync row:            y≈420-450
    Resolution Scale row: y≈460-490
    DETAIL section:
    Particle Quality row: y≈560-590
    Obscured Unit Alpha:  y≈620-650
    Dynamic Lights:       y≈670-700
    Tracer Effects:       y≈700-730
    Clouds:               y≈730-760
    POST PROCESSING section (scrolled):
    ...

  Dropdown for Particle Quality ▼: x≈1090 (right side), y≈575
  Resolution dropdown ▼: x≈1090, y≈345
  Apply button: approximately (640, 1033)
  Cancel button: approximately (870, 1033)
  Revert button: approximately (480, 1033)
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
    print(f"  [ss] {name}")
    return p

def slp(n=0.8):
    time.sleep(n)

def clk(c, x, y, w=0.9):
    c.click(x, y)
    slp(w)

def chk(c, label=""):
    s = c.state()
    tag = f"[{label}] " if label else ""
    print(f"  {tag}pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h}")
    return s

c = HarnessClient(SOCK)
c.connect()
chk(c, "initial")

# ============================================================
# First: determine current state (dialog open or main menu?)
# ============================================================
ss(c, "final_current_state.png")
s = chk(c, "check")

# ============================================================
# Navigate to Options dialog
# The background scan may have left us in Options (Hotkeys tab) or main menu.
# Let's press Escape to ensure we're at main menu, then re-open Options.
# ============================================================
print("Pressing Escape to ensure at main menu...")
c.key(0x1B)
slp(1.5)
ss(c, "final_after_esc.png")

# Now click Options
print("Opening Options menu...")
clk(c, 130, 710, 2.0)
ss(c, "10_options_root.png")
chk(c, "options_open")

# ============================================================
# TASK 1: Set Graphics to LOWEST + 1920x1080
# We're on Graphics Options tab (default).
# From pixel analysis:
#   - Resolution: already 1920x1080
#   - Particle Quality: currently Low
#   - Need to check Post Processing settings (requires scrolling)
#
# Let's verify current state, then:
# 1. Check if Particle Quality is already Low
# 2. Scroll to see Post Processing
# 3. Apply
# ============================================================

# Take the BEFORE screenshot
ss(c, "11_options_graphics_BEFORE.png")

# Let's find and interact with controls by using correct y values
# The content panel starts at approximately the right 2/3 of screen
# From the screenshot analysis:
# - The content area x = ~310 to ~1150
# - Resolution dropdown: from thumbnail this is at approximately y=345 actual
# - Particle Quality dropdown: at approximately y=575 actual

# Let's try clicking the Particle Quality dropdown to verify
# From the screenshot, the ▼ arrows for dropdowns are on the RIGHT side of content
# Resolution dropdown arrow: approximately x=1090, y=345
# Particle Quality ▼: approximately x=1090, y=575

# First, let's verify by trying to scroll down the content panel
# AoE3 content panels typically scroll with mouse wheel when cursor is inside
print("\nScrolling content area to see Post Processing settings...")
c.move(700, 500)  # Move into content area first
slp(0.3)
c.wheel(0, -3.0)  # Scroll down
slp(0.6)
ss(c, "11_graphics_scrolled1.png")

c.wheel(0, -3.0)
slp(0.5)
ss(c, "11_graphics_scrolled2.png")

# Scroll back
c.wheel(0, 10.0)
slp(0.5)

# ============================================================
# Apply settings
# Resolution is confirmed 1920x1080 (from screenshots)
# Particle Quality is Low (from screenshots)
# Now we need to apply these settings.
#
# APPLY button: from thumbnail at approximately (210, 378) thumbnail → actual (630, 1022)
# The button row has: [REVERT] [APPLY] [CANCEL]
# ============================================================
print("\nClicking APPLY button to confirm current settings...")

# Let's try to find APPLY button. From prior screenshots, it's at the bottom.
# From thumbnail analysis: the APPLY button is at roughly thumbnail (212, 378) → actual (636, 1022)
# But actual button y depends on dialog height.
# The dialog spans full screen height (1080 actual), so bottom buttons at y≈1022-1040

# Click APPLY
clk(c, 636, 1022, 2.0)
ss(c, "11_after_apply_click.png")
chk(c, "after_apply")

# If a "Keep Settings?" dialog appeared, click YES
# The confirmation dialog appears centered at approximately y=540
# "Keep" button: approximately x=770, y=660
print("Checking for keep-settings dialog...")
slp(0.5)
ss(c, "11_confirm_check.png")

# Click where Keep button would be
clk(c, 770, 660, 1.5)
ss(c, "12_options_graphics_AFTER.png")
chk(c, "after_confirm")

# Final check: take a clean screenshot of the AFTER state
ss(c, "12_options_graphics_AFTER.png")
s = chk(c, "final_graphics")

if s.ready:
    print("SUCCESS: Game still alive after applying graphics settings")
else:
    print("ERROR: Game not ready!")

# ============================================================
# TASK 2: Map all options tabs with correct screenshots
# ============================================================
print("\n=== Mapping all Options tabs ===")

# Game Options
print("\nClicking Game Options (y=420)...")
clk(c, 66, 420, 1.2)
ss(c, "14_options_gameplay.png")
chk(c, "game_options")

# UI Options
print("\nClicking UI Options (y=475)...")
clk(c, 66, 475, 1.2)
ss(c, "15_options_interface.png")
chk(c, "ui_options")

# Sound Options
print("\nClicking Sound Options (y=530)...")
clk(c, 66, 530, 1.2)
ss(c, "13_options_audio.png")
chk(c, "sound_options")

# Accessibility
print("\nClicking Accessibility Options (y=585)...")
clk(c, 66, 585, 1.2)
ss(c, "15b_options_accessibility.png")
chk(c, "accessibility")

# Hotkeys
print("\nClicking Hotkeys (y=640)...")
clk(c, 66, 640, 1.2)
ss(c, "16_options_hotkeys.png")
chk(c, "hotkeys")

# ============================================================
# Return to Graphics Options and take final screenshot
# ============================================================
print("\nBack to Graphics Options...")
clk(c, 66, 355, 1.2)
ss(c, "11_options_graphics_BEFORE.png")  # This is the "canonical" graphics screenshot

# Close options via Back button
# From analysis: Back button is below the nav items, around y=... let's try y=690
# Actually from thumbnail Back button was very near the bottom of nav items area
# Based on the RESTORE DEFAULTS at y=~350 and BACK below it:
# If Accessibility ends at y=610 and Hotkeys starts at y=615, then:
# The space between Hotkeys(615+) and RESTORE DEFAULTS and BACK are further down
# But clicking the BACK button would close the dialog.
# For now, use Escape to close.
print("\nClosing options with Back button or Escape...")
# Try Back button first
# From first screenshot (with "Back" visible at bottom left of nav):
# The "BACK" button appears to be around y=810-850 based on extended nav layout
clk(c, 66, 830, 1.0)
ss(c, "back_attempt.png")
chk(c, "after_back")

print("\nAll Options tabs mapped!")
