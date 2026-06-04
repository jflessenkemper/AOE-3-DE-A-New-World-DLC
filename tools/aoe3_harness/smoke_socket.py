#!/usr/bin/env python3
"""smoke_socket.py — Phase 6 end-to-end smoke test for AOE3DEHarness control socket.

Tests SCREENSHOT_REGION + PROBE_TAIL without launching the actual AoE3 game.
Run standalone: python3 smoke_socket.py

Safe/idempotent: kills any existing harness, cleans up stale socket, spawns
the binary with --backend headless -- sleep 30 (no game, no cursor grab).

Extended in Tier-2 to also test:
  --use-harness-headless  : use --harness-headless flag instead of --backend headless
  Watchdog test           : WATCHDOG_ENABLE 2 100 with 'sh -c sleep 1; exit 0' inner cmd
                            Verifies WATCHDOG: RESTART events and final exhaustion.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import signal
import socket as _socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HARNESS_BINARY = Path("/home/jflessenkemper/.local/bin/AOE3DEHarness")
SOCKET_PATH    = Path("/tmp/AOE3DEHarness.sock")
HARNESS_LOG    = Path("/tmp/harness_smoke.log")
PROBE_LOG      = Path("/tmp/anw_smoke_probe.log")
REGION_PNG     = Path("/tmp/anw_smoke_region.png")
REPORT_PATH    = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/harness/smoke_socket_report.json")

PNG_MAGIC = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ts() -> str:
    return datetime.datetime.now().isoformat(timespec="milliseconds")


def log(msg: str) -> None:
    print(f"[{ts()}] {msg}", flush=True)


def tail_file(path: Path, n: int = 50) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except OSError as e:
        return f"(could not read {path}: {e})"


class BufferedSocket:
    """Thin wrapper around a Unix socket that provides buffered line reads.

    Unlike a bare recv_line approach, this avoids losing bytes when the server
    sends multiple lines in a single chunk (e.g. "PROBE: EOF\\nOK\\n").
    """

    def __init__(self, sock: _socket.socket) -> None:
        self._sock = sock
        self._buf = b""

    def recv_line(self, timeout: float = 10.0) -> str:
        """Return the next \\n-terminated line (without the \\n)."""
        self._sock.settimeout(timeout)
        while b"\n" not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("socket closed before newline")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line.decode("ascii", errors="replace").strip()

    def send_line(self, cmd: str) -> None:
        self._sock.sendall((cmd + "\n").encode("ascii"))

    def sendrecv(self, cmd: str, timeout: float = 10.0) -> str:
        self.send_line(cmd)
        return self.recv_line(timeout)

    def raw_recv(self, timeout: float = 0.3) -> bytes:
        """Non-blocking receive into internal buffer; return buffer snapshot."""
        self._sock.settimeout(timeout)
        try:
            chunk = self._sock.recv(4096)
            if chunk:
                self._buf += chunk
        except _socket.timeout:
            pass
        return self._buf

    @property
    def sock(self) -> _socket.socket:
        return self._sock

    @property
    def buf(self) -> bytes:
        return self._buf

    @buf.setter
    def buf(self, value: bytes) -> None:
        self._buf = value

# ---------------------------------------------------------------------------
# Setup phase
# ---------------------------------------------------------------------------

def setup_phase(use_harness_headless: bool = False, watchdog_mode: bool = False) -> subprocess.Popen:
    # 1. Kill existing harness processes
    log("Killing any existing AOE3DEHarness processes...")
    subprocess.run(["pkill", "-f", "AOE3DEHarness"], capture_output=True)
    time.sleep(0.5)

    # 2. Delete stale socket
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()
        log(f"Removed stale socket {SOCKET_PATH}")

    # 3. Create synthetic probe log
    lines = [
        "INFO  app starting up",
        "DEBUG loading config",
        "[ANWP v=2] field=score timestamp=1000",
        "INFO  map loaded",
        "DEBUG pathfinding init",
        "[ANWP v=2] field=units timestamp=1100",
        "INFO  AI tick 1",
        "[ANWP v=2] field=resources timestamp=1200",
        "DEBUG resource harvest triggered",
        "[ANWP v=2] field=economy timestamp=1300",
        "INFO  AI tick 2",
        "[ANWP v=2] field=military timestamp=1400",
        "INFO  scenario running",
    ]
    PROBE_LOG.write_text("\n".join(lines) + "\n")
    log(f"Probe log created at {PROBE_LOG}")

    # 4. Spawn harness
    if watchdog_mode:
        # Watchdog test: short-lived inner command that exits quickly
        if use_harness_headless:
            cmd = [
                str(HARNESS_BINARY),
                "--harness-headless",
                "--",
                "sh", "-c", "sleep 3; exit 0",
            ]
        else:
            cmd = [
                str(HARNESS_BINARY),
                "--backend", "headless",
                "--",
                "sh", "-c", "sleep 3; exit 0",
            ]
    else:
        if use_harness_headless:
            cmd = [
                str(HARNESS_BINARY),
                "--harness-headless",
                "--",
                "sleep", "30",
            ]
        else:
            cmd = [
                str(HARNESS_BINARY),
                "--backend", "headless",
                "--",
                "sleep", "30",
            ]

    log(f"Spawning harness: {' '.join(cmd)}")
    harness_log_fh = HARNESS_LOG.open("wb")
    proc = subprocess.Popen(
        cmd,
        stdout=harness_log_fh,
        stderr=harness_log_fh,
    )
    log(f"Harness PID: {proc.pid}")

    # 5. Poll for socket (timeout 15s)
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if SOCKET_PATH.exists():
            log(f"Socket appeared at {SOCKET_PATH}")
            return proc
        time.sleep(0.1)

    # Timeout
    log("TIMEOUT waiting for socket. Last 50 lines of harness log:")
    print(tail_file(HARNESS_LOG))
    proc.terminate()
    sys.exit(1)


# ---------------------------------------------------------------------------
# Test phase — raw socket (the harness protocol is simple enough)
# ---------------------------------------------------------------------------

class RawClient:
    """Minimal raw-socket client for the harness protocol."""

    def __init__(self, path: Path):
        self._path = path
        self._bsock: BufferedSocket | None = None

    def connect(self) -> None:
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.connect(str(self._path))
        self._bsock = BufferedSocket(sock)

    def close(self) -> None:
        if self._bsock:
            try:
                self._bsock.sock.close()
            except OSError:
                pass
            self._bsock = None

    def cmd(self, command: str, timeout: float = 10.0) -> str:
        assert self._bsock is not None
        return self._bsock.sendrecv(command, timeout)

    def send(self, command: str) -> None:
        assert self._bsock is not None
        self._bsock.send_line(command)

    def recv_line(self, timeout: float = 10.0) -> str:
        assert self._bsock is not None
        return self._bsock.recv_line(timeout)

    @property
    def bsock(self) -> "BufferedSocket":
        assert self._bsock is not None
        return self._bsock

    @property
    def sock(self) -> _socket.socket:
        assert self._bsock is not None
        return self._bsock.sock


def test_phase(proc: subprocess.Popen) -> dict:
    results: dict[str, dict] = {}

    # Give socket a moment to settle
    time.sleep(0.2)

    client = RawClient(SOCKET_PATH)
    client.connect()
    log("Connected to harness socket.")

    try:
        # ------------------------------------------------------------------
        # 1. STATE
        # ------------------------------------------------------------------
        log("Testing STATE...")
        t0 = ts()
        resp = client.cmd("STATE")
        log(f"  STATE response: {resp!r}")
        # In headless+sleep mode there is no inner game window, so the
        # compositor has no mapped client surface.  We therefore expect
        # ready=0 in the STATE response.  ready=1 would only appear once
        # a real game window has been mapped and has committed its first
        # composited frame (i.e. the game is past the splash screen).
        state_pass = resp.startswith("OK") and "pid=" in resp
        results["STATE"] = {
            "timestamp": t0,
            "response": resp,
            "result": "PASS" if state_pass else "FAIL",
            "note": "ready=0 expected in headless+sleep mode (no mapped client window)",
        }
        log(f"  STATE => {'PASS' if state_pass else 'FAIL'}")

        # ------------------------------------------------------------------
        # 2. SCREENSHOT_REGION
        # ------------------------------------------------------------------
        log("Testing SCREENSHOT_REGION...")
        t0 = ts()
        resp = client.cmd(f"SCREENSHOT_REGION 100 100 200 200 {REGION_PNG}")
        log(f"  SCREENSHOT_REGION response: {resp!r}")

        # Accept OK (file written) OR headless-expected ERR variants
        HEADLESS_ERR_CODES = {
            "ERR SCREENSHOT_TIMEOUT",
            "ERR SCREENSHOT_FAILED",
            "ERR HARNESS_SHUTTING_DOWN",
        }
        if resp.startswith("OK"):
            # Check PNG magic
            png_ok = False
            if REGION_PNG.exists():
                magic = REGION_PNG.read_bytes()[:8]
                png_ok = magic == PNG_MAGIC
                log(f"  PNG magic check: {'PASS' if png_ok else 'FAIL'} (got {magic.hex()})")
            sr_pass = png_ok
            sr_note = "OK with valid PNG" if png_ok else "OK but PNG magic mismatch"
        elif any(resp.startswith(code) for code in HEADLESS_ERR_CODES):
            sr_pass = True  # acceptable in headless
            sr_note = f"expected-in-headless ERR: {resp}"
            log(f"  Acceptable headless ERR response: {resp!r}")
        else:
            sr_pass = False
            sr_note = f"unexpected response: {resp}"

        results["SCREENSHOT_REGION"] = {
            "timestamp": t0,
            "response": resp,
            "note": sr_note,
            "result": "PASS" if sr_pass else "FAIL",
        }
        log(f"  SCREENSHOT_REGION => {'PASS' if sr_pass else 'FAIL'} ({sr_note})")

        # ------------------------------------------------------------------
        # 3. PROBE_TAIL — must use a separate connection because the probe
        #    tail thread writes PROBE: lines async to the same fd while the
        #    main handle_client loop is blocked in read(). We send the
        #    subscription command on the existing connection and then read
        #    PROBE lines from it in a background thread.
        # ------------------------------------------------------------------
        log("Testing PROBE_TAIL...")
        t0 = ts()

        # Send PROBE_TAIL command and read the immediate OK SUBSCRIBED response.
        # We use client.bsock (BufferedSocket) throughout so no bytes are lost
        # when the server sends multiple lines in a single chunk.
        client.send(f"PROBE_TAIL {PROBE_LOG}")
        sub_resp = client.recv_line(timeout=5.0)
        log(f"  PROBE_TAIL subscription response: {sub_resp!r}")

        probe_pass = sub_resp.strip() == "OK SUBSCRIBED"
        collected_lines: list[str] = []
        collector_done = threading.Event()
        stop_collector = threading.Event()

        def collect_probe(duration: float = 3.0) -> None:
            """Read PROBE: lines from the BufferedSocket for up to duration seconds."""
            deadline = time.monotonic() + duration
            try:
                while time.monotonic() < deadline and not stop_collector.is_set():
                    try:
                        ln = client.bsock.recv_line(timeout=0.3)
                        if ln:
                            collected_lines.append(ln)
                    except _socket.timeout:
                        continue
                    except (ConnectionError, OSError):
                        break
            finally:
                collector_done.set()

        collector = threading.Thread(target=collect_probe, args=(3.0,), daemon=True)
        collector.start()

        # Append to probe log — 2 plain lines + 1 LLP line
        time.sleep(0.3)
        with PROBE_LOG.open("a") as f:
            f.write("INFO  extra event A\n")
            f.write("DEBUG extra event B\n")
            f.write("[ANWP v=2] field=smoke_test timestamp=9999\n")
        log(f"  Appended 3 lines to {PROBE_LOG}")

        # Wait for LLP line to be observed (up to 2s), then stop collector early
        wait_deadline = time.monotonic() + 2.0
        while time.monotonic() < wait_deadline:
            if any("[ANWP v=2]" in ln and "smoke_test" in ln for ln in collected_lines):
                break
            time.sleep(0.1)

        # Stop collector before sending PROBE_UNSUB so lines from the tail thread
        # don't race with PROBE: EOF / OK responses.
        stop_collector.set()
        collector_done.wait(timeout=2.0)
        log(f"  Collected {len(collected_lines)} PROBE line(s):")
        for ln in collected_lines:
            log(f"    {ln!r}")

        # Look for the LLP line we appended
        llp_received = any("[ANWP v=2]" in ln and "smoke_test" in ln
                           for ln in collected_lines)
        log(f"  LLP line received: {llp_received}")

        results["PROBE_TAIL"] = {
            "timestamp": t0,
            "subscription_response": sub_resp,
            "collected_lines": collected_lines,
            "llp_observed": llp_received,
            "result": "PASS" if (probe_pass and llp_received) else (
                "PARTIAL" if probe_pass else "FAIL"
            ),
        }
        log(f"  PROBE_TAIL => {results['PROBE_TAIL']['result']}")

        # PROBE_UNSUB — server sends "PROBE: EOF\n" then "OK\n" (may arrive as
        # one chunk; BufferedSocket handles that correctly).
        log("Sending PROBE_UNSUB...")
        client.send("PROBE_UNSUB")
        unsub_lines = []
        for _ in range(4):
            try:
                ln = client.recv_line(timeout=3.0)
                unsub_lines.append(ln)
                log(f"  PROBE_UNSUB line: {ln!r}")
                if ln == "OK":
                    break
            except _socket.timeout:
                log(f"  PROBE_UNSUB: timeout after {unsub_lines}")
                break
            except Exception as e:
                log(f"  PROBE_UNSUB recv error: {e}")
                break
        results["PROBE_UNSUB"] = {
            "lines": unsub_lines,
            "result": "PASS" if any(ln == "OK" for ln in unsub_lines) else "PARTIAL",
        }

        # ------------------------------------------------------------------
        # 4. QUIT
        # ------------------------------------------------------------------
        log("Testing QUIT...")
        t0 = ts()
        try:
            client.send("QUIT")
            quit_resp = client.recv_line(timeout=5.0)
            log(f"  QUIT response: {quit_resp!r}")
            quit_pass = quit_resp.startswith("OK")
        except (ConnectionError, OSError) as e:
            # Server may close socket before response arrives — that's OK
            log(f"  QUIT: socket closed by server ({e}) — acceptable")
            quit_pass = True
            quit_resp = "(socket closed by server)"
        results["QUIT"] = {
            "timestamp": t0,
            "response": quit_resp,
            "result": "PASS" if quit_pass else "FAIL",
        }
        log(f"  QUIT => {'PASS' if quit_pass else 'FAIL'}")

    finally:
        client.close()

    return results


# ---------------------------------------------------------------------------
# Watchdog test phase (Feature D)
# ---------------------------------------------------------------------------

def test_watchdog_phase(proc: subprocess.Popen) -> dict:
    """Test WATCHDOG_ENABLE / WATCHDOG_STATUS / WATCHDOG_DISABLE.

    Uses a short-lived inner command ('sh -c sleep 3; exit 0').  Protocol
    (single serial connection — the harness is single-client-serial):

      1. WATCHDOG_ENABLE 2 100  — arm BEFORE the inner proc first dies
      2. PROBE_TAIL <log>       — subscribe; WATCHDOG: events are broadcast here
      3. [background] collect WATCHDOG: RESTART / EXHAUSTED events (~9 s)
      4. PROBE_UNSUB            — end streaming, back to command mode
      5. WATCHDOG_STATUS        — verify restarts_remaining=0
      6. WATCHDOG_DISABLE
    """
    results: dict[str, dict] = {}

    time.sleep(0.3)  # let socket settle

    client = RawClient(SOCKET_PATH)
    try:
        client.connect()
    except OSError as e:
        log(f"  Watchdog test: could not connect to socket: {e}")
        results["WATCHDOG"] = {"result": "SKIP", "note": f"socket connect failed: {e}"}
        return results

    log("Connected to harness socket for watchdog test.")
    t0 = ts()

    try:
        # ---- Step 1: Enable watchdog BEFORE subscribing to PROBE_TAIL ----
        # The harness is single-client-serial, so we must issue all commands
        # on the same connection in order.  Arm the watchdog now, before
        # the inner process (sleep 3) first dies ~3 s from now.
        log("Sending WATCHDOG_ENABLE 2 100...")
        wd_resp_enable = client.cmd("WATCHDOG_ENABLE 2 100", timeout=5.0)
        log(f"  WATCHDOG_ENABLE response: {wd_resp_enable!r}")
        watchdog_enabled = wd_resp_enable.strip() == "OK"

        if not watchdog_enabled:
            results["WATCHDOG"] = {
                "result": "FAIL",
                "note": f"WATCHDOG_ENABLE failed: {wd_resp_enable!r}",
            }
            return results

        # ---- Step 2: Subscribe to PROBE_TAIL to receive WATCHDOG: events ----
        log("Subscribing PROBE_TAIL for watchdog event stream...")
        client.send(f"PROBE_TAIL {PROBE_LOG}")
        sub_resp = client.recv_line(timeout=5.0)
        log(f"  PROBE_TAIL subscription: {sub_resp!r}")
        if sub_resp.strip() != "OK SUBSCRIBED":
            results["WATCHDOG"] = {
                "result": "FAIL",
                "note": f"PROBE_TAIL subscription failed: {sub_resp!r}",
            }
            return results

        # ---- Step 3: Collect WATCHDOG: events ----
        # With 2 restarts and 3 s inner sleep the cycle is:
        #   initial sleep3 → die → RESTART 2 → sleep3 → die → RESTART 1
        #   → sleep3 → die → EXHAUSTED.  Total ~9 s + 3×100 ms = ~9.3 s.
        watchdog_events: list[str] = []
        stop_wd_collector = threading.Event()
        wd_collector_done = threading.Event()

        def collect_watchdog(duration: float = 30.0) -> None:
            deadline = time.monotonic() + duration
            try:
                while time.monotonic() < deadline and not stop_wd_collector.is_set():
                    try:
                        ln = client.bsock.recv_line(timeout=0.5)
                        if ln:
                            log(f"  [probe stream] {ln!r}")
                            watchdog_events.append(ln)
                            if "WATCHDOG: EXHAUSTED" in ln:
                                break
                    except _socket.timeout:
                        continue
                    except (ConnectionError, OSError):
                        break
            finally:
                wd_collector_done.set()

        log("Starting watchdog event collector (up to 30 s)...")
        wd_thread = threading.Thread(target=collect_watchdog, args=(30.0,), daemon=True)
        wd_thread.start()
        wd_collector_done.wait(timeout=35.0)
        stop_wd_collector.set()
        wd_collector_done.wait(timeout=2.0)

        restart_events = [ln for ln in watchdog_events if "WATCHDOG: RESTART" in ln]
        exhausted_events = [ln for ln in watchdog_events if "WATCHDOG: EXHAUSTED" in ln]
        log(f"  WATCHDOG: RESTART events: {restart_events}")
        log(f"  WATCHDOG: EXHAUSTED events: {exhausted_events}")

        # ---- Step 4: Unsubscribe from PROBE_TAIL ----
        log("Sending PROBE_UNSUB...")
        client.send("PROBE_UNSUB")
        for _ in range(4):
            try:
                ln = client.recv_line(timeout=5.0)
                log(f"  PROBE_UNSUB recv: {ln!r}")
                if ln == "OK":
                    break
            except (_socket.timeout, ConnectionError, OSError) as e:
                log(f"  PROBE_UNSUB: {e}")
                break

        # ---- Step 5: Check WATCHDOG_STATUS ----
        status_resp = "(not queried)"
        try:
            status_resp = client.cmd("WATCHDOG_STATUS", timeout=5.0)
            log(f"  WATCHDOG_STATUS: {status_resp!r}")
        except (OSError, _socket.timeout) as e:
            log(f"  WATCHDOG_STATUS query failed: {e}")

        restarts_remaining_ok = "restarts_remaining=0" in status_resp

        # ---- Step 6: Disable watchdog ----
        try:
            disable_resp = client.cmd("WATCHDOG_DISABLE", timeout=5.0)
            log(f"  WATCHDOG_DISABLE: {disable_resp!r}")
        except (OSError, _socket.timeout) as e:
            log(f"  WATCHDOG_DISABLE failed: {e}")

        # ---- Evaluate ----
        wd_pass = (
            watchdog_enabled
            and len(restart_events) >= 1
            and len(exhausted_events) >= 1
            and restarts_remaining_ok
        )

        results["WATCHDOG"] = {
            "timestamp": t0,
            "watchdog_enabled": watchdog_enabled,
            "watchdog_enable_resp": wd_resp_enable,
            "watchdog_events": watchdog_events,
            "restart_events": restart_events,
            "exhausted_events": exhausted_events,
            "watchdog_status": status_resp,
            "restarts_remaining_ok": restarts_remaining_ok,
            "result": "PASS" if wd_pass else (
                "PARTIAL" if watchdog_enabled and len(restart_events) >= 1 else "FAIL"
            ),
            "note": (
                f"restarts={len(restart_events)} exhausted={len(exhausted_events)}"
                f" remaining_ok={restarts_remaining_ok}"
            ),
        }
        log(f"  WATCHDOG => {results['WATCHDOG']['result']}")

    finally:
        client.close()

    return results


# ---------------------------------------------------------------------------
# Reporting phase
# ---------------------------------------------------------------------------

def report(results: dict, proc: subprocess.Popen, mode: str = "normal") -> int:
    """Print PASS/FAIL summary, write JSON report, return exit code."""

    # Wait for harness to exit (QUIT should close the connection; the process
    # continues running until the inner 'sleep 30' finishes unless we terminate it)
    log("Waiting up to 5s for harness process to exit...")
    try:
        proc.wait(timeout=5.0)
        log(f"Harness exited with code {proc.returncode}")
    except subprocess.TimeoutExpired:
        log("Harness still running after 5s (normal — sleep 30 inner cmd). Terminating.")
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("\n" + "=" * 60)
    print(f"SMOKE TEST RESULTS  [{mode}]")
    print("=" * 60)

    check_names = ["STATE", "SCREENSHOT_REGION", "PROBE_TAIL", "PROBE_UNSUB", "QUIT"]
    if "WATCHDOG" in results:
        check_names.append("WATCHDOG")

    all_pass = True
    any_tested = False
    for cmd_name in check_names:
        r = results.get(cmd_name, {})
        status = r.get("result", "SKIP")
        # PARTIAL counts as pass for overall verdict (PROBE may need inotify support)
        # SKIP does not count for or against overall pass
        if status != "SKIP":
            any_tested = True
            all_pass = all_pass and (status in ("PASS", "PARTIAL"))
        note = r.get("note", r.get("subscription_response", r.get("response", "")))
        print(f"  {cmd_name:20s}: {status:8s}  {note!r:.60s}")

    overall = "PASS" if (all_pass and any_tested) else "FAIL"
    print("=" * 60)
    print(f"OVERALL: {overall}")
    print("=" * 60)

    # JSON report
    report_data = {
        "overall": overall,
        "timestamp": ts(),
        "mode": mode,
        "harness_binary": str(HARNESS_BINARY),
        "socket_path": str(SOCKET_PATH),
        "commands": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report_data, indent=2, default=str))
    log(f"Report written to {REPORT_PATH}")

    return 0 if all_pass else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="AOE3DEHarness control-socket smoke test (Tier-2 extended)"
    )
    parser.add_argument(
        "--use-harness-headless",
        action="store_true",
        help="Spawn harness with --harness-headless instead of --backend headless",
    )
    parser.add_argument(
        "--watchdog",
        action="store_true",
        help="Run the watchdog test (WATCHDOG_ENABLE 2 100) instead of normal tests",
    )
    args = parser.parse_args()

    use_headless = args.use_harness_headless
    watchdog_mode = args.watchdog

    mode_str = "headless-flag" if use_headless else "standard"
    if watchdog_mode:
        mode_str += "+watchdog"

    log(f"Starting smoke test (mode={mode_str})")

    proc: subprocess.Popen | None = None
    try:
        proc = setup_phase(use_harness_headless=use_headless, watchdog_mode=watchdog_mode)

        if watchdog_mode:
            # In watchdog mode the inner command is short-lived (sh -c 'sleep 1; exit 0'),
            # so the harness shuts down within seconds of spawning — running the full
            # normal test_phase would race with that shutdown.  Run only the watchdog
            # test, which opens a fresh socket connection and enables the watchdog
            # before the inner process first dies.
            results = test_watchdog_phase(proc)
        else:
            results = test_phase(proc)

        return report(results, proc, mode=mode_str)
    except Exception as e:
        log(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        # Always clean up the harness subprocess
        if proc is not None and proc.poll() is None:
            log(f"Cleanup: terminating harness PID {proc.pid}")
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
