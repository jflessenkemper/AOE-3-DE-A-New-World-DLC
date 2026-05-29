#!/usr/bin/env python3
"""ydotool/grim-backed shim with the ``kwin-mcp`` tool surface.

Why this exists
---------------
``kwin-mcp`` is the right long-term answer for AI-driven KDE Plasma 6
Wayland automation, but on Fedora 43 / libei 1.5 it segfaults inside
``ei_seat_bind_capabilities`` (upstream issue
https://github.com/isac322/kwin-mcp/issues/29). Until that's patched
we drive input via the kernel uinput layer (``ydotool`` against the
system socket ``/tmp/.ydotool_socket``) and capture screens via
``grim``. uinput injects *below* both KWin and gamescope, so it
reaches a fullscreen gamescope-nested AoE3 the same way real hardware
does.

Tool surface mirrors kwin-mcp 0.7 so swapping back is a one-line
import change once upstream is fixed:

    mouse_move, mouse_click, mouse_drag, mouse_scroll,
    keyboard_type, keyboard_key, screenshot

Window-management / accessibility-tree calls (``list_windows``,
``focus_window``, ``find_ui_elements``, ``wait_for_element``) are
left as ``NotImplementedError`` — they require AT-SPI2 / KWin DBus
and we don't need them for the in-game AoE3 path; the in-game UI
isn't AT-SPI2-introspectable anyway.

All functions return a ``dict`` shaped like an MCP tool result so a
future swap to real kwin-mcp tool calls is a mechanical change.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

YDOTOOL_SOCKET = os.environ.get("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")

# Artifact root for screenshots
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SCREENSHOT_DIR = REPO_ROOT / "artifacts" / "kwin_compat_screenshots"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

class InputBackendError(RuntimeError):
    """Raised when the underlying input backend fails."""


def _require(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise InputBackendError(
            f"{binary} not found on PATH. Install with `dnf install {binary}` "
            f"or `rpm-ostree install {binary}`."
        )
    return path


def _ydotool(*args: str, timeout: float = 5.0) -> None:
    cmd = [_require("ydotool"), *args]
    env = {**os.environ, "YDOTOOL_SOCKET": YDOTOOL_SOCKET}
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                          timeout=timeout)
    if proc.returncode != 0:
        raise InputBackendError(
            f"ydotool {' '.join(args)} failed (rc={proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )


# ydotool button bitmask: 0x40=down, 0x80=up, 0x00=left, 0x01=right, 0x02=middle.
# A "click" is down|up = 0xC0 (left), 0xC1 (right), 0xC2 (middle).
_BUTTON_DOWN = {"left": 0x40, "right": 0x41, "middle": 0x42}
_BUTTON_UP   = {"left": 0x80, "right": 0x81, "middle": 0x82}
_BUTTON_CLICK = {"left": 0xC0, "right": 0xC1, "middle": 0xC2}


def _modifier_keycodes() -> dict[str, int]:
    # Linux evdev keycodes (linux/input-event-codes.h)
    return {
        "ctrl":  29, "control": 29,
        "shift": 42, "lshift":  42, "rshift": 54,
        "alt":   56, "lalt":    56, "ralt":   100, "altgr": 100,
        "super": 125, "meta":   125, "win":    125, "cmd":   125,
    }


# Common named keys (subset; extend as needed).
_NAMED_KEYS = {
    "return": 28, "enter": 28, "esc": 1, "escape": 1,
    "tab": 15, "space": 57, "backspace": 14, "delete": 111,
    "up": 103, "down": 108, "left": 105, "right": 106,
    "home": 102, "end": 107, "pageup": 104, "pagedown": 109,
    "insert": 110,
    "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64,
    "f7": 65, "f8": 66, "f9": 67, "f10": 68, "f11": 87, "f12": 88,
    "numlock": 69,
    # Letters / digits — ydotool can also `type` for these, but useful for combos.
    "a": 30, "b": 48, "c": 46, "d": 32, "e": 18, "f": 33, "g": 34,
    "h": 35, "i": 23, "j": 36, "k": 37, "l": 38, "m": 50, "n": 49,
    "o": 24, "p": 25, "q": 16, "r": 19, "s": 31, "t": 20, "u": 22,
    "v": 47, "w": 17, "x": 45, "y": 21, "z": 44,
    "0": 11, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7,
    "7": 8, "8": 9, "9": 10,
}


def _resolve_key(name: str) -> int:
    name = name.strip().lower()
    if name in _NAMED_KEYS:
        return _NAMED_KEYS[name]
    if name in _modifier_keycodes():
        return _modifier_keycodes()[name]
    raise InputBackendError(f"unknown key name: {name!r}. Add it to _NAMED_KEYS.")


# ---------------------------------------------------------------------------
# Public API (mirrors kwin-mcp 0.7)
# ---------------------------------------------------------------------------

def mouse_move(x: int, y: int,
               screenshot_after_ms: Optional[list[int]] = None) -> dict:
    """Move cursor to (x, y) in pixels. Returns MCP-shaped dict."""
    _ydotool("mousemove", "--absolute", "-x", str(int(x)), "-y", str(int(y)))
    frames = _capture_burst(screenshot_after_ms)
    return {"ok": True, "op": "mouse_move", "x": x, "y": y,
            "screenshots": frames}


def mouse_click(x: int, y: int,
                button: str = "left",
                double: bool = False,
                triple: bool = False,
                hold_ms: int = 0,
                modifiers: Optional[list[str]] = None,
                screenshot_after_ms: Optional[list[int]] = None) -> dict:
    """Click at (x, y). Modifiers held for the duration of the click."""
    if button not in _BUTTON_CLICK:
        raise InputBackendError(f"unknown button: {button!r}")
    repeats = 3 if triple else (2 if double else 1)

    # Move first.
    _ydotool("mousemove", "--absolute", "-x", str(int(x)), "-y", str(int(y)))
    time.sleep(0.02)  # let move settle

    # Press modifiers (if any).
    mods = [_resolve_key(m) for m in (modifiers or [])]
    for kc in mods:
        _ydotool("key", f"{kc}:1")

    try:
        if hold_ms > 0:
            # press → wait → release
            _ydotool("click", f"0x{_BUTTON_DOWN[button]:02X}")
            time.sleep(hold_ms / 1000.0)
            _ydotool("click", f"0x{_BUTTON_UP[button]:02X}")
        else:
            for _ in range(repeats):
                _ydotool("click", f"0x{_BUTTON_CLICK[button]:02X}")
                if repeats > 1:
                    time.sleep(0.05)  # double/triple inter-click gap
    finally:
        # Release modifiers in reverse order.
        for kc in reversed(mods):
            _ydotool("key", f"{kc}:0")

    frames = _capture_burst(screenshot_after_ms)
    return {"ok": True, "op": "mouse_click", "x": x, "y": y,
            "button": button, "repeats": repeats, "modifiers": modifiers or [],
            "screenshots": frames}


def mouse_drag(x1: int, y1: int, x2: int, y2: int,
               button: str = "left",
               steps: int = 20,
               step_delay_ms: int = 10) -> dict:
    """Press button at (x1,y1), interpolate to (x2,y2), release."""
    if button not in _BUTTON_DOWN:
        raise InputBackendError(f"unknown button: {button!r}")
    _ydotool("mousemove", "--absolute", "-x", str(int(x1)), "-y", str(int(y1)))
    time.sleep(0.02)
    _ydotool("click", f"0x{_BUTTON_DOWN[button]:02X}")
    try:
        for i in range(1, steps + 1):
            t = i / steps
            xi = int(x1 + (x2 - x1) * t)
            yi = int(y1 + (y2 - y1) * t)
            _ydotool("mousemove", "--absolute", "-x", str(xi), "-y", str(yi))
            time.sleep(step_delay_ms / 1000.0)
    finally:
        _ydotool("click", f"0x{_BUTTON_UP[button]:02X}")
    return {"ok": True, "op": "mouse_drag",
            "from": [x1, y1], "to": [x2, y2], "button": button}


def mouse_scroll(x: int, y: int, dy: int = -3, dx: int = 0) -> dict:
    """Scroll dy notches at (x,y). Negative dy = scroll down."""
    _ydotool("mousemove", "--absolute", "-x", str(int(x)), "-y", str(int(y)))
    time.sleep(0.02)
    if dy:
        _ydotool("mousemove", "--wheel", "-y", str(int(dy)))
    if dx:
        _ydotool("mousemove", "--wheel", "-x", str(int(dx)))
    return {"ok": True, "op": "mouse_scroll", "x": x, "y": y,
            "dx": dx, "dy": dy}


def keyboard_type(text: str,
                  screenshot_after_ms: Optional[list[int]] = None) -> dict:
    """Type ASCII text via ydotool (translates to keycodes internally)."""
    _ydotool("type", "--", text)
    frames = _capture_burst(screenshot_after_ms)
    return {"ok": True, "op": "keyboard_type", "text": text,
            "screenshots": frames}


def keyboard_key(key: str,
                 screenshot_after_ms: Optional[list[int]] = None) -> dict:
    """Press a named key or combo like 'Return', 'ctrl+c', 'alt+F4'."""
    parts = [p.strip() for p in key.split("+") if p.strip()]
    if not parts:
        raise InputBackendError(f"empty key: {key!r}")
    keycodes = [_resolve_key(p) for p in parts]
    # Press all down, then release in reverse.
    for kc in keycodes:
        _ydotool("key", f"{kc}:1")
    time.sleep(0.02)
    for kc in reversed(keycodes):
        _ydotool("key", f"{kc}:0")
    frames = _capture_burst(screenshot_after_ms)
    return {"ok": True, "op": "keyboard_key", "key": key,
            "screenshots": frames}


def screenshot(include_cursor: bool = False,
               output_dir: Optional[Path] = None) -> dict:
    """Capture a screenshot via KDE's ``spectacle`` (headless mode).

    KWin Wayland doesn't ship the wlroots ``wlr-screencopy`` protocol that
    ``grim`` uses, so we go through Spectacle's background mode instead.
    Spectacle drives KWin's native ``org.kde.KWin.ScreenShot2`` DBus.
    """
    out_dir = output_dir or SCREENSHOT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = out_dir / f"shot_{int(time.time() * 1000)}.png"
    cmd = [_require("spectacle"), "-b", "-n", "-f", "-o", str(fname)]
    if include_cursor:
        cmd.append("-p")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if proc.returncode != 0 or not fname.exists():
        raise InputBackendError(
            f"spectacle failed (rc={proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    size_kb = round(fname.stat().st_size / 1024, 1)
    return {"ok": True, "op": "screenshot", "path": str(fname),
            "size_kb": size_kb}


def _capture_burst(delays_ms: Optional[list[int]]) -> list[str]:
    """Helper: take screenshots after each delay (ms). Returns paths."""
    if not delays_ms:
        return []
    frames = []
    last = 0
    for d in delays_ms:
        wait = max(0, d - last)
        if wait:
            time.sleep(wait / 1000.0)
        frames.append(screenshot()["path"])
        last = d
    return frames


# ---------------------------------------------------------------------------
# NotImplemented facade (kept for API completeness — swap-friendly)
# ---------------------------------------------------------------------------

def list_windows() -> dict:
    raise NotImplementedError("AT-SPI2 introspection — use kwin-mcp once #29 lands")


def focus_window(app_name: str) -> dict:
    raise NotImplementedError("AT-SPI2 introspection — use kwin-mcp once #29 lands")


def find_ui_elements(query: str, app_name: str = "",
                     states: Optional[list[str]] = None) -> dict:
    raise NotImplementedError("AT-SPI2 introspection — use kwin-mcp once #29 lands")


def wait_for_element(query: str, timeout_ms: int = 5000,
                     poll_interval_ms: int = 200,
                     expected_states: Optional[list[str]] = None,
                     app_name: str = "") -> dict:
    raise NotImplementedError("AT-SPI2 introspection — use kwin-mcp once #29 lands")


# ---------------------------------------------------------------------------
# CLI for ad-hoc smoke tests
# ---------------------------------------------------------------------------

def _main() -> int:
    import argparse, json as _json
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("move"); p.add_argument("x", type=int); p.add_argument("y", type=int)
    p = sub.add_parser("click")
    p.add_argument("x", type=int); p.add_argument("y", type=int)
    p.add_argument("--button", default="left")
    p.add_argument("--double", action="store_true")
    p = sub.add_parser("type"); p.add_argument("text")
    p = sub.add_parser("key"); p.add_argument("key")
    p = sub.add_parser("screenshot"); p.add_argument("--cursor", action="store_true")
    p = sub.add_parser("smoke"); p.add_argument("--x", type=int, default=960); p.add_argument("--y", type=int, default=540)

    args = ap.parse_args()
    try:
        if args.cmd == "move":
            res = mouse_move(args.x, args.y)
        elif args.cmd == "click":
            res = mouse_click(args.x, args.y, button=args.button, double=args.double)
        elif args.cmd == "type":
            res = keyboard_type(args.text)
        elif args.cmd == "key":
            res = keyboard_key(args.key)
        elif args.cmd == "screenshot":
            res = screenshot(include_cursor=args.cursor)
        elif args.cmd == "smoke":
            # Move → screenshot → confirm — non-clicking
            before = screenshot(include_cursor=True)
            mouse_move(args.x, args.y)
            time.sleep(0.2)
            after = screenshot(include_cursor=True)
            res = {"ok": True, "op": "smoke",
                   "target": [args.x, args.y],
                   "before": before["path"], "after": after["path"]}
        else:
            res = {"ok": False, "error": "unknown command"}
    except InputBackendError as e:
        res = {"ok": False, "error": str(e)}
        print(_json.dumps(res, indent=2)); return 1
    print(_json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
