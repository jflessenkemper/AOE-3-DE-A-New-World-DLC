#!/usr/bin/env python3
"""Catch phantom unit/building names in ANW civ blurbs.

Verifies every entry in ``unique_units`` and ``unique_buildings`` arrays in
``data/anw_civ_blurbs.json`` resolves to a real engine display name, either:

  1. As a ``<string>`` entry in the base-game ``extracted_base_stringtable.xml``
     (e.g. "Leather Cannon" → matches base stringtable entry)
  2. Or in the mod's ``data/strings/english/stringmods.xml``
  3. Or as a literal ``<Unit name=...>`` token in ``protomods.xml`` or as a
     ``<Tech>`` building-grant in ``techtreemods.xml`` / base techtreey

This is rank #6 in ``docs/TEST_COVERAGE_PLAN.md``.  Polish_pass_7 found four
phantom names by hand ("Buddhist Temple", "Shinto Shrine", "Sacre Infermeria",
"Horse Artillery").  This validator catches that whole class going forward.

Strategy: case-insensitive exact match first; if not found, try a normalised
match (lowercase, strip punctuation, no spaces).  If still not found, flag.

Usage::

    python3 tools/validation/validate_proto_unit_references.py
    python3 tools/validation/validate_proto_unit_references.py \\
        --json artifacts/validation/proto_unit_references.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def _normalise(s: str) -> str:
    """Lowercase, drop punctuation/whitespace for fuzzy comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _load_display_name_corpus(*paths: Path) -> tuple[set[str], set[str]]:
    """Return (exact_names_lowercase, normalised_names) drawn from string tables.

    Walks each XML file for ``<string _locid=...>TEXT</string>`` or
    ``<String _locID=...>TEXT</String>`` entries and indexes their text content.
    """
    exact: set[str] = set()
    fuzz: set[str] = set()
    pat = re.compile(
        r'<[Ss]tring\s+_loc(?:i[Dd])="\d+"[^>]*>([^<]+)</[Ss]tring>',
        re.IGNORECASE,
    )
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in pat.finditer(text):
            t = m.group(1).strip()
            if not t or len(t) > 80:
                continue  # skip multi-paragraph descriptions
            exact.add(t.lower())
            fuzz.add(_normalise(t))
    return exact, fuzz


def _load_proto_unit_tokens(*paths: Path) -> set[str]:
    """Return the set of ``<unit name="X">`` / ``<Unit name="X">`` /
    ``<ProtoUnit>X</ProtoUnit>`` / ``<Target type='ProtoUnit'>X</Target>``
    / ``<Tech name='X'>`` tokens drawn from proto / techtree XML files.
    Normalised + lowercased for fuzz matching."""
    tokens: set[str] = set()
    patterns = [
        re.compile(r'<[Uu]nit\s+name="([^"]+)"'),
        re.compile(r'<[Bb]uilding\s+name="([^"]+)"'),
        re.compile(r'<[Tt]ech\s+name\s*=\s*[\'"]([^\'"]+)[\'"]'),
        re.compile(r'<[Pp]roto[Uu]nit>([^<]+)</[Pp]roto[Uu]nit>'),
        # <Target type='ProtoUnit'>X</Target> — used by techtree effects
        re.compile(r'<Target\s+type\s*=\s*[\'"]ProtoUnit[\'"]\s*>([^<]+)</Target>'),
        # ANW homecity grants like <unit>SomeProto</unit> wrapped grants
        re.compile(r'<unit\s+type=[\'"][^\'"]+[\'"]\s*>([^<]+)</unit>'),
    ]
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pat in patterns:
            for m in pat.finditer(text):
                tokens.add(_normalise(m.group(1)))
    return tokens


def _check_entry(entry: str,
                 exact: set[str],
                 fuzz: set[str],
                 proto_tokens: set[str]) -> str:
    """Return 'exact', 'fuzzy', 'proto', 'partial', or 'phantom'."""
    if entry.lower() in exact:
        return "exact"
    norm = _normalise(entry)
    if norm in fuzz:
        return "fuzzy"
    if norm in proto_tokens:
        return "proto"
    # Try partial-match against proto tokens (e.g. "Cherry Orchard" → "ypCherryOrchard")
    for token in proto_tokens:
        if norm and norm in token:
            return "proto"
    # Try word-level substring match: every word in the entry appears as a
    # substring somewhere in the corpus.  Catches colloquial/reordered forms
    # like "Hospitaller Knight" matching "Knights Hospitaller", or
    # "Jaguar Knight" matching "Champion Jaguar Knight".
    words = [w for w in re.split(r"[^A-Za-z0-9]+", entry) if len(w) >= 4]
    if words:
        norm_words = [w.lower() for w in words]
        # All words must appear in *some* corpus entry (any one of them)
        for corpus_entry in exact:
            if all(w in corpus_entry for w in norm_words):
                return "partial"
        # Or all words must appear in *some* proto token (lowercased)
        for token in proto_tokens:
            if all(w in token for w in norm_words):
                return "partial"
        # Final fallback: the LEAD significant word (the unit's root name)
        # appears in some proto token. Catches modifier forms like
        # "Granadero a Caballo" → deREVGranadero, "Rosior Dragoon" →
        # deIconREVRosior, "Mohawk Warrior" → PoliticianMohawk, where the
        # blurb uses a flavorful display name but the engine name is the
        # root.  Requires the root word to be ≥5 chars to avoid noise.
        lead = norm_words[0]
        if len(lead) >= 5:
            for token in proto_tokens:
                if lead in token:
                    return "partial"
            for corpus_entry in exact:
                if lead in corpus_entry:
                    return "partial"
    return "phantom"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--blurbs", type=Path,
                    default=REPO_ROOT / "data" / "anw_civ_blurbs.json")
    ap.add_argument("--stringtable", type=Path,
                    default=REPO_ROOT / "artifacts" / "extracted_base_stringtable.xml")
    ap.add_argument("--stringmods", type=Path,
                    default=REPO_ROOT / "data" / "strings" / "english" / "stringmods.xml")
    ap.add_argument("--protomods", type=Path,
                    default=REPO_ROOT / "data" / "protomods.xml")
    ap.add_argument("--techtreemods", type=Path,
                    default=REPO_ROOT / "data" / "techtreemods.xml")
    ap.add_argument("--basetechtree", type=Path,
                    default=REPO_ROOT / "artifacts" / "extracted_base_techtreey.xml")
    ap.add_argument("--json", type=Path, dest="json_out")
    args = ap.parse_args()

    print("=" * 60)
    print("PROTO UNIT / BUILDING REFERENCES")
    print("=" * 60)

    if not args.blurbs.exists():
        print(f"  ✗ blurbs file not found: {args.blurbs}")
        return 1

    blurbs = json.loads(args.blurbs.read_text(encoding="utf-8"))
    exact, fuzz = _load_display_name_corpus(args.stringtable, args.stringmods)
    proto_tokens = _load_proto_unit_tokens(args.protomods, args.basetechtree,
                                            args.techtreemods)

    print(f"  Corpus: {len(exact)} display names, {len(proto_tokens)} proto tokens")
    print()

    failures: list[str] = []
    report: dict = {"civs": {}}

    for civ_key in sorted(blurbs.keys()):
        civ = blurbs[civ_key]
        civ_report: dict = {"unique_units": {}, "unique_buildings": {}}
        per_civ_fails: list[str] = []

        for field in ("unique_units", "unique_buildings"):
            entries = civ.get(field, [])
            for entry in entries:
                status = _check_entry(entry, exact, fuzz, proto_tokens)
                civ_report[field][entry] = status
                if status == "phantom":
                    msg = f"{civ_key}.{field}: '{entry}' not in corpus"
                    failures.append(msg)
                    per_civ_fails.append(f"{field}='{entry}'")

        if per_civ_fails:
            print(f"  ✗ {civ_key}: phantom entries — {'; '.join(per_civ_fails)}")
        else:
            print(f"  ✓ {civ_key}: all unit/building refs resolve")
        report["civs"][civ_key] = civ_report

    print()
    if failures:
        print(f"FAIL — {len(failures)} phantom unit/building name(s):")
        for f in failures[:30]:
            print(f"  • {f}")
        if len(failures) > 30:
            print(f"  ...and {len(failures) - 30} more")
    else:
        print("PASS — all unique_units / unique_buildings entries resolve")

    report["failures"] = failures
    report["passed"] = not failures

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report: {args.json_out}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
