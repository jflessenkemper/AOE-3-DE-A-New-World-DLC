#!/usr/bin/env python3
"""Generate per-civ-CORRUPT logs and verify the validator catches each one.

For every civ in the enriched reference, emit a synthetic match log where one
key piece of doctrine compliance is INTENTIONALLY WRONG (wall_strategy off by
one, mdist out of band, build_style wrong). The validator must FAIL each one.

If all 46 corrupt fixtures FAIL and all 46 correct fixtures PASS, the
validator covers per-civ doctrine assertions correctly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.validation.synth_per_civ_log import synth_for_civ
from tools.validation.parse_match_log import parse_log
from tools.validation.validate_civ_behavior import validate_log


def synth_corrupt(spec: dict, *, corruption: str, player_id: int = 1) -> list[str]:
    """Emit a synthetic log with one specific doctrine value WRONG."""
    # Make a copy and corrupt it
    bad_spec = dict(spec)
    if corruption == "wall_strategy":
        # Set to a value clearly different from the expected
        original = spec.get("wall_strategy", 0)
        bad_spec["wall_strategy"] = (original + 3) % 6  # always ≠ original
    elif corruption == "build_style":
        original = spec.get("build_style", 1)
        bad_spec["build_style"] = ((original + 5) % 14) + 1  # always ≠ original
    elif corruption == "mdist_out_of_band":
        # Force mdist out of band by setting band tight + value far
        band = spec.get("military_distance_band", [1.0, 1.0])
        # Don't modify spec; instead synth with a value way outside band
        # We'll pass a sentinel and post-process
        bad_spec["military_distance_band"] = [band[0], band[1]]
        bad_spec["__force_mdist__"] = 2.5  # used by our patched synth
    elif corruption == "no_required_milestone":
        # Strip expected_milestones → synth_for_civ will skip those probes
        bad_spec["expected_milestones"] = {}
        bad_spec["__skip_milestones__"] = True
    else:
        raise ValueError(f"unknown corruption: {corruption}")
    return synth_for_civ(bad_spec, player_id=player_id)


def evaluate_one(civ_token: str, spec: dict, corruption: str,
                 reference_path: Path, tmp_dir: Path) -> dict:
    """Generate a corrupt log for one civ + one corruption type, validate."""
    log_path = tmp_dir / f"corrupt_{civ_token}_{corruption}.log"
    lines = synth_corrupt(spec, corruption=corruption)
    log_path.write_text("\n".join(lines))
    report = validate_log(log_path, reference_path)
    civ_report = report["per_civ"].get(civ_token)
    if not civ_report:
        return {"civ": civ_token, "corruption": corruption,
                "verdict": "NO_DATA", "expected": "FAIL"}
    return {
        "civ": civ_token,
        "corruption": corruption,
        "verdict": civ_report["verdict"],
        "expected": "FAIL",
        "fail_count": civ_report["counts"].get("FAIL", 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", type=Path,
                    default=REPO_ROOT / "enriched_reference.json")
    ap.add_argument("--corruptions", nargs="+",
                    default=["wall_strategy", "build_style"])
    ap.add_argument("--out-dir", type=Path,
                    default=REPO_ROOT / "artifacts" / "negative_test_runs")
    args = ap.parse_args()

    if not args.reference.exists():
        print(f"missing: {args.reference}", file=sys.stderr)
        return 1
    with open(args.reference) as f:
        ref = json.load(f)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}

    for corruption in args.corruptions:
        print(f"\n{'='*70}")
        print(f"CORRUPTION: {corruption}")
        print(f"{'='*70}")
        results = []
        for civ_token, spec in sorted(ref["civs"].items()):
            r = evaluate_one(civ_token, spec, corruption, args.reference,
                             args.out_dir)
            results.append(r)
            mark = "✓" if r["verdict"] == "FAIL" else "✗"
            print(f"  {mark} {civ_token:<24} verdict={r['verdict']:<8} "
                  f"fails={r.get('fail_count', 0)}")

        # Summary per corruption
        caught = sum(1 for r in results if r["verdict"] == "FAIL")
        total = len(results)
        print(f"\n  Caught: {caught}/{total} ({100*caught/total:.0f}%)")
        summary[corruption] = {"caught": caught, "total": total,
                               "results": results}

    # Top-level summary
    summary_path = args.out_dir / "negative_test_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary: {summary_path}")

    # Exit code based on whether ALL corruptions were caught for ALL civs
    all_caught = all(s["caught"] == s["total"] for s in summary.values())
    return 0 if all_caught else 1


if __name__ == "__main__":
    sys.exit(main())
