"""Phase 5 of the ANW migration: merge decks_standard.json + decks_legendary.json
into a single `decks_anw.json` keyed by ANW civ token.

Both inputs have the same shape — an outer dict keyed by civ identifier, with
each value being `{"0": [card_ids], "1": [card_ids], ...}` (one age per key,
0 = Discovery through 4 = Imperial). Only the outer keys differ between the
two files: standard uses civ slugs (e.g. "British", "MexicansStd") while
legendary uses homecity stems (e.g. "anwhomecitybarbary").

After the merge:

  decks_anw.json["ANWBritish"]      = decks_standard.json["British"]
  decks_anw.json["ANWMexicans"]     = decks_standard.json["MexicansStd"]
  decks_anw.json["ANWUSA"]          = decks_standard.json["UnitedStates"]
  decks_anw.json["ANWBarbary"]      = decks_legendary.json["anwhomecitybarbary"]
  ... (48 entries total)

Card IDs inside each deck are unchanged (cards.json keys, civ-agnostic).

CLI:
  python3 tools/migration/build_anw_decks.py            # dry-run (default)
  python3 tools/migration/build_anw_decks.py --apply    # delete the two
                                                          source files after
                                                          writing decks_anw.json
  python3 tools/migration/build_anw_decks.py --check    # CI drift gate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.migration.anw_token_map import iter_anw_civs  # noqa: E402

DECKS_STD = REPO / "data" / "decks_standard.json"
DECKS_LEG = REPO / "data" / "decks_legendary.json"
DECKS_OUT = REPO / "data" / "decks_anw.json"


# Two slug→std-deck-key irregularities. Most base civs use their slug as the
# decks_standard key, but these two diverge:
_STD_KEY_OVERRIDES = {
    "Mexicans (Standard)": "MexicansStd",
    "United States":       "UnitedStates",
}


def _std_deck_key(slug: str) -> str:
    return _STD_KEY_OVERRIDES.get(slug, slug)


def merge() -> tuple[dict, list[str]]:
    """Return (merged_dict, list_of_warnings)."""
    std = json.loads(DECKS_STD.read_text(encoding="utf-8"))
    leg = json.loads(DECKS_LEG.read_text(encoding="utf-8"))

    out: dict[str, dict[str, list[str]]] = {}
    warnings: list[str] = []

    for civ in iter_anw_civs():
        if civ.is_revolution:
            src_key = civ.old_homecity_stem
            src_dict = leg
        else:
            src_key = _std_deck_key(civ.slug)
            src_dict = std

        if src_key not in src_dict:
            warnings.append(
                f"{civ.slug} ({civ.anw_token}): source key {src_key!r} not found "
                f"in decks_{'legendary' if civ.is_revolution else 'standard'}.json"
            )
            continue

        out[civ.anw_token] = src_dict[src_key]

    # Surface any decks_standard / decks_legendary keys that we didn't claim —
    # those would be silently dropped by the merge.
    claimed_std = {_std_deck_key(c.slug) for c in iter_anw_civs() if not c.is_revolution}
    claimed_leg = {c.old_homecity_stem for c in iter_anw_civs() if c.is_revolution}
    orphan_std = sorted(set(std) - claimed_std)
    orphan_leg = sorted(set(leg) - claimed_leg)
    for k in orphan_std:
        warnings.append(f"orphan in decks_standard.json (no ANW slug claims it): {k!r}")
    for k in orphan_leg:
        warnings.append(f"orphan in decks_legendary.json (no ANW slug claims it): {k!r}")

    return out, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="Write decks_anw.json AND delete the two source files. "
                             "Default: write only decks_anw.json (sources untouched).")
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if decks_anw.json would change. "
                             "(Does not write anything.)")
    args = parser.parse_args()

    merged, warnings = merge()

    print(f"merged decks: {len(merged)}/48 ANW civs", file=sys.stderr)
    for w in warnings:
        print(f"  warn: {w}", file=sys.stderr)

    if len(merged) != 48:
        print(f"ERROR: expected 48 civs, got {len(merged)}", file=sys.stderr)
        return 1

    new_text = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not DECKS_OUT.is_file():
            return 1
        return 0 if DECKS_OUT.read_text(encoding="utf-8") == new_text else 1

    DECKS_OUT.write_text(new_text, encoding="utf-8")
    print(f"wrote {DECKS_OUT}", file=sys.stderr)

    if args.apply:
        DECKS_STD.unlink()
        DECKS_LEG.unlink()
        print(f"deleted {DECKS_STD} and {DECKS_LEG}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
