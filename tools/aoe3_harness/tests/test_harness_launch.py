"""Unit tests for tools/aoe3_harness/harness_launch.py.

All tests that involve subprocess spawning or binary existence checks use
mocks; no real AOE3DEHarness process or AoE3 installation is required.  Run with:

    cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
    python3 -m pytest tools/aoe3_harness/tests/test_harness_launch.py -v
"""

from __future__ import annotations

import os
import signal
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, call, patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_harness.harness_client import HarnessConnectionError  # noqa: E402
from tools.aoe3_harness.harness_launch import (  # noqa: E402
    DEFAULT_GS_BINARY,
    _check_aoe3_exe,
    _check_gs_binary,
    _default_socket_path,
    _parse_resolution,
    _wait_for_socket,
    build_arg_parser,
    build_gamescope_cmd,
    harness_launch,
)


# ---------------------------------------------------------------------------
# Tests: _parse_resolution
# ---------------------------------------------------------------------------


class TestParseResolution(unittest.TestCase):
    def test_valid_resolution(self) -> None:
        self.assertEqual(_parse_resolution("1920x1080"), (1920, 1080))

    def test_valid_small_resolution(self) -> None:
        self.assertEqual(_parse_resolution("640x480"), (640, 480))

    def test_case_insensitive(self) -> None:
        self.assertEqual(_parse_resolution("1280X720"), (1280, 720))

    def test_invalid_raises(self) -> None:
        import argparse
        with self.assertRaises(argparse.ArgumentTypeError):
            _parse_resolution("1920-1080")

    def test_non_numeric_raises(self) -> None:
        import argparse
        with self.assertRaises(argparse.ArgumentTypeError):
            _parse_resolution("WIDTHxHEIGHT")


# ---------------------------------------------------------------------------
# Tests: build_gamescope_cmd
# ---------------------------------------------------------------------------


class TestBuildGamescopeCmd(unittest.TestCase):
    def test_contains_harness_flags(self) -> None:
        cmd = build_gamescope_cmd(
            gs_binary=Path("/fake/AOE3DEHarness"),
            socket_path=Path("/tmp/test.sock"),
        )
        self.assertIn("--harness-mode", cmd)
        self.assertIn("--harness-socket", cmd)
        self.assertIn("/tmp/test.sock", cmd)

    def test_resolution_args(self) -> None:
        cmd = build_gamescope_cmd(
            gs_binary=Path("/fake/AOE3DEHarness"),
            socket_path=Path("/tmp/test.sock"),
            resolution=(2560, 1440),
        )
        idx_W = cmd.index("-W")
        idx_H = cmd.index("-H")
        self.assertEqual(cmd[idx_W + 1], "2560")
        self.assertEqual(cmd[idx_H + 1], "1440")

    def test_window_args(self) -> None:
        cmd = build_gamescope_cmd(
            gs_binary=Path("/fake/AOE3DEHarness"),
            socket_path=Path("/tmp/test.sock"),
            window=(800, 600),
        )
        idx_w = cmd.index("-w")
        idx_h = cmd.index("-h")
        self.assertEqual(cmd[idx_w + 1], "800")
        self.assertEqual(cmd[idx_h + 1], "600")

    def test_separator_present(self) -> None:
        cmd = build_gamescope_cmd(
            gs_binary=Path("/fake/AOE3DEHarness"),
            socket_path=Path("/tmp/test.sock"),
        )
        self.assertIn("--", cmd)

    def test_binary_is_first_arg(self) -> None:
        cmd = build_gamescope_cmd(
            gs_binary=Path("/custom/AOE3DEHarness"),
            socket_path=Path("/tmp/test.sock"),
        )
        self.assertEqual(cmd[0], "/custom/AOE3DEHarness")

    def test_borderless_flag(self) -> None:
        cmd = build_gamescope_cmd(
            gs_binary=Path("/fake/AOE3DEHarness"),
            socket_path=Path("/tmp/test.sock"),
        )
        self.assertIn("-b", cmd)


# ---------------------------------------------------------------------------
# Tests: _default_socket_path
# ---------------------------------------------------------------------------


class TestDefaultSocketPath(unittest.TestCase):
    def test_uses_xdg_runtime_dir(self) -> None:
        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/run/user/1234"}):
            path = _default_socket_path()
        self.assertEqual(path, Path("/run/user/1234/AOE3DEHarness.sock"))

    def test_fallback_when_no_xdg_runtime_dir(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "XDG_RUNTIME_DIR"}
        with patch.dict(os.environ, env, clear=True):
            path = _default_socket_path()
        self.assertEqual(path, Path("/tmp/AOE3DEHarness.sock"))


# ---------------------------------------------------------------------------
# Tests: _check_gs_binary
# ---------------------------------------------------------------------------


class TestCheckGsBinary(unittest.TestCase):
    def test_missing_binary_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            _check_gs_binary(Path("/nonexistent/AOE3DEHarness_binary_xyz"))

    def test_non_executable_raises_permission_error(self) -> None:
        with tempfile.NamedTemporaryFile() as f:
            # File exists but is not executable
            path = Path(f.name)
            os.chmod(path, 0o600)
            with self.assertRaises(PermissionError):
                _check_gs_binary(path)


# ---------------------------------------------------------------------------
# Tests: _check_aoe3_exe
# ---------------------------------------------------------------------------


class TestCheckAoe3Exe(unittest.TestCase):
    def test_missing_exe_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            _check_aoe3_exe(Path("/nonexistent/AoE3DE_s.exe"))


# ---------------------------------------------------------------------------
# Tests: _wait_for_socket
# ---------------------------------------------------------------------------


class TestWaitForSocket(unittest.TestCase):
    def test_socket_appears_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = Path(tmpdir) / "ready.sock"
            sock_path.touch()
            _wait_for_socket(sock_path, timeout=1.0)  # should not raise

    def test_socket_never_appears_raises(self) -> None:
        with self.assertRaises(HarnessConnectionError):
            _wait_for_socket(
                Path("/tmp/never_appears_xyz_12345.sock"),
                timeout=0.15,
                poll_interval=0.05,
            )

    def test_socket_appears_after_delay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = Path(tmpdir) / "late.sock"

            def _create_late() -> None:
                time.sleep(0.1)
                sock_path.touch()

            t = threading.Thread(target=_create_late, daemon=True)
            t.start()
            _wait_for_socket(sock_path, timeout=2.0, poll_interval=0.03)
            t.join(timeout=1.0)


# ---------------------------------------------------------------------------
# Tests: CLI argument parsing
# ---------------------------------------------------------------------------


class TestArgParsing(unittest.TestCase):
    def _parse(self, args: list[str]) -> object:
        return build_arg_parser().parse_args(args)

    def test_defaults(self) -> None:
        args = self._parse([])
        self.assertIsNone(args.socket)  # type: ignore[attr-defined]
        self.assertEqual(args.resolution, (1920, 1080))  # type: ignore[attr-defined]
        self.assertEqual(args.window, (1280, 720))  # type: ignore[attr-defined]
        self.assertIsNone(args.gs_binary)  # type: ignore[attr-defined]

    def test_socket_override(self) -> None:
        args = self._parse(["--socket", "/tmp/custom.sock"])
        self.assertEqual(args.socket, Path("/tmp/custom.sock"))  # type: ignore[attr-defined]

    def test_resolution_override(self) -> None:
        args = self._parse(["--resolution", "2560x1440"])
        self.assertEqual(args.resolution, (2560, 1440))  # type: ignore[attr-defined]

    def test_window_override(self) -> None:
        args = self._parse(["--window", "800x600"])
        self.assertEqual(args.window, (800, 600))  # type: ignore[attr-defined]

    def test_gs_binary_override(self) -> None:
        args = self._parse(["--gs-binary", "/custom/AOE3DEHarness"])
        self.assertEqual(args.gs_binary, Path("/custom/AOE3DEHarness"))  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Tests: harness_launch() integration (mocked binaries + subprocess)
# ---------------------------------------------------------------------------


class TestHarnessLaunch(unittest.TestCase):
    def test_gs_binary_missing_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            harness_launch(gs_binary=Path("/nonexistent/AOE3DEHarness_xyz"))

    def test_aoe3_exe_missing_raises(self) -> None:
        with tempfile.NamedTemporaryFile() as f:
            gs_bin = Path(f.name)
            os.chmod(gs_bin, 0o755)
            with self.assertRaises(FileNotFoundError):
                harness_launch(
                    gs_binary=gs_bin,
                    exe=Path("/nonexistent/AoE3DE_s.exe"),
                )

    def test_socket_timeout_raises(self) -> None:
        with tempfile.NamedTemporaryFile() as f_gs, \
             tempfile.NamedTemporaryFile(suffix=".exe") as f_exe, \
             tempfile.TemporaryDirectory() as tmpdir:
            gs_bin = Path(f_gs.name)
            exe = Path(f_exe.name)
            os.chmod(gs_bin, 0o755)
            sock_path = Path(tmpdir) / "never_created.sock"

            mock_proc = MagicMock()
            mock_proc.pid = 99999
            mock_proc.poll.return_value = None

            with patch("subprocess.Popen", return_value=mock_proc):
                with self.assertRaises(HarnessConnectionError):
                    harness_launch(
                        gs_binary=gs_bin,
                        socket_path=sock_path,
                        exe=exe,
                        socket_timeout=0.15,
                    )

    def test_graceful_shutdown_sends_sigterm(self) -> None:
        """harness_launch returns (proc, client); caller can SIGTERM the proc."""
        with tempfile.NamedTemporaryFile() as f_gs, \
             tempfile.NamedTemporaryFile(suffix=".exe") as f_exe, \
             tempfile.TemporaryDirectory() as tmpdir:
            gs_bin = Path(f_gs.name)
            exe = Path(f_exe.name)
            os.chmod(gs_bin, 0o755)
            sock_path = Path(tmpdir) / "harness.sock"

            mock_proc = MagicMock()
            mock_proc.pid = 42
            mock_proc.poll.return_value = 0  # already exited

            # We intercept Popen so that after it's "called", we create the
            # socket as the real AOE3DEHarness would do.
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

            def _fake_popen(cmd, **kwargs):  # type: ignore[no-untyped-def]
                # Bind the server socket now (simulates AOE3DEHarness creating it)
                srv.bind(str(sock_path))
                srv.listen(1)
                # Accept in a background thread so client.connect() can succeed
                def _accept() -> None:
                    try:
                        conn, _ = srv.accept()
                        conn.close()
                    except OSError:
                        pass
                    finally:
                        srv.close()
                threading.Thread(target=_accept, daemon=True).start()
                return mock_proc

            with patch("subprocess.Popen", side_effect=_fake_popen):
                proc, client = harness_launch(
                    gs_binary=gs_bin,
                    socket_path=sock_path,
                    exe=exe,
                    socket_timeout=5.0,
                    connect_timeout=5.0,
                )
            self.assertIs(proc, mock_proc)
            client.close()


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
