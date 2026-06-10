#!/usr/bin/env python3
"""Static validator: each data-layer wiki doc must name the REAL root element
of the data file it documents, and reference a data path that actually exists.

Born from a recurring drift class found across several data-layer docs: the
schema example used the *base game's* root element instead of the ANW mod's
actual `<*mods>` root, and/or pointed at a wrong file path:

  * docs/wiki/data-layer/protomods.md   showed root `<proto>`  (real: <protomods>)
  * docs/wiki/data-layer/techtreemods.md showed root `<techtree>` (real: <techtreemods>)
  * docs/wiki/data-layer/stringmods.md  showed root `<stringtable>` AND path
    `data/stringmods.xml` (real: <stringmods> at data/strings/english/stringmods.xml)

A doc that documents the wrong root element teaches a copy-paste that silently
fails to merge (additive overlays merge by their `<*mods>` envelope). This
pins each doc to its data file's true root.

For each (doc, data-file) pair below it asserts:
  1. The data file exists at the mapped path.
  2. The doc text contains the data file's REAL root element tag (`<root`),
     so the schema example can't quietly use the base-table name.

Usage:
    python3 tools/validation/validate_wiki_datalayer_accuracy.py

Exit codes:
    0 — every data-layer doc names its data file's real root (GREEN)
    1 — a mapped data file is missing, or a doc omits the real root (RED)
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "docs" / "wiki" / "data-layer"

# doc filename -> data file it documents (path relative to repo root).
# homecity uses a representative per-civ file (all share the <homecity> root).
DOC_TO_DATA = {
    "civmods.md": "data/civmods.xml",
    "protomods.md": "data/protomods.xml",
    "techtreemods.md": "data/techtreemods.xml",
    "stringmods.md": "data/strings/english/stringmods.xml",
    "homecity.md": "data/anwhomecitybritish.xml",
}


def real_root(data_path: Path) -> str | None:
    try:
        return ET.parse(data_path).getroot().tag
    except Exception:
        # Fall back to a cheap text scan for the first element tag.
        m = re.search(r"<([A-Za-z][\w]*)", data_path.read_text(encoding="utf-8", errors="ignore"))
        return m.group(1) if m else None


def main() -> int:
    errors: list[str] = []

    print("Data-layer wiki accuracy check (doc names its data file's real root)")
    print()

    for doc_name, rel in DOC_TO_DATA.items():
        doc = WIKI / doc_name
        data = REPO / rel
        if not doc.exists():
            errors.append(f"missing wiki doc: docs/wiki/data-layer/{doc_name}")
            continue
        if not data.exists():
            errors.append(f"{doc_name}: mapped data file does not exist: {rel}")
            continue
        root = real_root(data)
        if not root:
            errors.append(f"{doc_name}: could not determine root element of {rel}")
            continue
        text = doc.read_text(encoding="utf-8")
        # The doc must mention the real root tag as an element somewhere
        # (e.g. "<protomods>" in the schema block).
        if f"<{root}" not in text:
            errors.append(
                f"{doc_name}: does not name the real root element <{root}> of {rel} "
                f"(likely documents the base-table root instead)")
        else:
            print(f"  OK  {doc_name:22s} -> {rel}  (root <{root}>)")

    print()
    if errors:
        print("FAIL — data-layer wiki docs out of sync with their data files:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"PASS — all {len(DOC_TO_DATA)} data-layer docs name their data file's real root.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
