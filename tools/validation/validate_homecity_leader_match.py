#!/usr/bin/env python3
"""Verify each ANW homecity's <heroname> resolves to the canonical leader name.

Bug class this catches (hit on 2026-05-09): templating mass-produced
``data/anwhomecity*.xml`` from base-game homecity files left every civ
referencing the BASE leader name (e.g., ANWArgentines pointed at
``$$43030$$`` = "Francis Drake"). The mod ran fine but the SELECT HOME
CITY picker showed wrong leader names to users.

For each ANW civ:
  1. Read ``data/anwhomecity{stem}.xml``'s ``<heroname>$$N$$</heroname>``.
  2. Resolve N via stringmods or extracted base stringtable.
  3. Compare resolved text to the expected leader name in
     ``tools.migration.anw_token_map.ANW_CIVS[token]['leader']``.
  4. FAIL if they don't (case-insensitively) match.

Usage::

    python3 tools/validation/validate_homecity_leader_match.py
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402


_DATA_DIR = REPO_ROOT / "data"
_STRINGS_DIR = REPO_ROOT / "data" / "strings"
_BASE_ST = REPO_ROOT / "artifacts" / "extracted_base_stringtable.xml"
_STRING_RE = re.compile(
    r'<[Ss]tring\s+_loc[iI][dD]="(\d+)"[^>]*>\s*(.*?)\s*</[Ss]tring>',
    re.DOTALL,
)


def _build_locid_index() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in _STRINGS_DIR.rglob("stringmods*.xml"):
        for locid, body in _STRING_RE.findall(
                f.read_text(encoding="utf-8", errors="replace")):
            out.setdefault(locid, body.strip())
    if _BASE_ST.exists():
        for locid, body in _STRING_RE.findall(
                _BASE_ST.read_text(encoding="utf-8", errors="replace")):
            out.setdefault(locid, body.strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    print("=" * 60)
    print("ANW HOMECITY LEADER-NAME MATCH")
    print("=" * 60)

    locid_to_text = _build_locid_index()

    fails: list[tuple[str, str, str, str]] = []  # token, locid, actual, expected
    for token, info in ANW_CIVS.items():
        stem = info.get('file_stem') or (token[3:].lower() if token.startswith('ANW') else token.lower())
        p = _DATA_DIR / f"anwhomecity{stem}.xml"
        if not p.exists():
            fails.append((token, "?", "(missing file)", info.get("leader", "")))
            continue
        try:
            root = ET.parse(p).getroot()
        except Exception as e:
            fails.append((token, "?", f"(parse error: {e})", info.get("leader", "")))
            continue
        # Revolution civs that intentionally share a base civ's homecity file
        # (e.g. ANWAmericans → anwhomecityusa.xml whose <civ> is DEAmericans)
        # would always fail the leader-name check on the base civ's leader.
        # Detect this by comparing the file's declared <civ> to the token: if
        # they differ, the leader check is the base civ's responsibility — skip.
        civ_el = root.find("civ")
        file_civ = (civ_el.text or "").strip() if civ_el is not None else ""
        if file_civ and file_civ != token:
            continue
        hero_el = root.find("heroname")
        if hero_el is None or not (hero_el.text or "").strip():
            fails.append((token, "?", "(no <heroname>)", info.get("leader", "")))
            continue
        m = re.search(r'\$\$(\d+)\$\$', hero_el.text)
        if not m:
            fails.append((token, "?", f"(non-stringID: {hero_el.text!r})",
                         info.get("leader", "")))
            continue
        locid = m.group(1)
        actual = locid_to_text.get(locid, "")
        expected = info.get("leader", "").strip()
        if not expected:
            continue  # spec doesn't have a leader name — skip
        if not actual:
            fails.append((token, locid, "(unresolved)", expected))
            continue
        # Loose match: expected leader appears (case-insensitive) in actual
        if expected.lower() not in actual.lower():
            fails.append((token, locid, actual, expected))

    total = len(ANW_CIVS)
    pass_count = total - len(fails)
    print(f"  PASS: {pass_count:>2}/{total}")
    print(f"  FAIL: {len(fails):>2}/{total}")
    print()
    if fails:
        print("Mismatched homecities (each FAIL = wrong-leader copy-paste residue):")
        for token, locid, actual, expected in fails[:25]:
            print(f"  {token:<24}  $${locid}$$ → {actual!r}  "
                  f"(expected leader: {expected!r})")
        if len(fails) > 25:
            print(f"  … +{len(fails) - 25} more")

    if args.json:
        import json
        report = {"total": total, "pass": pass_count, "fail": len(fails),
                 "mismatches": [{"civ": t, "locid": l, "actual": a, "expected": e}
                               for t, l, a, e in fails]}
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2))

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
