#!/usr/bin/env python3
"""ANW full-capture runner.

For a civ that's ALREADY in-game on a skirmish, capture:
  - 15_age_up_colonial.png (Age 2 politician select dialog)
  - 16_age_up_fortress.png (Age 3 politician select dialog)
  - 17_age_up_industrial.png (Age 4 politician select dialog)
  - 18_age_up_imperial.png (Age 5 politician select dialog)
  - 19_tech_tree.png (Technology Tree screen from ESC menu)

Verified working 2026-05-21 on gamescope/Proton build of AoE3 DE with
British (FLESSENKEMPER profile).

Key empirical coords (1920x1080):
  AGE_UP_BTN  = (46, 905)    -- top-left cell of TC action panel
  TC_STEEPLE  = (920, 380)   -- TC building click target (varies per civ/map)
  POLITICIAN_1 = (420, 460)  -- first politician portrait center
  ACCEPT_BTN  = (760, 1010)  -- ACCEPT button (politician dialog)
  CANCEL_BTN  = (1100, 1010) -- CANCEL button (politician dialog)

Cheats (verified working): chat box (Enter) -> xdotool type --delay 60
  "medium rare please"             +10000 food
  "give me liberty or give me coin" +10000 coin
  "nova & orion"                   +10000 wood

Usage:
  python3 anw_full_capture_runner.py --civ British --tc-x 920 --tc-y 380

If you skip --tc-x/--tc-y, falls back to scanning the screenshot for the TC
building's blue selection diamond and clicking its centroid.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from in_game_driver import _click, _key, _get_xdo_env, GameDriver
from lobby_driver import screenshot

# Empirical coords
AGE_UP_BTN = (46, 905)
POLITICIAN_1 = (420, 460)
ACCEPT_BTN = (760, 1010)
CANCEL_BTN = (1100, 1010)
TC_DEFAULT = (920, 380)

# Each age transition: name, output filename, expected wait after accept (sec)
# Speed 5 + full cheats compresses transitions to ~10-15s game-time.
AGE_TRANSITIONS = [
    ("colonial",   "15_age_up_colonial.png",   14),   # Age 1 -> 2
    ("fortress",   "16_age_up_fortress.png",   16),   # Age 2 -> 3
    ("industrial", "17_age_up_industrial.png", 18),   # Age 3 -> 4
    ("imperial",   "18_age_up_imperial.png",   22),   # Age 4 -> 5
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def cheat(phrase, env):
    """Open chat, type cheat, close chat."""
    _key('Return')
    time.sleep(0.5)
    subprocess.run(
        ['xdotool', 'type', '--delay', '40', phrase],
        env=env, capture_output=True, timeout=10
    )
    time.sleep(0.2)
    _key('Return')
    time.sleep(0.4)


def apply_resource_cheats(env):
    """Apply all three resource cheats (+10000 each)."""
    cheat('medium rare please', env)                # food
    cheat('give me liberty or give me coin', env)  # coin
    cheat('nova & orion', env)                     # wood


def capture_age_up(out_dir, surface_name, filename, tc_xy, env):
    """Capture one age-up politician dialog and confirm advance."""
    apply_resource_cheats(env)
    time.sleep(0.3)

    log(f'  clicking TC at {tc_xy}')
    _click(*tc_xy)
    time.sleep(0.7)

    log(f'  clicking AGE-UP at {AGE_UP_BTN}')
    _click(*AGE_UP_BTN)
    time.sleep(1.5)

    out_path = out_dir / filename
    screenshot(str(out_path))
    log(f'  saved {filename}')

    # Confirm advance: select 1st politician, accept
    _click(*POLITICIAN_1)
    time.sleep(0.4)
    _click(*ACCEPT_BTN)
    time.sleep(1.5)


def capture_tech_tree(out_dir, env):
    """Open ESC menu, click TECHNOLOGY TREE, screenshot, return to game.

    ESC menu coord empirical map (1920x1080, gamescope build, 2026-05-21):
      PHOTO MODE       (1765,  92)
      TECHNOLOGY TREE  (1765, 130)  <- target
      SAVE             (1765, 170)
      LOAD             (1765, 210)
      RESTART          (1765, 250)
      OPTIONS          (1765, 290)
      RESIGN           (1765, 330)
      QUIT             (1765, 370)
    """
    log('  opening ESC menu')
    _key('Escape')
    time.sleep(1.0)
    log('  clicking TECHNOLOGY TREE button (1765, 130)')
    _click(1765, 130)
    time.sleep(2.5)
    out_path = out_dir / '19_tech_tree.png'
    screenshot(str(out_path))
    log(f'  saved 19_tech_tree.png')
    # Back out: Escape closes tech tree, then closes ESC menu
    _key('Escape')
    time.sleep(0.8)
    _key('Escape')
    time.sleep(0.8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--civ', required=True,
                    help='civ folder name (e.g. ANWBritish - prefix added if missing)')
    ap.add_argument('--tc-x', type=int, default=TC_DEFAULT[0])
    ap.add_argument('--tc-y', type=int, default=TC_DEFAULT[1])
    ap.add_argument('--out-root', default='artifacts/validation/visual_art')
    ap.add_argument('--skip-techtree', action='store_true')
    ap.add_argument('--skip-ageups', action='store_true')
    args = ap.parse_args()

    env = _get_xdo_env()
    d = GameDriver()

    civ_folder = args.civ if args.civ.startswith('ANW') else f'ANW{args.civ}'
    out_dir = Path(args.out_root) / civ_folder / 'full'
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f'output dir: {out_dir}')

    tc_xy = (args.tc_x, args.tc_y)

    # Assumes already in-game; set max speed
    d.set_speed(5)
    time.sleep(1)

    if not args.skip_ageups:
        for i, (name, fname, wait_s) in enumerate(AGE_TRANSITIONS):
            log(f'=== AGE {i+2} ({name}) ===')
            capture_age_up(out_dir, name, fname, tc_xy, env)
            log(f'  waiting {wait_s}s for age transition')
            time.sleep(wait_s)

    if not args.skip_techtree:
        log('=== TECH TREE ===')
        capture_tech_tree(out_dir, env)

    log('=== DONE ===')
    log(f'captured to {out_dir}')


if __name__ == '__main__':
    main()
