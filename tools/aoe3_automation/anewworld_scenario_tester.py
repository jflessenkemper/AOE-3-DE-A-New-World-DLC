#!/usr/bin/env python3
"""
ANEWWORLD Scenario Tester — Direct scenario launcher and trigger validator.

⚠ DEPRECATED (2026-05-12) — use ``tools/validation/run_scenario_test.py``.

This script was built around the legacy trigger-based pipeline
(``[AGEUP]``, ``[UNITS_TRAINED]``, ``[BUILDINGS]``, etc. patterns scraped
from ``Age3Log.txt``). Two findings made it unusable:

  1. AoE3 DE FINAL_RELEASE builds strip ``aiEcho()`` from the log entirely,
     so trigger-style probes never reach Age3Log.txt.
  2. The triggers themselves never made it into the ``.age3Yscn`` binary
     — existing trigger-injection tooling
     (``tools/validation/scenario_trigger_builder.py``,
     ``trigger_injector.py``) admits in its docstrings that "actual
     injection is risky without full format understanding".

Use ``tools/validation/run_scenario_test.py`` instead — it uses the
personality-channel pipeline (``Game/AI/<leader>.personality`` uservars)
which DOES survive FINAL_RELEASE, and integrates with the validator at
``tools/validation/validate_personality_vs_spec.py``.

See ``Scenario/TEST_LOOP.md`` for the canonical test-loop workflow.

Legacy usage (kept for reference only):
    python3 tools/aoe3_automation/anewworld_scenario_tester.py [--civ CIV_TOKEN] [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.migration.anw_token_map import ANW_CIVS

# Paths
SCENARIO_PATH = Path.home() / ".local/share/Steam/userdata/209941315/933110/remote/scenario@ANEWWORLD.age3Yscn"
AOE3_EXECUTABLE = Path.home() / ".steam/steam/steamapps/common/AoE3DE/Launcher.exe"
DEFAULT_LOG_PATH = (
    Path.home()
    / ".steam/steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser"
    / "Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)
ARTIFACT_BASE = REPO_ROOT / "tools/aoe3_automation/artifacts"


class TriggerValidator:
    """Validate trigger output patterns in game logs."""

    PATTERNS = {
        "ageup": r"\[AGEUP\]",
        "units": r"\[UNITS_TRAINED\]",
        "buildings": r"\[BUILDINGS\]",
        "cards": r"\[CARDS\]",
        "trade_routes": r"\[TRADE_ROUTES\]",
        "game_end": r"\[GAME_END\]",
    }

    @staticmethod
    def validate(log_text: str) -> tuple[dict[str, bool], list[str]]:
        """Return (trigger_status, errors)."""
        status = {name: bool(re.search(pattern, log_text))
                  for name, pattern in TriggerValidator.PATTERNS.items()}

        errors = []
        for trigger_name, fired in status.items():
            if not fired:
                errors.append(f"Missing trigger: {trigger_name}")

        if re.search(r"(crashed|unhandled exception|fatal error)", log_text, re.IGNORECASE):
            errors.append("Game encountered a crash or fatal error")

        return status, errors


class ScenarioTester:
    """Test ANEWWORLD scenario for a given civilization."""

    def __init__(self, civ_token: str, log_path: Path = DEFAULT_LOG_PATH):
        self.civ_token = civ_token
        self.civ_name = civ_token.replace("ANW", "")
        self.log_path = log_path
        self.result = {
            "civ_token": civ_token,
            "civ_name": self.civ_name,
            "status": "unknown",
            "triggers": {},
            "errors": [],
            "warnings": [],
            "elapsed_s": 0.0,
        }

    def run_scenario(self, dry_run: bool = False, timeout: int = 900) -> dict:
        """Run scenario and capture results."""
        print(f"\n[{self.civ_token}] {self.civ_name}")
        t0 = time.monotonic()

        # Clear old log
        if self.log_path.exists():
            self.log_path.write_text("", encoding="utf-8")
            time.sleep(0.5)

        if not dry_run:
            self._launch_scenario()
            self._wait_for_completion(timeout)
            self._parse_log()
        else:
            print(f"  [DRY RUN] Would launch scenario and wait {timeout}s")

        elapsed = time.monotonic() - t0
        self.result["elapsed_s"] = round(elapsed, 1)
        self._evaluate_result()

        status_icon = "✓" if self.result["status"] == "PASS" else "✗"
        triggers_icon = "✓" if all(self.result["triggers"].values()) else "✗"
        print(f"  {status_icon} {self.result['status']} | triggers {triggers_icon} | {elapsed:.1f}s")

        return self.result

    def _launch_scenario(self) -> None:
        """Launch AOE3 with the scenario (via Proton/Steam)."""
        # For now, just launch the game. A more sophisticated approach would
        # use Steam launch parameters or modify config files to auto-load the scenario.
        # This is a placeholder that relies on the user having the scenario ready.

        print(f"  Launching AOE3 DE...")
        cmd = ["steam", "-forcesteamruntime", "run", "933110"]

        try:
            # Use Proton to launch
            env = os.environ.copy()
            env["PROTON_LOG"] = "1"
            subprocess.Popen(cmd, env=env)
            time.sleep(8)  # Wait for game to launch
        except Exception as e:
            self.result["errors"].append(f"Failed to launch game: {e}")

    def _wait_for_completion(self, timeout: int) -> None:
        """Wait for game to end or timeout."""
        print(f"  Waiting up to {timeout}s for game completion...")
        start = time.time()
        deadline = start + timeout

        # Monitor log for game end markers or just wait
        while time.time() < deadline:
            if self.log_path.exists():
                log_text = self.log_path.read_text(encoding="utf-8", errors="replace")
                if re.search(r"\[GAME_END\]|Victory|Defeat", log_text):
                    print(f"  Game ended (detected via log)")
                    break
            time.sleep(5)  # Check every 5 seconds

        elapsed_wait = time.time() - start
        if elapsed_wait >= timeout:
            print(f"  Timeout after {timeout}s")
            self.result["warnings"].append(f"Game did not end within {timeout}s")

    def _parse_log(self) -> None:
        """Parse log file and validate triggers."""
        if not self.log_path.exists():
            self.result["errors"].append("Log file not found")
            return

        try:
            log_text = self.log_path.read_text(encoding="utf-8", errors="replace")
            trigger_status, errors = TriggerValidator.validate(log_text)
            self.result["triggers"] = trigger_status
            self.result["errors"].extend(errors)

            # Also capture raw log for debugging
            print(f"  Log size: {len(log_text)} bytes")
        except Exception as e:
            self.result["errors"].append(f"Failed to parse log: {e}")

    def _evaluate_result(self) -> None:
        """Set overall status based on triggers and errors."""
        if self.result["errors"]:
            self.result["status"] = "FAIL"
        elif not all(self.result["triggers"].values()):
            self.result["status"] = "WARN"
            self.result["warnings"].append("Not all triggers fired")
        else:
            self.result["status"] = "PASS"


def write_report(results: list[dict], report_path: Path) -> None:
    """Write validation report."""
    lines = [
        "# ANEWWORLD Scenario Trigger Validation Report",
        "",
        f"Generated: {datetime.datetime.now().isoformat()}",
        "",
        "## Summary Table",
        "",
        "| Civ | Status | AgeUp | Units | Bldgs | Cards | Trade | End | Elapsed |",
        "|-----|--------|-------|-------|-------|-------|-------|-----|---------|",
    ]

    for r in results:
        t = r.get("triggers", {})
        row = (
            f"| {r['civ_token']:<12} | {r['status']:<6} | "
            f"{'✓' if t.get('ageup') else '✗'} | "
            f"{'✓' if t.get('units') else '✗'} | "
            f"{'✓' if t.get('buildings') else '✗'} | "
            f"{'✓' if t.get('cards') else '✗'} | "
            f"{'✓' if t.get('trade_routes') else '✗'} | "
            f"{'✓' if t.get('game_end') else '✗'} | "
            f"{r['elapsed_s']:.0f}s |"
        )
        lines.append(row)

    lines.extend(["", "## Overall Results", ""])
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    total_elapsed = sum(r["elapsed_s"] for r in results)

    lines += [
        f"**Summary**: {pass_count} PASS / {warn_count} WARN / {fail_count} FAIL",
        f"**Elapsed**: {total_elapsed/3600:.1f}h total, {total_elapsed/len(results) if results else 0:.1f}s average",
        "",
    ]

    # Trigger coverage
    trigger_counts = {name: 0 for name in TriggerValidator.PATTERNS}
    for r in results:
        for trigger, fired in r.get("triggers", {}).items():
            if fired:
                trigger_counts[trigger] += 1

    lines.extend(["## Trigger Coverage", ""])
    for trigger, count in trigger_counts.items():
        pct = (count / len(results) * 100) if results else 0
        lines.append(f"- **{trigger}**: {count}/{len(results)} ({pct:.0f}%)")

    # Failures
    failures = [r for r in results if r["status"] == "FAIL"]
    if failures:
        lines.extend(["", "## Failures", ""])
        for r in failures:
            lines.append(f"### {r['civ_token']} — {r['civ_name']}")
            for e in r["errors"]:
                lines.append(f"- {e}")
            lines.append("")

    # Warnings
    warnings = [r for r in results if r["status"] == "WARN"]
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for r in warnings:
            lines.append(f"### {r['civ_token']} — {r['civ_name']}")
            for w in r.get("warnings", []):
                lines.append(f"- {w}")
            lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✓ Report: {report_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test ANEWWORLD scenario triggers.")
    parser.add_argument("--civ", action="append", default=[],
                        help="Run specific civ_token (repeatable). Default: all.")
    parser.add_argument("--skip", action="append", default=[],
                        help="Skip civ_token (repeatable).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't actually run the game, just validate structure.")
    parser.add_argument("--timeout", type=int, default=600,
                        help="Timeout per civ in seconds (default: 600).")
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH,
                        help="Age3Log.txt path.")
    args = parser.parse_args()

    # Validate scenario file exists
    if not SCENARIO_PATH.exists() and not args.dry_run:
        print(f"✗ Scenario not found: {SCENARIO_PATH}", file=sys.stderr)
        return 1

    # Build civ list
    civs = []
    for civ_obj in ANW_CIVS:
        # Handle both string and object formats
        civ_token = civ_obj.token if hasattr(civ_obj, 'token') else str(civ_obj)

        if args.civ and civ_token not in args.civ:
            continue
        if args.skip and civ_token in args.skip:
            continue
        civs.append(civ_token)

    print("="*80)
    print(f"ANEWWORLD Scenario Trigger Validator")
    print("="*80)
    print(f"\n{len(civs)} civs to test")
    print(f"Scenario: {SCENARIO_PATH}")
    print(f"Log path: {args.log_path}")
    if args.dry_run:
        print("[DRY RUN MODE]")

    results = []
    for civ_token in civs:
        tester = ScenarioTester(civ_token, args.log_path)
        result = tester.run_scenario(dry_run=args.dry_run, timeout=args.timeout)
        results.append(result)

    # Write report
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = ARTIFACT_BASE / f"anewworld_{ts}" / "ANEWWORLD_TRIGGERS_REPORT.md"
    write_report(results, report_path)

    print("\n" + "="*80)
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
