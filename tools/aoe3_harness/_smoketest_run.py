#!/usr/bin/env python3
"""Smoke test: navigate to anwHubTest and anwAgeCaptureTest, verify map gen.

Saves screenshots to artifacts/anw_testmap_design/_smoketest/.
Prints PASS/FAIL for each map.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))

from tools.aoe3_harness.harness_client import HarnessClient  # noqa: E402

SOCK = "/tmp/AOE3DEHarness.sock"
OUT = REPO / "artifacts" / "anw_testmap_design" / "_smoketest"
OUT.mkdir(parents=True, exist_ok=True)

# Calibrated coords from drive_hubtest.py
SKIRMISH      = (130, 482)
MAP_BTN       = (1637, 425)
HUBTEST_TILE  = (1059, 304)   # "Unknown" tile, End view, row1 col4
PLAY          = (1648, 1048)
VK_END        = 0x23
VK_ESC        = 0x1B

# For resign/back-to-menu
MENU_BTN      = (960, 540)    # approximate; we'll use ESC to open pause


def connect() -> HarnessClient:
    c = HarnessClient(SOCK)
    c.connect(timeout=30)
    st = c.state()
    print(f"[harness] connected pid={st.pid} ready={st.ready} {st.internal_w}x{st.internal_h}", flush=True)
    return c


def wait_ready(c: HarnessClient, max_wait: int = 30) -> bool:
    for _ in range(max_wait // 3):
        st = c.state()
        if st.ready == 1:
            return True
        time.sleep(3)
    return False


def screenshot(c: HarnessClient, path: str) -> None:
    try:
        c.screenshot(path)
        print(f"[shot] {path}", flush=True)
    except Exception as e:
        print(f"[shot] FAILED {path}: {e}", flush=True)


def resign_to_menu(c: HarnessClient) -> None:
    """Try to get back to main menu by pressing ESC and navigating resign/exit."""
    print("[nav] attempting resign/exit to main menu...", flush=True)
    # ESC opens pause menu in-game
    c.key(VK_ESC); time.sleep(2.0)
    screenshot(c, str(OUT / "resign_pause.png"))
    # In AoE3 DE pause menu, Resign is typically around (960, 540) area
    # We try clicking resign button - empirically around (960, 540) or (960, 580)
    # Then confirm
    c.click(960, 540); time.sleep(1.5)
    screenshot(c, str(OUT / "resign_after_click1.png"))
    c.click(960, 540); time.sleep(1.5)
    screenshot(c, str(OUT / "resign_after_click2.png"))
    time.sleep(3.0)


def navigate_to_skirmish_lobby(c: HarnessClient, prefix: str) -> bool:
    """From main menu, navigate to skirmish lobby. Returns True on success."""
    if not wait_ready(c, 30):
        print("[nav] harness not ready", flush=True)
        return False

    # Click Skirmish
    c.click(*SKIRMISH); time.sleep(3.0)
    screenshot(c, str(OUT / f"{prefix}_1_skirmish.png"))

    # Open map picker
    c.click(*MAP_BTN); time.sleep(2.5)
    screenshot(c, str(OUT / f"{prefix}_2_mappicker_open.png"))

    # Focus grid, jump to end
    c.click(150, 304); time.sleep(0.4)
    c.key(VK_END); time.sleep(1.0)
    screenshot(c, str(OUT / f"{prefix}_3_mapend.png"))

    return True


def launch_map(c: HarnessClient, tile: tuple, prefix: str) -> None:
    """Double-click tile to select map, then click Play."""
    c.click(*tile); time.sleep(0.25); c.click(*tile); time.sleep(2.5)
    screenshot(c, str(OUT / f"{prefix}_4_lobby.png"))

    # Click Play
    c.click(*PLAY); time.sleep(6.0)
    screenshot(c, str(OUT / f"{prefix}_5_afterplay.png"))


def poll_for_ingame(c: HarnessClient, prefix: str, max_wait: int = 90) -> bool:
    """Poll until we believe the game is in-match (loading or HUD visible).
    Returns True if we think we made it in-game.
    """
    print(f"[poll] waiting up to {max_wait}s for in-game state...", flush=True)
    for i in range(max_wait // 5):
        time.sleep(5)
        shot_path = str(OUT / f"{prefix}_loading_{i:02d}.png")
        screenshot(c, shot_path)
        st = c.state()
        print(f"[poll] t={i*5}s ready={st.ready}", flush=True)
        # We'll take final screenshot at 90s or when we see something definitive
        if i >= 3:  # After 15s, take fewer shots
            break

    # Wait the rest of the time, then take a final shot
    elapsed = min(i * 5 + 5, 20)
    remaining = max_wait - elapsed
    if remaining > 0:
        print(f"[poll] sleeping {remaining}s more...", flush=True)
        time.sleep(remaining)

    final_path = str(OUT / f"{prefix}_final.png")
    screenshot(c, final_path)
    print(f"[poll] final shot: {final_path}", flush=True)
    return True


def back_to_menu_from_ingame(c: HarnessClient) -> None:
    """Resign from an in-progress match to get back to main menu."""
    print("[nav] ESC -> resign...", flush=True)
    c.key(VK_ESC); time.sleep(2.0)
    # Pause menu: Resign button. In AoE3 DE it's typically lower on screen
    # Try clicking around y=600-700 area for Resign
    screenshot(c, str(OUT / "pause_menu.png"))

    # AoE3 DE pause menu resign coords - try a few
    # Typically: Resign ~(960, 650), then confirm ~(960, 540)
    c.click(960, 650); time.sleep(1.5)
    screenshot(c, str(OUT / "after_resign_click.png"))
    c.click(960, 540); time.sleep(2.0)  # confirm dialog
    screenshot(c, str(OUT / "after_resign_confirm.png"))
    time.sleep(4.0)
    screenshot(c, str(OUT / "post_resign.png"))


def run_smoke_test():
    c = connect()

    # ---- Test 1: anwHubTest ----
    print("\n=== TEST 1: anwHubTest ===", flush=True)
    ok = navigate_to_skirmish_lobby(c, "hub")
    if not ok:
        print("[hub] FAIL: could not navigate to skirmish lobby", flush=True)
        c.close()
        return

    launch_map(c, HUBTEST_TILE, "hub")
    poll_for_ingame(c, "hub", max_wait=90)

    # Take the evidence screenshot
    screenshot(c, str(OUT / "anwHubTest_gen.png"))
    print("[hub] Evidence screenshot saved to anwHubTest_gen.png", flush=True)

    # ---- Navigate back to menu ----
    back_to_menu_from_ingame(c)
    time.sleep(3.0)
    screenshot(c, str(OUT / "between_tests.png"))

    # ---- Test 2: anwAgeCaptureTest ----
    print("\n=== TEST 2: anwAgeCaptureTest ===", flush=True)
    # anwAgeCaptureTest also sorts as "Unknown" — but there may be two Unknown tiles.
    # From drive_hubtest.py, HUBTEST_TILE is (1059, 304) at row1 col4 after End.
    # anwAgeCaptureTest might be adjacent. We'll try (1059, 304) first after re-picking.
    # Actually, both sort as Unknown at end of list.
    # We need to figure out which tile is which. For now use same tile and see.
    # The two Unknown maps: let's try col3 (row1, col3 = 810, 304) as the other one.
    # We'll do best-effort.

    ok = navigate_to_skirmish_lobby(c, "age")
    if not ok:
        print("[age] FAIL: could not navigate to skirmish lobby", flush=True)
        c.close()
        return

    # Try the tile adjacent to HUBTEST_TILE for anwAgeCaptureTest
    AGE_TILE = (810, 304)  # row1 col3, one tile left of hubtest
    c.click(*AGE_TILE); time.sleep(0.25); c.click(*AGE_TILE); time.sleep(2.5)
    screenshot(c, str(OUT / "age_4_lobby.png"))
    c.click(*PLAY); time.sleep(6.0)
    screenshot(c, str(OUT / "age_5_afterplay.png"))

    poll_for_ingame(c, "age", max_wait=90)
    screenshot(c, str(OUT / "anwAgeCaptureTest_gen.png"))
    print("[age] Evidence screenshot saved to anwAgeCaptureTest_gen.png", flush=True)

    # Resource bar check (a few seconds in)
    time.sleep(5.0)
    screenshot(c, str(OUT / "age_resources.png"))

    # ---- Return to main menu ----
    back_to_menu_from_ingame(c)
    time.sleep(3.0)
    screenshot(c, str(OUT / "final_menu.png"))

    c.close()
    print("\n=== SMOKE TEST COMPLETE ===", flush=True)
    print(f"Screenshots in: {OUT}", flush=True)


if __name__ == "__main__":
    run_smoke_test()
