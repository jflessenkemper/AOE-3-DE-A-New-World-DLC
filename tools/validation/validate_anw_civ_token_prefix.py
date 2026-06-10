#!/usr/bin/env python3
"""Static validator: every ACTIVE ANW civ token must carry the `ANW` prefix.

ANW ships its civs as ANW-prefixed tokens (ANWBritish, ANWSwedes, …) while
keeping the corresponding base-game entries (British, Swedish, …) as separate
suppression/override rows pinned to <main>0</main>. The prefix is load-bearing:
the token is the primary key joined across homecity XML, personality files,
decks, and playercolors, so a civ added (or a base civ accidentally left) at
<main>1</main> WITHOUT the ANW prefix would either collide with a base civ or
dangle every cross-reference.

Born from a wiki-accuracy drift: docs/wiki/data-layer/civmods.md once gave its
worked example as a bare `<name>British</name>` with <main>1</main>, which
misrepresents the real active token (ANWBritish at civmods.xml l.5384). This
validator pins the actual invariant so the convention can't silently regress.

Asserts:
  1. Every <civ> with <main>1</main> in data/civmods.xml has a <name> that
     starts with "ANW".
  2. (Informational) reports the count of active civs so a sudden change in
     the active-civ total is visible in the gate log.

Usage:
    python3 tools/validation/validate_anw_civ_token_prefix.py

Exit codes:
    0 — every active civ token is ANW-prefixed (GREEN)
    1 — one or more active civ tokens lack the ANW prefix (RED)
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CIVMODS = REPO / "data" / "civmods.xml"


def main() -> int:
    root = ET.parse(CIVMODS).getroot()
    active: list[str] = []
    offenders: list[str] = []
    for civ in root.iter("civ"):
        if (civ.findtext("main") or "").strip() != "1":
            continue
        tok = (civ.findtext("name") or "").strip()
        active.append(tok)
        if not tok.startswith("ANW"):
            offenders.append(tok or "<empty name>")

    print("ANW civ-token prefix check")
    print(f"  active civs (<main>1</main>): {len(active)}")
    print()

    if offenders:
        print("FAIL — active civ token(s) without the required 'ANW' prefix:")
        for t in offenders:
            print(f"  {t}")
        print()
        print("Fix: ANW-prefix the token (ANW<Name>) and keep the base entry")
        print("     at <main>0</main> as a suppression/override row, OR set")
        print("     <main>0</main> if this was meant to be a base suppression.")
        return 1

    print(f"PASS — all {len(active)} active civ tokens are ANW-prefixed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
