#!/usr/bin/env python3
"""Static validator: the wiki Wall Strategy Index must stay in sync with the
authoritative per-civ wall_strategy claims.

Catches the exact drift this validator was born from: the wiki table at
docs/wiki/validation/nations-and-buildings.md ("## Wall Strategy Index") once
listed only 18 civs and declared "26 civs TBD / not yet validated", long after
every active ANW civ had received an explicit wall strategy. This asserts:

  1. Every active ANW civ token (<main>1</main> in data/civmods.xml) appears as
     a row in the wiki Wall Strategy Index table.
  2. The integer + enum NAME in each wiki row matches that civ's
     `claims.wall_strategy` in playstyle_spec.json (source of truth, also pinned
     against the AI XS by the gated spec/doctrine validators).
  3. No extra/stale token rows that are not active civs.

Usage:
    python3 tools/validation/validate_wiki_wall_strategy_sync.py

Exit codes:
    0 — wiki table fully matches the spec for all active civs (GREEN)
    1 — missing / extra / mismatched rows (RED — details printed)
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "docs" / "wiki" / "validation" / "nations-and-buildings.md"
SPEC = REPO / "playstyle_spec.json"
CIVMODS = REPO / "data" / "civmods.xml"

ENUM = {
    0: "FortressRing",
    1: "ChokepointSegments",
    2: "CoastalBatteries",
    3: "FrontierPalisades",
    4: "UrbanBarricade",
    5: "MobileNoWalls",
}

# Hard map for the two tokens whose civ_label diverges from the token stem.
_HARD = {
    "ANWRevFrance": "Revolutionary France Robespierre Revolution",
    "ANWUSA": "United States Washington",
}


def active_tokens() -> list[str]:
    root = ET.parse(CIVMODS).getroot()
    out = []
    for civ in root.iter("civ"):
        if (civ.findtext("main") or "").strip() == "1":
            tok = (civ.findtext("name") or "").strip()
            if tok:
                out.append(tok)
    return out


def token_display(civ) -> str:
    return (civ.findtext("displayNameID") or "").strip()


def spec_strategy_by_token() -> dict[str, int]:
    """Map each active token -> wall_strategy int from playstyle_spec claims."""
    spec = json.loads(SPEC.read_text(encoding="utf-8"))["civs"]
    by_dn: dict[str, int] = {}
    for label, c in spec.items():
        dn = c.get("data_name", label)
        claims = c.get("claims", {})
        ws = claims.get("wall_strategy") if isinstance(claims, dict) else None
        if isinstance(ws, int):
            by_dn[dn] = ws

    root = ET.parse(CIVMODS).getroot()
    out: dict[str, int] = {}
    for civ in root.iter("civ"):
        if (civ.findtext("main") or "").strip() != "1":
            continue
        tok = (civ.findtext("name") or "").strip()
        dn = _HARD.get(tok, token_display(civ))
        if dn not in by_dn:
            base = tok.replace("ANW", "").lower()
            cand = [d for d in by_dn if d.replace(" ", "").lower().startswith(base[:6])]
            if cand:
                dn = cand[0]
        if dn in by_dn:
            out[tok] = by_dn[dn]
    return out


_ROW_RE = re.compile(r"^\|\s*(ANW\w+)\s*\|\s*(\d+)\s*\|\s*([A-Za-z]+)\s*\|")


def wiki_rows() -> dict[str, tuple[int, str]]:
    """Parse the Wall Strategy Index table -> {token: (int, name)}."""
    text = WIKI.read_text(encoding="utf-8")
    # Restrict to the section to avoid catching unrelated ANW* table rows.
    start = text.find("## Wall Strategy Index")
    if start < 0:
        return {}
    nxt = text.find("\n## ", start + 1)
    section = text[start: nxt if nxt > 0 else len(text)]
    out: dict[str, tuple[int, str]] = {}
    for line in section.splitlines():
        m = _ROW_RE.match(line.strip())
        if m:
            out[m.group(1)] = (int(m.group(2)), m.group(3))
    return out


def main() -> int:
    tokens = set(active_tokens())
    spec = spec_strategy_by_token()
    rows = wiki_rows()

    print("Wiki Wall Strategy Index sync check")
    print(f"  active civ tokens     : {len(tokens)}")
    print(f"  spec strategies parsed: {len(spec)}")
    print(f"  wiki table rows       : {len(rows)}")
    print()

    errors: list[str] = []

    # Spec coverage gap (every active token must have a spec strategy to compare).
    no_spec = sorted(t for t in tokens if t not in spec)
    for t in no_spec:
        errors.append(f"no playstyle_spec wall_strategy claim for active civ {t}")

    # Missing rows.
    for t in sorted(tokens):
        if t not in rows:
            errors.append(f"missing from wiki Wall Strategy Index table: {t}")

    # Extra/stale rows.
    for t in sorted(rows):
        if t not in tokens:
            errors.append(f"stale wiki row for non-active token: {t}")

    # Value mismatches.
    for t in sorted(tokens):
        if t in spec and t in rows:
            want = spec[t]
            got_i, got_name = rows[t]
            if got_i != want:
                errors.append(
                    f"{t}: wiki strategy {got_i} != spec {want} ({ENUM.get(want, '?')})")
            elif got_name != ENUM.get(want):
                errors.append(
                    f"{t}: wiki name '{got_name}' != expected '{ENUM.get(want)}' for #{want}")

    if errors:
        print("FAIL — wiki Wall Strategy Index out of sync with playstyle_spec:")
        for e in errors:
            print(f"  {e}")
        print()
        print("Fix: regenerate the '## Wall Strategy Index' table in")
        print(f"     {WIKI.relative_to(REPO)} from playstyle_spec.json claims.wall_strategy.")
        return 1

    print(f"PASS — all {len(tokens)} active civs match the wiki Wall Strategy Index.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
