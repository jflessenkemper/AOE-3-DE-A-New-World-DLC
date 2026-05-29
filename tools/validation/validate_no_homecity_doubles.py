#!/usr/bin/env python3
"""Detect doubled-up civs in the SELECT HOME CITY picker.

Bug class this catches (hit on 2026-05-09): user reported the SELECT
HOME CITY picker showed both "Britain (London)" and "British Empire
(London)" — base civ AND ANW civ both present. Root cause: civmods
suppression entries ``<civ><name>British</name><main>0</main></civ>``
inherit the base civ's ``<homecityfilename>`` via the engine's merge,
so the base homecity still gets enumerated by that picker.

For each base civ that civmods is hiding (``<main>0</main>``):
  1. Check that the civmods entry also has an empty
     ``<homecityfilename></homecityfilename>`` (or has the field
     overridden to break the inherit-from-base merge).
  2. If the suppression entry lacks the empty homecityfilename, the
     SELECT HOME CITY picker will still show it. Flag as FAIL.

Also flags:
  - Two civmods entries pointing at the same homecity file (would show
    twice in the picker, both as ANW).
  - Any civmods entry referencing a non-existent homecity file path.

Usage::

    python3 tools/validation/validate_no_homecity_doubles.py
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


_CIVMODS = REPO_ROOT / "data" / "civmods.xml"
_BASE_CIVS = REPO_ROOT / "artifacts" / "extracted_base_civs.xml"
_DATA = REPO_ROOT / "data"


def _load_base_homecities() -> dict[str, str]:
    """{base_civ_name: homecityfilename} for every base civ."""
    if not _BASE_CIVS.exists():
        return {}
    out: dict[str, str] = {}
    for c in ET.parse(_BASE_CIVS).getroot().findall("civ"):
        n = c.find("name")
        h = c.find("homecityfilename")
        if n is not None and h is not None and (h.text or "").strip():
            out[n.text] = h.text.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    print("=" * 60)
    print("HOME-CITY PICKER DOUBLES")
    print("=" * 60)

    base_hcs = _load_base_homecities()
    civmods = ET.parse(_CIVMODS).getroot()

    suppress_without_empty_hc: list[tuple[str, str]] = []
    homecity_to_civs: dict[str, list[str]] = defaultdict(list)
    missing_hc_files: list[tuple[str, str]] = []

    for civ in civmods.findall("civ"):
        name = (civ.find("name").text or "").strip() if civ.find("name") is not None else ""
        if not name:
            continue
        main_el = civ.find("main")
        main_v = (main_el.text or "").strip() if main_el is not None else "1"
        hcf_el = civ.find("homecityfilename")
        hcf_v = (hcf_el.text or "").strip() if hcf_el is not None else None

        if main_v == "0":
            # ANW-prefixed names with main=0 are net-new revolution civs.
            # They have no base civ to inherit from — their <homecityfilename>
            # is their own ANW homecity, needed for revolution-dispatch homecity
            # resolution. The picker-doubles check only applies to
            # entries whose <name> matches a base-game civ.
            if name.startswith("ANW"):
                continue
            # Suppression entry. Must have empty homecityfilename
            # to properly hide from SELECT HOME CITY picker.
            if hcf_el is None or hcf_v:
                # The base civ has a homecity, and we didn't blank it →
                # picker will still show base homecity entry alongside
                # any ANW counterpart.
                base_hc = base_hcs.get(name, "(base civ has no hc)")
                suppress_without_empty_hc.append((name, base_hc))
            continue

        # Active civ — collect its homecityfilename
        if hcf_el is not None and hcf_v:
            homecity_to_civs[hcf_v].append(name)
            # Verify file exists
            full = _DATA / hcf_v
            if not full.exists():
                missing_hc_files.append((name, hcf_v))

    duplicate_hc = {k: v for k, v in homecity_to_civs.items() if len(v) > 1}

    fail_count = 0
    print(f"  Suppression entries (main=0): "
          f"{len([c for c in civmods.findall('civ') if c.find('main') is not None and (c.find('main').text or '').strip() == '0'])}")
    print(f"  Suppression entries WITHOUT empty homecityfilename: "
          f"{len(suppress_without_empty_hc)}")
    print(f"  Active civs sharing a homecity file (would double): "
          f"{len(duplicate_hc)}")
    print(f"  Active civs with missing homecityfilename file: "
          f"{len(missing_hc_files)}")
    print()

    if suppress_without_empty_hc:
        fail_count += len(suppress_without_empty_hc)
        print(f"✗ FAIL — {len(suppress_without_empty_hc)} base civ(s) hidden "
              "via main=0 but their <homecityfilename> still inherits from "
              "base — SELECT HOME CITY picker will show duplicate entries:")
        for civ, hc in suppress_without_empty_hc[:15]:
            print(f"    {civ}: base.<homecityfilename>={hc!r}  "
                  "(add empty <homecityfilename></homecityfilename>)")
        if len(suppress_without_empty_hc) > 15:
            print(f"    … +{len(suppress_without_empty_hc) - 15} more")
        print()

    if duplicate_hc:
        fail_count += len(duplicate_hc)
        print(f"✗ FAIL — multiple civmods civs reference the same homecity "
              "file (picker would show twice):")
        for hc, civs in list(duplicate_hc.items())[:10]:
            print(f"    {hc}: {civs}")
        print()

    if missing_hc_files:
        fail_count += len(missing_hc_files)
        print(f"✗ FAIL — civmods <homecityfilename> points at non-existent "
              "file:")
        for civ, hc in missing_hc_files[:10]:
            print(f"    {civ}: {hc}")
        print()

    if not fail_count:
        print("✓ PASS — no doubled-up homecities, no missing files.")

    if args.json:
        import json
        report = {
            "fail_count": fail_count,
            "suppress_without_empty_hc": suppress_without_empty_hc,
            "duplicate_homecities": duplicate_hc,
            "missing_homecity_files": missing_hc_files,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, default=list))

    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
