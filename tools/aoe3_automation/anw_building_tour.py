#!/usr/bin/env python3
"""ANW building-tour capture — cheat-build the full civ building set and
screenshot every building's command card (menu of trainable units / actions).

WHY THIS EXISTS
---------------
The user asked: "I'll need a screenshot of every british building selected so
I can see every building menu and every troop or actions the british can do
with their buildings."  This module cheat-builds each buildable structure,
selects it, and captures its command card to
``artifacts/validation/visual_art/<civ>/buildings/building_<name>.png``.

KEY DESIGN WIN (build menu is ONE grid, not N scattered icons)
--------------------------------------------------------------
Verified from base_data/proto.xml (Settler id=284, page="6"): EVERY buildable
structure lives on a single build-menu page whose icons sit at fixed COLUMN
slots 0..19 in a horizontal grid.  So calibration is reduced to TWO numbers —
the on-screen X of column 0 and the per-column X pitch — plus the row Y.  Once
those are measured on a live game, all 20 column positions are derived.  We do
NOT need to hand-calibrate 16 separate icon coordinates.

  proto.xml page-6 column -> representative building (British-buildable subset):
    col 0  Manor (British house)      col 10 Church
    col 2  Market                     col 11 Barracks
    col 3  Mill / Farm                col 12 Stable
    col 4  Plantation (Estate)        col 13 Artillery Foundry
    col 5  Dock                       col 14 Arsenal
    col 6  Outpost                    col 17 Capitol      (Age 5)
    col 7  Trading Post               col 18 Town Center  (Age 2+)
    col 8  Wall                       col 19 Native Embassy
  (col 1/9/15/16 = native/Dutch/other-culture houses & banks British can't build)

CALIBRATION STATUS (2026-06-06): the build command-card grid (BUILD_CARD_COLS_X
/ BUILD_CARD_ROWS_Y), SETTLER_XY, and PLACEMENT_SPOTS are VERIFIED LIVE on the
Alaska start (clicking cell (40,815) entered placement mode).  The weak point is
villager re-selection after a settler walks off to build — see _select_settler.
All plumbing (cheat-build, select, screenshot via harness/gamescopectl) reuses
the already-proven helpers from in_game_driver / anw_full_capture_runner.

This module performs NO cursor-grabbing — clicks route through the AOE3DEHarness
control socket (or the xdotool fallback inside the gamescope nested Xwayland),
never the user's real desktop cursor.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_automation.in_game_driver import (  # noqa: E402
    _click,
    _rclick,
    _key,
    _focus_window,
    _screenshot_raw,
    _get_xdo_env,
    set_harness_backend,
)
from tools.aoe3_harness.harness_client import HarnessClient, HarnessConnectionError
from tools.aoe3_automation import lobby_driver as _ld

# ---------------------------------------------------------------------------
# Build command-card geometry  — VERIFIED LIVE 2026-06-06 (1920x1080)
# ---------------------------------------------------------------------------
# CORRECTION to the earlier "single row of 20" model: AoE3 DE does NOT use a
# build hotkey.  Selecting a Settler immediately shows the build icons as a
# 5-column x 4-row grid in the bottom-left command card.  Clicking an icon
# enters placement mode (a footprint ghost follows the cursor; red = invalid
# ground, e.g. on trees); one click on valid open ground commits the build.
# The proto.xml page-6 "column" index is the logical build-list slot, NOT the
# command-card cell — so we iterate the visible grid cells directly and read
# each building's identity from its on-screen name after placing + selecting.
#
# Verified: clicking grid cell (row0,col0) = (40, 815) entered placement mode.
BUILD_CARD_COLS_X = [40, 95, 151, 206, 262]   # 5 column centres (px)
BUILD_CARD_ROWS_Y = [815, 873, 931, 989]      # 4 row centres (px)

# Settler select point.  VERIFIED this game at (960, 741) — the start-of-match
# villager cluster below the Town Center.  NOTE: this is map-position-specific;
# a robust select needs an idle-villager hotkey or click-on-TC-then-villager.
# For the Alaska start used by the visual runner the cluster lands here.
SETTLER_XY = (960, 741)

# Where to drop each placed building so footprints don't overlap.  Open grass
# spots near the start base (avoid the tree line centre-left and the TC centre).
# VERIFIED start camera = `Home` key centres on the Town Center.
PLACEMENT_SPOTS = [
    (700, 820), (820, 860), (1060, 830), (1190, 800), (1310, 770),
    (600, 700), (520, 880), (1120, 920), (1260, 900), (700, 930),
    (920, 900), (1160, 700), (1360, 860), (470, 760), (1410, 720),
    (560, 970), (1000, 690), (760, 690), (1240, 980), (900, 980),
]

# AoE3 DE has NO build hotkey — kept for back-compat but unused.
BUILD_HOTKEY = None

# Build-card grid cells, iterated row-major (top-left first).  Identity of the
# building in each cell is read from the on-screen unit name AFTER it is placed
# and selected — we do NOT pre-map cell->building (the command-card ordering is
# the engine's, not proto.xml's page-6 column order).
def _grid_cells() -> list[tuple[int, int]]:
    return [(x, y) for y in BUILD_CARD_ROWS_Y for x in BUILD_CARD_COLS_X]


# Verified cheats (anw_full_capture_runner.py:64-81 + verified_coords_british).
RESOURCE_CHEATS = [
    "medium rare please",                 # +food
    "give me liberty or give me coin",    # +coin
    "nova & orion",                       # +wood
]
BUILD_SPEED_CHEAT = "speed always wins"   # faster construction/training
BUILD_WAIT = 18.0   # sec to let a sped-up structure finish before selecting


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _cheat(phrase: str, env: dict) -> None:
    """Open chat, type a cheat, send.  Pattern from anw_full_capture_runner."""
    _key("Return")
    time.sleep(0.5)
    subprocess.run(
        ["xdotool", "type", "--delay", "40", phrase],
        env=env, capture_output=True, timeout=10,
    )
    time.sleep(0.2)
    _key("Return")
    time.sleep(0.4)


def _apply_resource_cheats(env: dict) -> None:
    for phrase in RESOURCE_CHEATS:
        _cheat(phrase, env)


# TC command-card position for "Train Settler" button.
# Verified: TC is selected by clicking (960, 500) after Home-key recentre.
# "Train Settler" is the first cell (col 0, row 0) of the TC command card.
_TC_XY = (960, 500)
_TC_TRAIN_SETTLER_XY = (BUILD_CARD_COLS_X[0], BUILD_CARD_ROWS_Y[0])  # (40, 815)
_SETTLER_CLUSTER_XY = (960, 741)   # kept for first-select (same as SETTLER_XY)
_FRESH_SETTLER_TRAIN_WAIT = 3.0    # seconds with speed-always-wins cheat active


def _select_settler(*, retrain: bool = False) -> None:
    """Select a settler to surface the build command card.

    If retrain=False (first building): directly click the start-of-match
    settler cluster at _SETTLER_CLUSTER_XY.

    If retrain=True (2nd+ building): recenter camera with Home key, click TC,
    train a fresh settler, then select it.  Robust to the previous settler
    having walked off to build.

    Strategy verified in IMPLEMENTATION_PLAN.md §2b:
      Home -> TC click -> Train Settler (cell 0,0) -> wait -> click cluster.
    The idle-villager hotkey (H) is explicitly documented as NOT working in
    this build (verified_coords_british.md line 152).
    """
    _focus_window()
    if not retrain:
        _click(*_SETTLER_CLUSTER_XY, delay=0.3)
        return
    # Re-center camera on TC with Home key
    _key("Home")
    time.sleep(1.5)
    # Select TC
    _click(*_TC_XY, delay=0.5)
    time.sleep(0.4)
    # Train a fresh settler (cell 0,0 of TC command card)
    _click(*_TC_TRAIN_SETTLER_XY, delay=0.4)
    time.sleep(_FRESH_SETTLER_TRAIN_WAIT)   # wait for production with cheat
    # Click the settler cluster area where the fresh settler appears
    _click(*_SETTLER_CLUSTER_XY, delay=0.3)


def run_building_tour(civ_token: str, out_root: Path, *, age_up: bool = True) -> int:
    """Build each command-card structure and screenshot its selected card.

    Iterates the 5x4 build grid: select villager -> click cell -> place on open
    ground -> wait for (sped-up) construction -> select the built structure ->
    screenshot.  Output goes to <out_root>/<civ_token>/full/building_{i:02d}.png,
    matching the validator's expectation (full/ directory, building_*.png pattern).

    Also captures build_command_card.png from the settler's full build grid BEFORE
    any buildings are placed.

    Per-civ expected building count is read from capture_profile so this function
    knows when the tour has satisfied the profile (the loop still iterates all grid
    cells; the count check is for logging only).

    Returns the number of building command-card screenshots captured.
    """
    from tools.aoe3_automation.capture_profile import expected_building_filenames
    expected = expected_building_filenames(civ_token)
    _log(f"civ={civ_token}  expected buildings from profile: {len(expected)}")

    env = _get_xdo_env()
    # Output to full/ so the validator picks up building_*.png alongside core surfaces
    buildings_dir = out_root / civ_token / "full"
    buildings_dir.mkdir(parents=True, exist_ok=True)

    if not PLACEMENT_SPOTS:
        _log("ABORT: no PLACEMENT_SPOTS configured.")
        return 0

    _focus_window()
    _log("applying resource + build-speed cheats")
    _apply_resource_cheats(env)
    _cheat(BUILD_SPEED_CHEAT, env)

    # ── Capture the full build command card BEFORE any placement ────────────
    # Settler is at the start-of-match cluster; no retrain needed yet.
    _select_settler(retrain=False)
    time.sleep(0.4)
    bcc_path = buildings_dir / "build_command_card.png"
    if _screenshot_raw(bcc_path):
        _log(f"  build_command_card.png saved -> {bcc_path}")
    else:
        _log("  WARNING: build_command_card.png screenshot failed")

    cells = _grid_cells()
    captured = 0
    for i, cell in enumerate(cells):
        if i >= len(PLACEMENT_SPOTS):
            break
        spot = PLACEMENT_SPOTS[i]
        _log(f"cell {i} {cell} -> place at {spot}")

        # First building: settler is still at cluster. Subsequent buildings:
        # the previous settler walked off; retrain a fresh one from TC.
        _select_settler(retrain=(i > 0))
        time.sleep(0.4)
        _click(*cell, delay=0.4)              # pick the build icon (placement mode)
        time.sleep(0.4)
        _click(*spot, delay=0.8)              # commit placement on open ground
        time.sleep(BUILD_WAIT)                # let the sped-up structure finish

        _focus_window()
        _click(*spot, delay=0.6)              # select the built structure
        time.sleep(0.6)

        # Save to full/ with numeric index; validator counts building_*.png files
        out_path = buildings_dir / f"building_{i:02d}.png"
        if _screenshot_raw(out_path):
            _log(f"  saved {out_path.name}")
            captured += 1
        else:
            _log(f"  screenshot FAILED for cell {i}")

        # Cancel any leftover placement-mode ghost via right-click on open
        # ground. Right-click cancels the ghost if active; if no ghost is
        # pending it is a harmless move-order on empty ground. Never opens
        # the ESC menu (unlike Escape). _rclick is verified in
        # in_game_driver.py:367-389 and harness_client.py:514-529.
        _rclick(*spot, delay=0.3)

    _log(f"building tour done: {captured}/{len(cells)} cells captured "
         f"(profile expects {len(expected)})")
    return captured


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--civ", default="ANWBritish", help="ANW civ token (default ANWBritish)")
    p.add_argument("--out", default="artifacts/validation/visual_art",
                   help="Output root (relative to repo root)")
    p.add_argument("--no-age-up", action="store_true",
                   help="Do not age up; only build current-age structures.")
    args = p.parse_args()

    out_root = Path(args.out)
    if not out_root.is_absolute():
        out_root = _REPO_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)

    # Register the harness backend so _screenshot_raw() uses the reliable
    # compositor-framebuffer SCREENSHOT socket path.  Mirror of ageup_capture.py:162-169.
    _SOCKET = "/tmp/AOE3DEHarness.sock"
    try:
        _c = HarnessClient(_SOCKET)
        _c.connect()
        set_harness_backend(_c)
        _ld.set_harness_backend(_c)
        _log(f"harness backend registered ({_SOCKET})")
    except HarnessConnectionError as _e:
        print(f"WARNING: harness socket not available ({_e}); "
              "screenshots will fall back to xdotool-PrintScreen (may fail on this rig)",
              flush=True)

    n = run_building_tour(args.civ, out_root, age_up=not args.no_age_up)
    return 0 if n > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
