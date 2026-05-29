from __future__ import annotations

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, child_elements, get_child_text, iter_repo_resource_paths, local_name

REQUIRED_FLAG_FIELDS = (
    "HomeCityFlagButtonSet",
    "HomeCityFlagButtonSetLarge",
    "PostgameFlagTexture",
    "PostgameFlagIconWPF",
    "HomeCityFlagIconWPF",
    "HomeCityFlagButtonWPF",
)


def get_matchmaking_portrait_wpf(civ: ET.Element) -> str:
    for child in child_elements(civ):
        if local_name(child.tag) != "matchmakingtextures":
            continue
        return get_child_text(child, "SmallPortraitTextureWPF")
    return ""


def iter_target_civs(root: ET.Element, name_prefixes: tuple[str, ...] | None):
    for civ in child_elements(root):
        if local_name(civ.tag) != "civ":
            continue
        name = get_child_text(civ, "Name")
        if not name:
            continue
        if name_prefixes and not any(name.startswith(prefix) for prefix in name_prefixes):
            continue
        yield civ


def validate_civmods_ui(repo_root: Path = REPO_ROOT, name_prefixes: tuple[str, ...] | None = ("ANW",)) -> list[str]:
    civmods_path = repo_root / "data" / "civmods.xml"
    root = ET.parse(civmods_path).getroot()
    errors: list[str] = []

    for civ in iter_target_civs(root, name_prefixes):
        name = get_child_text(civ, "Name")
        if not get_child_text(civ, "HomeCityFlagTexture"):
            continue

        missing_fields = [field for field in REQUIRED_FLAG_FIELDS if not get_child_text(civ, field)]
        if missing_fields:
            errors.append(f"{name}: missing required civ UI fields: {', '.join(missing_fields)}")

        if not get_child_text(civ, "HomeCityPreviewWPF"):
            errors.append(f"{name}: missing required civ portrait field: HomeCityPreviewWPF")

        if not get_matchmaking_portrait_wpf(civ):
            errors.append(f"{name}: missing required civ portrait field: MatchmakingTextures/SmallPortraitTextureWPF")

        for tag_name, relative_path in iter_repo_resource_paths(civ):
            file_path = repo_root / relative_path
            if not file_path.is_file():
                errors.append(f"{name}: {tag_name} references missing file {relative_path}")

    return errors


def main() -> int:
    parser = build_repo_root_parser("Validate civ UI fields and repo-owned WPF references.")
    parser.add_argument(
        "--name-prefix",
        action="append",
        default=[],
        help="Restrict validation to civ names starting with this prefix. Can be passed multiple times.",
    )
    parser.add_argument(
        "--all-civs",
        action="store_true",
        help="Validate all civs in civmods.xml rather than only prefix-matched custom civs.",
    )
    args = parser.parse_args()

    prefixes = None if args.all_civs else tuple(args.name_prefix or ["ANW"])
    errors = validate_civmods_ui(args.repo_root.resolve(), prefixes)

    if errors:
        print(f"Found {len(errors)} civ UI validation issue(s):")
        for error in errors:
            print(f" - {error}")
        return 1

    print("All custom civ UI fields and WPF asset references are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())