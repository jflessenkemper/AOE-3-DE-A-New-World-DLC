#!/usr/bin/env python3
"""Static validator: every building proto named in the wiki nations/building
map must resolve to a real proto in the extracted proto-name table.

docs/wiki/validation/nations-and-buildings.md documents each culture's
building roster as table rows:

    | Town Center        | `TownCenter`   | 1 |
    | War Hut            | `WarHut`       | 1 |
    | Fort               | `FortFrontier` | 3 |

The middle column is a proto name the engine must know. If a row cites a
proto that doesn't exist (typo, a renamed base proto, or a fabricated name),
the doc teaches a reader to look for a building that isn't there. This
validator extracts the proto from every building-table row and asserts it
exists in artifacts/unit_index/full_proto_name_to_locid.json — the extracted
authoritative map of every proto name (~2456 entries).

Scoped to table rows whose 2nd column is a single backticked CamelCase token,
so it does NOT trip over tech tokens (`DECivHasMosque`), effect subtypes
(`Enable`), or civ tokens (`ANWRioGrande`) that appear in prose elsewhere.

Usage:
    python3 tools/validation/validate_wiki_building_protos.py

Exit codes:
    0 — every building-table proto resolves (GREEN)
    1 — a referenced building proto is missing from the proto map, or the map
        itself is unreadable (RED — details printed)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WIKI = REPO / "docs" / "wiki" / "validation" / "nations-and-buildings.md"
PROTO_MAP = REPO / "artifacts" / "unit_index" / "full_proto_name_to_locid.json"

# | <display name> | `<Proto>` | <age> |   — capture the backticked proto.
ROW_RE = re.compile(r"^\|[^|]+\|\s*`([A-Za-z][A-Za-z0-9]+)`\s*\|\s*[^|]*\|")
# Non-proto placeholders that legitimately appear in the proto column for the
# few civs whose age-up building is engine-selected rather than a fixed proto.
ALLOW = {"base"}  # e.g. "base-game wonder set" rows use prose, not a token


def main() -> int:
    if not WIKI.exists():
        print(f"FAIL — wiki nations map not found: {WIKI.relative_to(REPO)}")
        return 1
    try:
        protos = set(json.loads(PROTO_MAP.read_text(encoding="utf-8")).keys())
    except (OSError, ValueError) as e:
        print(f"FAIL — cannot read proto map {PROTO_MAP.relative_to(REPO)}: {e}")
        return 1

    refs: set[str] = set()
    for line in WIKI.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if m and m.group(1) not in ALLOW:
            refs.add(m.group(1))

    missing = sorted(r for r in refs if r not in protos)

    print("Wiki building-proto check (every roster building resolves to a real proto)")
    print(f"  proto names in map: {len(protos)}")
    print(f"  building protos referenced in roster tables: {len(refs)}")
    print()

    if missing:
        print("FAIL — wiki building-table rows cite non-existent protos:")
        for r in missing:
            print(f"  {r}")
        return 1

    print(f"PASS — all {len(refs)} roster building protos resolve in the proto map.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
