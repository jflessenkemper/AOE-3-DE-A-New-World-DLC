#!/usr/bin/env python3
"""Drive the running AoE3 DE (via AOE3DEHarness socket) into an anwHubTest match.

Pre-condition: the game is already running and at the MAIN MENU, with the
harness control socket live at /tmp/AOE3DEHarness.sock (Steam launch options
include the `--keep-alive` AOE3DEHarness wrapper). The anwHubTest random map
must already be published into the live RandMaps dir (run_sandbox.py
--random-map anwHubTest).

Navigation (empirically calibrated 2026-05-31 on build v100.15.99076.0, 1920x1080):
  1. Main Menu -> Skirmish        : click (130, 482)
  2. Open Select Map picker       : click (1637, 425)
  3. Jump to bottom of map list   : press End (0x23)
       anwHubTest shows as "Unknown" (its displayNameID isn't registered),
       so it sorts at 'U' and lands in the End view at row1 col4 (1059, 304).
  4. Confirm map (double-click)    : click (1059, 304) x2
  5. Start match                   : click Play (1648, 1048)

NOTE: bottom-edge buttons (OK at y~985, Play at y~1048) need the LOWER Y of
their text box — clicks a few px high silently miss. Map confirm uses
double-click on the tile rather than the finicky OK button.

Usage:
    python3 tools/aoe3_harness/drive_hubtest.py [--shot-prefix NAME]

Exits 0 on reaching the loading/in-game screen, 2 if an XS-error dialog is
detected after Play (caller should inspect artifacts/harness_probe/<prefix>_*).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
OUT = REPO / "artifacts" / "harness_probe"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO))

from tools.aoe3_harness.harness_client import HarnessClient  # noqa: E402

SOCK = "/tmp/AOE3DEHarness.sock"

# Calibrated coords (1920x1080)
SKIRMISH = (130, 482)
MAP_BTN = (1637, 425)
HUBTEST_TILE = (1059, 304)   # "Unknown" tile after pressing End
PLAY = (1648, 1048)
VK_END = 0x23


def drive(prefix: str = "hub", from_lobby: bool = False) -> int:
    c = HarnessClient(SOCK)
    c.connect(timeout=30)
    st = c.state()
    print(f"[drive] connected; ready={st.ready} {st.internal_w}x{st.internal_h}", flush=True)
    if st.ready != 1:
        # give the menu a moment
        for _ in range(20):
            time.sleep(3)
            if c.state().ready == 1:
                break

    # 1. Skirmish (skip if we're already at the lobby)
    if not from_lobby:
        c.click(*SKIRMISH); time.sleep(3.0)
        c.screenshot(str(OUT / f"{prefix}_1_skirmish.png"))

    # 2. Open map picker
    c.click(*MAP_BTN); time.sleep(2.5)

    # 3. Click a grid tile FIRST to give the list keyboard focus, THEN jump to
    #    the bottom. Without the focus-click, End is a no-op and the view stays
    #    on the category tiles at the top (col4 there is "African Maps").
    c.click(150, 304); time.sleep(0.4)          # focus the grid (top-left tile)
    c.key(VK_END); time.sleep(1.0)
    c.screenshot(str(OUT / f"{prefix}_2_mapend.png"))

    # 4. Double-click the anwHubTest ('Unknown') tile to confirm
    c.click(*HUBTEST_TILE); time.sleep(0.25); c.click(*HUBTEST_TILE); time.sleep(2.5)
    c.screenshot(str(OUT / f"{prefix}_3_lobby.png"))

    # 5. Play
    c.click(*PLAY); time.sleep(6.0)
    shot = OUT / f"{prefix}_4_afterplay.png"
    c.screenshot(str(shot))
    print(f"[drive] post-Play screenshot: {shot}", flush=True)
    c.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot-prefix", default="hub")
    args = ap.parse_args()
    return drive(args.shot_prefix)


if __name__ == "__main__":
    sys.exit(main())
