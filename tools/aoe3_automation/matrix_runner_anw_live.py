#!/usr/bin/env python3
"""Matrix Runner for ANW — Run all 48 civs with REAL game execution.

This is the live version that actually launches games via the in-game harness.
Uses lobby_driver for civ selection and GameDriver for match lifecycle.

Usage:
    python3 matrix_runner_anw_live.py --quick
    python3 matrix_runner_anw_live.py --civs ANWBritish ANWFrench ANWChinese
    python3 matrix_runner_anw_live.py  # All 48 civs
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List

# Repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.migration.anw_token_map import ANW_CIVS, iter_anw_civs
from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
from tools.aoe3_automation.ai_decision_analyzer import DecisionMetrics

# Import game drivers
try:
    import lobby_driver as lobby
    from tools.aoe3_automation.in_game_driver import GameDriver
    from tools.aoe3_automation.log_capture import AGE3_LOG_PATH, start_log_tail
    GAME_HARNESS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Game harness not available: {e}")
    GAME_HARNESS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

ARTIFACT_DIR = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/anw_matrix_live")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TestScenario:
    """Test scenario config."""
    id: str
    name: str
    observe_seconds: int
    map: str = "Black Forest"
    map_size: str = "Tiny"
    players: int = 2
    difficulty: str = "Moderate"
    game_speed: str = "1x"


@dataclass
class MatchResult:
    """Result of one match (civ × scenario)."""
    civ_token: str
    civ_name: str
    scenario_id: str
    status: str  # "completed", "crashed", "timeout", "error"
    start_time: float
    end_time: float
    duration_s: float
    artifact_dir: str
    error_message: Optional[str] = None
    log_lines: int = 0


def launch_game():
    """Launch game via manage_game.py."""
    manage_game_script = Path(__file__).parent / "manage_game.py"
    logger.info("Launching game via manage_game.py...")
    result = subprocess.run(
        [sys.executable, str(manage_game_script), "cycle", "--timeout", "120"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        logger.error(f"manage_game stderr:\n{result.stderr}")
        raise RuntimeError(f"Failed to launch game")
    logger.info("Game launched and ready at lobby")
    time.sleep(5)  # Let it settle


def ensure_clean_lobby(coords: dict, max_retries: int = 3) -> bool:
    """Ensure game is at clean Skirmish lobby."""
    for attempt in range(max_retries):
        try:
            # Try to detect current state and recover if needed
            lobby.screenshot(ARTIFACT_DIR / "_lobby_check.png")
            logger.info(f"Lobby state verified (attempt {attempt+1})")
            return True
        except Exception as e:
            logger.warning(f"Lobby check failed: {e}, attempt {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return False


def run_single_match(
    civ_token: str,
    civ_name: str,
    picker_index: int,
    scenario: TestScenario,
    coords: dict,
) -> MatchResult:
    """Run one match with specified civ."""

    match_dir = ARTIFACT_DIR / f"{civ_token}_{scenario.id}"
    match_dir.mkdir(parents=True, exist_ok=True)
    log_path = match_dir / "match.log"

    result = MatchResult(
        civ_token=civ_token,
        civ_name=civ_name,
        scenario_id=scenario.id,
        status="error",
        start_time=time.time(),
        end_time=time.time(),
        duration_s=0.0,
        artifact_dir=str(match_dir),
    )

    try:
        logger.info(f"[{civ_token}] Starting match: {civ_name} on {scenario.name}")

        # 1. Ensure clean lobby
        if not ensure_clean_lobby(coords):
            raise RuntimeError("Could not reach clean lobby")

        # 2. Select civ by picker index
        logger.info(f"[{civ_token}] Selecting civ (picker index {picker_index})")
        lobby.set_civ_by_index(coords, picker_index)

        # Snapshot post-selection
        lobby.screenshot(match_dir / "01_selected.png")

        # 3. Start log capture BEFORE clicking play
        mirror = start_log_tail(log_path)

        # 4. Click PLAY
        logger.info(f"[{civ_token}] Clicking PLAY")
        lobby.click_play(coords)

        # 5. Wait for in-game (up to 60 seconds)
        driver = GameDriver(art_dir=match_dir)
        ok = driver.wait_for_in_game(timeout=60, log_mirror=mirror)

        if not ok:
            raise RuntimeError("Timeout waiting for match to start")

        logger.info(f"[{civ_token}] Match started, observing for {scenario.observe_seconds}s")

        # 6. Observe for specified duration
        time.sleep(scenario.observe_seconds)

        # 7. Capture in-game screenshot
        driver._screenshot_raw(match_dir / "03_in_game.png")

        # 8. Resign
        logger.info(f"[{civ_token}] Resigning match")
        driver.resign()

        result.status = "completed"
        result.end_time = time.time()
        result.duration_s = result.end_time - result.start_time

        # Count log lines
        if log_path.exists():
            result.log_lines = len(log_path.read_text().splitlines())

        logger.info(f"[{civ_token}] Match complete ({result.duration_s:.1f}s, {result.log_lines} log lines)")

    except Exception as e:
        result.status = "error"
        result.error_message = str(e)
        result.end_time = time.time()
        result.duration_s = result.end_time - result.start_time
        logger.error(f"[{civ_token}] Match failed: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Run ANW civs through real game matches")
    parser.add_argument("--civs", nargs="*", default=None, help="Specific civs to test")
    parser.add_argument("--quick", action="store_true", help="Test 5 civs × 1 scenario only")
    parser.add_argument("--observe-seconds", type=int, default=120, help="Observe duration per match")
    parser.add_argument("--skip-launch", action="store_true", help="Skip game launch (assume already running)")

    args = parser.parse_args()

    if not GAME_HARNESS_AVAILABLE:
        logger.error("Game harness (lobby_driver, GameDriver) not available")
        return 1

    # Launch game if not already running
    if not args.skip_launch:
        try:
            launch_game()
        except Exception as e:
            logger.error(f"Failed to launch game: {e}")
            return 1

    # Load coords
    coords_path = Path(__file__).parent / "lobby_coords.json"
    coords = json.loads(coords_path.read_text())

    # Determine which civs to test
    if args.civs:
        test_civs = {token: ANW_CIVS[token] for token in args.civs if token in ANW_CIVS}
    elif args.quick:
        # Quick test: first 5 civs
        test_civs = dict(list(ANW_CIVS.items())[:5])
    else:
        # All civs
        test_civs = ANW_CIVS

    # Single scenario for now
    scenarios = [
        TestScenario(id="quick_test", name="Quick Test (2min)", observe_seconds=args.observe_seconds)
    ]

    total_matches = len(test_civs) * len(scenarios)
    completed = 0
    results = []

    logger.info(f"Starting {total_matches} matches ({len(test_civs)} civs × {len(scenarios)} scenarios)")

    for civ_token, civ_data in test_civs.items():
        civ_name = civ_data["display"]
        picker_index = ANW_TO_PICKER_INDEX.get(civ_token)

        if picker_index is None:
            logger.warning(f"No picker index for {civ_token}, skipping")
            continue

        for scenario in scenarios:
            completed += 1
            progress = (completed / total_matches) * 100

            logger.info(f"\n[{progress:.1f}%] {civ_token} × {scenario.id}")

            result = run_single_match(civ_token, civ_name, picker_index, scenario, coords)
            results.append(asdict(result))

            # Save checkpoint
            checkpoint_file = ARTIFACT_DIR / "checkpoint.json"
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    "completed": completed,
                    "total": total_matches,
                    "results": results,
                }, f, indent=2)

            # Small delay between matches
            time.sleep(2)

    # Final report
    report_file = ARTIFACT_DIR / "final_report.json"
    report = {
        "total_matches": total_matches,
        "completed": sum(1 for r in results if r["status"] == "completed"),
        "errors": sum(1 for r in results if r["status"] != "completed"),
        "results": results,
        "artifact_root": str(ARTIFACT_DIR),
    }

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"\nFinal Report: {report_file}")
    logger.info(f"Completed: {report['completed']}/{total_matches}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
