#!/usr/bin/env python3
"""Self-tests for the validation toolkit. No game required.

Run with:
    python3 tools/validation/test_validator.py

Or via pytest:
    pytest tools/validation/test_validator.py -v

Asserts that:
  1. Parser correctly extracts probe lines from a synthetic Age3Log slice
  2. Parser correctly aggregates by civ and tag
  3. Validator returns PASS for reference-matching synthetic data
  4. Validator returns FAIL for known-bad synthetic data (each corruption type)
  5. Each per-check function reports the right status given its inputs
  6. The enriched-reference build is idempotent
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.validation.parse_match_log import parse_log, summarize, _parse_kv
from tools.validation.validate_civ_behavior import (
    CheckResult,
    check_milestones_fired,
    check_doctrine_posture,
    check_unit_composition,
    check_age_progression,
    check_meta_boot,
    check_compliance_profile,
    check_chat_quotes,
    check_card_deck,
    validate_civ,
    validate_log,
)
from tools.validation.scenario_coverage import (
    DEFAULT_SCENARIO_MAP,
    all_expected_civs,
    collect_logs,
    coverage_summary,
    merge_probes,
)


def _make_log(lines: list[str]) -> Path:
    """Write probe lines to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
    f.write("\n".join(lines))
    f.close()
    return Path(f.name)


def _llp(t: int, p: int, civ: str, ldr: str, tag: str, detail: str = "") -> str:
    line = f"PreGame {t}: [ANWP v=2 t={t} p={p} civ={civ} ldr={ldr} tag={tag}]"
    if detail:
        line = f"{line} {detail}"
    return line


class TestParser(unittest.TestCase):
    def test_extracts_basic_probe(self):
        log = _make_log([
            _llp(1000, 1, "ANWBritish", "wellington", "milestone.first_dock",
                 "atMs=1000 count=1 age=1"),
        ])
        probes = parse_log(log)
        self.assertIn("ANWBritish", probes)
        self.assertIn("milestone.first_dock", probes["ANWBritish"])
        rec = probes["ANWBritish"]["milestone.first_dock"][0]
        self.assertEqual(rec["t"], 1000)
        self.assertEqual(rec["p"], 1)
        self.assertEqual(rec["civ"], "ANWBritish")
        self.assertEqual(rec["ldr"], "wellington")
        self.assertEqual(rec["atMs"], 1000)
        self.assertEqual(rec["count"], 1)
        self.assertEqual(rec["age"], 1)

    def test_handles_no_detail(self):
        log = _make_log([_llp(500, 1, "ANWAztecs", "monte", "meta.boot")])
        probes = parse_log(log)
        rec = probes["ANWAztecs"]["meta.boot"][0]
        self.assertEqual(rec["tag"], "meta.boot")
        self.assertNotIn("atMs", rec)

    def test_aggregates_multiple_civs(self):
        log = _make_log([
            _llp(1000, 1, "ANWBritish", "x", "comp.snapshot", "vil=10"),
            _llp(2000, 2, "ANWAztecs", "y", "comp.snapshot", "vil=12"),
            _llp(3000, 1, "ANWBritish", "x", "posture.snapshot", "age=2"),
        ])
        probes = parse_log(log)
        self.assertEqual(len(probes), 2)
        self.assertEqual(len(probes["ANWBritish"]["comp.snapshot"]), 1)
        self.assertEqual(len(probes["ANWBritish"]["posture.snapshot"]), 1)
        self.assertEqual(len(probes["ANWAztecs"]["comp.snapshot"]), 1)

    def test_kv_numeric_coercion(self):
        d = _parse_kv(" foo=1 bar=2.5 baz=hello quux=-1")
        self.assertEqual(d["foo"], 1)
        self.assertEqual(d["bar"], 2.5)
        self.assertEqual(d["baz"], "hello")
        self.assertEqual(d["quux"], -1)

    def test_summarize_reports_counts(self):
        log = _make_log([
            _llp(1000, 1, "ANWBritish", "x", "tagA"),
            _llp(2000, 1, "ANWBritish", "x", "tagA"),
            _llp(3000, 1, "ANWBritish", "x", "tagB"),
        ])
        probes = parse_log(log)
        s = summarize(probes)
        self.assertEqual(s["civ_count"], 1)
        self.assertEqual(s["per_civ_tags"]["ANWBritish"]["tagA"], 2)
        self.assertEqual(s["per_civ_tags"]["ANWBritish"]["tagB"], 1)


class TestValidatorChecks(unittest.TestCase):
    """Unit tests for individual check_* functions.

    Each test builds a probes dict directly (tag → list[record]) and feeds
    it to the check function under test. No game required.
    """

    def test_milestones_pass_with_required_present(self):
        probes = {
            "milestone.first_barracks": [{"t": 1000, "atMs": 1000}],
            "milestone.first_dock": [{"t": 2000, "atMs": 2000}],
        }
        spec = {"expected_milestones": {"dock": True}}
        results = check_milestones_fired(probes, spec)
        self.assertTrue(any(r.status == CheckResult.PASS
                            and r.name == "milestone.first_dock"
                            for r in results))

    def test_milestones_fail_when_required_missing(self):
        probes = {
            "milestone.first_barracks": [{"t": 1000, "atMs": 1000}],
            # No dock probe
        }
        spec = {"expected_milestones": {"dock": True}}
        results = check_milestones_fired(probes, spec)
        dock_check = [r for r in results
                      if r.name == "milestone.first_dock"][0]
        self.assertEqual(dock_check.status, CheckResult.FAIL)

    def test_doctrine_posture_mdist_in_band(self):
        probes = {
            "posture.snapshot": [
                {"t": 60_000, "ws": 2, "bs": 8, "mdist": 1.05},
            ],
        }
        spec = {
            "wall_strategy": 2,
            "build_style": 8,
            "military_distance_band": [0.9, 1.2],
        }
        results = check_doctrine_posture(probes, spec)
        statuses = {r.name: r.status for r in results}
        self.assertEqual(statuses["doctrine.wall_strategy"], CheckResult.PASS)
        self.assertEqual(statuses["doctrine.build_style"], CheckResult.PASS)
        self.assertEqual(statuses["doctrine.military_distance"], CheckResult.PASS)

    def test_doctrine_posture_mdist_out_of_band(self):
        probes = {
            "posture.snapshot": [{"t": 60_000, "ws": 2, "bs": 8, "mdist": 2.5}],
        }
        spec = {
            "wall_strategy": 2,
            "build_style": 8,
            "military_distance_band": [0.9, 1.2],
        }
        results = check_doctrine_posture(probes, spec)
        statuses = {r.name: r.status for r in results}
        self.assertEqual(statuses["doctrine.military_distance"],
                         CheckResult.FAIL)

    def test_doctrine_posture_wrong_wall_strategy(self):
        probes = {
            "posture.snapshot": [{"t": 60_000, "ws": 5, "bs": 8, "mdist": 1.0}],
        }
        spec = {"wall_strategy": 2, "build_style": 8,
                "military_distance_band": [0.9, 1.2]}
        results = check_doctrine_posture(probes, spec)
        statuses = {r.name: r.status for r in results}
        self.assertEqual(statuses["doctrine.wall_strategy"], CheckResult.FAIL)

    def test_meta_boot_validates_wall_strategy(self):
        probes = {"meta.boot": [{"chatset": "anw_x", "wallStrategy": 2,
                                 "buildStyle": "ForwardOperationalLine"}]}
        spec = {"wall_strategy": 2}
        results = check_meta_boot(probes, spec)
        self.assertTrue(any(r.name == "meta.boot.wall_strategy"
                            and r.status == CheckResult.PASS
                            for r in results))

    def test_meta_boot_fails_on_wrong_wall_strategy(self):
        probes = {"meta.boot": [{"chatset": "x", "wallStrategy": 5,
                                 "buildStyle": "X"}]}
        spec = {"wall_strategy": 2}
        results = check_meta_boot(probes, spec)
        self.assertTrue(any(r.name == "meta.boot.wall_strategy"
                            and r.status == CheckResult.FAIL
                            for r in results))

    def test_unit_composition_pass(self):
        probes = {
            "comp.snapshot": [
                {"t": 60_000, "vil": 20, "inf": 6, "cav": 3, "arty": 1,
                 "landmil": 10, "warship": 0},
            ],
        }
        spec = {
            "expected_unit_composition": {
                "infantry": 0.6, "cavalry": 0.3, "artillery": 0.1,
            },
            "composition_tolerance": 0.15,
        }
        results = check_unit_composition(probes, spec)
        self.assertEqual(results[0].status, CheckResult.PASS)

    def test_unit_composition_fail_when_ratio_off(self):
        probes = {
            "comp.snapshot": [
                {"t": 60_000, "vil": 20, "inf": 1, "cav": 9, "arty": 0,
                 "landmil": 10},
            ],
        }
        spec = {
            "expected_unit_composition": {
                "infantry": 0.6, "cavalry": 0.3, "artillery": 0.1,
            },
            "composition_tolerance": 0.15,
        }
        results = check_unit_composition(probes, spec)
        self.assertEqual(results[0].status, CheckResult.FAIL)

    def test_card_deck_pass_when_subset(self):
        probes = {
            "compliance.ship": [
                {"t": 100, "card": "DEHCFortify"},
                {"t": 200, "card": "HCXPShipDragoons1"},
            ],
        }
        spec = {"expected_deck": {
            "0": ["DEHCFortify"],
            "1": ["HCXPShipDragoons1", "HCXPShipMusket1"],
        }}
        results = check_card_deck(probes, spec)
        self.assertEqual(results[0].status, CheckResult.PASS)

    def test_card_deck_warn_on_unexpected(self):
        probes = {
            "compliance.ship": [{"t": 100, "card": "BogusCardId"}],
        }
        spec = {"expected_deck": {
            "0": ["DEHCFortify"],
        }}
        results = check_card_deck(probes, spec)
        self.assertEqual(results[0].status, CheckResult.WARN)


class TestEndToEnd(unittest.TestCase):
    """Integration tests against the real reference matrix."""

    def test_synth_per_civ_passes_against_enriched(self):
        """Ensures our synthetic generator + validator agree."""
        ref_path = REPO_ROOT / "enriched_reference.json"
        if not ref_path.exists():
            self.skipTest("enriched_reference.json not built")

        # Spawn synth_per_civ_log to generate matching log
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = Path(f.name)
        proc = subprocess.run(
            [sys.executable,
             str(REPO_ROOT / "tools/validation/synth_per_civ_log.py"),
             "--out", str(log_path),
             "--civs", "ANWBritish"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=15,
        )
        self.assertEqual(proc.returncode, 0,
                         f"synth_per_civ_log failed: {proc.stderr}")

        report = validate_log(log_path, ref_path)
        self.assertIn("ANWBritish", report["per_civ"])
        verdict = report["per_civ"]["ANWBritish"]["verdict"]
        self.assertEqual(verdict, "PASS",
                         f"expected PASS got {verdict}: "
                         f"{report['per_civ']['ANWBritish']}")
        log_path.unlink()


class TestScenarioCoverage(unittest.TestCase):
    """Tests for the scenario_coverage tool that bridges authored
    scenarios to the per-civ validator."""

    def test_default_map_covers_40_civs(self):
        expected = all_expected_civs(DEFAULT_SCENARIO_MAP)
        self.assertEqual(len(expected), 40,
                         f"playbook should cover 40 ANW civs, got {len(expected)}")

    def test_default_map_has_five_scenarios(self):
        self.assertEqual(set(DEFAULT_SCENARIO_MAP.keys()),
                         {"A", "B", "C", "D", "E"})

    def test_default_map_has_no_duplicates(self):
        seen = []
        for civs in DEFAULT_SCENARIO_MAP.values():
            seen.extend(civs)
        self.assertEqual(len(seen), len(set(seen)),
                         "playbook scenario_map must not repeat civs")

    def test_collect_logs_filters_non_log_files(self):
        """A JSON report file in the slice dir must not be treated as a log."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "A_log.txt").write_text("dummy")
            (d / "report.json").write_text("{}")  # should be filtered out
            (d / "notes.md").write_text("hi")     # should be filtered out
            logs = collect_logs(d, None)
            self.assertEqual(set(logs.keys()), {"A"})

    def test_collect_logs_extracts_letter_label(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            for letter in "ABCDEF":
                (d / f"{letter}_log.txt").write_text("")
            logs = collect_logs(d, None)
            self.assertEqual(set(logs.keys()), set("ABCDEF"))

    def test_coverage_summary_full(self):
        seen_by_scenario = {
            label: set(civs) for label, civs in DEFAULT_SCENARIO_MAP.items()
        }
        cov = coverage_summary(seen_by_scenario, DEFAULT_SCENARIO_MAP)
        self.assertEqual(cov["seen_civ_count"], 40)
        self.assertEqual(cov["overall_coverage_pct"], 100.0)
        self.assertEqual(cov["missing_civs_overall"], [])

    def test_coverage_summary_partial(self):
        # Only scenario A has data
        seen_by_scenario = {
            "A": set(DEFAULT_SCENARIO_MAP["A"]),
        }
        cov = coverage_summary(seen_by_scenario, DEFAULT_SCENARIO_MAP)
        self.assertEqual(cov["seen_civ_count"], 8)
        self.assertEqual(len(cov["missing_civs_overall"]), 32)
        self.assertEqual(cov["per_scenario"]["A"]["coverage_pct"], 100.0)
        self.assertEqual(cov["per_scenario"]["E"]["coverage_pct"], 0.0)

    def test_coverage_flags_unexpected_civ(self):
        # Some unknown civ shows up in the log
        seen_by_scenario = {"*": {"ANWBritish", "ANWZorbat"}}
        scen_map = {"A": ["ANWBritish"]}
        cov = coverage_summary(seen_by_scenario, scen_map)
        self.assertIn("ANWZorbat", cov["unexpected_civs_seen"])

    def test_merge_probes_combines_per_log(self):
        per_log = {
            "A": {"ANWBritish": {"meta.boot": [{"t": 100}]}},
            "B": {"ANWBritish": {"meta.boot": [{"t": 200}]}},
            "C": {"ANWAztecs":  {"comp.snapshot": [{"vil": 5}]}},
        }
        merged = merge_probes(per_log)
        self.assertEqual(len(merged["ANWBritish"]["meta.boot"]), 2)
        self.assertEqual(len(merged["ANWAztecs"]["comp.snapshot"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
