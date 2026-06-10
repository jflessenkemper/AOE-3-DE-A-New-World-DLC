#!/usr/bin/env python3
"""Fails if any active ANW civ token (<main>1</main> in civmods.xml) is missing from the wiki nation/building map at docs/wiki/validation/nations-and-buildings.md, keeping the documentation in sync with the shipped civ list.

Exit codes:
    0 — all ANW civ tokens documented (GREEN)
    1 — one or more tokens missing from wiki (RED — details printed)
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CIVMODS_XML = REPO / "data" / "civmods.xml"
WIKI_FILE = REPO / "docs" / "wiki" / "validation" / "nations-and-buildings.md"


# ---------------------------------------------------------------------------
# Load canonical ANW tokens from civmods.xml
# ---------------------------------------------------------------------------

def _load_canonical_tokens() -> list[str]:
    """Return all ANW civ tokens from civmods.xml where <main>1</main>."""
    tree = ET.parse(CIVMODS_XML)
    root = tree.getroot()
    tokens: list[str] = []
    for civ in root.findall("civ"):
        main_tag = civ.find("main")
        if main_tag is not None and main_tag.text == "1":
            name_tag = civ.find("name")
            if name_tag is not None and name_tag.text:
                tokens.append(name_tag.text.strip())
    return sorted(tokens)


# ---------------------------------------------------------------------------
# Check wiki coverage
# ---------------------------------------------------------------------------

def check_wiki_coverage(canonical: list[str], wiki_content: str) -> list[str]:
    """Return list of canonical tokens NOT found in wiki content."""
    missing = []
    for token in canonical:
        if token not in wiki_content:
            missing.append(token)
    return missing


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("Wiki nation/building map coverage validation")
    print(f"  civmods    : {CIVMODS_XML.relative_to(REPO)}")
    print(f"  wiki file  : {WIKI_FILE.relative_to(REPO)}")
    print()

    try:
        canonical = _load_canonical_tokens()
    except ET.ParseError as exc:
        print(f"FAIL — could not parse civmods.xml: {exc}")
        return 1

    try:
        wiki_content = WIKI_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"FAIL — wiki file not found: {WIKI_FILE}")
        return 1
    except Exception as exc:
        print(f"FAIL — could not read wiki file: {exc}")
        return 1

    print(f"  canonical ANW tokens (civmods.xml <main>1>) : {len(canonical)}")
    print()

    missing = check_wiki_coverage(canonical, wiki_content)
    if missing:
        print(f"FAIL — {len(missing)} token(s) missing from wiki:")
        for token in missing:
            print(f"    {token}")
        print()
        print("RESULT: FAIL — add missing tokens to docs/wiki/validation/nations-and-buildings.md")
        return 1

    print(f"PASS — {len(canonical)}/{len(canonical)} civ tokens documented in wiki")
    print()
    print("RESULT: PASS — all checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
