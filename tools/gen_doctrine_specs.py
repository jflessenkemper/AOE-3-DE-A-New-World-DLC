#!/usr/bin/env python3
"""gen_doctrine_specs.py — Regenerate data/doctrine_specs/*.yaml from playstyle_spec.json.

Usage:
    python3 tools/gen_doctrine_specs.py [--spec playstyle_spec.json] [--out data/doctrine_specs/]

This script is the authoritative generator for the per-civ YAML doctrine specs.
Do NOT edit the generated YAML files manually; edit playstyle_spec.json instead
and rerun this script.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WALL_STRATEGY_NAMES = {
    0: "home_fortress",
    1: "jungle_choke",
    2: "harbor_compound",
    3: "perimeter_ring",
    4: "rolling_front",
    5: "forward_operational",
}


def to_slug(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def yaml_str(val: str) -> str:
    """Quote YAML string if it contains special characters."""
    if any(c in val for c in [':', '#', '[', ']', '{', '}', '&', '*', '!', '|', ">", "'", '"', ',', '\n']):
        escaped = val.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return val


def wrap_prose(prose: str, width: int = 80, indent: int = 2) -> list[str]:
    """Wrap prose text for YAML block scalar with given indent."""
    prefix = " " * indent
    words = html.unescape(prose).split()
    lines = []
    current = prefix
    for word in words:
        if len(current) + len(word) + 1 > width + indent:
            lines.append(current.rstrip())
            current = prefix + word + " "
        else:
            current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return lines


def generate_yaml(civ_key: str, civ: dict) -> str:
    claims = civ.get("claims", {})
    wall_id = claims.get("wall_strategy")
    wall_name = WALL_STRATEGY_NAMES.get(wall_id, "unknown") if wall_id is not None else "unknown"
    mil_band = claims.get("military_distance_band")
    prose = civ.get("doctrine_prose", "")

    lines: list[str] = [
        f"# Doctrine spec for {civ_key}",
        f"# Generated from playstyle_spec.json — do not edit manually; regenerate via tools/gen_doctrine_specs.py",
        "",
        "schema_version: 1",
        f"data_name: {yaml_str(civ_key)}",
        f"civ_label: {yaml_str(civ['civ_label'])}",
        f"leader_label: {yaml_str(civ['leader_label'])}",
        "",
        f"doctrine_label: {yaml_str(civ['doctrine_label'])}",
        f"doctrine_summary: {yaml_str(civ['doctrine_summary'])}",
        "doctrine_prose: >-",
        *wrap_prose(prose),
        "",
        f"portrait_path: {yaml_str(civ['portrait_path'])}",
        "",
        "# Behavioural claims — validated by tools/validation/validate_doctrine_compliance.py",
        "claims:",
    ]

    if wall_id is not None:
        lines.append(f"  wall_strategy: {wall_id}  # {wall_name}")
    if "first_military_building" in claims:
        lines.append(f"  first_military_building: {yaml_str(claims['first_military_building'])}")
    for ms_key in ("first_barracks_before_ms", "first_dock_before_ms", "first_wall_before_ms"):
        if ms_key in claims:
            ms = claims[ms_key]
            lines.append(f"  {ms_key}: {ms}  # {ms // 60000}min {(ms % 60000) // 1000}s")
    if mil_band is not None:
        lines.append(f"  military_distance_band: [{mil_band[0]}, {mil_band[1]}]  # normalized distance to enemy TC")
    for bool_key in ("expects_forward", "expects_cavalry", "expects_infantry",
                     "expects_artillery", "expects_naval", "expects_treaty"):
        if bool_key in claims:
            lines.append(f"  {bool_key}: {'true' if claims[bool_key] else 'false'}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-civ doctrine YAML specs.")
    parser.add_argument(
        "--spec",
        type=Path,
        default=REPO_ROOT / "playstyle_spec.json",
        help="Path to playstyle_spec.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "data" / "doctrine_specs",
        help="Output directory for YAML files",
    )
    args = parser.parse_args()

    if not args.spec.exists():
        print(f"ERROR: spec file not found: {args.spec}")
        raise SystemExit(1)

    with open(args.spec) as f:
        spec = json.load(f)

    civs = spec.get("civs", {})
    args.out.mkdir(parents=True, exist_ok=True)

    written = 0
    for civ_key, civ in civs.items():
        slug = to_slug(civ_key)
        out_path = args.out / f"{slug}.yaml"
        out_path.write_text(generate_yaml(civ_key, civ))
        written += 1

    print(f"[gen_doctrine_specs] Written {written} YAML files to {args.out}")


if __name__ == "__main__":
    main()
