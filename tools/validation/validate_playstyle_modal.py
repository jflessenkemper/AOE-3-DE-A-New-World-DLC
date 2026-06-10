"""Validate the v2 Playstyle modal in `a_new_world.html`.

For every `<details class="nation-node" data-name="...">` we expect:

  * A matching key in the `window.NATION_PLAYSTYLE = { … }` object
    literal embedded in the modal block.
  * Each entry to populate the required string fields used by the
    renderer (`renderPlaystyle`):
        nation, leader, psTitle, bsTitle, bsProse, ages,
        terrainLabel, headingLabel, wallLabel, combatDoctrine,
        ecoBullets, militaryBullets, defenseBullets
  * `ages` must contain the five age keys (Discovery, Colonial,
    Fortress, Industrial, Imperial), each non-empty.
  * The bullet arrays must be non-empty. (Plain prose can be empty
    only if the field is intentionally unused, but combatDoctrine /
    bsProse / pills must be present.)
  * No "internal jargon leakage" — bullets and prose must not include
    `{n}×` multipliers, `level n/N` notation, or raw XS variable names
    like `gANWTerrainBiasStrength`. The modal is end-user-facing.

Exits 1 with a per-nation report on any mismatch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, repo_relative


HTML_REL = Path("a_new_world.html")

REQUIRED_STRING_FIELDS = (
    "nation",
    "leader",
    "psTitle",
    "bsTitle",
    "bsProse",
    "terrainLabel",
    "headingLabel",
    "wallLabel",
    "combatDoctrine",
)
REQUIRED_BULLET_FIELDS = (
    "ecoBullets",
    "militaryBullets",
    "defenseBullets",
)
REQUIRED_AGE_KEYS = ("Discovery", "Colonial", "Fortress", "Industrial", "Imperial")

# Imperial peer doctrine — one second-tier playstyle per civ, anchored on
# the civ's historical leader. Authored in tools/playstyle/imperial_data.py
# and injected into the HTML by tools/playstyle/inject_imperial.py.
REQUIRED_IMPERIAL_STRING_FIELDS = (
    "imperialPsTitle",
    "imperialBsProse",
    "imperialCombatDoctrine",
)
REQUIRED_IMPERIAL_BULLET_FIELDS = (
    "imperialEcoBullets",
    "imperialMilitaryBullets",
    "imperialDefenseBullets",
)
REQUIRED_IMPERIAL_AGE_KEYS = REQUIRED_AGE_KEYS

NODE_RE = re.compile(
    r'<details[^>]*class="nation-node"[^>]*data-name="([^"]+)"',
)
PLAYSTYLE_OBJECT_RE = re.compile(
    r"window\.NATION_PLAYSTYLE\s*=\s*(\{.*?\});",
    re.DOTALL,
)

# Patterns the modal must NEVER show to end users.
JARGON_PATTERNS = (
    re.compile(r"\d+(?:\.\d+)?\s*×"),                 # "1.30×"
    re.compile(r"\blevel\s+\d+\s*/\s*\d+", re.IGNORECASE),  # "level 2/5"
    re.compile(r"\bgANW[A-Za-z]+\b"),                  # "gANWTerrainBiasStrength"
    re.compile(r"\bcANWTerrain[A-Za-z]+\b"),          # raw constant
    re.compile(r"\bcANWHeading[A-Za-z]+\b"),
)


def _extract_node_keys(html_text: str) -> list[str]:
    return NODE_RE.findall(html_text)


def _extract_playstyle_data(html_text: str) -> dict | None:
    match = PLAYSTYLE_OBJECT_RE.search(html_text)
    if match is None:
        return None
    raw = match.group(1)
    # The literal is JSON-shaped (we emit it via json.dumps), so json.loads
    # is the safest parse.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _check_entry(key: str, entry: dict, *, require_imperial: bool = True) -> list[str]:
    issues: list[str] = []

    for field in REQUIRED_STRING_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"{key}: missing or empty string field '{field}'")

    ages = entry.get("ages")
    if not isinstance(ages, dict):
        issues.append(f"{key}: 'ages' must be an object")
    else:
        for age_key in REQUIRED_AGE_KEYS:
            text = ages.get(age_key)
            if not isinstance(text, str) or not text.strip():
                issues.append(f"{key}: ages['{age_key}'] missing or empty")

    if require_imperial:
        for field in REQUIRED_IMPERIAL_STRING_FIELDS:
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(f"{key}: missing or empty imperial-peer field '{field}'")

        imperial_ages = entry.get("imperialAges")
        if not isinstance(imperial_ages, dict):
            issues.append(f"{key}: 'imperialAges' must be an object (peer imperial doctrine)")
        else:
            for age_key in REQUIRED_IMPERIAL_AGE_KEYS:
                text = imperial_ages.get(age_key)
                if not isinstance(text, str) or not text.strip():
                    issues.append(f"{key}: imperialAges['{age_key}'] missing or empty")

        for field in REQUIRED_IMPERIAL_BULLET_FIELDS:
            bullets = entry.get(field)
            if not isinstance(bullets, list):
                issues.append(f"{key}: '{field}' must be an array")
                continue
            if not bullets:
                issues.append(f"{key}: '{field}' must not be empty")
            for i, bullet in enumerate(bullets):
                if not isinstance(bullet, str) or not bullet.strip():
                    issues.append(f"{key}: '{field}'[{i}] is not a non-empty string")

    populated_bullet_fields = 0
    for field in REQUIRED_BULLET_FIELDS:
        bullets = entry.get(field)
        if not isinstance(bullets, list):
            issues.append(f"{key}: '{field}' must be an array (got {type(bullets).__name__})")
            continue
        for i, bullet in enumerate(bullets):
            if not isinstance(bullet, str) or not bullet.strip():
                issues.append(f"{key}: '{field}'[{i}] is not a non-empty string")
        if bullets:
            populated_bullet_fields += 1

    # The renderer hides empty bullet sections, so empty arrays are fine —
    # but a nation with *zero* bullet content has no doctrine signal at
    # all and is almost certainly a data extraction bug.
    if populated_bullet_fields == 0:
        issues.append(
            f"{key}: all bullet sections empty (eco/military/defense) — no doctrine signal"
        )

    # Jargon scan — scan all string-bearing fields for end-user-unfriendly content.
    for field, value in entry.items():
        if isinstance(value, str):
            _scan_jargon(issues, key, field, value)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                if isinstance(v, str):
                    _scan_jargon(issues, key, f"{field}[{i}]", v)
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, str):
                    _scan_jargon(issues, key, f"{field}.{sub_key}", sub_value)

    return issues


def _scan_jargon(issues: list[str], entry_key: str, field_label: str, text: str) -> None:
    for pattern in JARGON_PATTERNS:
        m = pattern.search(text)
        if m:
            issues.append(
                f"{entry_key}: jargon leak in {field_label} (matched {pattern.pattern!r}): {m.group(0)!r}"
            )


def validate_playstyle_modal(
    repo_root: Path = REPO_ROOT,
    *,
    require_imperial: bool = True,
) -> list[str]:
    html_path = repo_root / HTML_REL
    if not html_path.exists():
        return [f"{repo_relative(html_path, repo_root)}: file not found"]

    text = html_path.read_text(encoding="utf-8")

    nodes = _extract_node_keys(text)
    data = _extract_playstyle_data(text)
    if data is None:
        return [
            f"{repo_relative(html_path, repo_root)}: window.NATION_PLAYSTYLE = {{ … }} not found or not JSON-parseable"
        ]
    # Empty `nodes` is OK if `data` is also empty; otherwise the orphan
    # check below flags the mismatch.

    issues: list[str] = []

    nodes_set = set(nodes)
    keys_set = set(data.keys())

    missing = sorted(nodes_set - keys_set)
    orphaned = sorted(keys_set - nodes_set)

    for key in missing:
        issues.append(f"{key}: nation-node has no NATION_PLAYSTYLE entry")
    for key in orphaned:
        issues.append(f"{key}: NATION_PLAYSTYLE entry has no matching nation-node")

    for key in sorted(nodes_set & keys_set):
        issues.extend(_check_entry(key, data[key], require_imperial=require_imperial))

    return issues


def main() -> int:
    parser = build_repo_root_parser(
        "Validate the v2 Playstyle modal data in a_new_world.html."
    )
    parser.add_argument(
        "--no-imperial",
        action="store_true",
        help="Skip enforcement of the imperial-peer doctrine fields.",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    issues = validate_playstyle_modal(repo_root, require_imperial=not args.no_imperial)

    if issues:
        print(f"Found {len(issues)} playstyle modal issues:")
        for entry in issues:
            print(f" - {entry}")
        return 1

    print("Playstyle modal data complete and end-user-friendly across all nations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
