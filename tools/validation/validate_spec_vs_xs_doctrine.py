#!/usr/bin/env python3
"""Static validator: per-civ AI doctrine spec vs XS implementation.

Locks the per-civ AI doctrine guarantees (wall_strategy, first_military_building,
expects_forward) into the static gate so they cannot regress unnoticed.

For each ANW civ in playstyle_spec.json → civs.*.claims, this validator:
  1. Maps the spec entry to the canonical XS dispatch token (e.g. "ANWAztecs").
  2. Finds the matching ``else if (rvltName == "<token>")`` block in
     ``game/ai/leaders/leaderCommon.xs:llApplyBuildStyleForActiveCiv()``.
  3. Identifies the ``llUse*Style(...)`` call to derive style defaults.
  4. Applies any post-style overrides (``gLLWallStrategy = ...`` assignment or
     ``gLLForwardBaseEarliestMs = ...`` reset or ``llEnableEarlyForwardBase(...)``
     call) that appear inside the same dispatch block.
  5. Compares the final values against the spec claims.

Each civ emits a PASS or FAIL line. Exit 0 iff all civs pass.

Usage::

    python3 tools/validation/validate_spec_vs_xs_doctrine.py
    python3 tools/validation/validate_spec_vs_xs_doctrine.py \\
        --json artifacts/validation/spec_vs_xs_doctrine.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

SPEC_PATH = REPO_ROOT / "playstyle_spec.json"
LEADER_COMMON_XS = REPO_ROOT / "game" / "ai" / "leaders" / "leaderCommon.xs"
LEADER_REVOLUTION_XS = REPO_ROOT / "game" / "ai" / "leaders" / "leader_revolution_commanders.xs"

# ---------------------------------------------------------------------------
# Style → doctrine defaults (derived from leaderCommon.xs style functions)
# Wall strategy values match aiHeader.xs cLLWallStrategy* constants:
#   0 = FortressRing, 1 = ChokepointSegments, 2 = CoastalBatteries,
#   3 = FrontierPalisades, 4 = UrbanBarricade, 5 = MobileNoWalls
# expects_forward = True iff the style calls llEnableEarlyForwardBase(...)
#   without a subsequent reset to gLLForwardBaseEarliestMs = 1200000
# first_military_building is inferred from the style class:
#   NavalMercantileCompound → "dock"
#   ShrineTradeNodeSpread / DistributedEconomicNetwork → "trading_post_or_market"
#   CivicMilitiaCenter → "outpost"
#   everything else → "barracks_or_stable"
# ---------------------------------------------------------------------------
STYLE_DEFAULTS: dict[str, dict[str, Any]] = {
    "llUseCompactFortifiedCoreStyle":         {"wall_strategy": 0, "first_military_building": "barracks_or_stable", "expects_forward": False},
    "llUseAndeanTerraceFortressStyle":         {"wall_strategy": 1, "first_military_building": "barracks_or_stable", "expects_forward": False},
    "llUseNavalMercantileCompoundStyle":       {"wall_strategy": 2, "first_military_building": "dock",                 "expects_forward": False},
    "llUseDistributedEconomicNetworkStyle":    {"wall_strategy": 3, "first_military_building": "trading_post_or_market", "expects_forward": True},
    "llUseCivicMilitiaCenterStyle":            {"wall_strategy": 3, "first_military_building": "outpost",              "expects_forward": True},
    "llUseRepublicanLeveeStyle":               {"wall_strategy": 4, "first_military_building": "barracks_or_stable", "expects_forward": True},
    "llUseForwardOperationalLineStyle":        {"wall_strategy": 5, "first_military_building": "barracks_or_stable", "expects_forward": True},
    "llUseMobileFrontierScatterStyle":         {"wall_strategy": 5, "first_military_building": "barracks_or_stable", "expects_forward": True},
    "llUseShrineTradeNodeSpreadStyle":         {"wall_strategy": 5, "first_military_building": "trading_post_or_market", "expects_forward": True},
    "llUseSteppeCavalryWedgeStyle":            {"wall_strategy": 5, "first_military_building": "barracks_or_stable", "expects_forward": True},
    "llUseJungleGuerrillaNetworkStyle":        {"wall_strategy": 5, "first_military_building": "barracks_or_stable", "expects_forward": True},
    "llUseHighlandCitadelStyle":               {"wall_strategy": 0, "first_military_building": "barracks_or_stable", "expects_forward": False},
    "llUseSiegeTrainConcentrationStyle":       {"wall_strategy": 0, "first_military_building": "barracks_or_stable", "expects_forward": True},
    "llUseCossackVoiskoStyle":                 {"wall_strategy": 0, "first_military_building": "barracks_or_stable", "expects_forward": True},
}

# Wall strategy integer → name (for readable output)
WALL_STRATEGY_NAMES = {
    0: "FortressRing",
    1: "ChokepointSegments",
    2: "CoastalBatteries",
    3: "FrontierPalisades",
    4: "UrbanBarricade",
    5: "MobileNoWalls",
}

# Explicit wall-strategy override constants used in XS source (right-hand side of
# gLLWallStrategy = ...; assignments).
WALL_STRATEGY_VALUES: dict[str, int] = {
    "cLLWallStrategyFortressRing":       0,
    "cLLWallStrategyChokepointSegments": 1,
    "cLLWallStrategyCoastalBatteries":   2,
    "cLLWallStrategyFrontierPalisades":  3,
    "cLLWallStrategyUrbanBarricade":     4,
    "cLLWallStrategyMobileNoWalls":      5,
}

# ---------------------------------------------------------------------------
# Spec label → primary XS dispatch token
#
# Strategy: each spec entry's data_name maps to an ANW* civ in leaderCommon.xs.
# For canonical (non-revolution) mod civs the token is "ANW<CivName>".
# For revolution-only civs the token is "ANW<Nation>" (same ANW prefix).
# The base-engine civs (cCivXPAztec etc.) are handled via the matching ANW
# canonical nation block in llApplyBuildStyleForActiveCiv — we use that path
# as the ground truth for doctrine because the ANW mod always runs the ANW civ.
# ---------------------------------------------------------------------------
SPEC_DATA_NAME_TO_XS_TOKEN: dict[str, str] = {
    "Argentines San Martin Revolution":                    "ANWArgentines",
    "Aztecs Montezuma":                                    "ANWAztecs",
    "Barbary Barbarossa Corsair Revolution":               "ANWBarbary",
    "Brazil Pedro Revolution":                             "ANWBrazil",
    "British Elizabeth":                                   "ANWBritish",
    "Californians Vallejo Revolution":                     "RvltModCalifornians",
    "Canadians Brock Revolution":                          "ANWCanadians",
    "Central Americans Morazan Revolution":                "RvltModCentralAmericans",
    "Chileans OHiggins Revolution":                        "ANWChileans",
    "Chinese Kangxi":                                      "ANWChinese",
    "Columbians Bolivar Colombia Revolution":              "ANWColumbians",
    "Dutch Maurice Nassau":                                "ANWDutch",
    "Egyptians Muhammad Ali Revolution":                   "ANWEgyptians",
    "Ethiopians Menelik":                                  "ANWEthiopians",
    "Finnish Mannerheim Revolution":                       "ANWFinnish",
    "French Canadians Papineau Revolution":                "RvltModFrenchCanadians",
    "French Louis XVIII Bourbon":                          "ANWFrench",
    "Germans Frederick Great":                             "ANWGermans",
    "Haitians Louverture Revolution":                      "ANWHaitians",
    "Haudenosaunee Hiawatha Iroquois":                     "ANWHaudenosaunee",
    "Hausa Usman dan Fodio":                               "ANWHausa",
    "Hungarians Kossuth Revolution":                       "ANWHungarians",
    "Inca Pachacuti":                                      "ANWInca",
    "Indians Akbar":                                       "ANWIndians",
    "Indonesians Diponegoro Revolution":                   "ANWIndonesians",
    "Italians Garibaldi":                                  "ANWItalians",
    "Japanese Tokugawa Ieyasu":                            "ANWJapanese",
    "Lakota Crazy Horse":                                  "ANWLakota",
    "Maltese Valette":                                     "ANWMaltese",
    "Mayans Canek Maya Revolution":                        "ANWMayans",
    "Mexicans Hidalgo Standard":                           "ANWMexicans",
    "Napoleonic France Napoleon Bonaparte Revolution":     "ANWNapoleonicFrance",
    "Ottomans Suleiman":                                   "ANWOttomans",
    "Peruvians Santa Cruz Peru Revolution":                "ANWPeruvians",
    "Portuguese Henry Navigator":                          "ANWPortuguese",
    "Revolutionary France Robespierre Revolution":         "ANWRevFrance",
    "Rio Grande Canales Rosillo Revolution":               "RvltModRioGrande",
    "Romanians Cuza Revolution":                           "ANWRomanians",
    "Russians Catherine":                                  "ANWRussians",
    "South Africans Kruger Boer Revolution":               "ANWSouthAfricans",
    "Spanish Isabella Castile":                            "ANWSpanish",
    "Swedes Gustavus Adolphus Swedish":                    "ANWSwedes",
    "Texians Sam Houston Texas Revolution":                "ANWTexians",
    "United States Washington":                            "ANWUSA",
    "Yucatan Pat Revolution":                              "RvltModYucatan",
}


def _verify_style_defaults_against_xs(xs_source: str) -> list[str]:
    """Lock STYLE_DEFAULTS[*]['wall_strategy'] against the actual style helpers.

    For each ``void llUse<Name>Style(...)`` definition in leaderCommon.xs, walk
    the function body until the first ``gLLWallStrategy = cLLWallStrategy<X>;``
    assignment and check that it matches our hardcoded STYLE_DEFAULTS entry.
    Returns a list of mismatch strings; empty if every style helper is in sync
    with our table.

    This protects against the silent failure where a style helper in
    leaderCommon.xs gets its default strategy changed but STYLE_DEFAULTS does
    not — which would cause this validator to keep reporting PASS while the
    engine doctrine has drifted.
    """
    issues: list[str] = []
    # Match function header: `void llUse<Name>Style(...)` then take the body
    # from the opening { to the matching }.
    fn_header_re = re.compile(
        r"^void\s+(llUse[A-Za-z]+Style)\s*\([^)]*\)\s*$", re.MULTILINE
    )
    code = _strip_comments(xs_source)
    for m in fn_header_re.finditer(code):
        fn_name = m.group(1)
        if fn_name not in STYLE_DEFAULTS:
            # Not every llUse*Style helper appears in our defaults table;
            # only those used by ANW civs do. Skip unrelated ones.
            continue
        brace_start = code.find("{", m.end())
        if brace_start < 0:
            issues.append(f"{fn_name}: no opening brace after definition")
            continue
        # Find first gLLWallStrategy assignment inside the body (within the
        # next ~600 chars — body of these helpers is short).
        body_window = code[brace_start:brace_start + 800]
        ws_match = re.search(
            r"gLLWallStrategy\s*=\s*(cLLWallStrategy\w+)\s*;", body_window
        )
        if not ws_match:
            issues.append(
                f"{fn_name}: no gLLWallStrategy assignment in body — "
                f"STYLE_DEFAULTS expects ws={STYLE_DEFAULTS[fn_name]['wall_strategy']}"
            )
            continue
        const = ws_match.group(1)
        if const not in WALL_STRATEGY_VALUES:
            issues.append(
                f"{fn_name}: unknown wall-strategy constant {const!r}"
            )
            continue
        actual_ws = WALL_STRATEGY_VALUES[const]
        expected_ws = STYLE_DEFAULTS[fn_name]["wall_strategy"]
        if actual_ws != expected_ws:
            issues.append(
                f"{fn_name}: XS sets ws={actual_ws} ({WALL_STRATEGY_NAMES.get(actual_ws,'?')}) "
                f"but STYLE_DEFAULTS expects ws={expected_ws} "
                f"({WALL_STRATEGY_NAMES.get(expected_ws,'?')})"
            )
    return issues


def _strip_comments(text: str) -> str:
    """Remove C-style line comments (//) from XS source."""
    lines = []
    for line in text.splitlines():
        idx = line.find("//")
        if idx >= 0:
            line = line[:idx]
        lines.append(line)
    return "\n".join(lines)


def _extract_function_body(xs_source: str, fn_name: str) -> str | None:
    """Extract the body of a void function by name (between outermost braces)."""
    fn_start = xs_source.find(fn_name)
    if fn_start < 0:
        return None
    brace_start = xs_source.find("{", fn_start)
    if brace_start < 0:
        return None
    depth = 0
    i = brace_start
    while i < len(xs_source):
        ch = xs_source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return xs_source[brace_start + 1:i]
        i += 1
    return None


def _extract_dispatch_block(fn_body: str, token: str) -> str | None:
    """Return the body of the ``else if (rvltName == "<token>") { ... }`` block
    within a function body string (already scoped to the right function).
    """
    pattern = rf'rvltName\s*==\s*"{re.escape(token)}"\s*\)'
    m = re.search(pattern, fn_body)
    if not m:
        return None

    # Find the opening brace that follows.
    start = m.end()
    brace_start = fn_body.find("{", start)
    if brace_start < 0:
        return None

    # Walk forward to find the matching closing brace.
    depth = 0
    i = brace_start
    while i < len(fn_body):
        ch = fn_body[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return fn_body[brace_start + 1:i]
        i += 1
    return None


def _apply_block_overrides(state: dict[str, Any], block: str) -> None:
    """Apply wall_strategy and expects_forward overrides found in a block string.

    Mutates ``state`` in-place. The block should already have comments stripped
    and should start AFTER the style-call line (post-style content).
    """
    ws_override_re = re.compile(
        r"\bgLLWallStrategy\s*=\s*(cLLWallStrategy\w+)\s*;"
    )
    for mo in ws_override_re.finditer(block):
        const = mo.group(1)
        if const in WALL_STRATEGY_VALUES:
            state["wall_strategy"] = WALL_STRATEGY_VALUES[const]

    fwd_reset_re = re.compile(
        r"\bgLLForwardBaseEarliestMs\s*=\s*(\d+)\s*;"
    )
    for mo in fwd_reset_re.finditer(block):
        ms = int(mo.group(1))
        state["expects_forward"] = (ms < 1200000)

    if re.search(r"\bllEnableEarlyForwardBase\s*\(", block):
        state["expects_forward"] = True


def _compute_xs_doctrine(block: str,
                         override_block: str | None = None) -> dict[str, Any]:
    """Parse a dispatch block and return the final doctrine values.

    ``block`` is the primary dispatch block (from llApplyBuildStyleForActiveCiv).
    ``override_block`` is an optional secondary block (from
    initLegendaryRevolutionCommander) that can further override doctrine
    values AFTER the primary block runs. For RvltMod* civs the revolution
    commanders file runs second and its overrides win.

    Returns dict with keys: wall_strategy (int), first_military_building (str),
    expects_forward (bool).
    """
    # Strip comments so we don't match commented-out lines.
    block = _strip_comments(block)

    # Find the llUse*Style() call — there should be exactly one.
    style_call_re = re.compile(
        r"\b(llUse(?:CompactFortifiedCore|AndeanTerraceFortress|NavalMercantileCompound"
        r"|DistributedEconomicNetwork|CivicMilitiaCenter|RepublicanLevee"
        r"|ForwardOperationalLine|MobileFrontierScatter|ShrineTradeNodeSpread"
        r"|SteppeCavalryWedge|JungleGuerrillaNetwork|HighlandCitadel"
        r"|SiegeTrainConcentration|CossackVoisko)Style)\s*\("
    )
    m_style = style_call_re.search(block)
    if not m_style:
        return {"wall_strategy": -1, "first_military_building": "unknown", "expects_forward": False,
                "_error": "no llUse*Style call found"}

    style_fn = m_style.group(1)
    state = STYLE_DEFAULTS[style_fn].copy()

    # Apply post-style overrides from the primary block.
    after_style = block[m_style.end():]
    _apply_block_overrides(state, after_style)

    # Apply overrides from the secondary block (revolution commanders), if any.
    # These run AFTER the primary block so they win. The secondary block may
    # contain its own llUse*Style() call that resets state — if present, we
    # recompute from that style; otherwise we only apply the override lines.
    if override_block is not None:
        override_block = _strip_comments(override_block)
        m_override_style = style_call_re.search(override_block)
        if m_override_style:
            # The revolution commanders file re-runs the full style setup.
            # Re-derive state from the override style.
            state2 = STYLE_DEFAULTS[m_override_style.group(1)].copy()
            after_override_style = override_block[m_override_style.end():]
            _apply_block_overrides(state2, after_override_style)
            state.update(state2)
            state["_style_fn"] = m_override_style.group(1)
        else:
            # No re-style — just apply override lines on top of existing state.
            _apply_block_overrides(state, override_block)

    state.setdefault("_style_fn", style_fn)
    return state


def _spec_expects_forward(claims: dict) -> bool | None:
    """Return spec's expects_forward value; treat None/missing as not_checked."""
    val = claims.get("expects_forward")
    if val is None:
        return None
    return bool(val)


def _spec_expects_naval(claims: dict) -> bool | None:
    """Return spec's expects_naval value; treat None/missing as not_checked."""
    val = claims.get("expects_naval")
    if val is None:
        return None
    return bool(val)


def _check_spec_internal_consistency(data_name: str, claims: dict) -> list[str]:
    """Sanity-check that a civ's claim set is internally consistent.

    Rules (each violation produces one diff line):
      • expects_naval=True ↔ first_military_building == "dock"
      • expects_naval=True ↔ wall_strategy == 2 (CoastalBatteries)
      • first_military_building == "dock" ↔ wall_strategy == 2

    These are *spec-internal* consistency checks — they catch hand-edits
    to playstyle_spec.json that drift one field without updating the
    related fields. Returns an empty list if the claim set is consistent.
    """
    diffs: list[str] = []
    naval = claims.get("expects_naval")
    fmb = claims.get("first_military_building")
    ws = claims.get("wall_strategy")

    if naval is True and fmb is not None and fmb != "dock":
        diffs.append(
            f"spec-internal: expects_naval=True but first_military_building={fmb!r}"
            f" (expected 'dock')"
        )
    if naval is True and ws is not None and ws != 2:
        diffs.append(
            f"spec-internal: expects_naval=True but wall_strategy={ws}"
            f" (expected 2/CoastalBatteries)"
        )
    if fmb == "dock" and ws is not None and ws != 2:
        diffs.append(
            f"spec-internal: first_military_building='dock' but wall_strategy={ws}"
            f" (expected 2/CoastalBatteries)"
        )
    if fmb == "dock" and naval is False:
        diffs.append(
            "spec-internal: first_military_building='dock' but expects_naval=False"
        )
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=SPEC_PATH)
    ap.add_argument("--xs", type=Path, default=LEADER_COMMON_XS)
    ap.add_argument("--xs-revolution", type=Path, default=LEADER_REVOLUTION_XS)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("SPEC VS XS DOCTRINE")
    print("=" * 60)

    # Load spec.
    if not args.spec.exists():
        print(f"  ERROR: spec file not found: {args.spec}")
        return 2
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    civs_spec = spec.get("civs", {})
    print(f"  Loaded {len(civs_spec)} civs from playstyle_spec.json")

    # Load leaderCommon.xs.
    if not args.xs.exists():
        print(f"  ERROR: XS file not found: {args.xs}")
        return 2
    xs_raw = args.xs.read_text(encoding="utf-8")
    print(f"  Loaded leaderCommon.xs ({len(xs_raw)} bytes)")

    # Self-check: lock STYLE_DEFAULTS against the actual style helpers so the
    # validator can't silently report PASS after an XS edit that drifts a
    # style's default wall_strategy without updating our table.
    style_issues = _verify_style_defaults_against_xs(xs_raw)
    if style_issues:
        print()
        print("  ERROR: STYLE_DEFAULTS out of sync with leaderCommon.xs:")
        for issue in style_issues:
            print(f"    - {issue}")
        return 2
    print("  STYLE_DEFAULTS table in sync with XS style helpers")

    # Extract the llApplyBuildStyleForActiveCiv function body once.
    apply_fn_body = _extract_function_body(xs_raw, "llApplyBuildStyleForActiveCiv")
    if apply_fn_body is None:
        print("  ERROR: llApplyBuildStyleForActiveCiv not found in leaderCommon.xs")
        return 2
    print(f"  Scoped to llApplyBuildStyleForActiveCiv ({len(apply_fn_body)} chars)")

    # Load leader_revolution_commanders.xs (for RvltMod* overrides).
    rev_fn_body: str | None = None
    if args.xs_revolution.exists():
        rev_raw = args.xs_revolution.read_text(encoding="utf-8")
        rev_fn_body = _extract_function_body(rev_raw, "initLegendaryRevolutionCommander")
        if rev_fn_body:
            print(f"  Scoped to initLegendaryRevolutionCommander ({len(rev_fn_body)} chars)")
        else:
            print("  WARN: initLegendaryRevolutionCommander not found in revolution commanders xs")
    else:
        print(f"  WARN: revolution commanders XS not found: {args.xs_revolution}")
    print()

    results: dict[str, dict] = {}
    failures: list[str] = []

    for spec_key, civ_data in civs_spec.items():
        data_name = civ_data.get("data_name", spec_key)
        claims = civ_data.get("claims", {})

        xs_token = SPEC_DATA_NAME_TO_XS_TOKEN.get(data_name)
        if xs_token is None:
            print(f"  SKIP  {data_name!r}: no XS token mapping")
            results[data_name] = {"verdict": "SKIP", "reason": "no XS token mapping"}
            continue

        block = _extract_dispatch_block(apply_fn_body, xs_token)
        if block is None:
            print(f"  ERROR {data_name!r}: dispatch block for {xs_token!r} not found in XS")
            results[data_name] = {"verdict": "ERROR", "xs_token": xs_token,
                                  "reason": f"dispatch block not found for {xs_token}"}
            failures.append(data_name)
            continue

        # For RvltMod* civs, also fetch the override block from
        # initLegendaryRevolutionCommander which runs after llApplyBuildStyleForActiveCiv
        # and can override doctrine values (e.g. resetting gLLForwardBaseEarliestMs).
        override_block: str | None = None
        if xs_token.startswith("RvltMod") and rev_fn_body is not None:
            override_block = _extract_dispatch_block(rev_fn_body, xs_token)

        actual = _compute_xs_doctrine(block, override_block)
        if "_error" in actual:
            print(f"  ERROR {data_name!r} ({xs_token}): {actual['_error']}")
            results[data_name] = {"verdict": "ERROR", "xs_token": xs_token,
                                  "reason": actual["_error"]}
            failures.append(data_name)
            continue

        spec_ws = claims.get("wall_strategy")
        actual_ws = actual["wall_strategy"]
        spec_fmb = claims.get("first_military_building")
        actual_fmb = actual["first_military_building"]
        spec_fwd = _spec_expects_forward(claims)
        actual_fwd = actual["expects_forward"]
        spec_naval = _spec_expects_naval(claims)

        diffs: list[str] = []
        if spec_ws is not None and actual_ws != spec_ws:
            diffs.append(
                f"wall_strategy: spec={spec_ws} ({WALL_STRATEGY_NAMES.get(spec_ws, '?')}) "
                f"actual={actual_ws} ({WALL_STRATEGY_NAMES.get(actual_ws, '?')})"
            )
        if spec_fmb is not None and actual_fmb != spec_fmb:
            diffs.append(f"first_military_building: spec={spec_fmb!r} actual={actual_fmb!r}")
        if spec_fwd is not None and actual_fwd != spec_fwd:
            diffs.append(f"expects_forward: spec={spec_fwd} actual={actual_fwd}")

        # Defence-in-depth: expects_naval is derived from first_military_building
        # in the style. If the spec asserts expects_naval=True the dispatched
        # style must produce a dock-first AI.
        if spec_naval is True and actual_fmb != "dock":
            diffs.append(
                f"expects_naval=True implies first_military_building='dock' but actual={actual_fmb!r}"
            )

        # Spec-internal consistency (catches hand-edits to playstyle_spec.json
        # that drift one claim field without updating its dependents).
        diffs.extend(_check_spec_internal_consistency(data_name, claims))

        verdict = "FAIL" if diffs else "PASS"
        mark = "FAIL" if diffs else "PASS"
        style_name = actual.get("_style_fn", "?")

        entry: dict = {
            "xs_token": xs_token,
            "style_fn": style_name,
            "spec_wall_strategy": spec_ws,
            "actual_wall_strategy": actual_ws,
            "spec_first_military_building": spec_fmb,
            "actual_first_military_building": actual_fmb,
            "spec_expects_forward": spec_fwd,
            "actual_expects_forward": actual_fwd,
            "verdict": verdict,
        }
        if diffs:
            entry["diffs"] = diffs
        results[data_name] = entry

        if diffs:
            failures.append(data_name)
            print(f"  FAIL  {data_name} ({xs_token})")
            for d in diffs:
                print(f"          -> {d}")
        else:
            print(f"  PASS  {data_name} ({xs_token})")

    print()
    total = len(results)
    passed = sum(1 for v in results.values() if v["verdict"] == "PASS")
    failed = len(failures)
    skipped = sum(1 for v in results.values() if v["verdict"] == "SKIP")

    overall_passed = failed == 0
    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }

    if overall_passed:
        print(f"PASS — {passed}/{total} civs pass spec-vs-XS doctrine check")
    else:
        print(f"FAIL — {failed}/{total} civs have spec-vs-XS doctrine mismatches:")
        for f in failures:
            e = results[f]
            if e.get("diffs"):
                for d in e["diffs"]:
                    print(f"  {f}: {d}")

    report = {
        "civs": results,
        "summary": summary,
        "passed": overall_passed,
    }

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 0 if overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
