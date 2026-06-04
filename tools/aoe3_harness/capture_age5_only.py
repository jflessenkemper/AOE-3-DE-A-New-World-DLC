#!/usr/bin/env python3
"""Re-capture age5 only. Assumes we're currently in-game at Age IV or have just completed it.

The problem: age4 and age5 captures were identical because the age IV transition
hadn't fully completed when we clicked age-up for age V.

This script:
1. Launches a fresh game (navigates from current menu state)
2. Advances through ages II, III, IV quickly (skip saving, they exist)
3. Waits a LONG time after age IV transition before clicking age-up for V
4. Saves age5 distinctly from age4

Key fix: after accepting politician, sleep 15s (cinematic) + poll until HUD stable.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))

from PIL import Image
from tools.aoe3_harness.harness_client import HarnessClient

SOCK = "/tmp/AOE3DEHarness.sock"
OUT  = REPO / "artifacts/validation/visual_art/ANWBritish/full"
TMP  = Path("/tmp/capture_a5")
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)

VK_ESC    = 0x1B
VK_END    = 0x23
VK_RETURN = 0x0D

SKIRMISH_BTN = (130, 482)
MAP_BTN      = (1637, 425)
HUBTEST_TILE = (1059, 304)
PLAY_BTN     = (1648, 1048)
AGE_UP_BTN   = (1356, 1029)
POLITICIAN_1 = (435, 540)
ESC_RESIGN   = (1830, 365)
RESIGN_YES   = (760, 605)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def screenshot(c: HarnessClient, path: Path) -> Image.Image:
    c.screenshot(str(path))
    return Image.open(path)


def probe_top_row(c: HarnessClient) -> float:
    p = TMP / "_probe.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        row = [im.getpixel((x, 15)) for x in range(50, 1800, 100)]
        return sum(sum(px[:3]) for px in row) / len(row) / 3


def is_in_game(c: HarnessClient) -> bool:
    p = TMP / "_state.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        hud_row = [im.getpixel((x, 15)) for x in range(200, 1200, 100)]
        hud_avg = sum(sum(px[:3]) for px in hud_row) / len(hud_row) / 3
        log(f"    is_in_game probe: hud_avg={hud_avg:.1f}")
        return hud_avg > 60


def wait_for_in_game(c: HarnessClient, timeout: int = 180) -> bool:
    log(f"  waiting for in-game (up to {timeout}s)...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_in_game(c):
            log("  -> in-game!")
            return True
        time.sleep(5)
    return False


def ensure_main_menu(c: HarnessClient) -> None:
    """Try to get back to main menu by pressing ESC a few times."""
    for _ in range(3):
        c.key(VK_ESC)
        time.sleep(1.5)
    c.screenshot(str(TMP / "_main_menu_check.png"))


def launch_new_game(c: HarnessClient) -> bool:
    log("navigating to ANW Hub Test and launching...")
    c.click(*SKIRMISH_BTN)
    time.sleep(3.5)
    c.click(*MAP_BTN)
    time.sleep(2.5)
    c.click(150, 304)
    time.sleep(0.4)
    c.key(VK_END)
    time.sleep(1.0)
    c.screenshot(str(TMP / "_map_end.png"))
    c.click(*HUBTEST_TILE)
    time.sleep(0.25)
    c.click(*HUBTEST_TILE)
    time.sleep(2.5)
    c.screenshot(str(TMP / "_lobby.png"))
    c.click(*PLAY_BTN)
    time.sleep(2.0)
    return wait_for_in_game(c, timeout=180)


def probe_politician_dialog(c: HarnessClient) -> tuple[bool, float]:
    p = TMP / "_pol_probe.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        title_row = [im.getpixel((x, 200)) for x in range(600, 1300, 50)]
        title_avg = sum(sum(px[:3]) for px in title_row) / len(title_row) / 3
        portrait = im.getpixel((435, 540))
        portrait_b = sum(portrait[:3]) / 3
        return (title_avg > 40 or portrait_b > 30), title_avg


def wait_politician_dialog(c: HarnessClient, timeout: int = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ok, avg = probe_politician_dialog(c)
        log(f"    pol_probe: title_avg={avg:.1f} ok={ok}")
        if ok:
            return True
        time.sleep(1.5)
    return False


def wait_transition_done(c: HarnessClient, age_num: int, min_wait: int = 10, timeout: int = 120) -> bool:
    """Wait for age transition: mandatory min_wait + poll until HUD visible again."""
    log(f"  waiting {min_wait}s mandatory then polling for HUD after age {age_num} transition...")
    time.sleep(min_wait)
    deadline = time.monotonic() + timeout
    last_row = 0.0
    while time.monotonic() < deadline:
        row_avg = probe_top_row(c)
        log(f"    row_avg={row_avg:.1f} (last={last_row:.1f})")
        # HUD is visible: bright. Also confirm it stabilized (two readings > 60)
        if row_avg > 60 and last_row > 60:
            log("  -> HUD stable, transition done")
            return True
        last_row = row_avg
        time.sleep(3)
    log(f"  WARNING: transition timeout after age {age_num}")
    return False


def apply_cheats(c: HarnessClient) -> None:
    """Apply food/wood/coin cheats without using H key."""
    # 'coinage' = +10000 coin. No H.
    for cheat in ["coinage", "coinage", "coinage", "coinage"]:
        c.key(VK_RETURN)
        time.sleep(0.6)
        for ch in cheat:
            c.key(ord(ch.upper()))
            time.sleep(0.05)
        time.sleep(0.3)
        c.key(VK_RETURN)
        time.sleep(1.0)

    # 'lumberjack' = +1000 wood. No H.
    for cheat in ["lumberjack", "lumberjack", "lumberjack"]:
        c.key(VK_RETURN)
        time.sleep(0.6)
        for ch in cheat:
            c.key(ord(ch.upper()))
            time.sleep(0.05)
        time.sleep(0.3)
        c.key(VK_RETURN)
        time.sleep(1.0)


def avg_hash(path: Path) -> int:
    with Image.open(path) as im:
        small = im.convert("L").resize((8, 8), Image.LANCZOS)
        pixels = list(small.get_flattened_data() if hasattr(small, 'get_flattened_data') else small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = [1 if p >= avg else 0 for p in pixels]
        val = 0
        for b in bits:
            val = (val << 1) | b
        return val


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count('1')


def main() -> int:
    c = HarnessClient(SOCK)
    c.connect(timeout=30)
    st = c.state()
    log(f"connected: ready={st.ready} {st.internal_w}x{st.internal_h}")

    # Check state
    in_game = is_in_game(c)
    log(f"initial in_game={in_game}")

    if in_game:
        # Resign first, get to main menu
        log("in-game detected — resigning to get to main menu...")
        c.key(VK_ESC)
        time.sleep(1.5)
        c.screenshot(str(TMP / "_esc.png"))
        c.click(*ESC_RESIGN)
        time.sleep(1.5)
        c.screenshot(str(TMP / "_resign.png"))
        c.click(*RESIGN_YES)
        time.sleep(4)
        c.screenshot(str(TMP / "_after_resign.png"))
        # Check if we're now at main menu
        if is_in_game(c):
            log("still in game after resign — pressing ESC repeatedly")
            for _ in range(5):
                c.key(VK_ESC)
                time.sleep(1.5)
            time.sleep(2)

    log("launching new game...")
    ok = launch_new_game(c)
    if not ok:
        log("ERROR: failed to detect in-game")
        c.screenshot(str(TMP / "_fail.png"))
        c.close()
        return 1

    c.screenshot(str(TMP / "_game_start.png"))
    log("applying cheats...")
    apply_cheats(c)
    c.screenshot(str(TMP / "_after_cheats.png"))

    # Advance through ages 2, 3, 4 (skip saving age2/age3 since they exist)
    for age_num in [2, 3, 4]:
        out_path = OUT / f"08_ageup_age{age_num}.png"
        log(f"\n=== Advancing through Age {age_num} ===")

        # Click age-up
        log(f"  clicking age-up...")
        c.click(*AGE_UP_BTN)
        time.sleep(3.0)

        # Wait for politician dialog
        if wait_politician_dialog(c, timeout=30):
            log(f"  politician dialog visible")
        else:
            log(f"  WARNING: no politician dialog for age {age_num}")
            c.screenshot(str(TMP / f"_age{age_num}_no_dialog.png"))

        # Screenshot if needed
        if not out_path.exists():
            log(f"  saving age{age_num}...")
            c.screenshot(str(out_path))

        # Accept
        log(f"  accepting politician...")
        c.click(*POLITICIAN_1)
        time.sleep(1.0)

        # Wait for transition with LONGER mandatory wait
        wait_transition_done(c, age_num, min_wait=15, timeout=90)
        c.screenshot(str(TMP / f"_post_age{age_num}.png"))

    # Now capture age 5
    log("\n=== Capturing Age 5 ===")
    out_age5 = OUT / "08_ageup_age5.png"

    log("clicking age-up for age 5...")
    c.click(*AGE_UP_BTN)
    time.sleep(3.0)

    if wait_politician_dialog(c, timeout=30):
        log("politician dialog visible for age 5")
        c.screenshot(str(out_age5))
        log(f"saved {out_age5}")
    else:
        log("WARNING: no politician dialog for age 5")
        c.screenshot(str(TMP / "_age5_no_dialog.png"))
        c.screenshot(str(out_age5))  # save anyway

    # Accept age 5
    c.click(*POLITICIAN_1)
    time.sleep(2.0)

    # Resign
    log("resigning...")
    c.key(VK_ESC)
    time.sleep(1.5)
    c.click(*ESC_RESIGN)
    time.sleep(1.5)
    c.click(*RESIGN_YES)
    time.sleep(3)

    # Distinctness check
    log("\n=== Distinctness check ===")
    all_caps = [
        ("age2", OUT / "08_ageup_age2.png"),
        ("age3", OUT / "08_ageup_age3.png"),
        ("age4", OUT / "08_ageup_age4.png"),
        ("age5", OUT / "08_ageup_age5.png"),
    ]
    existing = [(name, p) for name, p in all_caps if p.exists()]
    hashes = [(name, avg_hash(p)) for name, p in existing]
    all_distinct = True
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = hamming(hashes[i][1], hashes[j][1])
            status = "DISTINCT" if d > 15 else "SAME!"
            log(f"  {hashes[i][0]} vs {hashes[j][0]}: hamming={d} [{status}]")
            if d <= 15:
                all_distinct = False

    log(f"\nResult: all_distinct={all_distinct}")
    c.close()
    return 0 if all_distinct else 1


if __name__ == "__main__":
    sys.exit(main())
