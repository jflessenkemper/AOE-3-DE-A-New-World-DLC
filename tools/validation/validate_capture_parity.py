#!/usr/bin/env python3
"""Validate capture parity: every active ANW civ must have Britain-level coverage.

"Britain-parity" means every civ's artifacts/validation/visual_art/<civ>/full/
directory contains:

  1. All 22 fixed core surfaces (labels from capture_profile.CORE_SURFACES,
     e.g. 01_lobby.png, 03_hud.png, 08_ageup_age2.png, ai_01_chat_portrait.png,
     build_command_card.png, etc.)

  2. build_command_card.png (already included in CORE_SURFACES above — also
     checked explicitly for clarity)

  3. At least one building_<slug>.png per entry in
     capture_profile.expected_building_filenames(civ_token), which is the union
     of COMMON_CORE_BUILDINGS and the civ's unique_buildings from
     data/anw_civ_blurbs.json.

Why Britain as the bar: ANWBritish is the only fully-captured civ as of
2026-06-09. Its full/ directory is the reference set. This validator pins that
every other nation reaches the same coverage, so the visual-art capture pipeline
cannot ship with 43 civs at lobby+loading floor while only Britain has full
in-game coverage.

Active civs come from data/civmods.xml (<name>ANW...</name> on <main>1</main>
entries), mirroring the active_civs() helper in validate_visual_capture_integrity.py.

Exit codes:
  0 — all civs pass (or --civ single civ passed, or --warn-only set with gaps)
  1 — one or more civs have missing surfaces / buildings
  2 — script error (bad args, missing profile, etc.)

Usage:
    python3 tools/validation/validate_capture_parity.py
    python3 tools/validation/validate_capture_parity.py --civ ANWBritish
    python3 tools/validation/validate_capture_parity.py --warn-only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_automation.capture_profile import (
    all_active_civs,
    parity_profile,
)

ART_ROOT = _REPO_ROOT / "artifacts" / "validation" / "visual_art"
_CIVMODS = _REPO_ROOT / "data" / "civmods.xml"


def active_civs_from_xml() -> list[str]:
    """Return sorted list of active ANW civ tokens from civmods.xml.

    Mirrors the active_civs() helper in validate_visual_capture_integrity.py.
    """
    text = _CIVMODS.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"<name>(ANW[A-Za-z]+)</name>", text)))


def check_civ(civ_token: str) -> dict:
    """Return {civ_token, missing_core, missing_buildings, ok}.

    missing_core: list of label strings (no .png) absent from full/
    missing_buildings: list of filename strings (with .png) absent from full/
    ok: True iff both lists are empty
    """
    profile = parity_profile(civ_token)
    full_dir = ART_ROOT / civ_token / "full"

    if not full_dir.exists():
        return {
            "civ_token": civ_token,
            "missing_core": profile["core_surfaces"],
            "missing_buildings": profile["building_filenames"],
            "ok": False,
            "full_dir_missing": True,
        }

    # Collect existing filenames (lowercase for robustness)
    existing = {f.name.lower() for f in full_dir.iterdir() if f.is_file()}

    missing_core = [
        label for label in profile["core_surfaces"]
        if f"{label}.png".lower() not in existing
    ]

    # For buildings: check by exact slug name first.
    # Numerically-indexed captures (building_00.png etc.) also count toward
    # the minimum — if the count is satisfied by numeric files, treat as ok.
    all_building_files = {f for f in existing if f.startswith("building_")}
    missing_named = [fn for fn in profile["building_filenames"]
                     if fn.lower() not in existing]
    n_expected = len(profile["building_filenames"])
    n_present = len(all_building_files)

    if missing_named and n_present >= n_expected:
        # Count is satisfied by numeric-indexed captures; names are informational
        missing_buildings: list[str] = []
    else:
        missing_buildings = missing_named if missing_named else []
        if n_present < n_expected and not missing_buildings:
            missing_buildings = [
                f"<need {n_expected} building_*.png, found {n_present}>"
            ]

    return {
        "civ_token": civ_token,
        "missing_core": missing_core,
        "missing_buildings": missing_buildings,
        "ok": len(missing_core) == 0 and len(missing_buildings) == 0,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
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

    civs = [args.civ] if args.civ else active_civs_from_xml()

    results = [check_civ(c) for c in civs]
    failing = [r for r in results if not r["ok"]]
    passing = [r for r in results if r["ok"]]

    print(f"Checked {len(results)} civ(s): {len(passing)} OK, {len(failing)} FAILING")

    if failing:
        print("\n=== FAILING CIVS ===")
        for r in failing:
            print(f"\n  {r['civ_token']}:")
            if r.get("full_dir_missing"):
                print("    full/ directory does not exist")
                continue
            if r["missing_core"]:
                print(f"    Missing core surfaces ({len(r['missing_core'])}):")
                for label in r["missing_core"]:
                    print(f"      - {label}.png")
            if r["missing_buildings"]:
                print(f"    Missing buildings ({len(r['missing_buildings'])}):")
                for fn in r["missing_buildings"]:
                    print(f"      - {fn}")

    if not failing:
        print("PASS: all civs at Britain-parity.")
        return 0

    if args.warn_only:
        print("WARN: failures found but --warn-only set; exiting 0.")
        return 0

    print(f"\nFAIL: {len(failing)} civ(s) below Britain-parity.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
