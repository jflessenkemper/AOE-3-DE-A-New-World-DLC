#!/usr/bin/env python3
"""game_safety.py — guardrails so AoE3 automation can never thrash the desktop.

Why this exists
---------------
On 2026-06-05 a long-running AoE3 (7-AI) match under Proton/gamescope leaked
memory until the system fell into swap-thrash and KDE's compositor hung — a
"1 frame per minute" freeze that forced a restart. The game is launched
DETACHED via `steam -applaunch`, so it is NOT a child of the controlling
script: a Python finally/atexit can't reliably kill it, and a `timeout`
SIGKILL of the controller skips cleanup entirely.

This module provides:
  * kill_game_stack()  — robust, CoH2-safe teardown of ONLY the AoE3 stack.
  * read_mem()         — MemAvailable / swap-used snapshot from /proc/meminfo.
  * watchdog()         — independent loop that kills the AoE3 stack the moment
                         memory gets tight, a runtime cap is hit, or the
                         controller's heartbeat goes stale (controller died).
  * GameSession        — context manager controllers use; spawns the watchdog
                         (detached) and beats a heartbeat, so the watchdog is
                         the backstop even if the controller is SIGKILL'd.

Run as a daemon:
    python3 -m tools.aoe3_automation.game_safety watch \
        --mem-floor-mb 2800 --swap-cap-mb 3000 --max-runtime-s 1200 \
        --heartbeat /tmp/anw_game_hb --hb-stale-s 90
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# ── what we are allowed to kill ────────────────────────────────────────────
# ONLY the AoE3 stack. Exact-name for the gamescope fork so we never touch the
# user's desktop compositor. Anything whose cmdline mentions CoH2 is spared.
_AOE3_EXE = "AoE3DE_s.exe"
_HARNESS_EXACT = "AOE3DEHarness"          # the AoE3 gamescope fork (pkill -x)
_AOE3_APPID = "933110"
_COH2_MARKERS = ("231430", "coh2", "RelicCoH2")  # never kill these


def _cmdline(pid: str) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", "replace")
    except OSError:
        return ""


def _pgrep(pattern: str, exact: bool = False) -> list[str]:
    args = ["pgrep", "-x" if exact else "-f", pattern]
    r = subprocess.run(args, capture_output=True, text=True)
    return [p for p in r.stdout.split() if p.strip().isdigit()]


def kill_game_stack(reason: str = "", dry_run: bool = False) -> list[int]:
    """SIGKILL only the AoE3 game stack. Returns the pids killed. CoH2-safe."""
    killed: list[int] = []
    # 1) the game binary (the big memory consumer)
    for pid in _pgrep(_AOE3_EXE):
        cl = _cmdline(pid)
        if any(m in cl for m in _COH2_MARKERS):
            continue
        killed.append(int(pid))
    # 2) the AoE3 gamescope fork (exact name — never the desktop compositor)
    killed += [int(p) for p in _pgrep(_HARNESS_EXACT, exact=True)]
    # 3) pressure-vessel / proton reaper scoped to this appid only
    for pid in _pgrep(_AOE3_APPID):
        cl = _cmdline(pid)
        if _AOE3_APPID in cl and not any(m in cl for m in _COH2_MARKERS):
            killed.append(int(pid))
    killed = sorted(set(killed))
    if dry_run:
        return killed
    for pid in killed:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    if killed:
        _log(f"kill_game_stack: killed {killed} ({reason})")
    return killed


# ── memory snapshot ────────────────────────────────────────────────────────
def read_mem() -> tuple[int, int]:
    """Return (MemAvailable_MB, SwapUsed_MB) from /proc/meminfo."""
    vals: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, _, rest = line.partition(":")
        vals[k] = int(rest.strip().split()[0])  # kB
    avail = vals.get("MemAvailable", 0) // 1024
    swap_used = (vals.get("SwapTotal", 0) - vals.get("SwapFree", 0)) // 1024
    return avail, swap_used


def aoe3_running() -> bool:
    return bool(_pgrep(_AOE3_EXE))


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    sys.stderr.write(f"[game_safety {ts}] {msg}\n")
    sys.stderr.flush()


# ── pure breach decision (unit-testable without the game) ──────────────────
def breach_reason(avail_mb: int, swap_used_mb: int, elapsed_s: float,
                  game_alive: bool, hb_age_s: float | None,
                  mem_floor_mb: int, swap_cap_mb: int, max_runtime_s: int,
                  hb_stale_s: int) -> str | None:
    """Return a kill reason if any guard is breached, else None. Pure → testable."""
    if avail_mb < mem_floor_mb:
        return f"LOW MEMORY avail={avail_mb}MB < {mem_floor_mb}MB"
    if swap_used_mb > swap_cap_mb:
        return f"SWAP THRASH swap={swap_used_mb}MB > {swap_cap_mb}MB"
    if elapsed_s > max_runtime_s and game_alive:
        return f"runtime cap {max_runtime_s}s exceeded"
    if hb_age_s is not None and hb_age_s > hb_stale_s:
        return f"controller heartbeat stale > {hb_stale_s}s"
    return None


# ── the watchdog loop ──────────────────────────────────────────────────────
def watchdog(mem_floor_mb: int = 2800, swap_cap_mb: int = 3000,
             max_runtime_s: int = 1200, heartbeat: str | None = None,
             hb_stale_s: int = 90, poll_s: int = 5,
             max_lifetime_s: int = 3600) -> int:
    """Independently guard the machine. Kills the AoE3 stack + exits on the
    first breach. Self-terminates after max_lifetime_s (deadman — never lingers).
    """
    start = time.time()
    _log(f"watchdog up: floor={mem_floor_mb}MB swapcap={swap_cap_mb}MB "
         f"maxrun={max_runtime_s}s hb={heartbeat} stale={hb_stale_s}s")
    while True:
        now = time.time()
        if now - start > max_lifetime_s:
            kill_game_stack("watchdog max lifetime"); return 0
        avail, swap_used = read_mem()
        alive = aoe3_running()
        hb_age = None
        if heartbeat:
            hb = Path(heartbeat)
            hb_age = (now - hb.stat().st_mtime) if hb.exists() else (now - start)
        reason = breach_reason(avail, swap_used, now - start, alive, hb_age,
                               mem_floor_mb, swap_cap_mb, max_runtime_s, hb_stale_s)
        if reason:
            kill_game_stack(reason); return 10
        if not alive and now - start > 30:
            _log("game stack gone — watchdog exiting clean"); return 0
        time.sleep(poll_s)


# ── controller-side context manager ────────────────────────────────────────
class GameSession:
    """Wrap any block that runs a live AoE3 match.

    Spawns a DETACHED watchdog (survives this process being SIGKILL'd), beats
    a heartbeat, and force-kills the stack on exit no matter how we leave.

        with GameSession(max_runtime_s=600):
            ... drive one match ...
    """

    def __init__(self, mem_floor_mb: int = 2800, swap_cap_mb: int = 3000,
                 max_runtime_s: int = 900, heartbeat: str = "/tmp/anw_game_hb",
                 kill_on_exit: bool = True, hb_stale_s: int = 120):
        self.hb_stale_s = hb_stale_s
        # kill_on_exit: True for scripts that LAUNCH the game (own its
        # lifecycle); False when reusing an already-running instance — the
        # memory watchdog still protects the desktop either way.
        self.cfg = dict(mem_floor_mb=mem_floor_mb, swap_cap_mb=swap_cap_mb,
                        max_runtime_s=max_runtime_s, heartbeat=heartbeat)
        self.heartbeat = heartbeat
        self.kill_on_exit = kill_on_exit
        self._wd: subprocess.Popen | None = None
        self._installed_handlers: list = []

    def _beat(self) -> None:
        Path(self.heartbeat).write_text(str(time.time()))

    def __enter__(self) -> "GameSession":
        self._beat()
        # Detached watchdog: own session so a SIGKILL of us doesn't take it down.
        self._wd = subprocess.Popen(
            [sys.executable, "-m", "tools.aoe3_automation.game_safety", "watch",
             "--mem-floor-mb", str(self.cfg["mem_floor_mb"]),
             "--swap-cap-mb", str(self.cfg["swap_cap_mb"]),
             "--max-runtime-s", str(self.cfg["max_runtime_s"]),
             "--heartbeat", self.heartbeat, "--hb-stale-s", str(self.hb_stale_s)],
            start_new_session=True,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._installed_handlers.append((sig, signal.getsignal(sig)))
            signal.signal(sig, self._on_signal)
        return self

    def beat(self) -> None:
        """Call periodically from the controller's observe loop."""
        self._beat()

    def _on_signal(self, *_a) -> None:
        self.__exit__(None, None, None)
        os._exit(143)

    def __exit__(self, *_exc) -> None:
        try:
            if self.kill_on_exit:
                kill_game_stack("GameSession exit")
        finally:
            # Drop the heartbeat. If kill_on_exit was False, the detached
            # watchdog still runs until the game exits, max-runtime, or a
            # memory breach — the desktop stays protected regardless.
            try:
                Path(self.heartbeat).unlink(missing_ok=True)
            except OSError:
                pass


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="game_safety")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("watch")
    w.add_argument("--mem-floor-mb", type=int, default=2800)
    w.add_argument("--swap-cap-mb", type=int, default=3000)
    w.add_argument("--max-runtime-s", type=int, default=1200)
    w.add_argument("--heartbeat", default=None)
    w.add_argument("--hb-stale-s", type=int, default=90)
    sub.add_parser("kill")
    sub.add_parser("mem")
    a = p.parse_args(argv)
    if a.cmd == "watch":
        return watchdog(a.mem_floor_mb, a.swap_cap_mb, a.max_runtime_s,
                        a.heartbeat, a.hb_stale_s)
    if a.cmd == "kill":
        print("killed:", kill_game_stack("manual"))
        return 0
    if a.cmd == "mem":
        avail, swap = read_mem()
        print(f"MemAvailable={avail}MB  SwapUsed={swap}MB  aoe3={aoe3_running()}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(_main())
