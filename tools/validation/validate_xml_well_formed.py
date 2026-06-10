"""Verify every XML, tactics, material, and dmg file in the repo parses as well-formed XML."""
from __future__ import annotations

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, repo_relative

XML_SUFFIXES = {".xml", ".tactics", ".material", ".dmg"}
IGNORED_DIRS = {".git", ".venv", "node_modules"}


def iter_candidate_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in XML_SUFFIXES:
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        yield path


def validate_xml_well_formed(repo_root: Path = REPO_ROOT) -> list[str]:
    malformed = []
    for file_path in iter_candidate_files(repo_root):
        try:
            ET.parse(file_path)
        except ET.ParseError as exc:
            malformed.append(f"{repo_relative(file_path, repo_root)}: {exc}")

    return malformed


def main() -> int:
    parser = build_repo_root_parser("Validate XML-like files are well-formed.")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    malformed = validate_xml_well_formed(repo_root)

    if malformed:
        print(f"Found {len(malformed)} malformed XML-like files:")
        for entry in malformed:
            print(f" - {entry}")
        return 1

    print("All XML-like files are well-formed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
