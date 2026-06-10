"""Validate stringmods.xml string table files for duplicate _locID values, malformed entries, and missing language nodes."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, find_children, find_first_child, get_attr_case_insensitive, local_name, repo_relative

STRINGS_ROOT = REPO_ROOT / "data" / "strings"


def iter_string_nodes(node: ET.Element) -> list[ET.Element]:
    """All <String>/<string> elements at or below ``node`` (case-insensitive)."""
    return [el for el in node.iter() if isinstance(el.tag, str) and local_name(el.tag) == "string"]


def iter_language_nodes(node: ET.Element) -> list[ET.Element]:
    """All <Language>/<language> elements at or below ``node`` (case-insensitive)."""
    return [el for el in node.iter() if isinstance(el.tag, str) and local_name(el.tag) == "language"]


def stringmods_repo_root(file_path: Path) -> Path:
    if file_path.name == "stringmods.xml" and len(file_path.parents) >= 4:
        return file_path.parents[3]
    return REPO_ROOT


def find_language_node(root) -> ET.Element | None:
    string_table = find_first_child(root, "stringtable")
    if string_table is None:
        return None
    return find_first_child(string_table, "language")


def validate_stringmods(file_path: Path) -> list[str]:
    issues: list[str] = []
    expected_language = file_path.parent.name.lower()
    report_root = stringmods_repo_root(file_path)

    try:
        root = ET.parse(file_path).getroot()
    except ET.ParseError as exc:
        return [f"{repo_relative(file_path, report_root)}: XML parse error: {exc}"]

    language_node = find_language_node(root)
    if language_node is None:
        return [f"{repo_relative(file_path, report_root)}: missing StringTable/Language node"]

    actual_language = get_attr_case_insensitive(language_node, "name").lower()
    if actual_language != expected_language:
        issues.append(
            f"{repo_relative(file_path, report_root)}: folder is '{expected_language}' but language name is '{actual_language or 'missing'}'"
        )

    locids: list[str] = []
    empty_locids = 0
    empty_strings: list[str] = []
    invalid_locids: list[str] = []

    for string_node in find_children(language_node, "string"):
        locid = get_attr_case_insensitive(string_node, "_locid").strip()
        text = (string_node.text or "").strip()

        if locid == "":
            empty_locids += 1
        else:
            locids.append(locid)
            if not locid.isdigit():
                invalid_locids.append(locid)

        if text == "":
            empty_strings.append(locid or "<missing locid>")

    duplicate_locids = sorted(locid for locid, count in Counter(locids).items() if count > 1)

    if empty_locids:
        issues.append(f"{repo_relative(file_path, report_root)}: {empty_locids} strings missing _locID")
    if invalid_locids:
        issues.append(f"{repo_relative(file_path, report_root)}: invalid _locID values: {', '.join(sorted(set(invalid_locids)))}")
    if duplicate_locids:
        issues.append(f"{repo_relative(file_path, report_root)}: duplicate _locID values: {', '.join(duplicate_locids)}")
    if empty_strings:
        issues.append(f"{repo_relative(file_path, report_root)}: empty string values for locids: {', '.join(empty_strings[:20])}")

    # Orphaned-string check: every <String> must live INSIDE a <Language> node.
    # Strings stranded between </Language> and </StringTable> are well-formed XML
    # but the engine never loads them, so their locids silently resolve to empty
    # (e.g. civ display names rendering as a blank nation title in the lobby).
    language_string_ids = set()
    for language in iter_language_nodes(root):
        for string_node in iter_string_nodes(language):
            language_string_ids.add(id(string_node))
    orphaned = [s for s in iter_string_nodes(root) if id(s) not in language_string_ids]
    if orphaned:
        orphan_locids = [get_attr_case_insensitive(s, "_locid").strip() or "<missing locid>" for s in orphaned]
        shown = ", ".join(orphan_locids[:20]) + ("…" if len(orphan_locids) > 20 else "")
        issues.append(
            f"{repo_relative(file_path, report_root)}: {len(orphaned)} <String> entries are outside any "
            f"<Language> scope (engine will not load them): {shown}"
        )

    return issues


def build_locid_map(repo_root: Path) -> tuple[dict[str, str], bool]:
    """Build a merged locid→text map from the base table (optional) and ANW stringmods.

    Returns (locid_map, base_table_loaded).
    """
    locid_map: dict[str, str] = {}

    # 1. Base table (optional)
    base_table_loaded = False
    base_table_path = repo_root / "artifacts" / "extracted_base_stringtable.xml"
    if base_table_path.exists():
        try:
            root = ET.parse(base_table_path).getroot()
            for string_node in iter_string_nodes(root):
                locid = get_attr_case_insensitive(string_node, "_locid").strip()
                text = (string_node.text or "").strip()
                if locid:
                    locid_map[locid] = text
            base_table_loaded = True
        except ET.ParseError:
            pass

    # 2. ANW stringmods (later wins)
    strings_root = repo_root / "data" / "strings"
    if strings_root.exists():
        for file_path in sorted(strings_root.rglob("stringmods.xml")):
            try:
                root = ET.parse(file_path).getroot()
                language_node = find_language_node(root)
                if language_node is None:
                    continue
                for string_node in find_children(language_node, "string"):
                    locid = get_attr_case_insensitive(string_node, "_locid").strip()
                    text = (string_node.text or "").strip()
                    if locid:
                        locid_map[locid] = text
            except ET.ParseError:
                pass

    return locid_map, base_table_loaded


def validate_civ_display_names(repo_root: Path = REPO_ROOT) -> list[str]:
    """Check that every civ with a <displaynameid> resolves to a non-empty string."""
    civmods_path = repo_root / "data" / "civmods.xml"
    if not civmods_path.exists():
        return []

    locid_map, base_table_loaded = build_locid_map(repo_root)

    try:
        root = ET.parse(civmods_path).getroot()
    except ET.ParseError as exc:
        return [f"{repo_relative(civmods_path, repo_root)}: XML parse error: {exc}"]

    issues: list[str] = []
    for civ in root.iter():
        if not (isinstance(civ.tag, str) and local_name(civ.tag) == "civ"):
            continue

        name_node = find_first_child(civ, "name")
        civ_name = (name_node.text or "").strip() if name_node is not None else "<unknown>"

        displaynameid_node = find_first_child(civ, "displaynameid")
        if displaynameid_node is None:
            # Base-game stub — intentionally no displaynameid; skip.
            continue

        locid = (displaynameid_node.text or "").strip()
        if not locid:
            continue

        if not locid.isdigit():
            issues.append(
                f"{repo_relative(civmods_path, repo_root)}: civ '{civ_name}' has non-numeric displaynameid '{locid}'"
            )
            continue

        # Determine whether to flag a missing resolution.
        if base_table_loaded:
            # Full map available — flag any unresolved id.
            if locid_map.get(locid, "") == "":
                issues.append(
                    f"{repo_relative(civmods_path, repo_root)}: civ '{civ_name}' displaynameid {locid} does not resolve to a non-empty string"
                )
        else:
            # No base table — only flag ANW-authored range to avoid false positives.
            if int(locid) >= 400000 and locid_map.get(locid, "") == "":
                issues.append(
                    f"{repo_relative(civmods_path, repo_root)}: civ '{civ_name}' displaynameid {locid} does not resolve to a non-empty string"
                )

    return sorted(issues)


def validate_stringtables(repo_root: Path = REPO_ROOT) -> list[str]:
    strings_root = repo_root / "data" / "strings"
    if not strings_root.exists():
        return [f"Strings folder not found: {repo_relative(strings_root, repo_root)}"]

    stringmods_files = sorted(strings_root.rglob("stringmods.xml"))
    if not stringmods_files:
        return ["No stringmods.xml files found under data/strings."]

    issues: list[str] = []
    for file_path in stringmods_files:
        issues.extend(validate_stringmods(file_path))
    issues.extend(validate_civ_display_names(repo_root))
    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate StringTable files.")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    issues = validate_stringtables(repo_root)
    stringmods_files = sorted((repo_root / "data" / "strings").rglob("stringmods.xml")) if (repo_root / "data" / "strings").exists() else []

    if issues:
        print("StringTable validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print(f"Validated {len(stringmods_files)} StringTable file(s) successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
