#!/usr/bin/env python3
"""Emit per-civ tooltip strings into stringmods.xml.

Tooltip structure (matches user's spec):

    <color=1.0, 1.0, 0.0>{Leader Name}</color>
    {Leader history — 1-2 sentences}

    <color=1.0, 1.0, 0.0>{State Name}</color>
    {Nation history — 1-2 sentences}

    <color=1.0, 1.0, 0.0>Unique Units:</color>
    {Comma-separated list — verified from research}

    <color=1.0, 1.0, 0.0>Unique Buildings:</color>
    {Comma-separated list — verified from research, omitted if empty}

Inputs:
  - tools/migration/anw_blurb_data.py  — leader_history + nation_history
  - artifacts/civ_unique_units_research.json — verified units/buildings
  - artifacts/civ_tooltip_ids.json      — token → tooltipID
  - tools/migration/anw_token_map.py    — token → leader/display

Output: replaces each civ's <String _locID=...> body in
``data/strings/english/stringmods.xml``. Idempotent — re-running
overwrites with the latest data.

Usage::

    python3 tools/migration/generate_civ_blurbs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402
from tools.migration.anw_blurb_data import BLURBS   # noqa: E402


_STRINGMODS = REPO_ROOT / "data" / "strings" / "english" / "stringmods.xml"
_TOOLTIPS = REPO_ROOT / "artifacts" / "civ_tooltip_ids.json"
_RESEARCH = REPO_ROOT / "artifacts" / "civ_unique_units_research.json"


def _xml_encode(s: str) -> str:
    """Engine reads &lt;color&gt;…&lt;/color&gt; as inline color tags."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


def build_tooltip(token: str, info: dict, blurb: dict, units_data: dict) -> str:
    """Build a plain-text tooltip body — leader history + nation history only.

    The picker UI auto-renders the leader name (from personality nameID)
    and the civ display name (from civmods displaynameid) as bullets/
    headers. Including them in our body causes visible duplication. So
    we ship ONLY the prose:

        {Leader history sentence}
        {Nation history sentence}

    Per user feedback (2026-05-09):
      - No leader/civ-name headings in body (picker auto-renders them).
      - No Unique Units or Unique Buildings sections.
    """
    sections = [
        blurb["leader_history"],
        blurb["nation_history"],
    ]
    text = "\\n".join(s.strip() for s in sections if s.strip())
    return _xml_encode(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would change, don't write")
    args = ap.parse_args()

    for required in (_TOOLTIPS, _RESEARCH):
        if not required.exists():
            print(f"ERROR: {required} not found.", file=sys.stderr)
            return 2

    tooltip_ids: dict[str, str] = json.loads(_TOOLTIPS.read_text())
    research: dict[str, dict] = json.loads(_RESEARCH.read_text())
    text = _STRINGMODS.read_text(encoding="utf-8")
    original = text

    n_replaced = 0
    n_inserted = 0
    n_missing = 0

    for token, info in ANW_CIVS.items():
        blurb = BLURBS.get(token)
        if blurb is None:
            n_missing += 1
            print(f"  ! no leader/nation blurb for {token}, skip")
            continue
        units_data = research.get(token, {})
        locid = tooltip_ids.get(token)
        if locid is None:
            print(f"  ! no tooltipID for {token}, skip")
            continue

        body = build_tooltip(token, info, blurb, units_data)
        new_str = f'<String _locID="{locid}">{body}</String>'

        # Replace existing entry (whole body) — never use re.sub on body because
        # the body contains regex-special characters (commas/dots/quotes/etc).
        pat = re.compile(
            rf'<String\s+_locID="{re.escape(locid)}"[^>]*>.*?</String>',
            re.DOTALL,
        )
        m = pat.search(text)
        if m:
            text = text.replace(m.group(0), new_str, 1)
            n_replaced += 1
        else:
            text = text.replace("</Language>", f"\t{new_str}\n</Language>", 1)
            n_inserted += 1

    print(f"Tooltips replaced: {n_replaced}")
    print(f"Tooltips inserted: {n_inserted}")
    if n_missing:
        print(f"Civs without blurb data: {n_missing}")

    if args.dry_run:
        print("(dry run — stringmods.xml not written)")
        return 0
    if text != original:
        _STRINGMODS.write_text(text, encoding="utf-8")
        print(f"Wrote: {_STRINGMODS}")
    else:
        print("No changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
