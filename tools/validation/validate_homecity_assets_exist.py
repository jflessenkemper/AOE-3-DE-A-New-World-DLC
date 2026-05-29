#!/usr/bin/env python3
"""Verify every ANW homecity's visual/pathdata/camera/sound asset exists.

Complements ``validate_homecity_visuals.py`` (which checks
namespace-coherence to prevent the "floating citizens" bug). This one
checks that the referenced assets actually exist in the base game's
``.bar`` archives — guarding against typos and broken refs.

Each ``data/anwhomecity*.xml`` references base-game art:
  - ``<visual>X\\X_homecity.xml</visual>``           — building scene
  - ``<watervisual>X\\X_homecity_water.xml</watervisual>``
  - ``<backgroundvisual>X\\X_background.xml</backgroundvisual>``
  - ``<pathdata>X\\pathable_area*.gr2</pathdata>``    — NPC walk paths
  - ``<camera>X\\X_homecity_camera.cam</camera>``
  - ``<widescreencamera>...</widescreencamera>``
  - ``<ambientsounds>homecity\\Xambientsounds.xml</ambientsounds>``

Missing references = empty void / fallback rendering / sound failure
in the home city scene.

Usage::

    python3 tools/validation/validate_homecity_assets_exist.py
    python3 tools/validation/validate_homecity_assets_exist.py --rebuild-cache
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
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402


_BAR_INDEX_CACHE = REPO_ROOT / "artifacts" / "extracted_bar_index.json"
_AOE3_ART = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game"
)


_VISUAL_FIELDS = (
    "visual", "watervisual", "backgroundvisual",
    "pathdata", "camera", "widescreencamera",
    "ambientsounds",
)


def _build_asset_index() -> set[str]:
    """Lower-cased, slash-normalized set of every asset name across all .bar."""
    if _BAR_INDEX_CACHE.exists():
        return set(json.loads(_BAR_INDEX_CACHE.read_text()))
    sys.path.insert(0, str(REPO_ROOT))
    from tools.cardextract.bar import open_bar
    names: set[str] = set()
    for bar in _AOE3_ART.rglob("*.bar"):
        try:
            arc = open_bar(bar)
            for h in arc.find(lambda e: True):
                names.add(h.normalized_name)
        except Exception:
            continue
    _BAR_INDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _BAR_INDEX_CACHE.write_text(json.dumps(sorted(names), indent=0))
    return names


def _norm(p: str) -> str:
    return p.replace("\\", "/").lower()


def _asset_exists(ref: str, idx: set[str], suffixes: tuple[str, ...]) -> bool:
    """Engine appends a suffix and may prepend a folder.

    AoE3 DE home city visuals live at ``homecity\\<civ>\\…`` inside
    ``ArtHomecity.bar`` / ``ArtBuildings.bar`` / ``Sound.bar``. Our
    XML refs typically omit the ``homecity\\`` prefix (engine adds it),
    so we try common prefix variants.
    """
    if not ref:
        return True
    base = _norm(ref)
    prefix_variants = ("", "homecity/", "buildings/", "homecity/" + base.split('/')[0] + "/")
    for prefix in prefix_variants:
        for suffix in suffixes:
            candidate = f"{prefix}{base}{suffix}".lower()
            if candidate in idx:
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--rebuild-cache", action="store_true")
    args = ap.parse_args()

    if args.rebuild_cache and _BAR_INDEX_CACHE.exists():
        _BAR_INDEX_CACHE.unlink()

    print("=" * 60)
    print("HOMECITY VISUAL ASSET EXISTENCE")
    print("=" * 60)

    idx = _build_asset_index()
    print(f"  Indexed {len(idx):,} assets from base .bar archives")

    # XML refs already include .xml extension; engine looks up .xml.XMB on disk.
    # So suffixes append .xmb to existing .xml. Also try no-suffix and .xmb alone
    # for edge cases (e.g., .gr2 paths shouldn't get suffix).
    field_suffixes = {
        "visual":            ("", ".xmb"),
        "watervisual":       ("", ".xmb"),
        "backgroundvisual":  ("", ".xmb"),
        "pathdata":          ("", ".precomp"),
        "camera":            ("", ".xmb"),
        "widescreencamera":  ("", ".xmb"),
        "ambientsounds":     ("", ".xmb"),
    }

    failures: list[tuple[str, str, str]] = []
    civs_checked = 0
    for token, info in ANW_CIVS.items():
        stem = info.get("file_stem") or (
            token[3:].lower() if token.startswith("ANW") else token.lower()
        )
        p = REPO_ROOT / "data" / f"anwhomecity{stem}.xml"
        if not p.exists():
            failures.append((token, "(homecity-file)", f"missing: {p.name}"))
            continue
        civs_checked += 1
        try:
            root = ET.parse(p).getroot()
        except Exception as e:
            failures.append((token, "(parse)", f"{e}"))
            continue
        for fld in _VISUAL_FIELDS:
            e = root.find(fld)
            if e is None:
                continue
            v = (e.text or "").strip()
            if not v:
                continue
            if not _asset_exists(v, idx, field_suffixes[fld]):
                failures.append((token, fld, v))

    print(f"  ANW civs checked: {civs_checked}")
    print(f"  Asset references that fail to resolve: {len(failures)}")
    print()

    if failures:
        print("FAIL — these references don't resolve in any base .bar archive:")
        for civ, fld, val in failures[:30]:
            print(f"  {civ}.{fld} = {val!r}")
        if len(failures) > 30:
            print(f"  … +{len(failures) - 30} more")
    else:
        print("✓ PASS — every homecity asset reference resolves.")

    if args.json:
        report = {
            "civs_checked": civs_checked,
            "fail_count": len(failures),
            "failures": [{"civ": c, "field": f, "value": v}
                         for c, f, v in failures],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
