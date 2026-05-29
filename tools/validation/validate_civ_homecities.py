from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, child_elements, get_child_text, local_name, repo_relative


DEFAULT_HOMECITY_GLOB = "anwhomecity*.xml"
DEFAULT_NAME_PREFIXES = ("ANW",)


def iter_target_civs(root: ET.Element, name_prefixes: tuple[str, ...] | None):
    for civ in child_elements(root):
        if local_name(civ.tag) != "civ":
            continue
        name = get_child_text(civ, "Name")
        if not name:
            continue
        if name_prefixes and not any(name.startswith(prefix) for prefix in name_prefixes):
            continue
        if get_child_text(civ, "HomeCityFilename"):
            yield civ


def validate_civ_homecities(
    repo_root: Path = REPO_ROOT,
    name_prefixes: tuple[str, ...] | None = DEFAULT_NAME_PREFIXES,
    homecity_glob: str = DEFAULT_HOMECITY_GLOB,
    allow_missing_homecity_files: bool = False,
) -> list[str]:
    data_root = repo_root / "data"
    civmods_path = data_root / "civmods.xml"
    issues: list[str] = []

    try:
        civmods_root = ET.parse(civmods_path).getroot()
    except ET.ParseError as exc:
        return [f"{repo_relative(civmods_path, repo_root)}: XML parse error: {exc}"]

    referenced_homecities: list[str] = []

    for civ in iter_target_civs(civmods_root, name_prefixes):
        civ_name = get_child_text(civ, "Name")
        homecity_filename = get_child_text(civ, "HomeCityFilename")

        if not homecity_filename:
            issues.append(f"{civ_name}: missing HomeCityFilename")
            continue

        referenced_homecities.append(homecity_filename)
        homecity_path = data_root / homecity_filename
        if not homecity_path.is_file():
            if allow_missing_homecity_files:
                continue
            issues.append(f"{civ_name}: HomeCityFilename references missing file data/{homecity_filename}")
            continue

        try:
            homecity_root = ET.parse(homecity_path).getroot()
        except ET.ParseError as exc:
            issues.append(f"{repo_relative(homecity_path, repo_root)}: XML parse error: {exc}")
            continue

        homecity_civ = get_child_text(homecity_root, "civ")
        if not homecity_civ:
            issues.append(f"{repo_relative(homecity_path, repo_root)}: missing <civ> binding")
        elif homecity_civ != civ_name:
            issues.append(
                f"{civ_name}: {repo_relative(homecity_path, repo_root)} binds to '{homecity_civ}' instead"
            )

    duplicate_homecities = sorted(name for name, count in Counter(referenced_homecities).items() if count > 1)
    for homecity_filename in duplicate_homecities:
        issues.append(f"HomeCityFilename referenced by multiple civs: data/{homecity_filename}")

    referenced_set = set(referenced_homecities)
    for homecity_path in sorted(data_root.glob(homecity_glob)):
        if homecity_path.name not in referenced_set:
            issues.append(f"Orphan custom home city file not referenced by civmods: {repo_relative(homecity_path, repo_root)}")

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate civ to home-city linkage.")
    parser.add_argument(
        "--name-prefix",
        action="append",
        default=[],
        help="Restrict validation to civ names starting with this prefix. Can be passed multiple times.",
    )
    parser.add_argument(
        "--all-civs",
        action="store_true",
        help="Validate all civs that declare HomeCityFilename, regardless of name prefix.",
    )
    parser.add_argument(
        "--homecity-glob",
        default=DEFAULT_HOMECITY_GLOB,
        help="Glob for repo-owned homecity XML files used by orphan checks.",
    )
    parser.add_argument(
        "--allow-missing-homecity-files",
        action="store_true",
        help="Do not fail when a HomeCityFilename points at a stock-game file that is not present in the repo.",
    )
    args = parser.parse_args()

    prefixes = None if args.all_civs else tuple(args.name_prefix or DEFAULT_NAME_PREFIXES)
    issues = validate_civ_homecities(
        repo_root=args.repo_root.resolve(),
        name_prefixes=prefixes,
        homecity_glob=args.homecity_glob,
        allow_missing_homecity_files=args.allow_missing_homecity_files,
    )
    if issues:
        print("Civ/HomeCity validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Civ/HomeCity validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
