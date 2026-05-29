"""gs_launch.py — Launch AoE3 DE under gamescope-anw with harness mode enabled.

Replaces the legacy ``launch.py`` + ``attach.py`` approach.  Instead of
relying on a Wine DLL named pipe, this module:

  1. Validates the gamescope binary and AoE3DE_s.exe.
  2. Computes the Unix-domain socket path.
  3. Builds the gamescope + umu-run command line.
  4. Spawns gamescope as a subprocess.
  5. Polls for the socket to appear, then connects a :class:`GamescopeClient`.
  6. Returns ``(gamescope_proc, GamescopeClient)`` for the caller to drive.

When run as ``__main__``:
    Launches everything, prints the STATE response, then sleeps until SIGINT.
    On SIGINT: sends ``QUIT`` to the socket, then SIGTERM to the gamescope
    process.

Environment variables:
    GAMESCOPE_ANW_BINARY — override the default gamescope binary path.
    XDG_RUNTIME_DIR      — used to compute the default socket path.

Usage::

    python -m tools.aoe3_harness.gs_launch [--socket PATH]
                                            [--resolution WxH]
                                            [--window WxH]
                                            [--gs-binary PATH]
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from tools.aoe3_harness.gamescope_client import (
    GamescopeClient,
    GamescopeConnectionError,
)
from tools.aoe3_harness.paths import AOE3_EXE, UMU_RUN

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

#: Default gamescope-anw binary location.  Override via CLI or env var.
DEFAULT_GS_BINARY: Path = Path(
    "/var/home/jflessenkemper/AOE-3-DE-Harness/build/src/gamescope"
)


def _default_socket_path() -> Path:
    """Return the default socket path, honouring XDG_RUNTIME_DIR.

    Returns:
        ``$XDG_RUNTIME_DIR/gamescope-anw.sock`` if XDG_RUNTIME_DIR is set,
        otherwise ``/tmp/gamescope-anw.sock``.
    """
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return Path(runtime) / "gamescope-anw.sock"
    return Path("/tmp/gamescope-anw.sock")


# ---------------------------------------------------------------------------
# Command-line construction
# ---------------------------------------------------------------------------


def _build_umu_cmd(exe: Path = AOE3_EXE) -> list[str]:
    """Return the umu-run command list that runs AoE3DE_s.exe.

    Args:
        exe: Path to the AoE3DE_s.exe executable.

    Returns:
        List of strings suitable for subprocess argv.
    """
    return [str(UMU_RUN), str(exe)]


def build_gamescope_cmd(
    gs_binary: Path,
    socket_path: Path,
    resolution: tuple[int, int] = (1920, 1080),
    window: tuple[int, int] = (1280, 720),
    exe: Path = AOE3_EXE,
) -> list[str]:
    """Build the full gamescope + umu-run argv list.

    Args:
        gs_binary:   Path to the gamescope binary.
        socket_path: Unix-domain socket path for the harness.
        resolution:  Internal resolution ``(width, height)`` (default: 1920x1080).
        window:      Window size ``(width, height)`` (default: 1280x720).
        exe:         Path to AoE3DE_s.exe (default: from ``paths.AOE3_EXE``).

    Returns:
        Full argv list including the ``--`` separator and umu-run inner command.
    """
    rw, rh = resolution
    ww, wh = window
    inner = _build_umu_cmd(exe)
    return [
        str(gs_binary),
        "-W", str(rw),
        "-H", str(rh),
        "-w", str(ww),
        "-h", str(wh),
        "-b",
        "--harness-mode",
        "--harness-socket", str(socket_path),
        "--",
        *inner,
    ]


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------


def _check_gs_binary(gs_binary: Path) -> None:
    """Assert the gamescope binary exists and is executable.

    Args:
        gs_binary: Path to check.

    Raises:
        FileNotFoundError: if the binary is absent.
        PermissionError:   if the file is not executable.
    """
    if not gs_binary.exists():
        raise FileNotFoundError(
            f"gamescope binary not found at {gs_binary}. "
            "Build with: cmake --build /var/home/jflessenkemper/AOE-3-DE-Harness/build"
        )
    if not os.access(gs_binary, os.X_OK):
        raise PermissionError(
            f"gamescope binary at {gs_binary} is not executable."
        )


def _check_aoe3_exe(exe: Path = AOE3_EXE) -> None:
    """Assert AoE3DE_s.exe exists.

    Args:
        exe: Path to check (default: from ``paths.AOE3_EXE``).

    Raises:
        FileNotFoundError: if the executable is absent.
    """
    if not exe.exists():
        raise FileNotFoundError(
            f"AoE3DE_s.exe not found at {exe}. "
            "Verify the game is installed via Steam."
        )


# ---------------------------------------------------------------------------
# Socket polling
# ---------------------------------------------------------------------------


def _wait_for_socket(
    socket_path: Path,
    timeout: float = 30.0,
    poll_interval: float = 0.1,
) -> None:
    """Block until the socket file appears on disk or timeout expires.

    Args:
        socket_path:   Path to poll for.
        timeout:       Maximum seconds to wait (default: 30.0).
        poll_interval: Seconds between filesystem checks (default: 0.1).

    Raises:
        GamescopeConnectionError: if the socket does not appear in time.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if socket_path.exists():
            return
        remaining = deadline - time.monotonic()
        time.sleep(min(poll_interval, max(remaining, 0)))
    raise GamescopeConnectionError(
        f"gamescope socket {socket_path} did not appear within {timeout}s. "
        "Check that gamescope was launched with --harness-mode --harness-socket."
    )


# ---------------------------------------------------------------------------
# Main launcher
# ---------------------------------------------------------------------------


def gs_launch(
    gs_binary: Optional[Path] = None,
    socket_path: Optional[Path] = None,
    resolution: tuple[int, int] = (1920, 1080),
    window: tuple[int, int] = (1280, 720),
    exe: Path = AOE3_EXE,
    socket_timeout: float = 30.0,
    connect_timeout: float = 30.0,
) -> tuple[subprocess.Popen[bytes], GamescopeClient]:
    """Validate, spawn, and connect to gamescope-anw.

    Steps:
        1. Validate binaries.
        2. Compute socket path.
        3. Spawn gamescope as a non-blocking subprocess.
        4. Poll for the socket file.
        5. Connect a :class:`GamescopeClient`.

    Args:
        gs_binary:       Path to the gamescope binary.  Defaults to
                         ``DEFAULT_GS_BINARY``; overridden by env var
                         ``GAMESCOPE_ANW_BINARY``.
        socket_path:     Unix-domain socket path.  Defaults to
                         ``_default_socket_path()``.
        resolution:      Internal resolution ``(w, h)`` (default: 1920x1080).
        window:          Window size ``(w, h)`` (default: 1280x720).
        exe:             Path to AoE3DE_s.exe.
        socket_timeout:  Seconds to wait for the socket file to appear.
        connect_timeout: Seconds to wait for the socket to accept connections.

    Returns:
        Tuple of ``(gamescope_proc, GamescopeClient)``.  The caller is
        responsible for calling ``client.close()`` and terminating the
        process when done.

    Raises:
        FileNotFoundError:        if a required binary is missing.
        GamescopeConnectionError: if the socket never appears or connect fails.
    """
    if gs_binary is None:
        env_bin = os.environ.get("GAMESCOPE_ANW_BINARY")
        gs_binary = Path(env_bin) if env_bin else DEFAULT_GS_BINARY
    if socket_path is None:
        socket_path = _default_socket_path()

    # Preflight
    _check_gs_binary(gs_binary)
    _check_aoe3_exe(exe)

    # Remove stale socket if present from a previous crashed session
    try:
        socket_path.unlink()
    except FileNotFoundError:
        pass

    # Build command
    cmd = build_gamescope_cmd(
        gs_binary=gs_binary,
        socket_path=socket_path,
        resolution=resolution,
        window=window,
        exe=exe,
    )
    print(f"[gs_launch] Command: {' '.join(cmd)}")

    # Spawn
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"[gs_launch] Launched gamescope — PID {proc.pid}")

    # Poll for socket
    print(f"[gs_launch] Waiting for socket {socket_path} ...")
    _wait_for_socket(socket_path, timeout=socket_timeout)
    print(f"[gs_launch] Socket appeared; connecting ...")

    # Connect client
    client = GamescopeClient(socket_path)
    client.connect(timeout=connect_timeout)
    print("[gs_launch] Connected to gamescope harness socket.")
    return proc, client


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def _parse_resolution(s: str) -> tuple[int, int]:
    """Parse ``WxH`` string into ``(int, int)``.

    Args:
        s: String in ``WxH`` format, e.g. ``"1920x1080"``.

    Returns:
        Tuple ``(width, height)``.

    Raises:
        argparse.ArgumentTypeError: if the format is invalid.
    """
    try:
        parts = s.lower().split("x")
        if len(parts) != 2:
            raise ValueError
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        raise argparse.ArgumentTypeError(
            f"Invalid resolution {s!r}; expected WxH (e.g. 1920x1080)"
        )


def build_arg_parser() -> argparse.ArgumentParser:
    """Return the argument parser for gs_launch.

    Returns:
        Configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="python -m tools.aoe3_harness.gs_launch",
        description=(
            "Launch AoE3 DE under gamescope-anw harness mode and connect "
            "the Python control socket."
        ),
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Unix-domain socket path (default: $XDG_RUNTIME_DIR/gamescope-anw.sock "
            "or /tmp/gamescope-anw.sock)."
        ),
    )
    parser.add_argument(
        "--resolution",
        type=_parse_resolution,
        default=(1920, 1080),
        metavar="WxH",
        help="Internal gamescope resolution (default: 1920x1080).",
    )
    parser.add_argument(
        "--window",
        type=_parse_resolution,
        default=(1280, 720),
        metavar="WxH",
        help="Gamescope window size (default: 1280x720).",
    )
    parser.add_argument(
        "--gs-binary",
        type=Path,
        default=None,
        dest="gs_binary",
        metavar="PATH",
        help=f"Path to gamescope binary (default: {DEFAULT_GS_BINARY}).",
    )
    return parser


# ---------------------------------------------------------------------------
# __main__ entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> None:
    """Entry point for ``python -m tools.aoe3_harness.gs_launch``."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    proc, client = gs_launch(
        gs_binary=args.gs_binary,
        socket_path=args.socket,
        resolution=args.resolution,
        window=args.window,
    )

    try:
        state = client.state()
        print(
            f"[gs_launch] STATE pid={state.pid} uptime={state.uptime_ms}ms "
            f"w={state.internal_w} h={state.internal_h}"
        )
        print("[gs_launch] Ready. Press Ctrl+C to quit.")
        # Sleep until SIGINT
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[gs_launch] SIGINT received; shutting down ...")
    finally:
        # Graceful shutdown: QUIT to socket, then SIGTERM to gamescope
        try:
            client.quit()
        except Exception:  # noqa: BLE001
            pass
        client.close()

        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            print(f"[gs_launch] SIGTERM -> PID {proc.pid}")
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"[gs_launch] SIGKILL -> PID {proc.pid}")
        sys.exit(0)


if __name__ == "__main__":
    main()
