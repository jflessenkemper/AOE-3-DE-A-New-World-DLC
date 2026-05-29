"""Validate the historical terrain + heading enforcement layer is wired
for every civ.

For the 22 base civs, 26 revolution civs, and 40 ANW civs we expect:

  * `llApplyBuildStyleForActiveCiv()` in
    `game/ai/leaders/leaderCommon.xs` to contain a branch that calls
    `llSetPreferredTerrain(...)` and `llSetExpansionHeading(...)`.
  * Each call must reference a `cLLTerrain*` / `cLLHeading*` constant
    that is actually declared in `game/ai/aiHeader.xs`.
  * The bias-strength argument (third positional arg to
    `llSetPreferredTerrain`, second to `llSetExpansionHeading`) must be
    a numeric literal in the closed range [0.0, 1.0].

Exits 1 with a per-civ report on any mismatch.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, repo_relative


HEADER_REL = Path("game/ai/aiHeader.xs")
LEADER_COMMON_REL = Path("game/ai/leaders/leaderCommon.xs")

# Civs we expect to be wired. Names are the cMyCiv constants for base
# civs and the kbGetCivName() string keys for revolution civs.
BASE_CIVS = (
    "cCivBritish",
    "cCivChinese",
    "cCivDEAmericans",
    "cCivDEEthiopians",
    "cCivDEHausa",
    "cCivDEInca",
    "cCivDEItalians",
    "cCivDEMaltese",
    "cCivDEMexicans",
    "cCivDESwedish",
    "cCivDutch",
    "cCivFrench",
    "cCivGermans",
    "cCivIndians",
    "cCivJapanese",
    "cCivOttomans",
    "cCivPortuguese",
    "cCivRussians",
    "cCivSpanish",
    "cCivXPAztec",
    "cCivXPIroquois",
    "cCivXPSioux",
)

REVOLUTION_CIVS = (
    "ANWAmericans",
    "ANWArgentines",
    "ANWBajaCalifornians",
    "ANWBarbary",
    "ANWBrazil",
    "ANWCanadians",
    "ANWChileans",
    "ANWColumbians",
    "ANWEgyptians",
    "ANWFinnish",
    "ANWHaitians",
    "ANWHungarians",
    "ANWIndonesians",
    "ANWMayans",
    "ANWMexicans",
    "ANWNapoleonicFrance",
    "ANWPeruvians",
    "ANWRevFrance",
    "ANWRioGrande",
    "ANWRomanians",
    "ANWSouthAfricans",
    "ANWTexians",
)

ANW_CIVS = (
    # 19 ANW revolution / variant civs
    "ANWArgentines",
    "ANWBarbary",
    "ANWBrazil",
    "ANWCanadians",
    "ANWChileans",
    "ANWColumbians",
    "ANWEgyptians",
    "ANWFinnish",
    "ANWHaitians",
    "ANWHungarians",
    "ANWIndonesians",
    "ANWMayans",
    "ANWMexicans",
    "ANWNapoleonicFrance",
    "ANWPeruvians",
    "ANWRevFrance",
    "ANWRomanians",
    "ANWSouthAfricans",
    "ANWTexians",
    # 21 ANW canonical civs (mod-added; cMyCiv != cCivXxx so name-dispatched)
    "ANWAztecs",
    "ANWBritish",
    "ANWChinese",
    "ANWDutch",
    "ANWEthiopians",
    "ANWFrench",
    "ANWGermans",
    "ANWHaudenosaunee",
    "ANWHausa",
    "ANWInca",
    "ANWIndians",
    "ANWItalians",
    "ANWJapanese",
    "ANWLakota",
    "ANWMaltese",
    "ANWOttomans",
    "ANWPortuguese",
    "ANWRussians",
    "ANWSpanish",
    "ANWSwedes",
    "ANWUSA",
)

# Vanilla-compatibility branches kept in the XS files for defensive fallback
# when a player revolts INTO one of these civs via the base game.  They are
# NOT ANW civs — no nation-card content — so they're excluded from the roster
# check but silently tolerated rather than flagged as unexpected.
VANILLA_COMPAT_CIVS = frozenset({
    "ANWCalifornians",
    "ANWCentralAmericans",
    "ANWYucatan",
})

EXPECTED_TOTAL = len(BASE_CIVS) + len(REVOLUTION_CIVS) + len(ANW_CIVS)

TERRAIN_CONST_RE = re.compile(r"\bcLLTerrain[A-Za-z]+\b")
HEADING_CONST_RE = re.compile(r"\bcLLHeading[A-Za-z]+\b")
APPLY_FN_HEADER_RE = re.compile(
    r"void\s+llApplyBuildStyleForActiveCiv\s*\(.*?\)\s*\{",
    re.DOTALL,
)


def _extract_constants(header_text: str) -> tuple[set[str], set[str]]:
    terrain = set(TERRAIN_CONST_RE.findall(header_text))
    heading = set(HEADING_CONST_RE.findall(header_text))
    return terrain, heading


def _extract_apply_body(leader_common_text: str) -> str | None:
    match = APPLY_FN_HEADER_RE.search(leader_common_text)
    if match is None:
        return None
    # The function body starts immediately after the opening brace; walk
    # the source counting braces so nested if-blocks don't terminate the
    # outer match early.
    start = match.end()
    depth = 1
    i = start
    while i < len(leader_common_text) and depth > 0:
        ch = leader_common_text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return leader_common_text[start : i - 1]


def _split_branches(body: str) -> list[tuple[str, str]]:
    """Return [(label, branch_body), …] for each `if` / `else if` branch
    in the function body. Label is the cMyCiv constant or rvltName
    string literal that the branch tests against.
    """
    pat = re.compile(
        r"(?:if|else\s+if)\s*\(\s*"
        r"(?:cMyCiv\s*==\s*(?P<civ>cCiv[A-Za-z0-9_]+)"
        r"|rvltName\s*==\s*\"(?P<rvlt>[^\"]+)\")"
        r"\s*\)\s*\{",
        re.DOTALL,
    )
    out: list[tuple[str, str]] = []
    for m in pat.finditer(body):
        # Find the matching close brace, accounting for nested braces.
        depth = 1
        i = m.end()
        while i < len(body) and depth > 0:
            ch = body[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        branch_body = body[m.end():i - 1]
        label = m.group("civ") or m.group("rvlt")
        out.append((label, branch_body))
    return out


def _check_branch(
    label: str,
    branch_body: str,
    terrain_consts: set[str],
    heading_consts: set[str],
) -> list[str]:
    issues: list[str] = []

    terrain_calls = re.findall(
        r"llSetPreferredTerrain\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)",
        branch_body,
    )
    heading_calls = re.findall(
        r"llSetExpansionHeading\s*\(\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)",
        branch_body,
    )

    if not terrain_calls:
        issues.append(f"{label}: missing llSetPreferredTerrain(...) call")
    if not heading_calls:
        issues.append(f"{label}: missing llSetExpansionHeading(...) call")

    for primary, secondary, strength in terrain_calls:
        for token in (primary, secondary):
            token = token.strip()
            if token not in terrain_consts:
                issues.append(
                    f"{label}: llSetPreferredTerrain refers to unknown terrain constant '{token}'"
                )
        try:
            value = float(strength.strip())
        except ValueError:
            issues.append(
                f"{label}: llSetPreferredTerrain strength '{strength.strip()}' is not a numeric literal"
            )
        else:
            if not 0.0 <= value <= 1.0:
                issues.append(
                    f"{label}: llSetPreferredTerrain strength {value} outside [0.0, 1.0]"
                )

    for heading, strength in heading_calls:
        token = heading.strip()
        if token not in heading_consts:
            issues.append(
                f"{label}: llSetExpansionHeading refers to unknown heading constant '{token}'"
            )
        try:
            value = float(strength.strip())
        except ValueError:
            issues.append(
                f"{label}: llSetExpansionHeading strength '{strength.strip()}' is not a numeric literal"
            )
        else:
            if not 0.0 <= value <= 1.0:
                issues.append(
                    f"{label}: llSetExpansionHeading strength {value} outside [0.0, 1.0]"
                )

    return issues


def validate_terrain_heading(repo_root: Path = REPO_ROOT) -> list[str]:
    header_path = repo_root / HEADER_REL
    leader_path = repo_root / LEADER_COMMON_REL

    if not header_path.exists():
        return [f"{repo_relative(header_path, repo_root)}: file not found"]
    if not leader_path.exists():
        return [f"{repo_relative(leader_path, repo_root)}: file not found"]

    header_text = header_path.read_text(encoding="utf-8")
    leader_text = leader_path.read_text(encoding="utf-8")

    terrain_consts, heading_consts = _extract_constants(header_text)
    if not terrain_consts:
        return [f"{repo_relative(header_path, repo_root)}: no cLLTerrain* constants found"]
    if not heading_consts:
        return [f"{repo_relative(header_path, repo_root)}: no cLLHeading* constants found"]

    body = _extract_apply_body(leader_text)
    if body is None:
        return [
            f"{repo_relative(leader_path, repo_root)}: llApplyBuildStyleForActiveCiv() function body not found"
        ]

    branches = _split_branches(body)
    branch_labels = {label for label, _ in branches}

    issues: list[str] = []

    expected = set(BASE_CIVS) | set(REVOLUTION_CIVS) | set(ANW_CIVS)
    missing = sorted(expected - branch_labels)
    for label in missing:
        issues.append(f"{label}: no branch in llApplyBuildStyleForActiveCiv()")

    for label, branch_body in branches:
        if label not in expected:
            if label in VANILLA_COMPAT_CIVS:
                # Vanilla-compatibility fallback branch — intentionally kept in
                # XS but not an ANW civ.  Silently skip.
                continue
            # Tolerate experimental branches but flag them so they don't drift.
            issues.append(f"{label}: unexpected civ branch (not in known ANW roster)")
            continue
        issues.extend(_check_branch(label, branch_body, terrain_consts, heading_consts))

    return issues


def main() -> int:
    parser = build_repo_root_parser(
        "Validate terrain + heading enforcement is wired for every civ."
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    issues = validate_terrain_heading(repo_root)

    if issues:
        print(f"Found {len(issues)} terrain/heading wiring issues:")
        for entry in issues:
            print(f" - {entry}")
        return 1

    print(
        f"Terrain/heading wiring OK for {EXPECTED_TOTAL} civs "
        f"({len(BASE_CIVS)} base + {len(REVOLUTION_CIVS)} revolution + "
        f"{len(ANW_CIVS)} ANW [19 variant + 21 canonical])."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
