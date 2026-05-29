#!/usr/bin/env python3
"""Static validator: ``playstyle_spec.json`` internal consistency.

Locks the *logical implications* between claim fields. These are
invariants the spec currently honors with zero violations — if a future
edit breaks one, that's a real data model bug worth catching at the
static gate before it reaches a runtime test.

Invariants enforced (each tested against all 45 civs):

  I-1  ``expects_forward=True`` ⇒ ``first_military_building=='barracks_or_stable'``

       A "forward" doctrine pushes a forward-base early — by definition
       that means the first military building is a barracks or stable.
       If fmb is a market, dock, etc., the civ is not running a
       forward push and shouldn't claim it.

  I-2  ``expects_naval=True`` ⇔ ``wall_strategy==2`` (CoastalBatteries)

       Coastal Batteries is the *only* doctrine where naval is the
       expected primary axis. Other doctrines may *use* navy
       opportunistically but should not claim naval expectation,
       and Coastal civs must claim naval expectation.

  I-3  ``wall_strategy==5`` (MobileNoWalls) AND ``first_wall_before_ms``
       is set ⇒ value MUST be exactly 720000ms (12 minutes).

       Mobile doctrines are not wall-focused, but the spec uses a
       single "late opportunistic wall" deadline for them so the
       runtime probe still has a meaningful comparison. Drift on
       this value (e.g. someone setting it to 360s) would
       mis-categorise the civ.

  I-4  ``first_dock_before_ms`` is set ⇒ ``expects_naval=True``.

       If we require a dock by deadline N, the doctrine expects a
       naval axis. Without ``expects_naval``, the dock requirement
       is incoherent.

  I-5  ``military_distance_band[0] >= 1.0`` AND
       ``first_military_building=='barracks_or_stable'`` ⇒ ``expects_forward=True``.

       A distance band whose lower bound starts AT the home base or
       beyond means the military is positioned forward. Combined with
       a military fmb (not a trading post), this is by definition a
       forward push and must declare it.

  I-6  ``claims.wall_strategy`` MUST equal ``CALIBRATION[<rev_token>].strategy``.

       The spec field is documentation; the *runtime* wall doctrine is
       driven by ``tools/ai_design/wall_knob_calibration.CALIBRATION``
       (which emits ``game/ai/core/aiWallKnobsByCiv.xs``). When the
       two disagree, the release-readiness site renders one strategy
       in the doctrine card header while the in-game AI builds a
       different one — exactly the Brazil bug caught on 2026-05-27
       (spec said FrontierPalisades, runtime built FortressRing).

Run::

    python3 tools/validation/validate_spec_internal_consistency.py
    python3 tools/validation/validate_spec_internal_consistency.py \\
        --json artifacts/validation/spec_internal_consistency.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SPEC_PATH = REPO_ROOT / "playstyle_spec.json"

MOBILE_NO_WALLS_DEADLINE_MS = 720_000  # design-intentional late-game opportunistic deadline

# Lazy import of CALIBRATION + the site's spec-token → calib-key resolver so the
# I-6 check can lock spec wall_strategy ↔ runtime calibration strategy.
sys.path.insert(0, str(REPO_ROOT))


def _load_calibration_and_resolver():
    """Return (CALIBRATION, _spec_token_to_calib_key) or (None, None) on import error."""
    try:
        from tools.ai_design.wall_knob_calibration import CALIBRATION  # type: ignore
        from tools.validation.build_release_readiness_site import (
            _spec_token_to_calib_key,  # type: ignore
        )
        return CALIBRATION, _spec_token_to_calib_key
    except Exception:
        return None, None


def check_i1_forward_implies_barracks(civs: dict) -> list[dict]:
    """expects_forward=True ⇒ first_military_building=='barracks_or_stable'."""
    out = []
    for tok, civ in civs.items():
        c = civ.get("claims") or {}
        if c.get("expects_forward") is True:
            fmb = c.get("first_military_building")
            if fmb != "barracks_or_stable":
                out.append({"civ": tok, "fmb": fmb,
                            "msg": "expects_forward=True but fmb is not barracks_or_stable"})
    return out


def check_i2_naval_iff_coastal(civs: dict) -> list[dict]:
    """expects_naval=True ⇔ wall_strategy==2 (CoastalBatteries)."""
    out = []
    for tok, civ in civs.items():
        c = civ.get("claims") or {}
        naval = c.get("expects_naval") is True
        coastal = c.get("wall_strategy") == 2
        if naval and not coastal:
            out.append({"civ": tok, "wall_strategy": c.get("wall_strategy"),
                        "msg": "expects_naval=True but wall_strategy != 2 (CoastalBatteries)"})
        elif coastal and not naval:
            out.append({"civ": tok, "expects_naval": c.get("expects_naval"),
                        "msg": "wall_strategy=2 (CoastalBatteries) but expects_naval is not True"})
    return out


def check_i3_mobile_wall_deadline_value(civs: dict) -> list[dict]:
    """wall_strategy==5 with first_wall_before_ms set ⇒ value == 720000ms."""
    out = []
    for tok, civ in civs.items():
        c = civ.get("claims") or {}
        if c.get("wall_strategy") != 5:
            continue
        v = c.get("first_wall_before_ms")
        if v is not None and v != MOBILE_NO_WALLS_DEADLINE_MS:
            out.append({"civ": tok, "value_ms": v,
                        "expected_ms": MOBILE_NO_WALLS_DEADLINE_MS,
                        "msg": f"ws=5 (MobileNoWalls) wall deadline must be {MOBILE_NO_WALLS_DEADLINE_MS}ms (got {v}ms)"})
    return out


def check_i4_dock_deadline_implies_naval(civs: dict) -> list[dict]:
    """first_dock_before_ms set ⇒ expects_naval=True."""
    out = []
    for tok, civ in civs.items():
        c = civ.get("claims") or {}
        if c.get("first_dock_before_ms") is not None and c.get("expects_naval") is not True:
            out.append({"civ": tok, "first_dock_before_ms": c.get("first_dock_before_ms"),
                        "expects_naval": c.get("expects_naval"),
                        "msg": "first_dock_before_ms set but expects_naval is not True"})
    return out


def check_i5_high_band_barracks_implies_forward(civs: dict) -> list[dict]:
    """military_distance_band[0]>=1.0 AND fmb=='barracks_or_stable' ⇒ expects_forward=True."""
    out = []
    for tok, civ in civs.items():
        c = civ.get("claims") or {}
        band = c.get("military_distance_band")
        if not band or len(band) < 1:
            continue
        if band[0] < 1.0:
            continue
        if c.get("first_military_building") != "barracks_or_stable":
            continue
        if c.get("expects_forward") is not True:
            out.append({"civ": tok, "band": band,
                        "fmb": c.get("first_military_building"),
                        "expects_forward": c.get("expects_forward"),
                        "msg": "military_distance_band[0]>=1.0 + fmb=barracks_or_stable but expects_forward not True"})
    return out


def check_i6_spec_ws_matches_calibration(civs: dict) -> list[dict]:
    """spec claims.wall_strategy == CALIBRATION[<rev_token>].strategy.

    The XS runtime wall doctrine is driven by CALIBRATION (emits
    aiWallKnobsByCiv.xs). The spec field is documentation surfaced on
    the release-readiness site and in playstyle reports — if it
    diverges, users see one strategy in the doctrine card but the AI
    builds a different one in-game.
    """
    out: list[dict] = []
    CALIBRATION, resolver = _load_calibration_and_resolver()
    if not CALIBRATION or not resolver:
        # Calibration table can't be loaded — surface as a single
        # violation so the validator fails loud rather than passing
        # vacuously.
        return [{"civ": "(harness)",
                 "msg": "could not import CALIBRATION or resolver"}]
    for tok, civ in civs.items():
        c = civ.get("claims") or {}
        spec_ws = c.get("wall_strategy")
        if spec_ws is None:
            continue  # civs without claims.wall_strategy are exempt
        calib_key = resolver(tok)
        if not calib_key or calib_key not in CALIBRATION:
            out.append({"civ": tok, "spec_ws": spec_ws, "calib_key": calib_key,
                        "msg": f"no CALIBRATION entry resolved for spec token "
                               f"(resolved key={calib_key!r})"})
            continue
        calib_ws = CALIBRATION[calib_key].get("strategy")
        if spec_ws != calib_ws:
            out.append({"civ": tok, "spec_ws": spec_ws, "calib_ws": calib_ws,
                        "calib_key": calib_key,
                        "msg": f"spec wall_strategy={spec_ws} but calibration "
                               f"strategy={calib_ws} (calib is runtime source of truth)"})
    return out


INVARIANTS = [
    ("I-1", "expects_forward=True ⇒ fmb=='barracks_or_stable'",
     check_i1_forward_implies_barracks),
    ("I-2", "expects_naval=True ⇔ wall_strategy==2 (CoastalBatteries)",
     check_i2_naval_iff_coastal),
    ("I-3", "ws=5 + first_wall_before_ms set ⇒ value == 720000ms",
     check_i3_mobile_wall_deadline_value),
    ("I-4", "first_dock_before_ms set ⇒ expects_naval=True",
     check_i4_dock_deadline_implies_naval),
    ("I-5", "band[0]>=1.0 + barracks_or_stable ⇒ expects_forward=True",
     check_i5_high_band_barracks_implies_forward),
    ("I-6", "spec claims.wall_strategy == CALIBRATION[rev_token].strategy",
     check_i6_spec_ws_matches_calibration),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=SPEC_PATH)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("SPEC INTERNAL CONSISTENCY")
    print("=" * 60)

    if not args.spec.exists():
        print(f"  ERROR: spec file not found: {args.spec}")
        return 2

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    civs = spec.get("civs", {}) or {}
    print(f"  Loaded {len(civs)} civs from {args.spec.name}\n")

    all_results = {}
    total_violations = 0
    for code, desc, fn in INVARIANTS:
        violations = fn(civs)
        all_results[code] = {"desc": desc, "violations": violations,
                             "passed": not violations}
        total_violations += len(violations)
        status = "PASS" if not violations else f"FAIL ({len(violations)})"
        print(f"  {code}  {status:10s}  {desc}")
        for v in violations[:6]:
            print(f"          - {v['civ']}: {v['msg']}")
        if len(violations) > 6:
            print(f"          ... +{len(violations)-6} more")

    print()
    overall_pass = total_violations == 0
    if overall_pass:
        print(f"PASS — all {len(INVARIANTS)} spec invariants honored across "
              f"{len(civs)} civs")
    else:
        print(f"FAIL — {total_violations} violations across "
              f"{sum(1 for r in all_results.values() if not r['passed'])} invariants")

    report = {
        "invariants": all_results,
        "total_violations": total_violations,
        "civ_count": len(civs),
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
