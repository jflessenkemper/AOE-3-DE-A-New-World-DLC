"""Rename every deck slot in `data/anwhomecity*.xml` to its country name.

Each revolution civ ships 6 identical deck slots (Beginner / Land / Naval /
Tycoon / TreatyNoNat / TreatyNative) all carrying the same AOE 3 DE - A New World
25-card list. The user wants the deck name in the in-game Deck Builder to
read as the country itself rather than the stock stringtable labels.

Strategy: replace every `<name>$$NNNN$$<suffix></name>` line that lives
inside `<decks>` (one of the six deck slots) with `<name>{Country}</name>`.
The single homecity-level `<name>$$80850$$</name>` (the city's own name,
which sits outside the `<decks>` block) is left alone.

Run from repo root:
    python3 tools/rename_revolution_decks.py            # rewrites in place
    python3 tools/rename_revolution_decks.py --dry-run  # show diff only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

# Filename → display name shown in the in-game Deck Builder.
COUNTRY_FOR = {
    "anwhomecityamericans.xml": "Americans",
    "anwhomecityargentina.xml": "Argentina",
    "anwhomecitybajacalifornians.xml": "Baja California",
    "anwhomecitybarbary.xml": "Barbary States",
    "anwhomecitybrazil.xml": "Brazil",
    "anwhomecitycalifornia.xml": "California",
    "anwhomecitycanada.xml": "Canada",
    "anwhomecitycentralamericans.xml": "Central America",
    "anwhomecitychile.xml": "Chile",
    "anwhomecitycolumbia.xml": "Colombia",
    "anwhomecityegypt.xml": "Egypt",
    "anwhomecityfinland.xml": "Finland",
    "anwhomecityhaiti.xml": "Haiti",
    "anwhomecityhungary.xml": "Hungary",
    "anwhomecityindonesians.xml": "Indonesia",
    "anwhomecitymaya.xml": "Maya",
    "anwhomecitymexicans.xml": "Mexico",
    "anwhomecitynapoleon.xml": "Napoleonic France",
    "anwhomecityperu.xml": "Peru",
    "anwhomecityrevolutionaryfrance.xml": "Revolutionary France",
    "anwhomecityriogrande.xml": "Rio Grande",
    "anwhomecityromania.xml": "Romania",
    "anwhomecitysouthafricans.xml": "South Africa",
    "anwhomecitytexas.xml": "Texas",
    "anwhomecityyucatan.xml": "Yucatán",
}

# Matches a stringtable-style deck name. Captures leading whitespace so we
# preserve indentation when we rewrite the line. The deck-slot names look
# like `$$71332$$Beginner` — they always have a non-empty suffix after the
# closing `$$`, which is what distinguishes them from the bare homecity
# name `$$80850$$`.
DECK_NAME_RE = re.compile(
    r"^(?P<indent>\s*)<name>\$\$\d+\$\$(?P<suffix>\w+)</name>\s*$",
    re.MULTILINE,
)


def rewrite(text: str, country: str) -> tuple[str, int]:
    """Return (new_text, replacement_count)."""

    def sub(m: re.Match[str]) -> str:
        return f"{m.group('indent')}<name>{country}</name>"

    new_text, count = DECK_NAME_RE.subn(sub, text)
    return new_text, count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="show what would change, don't write")
    args = ap.parse_args()

    found = sorted(p.name for p in DATA.glob("anwhomecity*.xml"))
    expected = set(COUNTRY_FOR)
    missing_files = expected - set(found)
    unexpected_files = set(found) - expected
    if missing_files:
        print(f"ERROR: COUNTRY_FOR has entries with no file on disk: {sorted(missing_files)}")
        return 2
    if unexpected_files:
        print(f"ERROR: file on disk not in COUNTRY_FOR: {sorted(unexpected_files)}")
        return 2

    total = 0
    for fname, country in COUNTRY_FOR.items():
        path = DATA / fname
        text = path.read_text(encoding="utf-8")
        new_text, count = rewrite(text, country)
        if count != 6:
            print(f"WARN: {fname} — expected 6 deck-name replacements, got {count}")
        if new_text != text:
            total += count
            verb = "would write" if args.dry_run else "wrote"
            print(f"  {verb} {fname:<48} → {country!r} ({count} slots)")
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")

    print(f"\n{'(dry-run) ' if args.dry_run else ''}renamed {total} deck slots across {len(COUNTRY_FOR)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
