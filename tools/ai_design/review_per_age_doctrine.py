#!/usr/bin/env python3
"""review_per_age_doctrine.py — cross-check & correct spec per_age vs leader files.

The authoritative per-age doctrine is each leader file's bt* biases
(btOffenseDefense on a -1..+1 scale; btBiasInf/Cav/Art relative weights),
overlaid age-by-age (values persist until re-set). This:
  1. parses init (Age1) + cAge2/3/4/5 rule blocks for each dedicated leader,
  2. derives authoritative posture (sign of btOffenseDefense) + comp lean,
  3. reports every mismatch vs playstyle_spec.json per_age,
  4. (with --fix) rewrites per_age posture + comp bands from the real doctrine.
"""
from __future__ import annotations
import argparse, importlib.util, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LDIR = REPO / "game" / "ai" / "leaders"
SPEC = REPO / "playstyle_spec.json"

# engine civ token -> leader file basename (from aiLoaderStandard dispatch)
CIV_TO_LEADER = {
    "French": "bourbon", "ANWNapoleonicFrance": "napoleon", "British": "wellington",
    "Germans": "frederick", "Russians": "catherine", "Spanish": "isabella",
    "Ottomans": "suleiman", "Portuguese": "henry", "Dutch": "maurice",
    "DEAmericans": "washington", "DEMexicans": "hidalgo", "DEItalians": "garibaldi",
    "DEMaltese": "valette", "XPAztec": "montezuma", "Chinese": "kangxi",
    "DEEthiopians": "menelik", "XPIroquois": "hiawatha", "DEHausa": "usman",
    "DEInca": "pachacuti", "Indians": "shivaji", "Japanese": "tokugawa",
    "XPSioux": "crazy_horse", "DESwedish": "gustavus",
}
BT = ["btOffenseDefense", "btBiasInf", "btBiasCav", "btBiasArt"]


def _spec_to_calib_map() -> dict:
    p = REPO / "tools" / "validation" / "build_release_readiness_site.py"
    s = importlib.util.spec_from_file_location("brrs", p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return dict(getattr(m, "_SPEC_TO_CALIB_KEY", {}))


def _grab_assigns(block: str) -> dict:
    out = {}
    for bt in BT:
        m = re.search(rf"{bt}\s*=\s*(-?[0-9.]+)\s*;", block)
        if m:
            out[bt] = float(m.group(1))
    return out


def parse_leader(leader: str) -> dict:
    """Return {age: {bt: value}} with carry-forward overlay (ages 1..5)."""
    f = LDIR / f"leader_{leader}.xs"
    if not f.is_file():
        return {}
    txt = f.read_text(encoding="utf-8", errors="replace")
    # Age 1 = init function body
    im = re.search(r"void initLeader\w+\(void\)\s*\{", txt)
    init_block = ""
    if im:
        init_block = txt[im.end(): txt.find("\nvoid ", im.end()) if "\nvoid " in txt[im.end():] else len(txt)]
    per = {1: _grab_assigns(init_block)}
    # Ages 2..5: scan each `kbGetAge() == cAgeN` (or >=) block
    for age in (2, 3, 4, 5):
        per[age] = {}
        for m in re.finditer(rf"kbGetAge\(\)\s*(==|>=)\s*cAge{age}\b", txt):
            # capture ~25 lines / until the if-block closes
            seg = txt[m.end(): m.end() + 900]
            seg = seg.split("\n   }")[0]  # rule-indent close
            per[age].update(_grab_assigns(seg))
    # overlay carry-forward
    running = {}
    eff = {}
    for age in (1, 2, 3, 4, 5):
        running.update(per.get(age, {}))
        eff[age] = dict(running)
    return eff


def parse_revolution() -> dict:
    """Return {ANWtoken: {bt: value}} from the shared revolution-commander
    file's per-civ rvltName branches (flat posture across ages)."""
    f = LDIR / "leader_revolution_commanders.xs"
    if not f.is_file():
        return {}
    txt = f.read_text(encoding="utf-8", errors="replace")
    out = {}
    parts = re.split(r'(?:else\s+)?if\s*\(\s*rvltName\s*==\s*"', txt)
    for seg in parts[1:]:
        m = re.match(r'(ANW\w+)"', seg)
        if not m:
            continue
        block = seg.split("\n   else if")[0][:1200]
        out[m.group(1)] = _grab_assigns(block)
    return out


def posture(off: float | None) -> str:
    if off is None:
        return "unknown"
    return "offensive" if off > 0.05 else ("defensive" if off < -0.05 else "balanced")


def comp_bands(eff_age: dict) -> dict:
    inf = max(0.0, eff_age.get("btBiasInf", 0.0))
    cav = max(0.0, eff_age.get("btBiasCav", 0.0))
    art = max(0.0, eff_age.get("btBiasArt", 0.0))
    tot = inf + cav + art
    if tot <= 0:
        return {"inf": [0.40, 0.65], "cav": [0.20, 0.45], "art": [0.05, 0.20]}
    out = {}
    for name, w in (("inf", inf), ("cav", cav), ("art", art)):
        frac = w / tot
        out[name] = [round(max(0.0, frac - 0.12), 2), round(min(1.0, frac + 0.18), 2)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="rewrite per_age from leader files")
    a = ap.parse_args()

    spec = json.loads(SPEC.read_text())
    civs = spec.get("civs", spec)
    key_map = _spec_to_calib_map()
    rev = parse_revolution()
    mismatches = 0; checked = 0; rev_checked = 0

    for token, civ in civs.items():
        ck = key_map.get(token)
        leader = CIV_TO_LEADER.get(ck)
        claims = civ.get("claims", {})
        pa = claims.get("per_age", {})
        if not leader:
            # revolution civ — flat per-civ posture from the shared commander file
            rb = rev.get(ck or "")
            if not rb:
                continue
            rev_checked += 1
            eff = {2: rb, 3: rb, 4: rb}  # flat across ages
        else:
            eff = parse_leader(leader)
            if not eff:
                continue
            checked += 1
        src = f"leader_{leader}.xs bt biases" if leader else "leader_revolution_commanders.xs (per-civ)"
        for age in (2, 3, 4):
            true_post = posture(eff.get(age, {}).get("btOffenseDefense"))
            spec_post = pa.get(str(age), {}).get("posture")
            if true_post in ("offensive", "defensive") and spec_post != true_post:
                mismatches += 1
                print(f"  MISMATCH {token:32s} ({ck}->{leader or 'rev'}) Age{age}: "
                      f"spec={spec_post} -> btOff={eff[age].get('btOffenseDefense')} = {true_post}")
            if a.fix and str(age) in pa:
                if true_post in ("offensive", "defensive"):
                    pa[str(age)]["posture"] = true_post
                if any(k in eff.get(age, {}) for k in ("btBiasInf", "btBiasCav", "btBiasArt")):
                    pa[str(age)]["comp"] = comp_bands(eff.get(age, {}))
                pa[str(age)]["_source"] = src

    print(f"\nchecked {checked} dedicated-leader + {rev_checked} revolution civs;"
          f" {mismatches} posture mismatches.")
    if a.fix:
        SPEC.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
        print("spec per_age corrected from leader files (posture + comp bands).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
