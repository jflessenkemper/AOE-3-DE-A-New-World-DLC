#!/usr/bin/env python3
"""Static validator: ``artifacts/validation/hub_test_roster.json`` integrity.

The 40-civ canonical hub-test roster (``artifacts/validation/hub_test_roster.md``
+ ``.json``) is the schedule referenced from the release-readiness site to
spot-check every civ in-engine via the ``anwHubTest`` random map. It MUST
stay in sync with three sources of truth:

1. ``playstyle_spec.json`` — every spec civ (40) appears exactly once in
   the roster; no orphans, no duplicates.

2. ``RandMaps/anwHubTest.xs`` — each pass fits the 7-AI-slots-per-run
   capacity (the 8th slot is the observer player). Hub test cannot seat
   more than 7 civs at a time.

3. ``tools/validation/build_hub_test_roster.py`` — the JSON checked in
   matches the script's output for the current spec. Regenerating the
   roster is deterministic (stable sort), so a stale JSON would mean
   someone edited the file by hand or the spec changed without re-running
   the generator. Either is a release-blocking drift.

This validator parallels ``validate_per_civ_wall_knobs.py``: a static
JSON-vs-spec cross-check that ensures the test schedule the release-
readiness site advertises is real and current.

Run::

    python3 tools/validation/validate_hub_test_roster.py
    python3 tools/validation/validate_hub_test_roster.py \\
        --json artifacts/validation/hub_test_roster_integrity.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

SPEC_PATH = REPO_ROOT / "playstyle_spec.json"
ROSTER_JSON = REPO_ROOT / "artifacts" / "validation" / "hub_test_roster.json"
ROSTER_MD = REPO_ROOT / "artifacts" / "validation" / "hub_test_roster.md"
BUILD_SCRIPT = REPO_ROOT / "tools" / "validation" / "build_hub_test_roster.py"

# The anwHubTest map is hard-coded to 8 player slots, slot 1 = observer.
HUB_SLOT_CAPACITY = 7


def check_coverage(roster: dict, spec_civs: dict) -> list[str]:
    """Every spec civ must be seated exactly once; no extras."""
    out = []
    seated = []
    for p in roster.get("passes", []):
        seated.extend(p.get("civs", []))
    seated_set = set(seated)
    spec_set = set(spec_civs.keys())

    if len(seated) != len(seated_set):
        from collections import Counter
        for civ, n in Counter(seated).items():
            if n > 1:
                out.append(f"duplicate seating: {civ} appears {n} times")

    missing = spec_set - seated_set
    extra = seated_set - spec_set
    for civ in sorted(missing):
        out.append(f"spec civ NOT in roster: {civ}")
    for civ in sorted(extra):
        out.append(f"roster civ NOT in spec: {civ}")
    return out


def check_capacity(roster: dict) -> list[str]:
    """No pass may exceed the hub test 7-AI slot capacity."""
    out = []
    for p in roster.get("passes", []):
        n = len(p.get("civs", []))
        if n > HUB_SLOT_CAPACITY:
            out.append(
                f"pass {p.get('index')}: {n} civs exceeds capacity "
                f"({HUB_SLOT_CAPACITY})"
            )
        if n == 0:
            out.append(f"pass {p.get('index')}: empty (0 civs)")
    return out


def check_strategy_alignment(roster: dict, spec_civs: dict) -> list[str]:
    """Each seated civ's strategy in the roster matches the spec claim."""
    out = []
    for p in roster.get("passes", []):
        civs = p.get("civs", [])
        strats = p.get("strategies", [])
        if len(civs) != len(strats):
            out.append(
                f"pass {p.get('index')}: civ count ({len(civs)}) != "
                f"strategy count ({len(strats)})"
            )
            continue
        for civ, claimed_ws in zip(civs, strats):
            spec_ws = (
                spec_civs.get(civ, {}).get("claims", {}) or {}
            ).get("wall_strategy")
            if spec_ws != claimed_ws:
                out.append(
                    f"pass {p.get('index')}: {civ} roster ws={claimed_ws} "
                    f"but spec ws={spec_ws}"
                )
    return out


def check_regeneratable(spec_path: Path, current_json: dict) -> list[str]:
    """Re-run the generator and confirm the roster is byte-equivalent
    (deterministic stable sort means any drift = stale JSON)."""
    out = []
    proc = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT),
         "--spec", str(spec_path),
         "--md", "/tmp/hub_test_roster_check.md",
         "--json", "/tmp/hub_test_roster_check.json"],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        out.append(f"build_hub_test_roster.py crashed: {proc.stderr[:200]}")
        return out
    try:
        regenerated = json.loads(Path("/tmp/hub_test_roster_check.json").read_text())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        out.append(f"regenerated JSON unreadable: {e}")
        return out

    cur_passes = [(p.get("index"), p.get("civs", []), p.get("strategies", []))
                  for p in current_json.get("passes", [])]
    new_passes = [(p.get("index"), p.get("civs", []), p.get("strategies", []))
                  for p in regenerated.get("passes", [])]

    if cur_passes != new_passes:
        out.append("roster JSON drifts from build_hub_test_roster.py output "
                   "(re-run the generator)")
        for i, (cur, new) in enumerate(zip(cur_passes, new_passes)):
            if cur != new:
                out.append(f"  pass {i + 1}: checked={cur[1]} vs generated={new[1]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=SPEC_PATH)
    ap.add_argument("--roster", type=Path, default=ROSTER_JSON)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("HUB TEST ROSTER INTEGRITY")
    print("=" * 60)

    if not args.spec.exists():
        print(f"  ERROR: spec file not found: {args.spec}")
        return 2
    if not args.roster.exists():
        print(f"  ERROR: roster JSON not found: {args.roster}")
        print("         re-run: python3 tools/validation/build_hub_test_roster.py")
        return 2
    if not ROSTER_MD.exists():
        print(f"  ERROR: roster MD not found: {ROSTER_MD}")
        return 2

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    civs = spec.get("civs", {}) or {}
    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    print(f"  Spec civs:        {len(civs)}")
    print(f"  Roster passes:    {len(roster.get('passes', []))}")
    print(f"  Roster seated:    {sum(len(p.get('civs', [])) for p in roster.get('passes', []))}")
    print()

    checks = [
        ("coverage (every civ once, no extras)", check_coverage(roster, civs)),
        ("capacity (≤7 civs/pass)",              check_capacity(roster)),
        ("strategy alignment (roster ws == spec ws)",
                                                  check_strategy_alignment(roster, civs)),
        ("regeneratable (JSON == script output)", check_regeneratable(args.spec, roster)),
    ]
    total_violations = 0
    results: dict = {}
    for name, violations in checks:
        results[name] = violations
        total_violations += len(violations)
        status = "PASS" if not violations else f"FAIL ({len(violations)})"
        print(f"  {status:11s}  {name}")
        for v in violations[:6]:
            print(f"               - {v}")
        if len(violations) > 6:
            print(f"               ... +{len(violations) - 6} more")

    print()
    overall_pass = total_violations == 0
    if overall_pass:
        print(f"PASS — roster covers {sum(len(p.get('civs', [])) for p in roster.get('passes', []))}"
              f"/{len(civs)} civs across {len(roster.get('passes', []))} passes,"
              f" all integrity checks green")
    else:
        print(f"FAIL — {total_violations} integrity violations")

    report = {
        "checks": {k: v for k, v in results.items()},
        "total_violations": total_violations,
        "spec_civ_count": len(civs),
        "roster_pass_count": len(roster.get("passes", [])),
        "passed": overall_pass,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
