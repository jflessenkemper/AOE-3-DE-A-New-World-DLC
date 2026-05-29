#!/usr/bin/env python3
"""OCR-based UI text validation for ANW screenshots.

Extracts in-game UI text (population, age, resources) and validates
against expected game state values.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False


class OCRValidator:
    """Validates in-game UI text via OCR."""

    def __init__(self):
        """Initialize validator."""
        self.pytesseract_available = PYTESSERACT_AVAILABLE

    def extract_text(self, screenshot_path: Path) -> Dict:
        """Extract all text from screenshot via OCR.

        Returns: {
            "raw_text": "extracted OCR text",
            "status": "OK" | "ERROR",
            "error": optional error message
        }
        """
        if not self.pytesseract_available:
            return {
                "error": "pytesseract not available",
                "status": "ERROR"
            }

        try:
            img = Image.open(screenshot_path)
            text = pytesseract.image_to_string(img)

            return {
                "raw_text": text,
                "image_path": str(screenshot_path),
                "status": "OK"
            }

        except Exception as e:
            return {
                "error": str(e),
                "image_path": str(screenshot_path),
                "status": "ERROR"
            }

    def extract_ui_metrics(self, raw_text: str) -> Dict:
        """Extract common UI metrics from OCR text.

        Looks for patterns like:
        - Population: X/Y
        - Age: Colonial
        - Resources: X food, Y wood, Z gold
        """
        metrics = {}

        # Population pattern: "Population: X/Y" or "Pop: X/Y"
        pop_match = re.search(r'(?:Population|Pop)[\s:]*(\d+)\s*/\s*(\d+)', raw_text, re.IGNORECASE)
        if pop_match:
            metrics["population_used"] = int(pop_match.group(1))
            metrics["population_cap"] = int(pop_match.group(2))

        # Age pattern: "Age: Colonial" or "Colonial Age"
        age_match = re.search(r'(?:Age|Colonial|Fortress|Industrial|Imperial)', raw_text, re.IGNORECASE)
        if age_match:
            metrics["age"] = age_match.group(0).strip()

        # Resources: look for food, wood, gold, coin
        food_match = re.search(r'Food[\s:]*(\d+)', raw_text, re.IGNORECASE)
        if food_match:
            metrics["food"] = int(food_match.group(1))

        wood_match = re.search(r'Wood[\s:]*(\d+)', raw_text, re.IGNORECASE)
        if wood_match:
            metrics["wood"] = int(wood_match.group(1))

        gold_match = re.search(r'Gold[\s:]*(\d+)', raw_text, re.IGNORECASE)
        if gold_match:
            metrics["gold"] = int(gold_match.group(1))

        coin_match = re.search(r'Coin[\s:]*(\d+)', raw_text, re.IGNORECASE)
        if coin_match:
            metrics["coin"] = int(coin_match.group(1))

        return metrics

    def validate_metrics(
        self,
        metrics: Dict,
        expected: Dict
    ) -> Dict:
        """Validate extracted metrics against expected values.

        Args:
            metrics: {population_used, population_cap, food, wood, gold, age}
            expected: {population_cap: X, age: "Colonial", ...}

        Returns: {
            "valid": bool,
            "errors": [list of validation errors],
            "warnings": [list of warnings]
        }
        """
        errors = []
        warnings = []

        # Check population cap
        if "population_cap" in expected:
            if "population_cap" in metrics:
                expected_cap = expected["population_cap"]
                actual_cap = metrics["population_cap"]
                if actual_cap != expected_cap:
                    errors.append(
                        f"Population cap mismatch: expected {expected_cap}, got {actual_cap}"
                    )
            else:
                warnings.append("Could not extract population cap from screenshot")

        # Check population doesn't exceed cap
        if "population_used" in metrics and "population_cap" in metrics:
            if metrics["population_used"] > metrics["population_cap"]:
                errors.append(
                    f"Population exceeds cap: {metrics['population_used']} > {metrics['population_cap']}"
                )

        # Check age
        if "age" in expected and "age" in metrics:
            if expected["age"].lower() != metrics["age"].lower():
                errors.append(
                    f"Age mismatch: expected {expected['age']}, got {metrics['age']}"
                )

        # Check resources are non-negative
        for resource in ["food", "wood", "gold", "coin"]:
            if resource in metrics and metrics[resource] < 0:
                errors.append(f"{resource} is negative: {metrics[resource]}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metrics": metrics,
        }

    def validate_screenshot(
        self,
        screenshot_path: Path,
        expected: Optional[Dict] = None
    ) -> Dict:
        """Full validation: OCR → extract metrics → validate.

        Returns: {
            "image_path": str,
            "raw_text": str,
            "metrics": {extracted metrics},
            "validation": {validation results},
            "status": "OK" | "WARNING" | "ERROR"
        }
        """
        # Extract text
        text_result = self.extract_text(screenshot_path)
        if text_result["status"] == "ERROR":
            return {
                "image_path": str(screenshot_path),
                "status": "ERROR",
                "error": text_result.get("error")
            }

        raw_text = text_result["raw_text"]

        # Extract metrics
        metrics = self.extract_ui_metrics(raw_text)

        result = {
            "image_path": str(screenshot_path),
            "raw_text": raw_text,
            "metrics": metrics,
            "status": "OK"
        }

        # Validate if expected provided
        if expected:
            validation = self.validate_metrics(metrics, expected)
            result["validation"] = validation

            if validation["errors"]:
                result["status"] = "ERROR"
            elif validation["warnings"]:
                result["status"] = "WARNING"

        return result

    def batch_validate(
        self,
        screenshot_dir: Path,
        expected: Optional[Dict] = None
    ) -> List[Dict]:
        """Validate all screenshots in a directory.

        Returns: List of validation results
        """
        results = []

        if not screenshot_dir.exists():
            return [{"error": f"Directory not found: {screenshot_dir}"}]

        screenshots = list(screenshot_dir.glob("*.png")) + list(screenshot_dir.glob("*.jpg"))
        screenshots.sort()

        for screenshot_path in screenshots:
            result = self.validate_screenshot(screenshot_path, expected)
            results.append(result)

        return results


def main():
    """Command-line interface."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="OCR-based screenshot text validation")
    parser.add_argument("screenshot", help="Screenshot file or directory")
    parser.add_argument("--expected-age", help="Expected age (Colonial, etc)")
    parser.add_argument("--expected-pop-cap", type=int, help="Expected population cap")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    validator = OCRValidator()

    if not validator.pytesseract_available:
        print("ERROR: pytesseract not available. Install with: pip install pytesseract")
        return 1

    path = Path(args.screenshot)
    expected = {}
    if args.expected_age:
        expected["age"] = args.expected_age
    if args.expected_pop_cap:
        expected["population_cap"] = args.expected_pop_cap

    if path.is_file():
        result = validator.validate_screenshot(path, expected if expected else None)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"File: {path.name}")
            print(f"Status: {result['status']}")
            if "metrics" in result:
                print("Metrics:")
                for key, value in result["metrics"].items():
                    print(f"  {key}: {value}")
            if "validation" in result and result["validation"]["errors"]:
                print("Errors:")
                for error in result["validation"]["errors"]:
                    print(f"  - {error}")

    elif path.is_dir():
        results = validator.batch_validate(path, expected if expected else None)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Analyzing {len(results)} screenshots...")
            for result in results:
                status = result.get("status", "UNKNOWN")
                filename = Path(result.get("image_path", "")).name
                print(f"  [{status}] {filename}")
                if status == "ERROR" and "error" in result:
                    print(f"    {result['error']}")


if __name__ == "__main__":
    main()
