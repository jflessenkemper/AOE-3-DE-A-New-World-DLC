#!/usr/bin/env python3

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.validation.common import REPO_ROOT
from tools.validation.validate_live_mod_install import GAME_PAYLOAD_TOP_LEVEL, NON_RUNTIME_SUFFIXES, resolve_live_mod_root, validate_live_mod_install
from tools.validation.validate_packaged_mod import build_packaged_tree


APP_ID = 933110
PROFILE_RELATIVE_PATH = Path("Games/Age of Empires 3 DE/76561198170207043")
DEFAULT_FLOW = REPO_ROOT / "tools" / "aoe3_automation" / "flows" / "launch_and_capture_menu.json"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "tools" / "aoe3_automation" / "artifacts" / "sandbox_runs"
# 2026-05-11: was "Legendary Leaders Test" — that custom randmap was retired
# in favor of the ANEWWORLD scenario (Scenario/ANEWWORLD.age3Yscn). Default
# is now None so the sandbox uses whatever the user picks at the lobby; pass
# --random-map <BaseName> only when a specific randmap needs publishing.
DEFAULT_RANDOM_MAP: str | None = None


@dataclass(frozen=True)
class SandboxPlan:
    live_mod_root: Path
    profile_root: Path
    artifacts_dir: Path
    flow_path: Path
    random_map_name: str | None
    scenario_name: str | None


def default_profile_root_candidates() -> list[Path]:
    user_name = Path.home().name
    candidates = [
        Path.home() / ".local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser" / PROFILE_RELATIVE_PATH,
        Path(f"/var/home/{user_name}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser") / PROFILE_RELATIVE_PATH,
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


def resolve_profile_root(explicit_root: Path | None = None, live_mod_root: Path | None = None) -> Path:
    if explicit_root is not None:
        return explicit_root.expanduser()

    if live_mod_root is not None and len(live_mod_root.parents) >= 3:
        candidate = live_mod_root.parents[2]
        if candidate.exists():
            return candidate

    candidates = default_profile_root_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def ensure_parent(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def replace_path(source: Path, destination: Path, dry_run: bool, actions: list[str]) -> None:
    actions.append(f"sync {source} -> {destination}")
    if dry_run:
        return

    if source.is_dir():
        if destination.exists() and destination.is_file():
            destination.unlink()
        destination.mkdir(parents=True, exist_ok=True)
        sync_directory(source, destination, prune=True, dry_run=False, actions=actions)
        return

    ensure_parent(destination, dry_run=False)
    if destination.exists() and destination.is_dir():
        shutil.rmtree(destination)
    shutil.copy2(source, destination)


def sync_directory(source_root: Path, destination_root: Path, prune: bool, dry_run: bool, actions: list[str]) -> None:
    if source_root.exists() is False:
        raise FileNotFoundError(f"Source path not found: {source_root}")

    actions.append(f"ensure directory {destination_root}")
    if dry_run is False:
        destination_root.mkdir(parents=True, exist_ok=True)

    source_children = {child.name: child for child in source_root.iterdir()}

    if prune and destination_root.exists():
        for destination_child in destination_root.iterdir():
            if destination_child.name in source_children:
                continue
            actions.append(f"remove stale {destination_child}")
            if dry_run:
                continue
            if destination_child.is_dir():
                shutil.rmtree(destination_child)
            else:
                destination_child.unlink()

    for child_name, source_child in sorted(source_children.items()):
        destination_child = destination_root / child_name
        if source_child.is_dir():
            if destination_child.exists() and destination_child.is_file():
                actions.append(f"replace file with directory {destination_child}")
                if dry_run is False:
                    destination_child.unlink()
            sync_directory(source_child, destination_child, prune=True, dry_run=dry_run, actions=actions)
            continue

        if destination_child.exists() and destination_child.is_dir():
            actions.append(f"replace directory with file {destination_child}")
            if dry_run is False:
                shutil.rmtree(destination_child)

        if destination_child.exists() and filecmp.cmp(source_child, destination_child, shallow=False):
            continue

        actions.append(f"copy {source_child} -> {destination_child}")
        if dry_run:
            continue
        ensure_parent(destination_child, dry_run=False)
        shutil.copy2(source_child, destination_child)


def publish_random_map(repo_root: Path, profile_root: Path, map_name: str, dry_run: bool, actions: list[str]) -> None:
    source_dir = repo_root / "RandMaps"
    destination_dir = profile_root / "RandMaps"
    published_any = False
    for extension in (".xs", ".xml"):
        source_path = source_dir / f"{map_name}{extension}"
        if source_path.exists() is False:
            continue
        replace_path(source_path, destination_dir / source_path.name, dry_run=dry_run, actions=actions)
        published_any = True

    if published_any is False:
        raise FileNotFoundError(f"Random map not found in repo: {map_name}")


def publish_scenario(repo_root: Path, profile_root: Path, scenario_name: str, dry_run: bool, actions: list[str]) -> None:
    source_path = repo_root / "Scenario" / f"{scenario_name}.age3Yscn"
    if source_path.exists() is False:
        raise FileNotFoundError(f"Scenario not found in repo: {scenario_name}")
    replace_path(source_path, profile_root / "Scenario" / source_path.name, dry_run=dry_run, actions=actions)


def build_runtime_payload(repo_root: Path) -> tuple[Path, tempfile.TemporaryDirectory[str], list[str]]:
    temp_dir = tempfile.TemporaryDirectory(prefix="aoe3-sandbox-packaged-")
    packaged_root = Path(temp_dir.name) / repo_root.name
    packaged_root.mkdir(parents=True, exist_ok=True)
    included_entries = build_packaged_tree(repo_root, packaged_root)
    return packaged_root, temp_dir, included_entries


def build_live_runtime_subset(packaged_root: Path, temp_dir_name: str) -> Path:
    subset_root = Path(temp_dir_name) / "runtime_payload"
    subset_root.mkdir(parents=True, exist_ok=True)

    for top_level_name in sorted(GAME_PAYLOAD_TOP_LEVEL):
        source_path = packaged_root / top_level_name
        if source_path.exists() is False:
            continue

        destination_path = subset_root / top_level_name
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            for nested_path in sorted(source_path.rglob("*")):
                relative_path = nested_path.relative_to(source_path)
                filtered_destination = destination_path / relative_path
                if nested_path.is_dir():
                    filtered_destination.mkdir(parents=True, exist_ok=True)
                    continue
                if nested_path.suffix.lower() in NON_RUNTIME_SUFFIXES:
                    continue
                filtered_destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(nested_path, filtered_destination)
            continue

        if source_path.suffix.lower() in NON_RUNTIME_SUFFIXES:
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

    return subset_root


def write_plan(plan: SandboxPlan, actions: list[str], dry_run: bool) -> None:
    plan.artifacts_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"timestamp={datetime.now().isoformat(timespec='seconds')}",
        f"dry_run={'yes' if dry_run else 'no'}",
        f"live_mod_root={plan.live_mod_root}",
        f"profile_root={plan.profile_root}",
        f"artifacts_dir={plan.artifacts_dir}",
        f"flow_path={plan.flow_path}",
        f"random_map_name={plan.random_map_name or ''}",
        f"scenario_name={plan.scenario_name or ''}",
        "actions:",
    ]
    lines.extend(f"- {action}" for action in actions)
    (plan.artifacts_dir / "sandbox_plan.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_command(args: list[str]) -> int:
    return subprocess.run(args, cwd=REPO_ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync the live AoE3 mod/profile state, then run the existing automation harness.")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use for child commands.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Repository root. Defaults to the current workspace root.")
    parser.add_argument("--live-mod-root", type=Path, help="Explicit live mod root. Defaults to the first existing Proton local-mod path candidate.")
    parser.add_argument("--profile-root", type=Path, help="Explicit AoE3 profile root ending in 765611... .")
    parser.add_argument("--flow", type=Path, default=DEFAULT_FLOW, help="UI flow JSON to run after launch.")
    parser.add_argument("--artifacts-dir", type=Path, help="Directory for sandbox and retest artifacts.")
    parser.add_argument("--random-map", default=DEFAULT_RANDOM_MAP, help="Publish this random map basename into the profile RandMaps folder.")
    parser.add_argument("--skip-random-map", action="store_true", help="Do not publish a random map into the profile RandMaps folder.")
    parser.add_argument("--scenario", help="Publish this scenario basename into the profile Scenario folder.")
    parser.add_argument("--skip-live-sync", action="store_true", help="Do not mirror the packaged runtime payload into the live local-mod folder.")
    parser.add_argument("--skip-live-validate", action="store_true", help="Skip the post-sync live install validation step.")
    parser.add_argument("--skip-launch", action="store_true", help="Pass through to launch_retest_mod.sh.")
    parser.add_argument("--skip-flow", action="store_true", help="Pass through to launch_retest_mod.sh.")
    parser.add_argument("--skip-static", action="store_true", help="Pass through to launch_retest_mod.sh.")
    parser.add_argument("--runtime-suite", action="append", default=[], help="Runtime validation suite. Repeat for multiple suites.")
    parser.add_argument("--launch-wait", type=int, default=25, help="Pass through to launch_retest_mod.sh when no flow is run.")
    parser.add_argument("--dry-run", action="store_true", help="Print the sync plan without modifying the live install or launching the game.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    flow_path = args.flow.resolve()
    if args.skip_flow is False and flow_path.exists() is False:
        print(f"error: flow file not found: {flow_path}", file=sys.stderr)
        return 1

    live_mod_root = resolve_live_mod_root(args.live_mod_root)
    profile_root = resolve_profile_root(args.profile_root, live_mod_root=live_mod_root)
    artifacts_dir = args.artifacts_dir.resolve() if args.artifacts_dir is not None else DEFAULT_ARTIFACT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")

    plan = SandboxPlan(
        live_mod_root=live_mod_root,
        profile_root=profile_root,
        artifacts_dir=artifacts_dir,
        flow_path=flow_path,
        random_map_name=None if args.skip_random_map else args.random_map,
        scenario_name=args.scenario,
    )
    actions: list[str] = []
    write_plan(plan, actions, dry_run=args.dry_run)

    packaged_root = None
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.skip_live_sync is False:
            packaged_root, temp_dir, _ = build_runtime_payload(repo_root)
            live_subset_root = build_live_runtime_subset(packaged_root, temp_dir.name)
            actions.append(f"ensure directory {live_mod_root}")
            if args.dry_run is False:
                live_mod_root.mkdir(parents=True, exist_ok=True)
            for top_level_name in sorted(GAME_PAYLOAD_TOP_LEVEL):
                source_path = live_subset_root / top_level_name
                if source_path.exists() is False:
                    continue
                replace_path(source_path, live_mod_root / top_level_name, dry_run=args.dry_run, actions=actions)

        if args.skip_random_map is False:
            publish_random_map(repo_root, profile_root, args.random_map, dry_run=args.dry_run, actions=actions)

        if args.scenario:
            publish_scenario(repo_root, profile_root, args.scenario, dry_run=args.dry_run, actions=actions)

        write_plan(plan, actions, dry_run=args.dry_run)

        if args.dry_run:
            print(f"Sandbox dry run written to {plan.artifacts_dir / 'sandbox_plan.txt'}")
            return 0

        if args.skip_live_sync is False and args.skip_live_validate is False:
            validation_result = validate_live_mod_install(repo_root=repo_root, live_root=live_mod_root)
            if validation_result.issues:
                print("error: live install validation failed after sync:", file=sys.stderr)
                for issue in validation_result.issues:
                    print(f" - {issue}", file=sys.stderr)
                return 1

        launch_script = repo_root / "tools" / "aoe3_automation" / "launch_retest_mod.sh"
        launch_args = [str(launch_script), "--artifacts-dir", str(plan.artifacts_dir), "--launch-wait", str(args.launch_wait)]
        if args.skip_launch:
            launch_args.append("--skip-launch")
        if args.skip_flow:
            launch_args.append("--skip-flow")
        else:
            launch_args.extend(["--flow", str(flow_path)])
        if args.skip_static:
            launch_args.append("--skip-static")
        for suite_name in args.runtime_suite:
            launch_args.extend(["--runtime-suite", suite_name])

        return run_command(launch_args)
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())