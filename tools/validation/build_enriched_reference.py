#!/usr/bin/env python3
"""Merge playstyle_spec.json claims into reference_matrix.json.

The reference_matrix.json (built from a_new_world.html) has per-civ metadata
but no testable assertions. The playstyle_spec.json has detailed `claims`
per civ:

    {
      "wall_strategy": 2,
      "first_military_building": "dock",
      "expects_naval": true,
      "first_dock_before_ms": 360000,
      "first_wall_before_ms": 900000,
      "military_distance_band": [0.9, 1.2]
    }

This script merges those claims into each civ entry in reference_matrix.json
and writes an enriched_reference.json that the validator can consume directly.

Usage:
    python3 build_enriched_reference.py [--output enriched_reference.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

DEFAULT_REF = REPO_ROOT / "reference_matrix.json"
DEFAULT_PLAY = REPO_ROOT / "playstyle_spec.json"
DEFAULT_DECKS = REPO_ROOT / "data" / "decks_anw.json"
DEFAULT_BLURBS = REPO_ROOT / "data" / "anw_civ_blurbs.json"
DEFAULT_OUT = REPO_ROOT / "enriched_reference.json"


def find_playstyle_for_civ(
    playstyle_spec: dict[str, Any],
    anw_token: str,
    data_name: str,
    playstyle_section: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Find the playstyle entry for a civ.

    The playstyle_spec.civs dict is keyed by data_name (e.g., 'British Elizabeth').
    We try (in order):
      1. exact match on data_name
      2. match the civ_label + leader_label combination
      3. anw_token-based heuristic (strip 'ANW' prefix, fuzzy match)
    """
    civs = playstyle_spec.get("civs", {})

    if data_name and data_name in civs:
        return civs[data_name]

    if playstyle_section:
        civ_label = playstyle_section.get("civ_label", "")
        leader_label = playstyle_section.get("leader_label", "")
        composite = f"{civ_label} {leader_label}".strip()
        if composite in civs:
            return civs[composite]

    # Fuzzy: strip "ANW" prefix from token, look for civ entries containing it
    bare = anw_token.replace("ANW", "")
    for key, entry in civs.items():
        if entry.get("civ_label", "").lower().replace(" ", "") == bare.lower():
            return entry
    return None


def to_validator_spec(
    civ_record: dict[str, Any],
    playstyle_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the spec dict the validator consumes for a single civ.

    Maps:
      claims.wall_strategy             → spec.wall_strategy
      claims.military_distance_band    → spec.military_distance_band
      claims.first_military_building   → spec.expected_milestones.{barracks,stable,dock}
      claims.expects_naval             → spec.expected_milestones.dock = True
      claims.first_dock_before_ms      → spec.dock_deadline_ms
      claims.first_wall_before_ms      → spec.wall_deadline_ms (and expects.wall_segment)
      build_style derived from doctrine_label
    """
    spec: dict[str, Any] = {
        "anw_token": civ_record.get("anw_token"),
        "display_name": civ_record.get("display_name"),
        "data_name": civ_record.get("data_name"),
        "playstyle_spec": civ_record.get("playstyle_spec", {}),
        "expected_milestones": {},
    }
    if not playstyle_entry:
        return spec

    claims = playstyle_entry.get("claims", {}) or {}

    # 1. Wall strategy
    if "wall_strategy" in claims:
        spec["wall_strategy"] = claims["wall_strategy"]

    # 2. Military distance band
    if "military_distance_band" in claims:
        spec["military_distance_band"] = claims["military_distance_band"]

    # 3. First military building → which milestone is required
    fmb = claims.get("first_military_building")
    if fmb == "dock":
        spec["expected_milestones"]["dock"] = True
    elif fmb == "barracks":
        spec["expected_milestones"]["barracks"] = True
    elif fmb == "stable":
        spec["expected_milestones"]["stable"] = True
    elif fmb == "barracks_or_stable":
        # universal expectation; validator already handles via the unified check
        pass

    # 4. Naval civs need a dock
    if claims.get("expects_naval"):
        spec["expected_milestones"]["dock"] = True

    # 5. Wall expectation
    if "first_wall_before_ms" in claims:
        spec["expected_milestones"]["wall_segment"] = True
        spec["wall_deadline_ms"] = claims["first_wall_before_ms"]

    # 6. Forward-base expectation
    if claims.get("expects_forward"):
        spec["expected_milestones"]["forward_base"] = True

    # 7. Trading post (if civ doctrine emphasises trade)
    doctrine = (playstyle_entry.get("doctrine_label") or "").lower()
    if any(k in doctrine for k in ["trade", "mercantile", "trading"]):
        spec["expected_milestones"]["trading_post"] = True

    # 8. Doctrine label → build_style enum (cLLBuildStyle* in aiHeader.xs)
    # Mapping is normalised: lowercase, dash/hyphen stripped, " or " removed.
    # Some doctrine labels in playstyle_spec.json use synonyms ("Plains" for
    # "Steppe", "Streltsy siege" for "Siege Train Concentration") — handle
    # those via secondary aliases.
    BUILD_STYLE_MAP = {
        "compact fortified core": 1,
        "distributed economic network": 2,
        "forward operational line": 3,
        "mobile frontier scatter": 4,
        "shrine trade node spread": 5,
        "civic militia center": 6,
        "steppe cavalry wedge": 7,
        "plains cavalry wedge": 7,           # alias of Steppe
        "naval mercantile compound": 8,
        "siege train concentration": 9,
        "streltsy siege": 9,                 # Russian variant of Siege Train
        "jungle guerrilla network": 10,
        "highland citadel": 11,
        "cossack voisko": 12,
        "republican levee": 13,
        "andean terrace fortress": 14,
    }
    # Normalise: lowercase, strip dashes/hyphens, replace " or " with space
    norm = doctrine.replace("-", " ").replace(" or ", " ")
    norm = " ".join(norm.split())  # collapse whitespace
    bs = BUILD_STYLE_MAP.get(norm)
    if bs is not None:
        spec["build_style"] = bs

    # 9. Pass-through metadata
    spec["doctrine_label"] = playstyle_entry.get("doctrine_label")
    spec["doctrine_summary"] = playstyle_entry.get("doctrine_summary")
    spec["doctrine_prose"] = playstyle_entry.get("doctrine_prose")

    return spec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", type=Path, default=DEFAULT_REF)
    ap.add_argument("--playstyle", type=Path, default=DEFAULT_PLAY)
    ap.add_argument("--decks", type=Path, default=DEFAULT_DECKS)
    ap.add_argument("--blurbs", type=Path, default=DEFAULT_BLURBS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.reference.exists():
        print(f"missing: {args.reference}", file=sys.stderr)
        return 1
    if not args.playstyle.exists():
        print(f"missing: {args.playstyle}", file=sys.stderr)
        return 1

    with open(args.reference) as f:
        reference = json.load(f)
    with open(args.playstyle) as f:
        playstyle = json.load(f)
    decks = {}
    if args.decks.exists():
        with open(args.decks) as f:
            decks = json.load(f)
    blurbs = {}
    if args.blurbs.exists():
        with open(args.blurbs) as f:
            blurbs = json.load(f)

    out = {
        "schema_version": 3,
        "generated_from": [str(args.reference), str(args.playstyle),
                           str(args.decks), str(args.blurbs)],
        "total_civs": reference.get("total_civs", 0),
        "doctrines_per_civ": reference.get("doctrines_per_civ", 0),
        "civs": {},
    }

    matched = 0
    unmatched: list[str] = []
    for civ_token, civ_record in reference.get("civs", {}).items():
        ps_entry = find_playstyle_for_civ(
            playstyle,
            civ_token,
            civ_record.get("data_name", ""),
            civ_record.get("playstyle_spec"),
        )
        if ps_entry:
            matched += 1
        else:
            unmatched.append(civ_token)
        spec = to_validator_spec(civ_record, ps_entry)
        # Merge in deck (per-civ list of card IDs by age)
        if civ_token in decks:
            spec["expected_deck"] = decks[civ_token]
        # Merge in blurb (description text)
        if civ_token in blurbs:
            spec["blurb"] = blurbs[civ_token]
        out["civs"][civ_token] = spec

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)

    print(f"Wrote {args.output}")
    print(f"  matched: {matched}/{len(reference.get('civs', {}))}")
    if unmatched:
        print(f"  unmatched ({len(unmatched)}): {unmatched[:5]}{'...' if len(unmatched) > 5 else ''}")

    # Show sample of enriched data
    sample = next(iter(out["civs"].values()))
    print()
    print("Sample enriched record:")
    print(json.dumps(sample, indent=2)[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
