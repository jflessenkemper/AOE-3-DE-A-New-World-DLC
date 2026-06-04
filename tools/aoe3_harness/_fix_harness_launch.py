"""One-shot harness relaunch with the CORRECT umu env.

Combines launch.build_env()/kill_stale() (correct WINEPREFIX/PROTONPATH/GAMEID)
with harness_launch.build_gamescope_cmd() (the AOE3DEHarness wrapper command).
The stock harness_launch.harness_launch() spawns with inherited env, which is
why standalone launches failed with "umu-run env insufficient".

Run:  python3 -m tools.aoe3_harness._fix_harness_launch
Spawns AOE3DEHarness, polls socket + STATE until ready, prints STATE, then
detaches (leaves harness running) so a separate capture driver can connect.
"""
from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

from tools.aoe3_harness.launch import build_env, kill_stale
from tools.aoe3_harness.harness_launch import (
    DEFAULT_GS_BINARY,
    build_gamescope_cmd,
    _default_socket_path,
)
from tools.aoe3_harness.harness_client import HarnessClient


def main() -> int:
    sock = _default_socket_path()

    print("[fix] killing stale game/gamescope processes ...", flush=True)
    kill_stale(force_kill=True)
    time.sleep(3)

    # double-check the game is gone
    r = subprocess.run(["pgrep", "-f", "AoE3DE_s.exe"], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"[fix] AoE3DE_s.exe still alive (PIDs {r.stdout.split()}); SIGKILL", flush=True)
        for pid in r.stdout.split():
            try:
                subprocess.run(["kill", "-9", pid])
            except Exception:
                pass
        time.sleep(2)

    # remove stale socket
    try:
        sock.unlink()
        print(f"[fix] removed stale socket {sock}", flush=True)
    except FileNotFoundError:
        pass

    env = build_env()
    cmd = build_gamescope_cmd(gs_binary=DEFAULT_GS_BINARY)
    print(f"[fix] launching: {' '.join(cmd)}", flush=True)
    print(f"[fix] WINEPREFIX={env['WINEPREFIX']}", flush=True)

    log = open("/tmp/anw_harness_fix.log", "wb")
    proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(f"[fix] AOE3DEHarness PID {proc.pid}", flush=True)

    # poll for socket (asset preload can take a while)
    deadline = time.monotonic() + 200
    while time.monotonic() < deadline:
        if sock.exists():
            print(f"[fix] socket appeared after ~{int(200 - (deadline - time.monotonic()))}s", flush=True)
            break
        if proc.poll() is not None:
            print(f"[fix] FAIL: harness process exited early rc={proc.returncode}; see /tmp/anw_harness_fix.log", flush=True)
            return 2
        time.sleep(1)
    else:
        print("[fix] FAIL: socket never appeared within 200s", flush=True)
        return 3

    # poll STATE until ready
    deadline = time.monotonic() + 240
    last_err = None
    while time.monotonic() < deadline:
        try:
            c = HarnessClient(sock)
            c.connect(timeout=10)
            st = c.state()
            if getattr(st, "ready", 0):
                print(f"[fix] READY: {st}", flush=True)
                c.close()
                return 0
            else:
                print(f"[fix] state not-ready yet: {st}", flush=True)
            c.close()
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(5)

    print(f"[fix] FAIL: STATE never reached ready=1 within 240s (last_err={last_err})", flush=True)
    return 4


if __name__ == "__main__":
    sys.exit(main())
