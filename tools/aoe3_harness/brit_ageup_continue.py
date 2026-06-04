#!/usr/bin/env python3
"""Continue British age-up captures from Age II dialog already showing.

Run from repo root:
  python3 tools/aoe3_harness/brit_ageup_continue.py

Assumes:
  - Harness socket is live at /tmp/AOE3DEHarness.sock
  - Game is currently showing the Age II "Select a Commerce Age Politician" dialog
  - age II snapshot was already taken (08_ageup_age2.png exists)
  - Next: Accept Age II → wait → capture Age III → IV → V → resign → rebuild site
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_harness_dir = str(Path(__file__).resolve().parent)
while _harness_dir in sys.path:
    sys.path.remove(_harness_dir)

from tools.aoe3_harness.harness_client import HarnessClient
from tools.aoe3_harness.vk import (
    VK_ESCAPE, VK_RETURN, VK_SPACE,
    VK_A, VK_B, VK_C, VK_D, VK_E, VK_F, VK_G, VK_H, VK_I, VK_J,
    VK_K, VK_L, VK_M, VK_N, VK_O, VK_P, VK_Q, VK_R, VK_S, VK_T,
    VK_U, VK_V, VK_W, VK_X, VK_Y, VK_Z,
    VK_0, VK_1, VK_2, VK_3, VK_4, VK_5, VK_6, VK_7, VK_8, VK_9,
)

SOCK = "/tmp/AOE3DEHarness.sock"
OUT = REPO / "artifacts" / "validation" / "visual_art" / "ANWBritish" / "full"
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/brit_capture")
TMP.mkdir(exist_ok=True)

# Verified coords
GEARS_BTN     = (1860, 30)
ESC_RESIGN    = (1830, 365)
RESIGN_YES    = (760, 605)
VIEW_POSTGAME = (1145, 737)
POSTGAME_QUIT = (50, 20)
POLITICIAN_1  = (435, 540)   # leftmost politician portrait
ACCEPT_BTN    = (760, 1010)  # Accept button
AGE_UP_BTN    = (57, 895)    # CONFIRMED WORKING (not 1356,1029)

_CHAR_TO_VK = {
    'a': VK_A, 'b': VK_B, 'c': VK_C, 'd': VK_D, 'e': VK_E, 'f': VK_F,
    'g': VK_G, 'h': VK_H, 'i': VK_I, 'j': VK_J, 'k': VK_K, 'l': VK_L,
    'm': VK_M, 'n': VK_N, 'o': VK_O, 'p': VK_P, 'q': VK_Q, 'r': VK_R,
    's': VK_S, 't': VK_T, 'u': VK_U, 'v': VK_V, 'w': VK_W, 'x': VK_X,
    'y': VK_Y, 'z': VK_Z,
    '0': VK_0, '1': VK_1, '2': VK_2, '3': VK_3, '4': VK_4,
    '5': VK_5, '6': VK_6, '7': VK_7, '8': VK_8, '9': VK_9,
    ' ': VK_SPACE,
}

_c: HarnessClient = None  # type: ignore


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def connect() -> None:
    global _c
    _c = HarnessClient(SOCK, timeout=15.0)
    _c.connect(timeout=10.0)
    s = _c.state()
    log(f"Connected: pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h}")


def alive() -> bool:
    try:
        _c.state()
        return True
    except Exception:
        return False


def snap(name: str) -> Path:
    p = OUT / name
    r = _c.screenshot(str(p))
    log(f"  => {name} ({r.bytes_written:,}B)")
    return p


def tmp_snap(name: str) -> Path:
    p = TMP / name
    _c.screenshot(str(p))
    return p


def click(x: int, y: int, wait: float = 0.3) -> None:
    _c.move(x, y)
    time.sleep(0.05)
    _c.click(x, y)
    time.sleep(wait)


def key(vk: int, wait: float = 0.15) -> None:
    _c.key(vk)
    time.sleep(wait)


def type_text(text: str) -> None:
    for ch in text.lower():
        vk = _CHAR_TO_VK.get(ch)
        if vk is None:
            continue
        _c.key(vk)
        time.sleep(0.04)


def apply_cheat(phrase: str) -> None:
    log(f"  cheat: {phrase!r}")
    key(VK_RETURN, wait=0.8)
    type_text(phrase)
    time.sleep(0.3)
    key(VK_RETURN, wait=1.5)


def select_tc() -> None:
    """Grid scan to find and click TC (British TC on Budapest 8-player map)."""
    log("  Scanning for TC via grid...")
    for ty in range(430, 490, 8):
        for tx in range(740, 850, 12):
            click(tx, ty, 0.08)
    time.sleep(0.3)
    log("  TC grid scan complete")


def capture_age_dialog(age: int, out_name: str) -> bool:
    """Apply cheats, select TC, click age-up, capture dialog."""
    log(f"--- Capturing Age {age} dialog ({out_name}) ---")

    # Apply resources first (before selecting TC — chat deselects TC)
    apply_cheat("this is too hard")
    apply_cheat("this is too hard")
    time.sleep(1.5)

    # Select TC via grid scan
    select_tc()
    time.sleep(0.5)

    # Take a pre-click diagnostic snap
    tmp_snap(f"ageup{age}_before_click.png")

    # Click age-up button (confirmed at 57, 895)
    click(AGE_UP_BTN[0], AGE_UP_BTN[1], wait=2.5)

    # Diagnostic snap
    tmp_snap(f"ageup{age}_after_click.png")

    # Capture
    snap(out_name)
    log(f"  {out_name} saved")
    return True


def accept_age() -> None:
    """Click leftmost politician + Accept."""
    click(POLITICIAN_1[0], POLITICIAN_1[1], wait=0.8)
    click(ACCEPT_BTN[0], ACCEPT_BTN[1], wait=2.0)
    log("  Accepted, waiting 30s for age transition...")
    time.sleep(30.0)


def resign_and_quit() -> None:
    log("Resigning...")
    click(*GEARS_BTN, wait=1.5)
    tmp_snap("resign_esc_menu.png")
    click(*ESC_RESIGN, wait=1.5)
    tmp_snap("resign_confirm.png")
    click(*RESIGN_YES, wait=4.0)
    tmp_snap("resign_postgame.png")
    time.sleep(2.0)
    # Try to click View Postgame
    click(*VIEW_POSTGAME, wait=3.0)
    tmp_snap("resign_results.png")
    # Save endgame
    snap("07_endgame_screen.png")
    log("  07_endgame_screen.png saved")
    # Go to main menu
    time.sleep(1.0)
    click(*POSTGAME_QUIT, wait=3.0)
    log("  Returned to main menu")


def rebuild_site() -> None:
    log("Rebuilding release readiness site...")
    result = subprocess.run(
        [sys.executable, "tools/validation/build_release_readiness_site.py"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        log("  Site rebuilt successfully")
    else:
        log(f"  Site rebuild FAILED (rc={result.returncode})")
        if result.stderr:
            log(f"  stderr: {result.stderr[-500:]}")


def summarize() -> None:
    log("\n=== FINAL CAPTURE SUMMARY ===")
    surfaces = [
        "01_lobby.png", "02_loading.png", "03_hud.png",
        "09_hero_selected.png", "07_scoreboard.png", "06_diplomacy.png",
        "05_homecity_panel.png", "05_tech_tree.png", "08_esc_menu.png",
        "08_ageup_age2.png", "08_ageup_age3.png", "08_ageup_age4.png",
        "08_ageup_age5.png", "07_endgame_screen.png",
    ]
    ok = 0
    for s in surfaces:
        p = OUT / s
        if p.exists():
            log(f"  OK   ({p.stat().st_size:>10,}B)  {s}")
            ok += 1
        else:
            log(f"  MISS                       {s}")
    log(f"\nTotal: {ok}/{len(surfaces)} surfaces")


def main() -> int:
    connect()

    if not alive():
        log("ABORT: harness not responding")
        return 1

    log("Starting from: Age II dialog showing (Age II already captured)")
    log("Step 1: Accept Age II politician")
    # Age II dialog should already be on screen
    click(POLITICIAN_1[0], POLITICIAN_1[1], wait=0.8)
    click(ACCEPT_BTN[0], ACCEPT_BTN[1], wait=2.0)
    log("  Age II accepted, waiting 30s for transition...")
    time.sleep(30.0)

    if not alive():
        log("CRASH after Age II accept")
        summarize()
        return 1

    # Age III
    capture_age_dialog(3, "08_ageup_age3.png")
    if not alive():
        log("CRASH after Age III capture")
        summarize()
        return 1
    accept_age()

    if not alive():
        log("CRASH after Age III accept")
        summarize()
        return 1

    # Age IV
    capture_age_dialog(4, "08_ageup_age4.png")
    if not alive():
        log("CRASH after Age IV capture")
        summarize()
        return 1
    accept_age()

    if not alive():
        log("CRASH after Age IV accept")
        summarize()
        return 1

    # Age V
    capture_age_dialog(5, "08_ageup_age5.png")
    if not alive():
        log("CRASH after Age V capture")
        summarize()
        return 1
    # Accept Age V (game will transition to Age V, no further age-up needed)
    click(POLITICIAN_1[0], POLITICIAN_1[1], wait=0.8)
    click(ACCEPT_BTN[0], ACCEPT_BTN[1], wait=3.0)
    log("  Age V accepted")
    time.sleep(10.0)

    if alive():
        resign_and_quit()

    summarize()

    if alive():
        rebuild_site()
    else:
        log("Game crashed before rebuild — running rebuild anyway from files on disk")
        rebuild_site()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
