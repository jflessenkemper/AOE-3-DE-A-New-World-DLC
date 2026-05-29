#!/usr/bin/env python3
"""Catch orphan XML shadow files that confuse validators and the engine.

We hit this on 2026-05-08: ``data/civmods.anw.xml`` shadowed
``data/civmods.xml`` for half the validator suite, while the engine read
``civmods.xml``. Edits applied to one file silently didn't take effect
because the other was the actual source-of-truth. We deleted that one,
but the pattern can recur: any ``foo.anw.xml`` next to ``foo.xml``, or
any ``*.proposed`` extension that's a stale dev artifact.

This validator scans ``data/`` and ``game/`` and flags:
  - ``*.anw.xml`` files where a sibling ``*.xml`` exists (likely shadow)
  - ``*.proposed`` files anywhere (stale dev work-in-progress)
  - ``*.bak*`` files in source dirs (should be in artifacts/)

Usage::

    python3 tools/validation/validate_no_orphan_xml.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def find_orphans(roots: list[Path]) -> dict[str, list[Path]]:
    """Return {category: [paths]}."""
    out: dict[str, list[Path]] = {
        "anw_shadow": [],
        "proposed": [],
        "backup": [],
    }
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            name = p.name
            if name.endswith(".anw.xml"):
                # Check if a sibling .xml exists with same prefix
                primary = p.with_name(name.replace(".anw.xml", ".xml"))
                if primary.exists():
                    out["anw_shadow"].append(p)
            if name.endswith(".proposed") or name.endswith(".xml.proposed"):
                out["proposed"].append(p)
            if ".bak" in name and name not in ("backups",):
                # Tolerate backups inside artifacts/ (those are intentional)
                if "artifacts/" not in str(p):
                    out["backup"].append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path,
                    default=REPO_ROOT / "data")
    ap.add_argument("--game-dir", type=Path,
                    default=REPO_ROOT / "game")
    ap.add_argument("--allow-proposed", action="store_true",
                    help="treat .proposed files as warnings instead of fail")
    args = ap.parse_args()

    orphans = find_orphans([args.data_dir, args.game_dir])

    print("=" * 60)
    print("ORPHAN XML / SHADOW FILE CHECK")
    print("=" * 60)
    total_fail = 0
    total_warn = 0

    if orphans["anw_shadow"]:
        print(f"\n✗ {len(orphans['anw_shadow'])} .anw.xml shadow file(s) "
              f"(sibling .xml exists — pick one as canonical):")
        for p in orphans["anw_shadow"][:10]:
            print(f"    {p.relative_to(REPO_ROOT)}")
        total_fail += len(orphans["anw_shadow"])
    else:
        print("✓ No .anw.xml shadow files")

    if orphans["proposed"]:
        marker = "⚠" if args.allow_proposed else "✗"
        cat = "WARN" if args.allow_proposed else "FAIL"
        print(f"\n{marker} {len(orphans['proposed'])} .proposed file(s) "
              f"(dev work-in-progress; engine ignores) — {cat}:")
        for p in orphans["proposed"][:15]:
            print(f"    {p.relative_to(REPO_ROOT)}")
        if len(orphans["proposed"]) > 15:
            print(f"    … +{len(orphans['proposed']) - 15} more")
        if args.allow_proposed:
            total_warn += len(orphans["proposed"])
        else:
            total_fail += len(orphans["proposed"])
    else:
        print("✓ No .proposed files")

    if orphans["backup"]:
        print(f"\n⚠ {len(orphans['backup'])} .bak file(s) in source dirs "
              f"(should live in artifacts/):")
        for p in orphans["backup"][:10]:
            print(f"    {p.relative_to(REPO_ROOT)}")
        total_warn += len(orphans["backup"])
    else:
        print("✓ No .bak files in source dirs")

    print()
    print(f"FAIL: {total_fail}  WARN: {total_warn}")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
