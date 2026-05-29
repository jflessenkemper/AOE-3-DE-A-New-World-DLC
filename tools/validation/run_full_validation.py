#!/usr/bin/env python3
"""ONE-COMMAND full 46-civ validation pipeline.

Wraps everything into a single command:

  1. Build enriched_reference.json from playstyle_spec + reference_matrix
  2. Enable test-mode (cLLTestModeAutoResignMs = N) so AI auto-resigns
  3. Sync mod to deployed tree
  4. Cycle game (one-time)
  5. For each civ:
       - Pick civ in skirmish lobby
       - Click PLAY
       - Wait for in-game (mode-27)
       - Wait for auto-resign + post-match (no UI nav needed)
       - Navigate post-match -> skirmish lobby
       - Slice Age3Log.txt into per-civ artifact
  6. Disable test-mode
  7. Concatenate all per-civ slices
  8. Run validate_civ_behavior.py against the concatenated log
  9. Emit final report (per-civ pass/fail + overall verdict)

Usage:
    # Full real-game run:
    python3 tools/validation/run_full_validation.py --threshold-ms 60000

    # Synthetic-only (no game; verifies the pipeline shape works):
    python3 tools/validation/run_full_validation.py --synthetic
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.aoe3_automation import test_mode_xs
from tools.validation.parse_match_log import parse_log
from tools.validation.validate_civ_behavior import validate_log

DEFAULT_THRESHOLD_MS = 60000


def step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}", flush=True)


def step1_build_enriched_reference(repo_root: Path) -> Path:
    out = repo_root / "enriched_reference.json"
    builder = repo_root / "tools/validation/build_enriched_reference.py"
    proc = subprocess.run(
        [sys.executable, str(builder), "--output", str(out)],
        capture_output=True, text=True, cwd=repo_root, timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"build_enriched_reference failed:\n{proc.stderr}")
    print(proc.stdout.splitlines()[0] if proc.stdout else "ok")
    return out


def step_synth(repo_root: Path, run_dir: Path, civs: list[str] | None) -> Path:
    """Generate a synthetic per-civ-correct log (no game required)."""
    log_path = run_dir / "synth_full.log"
    synth = repo_root / "tools/validation/synth_per_civ_log.py"
    cmd = [sys.executable, str(synth), "--out", str(log_path)]
    if civs:
        cmd += ["--civs", *civs]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd=repo_root, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"synth failed:\n{proc.stderr}")
    print(proc.stdout.strip())
    return log_path


def step_validate(log_path: Path, ref_path: Path, out_report: Path) -> dict:
    """Validate a log against reference; emit JSON report."""
    report = validate_log(log_path, ref_path)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    with open(out_report, "w") as f:
        json.dump(report, f, indent=2)
    return report


def step_print_summary(report: dict) -> None:
    print("=" * 70)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Log:        {report['log_path']}")
    print(f"Reference:  {report['reference_path']}")
    print(f"Civs in log:       {report['civs_in_log']}")
    print(f"Civs in reference: {report['civs_in_reference']}")
    print(f"Overall verdict:   {report['overall_verdict']}")
    print(f"Civ verdicts:      {report['civ_verdict_counts']}")
    print()

    # Per-civ status table
    if report["per_civ"]:
        print(f"{'CIV':<24}  {'VERDICT':<8}  {'CHECKS':<24}")
        print("-" * 60)
        for civ in sorted(report["per_civ"].keys()):
            r = report["per_civ"][civ]
            v = r["verdict"]
            counts = r["counts"]
            check_summary = (
                f"P:{counts['PASS']:>2} W:{counts['WARN']:>2} "
                f"F:{counts['FAIL']:>2} S:{counts['SKIP']:>2}"
            )
            mark = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗",
                    "NO_DATA": "?"}.get(v, "?")
            print(f"  {mark} {civ:<22}  {v:<8}  {check_summary}")


def coverage_match_loop(
    repo_root: Path, run_dir: Path, threshold_ms: int,
) -> Path:
    """Path B: 6 matches × 8 civs each, OCR-verified per-slot picker selection.

    Each scenario letter A..F runs one match with the full 8-civ roster
    sourced from scenario_coverage.DEFAULT_SCENARIO_MAP. Per match:
      1. Wait for clean lobby
      2. set_anw_8civ_lobby(roster, ref) — OCR-verified per slot
      3. click_play()
      4. observe_secs (auto-resign fires at threshold_ms in-game time)
      5. cycle game so we land on the main menu again
      6. clear Age3Log.txt and start the next match

    Per-letter slices land at run_dir/scenario_logs/<LETTER>_log.txt; this
    function returns the slice directory path so the caller can fan out via
    scenario_coverage.py.
    """
    from tools.aoe3_automation import lobby_driver as lobby
    from tools.aoe3_automation import manage_game
    from tools.aoe3_automation.in_game_driver import GameDriver
    from tools.validation.scenario_coverage import DEFAULT_SCENARIO_MAP

    ref_path = repo_root / "enriched_reference.json"
    with open(ref_path) as f:
        ref = json.load(f)

    coords = lobby.load_coords()
    artifact_dir = run_dir / "scenario_logs"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    lobby_diag = run_dir / "lobby_diagnostics"
    lobby_diag.mkdir(parents=True, exist_ok=True)

    aoe3_log = (
        Path.home()
        / ".local/share/Steam/steamapps/compatdata/933110"
        / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
    )

    observe_secs = max(15, (threshold_ms // 1000) + 30)
    print(f"observe_secs={observe_secs}", flush=True)

    summary: dict[str, dict] = {}
    for letter, roster in DEFAULT_SCENARIO_MAP.items():
        # Pad short rosters (F has 6 ANW civs + 2 fillers) to 8 entries by
        # repeating the last civ. The validator only consumes ANW-civ probes;
        # filler rows give us the engine's own filler default (which is fine
        # — they don't generate ANW probes).
        full_roster = list(roster)
        while len(full_roster) < 8:
            full_roster.append(roster[-1])
        full_roster = full_roster[:8]

        # Make sure log starts fresh
        if aoe3_log.exists():
            aoe3_log.write_text("")

        print(f"\n--- Scenario {letter}: {full_roster} ---", flush=True)

        # Step 1: ensure clean lobby
        try:
            lobby.click_skirmish(coords)
            time.sleep(3)
        except Exception as e:
            print(f"  WARN click_skirmish failed: {e}", flush=True)

        # Step 2: configure the 8-slot lobby with OCR verification
        cfg = lobby.set_anw_8civ_lobby(coords, full_roster, ref)
        with open(lobby_diag / f"{letter}_lobby_cfg.json", "w") as f:
            json.dump(cfg, f, indent=2, default=str)
        print(f"  lobby ok={cfg['ok']}; "
              f"P1={cfg['p1'].get('attempts')} attempts; "
              f"opp_attempts={[o.get('attempts') for o in cfg['opponents']]}",
              flush=True)

        # Step 3: click PLAY
        lobby.click_play(coords)

        # Step 4: wait for in-game then observe
        try:
            gd = GameDriver(art_dir=lobby_diag / f"{letter}_in_game")
            gd.wait_for_in_game(timeout=360)
        except Exception as e:
            print(f"  WARN wait_for_in_game: {e}", flush=True)

        # Game observes for observe_secs; auto-resign fires from XS.
        time.sleep(observe_secs)

        # Step 5: cycle to be sure we're back at main menu cleanly
        cycle_proc = subprocess.run(
            [sys.executable,
             str(repo_root / "tools/aoe3_automation/manage_game.py"),
             "cycle", "--timeout", "180", "--post-menu-wait", "8"],
            capture_output=True, text=True, timeout=300,
        )
        if cycle_proc.returncode != 0:
            print(f"  WARN cycle rc={cycle_proc.returncode}", flush=True)

        # Step 6: slice the log
        slice_path = artifact_dir / f"{letter}_log.txt"
        if aoe3_log.exists():
            slice_path.write_text(
                aoe3_log.read_text(encoding="utf-8", errors="replace")
            )
        else:
            slice_path.write_text("")
        summary[letter] = {
            "lobby_ok": cfg["ok"],
            "log_size": slice_path.stat().st_size if slice_path.exists() else 0,
            "civs": full_roster,
        }

    with open(run_dir / "coverage_match_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return artifact_dir


def real_game_match_loop(
    repo_root: Path, run_dir: Path, threshold_ms: int,
    civs: list[str] | None,
) -> Path:
    """Run the real-game per-civ loop. Caller must already have:
       - mod synced
       - test mode enabled
       - game cycled and at main menu

    Imports the existing GameController. Returns path to concatenated log.
    """
    from tools.aoe3_automation.game_ctl import GameController
    from tools.migration.anw_token_map import ANW_CIVS
    from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX

    if civs is None:
        # Filter ANW_CIVS to only those with a picker index (i.e. in-lobby)
        civs = [t for t in ANW_CIVS.keys()
                if ANW_TO_PICKER_INDEX.get(t) is not None]

    artifact_dir = run_dir / "civ_logs"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ctl = GameController(artifact_dir)

    # The auto-resign rule fires after game-time threshold_ms. At Normal speed
    # this is wall-time too. Add 30s margin for engine flush + post-match
    # screen render.
    observe_secs = max(15, (threshold_ms // 1000) + 30)
    print(f"observe_secs={observe_secs}", flush=True)

    aoe3_log = (
        Path.home()
        / ".local/share/Steam/steamapps/compatdata/933110"
        / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
    )

    results: dict[str, dict] = {}
    for i, civ_token in enumerate(civs, 1):
        picker_idx = ANW_TO_PICKER_INDEX.get(civ_token)
        if picker_idx is None:
            print(f"[{i}/{len(civs)}] {civ_token}: SKIP (no picker index)")
            results[civ_token] = {"status": "SKIP_NO_PICKER"}
            continue

        # Clear log to capture only this civ's slice
        if aoe3_log.exists():
            aoe3_log.write_text("")

        print(f"[{i}/{len(civs)}] {civ_token} (picker_idx={picker_idx})",
              flush=True)
        match = ctl.run_match(picker_idx, observe_secs=observe_secs)
        results[civ_token] = {
            "success": match.success,
            "duration_s": match.duration_s,
            "error": match.error,
        }

        # Slice the log for this civ
        if aoe3_log.exists():
            slice_path = artifact_dir / f"{civ_token}.log"
            slice_path.write_text(
                aoe3_log.read_text(encoding="utf-8", errors="replace")
            )

    # Concatenate all slices into one log
    full_log = run_dir / "full_match.log"
    with open(full_log, "w") as out:
        for civ in civs:
            sl = artifact_dir / f"{civ}.log"
            if sl.exists():
                out.write(f"\n# === {civ} === #\n")
                out.write(sl.read_text(encoding="utf-8", errors="replace"))
    return full_log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", action="store_true",
                    help="run synthetic pipeline only (no game)")
    ap.add_argument("--scenario-dir", type=Path,
                    help="run in scenario mode: validate a directory of "
                         "per-scenario log slices (A_log.txt, …, F_log.txt) "
                         "produced by the playbook flow. Bypasses the picker. "
                         "Mutually exclusive with --synthetic.")
    ap.add_argument("--coverage-mode", action="store_true",
                    help="Path B: run 6 lobby matches × 8 civs each (46 ANW "
                         "civs across 6 matches via the playbook A-F roster). "
                         "Each lobby uses OCR-verified set_anw_8civ_lobby. "
                         "Auto-resign at --threshold-ms; one game cycle between "
                         "matches. Mutually exclusive with --synthetic and "
                         "--scenario-dir.")
    ap.add_argument("--threshold-ms", type=int, default=DEFAULT_THRESHOLD_MS,
                    help="auto-resign threshold (game-time ms)")
    ap.add_argument("--civs", nargs="*",
                    help="restrict to specific civs (default: all)")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO_ROOT / "artifacts" / "full_validation_runs",
                    help="root for run artifacts")
    args = ap.parse_args()

    if args.scenario_dir and args.synthetic:
        ap.error("--scenario-dir and --synthetic are mutually exclusive")
    if args.coverage_mode and (args.scenario_dir or args.synthetic):
        ap.error("--coverage-mode is mutually exclusive with "
                 "--scenario-dir/--synthetic")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run dir: {run_dir}")

    if args.scenario_dir:
        total_steps = 3
    elif args.synthetic:
        total_steps = 4
    elif args.coverage_mode:
        # build_ref + enable_test + sync + cycle + match_loop + coverage + done
        total_steps = 7
    else:
        total_steps = 7
    s = 0

    s += 1
    step(s, total_steps, "Build enriched_reference.json")
    ref_path = step1_build_enriched_reference(REPO_ROOT)

    # Scenario-mode short-circuit: just run the coverage report on user's
    # pre-collected log slices and bail. Bypasses both synth and real-game.
    if args.scenario_dir:
        s += 1
        step(s, total_steps, f"Scenario coverage on {args.scenario_dir}")
        coverage_proc = subprocess.run(
            [sys.executable,
             str(REPO_ROOT / "tools/validation/scenario_coverage.py"),
             "--slice-dir", str(args.scenario_dir),
             "--reference", str(ref_path),
             "--report", str(run_dir / "scenario_coverage_report.json")],
            cwd=REPO_ROOT,
        )
        s += 1
        step(s, total_steps, "Done")
        return coverage_proc.returncode

    log_path: Path
    if args.synthetic:
        s += 1
        step(s, total_steps, "Generate synthetic per-civ-correct log")
        log_path = step_synth(REPO_ROOT, run_dir, args.civs)
    elif args.coverage_mode:
        # Path B: 6 lobby matches with 8 OCR-verified civs each, then run
        # scenario_coverage on the slice dir for the 46-civ verdict.
        s += 1
        step(s, total_steps, f"Enable test mode (auto-resign at {args.threshold_ms}ms)")
        test_mode_xs.enable(args.threshold_ms)
        try:
            s += 1
            step(s, total_steps, "Sync mod to deployed tree")
            sync_proc = subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                 "sync"],
                capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
            )
            if sync_proc.returncode != 0:
                raise RuntimeError(f"sync failed: {sync_proc.stderr[-300:]}")
            print("sync ok")

            s += 1
            step(s, total_steps, "Cycle game (one-time launch)")
            subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                 "cycle", "--timeout", "180", "--post-menu-wait", "30"],
                capture_output=True, text=True, cwd=REPO_ROOT, timeout=300,
            )

            s += 1
            step(s, total_steps,
                 "Run coverage-mode match loop (6 matches × 8 civs)")
            slice_dir = coverage_match_loop(REPO_ROOT, run_dir, args.threshold_ms)

            # Fan out via scenario_coverage.py — same path the playbook uses.
            s += 1
            step(s, total_steps, f"Scenario coverage on {slice_dir}")
            coverage_proc = subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "tools/validation/scenario_coverage.py"),
                 "--slice-dir", str(slice_dir),
                 "--reference", str(ref_path),
                 "--report", str(run_dir / "scenario_coverage_report.json")],
                cwd=REPO_ROOT,
            )
            s += 1
            step(s, total_steps, "Done")
            return coverage_proc.returncode
        finally:
            print("\n[cleanup] disabling test mode...")
            test_mode_xs.disable()
            subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                 "sync"],
                capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
            )
    else:
        s += 1
        step(s, total_steps, f"Enable test mode (auto-resign at {args.threshold_ms}ms)")
        prev_threshold = test_mode_xs.enable(args.threshold_ms)

        try:
            s += 1
            step(s, total_steps, "Sync mod to deployed tree")
            sync_proc = subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                 "sync"],
                capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
            )
            if sync_proc.returncode != 0:
                raise RuntimeError(f"sync failed: {sync_proc.stderr[-300:]}")
            print("sync ok")

            s += 1
            step(s, total_steps, "Cycle game (one-time launch)")
            cycle_proc = subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                 "cycle", "--timeout", "180", "--post-menu-wait", "30"],
                capture_output=True, text=True, cwd=REPO_ROOT, timeout=300,
            )
            print(f"cycle rc={cycle_proc.returncode}")

            s += 1
            step(s, total_steps,
                 f"Run match loop (target {len(args.civs) if args.civs else 46} civs)")
            log_path = real_game_match_loop(
                REPO_ROOT, run_dir, args.threshold_ms, args.civs,
            )
        finally:
            print("\n[cleanup] disabling test mode...")
            test_mode_xs.disable()
            # Re-sync to revert the deployed mod's threshold to 0
            subprocess.run(
                [sys.executable,
                 str(REPO_ROOT / "tools/aoe3_automation/manage_game.py"),
                 "sync"],
                capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
            )

    s += 1
    step(s, total_steps, "Parse + validate full log")
    report_path = run_dir / "validation_report.json"
    report = step_validate(log_path, ref_path, report_path)
    print(f"report: {report_path}")

    s += 1
    step(s, total_steps, "Final summary")
    step_print_summary(report)

    # Top-level run summary
    summary_path = run_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "run_id": run_id,
            "synthetic": args.synthetic,
            "threshold_ms": args.threshold_ms,
            "log_path": str(log_path),
            "report_path": str(report_path),
            "overall_verdict": report["overall_verdict"],
            "civ_verdict_counts": report["civ_verdict_counts"],
            "civs_in_log": report["civs_in_log"],
            "civs_in_reference": report["civs_in_reference"],
        }, f, indent=2)
    print(f"\nSummary: {summary_path}")

    return {"PASS": 0, "WARN": 1, "FAIL": 2,
            "NO_DATA": 3}.get(report["overall_verdict"], 4)


if __name__ == "__main__":
    sys.exit(main())
