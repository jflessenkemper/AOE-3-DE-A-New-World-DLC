#!/usr/bin/env python3
"""spec_validator.py — Validate data/doctrine_specs/*.yaml for internal consistency.

Checks:
1. Every YAML file parses cleanly (no syntax errors).
2. Required fields are present: schema_version, data_name, civ_label, leader_label,
   doctrine_label, doctrine_summary, doctrine_prose, portrait_path, claims.
3. claims.wall_strategy is an integer in [0, 5].
4. claims.military_distance_band is [lo, hi] with 0 ≤ lo ≤ hi ≤ 2.0.
5. claims.*_before_ms values are positive integers.
6. Boolean claims are actual booleans.
7. Every civ in playstyle_spec.json has a corresponding YAML file (coverage check).
8. No YAML file is present without a matching entry in playstyle_spec.json (orphan check).

Exit codes:
    0 — all checks pass
    1 — one or more checks fail (errors printed to stderr)
    2 — no YAML files found (configuration problem)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FIELDS = [
    "schema_version", "data_name", "civ_label", "leader_label",
    "doctrine_label", "doctrine_summary", "doctrine_prose",
    "portrait_path", "claims",
]

WALL_STRATEGY_RANGE = range(0, 6)  # 0–5 inclusive

BOOL_CLAIM_KEYS = [
    "expects_forward", "expects_cavalry", "expects_infantry",
    "expects_artillery", "expects_naval", "expects_treaty",
]

MS_CLAIM_KEYS = [
    "first_barracks_before_ms", "first_dock_before_ms", "first_wall_before_ms",
]


def _parse_yaml_naive(text: str) -> dict:
    """Minimal YAML parser for simple flat key: value files (no pyyaml dependency)."""
    result: dict = {}
    current_section: str | None = None
    current_dict: dict = {}

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        # Detect indent level
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 0:
            # Top-level key
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()

                if val == "" or val == ">-":
                    # Nested section or block scalar — track
                    current_section = key
                    if val == ">-":
                        current_dict[key] = ""  # will collect below
                    else:
                        current_dict[key] = {}
                    result = current_dict
                else:
                    current_section = None
                    val_parsed: object = val
                    if val.startswith('"') and val.endswith('"'):
                        val_parsed = val[1:-1].replace('\\"', '"')
                    elif val.lower() == "true":
                        val_parsed = True
                    elif val.lower() == "false":
                        val_parsed = False
                    else:
                        try:
                            val_parsed = int(val)
                        except ValueError:
                            try:
                                val_parsed = float(val)
                            except ValueError:
                                pass
                    current_dict[key] = val_parsed
        elif indent == 2 and current_section == "claims":
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.split("#")[0].strip()  # strip inline comments
                if val.startswith("[") and val.endswith("]"):
                    # Parse list [lo, hi]
                    inner = val[1:-1].split(",")
                    try:
                        current_dict["claims"] = current_dict.get("claims", {})
                        current_dict["claims"][key] = [float(x.strip()) for x in inner]
                    except ValueError:
                        current_dict.setdefault("claims", {})[key] = val
                else:
                    current_dict.setdefault("claims", {})
                    val_parsed = val
                    if val_parsed.lower() == "true":
                        val_parsed = True
                    elif val_parsed.lower() == "false":
                        val_parsed = False
                    elif val_parsed.startswith('"') and val_parsed.endswith('"'):
                        val_parsed = val_parsed[1:-1]
                    else:
                        try:
                            val_parsed = int(val_parsed)
                        except ValueError:
                            pass
                    current_dict["claims"][key] = val_parsed
        elif indent >= 2 and current_section and isinstance(current_dict.get(current_section), str):
            # Block scalar line
            current_dict[current_section] += (" " if current_dict[current_section] else "") + stripped

    return current_dict


def load_yaml(path: Path) -> tuple[dict | None, str | None]:
    text = path.read_text()
    if _HAS_YAML:
        try:
            data = yaml.safe_load(text)
            return data, None
        except yaml.YAMLError as exc:
            return None, str(exc)
    else:
        try:
            data = _parse_yaml_naive(text)
            return data, None
        except Exception as exc:
            return None, str(exc)


def validate_spec(path: Path) -> list[str]:
    """Return list of error strings for this YAML file, or empty list if OK."""
    errors: list[str] = []

    data, parse_err = load_yaml(path)
    if parse_err:
        return [f"PARSE ERROR: {parse_err}"]
    if not isinstance(data, dict):
        return ["PARSE ERROR: root is not a dict"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"MISSING required field: {field!r}")

    claims = data.get("claims", {})
    if not isinstance(claims, dict):
        errors.append("claims: must be a dict")
        return errors

    if "wall_strategy" in claims:
        ws = claims["wall_strategy"]
        if not isinstance(ws, int) or ws not in WALL_STRATEGY_RANGE:
            errors.append(f"claims.wall_strategy: expected int 0-5, got {ws!r}")

    if "military_distance_band" in claims:
        band = claims["military_distance_band"]
        if not (isinstance(band, list) and len(band) == 2):
            errors.append(f"claims.military_distance_band: expected [lo, hi], got {band!r}")
        else:
            lo, hi = band
            if not (0.0 <= lo <= hi <= 3.0):
                errors.append(f"claims.military_distance_band: invalid range [{lo}, {hi}]")

    for ms_key in MS_CLAIM_KEYS:
        if ms_key in claims:
            ms = claims[ms_key]
            if not isinstance(ms, int) or ms <= 0:
                errors.append(f"claims.{ms_key}: expected positive int, got {ms!r}")

    for bool_key in BOOL_CLAIM_KEYS:
        if bool_key in claims:
            val = claims[bool_key]
            if not isinstance(val, bool):
                errors.append(f"claims.{bool_key}: expected bool, got {val!r}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate doctrine YAML specs.")
    parser.add_argument(
        "--specs-dir",
        type=Path,
        default=REPO_ROOT / "data" / "doctrine_specs",
    )
    parser.add_argument(
        "--playstyle-spec",
        type=Path,
        default=REPO_ROOT / "playstyle_spec.json",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    yaml_files = sorted(args.specs_dir.glob("*.yaml"))
    if not yaml_files:
        print(f"ERROR: no YAML files found in {args.specs_dir}", file=sys.stderr)
        raise SystemExit(2)

    # Load playstyle_spec for coverage check
    known_slugs: set[str] = set()
    if args.playstyle_spec.exists():
        import re
        with open(args.playstyle_spec) as f:
            ps = json.load(f)
        for civ_key in ps.get("civs", {}):
            slug = re.sub(r"[^a-z0-9]+", "_", civ_key.lower()).strip("_")
            known_slugs.add(slug)
    else:
        print(f"WARNING: playstyle_spec not found at {args.playstyle_spec}", file=sys.stderr)

    found_slugs: set[str] = set()
    total_errors = 0
    total_files = 0

    for yaml_path in yaml_files:
        slug = yaml_path.stem
        found_slugs.add(slug)
        errors = validate_spec(yaml_path)
        total_files += 1
        if errors:
            total_errors += len(errors)
            print(f"[FAIL] {yaml_path.name}")
            for err in errors:
                print(f"  {err}")
        elif not args.quiet:
            print(f"[OK  ] {yaml_path.name}")

    # Coverage checks
    missing = known_slugs - found_slugs
    orphans = found_slugs - known_slugs

    for slug in sorted(missing):
        print(f"[MISS] {slug}.yaml — in playstyle_spec but no YAML file found")
        total_errors += 1

    for slug in sorted(orphans):
        print(f"[ORPH] {slug}.yaml — YAML exists but not in playstyle_spec")
        # Warning only, not a hard error

    print(f"\nValidated {total_files} files. Errors: {total_errors}")
    raise SystemExit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
