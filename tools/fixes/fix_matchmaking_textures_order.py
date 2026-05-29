#!/usr/bin/env python3
"""Fix Bug 1: F10 Player Communication portraits empty for some ANW civs.

Root cause: 13 civmod entries had inverted field order in
``<MatchmakingTextures>``. The canonical order (used by 32 working civs) is:

    <BannerTexture/>
    <BannerTextureCoords/>
    <PortraitTexture/>
    <PortraitTextureCoords/>
    <SmallPortraitTexture>...</SmallPortraitTexture>
    <SmallPortraitTextureCoords/>      <-- often missing in broken civs
    <SmallPortraitTextureWPF>...</SmallPortraitTextureWPF>

The 13 broken civs had:

    <BannerTexture/>
    <BannerTextureCoords/>
    <PortraitTexture/>
    <PortraitTextureCoords/>
    <SmallPortraitTextureWPF>...</SmallPortraitTextureWPF>   <-- WPF first
    <SmallPortraitTexture>...</SmallPortraitTexture>          <-- DDT second
    (no <SmallPortraitTextureCoords/>)

The AoE3 DE engine parses ``<MatchmakingTextures>`` children by ordinal
position. When the order is inverted, the engine reads
``SmallPortraitTextureWPF`` into the slot it expects to be the DDT path,
and ``SmallPortraitTexture`` into the slot it expects to be Coords —
silently corrupting both. F10 Player Communication panel renders blank
for those civs.

This script normalises all civmod ``<MatchmakingTextures>`` blocks to the
canonical order and inserts a self-closing ``<SmallPortraitTextureCoords/>``
when it is missing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CIVMODS = REPO_ROOT / "data" / "civmods.xml"

CANONICAL_FIELDS = [
    "BannerTexture",
    "BannerTextureCoords",
    "PortraitTexture",
    "PortraitTextureCoords",
    "SmallPortraitTexture",
    "SmallPortraitTextureCoords",
    "SmallPortraitTextureWPF",
]


def reorder_matchmaking_block(block: str, indent: str = "\t\t\t") -> tuple[str, bool]:
    """Reorder a ``<MatchmakingTextures>`` block's children to canonical order.

    Returns (new_block, changed?). Preserves indentation prefix.
    """
    # Capture every direct child element, both self-closing and open/close.
    pattern = re.compile(
        r"<(?P<name>[A-Za-z]+)\b(?P<attrs>[^>/]*)"
        r"(?:/>|>(?P<inner>[^<]*)</(?P=name)>)"
    )
    fields: dict[str, str] = {}
    for m in pattern.finditer(block):
        name = m.group("name")
        # Reconstruct the exact tag text the matcher matched
        fields[name] = m.group(0)

    if not fields:
        return block, False

    # Detect whether the existing order is already canonical.
    existing_order = [name for name in re.findall(r"<([A-Za-z]+)\b", block)]
    expected_order = [f for f in CANONICAL_FIELDS if f in fields]
    if existing_order == expected_order and "SmallPortraitTextureCoords" in fields:
        return block, False

    # Ensure SmallPortraitTextureCoords exists (self-closing) if it's missing
    if "SmallPortraitTextureCoords" not in fields:
        fields["SmallPortraitTextureCoords"] = "<SmallPortraitTextureCoords />"

    # Rebuild block in canonical order with original indentation
    new_lines = []
    for field in CANONICAL_FIELDS:
        if field in fields:
            new_lines.append(f"{indent}{fields[field]}")
    return "\n".join(new_lines) + "\n", True


def fix_file(path: Path) -> tuple[int, list[str]]:
    """Apply field reorder to all ``<MatchmakingTextures>`` blocks. Returns
    (num_fixed, list_of_civ_names_touched)."""
    content = path.read_text()
    fixed = 0
    touched: list[str] = []

    # Capture each <Civ>...</Civ> block to know which civ a fix applies to
    civ_pattern = re.compile(
        r"(<Civ>\s*<Name>(?P<name>[^<]+)</Name>)(?P<body>.*?)(</Civ>)",
        re.DOTALL,
    )

    def fix_civ(match: re.Match) -> str:
        head, name, body, tail = (
            match.group(1),
            match.group("name"),
            match.group("body"),
            match.group(4),
        )

        # Find the inner MatchmakingTextures block
        mt_pattern = re.compile(
            r"(<MatchmakingTextures>\s*\n)(.*?)(\s*</MatchmakingTextures>)",
            re.DOTALL,
        )

        def fix_mt(mm: re.Match) -> str:
            nonlocal fixed
            opener, inner, closer = mm.group(1), mm.group(2), mm.group(3)
            # Detect indentation of children (default to 4 tabs based on file style)
            first_line = inner.lstrip("\n").splitlines()[0] if inner.strip() else ""
            indent_match = re.match(r"([ \t]+)", first_line)
            indent = indent_match.group(1) if indent_match else "\t\t\t"
            new_inner, changed = reorder_matchmaking_block(inner, indent=indent)
            if changed:
                fixed += 1
                touched.append(name)
                return opener + new_inner + closer
            return mm.group(0)

        new_body = mt_pattern.sub(fix_mt, body)
        return head + new_body + tail

    new_content = civ_pattern.sub(fix_civ, content)
    if new_content != content:
        path.write_text(new_content)
    return fixed, touched


def main() -> int:
    if not CIVMODS.exists():
        print(f"ERROR: {CIVMODS} not found", file=sys.stderr)
        return 2
    fixed, touched = fix_file(CIVMODS)
    print(f"Fixed {fixed} civmod entries in {CIVMODS}:")
    for name in touched:
        print(f"  - {name}")
    return 0 if fixed >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
