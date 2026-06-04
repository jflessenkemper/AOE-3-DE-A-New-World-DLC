"""Curate a thematically-coherent 25-card 'A New World' deck for every
standard *and* revolution civ.

Replaces the dumb age-padded pickers in build_default_decks.py and
build_standard_decks.py with a single scored picker that:

  • Honors per-civ THEME keywords (Napoleon → Imperial Old Guard, etc.)
  • Reinforces the civ's BUILDSTYLE archetype (Highland Citadel → walls/forts)
  • Excludes revolution-only cards from STANDARD civ decks
  • Heavily preferences DEHCREV* cards in REVOLUTION civ decks
  • Maintains a sensible age distribution (no all-age-0 piles)
  • Always picks `must_include` cards if they exist in the civ's pool

Reads the existing override XMLs in `data/` (so this is idempotent and respects
hand edits to the pool) plus the vanilla XMBs from Data.bar as a fallback for
any standard-civ XML we haven't materialized yet.

Writes:
  • data/<homecity-basename>.xml       (the override the AI loads)
  • data/decks_anw_themed.json          (civ_id → {age_str → [card_names]})
  • data/decks_standard.json           (mirror, kept for inject_standard_decks)
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import civ_themes
from bar import open_bar
from xmb import parse_xmb

REPO = Path(__file__).resolve().parents[2]
GAME = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game"
)
DATA_BAR = GAME / "Data" / "Data.bar"
DATA_OUT = REPO / "data"

TARGET_SIZE = 25
DECK_NAME = "A New World"

# A floor on how many cards from each age to pick when possible. Real pools
# don't always have age-4 cards so we'll fall through if the bucket is empty.
AGE_FLOOR = {0: 2, 1: 5, 2: 6, 3: 5, 4: 2}

# Standard civs MUST NOT include these (post-revolt or revolt-trigger cards).
REV_PREFIX_RE = re.compile(r"^(DEHCREV|HCREV)", re.IGNORECASE)
REV_TRIGGER_RE = re.compile(r"Revolution[A-Z]?$|Revolution\d?$|^DEHC[A-Z][a-z]+Revolution$")

# High-impact "always nice to have" generic cards (small bonus when they're
# already in the pool).
HIGH_IMPACT_GENERIC = {
    "HCUnlockFactory", "HCRobberBarons", "HCUnlockFort", "HCXPBankWagon",
    "HCXPEconomicTheory", "HCRefrigeration", "HCExoticHardwoods",
    "HCFrontierDefenses", "HCWildernessWarfare", "HCHeavyFortifications",
    "HCAdvancedArsenal", "HCRoyalMint",
}


# ── pool extraction ────────────────────────────────────────────────────────

_arc_cache = None

def _get_arc():
    global _arc_cache
    if _arc_cache is None:
        print(f"  opening {DATA_BAR.name} ...")
        _arc_cache = open_bar(DATA_BAR)
    return _arc_cache


def load_homecity_root(basename: str) -> ET.Element:
    """Prefer existing override in data/, fall back to vanilla XMB."""
    override = DATA_OUT / f"{basename}.xml"
    if override.exists():
        return ET.parse(override).getroot()
    arc = _get_arc()
    entry = next(
        (e for e in arc.entries if e.normalized_name == f"{basename}.xml.xmb"),
        None,
    )
    if entry is None:
        raise RuntimeError(f"no {basename}.xml.xmb in {DATA_BAR.name}")
    return parse_xmb(arc.read_payload(entry))


def collect_pool(root: ET.Element) -> dict[str, int]:
    pool: dict[str, int] = {}
    cb = root.find("cards")
    if cb is None:
        return pool
    for card in cb.findall("card"):
        n = (card.findtext("name") or "").strip()
        if not n:
            continue
        try:
            a = int((card.findtext("age") or "0").strip())
        except ValueError:
            a = 0
        pool[n] = a
    return pool


# ── scoring + selection ────────────────────────────────────────────────────

def score_card(card: str, age: int, theme: dict) -> int:
    u = card.upper()
    s = 0
    is_rev_civ = theme["is_revolution"]
    keywords = [k.upper().replace(" ", "") for k in theme["keywords"]]
    bs_kws = [k.upper() for k in
              civ_themes.BUILDSTYLE_KEYWORDS.get(theme.get("buildstyle", ""), [])]

    # Theme-keyword bonuses (case-insensitive substring on card name)
    for kw in keywords:
        if kw and kw in u:
            s += 200

    # Buildstyle reinforcement
    for kw in bs_kws:
        if kw and kw in u:
            s += 60

    # Revolution civ-specific
    if is_rev_civ:
        if "DEHCREV" in u:
            s += 350  # huge: this is the post-revolt themed card
        elif u.startswith("DEHC"):
            s += 80   # general civ-unique pre-revolt
        elif u.startswith("HC"):
            s += 10
    else:
        # Standard civ: civ-uniques rule the pool
        if u.startswith("DEHC"):
            s += 150

    # High-impact named cards regardless of civ
    if card in HIGH_IMPACT_GENERIC:
        s += 50

    # Mercenary diversity is fun and powerful
    if "MERC" in u and "REV" not in u:
        s += 40

    # Naval is a special case
    if any(t in u for t in ("FRIGATE", "GALLEON", "MONITOR", "IRONCLAD",
                            "BATTLESHIP", "CARAVEL")):
        s += 25

    # Age weighting
    age_bonus = {0: -20, 1: 25, 2: 35, 3: 30, 4: 18}.get(age, 0)
    s += age_bonus

    return s


def select_deck(civ_id: str, pool: dict[str, int], theme: dict,
                warnings: list[str] | None = None) -> list[str]:
    excludes = set(theme.get("must_exclude", []))
    if not theme["is_revolution"]:
        # Strip ALL revolution-themed and revolution-trigger cards from
        # standard civ decks.
        for c in pool:
            if REV_PREFIX_RE.search(c):
                excludes.add(c)
            elif c.endswith("Revolution") and c.startswith(("HC", "DEHC")):
                excludes.add(c)

    candidates = [c for c in pool if c not in excludes]
    scored = sorted(candidates,
                    key=lambda c: (-score_card(c, pool[c], theme), c))

    chosen: list[str] = []
    seen: set[str] = set()
    by_age: dict[int, int] = defaultdict(int)

    # Pass 1: must_include (only if present in pool & not excluded)
    for c in theme.get("must_include", []):
        if c not in pool:
            if warnings is not None:
                warnings.append(f"{civ_id}: must_include '{c}' not in pool")
            continue
        if c in excludes or c in seen:
            continue
        chosen.append(c)
        seen.add(c)
        by_age[pool[c]] += 1
        if len(chosen) >= TARGET_SIZE:
            return chosen

    # Pass 2: walk scored list, respecting AGE_FLOOR (try to fill each age
    # bucket up to its floor before letting any single age dominate)
    for age, floor in sorted(AGE_FLOOR.items()):
        for c in scored:
            if len(chosen) >= TARGET_SIZE:
                return chosen
            if c in seen or pool[c] != age:
                continue
            if by_age[age] >= floor:
                break
            chosen.append(c)
            seen.add(c)
            by_age[age] += 1

    # Pass 3: fill remaining slots top-down by score, ignoring age floors
    for c in scored:
        if len(chosen) >= TARGET_SIZE:
            break
        if c in seen:
            continue
        chosen.append(c)
        seen.add(c)
        by_age[pool[c]] += 1

    return chosen[:TARGET_SIZE]


# ── deck rewrite (XML) ─────────────────────────────────────────────────────

def find_default_deck(root: ET.Element) -> ET.Element | None:
    decks = root.find("decks")
    if decks is None:
        return None
    for deck in decks.findall("deck"):
        if deck.find("default") is not None:
            return deck
    return decks.find("deck")


def rewrite_deck(deck: ET.Element, names: list[str]) -> None:
    name_el = deck.find("name")
    if name_el is None:
        name_el = ET.SubElement(deck, "name")
    name_el.text = DECK_NAME
    if deck.find("default") is None:
        ET.SubElement(deck, "default")
    old_cards = deck.find("cards")
    if old_cards is not None:
        deck.remove(old_cards)
    cards_el = ET.SubElement(deck, "cards")
    for n in names:
        c = ET.SubElement(cards_el, "card")
        c.text = n


def serialize(root: ET.Element) -> str:
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        root, encoding="unicode") + "\n"


# ── orchestrator ───────────────────────────────────────────────────────────

def main() -> int:
    summary_legendary: dict[str, dict[str, list[str]]] = {}
    summary_standard: dict[str, dict[str, list[str]]] = {}

    civ_ids = civ_themes.all_civs()
    warnings: list[str] = []
    print(f"curating {len(civ_ids)} decks (target {TARGET_SIZE} cards)\n")

    # Pretty header
    print(f"{'civ_id':40s} {'pool':>5}  {'pick':>4}  by-age (0/1/2/3/4)")
    print("-" * 78)

    for civ_id in civ_ids:
        theme = civ_themes.get(civ_id)
        try:
            root = load_homecity_root(civ_id)
        except Exception as e:
            print(f"  {civ_id:38s} ERROR: {e}")
            continue
        pool = collect_pool(root)
        if not pool:
            print(f"  {civ_id:38s} no pool found")
            continue

        chosen = select_deck(civ_id, pool, theme, warnings)
        deck = find_default_deck(root)
        if deck is None:
            decks = root.find("decks") or ET.SubElement(root, "decks")
            deck = ET.SubElement(decks, "deck")
        rewrite_deck(deck, chosen)

        # Per-age breakdown for the summary JSON
        by_age: dict[str, list[str]] = defaultdict(list)
        for c in chosen:
            by_age[str(pool[c])].append(c)
        if theme["is_revolution"]:
            summary_legendary[civ_id] = dict(by_age)
        else:
            # Standard civs use a different summary key for inject_standard_decks
            short = civ_id.replace("homecity", "")
            # Map the file basename → the civ_id used by inject_standard_decks
            STD_KEY = {
                "british": "British", "chinese": "Chinese", "dutch": "Dutch",
                "ethiopians": "Ethiopians", "french": "French", "german": "Germans",
                "hausa": "Hausa", "italians": "Italians", "japanese": "Japanese",
                "ottomans": "Ottomans", "portuguese": "Portuguese",
                "russians": "Russians", "spanish": "Spanish", "swedish": "Swedes",
                "xpaztec": "Aztecs", "xpsioux": "Lakota",
                "americans": "UnitedStates", "deinca": "Inca",
                "indians": "Indians", "maltese": "Maltese",
                "mexicans": "MexicansStd", "xpiroquois": "Haudenosaunee",
            }
            key = STD_KEY.get(short, short)
            summary_standard[key] = dict(by_age)

        # Write the homecity XML override
        out = DATA_OUT / f"{civ_id}.xml"
        out.write_text(serialize(root), encoding="utf-8")

        bins = [str(len(by_age.get(str(a), []))) for a in range(5)]
        print(f"  {civ_id:38s} {len(pool):5d}  {len(chosen):4d}  "
              f"{'/'.join(bins)}")

    (DATA_OUT / "decks_anw_themed.json").write_text(
        json.dumps(summary_legendary, indent=2, sort_keys=True), encoding="utf-8")
    (DATA_OUT / "decks_standard.json").write_text(
        json.dumps(summary_standard, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote data/decks_anw_themed.json ({len(summary_legendary)} civs)")
    print(f"wrote data/decks_standard.json   ({len(summary_standard)} civs)")
    if warnings:
        print(f"\n{len(warnings)} warnings (must_include cards not in pool):")
        for w in warnings:
            print(f"  {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
