"""End-to-end extraction: cards from 26 revolution decks → metadata + icons.

Outputs:
  - data/cards.json         {card_name: {name, desc, icon}}
  - data/decks.json         {civ_id: {age_int: [card_names...]}}
  - resources/images/icons/cards/<icon_basename>.png   (extracted from BARs)
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from bar import open_bar
from xmb import parse_xmb

REPO = Path(__file__).resolve().parents[2]
GAME = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game"
)
DECK_DIR = REPO / "data"
ICON_OUT = REPO / "resources" / "images" / "icons" / "cards"
META_OUT = REPO / "data" / "cards.json"
DECKS_OUT = REPO / "data" / "decks.json"
ICON_OUT.mkdir(parents=True, exist_ok=True)

# civ id → display name + deck filename
CIVS = {
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


def log(msg: str) -> None:
    print(msg, flush=True)


# ── parse decks ──────────────────────────────────────────────────────────
def parse_deck(path: Path) -> dict[int, list[str]]:
    by_age: dict[int, list[str]] = defaultdict(list)
    seen: set[str] = set()
    tree = ET.parse(path)
    for card in tree.iterfind(".//card"):
        name = (card.findtext("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        age = int(card.findtext("age") or "0")
        by_age[age].append(name)
    return dict(by_age)


# ── load techtreey + stringtable from Data.bar ───────────────────────────
def load_game_meta() -> tuple[dict, dict]:
    log("opening Data.bar...")
    arc = open_bar(GAME / "Data" / "Data.bar")
    tt = next(e for e in arc.entries
              if e.normalized_name.endswith("techtreey.xml.xmb"))
    log(f"  parsing techtreey.xml.XMB ({tt.size_decompressed:,} bytes)...")
    tt_root = parse_xmb(arc.read_payload(tt))
    techs: dict[str, dict] = {}
    for tech in tt_root:
        name = tech.attrib.get("name")
        if not name:
            continue
        techs[name] = {
            "displaynameid": tech.findtext("displaynameid"),
            "rollovertextid": tech.findtext("rollovertextid"),
            "icon": tech.findtext("icon"),
        }
    log(f"  techtreey: {len(techs):,} techs")

    st = next(e for e in arc.entries
              if e.normalized_name == "strings/english/stringtabley.xml.xmb")
    log(f"  parsing stringtabley.xml.XMB ({st.size_decompressed:,} bytes)...")
    st_root = parse_xmb(arc.read_payload(st))
    lang = list(st_root)[0]
    strings = {c.attrib["_locid"]: (c.text or "") for c in lang}
    log(f"  stringtable: {len(strings):,} strings")
    return techs, strings


# ── augment with mod-defined card techs ──────────────────────────────────
def load_mod_techs() -> dict[str, dict]:
    """Parse data/techtreemods.xml for ANW* card techs.

    The mod uses unusual whitespace ('name =' with space) and lowercase tags
    inconsistently, so we go through ET with permissive parsing.
    """
    path = DECK_DIR / "techtreemods.xml"
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8", errors="replace")
    # ET handles "name ='foo'" fine, normalize attribute case for safety
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        log(f"  WARN: techtreemods.xml parse error: {e}")
        return out
    for tech in root.iter():
        if tech.tag.lower() != "tech":
            continue
        name = tech.attrib.get("name") or tech.attrib.get("Name")
        if not name:
            continue
        # Look up children case-insensitively
        def child(tag):
            for c in tech:
                if c.tag.lower() == tag:
                    return (c.text or "").strip()
            return None
        out[name] = {
            "displaynameid": child("displaynameid"),
            "rollovertextid": child("rollovertextid"),
            "icon": child("icon"),
        }
    log(f"  mod techs: {len(out):,} entries")
    return out


# ── icon extraction from BAR archives ────────────────────────────────────
class IconExtractor:
    SOURCES = [
        GAME / "UI" / "UIResources1.bar",
        GAME / "UI" / "UIResources2.bar",
        GAME / "UI" / "UIResources3.bar",
        GAME / "UI" / "UIResources4.bar",
        GAME / "UI" / "UI.bar",
        GAME / "Art" / "ArtUI.bar",
    ]

    def __init__(self):
        self.archives = []
        for p in self.SOURCES:
            if not p.exists():
                continue
            log(f"  indexing {p.name}...")
            arc = open_bar(p)
            self.archives.append(arc)

    def extract(self, icon_path: str) -> Path | None:
        """icon_path like 'resources\\art\\units\\.../foo_icon.png'.

        Try matching across all source BARs by normalized full path.
        Return saved Path or None.
        """
        if not icon_path:
            return None
        target = icon_path.replace("\\", "/").lower()
        basename = Path(target).name
        out = ICON_OUT / basename
        if out.exists():
            return out
        for arc in self.archives:
            for entry in arc.entries:
                norm = entry.normalized_name
                if norm == target or norm.endswith("/" + target) \
                        or norm.endswith(basename):
                    if not norm.endswith(basename):
                        continue
                    payload = arc.read_payload(entry)
                    out.write_bytes(payload)
                    return out
        return None


# ── orchestrator ─────────────────────────────────────────────────────────
def main() -> int:
    log("== Step 1: parse 26 revolution decks ==")
    decks: dict[str, dict[int, list[str]]] = {}
    all_cards: set[str] = set()
    for civ, fname in CIVS.items():
        deck_path = DECK_DIR / fname
        if not deck_path.exists():
            log(f"  MISSING: {fname}")
            continue
        decks[civ] = parse_deck(deck_path)
        for cards in decks[civ].values():
            all_cards.update(cards)
    log(f"  unique cards across all civs: {len(all_cards):,}")

    log("\n== Step 2: load game metadata ==")
    techs, strings = load_game_meta()
    log("  loading mod techs...")
    mod_techs = load_mod_techs()

    log("\n== Step 3: resolve card metadata ==")
    cards_meta: dict[str, dict] = {}
    missing_tech = 0
    missing_icon_path = 0
    for cname in sorted(all_cards):
        info = techs.get(cname) or mod_techs.get(cname)
        if not info:
            missing_tech += 1
            cards_meta[cname] = {"name": cname, "desc": "", "icon": ""}
            continue
        name = (strings.get(info.get("displaynameid", "") or "", "")
                or cname).strip()
        desc = (strings.get(info.get("rollovertextid", "") or "", "") or
                "").strip()
        icon_path = (info.get("icon") or "").strip()
        if not icon_path:
            missing_icon_path += 1
        cards_meta[cname] = {
            "name": name,
            "desc": desc,
            "icon_src": icon_path,
        }
    log(f"  resolved: {len(cards_meta) - missing_tech} / {len(cards_meta)}")
    log(f"  missing tech def: {missing_tech}")
    log(f"  no icon path: {missing_icon_path}")

    log("\n== Step 4: extract icons ==")
    extractor = IconExtractor()
    extracted = 0
    not_found = 0
    for cname, meta in cards_meta.items():
        icon_path = meta.get("icon_src", "")
        if not icon_path:
            meta["icon"] = ""
            continue
        out = extractor.extract(icon_path)
        if out:
            meta["icon"] = out.name
            extracted += 1
        else:
            meta["icon"] = ""
            not_found += 1
        meta.pop("icon_src", None)
    log(f"  extracted: {extracted}")
    log(f"  icon path set but not found in BARs: {not_found}")

    log("\n== Step 5: write outputs ==")
    META_OUT.write_text(
        json.dumps(cards_meta, indent=2, sort_keys=True), encoding="utf-8"
    )
    log(f"  wrote {META_OUT.relative_to(REPO)}")
    DECKS_OUT.write_text(
        json.dumps({civ: {str(a): cs for a, cs in by_age.items()}
                    for civ, by_age in decks.items()}, indent=2),
        encoding="utf-8",
    )
    log(f"  wrote {DECKS_OUT.relative_to(REPO)}")
    log(f"  icons in {ICON_OUT.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
