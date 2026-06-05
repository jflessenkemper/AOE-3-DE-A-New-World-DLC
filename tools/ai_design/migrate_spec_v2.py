#!/usr/bin/env python3
"""migrate_spec_v2.py — add testable per-age + walling doctrine to every civ.

Adds to each civ's `claims`:
  * wall      — REAL designed values from wall_knob_calibration.CALIBRATION
  * per_age   — Expert-level bands (intent-seeded; farm-calibrated)
These are difficulty-aware: the validator scales bands by the meta.difficulty
`intensity` the engine reports. See docs/SPEC_V2_SCHEMA.md.

Idempotent. Backs up the spec before writing.
"""
from __future__ import annotations
import importlib.util, json, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "playstyle_spec.json"

# strategy enum -> name (for readability + chokepoint detection)
MOBILE = 5
CHOKE = 1


def _load_calibration() -> dict:
    p = REPO / "tools" / "ai_design" / "wall_knob_calibration.py"
    spec = importlib.util.spec_from_file_location("wkc", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return dict(getattr(m, "CALIBRATION", {}))


def _spec_to_calib_map() -> dict:
    p = REPO / "tools" / "validation" / "build_release_readiness_site.py"
    spec = importlib.util.spec_from_file_location("brrs", p)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
        return dict(getattr(m, "_SPEC_TO_CALIB_KEY", {}))
    except Exception as e:
        print(f"  [warn] could not import key map: {e}", file=sys.stderr)
        return {}


def build_wall(kn: dict | None) -> dict:
    if not kn:
        return {}
    strat = kn.get("strategy", 0)
    if strat == MOBILE:
        return {"strategy": MOBILE, "closure_pct_target": 0, "trigger_age": 0,
                "tier_by_age": {}, "gate_count": 0, "towers_every": 0,
                "chokepoint": False, "note": "MobileNoWalls — outpost screen, no perimeter"}
    age2 = "stone" if kn.get("age2stone") else "palisade"
    return {
        "strategy": strat,
        "closure_pct_target": kn.get("closure_pct", 100),
        "trigger_age": kn.get("trigger_age", 2),
        "tier_by_age": {"2": age2, "3": "stone", "4": "fortified"},
        "gate_count": kn.get("gates", 3),
        "towers_every": kn.get("towers", 0),
        "chokepoint": strat == CHOKE or kn.get("secondary") == CHOKE,
        "radius": kn.get("radius", 0),
    }


def build_per_age(claims: dict) -> dict:
    """Intent-seeded Expert bands from existing directional claims. Provisional."""
    cav, inf, art = claims.get("expects_cavalry"), claims.get("expects_infantry"), claims.get("expects_artillery")
    fwd = claims.get("expects_forward")
    mdist = claims.get("military_distance_band", [0.8, 1.2])
    offensive = bool(fwd) or (isinstance(mdist, list) and len(mdist) == 2 and mdist[1] >= 1.2)
    # rusher vs boomer tempo from first_barracks timing
    fb = claims.get("first_barracks_before_ms", 480000)
    rush = fb <= 360000

    def comp(base_inf, base_cav, base_art):
        # nudge toward declared leans (+0.15 on the led class)
        i = list(base_inf); c = list(base_cav); a = list(base_art)
        if cav: c = [min(0.95, c[0] + 0.15), min(1.0, c[1] + 0.15)]
        if inf: i = [min(0.95, i[0] + 0.10), min(1.0, i[1] + 0.10)]
        if art: a = [min(0.6, a[0] + 0.10), min(0.7, a[1] + 0.10)]
        return {"inf": [round(i[0], 2), round(i[1], 2)],
                "cav": [round(c[0], 2), round(c[1], 2)],
                "art": [round(a[0], 2), round(a[1], 2)]}

    a2 = [240000, 420000] if rush else [360000, 540000]
    a3 = [540000, 840000] if rush else [660000, 960000]
    a4 = [840000, 1200000] if rush else [1020000, 1440000]
    a5 = [1200000, 1680000] if rush else [1440000, 1920000]
    pres = "offensive" if offensive else "defensive"
    return {
        # Age 1 (Discovery): eco/scout phase — minimal military, so posture only.
        "1": {"comp": comp([0.50, 0.80], [0.10, 0.35], [0.00, 0.05]),
              "posture": "offensive" if (offensive and rush) else "defensive",
              "note": "Discovery — economy / scouting"},
        "2": {"ageup_by_ms": a2, "comp": comp([0.45, 0.70], [0.15, 0.40], [0.00, 0.10]),
              "posture": "offensive" if (offensive and rush) else "defensive"},
        "3": {"ageup_by_ms": a3, "comp": comp([0.40, 0.62], [0.20, 0.45], [0.05, 0.22]),
              "posture": pres},
        "4": {"ageup_by_ms": a4, "comp": comp([0.38, 0.60], [0.20, 0.45], [0.10, 0.28]),
              "posture": pres},
        "5": {"ageup_by_ms": a5, "comp": comp([0.35, 0.58], [0.20, 0.45], [0.12, 0.32]),
              "posture": pres},
    }


def main() -> int:
    spec = json.loads(SPEC.read_text())
    civs = spec.get("civs", spec)
    calib = _load_calibration()
    key_map = _spec_to_calib_map()
    shutil.copy2(SPEC, SPEC.with_suffix(".json.v1bak"))

    wall_real = wall_missing = 0
    for token, civ in civs.items():
        claims = civ.setdefault("claims", {})
        ck = key_map.get(token)
        kn = calib.get(ck) if ck else None
        if kn:
            claims["wall"] = build_wall(kn); wall_real += 1
        else:
            wall_missing += 1
        claims["per_age"] = build_per_age(claims)
        claims["_calibration"] = "wall=real(knobs); per_age=intent-seeded → refine via sim-farm"

    if isinstance(spec, dict):
        spec["_spec_version"] = 2
        spec["_difficulty_model"] = ("bands are Expert-level; validator scales by "
                                     "meta.difficulty intensity (Sandbox25/Easy45/"
                                     "Moderate65/Hard85/Expert100)")
    SPEC.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    print(f"migrated {len(civs)} civs: wall(real)={wall_real} wall(missing-calib)={wall_missing}")
    print(f"backup: {SPEC.with_suffix('.json.v1bak').name}")
    return 0 if wall_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
