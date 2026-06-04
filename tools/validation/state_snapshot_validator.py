#!/usr/bin/env python3
"""State snapshot validation for ANW determinism testing.

Compares actual game state trajectories against baseline snapshots
to detect silent state divergence during gameplay.

State captured via XS trigger at 30-60 second intervals:
  - Population (used / cap)
  - Age progression
  - Unit counts by type
  - Resource state (food, wood, gold)
  - Technology status
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class StateSnapshot:
    """Single point-in-time game state snapshot."""

    def __init__(
        self,
        timestamp_ms: int,
        population_used: int,
        population_cap: int,
        age: str,
        resources: Dict[str, int],
        units: Dict[str, int],
    ):
        self.timestamp_ms = timestamp_ms
        self.population_used = population_used
        self.population_cap = population_cap
        self.age = age
        self.resources = resources or {}
        self.units = units or {}

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp_ms": self.timestamp_ms,
            "population": {
                "used": self.population_used,
                "cap": self.population_cap,
            },
            "age": self.age,
            "resources": self.resources,
            "units": self.units,
        }

    @staticmethod
    def from_dict(data: Dict) -> "StateSnapshot":
        """Create from dictionary."""
        return StateSnapshot(
            timestamp_ms=data["timestamp_ms"],
            population_used=data["population"]["used"],
            population_cap=data["population"]["cap"],
            age=data.get("age", ""),
            resources=data.get("resources", {}),
            units=data.get("units", {}),
        )


class StateSnapshotParser:
    """Parses state snapshots from match logs.

    Supports two emission formats:
      • Legacy:  ``[STATE t=12345 pop_used=42 ... ]``
      • ANWP v=2: ``[ANWP v=2 t=12345 p=1 civ=ANWBritish ldr=elizabeth
                     tag=state.snapshot] ageMs=12345 pop_used=42 ...``
        (emitted by ``game/ai/core/aiStateSnapshot.xs`` via ``llProbe``).
    """

    # Match either marker style — both encode k=v pairs we already parse.
    STATE_PATTERN = re.compile(
        r"(?:\[STATE\b|tag=state\.snapshot\b)"
    )

    def parse_log(self, log_path: Path) -> List[StateSnapshot]:
        """Parse state snapshots from match.log.

        Expected formats in log:
          [STATE t=30000 pop_used=42 pop_cap=75 age=Colonial ...]
          [ANWP v=2 t=30000 p=1 civ=ANWBritish ldr=elizabeth
              tag=state.snapshot] ageMs=30000 pop_used=42 pop_cap=75 ...

        Returns: List of StateSnapshot objects, chronologically sorted.
        """
        snapshots = []

        if not log_path.exists():
            return snapshots

        try:
            log_content = log_path.read_text()

            for line in log_content.split('\n'):
                if "[STATE" not in line and "tag=state.snapshot" not in line:
                    continue

                # Extract values from log line
                state = self._parse_state_line(line)
                if state:
                    snapshots.append(state)

            # Sort by timestamp
            snapshots.sort(key=lambda s: s.timestamp_ms)
            return snapshots

        except Exception as e:
            print(f"ERROR parsing {log_path}: {e}")
            return []

    def _parse_state_line(self, line: str) -> Optional[StateSnapshot]:
        """Parse single [STATE ...] line from log."""
        try:
            # Extract timestamp
            t_match = re.search(r't=(\d+)', line)
            if not t_match:
                return None

            timestamp_ms = int(t_match.group(1))

            # Extract population
            pop_used = 0
            pop_cap = 0

            pop_used_match = re.search(r'pop_used[=:](\d+)', line)
            if pop_used_match:
                pop_used = int(pop_used_match.group(1))

            pop_cap_match = re.search(r'pop_cap[=:](\d+)', line)
            if pop_cap_match:
                pop_cap = int(pop_cap_match.group(1))

            # Extract age
            age = ""
            age_match = re.search(r'age[=:](\w+)', line)
            if age_match:
                age = age_match.group(1)

            # Extract resources
            resources = {}
            for resource in ["food", "wood", "gold", "coin"]:
                match = re.search(rf'{resource}[=:](\d+)', line)
                if match:
                    resources[resource] = int(match.group(1))

            # Extract units. Field names match what aiStateSnapshot.xs emits
            # (villager / infantry / cavalry / artillery / warship / landmil)
            # plus "explorer" carried over from the legacy [STATE ...] format.
            units = {}
            for unit_type in [
                "villager",
                "infantry",
                "cavalry",
                "artillery",
                "warship",
                "landmil",
                "explorer",
            ]:
                match = re.search(rf'\b{unit_type}[=:](\d+)', line)
                if match:
                    units[unit_type] = int(match.group(1))

            return StateSnapshot(
                timestamp_ms=timestamp_ms,
                population_used=pop_used,
                population_cap=pop_cap,
                age=age,
                resources=resources,
                units=units,
            )

        except Exception:
            return None


class StateTrajectoryValidator:
    """Validates actual state trajectories against baseline."""

    def __init__(self, tolerance: float = 0.05):
        """Initialize validator.

        Args:
            tolerance: Allowed variance as percentage (0.05 = 5%)
        """
        self.tolerance = tolerance

    def compare_trajectories(
        self,
        actual: List[StateSnapshot],
        baseline: List[StateSnapshot],
    ) -> Dict:
        """Compare actual vs. baseline state trajectory.

        Returns: {
            "matches": bool,
            "divergence_points": [list of timestamps where divergence detected],
            "errors": [list of error descriptions],
            "analysis": summary
        }
        """
        errors = []
        divergence_points = []

        if len(actual) != len(baseline):
            errors.append(
                f"Trajectory length mismatch: {len(actual)} actual vs {len(baseline)} baseline"
            )

        # Compare each snapshot
        for i, (actual_snap, baseline_snap) in enumerate(zip(actual, baseline)):
            divergence = self._compare_snapshots(actual_snap, baseline_snap)

            if divergence:
                divergence_points.append({
                    "timestamp_ms": actual_snap.timestamp_ms,
                    "snapshot_index": i,
                    "divergence": divergence,
                })
                errors.extend(divergence)

        result = {
            "matches": len(errors) == 0,
            "divergence_points": divergence_points,
            "errors": errors,
        }

        # Analysis
        if len(errors) == 0:
            result["analysis"] = "✓ State trajectory matches baseline (deterministic)"
        else:
            result["analysis"] = f"✗ Detected {len(errors)} state divergences"

        return result

    def _compare_snapshots(
        self,
        actual: StateSnapshot,
        baseline: StateSnapshot,
        tolerance: Optional[float] = None,
    ) -> List[str]:
        """Compare two snapshots, return list of divergences."""
        if tolerance is None:
            tolerance = self.tolerance

        divergences = []

        # Check population
        if actual.population_cap != baseline.population_cap:
            divergences.append(
                f"Population cap: {actual.population_cap} vs {baseline.population_cap}"
            )

        if actual.population_cap > 0:
            pop_variance = abs(
                actual.population_used - baseline.population_used
            ) / baseline.population_cap

            if pop_variance > tolerance:
                divergences.append(
                    f"Population used diverged by {pop_variance*100:.1f}%: "
                    f"{actual.population_used} vs {baseline.population_used}"
                )

        # Check age
        if actual.age != baseline.age:
            divergences.append(f"Age: {actual.age} vs {baseline.age}")

        # Check resources
        for resource in ["food", "wood", "gold"]:
            actual_val = actual.resources.get(resource, 0)
            baseline_val = baseline.resources.get(resource, 0)

            if baseline_val > 0:
                variance = abs(actual_val - baseline_val) / baseline_val
                if variance > tolerance:
                    divergences.append(
                        f"{resource.capitalize()} diverged by {variance*100:.1f}%: "
                        f"{actual_val} vs {baseline_val}"
                    )

        # Check units (allow ±2 unit variance)
        for unit_type in actual.units:
            actual_count = actual.units.get(unit_type, 0)
            baseline_count = baseline.units.get(unit_type, 0)

            if abs(actual_count - baseline_count) > 2:
                divergences.append(
                    f"{unit_type.capitalize()} count: {actual_count} vs {baseline_count}"
                )

        return divergences

    def validate_state_integrity(self, snapshots: List[StateSnapshot]) -> Dict:
        """Check internal state consistency (population, resources, etc).

        Returns: {
            "valid": bool,
            "errors": [list of integrity issues]
        }
        """
        errors = []

        for i, snap in enumerate(snapshots):
            # Population can't exceed cap
            if snap.population_used > snap.population_cap:
                errors.append(
                    f"Snapshot {i} (t={snap.timestamp_ms}): "
                    f"Population exceeds cap: {snap.population_used} > {snap.population_cap}"
                )

            # Resources can't be negative
            for resource, value in snap.resources.items():
                if value < 0:
                    errors.append(
                        f"Snapshot {i} (t={snap.timestamp_ms}): "
                        f"Negative {resource}: {value}"
                    )

            # Units can't be negative
            for unit_type, count in snap.units.items():
                if count < 0:
                    errors.append(
                        f"Snapshot {i} (t={snap.timestamp_ms}): "
                        f"Negative {unit_type} count: {count}"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }


def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="State snapshot validation"
    )
    parser.add_argument("log_file", help="Match log file to parse")
    parser.add_argument("--baseline", help="Baseline state file for comparison")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    parser_obj = StateSnapshotParser()
    snapshots = parser_obj.parse_log(Path(args.log_file))

    print(f"Parsed {len(snapshots)} state snapshots from {args.log_file}")

    if args.baseline:
        with open(args.baseline) as f:
            baseline_data = json.load(f)
        baseline_snapshots = [StateSnapshot.from_dict(d) for d in baseline_data]

        validator = StateTrajectoryValidator()
        result = validator.compare_trajectories(snapshots, baseline_snapshots)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Comparison: {result['analysis']}")
            if result["errors"]:
                print("Errors:")
                for error in result["errors"][:10]:
                    print(f"  - {error}")

    else:
        # Just check integrity
        validator = StateTrajectoryValidator()
        result = validator.validate_state_integrity(snapshots)

        if result["valid"]:
            print("✓ State integrity check PASSED")
        else:
            print(f"✗ State integrity check FAILED ({len(result['errors'])} errors)")
            for error in result["errors"][:5]:
                print(f"  - {error}")


if __name__ == "__main__":
    main()
