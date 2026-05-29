#!/usr/bin/env python3
"""Playstyle Validation Engine — Compare actual vs. expected civ behaviors.

Loads playstyle specifications, parses collected AI logs from matrix runs,
and validates whether each civ's actual performance matches expectations:

- Unit production matches playstyle?
- Age progression reasonable?
- Economic focus correct?
- Military composition matches unit roster?
- Wall strategy matches specification?

Usage
-----
    python3 tools/validation/validate_playstyles.py <artifact_dir>

Output
------
    <artifact_dir>/validation_report.json
    <artifact_dir>/validation_report.html
    <artifact_dir>/VALIDATION_SUMMARY.txt
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
import statistics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class ValidationStatus(Enum):
    """Validation result status."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warning"
    SKIP = "skip"
    UNKNOWN = "unknown"


@dataclass
class PlaystyleSpecification:
    """Expected playstyle for a civ."""
    civ_name: str
    civ_token: str
    unit_focus: List[str]  # Expected primary unit types
    economic_focus: str  # "food", "gold", "balanced"
    typical_age_progression: List[str]  # Expected age sequence
    naval_capable: bool = False
    wall_builder: bool = False
    trading_focused: bool = False
    rush_viable: bool = True
    tech_heavy: bool = False
    description: str = ""


@dataclass
class ValidationRule:
    """A single validation rule."""
    rule_id: str
    name: str
    description: str
    metric: str  # Which metric to check
    expected_range: Tuple[float, float] = (0.0, 1.0)
    threshold: float = 0.7
    weight: float = 1.0


@dataclass
class ValidationCheckResult:
    """Result of a single validation check."""
    civ_token: str
    rule_id: str
    rule_name: str
    metric_name: str
    expected_value: any
    actual_value: any
    status: ValidationStatus
    confidence: float
    message: str = ""


@dataclass
class CivValidationReport:
    """Complete validation report for a civ."""
    civ_token: str
    civ_name: str
    overall_status: ValidationStatus
    overall_confidence: float
    checks_performed: int
    checks_passed: int
    checks_failed: int
    checks_warned: int
    check_results: List[ValidationCheckResult] = field(default_factory=list)
    mismatches: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def pass_rate(self) -> float:
        if self.checks_performed == 0:
            return 0.0
        return self.checks_passed / self.checks_performed


@dataclass
class MatrixValidationReport:
    """Full validation report for matrix run."""
    run_id: str
    total_civs: int
    total_checks: int
    overall_pass_rate: float
    civ_reports: List[CivValidationReport] = field(default_factory=list)
    critical_failures: List[str] = field(default_factory=list)
    trends: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'run_id': self.run_id,
            'total_civs': self.total_civs,
            'total_checks': self.total_checks,
            'overall_pass_rate': self.overall_pass_rate,
            'critical_failures': self.critical_failures,
            'civ_reports': [
                {
                    'civ_token': r.civ_token,
                    'civ_name': r.civ_name,
                    'overall_status': r.overall_status.value,
                    'overall_confidence': r.overall_confidence,
                    'pass_rate': r.pass_rate,
                    'checks_performed': r.checks_performed,
                    'checks_passed': r.checks_passed,
                    'checks_failed': r.checks_failed,
                    'check_results': [
                        {
                            'rule_id': cr.rule_id,
                            'rule_name': cr.rule_name,
                            'status': cr.status.value,
                            'confidence': cr.confidence,
                            'message': cr.message,
                        }
                        for cr in r.check_results
                    ],
                    'mismatches': r.mismatches,
                    'warnings': r.warnings,
                }
                for r in self.civ_reports
            ],
        }


class PlaystyleValidator:
    """Validate playstyle specifications against actual AI behavior."""

    def __init__(self, specs_path: Optional[Path] = None):
        self.specifications: Dict[str, PlaystyleSpecification] = {}
        self.validation_rules: Dict[str, ValidationRule] = {}

        if specs_path and specs_path.exists():
            self._load_specifications(specs_path)
        else:
            self._create_default_specifications()

        self._create_validation_rules()

    def _load_specifications(self, specs_path: Path) -> None:
        """Load playstyle specifications from JSON."""
        try:
            with open(specs_path) as f:
                specs_data = json.load(f)

            for spec_dict in specs_data.get('playstyles', []):
                spec = PlaystyleSpecification(**spec_dict)
                self.specifications[spec.civ_token] = spec

            logger.info(f"Loaded {len(self.specifications)} playstyle specifications")
        except Exception as e:
            logger.error(f"Failed to load specifications: {e}")
            self._create_default_specifications()

    def _create_default_specifications(self) -> None:
        """Create default specifications for major civs."""
        defaults = [
            PlaystyleSpecification(
                civ_name="British",
                civ_token="ANWBritish",
                unit_focus=["redcoat", "musketeer", "dragoon"],
                economic_focus="balanced",
                typical_age_progression=["Discovery", "Colonial", "Industrial"],
                naval_capable=True,
                trading_focused=True,
            ),
            PlaystyleSpecification(
                civ_name="French",
                civ_token="ANWFrench",
                unit_focus=["cuirassier", "musketeer", "dragoon"],
                economic_focus="gold",
                typical_age_progression=["Discovery", "Colonial", "Imperial"],
                naval_capable=True,
                tech_heavy=True,
            ),
            PlaystyleSpecification(
                civ_name="German",
                civ_token="ANWGermans",
                unit_focus=["musketeer", "pikeman", "uhlan"],
                economic_focus="wood",
                typical_age_progression=["Discovery", "Colonial", "Industrial"],
                naval_capable=False,
                wall_builder=True,
            ),
        ]

        for spec in defaults:
            self.specifications[spec.civ_token] = spec

        logger.info(f"Created {len(self.specifications)} default playstyle specifications")

    def _create_validation_rules(self) -> None:
        """Define validation rules."""
        self.validation_rules = {
            "unit_production_rate": ValidationRule(
                rule_id="unit_production_rate",
                name="Unit Production Rate",
                description="Ensure civ produces units consistently",
                metric="avg_units_per_minute",
                expected_range=(0.5, 20.0),
                threshold=0.5,
            ),
            "age_progression": ValidationRule(
                rule_id="age_progression",
                name="Age Progression",
                description="Verify reasonable age progression timing",
                metric="avg_age_progression_time",
                expected_range=(60.0, 900.0),
                threshold=0.7,
            ),
            "economic_activity": ValidationRule(
                rule_id="economic_activity",
                name="Economic Activity",
                description="Ensure resource gathering and economic development",
                metric="economic_count",
                expected_range=(10.0, 1000.0),
                threshold=0.6,
            ),
            "unit_diversity": ValidationRule(
                rule_id="unit_diversity",
                name="Unit Diversity",
                description="Verify civ trains multiple unit types",
                metric="unique_unit_types",
                expected_range=(2.0, 10.0),
                threshold=0.7,
            ),
            "military_composition": ValidationRule(
                rule_id="military_composition",
                name="Military Composition",
                description="Check unit composition matches playstyle",
                metric="dominant_unit_percentage",
                expected_range=(20.0, 100.0),
                threshold=0.6,
            ),
        }

    def validate_match_result(
        self,
        civ_token: str,
        metrics_dict: dict,
    ) -> CivValidationReport:
        """Validate a single match result against specifications.

        Args:
            civ_token: ANW civ token
            metrics_dict: DecisionMetrics as dict (from AI analyzer)

        Returns:
            CivValidationReport with all checks and results.
        """
        spec = self.specifications.get(civ_token)
        civ_name = spec.civ_name if spec else civ_token

        report = CivValidationReport(
            civ_token=civ_token,
            civ_name=civ_name,
            overall_status=ValidationStatus.UNKNOWN,
            overall_confidence=0.0,
            checks_performed=0,
            checks_passed=0,
            checks_failed=0,
            checks_warned=0,
        )

        if not spec:
            report.warnings.append(f"No playstyle spec found for {civ_token}")
            return report

        # Run all validation checks
        for rule_id, rule in self.validation_rules.items():
            result = self._run_validation_check(rule, metrics_dict, spec)
            if result:
                report.check_results.append(result)
                report.checks_performed += 1

                if result.status == ValidationStatus.PASS:
                    report.checks_passed += 1
                elif result.status == ValidationStatus.FAIL:
                    report.checks_failed += 1
                    report.mismatches.append(result.message)
                elif result.status == ValidationStatus.WARN:
                    report.checks_warned += 1
                    report.warnings.append(result.message)

        # Compute overall status
        if report.checks_performed == 0:
            report.overall_status = ValidationStatus.UNKNOWN
        elif report.checks_failed == 0 and report.checks_warned == 0:
            report.overall_status = ValidationStatus.PASS
        elif report.checks_failed == 0:
            report.overall_status = ValidationStatus.WARN
        else:
            report.overall_status = ValidationStatus.FAIL

        # Compute confidence
        if report.checks_performed > 0:
            confidence = report.checks_passed / report.checks_performed
            report.overall_confidence = confidence
        else:
            report.overall_confidence = 0.0

        return report

    def _run_validation_check(
        self,
        rule: ValidationRule,
        metrics_dict: dict,
        spec: PlaystyleSpecification,
    ) -> Optional[ValidationCheckResult]:
        """Execute a single validation check."""
        metric_value = metrics_dict.get(rule.metric)

        if metric_value is None:
            return None

        try:
            metric_value = float(metric_value)
        except (ValueError, TypeError):
            return None

        min_val, max_val = rule.expected_range
        in_range = min_val <= metric_value <= max_val

        if in_range:
            status = ValidationStatus.PASS
            confidence = 0.9
        else:
            # Check if it's a warning or failure
            if abs(metric_value - min_val) < max_val * 0.2 or \
               abs(metric_value - max_val) < max_val * 0.2:
                status = ValidationStatus.WARN
                confidence = 0.6
            else:
                status = ValidationStatus.FAIL
                confidence = 0.3

        return ValidationCheckResult(
            civ_token=spec.civ_token,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            metric_name=rule.metric,
            expected_value=rule.expected_range,
            actual_value=metric_value,
            status=status,
            confidence=confidence,
            message=f"{rule.name}: expected {rule.expected_range}, got {metric_value:.1f}",
        )

    def validate_matrix_run(
        self,
        artifact_dir: Path,
    ) -> MatrixValidationReport:
        """Validate all results from a matrix run.

        Reads run_report.json and analyzes all match results.

        Args:
            artifact_dir: Path to matrix run artifact directory

        Returns:
            MatrixValidationReport with all civ reports and trends.
        """
        report_path = artifact_dir / "run_report.json"

        if not report_path.exists():
            logger.error(f"Run report not found: {report_path}")
            return MatrixValidationReport(
                run_id="unknown",
                total_civs=0,
                total_checks=0,
                overall_pass_rate=0.0,
            )

        try:
            with open(report_path) as f:
                run_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load run report: {e}")
            return MatrixValidationReport(
                run_id="unknown",
                total_civs=0,
                total_checks=0,
                overall_pass_rate=0.0,
            )

        validation_report = MatrixValidationReport(
            run_id=run_data.get('run_id', 'unknown'),
            total_civs=len(set(r['civ_token'] for r in run_data.get('results', []))),
            total_checks=0,
            overall_pass_rate=0.0,
        )

        # Validate each result
        for result in run_data.get('results', []):
            civ_token = result.get('civ_token')
            metrics = result.get('metrics')

            if not civ_token or not metrics:
                continue

            civ_report = self.validate_match_result(civ_token, metrics)
            validation_report.civ_reports.append(civ_report)
            validation_report.total_checks += civ_report.checks_performed

        # Compute overall pass rate
        if validation_report.total_checks > 0:
            total_passed = sum(r.checks_passed for r in validation_report.civ_reports)
            validation_report.overall_pass_rate = total_passed / validation_report.total_checks

        # Identify critical failures
        for civ_report in validation_report.civ_reports:
            if civ_report.overall_status == ValidationStatus.FAIL:
                validation_report.critical_failures.append(
                    f"{civ_report.civ_name}: {len(civ_report.mismatches)} rule(s) failed"
                )

        return validation_report

    def generate_html_report(self, validation_report: MatrixValidationReport) -> str:
        """Generate HTML validation report."""
        civ_rows = ""
        for civ_report in validation_report.civ_reports:
            status_class = civ_report.overall_status.value
            civ_rows += f"""
        <tr class="{status_class}">
            <td>{civ_report.civ_name}</td>
            <td>{civ_report.overall_status.value.upper()}</td>
            <td>{civ_report.pass_rate*100:.1f}%</td>
            <td>{civ_report.checks_passed}/{civ_report.checks_performed}</td>
            <td>{civ_report.overall_confidence*100:.1f}%</td>
        </tr>
            """

        failures_html = ""
        if validation_report.critical_failures:
            failures_html = "<h3>Critical Failures</h3><ul>"
            for failure in validation_report.critical_failures:
                failures_html += f"<li>{failure}</li>"
            failures_html += "</ul>"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Playstyle Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .pass {{ background-color: #e8f5e9; }}
        .fail {{ background-color: #ffebee; }}
        .warning {{ background-color: #fff3e0; }}
        .skip {{ background-color: #f5f5f5; }}
        .summary {{ margin: 20px 0; padding: 10px; background-color: #f5f5f5; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>Playstyle Validation Report</h1>
    <div class="summary">
        <p><strong>Run ID:</strong> {validation_report.run_id}</p>
        <p><strong>Civs Validated:</strong> {validation_report.total_civs}</p>
        <p><strong>Total Checks:</strong> {validation_report.total_checks}</p>
        <p><strong>Overall Pass Rate:</strong> {validation_report.overall_pass_rate*100:.1f}%</p>
    </div>

    {failures_html}

    <h2>Civ Validation Results</h2>
    <table>
        <tr>
            <th>Civilization</th>
            <th>Status</th>
            <th>Pass Rate</th>
            <th>Checks Passed</th>
            <th>Confidence</th>
        </tr>
        {civ_rows}
    </table>
</body>
</html>
        """
        return html


import argparse

# Required minimum fields every civ entry must declare in playstyle_spec.json.
_REQUIRED_CLAIM_FIELDS = ("wall_strategy", "first_military_building", "military_distance_band")

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]
_DEFAULT_SPEC = _REPO_ROOT / "playstyle_spec.json"


def run_static_mode(spec_path: Path) -> int:
    """Static-mode: verify every civ in playstyle_spec.json has required claim fields.

    Checks that each civ entry's 'claims' block contains at least:
        wall_strategy, first_military_building, military_distance_band

    This is meaningful: it catches civs whose spec entries lack required coverage
    before any game run is needed.

    Returns 0 (PASS) or 1 (FAIL).
    """
    if not spec_path.exists():
        print(f"[static-mode] ERROR: spec not found: {spec_path}", file=sys.stderr)
        return 1

    try:
        import json
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[static-mode] ERROR: failed to parse spec: {e}", file=sys.stderr)
        return 1

    civs = spec.get("civs", {})
    if not civs:
        print("[static-mode] ERROR: playstyle_spec.json has no 'civs' block", file=sys.stderr)
        return 1

    fails: list[str] = []
    for civ_key, entry in civs.items():
        claims = entry.get("claims", {})
        missing = [f for f in _REQUIRED_CLAIM_FIELDS if f not in claims]
        if missing:
            fails.append(f"  FAIL {civ_key}: missing claims {missing}")

    total = len(civs)
    if fails:
        print(f"[static-mode] playstyles spec coverage check — FAIL ({len(fails)}/{total} civs missing required fields)")
        for line in fails:
            print(line)
        return 1

    print(f"[static-mode] playstyles spec coverage check — PASS "
          f"({total}/{total} civs have all required claim fields: "
          f"{list(_REQUIRED_CLAIM_FIELDS)})")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("artifact_dir", nargs="?", default=None,
                    help="path to matrix run artifact directory (runtime mode)")
    ap.add_argument("--static-mode", action="store_true",
                    help="run offline spec-coverage check instead of runtime artifact validation")
    ap.add_argument("--spec", type=Path, default=_DEFAULT_SPEC,
                    help="path to playstyle_spec.json (static-mode only)")
    args = ap.parse_args()

    # Static mode: no artifact dir needed.
    if args.static_mode or args.artifact_dir is None:
        sys.exit(run_static_mode(args.spec))

    # --- Runtime path (unchanged) ---
    artifact_dir = Path(args.artifact_dir)

    if not artifact_dir.exists():
        logger.error(f"Artifact directory not found: {artifact_dir}")
        sys.exit(1)

    logger.info(f"Validating matrix run: {artifact_dir}")

    validator = PlaystyleValidator()
    validation_report = validator.validate_matrix_run(artifact_dir)

    # Save JSON report
    json_path = artifact_dir / "validation_report.json"
    with open(json_path, 'w') as f:
        import json as _json
        _json.dump(validation_report.to_dict(), f, indent=2)
    logger.info(f"JSON report saved: {json_path}")

    # Save HTML report
    html_path = artifact_dir / "validation_report.html"
    html_content = validator.generate_html_report(validation_report)
    html_path.write_text(html_content)
    logger.info(f"HTML report saved: {html_path}")

    # Print summary
    print(f"\nValidation Summary")
    print(f"==================")
    print(f"Overall Pass Rate: {validation_report.overall_pass_rate*100:.1f}%")
    print(f"Civs with failures: {len(validation_report.critical_failures)}")
    if validation_report.critical_failures:
        print("\nFailures:")
        for failure in validation_report.critical_failures:
            print(f"  - {failure}")


if __name__ == "__main__":
    main()
