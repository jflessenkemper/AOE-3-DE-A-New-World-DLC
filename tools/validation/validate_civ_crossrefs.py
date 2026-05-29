from __future__ import annotations

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import (
    REPO_ROOT,
    build_repo_root_parser,
    child_elements,
    find_children,
    get_attr_case_insensitive,
    get_child_text,
    local_name,
)


TECH_TAGS = (
    "PostIndustrialTech",
    "PostImperialTech",
    "DeathMatchTech",
    "TreatyTech",
    "EmpireWarsTech",
)
DEFAULT_CIV_PREFIXES = ("ANW",)
DEFAULT_TECH_PREFIXES = ("ANW",)


def iter_civs(root: ET.Element):
    for civ in child_elements(root):
        if local_name(civ.tag) == "civ":
            yield civ


def iter_referenced_techs(civ: ET.Element):
    for age_tech in find_children(civ, "AgeTech"):
        tech_name = get_child_text(age_tech, "Tech")
        if tech_name:
            yield "AgeTech", tech_name

    for tag_name in TECH_TAGS:
        tech_name = get_child_text(civ, tag_name)
        if tech_name:
            yield tag_name, tech_name


def load_string_ids(strings_file: Path) -> set[str]:
    root = ET.parse(strings_file).getroot()
    string_ids: set[str] = set()

    for string_table in child_elements(root):
        if local_name(string_table.tag) != "stringtable":
            continue
        for language in child_elements(string_table):
            if local_name(language.tag) != "language":
                continue
            for string_node in child_elements(language):
                if local_name(string_node.tag) != "string":
                    continue
                locid = get_attr_case_insensitive(string_node, "_locid")
                if locid:
                    string_ids.add(locid)

    return string_ids


def load_techtree_names(techtree_file: Path) -> set[str]:
    root = ET.parse(techtree_file).getroot()
    tech_names: set[str] = set()
    for tech in child_elements(root):
        if local_name(tech.tag) != "tech":
            continue
        tech_name = get_attr_case_insensitive(tech, "name")
        if tech_name:
            tech_names.add(tech_name)
    return tech_names


def validate_civ_crossrefs(
    repo_root: Path = REPO_ROOT,
    civ_prefixes: tuple[str, ...] | None = DEFAULT_CIV_PREFIXES,
    tech_prefixes: tuple[str, ...] = DEFAULT_TECH_PREFIXES,
    language: str = "english",
    validate_display_name_ids: bool = False,
    allowed_missing_string_ids: set[str] | None = None,
) -> list[str]:
    data_root = repo_root / "data"
    civmods_path = data_root / "civmods.xml"
    strings_path = data_root / "strings" / language / "stringmods.xml"
    techtree_path = data_root / "techtreemods.xml"

    civmods_root = ET.parse(civmods_path).getroot()
    string_ids = load_string_ids(strings_path)
    techtree_names = load_techtree_names(techtree_path)
    allowed_missing_string_ids = allowed_missing_string_ids or set()
    issues: list[str] = []

    for civ in iter_civs(civmods_root):
        civ_name = get_child_text(civ, "Name")
        if not civ_name:
            continue
        if civ_prefixes and not any(civ_name.startswith(prefix) for prefix in civ_prefixes):
            continue

        rollover_locid = get_child_text(civ, "RolloverNameID")
        if rollover_locid and rollover_locid not in string_ids and rollover_locid not in allowed_missing_string_ids:
            issues.append(f"{civ_name}: RolloverNameID references missing string ID {rollover_locid}")

        if validate_display_name_ids:
            display_locid = get_child_text(civ, "DisplayNameID")
            if display_locid and display_locid not in string_ids and display_locid not in allowed_missing_string_ids:
                issues.append(f"{civ_name}: DisplayNameID references missing string ID {display_locid}")

        for tag_name, tech_name in iter_referenced_techs(civ):
            if tech_prefixes and not any(tech_name.startswith(prefix) for prefix in tech_prefixes):
                continue
            if tech_name not in techtree_names:
                issues.append(f"{civ_name}: {tag_name} references missing tech '{tech_name}'")

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate civ string and tech cross-references.")
    parser.add_argument(
        "--civ-prefix",
        action="append",
        default=[],
        help="Restrict validation to civ names starting with this prefix. Can be passed multiple times.",
    )
    parser.add_argument(
        "--all-civs",
        action="store_true",
        help="Validate all civs in civmods.xml.",
    )
    parser.add_argument(
        "--tech-prefix",
        action="append",
        default=[],
        help="Only require tech references with these prefixes to exist in techtreemods. Can be passed multiple times.",
    )
    parser.add_argument(
        "--language",
        default="english",
        help="Language folder used for DisplayNameID and RolloverNameID lookups.",
    )
    parser.add_argument(
        "--validate-display-name-ids",
        action="store_true",
        help="Require DisplayNameID locIDs to exist in the repo StringTables as well.",
    )
    parser.add_argument(
        "--allow-missing-string-id",
        action="append",
        default=[],
        help="String locID that is allowed to stay unresolved because it is expected to come from stock data. Can be passed multiple times.",
    )
    args = parser.parse_args()

    civ_prefixes = None if args.all_civs else tuple(args.civ_prefix or DEFAULT_CIV_PREFIXES)
    tech_prefixes = tuple(args.tech_prefix or DEFAULT_TECH_PREFIXES)
    issues = validate_civ_crossrefs(
        args.repo_root.resolve(),
        civ_prefixes,
        tech_prefixes,
        args.language,
        args.validate_display_name_ids,
        set(args.allow_missing_string_id),
    )

    if issues:
        print("Civ cross-reference validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Civ cross-reference validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
