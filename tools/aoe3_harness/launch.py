"""Game launch via umu-run (gamescope-free, Steam-independent).

Environment contract:
  - /usr/bin/umu-run v1.4.0 (verified installed on Bazzite)
  - WINEPREFIX: ~/.local/share/Steam/steamapps/compatdata/933110/pfx
  - PROTONPATH: ~/.local/share/Steam/steamapps/common/Proton - Experimental
  - GAMEID: 933110
  - STEAM_COMPAT_CLIENT_INSTALL_PATH: ~/.local/share/Steam  (must be set explicitly;
    not in the shell environment by default)

Key constants (verified paths):
  UMU_RUN      = Path("/usr/bin/umu-run")
  EXE_PATH     = Path("~/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe")
  WINEPREFIX   = Path("~/.local/share/Steam/steamapps/compatdata/933110/pfx")
  PROTONPATH   = Path("~/.local/share/Steam/steamapps/common/Proton - Experimental")
  GAMEID       = "933110"
  STEAM_COMPAT = Path("~/.local/share/Steam")

Fallback direct Proton invocation (if umu-run fails):
  SLR_ENTRY    = ~/.local/share/Steam/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point
  PROTON_BIN   = ~/.local/share/Steam/steamapps/common/Proton - Experimental/proton
  The full fallback command is documented in phase1_system_verification.md §2.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from tools.aoe3_harness.paths import (
    AOE3_EXE,
    APPID,
    PROTONPATH,
    REPO_ROOT,
    STEAM_ROOT,
    UMU_RUN,
    USER_PROFILE_XML,
    WINEPREFIX,
)

# Path to the LD_PRELOAD injection .so (Linux host-side input server)
PRELOAD_SO: Path = REPO_ROOT / "tools" / "aoe3_harness" / "preload" / "anw_preload.so"


def kill_stale(force_kill: bool = False) -> bool:
    """Kill any stale AoE3 DE or gamescope processes from previous runs.

    Sends SIGTERM to processes matching ``AppId=933110``, ``gamescopereaper``,
    or ``AoE3DE_s.exe``.  If ``force_kill`` is True and processes are still
    running 5 seconds after SIGTERM, escalates to SIGKILL.

    Args:
        force_kill: If True, escalate to SIGKILL after a 5-second grace period.

    Returns:
        True if any processes were killed, False if none were running.
    """
    patterns = ["AppId=933110", "gamescopereaper", "AoE3DE_s.exe"]
    any_killed = False

    for pattern in patterns:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            pids = [int(p) for p in result.stdout.strip().splitlines() if p.strip()]
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    any_killed = True
                    print(f"[harness/launch] SIGTERM -> PID {pid} ({pattern})")
                except ProcessLookupError:
                    pass  # already gone

    if not any_killed:
        return False

    # Wait for processes to die after SIGTERM
    time.sleep(2)

    # Check if any are still alive
    still_alive: list[int] = []
    for pattern in patterns:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            still_alive.extend(
                int(p) for p in result.stdout.strip().splitlines() if p.strip()
            )

    if still_alive:
        if force_kill:
            print(
                f"[harness/launch] Processes still alive after SIGTERM; "
                f"waiting 3 more seconds then SIGKILL: {still_alive}"
            )
            time.sleep(3)
            for pid in still_alive:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"[harness/launch] SIGKILL -> PID {pid}")
                except ProcessLookupError:
                    pass
        else:
            print(
                f"[harness/launch] WARNING: some processes still alive after SIGTERM "
                f"(use --force-kill to escalate): {still_alive}",
                file=sys.stderr,
            )

    return True


def _detect_display_mode() -> Optional[str]:
    """Read AoE3 UserProfile.xml and return the display mode string.

    Returns the lowercased display-mode value, or None if the file is absent
    or unparseable.  Typical values: ``"windowed"``, ``"borderless windowed"``,
    ``"fullscreen"``.
    """
    if not USER_PROFILE_XML.exists():
        return None
    try:
        tree = ET.parse(str(USER_PROFILE_XML))
        root = tree.getroot()
        # The tag may be <displaymode> or nested; search recursively.
        for elem in root.iter():
            if elem.tag.lower() in ("displaymode", "display_mode", "displayMode"):
                return (elem.text or "").strip().lower()
        # Fallback: search for common attribute names
        for elem in root.iter():
            mode = elem.get("displaymode") or elem.get("DisplayMode")
            if mode:
                return mode.strip().lower()
    except ET.ParseError:
        pass
    return None


def _check_display_mode() -> bool:
    """Check that AoE3 is configured for borderless/windowed mode.

    Logs a clear warning if exclusive fullscreen is detected (which causes
    DXVK direct-scanout, making the framebuffer invisible to compositor tools).

    Returns:
        True if display mode is safe for screenshot capture, False if
        exclusive fullscreen is detected (or mode could not be read).
    """
    mode = _detect_display_mode()
    if mode is None:
        print(
            "[harness/launch] NOTICE: Could not read UserProfile.xml display mode. "
            "If AoE3 is in exclusive fullscreen, screenshots via capture.py will fail. "
            "Recommend: Video Settings -> Display Mode -> Borderless Windowed.",
            file=sys.stderr,
        )
        return True  # permissive: don't block launch
    if "fullscreen" in mode and "borderless" not in mode:
        print(
            f"[harness/launch] WARNING: AoE3 display mode is '{mode}' (exclusive fullscreen). "
            "DXVK will take direct-scanout path; screenshot capture via capture.py WILL FAIL. "
            "Change Video Settings -> Display Mode -> Borderless Windowed before visual capture.",
            file=sys.stderr,
        )
        return False
    print(f"[harness/launch] Display mode: '{mode}' — safe for compositor-level screenshot capture.")
    return True


def build_env(extra: Optional[dict] = None, with_preload: bool = True) -> dict:
    """Build the subprocess environment for umu-run.

    Sets WINEPREFIX, PROTONPATH, GAMEID, STEAM_COMPAT_CLIENT_INSTALL_PATH.
    If ``with_preload`` is True (default) and ``anw_preload.so`` exists, injects
    it via LD_PRELOAD to enable the host-side input injection socket server.
    Merges with os.environ and any caller-supplied overrides.

    Args:
        extra: Optional dict of additional environment variables to set.
        with_preload: If True, inject anw_preload.so via LD_PRELOAD.

    Returns:
        A dict suitable for passing as the ``env`` kwarg to subprocess.run /
        subprocess.Popen.
    """
    env = dict(os.environ)
    env.update(
        {
            "WINEPREFIX": str(WINEPREFIX),
            "PROTONPATH": str(PROTONPATH),
            "GAMEID": APPID,
            "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(STEAM_ROOT),
        }
    )
    if with_preload and PRELOAD_SO.exists():
        existing = env.get("LD_PRELOAD", "")
        new_preload = str(PRELOAD_SO)
        if existing:
            env["LD_PRELOAD"] = f"{new_preload}:{existing}"
        else:
            env["LD_PRELOAD"] = new_preload
        # Remove stale lock so the new server can start
        import os as _os
        _os.unlink("/tmp/anw_preload.lock") if _os.path.exists("/tmp/anw_preload.lock") else None
        print(f"[harness/launch] LD_PRELOAD={env['LD_PRELOAD']}")
    if extra:
        env.update(extra)
    return env


def launch_game(
    scenario: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    dry_run: bool = False,
    force_kill: bool = False,
    extra_env: Optional[dict] = None,
) -> Optional[subprocess.Popen]:
    """Launch AoE3 DE via umu-run.

    Runs a preflight:
    1. Checks that umu-run and AoE3DE_s.exe exist.
    2. Kills stale AoE3/gamescope processes via kill_stale().
    3. Checks display mode; warns if exclusive fullscreen.
    4. Builds the environment and launches the process.

    Args:
        scenario: Optional scenario filename (without path) to pass as
                  ``-scenario <name>`` to AoE3DE_s.exe.
        extra_args: Additional args appended after the exe path.
        dry_run: If True, print the command but do not execute.
        force_kill: If True, escalate stale-process kill to SIGKILL after 5s.
        extra_env: Optional dict of additional environment variables to set
                   (e.g. ``{"WINEDLLOVERRIDES": "anw_hook=n,b"}``).

    Returns:
        subprocess.Popen handle for the launched process, or None if dry_run.

    Raises:
        FileNotFoundError: if umu-run or AoE3DE_s.exe is missing.
        RuntimeError: if stale AoE3 processes are still running after kill_stale().
    """
    # Preflight: tool existence
    if not UMU_RUN.exists():
        raise FileNotFoundError(
            f"umu-run not found at {UMU_RUN}. "
            "Install via: sudo dnf install umu-launcher"
        )
    if not AOE3_EXE.exists():
        raise FileNotFoundError(
            f"AoE3DE_s.exe not found at {AOE3_EXE}. "
            "Verify the game is installed via Steam."
        )

    # Preflight: kill stale processes
    kill_stale(force_kill=force_kill)

    # Verify nothing is still running
    result = subprocess.run(
        ["pgrep", "-f", "AoE3DE_s.exe"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        pids = result.stdout.strip()
        raise RuntimeError(
            f"AoE3DE_s.exe still running after kill_stale() (PIDs: {pids}). "
            "Manually kill those processes or use --force-kill."
        )

    # Preflight: display mode check
    _check_display_mode()

    # Build command
    cmd: list[str] = [str(UMU_RUN), str(AOE3_EXE)]
    if scenario:
        cmd += ["-scenario", scenario]
    if extra_args:
        cmd.extend(extra_args)

    env = build_env(extra=extra_env)

    print(f"[harness/launch] Command: {' '.join(cmd)}")
    print(f"[harness/launch] WINEPREFIX={env['WINEPREFIX']}")
    print(f"[harness/launch] PROTONPATH={env['PROTONPATH']}")
    print(f"[harness/launch] GAMEID={env['GAMEID']}")

    if dry_run:
        print("[harness/launch] dry-run: not executing.")
        return None

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[harness/launch] Launched AoE3DE_s.exe — PID {proc.pid}")
    return proc


def wait_for_exit(proc: subprocess.Popen, timeout: float = 1800.0) -> int:
    """Wait for the game process to exit, with a timeout.

    Args:
        proc: The Popen handle returned by launch_game().
        timeout: Maximum seconds to wait before raising TimeoutError.

    Returns:
        The process exit code.

    Raises:
        TimeoutError: if the process does not exit within timeout seconds.
    """
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            f"AoE3 process PID {proc.pid} did not exit within {timeout}s"
        ) from exc
