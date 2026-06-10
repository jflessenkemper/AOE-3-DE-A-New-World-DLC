"""Check data/techtreemods.xml for duplicate tech names and dbid values that would cause silent engine overrides."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, child_elements, get_attr_case_insensitive, get_child_text, local_name, repo_relative


def validate_techtree(repo_root: Path = REPO_ROOT) -> list[str]:
    techtree_file = repo_root / "data" / "techtreemods.xml"

    try:
        root = ET.parse(techtree_file).getroot()
    except ET.ParseError as exc:
        return [f"Failed to parse {repo_relative(techtree_file, repo_root)}: {exc}"]

    tech_names: list[str] = []
    dbids: list[str] = []

    for tech in child_elements(root):
        if local_name(tech.tag) != "tech":
            continue

        tech_name = get_attr_case_insensitive(tech, "name")
        dbid = get_child_text(tech, "dbid")

        if tech_name:
            tech_names.append(tech_name.lower())
        if dbid:
            dbids.append(dbid)

    issues: list[str] = []

    duplicate_names = sorted(name for name, count in Counter(tech_names).items() if count > 1)
    duplicate_dbids = sorted(dbid for dbid, count in Counter(dbids).items() if count > 1)

    if duplicate_names:
        issues.append(f"Duplicate tech names: {', '.join(duplicate_names)}")
    if duplicate_dbids:
        issues.append(f"Duplicate tech DBIDs: {', '.join(duplicate_dbids)}")

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate techtree duplicate names and IDs.")
    args = parser.parse_args()
    issues = validate_techtree(args.repo_root.resolve())

    if issues:
        print("TechTree validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("TechTree validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
