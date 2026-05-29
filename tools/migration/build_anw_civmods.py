"""Phase 2 of the ANW migration: rebuild civmods.xml under the ANW namespace.

Two transformations:

  1. RENAME the 26 existing `ANW{X}` `<Civ>` blocks → `ANW{X}` (PascalCase
     replacement throughout each block: Civ Name, AgeTech tech names,
     HomeCityFilename, MultipleBlockUnit names, etc.)

  2. APPEND 22 new `<Civ>` blocks for the base civs (British, Dutch, Aztec, …).
     These need engine-specific data (StatsID, AgeTech tech names, starting
     units, flag/portrait texture paths) that lives in the engine's vanilla
     `civs.xml` inside its `.bar` archives.

Status of each civ in this generator:

  * 26 rev civs — fully handled (rename only, no engine data needed).
  * 22 base civs — STUB blocks emitted with TODO markers. Each stub contains
    the fields we can derive from `data/homecity*.xml` plus the existing
    `tools/cardextract/refresh_dev_subtrees.py::SLUG_TO_LEADER` mapping.
    The fields requiring vanilla `civs.xml` extraction are marked
    `<!-- TODO ANW: vanilla civs.xml -->` so a subsequent extraction pass
    (see `tools/migration/extract_vanilla_civs.py` — TODO) can fill them in.

CLI:
  python3 tools/migration/build_anw_civmods.py
        Dry-run. Writes the proposed output to `data/civmods.anw.xml`
        and prints a summary of changes. The live `data/civmods.xml`
        is NOT modified.

  python3 tools/migration/build_anw_civmods.py --diff
        Dry-run + show a unified diff of the proposed changes.

  python3 tools/migration/build_anw_civmods.py --apply
        Replace `data/civmods.xml` in place.

  python3 tools/migration/build_anw_civmods.py --check
        Exit non-zero if `data/civmods.xml` would change. For CI drift gate.

Why dry-run by default: the ANW migration is a multi-phase atomic change.
Renaming civmods.xml without simultaneously renaming personality + homecity
files would break the running mod. The migration only flips when ALL
phase scripts are applied together (orchestrated by `run_anw_migration.py`).
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.migration.anw_token_map import ANW_CIVS, AnwCiv, iter_anw_civs  # noqa: E402

CIVMODS_IN = REPO / "data" / "civmods.xml"
CIVMODS_OUT = REPO / "data" / "civmods.anw.xml"


# ──────────────────────────────────────────────────────────────────────────────
# Step 1 — rename ANW → ANW in existing 26 rev-civ blocks
# ──────────────────────────────────────────────────────────────────────────────


def rename_rvlt_blocks(text: str) -> tuple[str, int]:
    """Rename every `ANW{X}` and `anw{x}` token to its ANW equivalent.

    Two distinct tokens to handle:
      - PascalCase civ tokens (e.g. `ANWBarbary` → `ANWBarbary`)
      - lowercase filename stems (e.g. `anwhomecitybarbary` →
        `anwhomecitybarbary`)
      - tech name compounds (e.g. `ANWColonializeCanadians` →
        `ANWColonializeCanadians`) — these match the `ANW...` pattern
        with civ-suffix that may not be in the ANW_CIVS table; we transform
        the prefix only.

    Returns (new_text, replacement_count).
    """
    count = 0

    # First pass: civ-token-keyed rename (uses anw_token_map for civmods Names
    # to avoid accidentally renaming a generic `ANW` prefix to a wrong
    # ANW token).
    civ_token_pairs = sorted(
        ((c.old_civ_token, c.anw_token) for c in iter_anw_civs() if c.is_revolution),
        key=lambda p: -len(p[0]),  # longest first to avoid prefix collisions
    )
    for old, new in civ_token_pairs:
        # Word-boundary substitution to avoid matching e.g. "ANWBarbary" inside
        # "ANWBarbaryHelper". Use lookahead/behind for non-word chars.
        new_text, n = re.subn(rf"\b{re.escape(old)}\b", new, text)
        if n:
            text = new_text
            count += n

    # Second pass: rename the lowercase homecity filename stems (anwhomecity*)
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

    # Third pass: rename remaining `ANW{X}` tech-name compounds → `ANW{X}`.
    # These are mod-defined tech names (e.g. ANWColonializeCanadians) whose
    # suffix is a civ-derivative. Pattern is `ANW` followed by uppercase ASCII.
    new_text, n = re.subn(r"\bANW(?=[A-Z])", "ANW", text)
    if n:
        text = new_text
        count += n

    # Fourth pass: lowercase variant `anw` followed by lowercase letter
    # (covers any stragglers like `anwage0NapoleonicFrench` if any exist).
    new_text, n = re.subn(r"\banw(?=[a-z])", "anw", text)
    if n:
        text = new_text
        count += n

    return text, count


# ──────────────────────────────────────────────────────────────────────────────
# Step 2 — generate stub <Civ> blocks for the 22 base civs
# ──────────────────────────────────────────────────────────────────────────────


_BASE_CIV_STUB_TEMPLATE = """\
\t<Civ>
\t\t<Name>{anw_token}</Name>
\t\t<Main>1</Main>
\t\t<!-- TODO-ANW-VANILLA: StatsID, AgeTechs (Age0-Age4 + Post),
\t\t     BuildingEfficiency, FreeBuildingEfficiency, starting units,
\t\t     EmpireWars params, MultipleBlockTrain entries.
\t\t     Source: vanilla civs.xml (inside engine .bar archive). -->
\t\t<DisplayNameID>{display_id}</DisplayNameID>
\t\t<RolloverNameID>{rollover_id}</RolloverNameID>
\t\t<HomeCityFilename>{homecity_filename}</HomeCityFilename>
\t\t<HomeCityPreviewWPF>{portrait_wpf}</HomeCityPreviewWPF>
\t\t<!-- TODO-ANW-VANILLA: HomeCityFlagTexture, PostgameFlagTexture,
\t\t     HomeCityFlagButtonSet, HomeCityFlagButtonSetLarge,
\t\t     PostgameFlagIconWPF, HomeCityFlagIconWPF, HomeCityFlagButtonWPF,
\t\t     MatchmakingTextures sub-block. Source: vanilla civs.xml. -->
\t</Civ>
"""


# String IDs for the 22 base civs reside in 410000-410999 to avoid collisions
# with mod IDs (400000-409999 in use) and base game (< 400000).
_BASE_CIV_DISPLAY_ID_BASE = 410000
_BASE_CIV_ROLLOVER_ID_BASE = 410500


def emit_base_civ_stubs() -> tuple[str, list[str]]:
    """Return (concatenated_stub_blocks_xml, list_of_anw_tokens).

    Stable ID assignment by alphabetical slug order so re-running the
    generator never reshuffles IDs.
    """
    base_civs = [c for c in iter_anw_civs() if not c.is_revolution]
    base_civs.sort(key=lambda c: c.slug)

    blocks: list[str] = []
    tokens: list[str] = []
    for i, c in enumerate(base_civs):
        portrait = (
            f"resources/images/icons/singleplayer/cpai_avatar_"
            f"{c.anw_stem[3:]}_{c.old_personality_stem.lower()}.png"
        )
        blocks.append(_BASE_CIV_STUB_TEMPLATE.format(
            anw_token=c.anw_token,
            display_id=_BASE_CIV_DISPLAY_ID_BASE + i,
            rollover_id=_BASE_CIV_ROLLOVER_ID_BASE + i,
            homecity_filename=c.new_homecity_filename,
            portrait_wpf=portrait,
        ))
        tokens.append(c.anw_token)

    header = (
        "\n\t<!-- ────────────────────────────────────────────────────────\n"
        "\t     ANW base-civ blocks (22). Initially emitted as stubs by\n"
        "\t     tools/migration/build_anw_civmods.py, then populated with\n"
        "\t     vanilla civ data via tools/migration/extract_vanilla_civs.py.\n"
        "\t     ──────────────────────────────────────────────────────── -->\n\n"
    )
    return header + "\n".join(blocks), tokens


# ──────────────────────────────────────────────────────────────────────────────
# Driver
# ──────────────────────────────────────────────────────────────────────────────


def transform(input_xml: str) -> tuple[str, dict[str, int]]:
    """Run both transformations. Returns (new_xml, stats)."""
    renamed, replacements = rename_rvlt_blocks(input_xml)

    stub_blocks, base_tokens = emit_base_civ_stubs()

    # Insert the 22 base-civ stubs immediately before the closing </civmods> tag.
    closing = "</civmods>"
    if closing not in renamed:
        raise SystemExit("civmods.xml: missing </civmods> closing tag")
    new_xml = renamed.replace(closing, stub_blocks + "\n" + closing)

    return new_xml, {
        "rvlt_replacements": replacements,
        "base_civ_stubs_added": len(base_tokens),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="Replace data/civmods.xml in place "
                             "(default: write to data/civmods.anw.xml).")
    parser.add_argument("--diff", action="store_true",
                        help="Print a unified diff of the changes.")
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if civmods.xml would change. "
                             "(Does not write anything.)")
    args = parser.parse_args()

    src = CIVMODS_IN.read_text(encoding="utf-8")
    new_xml, stats = transform(src)

    print(f"transform stats: {stats}", file=sys.stderr)

    if args.check:
        return 0 if new_xml == src else 1

    if args.diff:
        sys.stdout.writelines(difflib.unified_diff(
            src.splitlines(keepends=True),
            new_xml.splitlines(keepends=True),
            fromfile="data/civmods.xml (current)",
            tofile="data/civmods.xml (proposed ANW)",
            n=3,
        ))

    target = CIVMODS_IN if args.apply else CIVMODS_OUT
    target.write_text(new_xml, encoding="utf-8")
    print(f"wrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
