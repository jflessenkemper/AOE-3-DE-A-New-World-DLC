"""Unit tests for tools/aoe3_harness/dll_client.py.

All tests use mocked sockets so no game, Wine, or network is required.
Run with:
    cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
    python3 -m pytest tools/aoe3_harness/tests/test_dll_client.py -v

Coverage target: 100% line coverage of dll_client.py except for the real
socket.connect() call (which is always mocked out).
"""

from __future__ import annotations

import os
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Ensure the repo root is on sys.path so we can import the package directly.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_harness.dll_client import (  # noqa: E402
    DllClient,
    DllClientError,
    get_pipe_socket_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_socket(responses: list[bytes]) -> MagicMock:
    """Return a mock socket whose recv() yields successive response bytes.

    Each element of *responses* is one raw bytes value returned by recv().
    When the list is exhausted recv() returns b'' (simulating EOF).
    """
    sock = MagicMock(spec=socket.socket)
    sock.recv.side_effect = responses + [b""]
    return sock


def _client_with_mock_socket(mock_sock: MagicMock) -> DllClient:
    """Return a DllClient instance that already has mock_sock wired in."""
    client = DllClient(pfx="/fake/pfx")
    client._sock = mock_sock
    return client


# ---------------------------------------------------------------------------
# Test: get_pipe_socket_path
# ---------------------------------------------------------------------------

class TestGetPipeSocketPath(unittest.TestCase):
    def test_path_format(self) -> None:
        """Path is /tmp/.wine-<uid>/server-<dev_minor_hex>-<inode_hex>/pipe/<name>."""
        fake_stat = MagicMock()
        fake_stat.st_dev = os.makedev(0, 0x23)   # minor = 0x23
        fake_stat.st_ino = 0x12e354e
        with patch("os.stat", return_value=fake_stat), \
             patch("os.getuid", return_value=1000):
            path = get_pipe_socket_path("anwhook", pfx="/fake/pfx")
        self.assertEqual(path, "/tmp/.wine-1000/server-23-12e354e/pipe/anwhook")

    def test_pipe_name_lowercased(self) -> None:
        fake_stat = MagicMock()
        fake_stat.st_dev = os.makedev(0, 1)
        fake_stat.st_ino = 1
        with patch("os.stat", return_value=fake_stat), \
             patch("os.getuid", return_value=1000):
            path = get_pipe_socket_path("AnwHook", pfx="/fake/pfx")
        self.assertTrue(path.endswith("/pipe/anwhook"))

    def test_missing_pfx_raises(self) -> None:
        with patch("os.stat", side_effect=FileNotFoundError("no such dir")):
            with self.assertRaises(FileNotFoundError):
                get_pipe_socket_path("anwhook", pfx="/nonexistent/pfx")

    def test_default_pfx_is_used_when_none(self) -> None:
        """When pfx=None, the function uses the default AoE3 prefix path."""
        fake_stat = MagicMock()
        fake_stat.st_dev = os.makedev(0, 0x23)
        fake_stat.st_ino = 0x1
        with patch("os.stat", return_value=fake_stat) as mock_stat, \
             patch("os.getuid", return_value=1000):
            get_pipe_socket_path("anwhook", pfx=None)
        # stat should have been called with the default prefix path
        called_path = mock_stat.call_args[0][0]
        self.assertIn("933110", called_path)


# ---------------------------------------------------------------------------
# Test: DllClient.connect() — retry with exponential backoff
# ---------------------------------------------------------------------------

class TestConnect(unittest.TestCase):
    def _fake_stat(self) -> MagicMock:
        st = MagicMock()
        st.st_dev = os.makedev(0, 1)
        st.st_ino = 1
        return st

    def test_connect_retries_5x_on_socket_missing(self) -> None:
        """connect() should attempt exactly *retries* times before raising ConnectionError."""
        with patch("os.stat", return_value=self._fake_stat()), \
             patch("os.getuid", return_value=1000), \
             patch("socket.socket") as mock_sock_cls, \
             patch("time.sleep") as mock_sleep:
            instance = MagicMock()
            instance.connect.side_effect = FileNotFoundError("socket not found")
            mock_sock_cls.return_value = instance

            client = DllClient(pfx="/fake/pfx")
            with self.assertRaises(ConnectionError) as ctx:
                client.connect(retries=5)

        self.assertIn("5 attempts", str(ctx.exception))
        self.assertEqual(instance.connect.call_count, 5)

    def test_connect_exponential_backoff_delays(self) -> None:
        """Backoff delays double each attempt: 0.5, 1.0, 2.0, 4.0 seconds."""
        with patch("os.stat", return_value=self._fake_stat()), \
             patch("os.getuid", return_value=1000), \
             patch("socket.socket") as mock_sock_cls, \
             patch("time.sleep") as mock_sleep:
            instance = MagicMock()
            instance.connect.side_effect = ConnectionRefusedError("refused")
            mock_sock_cls.return_value = instance

            client = DllClient(pfx="/fake/pfx")
            with self.assertRaises(ConnectionError):
                client.connect(retries=5)

        # 4 sleeps for 5 attempts (no sleep after the last attempt)
        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls, [0.5, 1.0, 2.0, 4.0])

    def test_connect_succeeds_on_first_attempt(self) -> None:
        with patch("os.stat", return_value=self._fake_stat()), \
             patch("os.getuid", return_value=1000), \
             patch("socket.socket") as mock_sock_cls, \
             patch("time.sleep") as mock_sleep:
            instance = MagicMock()
            instance.connect.return_value = None  # success
            mock_sock_cls.return_value = instance

            client = DllClient(pfx="/fake/pfx")
            client.connect(retries=5)

        mock_sleep.assert_not_called()
        self.assertIs(client._sock, instance)

    def test_connect_succeeds_on_third_attempt(self) -> None:
        with patch("os.stat", return_value=self._fake_stat()), \
             patch("os.getuid", return_value=1000), \
             patch("socket.socket") as mock_sock_cls, \
             patch("time.sleep"):
            instances = [MagicMock() for _ in range(3)]
            instances[0].connect.side_effect = FileNotFoundError("not yet")
            instances[1].connect.side_effect = FileNotFoundError("not yet")
            instances[2].connect.return_value = None  # 3rd succeeds
            mock_sock_cls.side_effect = instances

            client = DllClient(pfx="/fake/pfx")
            client.connect(retries=5)

        self.assertIs(client._sock, instances[2])

    def test_backoff_caps_at_8_seconds(self) -> None:
        """Delay should not exceed 8 seconds regardless of retry count."""
        with patch("os.stat", return_value=self._fake_stat()), \
             patch("os.getuid", return_value=1000), \
             patch("socket.socket") as mock_sock_cls, \
             patch("time.sleep") as mock_sleep:
            instance = MagicMock()
            instance.connect.side_effect = ConnectionRefusedError("refused")
            mock_sock_cls.return_value = instance

            client = DllClient(pfx="/fake/pfx")
            with self.assertRaises(ConnectionError):
                client.connect(retries=8)

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertTrue(all(d <= 8.0 for d in sleep_calls))
        # After doubling: 0.5, 1.0, 2.0, 4.0, 8.0, 8.0, 8.0
        self.assertEqual(sleep_calls[-1], 8.0)


# ---------------------------------------------------------------------------
# Test: DllClient._send() — wire format
# ---------------------------------------------------------------------------

class TestSend(unittest.TestCase):
    def test_send_appends_crlf(self) -> None:
        """_send() must append \\r\\n to the command before sending."""
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client._send("STATE")
        mock_sock.sendall.assert_called_once_with(b"STATE\r\n")

    def test_send_reads_until_crlf(self) -> None:
        """_send() assembles recv() chunks until \\r\\n is seen."""
        # Response split across two recv() calls
        mock_sock = _make_mock_socket([b"ALI", b"VE pid=1234\r\n"])
        client = _client_with_mock_socket(mock_sock)
        result = client._send("STATE")
        self.assertEqual(result, "ALIVE pid=1234")

    def test_send_strips_crlf_from_response(self) -> None:
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        result = client._send("KEY 0x57")
        self.assertEqual(result, "OK")

    def test_send_decodes_utf8_ascii(self) -> None:
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        result = client._send("STATE")
        self.assertIsInstance(result, str)

    def test_send_raises_on_empty_recv(self) -> None:
        """If recv() returns b'' (connection closed), _send() raises ConnectionError."""
        mock_sock = _make_mock_socket([b""])  # immediate EOF
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(ConnectionError):
            client._send("STATE")

    def test_send_raises_when_not_connected(self) -> None:
        client = DllClient(pfx="/fake/pfx")
        # _sock is None (never connected)
        with self.assertRaises(RuntimeError) as ctx:
            client._send("STATE")
        self.assertIn("connect()", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test: screenshot() — path translation
# ---------------------------------------------------------------------------

class TestScreenshot(unittest.TestCase):
    def test_screenshot_translates_linux_path_to_z_drive(self) -> None:
        """screenshot() must convert /tmp/frame.bgra → Z:\\tmp\\frame.bgra on the wire."""
        mock_sock = _make_mock_socket([b"OK Z:\\tmp\\frame.bgra\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.screenshot(Path("/tmp/frame.bgra"))
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertTrue(sent.startswith("SCREENSHOT Z:\\tmp\\frame.bgra\r\n"),
                        f"Unexpected wire bytes: {sent!r}")

    def test_screenshot_nested_path(self) -> None:
        """Deep paths like /home/user/frames/001.bgra → Z:\\home\\user\\frames\\001.bgra."""
        mock_sock = _make_mock_socket([b"OK Z:\\home\\user\\frames\\001.bgra\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.screenshot(Path("/home/user/frames/001.bgra"))
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertIn("Z:\\home\\user\\frames\\001.bgra", sent)

    def test_screenshot_raises_on_err_response(self) -> None:
        mock_sock = _make_mock_socket([b"ERR DXGI_NOT_IMPLEMENTED\r\n"])
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(DllClientError) as ctx:
            client.screenshot(Path("/tmp/frame.bgra"))
        self.assertIn("DXGI_NOT_IMPLEMENTED", str(ctx.exception))

    def test_screenshot_ok_response(self) -> None:
        """screenshot() should not raise when the DLL returns OK."""
        mock_sock = _make_mock_socket([b"OK Z:\\tmp\\frame.bgra\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.screenshot(Path("/tmp/frame.bgra"))  # should not raise


# ---------------------------------------------------------------------------
# Test: press_key() — wire format
# ---------------------------------------------------------------------------

class TestPressKey(unittest.TestCase):
    def test_press_key_formats_hex_correctly(self) -> None:
        """press_key(0x57) must send 'KEY 0x57\\r\\n' on the wire."""
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.press_key(0x57)
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY 0x57\r\n")

    def test_press_key_formats_small_vk(self) -> None:
        """VK < 0x10 should still have leading zero: 0x01 → '0x01'."""
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.press_key(0x01)
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY 0x01\r\n")

    def test_press_key_raises_on_err(self) -> None:
        mock_sock = _make_mock_socket([b"ERR invalid vk\r\n"])
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(DllClientError):
            client.press_key(0x57)

    def test_key_down_wire_format(self) -> None:
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.key_down(0x41)
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY_DOWN 0x41\r\n")

    def test_key_up_wire_format(self) -> None:
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.key_up(0x41)
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "KEY_UP 0x41\r\n")

    def test_key_down_raises_on_err(self) -> None:
        mock_sock = _make_mock_socket([b"ERR invalid vk\r\n"])
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(DllClientError) as ctx:
            client.key_down(0x00)
        self.assertIn("KEY_DOWN failed", str(ctx.exception))

    def test_key_up_raises_on_err(self) -> None:
        mock_sock = _make_mock_socket([b"ERR invalid vk\r\n"])
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(DllClientError) as ctx:
            client.key_up(0x00)
        self.assertIn("KEY_UP failed", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test: click() — wire format and response parsing
# ---------------------------------------------------------------------------

class TestClick(unittest.TestCase):
    def test_click_sends_correct_wire_format(self) -> None:
        """click(100, 200) must send 'CLICK 100 200\\r\\n'."""
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.click(100, 200)
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "CLICK 100 200\r\n")

    def test_click_parses_ok_response(self) -> None:
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.click(960, 540)  # should not raise

    def test_click_raises_on_err(self) -> None:
        mock_sock = _make_mock_socket([b"ERR expected CLICK <x> <y>\r\n"])
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(DllClientError) as ctx:
            client.click(100, 200)
        self.assertIn("CLICK failed", str(ctx.exception))

    def test_move_wire_format(self) -> None:
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.move(50, 75)
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "MOVE 50 75\r\n")

    def test_move_raises_on_err(self) -> None:
        mock_sock = _make_mock_socket([b"ERR expected MOVE <x> <y>\r\n"])
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(DllClientError) as ctx:
            client.move(50, 75)
        self.assertIn("MOVE failed", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test: context manager (__enter__ / __exit__)
# ---------------------------------------------------------------------------

class TestContextManager(unittest.TestCase):
    def _fake_stat(self) -> MagicMock:
        st = MagicMock()
        st.st_dev = os.makedev(0, 1)
        st.st_ino = 1
        return st

    def test_enter_calls_connect(self) -> None:
        with patch("os.stat", return_value=self._fake_stat()), \
             patch("os.getuid", return_value=1000), \
             patch("socket.socket") as mock_sock_cls:
            instance = MagicMock()
            instance.connect.return_value = None
            mock_sock_cls.return_value = instance

            client = DllClient(pfx="/fake/pfx")
            with patch.object(client, "connect") as mock_connect, \
                 patch.object(client, "close") as mock_close:
                result = client.__enter__()
                self.assertIs(result, client)
                mock_connect.assert_called_once_with()

    def test_exit_calls_close(self) -> None:
        client = DllClient(pfx="/fake/pfx")
        with patch.object(client, "connect"), \
             patch.object(client, "close") as mock_close:
            with client:
                pass
            mock_close.assert_called_once_with()

    def test_exit_calls_close_even_on_exception(self) -> None:
        client = DllClient(pfx="/fake/pfx")
        with patch.object(client, "connect"), \
             patch.object(client, "close") as mock_close:
            try:
                with client:
                    raise RuntimeError("test error")
            except RuntimeError:
                pass
            mock_close.assert_called_once_with()

    def test_close_is_idempotent(self) -> None:
        """Calling close() twice should not raise."""
        mock_sock = MagicMock()
        client = DllClient(pfx="/fake/pfx")
        client._sock = mock_sock
        client.close()
        client.close()  # second call — _sock is None, should not raise
        self.assertIsNone(client._sock)

    def test_close_swallows_oserror(self) -> None:
        """close() swallows OSError from sock.close() (already-closed socket)."""
        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("already closed")
        client = DllClient(pfx="/fake/pfx")
        client._sock = mock_sock
        client.close()  # should not raise
        self.assertIsNone(client._sock)


# ---------------------------------------------------------------------------
# Test: state() — response parsing
# ---------------------------------------------------------------------------

class TestState(unittest.TestCase):
    def test_state_parses_alive_response(self) -> None:
        """state() must return the full 'ALIVE pid=12345 tick=0' string."""
        mock_sock = _make_mock_socket([b"ALIVE pid=12345 tick=0\r\n"])
        client = _client_with_mock_socket(mock_sock)
        result = client.state()
        self.assertEqual(result, "ALIVE pid=12345 tick=0")

    def test_state_raises_on_unexpected_response(self) -> None:
        mock_sock = _make_mock_socket([b"ERR worker crashed\r\n"])
        client = _client_with_mock_socket(mock_sock)
        with self.assertRaises(DllClientError) as ctx:
            client.state()
        self.assertIn("Unexpected STATE response", str(ctx.exception))

    def test_state_extracts_pid(self) -> None:
        mock_sock = _make_mock_socket([b"ALIVE pid=99999 tick=0\r\n"])
        client = _client_with_mock_socket(mock_sock)
        resp = client.state()
        self.assertIn("pid=99999", resp)


# ---------------------------------------------------------------------------
# Test: quit()
# ---------------------------------------------------------------------------

class TestQuit(unittest.TestCase):
    def test_quit_sends_quit_command(self) -> None:
        mock_sock = _make_mock_socket([b"OK\r\n"])
        client = _client_with_mock_socket(mock_sock)
        client.quit()
        sent = mock_sock.sendall.call_args[0][0].decode()
        self.assertEqual(sent, "QUIT\r\n")

    def test_quit_does_not_raise_on_connection_error(self) -> None:
        """quit() swallows ConnectionError (server closes pipe on QUIT)."""
        mock_sock = MagicMock()
        mock_sock.sendall.side_effect = ConnectionError("pipe closed")
        client = _client_with_mock_socket(mock_sock)
        client.quit()  # should not raise


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
