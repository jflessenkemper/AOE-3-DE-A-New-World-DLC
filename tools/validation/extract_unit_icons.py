#!/usr/bin/env python3
"""Extract every unit menu/selection icon referenced by the game's proto.xml
straight out of the AoE3 DE BAR archives, so the unit index and the
release-readiness site can render an authentic icon for *every* unit a nation
can train.

Why this exists
---------------
The old icon resolver guessed a PNG basename from the proto name (slug +
``_icon.png``) and only resolved ~168/408 roster units, because most unit
icons had never been extracted from the game. But the game ships every unit's
icon as a PNG *inside* ``UI/UIResources1.bar`` (1,400+ unit icons), and each
unit's ``proto.xml`` ``<icon>`` element names the exact file. Matching on that
path is unambiguous — no fuzzy slugging — and resolves 404/408 roster units.

Pipeline
--------
1. Parse ``artifacts/roster_audit/base_data/proto.xml`` → ``{proto: <icon> path}``.
2. Index the relevant BARs (UIResources1/2, UI, ArtUI) by normalized path.
3. For every proto, find its icon entry by exact normalized path (falling back
   to basename), write the PNG payload to
   ``resources/images/icons/units/<basename>``.
4. Emit ``artifacts/unit_index/proto_icon_map.json`` = ``{proto: basename}`` so
   downstream tools resolve icons by proto with zero guessing.

Run: ``python3 tools/validation/extract_unit_icons.py``
Idempotent — re-running only re-copies changed/missing files.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
GAME = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game"
)
PROTO_XML = REPO / "artifacts" / "roster_audit" / "base_data" / "proto.xml"
ROSTERS = REPO / "artifacts" / "roster_audit" / "resolved_rosters.json"
ICON_OUT = REPO / "resources" / "images" / "icons" / "units"
MAP_OUT = REPO / "artifacts" / "unit_index" / "proto_icon_map.json"

# BAR archives that hold unit icon PNGs, in priority order. UIResources1.bar
# carries essentially all of them; the rest are cheap fallbacks.
BAR_SOURCES = [
    GAME / "UI" / "UIResources1.bar",
    GAME / "UI" / "UIResources2.bar",
    GAME / "UI" / "UI.bar",
    GAME / "Art" / "ArtUI.bar",
]

# Make the in-repo bar.py reader importable (tools/cardextract/bar.py).
sys.path.insert(0, str(REPO / "tools" / "cardextract"))
from bar import open_bar  # noqa: E402


def load_proto_icon_paths() -> dict[str, str]:
    """Return ``{proto_name: icon_path}`` for every unit in proto.xml that
    declares an ``<icon>``. The path is the game-relative Windows path, e.g.
    ``resources\\art\\units\\cavalry\\cossack\\cossack_icon.png``."""
    tree = ET.parse(PROTO_XML)
    root = tree.getroot()
    out: dict[str, str] = {}
    for unit in root.iter("unit"):
        name = unit.get("name", "")
        ic = unit.find("icon")
        if name and ic is not None and ic.text and ic.text.strip():
            out[name] = ic.text.strip()
    return out


def load_needed_protos() -> set[str]:
    """The set of protos that appear in any civ roster (hero + military +
    mercenaries) — i.e. the icons we actually need on the site."""
    data = json.loads(ROSTERS.read_text(encoding="utf-8"))
    needed: set[str] = set()
    for civ in data.values():
        for u in civ.get("military_units", []) + civ.get("mercenaries", []):
            needed.add(u["proto"])
        for h in civ.get("hero", []):
            needed.add(h)
    return needed


class BarIndex:
    """Indexes one-or-more BARs by normalized full path and by basename for
    fast icon lookup."""

    def __init__(self, bar_paths: list[Path]):
        self.archives = []
        self.by_norm: dict[str, tuple] = {}     # normalized path -> (arc, entry)
        self.by_base: dict[str, tuple] = {}     # basename -> (arc, entry)
        for p in bar_paths:
            if not p.exists():
                print(f"  [skip] missing BAR: {p.name}")
                continue
            arc = open_bar(p)
            self.archives.append(arc)
            for e in arc.entries:
                nm = e.normalized_name
                if not nm.endswith(".png"):
                    continue
                # First archive wins (priority order) for any given key.
                self.by_norm.setdefault(nm, (arc, e))
                self.by_base.setdefault(Path(nm).name, (arc, e))
            print(f"  indexed {p.name}: {len(arc.entries)} entries")

    def find(self, icon_path: str):
        """Resolve a proto ``<icon>`` path to ``(arc, entry, basename)`` or
        ``None``. Tries exact normalized path first, then basename."""
        norm = icon_path.replace("\\", "/").lower().lstrip("/")
        base = Path(norm).name
        hit = self.by_norm.get(norm)
        if hit is None:
            # Some proto paths omit a leading dir segment; try suffix match.
            for n, ae in self.by_norm.items():
                if n.endswith("/" + norm):
                    hit = ae
                    break
        if hit is None:
            hit = self.by_base.get(base)
        if hit is None:
            return None
        arc, entry = hit
        return arc, entry, base


def main() -> int:
    print("Loading proto icon paths ...", flush=True)
    proto_icon = load_proto_icon_paths()
    needed = load_needed_protos()
    print(f"  proto.xml units with <icon>: {len(proto_icon)}")
    print(f"  roster units needed         : {len(needed)}")

    print("Indexing BAR archives ...", flush=True)
    index = BarIndex(BAR_SOURCES)

    ICON_OUT.mkdir(parents=True, exist_ok=True)
    MAP_OUT.parent.mkdir(parents=True, exist_ok=True)

    proto_to_icon: dict[str, str] = {}
    written = 0
    reused = 0
    no_path: list[str] = []
    not_in_bar: list[str] = []
    # Detect basename collisions (two different source paths, same out file).
    base_to_src: dict[str, str] = {}
    collisions: list[str] = []

    for proto in sorted(needed):
        icon_path = proto_icon.get(proto)
        if not icon_path:
            no_path.append(proto)
            continue
        found = index.find(icon_path)
        if found is None:
            not_in_bar.append(proto)
            continue
        arc, entry, base = found
        norm_src = icon_path.replace("\\", "/").lower()
        if base in base_to_src and base_to_src[base] != norm_src:
            collisions.append(f"{base}: {base_to_src[base]} vs {norm_src}")
        base_to_src[base] = norm_src

        out = ICON_OUT / base
        proto_to_icon[proto] = base
        if out.exists():
            reused += 1
            continue
        try:
            payload = arc.read_payload(entry)
            out.write_bytes(payload)
            written += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] failed to extract {proto} ({base}): {exc}",
                  file=sys.stderr)
            proto_to_icon.pop(proto, None)
            not_in_bar.append(proto)

    MAP_OUT.write_text(json.dumps(proto_to_icon, indent=2, ensure_ascii=False))

    resolved = len(proto_to_icon)
    total = len(needed)
    print("\n=== EXTRACTION SUMMARY ===")
    print(f"  resolved icons : {resolved}/{total} roster units")
    print(f"  newly written  : {written}")
    print(f"  already present: {reused}")
    print(f"  no <icon> path : {len(no_path)} {no_path[:8]}")
    print(f"  path not in BAR: {len(not_in_bar)} {not_in_bar[:8]}")
    if collisions:
        print(f"  [note] {len(collisions)} basename collisions (last wins):")
        for c in collisions[:8]:
            print(f"    {c}")
    print(f"  -> {MAP_OUT.relative_to(REPO)}")
    print(f"  -> {ICON_OUT.relative_to(REPO)}/ ({resolved} icons mapped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
