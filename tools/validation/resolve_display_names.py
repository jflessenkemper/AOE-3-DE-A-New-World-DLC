#!/usr/bin/env python3
"""resolve_display_names.py — build a `proto -> in-game display name` map from
the game's own data, so every downstream tool can show/match the real unit
name (e.g. ``deIncaRunner`` -> "Chimu Runner") instead of the raw engine proto.

Why this exists
---------------
The unit index (`build_unit_index.py`) labels many units with their raw proto
because it never resolves the engine's display-name string. That breaks two
things at once:
  * the release-readiness site shows ugly captions like "deHoopThrower"
    instead of "Fire Thrower";
  * `classify_unit_roles.py` can't match a civ's curated signature names
    (display spellings) against its roster, so genuinely-present unique units
    (Japanese Samurai = ``ypKensei``, Maltese Sentinel = ``deMalteseMusketeer``,
    Inca Huaraca = ``deSlinger`` ...) were wrongly flagged as content gaps.

The authoritative source is the game data itself:
  proto.xml / protomods.xml  ->  <unit name="PROTO"><displaynameid>NNNN</...>
  string tables              ->  locid NNNN  ->  human display string

Resolving through that chain is exact and non-guessing — the same lookup the
engine performs at runtime.

Sources (first found wins for the proto map; mod overrides base for strings):
  artifacts/roster_audit/base_data/proto.xml   (base protos)
  data/protomods.xml                            (ANW mod proto add/override)
  artifacts/extracted_base_stringtable.xml      (base English strings)
  data/strings/english/stringmods.xml           (ANW mod English strings)

Output:
  artifacts/unit_index/proto_display_names.json
      { "generated": ..., "count": N, "names": { proto: "Display Name" } }

Run:  python3 tools/validation/resolve_display_names.py
Or import:  from resolve_display_names import load_display_names
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

PROTO_BASE = REPO / "artifacts" / "roster_audit" / "base_data" / "proto.xml"
PROTO_MODS = REPO / "data" / "protomods.xml"
STR_BASE   = REPO / "artifacts" / "extracted_base_stringtable.xml"
STR_MODS   = REPO / "data" / "strings" / "english" / "stringmods.xml"

OUT = REPO / "artifacts" / "unit_index" / "proto_display_names.json"

_UNIT_RE = re.compile(r"<unit\b[^>]*\bname=\"([^\"]+)\"[^>]*>(.*?)</unit>", re.S)
_DID_RE  = re.compile(r"<displaynameid>(\d+)</displaynameid>")
_BASE_STR_RE = re.compile(r"<string _locid=\"(\d+)\"[^>]*>(.*?)</string>", re.S)
_MODS_STR_RE = re.compile(r"<String _locID=\"(\d+)\"[^>]*>(.*?)</String>", re.S)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def _build_string_table() -> dict[str, str]:
    strings: dict[str, str] = {}
    for locid, val in _BASE_STR_RE.findall(_read(STR_BASE)):
        strings[locid] = val
    # Mod strings override / extend base.
    for locid, val in _MODS_STR_RE.findall(_read(STR_MODS)):
        strings[locid] = val
    return strings


def _build_proto_displayid() -> dict[str, str]:
    pmap: dict[str, str] = {}
    for src in (PROTO_BASE, PROTO_MODS):
        for name, body in _UNIT_RE.findall(_read(src)):
            did = _DID_RE.search(body)
            if did:
                pmap[name] = did.group(1)   # later src (mods) overrides base
    return pmap


def build_display_names() -> dict[str, str]:
    """Return {proto: display_name} for every proto whose displaynameid
    resolves to a real string. Display strings that are empty or still look
    like a placeholder are skipped."""
    strings = _build_string_table()
    proto_did = _build_proto_displayid()
    names: dict[str, str] = {}
    for proto, did in proto_did.items():
        s = strings.get(did)
        if not s:
            continue
        s = s.strip()
        # Skip obvious non-names (format strings / empty).
        if not s or "%" in s or s.startswith("<"):
            continue
        names[proto] = s
    return names


def load_display_names() -> dict[str, str]:
    """Load the cached map if present and non-empty, else rebuild it."""
    if OUT.is_file():
        try:
            blob = json.loads(OUT.read_text(encoding="utf-8"))
            if blob.get("names"):
                return blob["names"]
        except Exception:
            pass
    return build_display_names()


def main() -> int:
    names = build_display_names()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "count": len(names),
        "names": dict(sorted(names.items())),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resolved {len(names)} proto display names.")
    print(f"  -> {OUT.relative_to(REPO)}")
    # Spot samples for a quick sanity glance.
    for p in ("deIncaRunner", "deHoopThrower", "ypKensei", "deMalteseMusketeer"):
        if p in names:
            print(f"     {p} -> {names[p]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
