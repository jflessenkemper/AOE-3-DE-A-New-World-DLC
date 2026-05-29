#!/usr/bin/env python3
"""ally_all.py — set every AI opponent to Ally via xdotool (no ei_inject).

Why this exists
---------------
The original ``ally_all.sh`` piped events into ``ei_inject``, which requires
``LIBEI_SOCKET=gamescope-0-ei`` to be exposed on this host. That socket
is **not** present under the current gamescope build:

    $ ls /run/user/1000/gamescope-* 2>/dev/null
    (no -ei socket)

But we *do* have an xdotool path that reaches the AoE3 nested Xwayland —
the same one ``in_game_driver._xdo`` / ``lobby_driver.click`` use every
day. So this script just replays the original ally_all flow over xdotool.

What it does
------------
1. Focus the AoE3 game window (xdotool windowactivate).
2. Press **Alt+D** (stock AoE3 DE Diplomacy hotkey).
3. For each opponent row, click the Ally column toggle.
4. Press Escape to close the panel.

Coordinates
-----------
Default ALLY_X / ROW0_Y / ROW_DY values are inherited verbatim from
``ally_all.sh`` (1180 / 380 / 58 on a 1920x1080 gamescope surface).
They may need calibration for the current build — pass overrides via
``--ally-x``, ``--row0-y``, ``--row-dy``.

Usage
-----
    python3 tools/aoe3_automation/ally_all.py            # 7 opponents
    python3 tools/aoe3_automation/ally_all.py -n 3       # 3 opponents
    python3 tools/aoe3_automation/ally_all.py --dry-run  # print only

This script does NOT launch the game or open the lobby; it expects the
match to already be in-game. Run it once at match start (e.g. from a
TodoWrite "post game start" step or the user pressing Enter when ready).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Reuse the proven xdotool helpers from in_game_driver.
_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR.parent.parent))  # repo root for imports

from tools.aoe3_automation.in_game_driver import (  # noqa: E402
    _xdo, _click, _key, _focus_window, _get_xdo_env,
)

# ─── Defaults (calibrate for current build if needed) ───────────────────────

DEFAULT_OPPONENTS = 7      # 8-player FFA → 7 AI opponents
DEFAULT_ALLY_X    = 1180   # x of the Ally column toggle (1920x1080)
DEFAULT_ROW0_Y    = 380    # y of first opponent row
DEFAULT_ROW_DY    = 58     # pixel pitch between rows
DEFAULT_CONFIRM_X = 960    # OK/confirm button (centred)
DEFAULT_CONFIRM_Y = 960

# Pause between substeps. We're kinder than ally_all.sh's 30 ms — clicks
# need to settle inside gamescope's compositor or they merge into one event.
STEP_PAUSE = 0.08          # generic between-step wait
PANEL_OPEN_PAUSE = 0.45    # wait for diplomacy panel to slide in
ROW_CLICK_PAUSE = 0.12     # wait between ally row clicks
CONFIRM_PAUSE = 0.25       # wait after confirm
CLOSE_PAUSE = 0.15         # wait after Escape


def _press_alt_d() -> None:
    """Press Alt+D to open the Diplomacy panel.

    xdotool's `key` directive supports modifier+key combos via "alt+d".
    We use that form for atomic delivery; if the panel doesn't open on
    one shot, caller can retry by re-running.
    """
    _xdo("key", "alt+d")
    time.sleep(PANEL_OPEN_PAUSE)


def _set_ally_row(row_index: int, ally_x: int, row0_y: int, row_dy: int) -> None:
    """Click the Ally toggle in the Nth opponent row (0-indexed)."""
    y = row0_y + row_index * row_dy
    _click(ally_x, y, delay=ROW_CLICK_PAUSE)


def _confirm_and_close(confirm_x: int, confirm_y: int) -> None:
    """Click OK (if present) and press Escape to close the panel.

    Some skirmish flavours have an explicit OK button on the diplomacy
    panel; some don't. Clicking blank space is harmless — gamescope
    discards clicks that don't hit a UI element.
    """
    _click(confirm_x, confirm_y, delay=CONFIRM_PAUSE)
    _xdo("key", "Escape")
    time.sleep(CLOSE_PAUSE)


def ally_all(
    *,
    opponents: int = DEFAULT_OPPONENTS,
    ally_x: int = DEFAULT_ALLY_X,
    row0_y: int = DEFAULT_ROW0_Y,
    row_dy: int = DEFAULT_ROW_DY,
    confirm_x: int = DEFAULT_CONFIRM_X,
    confirm_y: int = DEFAULT_CONFIRM_Y,
    dry_run: bool = False,
) -> int:
    """Execute the ally-all flow.

    Returns 0 on success, non-zero if the game window can't be focused.
    """
    if dry_run:
        print(f"[DRY] would focus window, press Alt+D, then click Ally at:")
        for i in range(opponents):
            y = row0_y + i * row_dy
            print(f"[DRY]   row {i+1}: ({ally_x}, {y})")
        print(f"[DRY] then click OK at ({confirm_x}, {confirm_y}) and press Escape")
        return 0

    # Sanity check: xdotool must be present, and the AoE3 window
    # must be searchable.
    env = _get_xdo_env()
    r = subprocess.run(
        ["xdotool", "search", "--name", "Age of Empires"],
        env=env, capture_output=True, text=True,
    )
    wids = [w.strip() for w in r.stdout.splitlines() if w.strip()]
    if not wids:
        print("[err] no AoE3 window found via xdotool. Is the game running and "
              "in-game (not at the menu)?", file=sys.stderr)
        return 2

    print(f"[ally_all] focusing window {wids[0]}")
    _focus_window()
    time.sleep(STEP_PAUSE)

    print(f"[ally_all] opening diplomacy panel (Alt+D)")
    _press_alt_d()

    print(f"[ally_all] clicking Ally on {opponents} opponent rows")
    for i in range(opponents):
        _set_ally_row(i, ally_x, row0_y, row_dy)

    print(f"[ally_all] confirming + closing panel")
    _confirm_and_close(confirm_x, confirm_y)

    print(f"[ally_all] done — verify diplomacy state in HUD")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--opponents", type=int, default=DEFAULT_OPPONENTS,
                    help=f"number of AI opponents to ally (default {DEFAULT_OPPONENTS})")
    ap.add_argument("--ally-x", type=int, default=DEFAULT_ALLY_X,
                    help=f"x coord of Ally toggle column (default {DEFAULT_ALLY_X})")
    ap.add_argument("--row0-y", type=int, default=DEFAULT_ROW0_Y,
                    help=f"y coord of first opponent row (default {DEFAULT_ROW0_Y})")
    ap.add_argument("--row-dy", type=int, default=DEFAULT_ROW_DY,
                    help=f"pixel pitch between rows (default {DEFAULT_ROW_DY})")
    ap.add_argument("--confirm-x", type=int, default=DEFAULT_CONFIRM_X,
                    help=f"x coord of OK button (default {DEFAULT_CONFIRM_X})")
    ap.add_argument("--confirm-y", type=int, default=DEFAULT_CONFIRM_Y,
                    help=f"y coord of OK button (default {DEFAULT_CONFIRM_Y})")
    ap.add_argument("--dry-run", action="store_true",
                    help="print planned actions without injecting input")
    args = ap.parse_args()

    return ally_all(
        opponents=args.opponents,
        ally_x=args.ally_x,
        row0_y=args.row0_y,
        row_dy=args.row_dy,
        confirm_x=args.confirm_x,
        confirm_y=args.confirm_y,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
