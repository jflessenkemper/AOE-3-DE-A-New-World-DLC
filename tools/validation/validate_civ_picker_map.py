#!/usr/bin/env python3
"""Static validator for tools/aoe3_automation/anw_civ_picker_map.py.

Assertions (all three must pass for exit 0):

  (a) COVERAGE — every ANW civ token that appears in data/civmods.xml with
      <main>1</main> also has an entry in ANW_TO_PICKER_INDEX.  Missing
      entries mean the analytical fallback for lobby_driver (and any code
      that uses keyboard Up/Down picker navigation) would silently skip or
      mis-select those civs.

  (b) NO DUPLICATE INDICES — no two different civ tokens map to the same
      picker index.  Duplicate indices cause one civ to be unselectable via
      the integer-index code path, and mis-selection warnings are silent.

  (c) VALID RANGE — every index is an integer >= 0 and <= MAX_PICKER_INDEX
      (currently 60, generous ceiling for the live picker which has ~50
      entries including base-game civs).  An out-of-range index causes
      keyboard navigation to overshoot the list and land on a random civ.

Usage::

    python3 tools/validation/validate_civ_picker_map.py
    python3 -m tools.validation.validate_civ_picker_map

Exit codes:
    0 — all assertions pass (GREEN)
    1 — one or more assertions fail (RED — details are printed)
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CIVMODS_XML = REPO / "data" / "civmods.xml"
PICKER_MAP_PY = REPO / "tools" / "aoe3_automation" / "anw_civ_picker_map.py"

# Generous upper bound for the live picker index.  The live picker (as of
# 2026-05-17) has ~50 entries.  We use 60 to leave headroom for future civs
# without needing to update this validator.
MAX_PICKER_INDEX: int = 60

# Minimum valid index.  Index 0 is "Random Personality"; index 1 is
# "American Republic" (base game).  All ANW civs occupy indices >= 2.
MIN_PICKER_INDEX: int = 2


# ---------------------------------------------------------------------------
# Step 1 — collect canonical ANW tokens from civmods.xml (<main>1</main>)
# ---------------------------------------------------------------------------

def _load_canonical_tokens() -> list[str]:
    """Return all ANW civ tokens from civmods.xml where <main>1</main>."""
    tree = ET.parse(CIVMODS_XML)
    root = tree.getroot()
    tokens: list[str] = []
    for civ in root.findall("civ"):
        main_tag = civ.find("main")
        if main_tag is not None and main_tag.text == "1":
            name_tag = civ.find("name")
            if name_tag is not None and name_tag.text:
                tokens.append(name_tag.text.strip())
    return sorted(tokens)


# ---------------------------------------------------------------------------
# Step 2 — load ANW_TO_PICKER_INDEX from the map module
# ---------------------------------------------------------------------------

def _load_picker_map() -> dict[str, int]:
    """Import ANW_TO_PICKER_INDEX from anw_civ_picker_map.py."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "anw_civ_picker_map", PICKER_MAP_PY
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec from {PICKER_MAP_PY}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return dict(mod.ANW_TO_PICKER_INDEX)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_coverage(
    canonical: list[str], picker_map: dict[str, int]
) -> list[str]:
    """Return list of canonical tokens missing from the picker map."""
    return [t for t in canonical if t not in picker_map]


def check_no_duplicate_indices(
    picker_map: dict[str, int]
) -> dict[int, list[str]]:
    """Return {index: [token, token, ...]} for any index that appears > once."""
    index_to_tokens: dict[int, list[str]] = {}
    for token, idx in picker_map.items():
        index_to_tokens.setdefault(idx, []).append(token)
    return {idx: tokens for idx, tokens in index_to_tokens.items()
            if len(tokens) > 1}


def check_valid_range(
    picker_map: dict[str, int]
) -> list[tuple[str, int]]:
    """Return [(token, index), ...] for out-of-range entries."""
    return [
        (token, idx)
        for token, idx in picker_map.items()
        if not (MIN_PICKER_INDEX <= idx <= MAX_PICKER_INDEX)
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("ANW civ picker-map validation")
    print(f"  picker map : {PICKER_MAP_PY.relative_to(REPO)}")
    print(f"  civmods    : {CIVMODS_XML.relative_to(REPO)}")
    print()

    try:
        canonical = _load_canonical_tokens()
    except ET.ParseError as exc:
        print(f"FAIL — could not parse civmods.xml: {exc}")
        return 1

    try:
        picker_map = _load_picker_map()
    except Exception as exc:
        print(f"FAIL — could not load anw_civ_picker_map.py: {exc}")
        return 1

    print(f"  canonical ANW tokens (civmods.xml <main>1>) : {len(canonical)}")
    print(f"  picker map entries                           : {len(picker_map)}")
    print()

    fail = False

    # (a) Coverage
    missing = check_coverage(canonical, picker_map)
    if missing:
        fail = True
        print(f"FAIL (a) COVERAGE — {len(missing)} canonical token(s) missing "
              f"from ANW_TO_PICKER_INDEX:")
        for tok in missing:
            print(f"    {tok}")
        print()
    else:
        print(f"PASS (a) coverage — all {len(canonical)} canonical tokens present")

    # (b) No duplicates
    dupes = check_no_duplicate_indices(picker_map)
    if dupes:
        fail = True
        print(f"FAIL (b) DUPLICATE INDICES — {len(dupes)} index/indices shared "
              f"by multiple tokens:")
        for idx, tokens in sorted(dupes.items()):
            print(f"    index {idx}: {', '.join(sorted(tokens))}")
        print()
    else:
        print("PASS (b) no duplicate indices")

    # (c) Valid range
    out_of_range = check_valid_range(picker_map)
    if out_of_range:
        fail = True
        print(f"FAIL (c) VALID RANGE — {len(out_of_range)} entry/entries outside "
              f"[{MIN_PICKER_INDEX}, {MAX_PICKER_INDEX}]:")
        for token, idx in sorted(out_of_range, key=lambda x: x[1]):
            print(f"    {token}: index {idx}")
        print()
    else:
        print(f"PASS (c) all indices in valid range [{MIN_PICKER_INDEX}, {MAX_PICKER_INDEX}]")

    print()
    if fail:
        print("RESULT: FAIL — fix the issues above in "
              "tools/aoe3_automation/anw_civ_picker_map.py")
        return 1

    print("RESULT: PASS — all checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
