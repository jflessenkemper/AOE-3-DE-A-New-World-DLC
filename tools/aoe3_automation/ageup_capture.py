#!/usr/bin/env python3
"""Age-up dialog capture for ANWBritish — new strategy (no H-hotkey, no AGE_UP_BTN guess).

Strategy:
  1. Launch game via manage_game.py open if needed.
  2. Start a 1v1 skirmish as British Empire (picker Down×3) vs 1 Easy AI.
  3. Wait for in-game HUD.
  4. Set speed to max.
  5. Capture scoreboard (03_scoreboard.png) by taking a clean HUD screenshot.
  6. Grant resources via chat cheats.
  7. Click near screen center (960, 500) to select Town Center.
  8. Verify TC selected by probing command panel area.
  9. Click age-up button (hunt for it in command panel).
  10. Capture each age-up dialog and save.

Usage:
    cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
    python3 tools/aoe3_automation/ageup_capture.py
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.aoe3_harness.harness_client import HarnessClient, HarnessConnectionError
from tools.aoe3_automation.in_game_driver import (
    GameDriver, _click, _key, _screenshot_raw, set_harness_backend,
    SKIRMISH_BTN, P1_CIV_FLAG, P2_CIV_FLAG, PICKER_OK, PLAY_BTN,
    GEARS_BTN, ESC_RESIGN, RESIGN_YES,
)

SOCKET = "/tmp/AOE3DEHarness.sock"

# Resource cheats — try in order; verify by watching resource bar
RESOURCE_CHEATS = [
    "give me liberty or give me coin",   # +10000 gold (documented)
    "medium rare please",                # +10000 food (AoE3 classic cheat)
    "speed always wins",                 # faster building (useful but not resources)
    "nova & orion",                      # +10000 all resources (AoE3 DE confirmed)
    "a recent study indicated that 100% of herdables are obese",  # alt food cheat
]

def log(msg: str) -> None:
    print(f"[ageup] {msg}", flush=True)


def snap(c: HarnessClient, name: str, out_dir: Path) -> Path:
    dest = out_dir / name
    r = c.screenshot(str(dest))
    log(f"  => {dest.name} ({r.bytes_written:,} bytes)")
    return dest


def hclick(c: HarnessClient, x: int, y: int, settle: float = 0.3) -> None:
    c.move(x, y)
    time.sleep(0.05)
    c.click(x, y)
    time.sleep(settle)


def hkey_str(c: HarnessClient, text: str, settle: float = 0.05) -> None:
    """Type a string using xdotool (harness doesn't have string type)."""
    import subprocess
    import os
    env = {**os.environ, "DISPLAY": ":1"}
    for ch in text:
        if ch == ' ':
            subprocess.run(["xdotool", "key", "space"], env=env, capture_output=True)
        elif ch.isalpha() and ch.islower():
            subprocess.run(["xdotool", "key", ch], env=env, capture_output=True)
        elif ch.isalpha() and ch.isupper():
            subprocess.run(["xdotool", "key", f"shift+{ch.lower()}"], env=env, capture_output=True)
        elif ch.isdigit():
            subprocess.run(["xdotool", "key", ch], env=env, capture_output=True)
        elif ch == "'":
            subprocess.run(["xdotool", "key", "apostrophe"], env=env, capture_output=True)
        elif ch == "%":
            subprocess.run(["xdotool", "key", "percent"], env=env, capture_output=True)
        elif ch == "&":
            subprocess.run(["xdotool", "key", "ampersand"], env=env, capture_output=True)
        elif ch == ",":
            subprocess.run(["xdotool", "key", "comma"], env=env, capture_output=True)
        elif ch in (".", "!"):
            subprocess.run(["xdotool", "key", "period"], env=env, capture_output=True)
        time.sleep(settle)


def send_chat_cheat(c: HarnessClient, cheat: str) -> None:
    """Open chat with Enter, type cheat, send with Enter."""
    import subprocess
    import os
    env = {**os.environ, "DISPLAY": ":1"}
    # Open chat
    subprocess.run(["xdotool", "key", "Return"], env=env, capture_output=True)
    time.sleep(0.5)
    # Type cheat
    hkey_str(c, cheat, settle=0.04)
    time.sleep(0.2)
    # Send
    subprocess.run(["xdotool", "key", "Return"], env=env, capture_output=True)
    time.sleep(1.0)


def select_civ(c: HarnessClient, flag_xy: tuple, civ_idx: int) -> None:
    """Click civ flag, scroll to top, select civ by index, confirm."""
    hclick(c, *flag_xy, settle=2.0)
    # Scroll to top
    import subprocess, os
    env = {**os.environ, "DISPLAY": ":1"}
    for _ in range(60):
        subprocess.run(["xdotool", "key", "Up"], env=env, capture_output=True)
        time.sleep(0.03)
    time.sleep(0.3)
    for _ in range(civ_idx):
        subprocess.run(["xdotool", "key", "Down"], env=env, capture_output=True)
        time.sleep(0.04)
    time.sleep(0.3)
    hclick(c, *PICKER_OK, settle=2.5)


def pixel_brightness(img_path: Path, x: int, y: int) -> int:
    """Return R+G+B at (x,y). 0 on error."""
    try:
        from PIL import Image
        with Image.open(img_path) as im:
            px = im.getpixel((x, y))
            return sum(px[:3])
    except Exception:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Age-up dialog capture — parameterized by civ token.")
    ap.add_argument("--civ", default="ANWBritish",
                    help="ANW civ token (e.g. ANWFrench).  Default: ANWBritish")
    ap.add_argument("--out-root", default="artifacts/validation/visual_art",
                    help="Output root directory (relative to repo root or absolute).  "
                         "Output goes to <out-root>/<civ>/full/")
    args = ap.parse_args()

    civ_token = args.civ
    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = REPO / out_root
    out_dir = out_root / civ_token / "full"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve picker index from lobby_driver's civ order so any of the 44
    # ANW civs can be selected without hardcoding per-civ indices.
    from tools.aoe3_automation import lobby_driver as ld
    civ_order = ld.get_civ_order()   # list of civ tokens in picker scroll order
    try:
        civ_idx = civ_order.index(civ_token)
    except ValueError:
        log(f"ERROR: {civ_token!r} not found in picker order; cannot auto-select")
        log(f"  Available tokens: {civ_order}")
        return 1

    log(f"=== {civ_token} age-up capture (picker index {civ_idx}) ===")

    # Connect to harness
    log(f"Connecting to harness socket {SOCKET} ...")
    try:
        c = HarnessClient(SOCKET)
        c.connect()
        log("  Connected.")
    except HarnessConnectionError as e:
        log(f"  Harness not running: {e}")
        log("  Launching game via manage_game.py ...")
        import subprocess
        r = subprocess.run(
            [sys.executable, str(REPO / "tools/aoe3_automation/manage_game.py"),
             "open", "--timeout", "120"],
            capture_output=False
        )
        if r.returncode != 0:
            log("  ERROR: game launch failed")
            return 1
        time.sleep(5)
        c = HarnessClient(SOCKET)
        c.connect()
        log("  Connected after launch.")

    # Register as harness backend
    set_harness_backend(c)
    ld.set_harness_backend(c)

    d = GameDriver(art_dir="/tmp/ageup_capture")

    # ---- Step 1: Navigate to skirmish setup ----
    log("Step 1: Navigate to skirmish setup ...")
    hclick(c, *SKIRMISH_BTN, settle=3.0)
    snap(c, "dbg_skirmish_setup.png", out_dir)

    # ---- Step 2: Select civ (P1) ----
    log(f"Step 2: Select {civ_token} (Down×{civ_idx}) for P1 ...")
    select_civ(c, P1_CIV_FLAG, civ_idx)
    snap(c, "dbg_civ_selected.png", out_dir)

    # ---- Step 3: Set P2 to Easy AI (leave default, just verify) ----
    # P2 already defaults to AI. We start with 2 players (1v1 easy).
    # Optionally set difficulty to Easy by clicking at difficulty dropdown
    # Try clicking the difficulty area to set to Easy
    # The dropdown is at x=1700, y=570 — we'll leave it as-is (hard AI is fine for age-up test)

    # ---- Step 4: Click Play ----
    log("Step 4: Clicking Play ...")
    hclick(c, *PLAY_BTN, settle=3.0)
    snap(c, "dbg_loading.png", out_dir)

    # ---- Step 5: Wait for in-game ----
    log("Step 5: Waiting for in-game HUD (up to 240s) ...")
    if not d.wait_for_in_game(timeout=240):
        log("  ERROR: never reached in-game state")
        snap(c, "dbg_waitfail.png", out_dir)
        return 1
    time.sleep(5)  # extra settle
    log("  In-game!")
    snap(c, "dbg_ingame_hud.png", out_dir)

    # ---- Step 6: Set game speed to max ----
    log("Step 6: Setting speed to max ...")
    d.set_speed(5)
    time.sleep(1)

    # ---- Step 7: Capture clean scoreboard (03_scoreboard.png) ----
    log("Step 7: Capturing clean scoreboard ...")
    # Game map should be fully visible; just take a screenshot now
    scoreboard_path = snap(c, "03_scoreboard.png", out_dir)
    log(f"  Scoreboard saved: {scoreboard_path}")
    # Verify it's not black
    brightness = pixel_brightness(scoreboard_path, 960, 540)
    log(f"  Center pixel brightness: {brightness} (>200 = game visible)")

    # ---- Step 8: Grant resources via chat cheats ----
    log("Step 8: Granting resources via chat cheats ...")
    cheats_to_send = [
        "nova & orion",                  # +10000 all resources
        "give me liberty or give me coin",  # +10000 gold
        "medium rare please",            # +10000 food
    ]
    for cheat in cheats_to_send:
        log(f"  Sending cheat: {cheat!r}")
        send_chat_cheat(c, cheat)
    time.sleep(1)
    snap(c, "dbg_after_cheats.png", out_dir)

    # ---- Step 9: Select Town Center (click near screen center) ----
    log("Step 9: Selecting Town Center by clicking near screen center ...")
    # First press spacebar / Home to recenter camera on TC
    import subprocess, os
    env_x = {**os.environ, "DISPLAY": ":1"}
    # Try Home key to center on TC
    subprocess.run(["xdotool", "key", "Home"], env=env_x, capture_output=True)
    time.sleep(1.5)
    snap(c, "dbg_after_home.png", out_dir)

    # Click center of screen where TC should be
    hclick(c, 960, 500, settle=0.5)
    snap(c, "dbg_tc_click1.png", out_dir)

    # Check if TC is selected — look at bottom command panel
    # TC's command panel shows at y≈900-1080, we look for non-black pixels there
    tc_brightness = pixel_brightness(out_dir / "dbg_tc_click1.png", 960, 950)
    log(f"  Command panel brightness at (960,950): {tc_brightness}")

    # Also try pressing spacebar (center camera on TC / last event)
    if tc_brightness < 50:
        log("  TC may not be selected, trying spacebar + recenter ...")
        subprocess.run(["xdotool", "key", "space"], env=env_x, capture_output=True)
        time.sleep(1.0)
        hclick(c, 960, 500, settle=0.5)
        snap(c, "dbg_tc_click2.png", out_dir)
        tc_brightness = pixel_brightness(out_dir / "dbg_tc_click2.png", 960, 950)
        log(f"  After spacebar, command panel brightness: {tc_brightness}")

    # ---- Step 10: Find and probe the Age-Up button ----
    # The age-up button is typically in the bottom command panel
    # In AoE3 the TC commands show a grid of buttons; age-up is usually
    # the last button or has a distinctive icon.
    # Command panel typical range: x=500-1400, y=900-1080
    # Let's try several candidate positions for the age-up button
    # Based on AoE3 UI: command buttons are at y≈960-1000, spread across x
    # Age-up is typically bottom-right of command card

    # Before clicking age-up, verify we're still in-game
    snap(c, "dbg_before_ageup.png", out_dir)

    # Try clicking several candidate age-up button positions
    # Standard AoE3 command card grid: 5 columns x 3 rows
    # Row 3 (y≈998), columns spaced ~70px apart, centered around 960
    # Age-up button is usually position (4,3) or (5,3) = rightmost bottom
    ageup_candidates = [
        (1356, 1029),  # original documented (unvalidated) guess
        (1290, 998),   # col 5, row 3
        (1220, 998),   # col 4, row 3
        (960, 960),    # center row 2
        (840, 1000),   # alternate
    ]

    # We'll do a visual scan: take a screenshot, view the command panel area
    # to find where the age-up button is
    log("  Taking scan screenshot to identify TC command card ...")
    scan_path = snap(c, "dbg_tc_command_card.png", out_dir)

    # Try to find the age-up button by probing the command panel for
    # a golden/bright pixel (age-up button often has a distinctive color)
    # For now, try clicking the most likely position based on AoE3 layout
    # The "Advance to Age II" button in AoE3 is at top of command card when TC selected
    # In AoE3 DE the TC command card layout:
    #   Row 1: Train Settler | [empty] | [empty] | [empty] | [empty]
    #   Row 2: [empty] | ...
    #   Row 3: [empty] | ... | ADVANCE TO AGE II
    # Actual y range for command buttons: ~930-1070
    # The age-up button ("Advance to Colonial Age") is typically at position 5 of row 3
    # or specially placed; in AoE3 DE it's usually a large button

    # Let's do this methodically - try age-up button positions and check for dialog
    age_up_button_xy = None

    for ax, ay in ageup_candidates:
        log(f"  Trying age-up click at ({ax},{ay}) ...")
        # Make sure TC is still selected
        hclick(c, 960, 500, settle=0.3)
        time.sleep(0.3)
        # Click candidate age-up position
        hclick(c, ax, ay, settle=1.5)
        cand_path = snap(c, f"dbg_ageup_try_{ax}_{ay}.png", out_dir)
        # Check if a dialog appeared: look for bright pixels in center-screen area
        # A dialog would show bright UI in the ~y=200-800 range
        dialog_brightness = pixel_brightness(cand_path, 960, 400)
        log(f"    Dialog area brightness at (960,400): {dialog_brightness}")
        if dialog_brightness > 400:
            log(f"  *** Possible dialog at ({ax},{ay})! brightness={dialog_brightness}")
            age_up_button_xy = (ax, ay)
            break
        # Dismiss any accidental dialog with Escape
        subprocess.run(["xdotool", "key", "Escape"], env=env_x, capture_output=True)
        time.sleep(0.5)

    if age_up_button_xy is None:
        log("  WARNING: Could not auto-detect age-up button. Using best guess (1356,1029).")
        log("  Will attempt capture anyway.")
        age_up_button_xy = (1356, 1029)

    # ---- Step 11: Capture Age II dialog ----
    log("\nStep 11: Capturing Age II dialog ...")
    # Re-select TC
    hclick(c, 960, 500, settle=0.4)
    time.sleep(0.5)
    # Grant more resources to be sure
    send_chat_cheat(c, "nova & orion")
    time.sleep(0.5)
    # Click age-up
    hclick(c, *age_up_button_xy, settle=2.0)
    age2_path = snap(c, "08_ageup_age2.png", out_dir)
    brightness2 = pixel_brightness(age2_path, 960, 400)
    log(f"  Age II dialog brightness at (960,400): {brightness2}")

    if brightness2 < 200:
        log("  WARNING: Age II shot may not show the dialog (low brightness). Checking ...")
        # Try pressing Escape to dismiss any unintended state and retry
        subprocess.run(["xdotool", "key", "Escape"], env=env_x, capture_output=True)
        time.sleep(0.5)
        # Try a different approach: single-click TC, then probe command card more carefully
        hclick(c, 960, 480, settle=0.5)  # slightly higher
        snap(c, "dbg_tc_higher_click.png", out_dir)
        hclick(c, *age_up_button_xy, settle=2.0)
        age2_path = snap(c, "08_ageup_age2.png", out_dir)
        brightness2 = pixel_brightness(age2_path, 960, 400)
        log(f"  Retry Age II brightness: {brightness2}")

    # ---- Choose a politician and wait for age-up to complete ----
    log("  Choosing first politician (click left option ~600,500) ...")
    # Politician buttons are typically left side of dialog, y~400-600
    hclick(c, 600, 500, settle=2.0)
    # Wait for age-up to complete (can take 30-60s at game speed; at max speed ~5-10s)
    log("  Waiting 15s for age-up to complete ...")
    time.sleep(15)
    snap(c, "dbg_after_age2.png", out_dir)

    # ---- Step 12: Capture Age III dialog ----
    log("\nStep 12: Capturing Age III dialog ...")
    send_chat_cheat(c, "nova & orion")
    time.sleep(0.5)
    hclick(c, 960, 500, settle=0.5)
    time.sleep(0.3)
    hclick(c, *age_up_button_xy, settle=2.0)
    age3_path = snap(c, "08_ageup_age3.png", out_dir)
    brightness3 = pixel_brightness(age3_path, 960, 400)
    log(f"  Age III dialog brightness at (960,400): {brightness3}")
    # Choose politician
    hclick(c, 600, 500, settle=2.0)
    log("  Waiting 15s for age-up ...")
    time.sleep(15)
    snap(c, "dbg_after_age3.png", out_dir)

    # ---- Step 13: Capture Age IV dialog ----
    log("\nStep 13: Capturing Age IV dialog ...")
    send_chat_cheat(c, "nova & orion")
    time.sleep(0.5)
    hclick(c, 960, 500, settle=0.5)
    time.sleep(0.3)
    hclick(c, *age_up_button_xy, settle=2.0)
    age4_path = snap(c, "08_ageup_age4.png", out_dir)
    brightness4 = pixel_brightness(age4_path, 960, 400)
    log(f"  Age IV dialog brightness at (960,400): {brightness4}")
    hclick(c, 600, 500, settle=2.0)
    log("  Waiting 15s for age-up ...")
    time.sleep(15)
    snap(c, "dbg_after_age4.png", out_dir)

    # ---- Step 14: Capture Age V dialog ----
    log("\nStep 14: Capturing Age V dialog ...")
    send_chat_cheat(c, "nova & orion")
    time.sleep(0.5)
    hclick(c, 960, 500, settle=0.5)
    time.sleep(0.3)
    hclick(c, *age_up_button_xy, settle=2.0)
    age5_path = snap(c, "08_ageup_age5.png", out_dir)
    brightness5 = pixel_brightness(age5_path, 960, 400)
    log(f"  Age V dialog brightness at (960,400): {brightness5}")
    hclick(c, 600, 500, settle=2.0)

    # ---- Summary ----
    log("\n=== Capture Summary ===")
    results = [
        ("scoreboard", "03_scoreboard.png", brightness),
        ("age2", "08_ageup_age2.png", brightness2),
        ("age3", "08_ageup_age3.png", brightness3),
        ("age4", "08_ageup_age4.png", brightness4),
        ("age5", "08_ageup_age5.png", brightness5),
    ]
    for name, fname, bri in results:
        status = "LIKELY_OK" if bri > 300 else "POSSIBLE_FAIL"
        log(f"  {name:15s}: {fname}  brightness={bri}  [{status}]")

    log(f"\nFiles in {out_dir}:")
    for fname in ["03_scoreboard.png", "08_ageup_age2.png", "08_ageup_age3.png",
                  "08_ageup_age4.png", "08_ageup_age5.png"]:
        fp = out_dir / fname
        exists = fp.exists()
        size = fp.stat().st_size if exists else 0
        log(f"  {'OK' if exists else 'MISSING':6s} {fname} ({size:,} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
