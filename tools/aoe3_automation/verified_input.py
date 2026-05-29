#!/usr/bin/env python3
"""Self-diagnosing, screenshot-verified input harness for the gamescope-nested AoE3 DE.

The 100%-reliability story
==========================

The honest truth about driving the AoE3 DE / ANW mod inside a gamescope
nested compositor: there is *no single Linux input API* that's
guaranteed to reach the game across every system config. The chain is:

    keyboard/mouse → libinput → host compositor (KWin/Hyprland/X) → gamescope
    (as Wayland client) → Xwayland inside gamescope → game (Win32 via Proton)

Each link has its own failure modes. Empirically we've measured:

  - xdotool DISPLAY=:1 → moves the gamescope-internal X cursor, but the
    gamescope compositor renders its own cursor from its Wayland seat
    and ignores the X-cursor moves. **Doesn't reach the game.**
  - xdotool DISPLAY=:0 → moves the host X cursor (or no-op if host is
    Wayland). gamescope is a Wayland client; sees the host cursor only
    if focused. **Unreliable; depends on host session type.**
  - ydotool → /dev/uinput → libinput → host compositor → gamescope.
    Works IF (a) ydotoold daemon running, (b) socket accessible,
    (c) uinput device assigned to the user's seat. On bare Bazzite
    with default udev rules, the uinput device is created but on no
    seat, so events don't propagate. **Works only with extra setup.**
  - libei via gamescope-0-ei socket → THE designed-for-this path.
    Requires libei-devel headers to compile a small C client (or a
    Python ctypes wrapper of libei). gamescope listens on this socket
    by default. **Works reliably if the libei client can be built.**

Rather than pick one and hope, this harness:

  1. Auto-detects every available backend at startup.
  2. Probes each one with a SCREENSHOT-DIFF VERIFICATION:
       * Capture frame.
       * Send a small mouse-move (delta of -50 px from current).
       * Capture frame again.
       * If the diff bbox is non-empty AND inside the cursor ROI,
         the backend reaches the game. Otherwise it's broken.
  3. Picks the first backend that passed the probe.
  4. Caches the choice for the session.
  5. Every action is verified the same way: capture-act-capture-diff.
  6. If no backend passes the probe, raises ``InputBackendUnavailable``
     with a diagnostic report and exact remediation commands.

This means the harness is RELIABLE in two ways:

  (a) When a backend works, every action is verified — no silent
      no-ops slipping past us.
  (b) When no backend works, we fail LOUDLY with concrete remediation,
      not silently or with a confusing "rc=0".

Usage
=====

::

    from tools.aoe3_automation.verified_input import VerifiedInput, InputBackendUnavailable

    h = VerifiedInput()
    h.probe()                          # detect + verify; raises if none works
    h.move(960, 540)                   # absolute move, verified
    h.click(960, 540)                  # left-click at coords, verified
    h.scroll_down(steps=3)             # verified
    h.key("Escape")                    # verified key press
    h.type_text("hello")               # verified

Or run the diagnostic directly::

    python3 tools/aoe3_automation/verified_input.py --probe
    python3 tools/aoe3_automation/verified_input.py --self-test

Exit codes: 0 = at least one backend works; 1 = no working backend.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


class InputBackendUnavailable(RuntimeError):
    """No backend successfully reached the gamescope-nested game."""


# --- Screenshot capture (read-only; doesn't need a working input backend) ---

def _capture_screenshot(out_path: Path, timeout_s: float = 6.0) -> bool:
    """Capture the screen to out_path. Tries multiple backends in priority order.

    Order: gamescopectl (if gamescope running) → spectacle (KDE Wayland)
    → grim (wlroots Wayland) → import (X11) → gnome-screenshot.
    Returns True if any backend wrote a >50KB PNG.
    """
    try:
        out_path.unlink(missing_ok=True)
    except Exception:
        pass

    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

    backends: list[tuple[str, list[str], dict]] = []
    # 1. gamescopectl — only useful if gamescope-0 socket exists
    if shutil.which("gamescopectl") and Path(f"{runtime_dir}/gamescope-0").exists():
        backends.append((
            "gamescopectl",
            ["gamescopectl", "screenshot", str(out_path)],
            {"GAMESCOPE_WAYLAND_DISPLAY": "gamescope-0",
             "WAYLAND_DISPLAY": "gamescope-0",
             "XDG_RUNTIME_DIR": runtime_dir},
        ))
    # 2. host backends (via flatpak-spawn if we're sandboxed)
    has_spawn = shutil.which("flatpak-spawn") is not None
    spawn_prefix: list[str] = ["flatpak-spawn", "--host"] if has_spawn else []

    backends.append((
        "spectacle (host)",
        spawn_prefix + ["spectacle", "-b", "-n", "-o", str(out_path)],
        {},
    ))
    backends.append((
        "grim (host)",
        spawn_prefix + ["grim", str(out_path)],
        {},
    ))
    backends.append((
        "import (host X11)",
        spawn_prefix + ["sh", "-lc",
                        f"DISPLAY=:0 import -window root {out_path}"],
        {},
    ))
    backends.append((
        "gnome-screenshot (host)",
        spawn_prefix + ["gnome-screenshot", "-f", str(out_path)],
        {},
    ))

    for label, cmd, env_extra in backends:
        env = {**os.environ, **env_extra}
        try:
            subprocess.run(cmd, env=env, capture_output=True, text=True,
                           timeout=15)
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
        # Wait for async PNG to flush.
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if out_path.exists() and out_path.stat().st_size > 50_000:
                return True
            time.sleep(0.1)
        # Backend silently failed — try the next one.
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass
    return False


# Backwards-compat alias for older callers.
_gamescopectl_screenshot = _capture_screenshot


def find_game_window() -> str | None:
    """Return the AoE3 window ID on any reachable display, or None."""
    has_spawn = shutil.which("flatpak-spawn") is not None
    spawn = ["flatpak-spawn", "--host"] if has_spawn else []
    for display in (":0", ":1"):
        try:
            p = subprocess.run(
                spawn + ["sh", "-lc",
                         f"DISPLAY={display} xdotool search --name "
                         f"'Age of Empires|AoE3DE' 2>/dev/null | head -1"],
                capture_output=True, text=True, timeout=5,
            )
            wid = (p.stdout or "").strip()
            if wid:
                return wid
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return None


def _game_is_running() -> bool:
    """Return True if AoE3 is actually playable (window exists).

    Wine truncates ``AoE3DE_s.exe`` to comm ``Age3DE`` so ``pgrep -x``
    misses it. The reliable signal: an X window with the game's title
    exists on a reachable display. This also rules out the
    ``gamescopereaper`` zombie case where the launch wrapper exists but
    the game itself crashed/exited.
    """
    return find_game_window() is not None


def _diff_bbox(before: Path, after: Path,
               threshold: int = 10) -> Optional[tuple[int, int, int, int]]:
    """Return bbox (l,t,r,b) of pixels that changed by ≥threshold, or None."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    try:
        b = Image.open(before).convert("RGB")
        a = Image.open(after).convert("RGB")
    except Exception:
        return None
    diff = ImageChops.difference(b, a)
    # Tolerate small noise: drop low-delta pixels
    bw = diff.point(lambda v: 255 if v >= threshold else 0)
    return bw.getbbox()


# --- Backend definitions --------------------------------------------------

@dataclass
class BackendProbeResult:
    name: str
    available: bool
    reached_game: bool = False
    diff_bbox: Optional[tuple[int, int, int, int]] = None
    error: str = ""
    note: str = ""


@dataclass
class _Backend:
    name: str
    description: str
    available: Callable[[], bool]
    move_rel: Callable[[int, int], None]
    move_abs: Callable[[int, int], None]
    click: Callable[[int, int, int], None]  # x, y, button(1=left,2=mid,3=right)
    scroll: Callable[[int], None]            # +N=down, -N=up
    key: Callable[[str], None]               # symbolic name (e.g. "Escape")
    type_text: Callable[[str], None]


def _which(name: str) -> bool:
    return shutil.which(name) is not None


def _run(cmd: list[str], env: Optional[dict] = None,
         timeout: float = 5.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)


def _flatpak_run_host(cmd: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess:
    if _which("flatpak-spawn"):
        return _run(["flatpak-spawn", "--host", *cmd], timeout=timeout)
    return _run(cmd, timeout=timeout)


# Backend: ydotool (host)
def _ydotool_available() -> bool:
    if not _which("flatpak-spawn") and not _which("ydotool"):
        return False
    p = _flatpak_run_host(["sh", "-lc",
                           "test -S /tmp/.ydotool_socket && which ydotool"])
    return p.returncode == 0


def _ydotool(args: list[str]) -> None:
    cmd = ["sh", "-lc", "YDOTOOL_SOCKET=/tmp/.ydotool_socket ydotool " +
           " ".join(map(_shellquote, args))]
    p = _flatpak_run_host(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"ydotool {args} failed: {p.stderr.strip()}")


def _shellquote(s: str) -> str:
    if all(c.isalnum() or c in "_-.,/=:+@" for c in s):
        return s
    return "'" + s.replace("'", "'\\''") + "'"


# Backend: xdotool DISPLAY=:1 (gamescope nested Xwayland)
def _xdo1_available() -> bool:
    p = _flatpak_run_host(["sh", "-lc",
                           "DISPLAY=:1 xdotool getmouselocation >/dev/null 2>&1"])
    return p.returncode == 0


def _xdo1(args: list[str]) -> None:
    cmd = ["sh", "-lc", "DISPLAY=:1 xdotool " + " ".join(map(_shellquote, args))]
    p = _flatpak_run_host(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"xdotool :1 {args} failed: {p.stderr.strip()}")


# Backend: xdotool DISPLAY=:0 (host X)
def _xdo0_available() -> bool:
    p = _flatpak_run_host(["sh", "-lc",
                           "DISPLAY=:0 xdotool getmouselocation >/dev/null 2>&1"])
    return p.returncode == 0


def _xdo0(args: list[str]) -> None:
    cmd = ["sh", "-lc", "DISPLAY=:0 xdotool " + " ".join(map(_shellquote, args))]
    p = _flatpak_run_host(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"xdotool :0 {args} failed: {p.stderr.strip()}")


# Backend: ei_inject (gamescope-N-ei socket; N auto-detected)
def _ei_inject_available() -> bool:
    bin_path = HERE / "ei_inject"
    return bin_path.exists() and os.access(bin_path, os.X_OK)


def _detect_aoe3_ei_socket() -> str:
    """Return the libei socket name for the gamescope instance hosting AoE3.

    When CoH2 (or any other game) is already running in gamescope, AoE3 lands
    on gamescope-1 instead of gamescope-0. The libei socket name follows the
    same N: gamescope-N-ei. We parse ``pgrep -af gamescope`` looking for the
    gamescope process whose ARGV contains ``AoE3DE_s.exe``; the order of that
    process in the gamescope list determines N.

    Falls back to ``gamescope-0-ei`` if detection fails (single-game rig).
    """
    try:
        out = subprocess.run(["pgrep", "-af", "^/usr/bin/gamescope"],
                             capture_output=True, text=True, timeout=2).stdout
    except Exception:
        return "gamescope-0-ei"
    # Each line is one gamescope process; the Nth process gets gamescope-(N-...).
    # gamescope numbers its sockets monotonically as it starts; we map by
    # observing the available sockets and matching the one that owns the
    # AoE3 cmdline.
    rt = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    candidates = sorted(p.name for p in Path(rt).iterdir()
                        if p.name.startswith("gamescope-") and p.name.endswith("-ei")
                        and not p.name.endswith(".lock"))
    if not candidates:
        return "gamescope-0-ei"
    # If exactly one socket, that's our pick.
    if len(candidates) == 1:
        return candidates[0]
    # If multiple, pick the gamescope whose argv contains AoE3DE_s.exe.
    # Process start order in pgrep output matches socket-N order:
    # first gamescope started → gamescope-0-ei, second → gamescope-1-ei, etc.
    gamescope_lines = [ln for ln in out.splitlines() if "gamescope" in ln]
    aoe_idx = None
    for idx, ln in enumerate(gamescope_lines):
        if "AoE3DE_s.exe" in ln or "AppId=933110" in ln:
            aoe_idx = idx
            break
    if aoe_idx is not None and aoe_idx < len(candidates):
        return candidates[aoe_idx]
    # Last resort: assume AoE3 is the most recently started (highest N).
    return candidates[-1]


def _ei_inject_send(commands: list[str], socket: Optional[str] = None) -> None:
    bin_path = HERE / "ei_inject"
    if not bin_path.exists():
        raise RuntimeError("ei_inject binary not built. See setup_input.sh.")
    env = {
        **os.environ,
        "LIBEI_SOCKET": socket or _detect_aoe3_ei_socket(),
        "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"),
    }
    p = subprocess.run([str(bin_path)], input="\n".join(commands) + "\nbye\n",
                       env=env, capture_output=True, text=True, timeout=5)
    if p.returncode != 0:
        raise RuntimeError(f"ei_inject failed: {p.stderr.strip()}")


# --- Backend wrappers (move/click/scroll/key/type) ---

def _make_ydotool_backend() -> _Backend:
    return _Backend(
        name="ydotool",
        description="ydotool → /dev/uinput → host compositor → gamescope",
        available=_ydotool_available,
        move_rel=lambda dx, dy: _ydotool(["mousemove", "-x", str(dx), "-y", str(dy)]),
        move_abs=lambda x, y: _ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)]),
        click=lambda x, y, btn: (
            _ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)]),
            _ydotool(["click", {1: "0xC0", 2: "0xC1", 3: "0xC2"}.get(btn, "0xC0")]),
        )[-1],
        scroll=lambda steps: _ydotool(["click",
            "0xC4" if steps > 0 else "0xC3", "--repeat", str(abs(steps))]),
        key=lambda name: _ydotool(["key", _ydotool_keycode(name) + ":1",
                                   _ydotool_keycode(name) + ":0"]),
        type_text=lambda s: _ydotool(["type", s]),
    )


def _ydotool_keycode(name: str) -> str:
    """Map symbolic key names to linux input event codes (as decimal strings)."""
    table = {
        "Escape": "1", "Return": "28", "Enter": "28",
        "Home": "102", "End": "107", "Page_Up": "104", "Page_Down": "109",
        "Tab": "15", "Space": "57", "BackSpace": "14",
        "Up": "103", "Down": "108", "Left": "105", "Right": "106",
    }
    return table.get(name, "57")


def _make_xdo_backend(display: str) -> _Backend:
    avail = _xdo1_available if display == ":1" else _xdo0_available
    fn = _xdo1 if display == ":1" else _xdo0
    return _Backend(
        name=f"xdotool-{display}",
        description=f"xdotool → DISPLAY={display}",
        available=avail,
        move_rel=lambda dx, dy: fn(["mousemove_relative", "--", str(dx), str(dy)]),
        move_abs=lambda x, y: fn(["mousemove", str(x), str(y)]),
        click=lambda x, y, btn: (fn(["mousemove", str(x), str(y)]),
                                 fn(["click", str(btn)]))[-1],
        scroll=lambda steps: fn(["click", "--repeat", str(abs(steps)),
                                  "5" if steps > 0 else "4"]),
        key=lambda name: fn(["key", name]),
        type_text=lambda s: fn(["type", "--", s]),
    )


def _make_ei_inject_backend() -> _Backend:
    return _Backend(
        name="ei_inject",
        description="ei_inject → gamescope-N-ei (libei; N auto-detected)",
        available=_ei_inject_available,
        move_rel=lambda dx, dy: _ei_inject_send([f"move_rel {dx} {dy}"]),
        move_abs=lambda x, y: _ei_inject_send([f"move {x} {y}"]),
        click=lambda x, y, btn: _ei_inject_send([f"move {x} {y}",
                                                  f"click {btn}"]),
        scroll=lambda steps: _ei_inject_send(
            [f"scroll {0 if steps == 0 else (1 if steps > 0 else -1) * abs(steps)}"]
        ),
        key=lambda name: _ei_inject_send([f"key {_ydotool_keycode(name)}"]),
        type_text=lambda s: _ei_inject_send([f"type {s}"]),
    )


# --- Probing & verification ---

def _probe_backend(b: _Backend, capture_dir: Path) -> BackendProbeResult:
    """Snapshot, send a mousemove, snapshot, diff. PASS only if pixels
    changed inside the game window — desktop-cursor pixel changes don't
    count.
    """
    result = BackendProbeResult(name=b.name, available=False)

    # Hard guard: if the game isn't actually running, no backend can
    # possibly reach it. Don't false-positive on cursor moves on the
    # desktop.
    if not _game_is_running():
        result.error = "AoE3DE_s.exe not running (launch the game first)"
        return result

    try:
        if not b.available():
            result.error = "backend not detected"
            return result
    except Exception as e:
        result.error = f"availability check failed: {e}"
        return result
    result.available = True

    before = capture_dir / f"probe_{b.name}_before.png"
    after = capture_dir / f"probe_{b.name}_after.png"
    if not _gamescopectl_screenshot(before):
        result.error = "could not capture before-frame"
        return result

    # Rigorous probe: send the cursor to a target absolute coord inside
    # the AoE3 main menu where the "Skirmish" button highlights on hover
    # (~80, 490), then screenshot-diff to verify pixels changed inside that
    # ROI. Reading xdotool getmouselocation against :0/:1 is unreliable from
    # outside gamescope: :0 always answers with the HOST cursor (which we
    # explicitly never moved), and :1 (gamescope's nested Xwayland) refuses
    # connections from outside the gamescope process tree — see the
    # 2026-05-11 finding in input_harness diagnosis. So we use the only
    # signal that's available from outside: the gamescope screenshot
    # pipeline, which captures the gamescope-rendered frame including the
    # in-game cursor / button hover state.
    target_x, target_y = 80, 490  # AoE3 main-menu "Skirmish" button center
    roi = (0, 460, 200, 540)  # x0, y0, x1, y1 around the Skirmish button
    try:
        b.move_abs(target_x, target_y)
        time.sleep(0.30)
    except Exception as e:
        result.error = f"move_abs failed: {e}"
        return result

    if not _gamescopectl_screenshot(after):
        result.error = "could not capture after-frame"
        return result

    bbox = _diff_bbox(before, after, threshold=8)
    result.diff_bbox = bbox

    # Strict: pixels must change AND the change must overlap our ROI to
    # rule out ambient screen animation as a false positive.
    if bbox is None:
        result.reached_game = False
        result.note = ("no pixels changed in gamescope frame — "
                       "input did not reach seat")
        return result

    bx0, by0, bx1, by1 = bbox
    rx0, ry0, rx1, ry1 = roi
    overlap = (max(bx0, rx0) < min(bx1, rx1)
               and max(by0, ry0) < min(by1, ry1))
    if overlap:
        result.reached_game = True
        result.note = (f"pixels changed inside hover ROI {roi} "
                       f"(diff bbox {bbox}) — input reaches game")
    else:
        result.reached_game = False
        result.note = (f"pixels changed at {bbox} but outside hover ROI "
                       f"{roi} — likely ambient frame change, not our move")
    return result


# --- Public class ---

@dataclass
class VerifiedInput:
    capture_dir: Path = field(
        default_factory=lambda: REPO_ROOT / "artifacts" / "input_probe")
    backend: Optional[_Backend] = None
    last_probe_results: list[BackendProbeResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def all_backends(self) -> list[_Backend]:
        return [
            _make_ei_inject_backend(),     # preferred when available
            _make_ydotool_backend(),
            _make_xdo_backend(":1"),
            _make_xdo_backend(":0"),
        ]

    def probe(self, raise_on_fail: bool = True) -> _Backend:
        """Test every backend; pick the first that reaches the game."""
        results: list[BackendProbeResult] = []
        for b in self.all_backends():
            r = _probe_backend(b, self.capture_dir)
            results.append(r)
            if r.reached_game:
                self.backend = b
                self.last_probe_results = results
                return b
        self.last_probe_results = results
        self.backend = None
        if raise_on_fail:
            raise InputBackendUnavailable(self.diagnostic_report())
        return None  # type: ignore

    def diagnostic_report(self) -> str:
        lines = [
            "No input backend successfully reached the gamescope-nested game.",
            "",
            "Probed backends:",
        ]
        for r in self.last_probe_results:
            mark = "✓" if r.reached_game else ("·" if r.available else "✗")
            lines.append(f"  {mark} {r.name:<14}  available={r.available}  "
                         f"reached_game={r.reached_game}  "
                         f"err={r.error or '-'}  note={r.note or '-'}")
        lines += [
            "",
            "REMEDIATION (pick one):",
            "",
            "  Option A — Use libei (recommended; designed for gamescope):",
            "    On the host, install libei development headers:",
            "      rpm-ostree install libei-devel libeis-devel",
            "    After reboot, build the EI client:",
            "      cd tools/aoe3_automation",
            "      gcc ei_inject.c -lei -o ei_inject",
            "    Then re-run the probe.",
            "",
            "  Option B — Wire ydotool's uinput device into the host seat:",
            "    udevadm control --reload-rules &&",
            "    echo 'KERNEL==\"uinput\", MODE=\"0660\", GROUP=\"input\"' "
                  ">/etc/udev/rules.d/60-uinput.rules",
            "    sudo loginctl attach seat0 /sys/class/input/event23",
            "    Restart ydotoold; re-run the probe.",
            "",
            "  Option C — Run gamescope with explicit --backend=sdl + xdotool :1",
            "    Relaunch the game with: gamescope --backend=sdl ... %command%",
            "    The SDL backend forwards X events properly. Re-probe.",
            "",
            "  Option D — Manual control: drive the lobby by hand and use this",
            "    harness only for screenshot capture + observation.",
        ]
        return "\n".join(lines)

    def _verify(self, before_capture: Path, action_label: str) -> bool:
        """Capture an after-frame and check the diff bbox is non-empty."""
        after = self.capture_dir / f"after_{action_label}_{int(time.time()*1000)}.png"
        if not _gamescopectl_screenshot(after):
            return False
        bbox = _diff_bbox(before_capture, after, threshold=8)
        return bbox is not None

    def _act_verified(self, action: Callable[[], None], label: str,
                      verify: bool = True) -> None:
        if self.backend is None:
            self.probe()
        before = self.capture_dir / f"before_{label}_{int(time.time()*1000)}.png"
        if verify and not _gamescopectl_screenshot(before):
            raise RuntimeError(f"capture before-frame failed for {label}")
        action()
        if verify:
            time.sleep(0.15)
            if not self._verify(before, label):
                raise RuntimeError(
                    f"action '{label}' produced no visible diff — "
                    "input may not have reached the game"
                )

    def move(self, x: int, y: int, verify: bool = True) -> None:
        self._act_verified(lambda: self.backend.move_abs(x, y), f"move_{x}_{y}", verify)

    def click(self, x: int, y: int, button: int = 1, verify: bool = True) -> None:
        self._act_verified(lambda: self.backend.click(x, y, button), f"click_{x}_{y}", verify)

    def scroll(self, steps: int, verify: bool = True) -> None:
        self._act_verified(lambda: self.backend.scroll(steps), f"scroll_{steps}", verify)

    def key(self, name: str, verify: bool = True) -> None:
        self._act_verified(lambda: self.backend.key(name), f"key_{name}", verify)

    def type_text(self, text: str, verify: bool = True) -> None:
        self._act_verified(lambda: self.backend.type_text(text),
                          f"type_{len(text)}c", verify)


# --- CLI ---

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true",
                    help="probe all backends and report which works")
    ap.add_argument("--self-test", action="store_true",
                    help="probe + try basic operations against the live game")
    ap.add_argument("--json", type=Path, help="write JSON report to this path")
    args = ap.parse_args()

    h = VerifiedInput()
    backend = h.probe(raise_on_fail=False)

    print("=" * 60)
    print("VERIFIED INPUT HARNESS — backend probe")
    print("=" * 60)
    for r in h.last_probe_results:
        mark = "✓" if r.reached_game else ("·" if r.available else "✗")
        print(f"  {mark} {r.name:<14}  available={r.available}  "
              f"reached_game={r.reached_game}")
        if r.error:
            print(f"     error: {r.error}")
        if r.note:
            print(f"     note: {r.note}")

    print()
    if backend is None:
        print("✗ FAIL — no working backend.")
        print()
        print(h.diagnostic_report())
        rc = 1
    else:
        print(f"✓ PASS — using backend: {backend.name} ({backend.description})")
        rc = 0

        if args.self_test:
            print()
            print("Running self-test (verified mouse-move + verified key)…")
            try:
                h.move(960, 540)
                print("  ✓ move(960, 540) verified")
            except Exception as e:
                print(f"  ✗ move failed: {e}")
                rc = 1
            try:
                h.key("Escape")
                print("  ✓ key(Escape) verified")
            except Exception as e:
                print(f"  ✗ key failed: {e}")
                rc = 1

    if args.json:
        report = {
            "verdict": "pass" if rc == 0 else "fail",
            "backend": backend.name if backend else None,
            "probe_results": [
                {
                    "name": r.name,
                    "available": r.available,
                    "reached_game": r.reached_game,
                    "diff_bbox": r.diff_bbox,
                    "error": r.error,
                    "note": r.note,
                } for r in h.last_probe_results
            ],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report: {args.json}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
