from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from tools.validation.validate_runtime_logs import validate_runtime_log


SAMPLE_SPEC = {
    "suites": [
        {
            "name": "runtime_happy_path",
            "required": [
                {"value": "A New World: [RULE] AI non-elite rout enabled at 25% health; elite units hold and human-controlled units keep manual control", "description": "bootstrap"},
                {"value": "A New World: created explorer escort plan", "description": "escort"},
            ],
            "ordered": [
                {"value": "A New World: [UNIT] ai-rout-start unit=", "description": "start"},
                {"value": "A New World: [UNIT] ai-rout-move unit=", "description": "move"},
                {"value": "A New World: [UNIT] ai-rout-arrival unit=", "description": "arrival"},
            ],
            "forbidden": [
                {"value": "Runtime log validation failed", "description": "validator recursion"}
            ],
        },
        {
            "name": "regex_suite",
            "required": [
                {"kind": "regex", "value": r"A New World: \[UNIT\] ai-rout-move unit=\d+", "description": "AI move"}
            ]
        }
    ]
}


GOOD_LOG = """A New World: [RULE] AI non-elite rout enabled at 25% health; elite units hold and human-controlled units keep manual control
A New World: created explorer escort plan 12 for attack plan 8 using 4 non-elite troops.
A New World: [UNIT] ai-rout-start unit=27 destination=<7,8,9>
A New World: [UNIT] ai-rout-move unit=27 destination=<7,8,9>
A New World: [UNIT] ai-rout-arrival unit=27 destination=<7,8,9>
"""


BAD_ORDER_LOG = """A New World: [UNIT] ai-rout-arrival unit=27 destination=<7,8,9>
A New World: [UNIT] ai-rout-start unit=27 destination=<7,8,9>
A New World: [UNIT] ai-rout-move unit=27 destination=<7,8,9>
"""


class ValidateRuntimeLogsTests(unittest.TestCase):
    def make_inputs(self, log_text: str, spec: dict | None = None) -> tuple[Path, Path, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        repo_root = Path(temp_dir.name)
        log_path = repo_root / "Age3Log.txt"
        spec_path = repo_root / "runtime_spec.json"
        log_path.write_text(log_text, encoding="utf-8")
        spec_path.write_text(json.dumps(spec or SAMPLE_SPEC, indent=2), encoding="utf-8")
        return repo_root, log_path, spec_path

    def test_accepts_matching_runtime_suite(self) -> None:
        repo_root, log_path, spec_path = self.make_inputs(GOOD_LOG)
        self.assertEqual(
            validate_runtime_log(repo_root=repo_root, log_path=log_path, spec_path=spec_path, suite_names=["runtime_happy_path"]),
            [],
        )

    def test_reports_missing_required_marker(self) -> None:
        repo_root, log_path, spec_path = self.make_inputs("A New World: [UNIT] ai-rout-move unit=11")
        issues = validate_runtime_log(repo_root=repo_root, log_path=log_path, spec_path=spec_path, suite_names=["runtime_happy_path"])
        self.assertIn("[runtime_happy_path] missing required log marker: bootstrap", issues)

    def test_reports_out_of_order_markers(self) -> None:
        repo_root, log_path, spec_path = self.make_inputs(BAD_ORDER_LOG)
        issues = validate_runtime_log(repo_root=repo_root, log_path=log_path, spec_path=spec_path, suite_names=["runtime_happy_path"])
        self.assertIn("[runtime_happy_path] ordered marker out of sequence: arrival", issues)

    def test_supports_regex_expectations(self) -> None:
        repo_root, log_path, spec_path = self.make_inputs(GOOD_LOG)
        self.assertEqual(
            validate_runtime_log(repo_root=repo_root, log_path=log_path, spec_path=spec_path, suite_names=["regex_suite"]),
            [],
        )

    def test_reports_unknown_suite(self) -> None:
        repo_root, log_path, spec_path = self.make_inputs(GOOD_LOG)
        issues = validate_runtime_log(repo_root=repo_root, log_path=log_path, spec_path=spec_path, suite_names=["missing_suite"])
        self.assertEqual(issues, ["Unknown runtime suite 'missing_suite' in runtime_spec.json"])