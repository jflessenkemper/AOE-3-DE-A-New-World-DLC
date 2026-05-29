from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import tempfile

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser
from tools.validation.validate_civ_crossrefs import validate_civ_crossrefs
from tools.validation.validate_civ_homecities import validate_civ_homecities
from tools.validation.validate_homecity_cards import validate_homecity_cards
from tools.validation.validate_civmods_ui import validate_civmods_ui
from tools.validation.validate_protomods import validate_protomods
from tools.validation.validate_stringtables import validate_stringtables
from tools.validation.validate_techtree import validate_techtree
from tools.validation.validate_xml_well_formed import validate_xml_well_formed
from tools.validation.validate_xs_scripts import validate_xs_scripts


DEV_ONLY_TOP_LEVEL = {
    ".git",
    ".github",
    ".venv",
    "age-of-pirates",
    "age-of-pirates-main",
    "artifacts",
    "docs",
    "logs",
    "reference-mods",
    "tests",
    "tools",
}

# Allow-list of top-level entries that legitimately ship in a release. Anything
# else at repo root (dev docs, validation reports, session notes, run scripts,
# state JSON, top-level HTML reference, recorded replays, etc.) is filtered
# out of the packaged tree even if it's not in DEV_ONLY_TOP_LEVEL.
RELEASE_TOP_LEVEL = {
    "art",
    "data",
    "game",
    "modinfo.json",
    "mod.xml",
    "RandMaps",
    "resources",
    "Scenario",
    "sound",
    "thumbnail.jpg",
}


@dataclass
class PackageValidationResult:
    packaged_root: Path
    included_entries: list[str]
    issues: list[str]


def format_packaged_mod_report(result: PackageValidationResult) -> str:
    lines = ["Packaged mod validation report", f"Packaged root: {result.packaged_root}", ""]
    lines.append(f"Included top-level entries: {', '.join(result.included_entries)}")
    lines.append("")
    if result.issues:
        lines.append(f"Summary: FAIL ({len(result.issues)} issue(s))")
        lines.append("")
        for issue in result.issues:
            lines.append(f" - {issue}")
    else:
        lines.append("Summary: PASS")
    return "\n".join(lines).rstrip() + "\n"


def should_exclude_top_level(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if path.name in DEV_ONLY_TOP_LEVEL:
        return True
    # Allow-list mode: anything not on the release manifest is dev cruft.
    if path.name not in RELEASE_TOP_LEVEL:
        return True
    return False


def build_packaged_tree(repo_root: Path, packaged_root: Path) -> list[str]:
    included_entries: list[str] = []

    for child in sorted(repo_root.iterdir(), key=lambda path: path.name.lower()):
        if should_exclude_top_level(child):
            continue

        destination = packaged_root / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)
        included_entries.append(child.name)

    return included_entries


def validate_packaged_mod(repo_root: Path = REPO_ROOT) -> PackageValidationResult:
    return validate_packaged_mod_with_options(repo_root)


def validate_packaged_mod_with_options(
    repo_root: Path = REPO_ROOT,
    validate_display_name_ids: bool = False,
) -> PackageValidationResult:
    with tempfile.TemporaryDirectory(prefix="aoe3-packaged-mod-") as temp_dir:
        packaged_root = Path(temp_dir) / repo_root.name
        packaged_root.mkdir(parents=True, exist_ok=True)
        included_entries = build_packaged_tree(repo_root, packaged_root)

        issues: list[str] = []
        for dev_only_name in sorted(DEV_ONLY_TOP_LEVEL):
            if (packaged_root / dev_only_name).exists():
                issues.append(f"Packaged output should exclude top-level path: {dev_only_name}")

        issues.extend(validate_civ_homecities(packaged_root))
        issues.extend(validate_civmods_ui(packaged_root))
        issues.extend(validate_civ_crossrefs(packaged_root, validate_display_name_ids=validate_display_name_ids))
        issues.extend(validate_homecity_cards(packaged_root))
        issues.extend(validate_protomods(packaged_root))
        issues.extend(validate_stringtables(packaged_root))
        issues.extend(validate_techtree(packaged_root))
        issues.extend(validate_xml_well_formed(packaged_root))
        issues.extend(validate_xs_scripts(packaged_root))

        return PackageValidationResult(packaged_root=packaged_root, included_entries=included_entries, issues=issues)


def main() -> int:
    parser = build_repo_root_parser("Build a clean packaged mod tree and validate it.")
    parser.add_argument(
        "--report-file",
        type=Path,
        help="Optional path to write the packaged validation report to.",
    )
    parser.add_argument(
        "--validate-display-name-ids",
        action="store_true",
        help="Require DisplayNameID locIDs to resolve from repo StringTables inside the packaged tree.",
    )
    args = parser.parse_args()
    result = validate_packaged_mod_with_options(
        args.repo_root.resolve(),
        validate_display_name_ids=args.validate_display_name_ids,
    )
    report = format_packaged_mod_report(result)
    print(report, end="")

    if args.report_file is not None:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(report, encoding="utf-8")

    if result.issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())