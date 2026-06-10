"""Check ANW home city XML files for duplicate card names, missing tech references, and broken prerequisite chains."""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, child_elements, get_attr_case_insensitive, get_child_text, local_name, repo_relative


DEFAULT_HOMECITY_GLOB = "anwhomecity*.xml"
DEFAULT_TECH_PREFIXES = ("ANW", "HCREV", "DEHCREV")


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


def iter_cards(homecity_root: ET.Element):
    cards_node = None
    for child in child_elements(homecity_root):
        if local_name(child.tag) == "cards":
            cards_node = child
            break
    if cards_node is None:
        return
    for card in child_elements(cards_node):
        if local_name(card.tag) == "card":
            yield card


def validate_homecity_cards(
    repo_root: Path = REPO_ROOT,
    homecity_glob: str = DEFAULT_HOMECITY_GLOB,
    tech_prefixes: tuple[str, ...] = DEFAULT_TECH_PREFIXES,
) -> list[str]:
    data_root = repo_root / "data"
    techtree_names = load_techtree_names(data_root / "techtreemods.xml")
    issues: list[str] = []

    for homecity_path in sorted(data_root.glob(homecity_glob)):
        homecity_root = ET.parse(homecity_path).getroot()
        card_names: list[str] = []
        prereqs: list[tuple[str, str]] = []

        for card in iter_cards(homecity_root):
            card_name = get_child_text(card, "name")
            if not card_name:
                issues.append(f"{repo_relative(homecity_path, repo_root)}: card entry missing <name>")
                continue
            card_names.append(card_name)
            prereq = get_child_text(card, "prereqtech")
            if prereq and prereq != "-1":
                prereqs.append((card_name, prereq))

        duplicate_names = sorted(name for name, count in Counter(card_names).items() if count > 1)
        for duplicate_name in duplicate_names:
            issues.append(f"{repo_relative(homecity_path, repo_root)}: duplicate card name '{duplicate_name}'")

        card_name_set = set(card_names)
        lower_name_map = {name.lower(): name for name in card_names}
        dependents: dict[str, list[str]] = defaultdict(list)
        rooted_cards: set[str] = set()

        for card_name, prereq in prereqs:
            if prereq in card_name_set:
                dependents[prereq].append(card_name)
                continue
            normalized_prereq = prereq.lower()
            if normalized_prereq in lower_name_map:
                issues.append(
                    f"{repo_relative(homecity_path, repo_root)}: card '{card_name}' has case-mismatched prereqtech '{prereq}' (did you mean '{lower_name_map[normalized_prereq]}')"
                )
                rooted_cards.add(card_name)
                continue

            rooted_cards.add(card_name)
            if any(prereq.startswith(prefix) for prefix in tech_prefixes) and prereq not in techtree_names:
                issues.append(
                    f"{repo_relative(homecity_path, repo_root)}: card '{card_name}' references missing custom prereqtech '{prereq}'"
                )

        for card_name in card_names:
            if card_name not in {name for name, _ in prereqs}:
                rooted_cards.add(card_name)

        reachable_cards = set(rooted_cards)
        queue = deque(rooted_cards)
        while queue:
            current = queue.popleft()
            for dependent in dependents.get(current, []):
                if dependent in reachable_cards:
                    continue
                reachable_cards.add(dependent)
                queue.append(dependent)

        unreachable_cards = sorted(card_name for card_name in card_name_set if card_name not in reachable_cards)
        if unreachable_cards:
            issues.append(
                f"{repo_relative(homecity_path, repo_root)}: unreachable same-file prereq chain involving cards: {', '.join(unreachable_cards)}"
            )

    return issues


def main() -> int:
    parser = build_repo_root_parser("Validate homecity card links and custom tech references.")
    parser.add_argument(
        "--homecity-glob",
        default=DEFAULT_HOMECITY_GLOB,
        help="Glob used to find repo-owned homecity XML files.",
    )
    parser.add_argument(
        "--tech-prefix",
        action="append",
        default=[],
        help="Custom tech/card prefixes that must resolve in techtreemods.xml. Can be passed multiple times.",
    )
    args = parser.parse_args()

    issues = validate_homecity_cards(
        args.repo_root.resolve(),
        homecity_glob=args.homecity_glob,
        tech_prefixes=tuple(args.tech_prefix or DEFAULT_TECH_PREFIXES),
    )

    if issues:
        print("Homecity card validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Homecity card validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
