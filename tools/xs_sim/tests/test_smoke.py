"""End-to-end smoke tests. Run with: python3 -m unittest tools.xs_sim.tests.test_smoke"""
import unittest
from pathlib import Path

from tools.xs_sim.lexer import tokenize
from tools.xs_sim.parser import parse
from tools.xs_sim.interpreter import Interpreter
from tools.xs_sim.gamestate import scenario_open_age2

REPO = Path(__file__).resolve().parents[3]


class TestLexer(unittest.TestCase):
    def test_basics(self):
        toks = tokenize("int x = 5; // comment\nfloat y = 3.14;")
        kinds = [t.kind for t in toks if t.kind != "eof"]
        self.assertEqual(kinds, ["kw", "id", "op", "int", "op",
                                 "kw", "id", "op", "float", "op"])

    def test_ternary(self):
        toks = tokenize("a ? 1 : 2")
        ops = [t.value for t in toks if t.kind == "op"]
        self.assertIn("?", ops); self.assertIn(":", ops)


class TestParser(unittest.TestCase):
    def test_rule(self):
        prog = parse("rule r1 inactive minInterval 30 { }")
        self.assertEqual(len(prog.items), 1)
        self.assertEqual(prog.items[0].name, "r1")
        self.assertFalse(prog.items[0].active)
        self.assertEqual(prog.items[0].min_interval, 30)

    def test_c_style_for(self):
        prog = parse("void f() { for (int i = 0; i < 10; i++) { } }")
        # Should parse without error; outer item is FuncDef.
        self.assertEqual(prog.items[0].name, "f")

    def test_switch(self):
        prog = parse("void f() { switch (x) { case 1: break; default: break; } }")
        self.assertEqual(prog.items[0].name, "f")

    def test_ternary_expr(self):
        prog = parse("int g = 1 > 0 ? 5 : 6;")
        self.assertEqual(prog.items[0].name, "g")

    def test_all_leader_files_parse(self):
        leaders = sorted((REPO / "game" / "ai" / "leaders").glob("leader_*.xs"))
        self.assertGreater(len(leaders), 20, "expected ≥20 leader files")
        for f in leaders:
            with self.subTest(leader=f.name):
                parse(f.read_text(), str(f))


class TestInterpreter(unittest.TestCase):
    def test_basic_arith(self):
        i = Interpreter()
        i.load_source("int g = 2 + 3 * 4;")
        self.assertEqual(i.globals["g"], 14)

    def test_function_call(self):
        i = Interpreter()
        i.load_source("int add(int a, int b) { return a + b; } int g = add(2, 5);")
        self.assertEqual(i.globals["g"], 7)

    def test_ternary(self):
        i = Interpreter()
        i.load_source("int g = (1 < 2) ? 10 : 20;")
        self.assertEqual(i.globals["g"], 10)

    def test_rule_fires_at_interval(self):
        i = Interpreter()
        i.load_source(
            "int counter = 0;"
            "rule r active minInterval 5 { counter = counter + 1; }"
        )
        i.run(20.0, dt=1.0)
        # Fires at t=5,10,15,20 (last_fire starts at -inf, so first fire at t=5
        # since dt=1 increments time before evaluating the threshold).
        self.assertGreaterEqual(i.globals["counter"], 3)

    def test_napoleon_init_sets_doctrine(self):
        i = Interpreter()
        i.load_file(REPO / "game" / "ai" / "leaders" / "leader_napoleon.xs")
        i.call_init("initLeaderNapoleon")
        self.assertEqual(i.globals.get("btRushBoom"), 0.1)
        self.assertEqual(i.globals.get("btBiasTrade"), -0.4)   # Continental System
        self.assertTrue(i.globals.get("gNapoleonRulesEnabled"))

    def test_xs_disable_self(self):
        i = Interpreter()
        i.load_source(
            "int counter = 0;"
            "rule r active minInterval 1 { counter = counter + 1; xsDisableSelf(); }"
        )
        i.run(10.0, dt=1.0)
        self.assertEqual(i.globals["counter"], 1)


class TestCompositionStaticScan(unittest.TestCase):
    """The static bias-setter scan added for expects_inf/cav/art verification.

    Validates that _scan_bias_setters and _scan_revolution_bias_setters return
    the MAX across all rules / branches — not just the Age 2 slice — so civs
    with `btBiasArt = -0.1` in Age 2 but `+0.85` in Age 4 still report 0.85.
    """

    def test_named_leader_max_bias(self):
        from tools.xs_sim.compare_doctrine import _scan_bias_setters
        cath = REPO / "game" / "ai" / "leaders" / "leader_catherine.xs"
        biases = _scan_bias_setters(cath.read_text(encoding="utf-8"))
        # Catherine sets btBiasArt = -0.1 in Age 2 but 0.85 in Age 5 — the
        # max-over-all-rules scan should report the positive late-age value.
        self.assertGreaterEqual(biases["Art"], 0.5,
            f"Catherine max btBiasArt should be ≥0.5; got {biases['Art']}")
        # Russians are infantry-heavy → btBiasInf should be at max.
        self.assertGreaterEqual(biases["Inf"], 0.9)

    def test_revolution_block_scan(self):
        from tools.xs_sim.compare_doctrine import _scan_revolution_bias_setters
        # ANWMexicans uses llSetMilitaryFocus(0.75, 0.25, 0.3) — the scanner
        # should pick that up via the _MIL_FOCUS_RE pattern.
        out = _scan_revolution_bias_setters("ANWMexicans")
        self.assertGreaterEqual(out["Inf"], 0.7)
        self.assertGreaterEqual(out["Art"], 0.25)
        # ANWNapoleonicFrance uses llSetMilitaryFocus(0.75, 0.55, 0.55)
        out2 = _scan_revolution_bias_setters("ANWNapoleonicFrance")
        self.assertGreaterEqual(out2["Art"], 0.5)
        self.assertGreaterEqual(out2["Cav"], 0.5)


class TestCompositionCompare(unittest.TestCase):
    """The tightened _composition_compare floor + lead-margin check.

    The compare contract: when a doctrine's spec includes expects_<type>=True,
    the leader file's MAX btBias for that type must be ≥ 0.5 (floor). Below
    the floor, a non-target type may not lead by more than 0.3 (lead-margin).
    """

    def test_meets_floor_passes(self):
        from tools.xs_sim.compare_doctrine import (
            _composition_compare, _COMP_MIN_TARGET,
        )
        # Floor exactly met: target = floor, others above are allowed
        # (combined-arms doctrines).
        p, f, u = _composition_compare(
            {"expects_artillery": True},
            {"Inf": 1.0, "Cav": 0.3, "Art": _COMP_MIN_TARGET},
        )
        self.assertEqual(f, [], f"floor met should not fail: {f}")
        self.assertEqual(u, [], f"floor met should not surface as unknown: {u}")
        self.assertEqual(len(p), 1, "expected one PASS line")

    def test_well_below_floor_with_lead_fails(self):
        from tools.xs_sim.compare_doctrine import _composition_compare
        p, f, u = _composition_compare(
            {"expects_cavalry": True},
            {"Inf": 1.0, "Cav": 0.1, "Art": 0.0},   # 0.1 << 1.0 (Δ=0.9)
        )
        self.assertEqual(len(f), 1, f"expected FAIL line; got fails={f} unknowns={u}")
        self.assertIn("expects_cavalry", f[0])

    def test_below_floor_no_clear_lead_is_unknown(self):
        from tools.xs_sim.compare_doctrine import _composition_compare
        # All three types ≈0.3 — target is below floor but nothing is
        # actually dominating either. Surface as UNKNOWN, not FAIL.
        p, f, u = _composition_compare(
            {"expects_infantry": True},
            {"Inf": 0.3, "Cav": 0.3, "Art": 0.2},
        )
        self.assertEqual(f, [], "no clear winner shouldn't fail")
        self.assertEqual(len(u), 1, f"expected UNKNOWN line; got {u}")
        self.assertIn("weak", u[0].lower())

    def test_no_claim_no_check(self):
        from tools.xs_sim.compare_doctrine import _composition_compare
        # No expects_* claims set → no compositional rows emitted
        p, f, u = _composition_compare({}, {"Inf": 1.0, "Cav": 1.0, "Art": 1.0})
        self.assertEqual((p, f, u), ([], [], []))


class TestChokepointCacheInvalidation(unittest.TestCase):
    """Lock in the cache-key contract for llDetectChokepointVector.

    The chokepoint cache was previously a single global flag — it
    returned the same cached vector forever, even if the AI's main
    base moved to a different area (TC kill+retrain, Asian Wonder
    relocation, revolution re-anchor). The 2026-05-27 fix keys the
    cache on the resolved ``baseAreaID`` so a base-area change forces
    re-detection. This test pins that contract via static-grep against
    the source so the regression can't sneak back in.
    """

    def test_cache_keyed_on_base_area_id(self):
        path = REPO / "game" / "ai" / "core" / "aiBuildingsWalls.xs"
        src = path.read_text(encoding="utf-8")
        # The cache must include a second static variable holding the
        # base-area-id the cached vector was computed against.
        self.assertIn("static int chokepointBaseAreaID", src,
            "expected static int chokepointBaseAreaID alongside the "
            "chokepointCached flag — without it the cache can't tell "
            "when the AI base has moved to a different area")

    def test_cache_hit_guard_checks_base_area(self):
        path = REPO / "game" / "ai" / "core" / "aiBuildingsWalls.xs"
        src = path.read_text(encoding="utf-8")
        # The cache-hit branch must require BOTH cached==1 AND a matching
        # baseAreaID. A pure cached==1 check is the regressed behaviour.
        self.assertIn("chokepointCached == 1) && (chokepointBaseAreaID == baseAreaID", src,
            "expected the cache-hit guard to require both cached==1 "
            "AND chokepointBaseAreaID == baseAreaID")

    def test_invalidation_emits_probe(self):
        path = REPO / "game" / "ai" / "core" / "aiBuildingsWalls.xs"
        src = path.read_text(encoding="utf-8")
        # When the cached entry is stale (base moved), the function must
        # emit a probe line so doctrine validators can correlate
        # base-relocation events with re-detection.
        self.assertIn('llProbe("wall.chokepoint", "invalidated', src,
            "expected wall.chokepoint 'invalidated' probe on cache miss")

    def test_coast_cache_keyed_on_base_area_id(self):
        """The coast-vector cache has the same staleness foot-gun as the
        chokepoint one — a base relocation must invalidate it. Same
        contract: keyed on baseAreaID, with an 'invalidated' probe on miss.
        """
        path = REPO / "game" / "ai" / "core" / "aiBuildingsWalls.xs"
        src = path.read_text(encoding="utf-8")
        self.assertIn("static int coastBaseAreaID", src,
            "expected static int coastBaseAreaID alongside the coastCached flag")
        self.assertIn("coastCached == 1) && (coastBaseAreaID == baseAreaID", src,
            "expected the coast cache-hit guard to require both cached==1 "
            "AND coastBaseAreaID == baseAreaID")
        self.assertIn('llProbe("wall.coast", "invalidated', src,
            "expected wall.coast 'invalidated' probe on cache miss")


if __name__ == "__main__":
    unittest.main()
