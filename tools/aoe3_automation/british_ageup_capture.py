#!/usr/bin/env python3
"""Capture British age-up politician dialog screenshots for release readiness site.

Saves:
  08_ageup_age2.png  — Age II (Colonial) politician selection dialog
  08_ageup_age3.png  — Age III (Fortress)
  08_ageup_age4.png  — Age IV (Industrial)
  08_ageup_age5.png  — Age V (Imperial)

Output: artifacts/validation/visual_art/ANWBritish/full/
"""

import sys
import time
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.aoe3_automation import lobby_driver
from tools.aoe3_automation.in_game_driver import (
    _click, _key, _focus_window, GameDriver,
)
from tools.aoe3_automation.anw_autonomous_age_up_runner import (
    AGE_UP_BTN, POLITICIAN_LEFT, CHEAT_RESOURCES,
    apply_cheat, probe_age_up_button_active, log,
)

OUT = REPO / "artifacts/validation/visual_art/ANWBritish/full"
OUT.mkdir(parents=True, exist_ok=True)

# Age-up target mapping: (target_age, output_filename)
AGE_TARGETS = [
    (2, "08_ageup_age2.png"),
    (3, "08_ageup_age3.png"),
    (4, "08_ageup_age4.png"),
    (5, "08_ageup_age5.png"),
]

ALASKA_MAP_IDX = 2
BRITISH_CIV_IDX = 7


def capture_age_up_dialog(target_age: int, out_name: str) -> bool:
    """Press H, click age-up button, capture dialog, pick politician."""
    log(f"--- Age {target_age}: {out_name} ---")

    # Probe age-up button is available
    for attempt in range(1, 5):
        log(f"  H: select TC (attempt {attempt}/4)")
        _key("h")
        time.sleep(0.8)
        probe = Path(f"/tmp/ageup_probe_{target_age}.png")
        lobby_driver.screenshot(probe)
        if probe_age_up_button_active(probe):
            log("  probe: age-up button is ACTIVE")
            break
        log(f"  probe not active yet; sleeping 6s...")
        time.sleep(6.0)
    else:
        log(f"  WARN: age-up button never active for age {target_age}")
        return False

    # Click the age-up button
    log(f"  clicking age-up at {AGE_UP_BTN}")
    _click(*AGE_UP_BTN, delay=1.5)
    time.sleep(1.5)

    # Capture dialog
    dialog_tmp = Path(f"/tmp/ageup_dialog_{target_age}.png")
    lobby_driver.screenshot(dialog_tmp)

    # Save to output
    out_path = OUT / out_name
    shutil.copy(dialog_tmp, out_path)
    log(f"  saved: {out_path.name} ({out_path.stat().st_size // 1024}KB)")

    # Click left politician to advance
    log(f"  clicking politician at {POLITICIAN_LEFT}")
    _click(*POLITICIAN_LEFT, delay=1.0)

    # Wait for age transition (at speed 5)
    log("  waiting 15s for age transition...")
    time.sleep(15)

    # Apply cheats again to ensure resources for next age
    apply_cheat(CHEAT_RESOURCES)
    time.sleep(2)

    return True


def main():
    log("=== British age-up capture ===")
    log(f"Output: {OUT}")

    driver = GameDriver(art_dir=Path("/tmp/british_ageup"))

    # Start from main menu (assumes we're already there)
    log("Starting British skirmish...")
    driver.start_skirmish(
        p1_civ_idx=BRITISH_CIV_IDX,
        map_idx=ALASKA_MAP_IDX,
        difficulty="Hard",
        speed_tick=5,
    )

    log("Waiting for in-game (timeout 420s)...")
    if not driver.wait_for_in_game(timeout=420, dismiss_errors=True):
        log("ERROR: never reached in-game")
        return 3

    log("Polling for HUD visibility...")
    for i in range(36):
        if driver.is_in_game():
            log(f"HUD visible after {i*5}s")
            break
        time.sleep(5)
    else:
        log("ERROR: HUD never appeared")
        return 3

    time.sleep(8)

    # Set max speed and apply resources cheat
    driver.set_speed(5)
    apply_cheat(CHEAT_RESOURCES)
    apply_cheat(CHEAT_RESOURCES)  # double = 20000 each
    time.sleep(2)

    captured = []
    for target_age, out_name in AGE_TARGETS:
        ok = capture_age_up_dialog(target_age, out_name)
        if ok:
            captured.append(out_name)
        else:
            log(f"  FAILED: {out_name} - moving on")

    log(f"=== Done: captured {len(captured)}/{len(AGE_TARGETS)} ===")
    for c in captured:
        log(f"  PASS: {c}")
    for _, n in AGE_TARGETS:
        if n not in captured:
            log(f"  FAIL: {n}")

    log("Resigning...")
    try:
        driver.resign(verify_lobby=False)
    except Exception as e:
        log(f"resign error: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
