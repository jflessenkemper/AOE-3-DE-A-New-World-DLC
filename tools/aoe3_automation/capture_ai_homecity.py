#!/usr/bin/env python3
"""Targeted capture: AI Home City and Deck screenshots, parameterized by civ token.

Assumes game is running and in a match. Navigates:
  1. Click Diplomacy button -> Player Summary opens
  2. Click P2 flag -> AI Home City scene opens
  3. Screenshot -> ai_02_homecity.png
  4. Screenshot again (deck view) -> ai_03_deck.png
  5. Press Escape to close HC view

Output goes to artifacts/validation/visual_art/<civ>/full/
(or the --out-root you specify).

Usage:
    python3 tools/aoe3_automation/capture_ai_homecity.py
    python3 tools/aoe3_automation/capture_ai_homecity.py --civ ANWFrench
    python3 tools/aoe3_automation/capture_ai_homecity.py \\
        --civ ANWChinese --out-root artifacts/validation/visual_art
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_automation.in_game_driver import (
    DIPLOMACY_BTN,
    DIPLOMACY_FLAG_X,
    diplomacy_row_y,
    _click,
    _key,
    _focus_window,
)
from tools.aoe3_automation.lobby_driver import screenshot as _gs_screenshot

# P2 is the AI player (Muhammad Ali / red) per Player Summary screenshot
DEMO_PLAYER_INDEX = 2


def main(civ_token: str = "ANWBritish",
         out_root: "Path | None" = None) -> None:
    """Capture ai_02_homecity.png and ai_03_deck.png for civ_token.

    Parameters
    ----------
    civ_token:
        ANW civ token (e.g. "ANWFrench").  Default: "ANWBritish".
    out_root:
        Root directory under which <civ_token>/full/ is created.
        Defaults to <repo_root>/artifacts/validation/visual_art.
    """
    if out_root is None:
        out_root = _REPO_ROOT / "artifacts" / "validation" / "visual_art"
    out_dir = out_root / civ_token / "full"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[capture_ai_homecity] civ={civ_token}  out_dir={out_dir}")
    print("Focusing game window...")
    _focus_window()
    time.sleep(0.5)

    print("Opening diplomacy panel (inkwell icon at 1691,35)...")
    _click(*DIPLOMACY_BTN, delay=1.2)
    time.sleep(1.5)

    row_y = diplomacy_row_y(DEMO_PLAYER_INDEX)
    print(f"Clicking P{DEMO_PLAYER_INDEX} flag at ({DIPLOMACY_FLAG_X}, {row_y})...")
    _click(DIPLOMACY_FLAG_X, row_y, delay=1.0)
    time.sleep(3.0)  # HC scene takes a moment to render

    # Capture ai_02_homecity.png
    p_homecity = out_dir / "ai_02_homecity.png"
    print(f"Capturing ai_02_homecity.png -> {p_homecity}")
    _gs_screenshot(p_homecity)
    print("  ai_02_homecity.png captured.")

    time.sleep(0.5)

    # Capture ai_03_deck.png (same scene; deck is visible in the HC view)
    p_deck = out_dir / "ai_03_deck.png"
    print(f"Capturing ai_03_deck.png -> {p_deck}")
    _gs_screenshot(p_deck)
    print("  ai_03_deck.png captured.")

    # Escape back to game
    print("Pressing Escape to close HC view...")
    _key("Escape")
    time.sleep(0.8)

    print("Done.")


if __name__ == "__main__":
    _ap = argparse.ArgumentParser(description=__doc__)
    _ap.add_argument("--civ", default="ANWBritish",
                     help="ANW civ token (e.g. ANWFrench).  Default: ANWBritish")
    _ap.add_argument("--out-root", default="artifacts/validation/visual_art",
                     help="Output root directory (relative to repo root or absolute).  "
                          "Output goes to <out-root>/<civ>/full/")
    _args = _ap.parse_args()
    _root = Path(_args.out_root)
    if not _root.is_absolute():
        _root = _REPO_ROOT / _root
    main(_args.civ, _root)
