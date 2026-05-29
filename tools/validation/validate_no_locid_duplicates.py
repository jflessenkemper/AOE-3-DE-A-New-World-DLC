#!/usr/bin/env python3
"""Catch stringmods.xml duplicate _locID values that render wrong text in-game.

We hit this on 2026-05-08: ``stringmods.xml`` had 42 _locID values
duplicated with CONFLICTING text (e.g. _locID=490206 had both
"Maurice of Nassau" AND "Frederick the Great transformed Prussia…").
Engine resolution of duplicate _locIDs is undefined — the lobby rendered
"Friedrich the Great" for ANWDutch.

This validator scans every stringmods*.xml under data/strings/ and
fails if ANY _locID has more than one ``<String>`` entry.

Usage::

    python3 tools/validation/validate_no_locid_duplicates.py
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def find_duplicates(text: str) -> dict[str, int]:
    """Return {locid: count} for any locid appearing more than once."""
    ids = re.findall(r'_locID="(\d+)"', text)
    c = Counter(ids)
    return {k: v for k, v in c.items() if v > 1}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strings-dir", type=Path,
                    default=REPO_ROOT / "data" / "strings")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if not args.strings_dir.exists():
        print(f"ERROR: {args.strings_dir} not found", file=sys.stderr)
        return 2

    files = list(args.strings_dir.rglob("stringmods*.xml"))
    if not files:
        print(f"WARN: no stringmods*.xml files found under {args.strings_dir}",
              file=sys.stderr)
        return 0

    overall_dups = 0
    per_file = []
    print("=" * 60)
    print("STRINGMODS LOCID DUPLICATES")
    print("=" * 60)
    for f in sorted(files):
        text = f.read_text(encoding="utf-8", errors="replace")
        dups = find_duplicates(text)
        per_file.append({"file": str(f.relative_to(REPO_ROOT)),
                         "duplicate_count": len(dups),
                         "duplicates": dups})
        rel = f.relative_to(REPO_ROOT)
        if dups:
            print(f"  ✗ {rel}: {len(dups)} duplicated _locID(s)")
            for k, v in sorted(dups.items())[:5]:
                print(f"      _locID={k} appears {v}× — "
                      f"engine resolution UNDEFINED, can render wrong text in-game")
            if len(dups) > 5:
                print(f"      … +{len(dups) - 5} more")
            overall_dups += len(dups)
        else:
            print(f"  ✓ {rel}: 0 duplicates")

    print()
    print(f"Total duplicate _locIDs across all files: {overall_dups}")

    if args.json:
        import json
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({"per_file": per_file,
                       "total_duplicates": overall_dups}, f, indent=2)
        print(f"Report: {args.json}")

    return 1 if overall_dups else 0


if __name__ == "__main__":
    sys.exit(main())
