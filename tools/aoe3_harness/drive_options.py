#!/usr/bin/env python3
"""
drive_options.py — Full Options mapping + lowest graphics preset script.

Runs against live AoE3 DE at /tmp/AOE3DEHarness.sock.
Screenshots go to artifacts/validation/ui_calibration/
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
    print(f"  [screenshot] {p}")
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
    print(f"  {tag}STATE: pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h} uptime={s.uptime_ms}ms")
    return s

c = HarnessClient(SOCK)
c.connect()
print("Connected.")
chk(c, "initial")

# ============================================================
# STEP 1: Verify main menu + take screenshot
# ============================================================
ss(c, "09_main_menu_verify.png")
print("Main menu verified.")

# ============================================================
# STEP 2: Open Options
# ============================================================
print("\n--- Opening Options (130, 710) ---")
clk(c, 130, 710, 1.8)
ss(c, "10_options_root.png")
chk(c, "options_open")

# ============================================================
# STEP 3: Read the options screen and identify tab positions
# The game should now show the Options dialog.
# AoE3 DE options dialog has tabs at the top.
# We need to screenshot and then determine tab positions.
# For now we'll try clicking known tab areas.
#
# AoE3 DE 1920x1080 options dialog layout (typical):
#   - Dialog centered, roughly x=130 to x=1790, y=60 to y=980
#   - Tab bar row around y=90-115
#   - Tabs (left to right): Graphics, Audio, Gameplay, Interface, Hotkeys
#   - Each tab roughly 200px wide starting from x=200
#     Graphics  ~ (290, 100)
#     Audio     ~ (490, 100)
#     Gameplay  ~ (690, 100)
#     Interface ~ (890, 100)
#     Hotkeys   ~ (1090, 100)
#
# BUT the actual positions depend on localization + mod. We need to verify.
# The 10_options_root.png screenshot will show us what's there.
# For now attempt the Graphics tab first.
# ============================================================

# The options dialog in AoE3 DE - tabs are usually centered top of panel
# Try clicking center-ish of where Graphics tab should be
print("\n--- Clicking Graphics tab ---")
# AoE3 DE default options: Graphics is typically the FIRST (leftmost) tab
# In a 1920-wide dialog, if dialog starts ~x=145 (left panel edge), tabs
# begin around x=200-250 from left edge of content area
# Let's try x=260 (first tab) at y=95

# Actually, let's look at what screenshot shows. For now, proceed with estimates.
# The content panel in AoE3 DE options is on the right side (x~400+)
# The left side (x<400) is a tab list (vertical tabs), not horizontal tabs!
# AoE3 DE options uses VERTICAL tabs on the left side:
#   Graphics  ~ (260, 140) or first item
#   Audio     ~ (260, 190)
#   Gameplay  ~ (260, 240)
#   Interface ~ (260, 290)
#   Hotkeys   ~ (260, 340)

# Let's try the vertical tab approach - Graphics is first
clk(c, 260, 140, 1.0)
ss(c, "10a_options_after_tab1_click.png")

# Also try: maybe tabs are labeled at a different y
# Let's try a few more coordinates to find the graphics tab
# Actually, AoE3 DE options has: "GRAPHICS" tab typically as first item
# in a left vertical nav list. The exact y depends on layout.
# From memory: in AoE3 DE the left nav starts around y=130 with first item.

# Let's also try clicking what might be "Graphics" text if it didn't work
clk(c, 260, 160, 0.8)
ss(c, "10b_options_nav_try.png")

# Now let's look at where the content area controls are and try to identify
# the graphics preset dropdown. Take another screenshot.
ss(c, "11_options_graphics_BEFORE.png")
chk(c, "graphics_tab")

# ============================================================
# STEP 4: Find and set Quality Preset to lowest
# ============================================================
# In AoE3 DE Graphics settings, the QUALITY PRESET dropdown is typically
# at the top of the content area. Content area is roughly x=450-1800.
# Controls in the content area:
#   Quality Preset dropdown: approximately (960, 195) or label left, value right
#   The dropdown arrow (▼) is typically at right side of the dropdown widget.
#
# AoE3 DE 1920x1080 Graphics tab layout estimate:
#   Row 1: "Quality Preset" label (x~500) | dropdown value (x~960) | ▼(x~1100)
#   Row 2: "Resolution"      label (x~500) | dropdown value (x~960) | ▼(x~1100)
#   Row 3: "Display Mode"    label (x~500) | dropdown value (x~960) | ▼(x~1100)
#   Row 4: "VSync"           label (x~500) | checkbox (x~960)
#   ...more rows...
#   Bottom: "Apply" button and "Reset to Default" button
#
# The exact y values for each row depend on game version/mod.
# Let's try clicking the Quality Preset dropdown first.

print("\n--- Attempting Quality Preset dropdown ---")
# Try clicking where preset dropdown value should be
# Multiple attempts with slightly different coords

# First attempt: typical position for first dropdown in content area
# In AoE3 DE the first graphics option row y is typically ~165-185
# after the tab header (which takes up ~y=60-140 area)
clk(c, 960, 178, 0.8)
ss(c, "11c_preset_click1.png")

# Check if dropdown opened (look for list items below)
# If it opened, the lowest quality is at the BOTTOM of the dropdown list
# AoE3 DE quality presets: Ultra, High, Medium, Low (Low is lowest)
# OR: Ultra High, High, Medium, Low, Very Low
# Dropdown items would appear below the clicked widget

# Try pressing End key to jump to last (lowest) item if dropdown is open
c.key(0x23)  # VK_END
slp(0.5)
ss(c, "11d_after_end_key.png")

# Press Enter to confirm selection
c.key(0x0D)  # VK_RETURN
slp(0.8)
ss(c, "11e_after_enter.png")

# ============================================================
# STEP 5: Find and set Resolution to 1920x1080
# ============================================================
print("\n--- Attempting Resolution dropdown ---")
# Resolution is typically the 2nd major dropdown in Graphics settings
# Estimated position: y ~ 220-240 (one row below preset)
clk(c, 960, 228, 0.8)
ss(c, "11f_resolution_click.png")

# 1920x1080 should be an option. It may be near the top or need selection.
# If dropdown opened, scroll to find 1920x1080 or type it.
# Since we can't type in dropdowns easily, we need to click the right item.
# For now take screenshot to see what opened.

# Let's try Home key to go to top of dropdown, then find 1920x1080
c.key(0x24)  # VK_HOME
slp(0.3)
ss(c, "11g_resolution_list.png")

# Press Escape to close without changing (we'll come back after seeing screenshots)
esc(c, 0.5)
ss(c, "11h_after_esc.png")

# ============================================================
# STEP 6: Let's take careful screenshots to read UI structure
# ============================================================
# At this point we have screenshots. Let me take a fresh clean screenshot
# of the full graphics settings page to read all control positions.
ss(c, "11_options_graphics_BEFORE.png")

print("\nInitial exploration done. Analyzing screenshots...")
print("Will now proceed with targeted interactions based on what we see.")

# ============================================================
# STEP 7: More systematic approach to find preset dropdown
# ============================================================
# In AoE3 DE, the options dialog structure:
# - Left side: vertical tab list (category navigation)
# - Right side: content area for selected tab
#
# For Graphics tab, common control layout at 1920x1080:
# The dialog is full-screen or large window.
# Let's try clicking through several y positions to find the preset

print("\n--- Systematic search for preset dropdown ---")
# Try rows from y=160 to y=280 at x=900 (right of labels)
for test_y in [165, 185, 205, 225, 245]:
    print(f"  Testing click at (900, {test_y})")
    clk(c, 900, test_y, 0.4)
    esc(c, 0.4)

ss(c, "11i_systematic_search.png")

# ============================================================
# STEP 8: Try interacting with controls via keyboard navigation
# ============================================================
# Use Tab key to navigate between controls
# Focus the content area first by clicking in it
print("\n--- Keyboard navigation approach ---")
clk(c, 700, 300, 0.5)  # Click in content area to focus it
# Tab through controls to find focusable dropdowns
for i in range(3):
    c.key(0x09)  # VK_TAB
    slp(0.3)
ss(c, "11j_tab_navigation.png")

# ESC to reset
esc(c, 0.5)

# ============================================================
# FINAL: Take clean screenshot of Graphics tab as it is now
# ============================================================
ss(c, "11_options_graphics_BEFORE.png")
chk(c, "before_settings_change")

print("\nPhase 1 screenshots done. Now proceeding to map remaining tabs.")

# ============================================================
# MAP OTHER OPTIONS TABS
# ============================================================
# We need to identify tab positions from the screenshots.
# Based on AoE3 DE layout, options has vertical navigation on left.
# Each category button is in the left nav panel.
# Let's try clicking different y positions in the left nav area.

# Left nav panel is roughly x=145-380
# Tab items from top:
#   Graphics/Video  y ~ 140
#   Audio           y ~ 190
#   Gameplay        y ~ 240
#   Interface       y ~ 290
#   Hotkeys         y ~ 340

print("\n--- Mapping Audio tab ---")
clk(c, 260, 190, 1.2)
ss(c, "13_options_audio.png")
chk(c, "audio_tab")

print("\n--- Mapping Gameplay tab ---")
clk(c, 260, 240, 1.2)
ss(c, "14_options_gameplay.png")
chk(c, "gameplay_tab")

print("\n--- Mapping Interface tab ---")
clk(c, 260, 290, 1.2)
ss(c, "15_options_interface.png")
chk(c, "interface_tab")

print("\n--- Mapping Hotkeys tab ---")
clk(c, 260, 340, 1.2)
ss(c, "16_options_hotkeys.png")
chk(c, "hotkeys_tab")

print("\n--- Checking for additional tabs (y=390, y=440) ---")
clk(c, 260, 390, 1.0)
ss(c, "17_options_tab5.png")
clk(c, 260, 440, 1.0)
ss(c, "18_options_tab6.png")

# ============================================================
# STEP: Close options and return to main menu
# ============================================================
print("\n--- Returning to main menu ---")
esc(c, 1.5)
ss(c, "19_back_to_main_menu.png")
chk(c, "after_options")

# ============================================================
# TASK 3: Map remaining top-level menus
# ============================================================

print("\n--- Campaign / Story Mode (130, 380) ---")
clk(c, 130, 380, 2.0)
ss(c, "20_campaign.png")
chk(c, "campaign")
esc(c, 1.5)
ss(c, "20a_after_campaign_esc.png")

print("\n--- Historical Battles (130, 435) ---")
clk(c, 130, 435, 2.0)
ss(c, "21_historical.png")
chk(c, "historical")
esc(c, 1.5)
ss(c, "21a_after_historical_esc.png")

print("\n--- Multiplayer top screen (130, 545) ---")
clk(c, 130, 545, 2.5)
ss(c, "22_multiplayer.png")
chk(c, "multiplayer")
esc(c, 1.5)
ss(c, "22a_after_multiplayer_esc.png")

print("\n--- Home City screen (130, 600) ---")
clk(c, 130, 600, 2.0)
ss(c, "23_homecity.png")
chk(c, "homecity")
esc(c, 1.5)
ss(c, "23a_after_homecity_esc.png")

print("\n--- Load Game screen (130, 325) ---")
clk(c, 130, 325, 2.0)
ss(c, "24_load.png")
chk(c, "load_game")
esc(c, 1.5)
ss(c, "24a_after_load_esc.png")

# Final state check
chk(c, "final")
ss(c, "25_final_main_menu.png")

print("\nAll screenshots taken. Now need to go back to Graphics and apply LOW preset.")
