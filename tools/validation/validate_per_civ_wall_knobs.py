#!/usr/bin/env python3
"""Validator: exercise llSetWallKnobsForCiv() for all 40 civs and cross-check
against the CALIBRATION source-of-truth in wall_knob_calibration.py.

Usage:
    python3 -m tools.validation.validate_per_civ_wall_knobs
    python3 -m tools.validation.validate_per_civ_wall_knobs --json artifacts/validation/per_civ_wall_knobs.json

Exit codes:
    0 — all 40 civs PASS
    1 — one or more civs FAIL
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — allow running as a module from repo root.
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# ---------------------------------------------------------------------------
# Import calibration table.
# ---------------------------------------------------------------------------
try:
    from tools.ai_design.wall_knob_calibration import CALIBRATION  # type: ignore
except ImportError:
    # Fallback: parse the source with ast (should not be needed, but kept for
    # robustness if the package layout changes).
    import ast as _ast
    _src = (REPO / "tools" / "ai_design" / "wall_knob_calibration.py").read_text()
    _tree = _ast.parse(_src)
    # Execute just the CALIBRATION assignment in a sandbox namespace.
    _ns: dict = {}
    exec(compile(_tree, "wall_knob_calibration.py", "exec"), _ns)
    CALIBRATION = _ns["CALIBRATION"]

# ---------------------------------------------------------------------------
# XS simulator imports.
# ---------------------------------------------------------------------------
from tools.xs_sim.interpreter import Interpreter  # type: ignore
from tools.xs_sim.gamestate import GameState       # type: ignore

# ---------------------------------------------------------------------------
# The 15 wall-knob global names we read back after dispatch.
# (14 knobs in the calibration table + gLLWallNoWaterBuild = 15 globals total)
# ---------------------------------------------------------------------------
WALL_GLOBALS = [
    "gLLWallStrategy",
    "gLLWallRadius",
    "gLLWallGateCount",
    "gLLWallTierAge2Stone",
    "gLLWallTriggerAge",
    "gLLWallSegmentLength",
    "gLLWallTowerInterleave",
    "gLLWallSecondaryStrategy",
    "gLLWallVillagerCount",
    "gLLWallForwardBiasFraction",
    "gLLWallOuterRingDelta",
    "gLLWallEarlyOutpostCount",
    "gLLWallRepairAggressiveness",
    "gLLWallClosurePctTarget",
    "gLLWallNoWaterBuild",
]

# Default values mirroring aiHeader.xs declarations (for pre-seeding the
# interpreter so we can run without loading the full aiHeader.xs).
WALL_DEFAULTS: dict[str, Any] = {
    "gLLWallStrategy":             0,
    "gLLWallRadius":               18,
    "gLLWallGateCount":            3,
    "gLLWallTierAge2Stone":        False,
    "gLLWallTriggerAge":           2,
    "gLLWallSegmentLength":        12,
    "gLLWallTowerInterleave":      6,
    "gLLWallSecondaryStrategy":    -1,
    "gLLWallVillagerCount":        4,
    "gLLWallForwardBiasFraction":  0.5,
    "gLLWallOuterRingDelta":       0,
    "gLLWallEarlyOutpostCount":    1,
    "gLLWallRepairAggressiveness": 1,
    "gLLWallClosurePctTarget":     60,
    "gLLWallNoWaterBuild":         True,
}

# Mapping from calibration dict key → expected value (normalised).
# The calibration stores age2stone and no_water as 0/1 ints; XS uses bool.
CALIB_KEY_MAP = {
    "strategy":    "gLLWallStrategy",
    "radius":      "gLLWallRadius",
    "gates":       "gLLWallGateCount",
    "age2stone":   "gLLWallTierAge2Stone",
    "trigger_age": "gLLWallTriggerAge",
    "seg_len":     "gLLWallSegmentLength",
    "towers":      "gLLWallTowerInterleave",
    "secondary":   "gLLWallSecondaryStrategy",
    "vils":        "gLLWallVillagerCount",
    "fwd_bias":    "gLLWallForwardBiasFraction",
    "outer_ring":  "gLLWallOuterRingDelta",
    "outposts":    "gLLWallEarlyOutpostCount",
    "repair":      "gLLWallRepairAggressiveness",
    "closure_pct": "gLLWallClosurePctTarget",
    "no_water":    "gLLWallNoWaterBuild",
}

DISPATCH_XS = REPO / "game" / "ai" / "core" / "aiWallKnobsByCiv.xs"


def _normalise_calib(kn: dict) -> dict[str, Any]:
    """Convert a CALIBRATION row to the global-name-keyed dict of expected values,
    normalising bool fields (age2stone, no_water stored as 0/1 ints in py)."""
    out: dict[str, Any] = {}
    for calib_key, global_name in CALIB_KEY_MAP.items():
        val = kn[calib_key]
        # Bool globals — calibration stores 0/1
        if global_name in ("gLLWallTierAge2Stone", "gLLWallNoWaterBuild"):
            val = bool(val)
        out[global_name] = val
    return out


def _close_enough(a: Any, b: Any) -> bool:
    """Compare two values; allow float rounding within 1e-9."""
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) < 1e-9
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    return a == b


def run_civ(civ_token: str, engine_key: str) -> tuple[bool, dict[str, Any]]:
    """Run the dispatch for one civ. Returns (passed, detail_dict)."""
    # Fresh interpreter per civ so globals don't bleed across runs.
    gs = GameState(civ_name=engine_key)
    interp = Interpreter(gs=gs)

    # Pre-seed the wall-knob globals with their aiHeader.xs defaults so the
    # XS dispatch can overwrite them without needing to load the full header.
    for name, default in WALL_DEFAULTS.items():
        interp.globals[name] = default

    # cMyCiv is referenced in the dispatch: `kbGetCivName(cMyCiv)`.
    # The interpreter treats unknown c-prefixed names as 0 (int). The builtin
    # kbGetCivName() ignores its argument and returns gs.civ_name, so we only
    # need gs.civ_name set correctly (done above).
    interp.globals["cMyCiv"] = 0

    # Load the dispatch XS — only this file; no full aiHeader needed.
    interp.load_file(DISPATCH_XS)

    # Call the dispatch function.
    if "llSetWallKnobsForCiv" not in interp.functions:
        return False, {"error": "function llSetWallKnobsForCiv not found in XS"}

    interp.call_init("llSetWallKnobsForCiv")

    # Read back all 15 globals.
    actual: dict[str, Any] = {g: interp.globals.get(g) for g in WALL_GLOBALS}
    return actual, interp


def validate_all(verbose: bool = False) -> tuple[list[dict], bool]:
    """Run all 40 civs. Returns (results, all_passed)."""
    results = []
    all_passed = True

    for civ_token, kn in CALIBRATION.items():
        # Engine key: base civs use civ_token directly; revolution civs use
        # rev_token (that's what kbGetCivName returns for them).
        rev_token = kn.get("rev_token")
        engine_key = rev_token if rev_token is not None else civ_token

        expected = _normalise_calib(kn)
        actual, interp = run_civ(civ_token, engine_key)

        if isinstance(actual, dict) and "error" in actual:
            result = {
                "civ": civ_token,
                "engine_key": engine_key,
                "status": "FAIL",
                "error": actual["error"],
                "mismatches": [],
            }
            all_passed = False
            results.append(result)
            continue

        mismatches = []
        for global_name, exp_val in expected.items():
            act_val = actual.get(global_name)
            if not _close_enough(act_val, exp_val):
                mismatches.append({
                    "global": global_name,
                    "expected": exp_val,
                    "actual": act_val,
                })

        passed = len(mismatches) == 0
        if not passed:
            all_passed = False

        result = {
            "civ": civ_token,
            "engine_key": engine_key,
            "strategy": kn["strategy"],
            "status": "PASS" if passed else "FAIL",
            "mismatches": mismatches,
        }
        if verbose and mismatches:
            result["actual"] = actual
            result["expected"] = expected

        results.append(result)

    return results, all_passed


def print_summary(results: list[dict]) -> None:
    STRATEGY_LABELS = {
        0: "FortressRing",
        1: "Choke",
        2: "Coastal",
        3: "Frontier",
        4: "Urban",
        5: "Mobile",
    }

    print()
    print(f"{'Civ':<25} {'EngineKey':<25} {'Strategy':<16} {'Status'}")
    print("-" * 80)

    fail_count = 0
    for r in results:
        strategy_label = STRATEGY_LABELS.get(r.get("strategy", -1), "?")
        status = r["status"]
        if status == "FAIL":
            fail_count += 1
        marker = "  " if status == "PASS" else "* "
        print(f"{marker}{r['civ']:<23} {r['engine_key']:<25} {strategy_label:<16} {status}")
        for mm in r.get("mismatches", []):
            print(f"    MISMATCH {mm['global']}: expected={mm['expected']!r} actual={mm['actual']!r}")

    print("-" * 80)
    total = len(results)
    passed = total - fail_count
    print(f"\nResult: {passed}/{total} civs PASS")

    # Distribution by strategy.
    print()
    by_strategy: dict[int, list[str]] = {}
    for r in results:
        s = r.get("strategy", -1)
        by_strategy.setdefault(s, []).append(r["civ"])
    print("Distribution by strategy:")
    for s in sorted(by_strategy):
        label = STRATEGY_LABELS.get(s, "Unknown")
        count = len(by_strategy[s])
        print(f"  strategy {s} {label:<16} {count:2d} civs")

    if fail_count > 0:
        print(f"\nFAILED: {fail_count} civ(s) did not match calibration (marked with *)")
    else:
        print("\nAll civs matched calibration. PASS.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate llSetWallKnobsForCiv() against wall_knob_calibration.py for all 40 civs."
    )
    ap.add_argument(
        "--json",
        metavar="PATH",
        help="Write machine-readable results to this JSON file (e.g. artifacts/validation/per_civ_wall_knobs.json)",
    )
    ap.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="On failure, show full actual/expected dicts",
    )
    args = ap.parse_args(argv)

    print(f"Loading dispatch from: {DISPATCH_XS.relative_to(REPO)}")
    print(f"Calibration civs: {len(CALIBRATION)}")

    results, all_passed = validate_all(verbose=args.verbose)

    print_summary(results)

    if args.json:
        out_path = Path(args.json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "PASS"),
            "failed": sum(1 for r in results if r["status"] == "FAIL"),
            "all_passed": all_passed,
            "results": results,
        }
        out_path.write_text(json.dumps(payload, indent=2, default=str))
        print(f"\nJSON written to: {out_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
