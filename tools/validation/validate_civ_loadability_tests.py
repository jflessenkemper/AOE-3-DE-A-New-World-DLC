#!/usr/bin/env python3
"""Tests for validate_civ_loadability.py."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.validation.validate_civ_loadability import (  # noqa: E402
    classify_statsid,
    is_base_game_format_statsid,
    load_anw_civs_from_civmods,
    diff_civs_against_cache,
)


class TestStatsIDClassification(unittest.TestCase):
    def test_base_game_format(self):
        for sid in ["AZ", "CH", "FR", "US", "BR", "JP", "PT"]:
            self.assertEqual(classify_statsid(sid), "BASE_GAME_FORMAT")
            self.assertTrue(is_base_game_format_statsid(sid))

    def test_digit_prefix_new(self):
        for sid in ["1A", "1F", "1R", "1Y"]:
            self.assertEqual(classify_statsid(sid), "DIGIT_PREFIX_NEW")
            self.assertFalse(is_base_game_format_statsid(sid))

    def test_other(self):
        for sid in ["XYZ", "abc", "2A", "AAA", "1"]:
            self.assertEqual(classify_statsid(sid), "OTHER")
            self.assertFalse(is_base_game_format_statsid(sid))

    def test_empty(self):
        self.assertEqual(classify_statsid(""), "EMPTY")
        self.assertFalse(is_base_game_format_statsid(""))


class TestLoadFromCivmods(unittest.TestCase):
    def test_loads_anw_civs_only(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "civmods.xml"
            p.write_text("""<?xml version='1.0'?>
<civmods>
  <civ>
    <name>Spanish</name>
    <statsid>SP</statsid>
    <displaynameid>40050</displaynameid>
  </civ>
  <civ>
    <name>ANWBritish</name>
    <statsid>1E</statsid>
    <displaynameid>490100</displaynameid>
  </civ>
  <civ>
    <name>ANWAztecs</name>
    <statsid>AZ</statsid>
    <displaynameid>410000</displaynameid>
  </civ>
</civmods>""")
            civs = load_anw_civs_from_civmods(p)
            self.assertEqual(len(civs), 2)
            tokens = {c["token"] for c in civs}
            self.assertEqual(tokens, {"ANWBritish", "ANWAztecs"})

    def test_classifies_each_civ(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "civmods.xml"
            p.write_text("""<?xml version='1.0'?>
<civmods>
  <civ><name>ANWA</name><statsid>AZ</statsid><displaynameid>1</displaynameid></civ>
  <civ><name>ANWB</name><statsid>1B</statsid><displaynameid>2</displaynameid></civ>
</civmods>""")
            civs = load_anw_civs_from_civmods(p)
            by_tok = {c["token"]: c for c in civs}
            self.assertEqual(by_tok["ANWA"]["statsid_class"], "BASE_GAME_FORMAT")
            self.assertEqual(by_tok["ANWB"]["statsid_class"], "DIGIT_PREFIX_NEW")


class TestDiffAgainstCache(unittest.TestCase):
    def setUp(self):
        self.civs = [
            {"token": "ANWAztecs", "statsid": "AZ",
             "statsid_class": "BASE_GAME_FORMAT", "display_name_id": "410000"},
            {"token": "ANWBritish", "statsid": "1E",
             "statsid_class": "DIGIT_PREFIX_NEW", "display_name_id": "490100"},
            {"token": "ANWFinnish", "statsid": "SW",
             "statsid_class": "BASE_GAME_FORMAT", "display_name_id": "410020"},
        ]

    def test_digit_prefix_always_fails(self):
        # ANWBritish (1E) — even if cache claims it's there, FAIL.
        # The cache may have been built by fuzzy OCR matchers that
        # over-attributed base-game rows to ANW tokens.
        cache = {"entries": {"ANWAztecs": {}, "ANWBritish": {},
                              "ANWFinnish": {}}}
        report = diff_civs_against_cache(self.civs, cache)
        self.assertEqual(report["counts"]["FAIL"], 1)
        fails = [r for r in report["results"] if r["verdict"] == "FAIL"]
        self.assertEqual(fails[0]["token"], "ANWBritish")
        self.assertIn("digit-prefix", fails[0]["why"])

    def test_base_format_in_cache_passes(self):
        cache = {"entries": {"ANWAztecs": {}, "ANWFinnish": {}}}
        report = diff_civs_against_cache(self.civs, cache)
        passes = [r for r in report["results"] if r["verdict"] == "PASS"]
        self.assertEqual({p["token"] for p in passes},
                         {"ANWAztecs", "ANWFinnish"})

    def test_base_format_missing_warns(self):
        # ANWAztecs (AZ) missing → WARN (probably stale cache, not real bug)
        cache = {"entries": {"ANWFinnish": {}}}
        report = diff_civs_against_cache(self.civs, cache)
        self.assertEqual(report["counts"]["WARN"], 1)
        warns = [r for r in report["results"] if r["verdict"] == "WARN"]
        self.assertEqual(warns[0]["token"], "ANWAztecs")
        self.assertIn("stale", warns[0]["why"])

    def test_empty_cache(self):
        report = diff_civs_against_cache(self.civs, {"entries": {}})
        # 2 BASE_GAME_FORMAT → WARN, 1 DIGIT_PREFIX_NEW → FAIL
        self.assertEqual(report["counts"]["WARN"], 2)
        self.assertEqual(report["counts"]["FAIL"], 1)
        self.assertEqual(report["counts"]["PASS"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
