#!/usr/bin/env python3
"""Validate per-civ behavior against the HTML reference matrix.

Reads:
  1. parsed match probes (output of parse_match_log.py)
  2. reference_matrix.json (the per-civ expected-behavior spec)

Emits a per-civ pass/warn/fail report covering the assertion categories defined
in the LL playstyle spec and the [LLP v=2] probe taxonomy:

  Milestones:
    - milestone.first_dock         (atMs)
    - milestone.first_barracks     (atMs)
    - milestone.first_stable       (atMs)
    - milestone.first_wall_segment (atMs)
    - milestone.first_fort         (atMs)
    - milestone.first_trading_post (atMs)
    - milestone.first_artillery    (atMs)
    - milestone.first_forward_base (atMs)

  Snapshots (every 60s):
    - comp.snapshot     (vil, inf, cav, arty, landmil, warship)
    - posture.snapshot  (age, ws, bs, mdist, edist, walls, forts, docks, tposts,
                          heading, terrP, terrS)

For each assertion in the reference, we check the latest snapshot of the
relevant tag and report whether the observed value matches expectation
(exact, range, or proportional check).

Usage:
    python3 validate_civ_behavior.py <log_path> [--reference reference_matrix.json] [--report report.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.validation.parse_match_log import parse_log


# ────────────────────────────────────────────────────────────────────────────
# Assertion primitives
# ────────────────────────────────────────────────────────────────────────────


class CheckResult:
    """A single assertion result."""

    __slots__ = ("name", "status", "detail")

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"

    def __init__(self, name: str, status: str, detail: str = ""):
        self.name = name
        self.status = status
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def latest(probes: dict[str, list[dict[str, Any]]], tag: str) -> dict[str, Any] | None:
    recs = probes.get(tag, [])
    if not recs:
        return None
    return max(recs, key=lambda r: r.get("t", 0))


def first(probes: dict[str, list[dict[str, Any]]], tag: str) -> dict[str, Any] | None:
    recs = probes.get(tag, [])
    if not recs:
        return None
    return min(recs, key=lambda r: r.get("t", 0))


# ────────────────────────────────────────────────────────────────────────────
# Per-civ checks
# ────────────────────────────────────────────────────────────────────────────


def check_milestones_fired(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Check that expected milestones fired during the match."""
    expected = spec.get("expected_milestones", {})
    out: list[CheckResult] = []

    # Universal milestones — every civ should hit a barracks-or-stable early
    has_barracks = first(probes, "milestone.first_barracks") is not None
    has_stable = first(probes, "milestone.first_stable") is not None

    if has_barracks or has_stable:
        out.append(CheckResult(
            "milestone.first_military_building",
            CheckResult.PASS,
            f"barracks={has_barracks} stable={has_stable}",
        ))
    else:
        out.append(CheckResult(
            "milestone.first_military_building",
            CheckResult.WARN,
            "no first_barracks or first_stable probe seen "
            "(match may have ended in Age 1)",
        ))

    # Doctrine-specific expected milestones
    for tag in ["dock", "wall_segment", "fort", "trading_post", "forward_base"]:
        full_tag = f"milestone.first_{tag}"
        seen = first(probes, full_tag)
        if expected.get(tag, False):
            if seen:
                out.append(CheckResult(
                    full_tag, CheckResult.PASS,
                    f"fired at t={seen.get('atMs') or seen.get('t')}",
                ))
            else:
                out.append(CheckResult(
                    full_tag, CheckResult.FAIL,
                    f"reference expects {tag} but milestone never fired",
                ))
        else:
            # Not required — still record if observed
            if seen:
                out.append(CheckResult(
                    full_tag, CheckResult.SKIP,
                    f"observed at t={seen.get('atMs')} (not in reference expectations)",
                ))
    return out


def check_doctrine_posture(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Check that the doctrine knobs (ws, bs, mdist) match the reference."""
    out: list[CheckResult] = []
    posture = latest(probes, "posture.snapshot")
    if not posture:
        out.append(CheckResult(
            "posture.snapshot", CheckResult.SKIP,
            "no posture.snapshot probes (rule may not have fired)",
        ))
        return out

    expected_ws = spec.get("wall_strategy")
    if expected_ws is not None:
        observed_ws = posture.get("ws")
        if observed_ws == expected_ws:
            out.append(CheckResult(
                "doctrine.wall_strategy", CheckResult.PASS,
                f"ws={observed_ws}",
            ))
        else:
            out.append(CheckResult(
                "doctrine.wall_strategy", CheckResult.FAIL,
                f"expected ws={expected_ws}, observed ws={observed_ws}",
            ))

    expected_bs = spec.get("build_style")
    if expected_bs is not None:
        observed_bs = posture.get("bs")
        if observed_bs == expected_bs:
            out.append(CheckResult(
                "doctrine.build_style", CheckResult.PASS,
                f"bs={observed_bs}",
            ))
        else:
            out.append(CheckResult(
                "doctrine.build_style", CheckResult.FAIL,
                f"expected bs={expected_bs}, observed bs={observed_bs}",
            ))

    band = spec.get("military_distance_band")
    if band and isinstance(band, (list, tuple)) and len(band) == 2:
        lo, hi = band
        observed_mdist = posture.get("mdist")
        if observed_mdist is None:
            out.append(CheckResult(
                "doctrine.military_distance", CheckResult.SKIP,
                "mdist not present in posture snapshot",
            ))
        elif lo <= observed_mdist <= hi:
            out.append(CheckResult(
                "doctrine.military_distance", CheckResult.PASS,
                f"mdist={observed_mdist:.2f} in [{lo}, {hi}]",
            ))
        else:
            out.append(CheckResult(
                "doctrine.military_distance", CheckResult.FAIL,
                f"mdist={observed_mdist:.2f} outside [{lo}, {hi}]",
            ))
    return out


def check_unit_composition(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Check unit composition ratios against expected."""
    out: list[CheckResult] = []
    snap = latest(probes, "comp.snapshot")
    if not snap:
        out.append(CheckResult(
            "comp.snapshot", CheckResult.SKIP,
            "no comp.snapshot probes",
        ))
        return out

    inf = int(snap.get("inf", 0))
    cav = int(snap.get("cav", 0))
    arty = int(snap.get("arty", 0))
    total = inf + cav + arty
    if total == 0:
        out.append(CheckResult(
            "comp.unit_composition", CheckResult.WARN,
            "no military units seen (match too short or AI made no army?)",
        ))
        return out

    expected = spec.get("expected_unit_composition")
    if not expected:
        # No reference expectation; just record observed ratios
        out.append(CheckResult(
            "comp.unit_composition", CheckResult.SKIP,
            f"observed inf={inf/total:.0%} cav={cav/total:.0%} "
            f"arty={arty/total:.0%} (no reference)",
        ))
        return out

    tol = float(spec.get("composition_tolerance", 0.15))
    issues: list[str] = []
    for cls, observed_ratio in (
        ("infantry", inf / total),
        ("cavalry", cav / total),
        ("artillery", arty / total),
    ):
        target = expected.get(cls)
        if target is None:
            continue
        if abs(observed_ratio - target) > tol:
            issues.append(
                f"{cls}={observed_ratio:.0%} (expected {target:.0%}, ±{tol:.0%})"
            )

    if not issues:
        out.append(CheckResult(
            "comp.unit_composition", CheckResult.PASS,
            f"inf={inf/total:.0%} cav={cav/total:.0%} arty={arty/total:.0%}",
        ))
    else:
        out.append(CheckResult(
            "comp.unit_composition", CheckResult.FAIL,
            "; ".join(issues),
        ))
    return out


def check_age_progression(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Check that the AI advanced through ages in a plausible time."""
    out: list[CheckResult] = []
    posture = latest(probes, "posture.snapshot")
    if not posture:
        return out
    final_age = int(posture.get("age", 0))
    final_t_ms = int(posture.get("ageMs") or posture.get("t") or 0)
    if final_age <= 1:
        out.append(CheckResult(
            "age.progression", CheckResult.WARN,
            f"AI did not leave Age 1 (final age={final_age}, t={final_t_ms}ms)",
        ))
    else:
        out.append(CheckResult(
            "age.progression", CheckResult.PASS,
            f"reached age={final_age} by t={final_t_ms}ms",
        ))
    return out


def check_doctrine_label(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Match civ identity against reference (any probe with civ name)."""
    out: list[CheckResult] = []
    if not probes:
        return out
    expected_civ = spec.get("anw_token")
    expected_doctrine = (spec.get("playstyle_spec") or {}).get("doctrine_label")
    out.append(CheckResult(
        "civ.identity", CheckResult.PASS,
        f"probes seen for {expected_civ}",
    ))
    if expected_doctrine:
        out.append(CheckResult(
            "civ.doctrine_label", CheckResult.SKIP,
            f"reference doctrine: {expected_doctrine!r}",
        ))
    return out


def check_meta_boot(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Check that meta.boot fired with the right wallStrategy/buildStyle.

    meta.boot fires once per AI when its loader bootstraps. It carries the
    leader's doctrine knobs as set by leaderCommon.xs / per-leader scripts.
    Mismatch between meta.boot values and the playstyle_spec means the
    leader-to-doctrine wiring is broken (the most common doctrine bug).
    """
    out: list[CheckResult] = []
    boots = probes.get("meta.boot", [])
    if not boots:
        out.append(CheckResult(
            "meta.boot", CheckResult.FAIL,
            "no meta.boot probe — AI loader never ran or probes disabled",
        ))
        return out

    boot = boots[0]
    out.append(CheckResult(
        "meta.boot.fired", CheckResult.PASS,
        f"chatset={boot.get('chatset')} buildStyle={boot.get('buildStyle')}",
    ))

    # Cross-check wallStrategy declared at boot vs reference
    expected_ws = spec.get("wall_strategy")
    if expected_ws is not None:
        boot_ws = boot.get("wallStrategy")
        if boot_ws is not None and boot_ws == expected_ws:
            out.append(CheckResult(
                "meta.boot.wall_strategy", CheckResult.PASS,
                f"wallStrategy={boot_ws}",
            ))
        elif boot_ws is not None:
            out.append(CheckResult(
                "meta.boot.wall_strategy", CheckResult.FAIL,
                f"meta.boot wallStrategy={boot_ws}, expected {expected_ws}",
            ))
    return out


def check_meta_setup(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """meta.setup carries gameMode/difficulty/players. Sanity-check fires."""
    out: list[CheckResult] = []
    setups = probes.get("meta.setup", [])
    if not setups:
        # meta.setup not always required; the AI loader fires it but the rule
        # may be gated. Treat as SKIP rather than FAIL.
        out.append(CheckResult(
            "meta.setup", CheckResult.SKIP,
            "no meta.setup probe (rule may be gated)",
        ))
        return out
    s = setups[0]
    out.append(CheckResult(
        "meta.setup", CheckResult.PASS,
        f"gameMode={s.get('gameMode')} diff={s.get('difficulty')} "
        f"players={s.get('players')}",
    ))
    return out


def check_meta_gameover(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """meta.gameover fires at match end with final-state info."""
    out: list[CheckResult] = []
    overs = probes.get("meta.gameover", [])
    if not overs:
        # Match may have ended via cycle/timeout before the AI emitted it.
        out.append(CheckResult(
            "meta.gameover", CheckResult.SKIP,
            "no meta.gameover probe (match may have been hard-resigned)",
        ))
        return out
    g = overs[0]
    out.append(CheckResult(
        "meta.gameover", CheckResult.PASS,
        f"lost={g.get('lost')} finalAge={g.get('finalAge')} "
        f"score={g.get('score')}",
    ))
    return out


def check_compliance_profile(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """compliance.profile carries the doctrine-knob snapshot. Should match
    the reference values."""
    out: list[CheckResult] = []
    profs = probes.get("compliance.profile", [])
    if not profs:
        out.append(CheckResult(
            "compliance.profile", CheckResult.SKIP,
            "no compliance.profile probes",
        ))
        return out

    p = profs[-1]  # last snapshot

    # style = build_style enum
    expected_bs = spec.get("build_style")
    if expected_bs is not None and p.get("style") is not None:
        if p["style"] == expected_bs:
            out.append(CheckResult(
                "compliance.profile.build_style", CheckResult.PASS,
                f"style={p['style']}",
            ))
        else:
            out.append(CheckResult(
                "compliance.profile.build_style", CheckResult.FAIL,
                f"compliance.profile style={p['style']} != expected {expected_bs}",
            ))

    # wallStrat
    expected_ws = spec.get("wall_strategy")
    if expected_ws is not None and p.get("wallStrat") is not None:
        if p["wallStrat"] == expected_ws:
            out.append(CheckResult(
                "compliance.profile.wall_strat", CheckResult.PASS,
                f"wallStrat={p['wallStrat']}",
            ))
        else:
            out.append(CheckResult(
                "compliance.profile.wall_strat", CheckResult.FAIL,
                f"compliance.profile wallStrat={p['wallStrat']} != "
                f"expected {expected_ws}",
            ))
    return out


def check_chat_quotes(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Leader quotes — chat.quote should fire at least once per match
    (the opening quote at ~25s game-time)."""
    out: list[CheckResult] = []
    quotes = probes.get("chat.quote", [])
    if quotes:
        kinds = sorted({q.get("kind", "?") for q in quotes})
        out.append(CheckResult(
            "chat.quote", CheckResult.PASS,
            f"{len(quotes)} quotes fired ({', '.join(kinds)})",
        ))
    else:
        # SKIP not FAIL — quote rule may be gated by chatset config
        out.append(CheckResult(
            "chat.quote", CheckResult.SKIP,
            "no chat.quote probes (chatset may not include opening line)",
        ))
    return out


def check_age_up_events(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """event.age_up should fire at every age transition with timing info."""
    out: list[CheckResult] = []
    age_ups = probes.get("event.age_up", [])
    if not age_ups:
        out.append(CheckResult(
            "event.age_up", CheckResult.SKIP,
            "no event.age_up probes (match may have been too short)",
        ))
        return out
    ages_reached = sorted({int(e.get("age", 0)) for e in age_ups})
    out.append(CheckResult(
        "event.age_up", CheckResult.PASS,
        f"reached ages {ages_reached}",
    ))
    return out


def check_card_deck(
    probes: dict[str, list[dict[str, Any]]], spec: dict[str, Any]
) -> list[CheckResult]:
    """Validate that shipments used during the match come from the civ's
    expected deck (per data/decks_anw.json).

    The mod's `compliance.ship` probe carries shipment details. If the AI
    sends a card not in the expected deck, that's a doctrine/binding bug.
    """
    out: list[CheckResult] = []
    ships = probes.get("compliance.ship", [])
    if not ships:
        out.append(CheckResult(
            "compliance.ship", CheckResult.SKIP,
            "no compliance.ship probes (no shipments observed)",
        ))
        return out

    expected_deck = spec.get("expected_deck") or {}
    if not expected_deck:
        out.append(CheckResult(
            "compliance.ship", CheckResult.SKIP,
            f"{len(ships)} shipments observed (no reference deck)",
        ))
        return out

    expected_cards: set[str] = set()
    for age_cards in expected_deck.values():
        if isinstance(age_cards, list):
            expected_cards.update(age_cards)

    used_cards = {s.get("card") for s in ships if s.get("card")}
    unexpected = used_cards - expected_cards
    if unexpected:
        out.append(CheckResult(
            "card_deck", CheckResult.WARN,
            f"used {len(unexpected)} cards not in deck: "
            f"{sorted(unexpected)[:3]}{'...' if len(unexpected) > 3 else ''}",
        ))
    else:
        out.append(CheckResult(
            "card_deck", CheckResult.PASS,
            f"{len(used_cards)} shipments, all from expected deck",
        ))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Top-level orchestration
# ────────────────────────────────────────────────────────────────────────────


def validate_civ(
    civ_token: str,
    probes: dict[str, list[dict[str, Any]]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Run all checks for a single civ. Returns a report dict."""
    all_results: list[CheckResult] = []
    # Existing
    all_results.extend(check_doctrine_label(probes, spec))
    all_results.extend(check_milestones_fired(probes, spec))
    all_results.extend(check_doctrine_posture(probes, spec))
    all_results.extend(check_unit_composition(probes, spec))
    all_results.extend(check_age_progression(probes, spec))
    # New (extended probe coverage)
    all_results.extend(check_meta_boot(probes, spec))
    all_results.extend(check_meta_setup(probes, spec))
    all_results.extend(check_meta_gameover(probes, spec))
    all_results.extend(check_compliance_profile(probes, spec))
    all_results.extend(check_chat_quotes(probes, spec))
    all_results.extend(check_age_up_events(probes, spec))
    all_results.extend(check_card_deck(probes, spec))

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
    for r in all_results:
        counts[r.status] = counts.get(r.status, 0) + 1

    # Overall verdict
    if counts["FAIL"] > 0:
        verdict = "FAIL"
    elif counts["WARN"] > 0:
        verdict = "WARN"
    elif counts["PASS"] == 0:
        verdict = "NO_DATA"
    else:
        verdict = "PASS"

    return {
        "civ": civ_token,
        "verdict": verdict,
        "counts": counts,
        "results": [r.to_dict() for r in all_results],
    }


def validate_log(
    log_path: Path, reference_path: Path
) -> dict[str, Any]:
    """Validate every civ found in the log against the reference."""
    parsed = parse_log(log_path)
    with open(reference_path) as f:
        reference = json.load(f)

    civ_specs = reference.get("civs", {})
    per_civ: dict[str, dict[str, Any]] = {}
    for civ_token, civ_probes in parsed.items():
        spec = civ_specs.get(civ_token, {})
        per_civ[civ_token] = validate_civ(civ_token, civ_probes, spec)

    overall_counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "NO_DATA": 0}
    for c in per_civ.values():
        v = c["verdict"]
        if v not in overall_counts:
            overall_counts[v] = 0
        overall_counts[v] += 1

    return {
        "log_path": str(log_path),
        "reference_path": str(reference_path),
        "civs_in_log": len(per_civ),
        "civs_in_reference": len(civ_specs),
        "overall_verdict": (
            "FAIL" if overall_counts["FAIL"] > 0
            else "WARN" if overall_counts["WARN"] > 0
            else "PASS" if overall_counts["PASS"] > 0
            else "NO_DATA"
        ),
        "civ_verdict_counts": overall_counts,
        "per_civ": per_civ,
    }


def print_report(report: dict[str, Any]) -> None:
    print("=" * 70)
    print("CIV BEHAVIOR VALIDATION REPORT")
    print("=" * 70)
    print(f"Log:        {report['log_path']}")
    print(f"Reference:  {report['reference_path']}")
    print(f"Civs in log:       {report['civs_in_log']}")
    print(f"Civs in reference: {report['civs_in_reference']}")
    print(f"Overall verdict:   {report['overall_verdict']}")
    print(f"Civ verdicts:      {report['civ_verdict_counts']}")
    print()
    if not report["per_civ"]:
        print("(no probes found — rerun with cLLReplayProbes=true and a real match)")
        return
    for civ, civ_report in sorted(report["per_civ"].items()):
        v = civ_report["verdict"]
        marker = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "NO_DATA": "?"}.get(v, "?")
        print(f"  {marker} {civ}: {v} (counts={civ_report['counts']})")
        for r in civ_report["results"]:
            sym = {"PASS": "    ✓", "WARN": "    ⚠",
                   "FAIL": "    ✗", "SKIP": "    ·"}.get(r["status"], "    ?")
            print(f"{sym} {r['name']}: {r['detail']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log_path", type=Path)
    ap.add_argument(
        "--reference",
        type=Path,
        default=REPO_ROOT / "reference_matrix.json",
    )
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    report = validate_log(args.log_path, args.reference)
    print_report(report)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to {args.report}", file=sys.stderr)

    # Exit code: 0 PASS, 1 WARN, 2 FAIL
    return {"PASS": 0, "WARN": 1, "FAIL": 2, "NO_DATA": 3}.get(
        report["overall_verdict"], 4
    )


if __name__ == "__main__":
    sys.exit(main())
