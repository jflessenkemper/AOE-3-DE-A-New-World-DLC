"""Tests for tools.playtest.replay_probes — runtime probe validator."""
from __future__ import annotations

import re as _re
import unittest
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.playtest.expectations import load_expectations
from tools.playtest.replay_probes import coverage_report, parse_probes, validate


def _probe(t: int, p: int, civ: str, ldr: str, tag: str, tail: str = "") -> str:
    return f"[ANWP v=2 t={t} p={p} civ={civ} ldr={ldr} tag={tag}] {tail}"


def _civ_token(exp) -> str:
    """Engine-faithful civ token derived from civ_id, not from the
    decorative CIV_LABELS string. ``kbGetCivName()`` emits the prefix-
    stripped civ_id (cCivBritish → British, cCivXPSioux → Sioux); rvlt
    civs arrive as their full ANW* string. Mirroring that here keeps
    test probes parseable as space-separated kv (labels like ``British
    (Elizabeth I)`` would otherwise blow up the kv split)."""
    cid = exp.civ_id
    m = _re.match(r"^cCiv(?:DE|XP)?(.*)$", cid)
    if m:
        return m.group(1)
    return cid


class TestProbeParsing(unittest.TestCase):
    def test_parses_atomic_kv_pairs(self) -> None:
        line = _probe(120, 2, "British", "wellington",
                      "meta.buildstyle",
                      "style=ManorBoom walls=1 terrain_primary=cLLTerrainCoast")
        records = parse_probes(line.encode())
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.player, 2)
        self.assertEqual(r.civ, "British")
        self.assertEqual(r.tag, "meta.buildstyle")
        self.assertEqual(r.fields["walls"], "1")
        self.assertEqual(r.fields["terrain_primary"], "cLLTerrainCoast")

    def test_handles_binary_noise_around_probes(self) -> None:
        # .age3Yrec has binary garbage between chat strings; the regex
        # must still extract LLP lines from inside that.
        blob = (
            b"\x00\x10\xfe junk header bytes "
            + _probe(60, 1, "British", "wellington", "meta.leader_assigned",
                     "civ_id=22 civ_name=British leader=wellington chatset=wellington").encode()
            + b"\xab\xcd more binary "
            + _probe(120, 1, "British", "wellington", "meta.buildstyle",
                     "style=ManorBoom walls=1 terrain_primary=cLLTerrainCoast "
                     "terrain_secondary=cLLTerrainPlain terrain_bias=0.55 "
                     "heading=cLLHeadingAlongCoast heading_bias=0.45 civic_anchor=false").encode()
            + b"\x00\x00 trailing"
        )
        records = parse_probes(blob)
        self.assertEqual(len(records), 2)
        tags = {r.tag for r in records}
        self.assertEqual(tags, {"meta.leader_assigned", "meta.buildstyle"})


class TestValidator(unittest.TestCase):
    def setUp(self) -> None:
        self.expectations = {e.label: e for e in load_expectations()}
        self.british = self.expectations["British (Elizabeth I)"]

    def _good_pair(self, pid: int, exp) -> str:
        return "\n".join([
            _probe(30, pid, _civ_token(exp), exp.leader_key, "meta.leader_init",
                   f"leader={exp.leader_key}"),
            _probe(60, pid, _civ_token(exp), exp.leader_key, "meta.leader_assigned",
                   f"civ_id=0 civ_name={_civ_token(exp)} leader={exp.leader_key} chatset={exp.leader_key}"),
            _probe(120, pid, _civ_token(exp), exp.leader_key, "meta.buildstyle",
                   f"style=Test walls=1 "
                   f"terrain_primary={exp.terrain_primary} "
                   f"terrain_secondary={exp.terrain_secondary} "
                   f"terrain_bias={exp.terrain_strength} "
                   f"heading={exp.heading} "
                   f"heading_bias={exp.heading_strength} "
                   f"civic_anchor=false"),
        ])

    def test_matching_probes_pass(self) -> None:
        text = self._good_pair(1, self.british)
        issues, summary = validate(parse_probes(text.encode()))
        self.assertEqual(issues, [], f"unexpected issues: {issues}")
        self.assertEqual(len(summary), 1)

    def test_leader_mismatch_flagged(self) -> None:
        text = self._good_pair(1, self.british).replace("leader=wellington", "leader=napoleon")
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(any("leader_key mismatch" in i for i in issues), issues)

    def test_unassigned_fallback_flagged(self) -> None:
        text = self._good_pair(1, self.british).replace(
            "leader=wellington", "leader=unassigned-British"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(any("unassigned fallback" in i for i in issues), issues)

    def test_terrain_bias_drift_flagged(self) -> None:
        text = self._good_pair(1, self.british).replace(
            f"terrain_bias={self.british.terrain_strength}",
            "terrain_bias=0.99",
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(any("terrain_bias mismatch" in i for i in issues), issues)

    def test_missing_buildstyle_probe_flagged(self) -> None:
        text = _probe(60, 1, "British", "wellington", "meta.leader_assigned",
                      "civ_id=0 civ_name=British leader=wellington chatset=wellington")
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(any("missing meta.buildstyle" in i for i in issues), issues)

    def test_missing_leader_init_flagged(self) -> None:
        # Drop the meta.leader_init line entirely.
        text = "\n".join(
            line for line in self._good_pair(1, self.british).splitlines()
            if "tag=meta.leader_init" not in line
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("missing meta.leader_init" in i for i in issues), issues
        )

    def test_leader_init_mismatch_flagged(self) -> None:
        # leader_assigned says wellington, leader_init says napoleon.
        text = self._good_pair(1, self.british).replace(
            "tag=meta.leader_init] leader=wellington",
            "tag=meta.leader_init] leader=napoleon",
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("meta.leader_init mismatch" in i for i in issues), issues
        )

    def test_leader_init_accepts_rvlt_prefix(self) -> None:
        # Revolution commander shares one init for many civs — any rvlt_*
        # leader_init key must satisfy the cross-check.
        text = self._good_pair(1, self.british).replace(
            "tag=meta.leader_init] leader=wellington",
            "tag=meta.leader_init] leader=rvlt_ANWBrazil",
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("meta.leader_init mismatch" in i for i in issues), issues
        )

    def test_heartbeat_without_plan_snap_flagged(self) -> None:
        text = self._good_pair(1, self.british) + "\n" + "\n".join(
            _probe(60 * n, 1, "British", "wellington", "telem.heartbeat",
                   f"hb_seq={n}")
            for n in (1, 2, 3)
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("mil.plan_snap never did" in i for i in issues), issues
        )

    def test_heartbeat_with_plan_snap_clean(self) -> None:
        text = self._good_pair(1, self.british) + "\n" + "\n".join([
            _probe(60, 1, "British", "wellington", "telem.heartbeat", "hb_seq=1"),
            _probe(60, 1, "British", "wellington", "mil.plan_snap",
                   "combat=0 attack=0 defend=0"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("mil.plan_snap never did" in i for i in issues), issues
        )


class TestComplianceProbes(unittest.TestCase):
    """Coverage for the compliance.* probe family wired into
    llComplianceSnapshot (every 60s) and llAgeUpProbe (on age change)."""

    def setUp(self) -> None:
        self.expectations = {e.label: e for e in load_expectations()}
        self.british = self.expectations["British (Elizabeth I)"]

    def _good_pair(self, pid: int, exp) -> str:
        return "\n".join([
            _probe(30, pid, _civ_token(exp), exp.leader_key, "meta.leader_init",
                   f"leader={exp.leader_key}"),
            _probe(60, pid, _civ_token(exp), exp.leader_key, "meta.leader_assigned",
                   f"civ_id=0 civ_name={_civ_token(exp)} leader={exp.leader_key} chatset={exp.leader_key}"),
            _probe(120, pid, _civ_token(exp), exp.leader_key, "meta.buildstyle",
                   f"style=Test walls=1 "
                   f"terrain_primary={exp.terrain_primary} "
                   f"terrain_secondary={exp.terrain_secondary} "
                   f"terrain_bias={exp.terrain_strength} "
                   f"heading={exp.heading} "
                   f"heading_bias={exp.heading_strength} "
                   f"civic_anchor=false"),
        ])

    def test_profile_drift_flagged(self) -> None:
        # Two compliance.profile snaps with different terrPrim values =
        # someone mutated the doctrine state mid-match. That's a real bug.
        text = self._good_pair(1, self.british) + "\n" + "\n".join([
            _probe(180, 1, "British", "wellington", "compliance.profile",
                   "style=ManorBoom wallStrat=2 wallLevel=1 earlyWalls=0 "
                   "terrPrim=4 terrSec=2 heading=1 milPlace=-1 "
                   "milDist=1.0 ecoDist=1.0 houseDist=1.0"),
            _probe(240, 1, "British", "wellington", "compliance.profile",
                   "style=ManorBoom wallStrat=2 wallLevel=1 earlyWalls=0 "
                   "terrPrim=9 terrSec=2 heading=1 milPlace=-1 "
                   "milDist=1.0 ecoDist=1.0 houseDist=1.0"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("compliance.profile drift" in i for i in issues), issues
        )

    def test_profile_stable_passes(self) -> None:
        # Two identical compliance.profile snaps = no drift. Should not flag.
        text = self._good_pair(1, self.british) + "\n" + "\n".join([
            _probe(180, 1, "British", "wellington", "compliance.profile",
                   "style=ManorBoom wallStrat=2 wallLevel=1 earlyWalls=0 "
                   "terrPrim=4 terrSec=2 heading=1 milPlace=-1 "
                   "milDist=1.0 ecoDist=1.0 houseDist=1.0"),
            _probe(240, 1, "British", "wellington", "compliance.profile",
                   "style=ManorBoom wallStrat=2 wallLevel=1 earlyWalls=0 "
                   "terrPrim=4 terrSec=2 heading=1 milPlace=-1 "
                   "milDist=1.0 ecoDist=1.0 houseDist=1.0"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("compliance.profile drift" in i for i in issues), issues
        )

    def test_placement_neutral_doctrine_clusters_flagged(self) -> None:
        # expectedPref=-1 (genuine spread) but 8/10 barracks all in front.
        text = self._good_pair(1, self.british) + "\n" + _probe(
            300, 1, "British", "wellington", "compliance.placement",
            "front=8 back=1 left=1 right=0 expectedPref=-1"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("clustered in one quadrant" in i for i in issues), issues
        )

    def test_placement_directional_doctrine_scattered_flagged(self) -> None:
        # Doctrine wants forward muster (pref=0) but barracks evenly split.
        text = self._good_pair(1, self.british) + "\n" + _probe(
            300, 1, "British", "wellington", "compliance.placement",
            "front=1 back=1 left=1 right=1 expectedPref=0"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("evenly scattered" in i for i in issues), issues
        )

    def test_placement_directional_doctrine_concentrated_passes(self) -> None:
        text = self._good_pair(1, self.british) + "\n" + _probe(
            300, 1, "British", "wellington", "compliance.placement",
            "front=4 back=0 left=1 right=0 expectedPref=0"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("evenly scattered" in i for i in issues), issues
        )

    def test_placement_too_few_barracks_no_flag(self) -> None:
        # With only 1 barracks the spread/cluster check is meaningless.
        text = self._good_pair(1, self.british) + "\n" + _probe(
            300, 1, "British", "wellington", "compliance.placement",
            "front=1 back=0 left=0 right=0 expectedPref=-1"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("quadrant" in i or "scattered" in i for i in issues), issues
        )

    def test_terrain_water_bias_violated_flagged(self) -> None:
        # British is Coast/Plain → water_bias=+1. Inland-heavy placement
        # should flag.
        text = self._good_pair(1, self.british) + "\n" + _probe(
            300, 1, "British", "wellington", "compliance.terrain",
            "barracksWaterAdj=1 barracksInland=4 navyVec=(120,0,80)"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("water-bias civ but only" in i for i in issues), issues
        )

    def test_terrain_water_bias_satisfied_passes(self) -> None:
        text = self._good_pair(1, self.british) + "\n" + _probe(
            300, 1, "British", "wellington", "compliance.terrain",
            "barracksWaterAdj=4 barracksInland=1 navyVec=(120,0,80)"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("water-bias civ but only" in i for i in issues), issues
        )


class TestExtendedComplianceProbes(unittest.TestCase):
    """Coverage for the second-wave compliance probes — combat / econ /
    ship / placeAll / wallGeom / diplo / rules — emitted by their
    respective rules at 60–120s ticks."""

    def setUp(self) -> None:
        self.expectations = {e.label: e for e in load_expectations()}
        # Pick a civ whose heading_axis is "outward" for the combat test.
        self.outward = next(
            e for e in self.expectations.values()
            if e.heading_axis == "outward"
        )
        self.british = self.expectations["British (Elizabeth I)"]

    def _good_pair(self, pid: int, exp) -> str:
        return "\n".join([
            _probe(30, pid, _civ_token(exp), exp.leader_key, "meta.leader_init",
                   f"leader={exp.leader_key}"),
            _probe(60, pid, _civ_token(exp), exp.leader_key, "meta.leader_assigned",
                   f"civ_id=0 civ_name={_civ_token(exp)} leader={exp.leader_key} chatset={exp.leader_key}"),
            _probe(120, pid, _civ_token(exp), exp.leader_key, "meta.buildstyle",
                   f"style=Test walls=1 "
                   f"terrain_primary={exp.terrain_primary} "
                   f"terrain_secondary={exp.terrain_secondary} "
                   f"terrain_bias={exp.terrain_strength} "
                   f"heading={exp.heading} "
                   f"heading_bias={exp.heading_strength} "
                   f"civic_anchor=false"),
        ])

    def test_outward_doctrine_no_attacks_flagged(self) -> None:
        # Two combat snaps with attackPlans=0 for an outward-heading civ.
        exp = self.outward
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(180, 1, _civ_token(exp), exp.leader_key, "compliance.combat",
                   "attackPlans=0 defendPlans=0 reservePlans=0 trainPlans=1 "
                   "researchPlans=0 milPop=0 milDelta=0 atkDelta=0 "
                   "hatedEnemy=2 defenseReflex=-1"),
            _probe(240, 1, _civ_token(exp), exp.leader_key, "compliance.combat",
                   "attackPlans=0 defendPlans=0 reservePlans=0 trainPlans=1 "
                   "researchPlans=0 milPop=0 milDelta=0 atkDelta=0 "
                   "hatedEnemy=2 defenseReflex=-1"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("never dispatched a combat plan" in i for i in issues), issues
        )

    def test_persistent_idle_villagers_flagged(self) -> None:
        # 3 econ snaps each with villsIdle=5.
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(60 + 60 * n, 1, _civ_token(exp), exp.leader_key, "compliance.econ",
                   "pctFood=0.5 pctWood=0.3 pctGold=0.2 vills=20 villsIdle=5 "
                   "pop=20 popCap=80 foodValid=2000 woodValid=1500 goldValid=800")
            for n in range(3)
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("plan starvation" in i for i in issues), issues
        )

    def test_idle_villager_spike_not_flagged(self) -> None:
        # 2 ticks idle then back to 0 — should not flag.
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(120, 1, _civ_token(exp), exp.leader_key, "compliance.econ",
                   "pctFood=0.5 pctWood=0.3 pctGold=0.2 vills=20 villsIdle=5 "
                   "pop=20 popCap=80 foodValid=2000 woodValid=1500 goldValid=800"),
            _probe(180, 1, _civ_token(exp), exp.leader_key, "compliance.econ",
                   "pctFood=0.5 pctWood=0.3 pctGold=0.2 vills=20 villsIdle=5 "
                   "pop=20 popCap=80 foodValid=2000 woodValid=1500 goldValid=800"),
            _probe(240, 1, _civ_token(exp), exp.leader_key, "compliance.econ",
                   "pctFood=0.5 pctWood=0.3 pctGold=0.2 vills=20 villsIdle=0 "
                   "pop=20 popCap=80 foodValid=2000 woodValid=1500 goldValid=800"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("plan starvation" in i for i in issues), issues
        )

    def test_mobile_no_walls_with_walls_flagged(self) -> None:
        # strategy=5 (MobileNoWalls) + segments=12 = compliance failure.
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            300, 1, _civ_token(exp), exp.leader_key, "compliance.wallGeom",
            "segments=12 plans=1 minDist=15.0 maxDist=45.0 avgDist=30.0 strategy=5"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("MobileNoWalls doctrine but" in i for i in issues), issues
        )

    def test_mobile_no_walls_with_zero_walls_passes(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            300, 1, _civ_token(exp), exp.leader_key, "compliance.wallGeom",
            "segments=0 plans=0 minDist=0.0 maxDist=0.0 avgDist=0.0 strategy=5"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("MobileNoWalls" in i for i in issues), issues
        )

    def test_disabled_probe_rule_flagged(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            300, 1, _civ_token(exp), exp.leader_key, "compliance.rules",
            "hb=1 planSnap=1 profile=1 combat=0 econ=1 ship=1 "
            "placeDeep=1 wallGeom=1 diplo=1 ageUp=1 wallStall=1"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("'combat' not active" in i for i in issues), issues
        )

    def test_heroes_zero_late_tactics_flagged(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(150_000, 1, _civ_token(exp), exp.leader_key, "compliance.tactics",
                   "treaty=0 treatyEnd=0 bases=2 fwdBase=-1 fwdState=0 "
                   "heroes=0 explorePlans=1"),
            _probe(210_000, 1, _civ_token(exp), exp.leader_key, "compliance.tactics",
                   "treaty=0 treatyEnd=0 bases=2 fwdBase=-1 fwdState=0 "
                   "heroes=0 explorePlans=1"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("heroes=0" in i and "explorer" in i for i in issues), issues
        )

    def test_heroes_present_late_tactics_passes(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(150_000, 1, _civ_token(exp), exp.leader_key, "compliance.tactics",
                   "treaty=0 treatyEnd=0 bases=2 fwdBase=-1 fwdState=0 "
                   "heroes=1 explorePlans=1"),
            _probe(210_000, 1, _civ_token(exp), exp.leader_key, "compliance.tactics",
                   "treaty=0 treatyEnd=0 bases=2 fwdBase=-1 fwdState=0 "
                   "heroes=1 explorePlans=1"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("heroes=0" in i for i in issues), issues
        )

    def test_event_tags_recognized_in_summary(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(60, 1, _civ_token(exp), exp.leader_key, "event.delta",
                   "tposts=1 bases=2 attacks=3 heroes=1 fwdBase=-1"),
            _probe(90, 1, _civ_token(exp), exp.leader_key, "event.combat.defense_reflex",
                   "loc=(100,200) radius=40 baseID=2 atMs=90000"),
        ])
        _, summary = validate(parse_probes(text.encode()))
        joined = "\n".join(summary)
        self.assertIn("delta=1", joined)
        self.assertIn("defRefl=1", joined)


class TestNewEventProbes(unittest.TestCase):
    """Phase-1b additions: every state-mutating mod hook now emits a probe.
    These tests prove the parser, summary, and coverage report recognize
    the new event.* / tech.* tag families."""

    def setUp(self) -> None:
        self.expectations = {e.label: e for e in load_expectations()}
        self.british = self.expectations["British (Elizabeth I)"]

    def _good_pair(self, pid: int, exp) -> str:
        return "\n".join([
            _probe(30, pid, _civ_token(exp), exp.leader_key, "meta.leader_init",
                   f"leader={exp.leader_key}"),
            _probe(60, pid, _civ_token(exp), exp.leader_key, "meta.leader_assigned",
                   f"civ_id=0 civ_name={_civ_token(exp)} leader={exp.leader_key} chatset={exp.leader_key}"),
            _probe(120, pid, _civ_token(exp), exp.leader_key, "meta.buildstyle",
                   f"style=Test walls=1 "
                   f"terrain_primary={exp.terrain_primary} "
                   f"terrain_secondary={exp.terrain_secondary} "
                   f"terrain_bias={exp.terrain_strength} "
                   f"heading={exp.heading} "
                   f"heading_bias={exp.heading_strength} "
                   f"civic_anchor=false"),
        ])

    def test_event_style_applied_parses_clean(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            10, 1, _civ_token(exp), exp.leader_key, "event.style.applied",
            "style=2 wallLevel=2 earlyWalls=true hMul=1.10 eMul=1.30 "
            "mMul=1.0 tcMul=1.25 towerL=2 fortL=2 fwdTowers=1 preferFwd=false"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(any("event.style" in i for i in issues), issues)

    def test_event_personality_applied_parses_clean(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            10, 1, _civ_token(exp), exp.leader_key, "event.personality.applied",
            "kind=balanced rush=0.0 offDef=0.0"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(any("event.personality" in i for i in issues), issues)

    def test_event_elite_retreat_core_parses_clean(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            300, 1, _civ_token(exp), exp.leader_key, "event.elite.retreat_core",
            "anchor=42 radius=36.0 heroes=1 elites=8 loc=(100,200)"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(any("retreat" in i for i in issues), issues)

    def test_event_commander_ransom_parses_clean(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            400, 1, _civ_token(exp), exp.leader_key, "event.commander.ransom_initiated",
            "fallenID=42 tcID=99"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(any("ransom" in i for i in issues), issues)

    def test_event_base_influence_parses_clean(self) -> None:
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + _probe(
            45, 1, _civ_token(exp), exp.leader_key, "event.base.influence",
            "plan=12 base=2 puid=85 centerDist=30.0 influDist=100.0 "
            "influVal=200.0 distMul=1.0 anchor=(150,210)"
        )
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(any("influence" in i for i in issues), issues)


class TestHtmlDoctrineContract(unittest.TestCase):
    """The validator cross-checks runtime probes against
    a_new_world.html doctrine claims (when the HTML promises
    something specific and at least one compliance.* probe fired)."""

    def setUp(self) -> None:
        self.expectations = {e.label: e for e in load_expectations()}
        self.british = self.expectations["British (Elizabeth I)"]
        self.aztecs = self.expectations["Aztecs"]

    def _good_pair(self, pid: int, exp) -> str:
        return "\n".join([
            _probe(30, pid, _civ_token(exp), exp.leader_key, "meta.leader_init",
                   f"leader={exp.leader_key}"),
            _probe(60, pid, _civ_token(exp), exp.leader_key, "meta.leader_assigned",
                   f"civ_id=0 civ_name={_civ_token(exp)} leader={exp.leader_key} chatset={exp.leader_key}"),
            _probe(120, pid, _civ_token(exp), exp.leader_key, "meta.buildstyle",
                   f"style=Test walls=1 "
                   f"terrain_primary={exp.terrain_primary} "
                   f"terrain_secondary={exp.terrain_secondary} "
                   f"terrain_bias={exp.terrain_strength} "
                   f"heading={exp.heading} "
                   f"heading_bias={exp.heading_strength} "
                   f"civic_anchor=false"),
        ])

    def test_aztec_html_promises_mobile_no_walls__violation_flagged(self) -> None:
        # Aztec HTML says "substitutes War Huts and causeways for walls"
        # → expected_wall_strategy = MobileNoWalls (5).
        # Simulate buggy run that emits FortressRing (1) instead.
        exp = self.aztecs
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            # Need a compliance.* probe to trigger the doctrine cross-check.
            _probe(300_000, 1, _civ_token(exp), exp.leader_key, "compliance.wallGeom",
                   "segments=12 plans=1 minDist=15.0 maxDist=45.0 avgDist=30.0 strategy=1"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("HTML promises wall strategy" in i and "Aztecs" in i for i in issues),
            issues,
        )

    def test_aztec_html_match_passes(self) -> None:
        exp = self.aztecs
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(300_000, 1, _civ_token(exp), exp.leader_key, "compliance.wallGeom",
                   "segments=0 plans=0 minDist=0.0 maxDist=0.0 avgDist=0.0 strategy=5"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("HTML promises wall strategy" in i for i in issues), issues,
        )

    def test_british_naval_promise_violation_flagged(self) -> None:
        # British HTML promises naval ("docks first ... fishing fleet").
        # Run with compliance probes but ZERO fleet/ship probes → flagged.
        exp = self.british
        text = self._good_pair(1, exp) + "\n" + "\n".join([
            _probe(60, 1, _civ_token(exp), exp.leader_key, "compliance.placement",
                   "milPlace=0 ts=60"),
        ])
        issues, _ = validate(parse_probes(text.encode()))
        self.assertTrue(
            any("naval doctrine" in i and "British" in i for i in issues),
            issues,
        )

    def test_doctrine_check_skipped_when_no_compliance(self) -> None:
        # Minimal fixture — only meta probes — must NOT trigger the
        # HTML cross-check (match too short / fixture too thin).
        exp = self.british
        text = self._good_pair(1, exp)
        issues, _ = validate(parse_probes(text.encode()))
        self.assertFalse(
            any("HTML promises" in i or "naval doctrine" in i for i in issues),
            issues,
        )


class TestCoverageReport(unittest.TestCase):
    def test_coverage_counts_per_tag(self) -> None:
        text = "\n".join([
            _probe(60, 1, "British", "wellington", "telem.heartbeat", "hb_seq=1"),
            _probe(120, 1, "British", "wellington", "telem.heartbeat", "hb_seq=2"),
            _probe(120, 1, "British", "wellington", "mil.plan_snap", "combat=0"),
        ])
        out = "\n".join(coverage_report(parse_probes(text.encode())))
        self.assertIn("telem.heartbeat", out)
        self.assertIn("mil.plan_snap", out)
        self.assertIn("2", out)  # heartbeat fired twice
        self.assertIn("1", out)  # plan_snap fired once

    def test_coverage_empty_returns_no_lines(self) -> None:
        self.assertEqual(coverage_report([]), [])


class TestNoProbes(unittest.TestCase):
    def test_no_probes_at_all_returns_helpful_error(self) -> None:
        issues, _ = validate(parse_probes(b"no probes in this file"))
        self.assertTrue(any("no [ANWP v=2] probes" in i for i in issues), issues)


if __name__ == "__main__":
    unittest.main()
