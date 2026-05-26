#!/usr/bin/env python3
"""Catch shared doctrine_prose templates that drift from their civs' claims.

The HTML reference (``a_new_world.html``) groups civs that share a
playstyle "template" — naval mercantile, forward operational, fortress
ring, etc.  Each shared template appears as identical
``doctrine_prose`` text on every civ in the group inside
``playstyle_spec.json``.

When a civ's mechanical ``claims`` block (wall_strategy,
first_military_building, expects_naval, etc.) diverges from its
template peers, the player reads a doctrine description that doesn't
match what the AI actually does in-game.  This is rank #8 in
``docs/TEST_COVERAGE_PLAN.md`` — "template drift": the prose says one
thing, the engine spec says another, and a release should not ship
that.

Strategy
========

1. Walk ``playstyle_spec.json`` and bucket civs by their
   ``doctrine_prose`` text (normalised whitespace).
2. For each bucket with two or more civs, verify that the *critical*
   fields in ``claims`` match across the bucket.  Critical fields:

     - ``wall_strategy``
     - ``first_military_building``
     - any ``expects_*`` boolean

3. Non-critical fields (timing bands, distance bands) are allowed to
   vary — those are per-civ tuning.

4. Any divergence is flagged as drift with the bucket's prose excerpt
   and the conflicting civs + values.

Usage::

    python3 tools/validation/validate_doctrine_template_drift.py
    python3 tools/validation/validate_doctrine_template_drift.py \\
        --json artifacts/validation/doctrine_template_drift.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Claims fields that MUST match across every civ sharing a prose template.
CRITICAL_FIELDS = ("wall_strategy", "first_military_building")
# Any field whose name starts with this prefix is also treated as critical.
CRITICAL_PREFIX = "expects_"


def _normalise_prose(p: str) -> str:
    """Strip HTML entities and collapse whitespace for bucketing."""
    p = re.sub(r"&[a-zA-Z]+;|&#x[0-9a-fA-F]+;|&#\d+;", " ", p)
    p = re.sub(r"\s+", " ", p).strip()
    return p


def _critical_signature(claims: dict) -> dict:
    """Pull out the fields that must match across the bucket."""
    sig: dict = {}
    for k, v in claims.items():
        if k in CRITICAL_FIELDS or k.startswith(CRITICAL_PREFIX):
            sig[k] = v
    return sig


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path,
                    default=REPO_ROOT / "playstyle_spec.json")
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("DOCTRINE TEMPLATE DRIFT")
    print("=" * 60)

    if not args.spec.exists():
        print(f"  ✗ spec file not found: {args.spec}")
        return 1

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    civs = spec.get("civs", {})
    print(f"  Scanning {len(civs)} civs in playstyle_spec.json…")

    # Bucket by normalised prose.
    buckets: dict[str, list[tuple[str, dict]]] = {}
    for civ_name, civ in civs.items():
        prose = _normalise_prose(civ.get("doctrine_prose", ""))
        if not prose:
            continue
        buckets.setdefault(prose, []).append((civ_name, civ.get("claims", {})))

    # Only buckets with 2+ civs share a template.
    shared = {k: v for k, v in buckets.items() if len(v) >= 2}
    print(f"  Found {len(shared)} shared doctrine templates")
    print()

    drifts: list[dict] = []
    bucket_report: dict[str, dict] = {}

    for prose, members in shared.items():
        # Compute the per-civ critical signatures.
        sigs = {name: _critical_signature(claims) for name, claims in members}
        # All sigs must be equal.  Find the dominant (first) sig and report
        # any divergent civs.
        reference_name, reference_sig = next(iter(sigs.items()))
        divergent: list[dict] = []
        for name, sig in sigs.items():
            if sig != reference_sig:
                # Field-level diff for the report
                diff = {}
                all_keys = set(reference_sig) | set(sig)
                for k in sorted(all_keys):
                    if reference_sig.get(k) != sig.get(k):
                        diff[k] = {
                            "reference": reference_sig.get(k),
                            "civ_value": sig.get(k),
                        }
                divergent.append({"civ": name, "diff": diff})

        excerpt = prose[:60] + ("…" if len(prose) > 60 else "")
        bucket_entry = {
            "prose_excerpt": excerpt,
            "members": [name for name, _ in members],
            "reference_civ": reference_name,
            "reference_signature": reference_sig,
            "divergent": divergent,
        }
        bucket_report[excerpt] = bucket_entry

        if divergent:
            drifts.append(bucket_entry)
            print(f"  ✗ Drift in template: \"{excerpt}\"")
            print(f"      Reference civ: {reference_name} → {reference_sig}")
            for d in divergent:
                print(f"      → {d['civ']} diverges on: {list(d['diff'].keys())}")
        else:
            print(f"  ✓ \"{excerpt}\" — {len(members)} civs aligned")

    print()
    if drifts:
        print(f"FAIL — {len(drifts)} doctrine template(s) have drifting civs")
    else:
        print("PASS — every shared doctrine_prose template has consistent claims across all civs")

    report = {
        "buckets": bucket_report,
        "drifts": drifts,
        "passed": not drifts,
    }

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 1 if drifts else 0


if __name__ == "__main__":
    sys.exit(main())
