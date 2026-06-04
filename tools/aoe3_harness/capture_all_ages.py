#!/usr/bin/env python3
"""Re-capture all 4 age-up politician dialogs with proper timing.

Key fixes:
- Longer mandatory wait between transitions (15s + poll)
- Screenshot BEFORE accepting (not after)
- Save all 4 ages fresh
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
TMP  = Path("/tmp/capture_all_ages")
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


def probe_hud_avg(c: HarnessClient) -> float:
    p = TMP / "_probe.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        row = [im.getpixel((x, 15)) for x in range(50, 1800, 100)]
        return sum(sum(px[:3]) for px in row) / len(row) / 3


def is_in_game(c: HarnessClient) -> bool:
    avg = probe_hud_avg(c)
    log(f"    hud_avg={avg:.1f}")
    return avg > 60


def wait_for_in_game(c: HarnessClient, timeout: int = 180) -> bool:
    log(f"  waiting for in-game (up to {timeout}s)...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_in_game(c):
            log("  -> in-game confirmed")
            return True
        time.sleep(5)
    return False


def launch_new_game(c: HarnessClient) -> bool:
    log("navigating: Skirmish -> Map -> HubTest -> Play")
    c.click(*SKIRMISH_BTN); time.sleep(3.5)
    c.click(*MAP_BTN); time.sleep(2.5)
    c.click(150, 304); time.sleep(0.4)
    c.key(VK_END); time.sleep(1.0)
    c.screenshot(str(TMP / "_map_end.png"))
    c.click(*HUBTEST_TILE); time.sleep(0.25)
    c.click(*HUBTEST_TILE); time.sleep(2.5)
    c.screenshot(str(TMP / "_lobby.png"))
    c.click(*PLAY_BTN); time.sleep(2.0)
    return wait_for_in_game(c, timeout=180)


def wait_politician(c: HarnessClient, timeout: int = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = TMP / "_pol.png"
        c.screenshot(str(p))
        with Image.open(p) as im:
            row = [im.getpixel((x, 200)) for x in range(600, 1300, 50)]
            avg = sum(sum(px[:3]) for px in row) / len(row) / 3
            log(f"    pol title avg={avg:.1f}")
            if avg > 40:
                return True
        time.sleep(1.5)
    return False


def wait_transition(c: HarnessClient, age_num: int) -> None:
    """Wait for age cinematic to complete: mandatory 20s + stable HUD."""
    log(f"  transition wait after age {age_num} (mandatory 20s)...")
    time.sleep(20)
    # Then poll for 2 consecutive bright HUD readings
    last = 0.0
    for _ in range(20):
        avg = probe_hud_avg(c)
        log(f"    post-transition hud_avg={avg:.1f} last={last:.1f}")
        if avg > 60 and last > 60:
            log("  -> transition done (HUD stable)")
            return
        last = avg
        time.sleep(3)
    log("  -> transition timeout, continuing anyway")


def apply_cheats(c: HarnessClient) -> None:
    """Apply food/wood/coin cheats. Uses only keys without H."""
    # 'coinage' = +10000 coin (no H)
    # 'lumberjack' = +1000 wood (no H)
    # 'medium difficulty' — has no H but weird spacing, skip
    # Apply coinage 5x for plenty of coin
    for cheat in ["coinage"] * 5 + ["lumberjack"] * 5:
        c.key(VK_RETURN); time.sleep(0.5)
        for ch in cheat:
            c.key(ord(ch.upper())); time.sleep(0.04)
        time.sleep(0.2)
        c.key(VK_RETURN); time.sleep(0.8)


def avg_hash(path: Path) -> int:
    with Image.open(path) as im:
        small = im.convert("L").resize((8, 8), Image.LANCZOS)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pixels = list(small.getdata())
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

    # Resign if in game
    if is_in_game(c):
        log("in game — resigning...")
        c.key(VK_ESC); time.sleep(1.5)
        c.click(*ESC_RESIGN); time.sleep(1.5)
        c.click(*RESIGN_YES); time.sleep(4)
        if is_in_game(c):
            log("still in game, ESC spam...")
            for _ in range(5):
                c.key(VK_ESC); time.sleep(1.5)

    # Launch fresh game
    log("launching fresh game...")
    if not launch_new_game(c):
        log("ERROR: could not detect in-game")
        c.screenshot(str(TMP / "_fail.png"))
        c.close()
        return 1

    c.screenshot(str(TMP / "_game_loaded.png"))
    log("applying cheats...")
    apply_cheats(c)
    c.screenshot(str(TMP / "_after_cheats.png"))

    # Capture all 4 ages
    results = {}
    for age_num in [2, 3, 4, 5]:
        out_path = OUT / f"08_ageup_age{age_num}.png"
        log(f"\n=== Age {age_num} ===")

        log("  clicking age-up button...")
        c.click(*AGE_UP_BTN)
        time.sleep(3.0)

        ok = wait_politician(c, timeout=30)
        log(f"  politician dialog: {'visible' if ok else 'NOT DETECTED'}")

        if not ok:
            c.screenshot(str(TMP / f"_age{age_num}_fail.png"))

        # Screenshot BEFORE accepting
        log(f"  saving {out_path.name}...")
        c.screenshot(str(out_path))
        results[f"age{age_num}"] = out_path

        # Accept politician
        log("  accepting politician...")
        c.click(*POLITICIAN_1)
        time.sleep(1.5)

        if age_num < 5:
            wait_transition(c, age_num)
            c.screenshot(str(TMP / f"_post_age{age_num}.png"))

    # Resign
    log("\nresigning...")
    c.key(VK_ESC); time.sleep(1.5)
    c.click(*ESC_RESIGN); time.sleep(1.5)
    c.click(*RESIGN_YES); time.sleep(3)

    # Distinctness check
    log("\n=== Distinctness check ===")
    caps = [(k, v) for k, v in results.items() if v.exists()]
    hashes = [(name, avg_hash(p)) for name, p in caps]
    all_distinct = True
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = hamming(hashes[i][1], hashes[j][1])
            ok_str = "DISTINCT" if d > 15 else "SAME!"
            log(f"  {hashes[i][0]} vs {hashes[j][0]}: hamming={d} [{ok_str}]")
            if d <= 15:
                all_distinct = False

    log(f"\nall_distinct={all_distinct}")
    c.close()
    return 0 if all_distinct else 1


if __name__ == "__main__":
    sys.exit(main())
