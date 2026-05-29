"""gamescope_client.py — Python client for the gamescope-anw control socket.

The gamescope fork (ASAP-Australia/AOE-3-DE-Harness) exposes a Unix-domain
socket when launched with ``--harness-mode --harness-socket <path>``.  This
module provides a high-level client with per-verb methods and an exception
hierarchy, replacing the legacy Wine named-pipe approach in ``dll_client.py``.

Wire protocol:
    - All commands are ``\\n``-terminated plain text lines.
    - Each connection may send multiple commands sequentially.
    - Server responds with one ``\\n``-terminated line per command.
    - Success responses begin with ``OK`` (possibly followed by payload).
    - Error responses: ``ERR <CODE> [detail ...]``
    - STATE response: ``STATE pid=<N> uptime=<N>ms w=<N> h=<N>``
    - SCREENSHOT success: ``OK path=<path> bytes=<N>``

Usage::

    with GamescopeClient("/run/user/1000/gamescope-anw.sock") as client:
        info = client.state()
        print(info.pid, info.internal_w, info.internal_h)
        client.key(0x57)          # tap W
        client.click(960, 540)
        result = client.screenshot(Path("/tmp/frame.png"))

See also:
    tools/aoe3_harness/gs_launch.py  — launcher that spawns gamescope and
                                        returns a connected GamescopeClient
    tools/aoe3_harness/vk.py         — Win32 VK code constants

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
    "GamescopeClient",
    "GamescopeState",
    "ScreenshotResult",
    "GamescopeError",
    "GamescopeConnectionError",
    "GamescopeProtocolError",
    "GamescopeCommandError",
    "GamescopeTimeoutError",
    "GamescopeShuttingDownError",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GamescopeState:
    """Snapshot of the gamescope compositor state.

    Attributes:
        pid:        PID of the gamescope process.
        uptime_ms:  Milliseconds since gamescope started.
        internal_w: Internal (output) resolution width in pixels.
        internal_h: Internal (output) resolution height in pixels.
    """

    pid: int
    uptime_ms: int
    internal_w: int
    internal_h: int


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


class GamescopeError(RuntimeError):
    """Base class for all gamescope client errors."""


class GamescopeConnectionError(GamescopeError):
    """Raised when the socket cannot be connected or drops unexpectedly."""


class GamescopeProtocolError(GamescopeError):
    """Raised when the server returns a response that cannot be parsed."""


class GamescopeCommandError(GamescopeError):
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


class GamescopeTimeoutError(GamescopeError):
    """Raised when a socket operation exceeds its configured timeout."""


class GamescopeShuttingDownError(GamescopeCommandError):
    """Raised when the server returns ``ERR HARNESS_SHUTTING_DOWN``."""

    def __init__(self, verb: str = "", detail: str = "") -> None:
        super().__init__(verb, "HARNESS_SHUTTING_DOWN", detail)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# Maximum bytes read per line; the protocol is line-based, so this is safe.
_LINE_MAX = 4096


class GamescopeClient:
    """Client for the gamescope-anw harness Unix-domain control socket.

    Connects to the socket exposed by ``gamescope --harness-mode
    --harness-socket <path>`` and provides per-verb methods for every
    supported command.

    Args:
        socket_path: Path to the Unix-domain socket file.
        timeout:     Per-operation socket timeout in seconds (default: 10.0).

    Example::

        with GamescopeClient("/run/user/1000/gamescope-anw.sock") as client:
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
        """Connect to the gamescope socket with exponential backoff.

        Attempts connection repeatedly until either the socket is available
        or ``timeout`` seconds have elapsed.  First retry fires after 50 ms;
        subsequent delays double, capped at 4 s.

        Args:
            timeout: Wall-clock seconds before giving up (default: 30.0).

        Raises:
            GamescopeConnectionError: if the socket is not reachable within
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

        raise GamescopeConnectionError(
            f"Could not connect to {self._socket_path} within {timeout}s: {last_exc}"
        )

    def reconnect(self, timeout: float = 30.0) -> None:
        """Close any existing socket and reconnect.

        Useful after a mid-session disconnect caused by a compositor stutter
        or a brief gamescope restart.

        Args:
            timeout: Wall-clock seconds before giving up (default: 30.0).

        Raises:
            GamescopeConnectionError: if the reconnect fails.
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

    def __enter__(self) -> "GamescopeClient":
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
            GamescopeConnectionError: if not connected or the server closes
                                      the connection mid-command.
            GamescopeTimeoutError:    if the socket operation times out.
        """
        if self._sock is None:
            raise GamescopeConnectionError(
                "Not connected; call connect() first."
            )
        try:
            self._sock.sendall((line + "\n").encode("ascii"))
            buf = b""
            while True:
                if len(buf) >= _LINE_MAX:
                    raise GamescopeProtocolError(
                        f"Response line exceeded {_LINE_MAX} bytes without \\n"
                    )
                chunk = self._sock.recv(_LINE_MAX - len(buf))
                if not chunk:
                    raise GamescopeConnectionError(
                        "gamescope closed the connection unexpectedly."
                    )
                buf += chunk
                if b"\n" in buf:
                    break
            return buf.split(b"\n", 1)[0].decode("ascii", errors="replace").strip()
        except socket.timeout as exc:
            raise GamescopeTimeoutError(
                f"Socket timed out after {self._timeout}s on command: {line!r}"
            ) from exc
        except GamescopeError:
            raise
        except OSError as exc:
            raise GamescopeConnectionError(
                f"Socket error during command {line!r}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_ok(verb: str, resp: str) -> str:
        """Assert *resp* starts with OK and return the payload after it.

        Raises:
            GamescopeShuttingDownError: if the response is HARNESS_SHUTTING_DOWN.
            GamescopeCommandError:      if the response is an ERR.
            GamescopeProtocolError:     if the response is unrecognised.
        """
        if resp.startswith("OK"):
            return resp[2:].strip()
        GamescopeClient._raise_err(verb, resp)
        return ""  # unreachable; satisfies type checker

    @staticmethod
    def _raise_err(verb: str, resp: str) -> None:
        """Parse an ERR response and raise the appropriate exception.

        Raises:
            GamescopeShuttingDownError: for HARNESS_SHUTTING_DOWN.
            GamescopeCommandError:      for all other ERR codes.
            GamescopeProtocolError:     if the response is not ERR either.
        """
        if resp.startswith("ERR"):
            parts = resp[3:].strip().split(None, 1)
            code = parts[0] if parts else "UNKNOWN"
            detail = parts[1] if len(parts) > 1 else ""
            if code == "HARNESS_SHUTTING_DOWN":
                raise GamescopeShuttingDownError(verb, detail)
            raise GamescopeCommandError(verb, code, detail)
        raise GamescopeProtocolError(
            f"Unexpected response for {verb}: {resp!r}"
        )

    # ------------------------------------------------------------------
    # Public command API
    # ------------------------------------------------------------------

    def state(self) -> GamescopeState:
        """Query the compositor state.

        Sends ``STATE`` and parses the response into a :class:`GamescopeState`.

        Wire response: ``STATE pid=<N> uptime=<N>ms w=<N> h=<N>``

        Returns:
            A :class:`GamescopeState` dataclass.

        Raises:
            GamescopeProtocolError:  if the response cannot be parsed.
            GamescopeCommandError:   if the server returns an error.
            GamescopeConnectionError: on socket failure.
        """
        resp = self.send_raw("STATE")
        if not resp.startswith("STATE"):
            self._raise_err("STATE", resp)
        payload = resp[len("STATE"):].strip()
        fields: dict[str, str] = {}
        for token in payload.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        try:
            pid = int(fields["pid"])
            uptime_ms = int(fields["uptime"].rstrip("ms"))
            internal_w = int(fields["w"])
            internal_h = int(fields["h"])
        except (KeyError, ValueError) as exc:
            raise GamescopeProtocolError(
                f"Cannot parse STATE response: {resp!r}"
            ) from exc
        return GamescopeState(
            pid=pid,
            uptime_ms=uptime_ms,
            internal_w=internal_w,
            internal_h=internal_h,
        )

    def key(self, vk: int) -> None:
        """Inject a key tap (KEY_DOWN + gap + KEY_UP) for a virtual key code.

        Args:
            vk: Win32 virtual key code (0x01–0xFF).

        Raises:
            GamescopeCommandError:    on server error.
            GamescopeConnectionError: on socket failure.
        """
        resp = self.send_raw(f"KEY {vk:#04x}")
        self._require_ok("KEY", resp)

    def key_down(self, vk: int) -> None:
        """Inject a key-down event for a virtual key code.

        Args:
            vk: Win32 virtual key code (0x01–0xFF).

        Raises:
            GamescopeCommandError:    on server error.
            GamescopeConnectionError: on socket failure.
        """
        resp = self.send_raw(f"KEY_DOWN {vk:#04x}")
        self._require_ok("KEY_DOWN", resp)

    def key_up(self, vk: int) -> None:
        """Inject a key-up event for a virtual key code.

        Args:
            vk: Win32 virtual key code (0x01–0xFF).

        Raises:
            GamescopeCommandError:    on server error.
            GamescopeConnectionError: on socket failure.
        """
        resp = self.send_raw(f"KEY_UP {vk:#04x}")
        self._require_ok("KEY_UP", resp)

    def move(self, x: int, y: int) -> None:
        """Inject a mouse-move to compositor coordinates (no click).

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Raises:
            GamescopeCommandError:    on server error.
            GamescopeConnectionError: on socket failure.
        """
        resp = self.send_raw(f"MOVE {x} {y}")
        self._require_ok("MOVE", resp)

    def click(self, x: int, y: int) -> None:
        """Inject a left-click at compositor coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Raises:
            GamescopeCommandError:    on server error.
            GamescopeConnectionError: on socket failure.
        """
        resp = self.send_raw(f"CLICK {x} {y}")
        self._require_ok("CLICK", resp)

    def screenshot(self, host_path: str | Path) -> ScreenshotResult:
        """Request a screenshot saved to the given host-filesystem path.

        The gamescope compositor writes the current frame as PNG.

        Args:
            host_path: Destination path on the host filesystem.

        Returns:
            :class:`ScreenshotResult` with the written path and byte count.

        Raises:
            GamescopeShuttingDownError: if the server is shutting down.
            GamescopeCommandError:      on any other server error
                                        (TIMEOUT, FAILED, INVALID_PATH).
            GamescopeConnectionError:   on socket failure.
            GamescopeProtocolError:     if the OK response cannot be parsed.
        """
        resp = self.send_raw(f"SCREENSHOT {host_path}")
        payload = self._require_ok("SCREENSHOT", resp)
        # Expected: path=<path> bytes=<N>
        fields: dict[str, str] = {}
        for token in payload.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        try:
            written_path = Path(fields["path"])
            bytes_written = int(fields["bytes"])
        except (KeyError, ValueError) as exc:
            raise GamescopeProtocolError(
                f"Cannot parse SCREENSHOT OK response: {resp!r}"
            ) from exc
        return ScreenshotResult(path=written_path, bytes_written=bytes_written)

    def quit(self) -> None:
        """Tell the server to close this connection cleanly.

        After this call the socket is no longer usable; call close().
        The gamescope process itself continues running.

        This method swallows connection errors because the server may close
        the socket before the response is fully delivered.
        """
        try:
            self.send_raw("QUIT")
        except (GamescopeConnectionError, GamescopeTimeoutError, OSError):
            pass  # expected: server may close socket on QUIT
