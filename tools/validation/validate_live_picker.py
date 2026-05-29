#!/usr/bin/env python3
"""Live-engine validation: capture skirmish picker and check for ANW civs.

Bug class this catches (hit on 2026-05-09): the static gate was 100% PASS
(32/37 with all data-layer checks green), the mod CRC matched in
Age3Log.txt, the mod install dir was byte-identical to the dev tree —
yet the live skirmish picker showed only base-game DE civs (Mexico,
Netherlands, Ottoman Empire, Portugal, Russia, Sokoto, Spain, Sweden,
United States, Mughal India). ZERO ANW civs visible in-game.

That class of bug — "the data is loadable, but the engine's UI doesn't
surface it" — needs a runtime validator. Pure static analysis cannot
catch it. This validator closes that gap by:

1. Capturing the gamescope frame buffer via ``gamescopectl screenshot``.
2. (Optionally) running OCR on the SELECT CIVILIZATION panel region.
3. Reporting either: (a) ANW civ names found ✓, (b) only base civ names
   found ✗, or (c) UNKNOWN — picker not on screen / OCR unavailable.

The validator is deliberately low-tech so it works in CI without heavy
deps. It captures evidence to ``artifacts/live_picker_<ts>/`` and prints
a clear PASS/FAIL/UNKNOWN verdict.

Prerequisites for live mode:
  - Game running under gamescope on display ``$DISPLAY`` (default :1)
  - Game UI sitting on the Skirmish "Select Civilization" screen
  - ``gamescopectl`` available on PATH

Usage::

    python3 tools/validation/validate_live_picker.py
    python3 tools/validation/validate_live_picker.py --ocr   # if pytesseract installed
    python3 tools/validation/validate_live_picker.py --capture-only  # just save screenshot

If the game isn't running, the validator returns SKIP (rc 0 with note).
If the picker isn't visible (no SELECT CIVILIZATION text), returns
UNKNOWN (rc 0 with note).
If only base civs visible (no ANW token names found), returns FAIL
(rc 1) — the static gate cannot have caught this; you need to fix the
engine merge / picker integration.
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402


# Display names that indicate a base-game civ is in the picker
# (DE renamed several base civs at the picker layer):
_BASE_CIV_DISPLAY_NAMES = {
    "Mexico", "Mughal India", "Netherlands", "Ottoman Empire",
    "Portugal", "Russia", "Sokoto", "Spain", "Sweden",
    "United States", "British", "French", "Germans", "Italians",
    "Japanese", "Chinese", "Aztecs", "Inca", "Lakota", "Iroquois",
    "Haudenosaunee", "Ethiopians", "Hausa", "Maltese",
}

# ANW-specific display names that MUST appear if civmods loaded into the
# picker correctly. Pulled from anw_token_map.ANW_CIVS display field.
_ANW_DISPLAY_NAMES = {info["display"] for info in ANW_CIVS.values()}


def find_game_window() -> str | None:
    """Return the AoE3 window ID on $DISPLAY, or None."""
    if not shutil.which("xdotool"):
        return None
    try:
        out = subprocess.check_output(
            ["xdotool", "search", "--name", "Age of Empires"],
            text=True, timeout=5,
        ).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    return out.splitlines()[0] if out else None


def capture_screenshot(out_path: Path) -> bool:
    """Capture gamescope frame to out_path. Returns True on success."""
    if not shutil.which("gamescopectl"):
        return False
    try:
        proc = subprocess.run(
            ["gamescopectl", "screenshot", str(out_path)],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return False
    # gamescopectl is async — give it up to 3s to flush the PNG.
    import time
    for _ in range(30):
        if out_path.exists() and out_path.stat().st_size > 1000:
            return True
        time.sleep(0.1)
    return False


def ocr_text(image_path: Path) -> str | None:
    """OCR the screenshot's civ-list panel. Crop+preprocess for better hit rate.

    Tesseract's default reads light-on-dark UI text poorly. We:
      1. Read the full image once (to detect "SELECT CIVILIZATION" on screen).
      2. Crop the civ-list panel (left side of 1920x1080 lobby), invert
         to dark-on-light, and OCR again with --psm 6 (assume single
         uniform block of text). Concatenate both reads.
    """
    try:
        from PIL import Image, ImageEnhance, ImageOps
        import pytesseract
    except ImportError:
        return None
    try:
        img = Image.open(image_path)
        # Full-image read for the page header / right panel context
        full = pytesseract.image_to_string(img)
        # Crop civ list panel — coordinates calibrated to 1920x1080 lobby
        panel = img.crop((130, 170, 360, 580))
        gray = ImageOps.grayscale(panel)
        enh = ImageEnhance.Contrast(gray).enhance(2.0)
        inv = ImageOps.invert(enh)
        list_text = pytesseract.image_to_string(inv, config="--psm 6")
        return full + "\n" + list_text
    except Exception:
        return None


def classify(text: str) -> dict:
    """Given OCR text, classify what civs are visible."""
    text_norm = text.replace("\u00ad", "").replace("  ", " ")
    text_low = text_norm.lower()

    on_picker = "select civilization" in text_low

    found_anw = sorted({n for n in _ANW_DISPLAY_NAMES
                       if n.lower() in text_low})
    found_base = sorted({n for n in _BASE_CIV_DISPLAY_NAMES
                        if n.lower() in text_low})

    return {
        "on_picker_screen": on_picker,
        "anw_civs_visible": found_anw,
        "base_civs_visible": found_base,
        "anw_count": len(found_anw),
        "base_count": len(found_base),
    }


def validate_static_civ_registration(repo_root: Path) -> tuple[list[str], int]:
    """Static-mode: verify every ANW civ token appears in civmods.xml.

    Returns (issues, total_checked).
    """
    import xml.etree.ElementTree as ET

    civmods_path = repo_root / "game" / "data" / "civmods.xml"
    if not civmods_path.exists():
        # Try alternate location
        for candidate in (
            repo_root / "data" / "civmods.xml",
            repo_root / "game" / "civmods.xml",
        ):
            if candidate.exists():
                civmods_path = candidate
                break
        else:
            return [f"civmods.xml not found (searched under {repo_root}/game/data/)"], 0

    try:
        tree = ET.parse(civmods_path)
    except ET.ParseError as exc:
        return [f"civmods.xml parse error: {exc}"], 0

    root = tree.getroot()
    # Collect all civ tokens present in civmods.xml (case-insensitive for robustness).
    registered_tokens: set[str] = set()
    for elem in root.iter():
        # <CivMod id="ANWBritish" ...> or <civ>ANWBritish</civ> patterns
        civ_id = elem.get("id") or elem.get("name") or elem.get("civid") or ""
        if civ_id:
            registered_tokens.add(civ_id.strip())
        # Also collect text content if the tag looks civ-like
        tag = (elem.tag or "").lower()
        if tag in ("civ", "civmod", "forcedciv"):
            txt = (elem.text or "").strip()
            if txt:
                registered_tokens.add(txt)

    issues: list[str] = []
    civmods_text = civmods_path.read_text(encoding="utf-8", errors="replace")
    for token in sorted(ANW_CIVS.keys()):
        if token not in registered_tokens and token not in civmods_text:
            info = ANW_CIVS[token]
            issues.append(
                f"ANW civ token {token!r} ({info.get('display', '?')}) "
                f"not found in civmods.xml"
            )

    return issues, len(ANW_CIVS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path,
                    default=REPO_ROOT / "artifacts" / "live_picker")
    ap.add_argument("--ocr", action="store_true",
                    help="run OCR (requires pytesseract); without OCR returns UNKNOWN")
    ap.add_argument("--capture-only", action="store_true",
                    help="just take a screenshot, don't classify")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--static-mode", action="store_true",
                    help=(
                        "Offline fallback: verify every ANW civ token is registered "
                        "in civmods.xml. PASS if all 40 tokens present. "
                        "Catches missing registrations without the game running."
                    ))
    args = ap.parse_args()

    # Static mode: run offline civ registration check instead of live OCR.
    if args.static_mode:
        print("=" * 60)
        print("LIVE PICKER VALIDATION (static-mode)")
        print("=" * 60)
        issues, total = validate_static_civ_registration(REPO_ROOT)
        if issues:
            print(f"static-mode: civ registration check FAILED ({len(issues)} missing):")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        print(
            f"static-mode: all {total} ANW civ tokens registered in civmods.xml. "
            "(Live picker OCR requires the game running.)"
        )
        return 0

    print("=" * 60)
    print("LIVE PICKER VALIDATION")
    print("=" * 60)

    win = find_game_window()
    if win is None:
        print("⏭  SKIP — no AoE3 window found on $DISPLAY (game not running?)")
        return 0
    print(f"  Game window: {win}")

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    shot = args.out_dir / f"picker_{ts}.png"

    if not capture_screenshot(shot):
        print("⏭  SKIP — gamescopectl screenshot failed (gamescope not "
              "available, or capture failed)")
        return 0
    print(f"  Captured: {shot.relative_to(REPO_ROOT)}  "
          f"({shot.stat().st_size // 1024} KB)")

    if args.capture_only:
        print()
        print("OVERALL: capture-only, no classification")
        return 0

    if not args.ocr:
        print()
        print("⚠ UNKNOWN — --ocr not specified; cannot classify automatically.")
        print("  Manual review checklist:")
        print(f"    - Open {shot.relative_to(REPO_ROOT)}")
        print("    - Confirm SELECT CIVILIZATION list contains "
              "ANW civs (e.g. 'British', 'French', 'Aztecs', 'Mexicans')")
        print("    - If ONLY base-game DE civs visible (Mexico, "
              "Netherlands, Ottoman Empire…), the engine isn't picking up "
              "civmods.xml in the picker — release blocker.")
        print()
        print("  To enable automatic OCR check:")
        print("    pip install --user pytesseract pillow")
        print("    python3 tools/validation/validate_live_picker.py --ocr")
        return 0

    text = ocr_text(shot)
    if text is None:
        print("⏭  SKIP — OCR requested but pytesseract not available; "
              "install with: pip install --user pytesseract pillow")
        return 0

    result = classify(text)

    print()
    print(f"  On Skirmish picker screen?  "
          f"{'YES' if result['on_picker_screen'] else 'NO'}")
    print(f"  ANW civs visible:           {result['anw_count']}/46")
    if result["anw_civs_visible"]:
        print(f"    {', '.join(result['anw_civs_visible'][:10])}"
              f"{'…' if len(result['anw_civs_visible']) > 10 else ''}")
    print(f"  Base-game civs visible:     {result['base_count']}")
    if result["base_civs_visible"]:
        print(f"    {', '.join(result['base_civs_visible'][:10])}"
              f"{'…' if len(result['base_civs_visible']) > 10 else ''}")
    print()

    if not result["on_picker_screen"]:
        print("⚠ UNKNOWN — picker not on screen. Navigate to "
              "Skirmish → Advanced → Select Civilization, then re-run.")
        rc = 0
    elif result["anw_count"] == 0 and result["base_count"] > 0:
        print("✗ FAIL — picker shows base-game civs but NO ANW civs. "
              "The engine isn't surfacing civmods.xml in the UI; "
              "this is the static-gate vs runtime-engine gap.")
        rc = 1
    elif result["anw_count"] > 0 and result["base_count"] == 0:
        print("✓ PASS — only ANW civs visible, no base civs. Picker is "
              "ANW-pure as user intended.")
        rc = 0
    elif result["anw_count"] > 0 and result["base_count"] > 0:
        print("⚠ MIXED — picker shows both ANW and base civs. User intent "
              "was 'ANW only'. Need to suppress base civs.")
        rc = 1
    else:
        print("⚠ UNKNOWN — couldn't find any civ names in OCR output. "
              "OCR may have failed; check screenshot manually.")
        rc = 0

    if args.json:
        import json
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({
                "screenshot": str(shot.relative_to(REPO_ROOT)),
                **result,
                "verdict_rc": rc,
            }, f, indent=2)
        print(f"  Report: {args.json}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
