#!/usr/bin/env python3
"""Pre-flight check that every ANW personality has a consistent lobby quadruple.

For every ``anw*.personality`` file under ``game/ai/`` this validator checks:

1. ``<nameID>`` resolves in stringmods.xml to a non-empty string.
2. ``<tooltipID>`` resolves in stringmods.xml to a non-empty string.
3. ``<icon>`` path resolves to a real file under the repo root.
4. ``<forcedciv>`` token exists as a ``<name>`` entry in civmods.xml.

Bug-class context (2026-05-08): locID duplicates caused wrong lobby text;
portrait DDTs with wrong format bytes caused blank AI portraits; forcedciv
typos caused the engine to fall back to a base-game civ silently.

Usage::

    python3 tools/validation/validate_personality_lobby.py
    python3 tools/validation/validate_personality_lobby.py \\
        --json artifacts/validation/personality_lobby.json
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _find_tag(text: str, tag: str) -> str | None:
    """Return first text content of <tag>…</tag>, or None."""
    m = re.search(rf"<{tag}>([^<]+)</{tag}>", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_personality(path: Path) -> dict[str, str | None]:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "nameID":    _find_tag(txt, "nameID"),
        "tooltipID": _find_tag(txt, "tooltipID"),
        "icon":      _find_tag(txt, "icon"),
        "forcedciv": _find_tag(txt, "forcedciv"),
    }


def load_string_table(path: Path) -> dict[str, str]:
    """Return {locID_str: text} for every <String _locID="…">…</String> entry.

    If an ID appears multiple times the last entry wins (matches engine
    behaviour — see validate_no_locid_duplicates.py for the canonical
    explanation).
    """
    txt = path.read_text(encoding="utf-8", errors="replace")
    table: dict[str, str] = {}
    for m in re.finditer(
        r"<[Ss]tring\s+_loc[Ii][Dd]=['\"](\d+)['\"][^>]*>([^<]*)</[Ss]tring>", txt
    ):
        table[m.group(1)] = m.group(2).strip()
    return table


def load_civ_names(path: Path) -> set[str]:
    """Return the set of <name> values from civmods.xml."""
    txt = path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"<name>([^<]+)</name>", txt))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ai-dir", type=Path,
                    default=REPO_ROOT / "game" / "ai",
                    help="directory containing *.personality files")
    ap.add_argument("--strings-file", type=Path,
                    default=REPO_ROOT / "data" / "strings" / "english" / "stringmods.xml",
                    help="stringmods.xml to resolve locIDs against")
    ap.add_argument("--civmods", type=Path,
                    default=REPO_ROOT / "data" / "civmods.xml",
                    help="civmods.xml to validate forcedciv tokens")
    ap.add_argument("--json", type=Path,
                    metavar="PATH",
                    help="write JSON report to PATH (e.g. artifacts/validation/personality_lobby.json)")
    args = ap.parse_args()

    # --- sanity-check inputs -----------------------------------------------
    errors: list[str] = []
    for label, p in [("--ai-dir", args.ai_dir),
                     ("--strings-file", args.strings_file),
                     ("--civmods", args.civmods)]:
        if not p.exists():
            errors.append(f"ERROR: {label} path not found: {p}")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 2

    # --- load shared data tables -------------------------------------------
    strings   = load_string_table(args.strings_file)
    civ_names = load_civ_names(args.civmods)

    personalities = sorted(args.ai_dir.glob("anw*.personality"))
    if not personalities:
        print(f"WARN: no anw*.personality files found under {args.ai_dir}",
              file=sys.stderr)
        return 0

    print("=" * 60)
    print("ANW PERSONALITY LOBBY QUADRUPLE CHECK")
    print("=" * 60)
    print(f"  stringmods entries : {len(strings)}")
    print(f"  civmods civ names  : {len(civ_names)}")
    print(f"  personality files  : {len(personalities)}")
    print()

    fail_count = 0
    report_entries: list[dict] = []

    for p in personalities:
        info = parse_personality(p)
        name_id    = info["nameID"]
        tooltip_id = info["tooltipID"]
        icon_path  = info["icon"]
        forced_civ = info["forcedciv"]

        fails: list[str] = []
        details: dict[str, str] = {}

        # 1. nameID -----------------------------------------------------------
        if not name_id:
            fails.append("missing <nameID>")
            details["name"] = "MISSING"
        else:
            name_text = strings.get(name_id, "")
            if name_text:
                details["name"] = f"{name_text!r} (locID={name_id})"
            else:
                fails.append(f"nameID {name_id} not found in stringmods")
                details["name"] = f"MISSING locID={name_id}"

        # 2. tooltipID --------------------------------------------------------
        if not tooltip_id:
            fails.append("missing <tooltipID>")
            details["tooltip"] = "MISSING"
        else:
            tt_text = strings.get(tooltip_id, "")
            if tt_text:
                details["tooltip"] = f"OK (locID={tooltip_id})"
            else:
                fails.append(f"tooltipID {tooltip_id} not found in stringmods")
                details["tooltip"] = f"MISSING locID={tooltip_id}"

        # 3. icon / portrait --------------------------------------------------
        if not icon_path:
            fails.append("missing <icon>")
            details["portrait"] = "MISSING"
        else:
            resolved = REPO_ROOT / icon_path
            if resolved.exists():
                details["portrait"] = f"OK ({icon_path})"
            else:
                fails.append(f"icon path not found: {icon_path}")
                details["portrait"] = f"MISSING {icon_path}"

        # 4. forcedciv --------------------------------------------------------
        if not forced_civ:
            fails.append("missing <forcedciv>")
            details["forcedciv"] = "MISSING"
        else:
            if forced_civ in civ_names:
                details["forcedciv"] = f"OK ({forced_civ})"
            else:
                fails.append(f"forcedciv '{forced_civ}' not found in civmods.xml")
                details["forcedciv"] = f"MISSING {forced_civ}"

        # --- per-personality output ----------------------------------------
        label = p.stem  # e.g. "anwbritish"
        if fails:
            fail_count += len(fails)
            for msg in fails:
                print(f"  \u2717 {label}: {msg}")
        else:
            name_display = details.get("name", "?")
            tt_display   = details.get("tooltip", "?")
            portrait_ok  = details.get("portrait", "?")
            civ_ok       = details.get("forcedciv", "?")
            print(f"  \u2713 {label}: name={name_display}, "
                  f"tooltip={tt_display}, portrait={portrait_ok}, "
                  f"forcedciv={civ_ok}")

        report_entries.append({
            "file": p.name,
            "nameID": name_id,
            "tooltipID": tooltip_id,
            "icon": icon_path,
            "forcedciv": forced_civ,
            "details": details,
            "fails": fails,
        })

    # --- summary -----------------------------------------------------------
    print()
    print(f"Total personalities: {len(personalities)}")
    print(f"Total FAILs:         {fail_count}")
    print()
    if fail_count:
        print("OVERALL: FAIL")
    else:
        print("OVERALL: PASS")

    # --- optional JSON report ----------------------------------------------
    if args.json:
        import json
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump({
                "total_personalities": len(personalities),
                "total_fails": fail_count,
                "overall": "FAIL" if fail_count else "PASS",
                "entries": report_entries,
            }, fh, indent=2)
        print(f"Report: {args.json}")

    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
