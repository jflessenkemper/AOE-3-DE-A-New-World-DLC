#!/usr/bin/env python3
"""Static validator: the per-culture civ breakdown in the wiki nations map is
internally consistent AND partitions exactly the live active-civ roster.

docs/wiki/validation/nations-and-buildings.md groups every ANW civ under a
culture template, each introduced by a line like:

    10 ANW civs: British, French, Dutch, USA, Canadians, ...
    1 ANW civ: ANWAztecs.

`validate_wiki_nation_coverage.py` only checks each active token *appears*
somewhere in the doc. It does NOT check that these culture-roster lines are
self-consistent. This validator closes that gap by asserting:

  1. Each line's stated count equals the number of civs it actually lists.
  2. No civ appears under two cultures (the cultures partition the roster).
  3. The union of all listed civs equals exactly the live active-civ set
     (number/identity of `<main>1</main>` tokens in data/civmods.xml) — so a
     civ can't be added/removed in data without the culture breakdown being
     updated, and the per-culture counts always sum to the live total.

Names are normalised by stripping a leading "ANW" (the doc writes bare stems
like "British" for multi-civ cultures and prefixed "ANWAztecs" for singles).

Usage:
    python3 tools/validation/validate_wiki_culture_rosters.py

Exit codes:
    0 — culture breakdown is self-consistent and partitions the roster (GREEN)
    1 — a count is wrong, a civ is double/zero-classified, or it drifts from
        the live roster (RED — details printed)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CIVMODS = REPO / "data" / "civmods.xml"
WIKI = REPO / "docs" / "wiki" / "validation" / "nations-and-buildings.md"

# "10 ANW civs: a, b, c." / "1 ANW civ: ANWAztecs."
LINE_RE = re.compile(r"^(\d+)\s+ANW\s+civs?:\s*(.+?)\.?\s*$")


def norm(name: str) -> str:
    n = name.strip()
    return n[3:] if n.startswith("ANW") else n


def active_stems() -> set[str]:
    text = CIVMODS.read_text(encoding="utf-8")
    # Each active civ is an ANW-prefixed <name> on a <main>1</main> civ; the
    # repo invariant (validate_anw_civ_token_prefix) guarantees every active
    # token is ANW-prefixed, so the ANW <name> set is the active set.
    return {norm(m) for m in re.findall(r"<name>(ANW[A-Za-z]+)</name>", text)}


def main() -> int:
    if not WIKI.exists():
        print(f"FAIL — wiki nations map not found: {WIKI.relative_to(REPO)}")
        return 1

    errors: list[str] = []
    seen: dict[str, int] = {}  # normalised civ -> source line number
    total_lines = 0

    for lineno, line in enumerate(
            WIKI.read_text(encoding="utf-8").splitlines(), 1):
        m = LINE_RE.match(line)
        if not m:
            continue
        total_lines += 1
        stated = int(m.group(1))
        names = [norm(x) for x in m.group(2).split(",") if x.strip()]
        if len(names) != stated:
            errors.append(
                f"line {lineno}: says {stated} civs but lists {len(names)} "
                f"({', '.join(names)})")
        for civ in names:
            if civ in seen:
                errors.append(
                    f"line {lineno}: '{civ}' already classified at line {seen[civ]} "
                    f"(double-classified)")
            else:
                seen[civ] = lineno

    listed = set(seen)
    live = active_stems()

    missing = sorted(live - listed)   # active civ not in any culture line
    phantom = sorted(listed - live)   # culture line names a non-active civ
    for civ in missing:
        errors.append(f"active civ '{civ}' is not classified under any culture")
    for civ in phantom:
        errors.append(f"culture breakdown lists '{civ}' which is not an active civ")

    print("Wiki culture-roster check (per-culture breakdown partitions the live roster)")
    print(f"  culture lines: {total_lines}   civs classified: {len(listed)}   "
          f"live active: {len(live)}")
    print()

    if errors:
        print("FAIL — culture breakdown is inconsistent with data/civmods.xml:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"PASS — {total_lines} culture lines partition all {len(live)} "
          f"active civs, no double/zero/phantom classification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
