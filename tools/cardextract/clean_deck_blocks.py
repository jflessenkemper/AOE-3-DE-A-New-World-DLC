"""Strip legacy double-deck content from each Card Deck <details> block in
a_new_world.html so every nation shows ONLY the curated icon
deck the AI actually plays.

Three legacy patterns being removed:

  1. Revolution civs had a stale `<p>Mod home city: <code>X.xml</code>.
     Full deck set: Beginner, Land, Naval, Tycoon, Treaty.</p>` intro that
     no longer matches reality (we now override with one Legendary
     Leaders deck).

  2. Standard civs had `<p>Base game home city. The AI selects an
     Enhanced-Land or Enhanced-Naval pre-built deck if one exists, or
     builds a deck dynamically card-by-card.</p>` — also stale, since
     our XML overrides force the curated A New World deck.

  3. A handful of standard civs (Aztecs, etc.) had a hand-curated
     TEXT-ONLY deck (`<dl class="buildparam">` + a "Bespoke deck
     designed for…" intro paragraph + a custom summary label like
     "Card Deck: Flower War & Tribute (25 cards, curated)") sitting
     ABOVE our injected icon deck — a duplicate.

After this script every Card Deck section has exactly:

    <details><summary><span class="cat-label">Card Deck</span></summary>
      <!-- (STD-)?DECK-START civ -->
        ... icon deck ...
      <!-- (STD-)?DECK-END civ -->
    </details>

Idempotent.
"""
from __future__ import annotations

import re
from pathlib import Path

HTML = Path(__file__).resolve().parents[2] / "a_new_world.html"

# Match a Card Deck details block. The cat-label may have a colon-suffix
# like "Card Deck: Flower War & Tribute (25 cards, curated)" — we'll
# rewrite all of them to plain "Card Deck".
DECK_BLOCK_RE = re.compile(
    r'(<details><summary><span class="cat-label">)Card Deck[^<]*(</span></summary>)'
    r'(.*?)'
    r'(</details>)',
    re.DOTALL,
)

# Inside each block, the boundary between legacy junk and the injected
# icon deck is the first DECK-START or STD-DECK-START marker.
DECK_INJECTION_RE = re.compile(
    r'<!--\s*(?:STD-)?DECK-START\s+\S+\s*-->',
)

# Strip the redundant "A New World deck — N cards across N ages.
# Hover any card for its description." paragraph that the inject scripts
# emit RIGHT INSIDE the marker block. The Card Deck summary already
# tells the user what they're looking at.
INTRO_P_RE = re.compile(
    r'<p style="[^"]*">A New World deck[^<]*</p>\n?',
)


def clean(text: str) -> tuple[str, int, int]:
    blocks = 0
    text_decks = 0

    def repl(m: re.Match) -> str:
        nonlocal blocks, text_decks
        blocks += 1
        body = m.group(3)
        marker = DECK_INJECTION_RE.search(body)
        if not marker:
            # No icon deck injected for this civ — leave the block alone
            # rather than wiping its contents.
            return m.group(0)
        # Discard everything before the first DECK-START marker.
        if marker.start() > 0:
            text_decks += 1
        new_body = body[marker.start():]
        # Drop the "A New World deck — N cards…" intro paragraph.
        new_body = INTRO_P_RE.sub("", new_body, count=1)
        new_body = "\n" + new_body.lstrip("\n")
        return m.group(1) + "Card Deck" + m.group(2) + new_body + m.group(4)

    new_text = DECK_BLOCK_RE.sub(repl, text)
    return new_text, blocks, text_decks


def main() -> int:
    text = HTML.read_text(encoding="utf-8")
    new_text, blocks, text_decks = clean(text)
    HTML.write_text(new_text, encoding="utf-8")
    print(f"swept {blocks} Card Deck <details> blocks")
    print(f"  removed legacy intro/text-deck content from {text_decks} of them")
    print(f"  every Card Deck summary is now plain 'Card Deck'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
