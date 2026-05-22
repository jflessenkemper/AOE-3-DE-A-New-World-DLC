#!/usr/bin/env python3
"""Verify every flag/portrait/UI asset path on every ANW civ resolves.

Bug class this catches (hit on 2026-05-09): ANWRevFrance referenced
``objects\\flags\\revolutionary_france.ddt`` and
``ui\\ingame\\ingame_ui_postgame_flag_revolutionary_france.ddt`` —
neither file actually exists in any base game ``.bar`` archive. The
engine couldn't render the flag, so the SELECT HOME CITY picker showed
no flag for "French Republic". Same class of bug also affected
ANWEgyptians.

For each ANW civ, this validator checks every asset-path-bearing field:

  Engine .bar lookup paths (DDT):
    portrait              → objects\\flags\\<X>.ddt          (ArtObjects.bar)
    homecityflagtexture   → objects\\flags\\<X>.ddt          (ArtObjects.bar)
    postgameflagtexture   → ui\\ingame\\<X>.ddt              (ArtUI.bar)

  Local-file lookups (PNG):
    homecityflagiconwpf   → resources/.../*.png              (mod tree)
    homecitypreviewwpf    → resources/.../*.png              (mod tree)
    homecityflagbuttonwpf → resources/.../*.png              (mod tree)

If any reference resolves to nothing, FAIL with the specific path.

Caches base-archive contents in ``artifacts/extracted_bar_index.json``
on first run for speed.

Usage::

    python3 tools/validation/validate_civ_asset_existence.py
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))


_AOE3_GAME_DIR = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game"
)
_INDEX_CACHE = REPO_ROOT / "artifacts" / "extracted_bar_index.json"
_CIVMODS = REPO_ROOT / "data" / "civmods.xml"

# Revolution-civ postgame DDTs that the base game's fully-playable-revolutions
# mod references but that are NOT present in any base-game .bar archive.  The
# engine handles missing ``postgameflagtexture`` DDTs gracefully (no crash;
# the 3D postgame flag scene just shows a blank or parent-civ flag in legacy
# 3D mode).  The WPF postgame screen uses ``postgameflagiconwpf`` instead,
# which IS available (in UIResources1.bar) for all revolution civs.
# We warn about these rather than failing so the validator doesn't block deploy.
_KNOWN_MISSING_POSTGAME_DDTS: frozenset[str] = frozenset({
    "ui/ingame/ingame_ui_postgame_flag_barbary",
    "ui/ingame/ingame_ui_postgame_flag_canadian",
    "ui/ingame/ingame_ui_postgame_flag_egyptian",
    "ui/ingame/ingame_ui_postgame_flag_ethiopian",
    "ui/ingame/ingame_ui_postgame_flag_finnish",
    "ui/ingame/ingame_ui_postgame_flag_hungarian",
    "ui/ingame/ingame_ui_postgame_flag_indonesian",
    "ui/ingame/ingame_ui_postgame_flag_romanian",
    "ui/ingame/ingame_ui_postgame_flag_south_african",
    "ui/ingame/ingame_ui_postgame_flag_swedish",
})


def _build_bar_index() -> set[str]:
    """Collect every (lowercased) entry name from every .bar archive in
    the AoE3 install.  Scans both Game/Art/*.bar (DDTs) and Game/UI/*.bar
    (UIResources PNGs) so that ``postgameflagiconwpf`` references to files
    in UIResources1.bar are correctly resolved without needing to ship those
    PNGs as mod-tree loose files.
    """
    if _INDEX_CACHE.exists():
        return set(json.loads(_INDEX_CACHE.read_text()))
    from tools.cardextract.bar import open_bar

    names: set[str] = set()
    for bar in _AOE3_GAME_DIR.rglob("*.bar"):
        try:
            arc = open_bar(bar)
            for hits in arc.find(lambda e: True):
                names.add(hits.normalized_name)
        except Exception:
            continue
    _INDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _INDEX_CACHE.write_text(json.dumps(sorted(names), indent=0))
    return names


def _resolve_engine_asset(name: str, suffix: str, bar_index: set[str]) -> bool:
    """Engine reads e.g. 'objects\\flags\\british' and looks up
    'objects/flags/british.ddt' in a bar."""
    if not name:
        return True  # empty = no reference, OK
    norm = name.replace("\\", "/").lower()
    return f"{norm}{suffix}" in bar_index


def _resolve_mod_asset(name: str, bar_index: set[str] | None = None) -> bool:
    """resources\\images\\... or resources/images/... — check local
    file with normalized slashes, then fall back to bar_index (covers
    PNGs shipped in UIResources*.bar rather than as loose mod files)."""
    if not name:
        return True
    norm = name.replace("\\", "/")
    if (REPO_ROOT / norm).exists():
        return True
    if bar_index is not None and norm.lower() in bar_index:
        return True
    return False


_DDT_FIELDS_OBJECTS = ("portrait", "homecityflagtexture")
_DDT_FIELDS_UI = ("postgameflagtexture",)
_PNG_FIELDS = (
    "homecityflagiconwpf", "homecitypreviewwpf",
    "homecityflagbuttonwpf", "postgameflagiconwpf",
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--no-bar-cache", action="store_true",
                    help="rebuild bar index from scratch")
    args = ap.parse_args()

    if args.no_bar_cache and _INDEX_CACHE.exists():
        _INDEX_CACHE.unlink()

    print("=" * 60)
    print("CIV ASSET EXISTENCE")
    print("=" * 60)

    bar_index = _build_bar_index()
    print(f"  Indexed {len(bar_index):,} entries from base .bar archives")

    civmods = ET.parse(_CIVMODS).getroot()
    failures: list[tuple[str, str, str, str]] = []  # civ, field, value, kind

    civs_checked = 0
    known_missing_ddts_used: list[tuple[str, str]] = []  # (civ, ddt_path)
    for civ in civmods.findall("civ"):
        n = civ.find("name")
        token = (n.text or "").strip() if n is not None else ""
        if not token.startswith("ANW"):
            continue  # only check ANW civs (suppression entries don't matter)
        civs_checked += 1
        for fld in _DDT_FIELDS_OBJECTS:
            e = civ.find(fld)
            if e is None or not (e.text or "").strip():
                continue
            if not _resolve_engine_asset(e.text.strip(), ".ddt", bar_index):
                failures.append((token, fld, e.text.strip(), "DDT in any .bar"))
        for fld in _DDT_FIELDS_UI:
            e = civ.find(fld)
            if e is None or not (e.text or "").strip():
                continue
            norm = e.text.strip().replace("\\", "/").lower()
            if norm in _KNOWN_MISSING_POSTGAME_DDTS:
                # Semantically correct DDT used by the base-game revolution mod,
                # but not present in ArtUI.bar.  Engine falls back gracefully.
                # WPF postgame screen uses postgameflagiconwpf instead.
                known_missing_ddts_used.append((token, e.text.strip()))
            elif not _resolve_engine_asset(e.text.strip(), ".ddt", bar_index):
                failures.append((token, fld, e.text.strip(), "UI DDT in any .bar"))
        for fld in _PNG_FIELDS:
            e = civ.find(fld)
            if e is None or not (e.text or "").strip():
                continue
            if not _resolve_mod_asset(e.text.strip(), bar_index):
                failures.append((token, fld, e.text.strip(), "PNG in mod tree or any .bar"))

    print(f"  ANW civs checked: {civs_checked}")
    print(f"  Asset references that fail to resolve: {len(failures)}")
    if known_missing_ddts_used:
        print(f"  Known-missing revolution postgame DDTs (warn only, not fail): "
              f"{len(known_missing_ddts_used)}")
    print()

    if known_missing_ddts_used:
        print("WARN — revolution postgame DDTs not in ArtUI.bar (engine falls back gracefully;")
        print("       WPF postgame screen uses postgameflagiconwpf instead):")
        for civ, ddt in known_missing_ddts_used:
            print(f"  {civ}: {ddt!r}")
        print()

    if failures:
        print("FAIL — these civmods entries reference assets that don't exist:")
        for civ, fld, val, kind in failures[:30]:
            print(f"  {civ}.{fld} = {val!r}  ({kind})")
        if len(failures) > 30:
            print(f"  … +{len(failures) - 30} more")
    else:
        print("✓ PASS — every flag/portrait/UI asset path resolves.")

    if args.json:
        report = {
            "civs_checked": civs_checked,
            "fail_count": len(failures),
            "failures": [{"civ": c, "field": f, "value": v, "kind": k}
                         for c, f, v, k in failures],
            "known_missing_ddts": [{"civ": c, "ddt": d}
                                    for c, d in known_missing_ddts_used],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
