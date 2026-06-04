"""Extend `data/cards.json` and `resources/images/icons/cards/` with metadata
+ icons for any card that appears in `data/decks_standard.json` but isn't
covered yet (i.e. the standard-civ cards we just pulled from vanilla XMBs).

Re-uses the same techtreey + stringtable + BAR icon-extraction pipeline as
`extract.py`, just with a different input set.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bar import open_bar
from xmb import parse_xmb

REPO = Path(__file__).resolve().parents[2]
GAME = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game"
)
ICON_OUT = REPO / "resources" / "images" / "icons" / "cards"
META_OUT = REPO / "data" / "cards.json"
DECKS_STD = REPO / "data" / "decks_standard.json"
DECKS_LEG = REPO / "data" / "decks_anw_themed.json"
ICON_OUT.mkdir(parents=True, exist_ok=True)


def load_game_meta() -> tuple[dict, dict]:
    print("opening Data.bar ...")
    arc = open_bar(GAME / "Data" / "Data.bar")
    tt = next(e for e in arc.entries
              if e.normalized_name.endswith("techtreey.xml.xmb"))
    print(f"  parsing techtreey.xml ({tt.size_decompressed:,} bytes)")
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

    st = next(e for e in arc.entries
              if e.normalized_name == "strings/english/stringtabley.xml.xmb")
    print(f"  parsing stringtabley.xml ({st.size_decompressed:,} bytes)")
    st_root = parse_xmb(arc.read_payload(st))
    lang = list(st_root)[0]
    strings = {c.attrib["_locid"]: (c.text or "") for c in lang}
    return techs, strings


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
            print(f"  indexing {p.name}")
            self.archives.append(open_bar(p))

    def extract(self, icon_path: str) -> Path | None:
        if not icon_path:
            return None
        target = icon_path.replace("\\", "/").lower()
        basename = Path(target).name
        out = ICON_OUT / basename
        if out.exists():
            return out
        for arc in self.archives:
            for entry in arc.entries:
                if entry.normalized_name.endswith(basename):
                    arc_target = entry.normalized_name
                    if arc_target == target or arc_target.endswith(
                            "/" + target) or arc_target.endswith(basename):
                        out.write_bytes(arc.read_payload(entry))
                        return out
        return None


def main() -> int:
    meta = json.loads(META_OUT.read_text(encoding="utf-8"))
    decks_std = json.loads(DECKS_STD.read_text(encoding="utf-8"))
    decks_leg = (
        json.loads(DECKS_LEG.read_text(encoding="utf-8"))
        if DECKS_LEG.exists() else {}
    )

    needed: set[str] = set()
    for src in (decks_std, decks_leg):
        for civ, by_age in src.items():
            for cards in by_age.values():
                needed.update(cards)
    new_cards = {c for c in needed if c not in meta or not meta[c].get("icon")}
    print(f"need metadata/icons for {len(new_cards)} cards "
          f"(of {len(needed)} in standard decks)")

    if not new_cards:
        print("nothing to do")
        return 0

    techs, strings = load_game_meta()
    extractor = IconExtractor()

    added = 0
    icon_extracted = 0
    icon_missing = 0
    for cname in sorted(new_cards):
        info = techs.get(cname)
        if not info:
            meta.setdefault(cname, {"name": cname, "desc": "", "icon": ""})
            continue
        display = (strings.get(info.get("displaynameid", "") or "", "")
                   or cname).strip()
        desc = (strings.get(info.get("rollovertextid", "") or "", "")
                or "").strip()
        icon_path = (info.get("icon") or "").strip()
        icon_name = ""
        if icon_path:
            out = extractor.extract(icon_path)
            if out:
                icon_name = out.name
                icon_extracted += 1
            else:
                icon_missing += 1
        meta[cname] = {"name": display, "desc": desc, "icon": icon_name}
        added += 1
    print(f"  metadata added: {added}")
    print(f"  icons extracted: {icon_extracted}")
    print(f"  icons missing:  {icon_missing}")

    META_OUT.write_text(json.dumps(meta, indent=2, sort_keys=True),
                        encoding="utf-8")
    print(f"wrote {META_OUT.relative_to(REPO)} ({len(meta)} cards total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
