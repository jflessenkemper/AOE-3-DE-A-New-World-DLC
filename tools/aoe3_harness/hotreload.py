"""Hot-reload XS file watcher — re-deploys ANW mod files on save.

Watches source files under the repo's game/ai, data, and RandMaps directories
for changes (the same surface as tools/deploy_to_mod.py) and re-invokes
``deploy_to_mod.py`` whenever a watched file is modified.

Usage::

    # Run directly (foreground; Ctrl-C to stop)
    python3 -m tools.aoe3_harness.hotreload

    # Via CLI subcommand
    python3 -m tools.aoe3_harness.cli hotreload start

The game does NOT need to be running.  When the user next launches AoE3 it
picks up the newly deployed mod files automatically.

Dependency preference:
    1. ``inotify_simple`` (if available) — event-driven, no polling overhead.
       Install with: ``pip install inotify_simple``
    2. ``stat()`` polling every POLL_INTERVAL_S seconds (fallback; no extra deps).

Status printed on each deployment::

    [hotreload] change: aiBuildingsWalls.xs (1023 lines, 38 KB)
    [hotreload] deploy OK (2 actions)
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Named constants — avoids magic numbers
POLL_INTERVAL_S: float = 1.0           # seconds between stat() polls in fallback mode
DEPLOY_TIMEOUT_S: int  = 60            # max seconds for one deploy_to_mod.py run

# Glob patterns to watch — mirrors SYNC_ROOTS in tools/deploy_to_mod.py.
# Any change here must also be reflected in deploy_to_mod.py SYNC_ROOTS.
WATCH_PATTERNS: list[tuple[str, list[str]]] = [
    ("game/ai",   ["**/*.xs", "**/*.xml", "**/*.personality"]),
    ("game",      ["**/*.xs"]),
    ("data",      ["**/*.xml", "**/*.json", "**/*.yaml"]),
    ("RandMaps",  ["**/*.xs", "**/*.xml"]),
]


def _collect_watch_files(repo_root: Path) -> list[Path]:
    """Return the deduplicated list of files to watch.

    Walks WATCH_PATTERNS relative to repo_root, deduplicating paths that
    would be matched by multiple patterns.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        Sorted list of absolute file paths matching WATCH_PATTERNS.
    """
    seen: set[Path] = set()
    result: list[Path] = []
    for src_rel, patterns in WATCH_PATTERNS:
        src_dir = repo_root / src_rel
        if not src_dir.is_dir():
            continue
        for pattern in patterns:
            for p in src_dir.glob(pattern):
                if p.is_file() and p not in seen:
                    seen.add(p)
                    result.append(p)
    result.sort()
    return result


def _collect_watch_dirs(repo_root: Path) -> list[Path]:
    """Return the unique set of directories containing watched files.

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        Sorted list of unique parent directory paths.
    """
    dirs: set[Path] = set()
    for p in _collect_watch_files(repo_root):
        dirs.add(p.parent)
    return sorted(dirs)


def _run_deploy(repo_root: Path) -> None:
    """Invoke deploy_to_mod.py synchronously and print a one-line status.

    Args:
        repo_root: Absolute path to the repository root.
    """
    deploy_script = repo_root / "tools" / "deploy_to_mod.py"
    try:
        result = subprocess.run(
            [sys.executable, str(deploy_script)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=DEPLOY_TIMEOUT_S,
        )
        if result.returncode == 0:
            # Count [deploy] action lines in output
            action_lines = [
                line for line in result.stdout.splitlines()
                if line.strip().startswith("[deploy]")
            ]
            print(f"[hotreload] deploy OK ({len(action_lines)} actions)")
        else:
            print(f"[hotreload] deploy FAILED (rc={result.returncode})", file=sys.stderr)
            if result.stderr:
                print(result.stderr[:500], file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(
            f"[hotreload] deploy timed out after {DEPLOY_TIMEOUT_S}s",
            file=sys.stderr,
        )


def _format_file_status(path: Path) -> str:
    """Return a one-line status string describing a changed file.

    Args:
        path: Path to the changed file.

    Returns:
        Human-readable string, e.g.
        ``'aiBuildingsWalls.xs (1023 lines, 38 KB)'``.
    """
    try:
        line_count = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
        size_kb = path.stat().st_size / 1024
        return f"{path.name} ({line_count} lines, {size_kb:.0f} KB)"
    except OSError:
        return str(path.name)


def watch_inotify(repo_root: Path) -> None:
    """Watch for file changes via ``inotify_simple`` (Linux inotify API wrapper).

    Blocks until Ctrl-C.  Triggers a deploy on IN_CLOSE_WRITE or IN_MOVED_TO
    events (covering both editors that write-in-place and those that use atomic
    renames like ``vim :w``).

    Args:
        repo_root: Absolute path to the repository root.

    Raises:
        ImportError: if ``inotify_simple`` is not installed.  Caller should
                     fall back to :func:`watch_poll`.
    """
    import inotify_simple  # type: ignore[import]

    watch_dirs = _collect_watch_dirs(repo_root)
    print(f"[hotreload] inotify mode — watching {len(watch_dirs)} directories")

    inotify = inotify_simple.INotify()
    # IN_CLOSE_WRITE fires when a file opened for writing is closed.
    # IN_MOVED_TO fires on atomic-rename saves (vim, emacs, etc.).
    flags = inotify_simple.flags.CLOSE_WRITE | inotify_simple.flags.MOVED_TO
    wd_to_dir: dict[int, Path] = {}
    for d in watch_dirs:
        try:
            wd = inotify.add_watch(str(d), flags)
            wd_to_dir[wd] = d
        except OSError as exc:
            print(f"[hotreload] WARN: cannot watch {d}: {exc}", file=sys.stderr)

    print(f"[hotreload] watching {len(wd_to_dir)} directories (Ctrl-C to stop)")

    try:
        while True:
            events = inotify.read(timeout=5000)  # 5s poll to stay responsive
            if not events:
                continue
            # Report first changed file; additional events in the burst are
            # coalesced into a single deploy call to avoid rapid-fire deploys.
            for event in events:
                name = event.name
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="replace")
                if not name:
                    continue
                d = wd_to_dir.get(event.wd, Path("."))
                changed_path = d / name
                print(f"[hotreload] change: {_format_file_status(changed_path)}")
                break  # log only the first event; deploy handles all files
            _run_deploy(repo_root)
    except KeyboardInterrupt:
        print("\n[hotreload] Stopped.")


def watch_poll(repo_root: Path) -> None:
    """Watch for file changes via stat() polling.

    Polls all files matched by WATCH_PATTERNS every POLL_INTERVAL_S seconds,
    comparing mtimes against a baseline snapshot.  Re-collects the file list
    on each cycle to pick up newly created files.

    Blocks until Ctrl-C.  No external dependencies required.

    Args:
        repo_root: Absolute path to the repository root.
    """
    print(
        f"[hotreload] poll mode ({POLL_INTERVAL_S}s interval) — "
        "install inotify_simple for event-driven watching"
    )

    files = _collect_watch_files(repo_root)
    mtimes: dict[Path, Optional[float]] = {}
    for f in files:
        try:
            mtimes[f] = f.stat().st_mtime
        except OSError:
            mtimes[f] = None

    print(f"[hotreload] watching {len(files)} files (Ctrl-C to stop)")

    try:
        while True:
            time.sleep(POLL_INTERVAL_S)
            current_files = _collect_watch_files(repo_root)
            changed: list[Path] = []
            for f in current_files:
                try:
                    mtime = f.stat().st_mtime
                except OSError:
                    mtime = None
                if mtimes.get(f) != mtime:
                    changed.append(f)
                    mtimes[f] = mtime
            if changed:
                for p in changed:
                    print(f"[hotreload] change: {_format_file_status(p)}")
                _run_deploy(repo_root)
    except KeyboardInterrupt:
        print("\n[hotreload] Stopped.")


def run(repo_root: Optional[Path] = None) -> None:
    """Start the hot-reload watcher.

    Tries ``inotify_simple`` first; falls back to polling if not available.

    Args:
        repo_root: Repository root path.  Defaults to the directory two levels
                   above this module file (i.e. the repo root).
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]

    try:
        watch_inotify(repo_root)
    except ImportError:
        watch_poll(repo_root)


if __name__ == "__main__":
    run()
