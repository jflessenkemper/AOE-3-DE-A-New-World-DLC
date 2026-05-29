#!/usr/bin/env python3
"""Generate a 6-pass roster schedule for anwHubTest covering all 40 civs.

The hub test seats up to 7 AI players per run (slot 1 = observer). With
40 civs total we need 6 cycles to spot-check every doctrine in-engine.
The schedule mixes wall-strategies per pass so each run exercises
cross-strategy interactions (e.g. FortressRing turtling next to a Mobile
forward-cavalry rusher).

This is the canonical 40-civ test-coverage plan referenced from the
release readiness site. Re-run after spec edits to keep the schedule
in sync.

Usage::

    python3 tools/validation/build_hub_test_roster.py
    python3 tools/validation/build_hub_test_roster.py --json artifacts/validation/hub_test_roster.json
"""
from __future__ import annotations
import argparse, json, itertools, sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = REPO / "playstyle_spec.json"
OUT_MD = REPO / "artifacts" / "validation" / "hub_test_roster.md"

STRAT_NAMES = ["FortressRing", "Chokepoint", "Coastal",
               "Frontier", "Urban", "Mobile"]


def build_schedule(civs: dict) -> list[list[str]]:
    by_strat = defaultdict(list)
    for n, v in civs.items():
        s = v.get("claims", {}).get("wall_strategy")
        if s is None:
            continue
        by_strat[s].append(n)
    # Stable round-robin so reruns yield identical schedule
    for s in by_strat:
        by_strat[s].sort()

    placed = []
    queues = {s: list(by_strat[s]) for s in sorted(by_strat)}
    strat_cycle = itertools.cycle(sorted(by_strat))
    while any(queues.values()):
        s = next(strat_cycle)
        if queues[s]:
            placed.append(queues[s].pop(0))
    # Split into chunks of 7
    return [placed[i:i + 7] for i in range(0, len(placed), 7)]


def render_md(passes: list[list[str]], civs: dict) -> str:
    lines = [
        "# ANW Hub Test — 40-Civ Roster Schedule",
        "",
        "**Map:** anwHubTest (8-player slot, observer at center)",
        "**Capacity:** ≤7 AI civs per run",
        f"**Total civs:** {sum(len(p) for p in passes)}/40",
        f"**Passes required:** {len(passes)}",
        "",
        "Each pass mixes wall strategies so cross-doctrine interactions",
        "(e.g. FortressRing turtle next to Mobile cavalry rusher) are",
        "exercised. Run the cycle once per pass with the listed civs",
        "seated in slots 2-8.",
        "",
    ]
    for i, p in enumerate(passes, 1):
        lines.append(f"## Pass {i} ({len(p)} civs)")
        lines.append("")
        lines.append("| Slot | Strategy | Civ + Leader |")
        lines.append("|---|---|---|")
        for slot, c in enumerate(p, 2):
            ws = civs[c]["claims"]["wall_strategy"]
            lines.append(f"| {slot} | s{ws}-{STRAT_NAMES[ws]} | {c} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=SPEC)
    ap.add_argument("--json", type=Path, dest="json_out")
    ap.add_argument("--md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text())
    civs = spec["civs"]
    passes = build_schedule(civs)
    md = render_md(passes, civs)

    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text(md)
    print(f"  Wrote: {args.md}  ({args.md.stat().st_size} bytes)")
    print(f"  Total: {sum(len(p) for p in passes)}/40 civs in {len(passes)} passes")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "passes": [
                {"index": i + 1, "civs": p,
                 "strategies": [civs[c]["claims"]["wall_strategy"] for c in p]}
                for i, p in enumerate(passes)
            ],
            "total_civs": sum(len(p) for p in passes),
            "pass_count": len(passes),
        }
        args.json_out.write_text(json.dumps(report, indent=2))
        print(f"  JSON: {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
