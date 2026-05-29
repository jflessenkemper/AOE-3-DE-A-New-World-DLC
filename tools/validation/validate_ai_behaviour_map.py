#!/usr/bin/env python3
"""Static validator: ``ai_behaviour_map.json`` reports zero spec mismatches.

The AI behaviour mapper (`tools/validation/ai_behaviour_map.py`) reads
every per-leader XS file in ``game/ai/leaders/`` plus
``leader_revolution_commanders.xs`` / ``leader_revolution_support.xs``,
derives the AI's actual behaviour (wall strategy, forward-base axis,
naval axis, military focus, age-up biases, …), and compares each
civ's derived behaviour against the player-facing claims in
``playstyle_spec.json``.

When a leader's XS code doesn't match the spec claim — for instance,
the spec says ``expects_naval=True`` but the XS doesn't use a Naval
build-style helper, or the spec promises ``expects_forward=True`` but
no rule enables a forward base — the mapper records a *mismatch*.

This validator hard-fails the static gate when any mismatch is present,
so the player-facing doctrine card can't drift away from the actual
AI behaviour without someone noticing.

Run::

    python3 tools/validation/validate_ai_behaviour_map.py
    python3 tools/validation/validate_ai_behaviour_map.py \\
        --json artifacts/validation/ai_behaviour_map_check.json

The validator re-runs the mapper if the JSON artifact is missing
(so this is safe to call from CI without a separate preparation step).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
MAP_JSON = REPO_ROOT / "artifacts" / "validation" / "ai_behaviour_map.json"
MAP_SCRIPT = HERE / "ai_behaviour_map.py"


def _ensure_map() -> bool:
    """Regenerate the mapper output. Returns True on success."""
    if not MAP_SCRIPT.exists():
        print(f"  ERROR: mapper script not found: {MAP_SCRIPT}")
        return False
    try:
        subprocess.run(
            [sys.executable, str(MAP_SCRIPT)],
            check=True,
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"  ERROR: mapper exec failed: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, dest="json_out")
    ap.add_argument("--skip-regen", action="store_true",
                    help="don't regenerate the mapper artifact; use what's on disk")
    args = ap.parse_args()

    print("=" * 60)
    print("AI BEHAVIOUR MAP — SPEC ↔ XS CONSISTENCY")
    print("=" * 60)

    if not args.skip_regen:
        if not _ensure_map():
            return 2

    if not MAP_JSON.exists():
        print(f"  ERROR: behaviour map not found: {MAP_JSON}")
        return 2

    data = json.loads(MAP_JSON.read_text(encoding="utf-8"))
    civs = data.get("civs") or {}
    by_severity = {"high": 0, "medium": 0, "low": 0}
    per_civ_mismatches: dict[str, list] = {}
    for token, civ in civs.items():
        mm = civ.get("mismatches") or []
        if not mm:
            continue
        per_civ_mismatches[token] = mm
        for m in mm:
            sev = (m.get("severity") or "low").lower()
            by_severity[sev] = by_severity.get(sev, 0) + 1

    total_civs = len(civs)
    total_with_mismatch = len(per_civ_mismatches)
    total_mismatches = sum(by_severity.values())

    print(f"  Civs derived: {total_civs}")
    print(f"  Civs with mismatches: {total_with_mismatch}")
    print(f"  Severity breakdown: {by_severity}")
    print()

    if per_civ_mismatches:
        print("  Mismatches:")
        for token, mm in sorted(per_civ_mismatches.items()):
            print(f"    {token}  ({civs[token].get('source_file','?')}):")
            for m in mm:
                print(f"      [{m.get('severity','?').upper():6s}] "
                      f"claim={m.get('claim')!r} spec={m.get('spec')!r} "
                      f"derived={m.get('derived')!r}")
        print()

    passed = total_mismatches == 0

    if passed:
        print(f"PASS — all {total_civs} civs' XS behaviour matches spec claims")
    else:
        print(f"FAIL — {total_mismatches} mismatches across "
              f"{total_with_mismatch}/{total_civs} civs "
              f"({by_severity['high']} high, {by_severity['medium']} medium, "
              f"{by_severity['low']} low)")

    report = {
        "civ_count": total_civs,
        "civs_with_mismatches": total_with_mismatch,
        "mismatch_severity_counts": by_severity,
        "mismatches_per_civ": per_civ_mismatches,
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
