"""dll_client.py — Python client for the ANW hook DLL named pipe server.

The DLL (anw_hook.dll) creates a Win32 named pipe ``\\\\.\\pipe\\anwhook`` inside
the AoE3 Wine/Proton process.  Wine named pipes are Unix domain sockets managed
by the live wineserver process.  This client derives the socket path at runtime
from the WINEPREFIX inode (see _get_pipe_socket_path) and connects via
``socket.AF_UNIX``.

Wire protocol (per architecture §4):
    - All commands are ``\\r\\n``-terminated plain text lines.
    - Each connection may send multiple commands sequentially.
    - Supported commands: KEY_DOWN, KEY_UP, KEY, CLICK, MOVE, STATE, QUIT,
      SCREENSHOT (stub — returns ERR DXGI_NOT_IMPLEMENTED until DXGI hook is
      enabled; see artifacts/harness_design/phase2_verification_checklist.md).

Usage::

    with DllClient() as client:
        client.state()                   # heartbeat: "ALIVE pid=1234 tick=0"
        client.press_key(0x57)           # tap W
        client.click(960, 540)           # left-click at screen centre
        client.screenshot(Path("/tmp/frame.png"))  # ERR until DXGI enabled

See also:
    tools/aoe3_harness/cli.py — CLI wrappers for these methods
    artifacts/harness_design/phase2_dll_architecture.md §5, §6

Design decisions:
    - Socket path is derived dynamically (not cached) so it survives reboots
      and Proton restarts without stale-path failures.
    - Retry with exponential backoff on connect so callers don't need to poll.
    - The client holds one persistent Unix socket per DllClient instance;
      multiple command-response cycles reuse the same connection.
"""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path
from typing import Optional

__all__ = [
    "DllClient",
    "DllClientError",
    "get_pipe_socket_path",
]

# Default Wine prefix path for AoE3 DE (AppID 933110)
_DEFAULT_PFX = os.path.expanduser(
    "~/.local/share/Steam/steamapps/compatdata/933110/pfx"
)

# DLL drop paths (host-side; for 'dll verify' / 'dll status' CLI commands)
DLL_SYSTEM32_PATH = Path(
    "~/.local/share/Steam/steamapps/compatdata/933110"
    "/pfx/drive_c/windows/system32"
).expanduser()

DLL_GAME_DATA_PATH = Path(
    "~/.local/share/Steam/steamapps/compatdata/933110"
    "/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE"
).expanduser()

DLL_NAMES = ("hello_anw.dll", "anw_hook.dll")


class DllClientError(RuntimeError):
    """Raised when the DLL pipe server returns an error response or is unreachable."""


def get_pipe_socket_path(pipe_name: str = "anwhook", pfx: Optional[str] = None) -> str:
    """Return the Unix socket path for a Wine named pipe.

    The wineserver stores pipe sockets at::

        /tmp/.wine-<uid>/server-<dev_minor_hex>-<inode_hex>/pipe/<name_lower>

    This path is stable across reboots as long as the prefix directory's inode
    does not change (it won't unless the prefix is deleted and recreated).  The
    device minor number can change after OS upgrades — always derive at runtime
    rather than hardcoding.

    Args:
        pipe_name: Win32 pipe name without the ``\\\\.\\pipe\\`` prefix.
                   Case-insensitive; converted to lowercase.
        pfx:       Path to the Wine prefix directory.  Defaults to the AoE3 DE
                   Proton prefix (``~/.local/.../compatdata/933110/pfx``).

    Returns:
        Absolute path to the Unix domain socket file.

    Raises:
        FileNotFoundError: if the prefix directory does not exist.
    """
    if pfx is None:
        pfx = _DEFAULT_PFX
    st = os.stat(pfx)
    dev_minor = os.minor(st.st_dev)
    inode = st.st_ino
    uid = os.getuid()
    server_dir = f"/tmp/.wine-{uid}/server-{dev_minor:x}-{inode:x}"
    return os.path.join(server_dir, "pipe", pipe_name.lower())


class DllClient:
    """Client for the ANW hook DLL named pipe server.

    Connects to ``anw_hook.dll``'s named pipe over a Wine Unix socket and
    sends line-protocol commands.

    Args:
        pipe_name: Win32 pipe name (default: ``"anwhook"``).
        pfx:       Wine prefix path (default: AoE3 DE Proton prefix).
        timeout:   Socket timeout in seconds (default: 10.0).

    Example::

        with DllClient() as client:
            print(client.state())
            client.press_key(0x57)   # W key
            client.click(960, 540)
    """

    def __init__(
        self,
        pipe_name: str = "anwhook",
        pfx: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        self._pipe_name = pipe_name
        self._pfx = pfx
        self._timeout = timeout
        self._sock: Optional[socket.socket] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self, retries: int = 5) -> None:
        """Connect to the DLL named pipe, retrying with exponential backoff.

        Args:
            retries: Maximum number of connection attempts (default: 5).

        Raises:
            ConnectionError: if all attempts fail.
        """
        socket_path = get_pipe_socket_path(self._pipe_name, self._pfx)
        delay = 0.5
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self._timeout)
                sock.connect(socket_path)
                self._sock = sock
                return
            except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
                last_exc = exc
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay = min(delay * 2, 8.0)
        raise ConnectionError(
            f"Could not connect to {socket_path} after {retries} attempts: {last_exc}"
        )

    def close(self) -> None:
        """Close the socket connection."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def __enter__(self) -> "DllClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def _send(self, cmd: str) -> str:
        """Send a command line and return the response line (both sans CRLF).

        Args:
            cmd: Command string without ``\\r\\n`` terminator.

        Returns:
            Response string without ``\\r\\n`` terminator.

        Raises:
            RuntimeError: if not connected.
            ConnectionError: if the DLL closes the connection unexpectedly.
        """
        if self._sock is None:
            raise RuntimeError("Not connected; call connect() first.")
        self._sock.sendall((cmd + "\r\n").encode("ascii"))
        buf = b""
        while not buf.endswith(b"\r\n"):
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("DLL closed the connection unexpectedly.")
            buf += chunk
        return buf.decode("ascii", errors="replace").strip()

    # ------------------------------------------------------------------
    # Public command API
    # ------------------------------------------------------------------

    def state(self) -> str:
        """Query the DLL worker thread status.

        Returns:
            Status string, e.g. ``"ALIVE pid=1234 tick=0"``.

        Raises:
            DllClientError: if the response is not ``ALIVE ...``.
        """
        resp = self._send("STATE")
        if not resp.startswith("ALIVE"):
            raise DllClientError(f"Unexpected STATE response: {resp}")
        return resp

    def key_down(self, vk: int) -> None:
        """Inject a WM_KEYDOWN event for the given virtual key code.

        Args:
            vk: Windows virtual key code (0x01–0xFF), e.g. ``0x57`` for W.

        Raises:
            DllClientError: if the DLL returns an error.
        """
        resp = self._send(f"KEY_DOWN {vk:#04x}")
        if not resp.startswith("OK"):
            raise DllClientError(f"KEY_DOWN failed: {resp}")

    def key_up(self, vk: int) -> None:
        """Inject a WM_KEYUP event for the given virtual key code.

        Args:
            vk: Windows virtual key code (0x01–0xFF).

        Raises:
            DllClientError: if the DLL returns an error.
        """
        resp = self._send(f"KEY_UP {vk:#04x}")
        if not resp.startswith("OK"):
            raise DllClientError(f"KEY_UP failed: {resp}")

    def press_key(self, vk: int) -> None:
        """Inject a key press (KEY_DOWN + 50ms gap + KEY_UP).

        Args:
            vk: Windows virtual key code (0x01–0xFF), e.g. ``0x57`` for W.

        Raises:
            DllClientError: if the DLL returns an error.
        """
        resp = self._send(f"KEY {vk:#04x}")
        if not resp.startswith("OK"):
            raise DllClientError(f"KEY failed: {resp}")

    def click(self, x: int, y: int) -> None:
        """Inject a left-click at game-window client-area coordinates.

        The DLL translates client-area pixels to screen-absolute coordinates
        via ClientToScreen() before calling SendInput.

        Args:
            x: Horizontal pixel coordinate in the game window's client area.
            y: Vertical pixel coordinate in the game window's client area.

        Raises:
            DllClientError: if the DLL returns an error.
        """
        resp = self._send(f"CLICK {x} {y}")
        if not resp.startswith("OK"):
            raise DllClientError(f"CLICK failed: {resp}")

    def move(self, x: int, y: int) -> None:
        """Inject a mouse-move to game-window client-area coordinates (no click).

        Args:
            x: Horizontal pixel coordinate in the game window's client area.
            y: Vertical pixel coordinate in the game window's client area.

        Raises:
            DllClientError: if the DLL returns an error.
        """
        resp = self._send(f"MOVE {x} {y}")
        if not resp.startswith("OK"):
            raise DllClientError(f"MOVE failed: {resp}")

    def screenshot(self, path: Path) -> None:
        """Request a screenshot saved to the given host filesystem path.

        Converts the Linux path to a Wine ``Z:`` drive path before sending.
        The DLL writes the frame as raw BGRA pixels; convert to PNG with Pillow
        if needed.

        NOTE: Currently returns ``ERR DXGI_NOT_IMPLEMENTED`` because the DXGI
        Present hook is stubbed.  See
        ``artifacts/harness_design/phase2_verification_checklist.md §5``.

        Args:
            path: Output file path on the host filesystem (e.g. ``Path("/tmp/frame.bgra")``).

        Raises:
            DllClientError: if the DLL returns an error (including the stub error).
        """
        # Convert Linux path to Wine Z: drive path
        wine_path = "Z:\\" + str(path).lstrip("/").replace("/", "\\")
        resp = self._send(f"SCREENSHOT {wine_path}")
        if not resp.startswith("OK"):
            raise DllClientError(f"SCREENSHOT failed: {resp}")

    def quit(self) -> None:
        """Tell the DLL worker thread to close the pipe and exit.

        After this call the socket is no longer usable; call close().
        The DLL itself stays loaded in the process until it exits.
        """
        try:
            self._send("QUIT")
        except (ConnectionError, OSError):
            pass  # Expected: server closes pipe on QUIT
