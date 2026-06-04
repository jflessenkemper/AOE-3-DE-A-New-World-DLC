#!/usr/bin/env python3
"""matrix_run_all.py — Drive the 48-civ skirmish matrix end-to-end.

Usage
-----
    python3 tools/aoe3_automation/flows/matrix_run_all.py [options]

Options
-------
    --dry-run           Print steps without actually running the flow runner.
    --civ CIV_ID        Run a single civ (by civ_id, e.g. cCivBritish).
    --skip CIV_ID       Skip a civ (repeatable).
    --log-path PATH     Age3Log.txt path (default: standard Proton location).
    --artifact-dir DIR  Override artifact root (default: artifacts/matrix_<ts>/).
    --suites SUITES     Comma-separated coverage_v2 suites to validate
                        (default: pacing_v2,shipment_order_v2,escort_v2).

Flow
----
For each civ in load_expectations():
  1. Set CIV_NAME / LEADER_NAME env vars.
  2. Run matrix_run_one_civ.json via aoe3_ui_automation run-flow.
  3. Rotate Age3Log.txt to per-civ slice.
  4. Run coverage_v2 checks against the slice.
  5. Write per-civ artifact dir.
Final: write report.md summarising pass / warn / fail per civ.

Speed knobs
-----------
Each match is played at gameSpeedMultiplier=2.0, revealMap=1, noFog=1,
handicap=2.0 (player gets double resources → CPU loses fast).
Target: 6-10 minutes wall-clock per match → 48 civs in ~6-8 hours.
Set these once in the Advanced Settings dialog via the setup flow, or
use scenario-script overrides if available.
"""

from __future__ import annotations

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path regardless of CWD.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.playtest.expectations import load_expectations, CivExpectation
from tools.playtest.coverage_v2 import (
    check_pacing_budget,
    check_shipment_order,
    check_leader_escort,
)

DEFAULT_LOG_PATH = (
    Path.home()
    / ".steam/steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser"
    / "Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)
FLOW_RUNNER = REPO_ROOT / "tools/aoe3_automation/aoe3_ui_automation.py"
ONE_CIV_FLOW = Path(__file__).parent / "matrix_run_one_civ.json"
ARTIFACT_BASE = REPO_ROOT / "tools/aoe3_automation/artifacts"


# ---------------------------------------------------------------------------
# Log rotation
# ---------------------------------------------------------------------------

def rotate_log(log_path: Path, dest: Path) -> None:
    """Copy current log to dest and truncate the source."""
    if log_path.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(log_path, dest)
        log_path.write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-civ validation
# ---------------------------------------------------------------------------

def validate_slice(slice_path: Path, suites: list[str]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) from coverage_v2 checks on a log slice."""
    if not slice_path.exists():
        return [f"slice not found: {slice_path}"], []
    text = slice_path.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    warnings: list[str] = []
    if "pacing_v2" in suites:
        errors.extend(check_pacing_budget(text))
    if "shipment_order_v2" in suites:
        e, w = check_shipment_order(text)
        errors.extend(e)
        warnings.extend(w)
    if "escort_v2" in suites:
        errors.extend(check_leader_escort(text))
    return errors, warnings


# ---------------------------------------------------------------------------
# Run one civ
# ---------------------------------------------------------------------------

def run_one_civ(
    exp: CivExpectation,
    log_path: Path,
    civ_artifact_dir: Path,
    dry_run: bool,
    suites: list[str],
) -> dict:
    """Run the per-civ flow, collect log, validate. Returns a result dict."""
    result: dict = {
        "civ_id": exp.civ_id,
        "label": exp.label,
        "leader_key": exp.leader_key,
        "status": "unknown",
        "errors": [],
        "warnings": [],
        "elapsed_s": 0,
    }
    civ_artifact_dir.mkdir(parents=True, exist_ok=True)

    env = {
        **os.environ,
        "CIV_NAME": exp.label,
        "LEADER_NAME": exp.leader_key,
    }

    cmd = [
        sys.executable,
        str(FLOW_RUNNER),
        "run-flow",
        str(ONE_CIV_FLOW),
    ]
    if dry_run:
        cmd.append("--dry-run")

    t0 = time.monotonic()
    print(f"\n=== [{exp.civ_id}] {exp.label} (leader: {exp.leader_key}) ===")
    if dry_run:
        print(f"  DRY RUN: would execute {' '.join(cmd)}")
    else:
        completed = subprocess.run(cmd, env=env)
        if completed.returncode != 0:
            result["errors"].append(f"flow runner exited with code {completed.returncode}")

    elapsed = time.monotonic() - t0
    result["elapsed_s"] = round(elapsed, 1)

    # Rotate log
    slice_path = civ_artifact_dir / "Age3Log_slice.txt"
    if not dry_run:
        rotate_log(log_path, slice_path)
    else:
        # In dry-run, create an empty slice so validation runs cleanly.
        slice_path.write_text("", encoding="utf-8")

    # Validate
    errors, warnings = validate_slice(slice_path, suites)
    result["errors"].extend(errors)
    result["warnings"].extend(warnings)

    if result["errors"]:
        result["status"] = "FAIL"
    elif result["warnings"]:
        result["status"] = "WARN"
    else:
        result["status"] = "PASS"

    print(f"  status={result['status']} elapsed={elapsed:.1f}s "
          f"errors={len(result['errors'])} warnings={len(result['warnings'])}")
    return result


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(results: list[dict], report_path: Path, suites: list[str]) -> None:
    lines = [
        "# A New World 48-civ Matrix Report",
        "",
        f"Generated: {datetime.datetime.now().isoformat()}",
        f"Suites: {', '.join(suites)}",
        "",
        "| Civ | Label | Status | Elapsed | Errors | Warnings |",
        "|----|-------|--------|---------|--------|----------|",
    ]
    for r in results:
        lines.append(
            f"| {r['civ_id']} | {r['label']} | {r['status']} "
            f"| {r['elapsed_s']}s | {len(r['errors'])} | {len(r['warnings'])} |"
        )
    lines.append("")

    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    total_elapsed = sum(r["elapsed_s"] for r in results)

    lines += [
        f"**Summary**: {pass_count} PASS / {warn_count} WARN / {fail_count} FAIL",
        f"**Total elapsed**: {total_elapsed/3600:.1f}h",
        "",
        "## Failures and Warnings",
        "",
    ]
    for r in results:
        if r["errors"] or r["warnings"]:
            lines.append(f"### {r['label']} ({r['civ_id']})")
            for e in r["errors"]:
                lines.append(f"- FAIL: {e}")
            for w in r["warnings"]:
                lines.append(f"- WARN: {w}")
            lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="48-civ skirmish matrix runner.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print steps without running the flow runner or game.")
    parser.add_argument("--civ", action="append", default=[],
                        help="Run only this civ_id (repeatable).")
    parser.add_argument("--skip", action="append", default=[],
                        help="Skip this civ_id (repeatable).")
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH,
                        help="Path to Age3Log.txt.")
    parser.add_argument("--artifact-dir", type=Path,
                        help="Override artifact root directory.")
    parser.add_argument("--suites", default="pacing_v2,shipment_order_v2,escort_v2",
                        help="Comma-separated coverage_v2 suites to run.")
    args = parser.parse_args()

    suites = [s.strip() for s in args.suites.split(",") if s.strip()]

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    artifact_root = args.artifact_dir or (ARTIFACT_BASE / f"matrix_{ts}")
    artifact_root.mkdir(parents=True, exist_ok=True)

    expectations = load_expectations()
    if args.civ:
        expectations = [e for e in expectations if e.civ_id in args.civ]
    if args.skip:
        expectations = [e for e in expectations if e.civ_id not in args.skip]

    print(f"Matrix runner: {len(expectations)} civs, artifacts at {artifact_root}")
    print(f"Suites: {', '.join(suites)}")

    results: list[dict] = []
    for exp in expectations:
        civ_dir = artifact_root / exp.civ_id
        r = run_one_civ(
            exp=exp,
            log_path=args.log_path,
            civ_artifact_dir=civ_dir,
            dry_run=args.dry_run,
            suites=suites,
        )
        results.append(r)

    report_path = artifact_root / "report.md"
    write_report(results, report_path, suites)

    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
