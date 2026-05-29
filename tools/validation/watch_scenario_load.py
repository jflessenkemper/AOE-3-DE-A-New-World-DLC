#!/usr/bin/env python3
"""Passive Age3Log.txt watcher — detect scenario load success or failure.

While the game is running and a scenario is loaded (manually or via UI
automation), this script tails Age3Log.txt and reports the verdict:

  - PASS: at least N distinct ANW civs emitted `meta.boot` (scenario loaded
    AND the AI bootstrap ran for those civs)
  - FAIL_LOAD: log contains a known scenario-load-failure marker
  - FAIL_TIMEOUT: deadline elapsed without either signal

Use this to verify a single emitted scenario *actually loads* before you
trust the emitter for the full 46-civ run.

Usage:
    # Truncate log, load scenario in-game, then run the watcher:
    python3 tools/validation/watch_scenario_load.py \\
        --expect-civs ANWArgentines ANWAztecs ANWBritish \\
        --timeout-s 180

The script blocks until verdict or timeout.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

DEFAULT_LOG = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)

# meta.boot is the first probe each AI player emits in preInit().
# Format: [LLP v=2 t=<ms> p=<pid> civ=<token> ldr=<key> tag=meta.boot] ...
_META_BOOT_RE = re.compile(
    r"\[LLP v=2 t=\d+ p=\d+ civ=(?P<civ>\S+) ldr=\S+ tag=meta\.boot\]"
)

# Known scenario-load failure markers (heuristic, expand as we observe more).
_LOAD_FAIL_PATTERNS = [
    r"Scenario .* failed to load",
    r"Failed to load scenario",
    r"Scenario .* cannot be loaded",
    r"Unable to load scenario",
    r"Error loading scenario",
    r"Invalid scenario file",
    r"corrupted scenario",
]
_LOAD_FAIL_RE = re.compile("|".join(_LOAD_FAIL_PATTERNS), re.IGNORECASE)

# Generic engine error signals worth flagging.
_FATAL_RE = re.compile(
    r"unhandled exception|fatal error|access violation|d3d11.*?error",
    re.IGNORECASE,
)


def watch(
    log_path: Path,
    expect_civs: list[str] | None,
    min_civs: int,
    timeout_s: float,
    poll_s: float = 1.0,
) -> dict:
    deadline = time.monotonic() + timeout_s
    seen: dict[str, int] = defaultdict(int)
    fail_lines: list[str] = []
    fatal_lines: list[str] = []
    last_size = 0
    last_print = 0.0

    while time.monotonic() < deadline:
        if not log_path.exists():
            time.sleep(poll_s)
            continue
        size = log_path.stat().st_size
        if size < last_size:
            # Log was truncated mid-watch
            last_size = 0
        if size > last_size:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                f.seek(last_size)
                chunk = f.read(size - last_size)
            for line in chunk.splitlines():
                m = _META_BOOT_RE.search(line)
                if m:
                    civ = m.group("civ")
                    seen[civ] += 1
                if _LOAD_FAIL_RE.search(line):
                    fail_lines.append(line.strip())
                if _FATAL_RE.search(line):
                    fatal_lines.append(line.strip())
            last_size = size

        # Verdict checks
        if fail_lines:
            return {
                "verdict": "FAIL_LOAD",
                "civs_seen": dict(seen),
                "fail_lines": fail_lines,
                "fatal_lines": fatal_lines,
                "elapsed_s": timeout_s - (deadline - time.monotonic()),
            }
        if expect_civs is not None:
            matched = [c for c in expect_civs if seen.get(c, 0) > 0]
            if len(matched) >= min_civs:
                return {
                    "verdict": "PASS",
                    "civs_seen": dict(seen),
                    "matched_expected": matched,
                    "fatal_lines": fatal_lines,
                    "elapsed_s": timeout_s - (deadline - time.monotonic()),
                }
        else:
            if len(seen) >= min_civs:
                return {
                    "verdict": "PASS",
                    "civs_seen": dict(seen),
                    "fatal_lines": fatal_lines,
                    "elapsed_s": timeout_s - (deadline - time.monotonic()),
                }

        # Periodic progress print
        now = time.monotonic()
        if now - last_print > 5.0:
            remaining = int(deadline - now)
            print(f"  [{remaining:>3}s] log_size={last_size} "
                  f"meta.boot_seen={dict(seen)}", flush=True)
            last_print = now
        time.sleep(poll_s)

    return {
        "verdict": "FAIL_TIMEOUT",
        "civs_seen": dict(seen),
        "fail_lines": fail_lines,
        "fatal_lines": fatal_lines,
        "elapsed_s": timeout_s,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--expect-civs", nargs="*",
                    help="civs we expect to see emit meta.boot")
    ap.add_argument("--min-civs", type=int, default=1,
                    help="minimum civs that must emit meta.boot to PASS")
    ap.add_argument("--timeout-s", type=float, default=180.0)
    args = ap.parse_args()

    print(f"watching: {args.log}")
    print(f"expect:   {args.expect_civs or 'any ANW civ'}")
    print(f"min:      {args.min_civs}  timeout: {args.timeout_s}s")
    print()

    result = watch(args.log, args.expect_civs, args.min_civs, args.timeout_s)

    print()
    print("=" * 60)
    print(f"VERDICT: {result['verdict']}")
    print("=" * 60)
    print(f"civs_seen: {result['civs_seen']}")
    if result.get("fail_lines"):
        print(f"fail_lines: {result['fail_lines']}")
    if result.get("fatal_lines"):
        print(f"fatal_lines: {result['fatal_lines'][:5]}")
    print(f"elapsed: {result['elapsed_s']:.1f}s")

    return {"PASS": 0, "FAIL_LOAD": 1, "FAIL_TIMEOUT": 2}.get(result["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
