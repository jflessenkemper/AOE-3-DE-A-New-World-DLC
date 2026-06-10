"""validate_xs_sim_interpreter_smoke.py — XS sim interpreter smoke validator.

Checks:
  (a) All new xsVector*, kbArea*, and kbBase* builtins are registered in BUILTINS.
  (b) Wall-strategy code (anwDetectChokepointVector, anwDetectCoastVector) executes
      with a canned GameState containing an area graph and base, without an
      unhandled exception.
  (c) anwDetectChokepointVector returns a non-fallback vector on a chokepoint map.

Usage (from repo root):
    python tools/validation/validate_xs_sim_interpreter_smoke.py

Exit codes:
    0  All checks pass.
    1  One or more checks failed (message printed to stdout).
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from pathlib import Path

from tools.xs_sim.builtins import BUILTINS
from tools.xs_sim.interpreter import Interpreter
from tools.xs_sim.gamestate import (
    scenario_chokepoint_area_graph,
    scenario_coastal_area_graph,
)

WALLS_XS = Path(REPO_ROOT) / "game" / "ai" / "core" / "aiBuildingsWalls.xs"
INVALID_VEC = (-1.0, -1.0, -1.0)

# ---- (a) Registry check ------------------------------------------------

REQUIRED_BUILTINS = [
    # P0: xsVector* stdlib
    "xsVectorGetX", "xsVectorGetY", "xsVectorGetZ",
    "xsVectorSet", "xsVectorSetX", "xsVectorSetZ",
    "xsVectorNormalize", "xsVectorLength",
    # P2: kbArea* mocks
    "kbAreaGetIDByPosition", "kbAreaGetType", "kbAreaGetCenter",
    "kbAreaGetNumberTiles", "kbAreaGetNumberBorderAreas", "kbAreaGetBorderAreaID",
    # P3: kbBase* mocks
    "kbBaseGetMainID", "kbBaseGetLocation", "kbBaseGetFrontVector",
]


def check_registry() -> list[str]:
    """Return list of failure messages, empty if all pass."""
    failures = []
    for name in REQUIRED_BUILTINS:
        if name not in BUILTINS:
            failures.append(f"  MISSING builtin: {name!r} not in BUILTINS")
    return failures


# ---- (b)+(c) Execution check -------------------------------------------

def _make_interpreter(gs):
    interp = Interpreter(
        gs=gs,
        search_paths=[Path(REPO_ROOT) / "game" / "ai" / "core"],
    )
    interp.load_file(WALLS_XS)
    # Provide required wall-strategy globals
    interp.globals["gANWWallStrategy"] = 0
    interp.globals["gANWWallLevel"] = 2
    interp.globals["gANWWallTriggerAge"] = 2
    interp.globals["gANWEarlyWallingEnabled"] = True
    interp.globals["gANWLateWallingEnabled"] = True
    interp.globals["cvOkToBuildWalls"] = True
    interp.globals["gIslandMap"] = False
    return interp


def check_chokepoint_execution() -> list[str]:
    """Return failure messages from chokepoint detection run."""
    failures = []
    gs = scenario_chokepoint_area_graph()
    try:
        interp = _make_interpreter(gs)
        result = interp._call_user(
            interp.functions["anwDetectChokepointVector"],
            [1, (100.0, 0.0, 100.0)],
        )
    except Exception as e:
        failures.append(f"  EXCEPTION in anwDetectChokepointVector: {e}")
        return failures

    if result is None or result == INVALID_VEC:
        failures.append(
            f"  anwDetectChokepointVector returned fallback/None ({result!r}); "
            "expected a real vector on chokepoint map"
        )
    return failures


def check_coast_execution() -> list[str]:
    """Return failure messages from coast detection run."""
    failures = []
    gs = scenario_coastal_area_graph()
    try:
        interp = _make_interpreter(gs)
        result = interp._call_user(
            interp.functions["anwDetectCoastVector"],
            [1, (100.0, 0.0, 100.0)],
        )
    except Exception as e:
        failures.append(f"  EXCEPTION in anwDetectCoastVector: {e}")
        return failures

    if result is None or result == INVALID_VEC:
        failures.append(
            f"  anwDetectCoastVector returned fallback/None ({result!r}); "
            "expected a real vector on coastal map"
        )
    return failures


# ---- main --------------------------------------------------------------

def main() -> int:
    all_failures: list[str] = []

    print("(a) Checking builtin registry...")
    reg_failures = check_registry()
    if reg_failures:
        all_failures.extend(reg_failures)
        print(f"  FAIL  {len(reg_failures)} missing builtin(s)")
    else:
        count = len(REQUIRED_BUILTINS)
        print(f"  PASS  all {count} required builtins registered")

    print("(b) Checking anwDetectChokepointVector execution (no exception, non-fallback)...")
    cp_failures = check_chokepoint_execution()
    if cp_failures:
        all_failures.extend(cp_failures)
        print(f"  FAIL  {len(cp_failures)} issue(s)")
    else:
        print("  PASS  chokepoint detection ran and returned non-fallback vector")

    print("(c) Checking anwDetectCoastVector execution (no exception, non-fallback)...")
    coast_failures = check_coast_execution()
    if coast_failures:
        all_failures.extend(coast_failures)
        print(f"  FAIL  {len(coast_failures)} issue(s)")
    else:
        print("  PASS  coast detection ran and returned non-fallback vector")

    if all_failures:
        print(f"\nFAILED — {len(all_failures)} issue(s):")
        for msg in all_failures:
            print(msg)
        return 1

    print("\nPASS  validate_xs_sim_interpreter_smoke — all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
