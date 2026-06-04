"""Unit tests for tools.playtest.coverage_v2.

Each new validator gets:
  - a GREEN path test (probe stream that should produce no errors)
  - a RED path test (probe stream that should produce errors)
"""

from __future__ import annotations

import unittest

from tools.playtest.coverage_v2 import (
    check_leader_escort,
    check_pacing_budget,
    check_shipment_order,
    parse_probes,
    run_all_checks,
    PACING_BUDGET_MS,
    ESCORT_RADIUS_M,
)


# ---------------------------------------------------------------------------
# Helper: build synthetic probe line
# ---------------------------------------------------------------------------

def make_probe(tag: str, t: int = 60000, player: int = 1,
               civ: str = "British", ldr: str = "elizabeth", kv: str = "") -> str:
    return f"[ANWP v=2 t={t} p={player} civ={civ} ldr={ldr} tag={tag}] {kv}"


# ---------------------------------------------------------------------------
# parse_probes
# ---------------------------------------------------------------------------

class TestParseProbes(unittest.TestCase):
    def test_parses_single_probe(self):
        line = make_probe("event.age_up", t=180000, kv="age=2 t=180000")
        probes = parse_probes(line)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].tag, "event.age_up")
        self.assertEqual(probes[0].t, 180000)
        self.assertEqual(probes[0].kv["age"], "2")

    def test_filter_by_prefix(self):
        text = "\n".join([
            make_probe("event.age_up", kv="age=2 t=100"),
            make_probe("mil.escort_check", kv="attack_active=1 leader_dist=5"),
        ])
        probes = parse_probes(text, tag_prefix="event.")
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].tag, "event.age_up")

    def test_no_probes_returns_empty(self):
        self.assertEqual(parse_probes("no probes here"), [])


# ---------------------------------------------------------------------------
# Gap 1: pacing budget
# ---------------------------------------------------------------------------

class TestPacingBudget(unittest.TestCase):
    def _log(self, civ: str, t_ms: int, player: int = 1) -> str:
        return make_probe("event.age_up", t=t_ms, player=player, civ=civ,
                          kv=f"age=2 t={t_ms}")

    # GREEN: ages within budget
    def test_green_british_on_time(self):
        budget = PACING_BUDGET_MS["British"]   # 240 000
        log = self._log("British", budget - 1000)
        self.assertEqual(check_pacing_budget(log), [])

    def test_green_exactly_at_budget(self):
        budget = PACING_BUDGET_MS.get("Dutch", 300_000)
        log = self._log("Dutch", budget)
        self.assertEqual(check_pacing_budget(log), [])

    # RED: ages past budget
    def test_red_british_too_slow(self):
        budget = PACING_BUDGET_MS["British"]   # 240 000
        log = self._log("British", budget + 30_000)
        issues = check_pacing_budget(log)
        self.assertTrue(any("pacing_v2" in i for i in issues))
        self.assertTrue(any("British" in i for i in issues))

    def test_red_unknown_civ_uses_default_budget(self):
        # UnknownCiv should default to 300 000 ms
        log = self._log("UnknownCiv", 400_000)
        issues = check_pacing_budget(log)
        self.assertTrue(issues)

    # Only age=2 probes counted
    def test_age3_probe_ignored(self):
        # age=3 probe at 500 000 ms should NOT trigger pacing budget
        log = make_probe("event.age_up", t=500_000, civ="British",
                         kv="age=3 t=500000")
        self.assertEqual(check_pacing_budget(log), [])

    # Multiple players: each evaluated independently
    def test_two_players_one_late(self):
        budget = PACING_BUDGET_MS["British"]
        log = "\n".join([
            self._log("British", budget - 5000, player=1),
            self._log("British", budget + 60000, player=2),
        ])
        issues = check_pacing_budget(log)
        self.assertEqual(len(issues), 1)
        self.assertIn("p2", issues[0])

    # Only first age-2 probe per player counted
    def test_only_first_age2_probe_counted(self):
        budget = PACING_BUDGET_MS["British"]
        # First probe is on time, second (malformed dupe) would be late
        log = "\n".join([
            self._log("British", budget - 1000, player=1),
            self._log("British", budget + 60000, player=1),
        ])
        self.assertEqual(check_pacing_budget(log), [])


# ---------------------------------------------------------------------------
# Gap 2: shipment order
# ---------------------------------------------------------------------------

class TestShipmentOrder(unittest.TestCase):
    def _ship(self, card: int, tech: int = 1, age: int = 1, player: int = 1) -> str:
        return make_probe("tech.ship", player=player,
                          kv=f"card={card} extended=0 tech={tech} value=1.0 age={age}")

    # GREEN: unique card indices per age
    def test_green_sequential_cards(self):
        log = "\n".join([self._ship(0), self._ship(1), self._ship(2)])
        errors, warnings = check_shipment_order(log)
        self.assertEqual(errors, [])

    # RED: same card index sent twice in same age
    def test_red_duplicate_card_same_age(self):
        log = "\n".join([self._ship(0), self._ship(0)])
        errors, _ = check_shipment_order(log)
        self.assertTrue(errors)

    def test_green_same_index_different_ages(self):
        # Card index 0 in age 1 and then card index 0 in age 2 is valid
        log = "\n".join([self._ship(0, age=1), self._ship(0, age=2)])
        errors, _ = check_shipment_order(log)
        self.assertEqual(errors, [])

    def test_green_no_shipments(self):
        errors, warnings = check_shipment_order("no probes")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_red_multi_player_duplicate_only_one_player(self):
        log = "\n".join([
            self._ship(0, player=1), self._ship(1, player=1),
            self._ship(0, player=2), self._ship(0, player=2),
        ])
        errors, _ = check_shipment_order(log)
        self.assertEqual(len(errors), 1)
        self.assertIn("p2", errors[0])


# ---------------------------------------------------------------------------
# Gap 3: leader escort
# ---------------------------------------------------------------------------

class TestLeaderEscort(unittest.TestCase):
    def _escort(self, dist: float, player: int = 1, civ: str = "British") -> str:
        return make_probe("mil.escort_check", player=player, civ=civ,
                          kv=f"attack_active=1 leader_dist={dist} explorerID=42 attackPlan=7")

    def _no_attack(self, player: int = 1) -> str:
        return make_probe("mil.escort_check", player=player,
                          kv="attack_active=0 leader_dist=50.0 explorerID=42 attackPlan=-1")

    # GREEN: all samples within radius
    def test_green_all_within_radius(self):
        log = "\n".join([self._escort(5.0), self._escort(10.0), self._escort(25.0)])
        self.assertEqual(check_leader_escort(log), [])

    # GREEN: exactly 10% violations (at tolerance boundary)
    def test_green_exactly_at_tolerance(self):
        within = [self._escort(5.0) for _ in range(9)]
        outside = [self._escort(ESCORT_RADIUS_M + 1.0)]
        log = "\n".join(within + outside)
        # 10% violation = exactly at tolerance, should NOT fail
        issues = check_leader_escort(log)
        self.assertEqual(issues, [])

    # RED: >10% violations
    def test_red_too_many_violations(self):
        within = [self._escort(5.0) for _ in range(8)]
        outside = [self._escort(ESCORT_RADIUS_M + 50.0) for _ in range(2)]
        log = "\n".join(within + outside)
        issues = check_leader_escort(log)
        self.assertTrue(issues)
        self.assertIn("escort_v2", issues[0])

    # GREEN: no attack-active samples means no failure
    def test_green_no_attack_active(self):
        log = self._no_attack()
        self.assertEqual(check_leader_escort(log), [])

    # Multiple players: each evaluated independently
    def test_two_players_one_violates(self):
        good = [self._escort(5.0, player=1) for _ in range(10)]
        bad_in = [self._escort(5.0, player=2) for _ in range(8)]
        bad_out = [self._escort(ESCORT_RADIUS_M + 100, player=2) for _ in range(2)]
        log = "\n".join(good + bad_in + bad_out)
        issues = check_leader_escort(log)
        self.assertEqual(len(issues), 1)
        self.assertIn("p2", issues[0])


# ---------------------------------------------------------------------------
# run_all_checks integration
# ---------------------------------------------------------------------------

class TestRunAllChecks(unittest.TestCase):
    def test_clean_log_no_issues(self):
        # A log with no probes at all → no errors, no warnings
        errors, warnings = run_all_checks("nothing here")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_combined_pacing_and_escort_failure(self):
        pacing_late = make_probe(
            "event.age_up", t=400_000, civ="British", kv="age=2 t=400000"
        )
        escort_bad = "\n".join(
            [make_probe("mil.escort_check", kv=f"attack_active=1 leader_dist={ESCORT_RADIUS_M+50} explorerID=1 attackPlan=1")]
            * 20
        )
        log = pacing_late + "\n" + escort_bad
        errors, _ = run_all_checks(log)
        tags = " ".join(errors)
        self.assertIn("pacing_v2", tags)
        self.assertIn("escort_v2", tags)


if __name__ == "__main__":
    unittest.main()
