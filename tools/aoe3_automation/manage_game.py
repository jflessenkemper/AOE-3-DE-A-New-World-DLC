#!/usr/bin/env python3
"""Close, sync, and reopen Age of Empires III: Definitive Edition on Linux/Proton.

Subcommands:
    status   — print whether the game is running plus window geometry.
    close    — gracefully close the game and wait for its processes to exit.
    sync     — rsync the repo into the live Steam mod install.
    open     — launch the game via Steam URI and wait for the main menu window.
    cycle    — close + sync + open, for applying a mod fix in one step.

Usage (from repo root):
    python3 tools/aoe3_automation/manage_game.py cycle
    python3 tools/aoe3_automation/manage_game.py close
    python3 tools/aoe3_automation/manage_game.py open --timeout 90
    python3 tools/aoe3_automation/manage_game.py open --no-dev-mode  # production launch

Developer mode
--------------
By default, ``open`` (and ``cycle``) place a ``user.cfg`` file containing the
bare token ``developer`` in the game's user Startup directory:

    ~/.local/share/.../76561198170207043/Startup/user.cfg

This activates the AoE3 DE engine's developer mode, which routes ``aiEcho()``
output from XS AI scripts to ``Age3Log.txt``.  Without this flag ``aiEcho()``
calls are silently dropped, so the ``[LLP v=2 ...]`` probe lines emitted by
the Legendary Leaders AI hooks never appear in the log — rendering the entire
probe-validation pipeline inoperative.

Mechanism (approach 3 — config file flag):
  AoE3 DE processes ``*.cfg`` files from two Startup directories on launch:
    1. <game_install>/Startup/game.cfg  — base config (has ``//developer``
       commented out by default in the production install).
    2. <user_gamedir>/<steamid>/Startup/*.cfg — personal overrides.
  Adding ``developer`` to a file in location 2 enables developer mode the
  same way as uncommenting it in game.cfg, but without touching the install.

Use ``--no-dev-mode`` for production (tournament / Safe-for-MP) launches
where the extra debug overhead is unwanted.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

APP_ID = 933110
GAME_EXE = "AoE3DE_s.exe"
WINDOW_TITLE_SUBSTR = "Age of Empires III"

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_MOD_PATH = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata"
    / str(APP_ID)
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World"
)

# Directories that exist in the repo but should NOT be copied to the live
# install. Mirrors tools/validation/validate_packaged_mod.py DEV_ONLY_TOP_LEVEL.
#
# IMPORTANT: sync uses `--delete-excluded` (see cmd_sync) so anything matching
# these patterns gets pruned from the live install too — not just kept out of
# new syncs. The 2026-05-11 0x5 incident was caused by 6 GB of stale .git,
# .venv, .claude, artifacts/, tools/, etc. left over from earlier syncs that
# pre-dated these excludes, slowing the engine's mod walk enough to time out
# Xwayland :2.
RSYNC_EXCLUDES = (
    "/.*",                     # dotfiles/dotdirs: .git, .venv, .claude, .vscode, .clone, .pytest_cache, .gitignore, etc.
    "/age-of-pirates",
    "/age-of-pirates-main",
    "/reference-mods",
    "/tests",
    "/tools",
    "/docs",
    "/artifacts",
    "/logs",
    "/*.md",                   # root-level markdown (CHANGELOG, README, MOD_HISTORY, etc.)
    "/*.txt",                  # root-level txt notes (session_notes_*, ANW_*.txt, etc.)
    "/*.sh",                   # root-level shell scripts (run_anw_*.sh, comprehensive_test.sh, etc.)
    "/*.html",                 # root-level reference HTML (a_new_world.html, DEVELOPMENT_REFERENCE.html, map_3d.html)
    "/*.age3Yrec",             # leftover replays
    "/blurb_database.json",
    "/civ_string_id_map.json",
    "/enriched_reference.json",
    "/PLAYSTYLE_SPECIFICATIONS.json",
    "/playstyle_spec.json",
    "/reference_matrix.json",
    "/test_scenarios.json",
)


def run(cmd: list[str], check: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def game_pids() -> list[int]:
    """Return PIDs of any live AoE3 DE game processes."""
    res = run(["pgrep", "-f", GAME_EXE], check=False)
    if res.returncode != 0:
        return []
    return [int(p) for p in res.stdout.split() if p.strip().isdigit()]


def game_window() -> tuple[str, int, int, int, int] | None:
    """Return (window_id, x, y, w, h) for the game window, or None.

    The Bazzite/gamescope rig nests each game under a fresh Xwayland on a
    new DISPLAY (`:0` is the desktop, `:1`/`:2`/... are gamescope children).
    `wmctrl` defaults to whatever `$DISPLAY` is set to, so we sweep every
    `/tmp/.X<N>-lock` displayed by the kernel, and merge the first hit."""
    import glob

    candidates: list[str] = []
    for lock in sorted(glob.glob("/tmp/.X*-lock")):
        # /tmp/.X1-lock → :1
        n = lock.removeprefix("/tmp/.X").removesuffix("-lock")
        if n.isdigit():
            candidates.append(f":{n}")
    # Always probe the inherited DISPLAY too, in case nothing showed up.
    if os.environ.get("DISPLAY") and os.environ["DISPLAY"] not in candidates:
        candidates.insert(0, os.environ["DISPLAY"])

    # gamescope's nested Xwayland servers don't implement EWMH, so wmctrl
    # fails on them with "Cannot get client list properties". Fall back to
    # `xwininfo -root -tree`, which only needs core X11 protocol.
    xwininfo_re = re.compile(
        r'^\s*(0x[0-9a-fA-F]+)\s+"([^"]*)":\s*\([^)]*\)\s+(\d+)x(\d+)\+(-?\d+)\+(-?\d+)'
    )
    for display in candidates:
        env = {**os.environ, "DISPLAY": display}
        res = subprocess.run(["wmctrl", "-lG"], env=env,
                             capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if WINDOW_TITLE_SUBSTR in line:
                    parts = line.split(None, 7)
                    if len(parts) >= 6:
                        return parts[0], int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
        # wmctrl failed or had no match → try xwininfo on this display.
        res2 = subprocess.run(["xwininfo", "-root", "-tree"], env=env,
                              capture_output=True, text=True)
        if res2.returncode != 0:
            continue
        for line in res2.stdout.splitlines():
            if WINDOW_TITLE_SUBSTR not in line:
                continue
            m = xwininfo_re.match(line)
            if m:
                wid, _title, w, h, x, y = m.groups()
                return wid, int(x), int(y), int(w), int(h)
    return None


def cmd_status(_args: argparse.Namespace) -> int:
    pids = game_pids()
    win = game_window()
    print(f"Game processes: {pids or 'none'}")
    print(f"Game window:    {win or 'none'}")
    if win is not None and (win[3], win[4]) != (1920, 1080):
        print(f"WARN: window geometry is {win[3]}x{win[4]}, expected 1920x1080")
    return 0 if pids else 1


def cmd_close(args: argparse.Namespace) -> int:
    pids = game_pids()
    if not pids:
        print("Game not running.")
        return 0

    # 1) Graceful WM close via window ID. wmctrl needs EWMH, which gamescope's
    # nested Xwayland lacks — fall back to xdotool windowclose, which uses
    # core X11 only. We ask both, on whatever display the window lives on.
    win = game_window()
    if win is not None:
        print(f"Sending WM_DELETE to window {win[0]}")
        # Find which display the window is on by re-sweeping and matching wid.
        import glob as _glob
        target_display = os.environ.get("DISPLAY", ":0")
        for lock in sorted(_glob.glob("/tmp/.X*-lock")):
            n = lock.removeprefix("/tmp/.X").removesuffix("-lock")
            if not n.isdigit():
                continue
            d = f":{n}"
            env = {**os.environ, "DISPLAY": d}
            r = subprocess.run(["xwininfo", "-id", win[0]], env=env,
                               capture_output=True, text=True)
            if r.returncode == 0:
                target_display = d
                break
        env = {**os.environ, "DISPLAY": target_display}
        subprocess.run(["wmctrl", "-i", "-c", win[0]], env=env, check=False,
                       capture_output=True)
        subprocess.run(["xdotool", "windowclose", win[0]], env=env, check=False,
                       capture_output=True)

    deadline = time.time() + args.graceful_timeout
    while time.time() < deadline:
        if not game_pids():
            print("Game closed cleanly.")
            return 0
        time.sleep(1)

    # 2) SIGTERM to the game EXE process(es).
    print(f"Graceful close timed out after {args.graceful_timeout}s; sending SIGTERM")
    run(["pkill", "-TERM", "-f", GAME_EXE], check=False)
    deadline = time.time() + 10
    while time.time() < deadline:
        if not game_pids():
            print("Game exited after SIGTERM.")
            return 0
        time.sleep(1)

    # 3) Last resort — SIGKILL.
    print("SIGTERM did not take; escalating to SIGKILL")
    run(["pkill", "-KILL", "-f", GAME_EXE], check=False)
    time.sleep(2)
    if game_pids():
        print("ERROR: game processes still present after SIGKILL:", game_pids(), file=sys.stderr)
        return 2

    # Give Steam a beat to register "not running" before any relaunch.
    time.sleep(3)
    print("Game closed (SIGKILL).")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    if not LIVE_MOD_PATH.exists():
        print(f"ERROR: live mod path does not exist: {LIVE_MOD_PATH}", file=sys.stderr)
        return 2
    if game_pids():
        print("WARN: game is still running; sync may not take effect until restart")

    excludes: list[str] = []
    for pattern in RSYNC_EXCLUDES:
        excludes.extend(["--exclude", pattern])

    src = str(REPO_ROOT) + os.sep
    dst = str(LIVE_MOD_PATH) + os.sep
    # --delete-excluded ensures excluded paths get pruned from the live
    # install, not just kept out of new syncs. Required to clean up cruft
    # that pre-dated the current exclude list (see RSYNC_EXCLUDES comment).
    cmd = ["rsync", "-a", "--checksum", "--delete", "--delete-excluded",
           *excludes, src, dst]
    if args.dry_run:
        cmd.insert(1, "-n")
    print("Running:", " ".join(cmd))
    res = run(cmd, check=False, capture=False)
    if res.returncode != 0:
        print(f"ERROR: rsync exited {res.returncode}", file=sys.stderr)
        return res.returncode
    print(f"Sync complete: {REPO_ROOT} -> {LIVE_MOD_PATH}")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    if game_pids():
        print("Game is already running.")
        win = game_window()
        if win:
            print(f"Window: {win}")
        return 0

    if not shutil.which("steam"):
        print("ERROR: steam binary not on PATH", file=sys.stderr)
        return 2

    # Dev-mode: write/remove the user.cfg that activates aiEcho() → Age3Log.txt.
    no_dev = getattr(args, "no_dev_mode", False)
    try:
        # log_capture.py lives next to this file. Add this script's parent
        # to sys.path so the import works regardless of CWD.
        _here = str(Path(__file__).resolve().parent)
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from log_capture import ensure_dev_mode, remove_dev_mode, USER_CFG_PATH
        if no_dev:
            removed = remove_dev_mode()
            if removed:
                print("Dev mode: removed user.cfg (production launch)")
            else:
                print("Dev mode: user.cfg already absent (production launch)")
        else:
            existed = ensure_dev_mode()
            if existed:
                print(f"Dev mode: user.cfg already present ({USER_CFG_PATH})")
            else:
                print(f"Dev mode: created user.cfg ({USER_CFG_PATH})")
    except ImportError:
        if not no_dev:
            print("WARN: log_capture module not found; dev mode not configured", file=sys.stderr)

    # `steam -applaunch <id>` asks the already-running Steam client to launch
    # the game. The `steam steam://rungameid/<id>` URI form is sometimes a
    # no-op after a recent game exit (observed on Bazzite/KDE), so prefer
    # -applaunch.
    print(f"Launching via steam -applaunch {APP_ID}")
    subprocess.Popen(
        ["steam", "-applaunch", str(APP_ID)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        win = game_window()
        if win is not None and (win[3], win[4]) == (1920, 1080):
            # Window exists at expected size; give the engine a moment to finish
            # rendering the main menu before returning success.
            time.sleep(args.post_menu_wait)
            print(f"Game window ready at geometry {win[3]}x{win[4]} offset ({win[1]}, {win[2]})")
            return 0
        time.sleep(2)

    print(f"ERROR: game window did not appear at 1920x1080 within {args.timeout}s", file=sys.stderr)
    win = game_window()
    if win:
        print(f"Current window: {win} (wrong size/geometry)", file=sys.stderr)
    return 3


def cmd_cycle(args: argparse.Namespace) -> int:
    rc = cmd_close(args)
    if rc != 0:
        return rc
    rc = cmd_sync(args)
    if rc != 0:
        return rc
    rc = cmd_open(args)
    return rc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Report game process + window state")

    p_close = sub.add_parser("close", help="Close the game; escalate to SIGKILL if needed")
    p_close.add_argument("--graceful-timeout", type=int, default=15,
                         help="Seconds to wait after WM_DELETE before SIGTERM (default 15)")

    p_sync = sub.add_parser("sync", help="Rsync repo into live Steam mod install")
    p_sync.add_argument("--dry-run", action="store_true", help="Show what would change without writing")

    p_open = sub.add_parser("open", help="Launch the game via steam:// URI and wait for main menu")
    p_open.add_argument("--timeout", type=int, default=90,
                        help="Seconds to wait for the main menu window (default 90)")
    p_open.add_argument("--post-menu-wait", type=int, default=5,
                        help="Seconds to wait after window appears so the engine settles (default 5)")
    p_open.add_argument("--no-dev-mode", action="store_true",
                        help="Remove developer user.cfg before launching (production launch; "
                             "disables aiEcho probe capture)")

    p_cycle = sub.add_parser("cycle", help="close + sync + open — one-shot mod-iterate")
    p_cycle.add_argument("--graceful-timeout", type=int, default=15)
    p_cycle.add_argument("--timeout", type=int, default=90)
    p_cycle.add_argument("--post-menu-wait", type=int, default=5)
    p_cycle.add_argument("--dry-run", action="store_true")
    p_cycle.add_argument("--no-dev-mode", action="store_true",
                         help="Remove developer user.cfg before launching (production launch)")

    args = p.parse_args(argv)
    return {
        "status": cmd_status,
        "close": cmd_close,
        "sync": cmd_sync,
        "open": cmd_open,
        "cycle": cmd_cycle,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
