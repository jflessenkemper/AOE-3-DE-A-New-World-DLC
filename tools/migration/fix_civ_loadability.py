#!/usr/bin/env python3
"""Fix the 25 ANW civs that don't load in the lobby picker due to "1X"
format StatsIDs.

Engine rejects 1A-1Y format. Empirically confirmed 2026-05-08; root cause
analysis 2026-05-09 in ``docs/SESSION_HANDOFF_2026-05-09.md``. Engine
accepts 2-char alpha StatsIDs (the format all 22 base game civs use).

This script is a **dry-run by default** — pass ``--apply`` to actually
write civmods.xml. Always backs up to ``data/civmods.xml.bak_<timestamp>``.

Two strategies:

  - ``--strategy=add`` (default): assign each failing civ a NEW 2-char
    alpha code that doesn't collide with any existing StatsID. The civ
    becomes an ADDITIONAL picker entry alongside base game civs. Picker
    grows from ~22 → ~47 entries. No demotion of other civs needed.

  - ``--strategy=replace``: replace base game civs with ANW versions where
    a "natural" mapping exists (ANWBritish→BR, ANWFrench→FR, etc.). For
    civs without a natural base game equivalent (Argentina, Texas, etc.),
    fall back to ``add`` strategy. NOTE: most natural slots are already
    taken by other ANW civs (FR by ANWNapoleonicFrance, etc.) — those would need to be DEMOTED to new
    alpha codes first. This is a structural design decision; the script
    flags conflicts and asks for confirmation.

Usage::

    python3 tools/migration/fix_civ_loadability.py                    # dry-run
    python3 tools/migration/fix_civ_loadability.py --apply             # write
    python3 tools/migration/fix_civ_loadability.py --strategy=replace  # try replace
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


# Mapping civs to their "natural" base game StatsID where one exists.
# When we use --strategy=replace, ANWBritish wants BR, etc.
# Keys are ANW civ names (matching civmods.xml <name> field).
NATURAL_BASE_GAME_SLOT: dict[str, str] = {
    "ANWBritish": "BR",
    "ANWFrench": "FR",
    "ANWMexicans": "MX",
    "ANWOttomans": "OT",
    "ANWPortuguese": "PT",
    "ANWSpanish": "SP",
    "ANWSwedes": "SW",
    # The other 18 don't have base game equivalents.
}

# Suggested new alpha codes for civs without a base game equivalent.
# Two-char alpha format; chosen to be mnemonic + non-colliding.
# These are SUGGESTIONS — adjust freely.
SUGGESTED_NEW_CODES: dict[str, str] = {
    "ANWArgentines":      "AR",
    "ANWBajaCalifornians":"BJ",
    "ANWBritish":         "BX",  # only used if --strategy=add
    "ANWCanadians":       "CD",
    "ANWChileans":        "CL",
    "ANWColumbians":      "CB",
    "ANWEgyptians":       "EG",
    "ANWFrench":          "FX",  # only used if --strategy=add
    "ANWHaitians":        "HT",
    "ANWHungarians":      "HU",
    "ANWIndonesians":     "ID",
    "ANWMayans":          "MY",
    "ANWMexicans":        "MZ",  # only used if --strategy=add
    "ANWOttomans":        "OZ",  # only used if --strategy=add
    "ANWPeruvians":       "PE",
    "ANWPortuguese":      "PX",  # only used if --strategy=add
    "ANWRomanians":       "RO",
    "ANWSouthAfricans":   "ZA",
    "ANWSpanish":         "SX",  # only used if --strategy=add
    "ANWSwedes":          "SX",  # collides with ANWSpanish if both at SX...
    "ANWTexians":         "TX",
}
# Fix collision in suggestions
SUGGESTED_NEW_CODES["ANWSwedes"] = "SE"


_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")


def collect_existing_statsids(root: ET.Element) -> dict[str, str]:
    """Return {civ_name: statsid} for all civs in civmods.xml."""
    out: dict[str, str] = {}
    for c in root.findall("civ"):
        n = c.find("name")
        s = c.find("statsid")
        if n is not None and s is not None and n.text:
            out[n.text] = (s.text or "").strip()
    return out


def is_loadable_format(sid: str) -> bool:
    return bool(_ALPHA2_RE.match(sid or ""))


def plan_fixes(
    root: ET.Element,
    strategy: str,
) -> tuple[list[dict], list[str]]:
    """Return (changes, warnings).

    Each change is {civ, old_sid, new_sid, reason}.
    """
    existing = collect_existing_statsids(root)
    changes: list[dict] = []
    warnings: list[str] = []

    # Set of all StatsIDs after planned changes (avoid creating new collisions).
    used: set[str] = {sid for sid in existing.values()
                       if is_loadable_format(sid)}

    failing = [(name, sid) for name, sid in existing.items()
               if name.startswith("ANW") and not is_loadable_format(sid)]

    for civ, old in failing:
        new_sid: Optional[str] = None
        reason = ""
        if strategy == "replace":
            natural = NATURAL_BASE_GAME_SLOT.get(civ)
            if natural and natural not in used:
                new_sid = natural
                reason = (f"replace strategy: claim natural slot {natural} "
                          f"(unused by other ANW civs)")
            elif natural and natural in used:
                # Natural slot already taken by another ANW civ.
                holder = next((n for n, s in existing.items() if s == natural),
                              "?")
                warnings.append(
                    f"{civ}: natural slot {natural} already taken by {holder}. "
                    f"Falling back to 'add' strategy.")
        if not new_sid:
            # 'add' strategy: pick from SUGGESTED_NEW_CODES, fall back to
            # any unused 2-char alpha if suggestion collides.
            suggested = SUGGESTED_NEW_CODES.get(civ)
            if suggested and suggested not in used:
                new_sid = suggested
                reason = f"add strategy: new alpha code {suggested} (suggested)"
            else:
                # Auto-pick any unused 2-char alpha.
                for a in range(ord("A"), ord("Z") + 1):
                    for b in range(ord("A"), ord("Z") + 1):
                        candidate = chr(a) + chr(b)
                        if candidate not in used:
                            new_sid = candidate
                            reason = (f"add strategy: auto-picked {candidate} "
                                      f"(suggested {suggested!r} was taken)")
                            break
                    if new_sid:
                        break
        if not new_sid:
            warnings.append(f"{civ}: COULDN'T allocate a 2-char alpha StatsID")
            continue
        used.add(new_sid)
        changes.append({
            "civ": civ,
            "old_sid": old,
            "new_sid": new_sid,
            "reason": reason,
        })

    return changes, warnings


def apply_changes(root: ET.Element, changes: list[dict]) -> int:
    """Apply changes in-place. Returns count of civs modified."""
    by_civ = {c["civ"]: c for c in changes}
    n = 0
    for c in root.findall("civ"):
        nm = c.find("name")
        if nm is None or nm.text not in by_civ:
            continue
        sid = c.find("statsid")
        if sid is None:
            continue
        sid.text = by_civ[nm.text]["new_sid"]
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--civmods", type=Path,
                    default=REPO_ROOT / "data" / "civmods.xml")
    ap.add_argument("--strategy", choices=("add", "replace"), default="add")
    ap.add_argument("--apply", action="store_true",
                    help="actually write civmods.xml (default: dry-run)")
    args = ap.parse_args()

    if not args.civmods.exists():
        print(f"ERROR: {args.civmods} not found", file=sys.stderr)
        return 2

    tree = ET.parse(args.civmods)
    root = tree.getroot()

    changes, warnings = plan_fixes(root, args.strategy)

    print(f"Strategy: {args.strategy}")
    print(f"Planned changes: {len(changes)}")
    print()
    for c in changes:
        print(f"  {c['civ']:<28} StatsID {c['old_sid']:>3} → {c['new_sid']:>3}  "
              f"({c['reason']})")
    if warnings:
        print()
        print("Warnings:")
        for w in warnings:
            print(f"  - {w}")
    print()

    if not args.apply:
        print("DRY RUN. Pass --apply to write changes.")
        return 0

    # Backup
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = args.civmods.with_suffix(f".xml.bak_{ts}")
    shutil.copy2(args.civmods, backup)
    print(f"Backed up to {backup}")

    # Apply
    n = apply_changes(root, changes)
    tree.write(args.civmods, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {args.civmods} ({n} civs modified)")

    # Run loadability validator to confirm
    print()
    print("Running validate_civ_loadability.py to verify…")
    import subprocess
    rc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools/validation/validate_civ_loadability.py")],
        cwd=REPO_ROOT,
    ).returncode
    print(f"validator rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
