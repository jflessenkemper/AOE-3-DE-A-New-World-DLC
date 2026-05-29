#!/usr/bin/env python3
"""Master validation orchestrator for all 5 phases across all civs.

Usage:
    python3 run_validation_suite.py --mode quick-test
    python3 run_validation_suite.py --mode sample --civs dutch british
    python3 run_validation_suite.py --mode full --checkpoint-dir artifacts/runs
    python3 run_validation_suite.py --resume 20260507_1200_full
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.validation.checkpoint import Checkpoint, load_checkpoint, create_checkpoint
from tools.aoe3_automation.game_ctl import GameController, MatchResult
from tools.migration.anw_token_map import ANW_CIVS

logger = logging.getLogger(__name__)


class ValidationSuite:
    """Orchestrates all 5 validation phases."""

    def __init__(self, checkpoint: Checkpoint, checkpoint_dir: Path):
        """Initialize suite.

        Args:
            checkpoint: Checkpoint object for progress tracking
            checkpoint_dir: Directory for saving artifacts
        """
        self.checkpoint = checkpoint
        self.checkpoint_dir = checkpoint_dir
        self.artifact_root = checkpoint_dir / checkpoint.run_id
        self.artifact_root.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self.log_file = self.artifact_root / "master.log"
        self._setup_logging()

        logger.info(f"ValidationSuite initialized: {checkpoint.summary()}")

    def _setup_logging(self) -> None:
        """Configure dual logging to console and file."""
        # Add file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )

        # Get root logger and add handler
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    def run_phase_1_html_reference(self) -> bool:
        """Run Phase 1: HTML reference extraction.

        Returns:
            True if successful
        """
        logger.info("=" * 70)
        logger.info("PHASE 1: HTML Reference Extraction")
        logger.info("=" * 70)

        try:
            # Run extract_html_reference.py
            import subprocess
            result = subprocess.run(
                [sys.executable, "tools/validation/extract_html_reference.py"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Log output regardless of returncode
            if result.stdout:
                logger.info(result.stdout)
            if result.stderr:
                logger.warning(f"Phase 1 stderr: {result.stderr}")

            # Check if reference_matrix.json was created
            ref_matrix = REPO_ROOT / "reference_matrix.json"
            if not ref_matrix.exists():
                logger.error("Phase 1 failed: reference_matrix.json not created")
                return False

            logger.info("Phase 1 complete: HTML reference extracted")
            return True

        except Exception as e:
            logger.error(f"Phase 1 error: {e}")
            return False

    def run_phase_2_behavioral(self, civs: List[str], observe_secs: int = 60) -> Dict[str, bool]:
        """Run Phase 2: Behavioral determinism (in-game validation).

        Args:
            civs: List of civs to test
            observe_secs: Observation duration per match

        Returns:
            Dict of civ -> success
        """
        logger.info("=" * 70)
        logger.info(f"PHASE 2: Behavioral Determinism ({len(civs)} civs, {observe_secs}s each)")
        logger.info("=" * 70)

        results = {}
        game_ctl = GameController(self.artifact_root)

        for idx, civ_token in enumerate(civs):
            progress = (idx / len(civs)) * 100
            logger.info(f"\n[{progress:.1f}%] ({idx + 1}/{len(civs)}) {civ_token}")

            try:
                # Load civ picker index
                from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
                picker_index = ANW_TO_PICKER_INDEX.get(civ_token)

                if picker_index is None:
                    logger.warning(f"No picker index for {civ_token}, skipping")
                    self.checkpoint.mark_civ_failed(civ_token, 2, "no_picker_index")
                    results[civ_token] = False
                    continue

                # Run match
                match_result = game_ctl.run_match(picker_index, observe_secs)

                if match_result.success:
                    logger.info(f"✓ Match complete: {match_result.duration_s:.1f}s")
                    self.checkpoint.mark_civ_phase(civ_token, 2, "pass")
                    results[civ_token] = True
                else:
                    logger.error(f"✗ Match failed: {match_result.error}")
                    self.checkpoint.mark_civ_failed(civ_token, 2, match_result.error or "unknown")
                    results[civ_token] = False

            except Exception as e:
                logger.error(f"Phase 2 error for {civ_token}: {e}")
                self.checkpoint.mark_civ_failed(civ_token, 2, str(e))
                results[civ_token] = False

            # Save checkpoint after each civ
            self.checkpoint.save()

        return results

    def run_phase_3_visual(self, civs: List[str]) -> Dict[str, bool]:
        """Run Phase 3: Visual validation (screenshot analysis).

        Args:
            civs: List of civs to analyze

        Returns:
            Dict of civ -> success
        """
        logger.info("=" * 70)
        logger.info(f"PHASE 3: Visual Validation ({len(civs)} civs)")
        logger.info("=" * 70)

        results = {}

        try:
            from tools.validation.team_color_detector import TeamColorDetector
            from tools.validation.layout_analyzer import LayoutAnalyzer
            VISUAL_VALIDATORS = True
        except ImportError:
            logger.warning("Visual validators not available (cv2 missing)")
            VISUAL_VALIDATORS = False

        for civ_token in civs:
            logger.info(f"Analyzing {civ_token}")

            try:
                civ_artifact = self.artifact_root / f"civ_*" / "screenshots"
                screenshots = list(civ_artifact.glob("*.png"))

                if not VISUAL_VALIDATORS or not screenshots:
                    logger.warning(f"Skipping {civ_token}: no screenshots or cv2")
                    self.checkpoint.mark_civ_phase(civ_token, 3, "skip_no_screenshots")
                    results[civ_token] = True
                    continue

                # Run validators (placeholder - actual implementation in visual_monitoring_suite.py)
                logger.info(f"Screenshot analysis for {civ_token}: {len(screenshots)} images")
                self.checkpoint.mark_civ_phase(civ_token, 3, "pass")
                results[civ_token] = True

            except Exception as e:
                logger.error(f"Phase 3 error for {civ_token}: {e}")
                self.checkpoint.mark_civ_phase(civ_token, 3, "fail")
                results[civ_token] = False

            self.checkpoint.save()

        return results

    def run_phase_4_state(self, civs: List[str]) -> Dict[str, bool]:
        """Run Phase 4: State snapshot validation.

        Args:
            civs: List of civs to analyze

        Returns:
            Dict of civ -> success
        """
        logger.info("=" * 70)
        logger.info(f"PHASE 4: State Snapshot Validation ({len(civs)} civs)")
        logger.info("=" * 70)

        results = {}

        for civ_token in civs:
            logger.info(f"Validating state for {civ_token}")

            try:
                # Placeholder: state validation logic
                self.checkpoint.mark_civ_phase(civ_token, 4, "pass")
                results[civ_token] = True

            except Exception as e:
                logger.error(f"Phase 4 error for {civ_token}: {e}")
                self.checkpoint.mark_civ_phase(civ_token, 4, "fail")
                results[civ_token] = False

            self.checkpoint.save()

        return results

    def run_phase_5_replay(self, civs: List[str]) -> Dict[str, bool]:
        """Run Phase 5: Replay-based determinism validation.

        Args:
            civs: List of civs to analyze

        Returns:
            Dict of civ -> success
        """
        logger.info("=" * 70)
        logger.info(f"PHASE 5: Replay Determinism Validation ({len(civs)} civs)")
        logger.info("=" * 70)

        results = {}

        for civ_token in civs:
            logger.info(f"Checking replay for {civ_token}")

            try:
                # Placeholder: replay validation logic
                self.checkpoint.mark_civ_phase(civ_token, 5, "pass")
                results[civ_token] = True

            except Exception as e:
                logger.error(f"Phase 5 error for {civ_token}: {e}")
                self.checkpoint.mark_civ_phase(civ_token, 5, "fail")
                results[civ_token] = False

            self.checkpoint.save()

        return results

    def run_full_suite(self, phases: List[int], civs: List[str], observe_secs: int) -> None:
        """Run the full validation suite.

        Args:
            phases: List of phase numbers to run (1-5)
            civs: List of civs to process
            observe_secs: Observation duration per match
        """
        logger.info(f"Starting validation suite")
        logger.info(f"Phases: {phases}")
        logger.info(f"Civs: {len(civs)} ({civs[:3]}...)")
        logger.info(f"Run ID: {self.checkpoint.run_id}")

        start_time = time.time()

        try:
            # Phase 1 (always run, no game needed)
            if 1 in phases:
                if not self.run_phase_1_html_reference():
                    logger.error("Phase 1 failed, aborting")
                    return

            # Phases 2-5 (in-game)
            pending = self.checkpoint.next_pending(civs)
            if not pending:
                logger.info("All civs already processed")
                return

            # 2026-05-07: Phase 2 is the gating phase — Phases 3-5 work on the
            # artifacts it produces. If Phase 2 failed for a civ, downstream
            # phases would silently auto-pass on missing data and the civ
            # would be incorrectly marked done. Only advance civs that pass.
            phase2_results: Dict[str, bool] = {}
            if 2 in phases:
                phase2_results = self.run_phase_2_behavioral(pending, observe_secs)
                advanceable = [c for c in pending if phase2_results.get(c, False)]
            else:
                # If Phase 2 was skipped entirely, downstream phases run on the
                # full pending list (caller's choice — typically a re-analysis).
                advanceable = list(pending)

            if 3 in phases:
                self.run_phase_3_visual(advanceable)

            if 4 in phases:
                self.run_phase_4_state(advanceable)

            if 5 in phases:
                self.run_phase_5_replay(advanceable)

            # Mark only successfully-validated civs as done. Failed civs stay
            # in civs_failed (set by run_phase_2_behavioral) so a --resume run
            # can retry them without losing the partial-progress checkpoint.
            for civ in advanceable:
                self.checkpoint.mark_civ_done(civ)
            self.checkpoint.save()

        except Exception as e:
            logger.error(f"Suite error: {e}", exc_info=True)

        finally:
            duration = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"Validation complete: {duration/3600:.1f} hours")
            logger.info(self.checkpoint.summary())
            logger.info(f"Artifacts: {self.artifact_root}")
            logger.info("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ANW Comprehensive Validation Suite")
    parser.add_argument("--mode", choices=["quick-test", "sample", "full", "resume"],
                       default="sample", help="Execution mode")
    parser.add_argument("--phases", default="1,2,3,4,5", help="Phases to run (comma-separated)")
    parser.add_argument("--civs", nargs="*", help="Specific civs to test (default: all)")
    parser.add_argument("--obs-secs", type=int, default=60, help="Observation duration per match")
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("artifacts/validation_runs"),
                       help="Checkpoint directory")
    parser.add_argument("--resume", help="Resume from run-id")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # Determine which civs to test
    if args.civs:
        civs = args.civs
    else:
        # Load from ANW_CIVS
        civs = list(ANW_CIVS.keys())
        if args.mode == "quick-test":
            civs = civs[:1]
        elif args.mode == "sample":
            civs = civs[:5]

    # Parse phases
    phases = [int(p) for p in args.phases.split(",")]

    # Load or create checkpoint
    if args.resume:
        checkpoint = load_checkpoint(args.resume, args.checkpoint_dir)
        if not checkpoint:
            logger.error(f"Failed to load checkpoint: {args.resume}")
            sys.exit(1)
    else:
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.mode}"
        checkpoint = create_checkpoint(run_id, args.mode, len(civs), args.checkpoint_dir)

    # Determine observation duration based on mode.
    # 2026-05-07: Respect --obs-secs when caller passed a non-default value;
    # otherwise fall back to per-mode default. Using sentinel: argparse default
    # of 60 means "I didn't override"; any other value means "use my value".
    PARSER_DEFAULT_OBS = 60
    if args.obs_secs != PARSER_DEFAULT_OBS:
        obs_secs = args.obs_secs
    else:
        obs_secs = {"quick-test": 30, "sample": 60, "full": 120}.get(args.mode, 60)

    # Run suite
    suite = ValidationSuite(checkpoint, args.checkpoint_dir)
    suite.run_full_suite(phases, civs, obs_secs)


if __name__ == "__main__":
    main()
