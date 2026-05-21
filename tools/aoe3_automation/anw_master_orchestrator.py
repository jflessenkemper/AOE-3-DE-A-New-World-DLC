#!/usr/bin/env python3
"""ANW master orchestrator: capture tech tree for all 40 ANW civs.

Per civ:
  1. ensure main menu
  2. Skirmish setup -> select civ at picker_idx
  3. Click Play
  4. Wait for in-game (~2-3 min)
  5. ESC -> click TECHNOLOGY TREE -> screenshot
  6. ESC -> resign -> main menu

Saves to artifacts/validation/visual_art/ANW{Civ}/full/05_tech_tree.png

Picker indexes for ANW civs are EMPIRICALLY derived. The current
picker_scroll_table.json is stale; this script builds its own table by
scanning each scroll step until a desired civ is on screen, then caches.

Usage:
  python3 anw_master_orchestrator.py             # all 40 civs
  python3 anw_master_orchestrator.py --civs Dutch,French,German
  python3 anw_master_orchestrator.py --resume    # skip civs with existing capture
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from in_game_driver import (
    GameDriver, _click, _key, _get_xdo_env, _focus_window,
    P1_CIV_FLAG, PICKER_OK, PLAY_BTN, SKIRMISH_BTN,
)
from lobby_driver import screenshot
from anw_civ_picker_map import ANW_TO_PICKER_INDEX

ART_ROOT = Path('artifacts/validation/visual_art')
TC_DEFAULT = (920, 380)
AGE_UP_BTN = (46, 905)
POLITICIAN_1 = (420, 460)
ACCEPT_BTN = (760, 1010)

# ESC menu (1920x1080 gamescope)
ESC_TECH_TREE = (1765, 130)
ESC_RESIGN_Y = 330  # rough
VIEW_POSTGAME = (1245, 760)
QUIT_TOP_LEFT = (50, 30)

# ANW civs (40 total) - matches data/anwhomecity*.xml
ANW_CIVS = [
    "Argentines", "Aztecs", "Barbary", "Brazil", "British",
    "Canadians", "Chileans", "Chinese", "Columbians", "Dutch",
    "Egyptians", "Ethiopians", "Finnish", "French", "Germans",
    "Haitians", "Haudenosaunee", "Hausa", "Hungarians", "Inca",
    "Indians", "Indonesians", "Italians", "Japanese", "Lakota",
    "Maltese", "Mayans", "Mexicans", "NapoleonicFrance", "Ottomans",
    "Peruvians", "Portuguese", "RevFrance", "Romanians", "Russians",
    "SouthAfricans", "Spanish", "Swedes", "Texians", "USA",
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def game_alive():
    """Check if AoE3 + gamescope are running."""
    if not Path('/run/user/1000/gamescope-0').exists():
        return False
    r = subprocess.run(['pgrep', '-f', 'AoE3DE_s.exe'],
                       capture_output=True, timeout=5)
    return r.returncode == 0


def relaunch_game(wait_main_menu=True, timeout=240):
    """Relaunch AoE3 via Steam URI. Wait for gamescope socket + main menu."""
    log('  RELAUNCH: launching AoE3 via steam URI')
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    subprocess.Popen(
        ['steam', 'steam://rungameid/933110'],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Wait for game process
    deadline = time.time() + timeout
    while time.time() < deadline:
        if game_alive():
            log('  RELAUNCH: AoE3 process detected')
            break
        time.sleep(3)
    else:
        log('  RELAUNCH: timeout waiting for AoE3 process')
        return False
    if not wait_main_menu:
        return True
    # Wait for main menu (use ensure_main_menu after a settle period)
    log('  RELAUNCH: settling 60s for menu to render')
    time.sleep(60)
    return True


def cheat(phrase, env):
    _key('Return')
    time.sleep(0.5)
    subprocess.run(['xdotool', 'type', '--delay', '40', phrase],
                   env=env, capture_output=True, timeout=10)
    time.sleep(0.2)
    _key('Return')
    time.sleep(0.4)


def has_capture(civ, surface):
    """Return True if surface already captured for this civ."""
    p = ART_ROOT / f'ANW{civ}' / 'full' / surface
    return p.exists() and p.stat().st_size > 100_000


def capture_tech_tree_only(civ, env):
    """In-game: ESC -> TECH TREE -> screenshot."""
    out_dir = ART_ROOT / f'ANW{civ}' / 'full'
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f'  opening ESC menu')
    _key('Escape')
    time.sleep(1.2)
    log(f'  clicking TECHNOLOGY TREE')
    _click(*ESC_TECH_TREE)
    time.sleep(3.0)
    out_path = out_dir / '05_tech_tree.png'
    screenshot(str(out_path))
    log(f'  saved {out_path}')
    # Verify it's tech tree (not save dialog)
    # Back out
    _key('Escape')
    time.sleep(0.8)
    return out_path


def capture_age_ups(civ, env, tc_xy=TC_DEFAULT):
    """Capture all 4 age-up dialogs sequentially."""
    out_dir = ART_ROOT / f'ANW{civ}' / 'full'
    out_dir.mkdir(parents=True, exist_ok=True)
    d = GameDriver()
    d.set_speed(5)
    time.sleep(0.5)

    # Speed-5 + cheats compresses transitions; aggressive waits.
    surfaces = [
        ("15_age_up_colonial.png",    8),
        ("16_age_up_fortress.png",   10),
        ("17_age_up_industrial.png", 12),
        ("18_age_up_imperial.png",   14),
    ]
    for fname, wait_s in surfaces:
        log(f'  cheats for {fname}')
        cheat('medium rare please', env)
        cheat('give me liberty or give me coin', env)
        cheat('nova & orion', env)
        time.sleep(0.3)
        log(f'  clicking TC at {tc_xy}')
        _click(*tc_xy)
        time.sleep(0.7)
        log(f'  clicking AGE-UP at {AGE_UP_BTN}')
        _click(*AGE_UP_BTN)
        time.sleep(1.5)
        out_path = out_dir / fname
        screenshot(str(out_path))
        log(f'  saved {fname}')
        # Confirm advance
        _click(*POLITICIAN_1)
        time.sleep(0.4)
        _click(*ACCEPT_BTN)
        time.sleep(1.0)
        log(f'  waiting {wait_s}s for age transition')
        time.sleep(wait_s)


def resign_and_return(d):
    """Resign, dismiss postgame, return to main menu."""
    log('  resigning...')
    try:
        d.resign(verify_lobby=False)
    except Exception as e:
        log(f'  resign threw {e}')
    time.sleep(5)
    # Dismiss YOU ABANDON YOUR TOWN
    _click(*VIEW_POSTGAME)
    time.sleep(3)
    # Quit out of postgame
    _click(*QUIT_TOP_LEFT)
    time.sleep(3)
    # Ensure main menu via Escape spam
    ok = d.ensure_main_menu(retries=10)
    log(f'  main menu: {ok}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--civs', default=None,
                    help='comma-separated subset (e.g. Dutch,French)')
    ap.add_argument('--resume', action='store_true',
                    help='skip civs with existing 05_tech_tree.png')
    ap.add_argument('--tech-tree-only', action='store_true',
                    help='skip age-up captures (faster)')
    ap.add_argument('--start-from', default=None,
                    help='resume from this civ name onward')
    ap.add_argument('--max-passes', type=int, default=3,
                    help='retry failed civs this many additional passes')
    args = ap.parse_args()

    env = _get_xdo_env()
    d = GameDriver()

    civs = ANW_CIVS
    if args.civs:
        civs = [c.strip() for c in args.civs.split(',') if c.strip()]
    if args.start_from:
        try:
            idx = civs.index(args.start_from)
            civs = civs[idx:]
        except ValueError:
            log(f'WARN: --start-from {args.start_from} not in list')

    log(f'orchestrator: {len(civs)} civs to process')
    log(f'civs: {", ".join(civs)}')

    # Stats
    successes, failures, skipped = [], [], []

    for idx, civ in enumerate(civs):
        log(f'=== [{idx+1}/{len(civs)}] {civ} ===')

        if args.resume and has_capture(civ, '05_tech_tree.png'):
            log(f'  SKIP (already captured)')
            skipped.append(civ)
            continue

        token = f'ANW{civ}'
        picker_idx = ANW_TO_PICKER_INDEX.get(token)
        if picker_idx is None:
            log(f'  FAIL: no picker idx for {token}')
            failures.append(civ)
            continue

        # Crash recovery: relaunch AoE3 if not running
        if not game_alive():
            log(f'  game not alive — relaunching')
            if not relaunch_game(wait_main_menu=True, timeout=240):
                log(f'  FAIL: relaunch failed')
                failures.append(civ)
                continue

        try:
            log(f'  ensure main menu')
            d.ensure_main_menu(retries=5)
            time.sleep(1.5)

            log(f'  start_skirmish picker_idx={picker_idx} (default map)')
            ok = d.start_skirmish(
                p1_civ_idx=picker_idx, map_idx=None,
                difficulty='Hard', speed_tick=5,
            )
            if not ok:
                log(f'  FAIL: start_skirmish returned False')
                failures.append(civ)
                continue

            log(f'  wait_for_in_game (240s timeout)')
            in_game = d.wait_for_in_game(timeout=240, dismiss_errors=True)
            if in_game:
                # Log marker fires when SP mode begins. HUD renders within
                # ~3-15s. Fast-poll instead of fixed sleep — first True wins.
                log(f'  log marker fired — fast HUD poll (10s budget)')
                for i in range(7):  # up to 10.5s
                    if d.is_in_game():
                        log(f'  HUD ready after {i*1.5:.1f}s')
                        break
                    time.sleep(1.5)
                else:
                    log(f'  HUD not ready in 10s — proceeding anyway')
            else:
                log(f'  log marker timed out — HUD poll fallback (90s)')
                hud_ok = False
                for i in range(18):  # up to 90s
                    if d.is_in_game():
                        log(f'  HUD visible after {i*5}s poll')
                        hud_ok = True
                        break
                    time.sleep(5)
                if not hud_ok:
                    log(f'  FAIL: HUD never visible')
                    failures.append(civ)
                    resign_and_return(d)
                    continue

            d.set_speed(5)
            time.sleep(0.5)

            if not args.tech_tree_only:
                log(f'  capture age-ups')
                try:
                    capture_age_ups(civ, env, tc_xy=TC_DEFAULT)
                except Exception as e:
                    log(f'  age-up capture threw {type(e).__name__}: {e}')

            log(f'  capture tech tree')
            try:
                capture_tech_tree_only(civ, env)
            except Exception as e:
                log(f'  tech tree capture threw {type(e).__name__}: {e}')

            log(f'  resign and return')
            resign_and_return(d)
            successes.append(civ)

        except Exception as e:
            log(f'  EXCEPTION {type(e).__name__}: {e}')
            failures.append(civ)
            # Check if game crashed — relaunch if needed
            if not game_alive():
                log(f'  game died in exception — relaunching')
                relaunch_game(wait_main_menu=True, timeout=240)
            else:
                try:
                    resign_and_return(d)
                except Exception:
                    pass

    log('=== SUMMARY ===')
    log(f'success: {len(successes)} ({", ".join(successes)})')
    log(f'failure: {len(failures)} ({", ".join(failures)})')
    log(f'skipped: {len(skipped)} ({", ".join(skipped)})')


if __name__ == '__main__':
    main()
