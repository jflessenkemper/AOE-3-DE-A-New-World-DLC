#!/usr/bin/env python3
"""Validate artifacts/nation_map/nation_map.json against authoritative sources.

Exit codes:
  0 — all assertions pass
  1 — one or more assertions failed
  0 (degrade) — a required input file is missing; prints a WARN and exits 0
                so CI is not blocked by a missing artifact (artifact must be
                generated first via the data-build step).

Assertions:
  A. Every active civ token from data/civmods.xml (main=1, ANW*) appears in
     nation_map.json.
  B. Every token in nation_map.json has a non-null home_city_name.
  C. Every token has a home-city alias in HOME_CITY_TO_TOKEN inside
     lobby_driver.py (required for post-launch identity OCR to work).
  D. Flags (WARN, not FAIL) tokens with empty expected_buildings lists
     (common-core only — may be intentional but worth surfacing).
  E. Every token in nation_map.json is also present in data/civmods.xml
     (no phantom entries).
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

NATION_MAP_PATH = REPO_ROOT / "artifacts" / "nation_map" / "nation_map.json"
CIVMODS_PATH    = REPO_ROOT / "data" / "civmods.xml"
LOBBY_DRIVER_PATH = REPO_ROOT / "tools" / "aoe3_automation" / "lobby_driver.py"


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_active_tokens_from_civmods(path: Path) -> set[str]:
    """Parse civmods.xml and return set of tokens where main=1 and name starts ANW."""
    root = ET.parse(path).getroot()
    tokens: set[str] = set()
    for civ in root.findall(".//civ"):
        n = civ.find("name")
        m = civ.find("main")
        if n is not None and m is not None and m.text == "1":
            tok = n.text
            if tok and tok.startswith("ANW"):
                tokens.add(tok)
    return tokens


def _extract_home_city_to_token(path: Path) -> dict[str, str]:
    """Read HOME_CITY_TO_TOKEN dict from lobby_driver.py via regex (no import)."""
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"HOME_CITY_TO_TOKEN\s*:\s*dict\[.*?\]\s*=\s*\{(.*?)\}",
        text,
        re.DOTALL,
    )
    if not m:
        return {}
    block = m.group(1)
    result: dict[str, str] = {}
    for line_m in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', block):
        result[line_m.group(1)] = line_m.group(2)
    return result


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    # ── Degrade-gracefully if inputs are missing ─────────────────────────────
    missing = [p for p in (NATION_MAP_PATH, CIVMODS_PATH, LOBBY_DRIVER_PATH)
               if not p.exists()]
    if missing:
        for p in missing:
            print(f"WARN  missing input: {p.relative_to(REPO_ROOT)}")
        print("WARN  validate_nation_map: inputs missing — skipping (degrade-0)")
        return 0

    # ── Load data ────────────────────────────────────────────────────────────
    with open(NATION_MAP_PATH, encoding="utf-8") as f:
        nation_map: dict = json.load(f)

    active_tokens = _load_active_tokens_from_civmods(CIVMODS_PATH)
    hc_to_token   = _extract_home_city_to_token(LOBBY_DRIVER_PATH)
    # Reverse: token -> set of aliases
    token_aliases: dict[str, set[str]] = {}
    for hc, tok in hc_to_token.items():
        token_aliases.setdefault(tok, set()).add(hc)

    # ── Assertion A: every active civmods token appears in nation_map ────────
    for tok in sorted(active_tokens):
        if tok not in nation_map:
            failures.append(
                f"FAIL  A: token {tok!r} is active in civmods.xml but absent from nation_map.json"
            )

    # ── Assertion E: no phantom entries in nation_map ────────────────────────
    for tok in sorted(nation_map):
        if tok not in active_tokens:
            failures.append(
                f"FAIL  E: token {tok!r} is in nation_map.json but NOT active in civmods.xml"
            )

    # ── Per-token assertions B, C, D ─────────────────────────────────────────
    missing_hcn: list[str]   = []
    missing_alias: list[str] = []
    empty_buildings: list[str] = []

    for tok, entry in sorted(nation_map.items()):
        # B: non-null home_city_name
        if not entry.get("home_city_name"):
            missing_hcn.append(tok)

        # C: has alias in HOME_CITY_TO_TOKEN
        if not token_aliases.get(tok):
            missing_alias.append(tok)

        # D: expected_buildings non-empty (warn only)
        if not entry.get("expected_buildings"):
            empty_buildings.append(tok)

    if missing_hcn:
        for tok in missing_hcn:
            failures.append(
                f"FAIL  B: {tok!r} has null home_city_name — identity OCR target missing"
            )

    if missing_alias:
        for tok in missing_alias:
            failures.append(
                f"FAIL  C: {tok!r} has no HOME_CITY_TO_TOKEN alias — "
                f"post-launch identity OCR will silently fail for this civ"
            )

    if empty_buildings:
        for tok in empty_buildings:
            warnings.append(
                f"WARN  D: {tok!r} has empty expected_buildings — "
                f"building tour will only visit common-core structures"
            )

    # ── Print summary ─────────────────────────────────────────────────────────
    total_civs = len(active_tokens)
    alias_count = sum(1 for tok in nation_map if token_aliases.get(tok))

    print(f"nation_map: {len(nation_map)} entries, {total_civs} active civmods tokens")
    print(f"  has home_city_name : {sum(1 for e in nation_map.values() if e.get('home_city_name'))}/{len(nation_map)}")
    print(f"  has alias          : {alias_count}/{len(nation_map)}")
    print(f"  missing alias      : {len(missing_alias)} (critical — identity OCR broken)")
    print(f"  empty buildings    : {len(empty_buildings)} (warn)")

    for w in warnings:
        print(w)
    for f_ in failures:
        print(f_)

    if failures:
        print(f"\nRESULT: FAIL ({len(failures)} failures, {len(warnings)} warnings)")
        return 1
    else:
        if warnings:
            print(f"\nRESULT: PASS with {len(warnings)} warnings")
        else:
            print("\nRESULT: PASS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
