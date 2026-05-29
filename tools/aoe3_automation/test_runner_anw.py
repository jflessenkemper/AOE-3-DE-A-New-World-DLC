#!/usr/bin/env python3
"""Quick test runner for ANW — validates single civ through a real match.

Tests the full pipeline:
  1. Launch game
  2. Select a civ
  3. Run match + capture log
  4. Extract [LLP v=2] probes
  5. Validate with PropertyValidatorSuite
  6. Report results

Usage:
    python3 test_runner_anw.py --civ ANWBritish --observe-seconds 60
"""
import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

# Repo setup (match matrix_runner.py pattern)
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]  # tools/aoe3_automation -> tools -> repo_root
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from tools.migration.anw_token_map import ANW_CIVS
from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

ARTIFACT_DIR = Path("artifacts/anw_test")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# Try to import game drivers (may not be available outside game env)
try:
    import lobby_driver as lobby
    from tools.aoe3_automation.in_game_driver import GameDriver
    from tools.aoe3_automation.log_capture import start_log_tail, AGE3_LOG_PATH
    GAME_HARNESS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Game harness not available: {e}")
    GAME_HARNESS_AVAILABLE = False

# Import validators
try:
    from tools.validation.property_validators_v1 import PropertyValidatorSuite
    VALIDATORS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Validators not available: {e}")
    VALIDATORS_AVAILABLE = False


def run_test_match(civ_token: str, observe_seconds: int = 60) -> dict:
    """Run a single real match and return results."""

    if not GAME_HARNESS_AVAILABLE:
        logger.error("Game harness not available. Can only run in-game.")
        return {
            "status": "error",
            "error": "Game harness not available",
            "civ": civ_token,
        }

    civ_name = ANW_CIVS.get(civ_token, {}).get("display", civ_token)
    picker_index = ANW_TO_PICKER_INDEX.get(civ_token)

    if picker_index is None:
        logger.error(f"No picker index for {civ_token}")
        return {
            "status": "error",
            "error": f"No picker index for {civ_token}",
            "civ": civ_token,
        }

    match_dir = ARTIFACT_DIR / f"{civ_token}_test"
    match_dir.mkdir(parents=True, exist_ok=True)
    log_path = match_dir / "match.log"

    logger.info(f"[TEST] Starting match: {civ_token} ({civ_name})")
    start_time = time.time()

    try:
        # Load lobby coordinates
        logger.info("[TEST] Loading lobby coordinates...")
        coords = lobby.load_coords()

        # 1. Verify at lobby
        logger.info("[TEST] Ensuring clean lobby...")
        try:
            lobby.screenshot(match_dir / "00_lobby_start.png")
            logger.info("[TEST] Lobby verified")
        except Exception as e:
            logger.warning(f"Lobby check failed: {e}")

        # 2. Select civ
        logger.info(f"[TEST] Selecting civ (picker index {picker_index})")
        try:
            lobby.set_civ_by_index(coords, picker_index)
            time.sleep(1)
            lobby.screenshot(match_dir / "01_civ_selected.png")
        except Exception as e:
            logger.error(f"Civ selection failed: {e}")
            raise

        # 3. Start log capture
        logger.info("[TEST] Starting log capture")
        log_mirror = start_log_tail(log_path)
        time.sleep(1)

        # 4. Click PLAY
        logger.info("[TEST] Clicking PLAY")
        try:
            lobby.click_play(coords)
        except Exception as e:
            logger.error(f"PLAY click failed: {e}")
            raise

        # 5. Wait for in-game
        logger.info("[TEST] Waiting for match to start...")
        driver = GameDriver(art_dir=match_dir)
        in_game = driver.wait_for_in_game(timeout=60, log_mirror=log_mirror)

        if not in_game:
            raise RuntimeError("Timeout waiting for match to start")

        logger.info(f"[TEST] Match started, observing for {observe_seconds}s")
        time.sleep(observe_seconds)

        # 6. Capture in-game screenshot
        logger.info("[TEST] Capturing in-game state")
        try:
            driver._screenshot_raw(match_dir / "02_in_game.png")
        except Exception as e:
            logger.warning(f"Screenshot capture failed: {e}")

        # 7. Resign
        logger.info("[TEST] Resigning match")
        try:
            driver.resign()
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Resign failed: {e}")

        # 8. Capture end state
        try:
            lobby.screenshot(match_dir / "03_end_state.png")
        except Exception as e:
            logger.warning(f"End screenshot failed: {e}")

        # 9. Parse results
        log_content = log_path.read_text() if log_path.exists() else ""

        validation_results = {}
        if VALIDATORS_AVAILABLE:
            logger.info("[TEST] Running property validators")
            validators = PropertyValidatorSuite()
            validation_results = validators.validate(log_content, {})
            passed, summary = validators.summarize(validation_results)
            logger.info(f"[TEST] Validation: {'PASS' if passed else 'FAIL'}")
            logger.info(f"[TEST] Summary: {summary}")
        else:
            logger.warning("Validators not available, skipping validation")

        end_time = time.time()
        duration = end_time - start_time

        return {
            "status": "completed",
            "civ": civ_token,
            "civ_name": civ_name,
            "duration_seconds": duration,
            "observe_seconds": observe_seconds,
            "log_path": str(log_path),
            "log_lines": len(log_content.splitlines()),
            "artifact_dir": str(match_dir),
            "validation_results": validation_results,
            "screenshots": [
                str(f) for f in sorted(match_dir.glob("*.png"))
            ],
        }

    except Exception as e:
        logger.error(f"[TEST] Match failed: {e}", exc_info=True)
        end_time = time.time()
        return {
            "status": "error",
            "civ": civ_token,
            "civ_name": civ_name,
            "error": str(e),
            "duration_seconds": end_time - start_time,
            "artifact_dir": str(match_dir),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Quick test runner for ANW"
    )
    parser.add_argument(
        "--civ",
        default="ANWBritish",
        help="ANW civ token to test (default: ANWBritish)"
    )
    parser.add_argument(
        "--observe-seconds",
        type=int,
        default=60,
        help="Observation duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually run the match (test harness setup only)"
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("ANW Test Runner")
    logger.info("="*60)
    logger.info(f"Civ: {args.civ}")
    logger.info(f"Observation: {args.observe_seconds}s")
    logger.info(f"Artifact dir: {ARTIFACT_DIR}")
    logger.info(f"Game harness available: {GAME_HARNESS_AVAILABLE}")
    logger.info(f"Validators available: {VALIDATORS_AVAILABLE}")
    logger.info("")

    if args.dry_run:
        logger.info("[DRY RUN] Skipping actual match execution")
        return 0

    result = run_test_match(args.civ, args.observe_seconds)

    # Save result
    result_file = ARTIFACT_DIR / f"{args.civ}_result.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)

    logger.info("")
    logger.info("="*60)
    logger.info(f"Result: {result['status'].upper()}")
    logger.info("="*60)

    if result["status"] == "completed":
        logger.info(f"Duration: {result['duration_seconds']:.1f}s")
        logger.info(f"Log lines: {result['log_lines']}")
        logger.info(f"Screenshots: {len(result['screenshots'])}")
        if result.get("validation_results"):
            logger.info(f"Validators run: {len(result['validation_results'])}")
            for name, (passed, msg) in result["validation_results"].items():
                status = "✓" if passed else "✗"
                logger.info(f"  {status} {name}: {msg}")
        logger.info(f"Results saved: {result_file}")
        return 0
    else:
        logger.error(f"Error: {result.get('error', 'Unknown')}")
        logger.info(f"Results saved: {result_file}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
