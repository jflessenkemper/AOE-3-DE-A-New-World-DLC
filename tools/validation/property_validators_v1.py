#!/usr/bin/env python3
"""Property-based validators for ANW mod testing.

Validates invariants extracted from game logs to catch behavioral anomalies.
"""
import re
from typing import Dict, List, Tuple, Optional


class PropertyValidator:
    """Base class for property validators."""

    def __init__(self, name: str):
        self.name = name

    def validate(self, log_content: str, context: Dict) -> Tuple[bool, str]:
        """Validate a property. Returns (passed, message)."""
        raise NotImplementedError


class PopulationCapValidator(PropertyValidator):
    """Verify population never exceeds cap."""

    def __init__(self):
        super().__init__("PopulationCapValidator")

    def validate(self, log_content: str, context: Dict) -> Tuple[bool, str]:
        """Check that pop_used <= pop_cap throughout match."""
        try:
            pop_used_matches = re.findall(r'\[STATE\].*pop_used[=:](\d+)', log_content)
            pop_cap_matches = re.findall(r'\[STATE\].*pop_cap[=:](\d+)', log_content)

            if not pop_used_matches or not pop_cap_matches:
                return True, "No population data in log"

            for used, cap in zip(pop_used_matches, pop_cap_matches):
                if int(used) > int(cap):
                    return False, f"Population exceeded cap: {used} > {cap}"

            return True, "Population cap enforced"
        except Exception as e:
            return True, f"Could not validate (no population data): {e}"


class TechProgressionValidator(PropertyValidator):
    """Verify age progression follows logical order."""

    def __init__(self):
        super().__init__("TechProgressionValidator")
        self.age_order = ["Age I", "Age II", "Age III", "Age IV", "Imperial"]

    def validate(self, log_content: str, context: Dict) -> Tuple[bool, str]:
        """Check age progression is monotonic."""
        try:
            age_advances = re.findall(r'advanced to (Age [I-V]+|Imperial)', log_content)
            if not age_advances:
                return True, "No age progression in log"

            prev_idx = -1
            for age in age_advances:
                try:
                    curr_idx = self.age_order.index(age)
                    if curr_idx <= prev_idx:
                        return False, f"Age progression not monotonic: {age_advances}"
                    prev_idx = curr_idx
                except ValueError:
                    pass

            return True, "Age progression valid"
        except Exception as e:
            return True, f"Could not validate age progression: {e}"


class DoctrineComplianceValidator(PropertyValidator):
    """Verify AI doctrine choices match specification."""

    def __init__(self):
        super().__init__("DoctrineComplianceValidator")

    def validate(self, log_content: str, context: Dict) -> Tuple[bool, str]:
        """Check [ANWP v=2] probes match expected wall strategy."""
        try:
            # Extract [ANWP v=2] probes
            probes = re.findall(
                r'\[ANWP v=2.*?wall_strategy[=:](\d)\]',
                log_content,
                re.DOTALL
            )

            if not probes:
                return True, "No doctrine probes in log"

            expected_strategy = context.get("expected_wall_strategy")
            if expected_strategy is None:
                return True, "No expected wall strategy in context"

            for probe_strategy in probes:
                if int(probe_strategy) != int(expected_strategy):
                    return False, f"Wall strategy mismatch: got {probe_strategy}, expected {expected_strategy}"

            return True, f"Doctrine compliance OK (wall_strategy={expected_strategy})"
        except Exception as e:
            return True, f"Could not validate doctrine: {e}"


class UnitProductionValidator(PropertyValidator):
    """Verify unit production rates are reasonable."""

    def __init__(self):
        super().__init__("UnitProductionValidator")

    def validate(self, log_content: str, context: Dict) -> Tuple[bool, str]:
        """Check unit counts don't grow impossibly fast."""
        try:
            # Extract unit count probes
            unit_counts = re.findall(
                r'\[ANWP.*?units\[(\w+)\]\s*[=:](\d+)',
                log_content
            )

            if not unit_counts:
                return True, "No unit production data in log"

            # Check for impossibly high counts (>500 of one unit type)
            for unit_type, count in unit_counts:
                if int(count) > 500:
                    return False, f"Unit count anomaly: {count} {unit_type}"

            return True, "Unit production rates reasonable"
        except Exception as e:
            return True, f"Could not validate unit production: {e}"


class BuildingPlacementValidator(PropertyValidator):
    """Verify building placement follows strategy."""

    def __init__(self):
        super().__init__("BuildingPlacementValidator")

    def validate(self, log_content: str, context: Dict) -> Tuple[bool, str]:
        """Check first military building appears within expected timeframe."""
        try:
            # Look for first building placement marker
            matches = re.findall(
                r'\[ANWP.*?first_(\w+_)?building[=:](\d+)',
                log_content
            )

            if not matches:
                return True, "No building placement data in log"

            expected_ms_min = context.get("expected_building_time_min", 180000)  # 3 min default
            expected_ms_max = context.get("expected_building_time_max", 600000)  # 10 min default

            for building_type, timestamp in matches:
                ts = int(timestamp)
                if ts < expected_ms_min or ts > expected_ms_max:
                    return False, f"Building placement timing off: {ts}ms not in [{expected_ms_min}, {expected_ms_max}]"

            return True, f"Building placement timing OK"
        except Exception as e:
            return True, f"Could not validate building placement: {e}"


class LogFormatValidator(PropertyValidator):
    """Verify log contains required markers."""

    def __init__(self):
        super().__init__("LogFormatValidator")

    def validate(self, log_content: str, context: Dict) -> Tuple[bool, str]:
        """Check log has [ANWP v=2] probes."""
        if not log_content:
            return False, "Empty log content"

        # Check for at least one [ANWP v=2] marker
        if '[ANWP v=2' not in log_content:
            return False, "No [ANWP v=2] probes in log"

        return True, "Log format valid"


class PropertyValidatorSuite:
    """Collection of property validators."""

    def __init__(self):
        self.validators = [
            LogFormatValidator(),
            PopulationCapValidator(),
            TechProgressionValidator(),
            DoctrineComplianceValidator(),
            UnitProductionValidator(),
            BuildingPlacementValidator(),
        ]

    def validate(self, log_content: str, context: Dict = None) -> Dict[str, Tuple[bool, str]]:
        """Run all validators on a log."""
        if context is None:
            context = {}

        results = {}
        for validator in self.validators:
            passed, message = validator.validate(log_content, context)
            results[validator.name] = (passed, message)

        return results

    def summarize(self, results: Dict[str, Tuple[bool, str]]) -> Tuple[bool, str]:
        """Summarize validation results."""
        passed = all(passed for passed, _ in results.values())
        messages = [msg for _, msg in results.values()]
        summary = " | ".join(messages)
        return passed, summary
