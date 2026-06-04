#!/usr/bin/env python3
"""Synthesise a per-civ-correct probe log from the enriched reference.

Reads `enriched_reference.json` and emits a synthetic Age3Log slice for each
civ (or a chosen subset), where the probe values match what the reference says
the civ SHOULD do. Used to:

  - sanity-check that the validator achieves PASS under correct conditions
  - establish a baseline log shape for downstream tooling
  - regression-test reference-matrix changes

Usage:
    python3 synth_per_civ_log.py --out /tmp/synth_all.txt
    python3 synth_per_civ_log.py --civs ANWBritish ANWAztecs --out /tmp/synth_pair.txt
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent


def synth_for_civ(spec: dict, *, player_id: int = 1) -> list[str]:
    """Emit reference-matching probe lines for a single civ."""
    civ = spec.get("anw_token", "ANWUnknown")
    ldr = (spec.get("playstyle_spec") or {}).get("leader_label", "default")
    ldr_key = ldr.split()[0].lower() if ldr else "default"

    lines: list[str] = []

    def emit(t_ms: int, tag: str, detail: str = "") -> None:
        head = (
            f"PreGame  {t_ms}:  [ANWP v=2 t={t_ms} p={player_id} "
            f"civ={civ} ldr={ldr_key} tag={tag}]"
        )
        if detail:
            lines.append(f"{head} {detail}")
        else:
            lines.append(head)

    # ── Lifecycle markers ─────────────────────────────────────────────
    ws = spec.get("wall_strategy", 0)
    bs = spec.get("build_style", 1)
    band = spec.get("military_distance_band", [1.0, 1.0])
    mdist = (band[0] + band[1]) / 2.0

    # meta.boot fires once at AI bootstrap (~5s game-time)
    emit(5_000, "meta.boot",
         f"chatset=anw_{civ.lower()} wallStrategy={ws} "
         f"buildStyle={spec.get('doctrine_label','Unknown').replace(' ','')} "
         f"wallLevel=1")
    emit(5_500, "meta.setup",
         f"gameMode=1 difficulty=4 team=1 players=8")

    # chat.quote opening line at ~25s
    emit(25_000, "chat.quote", "kind=opening")

    # event.age_up at each transition
    emit(180_000, "event.age_up", "atMs=180000 age=2")
    emit(360_000, "event.age_up", "atMs=360000 age=3")
    emit(540_000, "event.age_up", "atMs=540000 age=4")

    # compliance.profile snapshots — fire periodically with doctrine knobs
    for t in (120_000, 300_000, 540_000):
        emit(t, "compliance.profile",
             f"style={bs} wallStrat={ws} wallLevel=1 earlyWalls=true "
             f"terrPrim=0 terrSec=0")

    # meta.gameover at end (with our auto-resign threshold this fires ~60s wall)
    emit(600_000, "meta.gameover", "lost=false finalAge=4 score=18000")

    # ── Milestones (existing) ─────────────────────────────────────────
    # Universal milestone every civ should hit
    emit(180_000, "milestone.first_barracks", "atMs=180000 count=1 age=1")
    emit(220_000, "milestone.first_stable", "atMs=220000 count=1 age=2")

    # Doctrine-specific milestones from spec.expected_milestones
    expected = spec.get("expected_milestones", {})
    if expected.get("dock"):
        emit(300_000, "milestone.first_dock", "atMs=300000 count=1 age=2")
    if expected.get("wall_segment"):
        emit(360_000, "milestone.first_wall_segment", "atMs=360000 count=4 age=2")
    if expected.get("forward_base"):
        emit(420_000, "milestone.first_forward_base", "atMs=420000 baseID=2 age=2")
    if expected.get("trading_post"):
        emit(480_000, "milestone.first_trading_post", "atMs=480000 count=1 age=2")
    # Fort and artillery milestones (universal, fired late game)
    emit(540_000, "milestone.first_fort", "atMs=540000 count=1 age=3")
    emit(560_000, "milestone.first_artillery", "atMs=560000 count=1 age=3")

    # Composition snapshots — match a plausible profile for the doctrine
    # Default composition: 60% inf, 25% cav, 15% arty
    for t in range(60_000, 600_001, 60_000):
        scale = t / 60_000  # 1..10 progression
        inf = int(8 * scale)
        cav = int(3 * scale)
        arty = int(1 * scale)
        emit(t, "comp.snapshot",
             f"ageMs={t} vil=20 inf={inf} cav={cav} "
             f"arty={arty} landmil={inf+cav+arty} warship=0")

    # Posture snapshots — match the reference exactly
    ws = spec.get("wall_strategy", 0)
    bs = spec.get("build_style", 1)
    band = spec.get("military_distance_band", [1.0, 1.0])
    mdist = (band[0] + band[1]) / 2.0  # midpoint of allowed band
    edist = 1.0
    for t in range(60_000, 600_001, 60_000):
        age = min(4, 1 + (t // 150_000))
        walls = 4 if expected.get("wall_segment") else 0
        forts = 1 if t > 540_000 else 0
        docks = 1 if expected.get("dock") else 0
        tposts = 1 if expected.get("trading_post") else 0
        emit(t, "posture.snapshot",
             f"ageMs={t} age={age} ws={ws} bs={bs} "
             f"mdist={mdist:.2f} edist={edist:.2f} "
             f"walls={walls} forts={forts} docks={docks} "
             f"tposts={tposts} heading=3 terrP=0 terrS=0")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", type=Path, default=REPO_ROOT / "enriched_reference.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--civs", nargs="*", help="restrict to these civ tokens")
    args = ap.parse_args()

    with open(args.reference) as f:
        ref = json.load(f)

    civs = ref["civs"]
    if args.civs:
        civs = {k: v for k, v in civs.items() if k in args.civs}
    if not civs:
        print(f"no civs matched filter: {args.civs}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for i, (token, spec) in enumerate(sorted(civs.items())):
            for line in synth_for_civ(spec, player_id=1 + (i % 8)):
                f.write(line + "\n")
    print(f"wrote {args.out} for {len(civs)} civs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
