#!/usr/bin/env python3
"""Static validator wrapper: xs_sim doctrine comparison vs spec claims.

Each `game/ai/leaders/leader_*.xs` is run through the Python XS interpreter
in ``tools/xs_sim/``. The simulator boots the leader, runs ~180 simulated
seconds of rule ticks, and reads the doctrine globals the XS sets
(``gLLWallStrategy``, ``gLLMilitaryDistanceMultiplier``, ``cvOkToBuildForts``,
``btOffenseDefense``, …). Those observed values are then compared to the
``claims`` block for the matching civ in ``playstyle_spec.json``.

Compared to ``validate_ai_behaviour_map.py`` (which is a *grep-style*
derivation — "did the XS call ``llUseShrineTradeNodeSpreadStyle``?") this
wrapper actually *executes* the XS in a Python interpreter and checks the
*resulting* globals. That catches a different class of drift:

  - Leader calls the right build-style helper but then overrides a global
    that pushes it out of the spec's band (e.g. Shivaji called
    ``llUseHighlandCitadelStyle(2)`` which set ``gLLMilitaryDistanceMultiplier``
    to 0.80, putting it outside Shivaji's spec band ``[1.0, 1.3]``).
  - Style helper itself drifts (someone tunes the helper, every leader
    using it silently moves out of band).
  - A bug in the rule firing order leaves a global at a transient value.

Two FAILs were already caught when this wrapper was first wired in:

  - shivaji   military_distance=0.80 outside spec band [1.0, 1.3]
  - tokugawa  military_distance=0.95 outside spec band [1.0, 1.3]

Both fixed in the same change that added this validator.

Run::

    python3 tools/validation/validate_xs_sim_doctrine.py
    python3 tools/validation/validate_xs_sim_doctrine.py \\
        --json artifacts/validation/xs_sim_doctrine.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("XS_SIM DOCTRINE — SIMULATED XS ↔ SPEC CLAIMS")
    print("=" * 60)

    # Run the underlying comparator in --json mode so we can both parse
    # the row data AND surface a human summary of any failures.
    proc = subprocess.run(
        [sys.executable, "-m", "tools.xs_sim.compare_doctrine", "--json"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
    )
    if proc.returncode not in (0, 1):
        # Anything other than PASS/FAIL is an orchestration error.
        print("  ERROR: compare_doctrine.py crashed")
        print(proc.stderr or proc.stdout)
        return 2

    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        print(f"  ERROR: comparator produced invalid JSON: {e}")
        print(proc.stdout[:500])
        return 2

    n_pass = sum(1 for r in rows if r["status"] == "PASS")
    n_fail = sum(1 for r in rows if r["status"] == "FAIL")
    n_unk  = sum(1 for r in rows if r["status"] == "UNKNOWN")
    n_no   = sum(1 for r in rows if r["status"] in ("NO_SPEC", "NO_CLAIMS"))

    print(f"  Leaders simulated: {len(rows)}")
    print(f"  PASS={n_pass}  FAIL={n_fail}  UNKNOWN={n_unk}  NO_SPEC/CLAIMS={n_no}")
    print()

    fails = [r for r in rows if r["status"] == "FAIL"]
    if fails:
        print("  Failures:")
        for r in fails:
            print(f"    {r['leader']}  ({r.get('civ', '?')}):")
            for msg in r["fails"]:
                print(f"      - {msg}")
        print()

    passed = n_fail == 0
    if passed:
        print(f"PASS — all {n_pass}/{len(rows)} leaders' simulated XS match spec claims")
    else:
        print(f"FAIL — {n_fail} leader(s) drift from spec claims")

    report = {
        "leaders_total": len(rows),
        "pass": n_pass,
        "fail": n_fail,
        "unknown": n_unk,
        "no_spec_or_claims": n_no,
        "rows": rows,
        "passed": passed,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
