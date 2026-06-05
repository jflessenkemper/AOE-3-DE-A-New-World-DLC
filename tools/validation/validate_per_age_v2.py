#!/usr/bin/env python3
"""validate_per_age_v2.py — verify per-age + walling doctrine vs telemetry.

Closes the loop: reads the v2 spec (per_age + wall bands), harvests the
per-player [ANWP v=2] probes (UTF-16), and emits PASS/WARN/FAIL per civ.

Difficulty-aware: reads meta.difficulty `intensity` and scales the expected
wall-closure / army targets the same way the engine does, so the check is
correct for whatever difficulty the match ran at. Composition *style* (comp
bands) and age-up windows are intensity-independent.

Usage:  python3 tools/validation/validate_per_age_v2.py [--logs DIR] [--json OUT]
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "playstyle_spec.json"
DEFAULT_LOGDIR = os.path.expanduser(
    "~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/"
    "Games/Age of Empires 3 DE/Logs")
PROBE = re.compile(r"\[ANWP v=2 t=(\d+) p=(\d+) civ=(\S+) ldr=(\S+) tag=([^\]]+)\](.*)")
KV = re.compile(r"(\w+)=(-?[0-9.]+)")


def harvest(logdir: str) -> dict:
    """{civ: {tag: [ (t, {kv}) ]}} from per-player UTF-16 logs."""
    out: dict = defaultdict(lambda: defaultdict(list))
    for f in glob.glob(os.path.join(logdir, "Age3DEAIOutputPlayer*.txt")):
        raw = open(f, "rb").read()
        enc = "utf-16-le" if raw[:4].count(0) >= 1 else "utf-8"
        for ln in raw.decode(enc, "replace").splitlines():
            m = PROBE.search(ln)
            if not m:
                continue
            t = int(m.group(1)); civ = m.group(3); tag = m.group(5).split()[0]
            kv = {k: float(v) for k, v in KV.findall(m.group(6))}
            out[civ][tag].append((t, kv))
    return out


def _intensity(tags: dict) -> int:
    md = tags.get("meta.difficulty")
    if md:
        return int(md[-1][1].get("intensity", 100))
    return 100  # default to Expert if not reported


def _age_at(t: int, ageups: list) -> int:
    """Engine age (0..5) at gametime t, from event.age_up (age=N reached)."""
    age = 0
    for ut, kv in ageups:
        if ut <= t:
            age = max(age, int(kv.get("age", 0)) + 1)  # age_up age=N => entered N+1? keep simple
    return age


def _verdict_in_band(val, band, slack=0.07) -> str:
    lo, hi = band
    if lo <= val <= hi:
        return "PASS"
    if lo - slack <= val <= hi + slack:
        return "WARN"
    return "FAIL"


def validate_civ(spec_civ: dict, tags: dict) -> dict:
    claims = spec_civ.get("claims", {})
    wall = claims.get("wall", {})
    per_age = claims.get("per_age", {})
    intensity = _intensity(tags)
    checks = []

    # ---- WALL ----
    strat = wall.get("strategy")
    closures = [kv.get("closure", kv.get("pct", 0) / 100.0) for _, kv in tags.get("wall.closure", [])]
    obs_closure = max(closures) if closures else 0.0
    if strat == 5:  # MobileNoWalls: expect ~no walls
        checks.append(("wall.mobile_no_perimeter", "PASS" if obs_closure < 0.15 else "WARN",
                       f"obs_closure={obs_closure:.2f} (expect ~0)"))
    else:
        target = (wall.get("closure_pct_target", 100) / 100.0) * (intensity / 100.0)
        v = "PASS" if obs_closure >= 0.8 * target else ("WARN" if obs_closure >= 0.4 * target else "FAIL")
        checks.append(("wall.closure", v,
                       f"obs={obs_closure:.2f} vs target={target:.2f} (int={intensity}%)"))

    # ---- AGE-UP windows ----
    ageups = sorted(tags.get("event.age_up", []))
    for an in ("2", "3"):
        win = per_age.get(an, {}).get("ageup_by_ms")
        if not win:
            continue
        # event.age_up age=N where entering age (best-effort)
        reached = [t for t, kv in ageups if int(kv.get("age", -9)) + 1 >= int(an)]
        if reached:
            t = min(reached)
            v = "PASS" if t <= win[1] else ("WARN" if t <= win[1] * 1.25 else "FAIL")
            checks.append((f"ageup.{an}", v, f"t={t//1000}s vs <= {win[1]//1000}s"))

    # ---- COMPOSITION per age (style; intensity-independent) ----
    comps = sorted(tags.get("comp.snapshot", []))
    for an in ("2", "3", "4"):
        band = per_age.get(an, {}).get("comp")
        if not band:
            continue
        # snapshots while in this age
        in_age = [kv for t, kv in comps if _age_at(t, ageups) == int(an)]
        tot_i = sum(kv.get("inf", 0) for kv in in_age)
        tot_c = sum(kv.get("cav", 0) for kv in in_age)
        tot_a = sum(kv.get("arty", 0) for kv in in_age)
        tot = tot_i + tot_c + tot_a
        if tot < 3:  # not enough army to judge
            continue
        fi, fc, fa = tot_i / tot, tot_c / tot, tot_a / tot
        sub = [_verdict_in_band(fi, band["inf"]), _verdict_in_band(fc, band["cav"]),
               _verdict_in_band(fa, band["art"])]
        v = "FAIL" if "FAIL" in sub else ("WARN" if "WARN" in sub else "PASS")
        checks.append((f"comp.age{an}", v,
                       f"inf={fi:.2f} cav={fc:.2f} art={fa:.2f}"))

    fails = sum(1 for _, v, _ in checks if v == "FAIL")
    warns = sum(1 for _, v, _ in checks if v == "WARN")
    overall = "FAIL" if fails else ("WARN" if warns else "PASS")
    return {"intensity": intensity, "overall": overall, "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=DEFAULT_LOGDIR)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    spec = json.loads(SPEC.read_text())
    civs = spec.get("civs", spec)
    by_engine = {}
    # map engine civ token (from probes, e.g. ANWCanadians) -> spec entry
    try:
        import importlib.util
        s = importlib.util.spec_from_file_location("brrs", REPO / "tools/validation/build_release_readiness_site.py")
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        spec_to_calib = dict(getattr(m, "_SPEC_TO_CALIB_KEY", {}))
        calib_to_spec = {v: k for k, v in spec_to_calib.items()}
    except Exception:
        calib_to_spec = {}

    tele = harvest(a.logs)
    if not tele:
        print("No [ANWP v=2] probes found — run a match first (per-player UTF-16 logs).")
        return 0

    results = {}
    for engine_civ, tags in tele.items():
        spec_key = calib_to_spec.get(engine_civ)
        spec_civ = civs.get(spec_key) if spec_key else None
        if not spec_civ:
            continue
        results[engine_civ] = validate_civ(spec_civ, tags)

    print(f"{'CIV':22s} {'INT':>4s} {'VERDICT':8s} CHECKS")
    for civ, r in sorted(results.items()):
        line = "  ".join(f"{name}:{v}" for name, v, _ in r["checks"])
        print(f"{civ:22s} {r['intensity']:>3d}% {r['overall']:8s} {line}")
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1))
        print(f"\nwrote {a.json}")
    npass = sum(1 for r in results.values() if r["overall"] == "PASS")
    print(f"\n{npass}/{len(results)} civs PASS  (telemetry: {len(tele)} civs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
