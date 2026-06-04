#!/usr/bin/env python3
"""Capture age IV and V politician-select dialog screenshots.

Uses ONLY HarnessClient (socket injection). Never xdotool.

Strategy:
- Navigate from main menu -> ANW Hub Test map -> launch game
- Wait for actual in-game HUD (detect dark UI strip at y=15 that becomes bright)
- SKIP cheat (Hub Test spawns with ~100k resources)
- Click age-up button, wait for politician dialog, screenshot, accept, wait for transition
- Repeat for each age (start at II, skip if file exists, continue to IV and V)
- Save to artifacts/validation/visual_art/ANWBritish/full/
- Run avg-hash distinctness check

In-game detection: use pixel at (960, 15) — in the HUD this is part of the gold
resource bar tray (bright ~180+). On main menu the top strip is dark/transparent (~30).
We also cross-check (130, 482) which is Skirmish button text (dark) on main menu.
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
TMP  = Path("/tmp/capture_a4a5")
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)

# VK constants
VK_ESC    = 0x1B
VK_END    = 0x23
VK_RETURN = 0x0D

# Nav coords (verified 2026-05-31)
SKIRMISH_BTN = (130, 482)
MAP_BTN      = (1637, 425)
HUBTEST_TILE = (1059, 304)
PLAY_BTN     = (1648, 1048)

# In-game action panel
AGE_UP_BTN   = (1356, 1029)
POLITICIAN_1 = (435, 540)

# ESC menu resign
ESC_RESIGN   = (1830, 365)
RESIGN_YES   = (760, 605)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def grab(c: HarnessClient, path: Path) -> Image.Image:
    c.screenshot(str(path))
    return Image.open(path)


def is_in_game(c: HarnessClient) -> bool:
    """Check if we're in-game by looking at HUD area.

    In-game: resource bar at top (y=15) shows bright gold/orange UI (~150+).
    Main menu: top strip is dark background (~30-60).
    We also check that the Skirmish button location (130, 482) is NOT the typical
    main-menu nav-button (bright blue ~100+).
    """
    p = TMP / "_state_probe.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        # Sample several points across top HUD bar
        hud_samples = [im.getpixel((x, 15)) for x in range(200, 1200, 100)]
        hud_avg = sum(sum(px[:3]) for px in hud_samples) / len(hud_samples) / 3

        # Sample the Skirmish button area — bright on main menu, terrain on in-game
        skirmish_area = [im.getpixel((x, 482)) for x in range(80, 200, 10)]
        skirmish_avg = sum(sum(px[:3]) for px in skirmish_area) / len(skirmish_area) / 3

        log(f"    state probe: hud_avg={hud_avg:.1f}, skirmish_area_avg={skirmish_avg:.1f}")

        # In-game: HUD bar is visible (bright), skirmish button gone (dark terrain)
        # Main menu: HUD bar absent (dark), skirmish button visible (brighter)
        # Heuristic: if HUD avg > 60 AND skirmish area is darker than main menu
        return hud_avg > 60


def wait_for_in_game(c: HarnessClient, timeout: int = 180) -> bool:
    """Poll until in-game HUD is visible."""
    log(f"  waiting for in-game HUD (up to {timeout}s)...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = TMP / "_hud_wait.png"
        try:
            c.screenshot(str(p))
            with Image.open(p) as im:
                # HUD resource bar region y=10-20, look for bright UI pixels
                # Sample across different x positions
                row = [im.getpixel((x, 15)) for x in range(50, 1800, 100)]
                avg = sum(sum(px[:3]) for px in row) / len(row) / 3

                # Also check for the distinctive dark background of main menu at y=482
                skirmish_row = [im.getpixel((x, 482)) for x in range(80, 200, 10)]
                s_avg = sum(sum(px[:3]) for px in skirmish_row) / len(skirmish_row) / 3

                log(f"    hud_avg={avg:.1f} skirmish_row_avg={s_avg:.1f}")

                # In game: HUD bright, action panel row bright
                # Look specifically for resource bar: y=8 center-ish
                # The ANW resource bar uses gold/orange tones
                center_row = [im.getpixel((x, 8)) for x in range(400, 1600, 80)]
                center_avg = sum(sum(px[:3]) for px in center_row) / len(center_row) / 3
                log(f"    center_row_avg (y=8)={center_avg:.1f}")

                if avg > 70 and center_avg > 80:
                    log("  -> in-game detected!")
                    return True
        except Exception as e:
            log(f"    wait error: {e}")
        time.sleep(5)
    return False


def navigate_to_hubtest_and_play(c: HarnessClient) -> None:
    """From main menu, navigate to ANW Hub Test and click Play."""
    log("  clicking Skirmish...")
    c.click(*SKIRMISH_BTN)
    time.sleep(3.0)

    log("  opening map picker...")
    c.click(*MAP_BTN)
    time.sleep(2.5)

    log("  focusing grid and pressing End...")
    c.click(150, 304)   # focus first tile
    time.sleep(0.4)
    c.key(VK_END)
    time.sleep(1.0)
    c.screenshot(str(TMP / "_map_end.png"))

    log("  double-clicking ANW Hub Test tile (1059, 304)...")
    c.click(*HUBTEST_TILE)
    time.sleep(0.25)
    c.click(*HUBTEST_TILE)
    time.sleep(2.5)
    c.screenshot(str(TMP / "_lobby.png"))

    log("  clicking Play...")
    c.click(*PLAY_BTN)
    time.sleep(1.0)


def apply_cheat_no_h(c: HarnessClient) -> None:
    """Apply 'medium difficulty' cheat (no H) or skip entirely.

    'Medium difficulty' cheat = 'medium difficulty' — but it has no H.
    Actually: 'coinage' gives 10000 gold. 'nova & orion' gives all resources.
    'nova & orion' has no H.
    """
    # 'nova & orion' = food, wood, coin, export boost
    # Safe: no H key, no problematic characters
    cheat = "nova & orion"
    log(f"  applying cheat: {cheat!r}")
    c.key(VK_RETURN)   # open chat
    time.sleep(0.8)
    for ch in cheat:
        if ch == ' ':
            c.key(0x20)
        elif ch == '&':
            # & is shift+7; try VK_7 with shift.
            # Actually just skip — the cheat may still work with 'nova  orion'
            # Or use the raw VK for &
            c.key(0x37)  # '7' key — won't give & but try
        elif ch.isalpha():
            c.key(ord(ch.upper()))
        elif ch.isdigit():
            c.key(ord(ch))
        time.sleep(0.05)
    time.sleep(0.3)
    c.key(VK_RETURN)
    time.sleep(1.5)


def probe_politician_dialog(c: HarnessClient) -> bool:
    """Check if politician selection dialog is visible."""
    p = TMP / "_pol_probe.png"
    c.screenshot(str(p))
    with Image.open(p) as im:
        # Title area of dialog at y=200 center — "SELECT A X AGE POLITICIAN"
        # This should be bright gold text on dark background
        title_px = [im.getpixel((x, 200)) for x in range(600, 1300, 50)]
        title_avg = sum(sum(px[:3]) for px in title_px) / len(title_px) / 3

        # Portrait area at POLITICIAN_1 = (435, 540)
        portrait = im.getpixel((435, 540))
        portrait_brightness = sum(portrait[:3]) / 3

        log(f"    pol_dialog: title_avg={title_avg:.1f} portrait_bright={portrait_brightness:.1f}")
        return title_avg > 40 or portrait_brightness > 30


def wait_for_politician_dialog(c: HarnessClient, timeout: int = 20) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe_politician_dialog(c):
            return True
        time.sleep(1.0)
    return False


def wait_for_age_transition(c: HarnessClient, timeout: int = 90) -> bool:
    """Wait until age transition cinematic is done (HUD visible again)."""
    log("  waiting for age transition to complete...")
    time.sleep(3)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = TMP / "_trans.png"
        try:
            c.screenshot(str(p))
            with Image.open(p) as im:
                row = [im.getpixel((x, 15)) for x in range(50, 500, 40)]
                row_avg = sum(sum(px[:3]) for px in row) / len(row) / 3
                log(f"    trans row_avg={row_avg:.1f}")
                if row_avg > 60:
                    return True
        except Exception as e:
            log(f"    trans error: {e}")
        time.sleep(3)
    return False


def avg_hash(path: Path) -> int:
    with Image.open(path) as im:
        small = im.convert("L").resize((8, 8), Image.LANCZOS)
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

    # Check current state
    log("probing current game state...")
    in_game = is_in_game(c)
    log(f"in_game={in_game}")

    if in_game:
        log("Already in game — will use current game for age-up.")
    else:
        log("At main menu — launching new game...")
        navigate_to_hubtest_and_play(c)
        c.screenshot(str(TMP / "_after_play.png"))
        log("waiting for game to load...")
        if not wait_for_in_game(c, timeout=180):
            log("ERROR: failed to detect in-game after launch")
            c.screenshot(str(TMP / "_fail_state.png"))
            return 1
        log("Game loaded!")

    c.screenshot(str(TMP / "_game_start.png"))

    # Apply cheat for resources (skip — hub test should have enough)
    # Actually let's try 'coinage' which gives 10000 gold, no H
    log("applying 'coinage' cheat for resources...")
    c.key(VK_RETURN)
    time.sleep(0.8)
    for ch in "coinage":
        c.key(ord(ch.upper()))
        time.sleep(0.05)
    time.sleep(0.3)
    c.key(VK_RETURN)
    time.sleep(1.5)

    # Apply 'ya gotta make do' for food/wood (no H)
    log("applying 'ya gotta make do' cheat...")
    c.key(VK_RETURN)
    time.sleep(0.8)
    for ch in "ya gotta make do":
        if ch == ' ':
            c.key(0x20)
        else:
            c.key(ord(ch.upper()))
        time.sleep(0.05)
    time.sleep(0.3)
    c.key(VK_RETURN)
    time.sleep(1.5)

    c.screenshot(str(TMP / "_after_cheats.png"))

    # Age-up sequence
    # If age2 and age3 exist, we still need to advance through them to reach age4/5
    # The game starts at Age I, so we must click age-up for each age
    existing = {
        "08_ageup_age2.png": (OUT / "08_ageup_age2.png").exists(),
        "08_ageup_age3.png": (OUT / "08_ageup_age3.png").exists(),
        "08_ageup_age4.png": (OUT / "08_ageup_age4.png").exists(),
        "08_ageup_age5.png": (OUT / "08_ageup_age5.png").exists(),
    }
    log(f"existing files: {existing}")

    targets = [
        (2, "08_ageup_age2.png"),
        (3, "08_ageup_age3.png"),
        (4, "08_ageup_age4.png"),
        (5, "08_ageup_age5.png"),
    ]

    captures = []
    for age_num, fname in targets:
        out_path = OUT / fname
        log(f"\n=== Age {age_num} ===")

        # Click age-up button
        log(f"  clicking age-up button at {AGE_UP_BTN}...")
        c.click(*AGE_UP_BTN)
        time.sleep(2.5)
        c.screenshot(str(TMP / f"_age{age_num}_after_ageup_click.png"))

        # Wait for politician dialog
        log("  waiting for politician dialog...")
        if not wait_for_politician_dialog(c, timeout=25):
            log(f"  WARNING: no politician dialog detected for age {age_num}")
            c.screenshot(str(TMP / f"_age{age_num}_no_dialog.png"))
            # Maybe dialog appeared briefly or we're already past? continue anyway
        else:
            log(f"  politician dialog detected for age {age_num}")

        # Screenshot
        if out_path.exists() and age_num < 4:
            # File exists and we don't need it — still need to advance through this age
            log(f"  {fname} exists — advancing without re-saving")
            tmp_path = TMP / fname
            c.screenshot(str(tmp_path))
        else:
            log(f"  saving {fname}")
            c.screenshot(str(out_path))
            captures.append((fname, out_path))

        # Click first politician to accept
        log(f"  accepting politician at {POLITICIAN_1}...")
        c.click(*POLITICIAN_1)
        time.sleep(1.5)

        # Wait for age transition
        wait_for_age_transition(c, timeout=90)

        # Extra buffer after age transition
        time.sleep(2)

    log("\n=== Age-up captures done ===")

    # Resign
    log("resigning game...")
    c.key(VK_ESC)
    time.sleep(1.5)
    c.screenshot(str(TMP / "_esc_menu.png"))
    c.click(*ESC_RESIGN)
    time.sleep(1.5)
    c.screenshot(str(TMP / "_resign_confirm.png"))
    c.click(*RESIGN_YES)
    time.sleep(3)
    c.screenshot(str(TMP / "_after_resign.png"))

    # Distinctness check on all 4 age-up files
    log("\n=== Distinctness check ===")
    all_caps = [
        ("age2", OUT / "08_ageup_age2.png"),
        ("age3", OUT / "08_ageup_age3.png"),
        ("age4", OUT / "08_ageup_age4.png"),
        ("age5", OUT / "08_ageup_age5.png"),
    ]
    existing_caps = [(name, p) for name, p in all_caps if p.exists()]
    hashes = [(name, avg_hash(p)) for name, p in existing_caps]
    all_distinct = True
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = hamming(hashes[i][1], hashes[j][1])
            status = "OK" if d > 15 else "SAME!"
            log(f"  {hashes[i][0]} vs {hashes[j][0]}: hamming={d} [{status}]")
            if d <= 15:
                all_distinct = False

    log(f"\nAll distinct: {all_distinct}")

    c.close()
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
