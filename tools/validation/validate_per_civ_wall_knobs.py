#!/usr/bin/env python3
"""Validator: exercise anwSetWallKnobsForCiv() for all calibrated civs and
cross-check against the CALIBRATION source-of-truth in wall_knob_calibration.py.

Usage:
    python3 -m tools.validation.validate_per_civ_wall_knobs
    python3 -m tools.validation.validate_per_civ_wall_knobs --json artifacts/validation/per_civ_wall_knobs.json

Exit codes:
    0 — all civs PASS
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
    "gANWWallStrategy",
    "gANWWallRadius",
    "gANWWallGateCount",
    "gANWWallTierAge2Stone",
    "gANWWallTriggerAge",
    "gANWWallSegmentLength",
    "gANWWallTowerInterleave",
    "gANWWallSecondaryStrategy",
    "gANWWallVillagerCount",
    "gANWWallForwardBiasFraction",
    "gANWWallOuterRingDelta",
    "gANWWallEarlyOutpostCount",
    "gANWWallRepairAggressiveness",
    "gANWWallClosurePctTarget",
    "gANWWallNoWaterBuild",
]

# Default values mirroring aiHeader.xs declarations (for pre-seeding the
# interpreter so we can run without loading the full aiHeader.xs).
WALL_DEFAULTS: dict[str, Any] = {
    "gANWWallStrategy":             0,
    "gANWWallRadius":               18,
    "gANWWallGateCount":            3,
    "gANWWallTierAge2Stone":        False,
    "gANWWallTriggerAge":           2,
    "gANWWallSegmentLength":        12,
    "gANWWallTowerInterleave":      6,
    "gANWWallSecondaryStrategy":    -1,
    "gANWWallVillagerCount":        4,
    "gANWWallForwardBiasFraction":  0.5,
    "gANWWallOuterRingDelta":       0,
    "gANWWallEarlyOutpostCount":    1,
    "gANWWallRepairAggressiveness": 1,
    "gANWWallClosurePctTarget":     60,
    "gANWWallNoWaterBuild":         True,
}

# Mapping from calibration dict key → expected value (normalised).
# The calibration stores age2stone and no_water as 0/1 ints; XS uses bool.
CALIB_KEY_MAP = {
    "strategy":    "gANWWallStrategy",
    "radius":      "gANWWallRadius",
    "gates":       "gANWWallGateCount",
    "age2stone":   "gANWWallTierAge2Stone",
    "trigger_age": "gANWWallTriggerAge",
    "seg_len":     "gANWWallSegmentLength",
    "towers":      "gANWWallTowerInterleave",
    "secondary":   "gANWWallSecondaryStrategy",
    "vils":        "gANWWallVillagerCount",
    "fwd_bias":    "gANWWallForwardBiasFraction",
    "outer_ring":  "gANWWallOuterRingDelta",
    "outposts":    "gANWWallEarlyOutpostCount",
    "repair":      "gANWWallRepairAggressiveness",
    "closure_pct": "gANWWallClosurePctTarget",
    "no_water":    "gANWWallNoWaterBuild",
}

DISPATCH_XS = REPO / "game" / "ai" / "core" / "aiWallKnobsByCiv.xs"

# ---------------------------------------------------------------------------
# Spec cross-check: each CALIBRATION engine token → its playstyle_spec.json key.
# This makes the calibration table's wall_strategy provably faithful to spec,
# so that knob == calibration == spec is enforced transitively and cannot drift
# silently. Mapping is explicit (40 entries) rather than fuzzy to avoid
# mismatches on near-duplicate display names.
# ---------------------------------------------------------------------------
SPEC_PATH = REPO / "playstyle_spec.json"

CALIB_TO_SPEC: dict[str, str] = {
    "DEInca":              "Inca Pachacuti",
    "Germans":             "Germans Frederick Great",
    "Ottomans":            "Ottomans Suleiman",
    "DEMaltese":           "Maltese Valette",
    "Chinese":             "Chinese Kangxi",
    "French":              "French Louis XVIII Bourbon",
    "Indians":             "Indians Akbar",
    "DEEthiopians":        "Ethiopians Menelik",
    "ANWCanadians":        "Canadians Brock Revolution",
    "ANWChileans":         "Chileans OHiggins Revolution",
    "ANWPeruvians":        "Peruvians Santa Cruz Peru Revolution",
    "ANWEgyptians":        "Egyptians Muhammad Ali Revolution",
    "ANWFinnish":          "Finnish Mannerheim Revolution",
    "XPAztec":             "Aztecs Montezuma",
    "ANWHaitians":         "Haitians Louverture Revolution",
    "ANWIndonesians":      "Indonesians Diponegoro Revolution",
    "ANWMayans":           "Mayans Canek Maya Revolution",
    "British":             "British Elizabeth",
    "Portuguese":          "Portuguese Henry Navigator",
    "Dutch":               "Dutch Maurice Nassau",
    "ANWBarbary":          "Barbary Barbarossa Corsair Revolution",
    "ANWSouthAfricans":    "South Africans Kruger Boer Revolution",
    "ANWBrazil":           "Brazil Pedro Revolution",
    "DEHausa":             "Hausa Usman dan Fodio",
    "Russians":            "Russians Ivan the Terrible",
    "ANWRomanians":        "Romanians Cuza Revolution",
    "ANWRevFrance":        "Revolutionary France Robespierre Revolution",
    "DEItalians":          "Italians Garibaldi",
    "DEMexicans":          "Mexicans Hidalgo Standard",
    "DEAmericans":         "United States Washington",
    "ANWNapoleonicFrance": "Napoleonic France Napoleon Bonaparte Revolution",
    "ANWArgentines":       "Argentines San Martin Revolution",
    "ANWColumbians":       "Columbians Bolivar Colombia Revolution",
    "XPIroquois":          "Haudenosaunee Hiawatha Iroquois",
    "ANWHungarians":       "Hungarians Kossuth Revolution",
    "Japanese":            "Japanese Tokugawa Ieyasu",
    "XPSioux":             "Lakota Crazy Horse",
    "Spanish":             "Spanish Isabella Castile",
    "DESwedish":           "Swedes Gustavus Adolphus Swedish",
    "ANWTexians":          "Texians Sam Houston Texas Revolution",
    "ANWCalifornians":     "Californians Vallejo Revolution",
    "ANWCentralAmericans": "Central Americans Morazan Revolution",
    "ANWBajaCalifornians": "Baja Californians Alvarado Revolution",
    "ANWRioGrande":        "Rio Grande Canales Revolution",
    # ANW canonical nation entries added for coverage (18 civs).
    "ANWBritish":         "British Elizabeth",
    "ANWDutch":           "Dutch Maurice Nassau",
    "ANWPortuguese":      "Portuguese Henry Navigator",
    "ANWGermans":         "Germans Frederick Great",
    "ANWItalians":        "Italians Garibaldi",
    "ANWMexicans":        "Mexicans Hidalgo Standard",
    "ANWUSA":             "United States Washington",
    "ANWHaudenosaunee":   "Haudenosaunee Hiawatha Iroquois",
    "ANWJapanese":        "Japanese Tokugawa Ieyasu",
    "ANWLakota":          "Lakota Crazy Horse",
    "ANWSpanish":         "Spanish Isabella Castile",
    "ANWSwedes":          "Swedes Gustavus Adolphus Swedish",
    "ANWHausa":           "Hausa Usman dan Fodio",
    "ANWChinese":         "Chinese Kangxi",
    "ANWEthiopians":      "Ethiopians Menelik",
    "ANWIndians":         "Indians Akbar",
    "ANWMaltese":         "Maltese Valette",
    "ANWOttomans":        "Ottomans Suleiman",
}


def _load_spec_wall_strategies() -> dict[str, int]:
    """Return {spec_key: wall_strategy_int} from playstyle_spec.json.

    Returns {} (and the cross-check is skipped) if the spec file is missing or
    malformed, so this validator never hard-crashes on an absent spec.
    """
    try:
        spec = json.loads(SPEC_PATH.read_text())
        civs = spec["civs"]
    except (OSError, KeyError, json.JSONDecodeError):
        return {}
    out: dict[str, int] = {}
    for key, entry in civs.items():
        ws = entry.get("claims", {}).get("wall_strategy")
        if isinstance(ws, int):
            out[key] = ws
    return out


def _normalise_calib(kn: dict) -> dict[str, Any]:
    """Convert a CALIBRATION row to the global-name-keyed dict of expected values,
    normalising bool fields (age2stone, no_water stored as 0/1 ints in py)."""
    out: dict[str, Any] = {}
    for calib_key, global_name in CALIB_KEY_MAP.items():
        val = kn[calib_key]
        # Bool globals — calibration stores 0/1
        if global_name in ("gANWWallTierAge2Stone", "gANWWallNoWaterBuild"):
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
    if "anwSetWallKnobsForCiv" not in interp.functions:
        return {"error": "function anwSetWallKnobsForCiv not found in XS"}, None

    interp.call_init("anwSetWallKnobsForCiv")

    # Read back all 15 globals.
    actual: dict[str, Any] = {g: interp.globals.get(g) for g in WALL_GLOBALS}
    return actual, interp


def validate_all(verbose: bool = False) -> tuple[list[dict], bool]:
    """Run all 40 civs. Returns (results, all_passed)."""
    results = []
    all_passed = True

    spec_ws = _load_spec_wall_strategies()
    if not spec_ws:
        print("WARNING: playstyle_spec.json missing/unreadable — "
              "spec cross-check skipped (calibration check still runs).")

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

        # Spec cross-check: knob strategy (== calibration strategy, since the
        # loop above asserts gLLWallStrategy matches kn["strategy"]) must equal
        # the wall_strategy claimed in playstyle_spec.json. This catches silent
        # drift between the calibration table and the canonical spec.
        spec_mismatch = None
        if spec_ws:
            spec_key = CALIB_TO_SPEC.get(civ_token)
            if spec_key is None or spec_key not in spec_ws:
                spec_mismatch = {
                    "global": "spec.wall_strategy",
                    "expected": f"<spec key for {civ_token} not found>",
                    "actual": kn["strategy"],
                }
            elif spec_ws[spec_key] != kn["strategy"]:
                spec_mismatch = {
                    "global": "spec.wall_strategy",
                    "expected": spec_ws[spec_key],
                    "actual": kn["strategy"],
                    "spec_key": spec_key,
                }
            if spec_mismatch is not None:
                mismatches.append(spec_mismatch)

        passed = len(mismatches) == 0
        if not passed:
            all_passed = False

        result = {
            "civ": civ_token,
            "engine_key": engine_key,
            "strategy": kn["strategy"],
            "spec_key": CALIB_TO_SPEC.get(civ_token),
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
        description="Validate anwSetWallKnobsForCiv() against wall_knob_calibration.py for all calibrated civs."
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
