#!/usr/bin/env python3
"""Fix Bug 2: ANW home city decks show 0/N cards because <default /> is empty.

Root cause: every ANW home-city XML defines its primary deck with a
self-closing ``<default />`` element. The AoE3 DE engine treats
``<default>`` as the list of cards to auto-load into the player's
active deck. When ``<default />`` is empty, the active deck starts
empty — so the deck panel reads "0 / 25" even though the deck pool has
25 valid cards.

This script walks every ``data/anwhomecity*.xml`` file, locates each
``<deck>`` block, and replaces ``<default />`` with a populated
``<default><card>...</card>...</default>`` that mirrors the deck's own
``<cards>`` list (capped at ``<maxcardsperdeck>``).

Run from repo root::

    python3 tools/fixes/fix_deck_defaults.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOMECITY_GLOB = "data/anwhomecity*.xml"


def fix_file(path: Path) -> tuple[int, int]:
    """Return (decks_seen, decks_fixed) for this file."""
    content = path.read_text()

    # Cap each deck's <default> to the file's maxcardsperdeck (default 25)
    max_m = re.search(r"<maxcardsperdeck>(\d+)</maxcardsperdeck>", content)
    max_cards = int(max_m.group(1)) if max_m else 25

    decks_seen = 0
    decks_fixed = 0

    def process_deck(match: re.Match) -> str:
        nonlocal decks_seen, decks_fixed
        decks_seen += 1
        full_block = match.group(0)
        inner = match.group(1)

        # Look for <default /> or <default></default> (empty) — skip if non-empty
        default_pattern = re.compile(
            r"(?P<indent>[ \t]*)<default\s*/>|"
            r"(?P<indent2>[ \t]*)<default>\s*</default>",
        )
        dm = default_pattern.search(inner)
        if not dm:
            return full_block  # <default> already populated or absent

        # Extract the deck's own <cards> list
        cards_block = re.search(r"<cards>(.*?)</cards>", inner, re.DOTALL)
        if not cards_block:
            return full_block

        card_names = re.findall(r"<card>([^<]+)</card>", cards_block.group(1))
        if not card_names:
            return full_block

        # Cap and emit
        chosen = card_names[:max_cards]
        indent = dm.group("indent") or dm.group("indent2") or "      "
        # children are indented one extra level
        child_indent = indent + "  "
        new_default = (
            f"{indent}<default>\n"
            + "\n".join(f"{child_indent}<card>{c}</card>" for c in chosen)
            + f"\n{indent}</default>"
        )
        new_inner = default_pattern.sub(new_default, inner, count=1)
        decks_fixed += 1
        # Rebuild block with same opener/closer
        return f"<deck>{new_inner}</deck>"

    # Process every <deck>...</deck>
    new_content = re.sub(
        r"<deck>(.*?)</deck>",
        process_deck,
        content,
        flags=re.DOTALL,
    )

    if new_content != content:
        path.write_text(new_content)

    return decks_seen, decks_fixed


def main() -> int:
    files = sorted(REPO_ROOT.glob(HOMECITY_GLOB))
    if not files:
        print("No anwhomecity*.xml found under data/", file=sys.stderr)
        return 2

    total_seen = 0
    total_fixed = 0
    for path in files:
        if path.name.endswith(".proposed"):
            continue
        seen, fixed = fix_file(path)
        total_seen += seen
        total_fixed += fixed
        if fixed:
            print(f"  {path.name}: fixed {fixed}/{seen} decks")
    print(f"\nTotal: fixed {total_fixed} / {total_seen} decks "
          f"across {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
