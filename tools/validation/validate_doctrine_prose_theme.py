#!/usr/bin/env python3
"""Static validator: doctrine prose theme alignment with wall_strategy.

Locks the requirement that each civ's doctrine prose
(``doctrine_label`` + ``doctrine_summary`` + ``doctrine_prose``) contains
at least one keyword that thematically matches its declared
``wall_strategy``. Catches edits that change a civ's wall strategy
without updating the player-facing prose, or rewrites of prose that
contradict the AI doctrine.

This is a sanity check, not a strict natural-language parse — it works
because each strategy has a distinct vocabulary cluster:

  0 — FortressRing       : fortif / citadel / bastion / fortress / wall / hill-fort
  1 — ChokepointSegments : chokepoint / terrace / mountain / andean / jungle / highland
  2 — CoastalBatteries   : naval / coast / sea / dock / ship / fleet / corsair / harbor
  3 — FrontierPalisades  : frontier / palisade / distributed / outpost / civic / network
  4 — UrbanBarricade     : urban / barricade / levee / mass / industrial / republic
  5 — MobileNoWalls      : mobile / forward / raid / guerrilla / cavalry / steppe / shrine

A civ that misses ALL keywords for its declared strategy raises a FAIL.

Run::

    python3 tools/validation/validate_doctrine_prose_theme.py
    python3 tools/validation/validate_doctrine_prose_theme.py \
        --json artifacts/validation/doctrine_prose_theme.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SPEC_PATH = REPO_ROOT / "playstyle_spec.json"

# Keyword sets per wall_strategy. Stems / fragments are used (e.g.
# "fortif" matches both "fortify" and "fortified"). Curated to map
# the *style name vocabulary* + plausible thematic alternatives.
THEME_KEYWORDS: dict[int, list[str]] = {
    0: [
        "fortif", "citadel", "bastion", "fortress", "wall", "siege",
        "castle", "stronghold", "fort ", "fort.", "fort-", "hill-fort",
        "hold ", "anchor", "defen", "keep", "tower",
    ],
    1: [
        "chokepoint", "terrace", "mountain", "andean", "jungle",
        "narrow", "pass", "segment", "highland", "ridge", "pasture",
        "maya", "inca",
    ],
    2: [
        "naval", "coast", "mariti", "sea", "dock", "ship", "water",
        "fleet", "pirate", "corsair", "harbor", "port", "caravel",
        "frigate", "galley", "navy",
    ],
    3: [
        "frontier", "palisade", "distributed", "outpost", "patrol",
        "civic", "milit", "spread", "network", "levee",
    ],
    4: [
        "urban", "barricade", "levee", "mass", "mobilis", "industrial",
        "republic", "conscript", "levée",
    ],
    5: [
        "mobile", "forward", "aggress", "scatter", "raid", "guerrilla",
        "cavalry", "horse", "steppe", "no wall", "shrine", "trade",
        "wedge", "sweep", "flank", "corsair", "frontier",
    ],
}

STRATEGY_NAMES: dict[int, str] = {
    0: "FortressRing",
    1: "ChokepointSegments",
    2: "CoastalBatteries",
    3: "FrontierPalisades",
    4: "UrbanBarricade",
    5: "MobileNoWalls",
}


def evaluate_civ(token: str, civ: dict) -> dict:
    """Return verdict + diagnostics for one civ entry."""
    claims = civ.get("claims", {}) or {}
    ws = claims.get("wall_strategy")
    label = (civ.get("doctrine_label") or "").lower()
    summary = (civ.get("doctrine_summary") or "").lower()
    prose = (civ.get("doctrine_prose") or "").lower()
    combined = f"{label} | {summary} | {prose}"

    if ws is None:
        return {"verdict": "SKIP", "reason": "no wall_strategy claim"}

    keywords = THEME_KEYWORDS.get(ws)
    if keywords is None:
        return {
            "verdict": "ERROR",
            "reason": f"unknown wall_strategy={ws} (no keyword set)",
        }

    matched = [kw for kw in keywords if kw in combined]
    return {
        "verdict": "PASS" if matched else "FAIL",
        "wall_strategy": ws,
        "strategy_name": STRATEGY_NAMES.get(ws, "?"),
        "matched_keywords": matched,
        "doctrine_label": civ.get("doctrine_label"),
        "doctrine_summary": (civ.get("doctrine_summary") or "")[:140],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=SPEC_PATH)
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("DOCTRINE PROSE THEME ALIGNMENT")
    print("=" * 60)

    if not args.spec.exists():
        print(f"  ERROR: spec file not found: {args.spec}")
        return 2

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    civs = spec.get("civs", {}) or {}
    print(f"  Loaded {len(civs)} civs from playstyle_spec.json\n")

    results: dict[str, dict] = {}
    fails: list[str] = []
    for token, civ in civs.items():
        r = evaluate_civ(token, civ)
        results[token] = r
        if r["verdict"] == "PASS":
            print(f"  PASS  {token}  (ws={r['wall_strategy']}/"
                  f"{r['strategy_name']}, matched={len(r['matched_keywords'])})")
        elif r["verdict"] == "SKIP":
            print(f"  SKIP  {token}  ({r['reason']})")
        else:
            fails.append(token)
            print(f"  FAIL  {token}  (ws={r.get('wall_strategy')}/"
                  f"{r.get('strategy_name','?')})")
            print(f"          label:   {r.get('doctrine_label')!r}")
            print(f"          summary: {r.get('doctrine_summary')!r}")

    passed = sum(1 for v in results.values() if v["verdict"] == "PASS")
    failed = len(fails)
    total = len(results)
    print()
    if failed == 0:
        print(f"PASS — {passed}/{total} civs have theme-aligned doctrine prose")
    else:
        print(f"FAIL — {failed}/{total} civs have prose disconnected from wall_strategy")

    report = {
        "civs": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
        },
        "passed": failed == 0,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
