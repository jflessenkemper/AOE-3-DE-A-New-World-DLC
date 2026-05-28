"""Screenshot the AoE3 game window without grabbing the cursor.

User constraint: no Claude Preview / kwin MCP / Claude-in-Chrome — those move the
real cursor. We use ``import -window <wid>`` (ImageMagick X11) as primary and
``grim -g "x,y wxh"`` (Wayland portal) as fallback. Both are pure pixel reads.

This requires AoE3 to be in borderless windowed mode (NOT exclusive fullscreen),
otherwise DXVK direct-scanout bypasses Plasma's compositor and the pixels are
invisible to standard tools. The harness's launcher must verify this in user
config before launching; see launch.py.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def find_aoe3_window() -> Optional[int]:
    """Return the AoE3 X11 window id, or None if not found.

    Searches for windows with class ``AoE3DE_s`` via xdotool, then falls
    back to ``xwininfo -root -tree`` and looks for ``Age of Empires III``
    in window titles.

    Returns:
        An integer X11 window id if AoE3 is running, or None if not found.
    """
    # Primary: xdotool search by class
    try:
        result = subprocess.run(
            ["xdotool", "search", "--class", "AoE3DE_s"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            wids = [int(w) for w in result.stdout.strip().splitlines() if w.strip()]
            if wids:
                return wids[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: xwininfo tree scan
    try:
        result = subprocess.run(
            ["xwininfo", "-root", "-tree"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Age of Empires III" in line or "AoE3DE" in line:
                    # Lines look like: 0x12345678 "Title": ("class" "Class")...
                    parts = line.strip().split()
                    if parts and parts[0].startswith("0x"):
                        try:
                            return int(parts[0], 16)
                        except ValueError:
                            pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def capture_window(wid: int, out_path: Path) -> bool:
    """Capture AoE3 window pixels via ``import -window <wid> <out_path>``.

    Does NOT focus, raise, or move the window.  Uses ImageMagick's ``import``
    command which reads the composited framebuffer via X11 (requires borderless
    windowed mode; see module docstring).

    Args:
        wid: X11 window id (as returned by find_aoe3_window()).
        out_path: Output path for the PNG file.

    Returns:
        True on success, False on failure.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["import", "-window", str(wid), str(out_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
            print(f"[harness/capture] Captured window 0x{wid:x} -> {out_path}")
            return True
        else:
            print(
                f"[harness/capture] ERROR: import failed for wid 0x{wid:x}: "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
    except FileNotFoundError:
        print(
            "[harness/capture] ERROR: ImageMagick 'import' not found. "
            "Install via: sudo dnf install ImageMagick",
            file=sys.stderr,
        )
        return False
    except subprocess.TimeoutExpired:
        print(
            f"[harness/capture] ERROR: import timed out for wid 0x{wid:x}",
            file=sys.stderr,
        )
        return False


def capture_region(x: int, y: int, w: int, h: int, out_path: Path) -> bool:
    """Wayland-portal fallback via ``grim -g "{x},{y} {w}x{h}" <out_path>``.

    Only used when find_aoe3_window() fails (e.g. nested compositor scenario).
    Requires ``grim`` to be installed (Wayland screenshot utility).

    Args:
        x: Left edge of the capture region in screen coordinates.
        y: Top edge of the capture region in screen coordinates.
        w: Width of the capture region in pixels.
        h: Height of the capture region in pixels.
        out_path: Output path for the PNG file.

    Returns:
        True on success, False on failure.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    geometry = f"{x},{y} {w}x{h}"
    try:
        result = subprocess.run(
            ["grim", "-g", geometry, str(out_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
            print(f"[harness/capture] Captured region {geometry} -> {out_path}")
            return True
        else:
            print(
                f"[harness/capture] ERROR: grim failed for region {geometry}: "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
    except FileNotFoundError:
        print(
            "[harness/capture] ERROR: 'grim' not found. "
            "Install via: sudo dnf install grim",
            file=sys.stderr,
        )
        return False
    except subprocess.TimeoutExpired:
        print(
            f"[harness/capture] ERROR: grim timed out for region {geometry}",
            file=sys.stderr,
        )
        return False


def wait_for_ui_state(
    window_title_substring: str = "",
    timeout_s: int = 30,
) -> bool:
    """Poll until AoE3 is running (window is findable), with an optional timeout.

    Polls ``find_aoe3_window()`` every second.  Primarily used by the
    manual-nav + auto-capture flow to confirm the game window is present
    before attempting a screenshot.

    Note: AoE3's window title does not reliably change between UI states
    (menu, home city, diplomacy, etc.), so this function does not filter by
    ``window_title_substring`` — it only waits for the window to exist.
    The parameter is retained in the signature for forward-compatibility.

    Args:
        window_title_substring: Reserved for future use (not currently checked).
        timeout_s: Maximum seconds to wait before returning False.

    Returns:
        True if the AoE3 window is found within the timeout, False otherwise.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        wid = find_aoe3_window()
        if wid is not None:
            return True
        time.sleep(1)
    return False
