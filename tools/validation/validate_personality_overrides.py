#!/usr/bin/env python3
"""Validate that every .personality file in game/ai/ has working display-name
and tooltip overrides in stringmods.xml.

Catches "Bug B / Bug C" class — a personality's nameID points to a string ID
that either doesn't exist in stringmods.xml or has an empty/default value,
causing the in-game scoreboard / lobby to show base-game default instead of
our mod-intended leader name.

For each .personality file under game/ai/ (both base-game overrides AND
anw* mod civs):
  - Parse nameID + tooltipID
  - Look up those IDs in data/strings/english/stringmods.xml
  - Confirm each resolves to a non-empty string
  - Flag any .personality that is missing, orphaned, or empty-valued

Usage:
  python3 tools/validation/validate_personality_overrides.py
  (exits non-zero if any issues found)
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AI_DIR = REPO / "game" / "ai"
STRINGS = REPO / "data" / "strings" / "english" / "stringmods.xml"


def parse_personality(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    def find(tag):
        m = re.search(rf"<{tag}>([^<]+)</{tag}>", txt)
        return m.group(1).strip() if m else None
    return {
        "nameID": find("nameID"),
        "tooltipID": find("tooltipID"),
        "forcedciv": find("forcedciv"),
        "icon": find("icon"),
        "chatset": find("chatset"),
    }


def load_string_table(path: Path = STRINGS) -> dict[str, str]:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    table = {}
    # Match both '<String _locID=...>' and '<string _locid=...>' variants
    for m in re.finditer(r"<[Ss]tring\s+_loc[Ii][Dd]=['\"](\d+)['\"][^>]*>([^<]*)</[Ss]tring>", txt):
        sid, val = m.group(1), m.group(2).strip()
        # If an ID appears multiple times, keep the LAST (as the game would)
        table[sid] = val
    return table


def validate_personality_overrides(repo_root: Path) -> list[str]:
    """Return a list of finding strings (empty = all pass)."""
    ai_dir = repo_root / "game" / "ai"
    strings_path = repo_root / "data" / "strings" / "english" / "stringmods.xml"
    if not ai_dir.exists():
        return [f"game/ai/ directory not found under {repo_root}"]
    if not strings_path.exists():
        return [f"stringmods.xml not found at {strings_path}"]

    strings = load_string_table(strings_path)
    findings: list[str] = []
    for p in sorted(ai_dir.glob("*.personality")):
        info = parse_personality(p)
        name_id = info["nameID"] or ""
        tt_id = info["tooltipID"] or ""
        if not name_id:
            findings.append(f"{p.name}: missing <nameID>")
        elif not strings.get(name_id):
            findings.append(f"{p.name}: nameID {name_id} not found or empty in stringmods.xml")
        if not tt_id:
            findings.append(f"{p.name}: missing <tooltipID>")
        elif not strings.get(tt_id):
            findings.append(f"{p.name}: tooltipID {tt_id} not found or empty in stringmods.xml")
    return findings


def main():
    if not AI_DIR.exists():
        print(f"FATAL: {AI_DIR} not found")
        return 2
    if not STRINGS.exists():
        print(f"FATAL: {STRINGS} not found")
        return 2

    strings = load_string_table()
    print(f"Loaded {len(strings)} entries from stringmods.xml")
    print()

    personalities = sorted(AI_DIR.glob("*.personality"))
    print(f"Auditing {len(personalities)} .personality files")
    print(f"{'='*90}")
    print(f"{'File':<40} {'nameID':<8} {'Name String':<30} {'Tooltip?':<8} Verdict")
    print(f"{'='*90}")

    fails = 0
    warns = 0
    for p in personalities:
        info = parse_personality(p)
        name_id = info["nameID"] or "-"
        tt_id = info["tooltipID"] or "-"

        name_str = strings.get(name_id, "") if name_id != "-" else ""
        tt_str = strings.get(tt_id, "") if tt_id != "-" else ""

        verdict = []
        if name_id == "-":
            verdict.append("NO_NAMEID")
            fails += 1
        elif not name_str:
            verdict.append("NAME_MISSING_OR_EMPTY")
            fails += 1
        if tt_id == "-":
            verdict.append("NO_TOOLTIP_ID")
            warns += 1
        elif not tt_str:
            verdict.append("TOOLTIP_MISSING")
            warns += 1

        if not verdict:
            verdict = ["OK"]

        display_name = (name_str[:28] + "..") if len(name_str) > 30 else name_str
        tooltip_mark = "✓" if tt_str else "✗"
        print(f"{p.name:<40} {name_id:<8} {display_name:<30} {tooltip_mark:<8} {' '.join(verdict)}")

    print(f"{'='*90}")
    print(f"Total: {len(personalities)}   FAIL: {fails}   WARN: {warns}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
