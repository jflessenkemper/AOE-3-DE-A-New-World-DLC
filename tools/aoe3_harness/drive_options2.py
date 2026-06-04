#!/usr/bin/env python3
"""
drive_options2.py — Second pass: properly map all options tabs and apply lowest graphics settings.
"""
import sys, time, json
from pathlib import Path

sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
SS_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ui_calibration")

def ss(c, name):
    p = str(SS_DIR / name)
    c.screenshot(p)
    print(f"  [screenshot] {name}")
    return p

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
print("Connected.")
chk(c, "initial")

# ============================================================
# From prior screenshots we know exact coordinates:
#
# Options dialog left nav (x≈66, tabs at various y):
#   Graphics Options: y≈143
#   Game Options:     y≈176
#   UI Options:       y≈209
#   Sound Options:    y≈242
#   Accessibility:    y≈275
#   Hotkeys:          y≈308
#   Restore Defaults: y≈380
#   Back:             y≈413
#
# The dialog content area is roughly x=130-390 wide on left side
# and main content x=130-390 for nav, x=400-1800 for content.
# Wait - from screenshot image (640x400 thumbnail of 1920x1080):
# The dialog appears to be centered in the screen.
# Left nav panel appears at x=0-100 in thumbnail (0-300 in actual coords)
# Content panel at x=100-400 in thumbnail (300-1200 in actual coords)
#
# Let me recalculate from the thumbnail:
# The 640x400 image is thumbnail of 1920x1080.
# Scale factor: 1920/640=3.0x for horizontal, 1080/400=2.7x for vertical
#
# In thumbnail, Graphics Options tab appears at approximately:
#   x≈66, y≈53 in thumbnail → x≈198, y≈143 in actual
# Game Options:    y≈65 → y≈175
# UI Options:      y≈77 → y≈208
# Sound Options:   y≈89 → y≈241
# Accessibility:   y≈101 → y≈273
# Hotkeys:         y≈113 → y≈306
# Restore Defaults: y≈140 → y≈378
# Back:            y≈153 → y≈413
#
# Content area in thumbnail: x≈130-380
# In actual coords: x≈390-1140
#
# Controls in Graphics tab content:
# "Display Mode" row: y≈22 in thumbnail → y≈59 in actual... wait the header is "Graphics Options"
# Let me re-examine: the dialog starts at y≈8 in thumbnail (y≈22 in actual? no)
#
# The dialog "GRAPHICS OPTIONS" title is at top y≈8 thumbnail → y≈22 actual (wrong, too high)
# Looking at the image more carefully:
# The dialog occupies roughly y=10-395 in the 400px thumbnail
# → y=27-1067 in actual (almost full height)
#
# Within the dialog, the title "GRAPHICS OPTIONS" is at thumbnail y≈14 → actual y≈38
# The left nav items start at thumbnail y≈45 → actual y≈122
#
# Content "DISPLAY" section header: thumbnail y≈25 → actual y≈67
# Display Mode row: thumbnail y≈31 → actual y≈84
# Resolution row: thumbnail y≈37 → actual y≈100
# Frame Rate Limit row: thumbnail y≈44 → actual y≈119
# VSync row: thumbnail y≈50 → actual y≈135
# Resolution Scale row: thumbnail y≈57 → actual y≈154
# "DETAIL" section header: thumbnail y≈64 → actual y≈173
# Particle Quality row: thumbnail y≈71 → actual y≈192
# Obscured Unit Alpha row: thumbnail y≈79 → actual y≈213
# Dynamic Lights row: thumbnail y≈88 → actual y≈238
# Tracer Effects row: thumbnail y≈95 → actual y≈257
# Clouds row: thumbnail y≈103 → actual y≈278
#
# Buttons at bottom:
# Revert: thumbnail y≈380 → actual y≈1026
# Apply:  thumbnail y≈380 → actual y≈1026
# Cancel: thumbnail y≈380 → actual y≈1026
#
# BUT WAIT: the thumbnail size shows the screenshot at 640x400 resolution
# but the actual game is 1920x1080. The coordinates I need are in 1920x1080 space.
# I used c.screenshot() which saves the full 1920x1080 PNG but it's displayed as thumbnail.
# The render tool shows it at smaller size, but pixel coordinates I click must be 1920x1080.
#
# So I need to READ the image at full resolution to understand pixel coordinates.
# The thumbnail shows the image scaled down. The actual pixel positions in game are 1920x1080.
#
# From the thumbnail analysis (640x400 display of 1920x1080 image):
# Scale: x_actual = x_thumb * (1920/640) = x_thumb * 3.0
#        y_actual = y_thumb * (1080/400) = y_thumb * 2.7
#
# Let me recalculate with these scales:
#
# Left nav tabs (x≈66 thumb → x≈198 actual):
#   Graphics Options: y≈53 thumb → y≈143 actual ✓ (matches what I calculated before)
#   Game Options:     y≈65 thumb → y≈176 actual ✓
#   UI Options:       y≈77 thumb → y≈208 actual ✓
#   Sound Options:    y≈89 thumb → y≈241 actual ✓
#   Accessibility:    y≈101 thumb → y≈273 actual ✓
#   Hotkeys:          y≈113 thumb → y≈306 actual ✓
#
# Content controls (dropdown arrows on right side of content):
# The dropdown arrows (▼) for dropdowns in content area:
#   Display Mode ▼: x≈343 thumb → x≈1029 actual, y≈31 thumb → y≈84 actual
#   Resolution ▼:   x≈343 thumb → x≈1029 actual, y≈37 thumb → y≈100 actual
#   Particle Quality ▼: x≈343 thumb → x≈1029 actual, y≈71 thumb → y≈192 actual
#   Resolution Scale ▼: x≈343 thumb → x≈1029 actual, y≈57 thumb → y≈154 actual
#
# APPLY button: x≈212 thumb → x≈636 actual, y≈380 thumb → y≈1026 actual
# CANCEL button: x≈290 thumb → x≈870 actual, y≈380 thumb → y≈1026 actual
# REVERT button: x≈160 thumb → x≈480 actual, y≈380 thumb → y≈1026 actual
#
# Now the image thumbnail is 640x400 but I need to reconsider:
# The render tool might show it at different sizes. The game outputs 1920x1080.
# The key point is: clicking coordinates must be 1920x1080 space.
#
# ============================================================

# ============================================================
# Open Options
# ============================================================
print("\n--- Opening Options ---")
clk(c, 130, 710, 1.8)
ss(c, "10_options_root.png")
chk(c, "options_open")

# ============================================================
# We're already on Graphics Options tab.
# The content shows current settings. From the first screenshot we can see:
# - Display Mode: Windowed (row at y≈84)
# - Resolution: 1920x1080 (row at y≈100) -- ALREADY 1920x1080!
# - Frame Rate Limit: 30 FPS | 144 FPS | 144 FPS (row at y≈119)
# - VSync: unchecked (row at y≈135)
# - Resolution Scale: 100% (row at y≈154)
# - DETAIL section:
#   - Particle Quality: Low (dropdown at y≈192) -- ALREADY LOW!
#   - Obscured Unit Alpha: 60% slider (row at y≈213)
#   - Dynamic Lights: off/unchecked (row at y≈238)
#   - Tracer Effects: off/unchecked (row at y≈257)
#   - Clouds: off/unchecked (row at y≈278)
#
# There's no global "Quality Preset" dropdown visible in this view.
# We need to scroll down to see if there are more settings.
#
# Also we should check if there IS a preset dropdown that isn't visible.
# The game may need scrolling to see all graphics options.
# ============================================================

# Scroll down in the content area to see all graphics options
print("Scrolling down to see more graphics options...")
# Move mouse to content area center first
c.move(700, 400)
slp(0.3)
# Scroll down
c.wheel(0, -3.0)  # Scroll down (negative = down)
slp(0.5)
ss(c, "11_options_graphics_scrolled_down.png")

c.wheel(0, -3.0)  # More scroll
slp(0.5)
ss(c, "11a_graphics_more_scroll.png")

c.wheel(0, -3.0)
slp(0.5)
ss(c, "11b_graphics_max_scroll.png")

# Scroll back to top
c.wheel(0, 10.0)  # Scroll up
slp(0.5)
ss(c, "11c_graphics_top.png")

# Take a careful screenshot of the full graphics page
ss(c, "11_options_graphics_BEFORE.png")

print("Graphics options fully visible. Now checking Particle Quality is at Low.")
print("Current state: Particle Quality = Low, Resolution = 1920x1080")
print("These appear to already be at lowest/correct settings.")
print("Need to check if there are more quality settings below...")

# ============================================================
# Now properly map all options tabs
# ============================================================
# We need screenshots of each tab. From 10_options_root.png we know exact coords:
# Left nav: Graphics Options (x≈198, y≈143), Game Options (x≈198, y≈176), etc.

print("\n--- Mapping Game Options tab ---")
clk(c, 198, 176, 1.2)
ss(c, "14_options_gameplay.png")
chk(c, "game_options")

print("\n--- Mapping UI Options tab ---")
clk(c, 198, 209, 1.2)
ss(c, "15_options_interface.png")
chk(c, "ui_options")

print("\n--- Mapping Sound Options tab ---")
clk(c, 198, 242, 1.2)
ss(c, "13_options_audio.png")
chk(c, "sound_options")

print("\n--- Mapping Accessibility tab ---")
clk(c, 198, 275, 1.2)
ss(c, "15b_options_accessibility.png")
chk(c, "accessibility")

print("\n--- Mapping Hotkeys tab ---")
clk(c, 198, 308, 1.2)
ss(c, "16_options_hotkeys.png")
chk(c, "hotkeys")

# ============================================================
# Go back to Graphics Options tab to apply settings
# ============================================================
print("\n--- Back to Graphics Options tab ---")
clk(c, 198, 143, 1.2)
ss(c, "11_options_graphics_BEFORE.png")
chk(c, "graphics_before")

# ============================================================
# The graphics settings appear to already be:
# - Resolution: 1920x1080 ✓
# - Particle Quality: Low ✓
#
# We need to check if there are more quality settings.
# Let's scroll down to see everything, then set each to lowest.
# ============================================================

# Scroll down to see more settings
c.move(700, 400)
slp(0.3)
c.wheel(0, -5.0)
slp(0.6)
ss(c, "11d_graphics_scrolled.png")

# Scroll back up
c.wheel(0, 10.0)
slp(0.5)

# Now apply - even if settings look already low, let's:
# 1. Set Particle Quality to Low (click dropdown, select Low)
# 2. Set Resolution Scale to 100%
# 3. Click Apply

# PARTICLE QUALITY DROPDOWN: at approx x=1029, y=192 (from thumbnail analysis)
# But let's recalculate more carefully:
# In the 640x400 thumbnail display of 1920x1080 image:
# - The dropdown value "Low" for Particle Quality appears at roughly x=270 thumbnail
# - The ▼ arrow is at x≈345 thumbnail
# - y≈71 in thumbnail
#
# Actual coords:
# x_arrow = 345 * 3.0 = 1035 actual
# y = 71 * 2.7 = 192 actual
#
# But looking more carefully at the screenshot thumbnail - the dialog might not fill
# the full 1920x1080. Let me use coordinates relative to what I see.
#
# The Options dialog from screenshot 10_options_root.png:
# Looking at the thumbnail at native analysis:
# The dialog appears to span approximately the full height.
#
# Particle Quality dropdown ▼: trying (1035, 192)
print("\n--- Clicking Particle Quality dropdown ---")
clk(c, 1035, 192, 0.8)
ss(c, "11e_particle_quality_dropdown.png")

# If dropdown opened, we need to find and click "Low" option
# Low should be near the bottom of the dropdown list
# Typical AoE3 quality options: Ultra, High, Medium, Low
# Let's see what opened and click the lowest option
# Dropdown items usually appear below the clicked dropdown
# If 4 items, they'd be at y≈220, 240, 260, 280 approximately

# Click "Low" option - should be the last item in list
clk(c, 900, 260, 0.5)
ss(c, "11f_after_particle_select.png")

# If wrong, try a lower y
clk(c, 900, 280, 0.5)
ss(c, "11g_particle_low_selected.png")

# ============================================================
# Now we need to set any other quality sliders/dropdowns to minimum
# Looking at what's visible:
# - Obscured Unit Alpha: currently at 60% - slider control
#   Slider track center: the dot appears around x=780, y=213 (thumbnail x≈260, y≈79)
#   MIN label is at left side of slider: x≈480, y≈213
#   To set to MIN: click the MIN position of the slider
#   MIN position: looking at thumbnail x≈170 → actual x≈510, y≈79*2.7≈213
# - Dynamic Lights: checkbox/toggle - appears to be OFF already (circle outline)
# - Tracer Effects: appears to be OFF already
# - Clouds: appears to be OFF already
# ============================================================

# Set Obscured Unit Alpha to minimum
print("\n--- Setting Obscured Unit Alpha to MIN ---")
# The MIN label/position of the slider
# From thumbnail: MIN text at x≈170, y≈79 → actual x≈510, y≈213
# The slider handle/track starts at MIN position
clk(c, 510, 213, 0.5)  # Click at MIN position
ss(c, "11h_slider_min.png")

# ============================================================
# Apply the settings
# ============================================================
print("\n--- Clicking Apply button ---")
# Apply button from thumbnail: x≈212, y≈380 → actual x≈636, y≈1026
clk(c, 636, 1026, 2.0)
ss(c, "11_confirm_dialog.png")
chk(c, "after_apply")

# If a confirmation dialog appeared, click "Yes" or "Keep"
# The confirmation dialog typically appears in center of screen
# "Keep" button is usually at left of center, "Revert" on right
# Center of screen for dialog: y≈540
# "Keep"/"Yes" button: approximately (770, 650) or (960, 650)
print("Checking for confirmation dialog...")
ss(c, "11_confirm_check.png")

# Click center/left to confirm keeping settings
clk(c, 770, 650, 1.5)
ss(c, "12_options_graphics_AFTER.png")
chk(c, "after_confirm")

# If that didn't work (no dialog), just take screenshot of current state
ss(c, "12_options_graphics_AFTER.png")
chk(c, "final_graphics")

# Check state to verify game survived
s = chk(c, "graphics_applied")
if s.ready:
    print("SUCCESS: Game still alive (ready=1) after applying graphics settings")
else:
    print("ERROR: Game is not ready after applying settings!")

# ============================================================
# Return to main menu via Back button
# ============================================================
print("\n--- Returning to main menu via Back ---")
# Back button at x≈198, y≈413 from our thumbnail analysis
clk(c, 198, 413, 1.5)
ss(c, "19_back_to_main_menu.png")
chk(c, "back_at_main_menu")

print("\nAll done! Screenshots captured in artifacts/validation/ui_calibration/")
