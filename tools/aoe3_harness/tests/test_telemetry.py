"""Unit tests for tools/aoe3_harness/telemetry.py.

All tests are static — no game, no log files, no external deps.
Run with:
    cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
    python3 -m pytest tools/aoe3_harness/tests/test_telemetry.py -v

Coverage:
    - ProbeEvent dataclass and numeric_value() helper
    - _parse_line() for canonical and alternate key-order formats
    - parse_log_to_trajectories() with synthetic multi-line input
    - emit_html_report() structure sanity check
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repo root is on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aoe3_harness.telemetry import (  # noqa: E402
    ProbeEvent,
    _parse_line,
    emit_html_report,
    parse_log_to_trajectories,
)


# ---------------------------------------------------------------------------
# ProbeEvent
# ---------------------------------------------------------------------------

class TestProbeEvent(unittest.TestCase):
    """Tests for ProbeEvent dataclass and helpers."""

    def test_basic_construction(self) -> None:
        ev = ProbeEvent(tick_ms=1000, probe_name="wall.closure", params={"pct": "0.6"})
        self.assertEqual(ev.tick_ms, 1000)
        self.assertEqual(ev.probe_name, "wall.closure")
        self.assertEqual(ev.params, {"pct": "0.6"})
        self.assertEqual(ev.player, 0)

    def test_numeric_value_named_key(self) -> None:
        ev = ProbeEvent(tick_ms=0, probe_name="wall.closure",
                        params={"pct": "0.6", "radius": "80.0"})
        self.assertAlmostEqual(ev.numeric_value("pct"), 0.6)
        self.assertAlmostEqual(ev.numeric_value("radius"), 80.0)

    def test_numeric_value_auto_first(self) -> None:
        ev = ProbeEvent(tick_ms=0, probe_name="probe",
                        params={"n": "42", "label": "hello"})
        self.assertAlmostEqual(ev.numeric_value(), 42.0)

    def test_numeric_value_none_for_non_numeric(self) -> None:
        ev = ProbeEvent(tick_ms=0, probe_name="probe", params={"label": "abc"})
        self.assertIsNone(ev.numeric_value())

    def test_numeric_value_empty_params(self) -> None:
        ev = ProbeEvent(tick_ms=0, probe_name="probe", params={})
        self.assertIsNone(ev.numeric_value())

    def test_numeric_value_missing_named_key(self) -> None:
        ev = ProbeEvent(tick_ms=0, probe_name="probe", params={"a": "1.0"})
        self.assertIsNone(ev.numeric_value("b"))


# ---------------------------------------------------------------------------
# _parse_line
# ---------------------------------------------------------------------------

class TestParseLine(unittest.TestCase):
    """Tests for the low-level line parser."""

    # The spec example from the task brief
    _SPEC_LINE = "[LLP v=2] tick=12345 player=2 wall.closure pct=0.6 radius=80.0"

    def test_spec_example_tick(self) -> None:
        ev = _parse_line(self._SPEC_LINE)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.tick_ms, 12345)

    def test_spec_example_player(self) -> None:
        ev = _parse_line(self._SPEC_LINE)
        self.assertEqual(ev.player, 2)

    def test_spec_example_probe_name(self) -> None:
        ev = _parse_line(self._SPEC_LINE)
        self.assertEqual(ev.probe_name, "wall.closure")

    def test_spec_example_params_pct(self) -> None:
        ev = _parse_line(self._SPEC_LINE)
        self.assertAlmostEqual(float(ev.params["pct"]), 0.6)

    def test_spec_example_params_radius(self) -> None:
        ev = _parse_line(self._SPEC_LINE)
        self.assertAlmostEqual(float(ev.params["radius"]), 80.0)

    def test_spec_example_raw_stored(self) -> None:
        ev = _parse_line(self._SPEC_LINE)
        self.assertIn("wall.closure", ev.raw)

    def test_no_llp_prefix_returns_none(self) -> None:
        self.assertIsNone(_parse_line("INFO tick=100 some_probe x=1.0"))

    def test_no_player_field(self) -> None:
        line = "[LLP v=2] tick=5000 ai.attack count=3"
        ev = _parse_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.player, 0)
        self.assertEqual(ev.probe_name, "ai.attack")
        self.assertEqual(ev.params.get("count"), "3")

    def test_alternate_player_tick_order(self) -> None:
        line = "[LLP v=2] player=3 tick=9999 econ.idle pct=0.12"
        ev = _parse_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.player, 3)
        self.assertEqual(ev.tick_ms, 9999)
        self.assertEqual(ev.probe_name, "econ.idle")

    def test_zero_tick(self) -> None:
        line = "[LLP v=2] tick=0 player=1 init.start"
        ev = _parse_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.tick_ms, 0)

    def test_no_params(self) -> None:
        line = "[LLP v=2] tick=100 player=1 heartbeat"
        ev = _parse_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.params, {})

    def test_leading_whitespace_and_log_prefix(self) -> None:
        line = "  2026-05-01 12:00:00 [LLP v=2] tick=1000 player=1 wall.ring pct=0.8"
        ev = _parse_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev.tick_ms, 1000)

    def test_malformed_llp_returns_none(self) -> None:
        self.assertIsNone(_parse_line("[LLP v=2] garbage with no tick"))

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(_parse_line(""))


# ---------------------------------------------------------------------------
# parse_log_to_trajectories
# ---------------------------------------------------------------------------

_SAMPLE_LOG = """\
Not a probe line
[LLP v=2] tick=1000 player=1 wall.closure pct=0.5
[LLP v=2] tick=2000 player=1 wall.closure pct=0.7
[LLP v=2] tick=1500 player=2 econ.idle count=2
[LLP v=2] tick=3000 player=1 ai.attack n=5
More noise here
[LLP v=2] tick=500 player=1 wall.closure pct=0.3
"""


class TestParseLogToTrajectories(unittest.TestCase):
    """Tests for the high-level log file parser."""

    def _parse_sample(self) -> dict:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(_SAMPLE_LOG)
            tmp = Path(f.name)
        try:
            return parse_log_to_trajectories(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    def test_two_players_found(self) -> None:
        traj = self._parse_sample()
        self.assertIn("player_1", traj)
        self.assertIn("player_2", traj)

    def test_player1_event_count(self) -> None:
        traj = self._parse_sample()
        # 3 wall.closure + 1 ai.attack = 4 events
        self.assertEqual(len(traj["player_1"]), 4)

    def test_player2_event_count(self) -> None:
        traj = self._parse_sample()
        self.assertEqual(len(traj["player_2"]), 1)

    def test_events_sorted_by_tick(self) -> None:
        traj = self._parse_sample()
        ticks = [ev.tick_ms for ev in traj["player_1"]]
        self.assertEqual(ticks, sorted(ticks))

    def test_civ_map_renames_keys(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("[LLP v=2] tick=100 player=2 probe.x v=1.0\n")
            tmp = Path(f.name)
        try:
            traj = parse_log_to_trajectories(tmp, civ_map={2: "ANWFrench"})
            self.assertIn("ANWFrench", traj)
            self.assertNotIn("player_2", traj)
        finally:
            tmp.unlink(missing_ok=True)

    def test_no_llp_lines_returns_empty(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("nothing here\nsome other log\n")
            tmp = Path(f.name)
        try:
            traj = parse_log_to_trajectories(tmp)
            self.assertEqual(traj, {})
        finally:
            tmp.unlink(missing_ok=True)

    def test_empty_file_returns_empty(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            tmp = Path(f.name)
        try:
            traj = parse_log_to_trajectories(tmp)
            self.assertEqual(traj, {})
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# emit_html_report
# ---------------------------------------------------------------------------

class TestEmitHtmlReport(unittest.TestCase):
    """Structural sanity checks for the HTML renderer."""

    def _make_trajectories(self) -> dict:
        return {
            "player_1": [
                ProbeEvent(tick_ms=100, probe_name="wall.closure",
                           params={"pct": "0.5"}, player=1),
                ProbeEvent(tick_ms=200, probe_name="wall.closure",
                           params={"pct": "0.8"}, player=1),
                ProbeEvent(tick_ms=150, probe_name="ai.attack",
                           params={"count": "3"}, player=1),
            ],
            "player_2": [
                ProbeEvent(tick_ms=120, probe_name="econ.idle",
                           params={"n": "7"}, player=2),
            ],
        }

    def _render_to_temp(self, trajectories: dict) -> tuple[str, Path]:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.html"
            emit_html_report(trajectories, out, source_path="test://synthetic")
            text = out.read_text(encoding="utf-8")
        return text, out

    def test_output_is_html(self) -> None:
        text, _ = self._render_to_temp(self._make_trajectories())
        self.assertIn("<!DOCTYPE html>", text)
        self.assertIn("</html>", text)

    def test_title_present(self) -> None:
        text, _ = self._render_to_temp(self._make_trajectories())
        self.assertIn("ANW Telemetry Report", text)

    def test_player_keys_present(self) -> None:
        text, _ = self._render_to_temp(self._make_trajectories())
        self.assertIn("player_1", text)
        self.assertIn("player_2", text)

    def test_probe_names_present(self) -> None:
        text, _ = self._render_to_temp(self._make_trajectories())
        self.assertIn("wall.closure", text)
        self.assertIn("ai.attack", text)
        self.assertIn("econ.idle", text)

    def test_svg_charts_present(self) -> None:
        text, _ = self._render_to_temp(self._make_trajectories())
        self.assertIn("<svg", text)
        self.assertIn("polyline", text)

    def test_empty_trajectories_produces_valid_html(self) -> None:
        text, _ = self._render_to_temp({})
        self.assertIn("<!DOCTYPE html>", text)
        self.assertIn("No [LLP v=2] probe events", text)

    def test_no_numeric_placeholder_for_string_params(self) -> None:
        traj = {
            "player_1": [
                ProbeEvent(tick_ms=100, probe_name="log.event",
                           params={"label": "hello"}, player=1),
            ]
        }
        text, _ = self._render_to_temp(traj)
        self.assertIn("no numeric param found", text)

    def test_source_path_in_output(self) -> None:
        text, _ = self._render_to_temp(self._make_trajectories())
        self.assertIn("test://synthetic", text)

    def test_creates_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            nested = Path(td) / "a" / "b" / "report.html"
            emit_html_report({}, nested)
            self.assertTrue(nested.exists())

    def test_output_is_self_contained_no_external_refs(self) -> None:
        text, _ = self._render_to_temp(self._make_trajectories())
        # No CDN or external resource references
        self.assertNotIn("cdn.jsdelivr.net", text)
        self.assertNotIn("unpkg.com", text)
        self.assertNotIn("googleapis.com", text)
        self.assertNotIn('src="http', text)


if __name__ == "__main__":
    unittest.main()
