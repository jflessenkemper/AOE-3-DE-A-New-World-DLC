"""Refresh the A New World deck block between
<!-- DECK-START <civ> --> and <!-- DECK-END <civ> --> markers in
a_new_world.html for all 48 ANW civs.

Reads:
  - data/anwhomecity*.xml  (the authoritative in-game deck the AI uses)
  - data/cards.json        (card_name → {name, desc, icon})

Writes:
  - a_new_world.html  (between DECK-START/DECK-END markers)

Each card rendered as <span class="card-chip"><img class="card-icon" title="Name — Desc"></span>.
Cards grouped by age using the existing <dl class="deck-grid"> structure.
"""
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.migration.anw_mapping import ANW_CIVS_BY_SLUG, ANW_HOMECITY_MAP

REPO = Path(__file__).resolve().parents[2]
HTML = REPO / "a_new_world.html"
CARDS = REPO / "data" / "cards.json"
DATA = REPO / "data"

AGE_NAMES = ["Discovery", "Colonial", "Fortress", "Industrial", "Imperial"]
ICON_DIR = "resources/images/icons/cards"


def age_bucket_for(card_name: str, cards_meta: dict) -> int:
    """Classify by card name heuristic — minage field from metadata if present."""
    meta = cards_meta.get(card_name, {})
    if "minage" in meta:
        a = int(meta["minage"])
        return max(0, min(4, a))
    # Fallbacks based on known naming conventions
    name_l = card_name.lower()
    if "explore" in name_l or "scout" in name_l or "pioneers" in name_l:
        return 0
    if "musketeer" in name_l or "settler" in name_l or "coureur" in name_l:
        return 1
    if "fort" in name_l or "cavalry" in name_l or "grenadier" in name_l:
        return 2
    if "factor" in name_l or "industri" in name_l or "rocket" in name_l or "gatling" in name_l:
        return 3
    return 2  # Fortress default


def render_deck(civ: str, anw_stem: str, cards_meta: dict) -> str:
    homecity_filename = ANW_HOMECITY_MAP[anw_stem]
    path = DATA / homecity_filename
    tree = ET.parse(path)
    card_names = [c.text for c in tree.getroot().findall(".//deck/cards/card") if c.text]

    by_age: dict[int, list[str]] = {i: [] for i in range(5)}
    for cn in card_names:
        by_age[age_bucket_for(cn, cards_meta)].append(cn)

    out = ['<dl class="deck-grid">']
    for age_idx, cards in sorted(by_age.items()):
        if not cards:
            continue
        out.append(f"<dt>{AGE_NAMES[age_idx]}</dt>")
        chips = []
        for cn in cards:
            meta = cards_meta.get(cn, {})
            display = meta.get("name") or cn
            desc = meta.get("desc", "")
            icon = meta.get("icon") or ""
            title = f"{display} — {desc}" if desc else display
            title_attr = html.escape(title, quote=True)
            alt = html.escape(display, quote=True)
            if icon:
                src = f"{ICON_DIR}/{icon}"
                chips.append(
                    f'<span class="card-chip" title="{title_attr}">'
                    f'<img class="card-icon" src="{src}" alt="{alt}"></span>'
                )
            else:
                chips.append(
                    f'<span class="card-chip card-chip-noicon" title="{title_attr}">{alt}</span>'
                )
        out.append(f"<dd>{''.join(chips)}</dd>")
    out.append("</dl>")
    return "\n".join(out)


def main():
    cards_meta = json.loads(CARDS.read_text(encoding="utf-8"))
    html_text = HTML.read_text(encoding="utf-8")

    ok = miss = 0
    for anw_civ in ANW_CIVS_BY_SLUG.values():
        homecity_filename = ANW_HOMECITY_MAP[anw_civ.anw_stem]
        path = DATA / homecity_filename

        # Skip if homecity file doesn't exist
        if not path.is_file():
            print(f"  SKIP {anw_civ.slug}: homecity file not found")
            miss += 1
            continue

        block = render_deck(anw_civ.slug, anw_civ.anw_stem, cards_meta)
        # Replace between markers
        start_marker = f"<!-- DECK-START {anw_civ.slug} -->"
        end_marker = f"<!-- DECK-END {anw_civ.slug} -->"
        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL,
        )
        m = pattern.search(html_text)
        if not m:
            print(f"  SKIP {anw_civ.slug}: markers not found")
            miss += 1
            continue
        replacement = f"{start_marker}\n{block}\n{end_marker}"
        html_text = html_text[:m.start()] + replacement + html_text[m.end():]
        ok += 1
        print(f"  ok   {anw_civ.slug}: refreshed deck")

    HTML.write_text(html_text, encoding="utf-8")
    print(f"\nrefreshed: {ok}  skipped: {miss}")


if __name__ == "__main__":
    main()
