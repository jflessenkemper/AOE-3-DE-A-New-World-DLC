#!/usr/bin/env python3
"""Dynamic gamescope / Xwayland display detection for AoE3 DE on Bazzite/Proton.

The user may run two gamescope instances simultaneously (e.g. AoE3 DE + CoH2).
The gamescope-N → DISPLAY-N mapping is dynamic — order depends on launch order.
This module detects the AoE3 instance at runtime by sweeping every known
X display and gamescope socket until it finds the combination that owns the
"Age of Empires III" window.

Public API:
    detect_aoe3_display() -> tuple[str, str]
        Returns (X_DISPLAY, GAMESCOPE_WAYLAND_DISPLAY), e.g. (":2", "gamescope-1").
        Raises RuntimeError if AoE3 is not running.

    get_xdo_env()   -> dict  # {DISPLAY: ..., ...os.environ}
    get_gs_env()    -> dict  # {GAMESCOPE_WAYLAND_DISPLAY: ..., WAYLAND_DISPLAY: ..., ...}
    get_both_env()  -> dict  # both merged into os.environ copy

The result is cached process-wide after the first successful detection.
Call invalidate_cache() to force a re-detect on the next call (useful when
resetting between packs if CoH2 may have started/stopped).
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import time
from typing import Optional

WINDOW_TITLE_SUBSTR = "Age of Empires III"
_CACHE: Optional[tuple[str, str]] = None  # (X_DISPLAY, GAMESCOPE_WL)

# AoE3 DE identity constants — used to verify a gamescope process tree is
# actually hosting AoE3 and NOT another Proton/Steam title (e.g. CoH2).
_AOE3_APPID = "933110"
_AOE3_EXE = "AoE3DE_s.exe"


def invalidate_cache() -> None:
    """Force re-detection on the next call to detect_aoe3_display()."""
    global _CACHE
    _CACHE = None


def _is_x_display_alive(display: str, *, timeout: float = 3.0) -> bool:
    """Return True iff an X server actually answers on this display.

    Stale `/tmp/.X*-lock` files outlive their Xwayland processes — e.g. after
    a gamescope crash. Filtering on lock-file existence alone causes
    detect_aoe3_display() to spend seconds polling dead displays before
    falling through. xdpyinfo is the cheapest live-connect probe (~50 ms on
    success, rc=1 with "unable to open display" on stale).
    """
    env = {**os.environ, "DISPLAY": display}
    try:
        res = subprocess.run(
            ["xdpyinfo"], env=env, capture_output=True,
            text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return res.returncode == 0 and "name of display" in res.stdout


def _x_displays() -> list[str]:
    """Return live X displays only, lowest-numbered first.

    Lock-file scan finds candidates; aliveness probe filters out displays
    whose Xwayland process has died but whose lock file still exists.
    Display :0 (host KDE session) is included for completeness but will
    never own the AoE3 gamescope window — it's filtered out by the AoE3
    window-presence check downstream regardless.
    """
    candidates: list[str] = []
    for lock in sorted(glob.glob("/tmp/.X*-lock")):
        n = lock.removeprefix("/tmp/.X").removesuffix("-lock")
        if n.isdigit():
            candidates.append(f":{n}")
    # Also honour the inherited $DISPLAY.
    env_display = os.environ.get("DISPLAY", "")
    if env_display and env_display not in candidates:
        candidates.insert(0, env_display)
    # Filter out displays whose X server no longer answers. This is the
    # primary defence against a crash-then-restart cycle leaving stale
    # locks behind.
    alive = [d for d in candidates if _is_x_display_alive(d)]
    return alive


def _gamescope_sockets() -> list[str]:
    """Return all gamescope-N wayland socket names found in $XDG_RUNTIME_DIR."""
    xdg = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    sockets = sorted(glob.glob(os.path.join(xdg, "gamescope-*")))
    names = [os.path.basename(s) for s in sockets]
    # Fallback to well-known names if directory scan finds nothing.
    if not names:
        names = ["gamescope-0", "gamescope-1", "gamescope-2"]
    return names


_XWININFO_RE = re.compile(
    r'^\s*(0x[0-9a-fA-F]+)\s+"([^"]*)":\s*\([^)]*\)\s+(\d+)x(\d+)\+(-?\d+)\+(-?\d+)'
)


def _has_aoe3_window(display: str, *, timeout: float = 5.0) -> bool:
    """Return True if 'Age of Empires III' window exists on this X display.

    Both probes carry strict timeouts because a wedged-but-not-dead Xwayland
    (rare, but observed after Proton + gamescope OOM events) can hang
    wmctrl/xwininfo for tens of seconds and stall the whole detection loop.
    """
    env = {**os.environ, "DISPLAY": display}
    # Try wmctrl first (fast on EWMH-capable displays).
    try:
        res = subprocess.run(
            ["wmctrl", "-lG"], env=env, capture_output=True,
            text=True, timeout=timeout,
        )
        if res.returncode == 0 and WINDOW_TITLE_SUBSTR in res.stdout:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # fall through to xwininfo
    # Fallback: xwininfo (works on gamescope nested Xwayland, no EWMH).
    try:
        res2 = subprocess.run(
            ["xwininfo", "-root", "-tree"], env=env, capture_output=True,
            text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    if res2.returncode == 0:
        for line in res2.stdout.splitlines():
            if WINDOW_TITLE_SUBSTR in line:
                return True
    return False


def _gs_socket_works(gs_socket: str, *, timeout: int = 5) -> bool:
    """Return True if gamescopectl can reach the given gamescope socket."""
    env = {
        **os.environ,
        "GAMESCOPE_WAYLAND_DISPLAY": gs_socket,
        "WAYLAND_DISPLAY": gs_socket,
    }
    try:
        res = subprocess.run(
            ["gamescopectl", "status"],
            env=env, capture_output=True, timeout=timeout,
        )
        return res.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _gs_socket_resolution(gs_socket: str, *, timeout: int = 8) -> Optional[tuple[int, int]]:
    """Return (width, height) by taking a probe screenshot via gamescopectl.

    Multiple gamescope instances can answer to ``gamescopectl status`` simultaneously,
    so we identify the AoE3 instance by matching its render resolution against the
    AoE3 X display (which is 1920x1080 for AoE3 DE in our launcher).
    Returns None if the screenshot fails or cannot be measured.
    """
    import tempfile, struct
    env = {
        **os.environ,
        "GAMESCOPE_WAYLAND_DISPLAY": gs_socket,
        "WAYLAND_DISPLAY": gs_socket,
    }
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        probe_path = f.name
    try:
        try:
            os.unlink(probe_path)
        except FileNotFoundError:
            pass
        res = subprocess.run(
            ["gamescopectl", "screenshot", probe_path],
            env=env, capture_output=True, timeout=timeout,
        )
        if res.returncode != 0:
            return None
        # gamescopectl writes async; poll briefly.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                if os.path.getsize(probe_path) > 1024:
                    break
            except (FileNotFoundError, OSError):
                pass
            time.sleep(0.2)
        try:
            with open(probe_path, "rb") as f:
                data = f.read(32)
        except (FileNotFoundError, OSError):
            return None
        # PNG IHDR: bytes 16..24 = width, height (big-endian uint32 each)
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width, height = struct.unpack(">II", data[16:24])
        return (width, height)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    finally:
        try:
            os.unlink(probe_path)
        except FileNotFoundError:
            pass


def _gamescope_hosts_aoe3(gs_pid: int) -> bool:
    """Return True only if the gamescope process tree contains AoE3 DE.

    Walks the process tree rooted at *gs_pid* and looks for either:
      - ``AppId=933110`` in any process's cmdline (Steam/Proton injects this), or
      - ``AoE3DE_s.exe`` anywhere in any process's cmdline.

    Returns False (fail-safe) if process inspection is unavailable or raises
    any exception — the caller must then treat the gamescope as not-AoE3 rather
    than assume it is.
    """
    try:
        import psutil  # type: ignore
    except ImportError:
        # psutil unavailable — fall back to /proc scanning so the function
        # works without the optional dependency.
        return _gamescope_hosts_aoe3_proc(gs_pid)

    try:
        root = psutil.Process(gs_pid)
        # Include the gamescope process itself plus all descendants.
        procs = [root] + root.children(recursive=True)
        for proc in procs:
            try:
                cmdline = " ".join(proc.cmdline())
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                continue
            if _AOE3_APPID in cmdline or _AOE3_EXE in cmdline:
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        pass
    return False


def _gamescope_hosts_aoe3_proc(gs_pid: int) -> bool:
    """psutil-free fallback: walk /proc/<pid>/cmdline for the process tree.

    Uses only stdlib. Returns False on any error (fail-safe).
    """
    import glob as _glob

    def _cmdline(pid: int) -> str:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                return fh.read().replace(b"\x00", b" ").decode(errors="replace")
        except OSError:
            return ""

    def _ppid(pid: int) -> Optional[int]:
        try:
            with open(f"/proc/{pid}/stat", "r") as fh:
                parts = fh.read().split()
                return int(parts[3])  # field 4 (0-indexed 3) = ppid
        except (OSError, IndexError, ValueError):
            return None

    # Build a map pid -> [child_pid] for all accessible processes.
    try:
        all_pids = [int(os.path.basename(p))
                    for p in _glob.glob("/proc/[0-9]*")]
    except OSError:
        return False

    children: dict[int, list[int]] = {}
    for pid in all_pids:
        ppid = _ppid(pid)
        if ppid is not None:
            children.setdefault(ppid, []).append(pid)

    # BFS from gs_pid.
    queue = [gs_pid]
    seen: set[int] = set()
    while queue:
        pid = queue.pop()
        if pid in seen:
            continue
        seen.add(pid)
        cmd = _cmdline(pid)
        if _AOE3_APPID in cmd or _AOE3_EXE in cmd:
            return True
        queue.extend(children.get(pid, []))
    return False


def _find_gamescope_pid() -> Optional[int]:
    """Return the PID of the first 'gamescope' process found, or None."""
    try:
        res = subprocess.run(
            ["pgrep", "-x", "gamescope"],
            capture_output=True, text=True, timeout=5,
        )
        if res.returncode == 0:
            pids = [int(p.strip()) for p in res.stdout.splitlines() if p.strip().isdigit()]
            if pids:
                return pids[0]
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def _x_display_resolution(display: str) -> Optional[tuple[int, int]]:
    """Return (width, height) of the X root window on the given display, or None."""
    env = {**os.environ, "DISPLAY": display}
    try:
        res = subprocess.run(
            ["xwininfo", "-root"], env=env, capture_output=True, text=True, timeout=5
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if res.returncode != 0:
        return None
    w = h = None
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith("Width:"):
            try:
                w = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("Height:"):
            try:
                h = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    if w and h:
        return (w, h)
    return None


def _gamescope_pids_for_socket(gs_socket: str) -> list[int]:
    """Return PIDs of gamescope processes that own *gs_socket*.

    Looks for processes named 'gamescope' whose cmdline contains the socket
    name (e.g. 'gamescope-0').  Returns an empty list if none are found or
    /proc inspection fails — callers treat an empty list as unverifiable.
    """
    pids: list[int] = []
    try:
        res = subprocess.run(
            ["pgrep", "-x", "gamescope"],
            capture_output=True, text=True, timeout=5,
        )
        if res.returncode != 0:
            return pids
        for line in res.stdout.splitlines():
            pid_str = line.strip()
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as fh:
                    cmdline = fh.read().replace(b"\x00", b" ").decode(errors="replace")
                if gs_socket in cmdline:
                    pids.append(pid)
            except OSError:
                # If we can't read cmdline for this pid, still include it so the
                # caller can try process-tree inspection — better to check than skip.
                pids.append(pid)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return pids


def detect_aoe3_display(*, use_cache: bool = True) -> tuple[str, str]:
    """Detect (X_DISPLAY, GAMESCOPE_WL) for the running AoE3 DE instance.

    Algorithm:
      1. For each X display with an X-lock file, check for the AoE3 window.
      2. Verify at least one gamescope process tree hosting that display
         contains AppId=933110 or AoE3DE_s.exe (guards against false-positive
         when a different Steam title such as CoH2 is the only running gamescope).
      3. For each gamescope socket in $XDG_RUNTIME_DIR, try `gamescopectl status`.
      4. Pair the first valid X display with the first valid gamescope socket.
         (They are typically co-indexed: :1 + gamescope-0, :2 + gamescope-1, etc.
         but we verify each independently rather than assuming the offset.)

    Returns (X_DISPLAY, GAMESCOPE_WL), e.g. (":2", "gamescope-1").
    Raises RuntimeError if no AoE3 window is found on any display, or if
    process-tree verification confirms the only running gamescope hosts a
    different title (AppId != 933110 / exe != AoE3DE_s.exe).
    """
    global _CACHE
    if use_cache and _CACHE is not None:
        return _CACHE

    displays = _x_displays()
    sockets = _gamescope_sockets()

    aoe3_display: Optional[str] = None
    for d in displays:
        if _has_aoe3_window(d):
            aoe3_display = d
            break

    if aoe3_display is None:
        raise RuntimeError(
            f"AoE3 DE window not found on any X display "
            f"(checked: {displays}). Is the game running?"
        )

    # --- AppId / exe identity gate ----------------------------------------
    # After the window-title check passes, verify that a gamescope process
    # hosting AoE3 DE (AppId=933110 / AoE3DE_s.exe) is actually present.
    # This prevents the false-positive where a different game (e.g. CoH2,
    # AppId=231430 / RelicCoH2.exe) is the only live gamescope and the
    # window-title check mis-fired (tool timeout / stale window list).
    #
    # Fail-safe: if process inspection is completely unavailable (no pgrep,
    # no /proc, no psutil) we log a warning but do NOT claim AoE3 is present
    # — the caller gets a RuntimeError rather than a false positive.
    aoe3_verified = False
    # Gather all gamescope pids once and check whether any of their trees
    # contains the AoE3 identity markers.
    all_gs_pids: list[int] = []
    for gs_sock in sockets:
        all_gs_pids.extend(_gamescope_pids_for_socket(gs_sock))
    # Also check all gamescope pids even if they don't match a known socket name
    # (covers the fallback/derived-name path).
    try:
        res = subprocess.run(
            ["pgrep", "-x", "gamescope"],
            capture_output=True, text=True, timeout=5,
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                pid_str = line.strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid not in all_gs_pids:
                        all_gs_pids.append(pid)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    if all_gs_pids:
        for gs_pid in all_gs_pids:
            if _gamescope_hosts_aoe3(gs_pid):
                aoe3_verified = True
                break
        if not aoe3_verified:
            raise RuntimeError(
                f"AoE3 DE window title found on DISPLAY={aoe3_display}, but "
                f"no gamescope process tree contains AppId={_AOE3_APPID} or "
                f"{_AOE3_EXE!r}. A different Steam title is likely running "
                f"under gamescope (e.g. CoH2 AppId=231430). "
                f"Is AoE3 DE (AppId={_AOE3_APPID}) actually running?"
            )
    else:
        # pgrep / /proc unavailable — cannot verify identity. Fail safe.
        raise RuntimeError(
            f"AoE3 DE window title found on DISPLAY={aoe3_display}, but "
            f"process-tree inspection is unavailable (no pgrep / no /proc). "
            f"Cannot confirm AppId={_AOE3_APPID} / {_AOE3_EXE!r} is present. "
            f"Refusing to report AoE3 present without identity verification."
        )
    # ----------------------------------------------------------------------

    # Pair the AoE3 X display with the gamescope that renders at the same
    # resolution. Multiple gamescope instances may both answer ``status``,
    # but only one of them actually owns the AoE3 framebuffer.
    aoe3_res = _x_display_resolution(aoe3_display)
    aoe3_gs: Optional[str] = None
    if aoe3_res is not None:
        for gs in sockets:
            if not _gs_socket_works(gs):
                continue
            gs_res = _gs_socket_resolution(gs)
            if gs_res == aoe3_res:
                aoe3_gs = gs
                break

    if aoe3_gs is None:
        # Secondary path: take any responsive socket (legacy behaviour).
        for gs in sockets:
            if _gs_socket_works(gs):
                aoe3_gs = gs
                break

    if aoe3_gs is None:
        # Hard fallback: derive from display number (offset -1 for display :1 -> gamescope-0).
        num_str = aoe3_display.lstrip(":")
        try:
            idx = max(0, int(num_str) - 1)
        except ValueError:
            idx = 0
        aoe3_gs = f"gamescope-{idx}"
        print(
            f"[gamescope_detect] WARNING: gamescopectl did not respond on any socket; "
            f"falling back to derived name '{aoe3_gs}' (from DISPLAY={aoe3_display})."
        )

    print(
        f"[gamescope_detect] AoE3 detected: DISPLAY={aoe3_display}  "
        f"GAMESCOPE_WAYLAND_DISPLAY={aoe3_gs}"
    )
    _CACHE = (aoe3_display, aoe3_gs)
    return _CACHE


# ---------------------------------------------------------------------------
# Convenience helpers for callers that build subprocess env dicts.
# ---------------------------------------------------------------------------

def get_xdo_env(*, use_cache: bool = True) -> dict[str, str]:
    """Return os.environ copy with DISPLAY set to the AoE3 Xwayland display."""
    display, _ = detect_aoe3_display(use_cache=use_cache)
    return {**os.environ, "DISPLAY": display}


def get_gs_env(*, use_cache: bool = True) -> dict[str, str]:
    """Return os.environ copy with GAMESCOPE_WAYLAND_DISPLAY and WAYLAND_DISPLAY set."""
    _, gs = detect_aoe3_display(use_cache=use_cache)
    return {**os.environ, "GAMESCOPE_WAYLAND_DISPLAY": gs, "WAYLAND_DISPLAY": gs}


def get_both_env(*, use_cache: bool = True) -> dict[str, str]:
    """Return os.environ copy with DISPLAY + GAMESCOPE_WAYLAND_DISPLAY + WAYLAND_DISPLAY set."""
    display, gs = detect_aoe3_display(use_cache=use_cache)
    return {
        **os.environ,
        "DISPLAY": display,
        "GAMESCOPE_WAYLAND_DISPLAY": gs,
        "WAYLAND_DISPLAY": gs,
    }


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        d, gs = detect_aoe3_display()
        print(f"PASS: DISPLAY={d}  GAMESCOPE_WAYLAND_DISPLAY={gs}")
    except RuntimeError as e:
        print(f"FAIL: {e}")
        raise SystemExit(1)
