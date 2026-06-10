#!/usr/bin/env python3
"""Static validator: the nations-and-buildings wiki must not carry misleading
stale placeholders, and the facts those placeholders were replaced with must
stay true.

Born from two real defects fixed in the same pass:

  1. The "## Wall Strategy Index" table once declared "26 civs TBD / not yet
     validated" long after every active civ had an explicit wall strategy.
  2. The three Asian-civ building tables (Chinese / Indian / Japanese) carried
     "Wonder (age-up) | TBD / needs verification" with an "OPEN: proto not
     extracted" note — implying an unfinished mod, when in fact the Asian
     Wonders are pure base-game protounits (ANW defines zero Wonder protos in
     data/protomods.xml), so there is nothing for the mod to list.

This asserts:

  A. The wiki contains none of the misleading stale-placeholder phrases
     ("TBD / needs verification", "not yet validated", "TBD / not yet") that
     falsely signal an incomplete mod.
  B. The base-game-Wonder claim still holds: data/protomods.xml defines no
     Wonder protounit. If a future change adds an ANW Wonder proto, the wiki
     note must be revisited — this fails loudly so it can't go stale silently.

Usage:
    python3 tools/validation/validate_wiki_no_stale_placeholders.py

Exit codes:
    0 — no stale placeholders + base-game-Wonder invariant holds (GREEN)
    1 — stale placeholder found, or an ANW Wonder proto now exists (RED)
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "docs" / "wiki" / "validation" / "nations-and-buildings.md"
PROTOS = REPO / "data" / "protomods.xml"

# Phrases that falsely signal an unfinished mod / unresolved claim. Each was a
# real defect: bare uncertainty markers left in shipped wiki tables long after
# the underlying fact was verifiable from data/techtreemods.xml + protomods.xml.
STALE_PHRASES = [
    "TBD / needs verification",
    "not yet validated",
    "TBD / not yet",
    "NEEDS VERIFY",
]


def stale_placeholder_errors() -> list[str]:
    errors: list[str] = []
    text = WIKI.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        for phrase in STALE_PHRASES:
            if phrase.lower() in line.lower():
                errors.append(
                    f"{WIKI.relative_to(REPO)}:{i}: stale placeholder "
                    f"'{phrase}' — replace with the verified fact")
    return errors


def wonder_proto_errors() -> list[str]:
    """The wiki Asian-Wonder note asserts ANW defines no Wonder proto. Lock it."""
    if not PROTOS.exists():
        return [f"{PROTOS.relative_to(REPO)} missing — cannot verify Wonder invariant"]
    root = ET.parse(PROTOS).getroot()
    offenders = []
    for unit in root.iter("unit"):
        name = (unit.findtext("name") or "")
        if re.search(r"wonder", name, re.IGNORECASE):
            offenders.append(name)
    if offenders:
        return [
            "data/protomods.xml now defines Wonder protounit(s): "
            + ", ".join(sorted(offenders))
            + " — the wiki Asian-Wonder note ('ANW defines no Wonder protos') "
            "is now stale and must be updated."
        ]
    return []


def main() -> int:
    errors = stale_placeholder_errors() + wonder_proto_errors()

    print("Wiki stale-placeholder + base-game-Wonder invariant check")
    print(f"  wiki: {WIKI.relative_to(REPO)}")
    print()

    if errors:
        print("FAIL — wiki carries stale placeholders or the Wonder invariant broke:")
        for e in errors:
            print(f"  {e}")
        return 1

    print("PASS — no stale placeholders; ANW defines no Wonder proto "
          "(Asian-Wonder note remains accurate).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
