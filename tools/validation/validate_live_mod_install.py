from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import filecmp
import sys
import tempfile

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT, build_repo_root_parser, repo_relative
from tools.validation.validate_packaged_mod import build_packaged_tree


LIVE_MOD_RELATIVE_PATH = Path(
    "Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World"
)

GAME_PAYLOAD_TOP_LEVEL = {
    "art",
    "data",
    "game",
    "modinfo.json",
    "RandMaps",
    "resources",
    "Scenario",
    "sound",
}

NON_RUNTIME_SUFFIXES = {
    ".md",
    ".txt",
    ".age3yrec",
}


@dataclass(frozen=True)
class LiveInstallValidationResult:
    live_root: Path
    issues: list[str]


def default_live_mod_root_candidates() -> list[Path]:
    user_name = Path.home().name
    candidates = [
        Path.home() / ".local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser" / LIVE_MOD_RELATIVE_PATH,
        Path(f"/var/home/{user_name}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser") / LIVE_MOD_RELATIVE_PATH,
    ]

    ordered: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser()
        if resolved in seen:
            continue
        ordered.append(resolved)
        seen.add(resolved)
    return ordered


def resolve_live_mod_root(explicit_root: Path | None = None) -> Path:
    if explicit_root is not None:
        return explicit_root.expanduser()

    candidates = default_live_mod_root_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def list_relative_files(root: Path) -> set[str]:
    relative_files: set[str] = set()
    for path in root.rglob("*"):
        if path.is_file() is False:
            continue
        relative_path = path.relative_to(root).as_posix()
        top_level_name = relative_path.split("/", 1)[0]
        if top_level_name not in GAME_PAYLOAD_TOP_LEVEL:
            continue
        if path.suffix.lower() in NON_RUNTIME_SUFFIXES:
            continue
        relative_files.add(relative_path)
    return relative_files


def validate_live_mod_install(repo_root: Path = REPO_ROOT, live_root: Path | None = None) -> LiveInstallValidationResult:
    resolved_live_root = resolve_live_mod_root(live_root)
    if resolved_live_root.exists() is False:
        return LiveInstallValidationResult(
            live_root=resolved_live_root,
            issues=[f"Live mod install not found: {resolved_live_root}"],
        )

    with tempfile.TemporaryDirectory(prefix="aoe3-live-install-compare-") as temp_dir:
        packaged_root = Path(temp_dir) / repo_root.name
        packaged_root.mkdir(parents=True, exist_ok=True)
        build_packaged_tree(repo_root, packaged_root)

        packaged_files = list_relative_files(packaged_root)
        live_files = list_relative_files(resolved_live_root)

        issues: list[str] = []

        for relative_path in sorted(packaged_files - live_files):
            issues.append(f"Live install missing file: {relative_path}")

        for relative_path in sorted(live_files - packaged_files):
            issues.append(f"Live install has unexpected file: {relative_path}")

        for relative_path in sorted(packaged_files & live_files):
            packaged_file = packaged_root / relative_path
            live_file = resolved_live_root / relative_path
            if filecmp.cmp(packaged_file, live_file, shallow=False) is False:
                issues.append(f"Live install content mismatch: {relative_path}")

        return LiveInstallValidationResult(live_root=resolved_live_root, issues=issues)


def main() -> int:
    parser = build_repo_root_parser("Validate that the active live mod install matches the packaged repo payload.")
    parser.add_argument(
        "--live-root",
        type=Path,
        help="Explicit live mod root. Defaults to the first existing Proton local-mod path candidate.",
    )
    args = parser.parse_args()

    result = validate_live_mod_install(repo_root=args.repo_root.resolve(), live_root=args.live_root)
    if result.issues:
        print(f"Live install validation failed for {repo_relative(result.live_root, args.repo_root.resolve())}:")
        for issue in result.issues:
            print(f" - {issue}")
        return 1

    print(f"Live install validation passed for {result.live_root}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())