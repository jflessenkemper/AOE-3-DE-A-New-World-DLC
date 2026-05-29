"""Standardise the AI's default deck for every revolution civ.

Each `data/anwhomecity*.xml` file already contains a single `<deck>` block
flagged `<default>` — that is the deck the AI auto-picks when playing the civ.
Today they vary wildly in size (13–25 cards) and are named with inconsistent
localisation tokens (`$$41682$$`, `$$71332$$Beginner`).

This script:
  • pads every default deck up to TARGET_SIZE cards by drawing additional cards
    from the civ's available pool in `data/decks.json` (skipping duplicates),
  • renames the deck to "Legendary Leaders" so we can verify in-game that the
    AI is in fact using our deck,
  • wraps the rewritten deck in `<!-- LL-DEFAULT-DECK-START -->` /
    `<!-- LL-DEFAULT-DECK-END -->` markers so re-runs are idempotent.

The padding heuristic favours early-game cards (Discovery → Colonial → Fortress
→ Industrial → Imperial), preserves the existing card order, and never removes
hand-curated cards that are already present.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DECKS_JSON = DATA / "decks.json"

TARGET_SIZE = 25
DECK_NAME = "Legendary Leaders"

# decks.json civ key → anwhomecity*.xml stem
CIV_FILE = {
    "Americans":         "anwhomecityamericans.xml",
    "Argentines":        "anwhomecityargentina.xml",
    "BajaCalifornians":  "anwhomecitybajacalifornians.xml",
    "Barbary":           "anwhomecitybarbary.xml",
    "Brazilians":        "anwhomecitybrazil.xml",
    "Canadians":         "anwhomecitycanada.xml",
    "Chileans":          "anwhomecitychile.xml",
    "Colombians":        "anwhomecitycolumbia.xml",
    "Egyptians":         "anwhomecityegypt.xml",
    "Finns":             "anwhomecityfinland.xml",
    "Haitians":          "anwhomecityhaiti.xml",
    "Hungarians":        "anwhomecityhungary.xml",
    "Indonesians":       "anwhomecityindonesians.xml",
    "Mayans":            "anwhomecitymaya.xml",
    "Mexicans":          "anwhomecitymexicans.xml",
    "NapoleonicFrance":  "anwhomecitynapoleon.xml",
    "Peruvians":         "anwhomecityperu.xml",
    "RevolutionaryFr":   "anwhomecityrevolutionaryfrance.xml",
    "RioGrande":         "anwhomecityriogrande.xml",
    "Romanians":         "anwhomecityromania.xml",
    "SouthAfricans":     "anwhomecitysouthafricans.xml",
    "Texians":           "anwhomecitytexas.xml",
}

# Match the FIRST <deck>...</deck> block, capturing its inner body so we can
# inspect it.  Use non-greedy on body to stop at the first </deck>.
DECK_RE = re.compile(
    r"(?P<indent>[ \t]*)<deck>(?P<body>.*?)</deck>",
    re.DOTALL,
)
CARD_RE = re.compile(r"<card[^>]*>([^<]+)</card>")

START_MARK = "<!-- LL-DEFAULT-DECK-START -->"
END_MARK   = "<!-- LL-DEFAULT-DECK-END -->"


def build_padded_card_list(existing: list[str], pool_by_age: dict[str, list[str]]) -> list[str]:
    """Append cards from the per-age pool until the deck reaches TARGET_SIZE.

    Order: existing curated cards first (preserved), then fill from
    Discovery → Colonial → Fortress → Industrial → Imperial. Skip dupes.
    """
    out = list(existing)
    seen = {c for c in out}
    for age in ("0", "1", "2", "3", "4"):
        if len(out) >= TARGET_SIZE:
            break
        for c in pool_by_age.get(age, []):
            if len(out) >= TARGET_SIZE:
                break
            if c in seen:
                continue
            out.append(c)
            seen.add(c)
    return out


def render_deck_block(indent: str, cards: list[str]) -> str:
    inner_indent = indent + "  "
    card_indent  = indent + "    "
    lines = [f"{indent}<deck>",
             f"{inner_indent}<name>{DECK_NAME}</name>",
             f"{inner_indent}<default>",
             f"{inner_indent}</default>",
             f"{inner_indent}<cards>"]
    for c in cards:
        lines.append(f"{card_indent}<card>{c}</card>")
    lines.append(f"{inner_indent}</cards>")
    lines.append(f"{indent}</deck>")
    return "\n".join(lines)


def patch_one(civ: str, fname: str, pool: dict[str, list[str]]) -> tuple[str, int, int]:
    fp = DATA / fname
    text = fp.read_text(encoding="utf-8")

    # If we have already wrapped this file, just rewrite the marker block in
    # place — preserves any surrounding edits and stays idempotent.
    marker_re = re.compile(
        rf"{re.escape(START_MARK)}.*?{re.escape(END_MARK)}",
        re.DOTALL,
    )

    # Locate the first <deck> block to preserve its indentation
    m = DECK_RE.search(text)
    if not m:
        return ("no <deck> block", 0, 0)
    indent = m.group("indent")
    existing_cards = CARD_RE.findall(m.group("body"))

    new_cards = build_padded_card_list(existing_cards, pool)
    rendered = render_deck_block(indent, new_cards)
    wrapped = f"{indent}{START_MARK}\n{rendered}\n{indent}{END_MARK}"

    if marker_re.search(text):
        # Replace the entire marker block in place. The leading indent before
        # the START marker is captured by the regex; we re-emit `wrapped`
        # which carries its own indent on every line.
        full_marker_re = re.compile(
            rf"[ \t]*{re.escape(START_MARK)}.*?{re.escape(END_MARK)}",
            re.DOTALL,
        )
        new_text = full_marker_re.sub(lambda _: wrapped, text, count=1)
    else:
        # Replace the first <deck>…</deck> block with our wrapped block. The
        # match starts at the indent before <deck>, so `wrapped` (which has
        # `indent` baked into every line) drops in cleanly.
        new_text = text[: m.start()] + wrapped + text[m.end():]

    if new_text != text:
        fp.write_text(new_text, encoding="utf-8")
    return ("ok", len(existing_cards), len(new_cards))


def main() -> int:
    pools = json.loads(DECKS_JSON.read_text(encoding="utf-8"))
    print(f"target deck size: {TARGET_SIZE}")
    print(f"deck name:        {DECK_NAME!r}")
    print()
    for civ, fname in CIV_FILE.items():
        pool = pools.get(civ, {})
        status, before, after = patch_one(civ, fname, pool)
        print(f"  {civ:18s} {fname:40s}  {before:2d} -> {after:2d}  [{status}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
