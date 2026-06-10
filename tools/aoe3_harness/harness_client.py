"""harness_client.py — Python client for the AOE3DEHarness control socket.

The AOE3DEHarness binary (ASAP-Australia/AOE-3-DE-Harness, a fork of Valve's
gamescope) exposes a Unix-domain socket when launched with
``--harness-mode --harness-socket <path>``.  This module provides a high-level
client with per-verb methods and an exception hierarchy, replacing the legacy
Wine named-pipe approach in ``dll_client.py``.

Wire protocol:
    - All commands are ``\\n``-terminated plain text lines.
    - Each connection may send multiple commands sequentially.
    - Server responds with one ``\\n``-terminated line per command.
    - Success responses begin with ``OK`` (possibly followed by payload).
    - Error responses: ``ERR <CODE> [detail ...]``
    - STATE response: ``STATE pid=<N> uptime=<N>ms w=<N> h=<N>``
    - SCREENSHOT success: ``OK path=<path> bytes=<N>``

Usage::

    with HarnessClient("/run/user/1000/AOE3DEHarness.sock") as client:
        info = client.state()
        print(info.pid, info.internal_w, info.internal_h)
        client.key(0x57)          # tap W
        client.click(960, 540)
        result = client.screenshot(Path("/tmp/frame.png"))

See also:
    tools/aoe3_harness/harness_launch.py  — launcher that spawns AOE3DEHarness
                                            and returns a connected HarnessClient
    tools/aoe3_harness/vk.py              — Win32 VK code constants

Design decisions:
    - Explicit per-operation socket timeout prevents silent hangs.
    - Exponential backoff starts at 50 ms (not 500 ms) for fast first-connect.
    - recv() is always capped at 4096 bytes per line (line protocol).
    - Context-manager interface guarantees clean teardown on exceptions.
    - Reconnect helper re-establishes the connection after a mid-session drop.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

__all__ = [
    "HarnessClient",
    "HarnessState",
    "ScreenshotResult",
    "HarnessError",
    "HarnessConnectionError",
    "HarnessProtocolError",
    "HarnessCommandError",
    "HarnessTimeoutError",
    "HarnessShuttingDownError",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarnessState:
    """Snapshot of the AOE3DEHarness compositor state.

    Attributes:
        pid:        PID of the AOE3DEHarness process.
        uptime_ms:  Milliseconds since AOE3DEHarness started.
        internal_w: Internal (output) resolution width in pixels.
        internal_h: Internal (output) resolution height in pixels.
        ready:      1 when the inner game window has been mapped and has
                    committed its first composited frame (i.e. the game is
                    past the splash screen and on the main menu); 0 otherwise.
        inner_pid:  PID of the inner game (Wine/Proton) window process, or 0
                    if the game window has not composited a frame yet.
        inner_alive: 1 when ``inner_pid`` is non-zero and the process is still
                    alive (``kill(pid, 0)`` succeeds); 0 if it has exited.
                    ``inner_alive=0`` with ``inner_pid!=0`` flags a game crash.
    """

    pid: int
    uptime_ms: int
    internal_w: int
    internal_h: int
    ready: int = 0
    inner_pid: int = 0
    inner_alive: int = 0


@dataclass(frozen=True)
class ScreenshotResult:
    """Result from a successful SCREENSHOT command.

    Attributes:
        path:          Host-filesystem path where the PNG was written.
        bytes_written: Number of bytes written to the file.
    """

    path: Path
    bytes_written: int


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class HarnessError(RuntimeError):
    """Base class for all AOE3DEHarness client errors."""


class HarnessConnectionError(HarnessError):
    """Raised when the socket cannot be connected or drops unexpectedly."""


class HarnessProtocolError(HarnessError):
    """Raised when the server returns a response that cannot be parsed."""


class HarnessCommandError(HarnessError):
    """Raised when the server returns ``ERR <code> [detail]`` for a verb.

    Attributes:
        verb:   The command verb that triggered the error (e.g. ``"SCREENSHOT"``).
        code:   The error code token from the server (e.g. ``"TIMEOUT"``).
        detail: Optional free-text detail from the server.
    """

    def __init__(self, verb: str, code: str, detail: str = "") -> None:
        self.verb = verb
        self.code = code
        self.detail = detail
        super().__init__(
            f"{verb} failed with {code}" + (f": {detail}" if detail else "")
        )


class HarnessTimeoutError(HarnessError):
    """Raised when a socket operation exceeds its configured timeout."""


class HarnessShuttingDownError(HarnessCommandError):
    """Raised when the server returns ``ERR HARNESS_SHUTTING_DOWN``."""

    def __init__(self, verb: str = "", detail: str = "") -> None:
        super().__init__(verb, "HARNESS_SHUTTING_DOWN", detail)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# Maximum bytes read per line; the protocol is line-based, so this is safe.
_LINE_MAX = 4096


class HarnessClient:
    """Client for the AOE3DEHarness Unix-domain control socket.

    Connects to the socket exposed by ``AOE3DEHarness --harness-mode
    --harness-socket <path>`` and provides per-verb methods for every
    supported command.

    Args:
        socket_path: Path to the Unix-domain socket file.
        timeout:     Per-operation socket timeout in seconds (default: 10.0).

    Example::

        with HarnessClient("/run/user/1000/AOE3DEHarness.sock") as client:
            state = client.state()
            client.key(0x57)
            client.click(960, 540)
    """

    def __init__(
        self,
        socket_path: str | Path,
        timeout: float = 10.0,
    ) -> None:
        self._socket_path = Path(socket_path)
        self._timeout = timeout
        self._sock: Optional[socket.socket] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self, timeout: float = 30.0) -> None:
        """Connect to the AOE3DEHarness socket with exponential backoff.

        Attempts connection repeatedly until either the socket is available
        or ``timeout`` seconds have elapsed.  First retry fires after 50 ms;
        subsequent delays double, capped at 4 s.

        Args:
            timeout: Wall-clock seconds before giving up (default: 30.0).

        Raises:
            HarnessConnectionError: if the socket is not reachable within
                                    *timeout* seconds.
        """
        deadline = time.monotonic() + timeout
        delay = 0.05  # 50 ms first retry
        last_exc: Optional[Exception] = None

        while True:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self._timeout)
                sock.connect(str(self._socket_path))
                self._sock = sock
                return
            except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
                last_exc = exc
                try:
                    sock.close()
                except OSError:
                    pass

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sleep_for = min(delay, remaining)
            time.sleep(sleep_for)
            delay = min(delay * 2, 4.0)

        raise HarnessConnectionError(
            f"Could not connect to {self._socket_path} within {timeout}s: {last_exc}"
        )

    def reconnect(self, timeout: float = 30.0) -> None:
        """Close any existing socket and reconnect.

        Useful after a mid-session disconnect caused by a compositor stutter
        or a brief AOE3DEHarness restart.

        Args:
            timeout: Wall-clock seconds before giving up (default: 30.0).

        Raises:
            HarnessConnectionError: if the reconnect fails.
        """
        self.close()
        self.connect(timeout=timeout)

    def close(self) -> None:
        """Close the socket connection.  Safe to call multiple times."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def __enter__(self) -> "HarnessClient":
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def send_raw(self, line: str) -> str:
        """Send one command line and return the single-line response.

        Both the sent line and the returned line are without the ``\\n``
        terminator.  Reads are capped at ``_LINE_MAX`` bytes.

        Args:
            line: Command string without ``\\n`` terminator.

        Returns:
            Response string without ``\\n`` terminator.

        Raises:
            HarnessConnectionError: if not connected or the server closes
                                    the connection mid-command.
            HarnessTimeoutError:    if the socket operation times out.
        """
        if self._sock is None:
            raise HarnessConnectionError(
                "Not connected; call connect() first."
            )
        try:
            self._sock.sendall((line + "\n").encode("ascii"))
            buf = b""
            while True:
                if len(buf) >= _LINE_MAX:
                    raise HarnessProtocolError(
                        f"Response line exceeded {_LINE_MAX} bytes without \\n"
                    )
                chunk = self._sock.recv(_LINE_MAX - len(buf))
                if not chunk:
                    raise HarnessConnectionError(
                        "AOE3DEHarness closed the connection unexpectedly."
                    )
                buf += chunk
                if b"\n" in buf:
                    break
            return buf.split(b"\n", 1)[0].decode("ascii", errors="replace").strip()
        except socket.timeout as exc:
            raise HarnessTimeoutError(
                f"Socket timed out after {self._timeout}s on command: {line!r}"
            ) from exc
        except HarnessError:
            raise
        except OSError as exc:
            raise HarnessConnectionError(
                f"Socket error during command {line!r}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_ok(verb: str, resp: str) -> str:
        """Assert *resp* starts with OK and return the payload after it.

        Raises:
            HarnessShuttingDownError: if the response is HARNESS_SHUTTING_DOWN.
            HarnessCommandError:      if the response is an ERR.
            HarnessProtocolError:     if the response is unrecognised.
        """
        if resp.startswith("OK"):
            return resp[2:].strip()
        HarnessClient._raise_err(verb, resp)
        return ""  # unreachable; satisfies type checker

    @staticmethod
    def _raise_err(verb: str, resp: str) -> None:
        """Parse an ERR response and raise the appropriate exception.

        Raises:
            HarnessShuttingDownError: for HARNESS_SHUTTING_DOWN.
            HarnessCommandError:      for all other ERR codes.
            HarnessProtocolError:     if the response is not ERR either.
        """
        if resp.startswith("ERR"):
            parts = resp[3:].strip().split(None, 1)
            code = parts[0] if parts else "UNKNOWN"
            detail = parts[1] if len(parts) > 1 else ""
            if code == "HARNESS_SHUTTING_DOWN":
                raise HarnessShuttingDownError(verb, detail)
            raise HarnessCommandError(verb, code, detail)
        raise HarnessProtocolError(
            f"Unexpected response for {verb}: {resp!r}"
        )

    # ------------------------------------------------------------------
    # Public command API
    # ------------------------------------------------------------------

    def state(self) -> HarnessState:
        """Query the compositor state.

        Sends ``STATE`` and parses the response into a :class:`HarnessState`.

        Wire response:
            ``OK pid=<N> uptime_ms=<N> internal_w=<N> internal_h=<N> ready=<0|1>``

        ``ready=1`` means the inner game window has been mapped and has
        committed its first composited frame (i.e. past the splash screen).
        ``ready=0`` means no client window is compositing yet.

        Returns:
            A :class:`HarnessState` dataclass.

        Raises:
            HarnessProtocolError:   if the response cannot be parsed.
            HarnessCommandError:    if the server returns an error.
            HarnessConnectionError: on socket failure.
        """
        resp = self.send_raw("STATE")
        payload = self._require_ok("STATE", resp)
        fields: dict[str, str] = {}
        for token in payload.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        try:
            pid = int(fields["pid"])
            uptime_ms = int(fields["uptime_ms"])
            internal_w = int(fields["internal_w"])
            internal_h = int(fields["internal_h"])
        except (KeyError, ValueError) as exc:
            raise HarnessProtocolError(
                f"Cannot parse STATE response: {resp!r}"
            ) from exc
        ready = int(fields.get("ready", "0"))
        inner_pid = int(fields.get("inner_pid", "0"))
        inner_alive = int(fields.get("inner_alive", "0"))
        return HarnessState(
            pid=pid,
            uptime_ms=uptime_ms,
            internal_w=internal_w,
            internal_h=internal_h,
            ready=ready,
            inner_pid=inner_pid,
            inner_alive=inner_alive,
        )

    def wait_for_ready(self, timeout: float = 60.0) -> HarnessState:
        """Poll STATE until ``ready=1`` or *timeout* seconds elapse.

        The harness sets ``ready=1`` once the inner game window has been
        mapped and has committed its first composited frame.  Polling every
        0.5 s is sufficient to detect this transition without busy-waiting.

        Args:
            timeout: Wall-clock seconds to wait before raising (default: 60.0).

        Returns:
            The :class:`HarnessState` snapshot at the moment ``ready=1`` was
            observed.

        Raises:
            HarnessTimeoutError:    if ``ready`` has not become 1 within
                                    *timeout* seconds.
            HarnessConnectionError: on socket failure.
            HarnessProtocolError:   if STATE cannot be parsed.
        """
        deadline = time.monotonic() + timeout
        while True:
            s = self.state()
            if s.ready:
                return s
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HarnessTimeoutError(
                    f"Timed out waiting for harness ready=1 after {timeout}s "
                    f"(last uptime_ms={s.uptime_ms})"
                )
            time.sleep(min(0.5, remaining))

    def key(self, vk: int) -> None:
        """Inject a key tap (KEY_DOWN + gap + KEY_UP) for a virtual key code.

        Args:
            vk: Win32 virtual key code (0x01–0xFF).

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        resp = self.send_raw(f"KEY {vk:#04x}")
        self._require_ok("KEY", resp)

    def key_down(self, vk: int) -> None:
        """Inject a key-down event for a virtual key code.

        Args:
            vk: Win32 virtual key code (0x01–0xFF).

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        resp = self.send_raw(f"KEY_DOWN {vk:#04x}")
        self._require_ok("KEY_DOWN", resp)

    def key_up(self, vk: int) -> None:
        """Inject a key-up event for a virtual key code.

        Args:
            vk: Win32 virtual key code (0x01–0xFF).

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        resp = self.send_raw(f"KEY_UP {vk:#04x}")
        self._require_ok("KEY_UP", resp)

    def move(self, x: int, y: int) -> None:
        """Inject a mouse-move to compositor coordinates (no click).

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        resp = self.send_raw(f"MOVE {x} {y}")
        self._require_ok("MOVE", resp)

    def click(self, x: int, y: int, button: int = 1) -> None:
        """Inject a mouse click at compositor coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            button: Mouse button index — 1=left (default), 2=middle, 3=right.

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        if button == 1:
            resp = self.send_raw(f"CLICK {x} {y}")
        else:
            resp = self.send_raw(f"CLICK {x} {y} {button}")
        self._require_ok("CLICK", resp)

    def rclick(self, x: int, y: int) -> None:
        """Inject a right-click at compositor coordinates.

        In an RTS this is the primary command verb: move/rally/gather, and it
        cancels a pending building-placement ghost on open ground.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        resp = self.send_raw(f"RCLICK {x} {y}")
        self._require_ok("RCLICK", resp)

    def button(self, action: str, button: int = 1) -> None:
        """Press or release a mouse button at the current pointer position.

        Pair :meth:`move` with ``button("down")`` / ``button("up")`` to build
        custom gestures. For a simple click-drag prefer :meth:`drag`.

        Args:
            action: "down" or "up" (case-insensitive).
            button: Mouse button index — 1=left (default), 2=middle, 3=right.

        Raises:
            ValueError:             if action is not "down"/"up".
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        act = action.strip().upper()
        if act not in ("DOWN", "UP"):
            raise ValueError(f"button action must be 'down' or 'up', got {action!r}")
        resp = self.send_raw(f"BUTTON {act} {button}")
        self._require_ok("BUTTON", resp)

    def drag(self, x1: int, y1: int, x2: int, y2: int, button: int = 1) -> None:
        """Press at (x1,y1), warp to (x2,y2), then release — a click-drag.

        With button=1 this is a box-select (drag-select units); with button=3
        it is a right-drag.

        Args:
            x1, y1: Source pixel coordinate (press point).
            x2, y2: Destination pixel coordinate (release point).
            button: Mouse button index — 1=left (default), 2=middle, 3=right.

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        if button == 1:
            resp = self.send_raw(f"DRAG {x1} {y1} {x2} {y2}")
        else:
            resp = self.send_raw(f"DRAG {x1} {y1} {x2} {y2} {button}")
        self._require_ok("DRAG", resp)

    def screenshot(self, host_path: str | Path) -> ScreenshotResult:
        """Request a screenshot saved to the given host-filesystem path.

        The AOE3DEHarness compositor writes the current frame as PNG.

        Args:
            host_path: Destination path on the host filesystem.

        Returns:
            :class:`ScreenshotResult` with the written path and byte count.

        Raises:
            HarnessShuttingDownError: if the server is shutting down.
            HarnessCommandError:      on any other server error
                                      (TIMEOUT, FAILED, INVALID_PATH).
            HarnessConnectionError:   on socket failure.
            HarnessProtocolError:     if the OK response cannot be parsed.
        """
        resp = self.send_raw(f"SCREENSHOT {host_path}")
        payload = self._require_ok("SCREENSHOT", resp)
        # The server may reply in either of two shapes:
        #   key=value form:  "path=<path> bytes=<N>"
        #   positional form: "<path> <bytes>"
        fields: dict[str, str] = {}
        for token in payload.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        try:
            if "path" in fields:
                written_path = Path(fields["path"])
                bytes_written = int(fields["bytes"])
            else:
                # Positional fallback: trailing integer is the byte count,
                # everything before it is the (possibly space-free) path.
                parts = payload.split()
                if len(parts) >= 2 and parts[-1].isdigit():
                    written_path = Path(" ".join(parts[:-1]))
                    bytes_written = int(parts[-1])
                else:
                    # Only a path was returned; stat it for the byte count.
                    written_path = Path(payload.strip())
                    bytes_written = (
                        written_path.stat().st_size
                        if written_path.exists()
                        else 0
                    )
        except (KeyError, ValueError, OSError) as exc:
            raise HarnessProtocolError(
                f"Cannot parse SCREENSHOT OK response: {resp!r}"
            ) from exc
        return ScreenshotResult(path=written_path, bytes_written=bytes_written)

    def wheel(self, dx: float, dy: float) -> None:
        """Inject a smooth-scroll delta at the current pointer position.

        Sign convention (matches xdotool): dy > 0 = scroll UP (button 4);
        dy < 0 = scroll DOWN (button 5).  Move the pointer first with
        :meth:`move` before calling this.

        Args:
            dx: Horizontal scroll delta (typically 0.0).
            dy: Vertical scroll delta.  Positive = up, negative = down.
                Use integer ticks (e.g. ``-1.0`` per notch) for reliable
                discrete scrolling inside Wine/AoE3.

        Raises:
            HarnessCommandError:    on server error.
            HarnessConnectionError: on socket failure.
        """
        resp = self.send_raw(f"WHEEL {dx} {dy}")
        self._require_ok("WHEEL", resp)

    # ------------------------------------------------------------------
    # Selection / input helpers (DCLICK, MCLICK, CHORD, TYPE, SLEEP)
    # ------------------------------------------------------------------

    def dclick(self, x: int, y: int, button: int = 1) -> None:
        """Double-click at (x,y) within the system double-click interval.

        In AoE3 a left double-click selects all on-screen units of the
        clicked unit's type.

        Args:
            x, y:   Pixel coordinate.
            button: Mouse button index — 1=left (default), 2=middle, 3=right.
        """
        resp = self.send_raw(f"DCLICK {x} {y} {button}")
        self._require_ok("DCLICK", resp)

    def mclick(self, x: int, y: int, mod: str, button: int = 1) -> None:
        """Modifier-click: hold ``mod`` while clicking at (x,y).

        Shift-click adds to the current selection; Ctrl-click selects all of
        the unit's type.

        Args:
            x, y:   Pixel coordinate.
            mod:    Modifier name — "shift", "ctrl"/"control", or "alt".
            button: Mouse button index — 1=left (default), 2=middle, 3=right.
        """
        resp = self.send_raw(f"MCLICK {x} {y} {mod} {button}")
        self._require_ok("MCLICK", resp)

    def chord(self, vks: list[int]) -> None:
        """Press a key chord: all VKs down in order, released in reverse.

        Example: ``chord([0x11, 0x10, 0x31])`` for Ctrl+Shift+1 (assign a
        control group). Up to 16 keys.

        Args:
            vks: List of Win32 virtual-key codes.

        Raises:
            ValueError:          if the list is empty or longer than 16.
            HarnessCommandError: if any VK has no evdev mapping (no key is
                                 left stuck down in that case).
        """
        if not vks:
            raise ValueError("chord() requires at least one VK")
        if len(vks) > 16:
            raise ValueError("chord() accepts at most 16 keys")
        args = " ".join(f"{vk:#04x}" for vk in vks)
        resp = self.send_raw(f"CHORD {args}")
        self._require_ok("CHORD", resp)

    def type_text(self, text: str) -> None:
        """Type an ASCII string as synthetic keystrokes (Shift applied as needed).

        Letters, digits, space and common US-ANSI punctuation are supported;
        unmappable characters are skipped. Used for chat / cheat entry.

        Args:
            text: The string to type. Must not contain a newline.

        Raises:
            ValueError:          if *text* contains a newline (would break the
                                 line protocol).
            HarnessCommandError: on server error.
        """
        if "\n" in text:
            raise ValueError("type_text() text must not contain a newline")
        resp = self.send_raw(f"TYPE {text}")
        self._require_ok("TYPE", resp)

    def sleep(self, ms: int) -> None:
        """Ask the server to sleep for *ms* milliseconds (clamped to 10000).

        Useful inside a pipelined command sequence to pace actions without a
        Python-side round trip.

        Args:
            ms: Milliseconds to sleep (server clamps to a 10 s maximum).
        """
        resp = self.send_raw(f"SLEEP {int(ms)}")
        self._require_ok("SLEEP", resp)

    # ------------------------------------------------------------------
    # Server-side pixel / region readback (PIXEL, REGION_STAT, REGION_HASH)
    # ------------------------------------------------------------------

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        """Read one composited pixel; returns an ``(r, g, b)`` tuple (0-255).

        Args:
            x, y: Pixel coordinate in the logical 1920x1080 space.

        Returns:
            ``(r, g, b)`` channel values.
        """
        resp = self.send_raw(f"PIXEL {x} {y}")
        payload = self._require_ok("PIXEL", resp)
        f = self._parse_fields(payload)
        try:
            return (int(f["r"]), int(f["g"]), int(f["b"]))
        except (KeyError, ValueError) as exc:
            raise HarnessProtocolError(
                f"Cannot parse PIXEL response: {resp!r}"
            ) from exc

    def region_stat(
        self, x: int, y: int, w: int, h: int
    ) -> dict[str, int]:
        """Region statistics over RGB channels of every pixel in (x,y,w,h).

        Returns a dict with keys:
            ``sum``     — sum of (r+g+b) across all pixels.
            ``mean``    — average channel value (0-255).
            ``nonzero`` — count of pixels with any channel > 0.
            ``bright``  — count of pixels with (r+g+b) > 384.
        """
        resp = self.send_raw(f"REGION_STAT {x} {y} {w} {h}")
        payload = self._require_ok("REGION_STAT", resp)
        f = self._parse_fields(payload)
        try:
            return {
                "sum": int(f["sum"]),
                "mean": int(f["mean"]),
                "nonzero": int(f["nonzero"]),
                "bright": int(f["bright"]),
            }
        except (KeyError, ValueError) as exc:
            raise HarnessProtocolError(
                f"Cannot parse REGION_STAT response: {resp!r}"
            ) from exc

    def region_hash(self, x: int, y: int, w: int, h: int) -> int:
        """FNV-1a 64-bit hash over the region's decoded RGB bytes.

        Two captures of an unchanged region hash equal; any pixel change
        flips the hash. Returns the hash as an ``int``.
        """
        resp = self.send_raw(f"REGION_HASH {x} {y} {w} {h}")
        payload = self._require_ok("REGION_HASH", resp)
        f = self._parse_fields(payload)
        try:
            return int(f["hash"], 16)
        except (KeyError, ValueError) as exc:
            raise HarnessProtocolError(
                f"Cannot parse REGION_HASH response: {resp!r}"
            ) from exc

    def _wait_region(
        self,
        verb: str,
        x: int,
        y: int,
        w: int,
        h: int,
        timeout_ms: int,
        stable_ms: Optional[int],
    ) -> tuple[bool, int]:
        """Shared WAIT_STABLE / WAIT_CHANGE implementation.

        Returns ``(success, waited_ms)``. On timeout ``success`` is False.
        Uses a socket timeout long enough to cover the server-side wait.
        The server polls internally every 100 ms (not client-configurable).
        """
        parts = [verb, str(x), str(y), str(w), str(h), str(int(timeout_ms))]
        if stable_ms is not None:
            parts.append(str(int(stable_ms)))
        # Ensure the socket read outlives the server-side wait loop.
        prev = self._timeout
        self._set_sock_timeout(max(self._timeout, timeout_ms / 1000.0 + 5.0))
        try:
            resp = self.send_raw(" ".join(parts))
        finally:
            self._set_sock_timeout(prev)
        if resp.startswith("OK"):
            payload = resp[2:].strip()
            f = self._parse_fields(payload)
            return (True, int(f.get("waited", "0")))
        # ERR TIMEOUT waited=.. is an expected (non-exceptional) outcome.
        if resp.startswith("ERR"):
            parts2 = resp[3:].strip().split(None, 1)
            code = parts2[0] if parts2 else ""
            if code == "TIMEOUT":
                f = self._parse_fields(parts2[1] if len(parts2) > 1 else "")
                return (False, int(f.get("waited", str(int(timeout_ms)))))
        self._raise_err(verb, resp)
        return (False, 0)  # unreachable

    def wait_stable(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        timeout_ms: int = 8000,
        stable_ms: int = 600,
    ) -> tuple[bool, int]:
        """Block until the region's hash holds steady for *stable_ms*.

        Returns ``(True, waited_ms)`` once stable, or ``(False, timeout_ms)``
        on timeout. Good for "wait until the screen settles" after a click.
        """
        return self._wait_region(
            "WAIT_STABLE", x, y, w, h, timeout_ms, stable_ms
        )

    def wait_change(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        timeout_ms: int = 8000,
    ) -> tuple[bool, int]:
        """Block until the region's hash differs from the first sample.

        Returns ``(True, waited_ms)`` on first change, or ``(False, timeout_ms)``
        on timeout. Good for "wait until something happens" after an action.
        """
        return self._wait_region(
            "WAIT_CHANGE", x, y, w, h, timeout_ms, None
        )

    # ------------------------------------------------------------------
    # In-memory screenshot over the socket (SCREENSHOT_BYTES)
    # ------------------------------------------------------------------

    def screenshot_bytes(self, fmt: str = "png") -> bytes:
        """Capture the full frame and return its encoded bytes over the socket.

        Unlike :meth:`screenshot` (which writes a file the host must re-open),
        this ships the encoded image straight back: the server replies with an
        ``OK bytes=<N> fmt=<fmt>\\n`` header, then exactly ``N`` raw bytes.

        Args:
            fmt: "png" (default, lossless) or "jpg" (quality ~85, smaller).

        Returns:
            The encoded image bytes.

        Raises:
            ValueError:             if *fmt* is not png/jpg.
            HarnessCommandError:    on server error.
            HarnessConnectionError: if the socket closes mid-transfer.
        """
        fmt = fmt.strip().lower()
        if fmt not in ("png", "jpg", "jpeg"):
            raise ValueError(f"screenshot_bytes fmt must be png/jpg, got {fmt!r}")
        if self._sock is None:
            raise HarnessConnectionError("Not connected; call connect() first.")
        try:
            self._sock.sendall(f"SCREENSHOT_BYTES {fmt}\n".encode("ascii"))
            # Read the header line up to the first newline.
            buf = b""
            while b"\n" not in buf:
                chunk = self._sock.recv(4096)
                if not chunk:
                    raise HarnessConnectionError(
                        "AOE3DEHarness closed the connection during header read."
                    )
                buf += chunk
                if len(buf) > _LINE_MAX:
                    raise HarnessProtocolError(
                        "SCREENSHOT_BYTES header exceeded line limit"
                    )
            header, rest = buf.split(b"\n", 1)
            header_str = header.decode("ascii", errors="replace").strip()
            if not header_str.startswith("OK"):
                self._raise_err("SCREENSHOT_BYTES", header_str)
            fields = self._parse_fields(header_str[2:].strip())
            try:
                nbytes = int(fields["bytes"])
            except (KeyError, ValueError) as exc:
                raise HarnessProtocolError(
                    f"Cannot parse SCREENSHOT_BYTES header: {header_str!r}"
                ) from exc
            # `rest` already holds the first slice of the payload.
            data = bytearray(rest)
            while len(data) < nbytes:
                chunk = self._sock.recv(min(65536, nbytes - len(data)))
                if not chunk:
                    raise HarnessConnectionError(
                        f"SCREENSHOT_BYTES truncated: got {len(data)} of {nbytes}"
                    )
                data.extend(chunk)
            return bytes(data[:nbytes])
        except socket.timeout as exc:
            raise HarnessTimeoutError(
                f"Socket timed out during SCREENSHOT_BYTES after {self._timeout}s"
            ) from exc
        except HarnessError:
            raise
        except OSError as exc:
            raise HarnessConnectionError(
                f"Socket error during SCREENSHOT_BYTES: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_fields(payload: str) -> dict[str, str]:
        """Split a ``k=v k=v`` payload into a dict."""
        fields: dict[str, str] = {}
        for token in payload.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        return fields

    def _set_sock_timeout(self, seconds: float) -> None:
        """Adjust the live socket's timeout (used to cover long WAIT_* calls)."""
        if self._sock is not None:
            self._sock.settimeout(seconds)

    def quit(self) -> None:
        """Tell the server to close this connection cleanly.

        After this call the socket is no longer usable; call close().
        The AOE3DEHarness process itself continues running.

        This method swallows connection errors because the server may close
        the socket before the response is fully delivered.
        """
        try:
            self.send_raw("QUIT")
        except (HarnessConnectionError, HarnessTimeoutError, OSError):
            pass  # expected: server may close socket on QUIT
