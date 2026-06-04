#!/usr/bin/env python3
"""Single-scenario load test — does ANW_Coverage_X actually load and fire probes?

This is the pre-flight test before building a full multi-scenario runner. It:

  1. Truncates Age3Log.txt
  2. Drives the UI: main menu → Skirmish → Map → Custom Scenario → row
  3. Clicks OPEN
  4. Watches Age3Log for 240s for either:
        - PASS: ≥1 ANW civ emits meta.boot
        - FAIL_LOAD: load-failure marker in log
        - FAIL_TIMEOUT: deadline elapsed
  5. Reports verdict and the first 50 lines of any new log content.

Assumes the game is at the main menu when this runs.

Usage:
    python3 tools/validation/scenario_load_test.py --letter A --timeout-s 240
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.aoe3_automation.gamescope_detect import get_gs_env
from tools.aoe3_automation.lobby_driver import (
    click, click_skirmish, load_coords, move_mouse_off,
)

DEFAULT_LOG = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)

# Expected civs per scenario (matches docs/SCENARIO_AUTHORING_PLAYBOOK.md).
# 2026-05-18: Rebuilt for 44-civ roster (post ANWAmericans / ANWBajaCalifornians
# removal and ANWFrenchCanadians merge). Prior version had a missing "C" key
# (syntax error) and stale Baja entry.
SCENARIO_CIVS = {
    "A": ["ANWArgentines", "ANWAztecs", "ANWBarbary", "ANWBrazil",
    "B": ["ANWChileans", "ANWChinese", "ANWColumbians", "ANWDutch",
          "ANWEgyptians", "ANWEthiopians", "ANWFinnish", "ANWFrench"],
    "C": ["ANWGermans", "ANWHaitians", "ANWHaudenosaunee", "ANWHausa",
          "ANWHungarians", "ANWInca", "ANWIndians", "ANWIndonesians"],
    "D": ["ANWItalians", "ANWJapanese", "ANWLakota", "ANWMaltese",
          "ANWMayans", "ANWMexicans", "ANWNapoleonicFrance", "ANWOttomans"],
          "ANWRomanians", "ANWRussians", "ANWSouthAfricans", "ANWSpanish"],
}

_META_BOOT_RE = re.compile(
    r"\[ANWP v=2 t=\d+ p=\d+ civ=(?P<civ>\S+) ldr=\S+ tag=meta\.boot\]"
)
_LOAD_FAIL_RE = re.compile(
    r"Scenario .* failed to load|Failed to load scenario|"
    r"Scenario .* cannot be loaded|Unable to load scenario|"
    r"Error loading scenario|Invalid scenario file|corrupted scenario",
    re.IGNORECASE,
)
_FATAL_RE = re.compile(
    r"unhandled exception|fatal error|access violation",
    re.IGNORECASE,
)


def navigate_to_scenario_picker(coords: dict) -> None:
    """Main menu → Skirmish lobby → Map button → Custom Scenario."""
    sp = coords["scenario_picker"]
    print("  click SKIRMISH")
    click_skirmish(coords); time.sleep(4)
    print("  click map button")
    click(*sp["lobby_map_button"], settle=0.4); time.sleep(2.5)
    print("  click CUSTOM SCENARIO")
    click(*sp["map_picker_custom_scenario_btn"], settle=0.4); time.sleep(2.5)


def select_scenario_row(coords: dict, letter: str) -> None:
    """Click the row for ANW_Coverage_<letter> and then OPEN."""
    sp = coords["scenario_picker"]
    idx = sp["anw_coverage_row_index"][letter]
    y = sp["file_picker_first_row_y"] + idx * sp["file_picker_row_height"]
    x = sp["file_picker_row_x"]
    print(f"  click row[{idx}] ANW_Coverage_{letter} at ({x},{y})")
    click(x, y, settle=0.3); time.sleep(0.8)
    # Click again to ensure selection (some builds need double-click semantics)
    click(x, y, settle=0.3); time.sleep(0.8)
    open_btn = sp["file_picker_open_btn"]
    print(f"  click OPEN at {open_btn}")
    click(*open_btn, settle=0.3); time.sleep(2.0)


def truncate_log(log_path: Path) -> None:
    if log_path.exists():
        log_path.write_text("", encoding="utf-8")


def watch_log(log_path: Path, expect_civs: list[str], timeout_s: float) -> dict:
    deadline = time.monotonic() + timeout_s
    seen: dict[str, int] = defaultdict(int)
    fail_lines: list[str] = []
    fatal_lines: list[str] = []
    last_size = 0
    last_print = 0.0
    while time.monotonic() < deadline:
        if log_path.exists():
            size = log_path.stat().st_size
            if size > last_size:
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    f.seek(last_size)
                    chunk = f.read(size - last_size)
                for line in chunk.splitlines():
                    m = _META_BOOT_RE.search(line)
                    if m:
                        seen[m.group("civ")] += 1
                    if _LOAD_FAIL_RE.search(line):
                        fail_lines.append(line.strip())
                    if _FATAL_RE.search(line):
                        fatal_lines.append(line.strip())
                last_size = size
        if fail_lines:
            return {"verdict": "FAIL_LOAD", "civs_seen": dict(seen),
                    "fail_lines": fail_lines, "fatal_lines": fatal_lines,
                    "elapsed_s": timeout_s - (deadline - time.monotonic())}
        matched = [c for c in expect_civs if seen.get(c, 0) > 0]
        if matched:
            # First probe is enough to confirm the scenario loaded
            return {"verdict": "PASS", "civs_seen": dict(seen),
                    "matched_expected": matched,
                    "fatal_lines": fatal_lines,
                    "elapsed_s": timeout_s - (deadline - time.monotonic())}
        now = time.monotonic()
        if now - last_print > 5.0:
            print(f"    [{int(deadline - now):>3}s] log_size={last_size} "
                  f"meta.boot_seen={dict(seen)}", flush=True)
            last_print = now
        time.sleep(1.0)
    return {"verdict": "FAIL_TIMEOUT", "civs_seen": dict(seen),
            "fail_lines": fail_lines, "fatal_lines": fatal_lines,
            "elapsed_s": timeout_s}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--letter", choices=list("ABCDEF"), default="A")
    ap.add_argument("--timeout-s", type=float, default=240.0)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    coords = load_coords()
    expected_civs = SCENARIO_CIVS[args.letter]

    print(f"=== scenario load test: ANW_Coverage_{args.letter} ===")
    print(f"  expected civs (any 1+ must emit meta.boot): {expected_civs}")
    print(f"  log: {args.log}")
    print(f"  timeout: {args.timeout_s}s")

    print("\n[step 1] truncate log")
    truncate_log(args.log)
    print(f"  size={args.log.stat().st_size if args.log.exists() else 'missing'}")

    print("\n[step 2] navigate to scenario picker")
    navigate_to_scenario_picker(coords)
    move_mouse_off()

    print(f"\n[step 3] select ANW_Coverage_{args.letter} and OPEN")
    select_scenario_row(coords, args.letter)
    move_mouse_off()

    print(f"\n[step 4] watch log for up to {args.timeout_s}s")
    result = watch_log(args.log, expected_civs, args.timeout_s)

    print()
    print("=" * 60)
    print(f"VERDICT: {result['verdict']}")
    print("=" * 60)
    print(f"civs_seen: {result['civs_seen']}")
    print(f"matched_expected: {result.get('matched_expected', [])}")
    if result.get("fail_lines"):
        print("FAIL LINES:")
        for line in result["fail_lines"][:5]:
            print(f"  {line}")
    if result.get("fatal_lines"):
        print("FATAL LINES:")
        for line in result["fatal_lines"][:5]:
            print(f"  {line}")
    print(f"elapsed: {result['elapsed_s']:.1f}s")

    # Dump first 30 lines of log for diagnostics
    if args.log.exists() and args.log.stat().st_size > 0:
        print("\nFirst 30 log lines:")
        lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[:30]:
            print(f"  {line}")

    return {"PASS": 0, "FAIL_LOAD": 1, "FAIL_TIMEOUT": 2}.get(
        result["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
