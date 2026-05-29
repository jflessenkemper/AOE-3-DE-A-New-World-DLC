"""Lower the <level> unlock requirement to 0 for every card referenced by
the Legendary Leaders deck in each mod civ homecity XML.

Why: AoE3 DE gates cards behind home city level (0/10/25/40). A fresh player
starts at HC level 1, so any deck card with level > 1 is dropped from the
Deck Builder display — that's why Chileans showed 13/25 instead of 25/25.

For the curated Legendary Leaders deck we want every card playable from the
very first match. This script walks each anwhomecity*.xml, finds the
Legendary Leaders deck, and for every card in that deck also sets its
corresponding <cards>/<card>/<level> entry in the pool to 0.

Idempotent.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"


def unlock(path: Path) -> tuple[int, int]:
    tree = ET.parse(path)
    root = tree.getroot()

    deck_cards: set[str] = set()
    for d in root.findall(".//deck"):
        for c in d.findall("cards/card"):
            if c.text:
                deck_cards.add(c.text)

    pool = root.find("cards")
    if pool is None:
        return 0, 0

    lowered = 0
    total_deck = len(deck_cards)
    for card in pool.findall("card"):
        name = card.find("name")
        lvl = card.find("level")
        if name is None or lvl is None:
            continue
        if name.text in deck_cards:
            if (lvl.text or "0").strip() != "0":
                lvl.text = "0"
                lowered += 1

    if lowered:
        # Preserve XML indentation by re-serializing only if changed
        tree.write(path, encoding="utf-8", xml_declaration=True)
    return lowered, total_deck


def main():
    targets = sorted(DATA.glob("anwhomecity*.xml"))
    total_lowered = 0
    for p in targets:
        lowered, deck = unlock(p)
        marker = "✓" if lowered == 0 else f"lowered {lowered}"
        print(f"  {p.name:<45} deck={deck}  {marker}")
        total_lowered += lowered
    print(f"\nTotal card-level fields lowered: {total_lowered}")


if __name__ == "__main__":
    main()
