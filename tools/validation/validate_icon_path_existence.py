#!/usr/bin/env python3
"""Verify every icon/portrait/flag path in mod XMLs resolves on disk.

Walks ``data/civmods.xml`` + all ``data/anwhomecity*.xml`` files,
extracts every:

  - ``<portrait>``
  - ``<smallportraittexture>``
  - ``<smallportraittexturewpf>``
  - ``<portraittexture>``
  - ``<icon>``

…and verifies the path resolves to:

  1. A ``.png`` file in ``resources/images/`` (mod tree), OR
  2. A DDT/XML/texture in ``artifacts/extracted_bar_index.json`` (base game)

This is rank #7 in ``docs/TEST_COVERAGE_PLAN.md``.  Catches a whole
class of "broken portrait in lobby" / "blank flag in scoreboard"
bugs that previously had to be found by visual inspection.

Engine path conventions:

  - ``resources/images/icons/singleplayer/foo.png`` — literal mod file
  - ``ui\\singleplayer\\cpai_avatar_X`` — base .bar DDT (no extension)
  - ``objects\\flags\\X`` — base .bar DDT flag
  - ``ui\\home_city\\X_icon`` — base .bar DDT
  - ``homecity\\buildings_west\\X_icon`` — base .bar DDT

Strategy:

  1. Build a lowercased set of paths from extracted_bar_index.json
     (one normalisation: backslashes → slashes, drop trailing extension)
  2. For each extracted path, check (a) ``.png`` literal in mod tree
     (case-sensitive on Linux), (b) backslash → slash normalised form
     in the bar index, (c) try with `.ddt`, `.xmb`, `.png` extensions
     appended.
  3. Anything that fails → phantom asset reference.

Usage::

    python3 tools/validation/validate_icon_path_existence.py
    python3 tools/validation/validate_icon_path_existence.py \\
        --json artifacts/validation/icon_paths.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Tags that carry asset paths (lowercase).
ICON_TAGS = (
    "portrait",
    "smallportraittexture",
    "smallportraittexturewpf",
    "portraittexture",
    "icon",
    "flag",
    "tribute_flag",
)

# Build one regex like <(portrait|icon|...)>(...)</(\1)>
_TAG_PAT = re.compile(
    r"<(" + "|".join(ICON_TAGS) + r")>([^<>]+)</\1>",
    re.IGNORECASE,
)


def _normalise_path(p: str) -> str:
    """Lowercase, backslash→slash, strip extension for fuzzy compare."""
    p = p.strip().lower().replace("\\", "/")
    # Drop any extension for the canonical form (engine refs are extensionless).
    if "." in p.rsplit("/", 1)[-1]:
        p = p.rsplit(".", 1)[0]
    return p


def _load_bar_index(path: Path) -> set[str]:
    """Load extracted bar index as a set of normalised paths."""
    if not path.exists():
        return set()
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # File may be a giant flat list — try anyway
        return set()
    paths: set[str] = set()
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, str):
                paths.add(_normalise_path(entry))
    elif isinstance(data, dict):
        # Some indices map names → metadata; pull all keys + any string vals
        for k, v in data.items():
            if isinstance(k, str):
                paths.add(_normalise_path(k))
            if isinstance(v, str):
                paths.add(_normalise_path(v))
    return paths


def _extract_icon_refs(*xml_paths: Path) -> list[tuple[Path, str, str, int]]:
    """Return list of (file, tag, value, offset) for every icon-bearing element."""
    refs: list[tuple[Path, str, str, int]] = []
    for xml in xml_paths:
        if not xml.exists():
            continue
        text = xml.read_text(encoding="utf-8", errors="replace")
        for m in _TAG_PAT.finditer(text):
            tag = m.group(1).lower()
            val = m.group(2).strip()
            if not val:
                continue
            # Skip numeric-only values (locids, etc).
            if val.isdigit():
                continue
            refs.append((xml, tag, val, m.start()))
    return refs


def _has_nearby_wpf(refs_in_file: list[dict], pos: int, window: int = 600) -> bool:
    """True if a sibling ``smallportraittexturewpf`` element with a resolved
    value sits within ``window`` chars of the given ref position."""
    for sib in refs_in_file:
        if sib["tag"] == "smallportraittexturewpf" and sib["resolved"]:
            if abs(sib["offset"] - pos) <= window:
                return True
    return False


def _resolve(ref_value: str,
             bar_index: set[str],
             mod_root: Path) -> tuple[bool, str]:
    """Return (resolved?, where) for an icon reference.

    Where is one of: 'mod-tree', 'bar-index', 'mod-png-fallback',
    'missing'.
    """
    # Try the mod tree first (literal path, then with .png).
    candidate = ref_value.replace("\\", "/").lstrip("/")
    if (mod_root / candidate).exists():
        return True, "mod-tree"
    if not candidate.lower().endswith(".png"):
        if (mod_root / (candidate + ".png")).exists():
            return True, "mod-tree"
    # Otherwise normalise and check the bar index.
    norm = _normalise_path(ref_value)
    if norm in bar_index:
        return True, "bar-index"
    # Some engine refs use the "ui\\foo" form even though the DDT lives at
    # "ui/foo.ddt" in the bar index — _normalise_path already strips the
    # extension on both sides so a direct lookup should work.  If it doesn't,
    # try appending common engine suffixes.
    for suffix in ("_icon", ""):
        n2 = norm + suffix
        if n2 in bar_index:
            return True, "bar-index"
    # WPF fallback: many mod refs of form ``ui\singleplayer\cpai_avatar_X``
    # are actually served by a sibling PNG at
    # ``resources/images/icons/singleplayer/X.png`` (the
    # ``smallportraittexturewpf`` tag).  The engine resolves either path.
    # Check whether the basename exists anywhere under resources/images/.
    basename = norm.rsplit("/", 1)[-1]
    if basename:
        # Cheap scan: glob for the basename under known mod image dirs.
        for sub in ("resources/images/icons/singleplayer",
                    "resources/images/icons/cards",
                    "resources/images/icons/flags",
                    "resources/images/icons/units",
                    "resources/images/icons"):
            png = mod_root / sub / (basename + ".png")
            if png.exists():
                return True, "mod-png-fallback"
    return False, "missing"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path,
                    default=REPO_ROOT / "data")
    ap.add_argument("--bar-index", type=Path,
                    default=REPO_ROOT / "artifacts" / "extracted_bar_index.json")
    ap.add_argument("--mod-root", type=Path, default=REPO_ROOT)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("ICON / PORTRAIT / FLAG PATH EXISTENCE")
    print("=" * 60)

    bar_index = _load_bar_index(args.bar_index)
    print(f"  Bar index: {len(bar_index)} known asset paths")

    # Collect all icon-bearing XMLs.
    xml_paths = list(args.data_dir.glob("anwhomecity*.xml"))
    xml_paths.append(args.data_dir / "civmods.xml")
    print(f"  Scanning {len(xml_paths)} XML files for icon refs…")
    refs = _extract_icon_refs(*xml_paths)
    print(f"  Found {len(refs)} icon references")
    print()

    by_file: dict[str, list[dict]] = {}

    # First pass: resolve each ref individually.
    for xml, tag, val, off in refs:
        ok, where = _resolve(val, bar_index, args.mod_root)
        entry = {"tag": tag, "value": val, "resolved": ok,
                 "where": where, "offset": off}
        by_file.setdefault(xml.name, []).append(entry)

    # Second pass: rescue ``smallportraittexture`` refs that have a
    # nearby resolved ``smallportraittexturewpf`` sibling — the engine
    # uses the WPF path in DE so the texture-side ref is decorative.
    misses: list[dict] = []
    for fname, entries in by_file.items():
        for e in entries:
            if not e["resolved"] and e["tag"] == "smallportraittexture":
                if _has_nearby_wpf(entries, e["offset"]):
                    e["resolved"] = True
                    e["where"] = "wpf-sibling"
                    continue
            if not e["resolved"]:
                misses.append({"file": fname, "tag": e["tag"], "value": e["value"]})

    for fname in sorted(by_file.keys()):
        fmisses = [e for e in by_file[fname] if not e["resolved"]]
        if fmisses:
            print(f"  ✗ {fname}: {len(fmisses)} missing icon(s)")
            for m in fmisses[:5]:
                print(f"      <{m['tag']}>{m['value']}</{m['tag']}>")
            if len(fmisses) > 5:
                print(f"      ...and {len(fmisses) - 5} more")
        else:
            print(f"  ✓ {fname}: all {len(by_file[fname])} icon refs resolve")

    print()
    if misses:
        print(f"FAIL — {len(misses)} unresolved icon reference(s)")
    else:
        print("PASS — all icon/portrait/flag paths resolve")

    report = {
        "total_refs": len(refs),
        "missing": misses,
        "passed": not misses,
        "by_file": by_file,
    }

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
