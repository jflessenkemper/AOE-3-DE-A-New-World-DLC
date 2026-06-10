#!/usr/bin/env python3
"""Unit tests for the wall-closure section of validate_doctrine_compliance.

Synthesises [ANWP v=2 …] probe lines covering three scenarios:
  • PASS path  — closure climbs past 0.6 by the time the AI hits Age 3
  • FAIL path  — closure stays under 0.4 even after multiple emissions
  • SKIP path  — MobileNoWalls (wall_strategy=5) civ emits zero wall.closure

Test invocation:
    python3 -m unittest tools.validation.test_wall_closure_parser -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.validation.validate_doctrine_compliance import (
    WALL_FAIL,
    WALL_PASS,
    WALL_SKIP,
    evaluate_wall_closure,
    parse_probes,
)


# ─── synthetic log helpers ─────────────────────────────────────────────────


def _probe_line(t: int, civ: str, ldr: str, tag: str, kv: str) -> str:
    """Render a single canonical probe line matching aiUtilities.xs:llProbe."""
    return f"[ANWP v=2 t={t} p=1 civ={civ} ldr={ldr} tag={tag}] {kv}\n"


def _make_synthetic_log() -> str:
    """Two AIs, one PASS one FAIL.

    • British (wellington) — closure climbs 0.20 → 0.55 → 0.72 across ages 1→3
    • Lakota (crazyhorse)  — closure stuck at 0.15 across ages 1→3
    """
    lines: list[str] = []

    # British — posture snapshots mark the age boundaries. Closure jumps
    # past 0.6 *before* age3 crossing so closure_by_age3 lands in PASS.
    lines.append(_probe_line(30_000,  "British", "wellington",
                             "posture.snapshot", "ageMs=30000 age=1 ws=2 bs=1"))
    lines.append(_probe_line(60_000,  "British", "wellington",
                             "wall.closure", "expected=20 actual=4 closure=0.20 age=1"))
    lines.append(_probe_line(240_000, "British", "wellington",
                             "posture.snapshot", "ageMs=240000 age=2 ws=2 bs=1"))
    lines.append(_probe_line(300_000, "British", "wellington",
                             "wall.closure", "expected=20 actual=11 closure=0.55 age=2"))
    lines.append(_probe_line(420_000, "British", "wellington",
                             "wall.closure", "expected=20 actual=14 closure=0.70 age=2"))
    lines.append(_probe_line(480_000, "British", "wellington",
                             "posture.snapshot", "ageMs=480000 age=3 ws=2 bs=1"))
    lines.append(_probe_line(540_000, "British", "wellington",
                             "wall.closure", "expected=20 actual=15 closure=0.75 age=3"))
    # Corrective-mechanism probes — should be counted but don't gate verdict
    lines.append(_probe_line(300_000, "British", "wellington",
                             "wall.chokepoint", "vec=12,34 tiles=8 cached=1"))
    lines.append(_probe_line(450_000, "British", "wellington",
                             "wall.water_fix",
                             "orig=10,20 final=12,20 steps=2"))

    # Lakota — closure-stuck FAIL path
    lines.append(_probe_line(60_000,  "Lakota", "crazyhorse",
                             "posture.snapshot", "ageMs=60000 age=1 ws=1 bs=1"))
    lines.append(_probe_line(120_000, "Lakota", "crazyhorse",
                             "wall.closure", "expected=10 actual=1 closure=0.10 age=1"))
    lines.append(_probe_line(360_000, "Lakota", "crazyhorse",
                             "posture.snapshot", "ageMs=360000 age=2 ws=1 bs=1"))
    lines.append(_probe_line(420_000, "Lakota", "crazyhorse",
                             "wall.closure", "expected=10 actual=1 closure=0.10 age=2"))
    lines.append(_probe_line(600_000, "Lakota", "crazyhorse",
                             "posture.snapshot", "ageMs=600000 age=3 ws=1 bs=1"))
    lines.append(_probe_line(660_000, "Lakota", "crazyhorse",
                             "wall.closure", "expected=10 actual=2 closure=0.15 age=3"))
    lines.append(_probe_line(720_000, "Lakota", "crazyhorse",
                             "wall.escalate", "plan=hard closure=0.15"))
    lines.append(_probe_line(780_000, "Lakota", "crazyhorse",
                             "wall.reemit", "closure=0.15"))

    return "".join(lines)


def _write_log_to_tempfile(text: str) -> Path:
    fd, path = tempfile.mkstemp(prefix="wall_closure_test_", suffix=".log")
    os.close(fd)
    p = Path(path)
    p.write_text(text, encoding="utf-8")
    return p


# ─── tests ─────────────────────────────────────────────────────────────────


class WallClosureParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.log_path = _write_log_to_tempfile(_make_synthetic_log())
        # 2026-05-14: parse_probes now returns (probes, plan_closures) — was
        # a flat list when this test was first written. Unpack here so the
        # rest of the test body sees a list of Probe objects.
        # 2026-06-09: parse_probes now returns a 3-tuple
        # (probes, plan_closures, flat_closures); discard flat_closures.
        cls.probes, cls.plan_closures, _flat_closures = parse_probes([cls.log_path])

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.log_path.unlink()
        except OSError:
            pass

    def _probes_for(self, civ: str) -> list:
        return [p for p in self.probes if p.civ == civ]

    # PASS path — British reach closure ≥ 0.6 mid-game.
    def test_pass_path_for_closure_reaching_civ(self) -> None:
        british = self._probes_for("British")
        self.assertTrue(british, "synthetic log should produce British probes")
        summary = evaluate_wall_closure(
            "British Elizabeth", {"wall_strategy": 2}, british)

        self.assertEqual(summary.verdict, WALL_PASS)
        self.assertAlmostEqual(summary.final_closure, 0.75, places=2)
        # closure_by_age3 picks the t=420000 reading (0.70) which is the
        # most recent at-or-before the age3 crossing at t=480000.
        self.assertAlmostEqual(summary.closure_by_age3, 0.70, places=2)
        # 0.20 is the last reading at-or-before age2 crossing at t=240000
        self.assertAlmostEqual(summary.closure_by_age2, 0.20, places=2,
            msg="closure_by_age2 should be the reading at-or-before the "
                "first posture.snapshot with age >= 2")
        # time_to_60pct_ms — first probe with closure >= 0.6 was at t=420000
        self.assertEqual(summary.time_to_60pct_ms, 420_000)
        # Corrective probes are surfaced as counts
        self.assertEqual(summary.chokepoint_count, 1)
        self.assertEqual(summary.water_fix_count, 1)
        self.assertEqual(summary.escalate_count, 0)
        self.assertEqual(summary.reemit_count, 0)
        self.assertEqual(summary.closure_probe_count, 4)

    # FAIL path — Lakota stay under 0.4 throughout.
    def test_fail_path_for_closure_stuck_civ(self) -> None:
        lakota = self._probes_for("Lakota")
        self.assertTrue(lakota, "synthetic log should produce Lakota probes")
        summary = evaluate_wall_closure(
            "Lakota Gall", {"wall_strategy": 3}, lakota)

        self.assertEqual(summary.verdict, WALL_FAIL)
        self.assertAlmostEqual(summary.final_closure, 0.15, places=2)
        # closure_by_age3 = most recent reading at-or-before age3 crossing
        # (t=600_000) — that's the t=420_000 probe at 0.10, not the
        # t=660_000 probe at 0.15 (which is *after* age3).
        self.assertAlmostEqual(summary.closure_by_age3, 0.10, places=2)
        # Never crosses 0.6 → no time_to_60pct
        self.assertIsNone(summary.time_to_60pct_ms)
        # Escalate + reemit corrective mechanisms fired
        self.assertEqual(summary.escalate_count, 1)
        self.assertEqual(summary.reemit_count, 1)

    # SKIP path — MobileNoWalls civ with zero wall.closure probes.
    def test_skip_path_for_mobile_no_walls(self) -> None:
        # Construct a probe stream with no wall.closure tags at all —
        # only posture snapshots, mimicking a strategy=5 civ.
        synthetic = "".join([
            _probe_line(60_000,  "Argentines", "sanmartin",
                        "posture.snapshot", "ageMs=60000 age=1 ws=5 bs=1"),
            _probe_line(360_000, "Argentines", "sanmartin",
                        "posture.snapshot", "ageMs=360000 age=2 ws=5 bs=1"),
            _probe_line(600_000, "Argentines", "sanmartin",
                        "posture.snapshot", "ageMs=600000 age=3 ws=5 bs=1"),
        ])
        log = _write_log_to_tempfile(synthetic)
        try:
            probes, _plan_closures, _flat_closures = parse_probes([log])
            summary = evaluate_wall_closure(
                "Argentines San Martin Revolution",
                {"wall_strategy": 5},
                probes)
            self.assertEqual(summary.verdict, WALL_SKIP)
            self.assertIsNone(summary.final_closure)
            self.assertEqual(summary.closure_probe_count, 0)
        finally:
            try:
                log.unlink()
            except OSError:
                pass

    # INCOMPLETE path — non-MobileNoWalls civ with zero wall.closure probes.
    def test_incomplete_path_when_probes_missing_for_walling_civ(self) -> None:
        synthetic = _probe_line(60_000, "British", "wellington",
                                "posture.snapshot",
                                "ageMs=60000 age=1 ws=2 bs=1")
        log = _write_log_to_tempfile(synthetic)
        try:
            probes, _plan_closures, _flat_closures = parse_probes([log])
            summary = evaluate_wall_closure(
                "British Elizabeth", {"wall_strategy": 2}, probes)
            self.assertEqual(summary.verdict, "INCOMPLETE")
        finally:
            try:
                log.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
