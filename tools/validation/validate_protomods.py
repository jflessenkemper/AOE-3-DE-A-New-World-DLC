"""Check data/protomods.xml for duplicate unit names, IDs, and dbid values that would cause silent engine collisions, and assert its structural invariants: the root element is <protomods> and every <unit> carries the merge-key `name` attribute (additive proto entries merge into the base table BY name — a nameless or wrong-rooted entry silently fails to merge)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, child_elements, get_attr_case_insensitive, get_child_text, local_name, repo_relative


def validate_protomods(repo_root: Path = REPO_ROOT) -> list[str]:
    proto_file = repo_root / "data" / "protomods.xml"

    try:
        root = ET.parse(proto_file).getroot()
    except ET.ParseError as exc:
        return [f"Failed to parse {repo_relative(proto_file, repo_root)}: {exc}"]

    issues: list[str] = []

    # Structural invariant 1: the root element must be <protomods>. A wrong
    # root (e.g. a copy-pasted base <proto> block) is silently ignored by the
    # additive merge — nothing from the file would take effect.
    if local_name(root.tag) != "protomods":
        issues.append(
            f"Root element is <{local_name(root.tag)}>, expected <protomods> "
            "(additive proto overlay must be rooted at <protomods>)")

    unit_names: list[str] = []
    unit_ids: list[str] = []
    dbids: list[str] = []
    missing_name = 0

    for unit in child_elements(root):
        if local_name(unit.tag) != "unit":
            continue

        unit_name = get_attr_case_insensitive(unit, "name")
        unit_id = get_attr_case_insensitive(unit, "id")
        dbid = get_child_text(unit, "dbid")

        # Structural invariant 2: every <unit> needs a non-empty `name` — that
        # is the merge key the additive overlay joins on. A nameless unit
        # silently fails to merge into the base proto table.
        if not (unit_name and unit_name.strip()):
            missing_name += 1

        if unit_name:
            unit_names.append(unit_name.lower())
        if unit_id:
            unit_ids.append(unit_id)
        if dbid:
            dbids.append(dbid)

    if missing_name:
        issues.append(
            f"{missing_name} <unit> element(s) missing the merge-key `name` "
            "attribute (would silently fail to merge)")

    duplicate_names = sorted(name for name, count in Counter(unit_names).items() if count > 1)
    duplicate_ids = sorted(unit_id for unit_id, count in Counter(unit_ids).items() if count > 1)
    duplicate_dbids = sorted(dbid for dbid, count in Counter(dbids).items() if count > 1)

    if duplicate_names:
        issues.append(f"Duplicate unit names: {', '.join(duplicate_names)}")
    if duplicate_ids:
        issues.append(f"Duplicate unit ids: {', '.join(duplicate_ids)}")
    if duplicate_dbids:
        issues.append(f"Duplicate unit DBIDs: {', '.join(duplicate_dbids)}")

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate protomods duplicate names and IDs.")
    args = parser.parse_args()
    issues = validate_protomods(args.repo_root.resolve())

    if issues:
        print("Proto validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Proto validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
