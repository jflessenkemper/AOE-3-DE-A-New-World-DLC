"""Unit tests for tools/aoe3_harness/harness_client.py.

All tests use a mock socket server running in a background thread so no real
AOE3DEHarness process is required.  Run with:

    cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
    python3 -m pytest tools/aoe3_harness/tests/test_harness_client.py -v

Coverage target: 80%+ of harness_client.py, all public methods and all
error paths exercised.
"""

from __future__ import annotations

import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_harness.harness_client import (  # noqa: E402
    HarnessClient,
    HarnessCommandError,
    HarnessConnectionError,
    HarnessError,
    HarnessProtocolError,
    HarnessShuttingDownError,
    HarnessState,
    HarnessTimeoutError,
    ScreenshotResult,
)


# ---------------------------------------------------------------------------
# Helpers — mock socket server
# ---------------------------------------------------------------------------


class _MockServer:
    """A simple line-protocol server that runs in a background thread.

    The caller supplies a response script: a list of ``(command_prefix, response)``
    pairs.  When a line arrives starting with *command_prefix*, the server sends
    *response* + ``\\n``.  If *response* is None, the connection is closed
    immediately (simulates mid-command disconnect).
    """

    def __init__(self, script: list[tuple[str, Optional[str]]]) -> None:
        self._script = list(script)
        self._tmpdir = tempfile.mkdtemp()
        self.socket_path = Path(self._tmpdir) / "test.sock"
        self._server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()

    def start(self) -> None:
        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_sock.bind(str(self.socket_path))
        self._server_sock.listen(1)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self._started.wait(timeout=2.0)

    def _serve(self) -> None:
        self._started.set()
        assert self._server_sock is not None
        try:
            conn, _ = self._server_sock.accept()
        except OSError:
            return
        with conn:
            buf = b""
            script = list(self._script)
            while script:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line_s = line.decode("ascii", errors="replace").strip()
                    if not script:
                        break
                    prefix, response = script.pop(0)
                    if response is None:
                        # Close connection to simulate disconnect
                        return
                    conn.sendall((response + "\n").encode("ascii"))

    def stop(self) -> None:
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass


def _make_client_with_mock_socket(responses: list[bytes]) -> HarnessClient:
    """Return a HarnessClient with an already-injected mock socket."""
    sock = MagicMock(spec=socket.socket)
    sock.recv.side_effect = responses + [b""]
    client = HarnessClient("/fake/path.sock")
    client._sock = sock
    return client, sock


# ---------------------------------------------------------------------------
# Tests: exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy(unittest.TestCase):
    def test_all_errors_subclass_harness_error(self) -> None:
        for cls in (
            HarnessConnectionError,
            HarnessProtocolError,
            HarnessCommandError,
            HarnessTimeoutError,
            HarnessShuttingDownError,
        ):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, HarnessError))

    def test_shutting_down_subclasses_command_error(self) -> None:
        self.assertTrue(issubclass(HarnessShuttingDownError, HarnessCommandError))

    def test_command_error_attributes(self) -> None:
        err = HarnessCommandError("SCREENSHOT", "TIMEOUT", "timed out")
        self.assertEqual(err.verb, "SCREENSHOT")
        self.assertEqual(err.code, "TIMEOUT")
        self.assertEqual(err.detail, "timed out")

    def test_command_error_no_detail(self) -> None:
        err = HarnessCommandError("KEY", "INVALID_VK")
        self.assertIn("INVALID_VK", str(err))
        self.assertEqual(err.detail, "")

    def test_shutting_down_error_code(self) -> None:
        err = HarnessShuttingDownError("CLICK")
        self.assertEqual(err.code, "HARNESS_SHUTTING_DOWN")


# ---------------------------------------------------------------------------
# Tests: connect() — happy path and failure modes
# ---------------------------------------------------------------------------


class TestConnect(unittest.TestCase):
    def test_connect_happy_path(self) -> None:
        """connect() succeeds when the server is ready immediately."""
        server = _MockServer([("STATE", "STATE pid=1 uptime=0ms w=1920 h=1080")])
        server.start()
        try:
            client = HarnessClient(server.socket_path)
            client.connect(timeout=5.0)
            self.assertIsNotNone(client._sock)
            client.close()
        finally:
            server.stop()

    def test_connect_timeout_raises(self) -> None:
        """connect() raises HarnessConnectionError if socket never appears."""
        client = HarnessClient("/tmp/nonexistent_harness_test_9999.sock")
        with self.assertRaises(HarnessConnectionError) as ctx:
            client.connect(timeout=0.15)
        self.assertIn("nonexistent", str(ctx.exception))

    def test_connect_retry_succeeds_on_third_attempt(self) -> None:
        """connect() retries until the socket is ready."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = Path(tmpdir) / "late.sock"

            # Create the server socket after a short delay
            def _delayed_server() -> None:
                time.sleep(0.12)
                srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                srv.bind(str(sock_path))
                srv.listen(1)
                try:
                    conn, _ = srv.accept()
                    conn.close()
                except OSError:
                    pass
                finally:
                    srv.close()

            t = threading.Thread(target=_delayed_server, daemon=True)
            t.start()

            client = HarnessClient(sock_path)
            client.connect(timeout=5.0)
            client.close()
            t.join(timeout=2.0)

    def test_context_manager_connects_and_closes(self) -> None:
        server = _MockServer([])
        server.start()
        try:
            with HarnessClient(server.socket_path) as client:
                self.assertIsNotNone(client._sock)
            self.assertIsNone(client._sock)
        finally:
            server.stop()

    def test_context_manager_closes_on_exception(self) -> None:
        server = _MockServer([])
        server.start()
        try:
            client_ref: Optional[HarnessClient] = None
            try:
                with HarnessClient(server.socket_path) as client:
                    client_ref = client
                    raise RuntimeError("deliberate")
            except RuntimeError:
                pass
            self.assertIsNone(client_ref._sock)  # type: ignore[union-attr]
        finally:
            server.stop()

    def test_close_idempotent(self) -> None:
        client = HarnessClient("/fake/path")
        mock_sock = MagicMock()
        client._sock = mock_sock
        client.close()
        client.close()
        self.assertIsNone(client._sock)

    def test_close_swallows_oserror(self) -> None:
        client = HarnessClient("/fake/path")
        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("already closed")
        client._sock = mock_sock
        client.close()  # should not raise

    def test_reconnect_replaces_socket(self) -> None:
        server = _MockServer([])
        server.start()
        try:
            client = HarnessClient(server.socket_path)
            client.connect(timeout=5.0)
            old_sock = client._sock
            client.reconnect(timeout=5.0)
            self.assertIsNotNone(client._sock)
            # The old socket object should have been replaced
            # (reconnect closes and reopens)
            client.close()
        finally:
            server.stop()


# ---------------------------------------------------------------------------
# Tests: send_raw()
# ---------------------------------------------------------------------------


class TestSendRaw(unittest.TestCase):
    def test_sends_newline_terminated_line(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.send_raw("STATE")
        sock.sendall.assert_called_once_with(b"STATE\n")

    def test_reads_until_newline(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK some", b" data\n"])
        result = client.send_raw("KEY 0x57")
        self.assertEqual(result, "OK some data")

    def test_raises_connection_error_when_not_connected(self) -> None:
        client = HarnessClient("/fake/path")
        with self.assertRaises(HarnessConnectionError):
            client.send_raw("STATE")

    def test_raises_connection_error_on_eof(self) -> None:
        client, _ = _make_client_with_mock_socket([b""])
        with self.assertRaises(HarnessConnectionError):
            client.send_raw("STATE")

    def test_raises_timeout_error_on_socket_timeout(self) -> None:
        client = HarnessClient("/fake/path")
        mock_sock = MagicMock(spec=socket.socket)
        mock_sock.recv.side_effect = socket.timeout("timed out")
        client._sock = mock_sock
        with self.assertRaises(HarnessTimeoutError):
            client.send_raw("STATE")

    def test_raises_connection_error_on_oserror(self) -> None:
        client = HarnessClient("/fake/path")
        mock_sock = MagicMock(spec=socket.socket)
        mock_sock.sendall.side_effect = OSError("broken pipe")
        client._sock = mock_sock
        with self.assertRaises(HarnessConnectionError):
            client.send_raw("STATE")

    def test_raises_protocol_error_when_line_too_long(self) -> None:
        client = HarnessClient("/fake/path")
        mock_sock = MagicMock(spec=socket.socket)
        # Return a chunk without a newline but large enough to hit the limit
        # We need recv to be called enough times to exceed _LINE_MAX
        mock_sock.recv.return_value = b"X" * 4096
        client._sock = mock_sock
        with self.assertRaises(HarnessProtocolError):
            client.send_raw("STATE")

    def test_strips_whitespace_from_response(self) -> None:
        client, _ = _make_client_with_mock_socket([b"  OK  \n"])
        result = client.send_raw("KEY 0x57")
        self.assertEqual(result, "OK")


# ---------------------------------------------------------------------------
# Tests: state()
# ---------------------------------------------------------------------------


class TestState(unittest.TestCase):
    def _make(self, response: str) -> HarnessClient:
        client, _ = _make_client_with_mock_socket(
            [f"STATE pid=1234 uptime=5000ms w=1920 h=1080\n".encode()]
            if response == "valid"
            else [response.encode() + b"\n"]
        )
        return client

    def test_state_happy_path(self) -> None:
        client, _ = _make_client_with_mock_socket(
            [b"STATE pid=1234 uptime=5000ms w=1920 h=1080\n"]
        )
        result = client.state()
        self.assertIsInstance(result, HarnessState)
        self.assertEqual(result.pid, 1234)
        self.assertEqual(result.uptime_ms, 5000)
        self.assertEqual(result.internal_w, 1920)
        self.assertEqual(result.internal_h, 1080)

    def test_state_different_values(self) -> None:
        client, _ = _make_client_with_mock_socket(
            [b"STATE pid=9999 uptime=120000ms w=2560 h=1440\n"]
        )
        result = client.state()
        self.assertEqual(result.pid, 9999)
        self.assertEqual(result.uptime_ms, 120000)
        self.assertEqual(result.internal_w, 2560)
        self.assertEqual(result.internal_h, 1440)

    def test_state_err_response_raises_command_error(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR INTERNAL_ERROR detail\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.state()
        self.assertEqual(ctx.exception.code, "INTERNAL_ERROR")

    def test_state_malformed_response_raises_protocol_error(self) -> None:
        client, _ = _make_client_with_mock_socket([b"STATE pid=bad_not_int\n"])
        with self.assertRaises(HarnessProtocolError):
            client.state()

    def test_state_unexpected_response_raises_protocol_error(self) -> None:
        client, _ = _make_client_with_mock_socket([b"GARBAGE RESPONSE\n"])
        with self.assertRaises(HarnessProtocolError):
            client.state()


# ---------------------------------------------------------------------------
# Tests: key(), key_down(), key_up()
# ---------------------------------------------------------------------------


class TestKeyVerbs(unittest.TestCase):
    def test_key_wire_format(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.key(0x57)
        sent = sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY 0x57\n")

    def test_key_small_vk_format(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.key(0x01)
        sent = sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY 0x01\n")

    def test_key_err_raises_command_error(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR INVALID_VK\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.key(0xFF)
        self.assertEqual(ctx.exception.verb, "KEY")

    def test_key_down_wire_format(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.key_down(0x41)
        sent = sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY_DOWN 0x41\n")

    def test_key_down_err_raises(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR INVALID_VK\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.key_down(0x00)
        self.assertEqual(ctx.exception.verb, "KEY_DOWN")

    def test_key_up_wire_format(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.key_up(0x41)
        sent = sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY_UP 0x41\n")

    def test_key_up_err_raises(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR INVALID_VK\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.key_up(0x00)
        self.assertEqual(ctx.exception.verb, "KEY_UP")

    def test_key_shutting_down_raises_shutting_down_error(self) -> None:
        client, _ = _make_client_with_mock_socket(
            [b"ERR HARNESS_SHUTTING_DOWN\n"]
        )
        with self.assertRaises(HarnessShuttingDownError):
            client.key(0x57)


# ---------------------------------------------------------------------------
# Tests: move() and click()
# ---------------------------------------------------------------------------


class TestMoveClick(unittest.TestCase):
    def test_move_wire_format(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.move(50, 75)
        sent = sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "MOVE 50 75\n")

    def test_move_err_raises(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR OUT_OF_RANGE\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.move(99999, 99999)
        self.assertEqual(ctx.exception.verb, "MOVE")

    def test_click_wire_format(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.click(100, 200)
        sent = sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "CLICK 100 200\n")

    def test_click_err_raises(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR OUT_OF_RANGE\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.click(0, 0)
        self.assertEqual(ctx.exception.verb, "CLICK")

    def test_click_shutting_down(self) -> None:
        client, _ = _make_client_with_mock_socket(
            [b"ERR HARNESS_SHUTTING_DOWN\n"]
        )
        with self.assertRaises(HarnessShuttingDownError):
            client.click(960, 540)


# ---------------------------------------------------------------------------
# Tests: screenshot()
# ---------------------------------------------------------------------------


class TestScreenshot(unittest.TestCase):
    def test_screenshot_happy_path(self) -> None:
        client, sock = _make_client_with_mock_socket(
            [b"OK path=/tmp/frame.png bytes=12345\n"]
        )
        result = client.screenshot(Path("/tmp/frame.png"))
        self.assertIsInstance(result, ScreenshotResult)
        self.assertEqual(result.path, Path("/tmp/frame.png"))
        self.assertEqual(result.bytes_written, 12345)

    def test_screenshot_wire_format(self) -> None:
        client, sock = _make_client_with_mock_socket(
            [b"OK path=/tmp/frame.png bytes=1\n"]
        )
        client.screenshot("/tmp/frame.png")
        sent = sock.sendall.call_args[0][0].decode()
        self.assertTrue(sent.startswith("SCREENSHOT /tmp/frame.png\n"))

    def test_screenshot_timeout_error(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR TIMEOUT capture timed out\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.screenshot("/tmp/frame.png")
        self.assertEqual(ctx.exception.code, "TIMEOUT")

    def test_screenshot_failed_error(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR FAILED write error\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.screenshot("/tmp/frame.png")
        self.assertEqual(ctx.exception.code, "FAILED")

    def test_screenshot_invalid_path_error(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR INVALID_PATH\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.screenshot("/bad/path")
        self.assertEqual(ctx.exception.code, "INVALID_PATH")

    def test_screenshot_shutting_down(self) -> None:
        client, _ = _make_client_with_mock_socket(
            [b"ERR HARNESS_SHUTTING_DOWN\n"]
        )
        with self.assertRaises(HarnessShuttingDownError):
            client.screenshot("/tmp/frame.png")

    def test_screenshot_malformed_ok_response(self) -> None:
        client, _ = _make_client_with_mock_socket([b"OK no_fields_here\n"])
        with self.assertRaises(HarnessProtocolError):
            client.screenshot("/tmp/frame.png")


# ---------------------------------------------------------------------------
# Tests: quit()
# ---------------------------------------------------------------------------


class TestQuit(unittest.TestCase):
    def test_quit_sends_quit_command(self) -> None:
        client, sock = _make_client_with_mock_socket([b"OK\n"])
        client.quit()
        sent = sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "QUIT\n")

    def test_quit_swallows_connection_error(self) -> None:
        client = HarnessClient("/fake/path")
        mock_sock = MagicMock(spec=socket.socket)
        mock_sock.sendall.side_effect = OSError("pipe closed")
        client._sock = mock_sock
        client.quit()  # should not raise

    def test_quit_swallows_timeout_error(self) -> None:
        client = HarnessClient("/fake/path")
        mock_sock = MagicMock(spec=socket.socket)
        mock_sock.sendall.side_effect = socket.timeout("timed out")
        client._sock = mock_sock
        client.quit()  # should not raise


# ---------------------------------------------------------------------------
# Tests: mid-command disconnect
# ---------------------------------------------------------------------------


class TestMidCommandDisconnect(unittest.TestCase):
    def test_disconnect_during_state(self) -> None:
        """Server closes connection while client awaits STATE response."""
        server = _MockServer([("STATE", None)])  # None = close connection
        server.start()
        try:
            client = HarnessClient(server.socket_path)
            client.connect(timeout=5.0)
            with self.assertRaises(HarnessConnectionError):
                client.state()
        finally:
            server.stop()
            client.close()

    def test_reconnect_after_disconnect(self) -> None:
        """Client can reconnect after a mid-session disconnect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = Path(tmpdir) / "reconnect_test.sock"

            # First server: accepts and closes immediately
            srv1 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv1.bind(str(sock_path))
            srv1.listen(1)

            client = HarnessClient(sock_path)
            client.connect(timeout=5.0)
            # Accept on server side
            conn, _ = srv1.accept()
            conn.close()
            srv1.close()

            # Force the client side into disconnected state
            client.close()

            # Remove old socket file and start a new server on the same path
            try:
                sock_path.unlink()
            except FileNotFoundError:
                pass

            srv2 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv2.bind(str(sock_path))
            srv2.listen(1)

            def _accept_and_respond() -> None:
                try:
                    conn2, _ = srv2.accept()
                    # Respond to the STATE command
                    data = conn2.recv(4096)
                    if b"STATE" in data:
                        conn2.sendall(b"STATE pid=2 uptime=100ms w=1920 h=1080\n")
                    conn2.close()
                except OSError:
                    pass
                finally:
                    srv2.close()

            t = threading.Thread(target=_accept_and_respond, daemon=True)
            t.start()

            client.reconnect(timeout=5.0)
            state = client.state()
            self.assertEqual(state.pid, 2)
            client.close()
            t.join(timeout=2.0)


# ---------------------------------------------------------------------------
# Tests: malformed responses
# ---------------------------------------------------------------------------


class TestMalformedResponses(unittest.TestCase):
    def test_garbage_response_to_key(self) -> None:
        client, _ = _make_client_with_mock_socket([b"GIBBERISH 123\n"])
        with self.assertRaises(HarnessProtocolError):
            client.key(0x57)

    def test_garbage_response_to_move(self) -> None:
        client, _ = _make_client_with_mock_socket([b"NOPE\n"])
        with self.assertRaises(HarnessProtocolError):
            client.move(100, 100)

    def test_err_without_code_handled(self) -> None:
        client, _ = _make_client_with_mock_socket([b"ERR\n"])
        with self.assertRaises(HarnessCommandError) as ctx:
            client.click(0, 0)
        self.assertEqual(ctx.exception.code, "UNKNOWN")


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
