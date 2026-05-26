#!/usr/bin/env python3
"""Static validator: anwHubTest.xs covers every spec milestone deadline.

The random-map doctrine test arena (``RandMaps/anwHubTest.xs``) runs in
two modes:

  * **fast**     — ``gHubTestEndSeconds = 120`` (default; quick
                   wall_strategy + posture sanity check)
  * **extended** — ``gHubTestEndSeconds >= 1200`` (full milestone
                   window for dock/wall/forward-base captures)

This validator locks the requirement that the extended-cycle threshold
covers every ``*_before_ms`` claim in ``playstyle_spec.json`` (with
some headroom) so a future test-cycle shortening can't silently lose
coverage of any civ's longest milestone deadline.

Specifically it asserts::

    extended_cycle_seconds * 1000 >= max(first_*_before_ms across all civs)

Run::

    python3 tools/validation/validate_hub_test_coverage.py
    python3 tools/validation/validate_hub_test_coverage.py \\
        --json artifacts/validation/hub_test_coverage.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

SPEC_PATH = REPO_ROOT / "playstyle_spec.json"
HUB_TEST_XS = REPO_ROOT / "RandMaps" / "anwHubTest.xs"

DEFAULT_DECL_RE = re.compile(
    r"\bint\s+gHubTestEndSeconds\s*=\s*(\d+)\s*;"
)
# Captures the largest "if (gHubTestEndSeconds >= N)" threshold present.
EXTENDED_THRESHOLD_RE = re.compile(
    r"\bif\s*\(\s*gHubTestEndSeconds\s*>=\s*(\d+)\s*\)"
)

# Claim keys that express a "must happen before N ms" deadline.
DEADLINE_KEYS = (
    "first_barracks_before_ms",
    "first_dock_before_ms",
    "first_wall_before_ms",
    "first_forward_base_before_ms",
    "first_artillery_before_ms",
)


def parse_test_map(xs_path: Path) -> dict:
    """Return parsed test-cycle config from anwHubTest.xs."""
    text = xs_path.read_text(encoding="utf-8", errors="replace")
    # Strip line comments so a commented-out declaration doesn't fool us.
    code = re.sub(r"//[^\n]*", "", text)

    default_match = DEFAULT_DECL_RE.search(code)
    if not default_match:
        raise ValueError(
            "Could not find 'int gHubTestEndSeconds = N;' declaration"
        )
    default_seconds = int(default_match.group(1))

    extended_thresholds = [int(m.group(1)) for m in EXTENDED_THRESHOLD_RE.finditer(code)]
    if not extended_thresholds:
        raise ValueError(
            "Could not find any 'if (gHubTestEndSeconds >= N)' threshold"
        )
    # Use the LARGEST threshold — that's the gate for the longest-cycle
    # markers (e.g. T+960s first_wall_segment deadline).
    extended_seconds = max(extended_thresholds)

    return {
        "default_seconds": default_seconds,
        "extended_seconds": extended_seconds,
        "all_thresholds": sorted(extended_thresholds),
    }


def max_spec_deadline_ms(spec: dict) -> dict:
    """Find the max deadline (ms) per key across all civs, plus overall max."""
    civs = spec.get("civs", {}) or {}
    per_key: dict[str, dict] = {}
    overall_max = 0
    overall_civ = None
    overall_key = None
    for token, civ in civs.items():
        claims = civ.get("claims", {}) or {}
        for key in DEADLINE_KEYS:
            val = claims.get(key)
            if val is None:
                continue
            entry = per_key.get(key)
            if entry is None or val > entry["value_ms"]:
                per_key[key] = {"value_ms": val, "civ": token}
            if val > overall_max:
                overall_max = val
                overall_civ = token
                overall_key = key
    return {
        "per_key": per_key,
        "overall_max_ms": overall_max,
        "overall_civ": overall_civ,
        "overall_key": overall_key,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=SPEC_PATH)
    ap.add_argument("--map", type=Path, default=HUB_TEST_XS)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("HUB TEST COVERAGE")
    print("=" * 60)

    if not args.spec.exists():
        print(f"  ERROR: spec file not found: {args.spec}")
        return 2
    if not args.map.exists():
        print(f"  ERROR: hub test map not found: {args.map}")
        return 2

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    try:
        cfg = parse_test_map(args.map)
    except ValueError as e:
        print(f"  ERROR parsing test map: {e}")
        return 2

    print(f"  Hub test default cycle:  {cfg['default_seconds']}s")
    print(f"  Hub test extended cycle threshold: >= {cfg['extended_seconds']}s")
    print(f"  All thresholds detected: {cfg['all_thresholds']}")
    print()

    deadlines = max_spec_deadline_ms(spec)
    overall_ms = deadlines["overall_max_ms"]
    overall_s = overall_ms / 1000
    extended_ms = cfg["extended_seconds"] * 1000

    print("  Per-claim max deadlines across spec:")
    for key, entry in sorted(deadlines["per_key"].items()):
        print(
            f"    {key:32s} max={entry['value_ms']:>8,} ms  ({entry['civ']})"
        )

    print()
    print(f"  Spec overall max deadline: {overall_ms:,} ms "
          f"({overall_s:.0f}s) — {deadlines['overall_key']} for {deadlines['overall_civ']!r}")
    print(f"  Test extended cycle:       {extended_ms:,} ms "
          f"({cfg['extended_seconds']}s)")

    passed = extended_ms >= overall_ms
    headroom_ms = extended_ms - overall_ms

    print()
    if passed:
        print(
            f"PASS — extended cycle covers every spec deadline "
            f"(headroom={headroom_ms:,} ms / {headroom_ms / 1000:.0f}s)"
        )
    else:
        print(
            "FAIL — extended cycle does NOT cover spec deadlines: "
            f"need >= {overall_ms} ms, have {extended_ms} ms"
        )

    report = {
        "test_map": {
            "default_seconds": cfg["default_seconds"],
            "extended_seconds": cfg["extended_seconds"],
        },
        "spec": {
            "per_key_max_ms": deadlines["per_key"],
            "overall_max_ms": overall_ms,
            "overall_civ": deadlines["overall_civ"],
            "overall_key": deadlines["overall_key"],
        },
        "passed": passed,
        "headroom_ms": headroom_ms,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"Report: {args.json_out}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
