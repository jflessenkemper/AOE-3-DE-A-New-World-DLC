#!/usr/bin/env python3
"""Targeted capture: AI Home City and Deck screenshots for ANWBritish.

Assumes game is running and in a match. Navigates:
  1. Click Diplomacy button → Player Summary opens
  2. Click P2 flag → AI Home City scene opens
  3. Screenshot → ai_02_homecity.png
  4. Screenshot again (deck view) → ai_03_deck.png
  5. Press Escape to close HC view
"""
from __future__ import annotations
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

OUT_DIR = _REPO_ROOT / "artifacts/validation/visual_art/ANWBritish/full"

# P2 is the AI player (Muhammad Ali / red) per Player Summary screenshot
DEMO_PLAYER_INDEX = 2


def main() -> None:
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
    p_homecity = OUT_DIR / "ai_02_homecity.png"
    print(f"Capturing ai_02_homecity.png → {p_homecity}")
    _gs_screenshot(p_homecity)
    print("  ai_02_homecity.png captured.")

    time.sleep(0.5)

    # Capture ai_03_deck.png (same scene; deck is visible in the HC view)
    p_deck = OUT_DIR / "ai_03_deck.png"
    print(f"Capturing ai_03_deck.png → {p_deck}")
    _gs_screenshot(p_deck)
    print("  ai_03_deck.png captured.")

    # Escape back to game
    print("Pressing Escape to close HC view...")
    _key("Escape")
    time.sleep(0.8)

    print("Done.")


if __name__ == "__main__":
    main()
