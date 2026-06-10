#!/usr/bin/env python3
"""Static validator: every ANW civ token from data/civmods.xml must have an
EXPLICIT wall-strategy assignment reachable from aiWallKnobsByCiv.xs (a
``civKey == "ANW..."`` dispatch branch) OR from the leaderCommon.xs
per-civ ``gANWWallStrategy = ...`` assignment, so that no ANW civ silently
falls through to the global default (FortressRing=0).

Usage:
    python3 tools/validation/validate_anw_wall_strategy_coverage.py
    python3 -m tools.validation.validate_anw_wall_strategy_coverage

Exit codes:
    0 — every ANW civ has an explicit wall-strategy assignment (GREEN)
    1 — one or more ANW civs lack explicit coverage (RED — names are printed)
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CIVMODS_XML    = REPO / "data" / "civmods.xml"
DISPATCH_XS    = REPO / "game" / "ai" / "core" / "aiWallKnobsByCiv.xs"
LEADER_COMMON  = REPO / "game" / "ai" / "leaders" / "leaderCommon.xs"

# ---------------------------------------------------------------------------
# Step 1 — collect the 44 canonical ANW tokens from civmods.xml.
# ---------------------------------------------------------------------------

def _load_anw_tokens() -> list[str]:
    """Return all <name> values from civmods.xml where <main>1</main>."""
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
# Step 2 — collect dispatch branches in aiWallKnobsByCiv.xs.
# A branch is any line matching: civKey == "<token>"
# ---------------------------------------------------------------------------

_DISPATCH_RE = re.compile(r'civKey\s*==\s*"([^"]+)"')

def _load_dispatch_tokens(xs_path: Path) -> set[str]:
    """Return the set of civ-key strings matched in the dispatch XS."""
    text = xs_path.read_text(encoding="utf-8")
    return set(_DISPATCH_RE.findall(text))


# ---------------------------------------------------------------------------
# Step 3 — collect explicit gANWWallStrategy assignments in leaderCommon.xs.
# Strategy: split the file into per-civ blocks delimited by
#   else if (rvltName == "ANWXxx") { ... }
# and check each block individually for a gANWWallStrategy assignment.
# Using a block-by-block approach avoids cross-block regex matching.
# ---------------------------------------------------------------------------

_BLOCK_OPEN_RE  = re.compile(r'rvltName\s*==\s*"(ANW\w+)"')
_WALL_STRAT_RE  = re.compile(r'\bgANWWallStrategy\s*=')

def _load_leader_common_explicit(xs_path: Path) -> set[str]:
    """Return the set of ANW tokens that have an explicit gANWWallStrategy
    assignment within their own leaderCommon.xs block.

    Each block is delimited by ``rvltName == "ANWXxx"`` and ends at the
    matching closing brace (depth-tracked) before the next ``else if``.
    """
    text = xs_path.read_text(encoding="utf-8")
    explicit: set[str] = set()

    for m in _BLOCK_OPEN_RE.finditer(text):
        token = m.group(1)
        # Find the opening brace of this block (first '{' after the match).
        brace_start = text.find("{", m.end())
        if brace_start == -1:
            continue
        # Walk forward tracking brace depth to find the matching '}'.
        depth = 0
        pos = brace_start
        while pos < len(text):
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                depth -= 1
                if depth == 0:
                    break
            pos += 1
        block_body = text[brace_start : pos + 1]
        if _WALL_STRAT_RE.search(block_body):
            explicit.add(token)

    return explicit


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------

def check_coverage() -> tuple[list[str], list[str], list[str]]:
    """Return (all_anw_tokens, covered_tokens, missing_tokens)."""
    all_tokens    = _load_anw_tokens()
    dispatch_set  = _load_dispatch_tokens(DISPATCH_XS)
    explicit_set  = _load_leader_common_explicit(LEADER_COMMON)

    covered  = [t for t in all_tokens if t in dispatch_set or t in explicit_set]
    missing  = [t for t in all_tokens if t not in dispatch_set and t not in explicit_set]
    return all_tokens, covered, missing


def main() -> int:
    all_tokens, covered, missing = check_coverage()

    total   = len(all_tokens)
    n_cover = len(covered)
    n_miss  = len(missing)

    print(f"ANW wall-strategy coverage check")
    print(f"  civmods.xml canonical tokens : {total}")
    print(f"  explicitly covered           : {n_cover}")
    print(f"  missing explicit assignment  : {n_miss}")
    print()

    if missing:
        print("FAIL — the following ANW civ tokens have NO explicit wall-strategy assignment")
        print("and will silently fall through to the global default (FortressRing=0):")
        for tok in missing:
            print(f"  {tok}")
        print()
        print("Fix: add an entry for each token to wall_knob_calibration.py, re-emit XS,")
        print("     or add an explicit gANWWallStrategy assignment in leaderCommon.xs.")
        return 1

    print("PASS — all ANW civ tokens have an explicit wall-strategy assignment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
