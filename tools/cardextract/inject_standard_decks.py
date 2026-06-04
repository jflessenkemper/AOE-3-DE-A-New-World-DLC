"""Render the A New World deck inside each STANDARD-civ Card Deck
<details> block in a_new_world.html.

Reads:
  - data/cards.json            {card_name: {name, desc, icon}}
  - data/decks_standard.json   {civ_id: {age_str: [card_names...]}}
  - data/homecity<basename>.xml  (the override we wrote — read directly so
                                  HTML always mirrors the file the AI loads)

For each entry in CIV_SECTIONS we:
  1. Locate the civ's section by its `<!-- ──── <slug> ──── -->` comment
  2. Find the FIRST `<details>…<span class="cat-label">Card Deck</span>…</details>`
     within that section
  3. Inject (or replace) a `<!-- STD-DECK-START civ -->…<!-- STD-DECK-END civ -->`
     block right before `</details>` so the existing description text stays
     in place above the card grid

Idempotent: re-running replaces the previous block.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HTML_PATH = REPO / "a_new_world.html"
CARDS_PATH = REPO / "data" / "cards.json"
DECKS_STD_PATH = REPO / "data" / "decks_standard.json"

# civ_id (decks_standard.json key)  →  HTML civ-comment slug
CIV_SECTIONS = {
    "Aztecs":         "Aztecs",
    "British":        "British",
    "Chinese":        "Chinese",
    "Dutch":          "Dutch",
    "Ethiopians":     "Ethiopians",
    "French":         "French",
    "Germans":        "Germans",
    "Haudenosaunee":  "Haudenosaunee",
    "Hausa":          "Hausa",
    "Inca":           "Inca",
    "Indians":        "Indians",
    "Italians":       "Italians",
    "Japanese":       "Japanese",
    "Lakota":         "Lakota",
    "Maltese":        "Maltese",
    "MexicansStd":    "Mexicans (Standard)",
    "Ottomans":       "Ottomans",
    "Portuguese":     "Portuguese",
    "Russians":       "Russians",
    "Spanish":        "Spanish",
    "Swedes":         "Swedes",
    "UnitedStates":   "United States",
}

AGE_LABELS = {0: "Discovery", 1: "Colonial", 2: "Fortress",
              3: "Industrial", 4: "Imperial"}
ICON_DIR_REL = "resources/images/icons/cards"


def render_deck(civ_id: str, by_age: dict[str, list[str]], cards: dict) -> str:
    if not by_age:
        return ""
    rows: list[str] = []
    for age_int in sorted(int(a) for a in by_age):
        names = by_age[str(age_int)]
        if not names:
            continue
        chips: list[str] = []
        for cname in names:
            meta = cards.get(cname, {})
            display = meta.get("name") or cname
            desc = meta.get("desc") or ""
            icon = meta.get("icon") or ""
            tooltip = display if not desc else f"{display} — {desc}"
            t_attr = html.escape(tooltip, quote=True)
            d_attr = html.escape(display, quote=True)
            if icon:
                src = f"{ICON_DIR_REL}/{icon}"
                chips.append(
                    f'<span class="card-chip" title="{t_attr}">'
                    f'<img class="card-icon" src="{src}" alt="{d_attr}"></span>'
                )
            else:
                chips.append(
                    f'<span class="card-chip card-chip-noicon" '
                    f'title="{t_attr}">{d_attr}</span>'
                )
        rows.append(
            f'<dt>{AGE_LABELS[age_int]}</dt>\n<dd>' + "".join(chips) + '</dd>'
        )
    if not rows:
        return ""
    total = sum(len(v) for v in by_age.values())
    header = (
        f'<p style="margin:6px 0 4px;font-size:.85rem;color:var(--dim)">'
        f'A New World deck (override) &mdash; {total} cards across '
        f'{len(rows)} ages. Hover any card for its description.</p>\n'
    )
    return (
        f'<!-- STD-DECK-START {civ_id} -->\n'
        + header
        + '<dl class="deck-grid">\n'
        + "\n".join(rows)
        + '\n</dl>\n'
        + f'<!-- STD-DECK-END {civ_id} -->\n'
    )


# ── HTML surgery ────────────────────────────────────────────────────────────

def _section_bounds(text: str, slug: str, all_slugs: list[str]) -> tuple[int, int] | None:
    """Find [start, end) of the civ section identified by `slug`."""
    # Comment regex tolerant to box-drawing dashes vs ASCII dashes
    section_re = re.compile(
        r"<!--\s*[─\-]+\s*" + re.escape(slug) + r"\s*[─\-]+\s*-->"
    )
    m = section_re.search(text)
    if not m:
        return None
    start = m.end()
    # End at the next civ comment OR EOF
    next_re = re.compile(r"<!--\s*[─\-]+\s*([^─\-][^<]*?)\s*[─\-]+\s*-->")
    next_m = next_re.search(text, start)
    end = next_m.start() if next_m else len(text)
    return start, end


def inject_into_section(html_text: str, civ_id: str, slug: str,
                        block: str, all_slugs: list[str]) -> tuple[str, str]:
    """Returns (new_text, status). Idempotent."""
    bounds = _section_bounds(html_text, slug, all_slugs)
    if not bounds:
        return html_text, f"section-not-found"
    start, end = bounds
    section = html_text[start:end]

    # 1. Strip any existing block for this civ
    block_re = re.compile(
        rf'<!-- STD-DECK-START {re.escape(civ_id)} -->.*?'
        rf'<!-- STD-DECK-END {re.escape(civ_id)} -->\n?',
        re.DOTALL,
    )
    section = block_re.sub("", section)

    # 2. Find the FIRST Card Deck details block in this section
    cd_re = re.compile(
        r'(<details><summary><span class="cat-label">Card Deck'
        r'(?:[^<]*)?</span></summary>.*?)(</details>)',
        re.DOTALL,
    )
    cd_m = cd_re.search(section)
    if not cd_m:
        return html_text[:start] + section + html_text[end:], "no-card-deck"
    new_section = section[:cd_m.start(2)] + block + section[cd_m.start(2):]
    return html_text[:start] + new_section + html_text[end:], "ok"


def main() -> int:
    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    decks = json.loads(DECKS_STD_PATH.read_text(encoding="utf-8"))
    text = HTML_PATH.read_text(encoding="utf-8")

    slugs = list(CIV_SECTIONS.values())
    injected = skipped = 0
    for civ_id, slug in CIV_SECTIONS.items():
        by_age = decks.get(civ_id, {})
        block = render_deck(civ_id, by_age, cards)
        if not block:
            skipped += 1
            print(f"  SKIP {civ_id}: no deck data")
            continue
        text, status = inject_into_section(text, civ_id, slug, block, slugs)
        if status != "ok":
            skipped += 1
            print(f"  SKIP {civ_id}: {status}")
            continue
        injected += 1
        print(f"  ok   {civ_id}: injected into '{slug}' section")

    HTML_PATH.write_text(text, encoding="utf-8")
    print(f"\ninjected: {injected}  skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
