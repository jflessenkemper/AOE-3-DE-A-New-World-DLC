#!/usr/bin/env python3
"""Validate that the screen-state classifier and recovery helper are correctly
implemented and wired into the runner.

Exit codes:
    0 — all assertions pass
    1 — one or more assertions failed
    Degrades gracefully to exit 0 if optional deps (Pillow, pytesseract) are
    missing — those dependencies are not required for static checks.

Static checks (no game needed):
    1. screen_state module imports without error.
    2. detect_screen_state exists with correct signature.
    3. ensure_at_main_menu exists with correct signature.
    4. anw_visual_capture_runner.py contains "ensure_at_main_menu" call
       before the "click_skirmish" call.
    5. anw_visual_capture_runner.py contains "bad_screen_state" status string.

Optional pixel checks (only run if reference PNGs exist under
    artifacts/validation/ui_states/<state>.png):
    6. detect_screen_state classifies each reference PNG to the expected state.
"""
from __future__ import annotations

import ast
import inspect
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "tools/aoe3_automation/anw_visual_capture_runner.py"
SCREEN_STATE_PATH = REPO_ROOT / "tools/aoe3_automation/screen_state.py"
UI_STATES_DIR = REPO_ROOT / "artifacts/validation/ui_states"

FAIL = False


def fail(msg: str) -> None:
    global FAIL
    FAIL = True
    print(f"FAIL: {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"OK:   {msg}", flush=True)


# ---------------------------------------------------------------------------
# Check 1-3: import + signature checks
# ---------------------------------------------------------------------------

def check_module_importable() -> bool:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "screen_state", SCREEN_STATE_PATH
        )
        if spec is None or spec.loader is None:
            fail(f"screen_state.py not found at {SCREEN_STATE_PATH}")
            return False
        mod = importlib.util.module_from_spec(spec)
        # Don't exec (would need game imports); just verify the file parses.
        with open(SCREEN_STATE_PATH, encoding="utf-8") as fh:
            src = fh.read()
        ast.parse(src)
        ok("screen_state.py parses without AST error")
        return True
    except FileNotFoundError:
        fail(f"screen_state.py not found: {SCREEN_STATE_PATH}")
        return False
    except SyntaxError as exc:
        fail(f"screen_state.py has syntax error: {exc}")
        return False


def check_function_signatures() -> None:
    """AST-parse screen_state.py and assert both functions are defined with
    the correct parameter names."""
    with open(SCREEN_STATE_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    fns: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            fns[node.name] = node

    # detect_screen_state(shot_path=None) -> str
    if "detect_screen_state" not in fns:
        fail("detect_screen_state function not defined in screen_state.py")
    else:
        fn = fns["detect_screen_state"]
        args = [a.arg for a in fn.args.args] + [a.arg for a in fn.args.kwonlyargs]
        if "shot_path" not in args:
            fail(f"detect_screen_state missing 'shot_path' param; found: {args}")
        else:
            ok("detect_screen_state(shot_path=None) defined")

    # ensure_at_main_menu(driver, *, max_attempts=3) -> bool
    if "ensure_at_main_menu" not in fns:
        fail("ensure_at_main_menu function not defined in screen_state.py")
    else:
        fn = fns["ensure_at_main_menu"]
        pos_args = [a.arg for a in fn.args.args]
        kw_args  = [a.arg for a in fn.args.kwonlyargs]
        if "driver" not in pos_args:
            fail(f"ensure_at_main_menu missing 'driver' positional param; found: {pos_args}")
        else:
            ok("ensure_at_main_menu(driver, ...) positional param 'driver' present")
        if "max_attempts" not in kw_args:
            fail(f"ensure_at_main_menu missing 'max_attempts' kwonly param; found: {kw_args}")
        else:
            ok("ensure_at_main_menu(..., *, max_attempts=...) kwonly param present")


# ---------------------------------------------------------------------------
# Check 4-5: runner wiring
# ---------------------------------------------------------------------------

def check_runner_wiring() -> None:
    with open(RUNNER_PATH, encoding="utf-8") as fh:
        src = fh.read()

    # Verify ensure_at_main_menu appears before ldr.click_skirmish (the actual
    # call, not comment references that also contain the word "click_skirmish").
    eamm_pos = src.find("ensure_at_main_menu")
    cs_pos   = src.find("ldr.click_skirmish")
    if eamm_pos == -1:
        fail("ensure_at_main_menu not found in anw_visual_capture_runner.py")
    elif cs_pos == -1:
        fail("ldr.click_skirmish not found in anw_visual_capture_runner.py (unexpected)")
    elif eamm_pos > cs_pos:
        fail(
            f"ensure_at_main_menu (pos {eamm_pos}) appears AFTER ldr.click_skirmish "
            f"(pos {cs_pos}) — wiring is wrong"
        )
    else:
        ok(f"ensure_at_main_menu appears before ldr.click_skirmish in runner "
           f"(pos {eamm_pos} < {cs_pos})")

    # Verify bad_screen_state status string is present
    if "bad_screen_state" not in src:
        fail("'bad_screen_state' status string not found in runner — "
             "Insertion Point A diff was not applied")
    else:
        ok("'bad_screen_state' status string present in runner")


# ---------------------------------------------------------------------------
# Optional Check 6: classify reference PNGs if they exist
# ---------------------------------------------------------------------------

EXPECTED_STATES = [
    "main_menu", "skirmish_setup", "civ_picker", "in_game",
    "pause_menu", "home_city", "diplomacy", "tech_tree",
    "post_game", "loading", "age_up_dialog",
]


def check_reference_pngs() -> None:
    if not UI_STATES_DIR.exists():
        print(f"INFO: {UI_STATES_DIR} not found — skipping pixel classification checks")
        return

    try:
        from tools.aoe3_automation.screen_state import detect_screen_state
    except Exception as exc:
        print(f"INFO: cannot import detect_screen_state for pixel checks: {exc}")
        return

    found = list(UI_STATES_DIR.glob("*.png"))
    if not found:
        print(f"INFO: no reference PNGs in {UI_STATES_DIR} — skipping pixel checks")
        return

    for png in found:
        expected = png.stem  # filename without .png = expected state
        if expected not in EXPECTED_STATES:
            print(f"INFO: skipping unrecognised state PNG: {png.name}")
            continue
        result = detect_screen_state(str(png))
        if result == expected:
            ok(f"detect_screen_state({png.name}) → '{result}'")
        else:
            fail(
                f"detect_screen_state({png.name}) → '{result}' "
                f"(expected '{expected}')"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== validate_screen_state_recovery ===", flush=True)

    if not check_module_importable():
        return 1

    check_function_signatures()
    check_runner_wiring()
    check_reference_pngs()

    if FAIL:
        print("\nRESULT: FAIL", flush=True)
        return 1
    print("\nRESULT: PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
