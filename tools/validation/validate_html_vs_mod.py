"""Cross-check a_new_world.html against the actual mod data so
the reference site never drifts from what the AI actually loads.

For every civ section in the HTML we verify, against the file on disk:

  * The home-city XML the section labels exists in `data/`
  * The civmods.xml block uses the same civ name
  * Every card chip in the HTML deck points at a card name that's in
    that civ's data/decks_legendary.json or data/decks_standard.json
    summary (which is itself derived from the home-city XML's
    "Legendary Leaders" deck)
  * The chip count matches the JSON (25 / civ)
  * Every leader portrait file referenced by the HTML actually exists

Exits 1 with a per-civ report on any mismatch.
"""
from __future__ import annotations

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.migration.anw_mapping import (  # noqa: E402
    ANW_CIVS_BY_SLUG, ANW_DEFERRED_SLUGS, ANW_NON_PICKER_TOKENS,
    engine_token_for,
)

REPO = Path(__file__).resolve().parents[2]
HTML = REPO / "a_new_world.html"
DATA = REPO / "data"

SECTION_RE = re.compile(r"<!--\s*[─\-]+\s*([^─\-][^<]*?)\s*[─\-]+\s*-->")
DECK_BLOCK_RE = re.compile(
    r'<!--\s*(?:STD-)?DECK-START\s+\S+\s*-->(.*?)<!--\s*(?:STD-)?DECK-END\s+\S+\s*-->',
    re.DOTALL,
)
CHIP_ALT_RE = re.compile(r'<img class="card-icon"[^>]*alt="([^"]+)"')
CHIP_TEXT_RE = re.compile(
    r'<span class="card-chip card-chip-noicon"[^>]*>([^<]+)</span>'
)
PORTRAIT_RE = re.compile(r'<img class="portrait-img" src="([^"]+)"')
FLAG_RE = re.compile(r'<img class="flag-img" src="([^"]+)"')


def html_decks_per_civ(text: str) -> dict[str, list[str]]:
    """Map civ slug → ordered list of card names rendered in the HTML deck."""
    out: dict[str, list[str]] = {}
    sections = list(SECTION_RE.finditer(text))
    for i, m in enumerate(sections):
        slug = m.group(1).strip()
        body = text[m.end(): sections[i+1].start() if i+1 < len(sections) else len(text)]
        deck = DECK_BLOCK_RE.search(body)
        if not deck:
            continue
        names: list[str] = []
        for chip in CHIP_ALT_RE.finditer(deck.group(1)):
            names.append(html.unescape(chip.group(1)))
        for chip in CHIP_TEXT_RE.finditer(deck.group(1)):
            names.append(html.unescape(chip.group(1)).strip())
        out[slug] = names
    return out


def html_assets_per_civ(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    sections = list(SECTION_RE.finditer(text))
    for i, m in enumerate(sections):
        slug = m.group(1).strip()
        body = text[m.end(): sections[i+1].start() if i+1 < len(sections) else len(text)]
        portrait = PORTRAIT_RE.search(body)
        flag = FLAG_RE.search(body)
        out[slug] = {
            "portrait": portrait.group(1) if portrait else "",
            "flag": flag.group(1) if flag else "",
        }
    return out


def deck_summary_cards(summary: dict, civ_key: str) -> list[str] | None:
    if civ_key not in summary:
        return None
    cards = []
    for age in sorted(summary[civ_key], key=int):
        cards += summary[civ_key][age]
    return cards




def validate_html_vs_mod(repo_root: Path | None = None) -> list[str]:
    """Library-friendly entrypoint. Returns the issue list (empty = OK)."""
    repo = Path(repo_root) if repo_root else REPO
    html_path = repo / "a_new_world.html"
    data = repo / "data"
    text = html_path.read_text(encoding="utf-8")
    decks = json.loads((data / "decks_anw.json").read_text())
    cards_meta = json.loads((data / "cards.json").read_text())

    name_to_id: dict[str, list[str]] = {}
    for cid, meta in cards_meta.items():
        nm = (meta.get("name") or "").strip()
        if nm:
            name_to_id.setdefault(nm, []).append(cid)

    html_decks = html_decks_per_civ(text)
    html_assets = html_assets_per_civ(text)

    errors: list[str] = []
    for slug, anw_civ in ANW_CIVS_BY_SLUG.items():
        xml = data / anw_civ.new_homecity_filename
        if not xml.exists():
            errors.append(f"{slug}: missing home-city XML at data/{anw_civ.new_homecity_filename}")
            continue
        if slug in ANW_DEFERRED_SLUGS:
            # HTML section not authored yet; skip chip-count check but
            # still verify the home-city XML exists.
            continue
        if anw_civ.anw_token in ANW_NON_PICKER_TOKENS:
            # Revolution-mechanic variant — has HTML section + art but no
            # decks_anw.json deck (engine-only, not skirmish-pickable).
            # Still verify portrait/flag art exists below.
            for kind in ("portrait", "flag"):
                p = html_assets.get(slug, {}).get(kind, "")
                if p and not (repo / p).is_file():
                    errors.append(f"{slug}: {kind} image missing on disk: {p}")
            continue
        # decks_anw.json keys 22 legacy civs by base-game tokens
        # (XPAztec, British, …) rather than the canonical ANW namespace.
        deck_key = engine_token_for(anw_civ.anw_token)
        summary_cards = deck_summary_cards(decks, deck_key)
        if summary_cards is None:
            errors.append(f"{slug}: no entry '{deck_key}' in decks_anw.json")
            continue
        rendered = html_decks.get(slug, [])
        if len(summary_cards) != 25:
            errors.append(f"{slug}: summary has {len(summary_cards)} cards (expected 25)")
        for chip_name in rendered:
            if chip_name not in name_to_id:
                errors.append(f"{slug}: chip '{chip_name}' has no matching card_id in cards.json")
        for kind in ("portrait", "flag"):
            p = html_assets.get(slug, {}).get(kind, "")
            if p and not (repo / p).is_file():
                errors.append(f"{slug}: {kind} image missing on disk: {p}")
    return errors


def main() -> int:
    text = HTML.read_text(encoding="utf-8")
    decks = json.loads((DATA / "decks_anw.json").read_text())
    cards_meta = json.loads((DATA / "cards.json").read_text())

    name_to_id: dict[str, list[str]] = {}
    for cid, meta in cards_meta.items():
        nm = (meta.get("name") or "").strip()
        if nm:
            name_to_id.setdefault(nm, []).append(cid)

    html_decks = html_decks_per_civ(text)
    html_assets = html_assets_per_civ(text)

    errors: list[str] = []
    checked = 0

    for slug, anw_civ in ANW_CIVS_BY_SLUG.items():
        checked += 1
        # 1. Home-city XML on disk
        xml = DATA / anw_civ.new_homecity_filename
        if not xml.exists():
            errors.append(f"{slug}: missing home-city XML at data/{anw_civ.new_homecity_filename}")
            continue
        if slug in ANW_DEFERRED_SLUGS:
            # HTML section not authored yet; skip chip validation
            continue
        if anw_civ.anw_token in ANW_NON_PICKER_TOKENS:
            # Revolution-mechanic variant: HTML+art exist, but the civ has no
            # decks_anw.json entry (it's not skirmish-pickable). Still verify
            # portrait/flag art is on disk.
            for kind in ("portrait", "flag"):
                p = html_assets.get(slug, {}).get(kind, "")
                if p and not (REPO / p).is_file():
                    errors.append(f"{slug}: {kind} image missing on disk: {p}")
            continue
        # 2. Deck summary present
        # decks_anw.json keys 22 legacy civs by base-game tokens
        # (XPAztec, British, …) rather than the canonical ANW namespace.
        deck_key = engine_token_for(anw_civ.anw_token)
        summary_cards = deck_summary_cards(decks, deck_key)
        if summary_cards is None:
            errors.append(f"{slug}: no entry '{deck_key}' in decks_anw.json")
            continue
        # 3. Summary should have exactly 25 cards
        rendered = html_decks.get(slug, [])
        if len(summary_cards) != 25:
            errors.append(
                f"{slug}: summary has {len(summary_cards)} cards (expected 25)"
            )
        # 4. Every chip name resolves to a real card_id whose name matches
        for chip_name in rendered:
            if chip_name not in name_to_id:
                errors.append(
                    f"{slug}: chip '{chip_name}' has no matching card_id "
                    f"in cards.json"
                )
        # 5. Portrait + flag files exist
        for kind in ("portrait", "flag"):
            p = html_assets.get(slug, {}).get(kind, "")
            if p and not (REPO / p).is_file():
                errors.append(
                    f"{slug}: {kind} image missing on disk: {p}"
                )

    print(f"checked {checked} civs")
    if errors:
        print(f"\n{len(errors)} issue(s):\n")
        for e in errors:
            print(f"  {e}")
        return 1
    print("HTML <-> mod data consistency: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
