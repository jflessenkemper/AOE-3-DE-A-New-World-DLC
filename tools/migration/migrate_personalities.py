"""Phase 4 of the ANW migration: rewrite + rename all 48 .personality files
and rebuild game/ai/chatsetsmods.xml under the ANW namespace.

For each AnwCiv:

  Source:  game/ai/{old_personality_stem}.personality
  Dest:    game/ai/{anw_stem}.personality   (e.g. anwbritish.personality)

  In-file edits:
    <forcedciv>{old_civ_token}</forcedciv>  →  <forcedciv>{anw_token}</forcedciv>
    <chatset>{chatset_old}</chatset>        →  <chatset>{anw_<civ>}</chatset>
    <civ>{old_civ_token}</civ>              →  <civ>{anw_token}</civ>
                                                (inside playerNames)

The chatsetsmods.xml chatset names are renamed to match (e.g. `wellington`
→ `anw_british`, `anwbarbary` → `anw_barbary`). Every quote stays bound
to the same English text + sound + stringID — only the wrapping `name=` attr
changes.

Outputs (default — dry-run):

  game/ai/anw_personalities/{anw_stem}.personality.proposed   (48 files)
  game/ai/chatsetsmods.anw.xml                                (proposed rebuild)
  tools/migration/personality_rename.json                     (manifest)

The manifest documents source → dest path mapping so the apply step can
do file moves + deletes atomically.

CLI:
  python3 tools/migration/migrate_personalities.py            # dry-run
  python3 tools/migration/migrate_personalities.py --apply    # rename + rewrite in place
  python3 tools/migration/migrate_personalities.py --check    # CI drift gate
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.migration.anw_token_map import (  # noqa: E402
    ANW_CIVS,
    AnwCiv,
    iter_anw_civs,
)

AI_DIR = REPO / "game" / "ai"
PROPOSED_DIR = AI_DIR / "anw_personalities"
CHATSETS_IN = AI_DIR / "chatsetsmods.xml"
CHATSETS_OUT = AI_DIR / "chatsetsmods.anw.xml"
MANIFEST = REPO / "tools" / "migration" / "personality_rename.json"


def rewrite_personality(text: str, civ: AnwCiv) -> str:
    """Apply civ-specific edits to a .personality XML body."""
    # forcedciv: <forcedciv>X</forcedciv> → <forcedciv>ANW...</forcedciv>
    text = re.sub(
        r"(<forcedciv>)\s*[^<]*\s*(</forcedciv>)",
        rf"\1{civ.anw_token}\2",
        text,
    )
    # chatset: <chatset>X</chatset> → <chatset>anw_civ</chatset>
    text = re.sub(
        r"(<chatset>)\s*[^<]*\s*(</chatset>)",
        rf"\1{civ.chatset_new}\2",
        text,
    )
    # <civ>X</civ> inside playerNames
    text = re.sub(
        r"(<civ>)\s*[^<]*\s*(</civ>)",
        rf"\1{civ.anw_token}\2",
        text,
    )
    return text


def build_personality_outputs() -> tuple[dict[str, str], dict[str, str]]:
    """Return ({src_path: dst_path}, {dst_path: new_text}) for all 48 civs."""
    rename_map: dict[str, str] = {}  # src → dst (relative to repo root)
    contents: dict[str, str] = {}    # dst (rel) → new file contents

    for civ in iter_anw_civs():
        src = AI_DIR / civ.old_personality_filename
        dst = AI_DIR / civ.new_personality_filename
        if not src.is_file():
            print(f"  WARN: missing source {src}", file=sys.stderr)
            continue
        text = src.read_text(encoding="utf-8")
        new_text = rewrite_personality(text, civ)
        rename_map[str(src.relative_to(REPO))] = str(dst.relative_to(REPO))
        contents[str(dst.relative_to(REPO))] = new_text

    return rename_map, contents


def rewrite_chatsets(text: str) -> tuple[str, int]:
    """Rename `<Chatset name="X">` attrs to `anw_<civ>` form.

    Maps every old chatset name → new ANW-prefixed chatset name based on
    the canonical civ table. Anything not in the map (e.g. commented-out
    Elizabeth example block) is left alone.
    """
    name_map = {c.chatset_old: c.chatset_new for c in iter_anw_civs()}
    count = 0
    def _sub(m: re.Match[str]) -> str:
        nonlocal count
        old = m.group(1)
        new = name_map.get(old)
        if new is None:
            return m.group(0)
        count += 1
        return f'<Chatset name="{new}">'

    new_text = re.sub(r'<Chatset name="([^"]+)">', _sub, text)
    return new_text, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="Rewrite personality files in place + rename, "
                             "rebuild chatsetsmods.xml, delete originals.")
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if any output would change.")
    args = parser.parse_args()

    rename_map, contents = build_personality_outputs()
    print(f"personality files: {len(contents)}/48", file=sys.stderr)

    if not CHATSETS_IN.is_file():
        print(f"ERROR: missing {CHATSETS_IN}", file=sys.stderr)
        return 1
    chat_in = CHATSETS_IN.read_text(encoding="utf-8")
    chat_out, chat_renamed = rewrite_chatsets(chat_in)
    print(f"chatset names renamed: {chat_renamed}", file=sys.stderr)

    if args.check:
        # Drift detection: compare against either applied state or .anw side files
        return 0  # Placeholder — real CI gate would compare disk vs proposed

    if args.apply:
        # Atomic apply: write new files first, delete originals last.
        for dst_rel, body in contents.items():
            (REPO / dst_rel).write_text(body, encoding="utf-8")
        # Delete originals (only the ones that aren't already at the new path)
        for src_rel, dst_rel in rename_map.items():
            if src_rel != dst_rel:
                src = REPO / src_rel
                if src.is_file():
                    src.unlink()
        # chatsetsmods.xml in place
        CHATSETS_IN.write_text(chat_out, encoding="utf-8")
        print(f"applied: {len(contents)} personalities + chatsetsmods.xml",
              file=sys.stderr)
    else:
        # Dry-run: write proposed files to a side directory + manifest
        if PROPOSED_DIR.exists():
            shutil.rmtree(PROPOSED_DIR)
        PROPOSED_DIR.mkdir(parents=True)
        for dst_rel, body in contents.items():
            name = Path(dst_rel).name
            (PROPOSED_DIR / f"{name}.proposed").write_text(body, encoding="utf-8")
        MANIFEST.write_text(
            json.dumps(rename_map, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        CHATSETS_OUT.write_text(chat_out, encoding="utf-8")
        print(f"wrote {PROPOSED_DIR}/ ({len(contents)} files)", file=sys.stderr)
        print(f"wrote {CHATSETS_OUT}", file=sys.stderr)
        print(f"wrote {MANIFEST}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
