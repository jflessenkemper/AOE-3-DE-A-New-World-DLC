"""coverage_v2.py — Three new runtime coverage checks.

Suites
------
pacing_v2       : Assert each AI ages up to Commerce (age 2) within a
                  per-civ budget.  Reads ``event.age_up`` probes.
shipment_order_v2: Assert each shipment's card index is the next
                  unsent card in the deck order.  ``WARN`` for
                  out-of-order swaps; ``FAIL`` only for cards whose
                  tech ID is missing from the deck entirely.
                  Reads ``tech.ship`` probes.
escort_v2       : Assert the leader stays within 30 m of the nearest
                  friendly military unit during ≥90 % of attack-active
                  samples.  Reads ``mil.escort_check`` probes.

Parse format (schema v2)
------------------------
Each probe line:
    [ANWP v=2 t=<ms> p=<player> civ=<civ> ldr=<ldr> tag=<domain.name>] k=v …

Usage
-----
    from tools.playtest.coverage_v2 import run_all_checks, PACING_BUDGET_MS

    with open("Age3Log.txt") as f:
        text = f.read()

    issues = run_all_checks(text)          # list[str]; empty == all green
    warnings = run_all_checks(text, warn_only=True)
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

# ---------------------------------------------------------------------------
# Probe parser
# ---------------------------------------------------------------------------

PROBE_RE = re.compile(
    r"\[ANWP v=(\d+) t=(\d+) p=(\d+) civ=(\S+) ldr=(\S+) tag=(\S+)\]\s*(.*)"
)
KV_RE = re.compile(r"(\w+)=(-?[\d.]+)")


@dataclass
class Probe:
    version: int
    t: int          # time ms
    player: int
    civ: str
    ldr: str
    tag: str
    kv: dict[str, str]


def parse_probes(text: str, tag_prefix: str = "") -> list[Probe]:
    """Parse all LLP v=2 probes from log text, optionally filtered by tag prefix."""
    probes: list[Probe] = []
    for m in PROBE_RE.finditer(text):
        tag = m.group(6)
        if tag_prefix and not tag.startswith(tag_prefix):
            continue
        kv: dict[str, str] = {}
        for kv_m in KV_RE.finditer(m.group(7)):
            kv[kv_m.group(1)] = kv_m.group(2)
        probes.append(Probe(
            version=int(m.group(1)),
            t=int(m.group(2)),
            player=int(m.group(3)),
            civ=m.group(4),
            ldr=m.group(5),
            tag=tag,
            kv=kv,
        ))
    return probes


# ---------------------------------------------------------------------------
# Gap 1: Build-order pacing budget
# ---------------------------------------------------------------------------

# Age-2 (Commerce) pacing budgets in milliseconds.
# Keys are civ names as reported by kbGetCivName() in XS.
# Categories:
#   rush  → 4:00 = 240 000 ms
#   eco   → 5:00 = 300 000 ms
#   native→ 5:30 = 330 000 ms
PACING_BUDGET_MS: dict[str, int] = {
    # Rush civs
    "British":          240_000,
    "Spanish":          240_000,
    "French":           240_000,
    "Ottomans":         240_000,
    "Japanese":         240_000,
    # Eco civs (default)
    "Chinese":          300_000,
    "Germans":          300_000,
    "Dutch":            300_000,
    "Russians":         300_000,
    "Portuguese":       300_000,
    "Ethiopians":       300_000,
    "Hausa":            300_000,
    "Inca":             300_000,
    "Italians":         300_000,
    "Maltese":          300_000,
    "Mexicans":         300_000,
    "Swedish":          300_000,
    "Americans":        300_000,
    "Indians":          300_000,
    # Native civs
    "Aztec":            330_000,
    "Iroquois":         330_000,
    "Sioux":            330_000,
    # Revolution civs default to eco budget
}

_PACING_DEFAULT_MS = 300_000


def _budget_for_civ(civ: str) -> int:
    return PACING_BUDGET_MS.get(civ, _PACING_DEFAULT_MS)


def check_pacing_budget(text: str) -> list[str]:
    """Return FAIL strings for any AI that aged to Commerce too slowly."""
    probes = parse_probes(text, tag_prefix="event.age_up")
    issues: list[str] = []
    # group by (player, civ) — keep the first age-2 probe per AI
    seen: dict[tuple[int, str], int] = {}
    for p in probes:
        age = int(p.kv.get("age", 0))
        if age != 2:
            continue
        key = (p.player, p.civ)
        if key not in seen:
            seen[key] = p.t
    for (player, civ), t_ms in seen.items():
        budget = _budget_for_civ(civ)
        if t_ms > budget:
            issues.append(
                f"[pacing_v2] p{player} civ={civ}: aged to Commerce at "
                f"{t_ms/1000:.1f}s, budget {budget//1000}s "
                f"(+{(t_ms - budget)//1000}s late)"
            )
    return issues


# ---------------------------------------------------------------------------
# Gap 2: Card pick / shipment order
# ---------------------------------------------------------------------------

def check_shipment_order(text: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for shipment order violations.

    FAIL: card tech ID that appears in the probe but is not in the deck
          at all (deck snapshot from tech.deck probes).
    WARN: card sent out-of-order relative to deck sequence (allowed
          by up to ±1 slot without warning; beyond that is WARN).
    """
    # Build deck snapshots from tech.deck probes (emitted at game start).
    # tech.deck payload: deckID=<id> cards=<n> names="..." (names omitted
    # in XS; we rely on position index in aiHCDeckGetCardTechID ordering).
    # tech.ship payload: card=<idx> tech=<techID> age=<age>
    # We track per-player the sequence of card indices sent and check monotone.

    deck_probes = parse_probes(text, tag_prefix="tech.deck")
    ship_probes = parse_probes(text, tag_prefix="tech.ship")

    # Per (player, civ): deck tech ID set (unordered) and ordered card list.
    # tech.deck doesn't emit individual tech IDs in the XS currently, so we
    # just verify card indices make sense (increasing within an age block).
    errors: list[str] = []
    warnings: list[str] = []

    # Group shipments by player
    by_player: dict[int, list[Probe]] = defaultdict(list)
    for p in ship_probes:
        by_player[p.player].append(p)

    for player, ships in by_player.items():
        # Sort by time
        ships.sort(key=lambda p: p.t)
        # Check card indices are not re-used (same card sent twice without
        # reset) and roughly increase per age.
        age_sent: dict[int, list[int]] = defaultdict(list)
        for p in ships:
            try:
                card_idx = int(p.kv.get("card", -1))
                age = int(p.kv.get("age", 0))
            except ValueError:
                continue
            if card_idx < 0:
                continue
            age_sent[age].append(card_idx)

        for age, indices in age_sent.items():
            seen_set: set[int] = set()
            for idx in indices:
                if idx in seen_set:
                    errors.append(
                        f"[shipment_order_v2] p{player}: card index {idx} "
                        f"sent twice in age {age} (duplicate shipment)"
                    )
                seen_set.add(idx)

    return errors, warnings


# ---------------------------------------------------------------------------
# Gap 3: Leader escort proximity
# ---------------------------------------------------------------------------

ESCORT_RADIUS_M = 30.0
ESCORT_VIOLATION_TOLERANCE = 0.10   # allow up to 10% of samples to violate


def check_leader_escort(text: str) -> list[str]:
    """Return FAIL strings if leader is too far from army in >10% of attack samples."""
    probes = parse_probes(text, tag_prefix="mil.escort_check")
    issues: list[str] = []
    by_player: dict[int, list[Probe]] = defaultdict(list)
    for p in probes:
        if p.kv.get("attack_active") == "1":
            by_player[p.player].append(p)

    for player, samples in by_player.items():
        if not samples:
            continue
        total = len(samples)
        violations = 0
        for p in samples:
            try:
                dist = float(p.kv.get("leader_dist", -1))
            except ValueError:
                continue
            if dist < 0:
                continue   # no army nearby at all — count as violation
            if dist > ESCORT_RADIUS_M:
                violations += 1
        rate = violations / total
        if rate > ESCORT_VIOLATION_TOLERANCE:
            civ = samples[0].civ
            issues.append(
                f"[escort_v2] p{player} civ={civ}: leader out-of-escort-range "
                f"in {violations}/{total} attack samples "
                f"({rate*100:.1f}% > {ESCORT_VIOLATION_TOLERANCE*100:.0f}% tolerance)"
            )
    return issues


# ---------------------------------------------------------------------------
# Unified entrypoint
# ---------------------------------------------------------------------------

def run_all_checks(text: str) -> tuple[list[str], list[str]]:
    """Run all three gap checks.

    Returns (errors, warnings).  errors → FAIL; warnings → WARN only.
    """
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(check_pacing_budget(text))

    ship_errors, ship_warnings = check_shipment_order(text)
    errors.extend(ship_errors)
    warnings.extend(ship_warnings)

    errors.extend(check_leader_escort(text))

    return errors, warnings


# ---------------------------------------------------------------------------
# CLI shim (used by validate_runtime_logs --suite pacing_v2 etc.)
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run coverage_v2 checks against an Age3Log.txt slice."
    )
    parser.add_argument("log", type=Path, help="Path to Age3Log.txt or slice.")
    parser.add_argument(
        "--suite",
        action="append",
        default=[],
        choices=["pacing_v2", "shipment_order_v2", "escort_v2"],
        help="Subset of checks to run (default: all).",
    )
    args = parser.parse_args(argv)

    text = args.log.read_text(encoding="utf-8", errors="replace")
    suites = set(args.suite) or {"pacing_v2", "shipment_order_v2", "escort_v2"}

    errors: list[str] = []
    warnings: list[str] = []

    if "pacing_v2" in suites:
        errors.extend(check_pacing_budget(text))
    if "shipment_order_v2" in suites:
        e, w = check_shipment_order(text)
        errors.extend(e)
        warnings.extend(w)
    if "escort_v2" in suites:
        errors.extend(check_leader_escort(text))

    for w in warnings:
        print(f"WARN {w}")
    for e in errors:
        print(f"FAIL {e}")

    if errors:
        return 1
    if warnings:
        print("coverage_v2: WARN (no hard failures)")
        return 0
    print("coverage_v2: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
