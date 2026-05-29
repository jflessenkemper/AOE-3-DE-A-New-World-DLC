"""attach.py — Attach to a Steam-launched AoE3 DE process and verify the ANW hook.

Intended for use after the user has clicked Play in Steam with the
WINEDLLOVERRIDES environment variable set to load hello_anw.dll and anw_hook.dll.

Steps:
    A  Wait for AoE3DE_s.exe to appear in the process list.
    B  Check /tmp/anw_dll.log to confirm hello_anw.dll loaded (warn-only).
    C  Connect to anw_hook.dll via DllClient (named pipe / Unix socket).
    D  Send a STATE round-trip to confirm the hook is alive (optional, skippable).

Exit codes:
    0  Required steps (A + C) passed.
    1  A required step failed.

Usage::

    python -m tools.aoe3_harness.attach [--timeout N] [--no-state] [--quiet]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

_ANW_DLL_LOG = Path("/tmp/anw_dll.log")
_POLL_INTERVAL = 0.5   # seconds between pgrep polls
_LOG_STALE_SECONDS = 600  # how recently the log must have been written


def _log(msg: str, quiet: bool) -> None:
    if not quiet:
        print(msg)


def _wait_for_game(timeout: float, quiet: bool) -> Optional[int]:
    """Poll for AoE3DE_s.exe up to *timeout* seconds.

    Args:
        timeout: Maximum seconds to wait.
        quiet:   Suppress progress lines if True.

    Returns:
        The first PID found, or None if the process never appeared.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["pgrep", "-f", "AoE3DE_s.exe"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            pids = [int(p) for p in result.stdout.strip().splitlines() if p.strip()]
            if pids:
                return pids[0]
        time.sleep(_POLL_INTERVAL)
    return None


def _check_dll_log(quiet: bool) -> None:
    """Inspect /tmp/anw_dll.log and emit OK or WARN (never exits).

    Args:
        quiet: Suppress output if True.
    """
    if not _ANW_DLL_LOG.exists():
        _log(
            "[attach] WARN: /tmp/anw_dll.log absent or stale — hello_anw.dll may not "
            "have loaded. WINEDLLOVERRIDES may not be reaching Wine. "
            "Continuing to anw_hook check anyway.",
            quiet,
        )
        return

    stat = _ANW_DLL_LOG.stat()
    age = time.time() - stat.st_mtime
    if age > _LOG_STALE_SECONDS:
        _log(
            "[attach] WARN: /tmp/anw_dll.log absent or stale — hello_anw.dll may not "
            "have loaded. WINEDLLOVERRIDES may not be reaching Wine. "
            "Continuing to anw_hook check anyway.",
            quiet,
        )
        return

    try:
        lines = _ANW_DLL_LOG.read_text(errors="replace").splitlines()
        last_line = lines[-1].strip() if lines else "(empty)"
    except OSError as exc:
        _log(f"[attach] WARN: could not read /tmp/anw_dll.log: {exc}", quiet)
        return

    _log(f"[attach] hello_anw OK: {last_line}", quiet)


def _connect_dll_client(quiet: bool):  # type: ignore[return]
    """Import and connect a DllClient.

    Returns the connected DllClient instance.  Prints a failure message and
    calls sys.exit(1) if the connection cannot be established.
    """
    from tools.aoe3_harness.dll_client import DllClient  # noqa: PLC0415

    client = DllClient()
    try:
        client.connect()
    except Exception as exc:  # noqa: BLE001
        _log(
            "[attach] FAIL: could not connect to anw_hook named pipe — "
            "DLL did not load or pipe server crashed.",
            quiet=False,
        )
        _log(f"[attach]        detail: {exc}", quiet=False)
        sys.exit(1)

    _log("[attach] connected to anw_hook pipe", quiet)
    return client


def _state_round_trip(client, quiet: bool) -> None:  # type: ignore[type-arg]
    """Send STATE command and print the response.

    Exits with code 1 on failure.

    Args:
        client: A connected DllClient instance.
        quiet:  Suppress output if True.
    """
    try:
        resp = client.state()
    except Exception as exc:  # noqa: BLE001
        _log(
            f"[attach] FAIL: STATE round-trip failed: {exc}",
            quiet=False,
        )
        sys.exit(1)

    display = resp[:200] if len(resp) > 200 else resp
    _log(f"[attach] STATE: {display}", quiet)
    _log("[attach] STATE round-trip OK", quiet)


def main(argv: Optional[list[str]] = None) -> None:
    """Entry point for ``python -m tools.aoe3_harness.attach``."""
    parser = argparse.ArgumentParser(
        prog="python -m tools.aoe3_harness.attach",
        description="Attach to a Steam-launched AoE3 DE process and verify the ANW hook DLLs.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        metavar="SECONDS",
        help="Total seconds to wait for the game process (default: 120).",
    )
    parser.add_argument(
        "--no-state",
        action="store_true",
        help="Skip the STATE round-trip smoke test.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-step progress lines.",
    )
    args = parser.parse_args(argv)

    # ------------------------------------------------------------------
    # Step A — wait for game process
    # ------------------------------------------------------------------
    _log(f"[attach] waiting up to {args.timeout:.0f}s for AoE3DE_s.exe ...", args.quiet)
    pid = _wait_for_game(args.timeout, args.quiet)
    if pid is None:
        print(
            f"[attach] FAIL: AoE3DE_s.exe not running after {args.timeout:.0f}s — "
            "start the game via Steam first."
        )
        sys.exit(1)
    _log(f"[attach] game PID = {pid}", args.quiet)

    # ------------------------------------------------------------------
    # Step B — verify hello_anw.dll loaded (warn-only)
    # ------------------------------------------------------------------
    _check_dll_log(args.quiet)

    # ------------------------------------------------------------------
    # Step C — connect via DllClient
    # ------------------------------------------------------------------
    client = _connect_dll_client(args.quiet)

    # ------------------------------------------------------------------
    # Step D — STATE round-trip (skippable)
    # ------------------------------------------------------------------
    if not args.no_state:
        _state_round_trip(client, args.quiet)

    client.close()


if __name__ == "__main__":
    main()
