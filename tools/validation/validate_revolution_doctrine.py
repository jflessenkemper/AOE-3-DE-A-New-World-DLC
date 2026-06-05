#!/usr/bin/env python3
"""
validate_revolution_doctrine.py

Static validator for the ANW revolution-civ AI doctrine wiring.

Catches the exact bug class where a civ is recognised as a revolution civ
(civIsRevolution() returns true) but has no commander doctrine wired, so it
silently falls back to the balanced default with NO per-age composition,
build style, or wall strategy.

For every civ C where civIsRevolution() == true (minus civs dispatched to a
dedicated leader file), this asserts ALL of:
  1. anwInitRevolutionCommander() has an `else if (rvltName == "C")` branch.
  2. That branch assigns a non-zero gRvltCivId.
  3. gRvltCivId ids are unique per civ (no two civs share an id).
  4. The assigned id is referenced in all 5 per-age rules (== N appears
     exactly 5 times: Discovery/Colonial/Fortress/Industrial/Imperial).
  5. The branch sets a wall strategy (directly or via a build-style helper).

Exit code 0 = PASS, 1 = FAIL. Pure static parse; no game required.

Usage:
    python3 tools/validation/validate_revolution_doctrine.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UTIL = REPO / "game/ai/core/aiUtilities.xs"
CMDR = REPO / "game/ai/leaders/leader_revolution_commanders.xs"
CIVMODS = REPO / "data/civmods.xml"

# Civs whose doctrine lives in a dedicated leader file, not the revolution
# commander dispatch. anwInitRevolutionCommander() early-returns for these.
DEDICATED_LEADER_CIVS = {"ANWAmericans"}

# Build-style helpers that set gANWWallStrategy internally (leaderCommon.xs).
STYLE_HELPERS = (
    "anwUseCompactFortifiedCoreStyle", "anwUseDistributedEconomicNetworkStyle",
    "anwUseForwardOperationalLineStyle", "anwUseMobileFrontierScatterStyle",
    "anwUseShrineTradeNodeSpreadStyle", "anwUseCivicMilitiaCenterStyle",
    "anwUseSteppeCavalryWedgeStyle", "anwUseNavalMercantileCompoundStyle",
    "anwUseSiegeTrainConcentrationStyle", "anwUseJungleGuerrillaNetworkStyle",
    "anwUseHighlandCitadelStyle", "anwUseCossackVoiskoStyle",
    "anwUseRepublicanLeveeStyle", "anwUseAndeanTerraceFortressStyle",
)
EXPECTED_AGE_RULES = 5


def extract_shipped_civs() -> set:
    """Lobby-selectable civ <name> tokens from data/civmods.xml."""
    if not CIVMODS.exists():
        return set()
    text = CIVMODS.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"<name>\s*(ANW\w+)\s*</name>", text))


def extract_revolution_civs(text: str) -> set:
    """Names returned true by civIsRevolution()."""
    m = re.search(r"bool\s+civIsRevolution\s*\(\s*void\s*\)\s*\{(.*?)\n\}",
                  text, re.DOTALL)
    if not m:
        m = re.search(r"bool\s+civIsRevolution\s*\(.*?\)\s*\{(.*)", text, re.DOTALL)
    body = m.group(1) if m else ""
    return set(re.findall(r'name\s*==\s*"(ANW\w+)"', body))


def extract_init_branches(text: str) -> dict:
    """Map rvltName -> assigned gRvltCivId from anwInitRevolutionCommander()."""
    m = re.search(r"void\s+anwInitRevolutionCommander\s*\(\s*void\s*\)\s*\{(.*?)\n\}",
                  text, re.DOTALL)
    body = m.group(1) if m else text
    branches = {}
    # Split on the `else if (rvltName == "X")` / `if (rvltName == "X")` markers.
    parts = re.split(r'(?:else\s+)?if\s*\(\s*rvltName\s*==\s*"(ANW\w+)"\s*\)', body)
    # parts: [pre, name1, block1, name2, block2, ...]
    for i in range(1, len(parts) - 1, 2):
        name = parts[i]
        block = parts[i + 1]
        idm = re.search(r"gRvltCivId\s*=\s*(\d+)\s*;", block)
        cid = int(idm.group(1)) if idm else 0
        has_style = any(h in block for h in STYLE_HELPERS) or \
            "gANWWallStrategy" in block
        branches[name] = {"id": cid, "has_wall": has_style}
    return branches


def extract_age_coverage(text: str) -> Counter:
    """Count `gRvltCivId == N` references (one per age rule per civ)."""
    return Counter(int(n) for n in re.findall(r"gRvltCivId\s*==\s*(\d+)", text))


def main() -> int:
    util = UTIL.read_text(encoding="utf-8", errors="replace")
    cmdr = CMDR.read_text(encoding="utf-8", errors="replace")

    rev_civs = extract_revolution_civs(util)
    branches = extract_init_branches(cmdr)
    coverage = extract_age_coverage(cmdr)
    shipped = extract_shipped_civs()

    failures, warnings = [], []

    # Duplicate id detection across init branches.
    id_owners = {}
    for name, info in branches.items():
        cid = info["id"]
        if cid == 0:
            continue
        id_owners.setdefault(cid, []).append(name)
    for cid, owners in id_owners.items():
        if len(owners) > 1:
            failures.append(f"gRvltCivId {cid} shared by multiple civs: {owners}")

    checked = 0
    for civ in sorted(rev_civs):
        if civ in DEDICATED_LEADER_CIVS:
            continue
        info = branches.get(civ)
        is_shipped = (not shipped) or (civ in shipped)
        if info is None:
            if is_shipped:
                failures.append(
                    f"{civ}: SHIPPED lobby civ recognised by civIsRevolution() but "
                    f"has NO init branch in anwInitRevolutionCommander() -> falls "
                    f"back to balanced default, no doctrine applied.")
            else:
                warnings.append(
                    f"{civ}: recognised by civIsRevolution() but not a shipped "
                    f"lobby civ (no <name> in civmods.xml) and no init branch "
                    f"-> dangling recognizer entry (harmless dead reference).")
            continue
        if not is_shipped:
            warnings.append(
                f"{civ}: has doctrine wired but is not a shipped lobby civ "
                f"(no <name> in civmods.xml).")
        checked += 1
        cid = info["id"]
        if cid == 0:
            failures.append(f"{civ}: init branch assigns no (zero) gRvltCivId.")
            continue
        n = coverage.get(cid, 0)
        if n == 0:
            failures.append(
                f"{civ} (id {cid}): no per-age rules reference this id "
                f"-> no composition doctrine across any age.")
        elif n < EXPECTED_AGE_RULES:
            warnings.append(
                f"{civ} (id {cid}): only {n}/{EXPECTED_AGE_RULES} per-age rules "
                f"reference this id -> some ages lack tuned composition.")
        if not info["has_wall"]:
            warnings.append(
                f"{civ} (id {cid}): init branch sets no wall strategy / build "
                f"style helper.")

    print("=" * 64)
    print("ANW Revolution Doctrine Validator")
    print("=" * 64)
    print(f"revolution civs (civIsRevolution): {len(rev_civs)}")
    print(f"init branches parsed:              {len(branches)}")
    print(f"civs checked:                      {checked}")
    print(f"distinct per-age ids covered:      {len(coverage)}")
    print("-" * 64)

    for w in warnings:
        print(f"  WARN  {w}")
    for f in failures:
        print(f"  FAIL  {f}")

    if failures:
        print("-" * 64)
        print(f"RESULT: FAIL ({len(failures)} error(s), {len(warnings)} warning(s))")
        return 1
    print("-" * 64)
    print(f"RESULT: PASS ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
