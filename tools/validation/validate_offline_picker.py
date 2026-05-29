#!/usr/bin/env python3
"""Offline picker validator — predicts what the live skirmish picker will show
WITHOUT launching the game.

Bug class this catches (hit on 2026-05-09): static gate was 100% PASS, mod
was loaded, install dir matched dev tree byte-for-byte — yet the live
picker showed only base-game civs. Root cause: civmods.xml used
``<Civ>`` (capital) while base civs.xml uses ``<civ>`` (lowercase). The
engine's case-sensitive XML merge silently dropped all 46 ANW entries.

This validator reverse-engineers the engine's merge + picker enumeration
and runs it locally. Cuts the picker-validation loop from ~5 min (launch
+ navigate + screenshot + OCR) to ~5 sec (parse XML + simulate).

Verdict:
  PASS — case-sensitive merge produces the expected 46 ANW civs in picker.
  FAIL — some/all ANW civs missing; report exactly which and why.

Usage::

    python3 tools/validation/validate_offline_picker.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))
from tools.cardextract.offline_engine_sim import (  # noqa: E402
    diagnose_merge_gap, load_base_civs, load_civmods, merge, simulate_picker,
)
from tools.migration.anw_mapping import (  # noqa: E402
    ANW_NON_PICKER_TOKENS, engine_token_for,
)
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    print("=" * 60)
    print("OFFLINE PICKER VALIDATION")
    print("=" * 60)

    base = load_base_civs()
    mods = load_civmods()
    diag = diagnose_merge_gap(base, mods)

    # Pretend we're the engine — case-sensitive merge.
    sens = merge(base, mods, case="sensitive")
    picker = simulate_picker(sens)

    # Picker-pickable subset: exclude revolution-mechanic-only variants that
    # are intentionally NOT registered in civmods.xml. See ANW_NON_PICKER_TOKENS
    # docstring in tools/migration/anw_mapping.py.
    #
    # The engine registry (civmods.xml `<name>`) uses base-game tokens for 22
    # legacy civs (XPAztec, British, DEAmericans, …) while the canonical ANW
    # namespace renames them (ANWAztecs, ANWBritish, ANWUSA). Translate via
    # `engine_token_for()` before checking picker visibility.
    expected_anw = set(ANW_CIVS.keys()) - ANW_NON_PICKER_TOKENS
    expected_engine_tokens = {engine_token_for(t) for t in expected_anw}
    visible_engine = {c.name for c in picker if c.name in expected_engine_tokens}
    # Map back to canonical for the missing-list (sorts more naturally).
    visible_anw_canonical = {
        t for t in expected_anw if engine_token_for(t) in visible_engine
    }
    missing_anw = sorted(expected_anw - visible_anw_canonical)
    visible_anw = visible_anw_canonical
    expected_total = len(expected_anw)

    print(f"  Base civs in picker:        {sum(1 for c in picker if c.name not in expected_engine_tokens):>3}")
    print(f"  ANW civs in picker:         {len(visible_anw):>3} / {expected_total}")
    print(f"  Deferred (non-picker):      {len(ANW_NON_PICKER_TOKENS):>3} ({sorted(ANW_NON_PICKER_TOKENS)})")
    print(f"  Total picker civs:          {len(picker):>3}")
    print()
    print(f"  Civmods <Civ>/<civ> tag:    {diag['mod_root_tags']}")
    print(f"  Base civs.xml tag:          {diag['base_root_tags']}")
    print()

    fail_count = len(missing_anw)
    if fail_count:
        print(f"✗ FAIL — {fail_count}/{expected_total} ANW civs not in picker (engine merge "
              f"won't see them):")
        for token in missing_anw[:15]:
            print(f"    {token}")
        if len(missing_anw) > 15:
            print(f"    … +{len(missing_anw) - 15} more")
        print()
        if diag["mod_root_tags"] != diag["base_root_tags"]:
            print(f"  Likely cause: tag-case mismatch "
                  f"({diag['mod_root_tags']} vs {diag['base_root_tags']}). "
                  f"Run lowercase rewrite.")
    else:
        print(f"✓ PASS — all {expected_total} ANW civs predicted to render in the picker.")
        print()
        print(f"  Sample (first 10): {[c.name for c in picker[:10]]}")
        print(f"  Sample ANW civs visible: "
              f"{sorted(visible_anw)[:6]} …")

    if args.json:
        import json
        report = {
            "verdict": "fail" if fail_count else "pass",
            "expected_anw": expected_total,
            "visible_anw_count": len(visible_anw),
            "missing_anw": missing_anw,
            "deferred_non_picker": sorted(ANW_NON_PICKER_TOKENS),
            "total_picker_civs": len(picker),
            **diag,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2))
        print(f"  Report: {args.json}")

    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
