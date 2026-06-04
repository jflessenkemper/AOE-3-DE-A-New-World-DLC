#!/usr/bin/env python3
"""Final correct age-up capture script.

Key insight from analysis:
- Lobby hud_avg at y=15: ~100-150 (bright header)
- In-game hud_avg at y=15: ~55-75 (terrain + darker HUD)
- Main menu: ~30-60 (dark background)

So wait_for_in_game should detect: hud transitions from HIGH (lobby ~100+)
DOWN to MEDIUM (~55-80), indicating the game has loaded.

Uses only HarnessClient. No xdotool.
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
TMP  = Path("/tmp/capture_final2")
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


def hud_avg(c: HarnessClient) -> float:
    p = TMP / "_hud.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        row = [im.getpixel((x, 15)) for x in range(50, 1800, 100)]
        return sum(sum(px[:3]) for px in row) / len(row) / 3


def screen_state(c: HarnessClient) -> str:
    """Classify current screen: 'lobby', 'in_game', 'main_menu', 'unknown'"""
    p = TMP / "_state.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        # y=15 top strip
        row15 = [im.getpixel((x, 15)) for x in range(50, 1800, 100)]
        avg15 = sum(sum(px[:3]) for px in row15) / len(row15) / 3

        # y=500 middle strip (terrain in game, lobby UI / main menu bg)
        row500 = [im.getpixel((x, 500)) for x in range(50, 1800, 100)]
        avg500 = sum(sum(px[:3]) for px in row500) / len(row500) / 3

        # Bottom-right minimap area (dark in-game, bright in lobby/menu)
        br_region = [im.getpixel((x, y)) for x in range(1700, 1900, 20) for y in range(900, 1050, 20)]
        br_avg = sum(sum(px[:3]) for px in br_region) / len(br_region) / 3

        log(f"    state: avg15={avg15:.1f} avg500={avg500:.1f} br_avg={br_avg:.1f}")

        if avg15 > 90:
            return "lobby"  # Bright lobby header
        elif avg15 > 50 and br_avg < 80:
            return "in_game"  # Darker in-game with dark minimap
        elif avg15 < 60 and avg500 < 80:
            return "main_menu"
        else:
            return "unknown"


def wait_for_state(c: HarnessClient, target: str, timeout: int = 180) -> bool:
    log(f"  waiting for state='{target}' (up to {timeout}s)...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        st = screen_state(c)
        if st == target:
            log(f"  -> reached '{target}'")
            return True
        time.sleep(5)
    return False


def go_to_lobby(c: HarnessClient) -> bool:
    """Navigate to skirmish lobby with ANW Hub Test selected."""
    log("navigating to lobby...")
    c.click(*SKIRMISH_BTN); time.sleep(3.5)
    c.click(*MAP_BTN); time.sleep(2.5)
    c.click(150, 304); time.sleep(0.4)
    c.key(VK_END); time.sleep(1.0)
    c.screenshot(str(TMP / "_map_end.png"))
    c.click(*HUBTEST_TILE); time.sleep(0.25)
    c.click(*HUBTEST_TILE); time.sleep(2.5)
    c.screenshot(str(TMP / "_after_map_select.png"))
    # Check we're in lobby now
    st = screen_state(c)
    log(f"  after map select: state={st}")
    return True


def apply_cheats(c: HarnessClient) -> None:
    """Apply food/wood/coin cheats (no H key used)."""
    # 'coinage' = +10000 coin
    # 'lumberjack' = +1000 wood
    for cheat in ["coinage"] * 3 + ["lumberjack"] * 3:
        c.key(VK_RETURN); time.sleep(0.5)
        for ch in cheat:
            c.key(ord(ch.upper())); time.sleep(0.04)
        time.sleep(0.2)
        c.key(VK_RETURN); time.sleep(0.8)


def wait_politician_dialog(c: HarnessClient, timeout: int = 30) -> bool:
    """Wait for politician select dialog by checking overlay brightness."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = TMP / "_pol.png"
        c.screenshot(str(p))
        with Image.open(p) as im:
            # The politician dialog shows a dark overlay with bright portrait boxes
            # Check the center-left where the first politician portrait would be
            # Also check: when dialog is showing, the y=400-600 area becomes brighter
            # than normal in-game terrain due to the portrait cards
            portrait_region = [im.getpixel((x, 540)) for x in range(350, 550, 20)]
            portrait_avg = sum(sum(px[:3]) for px in portrait_region) / len(portrait_region) / 3

            # Title area: y=200, x=500-1400
            title = [im.getpixel((x, 200)) for x in range(500, 1400, 50)]
            title_avg = sum(sum(px[:3]) for px in title) / len(title) / 3

            # Overlay: when dialog is showing, center area (960, 540) has the overlay bg
            center = im.getpixel((960, 300))
            center_b = sum(center[:3]) / 3

            log(f"    pol: portrait_avg={portrait_avg:.1f} title_avg={title_avg:.1f} center_b={center_b:.1f}")

            # Dialog detected: bright portrait area AND darker title area (text on dark bg)
            # Compared to terrain which is ~80-100 uniformly
            if portrait_avg > 80 and title_avg > 50:
                return True
        time.sleep(1.5)
    return False


def wait_transition(c: HarnessClient, age_num: int) -> None:
    """Wait 25s mandatory then for HUD to stabilize at in-game level."""
    log(f"  waiting for age {age_num} transition (25s mandatory)...")
    time.sleep(25)
    # Poll: wait for state to be 'in_game' (not cinematic brightness)
    for _ in range(15):
        st = screen_state(c)
        if st == "in_game":
            log("  -> transition done")
            return
        log(f"    still transitioning: {st}")
        time.sleep(3)
    log("  -> transition timeout, proceeding")


def avg_hash(path: Path) -> int:
    import warnings
    with Image.open(path) as im:
        small = im.convert("L").resize((8, 8), Image.LANCZOS)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pixels = list(small.getdata())
        avg_v = sum(pixels) / len(pixels)
        bits = [1 if p >= avg_v else 0 for p in pixels]
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

    # Diagnose current state
    cur_state = screen_state(c)
    log(f"current state: {cur_state}")
    c.screenshot(str(TMP / "_initial.png"))

    if cur_state == "in_game":
        log("in-game — resigning first...")
        c.key(VK_ESC); time.sleep(1.5)
        c.screenshot(str(TMP / "_esc.png"))
        # Look for resign button - try multiple approaches
        c.click(*ESC_RESIGN); time.sleep(1.5)
        c.screenshot(str(TMP / "_resign_dialog.png"))
        c.click(*RESIGN_YES); time.sleep(4)
        cur_state = screen_state(c)
        log(f"after resign: {cur_state}")

    if cur_state == "lobby":
        log("in lobby — just need to click Play or re-select map...")
        # Re-navigate to ensure HubTest is selected
        # Or just click Play if the map is already selected
        # Let's look at the lobby screenshot to decide
        c.screenshot(str(TMP / "_lobby_state.png"))
        # Click Play
        log("clicking Play from lobby...")
        c.click(*PLAY_BTN); time.sleep(3)
    elif cur_state in ("main_menu", "unknown"):
        log("at main menu or unknown — full navigation...")
        go_to_lobby(c)
        c.screenshot(str(TMP / "_lobby_ready.png"))
        log("clicking Play...")
        c.click(*PLAY_BTN); time.sleep(3)

    # Wait for actual in-game state
    log("waiting for game to load (hud must drop from lobby ~100+ to in-game ~55-80)...")
    deadline = time.monotonic() + 200
    in_game_confirmed = False
    prev_avg = hud_avg(c)
    log(f"  initial hud_avg={prev_avg:.1f}")
    while time.monotonic() < deadline:
        time.sleep(5)
        st_check = screen_state(c)
        cur_avg = hud_avg(c)
        log(f"  state={st_check} hud_avg={cur_avg:.1f}")
        if st_check == "in_game":
            in_game_confirmed = True
            break
        # Also check: if avg was high (lobby) and dropped significantly, we're in game
        if prev_avg > 90 and cur_avg < 80 and cur_avg > 40:
            log("  -> HUD dropped from lobby level to in-game level!")
            in_game_confirmed = True
            break
        prev_avg = cur_avg

    if not in_game_confirmed:
        log("ERROR: could not confirm in-game state")
        c.screenshot(str(TMP / "_fail.png"))
        c.close()
        return 1

    c.screenshot(str(TMP / "_confirmed_in_game.png"))
    log("In-game confirmed!")

    # Give game a moment to settle
    time.sleep(3)

    # Apply resource cheats
    log("applying cheats...")
    apply_cheats(c)
    c.screenshot(str(TMP / "_after_cheats.png"))

    # Age-up capture loop
    for age_num in [2, 3, 4, 5]:
        out_path = OUT / f"08_ageup_age{age_num}.png"
        log(f"\n=== Age {age_num} ===")

        # Click age-up
        log("  clicking age-up...")
        c.click(*AGE_UP_BTN); time.sleep(3)

        # Wait for politician dialog
        ok = wait_politician_dialog(c, timeout=30)
        log(f"  politician dialog: {'detected' if ok else 'NOT DETECTED'}")

        if not ok:
            c.screenshot(str(TMP / f"_age{age_num}_no_dialog.png"))

        # Screenshot (save even if dialog not confirmed)
        log(f"  saving {out_path.name}...")
        c.screenshot(str(out_path))

        # Accept politician
        log("  accepting politician (1st portrait)...")
        c.click(*POLITICIAN_1); time.sleep(1.5)

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
    caps = [
        ("age2", OUT / "08_ageup_age2.png"),
        ("age3", OUT / "08_ageup_age3.png"),
        ("age4", OUT / "08_ageup_age4.png"),
        ("age5", OUT / "08_ageup_age5.png"),
    ]
    existing = [(n, p) for n, p in caps if p.exists()]
    hashes = [(n, avg_hash(p)) for n, p in existing]
    all_distinct = True
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = hamming(hashes[i][1], hashes[j][1])
            ok_str = "DISTINCT" if d > 15 else "SAME!"
            log(f"  {hashes[i][0]} vs {hashes[j][0]}: hamming={d} [{ok_str}]")
            if d <= 15:
                all_distinct = False

    log(f"\nResult: all_distinct={all_distinct}")
    c.close()
    return 0 if all_distinct else 1


if __name__ == "__main__":
    sys.exit(main())
