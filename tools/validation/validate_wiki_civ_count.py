#!/usr/bin/env python3
"""Static validator: every concrete "N ANW civ" roster-count claim in the wiki
must equal the live active-civ count in data/civmods.xml.

The authoritative active-civ count is the number of `<civ>` blocks carrying
`<main>1</main>` in data/civmods.xml (suppression entries for hidden base
civs are NOT active and are excluded). Today that is 44.

Born from a drift where three docs (data-layer/civmods.md,
additive-data-mods.md, modding-pitfalls/case-sensitivity.md) carried a stale
"restored 46 ANW civs" historical note while every other doc — and the live
data — says 44. Git history shows the active roster grew 40 -> 44 and was
never 46 in the `<main>`-era, so the "46" was an unreproducible figure that
contradicted the verifiable count. This validator pins the number so any
future roster change (44 -> 45, etc.) forces every doc to update in lockstep,
in BOTH directions.

Matched claim shapes (deliberately narrow to TOTAL-roster assertions, so the
validator does NOT catch the per-culture sub-group counts that legitimately
sum to the total — e.g. "10 ANW civs are European" — nor the 66 total `<civ>`
blocks or "416 units"):
  * "<N> ANW civ token..."      e.g. "44 ANW civ tokens"  (full token set)
  * "all <N> [ANW] civ..."      e.g. "all 44 civs", "all 44 ANW civ tokens"

Approximate ("~44 civs") and qualified ("44 active today") phrasings are
intentionally not pinned — only hard total-roster assertions.

Usage:
    python3 tools/validation/validate_wiki_civ_count.py

Exit codes:
    0 — every concrete ANW-civ-count claim matches the live count (GREEN)
    1 — a claim disagrees with the live count, or the count can't be read (RED)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "docs" / "wiki"
CIVMODS = REPO / "data" / "civmods.xml"

# Two narrow TOTAL-roster claim shapes. The capture group is the asserted
# count. "token" / "all" scope these to whole-roster assertions and keep the
# per-culture sub-group counts (which sum to the total) out of scope.
CLAIM_RES = [
    re.compile(r"(\d+)\s+ANW\s+civ\s+token"),
    re.compile(r"\ball\s+(\d+)\s+(?:ANW\s+)?civ"),
]


def live_active_count() -> int | None:
    try:
        return CIVMODS.read_text(encoding="utf-8").count("<main>1</main>")
    except OSError:
        return None


def main() -> int:
    live = live_active_count()
    if not live:
        print(f"FAIL — could not read active-civ count from {CIVMODS.relative_to(REPO)}")
        return 1

    errors: list[str] = []
    claims = 0

    for md in sorted(WIKI.rglob("*.md")):
        for lineno, line in enumerate(
                md.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for re_ in CLAIM_RES:
                for m in re_.finditer(line):
                    n = int(m.group(1))
                    claims += 1
                    if n != live:
                        rel = md.relative_to(REPO)
                        errors.append(
                            f"{rel}:{lineno}: claims {n} ANW civs but live "
                            f"count is {live} — '{m.group(0).strip()}'")

    print("Wiki civ-count check (every 'N ANW civ' claim must match live count)")
    print(f"  live active count (<main>1</main> in civmods.xml): {live}")
    print(f"  concrete claims scanned: {claims}")
    print()

    if errors:
        print("FAIL — wiki civ-count claims out of sync with data/civmods.xml:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"PASS — all {claims} concrete ANW-civ-count claims equal {live}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
