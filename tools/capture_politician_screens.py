#!/usr/bin/env python3
"""Fully automated Path-A capture of British politician-selection dialogs.

Launches game → starts skirmish as British → uses cheats to fast-age →
captures 4 politician screens → saves to crops + thumbs + updates manifest.

Usage:
    python3 tools/capture_politician_screens.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Import harness modules
from tools.aoe3_automation import lobby_driver   # screenshot()
from tools.aoe3_automation.in_game_driver import (
    GameDriver, _click, _key, _focus_window, _xdo, _get_xdo_env,
    SKIRMISH_BTN, P1_CIV_FLAG, PICKER_OK, PLAY_BTN,
    GEARS_BTN, ESC_RESIGN, RESIGN_YES, VIEW_POSTGAME, POSTGAME_QUIT,
    SPEED_TICKS, SPEED_BAR_Y,
)

OUT_DIR  = REPO / "artifacts/validation/visual_art/ANWBritish"
V2_DIR   = REPO / "artifacts/validation/visual_art_v2/ANWBritish/full"
MANIFEST = OUT_DIR / "manifest.json"

THUMB_MAX = 320

# In AoE3 DE at 1920x1080:
# - After pressing Home, TC is near center of screen (camera centers on TC)
# - Town Center building center: approximately (960, 490) — center x, slightly
#   above vertical center (AoE3 isometric view places TC slightly upper-center)
# - Age-up button in action panel at bottom:
#   The TC action panel has buttons at y≈945. Age-up is the rightmost button
#   in the first row (~8th button). Typical x range: 540..1020 (8 buttons spaced ~68px)
#   Age-up button is typically at x≈540+(7*68)=1016 or last slot
#   Safe bet: scan positions or use known AoE3 DE layout ~x=1020, y=945
# Reference: AoE3 DE TC panel at 1920×1080 has action buttons at y≈945,
# leftmost at x≈540, spacing ≈68px. Age-up (flag/arrow icon) is last (8th) = x≈1016.
TC_CLICK     = (960, 490)   # click on the TC building (center screen after Home)
AGE_UP_BTN   = (1020, 945)  # Age-up button in TC action panel (rightmost)

# Politician dialog: clicking any politician in the selection.
# In AoE3 DE the age-up politician dialog fills the screen with portraits.
# Typically 3-4 politicians across center ~y=450-550.
# Click near center to hit the first/middle politician:
POLITICIAN_CLICK = (580, 500)   # left-center politician option in dialog

# British civ index in the civ picker (0-based)
BRITISH_CIV_IDX = 5

# Resource cheats (Enter to open chat, type, Enter to confirm)
RESOURCE_CHEATS = [
    "give me liberty or give me coin",  # +10000 gold
    "medium rare please",               # all resources (if supported)
    "a recent fossil",                  # food
    "speed always wins",                # fast build/train
]

# Single reliable cheat confirmed working from verified_coords_british.md:
# "give me liberty or give me coin" → +10000 coin
# Also try "a recent fossil" → food
CHEATS_TO_APPLY = [
    "give me liberty or give me coin",
    "a recent fossil",
]

SURFACES = [
    ("15_age_up_colonial", "age_up_colonial_select",  "Age II — Colonial politicians"),
    ("16_age_up_fortress", "age_up_fortress_select",  "Age III — Fortress politicians"),
    ("17_age_up_industrial","age_up_industrial_select","Age IV — Industrial politicians"),
    ("18_age_up_imperial", "age_up_imperial_select",  "Age V — Imperial politicians"),
]


def log(msg: str) -> None:
    print(f"[politician_capture] {msg}", flush=True)


def write_thumb(src: Path, dest_webp: Path) -> None:
    with Image.open(src) as im:
        im = im.convert("RGBA")
        im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        im.save(dest_webp, format="WEBP", quality=75, method=4)


def type_cheat(cheat: str) -> None:
    """Open chat (Enter), type cheat, confirm (Enter)."""
    _focus_window()
    time.sleep(0.5)
    _xdo("key", "Return")           # open chat
    time.sleep(0.8)
    # Type via xdotool type on the gamescope display
    env = _get_xdo_env()
    subprocess.run(["xdotool", "type", "--delay", "40", cheat], env=env)
    time.sleep(0.5)
    _xdo("key", "Return")           # submit
    time.sleep(1.5)


def apply_resource_cheats() -> None:
    """Apply cheats to give lots of food + coin."""
    log("applying resource cheats")
    for cheat in CHEATS_TO_APPLY:
        log(f"  cheat: {cheat!r}")
        type_cheat(cheat)
    time.sleep(1.0)


def save_surface(label_idx: str, surface_name: str) -> bool:
    """Take screenshot, save crop + thumb + update manifest."""
    V2_DIR.mkdir(parents=True, exist_ok=True)
    full_path = V2_DIR / f"{label_idx}_{surface_name}.png"
    crop_rel  = f"crops/{surface_name}.png"
    thumb_rel = f"thumbs/{surface_name}.webp"
    crop_abs  = OUT_DIR / crop_rel
    thumb_abs = OUT_DIR / thumb_rel
    crop_abs.parent.mkdir(parents=True, exist_ok=True)
    thumb_abs.parent.mkdir(parents=True, exist_ok=True)

    log(f"  screenshotting → {full_path.name}")
    try:
        lobby_driver.screenshot(full_path)
    except Exception as exc:
        log(f"  WARN screenshot failed: {exc}")
        return False

    shutil.copyfile(full_path, crop_abs)
    write_thumb(full_path, thumb_abs)

    # Mirror full into visual_art/full
    mirror = OUT_DIR / "full" / f"{label_idx}_{surface_name}.png"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(full_path, mirror)

    # Update manifest
    mf = json.loads(MANIFEST.read_text(encoding="utf-8"))
    capture_entry = None
    for cap in mf.get("captures", []):
        if cap.get("label") == label_idx:
            capture_entry = cap
            break
    if capture_entry is None:
        capture_entry = {
            "label": label_idx,
            "full_path": f"full/{label_idx}_{surface_name}.png",
            "captured_ms": int(time.time() * 1000),
            "ocr_text": None,
            "crops": [],
        }
        mf.setdefault("captures", []).append(capture_entry)
    else:
        capture_entry["captured_ms"] = int(time.time() * 1000)
        capture_entry["full_path"] = f"full/{label_idx}_{surface_name}.png"

    crop_record = {
        "name": surface_name,
        "crop_region": [0, 0, 1920, 1080],
        "crop_path": crop_rel,
        "thumb_path": thumb_rel,
    }
    found = False
    for i, c in enumerate(capture_entry.get("crops", [])):
        if c.get("name") == surface_name:
            capture_entry["crops"][i] = crop_record
            found = True
            break
    if not found:
        capture_entry.setdefault("crops", []).append(crop_record)

    mf["synthesised"] = False
    mf["status"] = "complete"
    MANIFEST.write_text(json.dumps(mf, indent=2), encoding="utf-8")
    log(f"  saved {surface_name}")
    return True


def click_tc_and_open_age_up() -> None:
    """Press Home to center on TC, click TC, click age-up button."""
    log("pressing Home to center on TC")
    _focus_window()
    _key("Home")
    time.sleep(2.0)

    log(f"clicking TC at {TC_CLICK}")
    _click(*TC_CLICK, delay=1.0)
    # A second click to be sure TC is selected
    _click(*TC_CLICK, delay=1.5)


def select_politician_and_advance() -> None:
    """Click a politician in the selection dialog to age up."""
    log(f"clicking politician at {POLITICIAN_CLICK}")
    _click(*POLITICIAN_CLICK, delay=1.5)


def wait_age_up_done(seconds: int = 45) -> None:
    """Wait for age-up transition to finish."""
    log(f"waiting {seconds}s for age-up to complete")
    time.sleep(seconds)


def main() -> int:
    log("=== British Politician Capture (Path A) ===")

    # ── 1. Launch game ───────────────────────────────────────────────────────
    log("launching game (timeout=120s)")
    rc = subprocess.run(
        [sys.executable,
         str(REPO / "tools/aoe3_automation/manage_game.py"),
         "open", "--timeout", "120"],
        capture_output=False,
    ).returncode
    if rc != 0:
        log(f"FAIL: manage_game.py open returned {rc}")
        return 1
    log("game window detected")
    time.sleep(5)  # extra settle after menu is up

    # ── 2. Start skirmish as British ─────────────────────────────────────────
    log("starting skirmish as British (civ_idx=5)")
    d = GameDriver(art_dir="/tmp/aoe3_politician_capture")
    _focus_window()

    # Navigate to skirmish
    _click(*SKIRMISH_BTN, delay=3.0)

    # Select British for P1 slot
    _click(*P1_CIV_FLAG, delay=1.8)
    _key("Up", n=60, delay=0.03)
    time.sleep(0.3)
    _key("Down", n=BRITISH_CIV_IDX, delay=0.04)
    time.sleep(0.4)
    _click(*PICKER_OK, delay=2.5)

    # Click Play
    _click(*PLAY_BTN, delay=3.0)
    log("play clicked; waiting for in-game...")

    # ── 3. Wait for game to load ──────────────────────────────────────────────
    ok = d.wait_for_in_game(timeout=200)
    if not ok:
        log("FAIL: timed out waiting for in-game state")
        subprocess.run([sys.executable,
                        str(REPO / "tools/aoe3_automation/manage_game.py"), "close"])
        return 2
    log("in-game confirmed")
    time.sleep(5)  # let initial UI settle

    # Set game speed to max
    d.set_speed(5)
    time.sleep(1.0)

    # ── 4. Apply cheats for resources ─────────────────────────────────────────
    apply_resource_cheats()
    # Apply multiple times to get enough for all ages
    apply_resource_cheats()
    apply_resource_cheats()

    # ── 5. Age I → Colonial (Age II): click TC → age-up button → screenshot ──
    log("=== AGE UP 1: Colonial ===")
    # Press Home to center on TC
    click_tc_and_open_age_up()
    # Click the age-up button (in action panel at bottom)
    log(f"clicking age-up button at {AGE_UP_BTN}")
    _click(*AGE_UP_BTN, delay=2.0)

    # Wait for politician selection dialog to appear
    time.sleep(3.0)
    log("=== CAPTURING age_up_colonial_select ===")
    save_surface("15_age_up_colonial", "age_up_colonial_select")

    # Click a politician to proceed
    select_politician_and_advance()
    wait_age_up_done(30)  # Colonial age-up is relatively fast

    # More cheats
    apply_resource_cheats()
    apply_resource_cheats()

    # ── 6. Colonial → Fortress (Age III) ─────────────────────────────────────
    log("=== AGE UP 2: Fortress ===")
    click_tc_and_open_age_up()
    _click(*AGE_UP_BTN, delay=2.0)
    time.sleep(3.0)
    log("=== CAPTURING age_up_fortress_select ===")
    save_surface("16_age_up_fortress", "age_up_fortress_select")
    select_politician_and_advance()
    wait_age_up_done(30)

    # More cheats
    apply_resource_cheats()
    apply_resource_cheats()

    # ── 7. Fortress → Industrial (Age IV) ────────────────────────────────────
    log("=== AGE UP 3: Industrial ===")
    click_tc_and_open_age_up()
    _click(*AGE_UP_BTN, delay=2.0)
    time.sleep(3.0)
    log("=== CAPTURING age_up_industrial_select ===")
    save_surface("17_age_up_industrial", "age_up_industrial_select")
    select_politician_and_advance()
    wait_age_up_done(30)

    # More cheats
    apply_resource_cheats()
    apply_resource_cheats()

    # ── 8. Industrial → Imperial (Age V) ─────────────────────────────────────
    log("=== AGE UP 4: Imperial ===")
    click_tc_and_open_age_up()
    _click(*AGE_UP_BTN, delay=2.0)
    time.sleep(3.0)
    log("=== CAPTURING age_up_imperial_select ===")
    save_surface("18_age_up_imperial", "age_up_imperial_select")
    # No need to age up after this

    # ── 9. Close game ─────────────────────────────────────────────────────────
    log("closing game")
    subprocess.run([sys.executable,
                    str(REPO / "tools/aoe3_automation/manage_game.py"), "close"])

    # ── 10. Verify output ──────────────────────────────────────────────────────
    log("=== Results ===")
    for label_idx, surface_name, label in SURFACES:
        crop = OUT_DIR / "crops" / f"{surface_name}.png"
        thumb = OUT_DIR / "thumbs" / f"{surface_name}.webp"
        size = crop.stat().st_size if crop.exists() else 0
        status = "OK" if size > 1000 else "MISSING"
        log(f"  {status} {surface_name}: {size} bytes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
