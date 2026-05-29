"""Validate ``data/playercolors.xml`` against ``data/civmods.xml``.

Each ``<Color>`` row in ``playercolors.xml`` declares ``civ``, ``leader`` and
RGB attributes. This validator enforces:

- Every ``<Color>`` row is well-formed: civ + leader + r/g/b in [0, 255].
- ``civ`` values are unique (no two leaders mapped to the same civ).
- ``leader`` values are unique (a leader can't lead two civs).
- Every revolution civ that appears in ``civmods.xml`` has a colour entry.
- ``civmods.xml`` ``<Name>`` values that have a colour entry resolve.

The colour file is the mod-owned source of truth for civ→leader→RGB mapping.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import (
    REPO_ROOT,
    build_repo_root_parser,
    child_elements,
    get_attr_case_insensitive,
    get_child_text,
    local_name,
    repo_relative,
)


def load_civmods_names(civmods_path: Path) -> set[str]:
    """Return only PLAYABLE civmods entries — those with main=1.

    Civmods may include suppression entries with ``<main>0</main>`` to
    hide base-game civs from pickers; those don't need playercolor
    bindings (they aren't selectable).
    """
    root = ET.parse(civmods_path).getroot()
    names: set[str] = set()
    for civ in child_elements(root):
        if local_name(civ.tag) != "civ":
            continue
        # Skip suppression entries (main != 1)
        main_text = (get_child_text(civ, "Main") or "").strip()
        if main_text and main_text != "1":
            continue
        name = get_child_text(civ, "Name")
        if name:
            names.add(name)
    return names


def _parse_channel(value: str) -> int | None:
    try:
        i = int(value)
    except (TypeError, ValueError):
        return None
    if 0 <= i <= 255:
        return i
    return None


def validate_playercolors(repo_root: Path = REPO_ROOT) -> list[str]:
    data_root = repo_root / "data"
    colors_path = data_root / "playercolors.xml"
    civmods_path = data_root / "civmods.xml"
    issues: list[str] = []

    if not colors_path.is_file():
        return [f"{repo_relative(colors_path, repo_root)}: file not found"]

    try:
        colors_root = ET.parse(colors_path).getroot()
    except ET.ParseError as exc:
        return [f"{repo_relative(colors_path, repo_root)}: XML parse error: {exc}"]

    civs_with_color: list[str] = []
    leaders_seen: list[str] = []

    for entry in child_elements(colors_root):
        if local_name(entry.tag) != "color":
            continue
        civ = get_attr_case_insensitive(entry, "civ")
        leader = get_attr_case_insensitive(entry, "leader")

        if not civ:
            issues.append(f"{repo_relative(colors_path, repo_root)}: <Color> missing civ attribute")
            continue
        if not leader:
            issues.append(f"playercolors[{civ}]: missing leader attribute")
        else:
            leaders_seen.append(leader)

        civs_with_color.append(civ)

        for channel in ("r", "g", "b"):
            raw = get_attr_case_insensitive(entry, channel)
            if not raw:
                issues.append(f"playercolors[{civ}]: missing {channel} channel")
                continue
            if _parse_channel(raw) is None:
                issues.append(
                    f"playercolors[{civ}]: invalid {channel} channel '{raw}' (must be int 0..255)"
                )

    duplicate_civs = sorted(name for name, count in Counter(civs_with_color).items() if count > 1)
    for name in duplicate_civs:
        issues.append(f"playercolors: duplicate civ entry '{name}'")

    duplicate_leaders = sorted(name for name, count in Counter(leaders_seen).items() if count > 1)
    for name in duplicate_leaders:
        issues.append(f"playercolors: duplicate leader entry '{name}'")

    # Cross-reference against civmods.xml: every revolution civ declared there
    # must have a colour binding.
    if civmods_path.is_file():
        try:
            civmods_names = load_civmods_names(civmods_path)
        except ET.ParseError as exc:
            issues.append(f"{repo_relative(civmods_path, repo_root)}: XML parse error: {exc}")
        else:
            color_civs = set(civs_with_color)
            for name in sorted(civmods_names):
                if name not in color_civs:
                    issues.append(f"playercolors: missing color entry for civmods civ '{name}'")

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate playercolors.xml against civmods.xml.")
    args = parser.parse_args()

    issues = validate_playercolors(args.repo_root.resolve())
    if issues:
        print("Player-colors validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Player-colors validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
