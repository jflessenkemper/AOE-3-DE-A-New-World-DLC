#!/usr/bin/env python3
"""Team color detection for ANW visual validation.

Detects unit team colors in screenshots using HSV-based color detection.
Validates that AI is using correct color for its team assignment.
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# Standard AoE3 team colors (HSV ranges)
TEAM_COLORS = {
    "blue": {
        "name": "Blue Team",
        "hsv_lower": np.array([100, 100, 100]),
        "hsv_upper": np.array([130, 255, 255]),
    },
    "red": {
        "name": "Red Team",
        "hsv_lower": np.array([0, 100, 100]),
        "hsv_upper": np.array([10, 255, 255]),
    },
    "yellow": {
        "name": "Yellow Team",
        "hsv_lower": np.array([20, 100, 100]),
        "hsv_upper": np.array([35, 255, 255]),
    },
    "green": {
        "name": "Green Team",
        "hsv_lower": np.array([35, 100, 100]),
        "hsv_upper": np.array([85, 255, 255]),
    },
    "cyan": {
        "name": "Cyan Team",
        "hsv_lower": np.array([85, 100, 100]),
        "hsv_upper": np.array([100, 255, 255]),
    },
    "purple": {
        "name": "Purple Team",
        "hsv_lower": np.array([130, 100, 100]),
        "hsv_upper": np.array([160, 255, 255]),
    },
    "orange": {
        "name": "Orange Team",
        "hsv_lower": np.array([10, 100, 100]),
        "hsv_upper": np.array([20, 255, 255]),
    },
    "pink": {
        "name": "Pink Team",
        "hsv_lower": np.array([160, 100, 100]),
        "hsv_upper": np.array([180, 255, 255]),
    },
}


class TeamColorDetector:
    """Detects and validates team colors in screenshots."""

    def __init__(self):
        """Initialize detector."""
        self.team_colors = TEAM_COLORS

    def detect_team_color(self, screenshot_path: Path) -> Dict:
        """Detect dominant team color in screenshot.

        Returns: {
            "detected_colors": {color_name: pixel_count, ...},
            "dominant_color": "blue" or similar,
            "confidence": 0.0-1.0,
            "analysis": "Human-readable description"
        }
        """
        if not screenshot_path.exists():
            return {"error": f"Screenshot not found: {screenshot_path}"}

        try:
            # Read image
            img = cv2.imread(str(screenshot_path))
            if img is None:
                return {"error": f"Could not read image: {screenshot_path}"}

            # Convert BGR to HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Detect each team color
            detected_colors = {}
            for color_name, color_info in self.team_colors.items():
                mask = cv2.inRange(
                    hsv,
                    color_info["hsv_lower"],
                    color_info["hsv_upper"]
                )
                pixel_count = cv2.countNonZero(mask)
                detected_colors[color_name] = pixel_count

            # Find dominant color
            dominant_color = max(detected_colors, key=detected_colors.get)
            dominant_count = detected_colors[dominant_color]
            total_pixels = img.shape[0] * img.shape[1]
            confidence = dominant_count / total_pixels if total_pixels > 0 else 0.0

            result = {
                "detected_colors": detected_colors,
                "dominant_color": dominant_color,
                "dominant_color_name": self.team_colors[dominant_color]["name"],
                "pixel_count": dominant_count,
                "total_pixels": total_pixels,
                "confidence_pct": confidence * 100,
                "image_path": str(screenshot_path),
            }

            # Analysis
            if confidence > 0.05:
                result["status"] = "VALID"
                result["analysis"] = f"Detected {self.team_colors[dominant_color]['name']} ({confidence*100:.1f}% of pixels)"
            else:
                result["status"] = "AMBIGUOUS"
                result["analysis"] = "No clear team color detected"

            return result

        except Exception as e:
            return {"error": str(e), "image_path": str(screenshot_path)}

    def compare_to_expected(
        self,
        screenshot_path: Path,
        expected_color: str
    ) -> Dict:
        """Compare detected color against expected team color.

        Returns: {
            "matches": bool,
            "expected_color": "blue" or similar,
            "detected_color": "blue" or similar,
            "confidence": 0.0-1.0,
            "status": "PASS" | "FAIL" | "AMBIGUOUS"
        }
        """
        detection = self.detect_team_color(screenshot_path)

        if "error" in detection:
            return {
                "error": detection["error"],
                "expected_color": expected_color,
                "status": "ERROR"
            }

        detected = detection.get("dominant_color", "unknown")
        matches = detected.lower() == expected_color.lower()
        confidence = detection.get("confidence_pct", 0.0)

        result = {
            "matches": matches,
            "expected_color": expected_color,
            "detected_color": detected,
            "confidence_pct": confidence,
            "image_path": str(screenshot_path),
        }

        if matches:
            result["status"] = "PASS"
            result["analysis"] = f"Team color matches expected {expected_color}"
        elif confidence < 5.0:
            result["status"] = "AMBIGUOUS"
            result["analysis"] = "Could not detect clear team color"
        else:
            result["status"] = "FAIL"
            result["analysis"] = f"Expected {expected_color} but detected {detected}"

        return result

    def batch_analyze(self, screenshot_dir: Path, expected_color: str = None) -> List[Dict]:
        """Analyze all screenshots in directory.

        Args:
            screenshot_dir: Directory containing screenshots
            expected_color: Optional expected team color for validation

        Returns: List of analysis results
        """
        results = []

        if not screenshot_dir.exists():
            return [{"error": f"Directory not found: {screenshot_dir}"}]

        # Find all PNG/JPG files
        screenshots = list(screenshot_dir.glob("*.png")) + list(screenshot_dir.glob("*.jpg"))
        screenshots.sort()

        for screenshot_path in screenshots:
            if expected_color:
                result = self.compare_to_expected(screenshot_path, expected_color)
            else:
                result = self.detect_team_color(screenshot_path)

            results.append(result)

        return results


def main():
    """Command-line interface for team color detection."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Detect team colors in AoE3 screenshots"
    )
    parser.add_argument(
        "screenshot",
        help="Screenshot file or directory"
    )
    parser.add_argument(
        "--expected",
        help="Expected team color for validation"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    detector = TeamColorDetector()
    path = Path(args.screenshot)

    if path.is_file():
        if args.expected:
            result = detector.compare_to_expected(path, args.expected)
        else:
            result = detector.detect_team_color(path)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"File: {path.name}")
            print(f"Detected color: {result.get('dominant_color_name', 'Unknown')}")
            print(f"Confidence: {result.get('confidence_pct', 0):.1f}%")
            if args.expected:
                print(f"Expected: {args.expected}")
                print(f"Status: {result.get('status', 'UNKNOWN')}")
            if "analysis" in result:
                print(f"Analysis: {result['analysis']}")

    elif path.is_dir():
        results = detector.batch_analyze(path, args.expected)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Analyzing {len(results)} screenshots...")
            for result in results:
                if "error" not in result:
                    status = result.get("status", "UNKNOWN")
                    color = result.get("dominant_color_name", "Unknown")
                    conf = result.get("confidence_pct", 0)
                    filename = Path(result.get("image_path", "")).name
                    print(f"  [{status}] {filename}: {color} ({conf:.1f}%)")


if __name__ == "__main__":
    main()
