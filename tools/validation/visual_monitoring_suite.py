#!/usr/bin/env python3
"""Visual monitoring suite orchestrator for ANW validation.

Runs all Phase 3 visual validators on match screenshots:
  - Team color detection (verify correct team assignment)
  - OCR validation (verify UI text readability)
  - Layout analysis (verify building/wall patterns match doctrine)
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from tools.validation.team_color_detector import TeamColorDetector
    from tools.validation.layout_analyzer import LayoutAnalyzer
    from tools.validation.ocr_validator import OCRValidator
    VALIDATORS_AVAILABLE = True
except ImportError:
    VALIDATORS_AVAILABLE = False


class VisualMonitoringSuite:
    """Orchestrates all visual validation tools."""

    def __init__(self):
        """Initialize suite."""
        self.color_detector = TeamColorDetector() if VALIDATORS_AVAILABLE else None
        self.layout_analyzer = LayoutAnalyzer() if VALIDATORS_AVAILABLE else None
        self.ocr_validator = OCRValidator() if VALIDATORS_AVAILABLE else None
        self.available = VALIDATORS_AVAILABLE

    def analyze_match_screenshots(
        self,
        screenshot_dir: Path,
        expected_team_color: Optional[str] = None,
        expected_wall_strategy: Optional[str] = None,
    ) -> Dict:
        """Analyze all screenshots from a match.

        Returns: {
            "match_dir": str,
            "screenshots_found": int,
            "team_color_analysis": [results...],
            "layout_analysis": [results...],
            "ocr_analysis": [results...],
            "summary": {
                "color_pass_rate_pct": float,
                "layout_pass_rate_pct": float,
                "overall_pass_rate_pct": float
            }
        }
        """
        if not self.available:
            return {
                "error": "Visual validators not available",
                "match_dir": str(screenshot_dir)
            }

        if not screenshot_dir.exists():
            return {
                "error": f"Screenshot directory not found",
                "match_dir": str(screenshot_dir)
            }

        # Find screenshots
        screenshots = list(screenshot_dir.glob("*.png")) + list(screenshot_dir.glob("*.jpg"))
        screenshots.sort()

        result = {
            "match_dir": str(screenshot_dir),
            "screenshots_found": len(screenshots),
            "team_color_analysis": [],
            "layout_analysis": [],
            "ocr_analysis": [],
        }

        # Analyze each screenshot
        for screenshot_path in screenshots:
            # Team color detection
            if expected_team_color and self.color_detector:
                color_result = self.color_detector.compare_to_expected(
                    screenshot_path,
                    expected_team_color
                )
                result["team_color_analysis"].append(color_result)
            else:
                color_result = self.color_detector.detect_team_color(screenshot_path)
                result["team_color_analysis"].append(color_result)

            # Layout analysis
            if expected_wall_strategy and self.layout_analyzer:
                layout_result = self.layout_analyzer.validate_wall_strategy(
                    screenshot_path,
                    expected_wall_strategy
                )
                result["layout_analysis"].append(layout_result)
            else:
                layout_result = self.layout_analyzer.analyze_layout(screenshot_path)
                result["layout_analysis"].append(layout_result)

            # OCR validation
            if self.ocr_validator:
                ocr_result = self.ocr_validator.validate_screenshot(screenshot_path)
                result["ocr_analysis"].append(ocr_result)

        # Calculate summary statistics
        color_pass = sum(1 for r in result["team_color_analysis"] if r.get("status") == "PASS")
        layout_pass = sum(1 for r in result["layout_analysis"] if r.get("status") == "PASS")

        color_total = len(result["team_color_analysis"])
        layout_total = len(result["layout_analysis"])

        result["summary"] = {
            "color_pass_rate_pct": (color_pass / color_total * 100) if color_total > 0 else 0,
            "layout_pass_rate_pct": (layout_pass / layout_total * 100) if layout_total > 0 else 0,
            "overall_pass_rate_pct": (
                ((color_pass + layout_pass) / (color_total + layout_total) * 100)
                if (color_total + layout_total) > 0
                else 0
            ),
        }

        return result

    def generate_visual_report(self, results: List[Dict]) -> Dict:
        """Generate comprehensive visual validation report.

        Args:
            results: List of per-match visual analysis results

        Returns: {
            "total_matches": int,
            "color_compliance_pct": float,
            "layout_compliance_pct": float,
            "overall_compliance_pct": float,
            "failed_matches": [list of matches with failures],
            "analysis": description
        }
        """
        total_matches = len(results)

        if total_matches == 0:
            return {
                "error": "No results to report",
                "total_matches": 0
            }

        # Aggregate statistics
        total_color_pass = sum(r["summary"]["color_pass_rate_pct"] for r in results)
        total_layout_pass = sum(r["summary"]["layout_pass_rate_pct"] for r in results)

        avg_color_compliance = total_color_pass / total_matches
        avg_layout_compliance = total_layout_pass / total_matches
        avg_overall = (avg_color_compliance + avg_layout_compliance) / 2

        # Find failed matches
        failed_matches = []
        for result in results:
            if result["summary"]["overall_pass_rate_pct"] < 80:
                failed_matches.append({
                    "match_dir": result["match_dir"],
                    "color_compliance": result["summary"]["color_pass_rate_pct"],
                    "layout_compliance": result["summary"]["layout_pass_rate_pct"],
                })

        report = {
            "total_matches": total_matches,
            "color_compliance_pct": avg_color_compliance,
            "layout_compliance_pct": avg_layout_compliance,
            "overall_compliance_pct": avg_overall,
            "failed_matches_count": len(failed_matches),
            "failed_matches": failed_matches,
        }

        # Analysis
        if avg_overall >= 95:
            report["analysis"] = f"✓ Excellent visual compliance ({avg_overall:.1f}%)"
        elif avg_overall >= 85:
            report["analysis"] = f"✓ Good visual compliance ({avg_overall:.1f}%)"
        elif avg_overall >= 70:
            report["analysis"] = f"⚠ Fair visual compliance ({avg_overall:.1f}%)"
        else:
            report["analysis"] = f"✗ Poor visual compliance ({avg_overall:.1f}%)"

        return report


def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Visual monitoring suite for ANW validation"
    )
    parser.add_argument("screenshot_dir", help="Directory containing match screenshots")
    parser.add_argument("--expected-color", help="Expected team color")
    parser.add_argument("--expected-strategy", help="Expected wall strategy")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    suite = VisualMonitoringSuite()

    if not suite.available:
        print("ERROR: Visual validators not available")
        return 1

    result = suite.analyze_match_screenshots(
        Path(args.screenshot_dir),
        expected_team_color=args.expected_color,
        expected_wall_strategy=args.expected_strategy,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Match Directory: {result['match_dir']}")
        print(f"Screenshots: {result['screenshots_found']}")
        print(f"\nVisual Analysis Summary:")
        print(f"  Team Color Compliance: {result['summary']['color_pass_rate_pct']:.1f}%")
        print(f"  Layout Compliance: {result['summary']['layout_pass_rate_pct']:.1f}%")
        print(f"  Overall Compliance: {result['summary']['overall_pass_rate_pct']:.1f}%")


if __name__ == "__main__":
    main()
