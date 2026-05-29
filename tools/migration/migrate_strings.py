"""Phase 3 of the ANW migration: rewrite stringmods.xml + randomnamemods.xml +
techtreemods.xml + playercolors.xml under the ANW namespace.

This is mostly mechanical text substitution: every `ANW{X}` token gets
replaced with `ANW{X}`, and every lowercase `anw{x}` filename stem gets
replaced with `anw{x}` (preserving the homecity-prefix where present).

  PascalCase replacements:
      ANWBarbary       → ANWBarbary       (civ token)
      ANWColonializeCanadians → ANWColonializeCanadians  (mod tech)
      ANW (generic prefix when followed by uppercase) → ANW

  Lowercase replacements:
      anwhomecitybarbary → anwhomecitybarbary           (homecity stem)
      anwbarbary       → anwbarbary       (personality stem)

The 22 base civs (British, Dutch, Aztec, …) currently reuse vanilla
string IDs (< 400000). After migration, those base civs will use new
mod-owned IDs in the 410000-410999 range so the mod is fully self-
contained. Adding those new strings is a separate concern (handled by
the vanilla extraction pass — out of scope for this script). What this
script DOES do: rename existing 4xxxxx string IDs/keys that mention
ANW tokens, so the existing strings keep working under their new
ANW names.

Outputs (default — dry-run):

  data/strings/english/stringmods.anw.xml
  data/randomnamemods.anw.xml
  data/techtreemods.anw.xml
  data/playercolors.anw.xml

CLI:
  python3 tools/migration/migrate_strings.py            # dry-run
  python3 tools/migration/migrate_strings.py --apply    # write in place
                                                          (overwrites originals)
  python3 tools/migration/migrate_strings.py --check    # CI drift gate
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.migration.anw_token_map import iter_anw_civs  # noqa: E402

# (input_path, dry_run_output_path)
TARGETS = [
    (REPO / "data" / "strings" / "english" / "stringmods.xml",
     REPO / "data" / "strings" / "english" / "stringmods.anw.xml"),
    (REPO / "data" / "randomnamemods.xml",
     REPO / "data" / "randomnamemods.anw.xml"),
    (REPO / "data" / "techtreemods.xml",
     REPO / "data" / "techtreemods.anw.xml"),
    (REPO / "data" / "playercolors.xml",
     REPO / "data" / "playercolors.anw.xml"),
]


def transform(text: str) -> tuple[str, int]:
    """Apply ANW → ANW + anw → anw substitutions.

    Same logic as `build_anw_civmods.rename_rvlt_blocks` but extracted to
    operate on arbitrary text. Returns (new_text, replacement_count).
    """
    count = 0

    # Phase 1: civ-token rename via the canonical map (longest first to avoid
    # prefix collisions e.g. ANWMexicans before ANW generic).
    civ_token_pairs = sorted(
        ((c.old_civ_token, c.anw_token) for c in iter_anw_civs() if c.is_revolution),
        key=lambda p: -len(p[0]),
    )
    for old, new in civ_token_pairs:
        new_text, n = re.subn(rf"\b{re.escape(old)}\b", new, text)
        if n:
            text = new_text
            count += n

    # Phase 2: lowercase homecity stems
    homecity_pairs = sorted(
        ((c.old_homecity_stem, "anwhomecity" + c.anw_stem[3:])
         for c in iter_anw_civs() if c.is_revolution),
        key=lambda p: -len(p[0]),
    )
    for old, new in homecity_pairs:
        new_text, n = re.subn(rf"\b{re.escape(old)}\b", new, text)
        if n:
            text = new_text
            count += n

    # Phase 3: lowercase personality stems (anwbarbary → anwbarbary).
    # These are independent of homecity stems (homecity is anwhomecity*).
    personality_pairs = sorted(
        ((c.old_personality_stem, c.anw_stem) for c in iter_anw_civs() if c.is_revolution),
        key=lambda p: -len(p[0]),
    )
    for old, new in personality_pairs:
        new_text, n = re.subn(rf"\b{re.escape(old)}\b", new, text)
        if n:
            text = new_text
            count += n

    # Phase 4: catch any remaining `ANW{X}` (mod tech compounds, etc.)
    new_text, n = re.subn(r"\bANW(?=[A-Z])", "ANW", text)
    if n:
        text = new_text
        count += n

    new_text, n = re.subn(r"\banw(?=[a-z])", "anw", text)
    if n:
        text = new_text
        count += n

    return text, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="Write changes back to the source file in place. "
                             "Default: write to .anw.xml side files.")
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if any source file would change.")
    args = parser.parse_args()

    total_replacements = 0
    needs_change = False

    for src_path, dry_path in TARGETS:
        if not src_path.is_file():
            print(f"  skip (missing): {src_path}", file=sys.stderr)
            continue

        text = src_path.read_text(encoding="utf-8")
        new_text, n = transform(text)
        total_replacements += n
        if new_text != text:
            needs_change = True

        target = src_path if args.apply else dry_path
        if not args.check:
            target.write_text(new_text, encoding="utf-8")

        rel = src_path.relative_to(REPO)
        print(f"  {n:5d} replacements in {rel} → {target.relative_to(REPO)}",
              file=sys.stderr)

    print(f"total replacements: {total_replacements}", file=sys.stderr)

    if args.check:
        return 1 if needs_change else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
