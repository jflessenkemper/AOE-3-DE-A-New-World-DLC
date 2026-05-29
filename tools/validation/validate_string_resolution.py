#!/usr/bin/env python3
"""Verify every NameID/RolloverNameID/etc. in civmods.xml resolves in stringmods.

We hit this class of bug indirectly on 2026-05-08: an ANW civ used a
DisplayNameID pointing at a _locID that didn't exist (or pointed at the
wrong text after dedup). The engine silently falls back to the integer
ID as a string ("410100" rendered as a literal). Catching unresolved
NameIDs pre-deploy avoids that.

For each ANW civ, this validator confirms that the _locID values in:
  - DisplayNameID
  - RolloverNameID
  - AlliedID, AlliedOtherID, UnAlliedID

…each have a corresponding ``<String _locID="…">`` entry in some
``stringmods*.xml`` file under ``data/strings/<lang>/``. If a referenced
ID is missing, the validator FAILs.

Usage::

    python3 tools/validation/validate_string_resolution.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


# Civmods fields whose values are _locID integers.
_NAMEID_FIELDS = (
    "displaynameid",
    "rollovernameid",
    "alliedid",
    "alliedotherid",
    "unalliedid",
)


def collect_string_ids(strings_dir: Path) -> set[str]:
    """Collect every _locID present in any stringmods*.xml under strings_dir."""
    ids: set[str] = set()
    for f in strings_dir.rglob("stringmods*.xml"):
        text = f.read_text(encoding="utf-8", errors="replace")
        ids.update(re.findall(r'_locID="(\d+)"', text))
    return ids


def collect_referenced_ids(civmods: Path) -> dict[str, list[tuple[str, str]]]:
    """Return {locid: [(civ_token, field_name), ...]}."""
    if not civmods.exists():
        raise FileNotFoundError(civmods)
    root = ET.parse(civmods).getroot()
    refs: dict[str, list[tuple[str, str]]] = {}
    for c in root.findall("civ"):
        n = c.find("name")
        if n is None or not (n.text or "").startswith("ANW"):
            continue
        token = n.text
        for field in _NAMEID_FIELDS:
            e = c.find(field)
            if e is None or not (e.text or "").strip():
                continue
            v = e.text.strip()
            if v.isdigit():
                refs.setdefault(v, []).append((token, field))
    return refs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--civmods", type=Path,
                    default=REPO_ROOT / "data" / "civmods.xml")
    ap.add_argument("--strings-dir", type=Path,
                    default=REPO_ROOT / "data" / "strings")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not args.civmods.exists():
        print(f"ERROR: {args.civmods} not found", file=sys.stderr)
        return 2

    available = collect_string_ids(args.strings_dir)
    refs = collect_referenced_ids(args.civmods)

    print("=" * 60)
    print("STRING RESOLUTION (civmods.xml NameIDs vs stringmods.xml)")
    print("=" * 60)
    print(f"Available _locIDs in stringmods (deployed):  {len(available):>5}")
    print(f"Referenced _locIDs in civmods.xml NameIDs:   {len(refs):>5}")
    print()

    # Note: many DisplayNameIDs point at base-game string IDs (e.g. 410100
    # = base game "British"). Those won't be in our local stringmods.xml
    # because they're owned by base game's stringtable*.xml inside the .bar.
    # We treat 4XXXXX (base game range) as "trusted to resolve in base
    # game stringtable" and ANW range (49XXXX) as "must be in our mod's
    # stringmods.xml".
    failed = []
    base_range = []
    for locid, sources in sorted(refs.items()):
        if locid in available:
            continue
        # Empirically-verified base-game range (10670-230102 from
        # Game/Data.bar:strings/English/stringtabley.xml extracted via
        # tools/cardextract). Anything outside that range AND outside our
        # stringmods is unresolved.
        if 10670 <= int(locid) <= 230102:
            base_range.append((locid, sources))
        else:
            failed.append((locid, sources))

    print(f"Resolved (in stringmods.xml): {len(refs) - len(failed) - len(base_range)}")
    print(f"In base-game string range (assumed safe): {len(base_range)}")
    print(f"FAIL — referenced but not in our stringmods.xml AND not "
          f"in base-game range: {len(failed)}")
    print()

    if failed:
        print("FAIL:")
        for locid, sources in failed[:30]:
            srcs = ", ".join(f"{civ}.{field}" for civ, field in sources)
            print(f"  _locID={locid} referenced by: {srcs}")
        if len(failed) > 30:
            print(f"  … +{len(failed) - 30} more")

    if args.json:
        import json
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({
                "available_count": len(available),
                "referenced_count": len(refs),
                "failed_count": len(failed),
                "base_range_count": len(base_range),
                "failed": [(l, [list(s) for s in src])
                            for l, src in failed],
            }, f, indent=2)
        print(f"Report: {args.json}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
