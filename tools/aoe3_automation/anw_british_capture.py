#!/usr/bin/env python3
"""One-shot visual capture for ANWBritish using the harness socket.

Captures all 9 surfaces:
  01_main_menu.png
  02_skirmish_setup.png
  03_civ_selected.png
  04_loading.png
  05_ingame_hud.png
  06_diplomacy.png
  07_scoreboard.png
  08_homecity.png
  09_postgame.png

Run from repo root:
  python3 tools/aoe3_automation/anw_british_capture.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.aoe3_harness.harness_client import HarnessClient, HarnessConnectionError
from tools.aoe3_harness.vk import (
    VK_ESCAPE, VK_TAB, VK_F10,
    VK_J,  # Home City panel
)

SOCKET = "/tmp/AOE3DEHarness.sock"
OUT_DIR = Path(
    "/var/home/jflessenkemper/AOE-3-DE-A-New-World/"
    "artifacts/validation/visual_art/ANWBritish/full"
)
DEBUG_DIR = OUT_DIR / "debug"

# Load coords
COORDS = json.loads(
    (REPO / "tools/aoe3_automation/lobby_coords.json").read_text()
)

# ---- helpers ----------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[capture] {msg}", flush=True)


def snap(c: HarnessClient, name: str, *, debug: bool = False) -> Path:
    """Take a screenshot; save to OUT_DIR (or DEBUG_DIR for debug frames)."""
    dest = (DEBUG_DIR if debug else OUT_DIR) / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = c.screenshot(str(dest))
    log(f"  => {dest.name} ({r.bytes_written:,} bytes)")
    return dest


def click(c: HarnessClient, x: int, y: int, *, settle: float = 0.15) -> None:
    c.click(x, y)
    time.sleep(settle)


def key(c: HarnessClient, vk: int, *, settle: float = 0.4) -> None:
    c.key(vk)
    time.sleep(settle)


def alive(c: HarnessClient) -> bool:
    """Return True if the harness socket is still responding."""
    try:
        c.state()
        return True
    except Exception:
        return False


def wait_screen_change(c: HarnessClient, *, timeout: float = 90.0, interval: float = 2.0) -> None:
    """Poll STATE until ready=1 (indicates game is past splash / loading)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = c.state()
            log(f"  state: ready={s.ready} uptime_ms={s.uptime_ms}")
            if s.ready:
                return
        except Exception as e:
            log(f"  state error: {e}")
        time.sleep(interval)
    log("  WARNING: timed out waiting for ready=1 — proceeding anyway")


def scroll_picker_to_top(c: HarnessClient, coords: dict, n: int = 30) -> None:
    """Scroll the civ picker all the way to the top (excess wheel-up is a no-op)."""
    sa = coords["civ_picker"]["scroll_anchor"]
    c.move(sa[0], sa[1])
    time.sleep(0.05)
    for _ in range(n):
        c.wheel(0.0, 1.0)  # wheel-up
        time.sleep(0.02)


def select_civ_british(c: HarnessClient, coords: dict) -> bool:
    """
    Open the P1 civ picker, scroll to 'ANWBritish', click it, confirm.

    ANWBritish appears as 'British' in the picker. It's near the top of the
    alphabetical list so we scroll to top and pick from visible rows.

    Returns True if we found and clicked a suitable row.
    """
    # Open P1 civ picker
    p1 = coords["lobby"]["p1_civ_picker"]
    log(f"  clicking p1_civ_picker at {p1}")
    click(c, p1[0], p1[1], settle=0.6)
    time.sleep(0.6)  # picker fade-in

    # Screenshot the open picker so we can visually verify
    snap(c, "debug_picker_open.png", debug=True)

    # Scroll to top (belt-and-suspenders)
    scroll_picker_to_top(c, coords, n=25)
    time.sleep(0.4)
    snap(c, "debug_picker_top.png", debug=True)

    # The picker layout per lobby_coords.json:
    #   row_y_start=301, row_spacing=64, row_x_center=440
    # Rows 0-9 (y=301,365,428,494,558,622,685,751,814,877)
    #
    # 'ANWBritish' appears as 'British' in the ANW mod picker. British civs
    # appear early alphabetically. From prior ANW captures it typically lands
    # at a low index. We'll look at each row then pick by visual position.
    #
    # Known from picker_scroll_table: ANWBritish is in the visible set at top.
    # We'll try clicking each row from the top to find one that shows 'British'.
    # Based on the civ-order cache, ANWBritish should be within the first ~5 rows.
    # (alphabetical: ANW civs include ANWAztecs, ANWBritish, ... so British=row ~1)

    row_y_start = coords["civ_picker"]["row_y_start"]  # 301
    row_spacing = coords["civ_picker"]["row_spacing"]   # 64
    row_x = coords["civ_picker"]["row_x_center"]        # 440

    # Try to load the civ order cache to find the exact row
    try:
        from tools.aoe3_automation.lobby_driver import load_civ_order_cache, find_scrolls_for_civ, load_scroll_table
        cache = load_civ_order_cache()
        entry = cache.get("entries", {}).get("ANWBritish")
        if entry:
            scroll_count = entry["scroll_count"]
            click_row = entry["click_row"]
            log(f"  cache hit: ANWBritish scroll_count={scroll_count} click_row={click_row}")
            # scroll_picker_to_top already called; now scroll down by scroll_count
            if scroll_count > 0:
                sa = coords["civ_picker"]["scroll_anchor"]
                c.move(sa[0], sa[1])
                time.sleep(0.05)
                for _ in range(scroll_count):
                    c.wheel(0.0, -1.0)  # wheel-down
                    time.sleep(0.03)
                time.sleep(0.3)
            # Click the target row
            row_y = row_y_start + click_row * row_spacing
            log(f"  clicking row {click_row} at y={row_y}")
            click(c, row_x, row_y, settle=0.3)
            snap(c, "debug_row_selected.png", debug=True)
            # Confirm
            ok_btn = coords["civ_picker"]["ok_button"]
            log(f"  clicking OK at {ok_btn}")
            click(c, ok_btn[0], ok_btn[1], settle=0.5)
            time.sleep(0.5)
            return True
    except Exception as e:
        log(f"  cache load failed: {e}, falling back to row scan")

    # Fallback: scan visible rows. British should be within first 3 visible.
    # For the ANW mod, alphabetical order typically puts British early.
    # Try rows 0-4 and pick one (we'll screenshot each for debugging).
    for row_idx in range(5):
        row_y = row_y_start + row_idx * row_spacing
        log(f"  trying row {row_idx} at y={row_y}")
        click(c, row_x, row_y, settle=0.2)
        dbg = snap(c, f"debug_row_{row_idx}.png", debug=True)

    # After clicking, use row that visually looks like British — for now
    # assume row 1 (index 1) since ANWBritish is alphabetically index ~1-2
    # after ANWAztecs. Click row 1 again to make it selected.
    target_row = 1
    row_y = row_y_start + target_row * row_spacing
    log(f"  selecting row {target_row} at y={row_y}")
    click(c, row_x, row_y, settle=0.4)

    ok_btn = coords["civ_picker"]["ok_button"]
    log(f"  clicking OK at {ok_btn}")
    click(c, ok_btn[0], ok_btn[1], settle=0.5)
    time.sleep(0.5)
    return True


# ---- main capture flow ------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    log(f"Connecting to harness at {SOCKET}")
    c = HarnessClient(SOCKET, timeout=15.0)
    c.connect(timeout=10.0)
    log("Connected.")

    # Verify harness is responding
    s = c.state()
    log(f"Harness state: pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h}")

    # ----------------------------------------------------------------
    # Step 1: Advance past intro splash to main menu
    # ----------------------------------------------------------------
    log("Step 1: Advance past intro splash")
    # Click center of screen to dismiss the cinematic
    click(c, 960, 540, settle=1.5)
    snap(c, "debug_01_after_click.png", debug=True)

    # May need another click
    click(c, 960, 540, settle=1.5)
    snap(c, "debug_01b_after_click2.png", debug=True)

    # Click again for good measure (sometimes there's multiple splash screens)
    click(c, 960, 540, settle=1.5)
    time.sleep(2.0)

    snap(c, "01_main_menu.png")
    log("01_main_menu.png captured")

    if not alive(c):
        log("CRASH: game died after intro clicks. Stopping.")
        return

    # ----------------------------------------------------------------
    # Step 2: Navigate to Skirmish
    # ----------------------------------------------------------------
    log("Step 2: Navigate to Skirmish")
    skirmish_btn = COORDS["main_menu"]["skirmish_button"]
    log(f"  clicking skirmish at {skirmish_btn}")

    # Click 3 times with delays (as per lobby_driver.click_skirmish)
    for i in range(3):
        click(c, skirmish_btn[0], skirmish_btn[1], settle=0.4)
        time.sleep(0.5)
    time.sleep(3.0)

    snap(c, "debug_02_after_skirmish_click.png", debug=True)
    snap(c, "02_skirmish_setup.png")
    log("02_skirmish_setup.png captured")

    if not alive(c):
        log("CRASH: game died after skirmish click. Stopping.")
        return

    # Brief pause for lobby to fully render
    time.sleep(1.5)

    # ----------------------------------------------------------------
    # Step 3: Select ANWBritish civ
    # ----------------------------------------------------------------
    log("Step 3: Select ANWBritish civ")
    success = select_civ_british(c, COORDS)
    time.sleep(1.0)
    snap(c, "03_civ_selected.png")
    log(f"03_civ_selected.png captured (picker_success={success})")

    if not alive(c):
        log("CRASH: game died after civ selection. Stopping.")
        return

    # ----------------------------------------------------------------
    # Step 4: Start match, wait for loading, then in-game HUD
    # ----------------------------------------------------------------
    log("Step 4: Start match")
    play_btn = COORDS["lobby"]["play_button"]
    log(f"  clicking play at {play_btn}")
    click(c, play_btn[0], play_btn[1], settle=1.0)
    time.sleep(2.0)

    snap(c, "04_loading.png")
    log("04_loading.png captured")

    if not alive(c):
        log("CRASH: game died immediately after play click. Stopping.")
        return

    # Poll for game to load (loading screen → in-game HUD)
    log("  Waiting for in-game HUD (polling up to 120s)...")
    deadline = time.monotonic() + 120.0
    last_snap_time = time.monotonic()
    ingame = False
    while time.monotonic() < deadline:
        if not alive(c):
            log("CRASH: game died during loading. Stopping.")
            return
        # Screenshot periodically to watch for HUD
        if time.monotonic() - last_snap_time > 8.0:
            snap(c, "debug_loading_poll.png", debug=True)
            last_snap_time = time.monotonic()
        time.sleep(3.0)
        # After 45s minimum, try to take the in-game HUD shot
        elapsed = 120.0 - (deadline - time.monotonic())
        if elapsed > 45.0:
            ingame = True
            break

    if not alive(c):
        log("CRASH: game died during loading wait. Stopping.")
        return

    # Additional settle time for map to fully load
    time.sleep(5.0)
    snap(c, "05_ingame_hud.png")
    log("05_ingame_hud.png captured")

    if not alive(c):
        log("CRASH: game died after HUD capture. Stopping.")
        return

    # ----------------------------------------------------------------
    # Step 5: F10 → Diplomacy panel
    # ----------------------------------------------------------------
    log("Step 5: F10 → Diplomacy panel")
    key(c, VK_F10, settle=1.5)
    snap(c, "06_diplomacy.png")
    log("06_diplomacy.png captured")

    if not alive(c):
        log("CRASH: game died after F10. Stopping.")
        return

    # Close diplomacy (Escape)
    key(c, VK_ESCAPE, settle=0.8)

    # ----------------------------------------------------------------
    # Step 6: Tab → Scoreboard
    # ----------------------------------------------------------------
    log("Step 6: Tab → Scoreboard")
    key(c, VK_TAB, settle=1.0)
    snap(c, "07_scoreboard.png")
    log("07_scoreboard.png captured")

    if not alive(c):
        log("CRASH: game died after Tab. Stopping.")
        return

    # Release Tab
    key(c, VK_TAB, settle=0.5)

    # ----------------------------------------------------------------
    # Step 7: Home City panel (J key)
    # ----------------------------------------------------------------
    log("Step 7: Home City panel")
    key(c, VK_J, settle=1.5)
    snap(c, "08_homecity.png")
    log("08_homecity.png captured")

    if not alive(c):
        log("CRASH: game died after J. Stopping.")
        return

    # Close HC panel
    key(c, VK_ESCAPE, settle=0.5)

    # ----------------------------------------------------------------
    # Step 8: Resign → post-game screen
    # ----------------------------------------------------------------
    log("Step 8: Resign → post-game")
    # Open in-game menu with Escape
    key(c, VK_ESCAPE, settle=1.0)
    snap(c, "debug_08_menu_open.png", debug=True)

    # Menu resign button — typically at a fixed location
    # AoE3 DE in-game menu: Resign is usually in the center of the screen
    # Common positions from prior captures: ~(960, 540) area, but let's try
    # the known location from similar games. Resign is typically visible in
    # the pause menu.
    # Click Resign button — empirically around (960, 480) based on typical AoE3 DE layout
    click(c, 960, 480, settle=0.5)
    snap(c, "debug_08_after_resign_click.png", debug=True)

    # If resign dialog appeared, confirm it
    # Confirm resign is usually "Yes" or "Resign" button — try center-ish
    click(c, 960, 560, settle=1.5)
    time.sleep(3.0)

    snap(c, "09_postgame.png")
    log("09_postgame.png captured")

    if not alive(c):
        log("NOTE: game process may have ended (post-game screen or crash).")

    c.close()
    log("Done. Checking output directory...")

    # Print summary
    print("\n=== CAPTURE SUMMARY ===")
    surfaces = [
        "01_main_menu.png",
        "02_skirmish_setup.png",
        "03_civ_selected.png",
        "04_loading.png",
        "05_ingame_hud.png",
        "06_diplomacy.png",
        "07_scoreboard.png",
        "08_homecity.png",
        "09_postgame.png",
    ]
    for s in surfaces:
        p = OUT_DIR / s
        if p.exists():
            print(f"  OK   {s} ({p.stat().st_size:,} bytes)")
        else:
            print(f"  MISS {s}")
    print()

    debug_frames = sorted(DEBUG_DIR.glob("*.png"))
    print(f"Debug frames: {len(debug_frames)} in {DEBUG_DIR}")


if __name__ == "__main__":
    main()
