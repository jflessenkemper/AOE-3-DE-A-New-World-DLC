#!/usr/bin/env python3
"""Synthetic probe-log fixtures for testing the validator without running a real match.

Generates realistic [LLP v=2 ...] log lines that mirror what aiDoctrineProbes.xs
would emit for a given civ and a given doctrine compliance pattern.

Used by:
  - parse_match_log.py (parser correctness)
  - validate_civ_behavior.py (validator correctness)

Usage:
    python3 test_fixtures.py good > /tmp/log_good.txt
    python3 test_fixtures.py bad-mdist > /tmp/log_bad.txt
    python3 test_fixtures.py mixed --civs ANWBritish ANWAztecs > /tmp/log_mixed.txt
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterator

# Reasonable scenario for a 10-min match
DEFAULT_PLAYER_ID = 1


def _line(t_ms: int, p: int, civ: str, ldr: str, tag: str, detail: str = "") -> str:
    """Format a single [LLP v=2 ...] line, preceded by an Age3Log-style prefix."""
    base = (
        f"PreGame  {t_ms}:  [LLP v=2 t={t_ms} p={p} civ={civ} ldr={ldr} tag={tag}]"
    )
    if detail:
        return f"{base} {detail}"
    return base


def emit_match(
    civ: str,
    ldr: str = "default",
    *,
    player_id: int = DEFAULT_PLAYER_ID,
    profile: str = "good",
) -> Iterator[str]:
    """Emit a sequence of probe lines for a single civ over a 600s match.

    profile:
      - "good": all milestones fire, posture matches reference, comp ratios on-target
      - "bad-mdist": military_distance out of band
      - "no-walls": skips wall_segment milestone (bad for civs that expect walls)
      - "stuck-age1": never advances past age 1
      - "no-comp": no comp.snapshot probes (rule disabled)
    """
    # Milestones — fire times in ms
    if profile == "stuck-age1":
        # Only 1 milestone, no age-up
        yield _line(60_000, player_id, civ, ldr, "milestone.first_barracks",
                    "atMs=60000 count=1 age=1")
    else:
        # Common milestones at plausible times
        yield _line(180_000, player_id, civ, ldr, "milestone.first_barracks",
                    "atMs=180000 count=1 age=1")
        yield _line(220_000, player_id, civ, ldr, "milestone.first_stable",
                    "atMs=220000 count=1 age=2")
        if profile != "no-walls":
            yield _line(360_000, player_id, civ, ldr, "milestone.first_wall_segment",
                        "atMs=360000 count=4 age=2")
        yield _line(420_000, player_id, civ, ldr, "milestone.first_artillery",
                    "atMs=420000 count=1 age=3")
        yield _line(480_000, player_id, civ, ldr, "milestone.first_trading_post",
                    "atMs=480000 count=1 age=2")

    # Snapshots every 60s
    if profile != "no-comp":
        for t in range(60_000, 600_001, 60_000):
            age = 1 + (t // 180_000)
            inf = max(0, (t // 30_000) - 4)
            cav = max(0, (t // 45_000) - 5)
            arty = max(0, (t // 120_000) - 3)
            land = inf + cav + arty
            yield _line(t, player_id, civ, ldr, "comp.snapshot",
                        f"ageMs={t} vil=20 inf={inf} cav={cav} "
                        f"arty={arty} landmil={land} warship=0")

    # Posture snapshots
    for t in range(60_000, 600_001, 60_000):
        ws = 1            # ChokepointSegments
        bs = 3            # ForwardOperationalLine
        if profile == "bad-mdist":
            mdist = 2.5   # way out of normal [0.7, 1.4] band
        else:
            mdist = 1.05
        edist = 1.0
        age = min(4, 1 + (t // 150_000))
        yield _line(t, player_id, civ, ldr, "posture.snapshot",
                    f"ageMs={t} age={age} ws={ws} bs={bs} "
                    f"mdist={mdist:.2f} edist={edist:.2f} "
                    f"walls=4 forts=0 docks=0 tposts=1 heading=3 terrP=0 terrS=0")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("profile", choices=[
        "good", "bad-mdist", "no-walls", "stuck-age1", "no-comp", "mixed",
    ])
    ap.add_argument("--civs", nargs="+", default=["ANWBritish"])
    ap.add_argument("--ldr", default="wellington")
    args = ap.parse_args()

    if args.profile == "mixed":
        # Each civ gets a different profile for stress-testing the validator
        sub_profiles = ["good", "bad-mdist", "no-walls", "stuck-age1", "no-comp"]
        for i, civ in enumerate(args.civs):
            prof = sub_profiles[i % len(sub_profiles)]
            for line in emit_match(civ, args.ldr, player_id=1 + i, profile=prof):
                print(line)
    else:
        for i, civ in enumerate(args.civs):
            for line in emit_match(civ, args.ldr, player_id=1 + i,
                                   profile=args.profile):
                print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
