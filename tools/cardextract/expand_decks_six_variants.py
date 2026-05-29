"""Expand each mod civ homecity XML so the Legendary Leaders deck appears
under all six standard deck-name slots (Beginner / Land / Naval / Tycoon /
Treaty / Treaty-Natives). Each slot contains the same curated 25 cards.

Why: when the template had only our custom "Legendary Leaders" deck, the
game auto-generated its own 6 standard decks from the card pool at savegame
creation, erasing our curated content. By pre-populating all 6 standard
named decks with our 25 curated cards, the game preserves them and players
see the Legendary Leaders curation in every slot.

Idempotent.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"

DECK_SLOTS = [
    # (string_id, display_name_suffix)
    ("71332", "Beginner"),
    ("20310", "Land"),
    ("71333", "Naval"),
    ("55547", "Tycoon"),
    ("90974", "TreatyNoNat"),
    ("90975", "TreatyNative"),
]


def expand(path: Path) -> bool:
    txt = path.read_text(encoding="utf-8")
    # Extract the existing <deck>...</deck> (first one) — this has our 25 cards
    m = re.search(r"(\s*)<deck>(.*?)</deck>", txt, re.DOTALL)
    if not m:
        return False
    indent, body = m.group(1), m.group(2)

    # Pull out cards block so we can re-use it for each slot
    cards_m = re.search(r"(<cards>.*?</cards>)", body, re.DOTALL)
    if not cards_m:
        return False
    cards_block = cards_m.group(1)

    # Build six named decks with the same cards
    new_decks = []
    for sid, suffix in DECK_SLOTS:
        d = (
            f"{indent}<deck>\n"
            f"{indent}  <name>$${sid}$${suffix}</name>\n"
            f"{indent}  <default>\n"
            f"{indent}  </default>\n"
            f"{indent}  {cards_block}\n"
            f"{indent}</deck>"
        )
        new_decks.append(d)

    new_decks_str = "\n".join(new_decks)

    # Replace the entire <decks>...</decks> inner contents
    decks_wrap = re.search(r"(<decks>)(.*?)(</decks>)", txt, re.DOTALL)
    if not decks_wrap:
        return False
    new_inner = "\n" + new_decks_str + "\n  "
    new_txt = txt[:decks_wrap.start(2)] + new_inner + txt[decks_wrap.end(2):]
    path.write_text(new_txt, encoding="utf-8")
    return True


def main():
    # File-name prefix was renamed `anwhomecity*` → `anwhomecity*` when
    # the mod was rebranded from "Revolution Mod / Legendary Leaders" to
    # "A New World". The old glob pattern silently matched zero files, so
    # the standard 6-deck-slot expansion never ran in production. As a
    # result every allied AI showed "Hidden — 0/25 cards" because the
    # only deck slot ("A New World") didn't match any of the engine's
    # six string-table deck identifiers (Beginner / Land / Naval /
    # Tycoon / TreatyNoNat / TreatyNative).
    targets = sorted(DATA.glob("anwhomecity*.xml"))
    ok = 0
    for p in targets:
        if expand(p):
            ok += 1
            print(f"  {p.name}: expanded to 6 named decks x 25 cards")
        else:
            print(f"  {p.name}: skipped (no deck found)")
    print(f"\nExpanded {ok}/{len(targets)} mod civ homecity files.")


if __name__ == "__main__":
    main()
