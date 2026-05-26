#!/usr/bin/env python3
"""Per-civ match-start smoke test.

Opens the civ picker, scrolls to each target civ (alphabetical index),
clicks the row, OK, PLAY, screenshots at loading + in-game + t=5s,
checks for XS error dialogs, resigns, loops.

Runs inside gamescope; input via xdotool DISPLAY=:1, screenshot via
gamescopectl.
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

os.environ["GAMESCOPE_WAYLAND_DISPLAY"] = "gamescope-0"
os.environ["WAYLAND_DISPLAY"] = "gamescope-0"
XDO_ENV = {**os.environ, "DISPLAY": ":1"}

ART = Path("/tmp/aoe_test/civ_matrix_v2")
ART.mkdir(parents=True, exist_ok=True)
(ART / "picker").mkdir(exist_ok=True)
(ART / "setup").mkdir(exist_ok=True)
(ART / "loading").mkdir(exist_ok=True)
(ART / "errors").mkdir(exist_ok=True)
LOG_PATH = ART / "run.jsonl"


def log(entry: dict) -> None:
    entry["t"] = time.time()
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry), flush=True)


def shot(path: str) -> bool:
    try:
        res = subprocess.run(["gamescopectl", "screenshot", path],
                             timeout=15, capture_output=True, text=True)
        time.sleep(0.5)
        exists = Path(path).exists()
        size = Path(path).stat().st_size if exists else 0
        ok = exists and size > 1024
        if not ok:
            log({"event": "shot_failed", "rc": res.returncode,
                 "stderr": res.stderr[:200]})
        return ok
    except Exception as e:
        log({"event": "shot_exception", "error": str(e)})
        return False


def hash_roi(path: str, roi: tuple[int, int, int, int]) -> str:
    img = Image.open(path).convert("RGB").crop(
        (roi[0], roi[1], roi[0] + roi[2], roi[1] + roi[3]))
    return hashlib.md5(img.tobytes()).hexdigest()[:16]


def click_xy(x: int, y: int) -> None:
    subprocess.run(["xdotool", "mousemove", str(x), str(y)], env=XDO_ENV)
    time.sleep(0.15)
    subprocess.run(["xdotool", "click", "1"], env=XDO_ENV)


def press(key: str) -> None:
    subprocess.run(["xdotool", "key", key], env=XDO_ENV)


def error_dialog_up(path: str) -> bool:
    img = Image.open(path).convert("RGB")
    r, g, b = img.getpixel((960, 500))
    return (r + g + b) < 90


# ---- Known coordinates (1920×1080 gamescope inner surface) -----
P1_CIV_FLAG = (585, 176)             # click to open civ picker for player 1
PICKER_OK = (336, 976)               # OK button at bottom of picker
PICKER_DECKBUILDER = (544, 976)      # "DECK BUILDER" button
PICKER_CANCEL = (784, 976)           # CANCEL
PICKER_ROW_X = 496                   # x of civ row click (left side of text)
PICKER_ROW_Y0 = 262                  # y of first row (Random Personality)
PICKER_ROW_DY = 61                   # y spacing per row
PLAY_BTN = (1696, 960)               # PLAY on setup screen (setup bottom-right)

# ROIs
ROI_P1_SLOT = (300, 130, 900, 80)    # player 1 civ/flag/name row
ROI_CENTER = (500, 400, 900, 300)
ROI_SETUP_BODY = (100, 200, 1400, 600)


# Target civs to match-test (5 requested earlier).
# Each tuple: (internal_name, display_name_in_picker_list_alphabetical_position_index)
# We'll probe: open picker (random-personality is row 0), compute row index by
# alphabetical position among visible rows, scroll if needed, click.

# Full alphabetical list as visible in picker (from v1 screenshot).
# 'mod_' prefix = our mod civ; otherwise base game.
PICKER_LIST = [
    "Random Personality",              # 0
    "Argentines (Buenos Aires)",       # 1  mod
    "Aztecs (Tenochtitlán)",           # 2
    "Barbary States (Algiers)",        # 3  mod
    "Brazilians (Rio de Janeiro)",     # 4  mod
    "British (London)",                # 5
    "Californians (Sonoma)",           # 6  mod
    "Canadians (Québec)",              # 7  mod
    "Central Americans (Guatemala City)",  # 8  mod
    "Chileans (Santiago)",             # 9  mod
    # continues past visible area — scroll needed
    "Chinese",                         # 10
    "Columbians",                      # 11 mod
    "Dutch",                           # 12
    "Egyptians",                       # 13 mod
    "Ethiopians",                      # 14
    "Finnish",                         # 15 mod
    "French",                          # 16
    "Lower Canada",                    # 17 mod (display name; spec_key remains "French Canadians Papineau Revolution")
    "Germans",                         # 18
    "Haitians",                        # 19 mod
    "Haudenosaunee",                   # 20
    "Hausa",                           # 21
    "Hungarians",                      # 22 mod
    "Inca",                            # 23
    "Indians",                         # 24
    "Indonesians",                     # 25 mod
    "Italians",                        # 26
    "Japanese",                        # 27
    "Lakota",                          # 28
    "Maltese",                         # 29
    "Mayans",                          # 30 mod
    "Mexicans",                        # 31 mod
    "Napoleonic France",               # 32 mod
    "Ottomans",                        # 33
    "Peruvians",                       # 34 mod
    "Portuguese",                      # 35
    "Revolutionary France",            # 36 mod
    "Rio Grande",                      # 37 mod
    "Romanians",                       # 38 mod
    "Russians",                        # 39
    "South Africans",                  # 40 mod
    "Spanish",                         # 41
    "Swedes",                          # 42
    "Texians",                         # 43 mod
    "Baja Californians",               # ??? alphabetically should be near B
    "Yucatan",                         # 45 mod  (alphabetically Y last)
]

# 5 user-requested civs with their alphabetical indices
TARGETS = [
    ("brazil",            4),
    ("central_americans", 8),
    ("romanians",         38),
    ("barbary",           3),
]


def open_picker() -> bool:
    before = "/tmp/_pre_pick.png"
    after = "/tmp/_post_pick.png"
    if not shot(before):
        return False
    b = hash_roi(before, ROI_SETUP_BODY)
    click_xy(*P1_CIV_FLAG)
    time.sleep(2.0)
    if not shot(after):
        return False
    a = hash_roi(after, ROI_SETUP_BODY)
    return b != a


def close_picker_cancel() -> None:
    click_xy(*PICKER_CANCEL)
    time.sleep(1.2)


def scroll_picker_to(idx: int) -> None:
    """Scroll the picker down so that `idx`-th row is visible.

    Visible area holds ~10 rows without scrolling. For idx >= 10, we Page_Down
    in 10-row jumps. Simplest: send many Down-arrows to reach idx.
    """
    # First scroll to top
    for _ in range(60):
        press("Up")
        time.sleep(0.02)
    # Then step down to the target row
    for _ in range(idx):
        press("Down")
        time.sleep(0.03)


def select_civ_by_index(idx: int, tag: str) -> bool:
    # After scrolling with Down arrow, the highlighted row should be the idx-th
    # item. Press Enter (or Space) to confirm. But the picker may need a click
    # instead. Try arrow-navigate + OK click first.
    scroll_picker_to(idx)
    time.sleep(0.5)
    shot(str(ART / "picker" / f"{tag}_highlighted.png"))
    # Click OK
    click_xy(*PICKER_OK)
    time.sleep(2.0)
    return True


def run_match_test(civ_tag: str) -> dict:
    """For one civ: open picker, scroll+select, screenshot setup, click PLAY,
    screenshot loading + in-game, check XS error, resign."""
    result = {"civ": civ_tag, "steps": []}

    # Ensure we're on setup screen (best effort; press Escape a couple times)
    press("Escape"); time.sleep(0.5)
    press("Escape"); time.sleep(0.5)

    if not open_picker():
        result["error"] = "picker_didnt_open"
        return result
    result["steps"].append("picker_opened")

    # Get target index (lookup)
    idx = next((i for t, i in TARGETS if t == civ_tag), None)
    if idx is None:
        result["error"] = "no_idx"
        close_picker_cancel()
        return result

    select_civ_by_index(idx, civ_tag)
    result["steps"].append(f"civ_selected_idx={idx}")

    # After OK, we should be back on setup screen. Screenshot.
    setup_path = str(ART / "setup" / f"{civ_tag}_setup.png")
    shot(setup_path)
    result["setup_shot"] = setup_path

    # Click PLAY
    click_xy(*PLAY_BTN)
    result["steps"].append("play_clicked")
    time.sleep(3.5)

    # Sample loading
    for t in (3, 10, 25, 40):
        p = str(ART / "loading" / f"{civ_tag}_t{t}s.png")
        shot(p)
        result.setdefault("loading", []).append((t, p))
        if t < 40:
            time.sleep((t+3) - time.time() % 1 if False else 3.5)
        else:
            break

    # Check for XS error dialog
    last = str(ART / "loading" / f"{civ_tag}_t40s.png")
    if Path(last).exists() and error_dialog_up(last):
        err_path = str(ART / "errors" / f"{civ_tag}_xs_error.png")
        import shutil as sh
        sh.copy(last, err_path)
        result["xs_error"] = True
        result["xs_error_path"] = err_path
        log({"event": "XS_ERROR_DETECTED", "civ": civ_tag})

    # Resign. Key sequence: Menu (or ESC) → Resign → Confirm.
    # AoE3 default: F10 opens menu, then click Resign, then Yes.
    press("F10")
    time.sleep(1.5)
    shot(str(ART / "loading" / f"{civ_tag}_menu_open.png"))
    # Resign button — try a common position
    click_xy(960, 540)  # likely middle of menu panel where a button lives
    time.sleep(1.5)
    click_xy(960, 540)  # confirm
    time.sleep(4.0)

    # If still in-game, force via Escape + click
    press("Escape"); time.sleep(0.5)
    # Attempt "Exit to menu" sequence — not reliable without known coords
    # Last resort: close+relaunch via manage_game.py — slow but deterministic
    # For now, record what we got.

    return result


def main() -> int:
    log({"event": "v2_start"})

    # Enumerate target civs
    for civ_tag, idx in TARGETS:
        log({"event": "civ_start", "civ": civ_tag, "idx": idx})
        try:
            r = run_match_test(civ_tag)
            log({"event": "civ_result", **r})
        except Exception as e:
            log({"event": "civ_crashed", "civ": civ_tag, "error": str(e)})
        # Between civs, try to ensure we're at setup. If lost, break out.
        shot("/tmp/_state_check.png")
        try:
            img = Image.open("/tmp/_state_check.png").convert("RGB")
            c = img.getpixel((960, 540))
            if sum(c) > 200:  # too bright = probably main menu
                log({"event": "back_at_menu_navigating_to_setup"})
                # Click Skirmish again
                click_xy(80, 490)
                time.sleep(3.0)
        except Exception:
            pass

    log({"event": "v2_end"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
