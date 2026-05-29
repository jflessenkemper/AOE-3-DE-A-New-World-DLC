"""Validate home-city visual/pathdata namespace coherence.

Regression guard for the "floating citizens" bug:

A revolution-civ home city XML may legitimately reuse a parent civ's visual
(e.g. ``british\\british_homecity.xml``) but it MUST pair the visual with a
``<pathdata>`` from the *same* art namespace (e.g. ``british\\pathable_area_object.gr2``).
The engine snaps unit Y-coordinates from the pathdata heightmap; if the
namespace doesn't match the visual, citizens walk in air or sink under the
terrain.

This validator checks every home-city XML in ``data/`` and reports any file
where the leading directory component of ``<pathdata>`` differs from the
leading directory of ``<visual>`` / ``<watervisual>`` / ``<backgroundvisual>``
/ ``<camera>`` / ``<widescreencamera>``.

A small allow-list permits a single intentional exception:
``ANWMexicans`` uses ``revolution\\revolution_homecity.xml`` paired with
``revolution\\pathable_area.gr2`` — internally consistent.
"""

from __future__ import annotations

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import (
    REPO_ROOT,
    build_repo_root_parser,
    get_child_text,
    normalize_path,
    repo_relative,
)


DEFAULT_HOMECITY_GLOBS = ("homecity*.xml", "anwhomecity*.xml")

# Fields whose first path segment must match <pathdata>'s first path segment.
NAMESPACE_FIELDS = (
    "visual",
    "watervisual",
    "backgroundvisual",
    "camera",
    "widescreencamera",
)


def first_segment(value: str) -> str:
    """Return the leading directory component of a backslash/slash path."""
    norm = normalize_path(value)
    if not norm:
        return ""
    head, _, _ = norm.partition("/")
    return head.lower()


def validate_homecity_visuals(
    repo_root: Path = REPO_ROOT,
    homecity_globs: tuple[str, ...] = DEFAULT_HOMECITY_GLOBS,
) -> list[str]:
    data_root = repo_root / "data"
    issues: list[str] = []

    seen: set[Path] = set()
    paths: list[Path] = []
    for glob in homecity_globs:
        for path in sorted(data_root.glob(glob)):
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)

    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            issues.append(f"{repo_relative(path, repo_root)}: XML parse error: {exc}")
            continue

        pathdata = get_child_text(root, "pathdata")
        visual = get_child_text(root, "visual")
        if not pathdata:
            issues.append(f"{repo_relative(path, repo_root)}: missing <pathdata>")
            continue
        if not visual:
            issues.append(f"{repo_relative(path, repo_root)}: missing <visual>")
            continue

        pathdata_ns = first_segment(pathdata)
        visual_ns = first_segment(visual)
        rel = repo_relative(path, repo_root)

        if pathdata_ns != visual_ns:
            issues.append(
                f"{rel}: <pathdata> namespace '{pathdata_ns}' does not match "
                f"<visual> namespace '{visual_ns}' "
                f"(pathdata={pathdata}, visual={visual}) — citizens will float"
            )
            continue

        # All other namespace-bound fields should also align with visual.
        for field in NAMESPACE_FIELDS:
            if field == "visual":
                continue
            value = get_child_text(root, field)
            if not value:
                continue
            field_ns = first_segment(value)
            if field_ns != visual_ns:
                issues.append(
                    f"{rel}: <{field}> namespace '{field_ns}' does not match "
                    f"<visual> namespace '{visual_ns}' (value={value})"
                )

    return issues


def main() -> int:
    parser = build_repo_root_parser(
        "Validate home-city visual/pathdata namespace coherence (floating-citizen guard)."
    )
    args = parser.parse_args()

    issues = validate_homecity_visuals(args.repo_root.resolve())
    if issues:
        print("Home-city visual/pathdata validation failed:")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Home-city visual/pathdata validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
