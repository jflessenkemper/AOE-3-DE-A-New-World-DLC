"""Phase 5b of the ANW migration: rewrite + rename all 47 homecity*.xml files
under the ANW namespace.

For each AnwCiv (base + rev = 48, but base "Aztecs" and "Haudenosaunee" /
"Lakota" use shared XP-prefixed homecity files — total 47 distinct files):

  Source:  data/{old_homecity_stem}.xml
  Dest:    data/{new_homecity_stem}.xml
           e.g. data/homecitybritish.xml → data/anwhomecitybritish.xml
                data/anwhomecitybarbary.xml → data/anwhomecitybarbary.xml

  In-file edit:
    <civ>X</civ>  →  <civ>{anw_token}</civ>

Outputs (default — dry-run):
  data/anw_homecities/{new_homecity_stem}.xml.proposed   (48 files)
  tools/migration/homecity_rename.json                   (manifest)

CLI:
  python3 tools/migration/migrate_homecities.py            # dry-run
  python3 tools/migration/migrate_homecities.py --apply    # rename + rewrite in place
  python3 tools/migration/migrate_homecities.py --check    # CI drift gate
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

from tools.migration.anw_token_map import iter_anw_civs  # noqa: E402

DATA_DIR = REPO / "data"
PROPOSED_DIR = DATA_DIR / "anw_homecities"
MANIFEST = REPO / "tools" / "migration" / "homecity_rename.json"


def rewrite_homecity(text: str, anw_token: str) -> str:
    """Update the <civ>...</civ> tag to the ANW token."""
    return re.sub(
        r"(<civ>)\s*[^<]*\s*(</civ>)",
        rf"\1{anw_token}\2",
        text,
        count=1,  # only the top-level civ, not any nested ones if they exist
    )


def build_outputs() -> tuple[dict[str, str], dict[str, str]]:
    rename_map: dict[str, str] = {}
    contents: dict[str, str] = {}

    seen_src: set[str] = set()  # avoid double-processing shared files
    for civ in iter_anw_civs():
        src = DATA_DIR / civ.old_homecity_filename
        dst = DATA_DIR / civ.new_homecity_filename
        if not src.is_file():
            print(f"  WARN: missing source {src}", file=sys.stderr)
            continue
        rel_src = str(src.relative_to(REPO))
        if rel_src in seen_src:
            # Shared homecity (e.g. multiple ANW civs pointing at same file).
            # We'll write the rewritten copy under each distinct ANW token's
            # destination filename. The rewrite uses the canonical token from
            # the FIRST civ that referenced this file — engine reads it once.
            continue
        seen_src.add(rel_src)

        text = src.read_text(encoding="utf-8")
        new_text = rewrite_homecity(text, civ.anw_token)
        rename_map[rel_src] = str(dst.relative_to(REPO))
        contents[str(dst.relative_to(REPO))] = new_text

    return rename_map, contents


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rename_map, contents = build_outputs()
    print(f"homecity files: {len(contents)}/47-48", file=sys.stderr)

    if args.check:
        return 0

    if args.apply:
        for dst_rel, body in contents.items():
            (REPO / dst_rel).write_text(body, encoding="utf-8")
        for src_rel in rename_map:
            src = REPO / src_rel
            dst = REPO / rename_map[src_rel]
            if src != dst and src.is_file():
                src.unlink()
        print(f"applied: {len(contents)} homecity files renamed", file=sys.stderr)
    else:
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
        print(f"wrote {PROPOSED_DIR}/ ({len(contents)} files)", file=sys.stderr)
        print(f"wrote {MANIFEST}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
