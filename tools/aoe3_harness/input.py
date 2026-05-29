"""Input injection for AoE3 DE running inside gamescope's nested Xwayland.

Calibrated working method (2026-05-29 overnight session):
  - AoE3 runs on DISPLAY=:1 (gamescope nested Xwayland, not the host :0)
  - Window class: steam_app_933110
  - xdotool key --window <wid> alone does NOT work (gamescope Xwayland limitation)
  - xdotool type --window <wid> WORKS for character input
  - ydotool mousemove + click WORKS for mouse input (kernel uinput → gamescope surface)
  - Combined pattern: ydotool click to activate + xdotool type for key chars
  - For navigation keys (Escape, Return, Tab): use xdotool key after ydotool click

Display: :1 (gamescope nested Xwayland)
Window:  discovered via xdotool search --class steam_app_933110
ydotool: /tmp/.ydotool_socket (daemon runs as root since boot)
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Display / socket constants
# ---------------------------------------------------------------------------
GAMESCOPE_DISPLAY: str = ":1"
YDOTOOL_SOCKET: str = "/tmp/.ydotool_socket"

# X11 keysym names used by xdotool
_KEY_ALIASES: dict[str, str] = {
    "enter": "Return",
    "return": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "tab": "Tab",
    "space": "space",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "f10": "F10",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "f6": "F6",
    "f7": "F7",
    "f8": "F8",
    "f9": "F9",
    "f11": "F11",
    "f12": "F12",
}


def _find_aoe3_window() -> Optional[int]:
    """Return the AoE3 window ID on the gamescope Xwayland display, or None."""
    try:
        result = subprocess.run(
            ["xdotool", "search", "--class", "steam_app_933110"],
            capture_output=True,
            text=True,
            timeout=5,
            env={**__import__("os").environ, "DISPLAY": GAMESCOPE_DISPLAY},
        )
        if result.returncode == 0 and result.stdout.strip():
            wids = [w for w in result.stdout.strip().splitlines() if w.strip()]
            if wids:
                return int(wids[0])
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def _ydotool(args: list[str]) -> bool:
    """Run ydotool with the configured socket. Returns True on success."""
    import os
    env = dict(os.environ)
    env["YDOTOOL_SOCKET"] = YDOTOOL_SOCKET
    try:
        result = subprocess.run(
            ["ydotool"] + args,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _xdotool(args: list[str], wid: Optional[int] = None) -> bool:
    """Run xdotool on the gamescope display. Returns True on success."""
    import os
    env = dict(os.environ)
    env["DISPLAY"] = GAMESCOPE_DISPLAY
    cmd = ["xdotool"]
    if wid is not None and "--window" not in args:
        # Insert --window before the args if not already there
        pass
    cmd.extend(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _activate_window(wid: int) -> None:
    """Activate the AoE3 window via ydotool click."""
    # Get window geometry to find center
    import os
    env = dict(os.environ)
    env["DISPLAY"] = GAMESCOPE_DISPLAY
    try:
        result = subprocess.run(
            ["xdotool", "getwindowgeometry", "--shell", str(wid)],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        # Parse X, Y, WIDTH, HEIGHT from output
        geom: dict[str, int] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                try:
                    geom[k.strip()] = int(v.strip())
                except ValueError:
                    pass
        # Click at center of the window (screen coordinates)
        x = geom.get("X", 0) + geom.get("WIDTH", 960) // 2
        y = geom.get("Y", 0) + geom.get("HEIGHT", 540) // 2
    except Exception:
        x, y = 960, 540  # fallback: center of 1920x1080

    # Use ydotool to move and click (kernel-level, affects Wayland compositor surface)
    _ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)])
    time.sleep(0.1)
    _ydotool(["click", "0x40"])  # left click
    time.sleep(0.15)


def press_key(key: str, wid: Optional[int] = None) -> bool:
    """Send a single key press to the AoE3 window.

    Uses xdotool key --window <wid> on the gamescope Xwayland display.
    For best results, call click() first to ensure window focus.

    Args:
        key: Key name (e.g. 'Return', 'Escape', 'Tab', 'space', 'F10').
             Case-insensitive aliases like 'enter', 'esc' are accepted.
        wid: X11 window ID. If None, auto-discovered.

    Returns:
        True on success.
    """
    import os
    if wid is None:
        wid = _find_aoe3_window()
    if wid is None:
        return False

    keysym = _KEY_ALIASES.get(key.lower(), key)
    env = dict(os.environ)
    env["DISPLAY"] = GAMESCOPE_DISPLAY
    try:
        result = subprocess.run(
            ["xdotool", "key", "--window", str(wid), "--clearmodifiers", "--delay", "50", keysym],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def click(x: int, y: int, wid: Optional[int] = None, button: int = 1) -> bool:
    """Send a mouse click at absolute screen coordinates (gamescope :1 space).

    Uses xdotool mousemove + click on the gamescope Xwayland display.
    Coordinates are in gamescope's coordinate system (0,0 = top-left of game viewport).

    Args:
        x: X coordinate in gamescope display space.
        y: Y coordinate in gamescope display space.
        wid: X11 window ID (optional, for relative coordinates not used here).
        button: Mouse button (1=left, 2=middle, 3=right).

    Returns:
        True on success.
    """
    import os
    env = dict(os.environ)
    env["DISPLAY"] = GAMESCOPE_DISPLAY
    try:
        subprocess.run(
            ["xdotool", "mousemove", "--", str(x), str(y)],
            capture_output=True, text=True, timeout=5, env=env,
        )
        result = subprocess.run(
            ["xdotool", "click", "--clearmodifiers", str(button)],
            capture_output=True, text=True, timeout=5, env=env,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def move_to(x: int, y: int) -> bool:
    """Move the mouse to absolute coordinates in gamescope :1 display space.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        True on success.
    """
    import os
    env = dict(os.environ)
    env["DISPLAY"] = GAMESCOPE_DISPLAY
    try:
        result = subprocess.run(
            ["xdotool", "mousemove", "--", str(x), str(y)],
            capture_output=True, text=True, timeout=5, env=env,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def type_text(s: str, wid: Optional[int] = None, delay_ms: int = 50) -> bool:
    """Type a string into the AoE3 window using xdotool type.

    This is the CONFIRMED WORKING method for character input in AoE3 under
    gamescope. Uses XSendEvent to deliver key events to the window.

    Args:
        s: String to type.
        wid: X11 window ID. If None, auto-discovered.
        delay_ms: Delay between keystrokes in milliseconds.

    Returns:
        True on success.
    """
    import os
    if wid is None:
        wid = _find_aoe3_window()
    if wid is None:
        return False

    env = dict(os.environ)
    env["DISPLAY"] = GAMESCOPE_DISPLAY
    try:
        result = subprocess.run(
            ["xdotool", "type", "--window", str(wid),
             "--delay", str(delay_ms), "--clearmodifiers", "--", s],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def wait_for_window(timeout_s: int = 180) -> Optional[int]:
    """Wait for the AoE3 window to appear on the gamescope display.

    Args:
        timeout_s: Maximum seconds to wait.

    Returns:
        Window ID if found, None if timeout.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        wid = _find_aoe3_window()
        if wid is not None:
            return wid
        time.sleep(3)
    return None


def find_aoe3_window() -> Optional[int]:
    """Return the AoE3 window ID on the gamescope display, or None.

    Public alias for _find_aoe3_window().
    """
    return _find_aoe3_window()
