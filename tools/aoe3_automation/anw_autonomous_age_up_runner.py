#!/usr/bin/env python3
"""Autonomous age-up screenshot runner.

Drives an AoE3 DE skirmish from the main menu through 4 age-ups, capturing
the politician selection dialog at each transition. Designed to be run
without a human at the keyboard, but logs every step so failures are
recoverable.

Pre-condition: AoE3 DE running. If currently in a match, the script will
resign cleanly first. Designed for the Bazzite/Proton/gamescope rig.

Usage
-----
    python3 tools/aoe3_automation/anw_autonomous_age_up_runner.py --civ ANWBritish

Caveats
-------
- The TC age-up button position is empirically discovered via pixel probe.
  If the action panel layout differs from the assumed 1920x1080 grid, the
  script logs the failure and exits without forcing wrong clicks.
- "this is too hard" cheat is used to grant resources; developer mode in
  user.cfg must be active. (It is, per current rig setup.)
- Politician selection dialog buttons: the script clicks the LEFT-most
  politician (column 1) which is always present at every age.
- Imperial (Age 5) may be unreachable in a 5-min budget on Hard difficulty;
  this is logged as a partial outcome (Colonial/Fortress/Industrial
  captured, Imperial skipped) rather than a hard failure.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from PIL import Image

from tools.aoe3_automation import lobby_driver  # noqa: E402
from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX  # noqa: E402
from tools.aoe3_automation.in_game_driver import GameDriver, _get_xdo_env  # noqa: E402

# Action panel (where TC actions render when TC is selected) ─ 1920x1080:
#   The action grid is at the bottom-right corner.
#   Grid origin (top-left of grid):   x≈1320, y≈885
#   Cell size:                        72×72 px with ~6px gaps
#   Grid dims:                        5 columns × 3 rows
# Age-up icon, when TC selected and the player is not yet maximally aged:
#   Cell (col=0, row=2)  — bottom-left of the grid
#   Approximate centre:               x≈1356, y≈1029
# This is a probe target; if the icon isn't gold/yellow we abort.
AGE_UP_BTN = (1356, 1029)
AGE_UP_PROBE_BOX = (1320, 1000, 1395, 1060)  # for visual confirmation
GOLD_R_MIN, GOLD_G_MIN, GOLD_B_MAX = 180, 140, 100  # yellow/gold pixel threshold

# Politician select dialog: 5 politicians visible in a horizontal row.
# Each politician card centre y≈540. X positions empirically discovered
# below; we click the LEFT-most card.
POLITICIAN_LEFT = (435, 540)

# Cheat: grants 10000 of each resource (food/wood/gold/XP)
CHEAT_RESOURCES = "this is too hard"

# Map index for "Alaska" (vanilla, stable) — matches anw_visual_capture_runner.py
ALASKA_MAP_IDX = 2

# Surface label → manifest naming
AGE_SURFACES = [
    ("15_age_up_colonial",    "age_up_colonial_select",   2),
    ("16_age_up_fortress",    "age_up_fortress_select",   3),
    ("17_age_up_industrial",  "age_up_industrial_select", 4),
    ("18_age_up_imperial",    "age_up_imperial_select",   5),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _xdo(*args: str) -> None:
    """Direct xdotool wrapper using the in_game_driver's env."""
    subprocess.run(["xdotool", *args], env=_get_xdo_env(), check=False, timeout=8)


def click(x: int, y: int, *, delay: float = 0.3) -> None:
    _xdo("mousemove", str(x), str(y))
    _xdo("click", "1")
    time.sleep(delay)


def key(name: str, n: int = 1) -> None:
    for _ in range(n):
        _xdo("key", name)
        time.sleep(0.06)


def type_text(s: str) -> None:
    _xdo("type", "--delay", "30", s)


def apply_cheat(cheat: str) -> None:
    log(f"applying chat cheat: {cheat!r}")
    key("Return")
    time.sleep(0.6)
    type_text(cheat)
    time.sleep(0.3)
    key("Return")
    time.sleep(1.0)


def probe_age_up_button_active(shot_path: Path) -> bool:
    """Look at the age-up button cell — return True if the icon is the
    typical age-up gold/yellow tint (signalling 'age-up affordable, button
    clickable')."""
    try:
        with Image.open(shot_path) as im:
            crop = im.crop(AGE_UP_PROBE_BOX).convert("RGB")
            px = list(crop.getdata())
            golden = sum(
                1 for (r, g, b) in px
                if r >= GOLD_R_MIN and g >= GOLD_G_MIN and b <= GOLD_B_MAX
            )
            total = len(px)
            ratio = golden / total
            log(f"  age-up icon gold ratio: {ratio:.2%} ({golden}/{total})")
            return ratio > 0.05
    except Exception as e:
        log(f"  probe error: {e}")
        return False


def save_capture(civ: str, label_idx: str, surface_name: str, src: Path) -> None:
    out_dir = REPO / f"artifacts/validation/visual_art/{civ}"
    v2_dir = REPO / f"artifacts/validation/visual_art_v2/{civ}/full"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "crops").mkdir(parents=True, exist_ok=True)
    (out_dir / "thumbs").mkdir(parents=True, exist_ok=True)
    (out_dir / "full").mkdir(parents=True, exist_ok=True)
    v2_dir.mkdir(parents=True, exist_ok=True)

    full_name = f"{label_idx}_{surface_name}.png"
    shutil.copyfile(src, v2_dir / full_name)
    shutil.copyfile(src, out_dir / "full" / full_name)
    shutil.copyfile(src, out_dir / "crops" / f"{surface_name}.png")

    with Image.open(src) as im:
        im = im.convert("RGBA")
        im.thumbnail((320, 320), Image.LANCZOS)
        im.save(out_dir / "thumbs" / f"{surface_name}.webp",
                format="WEBP", quality=82, method=4)
    log(f"  saved capture → {out_dir.relative_to(REPO)}/{full_name}")


def run_age_up_capture(driver: GameDriver, civ: str, target_age: int,
                       label_idx: str, surface_name: str,
                       *, fast: bool = True, probe: bool = True,
                       probe_retries: int = 4, probe_retry_wait: float = 6.0) -> bool:
    """Click TC age-up, capture politician dialog, pick left politician.

    Returns True if dialog captured and a politician picked.
    """
    log(f"--- target age {target_age} ({surface_name}) ---")
    # Verify TC selected and age-up affordable — retry probe up to N times to
    # accommodate older-age transitions which take longer at speed 5.
    if probe:
        last_ratio_active = False
        for attempt in range(1, probe_retries + 1):
            log(f"  H: select TC (attempt {attempt}/{probe_retries})")
            key("H")
            time.sleep(0.5 if fast else 1.2)
            probe_path = Path("/tmp/anw_age_up_probe.png")
            if not lobby_driver.screenshot(probe_path):
                log("  WARN: probe screenshot failed")
                return False
            if probe_age_up_button_active(probe_path):
                last_ratio_active = True
                break
            log(f"  probe not active yet; sleeping {probe_retry_wait}s and retrying")
            time.sleep(probe_retry_wait)
        if not last_ratio_active:
            log(f"  WARN: age-up button never went active after {probe_retries} probes")
            log("         (could mean transition not complete, max age reached, or coord shift)")
            return False
    else:
        log("  H: select TC")
        key("H")
        time.sleep(0.5 if fast else 1.2)
    log(f"  click age-up button at {AGE_UP_BTN}")
    click(*AGE_UP_BTN, delay=1.0 if fast else 2.0)
    # Politician dialog should now be visible. Settle, then capture.
    time.sleep(0.5 if fast else 1.0)
    dialog_path = Path(f"/tmp/anw_age_up_dialog_{target_age}.png")
    if not lobby_driver.screenshot(dialog_path):
        log("  WARN: dialog screenshot failed")
        return False
    save_capture(civ, label_idx, surface_name, dialog_path)
    # Click left-most politician to commit and advance.
    log(f"  click politician at {POLITICIAN_LEFT}")
    click(*POLITICIAN_LEFT, delay=0.6 if fast else 1.5)
    # Wait for age-up animation (cinematic banner at speed 5 = ~10s real time).
    wait = 12 if fast else 45
    log(f"  waiting {wait}s for age transition to complete...")
    time.sleep(wait)
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--civ", default="ANWBritish",
                    help="ANW civ token (default: ANWBritish)")
    ap.add_argument("--max-age", type=int, default=5,
                    help="Stop after reaching this age (default: 5 = Imperial)")
    ap.add_argument("--start-age", type=int, default=2,
                    help="Skip ages below this target (default: 2 = Colonial); use for resume")
    ap.add_argument("--skip-resign", action="store_true",
                    help="Assume game is already at main menu; skip the resign step")
    ap.add_argument("--skip-setup", action="store_true",
                    help="Assume game is already in-game as the target civ; skip menu navigation")
    ap.add_argument("--no-fast", action="store_true",
                    help="Disable per-age fast delays (use conservative 45s waits)")
    ap.add_argument("--no-probe", action="store_true",
                    help="Skip gold-pixel TC age-up button probe (faster but less safe)")
    args = ap.parse_args(argv)

    civ = args.civ
    if civ not in ANW_TO_PICKER_INDEX:
        log(f"ERROR: unknown civ '{civ}'")
        return 2

    picker_idx = ANW_TO_PICKER_INDEX[civ]
    log(f"=== Autonomous age-up runner: {civ} (picker idx {picker_idx}) ===")

    driver = GameDriver(art_dir=Path(f"/tmp/anw_auto_age_up_{civ}"))

    if not args.skip_setup:
        # Step 1: ensure we're not mid-match
        if not args.skip_resign:
            log("step 1: resign any in-progress match")
            if driver.is_in_game():
                log("  game is in-progress; resigning")
                driver.resign(verify_lobby=False)
                time.sleep(3)
            else:
                log("  no active match detected")
        # Step 2: ensure main menu
        log("step 2: ensure main menu")
        driver.ensure_main_menu(retries=5)
        time.sleep(2)
        # Step 3: start skirmish as target civ
        log(f"step 3: start skirmish (p1={civ} idx={picker_idx}, map=alaska)")
        driver.start_skirmish(
            p1_civ_idx=picker_idx,
            map_idx=ALASKA_MAP_IDX,
            difficulty="Hard",
            speed_tick=5,
        )
        # Step 4: wait for in-game
        log("step 4: wait for in-game (timeout 420s)")
        if not driver.wait_for_in_game(timeout=420, dismiss_errors=True):
            log("ERROR: never reached in-game (log marker)")
            return 3
        log("  in-game log-marker fired")
        # CRITICAL: the Age3Log marker fires before the HUD is interactive
        # (Asset Preloading splash can still be on-screen for 30-90s after).
        # Poll is_in_game() (HUD pixel probe) before driving any clicks.
        log("  polling is_in_game() until HUD is visible (timeout 180s)...")
        hud_ok = False
        for poll_i in range(36):  # 36 * 5 = 180s
            if driver.is_in_game():
                hud_ok = True
                log(f"  HUD visible after {poll_i*5}s extra wait")
                break
            time.sleep(5)
        if not hud_ok:
            log("ERROR: HUD never appeared after log marker")
            return 3
        time.sleep(8)  # settle
        # Step 5: max speed + cheats
        driver.set_speed(5)
        apply_cheat(CHEAT_RESOURCES)
        apply_cheat(CHEAT_RESOURCES)  # double-tap = 20000 of each
        time.sleep(2)

    # Step 6: drive 4 age-ups, capturing politician dialog at each
    log("step 6: drive age-ups")
    captured = []
    for label_idx, surface_name, target_age in AGE_SURFACES:
        if target_age > args.max_age:
            log(f"  skipping {surface_name} (target_age {target_age} > max {args.max_age})")
            continue
        if target_age < args.start_age:
            log(f"  skipping {surface_name} (target_age {target_age} < start {args.start_age})")
            continue
        ok = run_age_up_capture(
            driver, civ, target_age, label_idx, surface_name,
            fast=(not args.no_fast),
            probe=(not args.no_probe),
        )
        if ok:
            captured.append(surface_name)
        else:
            log(f"  capture failed for {surface_name}; continuing")

    # Step 7: resign cleanly
    log(f"step 7: resign (captured {len(captured)}/{len(AGE_SURFACES)} age-ups)")
    try:
        driver.resign(verify_lobby=False)
    except Exception as e:
        log(f"  resign error: {e}")

    log("=== done ===")
    log(f"captured: {captured}")
    return 0 if captured else 4


if __name__ == "__main__":
    sys.exit(main())
