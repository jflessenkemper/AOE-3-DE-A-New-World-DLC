"""Inject per-civ deck blocks (age on left, cards on right) into the HTML.

Reads:
  - data/cards.json                 {card_name: {name, desc, icon}}
  - data/decks.json                 {civ: {age_str: [card_names...]}}  ← age lookup
  - data/anwhomecity*.xml       the actual `<default>` deck the AI plays,
                                    wrapped in <!-- LL-DEFAULT-DECK-START -->
                                    /<!-- LL-DEFAULT-DECK-END --> markers by
                                    `build_default_decks.py`.

For each civ we render the EXACT set of cards inside that civ's default deck
(so what the user sees in the HTML is what the AI actually plays). The card's
age is looked up from `decks.json` (the full available pool); cards not found
in the pool are bucketed as Discovery.

Edits a_new_world.html in place:
  - Replaces (or inserts) a marker block <!-- DECK-START civ -->...<!-- DECK-END --> immediately
    after each `<code>anwhomecity<key>.xml</code>` paragraph in the 26 revolution
    nation blocks.
  - Idempotent: re-running replaces the previous block.

Each card is an <img class="card-icon"> with a `title` attribute holding "Name —
Description" so the browser shows the description on hover.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HTML_PATH = REPO / "a_new_world.html"
CARDS_PATH = REPO / "data" / "cards.json"
DECKS_PATH = REPO / "data" / "decks.json"

# civ id → mod home city filename stem (matches what's already in the HTML)
CIV_FILES = {
    "Americans":         "anwhomecityamericans.xml",
    "Argentines":        "anwhomecityargentina.xml",
    "BajaCalifornians":  "anwhomecitybajacalifornians.xml",
    "Barbary":           "anwhomecitybarbary.xml",
    "Brazilians":        "anwhomecitybrazil.xml",
    "Californians":      "anwhomecitycalifornia.xml",
    "Canadians":         "anwhomecitycanada.xml",
    "CentralAmericans":  "anwhomecitycentralamericans.xml",
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
    "Yucatans":          "anwhomecityyucatan.xml",
}

AGE_LABELS = {
    0: "Discovery",
    1: "Colonial",
    2: "Fortress",
    3: "Industrial",
    4: "Imperial",
}

ICON_DIR_REL = "resources/images/icons/cards"

DECK_CSS = """\
.deck-grid{display:grid;grid-template-columns:88px 1fr;gap:6px 12px;\
margin:6px 0;align-items:start}
.deck-grid>dt{color:var(--accent);font-weight:600;font-size:.85rem;\
text-transform:uppercase;letter-spacing:.04em;padding-top:6px;text-align:right}
.deck-grid>dd{margin:0;display:flex;flex-wrap:wrap;gap:4px}
.card-chip{display:inline-block;line-height:0;border:1px solid var(--border);\
border-radius:4px;background:var(--card);padding:2px;transition:transform .12s,\
border-color .12s,box-shadow .12s;cursor:help}
.card-chip:hover{transform:translateY(-1px);border-color:var(--accent);\
box-shadow:0 2px 8px rgba(0,0,0,.45)}
.card-icon{height:40px;width:40px;object-fit:contain;display:block;\
border-radius:2px}
"""


DEFAULT_DECK_RE = re.compile(
    r"<!-- LL-DEFAULT-DECK-START -->(.*?)<!-- LL-DEFAULT-DECK-END -->",
    re.DOTALL,
)
# Find a named "A New World" deck block (the one build_themed_decks.py
# writes). XML serializers strip comment markers so we can't rely on them.
LL_DECK_RE = re.compile(
    r"<deck>\s*<name>\s*A New World\s*</name>(.*?)</deck>",
    re.DOTALL,
)
DECK_CARD_RE = re.compile(r"<card[^>]*>([^<]+)</card>")


def load_default_deck(fname: str) -> list[str]:
    """Return the ordered list of card names in this civ's default deck.

    Tries (in order):
      1. The legacy `<!-- LL-DEFAULT-DECK-START -->` marker block
      2. A `<deck>` whose `<name>` is exactly "A New World"
      3. The first `<deck>…</deck>` block in the file
    """
    fp = REPO / "data" / fname
    text = fp.read_text(encoding="utf-8")
    m = DEFAULT_DECK_RE.search(text)
    if m:
        return DECK_CARD_RE.findall(m.group(1))
    m = LL_DECK_RE.search(text)
    if m:
        return DECK_CARD_RE.findall(m.group(1))
    fb = re.search(r"<deck>(.*?)</deck>", text, re.DOTALL)
    if not fb:
        return []
    return DECK_CARD_RE.findall(fb.group(1))


def build_card_age_map(civ: str, decks: dict) -> dict[str, int]:
    """Map every card in this civ's full pool to its age (int)."""
    out: dict[str, int] = {}
    for age_str, names in decks.get(civ, {}).items():
        try:
            age = int(age_str)
        except ValueError:
            continue
        for n in names:
            out.setdefault(n, age)
    return out


def render_deck(civ: str, fname: str, decks: dict, cards: dict) -> str:
    """Build the <dl class="deck-grid"> markup for one civ.

    Renders the ACTUAL default deck (as written into the home city XML) — not
    the full available card pool — so HTML mirrors what the AI plays.
    """
    deck_cards = load_default_deck(fname)
    if not deck_cards:
        return ""
    age_map = build_card_age_map(civ, decks)

    # Group preserving the deck's intra-age ordering
    by_age: dict[int, list[str]] = {}
    for cname in deck_cards:
        age = age_map.get(cname, 0)  # default → Discovery
        by_age.setdefault(age, []).append(cname)
    if not by_age:
        return ""
    rows: list[str] = []
    for age_int in sorted(by_age):
        cards_in_age = by_age[age_int]
        if not cards_in_age:
            continue
        chips: list[str] = []
        for cname in cards_in_age:
            meta = cards.get(cname, {})
            display = meta.get("name") or cname
            desc = meta.get("desc") or ""
            icon = meta.get("icon") or ""
            tooltip = display if not desc else f"{display} — {desc}"
            tooltip_attr = html.escape(tooltip, quote=True)
            display_attr = html.escape(display, quote=True)
            if icon:
                src = f"{ICON_DIR_REL}/{icon}"
                chips.append(
                    f'<span class="card-chip" title="{tooltip_attr}">'
                    f'<img class="card-icon" src="{src}" alt="{display_attr}"></span>'
                )
            else:
                chips.append(
                    f'<span class="card-chip card-chip-noicon" '
                    f'title="{tooltip_attr}">{display_attr}</span>'
                )
        rows.append(
            f'<dt>{AGE_LABELS[age_int]}</dt>\n<dd>' + "".join(chips) + '</dd>'
        )
    if not rows:
        return ""
    total = sum(len(v) for v in by_age.values())
    header = (
        f'<p style="margin:4px 0 6px;font-size:.85rem;color:var(--dim)">'
        f'A New World deck &mdash; {total} cards across '
        f'{len(rows)} ages. Hover any card for its description.</p>\n'
    )
    return (
        f'<!-- DECK-START {civ} -->\n'
        + header
        + '<dl class="deck-grid">\n'
        + "\n".join(rows)
        + '\n</dl>\n'
        + f'<!-- DECK-END {civ} -->\n'
    )


def inject(html_text: str, civ: str, fname: str, block: str) -> str:
    """Insert / replace the deck block right after the `<code>{fname}</code>` <p>."""
    if not block:
        return html_text

    # 1. Strip any existing marker for this civ
    marker_re = re.compile(
        rf'<!-- DECK-START {re.escape(civ)} -->.*?<!-- DECK-END {re.escape(civ)} -->\n?',
        re.DOTALL,
    )
    html_text = marker_re.sub("", html_text)

    # 2. Find the anchor <p>...<code>fname</code>...</p>
    anchor_re = re.compile(
        rf'(<p[^>]*>[^<]*<code>{re.escape(fname)}</code>[^<]*</p>\n?)'
    )
    m = anchor_re.search(html_text)
    if not m:
        raise RuntimeError(f"anchor not found for {civ} ({fname})")
    insert_at = m.end()
    return html_text[:insert_at] + block + html_text[insert_at:]


def ensure_css(html_text: str) -> str:
    """Insert DECK_CSS before </style> if not already present."""
    if "DECK-CSS-MARKER" in html_text:
        # Replace existing block (idempotent)
        return re.sub(
            r"/\* DECK-CSS-MARKER \*/.*?/\* DECK-CSS-END \*/",
            f"/* DECK-CSS-MARKER */\n{DECK_CSS}/* DECK-CSS-END */",
            html_text,
            count=1,
            flags=re.DOTALL,
        )
    insert = f"/* DECK-CSS-MARKER */\n{DECK_CSS}/* DECK-CSS-END */\n"
    return html_text.replace("</style>", insert + "</style>", 1)


def main() -> int:
    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    decks = json.loads(DECKS_PATH.read_text(encoding="utf-8"))
    text = HTML_PATH.read_text(encoding="utf-8")

    text = ensure_css(text)
    injected = 0
    skipped = 0
    for civ, fname in CIV_FILES.items():
        block = render_deck(civ, fname, decks, cards)
        if not block:
            skipped += 1
            print(f"  SKIP {civ}: no deck data")
            continue
        text = inject(text, civ, fname, block)
        injected += 1

    HTML_PATH.write_text(text, encoding="utf-8")
    print(f"injected: {injected}  skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
