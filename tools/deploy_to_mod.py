#!/usr/bin/env python3
"""Deploy ANW source files to the gamescope-side `mods/local/A New World/` dir.

Syncs every file under `game/ai/**` (and any other tracked source roots)
to the deployed mod directory, only copying when the file is missing or
has a different md5. Prints a summary of what was deployed and what was
already in sync.

Usage:
    python3 tools/deploy_to_mod.py [--dry-run] [--verbose]

Why this exists:
    Wall_strategy compliance was regressed because
    `game/ai/core/aiBuildingsWalls.xs` was 4 hours newer in source than in
    the deployed mod dir. Stale deployed XS files cause the AI to honour
    older dispatch logic, which then writes incorrect probe data into
    `*.personality` files. Run this before every test cycle to guarantee
    parity.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_BASE = Path(
    "/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/"
    "933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/"
    "76561198170207043/mods/local/A New World"
)

# (source_root_relative, glob_patterns) - patterns are relative to source_root
SYNC_ROOTS = [
    ("game/ai", ["**/*.xs", "**/*.xml", "**/*.personality"]),
    ("game", ["**/*.xs"]),
    ("data", ["**/*.xml", "**/*.json", "**/*.yaml"]),
    # 2026-05-18: include RandMaps so anwHubTest.xs + scenario files reach
    # the deployed profile.  Without this, custom-map triggers (e.g.
    # doctrine-capture markers, auto-end Set Player Defeated) sit unused
    # while the game keeps loading the stale deployed map.
    ("RandMaps", ["**/*.xs", "**/*.xml"]),
    # 2026-05-26: portrait + UI art assets. Without this, rebuilding the
    # cpai_avatar_*.png (via tools/rebuild_portraits.py) and its
    # cpai_avatar_*.ddt counterpart (via tools/cardextract/png_to_ddt.py)
    # leaves the deployed mod stale, and the `live_mod_install` validator
    # fails. The engine reads the .ddt for in-game rendering; the WPF UI
    # reads the .png for lobby + scoreboard portraits.
    ("art", ["**/*.ddt", "**/*.png", "**/*.xml"]),
    ("resources", ["**/*.png", "**/*.xml", "**/*.json"]),
]

# Files we don't want to overwrite in deploy dir (e.g. user-saved history).
SKIP_PATTERNS = [
    # .personality files in mods/local should be source-clean, but the
    # *actual* runtime history is in 76561198170207043/Game/AI/, not mods/.
    # The mod-local copies are just installation templates; deploy them.
]


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_sources() -> list[tuple[Path, Path]]:
    """Return list of (source_path, deploy_path) pairs."""
    pairs: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    for src_root_rel, patterns in SYNC_ROOTS:
        src_root = REPO_ROOT / src_root_rel
        if not src_root.is_dir():
            continue
        for pat in patterns:
            for src in src_root.glob(pat):
                if not src.is_file():
                    continue
                if src in seen:
                    continue
                seen.add(src)
                rel = src.relative_to(REPO_ROOT)
                dep = MOD_BASE / rel
                pairs.append((src, dep))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be deployed without copying")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="List in-sync files too")
    args = ap.parse_args()

    if not MOD_BASE.is_dir():
        print(f"[err] mod base does not exist: {MOD_BASE}", file=sys.stderr)
        return 1

    pairs = collect_sources()
    deployed = 0
    in_sync = 0
    new_files = 0

    for src, dep in pairs:
        if not dep.exists():
            new_files += 1
            if args.verbose:
                print(f"NEW    {dep.relative_to(MOD_BASE)}")
            if not args.dry_run:
                dep.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dep)
            continue

        if md5(src) == md5(dep):
            in_sync += 1
            if args.verbose:
                print(f"SAME   {dep.relative_to(MOD_BASE)}")
            continue

        deployed += 1
        print(f"UPDATE {dep.relative_to(MOD_BASE)}")
        if not args.dry_run:
            shutil.copy2(src, dep)

    print()
    print(f"Summary: {deployed} updated, {new_files} new, "
          f"{in_sync} in-sync ({deployed + new_files + in_sync} total)")
    if args.dry_run:
        print("(dry-run — no files were actually copied)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
