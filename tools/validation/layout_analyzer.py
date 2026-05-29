#!/usr/bin/env python3
"""Building placement & layout analysis for ANW visual validation.

Analyzes building clusters, wall patterns, and settlement distribution
to validate that AI follows expected wall strategy and base layout.
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from scipy import ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class LayoutAnalyzer:
    """Analyzes building and settlement layouts in screenshots."""

    # Color ranges for detecting buildings/structures
    # Buildings are typically brown/gray in AoE3
    BUILDING_COLOR_LOWER = np.array([10, 30, 80])
    BUILDING_COLOR_UPPER = np.array([35, 200, 200])

    # Wall colors are typically paler/whiter
    WALL_COLOR_LOWER = np.array([0, 0, 150])
    WALL_COLOR_UPPER = np.array([180, 80, 255])

    def __init__(self):
        """Initialize analyzer."""
        self.scipy_available = SCIPY_AVAILABLE

    def detect_buildings(self, screenshot_path: Path) -> Dict:
        """Detect building clusters in screenshot.

        Returns: {
            "building_clusters": number of detected clusters,
            "total_pixels": pixels identified as buildings,
            "cluster_centers": [(x, y), ...],
            "largest_cluster_size": pixels in largest cluster,
            "distribution": "compact" | "scattered" | "linear",
            "analysis": description
        }
        """
        if not screenshot_path.exists():
            return {"error": f"Screenshot not found: {screenshot_path}"}

        try:
            img = cv2.imread(str(screenshot_path))
            if img is None:
                return {"error": f"Could not read image"}

            # Convert BGR to HSV for better color detection
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Detect buildings (brown/tan colors)
            mask = cv2.inRange(hsv, self.BUILDING_COLOR_LOWER, self.BUILDING_COLOR_UPPER)

            # Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # Find contours (building clusters)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Analyze clusters
            cluster_centers = []
            cluster_sizes = []

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 50:  # Minimum cluster size threshold
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cluster_centers.append((cx, cy))
                        cluster_sizes.append(area)

            # Analyze distribution pattern
            distribution = self._analyze_distribution(cluster_centers)

            total_pixels = cv2.countNonZero(mask)

            result = {
                "building_clusters": len(cluster_centers),
                "total_pixels": total_pixels,
                "cluster_centers": cluster_centers,
                "cluster_sizes": cluster_sizes,
                "largest_cluster_size": max(cluster_sizes) if cluster_sizes else 0,
                "distribution": distribution,
                "image_path": str(screenshot_path),
            }

            # Analysis
            if len(cluster_centers) < 3:
                result["analysis"] = "Very few building clusters detected (compact settlement)"
            elif distribution == "scattered":
                result["analysis"] = f"Scattered settlement pattern: {len(cluster_centers)} clusters spread across map"
            elif distribution == "compact":
                result["analysis"] = f"Compact settlement pattern: {len(cluster_centers)} clusters in concentrated area"
            else:
                result["analysis"] = f"{len(cluster_centers)} building clusters in linear/defensive pattern"

            return result

        except Exception as e:
            return {"error": str(e), "image_path": str(screenshot_path)}

    def detect_walls(self, screenshot_path: Path) -> Dict:
        """Detect wall patterns (ring, segments, etc).

        Returns: {
            "wall_pixels": number of pixels identified as walls,
            "wall_pattern": "ring" | "segments" | "minimal" | "none",
            "wall_coverage_pct": percentage of image covered by walls,
            "analysis": description
        }
        """
        if not screenshot_path.exists():
            return {"error": f"Screenshot not found: {screenshot_path}"}

        try:
            img = cv2.imread(str(screenshot_path))
            if img is None:
                return {"error": f"Could not read image"}

            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Detect walls (lighter colors, palisades are tan/gray)
            mask = cv2.inRange(hsv, self.WALL_COLOR_LOWER, self.WALL_COLOR_UPPER)

            # Morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            wall_pixels = cv2.countNonZero(mask)
            total_pixels = img.shape[0] * img.shape[1]
            wall_coverage_pct = (wall_pixels / total_pixels * 100) if total_pixels > 0 else 0

            # Classify wall pattern
            if wall_pixels == 0:
                wall_pattern = "none"
            elif wall_coverage_pct < 2:
                wall_pattern = "minimal"
            elif wall_coverage_pct < 5:
                wall_pattern = "segments"
            else:
                wall_pattern = "ring"

            result = {
                "wall_pixels": wall_pixels,
                "total_pixels": total_pixels,
                "wall_coverage_pct": wall_coverage_pct,
                "wall_pattern": wall_pattern,
                "image_path": str(screenshot_path),
            }

            # Analysis
            if wall_pattern == "none":
                result["analysis"] = "No walls detected (raiding/open map strategy)"
            elif wall_pattern == "minimal":
                result["analysis"] = "Minimal walls detected (light defense)"
            elif wall_pattern == "segments":
                result["analysis"] = "Wall segments detected (chokepoint or forward defense)"
            else:
                result["analysis"] = "Full wall ring detected (fortress strategy)"

            return result

        except Exception as e:
            return {"error": str(e), "image_path": str(screenshot_path)}

    def analyze_layout(self, screenshot_path: Path) -> Dict:
        """Comprehensive layout analysis combining buildings and walls.

        Returns: {
            "buildings": building analysis,
            "walls": wall analysis,
            "wall_strategy": inferred strategy,
            "status": "OK" | "ERROR"
        }
        """
        buildings = self.detect_buildings(screenshot_path)
        walls = self.detect_walls(screenshot_path)

        if "error" in buildings or "error" in walls:
            return {
                "error": buildings.get("error") or walls.get("error"),
                "image_path": str(screenshot_path),
                "status": "ERROR"
            }

        # Infer wall strategy from pattern
        wall_pattern = walls.get("wall_pattern", "unknown")
        building_dist = buildings.get("distribution", "unknown")

        strategy = self._infer_strategy(wall_pattern, building_dist)

        return {
            "buildings": buildings,
            "walls": walls,
            "wall_strategy": strategy,
            "image_path": str(screenshot_path),
            "status": "OK"
        }

    def validate_wall_strategy(
        self,
        screenshot_path: Path,
        expected_strategy: str
    ) -> Dict:
        """Validate actual wall strategy matches expected.

        Expected strategies: "fortress_ring", "chokepoint", "forward", "minimal", "mobile"
        """
        analysis = self.analyze_layout(screenshot_path)

        if analysis.get("status") == "ERROR":
            return {"error": analysis.get("error"), "status": "ERROR"}

        actual_strategy = analysis.get("wall_strategy", "unknown")

        result = {
            "expected": expected_strategy,
            "actual": actual_strategy,
            "image_path": str(screenshot_path),
        }

        if actual_strategy.lower() == expected_strategy.lower():
            result["status"] = "PASS"
            result["analysis"] = f"Wall strategy matches: {actual_strategy}"
        else:
            result["status"] = "FAIL"
            result["analysis"] = f"Expected {expected_strategy} but found {actual_strategy}"

        return result

    def _analyze_distribution(self, cluster_centers: List[Tuple]) -> str:
        """Analyze spatial distribution of building clusters.

        Returns: "compact" | "scattered" | "linear"
        """
        if not cluster_centers or len(cluster_centers) < 2:
            return "compact"

        # Calculate variance of positions
        x_coords = [c[0] for c in cluster_centers]
        y_coords = [c[1] for c in cluster_centers]

        x_variance = np.var(x_coords) if x_coords else 0
        y_variance = np.var(y_coords) if y_coords else 0

        # High variance in both = scattered
        # High variance in one = linear
        # Low variance in both = compact

        if x_variance > 5000 and y_variance > 5000:
            return "scattered"
        elif x_variance > 5000 or y_variance > 5000:
            return "linear"
        else:
            return "compact"

    def _infer_strategy(self, wall_pattern: str, building_dist: str) -> str:
        """Infer AI wall strategy from wall pattern and building distribution."""
        if wall_pattern == "none":
            if building_dist == "scattered":
                return "mobile_scattered"  # Mobile No Walls strategy
            else:
                return "economy_open"  # Economy-focused, open map

        elif wall_pattern == "minimal":
            if building_dist == "linear":
                return "frontier_palisades"  # Frontier Palisades strategy
            else:
                return "light_defense"

        elif wall_pattern == "segments":
            if building_dist == "linear":
                return "chokepoint_segments"  # Chokepoint Segments strategy
            else:
                return "forward_operational"  # Forward Operational Line

        else:  # wall_pattern == "ring"
            return "fortress_ring"  # Fortress Ring strategy


def main():
    """Command-line interface."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Layout analysis for ANW screenshots")
    parser.add_argument("screenshot", help="Screenshot file or directory")
    parser.add_argument("--expected-strategy", help="Expected wall strategy for validation")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    analyzer = LayoutAnalyzer()
    path = Path(args.screenshot)

    if path.is_file():
        if args.expected_strategy:
            result = analyzer.validate_wall_strategy(path, args.expected_strategy)
        else:
            result = analyzer.analyze_layout(path)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"File: {path.name}")
            if "buildings" in result:
                print(f"Buildings: {result['buildings']['building_clusters']} clusters")
                print(f"  Distribution: {result['buildings']['distribution']}")
            if "walls" in result:
                print(f"Walls: {result['walls']['wall_pattern']}")
                print(f"  Coverage: {result['walls']['wall_coverage_pct']:.2f}%")
            if "wall_strategy" in result:
                print(f"Inferred strategy: {result['wall_strategy']}")
            if args.expected_strategy:
                print(f"Validation: {result.get('status', 'UNKNOWN')}")

    elif path.is_dir():
        screenshots = list(path.glob("*.png")) + list(path.glob("*.jpg"))
        results = []
        for screenshot in sorted(screenshots):
            result = analyzer.analyze_layout(screenshot)
            results.append(result)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Analyzing {len(results)} screenshots...")
            for result in results:
                filename = Path(result.get("image_path", "")).name
                strategy = result.get("wall_strategy", "UNKNOWN")
                status = result.get("status", "OK")
                print(f"  [{status}] {filename}: {strategy}")


if __name__ == "__main__":
    main()
