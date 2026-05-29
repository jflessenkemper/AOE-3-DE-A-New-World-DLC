#!/usr/bin/env python3
"""Master validator for ANW — orchestrates full 5-phase deterministic testing.

Phases:
  1. HTML Reference Validation (extract a_new_world.html as ground truth)
  2. Behavioral Determinism (run all 48 civs, validate probes + properties)
  3. Visual Monitoring (screenshot every 30s, analyze team colors, OCR, layout)
  4. State Snapshot Validation (compare game state trajectories)
  5. Replay-Based Testing (parse replays, verify bit-perfect determinism)

Usage:
    python3 master_validator_anw.py --all  # All phases, all civs (8+ hours)
    python3 master_validator_anw.py --phase 2 --sample  # Phase 2 only, 5 civs
    python3 master_validator_anw.py --phase 2 --all --observe-seconds 120
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict

# Repo setup
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


class MasterValidatorANW:
    """Orchestrates all validation phases."""

    def __init__(self):
        """Initialize validator."""
        self.ref_matrix_path = Path("reference_matrix.json")
        self.reports = {}

    def phase_1_html_reference(self) -> Dict:
        """Phase 1: Extract HTML reference as ground truth."""
        logger.info("")
        logger.info("="*70)
        logger.info("PHASE 1: HTML Reference Validation")
        logger.info("="*70)

        try:
            from tools.validation.extract_html_reference import (
                extract_civ_metadata,
                generate_reference_matrix,
                merge_with_playstyle_spec,
                validate_reference_matrix,
            )

            # Read HTML
            html_path = Path("a_new_world.html")
            if not html_path.exists():
                logger.error(f"HTML reference not found: {html_path}")
                return {"status": "failed", "error": "HTML file not found"}

            logger.info(f"[→] Parsing {html_path}")
            html_content = html_path.read_text()

            # Extract civs
            logger.info(f"[→] Extracting civilization metadata")
            html_civs = extract_civ_metadata(html_content)
            logger.info(f"[+] Found {len(html_civs)} civs in HTML")

            # Generate matrix
            logger.info(f"[→] Generating reference_matrix.json")
            reference_matrix = generate_reference_matrix(html_civs)
            logger.info(f"[+] Generated matrix: {reference_matrix['total_civs']} civs")

            # Merge with playstyle spec
            logger.info(f"[→] Merging with playstyle_spec.json")
            reference_matrix = merge_with_playstyle_spec(
                reference_matrix,
                Path("playstyle_spec.json")
            )

            # Validate
            logger.info(f"[→] Validating reference matrix")
            issues = validate_reference_matrix(reference_matrix)
            if issues:
                logger.warning(f"[!] Found {len(issues)} validation issues:")
                for issue in issues:
                    logger.warning(f"    - {issue}")
            else:
                logger.info(f"[✓] Reference matrix validation PASSED")

            # Save
            logger.info(f"[→] Saving reference_matrix.json")
            with open(self.ref_matrix_path, 'w') as f:
                json.dump(reference_matrix, f, indent=2)

            result = {
                "status": "completed",
                "civs_extracted": len(html_civs),
                "civs_in_matrix": reference_matrix['total_civs'],
                "validation_issues": len(issues),
                "reference_matrix_path": str(self.ref_matrix_path),
            }
            logger.info(f"[✓] Phase 1 COMPLETE")
            return result

        except Exception as e:
            logger.error(f"[✗] Phase 1 FAILED: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    def phase_2_behavioral_determinism(
        self,
        all_civs: bool = False,
        sample_size: int = 5,
        civs: Optional[list] = None,
        observe_seconds: int = 60,
    ) -> Dict:
        """Phase 2: Behavioral determinism validation."""
        logger.info("")
        logger.info("="*70)
        logger.info("PHASE 2: Behavioral Determinism Validation")
        logger.info("="*70)

        try:
            from tools.aoe3_automation.exhibition_runner_anw import ExhibitionRunnerANW

            # Load reference matrix
            if not self.ref_matrix_path.exists():
                logger.error("reference_matrix.json not found")
                return {"status": "failed", "error": "reference_matrix.json missing"}

            logger.info(f"[→] Loaded reference_matrix.json")

            # Create runner
            timestamp = __import__('time').strftime("%Y%m%d_%H%M%S")
            artifact_dir = Path(f"artifacts/anw_exhibition_{timestamp}")
            runner = ExhibitionRunnerANW(artifact_root=artifact_dir)

            # Run matches
            if civs and len(civs) > 0:
                logger.info(f"[→] Running {len(civs)} specified civs")
                results = runner.run_specific_civs(civs, observe_seconds)
            elif all_civs:
                logger.info(f"[→] Running all 48 civs")
                results = runner.run_all_civs(observe_seconds)
            else:
                logger.info(f"[→] Running sample ({sample_size} civs)")
                results = runner.run_sample(sample_size, observe_seconds)

            # Generate report
            report = runner.generate_report()
            runner.save_report(report)

            logger.info(f"[✓] Phase 2 COMPLETE")
            return {
                "status": "completed",
                "total_matches": report['summary']['total_matches'],
                "completed": report['summary']['completed'],
                "success_rate_pct": report['summary']['success_rate_pct'],
                "validator_pass_rate_pct": report['validation_summary']['pass_rate_pct'],
                "artifact_dir": str(artifact_dir),
                "report_path": str(artifact_dir / "compliance_report.json"),
            }

        except Exception as e:
            logger.error(f"[✗] Phase 2 FAILED: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    def phase_3_visual_monitoring(self) -> Dict:
        """Phase 3: Continuous visual monitoring."""
        logger.info("")
        logger.info("="*70)
        logger.info("PHASE 3: Visual Monitoring (TBD)")
        logger.info("="*70)
        logger.info("[!] Phase 3 not yet implemented")
        logger.info("    Required: team_color_detector, ocr_validator, layout_analyzer")
        return {"status": "pending"}

    def phase_4_state_validation(self) -> Dict:
        """Phase 4: State snapshot validation."""
        logger.info("")
        logger.info("="*70)
        logger.info("PHASE 4: State Snapshot Validation (TBD)")
        logger.info("="*70)
        logger.info("[!] Phase 4 not yet implemented")
        logger.info("    Required: XS state snapshot trigger, state diff validator")
        return {"status": "pending"}

    def phase_5_determinism(self) -> Dict:
        """Phase 5: Replay-based bit-perfect testing."""
        logger.info("")
        logger.info("="*70)
        logger.info("PHASE 5: Replay-Based Determinism (TBD)")
        logger.info("="*70)
        logger.info("[!] Phase 5 not yet implemented")
        logger.info("    Required: replay_parser, determinism_validator")
        return {"status": "pending"}

    def run(
        self,
        phases: list = None,
        all_civs: bool = False,
        sample_size: int = 5,
        civs: Optional[list] = None,
        observe_seconds: int = 60,
    ):
        """Run specified validation phases."""
        if phases is None:
            phases = [1, 2]  # Default: phases 1-2

        logger.info("")
        logger.info("="*70)
        logger.info("ANW Master Validator")
        logger.info("="*70)
        logger.info(f"Phases to run: {phases}")
        logger.info(f"All civs: {all_civs}, Sample size: {sample_size}")
        logger.info(f"Observation window: {observe_seconds}s")
        logger.info("")

        if 1 in phases:
            self.reports['phase_1'] = self.phase_1_html_reference()

        if 2 in phases:
            self.reports['phase_2'] = self.phase_2_behavioral_determinism(
                all_civs=all_civs,
                sample_size=sample_size,
                civs=civs,
                observe_seconds=observe_seconds,
            )

        if 3 in phases:
            self.reports['phase_3'] = self.phase_3_visual_monitoring()

        if 4 in phases:
            self.reports['phase_4'] = self.phase_4_state_validation()

        if 5 in phases:
            self.reports['phase_5'] = self.phase_5_determinism()

        # Summary
        logger.info("")
        logger.info("="*70)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*70)
        for phase, report in self.reports.items():
            status = report.get('status', 'unknown').upper()
            logger.info(f"{phase}: {status}")
            if status == "COMPLETED":
                if 'success_rate_pct' in report:
                    logger.info(
                        f"  Success rate: {report['success_rate_pct']:.1f}%"
                    )
                if 'validator_pass_rate_pct' in report:
                    logger.info(
                        f"  Validator pass rate: {report['validator_pass_rate_pct']:.1f}%"
                    )

        # Save master report
        master_report = {
            "timestamp": __import__('time').time(),
            "phases": self.reports,
        }
        report_path = Path("artifacts/master_validation_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(master_report, f, indent=2)

        logger.info(f"\nMaster report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Master validator for ANW — orchestrates all validation phases"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4, 5],
        nargs="+",
        default=[1, 2],
        help="Phases to run (default: 1 2)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all civs (default: sample of 5)"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Sample size for --all not specified (default: 5)"
    )
    parser.add_argument(
        "--civs",
        nargs="*",
        default=None,
        help="Run specific civs (e.g., --civs ANWBritish ANWFrench)"
    )
    parser.add_argument(
        "--observe-seconds",
        type=int,
        default=60,
        help="Observation duration per match (default: 60)"
    )

    args = parser.parse_args()

    validator = MasterValidatorANW()
    validator.run(
        phases=args.phase,
        all_civs=args.all,
        sample_size=args.sample,
        civs=args.civs,
        observe_seconds=args.observe_seconds,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
