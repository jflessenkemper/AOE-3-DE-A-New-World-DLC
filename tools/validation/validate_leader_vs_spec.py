#!/usr/bin/env python3
"""validate_leader_vs_spec.py — static cross-check between
`game/ai/leaders/leader_*.xs` and `playstyle_spec.json`.

Why: each leader file invokes one of the `llUseXStyle()` helpers in
`leaderCommon.xs`, which locks down `gLLWallStrategy`,
`gLLBuildStyle`, and a default military-distance multiplier. The
playstyle_spec.json (extracted from a_new_world.html)
asserts what each civ *should* be doing. If a leader file's selected
style doesn't agree with the spec, the AI will play the wrong
doctrine — and the only signal today is a failed doctrine-compliance
report after a costly engine matrix run.

This linter parses both sides statically and reports mismatches
without ever launching the engine. Catches:
  • Wrong doctrine selected (style's wallStrategy ≠ spec's wall_strategy)
  • Per-leader overrides that contradict the style's defaults
    (e.g. a `gLLMilitaryDistanceMultiplier = 0.7` after a style that
    would normally land at 1.1, breaking the spec's [1.1, 1.3] band)

What it does NOT check (those need the engine):
  • Whether the AI actually *follows* the configured doctrine at runtime
    (that's `validate_doctrine_compliance.py` over match.log probes)
  • Tactics/composition emergent behaviour

CLI:
    python3 tools/validation/validate_leader_vs_spec.py
    # exit 0 = green, 1 = mismatches found

    --leaders DIR     override leaders dir (default: game/ai/leaders)
    --spec PATH       override playstyle_spec.json path
    --out PATH        write text report (default stdout)
    --allow-fail      exit 0 even on mismatches
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
LEADERS_DIR = REPO_ROOT / "game" / "ai" / "leaders"
SPEC_PATH = REPO_ROOT / "playstyle_spec.json"

# Wall strategy constant → int. Mirrors aiHeader.xs:202-207.
WALL_STRAT_INT = {
    "cLLWallStrategyFortressRing":        0,
    "cLLWallStrategyChokepointSegments":  1,
    "cLLWallStrategyCoastalBatteries":    2,
    "cLLWallStrategyFrontierPalisades":   3,
    "cLLWallStrategyUrbanBarricade":      4,
    "cLLWallStrategyMobileNoWalls":       5,
}
WALL_STRAT_NAME = {v: k.removeprefix("cLLWallStrategy") for k, v in WALL_STRAT_INT.items()}

# Runtime gLLLeaderKey (set in leaderCommon.xs cMyCiv switch) → spec slug.
# Kept in sync with tools/validation/validate_doctrine_compliance.py.
RUNTIME_TO_SPEC_LEADER = {
    "wellington": "elizabeth",
    "catherine":  "ivan",
    "crazyhorse": "gall",
    "jean":       "valette",        # Maltese: engine slug "jean", spec uses Valette
    "usman":      "muhammadu",      # Hausa: engine slug kept as Usman dan Fodio,
                                    # spec lists Muhammadu Kanta of Kebbi.
}

# Leader filename slug → runtime gLLLeaderKey. For 23/26 leader files
# the slug == gLLLeaderKey directly; the three exceptions are recorded
# explicitly. The two revolution dispatcher files (revolution_*) are
# skipped because they cover many revs in one file.
LEADER_FILE_TO_RUNTIME_KEY = {
    "valette":  "jean",   # leader_valette.xs sets gLLLeaderKey="jean" (Maltese)
    "crazy_horse": "crazyhorse",  # underscore in filename, no underscore in key
}


# ─── parsing helpers ───────────────────────────────────────────────────────

# Map from `llUseXStyle()` helper name → (build_style_const, wall_strategy_const).
# Built by parsing leaderCommon.xs once. We extract every void-defn block of
# the form `void llUseXStyle(...){ … gLLWallStrategy = ...; … }`.
STYLE_HELPER_RX = re.compile(
    r"void\s+(llUse\w+Style)\s*\([^)]*\)\s*\{(.*?)\n\}", re.DOTALL
)
WALL_ASSIGN_RX = re.compile(r"gLLWallStrategy\s*=\s*(cLLWallStrategy\w+)")
BUILD_ASSIGN_RX = re.compile(r"cLLBuildStyle(\w+)")


def parse_style_helpers(common_xs: Path) -> dict[str, dict[str, Any]]:
    """Return {helper_name: {wall_strategy: int, build_style: str}}."""
    text = common_xs.read_text(encoding="utf-8", errors="replace")
    out: dict[str, dict[str, Any]] = {}
    for m in STYLE_HELPER_RX.finditer(text):
        name = m.group(1)
        body = m.group(2)
        wm = WALL_ASSIGN_RX.search(body)
        bm = BUILD_ASSIGN_RX.search(body)
        if not wm and not bm:
            continue
        info: dict[str, Any] = {}
        if wm:
            info["wall_strategy"] = WALL_STRAT_INT.get(wm.group(1))
            info["wall_strategy_name"] = wm.group(1).removeprefix("cLLWallStrategy")
        if bm:
            info["build_style"] = "cLLBuildStyle" + bm.group(1)
        out[name] = info
    return out


# `gLLLeaderKey = "elizabeth"` style assignments in leaderCommon.xs
LEADER_KEY_RX = re.compile(r'gLLLeaderKey\s*=\s*"([a-zA-Z_]+)"')


def parse_leader_file(path: Path, helpers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Pull every llUse*Style() call + post-call gLL* override out of a
    leader file. Last write wins (engine semantics).

    For wall_strategy, any explicit ``gLLWallStrategy = cLLWallStrategy<X>``
    assignment that appears *after* the last llUse*Style() call in the file
    is treated as a spec override and takes precedence over the helper's
    default. This avoids false-positives when a leader file intentionally
    overrides the helper's wall strategy (e.g. Montezuma, Pachacuti).
    """
    text = path.read_text(encoding="utf-8", errors="replace")

    # Find position of last style-helper call so we can check for
    # post-helper gLLWallStrategy overrides.
    style_call_matches = list(re.finditer(r"(llUse\w+Style)\s*\(", text))
    style_calls = [m.group(1) for m in style_call_matches]
    direct_mdist = re.findall(r"gLLMilitaryDistanceMultiplier\s*=\s*([\d.]+)", text)

    style = style_calls[-1] if style_calls else None
    style_info = helpers.get(style, {}) if style else {}

    # Effective wall_strategy: start from the style helper's default, then
    # check for any explicit gLLWallStrategy assignment that appears AFTER
    # the last helper call in this leader file. Such post-helper overrides
    # are intentional spec overrides and must take precedence.
    effective_wall = style_info.get("wall_strategy")
    wall_override_const: Optional[str] = None

    if style_call_matches:
        helper_end_pos = style_call_matches[-1].end()
        post_helper_text = text[helper_end_pos:]
        post_walls = WALL_ASSIGN_RX.findall(post_helper_text)
        if post_walls:
            # Last post-helper assignment wins.
            wall_override_const = post_walls[-1]
            effective_wall = WALL_STRAT_INT.get(wall_override_const, effective_wall)
    else:
        # No style helper at all — check the whole file for a direct assign.
        direct_walls = WALL_ASSIGN_RX.findall(text)
        if direct_walls:
            wall_override_const = direct_walls[-1]
            effective_wall = WALL_STRAT_INT.get(wall_override_const, effective_wall)

    return {
        "file": path.name,
        "selected_style": style,
        "style_wall_strategy": style_info.get("wall_strategy"),
        "effective_wall_strategy": effective_wall,
        # Non-None when a post-helper direct assignment overrides the style.
        "wall_strategy_override_const": wall_override_const,
        "build_style": style_info.get("build_style"),
        "leader_key_assigns": LEADER_KEY_RX.findall(text),
        "mdist_overrides": [float(x) for x in direct_mdist],
    }


# ─── leader file → spec key resolution ─────────────────────────────────────

def _slug_from_filename(path: Path) -> str:
    """leader_wellington.xs → 'wellington'; leader_crazy_horse.xs → 'crazy_horse'."""
    return path.stem.removeprefix("leader_")


def _spec_key_for_leader(slug: str, runtime_keys: list[str],
                         spec: dict[str, Any]) -> Optional[str]:
    """Resolve a leader filename slug to a playstyle_spec.json key.

    Strategy:
      1) leader filename → runtime gLLLeaderKey via the explicit map or
         identity (leader_<slug>.xs ⇒ slug),
      2) runtime key → spec leader slug via RUNTIME_TO_SPEC_LEADER bridge,
      3) spec leader slug → spec data-name by linear scan over civs.
    """
    runtime = LEADER_FILE_TO_RUNTIME_KEY.get(slug, slug)
    spec_ldr = RUNTIME_TO_SPEC_LEADER.get(runtime, runtime)

    # Find the data-name whose leader_label starts with the spec slug
    # (case-insensitive). E.g. spec slug 'elizabeth' → 'British Elizabeth'
    # whose leader_label is 'Queen Elizabeth I'.
    target = spec_ldr.lower()
    for k, v in spec["civs"].items():
        ll = (v.get("leader_label") or "").lower()
        if target in ll:
            return k
        # Fall back to data-name slug match (revolutions: 'anwbrazil'
        # → data-name 'Brazil Pedro II' won't match leader_label, but
        # the runtime slug matches the chatset key one-to-one — for
        # revolutions the LEADER files are revolution_commanders /
        # revolution_support, which we skip below).
    return None


# ─── per-civ check ─────────────────────────────────────────────────────────

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
SKIP = "SKIP"


def check_leader(parsed: dict[str, Any], spec_entry: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return list of (status, claim, msg) tuples."""
    out: list[tuple[str, str, str]] = []
    claims = spec_entry.get("claims", {})

    # Wall strategy.
    if "wall_strategy" in claims:
        expected = claims["wall_strategy"]
        actual = parsed.get("effective_wall_strategy")
        if actual is None:
            out.append((WARN, "wall_strategy",
                f"no llUse*Style() call found; spec wants {WALL_STRAT_NAME.get(expected,'?')}({expected})"))
        elif actual != expected:
            via_str = parsed['selected_style']
            if parsed.get("wall_strategy_override_const"):
                via_str = f"gLLWallStrategy override after {via_str}"
            out.append((FAIL, "wall_strategy",
                f"file picks {WALL_STRAT_NAME.get(actual,'?')}({actual}) "
                f"via {via_str}, spec wants "
                f"{WALL_STRAT_NAME.get(expected,'?')}({expected})"))
        else:
            via_str = parsed['selected_style']
            if parsed.get("wall_strategy_override_const"):
                via_str = f"gLLWallStrategy override after {via_str}"
            out.append((PASS, "wall_strategy",
                f"{WALL_STRAT_NAME.get(actual,'?')} (via {via_str})"))

    # Military distance band — last gLLMilitaryDistanceMultiplier
    # override in the leader file vs. the band claim. If the leader file
    # never overrides, we trust the style helper's default (stored
    # implicitly inside llConfigureBuildStyleProfile and not parsed
    # here, so we can only check explicit overrides).
    if "military_distance_band" in claims and parsed["mdist_overrides"]:
        lo, hi = claims["military_distance_band"]
        actual = parsed["mdist_overrides"][-1]
        if not (lo <= actual <= hi):
            out.append((FAIL, "military_distance_band",
                f"leader-file override gLLMilitaryDistanceMultiplier={actual} "
                f"is outside spec band [{lo}, {hi}]"))
        else:
            out.append((PASS, "military_distance_band",
                f"override {actual} ∈ [{lo}, {hi}]"))

    return out


# ─── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--leaders", type=Path, default=LEADERS_DIR)
    ap.add_argument("--spec",    type=Path, default=SPEC_PATH)
    ap.add_argument("--out",     type=Path, default=None)
    ap.add_argument("--allow-fail", action="store_true")
    args = ap.parse_args()

    if not args.spec.exists():
        print(f"missing spec {args.spec}; run extract_playstyle_spec.py first",
              file=sys.stderr)
        return 2
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    common_xs = args.leaders / "leaderCommon.xs"
    helpers = parse_style_helpers(common_xs)

    # Collect runtime keys from leaderCommon for diagnostic clarity.
    runtime_keys = LEADER_KEY_RX.findall(common_xs.read_text(encoding="utf-8"))

    leader_files = sorted(p for p in args.leaders.glob("leader_*.xs")
                          if not p.name.startswith("leader_revolution_"))

    lines: list[str] = []
    lines.append(f"=== LEADER VS SPEC LINTER ===")
    lines.append(f"helpers parsed: {len(helpers)}")
    lines.append(f"leader files:   {len(leader_files)} (revolution dispatchers skipped)")
    lines.append("")

    overall = Counter()
    fail_count = 0
    for f in leader_files:
        slug = _slug_from_filename(f)
        spec_key = _spec_key_for_leader(slug, runtime_keys, spec)
        parsed = parse_leader_file(f, helpers)

        if spec_key is None:
            lines.append(f"[SKIP] {f.name}: no spec entry resolvable from slug={slug}")
            overall[SKIP] += 1
            continue

        results = check_leader(parsed, spec["civs"][spec_key])
        if not results:
            lines.append(f"[----] {f.name} → {spec_key}  (no checkable claims)")
            continue

        verdict = FAIL if any(s == FAIL for s, _, _ in results) else PASS
        overall[verdict] += 1
        if verdict == FAIL:
            fail_count += 1
        lines.append(f"[{verdict}] {f.name} → {spec_key}")
        for status, claim, msg in results:
            mark = {PASS: "  ✓", FAIL: "  ✗", WARN: "  ?"}[status]
            lines.append(f"{mark} {claim:<25s} {msg}")

    lines.append("")
    lines.append(f"=== SUMMARY: {overall[PASS]} pass / {overall[FAIL]} fail "
                 f"/ {overall[SKIP]} skipped over {len(leader_files)} files ===")

    text = "\n".join(lines)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    if fail_count and not args.allow_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
