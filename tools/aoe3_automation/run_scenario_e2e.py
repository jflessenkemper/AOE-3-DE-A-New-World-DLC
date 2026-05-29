#!/usr/bin/env python3
"""End-to-end ANW scenario runner.

Stitches together the three existing harness layers so a single command can
take the system from "no game running" to "scenario complete, region crops on
disk, manifest written" without manual clicking.

    Layer 1  manage_game.py open   — launch AoE3 via Steam, dev-mode user.cfg,
                                     wait for the 1920x1080 game window to
                                     appear under gamescope.
    Layer 2  flows/anw_navigate_to_skirmish.json  — OCR-driven main-menu →
                                     Skirmish lobby navigation.
    Layer 3  scripted_scenarios.py  — drive the calibrated lobby/in-game
                                     sequence, capture the canonical region
                                     crops, write a manifest.

Why a separate orchestrator instead of bolting this onto scripted_scenarios?
Because each layer has its own correct failure modes — if launch fails we
want to skip navigate; if navigate fails we want to skip the scenario; the
artifact directory should reflect which layer succeeded. Keeping the layers
addressable individually also lets us re-run only the part that broke
(e.g. if the user is already on the lobby, ``--skip-launch --skip-navigate``).

Usage::

    # Full end-to-end (launch game, navigate, run scenario, leave game open):
    python3 tools/aoe3_automation/run_scenario_e2e.py lobby_state

    # Civ-specific:
    python3 tools/aoe3_automation/run_scenario_e2e.py picker_pixel --civ ANWBritish

    # Game already on lobby — just take the canonical crops:
    python3 tools/aoe3_automation/run_scenario_e2e.py lobby_state \\
        --skip-launch --skip-navigate

    # Close the game cleanly after the scenario finishes:
    python3 tools/aoe3_automation/run_scenario_e2e.py lobby_state --close-after

Exit codes:
    0  every requested layer succeeded
    1  launch failed (game window never appeared 1920x1080)
    2  navigate flow failed (couldn't reach lobby)
    3  scenario itself failed (driver error, screenshot mismatch, etc.)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

MANAGE_GAME = HERE / "manage_game.py"
FLOW_RUNNER = HERE / "aoe3_ui_automation.py"
NAV_FLOW = HERE / "flows" / "anw_navigate_to_skirmish.json"
SCRIPTED = HERE / "scripted_scenarios.py"


def _run(cmd: list[str], *, label: str) -> int:
    """Run a subprocess with live output, return its exit code.

    We don't capture stdout/stderr — the caller wants to see flow progress as
    it happens (each `[N/M] action` line from the flow runner) so failures are
    immediately diagnosable without re-running with --verbose.
    """
    print(f"\n=== [{label}] $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    print(f"=== [{label}] exit code: {proc.returncode}")
    return proc.returncode


def _is_game_running() -> bool:
    """Cheap check: does manage_game.py status report a live process?"""
    res = subprocess.run(
        [sys.executable, str(MANAGE_GAME), "status"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    # status returns 0 when game is running, 1 when not.
    return res.returncode == 0


def step_launch(timeout: int, no_dev_mode: bool) -> int:
    if _is_game_running():
        print("[launch] game already running — skipping `manage_game.py open`")
        return 0
    cmd = [sys.executable, str(MANAGE_GAME), "open", "--timeout", str(timeout)]
    if no_dev_mode:
        cmd.append("--no-dev-mode")
    return _run(cmd, label="launch")


def step_navigate() -> int:
    cmd = [sys.executable, str(FLOW_RUNNER), "run-flow", str(NAV_FLOW)]
    return _run(cmd, label="navigate")


def step_scenario(scenario: str, civ: str | None, observe_seconds: int,
                  out_dir: Path | None) -> int:
    cmd = [sys.executable, str(SCRIPTED), scenario]
    if civ:
        cmd.extend(["--civ", civ])
    if scenario == "match_observe":
        cmd.extend(["--observe-seconds", str(observe_seconds)])
    if out_dir is not None:
        cmd.extend(["--out", str(out_dir)])
    return _run(cmd, label=f"scenario:{scenario}")


def step_close() -> int:
    return _run([sys.executable, str(MANAGE_GAME), "close"], label="close")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "scenario",
        choices=["lobby_state", "picker_pixel", "homecity_pixel", "match_observe"],
        help="Which scripted_scenarios.py scenario to drive after navigation.",
    )
    ap.add_argument("--civ",
                    help="ANW civ token (required for picker_pixel / homecity_pixel "
                         "/ match_observe).")
    ap.add_argument("--observe-seconds", type=int, default=30,
                    help="Observation window for match_observe (default 30).")
    ap.add_argument("--out", type=Path,
                    help="Output directory for region crops (forwarded to "
                         "scripted_scenarios.py).")
    ap.add_argument("--skip-launch", action="store_true",
                    help="Skip `manage_game.py open` (the game is already running).")
    ap.add_argument("--skip-navigate", action="store_true",
                    help="Skip the main-menu→Skirmish flow (you're already on the "
                         "lobby).")
    ap.add_argument("--close-after", action="store_true",
                    help="Run `manage_game.py close` after the scenario succeeds.")
    ap.add_argument("--launch-timeout", type=int, default=120,
                    help="Seconds to wait for the AoE3 main-menu window after "
                         "Steam launch (default 120).")
    ap.add_argument("--no-dev-mode", action="store_true",
                    help="Pass --no-dev-mode to manage_game.py open (production "
                         "launch — disables aiEcho() probe capture).")
    args = ap.parse_args(argv)

    if args.scenario != "lobby_state" and not args.civ:
        ap.error(f"--civ is required for scenario '{args.scenario}'")

    # 1) Launch
    if not args.skip_launch:
        rc = step_launch(args.launch_timeout, args.no_dev_mode)
        if rc != 0:
            print(f"\nABORT: launch failed (rc={rc}). "
                  f"Game window did not appear within {args.launch_timeout}s.",
                  file=sys.stderr)
            return 1

    # Even if --skip-launch, sanity-check the game is actually up before we
    # try to drive it. Saves an opaque OCR timeout 30s later.
    if not _is_game_running():
        print("\nABORT: AoE3 is not running. Either drop --skip-launch or start "
              "the game manually.", file=sys.stderr)
        return 1

    # 2) Navigate
    if not args.skip_navigate:
        rc = step_navigate()
        if rc != 0:
            print(f"\nABORT: navigation flow failed (rc={rc}). "
                  f"Inspect artifacts/anw_nav/*.png to see where it stopped.",
                  file=sys.stderr)
            return 2

    # Tiny settle so the lobby finishes painting before lobby_driver clicks.
    time.sleep(1.0)

    # 3) Scenario
    rc = step_scenario(args.scenario, args.civ, args.observe_seconds, args.out)
    if rc != 0:
        print(f"\nABORT: scenario '{args.scenario}' failed (rc={rc}).",
              file=sys.stderr)
        return 3

    # 4) Optional close
    if args.close_after:
        step_close()  # close failures are cosmetic at this point

    print("\nALL OK — scenario complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
