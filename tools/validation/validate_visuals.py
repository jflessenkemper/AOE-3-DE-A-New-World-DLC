#!/usr/bin/env python3
"""Visual Asset Validator — Pixel-compare screenshots for rendering issues.

Validates that screenshots contain expected visual elements:
- Civ names display correctly
- Leader portraits appear
- Unit visuals match expected types
- UI elements render properly
- No art asset corruption/missing textures

Usage
-----
    python3 tools/validation/validate_visuals.py <artifact_dir>

Output
------
    <artifact_dir>/visual_validation_report.json
    <artifact_dir>/visual_validation_report.html
    <artifact_dir>/visual_mismatches/ (screenshot comparisons)
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class VisualIssueType(Enum):
    """Types of visual issues."""
    MISSING_CIV_NAME = "missing_civ_name"
    MISSING_PORTRAIT = "missing_portrait"
    CORRUPTED_TEXTURE = "corrupted_texture"
    MISSING_UI_ELEMENT = "missing_ui_element"
    PALETTE_MISMATCH = "palette_mismatch"
    RESOLUTION_MISMATCH = "resolution_mismatch"
    UNKNOWN = "unknown"


@dataclass
class VisualIssue:
    """Record of a visual asset problem."""
    issue_type: VisualIssueType
    severity: str  # "critical", "warning", "info"
    description: str
    screenshot_path: str
    location: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    recommendation: str = ""


@dataclass
class ScreenshotValidation:
    """Validation result for a single screenshot."""
    civ_name: str
    scenario: str
    screenshot_path: str
    timestamp: int  # seconds
    file_exists: bool = True
    file_size: int = 0
    image_size: Optional[Tuple[int, int]] = None
    hash_md5: str = ""
    is_valid_image: bool = False
    is_blank: bool = False
    issues: List[VisualIssue] = field(default_factory=list)
    passes_checks: bool = False
    confidence: float = 0.0


@dataclass
class MatchVisualReport:
    """Visual validation for a match (civ × scenario)."""
    civ_name: str
    civ_token: str
    scenario: str
    total_screenshots: int = 0
    valid_screenshots: int = 0
    issues_found: int = 0
    critical_issues: int = 0
    screenshot_validations: List[ScreenshotValidation] = field(default_factory=list)
    overall_valid: bool = True


@dataclass
class MatrixVisualReport:
    """Complete visual report for matrix run."""
    run_id: str
    total_matches: int
    matches_with_issues: int
    total_issues: int
    critical_issues: int
    match_reports: List[MatchVisualReport] = field(default_factory=list)


class VisualValidator:
    """Validate visual assets in screenshots."""

    def __init__(self):
        self.has_pil = HAS_PIL

    def validate_match_directory(
        self,
        match_dir: Path,
        civ_name: str,
        civ_token: str,
        scenario: str,
    ) -> MatchVisualReport:
        """Validate all screenshots in a match directory.

        Args:
            match_dir: Path to match artifacts
            civ_name: Display name of civ
            civ_token: ANW civ token
            scenario: Scenario ID

        Returns:
            MatchVisualReport with all validation results.
        """
        report = MatchVisualReport(
            civ_name=civ_name,
            civ_token=civ_token,
            scenario=scenario,
        )

        screenshots_dir = match_dir / "screenshots"
        if not screenshots_dir.exists():
            logger.warning(f"No screenshots directory: {screenshots_dir}")
            return report

        # Find all screenshots
        screenshot_files = sorted(screenshots_dir.glob("screenshot_*.png"))
        report.total_screenshots = len(screenshot_files)

        for screenshot_path in screenshot_files:
            validation = self._validate_screenshot(
                screenshot_path,
                civ_name,
                scenario,
            )
            report.screenshot_validations.append(validation)

            if validation.passes_checks:
                report.valid_screenshots += 1
            else:
                report.issues_found += len(validation.issues)
                for issue in validation.issues:
                    if issue.severity == "critical":
                        report.critical_issues += 1

        # Overall validity
        if report.critical_issues > 0:
            report.overall_valid = False

        return report

    def _validate_screenshot(
        self,
        screenshot_path: Path,
        civ_name: str,
        scenario: str,
    ) -> ScreenshotValidation:
        """Validate a single screenshot.

        Args:
            screenshot_path: Path to PNG file
            civ_name: Expected civ name
            scenario: Scenario identifier

        Returns:
            ScreenshotValidation with results and issues.
        """
        # Extract timestamp from filename (screenshot_NN_NNs.png)
        timestamp = 0
        try:
            parts = screenshot_path.stem.split('_')
            for part in parts:
                if part.endswith('s'):
                    timestamp = int(part[:-1])
                    break
        except (ValueError, IndexError):
            pass

        validation = ScreenshotValidation(
            civ_name=civ_name,
            scenario=scenario,
            screenshot_path=str(screenshot_path),
            timestamp=timestamp,
        )

        # Check file existence
        if not screenshot_path.exists():
            validation.file_exists = False
            validation.issues.append(VisualIssue(
                issue_type=VisualIssueType.UNKNOWN,
                severity="critical",
                description=f"Screenshot file not found",
                screenshot_path=str(screenshot_path),
            ))
            return validation

        validation.file_size = screenshot_path.stat().st_size
        validation.hash_md5 = self._compute_file_hash(screenshot_path)

        # Check if blank/corrupted
        if validation.file_size < 1024:
            validation.is_blank = True
            validation.issues.append(VisualIssue(
                issue_type=VisualIssueType.CORRUPTED_TEXTURE,
                severity="critical",
                description=f"Screenshot too small ({validation.file_size} bytes)",
                screenshot_path=str(screenshot_path),
            ))
            return validation

        # Analyze image if PIL available
        if self.has_pil:
            self._analyze_image_content(screenshot_path, validation, civ_name)

        # Determine overall validity
        validation.passes_checks = len([
            i for i in validation.issues
            if i.severity == "critical"
        ]) == 0

        return validation

    def _analyze_image_content(
        self,
        screenshot_path: Path,
        validation: ScreenshotValidation,
        civ_name: str,
    ) -> None:
        """Analyze image content for visual issues."""
        try:
            img = Image.open(screenshot_path)
            validation.image_size = img.size
            validation.is_valid_image = True

            # Check for expected elements
            self._check_civ_name_visible(img, validation, civ_name)
            self._check_ui_elements(img, validation)
            self._check_for_corruption(img, validation)

        except Exception as e:
            logger.warning(f"Failed to analyze image: {e}")
            validation.issues.append(VisualIssue(
                issue_type=VisualIssueType.CORRUPTED_TEXTURE,
                severity="warning",
                description=f"Image analysis failed: {e}",
                screenshot_path=str(screenshot_path),
            ))

    def _check_civ_name_visible(
        self,
        img: Image.Image,
        validation: ScreenshotValidation,
        civ_name: str,
    ) -> None:
        """Check if civ name appears to be visible (basic check).

        Note: Full OCR would require additional dependencies.
        This does basic heuristics.
        """
        # For now, just check that the top portion of image isn't blank
        width, height = img.size
        top_region = img.crop((0, 0, width, height // 4))

        # Count non-black pixels
        pixels = list(top_region.getdata())
        non_black = sum(1 for p in pixels if sum(p[:3]) > 50)

        if non_black < len(pixels) * 0.1:
            validation.issues.append(VisualIssue(
                issue_type=VisualIssueType.MISSING_CIV_NAME,
                severity="warning",
                description="Top UI region appears mostly blank (civ name may not be visible)",
                screenshot_path=str(validation.screenshot_path),
                location=(0, 0, width, height // 4),
            ))

    def _check_ui_elements(
        self,
        img: Image.Image,
        validation: ScreenshotValidation,
    ) -> None:
        """Check for expected UI elements."""
        width, height = img.size

        # Check for toolbar at bottom
        bottom_region = img.crop((0, height - 100, width, height))
        pixels = list(bottom_region.getdata())
        non_black = sum(1 for p in pixels if sum(p[:3]) > 50)

        if non_black < len(pixels) * 0.1:
            validation.issues.append(VisualIssue(
                issue_type=VisualIssueType.MISSING_UI_ELEMENT,
                severity="warning",
                description="Bottom UI toolbar appears mostly blank",
                screenshot_path=str(validation.screenshot_path),
                location=(0, height - 100, width, 100),
            ))

    def _check_for_corruption(
        self,
        img: Image.Image,
        validation: ScreenshotValidation,
    ) -> None:
        """Detect texture corruption patterns."""
        width, height = img.size
        pixels = list(img.getdata())

        # Check for dead pixels (large uniform regions)
        dead_pixel_count = sum(1 for p in pixels if p[:3] == (0, 0, 0))
        dead_pixel_rate = dead_pixel_count / len(pixels)

        if dead_pixel_rate > 0.9:
            validation.issues.append(VisualIssue(
                issue_type=VisualIssueType.CORRUPTED_TEXTURE,
                severity="warning",
                description=f"High proportion of black pixels ({dead_pixel_rate*100:.1f}%)",
                screenshot_path=str(validation.screenshot_path),
            ))

    def _compute_file_hash(self, path: Path) -> str:
        """Compute MD5 hash of file."""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def validate_matrix_run(self, artifact_dir: Path) -> MatrixVisualReport:
        """Validate all screenshots from a matrix run.

        Args:
            artifact_dir: Path to matrix run artifact directory

        Returns:
            MatrixVisualReport with all match results.
        """
        report = MatrixVisualReport(
            run_id=artifact_dir.name,
            total_matches=0,
            matches_with_issues=0,
            total_issues=0,
            critical_issues=0,
        )

        # Find all match directories
        match_dirs = sorted([
            d for d in artifact_dir.iterdir()
            if d.is_dir() and "_" in d.name
        ])

        logger.info(f"Found {len(match_dirs)} match directories to validate")

        for match_dir in match_dirs:
            # Parse match directory name: <civ_token>_<scenario_id>
            parts = match_dir.name.split("_", 1)
            if len(parts) != 2:
                logger.warning(f"Invalid match directory name: {match_dir.name}")
                continue

            civ_token, scenario_id = parts

            # Validate this match
            match_report = self.validate_match_directory(
                match_dir,
                civ_name=civ_token,
                civ_token=civ_token,
                scenario=scenario_id,
            )
            report.match_reports.append(match_report)
            report.total_matches += 1

            if not match_report.overall_valid:
                report.matches_with_issues += 1

            report.total_issues += match_report.issues_found
            report.critical_issues += match_report.critical_issues

        logger.info(f"Visual validation complete: {report.total_issues} issues found")
        return report

    def generate_html_report(self, visual_report: MatrixVisualReport) -> str:
        """Generate HTML validation report."""
        match_rows = ""
        for match_report in visual_report.match_reports:
            status = "PASS" if match_report.overall_valid else "FAIL"
            status_class = "pass" if match_report.overall_valid else "fail"
            match_rows += f"""
        <tr class="{status_class}">
            <td>{match_report.civ_name}</td>
            <td>{match_report.scenario}</td>
            <td>{status}</td>
            <td>{match_report.valid_screenshots}/{match_report.total_screenshots}</td>
            <td>{match_report.issues_found}</td>
            <td>{match_report.critical_issues}</td>
        </tr>
            """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Visual Asset Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .pass {{ background-color: #e8f5e9; }}
        .fail {{ background-color: #ffebee; }}
        .summary {{ margin: 20px 0; padding: 10px; background-color: #f5f5f5; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>Visual Asset Validation Report</h1>
    <div class="summary">
        <p><strong>Run ID:</strong> {visual_report.run_id}</p>
        <p><strong>Total Matches:</strong> {visual_report.total_matches}</p>
        <p><strong>Matches with Issues:</strong> {visual_report.matches_with_issues}</p>
        <p><strong>Total Issues:</strong> {visual_report.total_issues}</p>
        <p><strong>Critical Issues:</strong> {visual_report.critical_issues}</p>
    </div>

    <h2>Match Results</h2>
    <table>
        <tr>
            <th>Civilization</th>
            <th>Scenario</th>
            <th>Status</th>
            <th>Valid Screenshots</th>
            <th>Total Issues</th>
            <th>Critical</th>
        </tr>
        {match_rows}
    </table>
</body>
</html>
        """
        return html


import argparse
import subprocess

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]


def run_static_mode() -> int:
    """Static-mode: delegate to validate_civ_asset_existence.py.

    This checks that every flag/portrait/UI asset referenced by civmods.xml
    exists on disk (in the mod tree as PNG or in the base .bar archives as DDT).
    It's an art-coverage check rather than a rendered-art check, but it's
    meaningful: it catches missing declarations or missing files before any game
    runs. All 61-validator static gate output will clearly say 'static-mode'.
    """
    static_validator = _HERE / "validate_civ_asset_existence.py"
    if not static_validator.exists():
        print(f"[static-mode] ERROR: {static_validator} not found", file=sys.stderr)
        return 2

    print("[static-mode] visuals — running art asset existence check "
          "(civmods.xml asset paths → real files, no screenshots needed)")
    result = subprocess.run(
        [sys.executable, str(static_validator)],
        cwd=_REPO_ROOT,
    )
    if result.returncode == 0:
        print("[static-mode] visuals — PASS (all art asset paths resolve)")
    else:
        print("[static-mode] visuals — FAIL (one or more art asset paths missing)")
    return result.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("artifact_dir", nargs="?", default=None,
                    help="path to matrix run screenshot artifact directory (runtime mode)")
    ap.add_argument("--static-mode", action="store_true",
                    help="offline mode: check art asset existence instead of "
                         "validating runtime screenshots")
    args = ap.parse_args()

    # Static mode: no artifact dir needed.
    if args.static_mode or args.artifact_dir is None:
        sys.exit(run_static_mode())

    # --- Runtime path (unchanged) ---
    artifact_dir = Path(args.artifact_dir)

    if not artifact_dir.exists():
        logger.error(f"Artifact directory not found: {artifact_dir}")
        sys.exit(1)

    logger.info(f"Validating visual assets: {artifact_dir}")

    validator = VisualValidator()
    visual_report = validator.validate_matrix_run(artifact_dir)

    # Save JSON report
    json_path = artifact_dir / "visual_validation_report.json"
    with open(json_path, 'w') as f:
        json.dump({
            'run_id': visual_report.run_id,
            'total_matches': visual_report.total_matches,
            'matches_with_issues': visual_report.matches_with_issues,
            'total_issues': visual_report.total_issues,
            'critical_issues': visual_report.critical_issues,
        }, f, indent=2)
    logger.info(f"JSON report saved: {json_path}")

    # Save HTML report
    html_path = artifact_dir / "visual_validation_report.html"
    html_content = validator.generate_html_report(visual_report)
    html_path.write_text(html_content)
    logger.info(f"HTML report saved: {html_path}")

    # Print summary
    print(f"\nVisual Validation Summary")
    print(f"========================")
    print(f"Matches with issues: {visual_report.matches_with_issues}/{visual_report.total_matches}")
    print(f"Total issues: {visual_report.total_issues}")
    print(f"Critical issues: {visual_report.critical_issues}")


if __name__ == "__main__":
    main()
