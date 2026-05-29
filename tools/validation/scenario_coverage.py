#!/usr/bin/env python3
"""Scenario-mode coverage report — bridge between authored scenarios and validator.

When the picker-based per-civ runner can't reliably bind ANW civs (the symptom
that motivated `docs/SCENARIO_AUTHORING_PLAYBOOK.md`), the alternative is to
author six 8-player scenarios (`ANW_Coverage_A` … `ANW_Coverage_F`) with
hard-coded player→civ bindings, run each, and concatenate the resulting log
slices.

This tool consumes either:
  * a directory of per-scenario log slices (e.g. `A_log.txt`, `B_log.txt`, …),
  * or a single `Age3Log.txt` containing multiple sequential scenario runs,

and answers two questions the existing validator cannot answer alone:

  1. **Coverage** — which of the 46 ANW civs actually emitted probes? Which
     are still missing? (Prevents declaring "all 46 PASS" when half never
     fired meta.boot.)
  2. **Scenario provenance** — which scenario file is each civ expected to
     come from? Which scenarios are incomplete?

It then concatenates the per-civ probes into a single dict and runs the
existing per-civ validator on each, emitting a 46-civ report aware of the
scenario-file split.

Usage:
    # Validate a directory of scenario log slices:
    python3 scenario_coverage.py --slice-dir artifacts/scenario_runs

    # Validate one combined log:
    python3 scenario_coverage.py --log artifacts/scenario_runs/full_log.txt

    # Override the expected scenario→civ map (e.g. you authored a different split):
    python3 scenario_coverage.py --slice-dir ... --scenario-map my_split.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.validation.parse_match_log import parse_log
from tools.validation.validate_civ_behavior import validate_civ


# Default scenario→civ matrix from docs/SCENARIO_AUTHORING_PLAYBOOK.md.
# Five 8-slot scenarios cover all 40 ANW civs (4 dormant civs removed 2026-05-19).
# 2026-05-18: Updated to 44-civ roster after ANWAmericans, ANWBajaCalifornians
# removal and ANWFrenchCanadians → ANWCanadians merge.
# 2026-05-19: Removed 4 dormant civs — now 40 primaries in A-E. F is dropped from coverage tracking
# (emitter PLAYBOOK_MATRIX still has an F with filler slots for binding tests).
DEFAULT_SCENARIO_MAP: dict[str, list[str]] = {
    "A": [
        "ANWArgentines", "ANWAztecs", "ANWBarbary", "ANWBrazil",
        "ANWBritish", "ANWCanadians", "ANWChileans", "ANWChinese",
    ],
    "B": [
        "ANWColumbians", "ANWDutch", "ANWEgyptians", "ANWEthiopians",
        "ANWFinnish", "ANWFrench", "ANWGermans", "ANWHaitians",
    ],
    "C": [
        "ANWHaudenosaunee", "ANWHausa", "ANWHungarians", "ANWInca",
        "ANWIndians", "ANWIndonesians", "ANWItalians", "ANWJapanese",
    ],
    "D": [
        "ANWLakota", "ANWMaltese", "ANWMayans", "ANWMexicans",
        "ANWNapoleonicFrance", "ANWOttomans", "ANWPeruvians", "ANWPortuguese",
    ],
    "E": [
        "ANWRevFrance", "ANWRomanians", "ANWRussians", "ANWSouthAfricans",
        "ANWSpanish", "ANWSwedes", "ANWTexians", "ANWUSA",
    ],
}


def all_expected_civs(scenario_map: dict[str, list[str]]) -> set[str]:
    out: set[str] = set()
    for civs in scenario_map.values():
        out.update(civs)
    return out


def collect_logs(
    slice_dir: Path | None,
    single_log: Path | None,
) -> dict[str, Path]:
    """Return {label: log_path}.

    When given a slice dir, looks for `<LETTER>_log.txt` (case-insensitive)
    and uses the letter as the scenario label. When given a single log, uses
    the label '*' (treats all probes as one big bucket).
    """
    if single_log is not None:
        if not single_log.exists():
            raise FileNotFoundError(single_log)
        return {"*": single_log}

    if slice_dir is None:
        raise ValueError("need either --slice-dir or --log")
    if not slice_dir.exists():
        raise FileNotFoundError(slice_dir)

    out: dict[str, Path] = {}
    # Accept e.g. A_log.txt, a_log.txt, scenario_A.log
    LOG_EXTS = {".log", ".txt"}
    for p in sorted(slice_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in LOG_EXTS:
            continue
        stem = p.stem.upper()
        # Heuristic: pull a single uppercase letter that looks like a label
        for tok in stem.replace("_", " ").replace("-", " ").split():
            if len(tok) == 1 and tok.isalpha():
                out[tok] = p
                break
        else:
            # No single-letter token — fall back to using the stem
            out[stem] = p
    if not out:
        raise RuntimeError(f"no log files found in {slice_dir}")
    return out


def coverage_summary(
    civs_seen_by_scenario: dict[str, set[str]],
    scenario_map: dict[str, list[str]],
) -> dict[str, Any]:
    """Per-scenario + overall coverage stats."""
    expected_total = all_expected_civs(scenario_map)
    seen_total: set[str] = set()
    for s in civs_seen_by_scenario.values():
        seen_total |= s

    per_scenario = {}
    for label, expected in scenario_map.items():
        # Match by exact label first, otherwise by '*' bucket
        seen = civs_seen_by_scenario.get(label) or civs_seen_by_scenario.get("*", set())
        seen_for_this = {c for c in seen if c in expected}
        missing = [c for c in expected if c not in seen_for_this]
        per_scenario[label] = {
            "expected": expected,
            "seen": sorted(seen_for_this),
            "missing": missing,
            "coverage_pct": (
                round(100 * len(seen_for_this) / max(1, len(expected)), 1)
            ),
        }

    return {
        "expected_civ_count": len(expected_total),
        "seen_civ_count": len(seen_total & expected_total),
        "unexpected_civs_seen": sorted(seen_total - expected_total),
        "missing_civs_overall": sorted(expected_total - seen_total),
        "overall_coverage_pct": (
            round(100 * len(seen_total & expected_total) / max(1, len(expected_total)), 1)
        ),
        "per_scenario": per_scenario,
    }


def merge_probes(
    per_log_probes: dict[str, dict[str, dict[str, list[dict[str, Any]]]]],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Combine probes from multiple log slices into one {civ: {tag: [...]}}."""
    merged: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for probes in per_log_probes.values():
        for civ, tagmap in probes.items():
            for tag, recs in tagmap.items():
                merged[civ][tag].extend(recs)
    return {c: dict(t) for c, t in merged.items()}


def run_validator(
    merged_probes: dict[str, dict[str, list[dict[str, Any]]]],
    reference: dict[str, Any],
) -> dict[str, Any]:
    """Run validate_civ on every civ that has probes."""
    per_civ: dict[str, Any] = {}
    for civ, tagmap in merged_probes.items():
        spec = reference.get("civs", {}).get(civ)
        if spec is None:
            per_civ[civ] = {"verdict": "NO_REFERENCE", "results": []}
            continue
        result = validate_civ(civ, tagmap, spec)
        per_civ[civ] = result
    return per_civ


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--slice-dir", type=Path,
                   help="directory containing per-scenario log slices")
    g.add_argument("--log", type=Path,
                   help="single combined Age3Log.txt to parse")
    ap.add_argument("--scenario-map", type=Path,
                    help="JSON of {scenario_label: [civ_token, ...]}; "
                         "defaults to the playbook matrix (A-F)")
    ap.add_argument("--reference", type=Path,
                    default=REPO_ROOT / "enriched_reference.json")
    ap.add_argument("--report", type=Path,
                    help="write JSON report here (default: stdout summary only)")
    args = ap.parse_args()

    # Load scenario map
    if args.scenario_map:
        with open(args.scenario_map) as f:
            scenario_map = json.load(f)
    else:
        scenario_map = DEFAULT_SCENARIO_MAP

    # Collect logs
    logs = collect_logs(args.slice_dir, args.log)

    # Parse each log
    per_log_probes: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
    civs_seen_by_scenario: dict[str, set[str]] = {}
    for label, path in logs.items():
        probes = parse_log(path)
        per_log_probes[label] = probes
        civs_seen_by_scenario[label] = set(probes.keys())

    coverage = coverage_summary(civs_seen_by_scenario, scenario_map)

    # Validate (only if reference available)
    validator_results: dict[str, Any] = {}
    if args.reference.exists():
        with open(args.reference) as f:
            reference = json.load(f)
        merged = merge_probes(per_log_probes)
        validator_results = run_validator(merged, reference)
    else:
        print(f"warning: {args.reference} not found; skipping validator step",
              file=sys.stderr)

    # Aggregate verdicts
    verdict_counts: dict[str, int] = defaultdict(int)
    for r in validator_results.values():
        verdict_counts[r.get("verdict", "?")] += 1

    report = {
        "logs_analyzed": {label: str(p) for label, p in logs.items()},
        "scenario_map_source": (
            str(args.scenario_map) if args.scenario_map else "default (playbook A-F)"
        ),
        "coverage": coverage,
        "validator": {
            "verdict_counts": dict(verdict_counts),
            "per_civ_verdicts": {
                civ: r.get("verdict", "?") for civ, r in validator_results.items()
            },
        },
    }
    if args.report:
        # When user wants the full validator detail, include it
        report["validator"]["per_civ"] = validator_results

    # Print summary
    print("=" * 70)
    print("SCENARIO COVERAGE REPORT")
    print("=" * 70)
    print(f"Logs analyzed: {len(logs)}")
    for label, path in logs.items():
        n = len(civs_seen_by_scenario[label])
        print(f"  [{label}] {path}  ({n} civs)")
    print()
    print(f"Overall ANW coverage: "
          f"{coverage['seen_civ_count']}/{coverage['expected_civ_count']} "
          f"({coverage['overall_coverage_pct']}%)")
    if coverage["missing_civs_overall"]:
        print(f"Missing: {coverage['missing_civs_overall']}")
    if coverage["unexpected_civs_seen"]:
        print(f"Unexpected civs in logs: {coverage['unexpected_civs_seen']}")
    print()
    print("Per-scenario coverage:")
    for label, info in coverage["per_scenario"].items():
        seen_n = len(info["seen"])
        exp_n = len(info["expected"])
        mark = "✓" if seen_n == exp_n else "✗" if seen_n == 0 else "⚠"
        print(f"  {mark} [{label}] {seen_n}/{exp_n} "
              f"({info['coverage_pct']}%)")
        if info["missing"]:
            print(f"      missing: {info['missing']}")
    print()
    if validator_results:
        print(f"Validator verdicts: {dict(verdict_counts)}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report: {args.report}")

    # Exit nonzero if any civ failed validation OR coverage incomplete
    if verdict_counts.get("FAIL", 0) > 0:
        return 2
    if coverage["seen_civ_count"] < coverage["expected_civ_count"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
