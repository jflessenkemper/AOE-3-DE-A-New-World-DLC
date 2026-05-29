#!/usr/bin/env python3
"""Deterministic civ-by-civ validation driver.

Runs inside gamescope via xdotool DISPLAY=:1 for input and
``gamescopectl screenshot`` for capture. Designed to be launched as a
background subprocess and logged to JSONL — no LLM involvement at loop time.

Pre-conditions:
- gamescope + AoE3 DE already running (Steam launch options set to wrap)
- Game at the Single Player Skirmish setup screen
- GAMESCOPE_WAYLAND_DISPLAY=gamescope-0

Coordinate basis: 1920×1080 gamescope inner surface. All coords are
game-relative; xdotool DISPLAY=:1 uses them directly.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image

# --- environment ---------------------------------------------------------
# MUST override, not setdefault — host already has WAYLAND_DISPLAY=wayland-0
os.environ["GAMESCOPE_WAYLAND_DISPLAY"] = "gamescope-0"
os.environ["WAYLAND_DISPLAY"] = "gamescope-0"
XDO_ENV = {**os.environ, "DISPLAY": ":1"}

ART = Path("/tmp/aoe_test/civ_matrix_v1")
ART.mkdir(parents=True, exist_ok=True)
(ART / "screens").mkdir(exist_ok=True)
(ART / "loading").mkdir(exist_ok=True)
LOG_PATH = ART / "run.jsonl"


def log(entry: dict) -> None:
    entry["t"] = time.time()
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry), flush=True)


# --- primitives ----------------------------------------------------------
def shot(path: str) -> bool:
    try:
        res = subprocess.run(
            ["gamescopectl", "screenshot", path],
            timeout=15, capture_output=True, text=True,
        )
        time.sleep(0.5)
        exists = Path(path).exists()
        size = Path(path).stat().st_size if exists else 0
        ok = exists and size > 1024
        if not ok:
            log({"event": "shot_failed", "path": path, "rc": res.returncode,
                 "stdout": res.stdout[:200], "stderr": res.stderr[:200],
                 "exists": exists, "size": size})
        return ok
    except Exception as e:
        log({"event": "shot_exception", "error": str(e), "path": path})
        return False


def roi_hash(path: str, region: tuple[int, int, int, int]) -> str:
    img = Image.open(path).convert("RGB").crop(
        (region[0], region[1], region[0] + region[2], region[1] + region[3])
    )
    return hashlib.md5(img.tobytes()).hexdigest()[:16]


def click_xy(x: int, y: int) -> None:
    subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=XDO_ENV, check=False)
    time.sleep(0.15)
    subprocess.run(["xdotool", "click", "1"], env=XDO_ENV, check=False)


def press(key: str) -> None:
    subprocess.run(["xdotool", "key", key], env=XDO_ENV, check=False)


def scroll(direction: str = "down", n: int = 1) -> None:
    btn = "5" if direction == "down" else "4"
    for _ in range(n):
        subprocess.run(["xdotool", "click", btn], env=XDO_ENV, check=False)
        time.sleep(0.08)


def click_verified(x: int, y: int, roi: tuple[int, int, int, int],
                   tag: str, post_sleep: float = 2.5) -> tuple[bool, str, str]:
    before_path = f"/tmp/_{tag}_before.png"
    after_path = f"/tmp/_{tag}_after.png"
    if not shot(before_path):
        return False, "", ""
    before = roi_hash(before_path, roi)
    click_xy(x, y)
    time.sleep(post_sleep)
    if not shot(after_path):
        return False, before, ""
    after = roi_hash(after_path, roi)
    return (before != after), before, after


# --- ROIs (1920×1080) ----------------------------------------------------
ROI_TOP_LABEL = (40, 10, 900, 80)       # detects "SINGLE PLAYER SKIRMISH" / "MULTIPLAYER" / menu tabs
ROI_P1_SLOT = (300, 130, 900, 80)       # player 1's civ slot row (covers civ flag + name)
ROI_SETUP_BODY = (100, 200, 1400, 600)  # general setup body (detects dropdowns opening)
ROI_CENTER = (500, 400, 900, 300)       # loading splash / in-game vs menu


# --- coordinates (Skirmish setup screen, 1920×1080) ----------------------
BACK_BTN = (60, 34)                # "< BACK" top-left
P1_CIV_FLAG = (585, 176)           # click to open civ picker for player 1
PLAY_BTN = (1720, 950)             # bottom-right PLAY button
# Menu button during in-game top-right ~(1880, 20)
IN_GAME_MENU = (1880, 25)
# Resign options vary; Escape → menu pane → click Resign
# After resign: confirm dialog


CIV_LIST_MOD = [
    "ANWNapoleonicFrance", "ANWRevFrance", "ANWAmericans",
    "ANWMexicans", "ANWCanadians",
    "ANWBrazil", "ANWArgentines", "ANWChileans", "ANWPeruvians",
    "ANWColumbians", "ANWHaitians", "ANWIndonesians",
    "ANWSouthAfricans", "ANWFinnish", "ANWHungarians",
    "ANWRomanians", "ANWBarbary", "ANWEgyptians",
    "ANWRioGrande", "ANWMayans", "ANWTexians",
]


def is_main_menu(path: str) -> bool:
    """Heuristic: main menu has warm sky colors in top-right area."""
    img = Image.open(path).convert("RGB")
    r, g, b = img.getpixel((1700, 100))
    return (r > 100 and g > 80 and b < 200 and r > b)


def is_setup_screen(path: str) -> bool:
    """Setup screen has dark wood everywhere, 'SINGLE PLAYER SKIRMISH' text at top."""
    img = Image.open(path).convert("RGB")
    # Center should be dark wood
    r, g, b = img.getpixel((960, 540))
    return (r + g + b) < 150


def ensure_main_menu() -> bool:
    """Press Escape up to 3 times to get back to main menu."""
    for attempt in range(4):
        p = f"/tmp/_state_{attempt}.png"
        if not shot(p):
            return False
        if is_main_menu(p):
            return True
        press("Escape")
        time.sleep(1.5)
    return False


def open_skirmish_setup() -> bool:
    """From main menu, click Skirmish (item 5 of 12) in left nav."""
    # Skirmish button y was (80, 490) on this menu layout per earlier exploration.
    # Verify by checking we land on setup screen.
    for y_try in (490, 475, 505, 460, 520):
        shot("/tmp/_pre_sk.png")
        click_xy(80, y_try)
        time.sleep(3)
        shot("/tmp/_post_sk.png")
        if is_setup_screen("/tmp/_post_sk.png"):
            log({"event": "skirmish_entered", "y": y_try})
            return True
        # Not setup — escape and try next
        press("Escape")
        time.sleep(1.5)
    log({"event": "skirmish_entry_failed"})
    return False


def main() -> int:
    log({"event": "driver_start", "artifact_dir": str(ART)})

    # Phase 0: confirm on setup screen (caller's precondition) OR navigate
    if not shot(str(ART / "00_start.png")):
        log({"event": "fatal_no_screenshot"})
        return 1

    if not is_setup_screen(str(ART / "00_start.png")):
        log({"event": "not_on_setup", "action": "navigating"})
        if not ensure_main_menu():
            log({"event": "fatal_cant_reach_main_menu"})
            return 2
        if not open_skirmish_setup():
            return 3

    baseline = str(ART / "01_setup_baseline.png")
    if not shot(baseline):
        log({"event": "fatal_baseline_shot_failed"})
        return 5
    log({"event": "phase0_anchor_ok",
         "baseline_hash": roi_hash(baseline, ROI_SETUP_BODY)})

    # Phase 1: open civ picker for player 1, iterate civs
    # Click player 1 civ flag → civ picker dialog opens
    ok, before, after = click_verified(
        P1_CIV_FLAG[0], P1_CIV_FLAG[1], ROI_SETUP_BODY,
        "p1_flag_click", post_sleep=2.5,
    )
    log({"event": "p1_flag_click", "verified": ok, "before": before, "after": after})
    if not ok:
        log({"event": "fatal_p1_flag_no_response"})
        return 4

    shot(str(ART / "02_civ_picker_opened.png"))

    # Close picker (Escape) — we've proven it opens, now we'll iterate per civ
    press("Escape")
    time.sleep(1.2)

    # For each mod civ: open picker, find civ (by scrolling/searching), click it,
    # verify selection, screenshot setup.
    # This is harder without knowing civ-row coords. We'll:
    # - Open picker
    # - Screenshot (civ grid visible)
    # - Save it as "<civ>_picker.png" (for later visual inspection)
    # - Close picker
    # Full selection + match-start is Phase 2; not all civs completed in Phase 1.
    for civ in CIV_LIST_MOD:
        tag = civ.replace("ANW", "").lower()
        log({"event": "civ_picker_probe", "civ": civ})
        click_xy(P1_CIV_FLAG[0], P1_CIV_FLAG[1])
        time.sleep(2.0)
        path = str(ART / "screens" / f"{tag}_picker.png")
        if shot(path):
            log({"event": "civ_picker_shot", "civ": civ, "path": path,
                 "hash": roi_hash(path, ROI_SETUP_BODY)})
        press("Escape")
        time.sleep(1.0)

    log({"event": "phase1_complete"})

    # Phase 2: pick one sample civ and run an actual match start.
    # Uses best-effort default civ (whatever is shown in player 1 slot).
    # This is a smoke test for "game loads without XS error dialog".
    shot(str(ART / "03_before_play.png"))
    ok, b, a = click_verified(PLAY_BTN[0], PLAY_BTN[1], ROI_CENTER,
                              "play", post_sleep=5.0)
    log({"event": "play_click", "verified": ok, "before": b, "after": a})

    if ok:
        # Wait for game to load, sample screenshots
        for t in (3, 8, 20, 40):
            time.sleep(max(0, t - (3 if t == 3 else t - 3)))
            p = str(ART / "loading" / f"default_t{t}s.png")
            shot(p)
            log({"event": "loading_sample", "t": t, "path": p})
        # XS error dialog detection
        img = Image.open(str(ART / "loading" / "default_t40s.png")).convert("RGB")
        r, g, b = img.getpixel((960, 500))
        if r + g + b < 90:
            log({"event": "XS_ERROR_DIALOG_DETECTED"})
        else:
            log({"event": "no_xs_error_detected"})
        # Resign
        press("Escape")
        time.sleep(1.5)
        # Click Resign — position approx (960, 400)
        click_xy(960, 400)
        time.sleep(1.5)
        click_xy(960, 500)  # Confirm
        time.sleep(3.0)

    log({"event": "driver_end"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
