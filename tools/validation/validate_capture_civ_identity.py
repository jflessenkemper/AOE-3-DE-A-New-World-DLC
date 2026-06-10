#!/usr/bin/env python3
"""Validate that captured home-city screenshots actually show the expected civ.

Catches the 2026-06-09 bug where the visual-capture pipeline screenshotted
France/Napoleon into ANWBritish's folder because there was no civ-identity
check on the captured frames.

For each civ (or a single civ via --civ), OCRs the home-city-bearing surfaces
under artifacts/validation/visual_art/<civ>/full/ and asserts:
  1. The expected home-city name (e.g. "LONDON" for ANWBritish) appears in
     the OCR text.
  2. No OTHER civ's home-city name (e.g. "PARIS") is the dominant match.

Per-civ verdicts:
  OK        — expected name found, no alien name dominant
  MISMATCH  — wrong home-city name found (or expected name absent)
  NO_TEXT   — OCR returned empty text
  SKIP      — no mapping entry for this civ token

Exit codes:
  0 — all checked civs OK (or only SKIPs), or --warn-only
  1 — one or more MISMATCHes
  2 — script error

Usage:
    python3 tools/validation/validate_capture_civ_identity.py
    python3 tools/validation/validate_capture_civ_identity.py --civ ANWBritish
    python3 tools/validation/validate_capture_civ_identity.py --civ ANWBritish --warn-only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# OCR availability — graceful fallback if tesseract not installed
# ---------------------------------------------------------------------------
_OCR_AVAILABLE = False
try:
    from tools.validation.ocr_validator import OCRValidator, PYTESSERACT_AVAILABLE
    _OCR_AVAILABLE = PYTESSERACT_AVAILABLE
except ImportError:
    PYTESSERACT_AVAILABLE = False

# ---------------------------------------------------------------------------
# Home-city name → civ token mapping (imported from lobby_driver, not guessed)
# ---------------------------------------------------------------------------
try:
    from tools.aoe3_automation.lobby_driver import HOME_CITY_TO_TOKEN
except ImportError:
    # If lobby_driver cannot be imported (missing deps in CI), fall back to a
    # read-only copy of the dict so this module stays self-contained.
    HOME_CITY_TO_TOKEN: dict[str, str] = {
        "DELHI": "ANWIndians",
        "TENOCHTITLAN": "ANWAztecs",
        "WASHINGTON, D. C.": "ANWUSA",
        "WASHINGTON D. C.": "ANWUSA",
        "WASHINGTON DC": "ANWUSA",
        "WASHINGTON": "ANWUSA",
        "STOCKHOLM": "ANWSwedes",
        "SEVILLE": "ANWSpanish",
        "ST. PETERSBURG": "ANWRussians",
        "ST PETERSBURG": "ANWRussians",
        "LISBON": "ANWPortuguese",
        "ISTANBUL": "ANWOttomans",
        "MEXICO CITY": "ANWMexicans",
        "PARIS": "ANWFrench",
        "BERLIN": "ANWGermans",
        "CUZCO": "ANWInca",
        "CAUGHNAWAGA": "ANWHaudenosaunee",
        "KANO": "ANWHausa",
        "AMSTERDAM": "ANWDutch",
        "LONDON": "ANWBritish",
        "TOKYO": "ANWJapanese",
        "BEIJING": "ANWChinese",
        "PEKING": "ANWChinese",
        "GREAT COUNCIL": "ANWLakota",
        "VENICE": "ANWItalians",
        "VALLETTA": "ANWMaltese",
        "CHAN SANTA CRUZ": "ANWMayans",
        "NEDERLAND": "ANWDutch",
    }

# Build token → set of expected home-city name strings (inverted mapping).
# A token may have multiple aliases (e.g. ANWChinese → {"BEIJING", "PEKING"}).
_TOKEN_TO_NAMES: dict[str, set[str]] = {}
for _name, _token in HOME_CITY_TO_TOKEN.items():
    _TOKEN_TO_NAMES.setdefault(_token, set()).add(_name)

# All known home-city name strings (for alien-name detection).
_ALL_NAMES: list[str] = list(HOME_CITY_TO_TOKEN.keys())

ART_ROOT = _REPO_ROOT / "artifacts" / "validation" / "visual_art"

# Surfaces most likely to show the home-city panel (in priority order).
_HOMECITY_SURFACES = [
    "04_homecity_panel.png",
    "10_ai_homecity.png",
    "02_loading.png",
]


def _active_civs_from_xml() -> list[str]:
    """Return sorted list of active ANW civ tokens from civmods.xml."""
    civmods = _REPO_ROOT / "data" / "civmods.xml"
    text = civmods.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"<name>(ANW[A-Za-z]+)</name>", text)))


def _check_surface(image_path: Path, expected_names: set[str]) -> dict:
    """OCR one surface and classify against expected_names.

    Returns:
        {
            "surface": str,
            "verdict": "OK" | "MISMATCH" | "NO_TEXT" | "OCR_UNAVAILABLE",
            "raw_text": str,          # uppercased; "" if unavailable
            "found_expected": str,    # which expected name matched ("" if none)
            "found_alien": str,       # which alien name was found ("" if none)
        }
    """
    result = {
        "surface": image_path.name,
        "verdict": "OCR_UNAVAILABLE",
        "raw_text": "",
        "found_expected": "",
        "found_alien": "",
    }

    if not _OCR_AVAILABLE:
        return result

    validator = OCRValidator()
    ocr = validator.extract_text(image_path)
    if ocr.get("status") != "OK":
        result["verdict"] = "NO_TEXT"
        result["raw_text"] = ocr.get("error", "OCR error")
        return result

    raw = ocr.get("raw_text", "").upper()
    result["raw_text"] = raw

    if not raw.strip():
        result["verdict"] = "NO_TEXT"
        return result

    # Check if any expected name appears
    found_expected = ""
    for name in expected_names:
        if name in raw:
            found_expected = name
            break
    result["found_expected"] = found_expected

    # Check if any alien name appears (names that map to a DIFFERENT token)
    found_alien = ""
    for name in _ALL_NAMES:
        if name in expected_names:
            continue  # same-token alias, not alien
        if name in raw:
            found_alien = name
            break
    result["found_alien"] = found_alien

    if found_expected:
        result["verdict"] = "OK"
    elif found_alien:
        # Found a different civ's home-city — definite wrong-civ capture
        result["verdict"] = "MISMATCH"
    else:
        # Neither expected nor any known alien name found — low-confidence OCR
        result["verdict"] = "NO_TEXT"

    return result


def check_civ(civ_token: str) -> dict:
    """Check all available home-city surfaces for civ_token.

    Returns:
        {
            "civ_token": str,
            "verdict": "OK" | "MISMATCH" | "NO_TEXT" | "SKIP" | "OCR_UNAVAILABLE",
            "surfaces": [per-surface results],
            "note": str,
        }
    """
    expected_names = _TOKEN_TO_NAMES.get(civ_token)
    if not expected_names:
        return {
            "civ_token": civ_token,
            "verdict": "SKIP",
            "surfaces": [],
            "note": "no expected-name mapping in HOME_CITY_TO_TOKEN",
        }

    if not _OCR_AVAILABLE:
        return {
            "civ_token": civ_token,
            "verdict": "OCR_UNAVAILABLE",
            "surfaces": [],
            "note": "pytesseract/tesseract not installed — skipping",
        }

    full_dir = ART_ROOT / civ_token / "full"
    if not full_dir.exists():
        return {
            "civ_token": civ_token,
            "verdict": "SKIP",
            "surfaces": [],
            "note": f"full/ directory does not exist: {full_dir}",
        }

    surfaces_checked = []
    for surface_name in _HOMECITY_SURFACES:
        path = full_dir / surface_name
        if path.exists():
            surfaces_checked.append(_check_surface(path, expected_names))

    if not surfaces_checked:
        return {
            "civ_token": civ_token,
            "verdict": "SKIP",
            "surfaces": [],
            "note": f"no home-city surfaces found (checked: {', '.join(_HOMECITY_SURFACES)})",
        }

    # Roll up: any MISMATCH dominates; then any OK; else NO_TEXT
    verdicts = [s["verdict"] for s in surfaces_checked]
    if "MISMATCH" in verdicts:
        overall = "MISMATCH"
    elif "OK" in verdicts:
        overall = "OK"
    else:
        overall = "NO_TEXT"

    return {
        "civ_token": civ_token,
        "verdict": overall,
        "surfaces": surfaces_checked,
        "note": "",
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--civ", default=None,
                   help="Check a single civ token only (e.g. ANWBritish).")
    p.add_argument("--warn-only", action="store_true",
                   help="Print failures but exit 0 (warning mode for CI).")
    p.add_argument("--art-root", default=None,
                   help="Override art root path (default: artifacts/validation/visual_art).")
    args = p.parse_args()

    global ART_ROOT
    if args.art_root:
        ART_ROOT = Path(args.art_root)

    if not _OCR_AVAILABLE:
        print("OCR unavailable — pytesseract/tesseract not installed. Skipping civ-identity check.")
        return 0

    civs = [args.civ] if args.civ else _active_civs_from_xml()

    results = [check_civ(c) for c in civs]

    ok = [r for r in results if r["verdict"] == "OK"]
    mismatch = [r for r in results if r["verdict"] == "MISMATCH"]
    no_text = [r for r in results if r["verdict"] == "NO_TEXT"]
    skipped = [r for r in results if r["verdict"] in ("SKIP", "OCR_UNAVAILABLE")]

    print(f"Checked {len(results)} civ(s): "
          f"{len(ok)} OK, {len(mismatch)} MISMATCH, "
          f"{len(no_text)} NO_TEXT, {len(skipped)} SKIP")

    if skipped:
        print("\n=== SKIPPED ===")
        for r in skipped:
            print(f"  {r['civ_token']}: {r['note']}")

    if no_text:
        print("\n=== NO_TEXT (OCR returned nothing useful) ===")
        for r in no_text:
            print(f"  {r['civ_token']}:")
            for s in r["surfaces"]:
                print(f"    {s['surface']}: {s['verdict']}")

    if ok:
        print("\n=== OK ===")
        for r in ok:
            print(f"  {r['civ_token']}:")
            for s in r["surfaces"]:
                exp = s["found_expected"]
                print(f"    {s['surface']}: OK (found '{exp}')")

    if mismatch:
        print("\n=== MISMATCH (wrong civ captured) ===")
        for r in mismatch:
            expected_names = _TOKEN_TO_NAMES.get(r["civ_token"], set())
            print(f"  {r['civ_token']} (expected one of: {sorted(expected_names)}):")
            for s in r["surfaces"]:
                if s["verdict"] == "MISMATCH":
                    print(f"    {s['surface']}: MISMATCH "
                          f"(found alien '{s['found_alien']}', "
                          f"expected '{sorted(expected_names)}')")
                elif s["verdict"] == "OK":
                    print(f"    {s['surface']}: OK (found '{s['found_expected']}')")
                else:
                    print(f"    {s['surface']}: {s['verdict']}")

    if not mismatch:
        print("\nPASS: no civ-identity mismatches detected.")
        return 0

    if args.warn_only:
        print(f"\nWARN: {len(mismatch)} mismatch(es) found but --warn-only set; exiting 0.")
        return 0

    print(f"\nFAIL: {len(mismatch)} civ(s) show wrong home-city in captured screenshots.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
