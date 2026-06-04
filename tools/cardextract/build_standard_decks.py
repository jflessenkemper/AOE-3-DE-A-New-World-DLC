"""Pull each standard-civ home city XMB out of Data.bar, swap its `<default>`
deck for a 25-card 'A New World' deck, and drop the result as plain XML
into `data/`. The mod's data layer overrides vanilla XMB with our XML, so the
AI for every civilization (standard + revolution) ends up playing our deck.

For each civ:
  • parse the XMB → ET
  • read the top-level `<cards>` block to learn each card's age
  • locate the FIRST `<deck>` flagged `<default>`
  • build a curated deck:
      - keep every card from the existing default deck (preserves the
        designer's intent)
      - pad to TARGET_SIZE from the available pool, age 0 → 4
  • rewrite the deck:
      - rename to "A New World"
      - keep `<default/>` flag
      - drop dbid attributes (the engine accepts both forms)
  • serialize the whole homecity tree back to XML and write to
    `data/<basename>.xml`

Idempotent: if `data/<basename>.xml` already exists, we read OUR previous
output (so any hand edits to the standard-civ XML carry forward) instead of
re-extracting from the BAR.

Side effect: builds `decks_standard.json` so inject_decks.py can render the
new deck blocks for the standard civ sections of the HTML.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bar import open_bar
from xmb import parse_xmb

REPO = Path(__file__).resolve().parents[2]
GAME = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game"
)
DATA_BAR = GAME / "Data" / "Data.bar"
DATA_OUT = REPO / "data"
DECKS_OUT = DATA_OUT / "decks_standard.json"

TARGET_SIZE = 25
DECK_NAME = "A New World"

# Standard 22-civ map: HTML civ slug → home city XMB basename in Data.bar.
# `civ_id` is what we'll key the JSON output on (used by inject_decks.py).
CIVS: list[tuple[str, str]] = [
    ("British",        "homecitybritish"),
    ("Chinese",        "homecitychinese"),
    ("Dutch",          "homecitydutch"),
    ("Ethiopians",     "homecityethiopians"),
    ("French",         "homecityfrench"),
    ("Germans",        "homecitygerman"),
    ("Hausa",          "homecityhausa"),
    ("Italians",       "homecityitalians"),
    ("Japanese",       "homecityjapanese"),
    ("Ottomans",       "homecityottomans"),
    ("Portuguese",     "homecityportuguese"),
    ("Russians",       "homecityrussians"),
    ("Spanish",        "homecityspanish"),
    ("Swedes",         "homecityswedish"),
    ("Aztecs",         "homecityxpaztec"),
    ("Lakota",         "homecityxpsioux"),
    ("UnitedStates",   "homecityamericans"),
    ("Inca",           "homecitydeinca"),
    ("Indians",        "homecityindians"),
    ("Maltese",        "homecitymaltese"),
    ("MexicansStd",    "homecitymexicans"),
    ("Haudenosaunee",  "homecityxpiroquois"),
]


# ── BAR / XMB extraction ────────────────────────────────────────────────────

def load_homecity_root(basename: str) -> ET.Element:
    """Return the parsed `<homecity>` ET root.

    Prefers an existing override in `data/<basename>.xml` (so the script is
    idempotent and respects any hand edits); falls back to the vanilla XMB.
    """
    override = DATA_OUT / f"{basename}.xml"
    if override.exists():
        return ET.parse(override).getroot()

    if not hasattr(load_homecity_root, "_arc"):
        print(f"  opening {DATA_BAR.name} ...")
        load_homecity_root._arc = open_bar(DATA_BAR)
    arc = load_homecity_root._arc
    entry = next(
        (e for e in arc.entries if e.normalized_name == f"{basename}.xml.xmb"),
        None,
    )
    if entry is None:
        raise RuntimeError(f"no {basename}.xml.xmb in {DATA_BAR.name}")
    return parse_xmb(arc.read_payload(entry))


# ── deck surgery ────────────────────────────────────────────────────────────

def collect_pool(root: ET.Element) -> dict[int, list[str]]:
    """Map age → ordered list of card names in this civ's full pool."""
    pool: dict[int, list[str]] = {}
    cards_block = root.find("cards")
    if cards_block is None:
        return pool
    for card in cards_block.findall("card"):
        name = (card.findtext("name") or "").strip()
        if not name:
            continue
        try:
            age = int((card.findtext("age") or "0").strip())
        except ValueError:
            age = 0
        pool.setdefault(age, []).append(name)
    return pool


def find_default_deck(root: ET.Element) -> ET.Element | None:
    decks = root.find("decks")
    if decks is None:
        return None
    for deck in decks.findall("deck"):
        if deck.find("default") is not None:
            return deck
    # No deck explicitly flagged default — fall back to the first.
    return decks.find("deck")


def existing_card_names(deck: ET.Element) -> list[str]:
    """Return ordered card names in a deck, supporting both vanilla and mod
    formats (text content vs <name> child)."""
    cards_el = deck.find("cards")
    if cards_el is None:
        return []
    out: list[str] = []
    for c in cards_el.findall("card"):
        # Vanilla: text is the name. Mod-revolution: text is the name too.
        text = (c.text or "").strip()
        if text:
            out.append(text)
            continue
        named = c.findtext("name")
        if named:
            out.append(named.strip())
    return out


def build_padded_cards(existing: list[str], pool: dict[int, list[str]]) -> list[str]:
    out = list(existing)
    seen = set(out)
    for age in (0, 1, 2, 3, 4):
        if len(out) >= TARGET_SIZE:
            break
        for cname in pool.get(age, []):
            if len(out) >= TARGET_SIZE:
                break
            if cname in seen:
                continue
            out.append(cname)
            seen.add(cname)
    return out


def rewrite_deck(deck: ET.Element, new_cards: list[str]) -> None:
    """Mutate `deck` in place: rename, keep <default>, replace <cards>."""
    # Update <name>
    name_el = deck.find("name")
    if name_el is None:
        name_el = ET.SubElement(deck, "name")
    name_el.text = DECK_NAME
    # Ensure <default/>
    if deck.find("default") is None:
        ET.SubElement(deck, "default")
    # Replace <cards>
    old_cards = deck.find("cards")
    if old_cards is not None:
        deck.remove(old_cards)
    cards_el = ET.SubElement(deck, "cards")
    for cname in new_cards:
        c = ET.SubElement(cards_el, "card")
        c.text = cname


# ── XML output ──────────────────────────────────────────────────────────────

def serialize(root: ET.Element) -> str:
    """ET serialization with a leading XML declaration and stable indentation."""
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        root, encoding="unicode"
    ) + "\n"


# ── orchestrator ────────────────────────────────────────────────────────────

def main() -> int:
    decks_summary: dict[str, dict[str, list[str]]] = {}
    print(f"target deck size: {TARGET_SIZE}")
    print(f"deck name:        {DECK_NAME!r}\n")

    for civ_id, basename in CIVS:
        try:
            root = load_homecity_root(basename)
        except Exception as e:
            print(f"  {civ_id:14s} {basename:24s}  ERROR: {e}")
            continue

        pool = collect_pool(root)
        deck = find_default_deck(root)
        if deck is None:
            print(f"  {civ_id:14s} {basename:24s}  WARN: no deck found")
            continue

        existing = existing_card_names(deck)
        new_cards = build_padded_cards(existing, pool)
        rewrite_deck(deck, new_cards)

        # Group new deck by age for the JSON summary so inject_decks.py can
        # render it without having to re-parse the homecity XML.
        # Build a name→age lookup from the pool.
        age_lookup = {c: a for a, names in pool.items() for c in names}
        by_age: dict[str, list[str]] = {}
        for c in new_cards:
            a = age_lookup.get(c, 0)
            by_age.setdefault(str(a), []).append(c)
        decks_summary[civ_id] = by_age

        out_path = DATA_OUT / f"{basename}.xml"
        out_path.write_text(serialize(root), encoding="utf-8")
        print(
            f"  {civ_id:14s} {basename:24s}  "
            f"{len(existing):2d} -> {len(new_cards):2d}  -> data/{out_path.name}"
        )

    DECKS_OUT.write_text(
        json.dumps(decks_summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"\nwrote {DECKS_OUT.relative_to(REPO)} ({len(decks_summary)} civs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
