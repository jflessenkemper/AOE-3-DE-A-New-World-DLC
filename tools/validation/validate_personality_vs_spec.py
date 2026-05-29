#!/usr/bin/env python3
"""Cross-check the personality-channel probe data against playstyle_spec.json.

Why this exists
---------------
AoE3 DE FINAL_RELEASE builds strip the ``aiEcho()`` log channel, so the
``[LLP v=2 ...]`` stream that ``validate_doctrine_compliance.py`` expects
never reaches ``Age3Log.txt``. The personality-uservar channel
(``aiPersonalitySetPlayerUserVar()`` → ``Game/AI/<leader>.personality``)
is the one path that survives FINAL_RELEASE — see
``tools/playtest/probes_from_replay.py`` for the rationale.

What this validator now covers (2026-05-13 extension)
-----------------------------------------------------
The probe pack was extended to carry the milestone-fire timestamps and the
first-military-building enum.  This validator now asserts the FULL set of
six claim dimensions documented in ``playstyle_spec.json``:

    1. ``wall_strategy``              enum 0..5
    2. ``first_military_building``    "dock" / "barracks_or_stable" /
                                      "trading_post_or_market"
    3. ``expects_forward``            bool — forward-base milestone fired
    4. ``first_barracks_before_ms``   milestone fired ≤ claim ms
    5. ``first_wall_before_ms``       milestone fired ≤ claim ms
    6. ``military_distance_band``     gLLMilitaryDistanceMultiplier ∈ band

For ``expects_naval`` / ``expects_treaty`` we treat
``first_military_building == dock`` (naval) and
``first_military_building ∈ {trading_post}`` (treaty) as the operational
evidence; both fold into the first-military-building dimension above so
they don't get double-counted.

Per-claim verdict semantics
---------------------------
For every (civ, claim) pair the validator emits one of:

* ``PASS``           — claim verified by probe data
* ``FAIL``           — probe data contradicts the claim
* ``SKIP_NO_PACK``   — playstyle-pack sentinel absent (probe is from a
                      mod build that predates the 2026-05-13 extension)
* ``SKIP_TOO_SHORT`` — match too short for the claim to be testable
                      (e.g. ``first_barracks_before_ms=420000`` and the
                      match only ran for 60s)

A civ's overall status is ``PASS`` iff every concrete claim is PASS or
skipped, ``FAIL`` if any concrete claim FAILs.

Output
------
- ``artifacts/validation/personality_compliance.md`` (human-readable)
- ``artifacts/validation/personality_compliance.json`` (machine-readable)

Exit codes
----------
0 = every civ either PASSes all claims or had every claim legitimately
    skipped (no probe data / match too short)
1 = at least one civ FAILed at least one claim
2 = no probe data at all (game never wrote personality vars — pipeline
    broken or no match ever ran)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.playtest.probes_from_replay import (  # noqa: E402
    FIRST_MIL_BUILDING_NAMES,
    FIRST_MIL_CLAIM_TO_ENUM,
    PERSONALITY_DIR,
    PersonalityProbe,
    WALL_STRATEGY_NAMES,
    scan_personality_dir,
)

# Civ-label → personality file stem overrides for the cases where the
# spec's civ_label doesn't match `anw` + lowercase-strip:
SPEC_CIV_TO_PERSONALITY = {
    "United States":         "anwusa",
    "Napoleonic France":     "anwnapoleonicfrance",
    "Revolutionary France":  "anwrevfrance",
    "Columbians":            "anwcolumbians",  # spec uses Columbians
    "South Africans":        "anwsouthafricans",
    # 2026-05-13: French Louis XVIII Bourbon is a leader variant of the
    # base ANWFrench civ token, not its own civ — engine writes to
    # anwfrench.personality.  Without this override the validator looks
    # for anwfrenchlouis.personality and flags NO_DATA forever.
    "French Louis":          "anwfrench",
}

# Per-civ minimum match length for milestone claims to be testable.
# A claim of "first barracks by 7 min" is meaningless if the match was 1
# min long — the AI hadn't had time to build anything yet. We skip
# milestone checks whose claim-ms exceeds the actual match-ms.
#
# For expects_forward: forward bases take longer to establish than the
# basic building set, so we require ≥ this many ms of match before
# flagging absence as a failure (the AI may still be running its early
# economy).
FORWARD_BASE_MIN_TESTABLE_MS = 600_000  # 10 min real game time


# ── Per-claim verdict helpers ─────────────────────────────────────────────────
PASS         = "PASS"
FAIL         = "FAIL"
SKIP_NO_PACK = "SKIP_NO_PACK"
SKIP_TOO_SHORT = "SKIP_TOO_SHORT"


def _check_wall_strategy(
    claim: Any, probe: PersonalityProbe,
) -> tuple[str, str]:
    expected = int(claim)
    actual = probe.wall_strategy
    if actual == expected:
        return PASS, ""
    return FAIL, (
        f"expected {WALL_STRATEGY_NAMES.get(expected, '?')}({expected}), "
        f"got {probe.wall_strategy_name}({actual})"
    )


def _check_first_military_building(
    claim: Any, probe: PersonalityProbe,
) -> tuple[str, str]:
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    if probe.first_military_building == 0:
        return FAIL, "AI never built any tracked military building"
    accepted = FIRST_MIL_CLAIM_TO_ENUM.get(str(claim))
    if accepted is None:
        return FAIL, f"unknown spec claim string: {claim!r}"
    if probe.first_military_building in accepted:
        return PASS, ""
    return FAIL, (
        f"expected first military building in {sorted(accepted)} ({claim!r}), "
        f"got {probe.first_military_building_name}"
        f"({probe.first_military_building})"
    )


def _check_expects_forward(
    claim: Any, probe: PersonalityProbe,
) -> tuple[str, str]:
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    want = bool(claim)
    if probe.expects_forward_observed == want:
        return PASS, ""
    if want and probe.match_ms < FORWARD_BASE_MIN_TESTABLE_MS:
        return SKIP_TOO_SHORT, (
            f"match_ms={probe.match_ms} < {FORWARD_BASE_MIN_TESTABLE_MS} "
            "(forward base needs time to establish)"
        )
    return FAIL, (
        f"expected expects_forward={want}, "
        f"got {probe.expects_forward_observed}"
    )


def _check_first_X_before_ms(
    actual_ms: Optional[int],
    claim_ms: Any,
    match_ms: int,
    label: str,
) -> tuple[str, str]:
    """Generic 'first <building> before <ms>' check."""
    try:
        threshold = int(claim_ms)
    except (TypeError, ValueError):
        return FAIL, f"non-int claim value: {claim_ms!r}"
    if actual_ms is None:
        if match_ms < threshold:
            return SKIP_TOO_SHORT, (
                f"match_ms={match_ms} < threshold {threshold} "
                f"(insufficient time to observe first {label})"
            )
        return FAIL, (
            f"AI never built {label} (threshold was {threshold} ms; "
            f"match ran {match_ms} ms)"
        )
    if actual_ms <= threshold:
        return PASS, ""
    return FAIL, f"first {label} at {actual_ms} ms > threshold {threshold} ms"


def _check_first_dock_before_ms(claim, probe):
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    return _check_first_X_before_ms(
        probe.first_dock_ms, claim, probe.match_ms, "dock")


def _check_first_barracks_before_ms(claim, probe):
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    # A barracks-or-stable spec is satisfied by either; treat earliest of
    # the two as the effective time so cavalry-led doctrines that open
    # with stable instead of barracks aren't false-failed.
    # v2 pack: first_stable_ms=0 is a "built-but-unknown-time" sentinel —
    # 0 ≤ any threshold so the claim auto-passes whenever stable was built.
    candidates = [t for t in (probe.first_barracks_ms, probe.first_stable_ms) if t is not None]
    earliest = min(candidates) if candidates else None
    return _check_first_X_before_ms(
        earliest, claim, probe.match_ms, "barracks_or_stable")


def _check_first_wall_before_ms(claim, probe):
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    return _check_first_X_before_ms(
        probe.first_wall_ms, claim, probe.match_ms, "wall_segment")


def _check_military_distance_band(claim, probe):
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    try:
        lo, hi = float(claim[0]), float(claim[1])
    except (TypeError, ValueError, IndexError):
        return FAIL, f"bad band: {claim!r}"
    actual = probe.military_distance
    # 0.0625-step quantisation tolerance: a configured 0.9 may decode as
    # 0.875 or 0.9375.  Pad both ends by half-step to avoid false fails.
    tol = 1.0 / 16.0 / 2.0
    if (lo - tol) <= actual <= (hi + tol):
        return PASS, ""
    return FAIL, (
        f"military_distance={actual:.3f} outside band [{lo}, {hi}] "
        f"(±{tol:.4f} quant tolerance)"
    )


# ── Naval / treaty claims — fold into first_military_building check ──────────
def _check_expects_naval(claim, probe):
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    want = bool(claim)
    is_naval = (probe.first_military_building == 1)  # dock enum
    if is_naval == want:
        return PASS, ""
    return FAIL, (
        f"expected expects_naval={want}, AI's first military building was "
        f"{probe.first_military_building_name} (dock-first ⇒ naval)"
    )


def _check_expects_treaty(claim, probe):
    if not probe.has_playstyle:
        return SKIP_NO_PACK, "playstyle pack absent"
    want = bool(claim)
    is_treaty = (probe.first_military_building == 4)  # trading_post enum
    if is_treaty == want:
        return PASS, ""
    return FAIL, (
        f"expected expects_treaty={want}, AI's first military building was "
        f"{probe.first_military_building_name} (trading_post-first ⇒ treaty)"
    )


# Map claim key → checker function. Anything not in this table is skipped
# silently (claim exists in spec but no validator implemented).
CLAIM_CHECKERS = {
    "wall_strategy":             _check_wall_strategy,
    "first_military_building":   _check_first_military_building,
    "expects_forward":           _check_expects_forward,
    "expects_naval":             _check_expects_naval,
    "expects_treaty":            _check_expects_treaty,
    "first_dock_before_ms":      _check_first_dock_before_ms,
    "first_barracks_before_ms":  _check_first_barracks_before_ms,
    "first_wall_before_ms":      _check_first_wall_before_ms,
    "military_distance_band":    _check_military_distance_band,
}


def spec_civ_to_personality_stem(civ_label: str) -> str:
    """Map a spec ``civ_label`` to the personality-file stem."""
    if civ_label in SPEC_CIV_TO_PERSONALITY:
        return SPEC_CIV_TO_PERSONALITY[civ_label]
    return "anw" + civ_label.lower().replace(" ", "")


def load_spec(spec_path: Path) -> dict[str, Any]:
    return json.loads(spec_path.read_text())


def index_probes_by_leader_key(probes: list[PersonalityProbe]) -> dict[str, PersonalityProbe]:
    """Return the most-recent probe per leader_key (highest match_ms)."""
    by_key: dict[str, PersonalityProbe] = {}
    for p in probes:
        existing = by_key.get(p.leader_key)
        if existing is None or p.match_ms > existing.match_ms:
            by_key[p.leader_key] = p
    return by_key


def evaluate(spec: dict[str, Any],
             probes_by_key: dict[str, PersonalityProbe],
             min_match_ms: int) -> dict[str, Any]:
    """Run the per-claim compliance check across all civs."""
    civs = spec.get("civs", {})
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    claim_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for spec_key, entry in sorted(civs.items()):
        civ_label = entry.get("civ_label", "")
        claims = entry.get("claims", {})
        pstem = spec_civ_to_personality_stem(civ_label)
        probe = probes_by_key.get(pstem)

        row: dict[str, Any] = {
            "spec_key": spec_key,
            "civ_label": civ_label,
            "personality_stem": pstem,
            "claim_results": {},
        }

        if probe is None:
            row.update({
                "status": "NO_DATA",
                "match_ms": None,
                "note": f"no personality data on disk for {pstem}",
            })
            counts["NO_DATA"] += 1
            rows.append(row)
            continue

        row["match_ms"] = probe.match_ms
        row["wall_strategy_actual"] = probe.wall_strategy
        row["wall_strategy_actual_name"] = probe.wall_strategy_name
        row["build_style_actual_name"] = probe.build_style_name
        row["age"] = probe.age
        row["score"] = probe.score
        row["has_playstyle_pack"] = probe.has_playstyle
        if probe.has_playstyle:
            row["first_military_building"] = probe.first_military_building_name
            row["military_distance"] = round(probe.military_distance, 3)
            row["expects_forward_observed"] = probe.expects_forward_observed

        any_fail = False
        any_pass = False
        any_concrete_skip = False
        for claim_key, claim_val in claims.items():
            checker = CLAIM_CHECKERS.get(claim_key)
            if checker is None:
                # Unknown claim type — skip but record so it's visible.
                row["claim_results"][claim_key] = {
                    "verdict": "SKIP_UNSUPPORTED",
                    "note": "validator has no checker for this claim type",
                }
                claim_counts[claim_key]["SKIP_UNSUPPORTED"] += 1
                continue
            verdict, note = checker(claim_val, probe)
            row["claim_results"][claim_key] = {
                "verdict": verdict,
                "expected": claim_val,
                "note": note,
            }
            claim_counts[claim_key][verdict] += 1
            if verdict == FAIL:
                any_fail = True
            elif verdict == PASS:
                any_pass = True
            elif verdict in (SKIP_NO_PACK, SKIP_TOO_SHORT):
                any_concrete_skip = True

        # Real-match threshold: under it, the wall_strategy check still
        # holds (preinit assignment) but milestone claims are unreliable.
        is_preinit_only = probe.match_ms < min_match_ms

        if any_fail:
            status = "FAIL"
        elif any_pass and not is_preinit_only:
            status = "PASS"
        elif any_pass and is_preinit_only:
            status = "PREINIT_PASS"
        elif any_concrete_skip:
            status = "SKIP"
        else:
            status = "EMPTY_CLAIMS"
        row["status"] = status
        counts[status] += 1
        rows.append(row)

    return {
        "schema_version": 2,
        "personality_dir": str(PERSONALITY_DIR),
        "min_real_match_ms": min_match_ms,
        "total_civs": len(rows),
        "counts": dict(counts),
        "per_claim_counts": {k: dict(v) for k, v in claim_counts.items()},
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    out: list[str] = []
    out.append("# Personality-channel vs playstyle_spec.json compliance")
    out.append("")
    out.append(f"- Source: `{report['personality_dir']}`")
    out.append(f"- Civs scored: **{report['total_civs']}**")
    out.append(f"- Real-match threshold: ≥ {report['min_real_match_ms']/1000:.0f}s")
    out.append("")
    out.append("## Roll-up")
    out.append("")
    out.append("| Status | Count |")
    out.append("|---|---|")
    for k in ("PASS", "FAIL", "PREINIT_PASS", "SKIP", "EMPTY_CLAIMS", "NO_DATA"):
        out.append(f"| {k} | {counts.get(k, 0)} |")
    out.append("")
    out.append("## Per-claim verdict roll-up")
    out.append("")
    out.append("| Claim | PASS | FAIL | SKIP_NO_PACK | SKIP_TOO_SHORT | SKIP_UNSUPPORTED |")
    out.append("|---|---|---|---|---|---|")
    for claim_key, vc in sorted(report["per_claim_counts"].items()):
        out.append(
            f"| {claim_key} | {vc.get('PASS', 0)} | {vc.get('FAIL', 0)} "
            f"| {vc.get('SKIP_NO_PACK', 0)} | {vc.get('SKIP_TOO_SHORT', 0)} "
            f"| {vc.get('SKIP_UNSUPPORTED', 0)} |"
        )
    out.append("")
    out.append("## Per-civ verdict")
    out.append("")
    out.append("| Spec key | Status | wall_strat | first_mil | mdist | "
               "expects_fwd | match_ms | Failed claims |")
    out.append("|---|---|---|---|---|---|---|---|")
    for r in report["rows"]:
        failed = [k for k, v in r.get("claim_results", {}).items()
                  if v.get("verdict") == "FAIL"]
        out.append(
            f"| {r['spec_key']} "
            f"| {r['status']} "
            f"| {r.get('wall_strategy_actual_name', '—')} "
            f"| {r.get('first_military_building', '—')} "
            f"| {r.get('military_distance', '—')} "
            f"| {r.get('expects_forward_observed', '—')} "
            f"| {r.get('match_ms') or '—'} "
            f"| {', '.join(failed) if failed else '—'} |"
        )
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path, default=REPO_ROOT / "playstyle_spec.json")
    ap.add_argument("--personality-dir", type=Path, default=PERSONALITY_DIR)
    ap.add_argument("--out-md", type=Path,
        default=REPO_ROOT / "artifacts/validation/personality_compliance.md")
    ap.add_argument("--out-json", type=Path,
        default=REPO_ROOT / "artifacts/validation/personality_compliance.json")
    ap.add_argument("--min-match-ms", type=int, default=60000,
        help="Match length (ms) below which we tag the record as PREINIT_PASS")
    ap.add_argument("--allow-preinit", action="store_true",
        help="Treat PREINIT_PASS as PASS for exit-code purposes")
    args = ap.parse_args()

    if not args.spec.exists():
        print(f"ERROR: spec not found at {args.spec}", file=sys.stderr)
        return 2

    spec = load_spec(args.spec)
    probes = scan_personality_dir(args.personality_dir)
    if not probes:
        print(f"ERROR: no personality probes found in {args.personality_dir}",
              file=sys.stderr)
        return 2

    probes_by_key = index_probes_by_leader_key(probes)
    report = evaluate(spec, probes_by_key, args.min_match_ms)

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(render_markdown(report))
    args.out_json.write_text(json.dumps(report, indent=2))

    counts = report["counts"]
    print(f"PASS={counts.get('PASS',0)}  FAIL={counts.get('FAIL',0)}  "
          f"PREINIT_PASS={counts.get('PREINIT_PASS',0)}  "
          f"SKIP={counts.get('SKIP',0)}  NO_DATA={counts.get('NO_DATA',0)}")
    pcc = report["per_claim_counts"]
    print("Per-claim:")
    for k, v in sorted(pcc.items()):
        print(f"  {k:30s}  PASS={v.get('PASS',0):3d} FAIL={v.get('FAIL',0):3d}"
              f" SKIP_NO_PACK={v.get('SKIP_NO_PACK',0):3d}"
              f" SKIP_TOO_SHORT={v.get('SKIP_TOO_SHORT',0):3d}"
              f" SKIP_UNSUPPORTED={v.get('SKIP_UNSUPPORTED',0):3d}")
    print(f"Reports: {args.out_md}")
    print(f"          {args.out_json}")

    return 0 if counts.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
