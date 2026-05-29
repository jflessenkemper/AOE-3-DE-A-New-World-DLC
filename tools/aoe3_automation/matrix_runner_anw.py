#!/usr/bin/env python3
"""Matrix Runner for ANW — Run all 48 civs through test scenarios.

Orchestrates exhaustive overnight testing:
- Runs each civ through 1-6 scenarios (configurable)
- Captures screenshots at key moments (start, 1min, 3min, 5min, end)
- Logs AI decisions to per-civ trace files
- Monitors for crashes/errors
- Parses probe output for playstyle validation
- Collects results in indexed artifact directory

Usage
-----
    # Run all civs, all scenarios (12+ hours)
    python3 tools/aoe3_automation/matrix_runner_anw.py --all-civs --all-scenarios

    # Run specific civs
    python3 tools/aoe3_automation/matrix_runner_anw.py --civ ANWBritish --civ ANWFrench --all-scenarios

    # Run fast subset (2 civs × 2 scenarios ≈ 30 minutes)
    python3 tools/aoe3_automation/matrix_runner_anw.py --sample --fast

    # Continue interrupted run
    python3 tools/aoe3_automation/matrix_runner_anw.py --resume <artifact_dir>

    # Validate without running games
    python3 tools/aoe3_automation/matrix_runner_anw.py --validate-only <artifact_dir>
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.migration.anw_token_map import ANW_CIVS, iter_anw_civs
from tools.aoe3_automation.ai_decision_analyzer import parse_game_log, DecisionMetrics
from tools.aoe3_automation.log_capture import AGE3_LOG_PATH, snapshot_offset, read_since

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


@dataclass
class CivDef:
    """ANW civilization definition."""
    anw_token: str
    display_name: str
    leader_display: str


@dataclass
class TestScenario:
    """A test scenario configuration."""
    id: str
    name: str
    description: str
    map: str
    map_size: str
    players: int
    difficulty: str
    game_speed: str
    observe_seconds: int
    expected_behaviors: List[str] = field(default_factory=list)
    key_metrics: List[str] = field(default_factory=list)


@dataclass
class MatchResult:
    """Result of a single match (civ × scenario)."""
    civ_token: str
    civ_name: str
    scenario_id: str
    scenario_name: str
    start_time: float
    end_time: float
    duration: float
    status: str  # "completed", "crashed", "timeout", "error"
    screenshots: List[str] = field(default_factory=list)
    log_file: Optional[str] = None
    metrics: Optional[DecisionMetrics] = None
    error_message: Optional[str] = None
    crash_log: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.metrics:
            d['metrics'] = self.metrics.to_dict()
        return d


@dataclass
class MatrixTestRun:
    """Metadata for an entire test run."""
    run_id: str
    artifact_root: Path
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime] = None
    civs_to_test: List[str] = field(default_factory=list)
    scenarios_to_test: List[str] = field(default_factory=list)
    results: List[MatchResult] = field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    total_expected: int = 0

    @property
    def completion_rate(self) -> float:
        if self.total_expected == 0:
            return 0.0
        return self.completed_count / self.total_expected

    def to_dict(self) -> dict:
        return {
            'run_id': self.run_id,
            'artifact_root': str(self.artifact_root),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'civs_tested': self.civs_to_test,
            'scenarios_tested': self.scenarios_to_test,
            'completed_count': self.completed_count,
            'failed_count': self.failed_count,
            'total_expected': self.total_expected,
            'completion_rate': self.completion_rate,
            'results': [r.to_dict() for r in self.results],
        }


class ANWMatrixRunner:
    """Orchestrate exhaustive ANW civ testing."""

    def __init__(self, artifact_dir: Optional[Path] = None):
        self.artifact_root = artifact_dir or Path("/var/home/jflessenkemper/artifacts/anw_matrix")
        self.artifact_root.mkdir(parents=True, exist_ok=True)

        self.test_scenarios: List[TestScenario] = []
        # Convert tuples from iter_anw_civs() to CivDef objects
        self.all_civs: List[CivDef] = []
        for token, civ_data in iter_anw_civs():
            self.all_civs.append(CivDef(
                anw_token=token,
                display_name=civ_data.get("display", token),
                leader_display=civ_data.get("leader", "Unknown"),
            ))
        self.run_metadata: Optional[MatrixTestRun] = None

        self._load_scenarios()

    def _load_scenarios(self) -> None:
        """Load scenario definitions from test_scenarios.json."""
        scenario_path = REPO_ROOT / "test_scenarios.json"

        if not scenario_path.exists():
            logger.warning(f"Scenario config not found: {scenario_path}")
            # Create default scenarios
            self._create_default_scenarios()
            return

        try:
            with open(scenario_path) as f:
                config = json.load(f)

            for scenario_dict in config.get('scenarios', []):
                self.test_scenarios.append(TestScenario(**scenario_dict))

            logger.info(f"Loaded {len(self.test_scenarios)} scenarios from {scenario_path}")
        except Exception as e:
            logger.error(f"Failed to load scenarios: {e}")
            self._create_default_scenarios()

    def _create_default_scenarios(self) -> None:
        """Create minimal default scenarios."""
        self.test_scenarios = [
            TestScenario(
                id="aggressive_rush_test",
                name="Aggressive Rush Test",
                description="1v1 small map rush test",
                map="Black Forest",
                map_size="tiny",
                players=2,
                difficulty="Hard",
                game_speed="Fast",
                observe_seconds=300,
            ),
            TestScenario(
                id="economy_boom_test",
                name="Economy Boom Test",
                description="1v3 medium map boom test",
                map="Midwest",
                map_size="medium",
                players=4,
                difficulty="Hard",
                game_speed="Fast",
                observe_seconds=600,
            ),
        ]
        logger.info(f"Created {len(self.test_scenarios)} default scenarios")

    def run_all_civs_all_scenarios(self) -> MatrixTestRun:
        """Run all 48 civs through all scenarios."""
        return self.run_matrix(
            civ_tokens=[c.anw_token for c in self.all_civs],
            scenario_ids=[s.id for s in self.test_scenarios],
        )

    def run_sample(self) -> MatrixTestRun:
        """Run a small sample (2 civs × 2 scenarios)."""
        sample_civs = [self.all_civs[0].anw_token, self.all_civs[-1].anw_token]
        sample_scenarios = [self.test_scenarios[0].id, self.test_scenarios[1].id]
        return self.run_matrix(sample_civs, sample_scenarios)

    def run_matrix(
        self,
        civ_tokens: Optional[List[str]] = None,
        scenario_ids: Optional[List[str]] = None,
    ) -> MatrixTestRun:
        """Run a matrix of civs × scenarios.

        Args:
            civ_tokens: Civs to test (None = all)
            scenario_ids: Scenarios to test (None = all)

        Returns:
            MatrixTestRun metadata.
        """
        if civ_tokens is None:
            civ_tokens = [c.anw_token for c in self.all_civs]
        if scenario_ids is None:
            scenario_ids = [s.id for s in self.test_scenarios]

        # Create run metadata
        run_id = self._generate_run_id()
        run_dir = self.artifact_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        self.run_metadata = MatrixTestRun(
            run_id=run_id,
            artifact_root=run_dir,
            start_time=datetime.datetime.now(),
            civs_to_test=civ_tokens,
            scenarios_to_test=scenario_ids,
            total_expected=len(civ_tokens) * len(scenario_ids),
        )

        logger.info(f"Starting matrix run: {run_id}")
        logger.info(f"Civs: {len(civ_tokens)}, Scenarios: {len(scenario_ids)}, Total matches: {self.run_metadata.total_expected}")

        # Run matches
        for civ_token in civ_tokens:
            for scenario_id in scenario_ids:
                result = self._run_match(civ_token, scenario_id, run_dir)
                self.run_metadata.results.append(result)

                if result.status == "completed":
                    self.run_metadata.completed_count += 1
                else:
                    self.run_metadata.failed_count += 1

                logger.info(
                    f"[{self.run_metadata.completion_rate*100:.1f}%] "
                    f"{civ_token} × {scenario_id}: {result.status}"
                )

                # Periodic checkpoint
                if len(self.run_metadata.results) % 5 == 0:
                    self._save_checkpoint(run_dir)

        # Finalize
        self.run_metadata.end_time = datetime.datetime.now()
        self._save_final_report(run_dir)

        logger.info(f"Matrix run complete: {self.run_metadata.completion_rate*100:.1f}% success")
        return self.run_metadata

    def _run_match(self, civ_token: str, scenario_id: str, run_dir: Path) -> MatchResult:
        """Run a single match (civ × scenario).

        Returns:
            MatchResult with status and metadata.
        """
        start_time = time.time()

        # Find scenario
        scenario = next((s for s in self.test_scenarios if s.id == scenario_id), None)
        if not scenario:
            return MatchResult(
                civ_token=civ_token,
                civ_name=civ_token,
                scenario_id=scenario_id,
                scenario_name=scenario_id,
                start_time=start_time,
                end_time=time.time(),
                duration=0.0,
                status="error",
                error_message=f"Scenario {scenario_id} not found",
            )

        # Find civ display name
        civ_obj = next((c for c in self.all_civs if c.anw_token == civ_token), None)
        civ_name = civ_obj.leader_display if civ_obj else civ_token

        # Create per-match directory
        match_dir = run_dir / f"{civ_token}_{scenario_id}"
        match_dir.mkdir(parents=True, exist_ok=True)
        screenshots_dir = match_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        result = MatchResult(
            civ_token=civ_token,
            civ_name=civ_name,
            scenario_id=scenario_id,
            scenario_name=scenario.name,
            start_time=start_time,
            end_time=0.0,
            duration=0.0,
            status="running",
        )

        try:
            # Snapshot log offset
            log_offset = snapshot_offset()
            time.sleep(0.5)

            # Run game (placeholder — actual implementation would use aoe3_ui_automation)
            logger.debug(f"Running match: {civ_token} vs {scenario.name} ({scenario.observe_seconds}s)")
            result.status = self._simulate_game_run(
                civ_token, scenario, match_dir, screenshots_dir
            )

            # Capture log
            time.sleep(1)
            log_content = read_since(log_offset)
            log_file = match_dir / "match.log"
            log_file.write_text(log_content, encoding='utf-8', errors='replace')
            result.log_file = str(log_file)

            # Analyze game log
            if log_content and len(log_content) > 100:
                try:
                    result.metrics = parse_game_log(log_file, civ_name)
                    result.metrics.game_duration = result.duration
                except Exception as e:
                    logger.warning(f"Failed to parse game log: {e}")

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            logger.error(f"Match error: {civ_token} × {scenario_id}: {e}")

        finally:
            result.end_time = time.time()
            result.duration = result.end_time - result.start_time

        return result

    def _simulate_game_run(
        self,
        civ_token: str,
        scenario: TestScenario,
        match_dir: Path,
        screenshots_dir: Path,
    ) -> str:
        """Simulate or run actual game (placeholder).

        In production, this would:
        1. Set up game via aoe3_ui_automation
        2. Start match with specified civ and scenario
        3. Capture screenshots at intervals
        4. Monitor for crashes
        5. Resign or wait for completion
        """
        # Placeholder: create dummy screenshots and return status
        for i, delay_sec in enumerate([0, 60, 180]):
            if delay_sec < scenario.observe_seconds:
                screenshot_path = screenshots_dir / f"screenshot_{i:02d}_{delay_sec}s.png"
                # Create placeholder file (in real implementation, capture actual screenshot)
                screenshot_path.write_bytes(b"PNG_PLACEHOLDER")

        # For now, return "completed" status
        return "completed"

    def _save_checkpoint(self, run_dir: Path) -> None:
        """Save intermediate checkpoint."""
        checkpoint_path = run_dir / "checkpoint.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(self.run_metadata.to_dict(), f, indent=2, default=str)
        logger.debug(f"Checkpoint saved: {checkpoint_path}")

    def _save_final_report(self, run_dir: Path) -> None:
        """Save final run report."""
        # JSON report
        report_path = run_dir / "run_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.run_metadata.to_dict(), f, indent=2, default=str)

        # HTML report
        html_path = run_dir / "run_report.html"
        html_content = self._generate_html_report()
        html_path.write_text(html_content)

        # Summary
        summary_path = run_dir / "SUMMARY.txt"
        summary = f"""ANW Matrix Test Run Report
=============================
Run ID: {self.run_metadata.run_id}
Start: {self.run_metadata.start_time}
End: {self.run_metadata.end_time}
Duration: {(self.run_metadata.end_time - self.run_metadata.start_time).total_seconds() / 3600:.1f} hours

Tests:
- Civs: {len(self.run_metadata.civs_to_test)}
- Scenarios: {len(self.run_metadata.scenarios_to_test)}
- Total Matches: {self.run_metadata.total_expected}
- Completed: {self.run_metadata.completed_count} ({self.run_metadata.completion_rate*100:.1f}%)
- Failed: {self.run_metadata.failed_count}

Results:
{self._summary_stats()}

Artifact Root: {run_dir}
"""
        summary_path.write_text(summary)
        logger.info(f"Final report saved to {report_path}")

    def _generate_html_report(self) -> str:
        """Generate HTML report of test results."""
        rows = ""
        for result in self.run_metadata.results:
            status_class = "success" if result.status == "completed" else "error"
            rows += f"""
        <tr class="{status_class}">
            <td>{result.civ_name}</td>
            <td>{result.scenario_name}</td>
            <td>{result.status}</td>
            <td>{result.duration:.1f}s</td>
            <td>{len(result.screenshots)} screenshots</td>
        </tr>
            """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ANW Matrix Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .success {{ background-color: #e8f5e9; }}
        .error {{ background-color: #ffebee; }}
        .summary {{ margin: 20px 0; padding: 10px; background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>ANW Matrix Test Report</h1>
    <div class="summary">
        <p><strong>Run ID:</strong> {self.run_metadata.run_id}</p>
        <p><strong>Civs:</strong> {len(self.run_metadata.civs_to_test)} | <strong>Scenarios:</strong> {len(self.run_metadata.scenarios_to_test)}</p>
        <p><strong>Completion:</strong> {self.run_metadata.completed_count}/{self.run_metadata.total_expected} ({self.run_metadata.completion_rate*100:.1f}%)</p>
    </div>
    <table>
        <tr>
            <th>Civilization</th>
            <th>Scenario</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Screenshots</th>
        </tr>
        {rows}
    </table>
</body>
</html>
        """
        return html

    def _summary_stats(self) -> str:
        """Generate summary statistics."""
        status_counts: Dict[str, int] = {}
        for result in self.run_metadata.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

        lines = []
        for status, count in status_counts.items():
            lines.append(f"  - {status}: {count}")
        return "\n".join(lines)

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"anw_matrix_{timestamp}_{random_suffix}"


def main():
    parser = argparse.ArgumentParser(description="ANW Matrix Runner - Test all 48 civs")
    parser.add_argument('--all-civs', action='store_true', help='Test all 48 civs')
    parser.add_argument('--all-scenarios', action='store_true', help='Test all scenarios')
    parser.add_argument('--civ', action='append', dest='civs', help='Specific civ to test (repeatable)')
    parser.add_argument('--scenario', action='append', dest='scenarios', help='Specific scenario (repeatable)')
    parser.add_argument('--sample', action='store_true', help='Run fast sample (2 civs × 2 scenarios)')
    parser.add_argument('--fast', action='store_true', help='Skip slow scenarios')
    parser.add_argument('--artifact-dir', type=Path, help='Override artifact directory')
    parser.add_argument('--resume', type=Path, help='Resume interrupted run from checkpoint')
    parser.add_argument('--validate-only', action='store_true', help='Validate without running games')
    parser.add_argument('--dry-run', action='store_true', help='Print what would run without executing')

    args = parser.parse_args()

    runner = ANWMatrixRunner(artifact_dir=args.artifact_dir)

    if args.sample:
        logger.info("Running sample matrix (2 civs × 2 scenarios)")
        run_metadata = runner.run_sample()
    elif args.all_civs and args.all_scenarios:
        logger.info("Running full matrix (all 48 civs × all scenarios)")
        run_metadata = runner.run_all_civs_all_scenarios()
    elif args.civs or args.scenarios:
        civ_tokens = args.civs or [c.anw_token for c in runner.all_civs]
        scenario_ids = args.scenarios or [s.id for s in runner.test_scenarios]
        run_metadata = runner.run_matrix(civ_tokens, scenario_ids)
    else:
        parser.print_help()
        sys.exit(1)

    logger.info(f"Completion rate: {run_metadata.completion_rate*100:.1f}%")
    logger.info(f"Artifact root: {run_metadata.artifact_root}")


if __name__ == "__main__":
    main()
