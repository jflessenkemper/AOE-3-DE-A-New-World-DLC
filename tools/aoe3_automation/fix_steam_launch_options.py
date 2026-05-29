#!/usr/bin/env python3
"""Clean up the Steam launch options for AoE3 DE (AppID 933110).

The 2026-05-11 0x5 incident had two contributing causes:

1. ~6 GB of stale dev-only files (.git, .venv, .claude, artifacts/, tools/,
   etc.) sitting in the live mod install directory because earlier syncs
   pre-dated the rsync exclude rules and `--delete` skips excluded paths.
   *Fixed* by adding `--delete-excluded` and broadening RSYNC_EXCLUDES in
   `manage_game.py`.

2. The Steam Launch Options for AoE3 still contained `WINEDEBUG=+file
   PROTON_LOG=1 PROTON_LOG_DIR=/home/jflessenkemper` — left over from
   earlier debugging. `WINEDEBUG=+file` traces every single file syscall;
   on AoE3 DE that produces multi-MB Proton logs per launch and slows
   startup enough that gamescope's nested Xwayland (`:2`) eventually
   times out (`XIO: fatal IO error 110 (Connection timed out) on X
   server ":2"`). The same launch options also keep `PROTON_LOG=1`
   active, doubling the I/O storm.

This script rewrites the AoE3 entry in Steam's `localconfig.vdf` so the
launch options keep the gamescope wrapper (we need that for windowed
1920x1080 fixed-resolution capture) but strip the debug environment.

Usage:
    1. Quit Steam completely (right-click tray icon → Exit, or
       `steam -shutdown`).
    2. python3 tools/aoe3_automation/fix_steam_launch_options.py
    3. Start Steam, launch AoE3 — 0x5 should not reappear and the
       game should reach the main menu in normal time.

The script refuses to run while Steam is up because Steam holds an
exclusive lock on localconfig.vdf and overwrites it on graceful exit.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "933110"
DESIRED_LAUNCH_OPTIONS = (
    "gamescope -W 1920 -H 1080 -w 1920 -h 1080 --xwayland-count 1 -- %command%"
)


def steam_is_running() -> bool:
    res = subprocess.run(["pgrep", "-af", "steam.sh|^/.*/steam$"],
                         capture_output=True, text=True)
    return res.returncode == 0 and bool(res.stdout.strip())


def find_localconfig() -> Path | None:
    base = Path.home() / ".local/share/Steam/userdata"
    if not base.exists():
        return None
    candidates = sorted(base.glob("*/config/localconfig.vdf"))
    return candidates[0] if candidates else None


def rewrite(p: Path) -> tuple[bool, str]:
    text = p.read_text()
    # Match the AppID block with its LaunchOptions line.
    pat = re.compile(
        r'("' + APP_ID + r'"\s*\{[^}]*?"LaunchOptions"\s*)"([^"]*)"',
        re.S,
    )
    m = pat.search(text)
    if not m:
        # No existing LaunchOptions — insert one inside the AppID block.
        pat2 = re.compile(r'("' + APP_ID + r'"\s*\{)', re.S)
        m2 = pat2.search(text)
        if not m2:
            return False, "AppID 933110 not found in localconfig.vdf"
        new_block = (m2.group(1)
                     + f'\n\t\t\t\t\t\t"LaunchOptions"\t\t"{DESIRED_LAUNCH_OPTIONS}"')
        text = text[:m2.start()] + new_block + text[m2.end():]
        p.write_text(text)
        return True, f'inserted LaunchOptions = "{DESIRED_LAUNCH_OPTIONS}"'
    current = m.group(2)
    if current == DESIRED_LAUNCH_OPTIONS:
        return True, f'LaunchOptions already clean: "{current}"'
    new_text = text[:m.start()] + m.group(1) + f'"{DESIRED_LAUNCH_OPTIONS}"' + text[m.end():]
    p.write_text(new_text)
    return True, f'was: "{current}"\nnow: "{DESIRED_LAUNCH_OPTIONS}"'


def main() -> int:
    if steam_is_running():
        print("ERROR: Steam is running. Quit Steam first "
              "(right-click tray → Exit, or `steam -shutdown`), "
              "then re-run this script.",
              file=sys.stderr)
        return 2
    cfg = find_localconfig()
    if cfg is None:
        print("ERROR: localconfig.vdf not found in ~/.local/share/Steam/userdata/*/config/",
              file=sys.stderr)
        return 2
    backup = cfg.with_suffix(".vdf.bak.fix_aoe3_launch_options")
    shutil.copy2(cfg, backup)
    print(f"backup: {backup}")
    ok, msg = rewrite(cfg)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
