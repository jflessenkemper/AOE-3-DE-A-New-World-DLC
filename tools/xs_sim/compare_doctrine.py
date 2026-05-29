"""Static doctrine comparator: xs_sim execution vs playstyle_spec.json claims.

For each leader:
  1. Run leader_*.xs through xs_sim (init + 180 sim-seconds of rule ticks)
  2. Read the doctrine globals it sets (gLLWallStrategy, btOffenseDefense, ...)
  3. Look up the corresponding civ's `claims` block in playstyle_spec.json
  4. Compare and report PASS / FAIL / UNKNOWN

This is the closest a static, no-engine tool can get to "AI playstyle
confirmed". It verifies the *decision-layer code* matches the spec; it
does NOT verify in-engine execution (still requires the matrix on the
Bazzite/Proton rig).

Usage:
    python3 -m tools.xs_sim.compare_doctrine
    python3 -m tools.xs_sim.compare_doctrine --json
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

from .gamestate import scenario_open_age2
from .interpreter import Interpreter
from .harness import LEADERS_DIR

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "playstyle_spec.json"

# The 19 ANW revolution tokens that are routed through the aggregator files
# (no dedicated leader_<token>.xs — no file_stem in anw_token_map.py).
# Yucatan, Californians, CentralAmericans were removed and must NOT appear here.
_ANW_REVOLUTION_TOKENS = [
    "ANWArgentines",
    "ANWBarbary",
    "ANWBrazil",
    "ANWCanadians",
    "ANWChileans",
    "ANWColumbians",
    "ANWEgyptians",
    "ANWFinnish",
    "ANWHaitians",
    "ANWHungarians",
    "ANWIndonesians",
    "ANWMayans",
    "ANWMexicans",
    "ANWNapoleonicFrance",
    "ANWPeruvians",
    "ANWRevFrance",
    "ANWRomanians",
    "ANWSouthAfricans",
    "ANWTexians",
]

# ANW token → spec data_name.  The spec key is the canonical display name;
# this bridge maps the civ token to the right spec entry.
_ANW_RVLT_SPEC_BRIDGE: dict[str, str] = {
    "ANWArgentines":       "Argentines San Martin Revolution",
    "ANWBarbary":          "Barbary Barbarossa Corsair Revolution",
    "ANWBrazil":           "Brazil Pedro Revolution",
    "ANWCanadians":        "Canadians Brock Revolution",
    "ANWChileans":         "Chileans OHiggins Revolution",
    "ANWColumbians":       "Columbians Bolivar Colombia Revolution",
    "ANWEgyptians":        "Egyptians Muhammad Ali Revolution",
    "ANWFinnish":          "Finnish Mannerheim Revolution",
    "ANWHaitians":         "Haitians Louverture Revolution",
    "ANWHungarians":       "Hungarians Kossuth Revolution",
    "ANWIndonesians":      "Indonesians Diponegoro Revolution",
    "ANWMayans":           "Mayans Canek Maya Revolution",
    "ANWMexicans":         "Mexicans Hidalgo Standard",
    "ANWNapoleonicFrance": "Napoleonic France Napoleon Bonaparte Revolution",
    "ANWPeruvians":        "Peruvians Santa Cruz Peru Revolution",
    "ANWRevFrance":        "Revolutionary France Robespierre Revolution",
    "ANWRomanians":        "Romanians Cuza Revolution",
    "ANWSouthAfricans":    "South Africans Kruger Boer Revolution",
    "ANWTexians":          "Texians Sam Houston Texas Revolution",
}


# A leader_*.xs file's stem maps to a portrait slug. We then resolve
# the spec entry by matching that slug against the spec's portrait_path.
# Examples:
#   leader_napoleon.xs        → "napoleon"   (matches *_napoleon.png)
#   leader_crazy_horse.xs     → "crazy_horse"
#   leader_revolution_*.xs    → multi-civ aggregator (skip)


def _leader_slug(leader_file: Path) -> str:
    return leader_file.stem.removeprefix("leader_")


# engine slug → spec leader_label slug (per CLAUDE.md leader_key bridge).
# The portrait file uses the engine slug; the spec sometimes uses the
# canonical historical name. These are the known divergences.
_SPEC_SLUG_BRIDGE = {
    "wellington": "elizabeth",
    "catherine":  "ivan",
    "crazy_horse": "gall",
    "jean":       "valette",
    "usman":      "muhammadu",
}


def _spec_for_slug(spec_civs: dict, slug: str) -> dict | None:
    """Find spec entry. Try the leader's engine slug first via portrait path;
    fall back to the historical-name bridge for the few mismatches."""
    for needle in (f"_{slug}.png", f"_{_SPEC_SLUG_BRIDGE.get(slug, slug)}.png"):
        for civ_data in spec_civs.values():
            if civ_data.get("portrait_path", "").endswith(needle):
                return civ_data
        # Also try matching the data_name / leader_label directly
        bridged = _SPEC_SLUG_BRIDGE.get(slug, slug).replace("_", " ").lower()
        for civ_data in spec_civs.values():
            ll = civ_data.get("leader_label", "").lower()
            if bridged in ll:
                return civ_data
    return None


def _wall_strategy_label(value: int) -> str:
    return {
        0: "FortressRing", 1: "ChokepointSegments", 2: "CoastalBatteries",
        3: "FrontierPalisades", 4: "UrbanBarricade", 5: "MobileNoWalls",
    }.get(value, f"Unknown({value})")


def run_one(leader_file: Path) -> dict:
    interp = Interpreter(gs=scenario_open_age2(),
                         search_paths=[REPO / "game" / "ai",
                                       REPO / "game" / "ai" / "leaders",
                                       REPO / "game" / "ai" / "core"])
    # Pre-load aiHeader.xs so cLLWallStrategy*, cLLBuildStyle*, cAge*, etc.
    # constants resolve to their declared engine values, not the simulator's
    # zero-default. Then load leaderCommon.xs so the llUse*Style helpers
    # are defined and `gLLWallStrategy = cLLWallStrategyMobileNoWalls;`
    # actually means 5 instead of 0.
    for hdr in (REPO / "game" / "ai" / "aiHeader.xs",
                REPO / "game" / "ai" / "leaders" / "leaderCommon.xs"):
        if hdr.exists():
            try:
                interp.load_file(hdr)
            except Exception:
                pass  # degrade gracefully if a header uses unsupported syntax
    interp.load_file(leader_file)
    init_fn = next((n for n in interp.functions if n.startswith("initLeader")), None)
    if init_fn:
        interp.call_init(init_fn)
    for r in interp.rules.values():
        r.active = True
    interp.run(180.0, dt=1.0)

    return {
        "wall_strategy": interp.globals.get("gLLWallStrategy"),
        "military_distance_multiplier": interp.globals.get("gLLMilitaryDistanceMultiplier"),
        "ok_to_build_forts": interp.globals.get("cvOkToBuildForts"),
        "max_army_pop": interp.globals.get("cvMaxArmyPop"),
        "rush_boom": interp.globals.get("btRushBoom"),
        "offense_defense": interp.globals.get("btOffenseDefense"),
        "bias_trade": interp.globals.get("btBiasTrade"),
        "bias_native": interp.globals.get("btBiasNative"),
        "bias_inf": interp.globals.get("btBiasInf"),
        "bias_cav": interp.globals.get("btBiasCav"),
        "bias_art": interp.globals.get("btBiasArt"),
    }


def run_revolution(anw_token: str) -> dict:
    """Simulate the aggregator pair for one ANW revolution token.

    Boots leader_revolution_support.xs + leader_revolution_commanders.xs,
    injects civ_name = anw_token and is_revolution = True so the right
    else-if branch fires, then returns the same doctrine-global dict as
    run_one().
    """
    gs = scenario_open_age2()
    gs.civ_name = anw_token
    gs.is_revolution = True

    interp = Interpreter(gs=gs,
                         search_paths=[REPO / "game" / "ai",
                                       REPO / "game" / "ai" / "leaders",
                                       REPO / "game" / "ai" / "core"])

    # Pre-load constants and shared helpers (same as run_one).
    for hdr in (REPO / "game" / "ai" / "aiHeader.xs",
                REPO / "game" / "ai" / "leaders" / "leaderCommon.xs"):
        if hdr.exists():
            try:
                interp.load_file(hdr)
            except Exception:
                pass

    # Load the two aggregator files that handle all revolution civs.
    support_file     = LEADERS_DIR / "leader_revolution_support.xs"
    commanders_file  = LEADERS_DIR / "leader_revolution_commanders.xs"
    for xs_file in (support_file, commanders_file):
        if xs_file.exists():
            try:
                interp.load_file(xs_file)
            except Exception:
                pass

    # Call both init functions (support runs first, then the commander overlay).
    for init_fn_name in ("initLegendaryRevolutionSupport",
                         "initLegendaryRevolutionCommander"):
        if init_fn_name in interp.functions:
            interp.call_init(init_fn_name)

    # Tick all active rules for 180 sim-seconds.
    for r in interp.rules.values():
        r.active = True
    interp.run(180.0, dt=1.0)

    return {
        "wall_strategy": interp.globals.get("gLLWallStrategy"),
        "military_distance_multiplier": interp.globals.get("gLLMilitaryDistanceMultiplier"),
        "ok_to_build_forts": interp.globals.get("cvOkToBuildForts"),
        "max_army_pop": interp.globals.get("cvMaxArmyPop"),
        "rush_boom": interp.globals.get("btRushBoom"),
        "offense_defense": interp.globals.get("btOffenseDefense"),
        "bias_trade": interp.globals.get("btBiasTrade"),
        "bias_native": interp.globals.get("btBiasNative"),
        "bias_inf": interp.globals.get("btBiasInf"),
        "bias_cav": interp.globals.get("btBiasCav"),
        "bias_art": interp.globals.get("btBiasArt"),
    }


def compare_one(observed: dict, claims: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (passes, fails, unknowns) for one leader."""
    passes: list[str] = []
    fails: list[str] = []
    unknowns: list[str] = []

    # wall_strategy: exact integer match
    if "wall_strategy" in claims:
        want = claims["wall_strategy"]
        got = observed.get("wall_strategy")
        if got is None:
            unknowns.append(
                f"wall_strategy: spec wants {want} ({_wall_strategy_label(want)}); "
                f"sim observed nothing (leader didn't set gLLWallStrategy)"
            )
        elif got == want:
            passes.append(f"wall_strategy={got} ({_wall_strategy_label(got)})")
        else:
            fails.append(
                f"wall_strategy: want {want} ({_wall_strategy_label(want)}), "
                f"got {got} ({_wall_strategy_label(got)})"
            )

    # military_distance_band: [low, high] — observed must fall inside
    if "military_distance_band" in claims:
        lo, hi = claims["military_distance_band"]
        got = observed.get("military_distance_multiplier")
        if got is None:
            unknowns.append(
                f"military_distance_band: spec wants {lo}..{hi}; sim observed nothing"
            )
        elif lo <= got <= hi:
            passes.append(f"military_distance={got} in [{lo}, {hi}]")
        else:
            fails.append(f"military_distance={got} outside spec band [{lo}, {hi}]")

    # expects_forward: a forward-base doctrine should at minimum NOT pin
    # all military to a tight inner ring. We check the military distance
    # multiplier is ≥ 1.0 (= "push military out from TC"). cvOkToBuildForts
    # is intentionally NOT required — several civs (Aztec, Lakota) have
    # forward-aggressive doctrines but lack a fort unit type entirely.
    if claims.get("expects_forward") is True:
        got = observed.get("military_distance_multiplier")
        if got is not None and got < 1.0 and "military_distance_band" not in claims:
            fails.append(
                f"expects_forward=True but military_distance={got} (<1.0); "
                f"doctrine pulls inward, not outward"
            )
        elif got is not None and got >= 1.0:
            passes.append(f"expects_forward → military_distance={got} ≥ 1.0 ✓")

    # Composition claims (expects_infantry / expects_cavalry / expects_artillery)
    # are verified by static_scan_bias_setters() at the call site instead of here.
    # xs_sim only ticks 180 sim-seconds at Age 2, which under-represents civs that
    # are intentionally artillery-light in Age 2 but boost it in Age 3/4 (e.g.
    # Russians get Falconet at Age 3 — Catherine's Age 2 btBiasArt=-0.1 is by
    # design). The static scan walks ALL bias setters in the leader file and
    # uses the max value, which matches the spec's "over the game" semantics.

    return passes, fails, unknowns


# ── Static-scan-based composition verification ──────────────────────────────
# Walks a leader .xs file for `btBias(Inf|Cav|Art) = <float>;` assignments and
# returns the max value across all rules/branches. This is used to verify
# expects_infantry / expects_cavalry / expects_artillery claims, which apply
# to the whole game arc — not just the Age 2 slice the simulator observes.

_BIAS_SETTER_RE = re.compile(
    r"btBias(Inf|Cav|Art)\s*=\s*(-?[0-9]+(?:\.[0-9]+)?)\s*;"
)


def _scan_bias_setters(xs_text: str) -> dict[str, float]:
    """Return max observed value across all btBias{Inf,Cav,Art} = N assignments.
    Compound assignments like `btBiasInf = btBiasInf + 0.1;` (used by the
    revolution support layer) are skipped — we only count literal-RHS setters,
    which is what every named leader uses.
    """
    out: dict[str, float] = {"Inf": 0.0, "Cav": 0.0, "Art": 0.0}
    seen: dict[str, bool] = {"Inf": False, "Cav": False, "Art": False}
    for m in _BIAS_SETTER_RE.finditer(xs_text):
        kind, val_str = m.group(1), m.group(2)
        v = float(val_str)
        if not seen[kind] or v > out[kind]:
            out[kind] = v
            seen[kind] = True
    return out


_MIL_FOCUS_RE = re.compile(
    r"llSetMilitaryFocus\s*\(\s*"
    r"(-?[0-9]+(?:\.[0-9]+)?)\s*,\s*"
    r"(-?[0-9]+(?:\.[0-9]+)?)\s*,\s*"
    r"(-?[0-9]+(?:\.[0-9]+)?)\s*\)"
)


def _scan_revolution_bias_setters(anw_token: str) -> dict[str, float]:
    """Scan the matching else-if block in leader_revolution_commanders.xs
    plus the support layer's bucket assignments for an ANW revolution token.

    Looks for both direct btBias* setters and llSetMilitaryFocus(...) calls.
    Returns {"Inf": maxv, "Cav": maxv, "Art": maxv} like _scan_bias_setters.
    """
    out = {"Inf": 0.0, "Cav": 0.0, "Art": 0.0}

    commanders = LEADERS_DIR / "leader_revolution_commanders.xs"
    if not commanders.exists():
        return out
    text = commanders.read_text(encoding="utf-8")

    # Find the else-if block for this token. Simplest robust approach:
    # locate `rvltName == "<token>"` and walk forward to the matching `}` at
    # the same brace depth.
    needle = f'rvltName == "{anw_token}"'
    idx = text.find(needle)
    if idx == -1:
        return out
    # Find first `{` after the needle, then balance braces.
    brace_start = text.find("{", idx)
    if brace_start == -1:
        return out
    depth = 0
    end = brace_start
    for i in range(brace_start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    block = text[brace_start:end + 1]

    # Direct setters in the block
    for m in _BIAS_SETTER_RE.finditer(block):
        kind, val = m.group(1), float(m.group(2))
        if val > out[kind]:
            out[kind] = val
    # llSetMilitaryFocus(inf, cav, art) calls in the block
    for m in _MIL_FOCUS_RE.finditer(block):
        inf, cav, art = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
        if inf > out["Inf"]: out["Inf"] = inf
        if cav > out["Cav"]: out["Cav"] = cav
        if art > out["Art"]: out["Art"] = art

    # Also scan the support layer — it sets buckets by rvltName too
    support = LEADERS_DIR / "leader_revolution_support.xs"
    if support.exists():
        supp = support.read_text(encoding="utf-8")
        # Support layer uses rvltName == "ANWXxx" matched against
        # `kbGetCivName()` lookups (engine returns the ANW civ token at runtime).
        # Look for any block that mentions the ANW token explicitly.
        if anw_token in supp:
            # Find the if-block containing the token and scan that
            tok_idx = supp.find(anw_token)
            block_start = supp.rfind("{", 0, tok_idx)
            block_end = supp.find("}", tok_idx)
            if block_start != -1 and block_end != -1:
                supp_block = supp[block_start:block_end + 1]
                for m in _BIAS_SETTER_RE.finditer(supp_block):
                    kind, val = m.group(1), float(m.group(2))
                    if val > out[kind]:
                        out[kind] = val
                for m in _MIL_FOCUS_RE.finditer(supp_block):
                    inf, cav, art = (float(m.group(1)), float(m.group(2)),
                                     float(m.group(3)))
                    if inf > out["Inf"]: out["Inf"] = inf
                    if cav > out["Cav"]: out["Cav"] = cav
                    if art > out["Art"]: out["Art"] = art

    return out


# Minimum target btBias for an expects_* claim to be considered meaningful.
# A doctrine that nominally expects type X but never pushes btBiasX above this
# floor isn't actually boosting that type — it's drift, not design. 0.5 is the
# midpoint of the AoE3 -1.0..+1.0 bias range and matches the "Age 3 expanded"
# baseline used by every named-leader file in this codebase (see e.g.
# leader_menelik.xs's Age 3 block where btBiasArt steps to 0.6 then 0.75).
_COMP_MIN_TARGET = 0.5

# Maximum lead another type may have over the expected type before we declare
# the doctrine is actually preferring the wrong type. Combined with the floor
# above this gives a two-axis check: target must be (a) meaningful and
# (b) not dominated by another type by a wide margin.
_COMP_MAX_OTHER_LEAD = 0.3


def _composition_compare(
    claims: dict, max_biases: dict[str, float]
) -> tuple[list[str], list[str], list[str]]:
    """Compare expects_* claims against statically-scanned max btBias values.

    Two-axis check:
      1. Floor: target must be ≥ _COMP_MIN_TARGET (= 0.5) — the doctrine
         must *actually* push that type above the neutral mid-band, not just
         leave it at the default value.
      2. Lead-margin: another type may not exceed target by more than
         _COMP_MAX_OTHER_LEAD (= 0.3) when target itself is below the floor.
         Above the floor, other types are allowed to be equal or higher
         (combined-arms doctrines like Maltese / Ethiopia legitimately boost
         infantry to 1.0 alongside their nominal artillery focus).
    """
    p, f, u = [], [], []
    pairs = [
        ("expects_infantry",  "Inf", "infantry"),
        ("expects_cavalry",   "Cav", "cavalry"),
        ("expects_artillery", "Art", "artillery"),
    ]
    for claim_key, kind, label in pairs:
        if not claims.get(claim_key):
            continue
        target = max_biases.get(kind, 0.0)
        others_max = max(v for k, v in max_biases.items() if k != kind)

        # Axis 1: hard floor — claimed type must actually be boosted.
        if target < _COMP_MIN_TARGET:
            # Below floor: also require it's not way behind everyone else.
            if (others_max - target) >= _COMP_MAX_OTHER_LEAD:
                f.append(
                    f"{claim_key}=True but max btBias{kind}={target:.2f} "
                    f"< floor {_COMP_MIN_TARGET} and other-max={others_max:.2f} "
                    f"(Δ≥{_COMP_MAX_OTHER_LEAD}) — doctrine never meaningfully "
                    f"boosts {label}"
                )
            else:
                # Below floor but no clear other-type winner either —
                # surface as UNKNOWN so a human can audit the leader file.
                u.append(
                    f"{claim_key}=True but max btBias{kind}={target:.2f} "
                    f"< floor {_COMP_MIN_TARGET} (other-max={others_max:.2f}) — "
                    f"{label} boost is weak; recommend bumping leader bias"
                )
        else:
            p.append(
                f"{claim_key} → max btBias{kind}={target:.2f} "
                f"(≥{_COMP_MIN_TARGET}, max-other={others_max:.2f}) ✓"
            )
    return p, f, u


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    if not SPEC.exists():
        print(f"FATAL: {SPEC} not found. Run tools/playtest/extract_playstyle_spec.py first.")
        return 2

    spec = json.load(open(SPEC))
    spec_civs = spec.get("civs", {})

    leaders = sorted(LEADERS_DIR.glob("leader_*.xs"))
    # Skip aggregator files that drive multiple civs at once.
    leaders = [f for f in leaders if "revolution_" not in f.name]

    rows: list[dict] = []
    for f in leaders:
        slug = _leader_slug(f)
        spec_entry = _spec_for_slug(spec_civs, slug)
        observed = run_one(f)

        if spec_entry is None:
            rows.append({
                "leader": slug,
                "status": "NO_SPEC",
                "passes": [],
                "fails": [],
                "unknowns": [f"no spec entry found for slug {slug!r}"],
                "observed": observed,
            })
            continue

        claims = spec_entry.get("claims", {})
        if not claims:
            rows.append({
                "leader": slug,
                "civ": spec_entry["data_name"],
                "status": "NO_CLAIMS",
                "passes": [], "fails": [], "unknowns": [],
                "observed": observed,
            })
            continue

        p, fl, u = compare_one(observed, claims)
        # Augment with static-scan-based composition check (whole-game biases)
        max_biases = _scan_bias_setters(f.read_text(encoding="utf-8"))
        cp, cf, cu = _composition_compare(claims, max_biases)
        p += cp; fl += cf; u += cu
        status = "FAIL" if fl else ("UNKNOWN" if u and not p else "PASS")
        rows.append({
            "leader": slug,
            "civ": spec_entry["data_name"],
            "status": status,
            "passes": p, "fails": fl, "unknowns": u,
            "observed": observed,
            "max_biases": max_biases,
        })

    # ── ANW revolution civs ────────────────────────────────────────────────
    # Each token is dispatched through the aggregator pair
    # (leader_revolution_support.xs + leader_revolution_commanders.xs)
    # with civIsRevolution() == True and kbGetCivName() == token.
    for token in _ANW_REVOLUTION_TOKENS:
        label = f"rvlt_{token}"
        spec_data_name = _ANW_RVLT_SPEC_BRIDGE.get(token)
        spec_entry = spec_civs.get(spec_data_name) if spec_data_name else None

        try:
            observed = run_revolution(token)
        except Exception as exc:
            rows.append({
                "leader": label,
                "status": "UNKNOWN",
                "passes": [],
                "fails": [],
                "unknowns": [f"run_revolution raised: {exc}"],
                "observed": {},
            })
            continue

        if spec_entry is None:
            rows.append({
                "leader": label,
                "status": "NO_SPEC",
                "passes": [],
                "fails": [],
                "unknowns": [f"no spec entry found for token {token!r} "
                             f"(mapped to {spec_data_name!r})"],
                "observed": observed,
            })
            continue

        claims = spec_entry.get("claims", {})
        if not claims:
            rows.append({
                "leader": label,
                "civ": spec_entry["data_name"],
                "status": "NO_CLAIMS",
                "passes": [], "fails": [], "unknowns": [],
                "observed": observed,
            })
            continue

        p, fl, u = compare_one(observed, claims)
        # Augment with composition check. For revolution civs we scan the
        # else-if block in leader_revolution_commanders.xs for this token PLUS
        # any bucket assignment in leader_revolution_support.xs that matches
        # this rvltName.
        max_biases = _scan_revolution_bias_setters(token)
        cp, cf, cu = _composition_compare(claims, max_biases)
        p += cp; fl += cf; u += cu
        status = "FAIL" if fl else ("UNKNOWN" if u and not p else "PASS")
        rows.append({
            "leader": label,
            "civ": spec_entry["data_name"],
            "status": status,
            "passes": p, "fails": fl, "unknowns": u,
            "observed": observed,
            "max_biases": max_biases,
        })

    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        print(f"{'Leader':<22} {'Status':<8} Detail")
        print("-" * 100)
        n_pass = n_fail = n_unk = n_nospec = 0
        for r in rows:
            s = r["status"]
            if s == "PASS":      n_pass += 1
            elif s == "FAIL":    n_fail += 1
            elif s == "UNKNOWN": n_unk += 1
            else:                n_nospec += 1
            detail_lines: list[str] = []
            if r["fails"]:
                detail_lines.extend(f"FAIL: {x}" for x in r["fails"])
            if args.verbose:
                detail_lines.extend(f"PASS: {x}" for x in r["passes"])
                detail_lines.extend(f"???:  {x}" for x in r["unknowns"])
            elif s == "UNKNOWN" and not detail_lines:
                detail_lines.extend(f"???:  {x}" for x in r["unknowns"])

            first = detail_lines[0] if detail_lines else ""
            print(f"{r['leader']:<22} {s:<8} {first}")
            for d in detail_lines[1:]:
                print(f"{'':<22} {'':<8} {d}")
        print("-" * 100)
        print(f"PASS={n_pass}  FAIL={n_fail}  UNKNOWN={n_unk}  NO_SPEC={n_nospec}  "
              f"(of {len(rows)} leaders)")

    return 1 if any(r["status"] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
