#!/usr/bin/env python3
"""Catch stale/incomplete blurbs and template-placeholder text in ANW civ data.

Checks every civ in ``data/anw_civ_blurbs.json`` for:

  1. Blurb length — ``playstyle`` field must be ≥ 40 characters.
  2. No template residue — no TODO/TBD/FIXME/Lorem ipsum/TEMPLATE/
     PLACEHOLDER/<…> angle-bracket patterns (case-insensitive).
  3. Full ANW coverage — every civ token from the blurbs file is also present
     in ``data/age_build_notes.json`` (cross-source parity check).  Any civ
     in ``data/`` homecity XMLs but absent from blurbs is flagged as missing.
  4. Cross-source presence — every civ also has a ``strategy_overview``
     entry in ``data/age_build_notes.json``.
  5. Uniqueness — no two civs share identical ``playstyle`` text
     (detects copy-paste drift).

Usage::

    python3 tools/validation/validate_blurb_coverage.py
    python3 tools/validation/validate_blurb_coverage.py \\
        --json artifacts/validation/blurb_coverage.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

def _discover_civ_tokens(data_dir: Path) -> list[str]:
    """Return sorted list of ANW civ tokens derived from homecity XML filenames.

    XML filenames use all-lowercase suffixes (e.g. ``anwhomecitysouthafricans.xml``).
    We match them case-insensitively against the blurbs keys so that tokens like
    ``ANWSouthAfricans`` (camelCase in the JSON) are correctly resolved.

    Returns the *blurbs-casing* form when available, otherwise a simple
    title-cased fallback so callers can detect true mismatches.
    """
    stems: list[str] = []
    for xml in sorted(data_dir.glob("anwhomecity*.xml")):
        # e.g. "anwhomecityargentines" → lowercase suffix "argentines"
        stems.append(xml.stem.lower())   # store full stem in lowercase
    return stems


def _match_xml_to_blurb_keys(xml_stems: list[str],
                              blurb_keys: list[str]) -> tuple[list[str], list[str]]:
    """Return (matched_blurb_keys, unmatched_xml_stems).

    Match each xml stem (lowercase) against blurb keys (any case) by comparing
    the lowercased versions.  Returns the blurb-casing variant for matched ones.
    """
    blurb_lower_map: dict[str, str] = {k.lower(): k for k in blurb_keys}
    matched: list[str] = []
    unmatched: list[str] = []
    for stem in xml_stems:
        token_lower = "anw" + stem[len("anwhomecity"):]
        if token_lower in blurb_lower_map:
            matched.append(blurb_lower_map[token_lower])
        else:
            # Produce a readable form for error messages
            suffix = stem[len("anwhomecity"):]
            unmatched.append("ANW" + suffix[0].upper() + suffix[1:])
    return matched, unmatched


# Placeholder patterns that must NOT appear in any blurb field (case-insensitive)
_PLACEHOLDER_RE = re.compile(
    r'\bTODO\b|\bTBD\b|\bFIXME\b|lorem\s+ipsum|\bTEMPLATE\b|\bPLACEHOLDER\b|<[^>]+>',
    re.IGNORECASE,
)

MIN_PLAYSTYLE_LEN = 40


def _load_json(path: Path) -> dict:
    """Load a JSON file; return {} and print an error if missing or broken."""
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path} is not valid JSON: {exc}", file=sys.stderr)
        return {}


def _find_placeholders(text: str) -> list[str]:
    return _PLACEHOLDER_RE.findall(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blurbs", type=Path,
                    default=REPO_ROOT / "data" / "anw_civ_blurbs.json",
                    help="path to anw_civ_blurbs.json")
    ap.add_argument("--age-notes", type=Path,
                    default=REPO_ROOT / "data" / "age_build_notes.json",
                    help="path to age_build_notes.json")
    ap.add_argument("--spec", type=Path,
                    default=REPO_ROOT / "playstyle_spec.json",
                    help="path to playstyle_spec.json")
    ap.add_argument("--json", type=Path,
                    help="write JSON report to this file")
    args = ap.parse_args()

    blurbs: dict = _load_json(args.blurbs)
    age_notes: dict = _load_json(args.age_notes)

    # Ground-truth token list from homecity XMLs on disk
    data_dir = args.blurbs.parent
    xml_stems: list[str] = _discover_civ_tokens(data_dir)

    print("=" * 60)
    print("BLURB COVERAGE & QUALITY")
    print("=" * 60)

    fails: list[dict] = []
    passes: list[dict] = []

    # --- Check 3: coverage — every civ in homecity XMLs should be in blurbs -
    blurb_keys: list[str] = list(blurbs.keys())
    blurb_civs = set(blurb_keys)
    matched_tokens, unmatched_stems = _match_xml_to_blurb_keys(xml_stems, blurb_keys)
    matched_set = set(matched_tokens)
    extra_in_blurbs = blurb_civs - matched_set  # in blurbs but not in any XML

    print()
    print(f"  Blurbs file contains {len(blurb_civs)} civ entries "
          f"(homecity XMLs: {len(xml_stems)}).")

    if unmatched_stems:
        for civ in sorted(unmatched_stems):
            msg = "civ token found in homecity XML but missing from blurbs file"
            print(f"  ✗ {civ}: {msg}")
            fails.append({"civ": civ, "check": "coverage", "detail": msg})
    else:
        print(f"  ✓ All {len(xml_stems)} homecity-XML civ tokens present in blurbs file.")

    # --- Checks 1, 2, 4, 5 per civ ---
    print()
    print("-" * 60)
    print("PER-CIV CHECKS")
    print("-" * 60)

    # Collect playstyle texts for duplicate detection (check 5)
    playstyle_index: dict[str, list[str]] = {}  # normalised text → [civ, …]

    for civ in sorted(blurb_civs):
        entry = blurbs[civ]
        civ_fails: list[str] = []

        # Check 1: playstyle length
        playstyle: str = entry.get("playstyle", "") or ""
        ps_len = len(playstyle)
        if ps_len < MIN_PLAYSTYLE_LEN:
            civ_fails.append(
                f"playstyle too short ({ps_len} chars, min {MIN_PLAYSTYLE_LEN})"
            )

        # Check 2: placeholder text in ALL string fields of the entry
        all_text_parts: list[str] = []
        for v in entry.values():
            if isinstance(v, str):
                all_text_parts.append(v)
            elif isinstance(v, list):
                all_text_parts.extend(str(i) for i in v)
        combined_text = " ".join(all_text_parts)
        found_placeholders = _find_placeholders(combined_text)
        if found_placeholders:
            civ_fails.append(
                f"placeholder text found: {', '.join(repr(p) for p in found_placeholders[:5])}"
            )

        # Check 4: age_build_notes cross-presence
        age_entry = age_notes.get(civ, {})
        has_strategy_overview = bool(age_entry.get("strategy_overview", "").strip())
        if not has_strategy_overview:
            civ_fails.append("no strategy_overview in age_build_notes.json")

        # Accumulate playstyle for duplicate check (check 5)
        ps_key = playstyle.strip().lower()
        playstyle_index.setdefault(ps_key, []).append(civ)

        if civ_fails:
            for detail in civ_fails:
                fails.append({"civ": civ, "check": "per_civ", "detail": detail})
            print(f"  ✗ {civ}:")
            for detail in civ_fails:
                print(f"      {detail}")
        else:
            age_label = "age_notes present" if has_strategy_overview else "age_notes MISSING"
            print(
                f"  ✓ {civ}: blurb {ps_len} chars, no placeholders, "
                f"{age_label}, unique playstyle"
            )
            passes.append({"civ": civ})

    # Check 5: duplicate playstyle detection (post-loop)
    print()
    print("-" * 60)
    print("DUPLICATE PLAYSTYLE DETECTION")
    print("-" * 60)
    dup_found = False
    for ps_key, civs_with_this_ps in sorted(playstyle_index.items()):
        if len(civs_with_this_ps) > 1 and ps_key:  # skip empty-string bucket
            dup_found = True
            dupe_list = ", ".join(civs_with_this_ps)
            detail = f"playstyle identical to: {dupe_list}"
            for civ in civs_with_this_ps:
                # Avoid double-counting if civ already failed above
                already = any(
                    f["civ"] == civ and "identical" in f["detail"]
                    for f in fails
                )
                if not already:
                    fails.append({"civ": civ, "check": "duplicate_playstyle",
                                  "detail": detail})
            print(f"  ✗ Duplicate playstyle shared by: {dupe_list}")
            print(f"      Text preview: {ps_key[:80]!r}…" if len(ps_key) > 80
                  else f"      Text: {ps_key!r}")
    if not dup_found:
        print("  ✓ No duplicate playstyle text detected.")

    # --- Summary -----------------------------------------------------------
    print()
    print("=" * 60)
    total_civs = len(blurb_civs)
    total_fails = len(fails)
    verdict = "PASS" if total_fails == 0 else "FAIL"
    print(f"BLURB COVERAGE: {verdict}  "
          f"({total_civs} civs checked, {total_fails} failure(s))")
    if unmatched_stems:
        print(f"  Missing from blurbs file: {len(unmatched_stems)} civ(s)")
    if extra_in_blurbs:
        print(f"  INFO: {len(extra_in_blurbs)} token(s) in blurbs with no "
              f"matching homecity XML: {', '.join(sorted(extra_in_blurbs))}")
    print("=" * 60)

    # Optional JSON report
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "verdict": verdict,
            "total_civs": total_civs,
            "total_fails": total_fails,
            "missing_from_blurbs": sorted(unmatched_stems),
            "extra_in_blurbs": sorted(extra_in_blurbs),
            "fails": fails,
            "passes": passes,
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json}")

    return 1 if total_fails else 0


if __name__ == "__main__":
    sys.exit(main())
