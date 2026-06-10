#!/usr/bin/env python3
"""Validate that _picker_title_visible() correctly detects the civ-picker modal.

Uses the reference PNGs under artifacts/validation/ui_states/:
  - civ_picker.png                       → True  (SELECT HOME CITY variant)
  - civ_picker_select_civilization.png   → True  (SELECT CIVILIZATION variant)
  - skirmish_setup.png                   → False (lobby, modal CLOSED)
  - main_menu.png                        → False (main menu, no picker)

Exit codes:
    0 — all assertions pass (or required deps / PNGs are missing — degrade-pass)
    1 — one or more assertions failed
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_STATES_DIR = REPO_ROOT / "artifacts" / "validation" / "ui_states"

PICKER_PNG       = UI_STATES_DIR / "civ_picker.png"
PICKER_CIV_PNG   = UI_STATES_DIR / "civ_picker_select_civilization.png"
SKIRMISH_PNG     = UI_STATES_DIR / "skirmish_setup.png"
MENU_PNG         = UI_STATES_DIR / "main_menu.png"

FAIL = False


def fail(msg: str) -> None:
    global FAIL
    FAIL = True
    print(f"FAIL: {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"OK:   {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"WARN: {msg}", flush=True)


def main() -> int:
    global FAIL

    # --- Degrade-pass: missing optional deps ---
    try:
        from PIL import Image  # noqa: F401
        import pytesseract     # noqa: F401
    except ImportError as e:
        warn(f"Optional dep missing ({e}); skipping OCR assertions (degrade-pass).")
        print("PASS (degraded — OCR deps not installed)", flush=True)
        return 0

    # --- Degrade-pass: missing reference PNGs ---
    missing = [p for p in (PICKER_PNG, SKIRMISH_PNG, MENU_PNG) if not p.exists()]
    if missing:
        warn(f"Reference PNGs missing: {[str(p) for p in missing]}; "
             "skipping assertions (degrade-pass).")
        print("PASS (degraded — reference PNGs not present)", flush=True)
        return 0

    # --- Import lobby_driver ---
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.aoe3_automation.lobby_driver import _picker_title_visible
    except Exception as e:
        fail(f"Could not import _picker_title_visible from lobby_driver: {e}")
        return 1

    # --- Assert civ_picker.png → True (SELECT HOME CITY variant) ---
    result_picker = _picker_title_visible(PICKER_PNG)
    if result_picker is True:
        ok(f"civ_picker.png → True (SELECT HOME CITY modal detected)")
    else:
        fail(f"civ_picker.png → {result_picker!r}, expected True "
             f"('SELECT HOME CITY' title not detected)")

    # --- Assert civ_picker_select_civilization.png → True (variant 2) ---
    if PICKER_CIV_PNG.exists():
        result_picker_civ = _picker_title_visible(PICKER_CIV_PNG)
        if result_picker_civ is True:
            ok(f"civ_picker_select_civilization.png → True (SELECT CIVILIZATION modal detected)")
        else:
            fail(f"civ_picker_select_civilization.png → {result_picker_civ!r}, expected True "
                 f"('SELECT CIVILIZATION' title not detected)")
    else:
        warn("civ_picker_select_civilization.png missing; skipping variant-2 assertion.")

    # --- Assert skirmish_setup.png → False ---
    result_skirmish = _picker_title_visible(SKIRMISH_PNG)
    if result_skirmish is False:
        ok(f"skirmish_setup.png → False (no false-positive on lobby)")
    else:
        fail(f"skirmish_setup.png → {result_skirmish!r}, expected False "
             f"(false-positive: lobby incorrectly detected as picker)")

    # --- Assert main_menu.png → False ---
    result_menu = _picker_title_visible(MENU_PNG)
    if result_menu is False:
        ok(f"main_menu.png → False (no false-positive on main menu)")
    else:
        fail(f"main_menu.png → {result_menu!r}, expected False "
             f"(false-positive: main menu incorrectly detected as picker)")

    if FAIL:
        print("FAIL", flush=True)
        return 1
    print("PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
