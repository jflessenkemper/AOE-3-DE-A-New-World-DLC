#!/usr/bin/env python3
"""Unit tests for the OCR-verified civ-picker selection path.

These tests stub out the parts of lobby_driver that touch the live game
(screenshot, set_civ_by_index, open_civ_picker, cancel_civ_picker) so the
retry loop and OCR-matching helpers can be exercised offline. Run with:

    python3 -m unittest tools/aoe3_automation/test_picker_verified.py
    # or
    python3 tools/aoe3_automation/test_picker_verified.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.aoe3_automation import lobby_driver  # noqa: E402


# Minimal in-memory stand-in for enriched_reference.json — only the fields
# the verifier reads are required.
FAKE_REF = {
    "civs": {
        "ANWBritish": {
            "display_name": "Britain",
            "playstyle_spec": {
                "civ_label": "British",
                "leader_label": "Elizabeth",
            },
        },
        "ANWPortuguese": {
            "display_name": "Portugal",
            "playstyle_spec": {
                "civ_label": "Portuguese",
                "leader_label": "John IV",
            },
        },
        "ANWAztecs": {
            "display_name": "Aztec Empire",
            "playstyle_spec": {
                "civ_label": "Aztecs",
                "leader_label": "Montezuma",
            },
        },
    },
}


class TestNormalisationAndMatching(unittest.TestCase):
    def test_normalise_lowers_and_strips(self):
        self.assertEqual(lobby_driver._normalise_ocr("BRITISH! "), "british")
        self.assertEqual(lobby_driver._normalise_ocr("(Lisbon)"), "lisbon")
        self.assertEqual(lobby_driver._normalise_ocr("Queen Elizabeth I"),
                         "queenelizabethi")
        self.assertEqual(lobby_driver._normalise_ocr(""), "")

    def test_match_civ_by_display_name(self):
        ok, on = lobby_driver._ocr_text_matches_civ(
            "Britain (London)", "ANWBritish", FAKE_REF,
        )
        self.assertTrue(ok)
        # display_name = "Britain" should match
        self.assertIn("Britain", on)

    def test_match_civ_by_civ_label_substring(self):
        # OCR returns "British" — civ_label is "British", display_name is
        # "Britain". Either should hit. We assert at least one match.
        ok, on = lobby_driver._ocr_text_matches_civ(
            "British", "ANWBritish", FAKE_REF,
        )
        self.assertTrue(ok)
        self.assertTrue(on)

    def test_match_civ_by_leader_label(self):
        # OCR returns "Queen Elizabeth I" — should match leader_label
        # "Elizabeth" via substring containment.
        ok, on = lobby_driver._ocr_text_matches_civ(
            "Queen Elizabeth I", "ANWBritish", FAKE_REF,
        )
        self.assertTrue(ok)
        self.assertEqual(on, "Elizabeth")

    def test_match_civ_by_home_city_alias(self):
        # OCR returns just "(LONDON)" — vanilla picker label format.
        # London is mapped to ANWBritish in HOME_CITY_TO_TOKEN.
        ok, on = lobby_driver._ocr_text_matches_civ(
            "(LONDON)", "ANWBritish", FAKE_REF,
        )
        self.assertTrue(ok)
        self.assertEqual(on, "LONDON")

    def test_no_match_for_wrong_civ(self):
        # OCR shows Lisbon but caller asked about ANWBritish — must not match.
        ok, on = lobby_driver._ocr_text_matches_civ(
            "(LISBON)", "ANWBritish", FAKE_REF,
        )
        self.assertFalse(ok)
        self.assertEqual(on, "")

    def test_identify_civ_from_ocr_via_home_city(self):
        # "(LISBON)" → ANWPortuguese
        token = lobby_driver._identify_civ_from_ocr("(LISBON)", FAKE_REF)
        self.assertEqual(token, "ANWPortuguese")

    def test_identify_civ_from_ocr_via_civ_label(self):
        token = lobby_driver._identify_civ_from_ocr(
            "AZTEC EMPIRE (TENOCHTITLAN)", FAKE_REF,
        )
        self.assertEqual(token, "ANWAztecs")

    def test_identify_civ_from_ocr_no_match(self):
        token = lobby_driver._identify_civ_from_ocr("garbledxyz", FAKE_REF)
        self.assertIsNone(token)


class TestSetCivByTokenVerified(unittest.TestCase):
    """Drive set_civ_by_token_verified with mocked I/O so we can assert
    the retry loop behaviour."""

    def setUp(self):
        self.coords = {
            "diff_thresholds": {"noise_floor": 30000,
                                "significant_change": 100000},
            "civ_picker": {"row_y_start": 301, "row_spacing": 64,
                           "row_x_center": 440},
        }

    def _patch_io(self, find_results):
        """Patch the live-I/O entry points so set_civ_by_token_verified can
        run without a live game. ``find_results`` is a list of values for
        successive calls to _find_target_row_in_picker; each entry is either
        an int (row index, indicating success) or None (civ not found).

        2026-05-08 rewrite: also patch ``get_cache_entry`` to return None so
        the fast-path attempt is skipped — the existing tests are exercising
        the OCR-find fallback path. New tests cover the fast path
        separately (see TestFastPathSelection).
        """
        self.find_index = 0

        def fake_find(_coords, _civ_token, _ref, **_kwargs):
            idx = min(self.find_index, len(find_results) - 1)
            self.find_index += 1
            return find_results[idx]

        return [
            mock.patch.object(lobby_driver, "open_civ_picker"),
            mock.patch.object(lobby_driver, "cancel_civ_picker"),
            mock.patch.object(lobby_driver, "click"),
            mock.patch.object(lobby_driver, "confirm_civ_selection"),
            mock.patch.object(lobby_driver, "_find_target_row_in_picker",
                              side_effect=fake_find),
            mock.patch.object(lobby_driver, "get_cache_entry",
                              return_value=None),  # force OCR fallback
            mock.patch("time.sleep"),  # speed up the test
        ]

    def test_first_try_match_returns_ok(self):
        # _find_target_row_in_picker returns row 9 immediately → ok=True.
        with self._make_patches([9]):
            res = lobby_driver.set_civ_by_token_verified(
                self.coords, "ANWBritish", FAKE_REF, max_attempts=8,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["attempts"], 1)
        self.assertEqual(res["matched_on"], "ocr_find")
        self.assertEqual(res["actual_token"], "ANWBritish")

    def test_mismatch_then_match_on_retry(self):
        # Attempt 1: find returns None (civ not visible). Attempt 2: returns 7.
        with self._make_patches([None, 7]):
            res = lobby_driver.set_civ_by_token_verified(
                self.coords, "ANWBritish", FAKE_REF, max_attempts=4,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(res["matched_on"], "ocr_find")

    def test_all_attempts_mismatch_returns_fail(self):
        # Every attempt _find returns None (civ never visible) → ok=False.
        with self._make_patches([None, None, None]):
            res = lobby_driver.set_civ_by_token_verified(
                self.coords, "ANWBritish", FAKE_REF, max_attempts=3,
            )
        self.assertFalse(res["ok"])
        self.assertEqual(res["attempts"], 3)

    def test_unknown_civ_token_still_runs_ocr(self):
        # New behaviour: unknown civ_token doesn't error early — the OCR
        # path tries to find it. If find returns None always → ok=False.
        with self._make_patches([None, None, None]):
            res = lobby_driver.set_civ_by_token_verified(
                self.coords, "ANWNotARealCiv", FAKE_REF, max_attempts=3,
            )
        self.assertFalse(res["ok"])

    # helper -----------------------------------------------------------

    def _make_patches(self, find_results):
        """Context manager that activates all the mocks at once."""
        patches = self._patch_io(find_results)

        class _All:
            def __enter__(_self):
                _self.entered = [p.__enter__() for p in patches]
                return _self.entered

            def __exit__(_self, *args):
                for p in reversed(patches):
                    p.__exit__(*args)

        return _All()


class TestNormalisationCrossCiv(unittest.TestCase):
    """The user explicitly asks: 'Britain' / 'British' / 'Queen Elizabeth I'
    must all match ANWBritish. This is a regression case for the
    matching logic."""

    def test_britain_matches(self):
        ok, _ = lobby_driver._ocr_text_matches_civ(
            "Britain (London)", "ANWBritish", FAKE_REF,
        )
        self.assertTrue(ok)

    def test_british_matches(self):
        ok, _ = lobby_driver._ocr_text_matches_civ(
            "British", "ANWBritish", FAKE_REF,
        )
        self.assertTrue(ok)

    def test_queen_elizabeth_matches(self):
        ok, _ = lobby_driver._ocr_text_matches_civ(
            "Queen Elizabeth I", "ANWBritish", FAKE_REF,
        )
        self.assertTrue(ok)


class TestSetOpponentCivByTokenVerified(unittest.TestCase):
    """Same retry-loop assertions as P1 but on the opponent path. We mock
    set_opponent_civ_by_index, open_opponent_picker, cancel_civ_picker, and
    _ocr_picker_rows so the loop logic is exercised offline."""

    def setUp(self):
        self.coords = {"diff_thresholds": {"noise_floor": 30000,
                                           "significant_change": 100000},
                       "civ_picker": {"row_y_start": 296, "row_spacing": 64}}

    def _patch_io(self, ocr_sequence):
        self.ocr_index = 0

        def fake_ocr_picker_rows(_shot_path, _coords=None):
            idx = min(self.ocr_index, len(ocr_sequence) - 1)
            self.ocr_index += 1
            hi_text, rows = ocr_sequence[idx]
            return [
                {"row": r,
                 "text": (hi_text if r == 5 else (rows[r] if r < len(rows) else "")),
                 "highlighted": (r == 5),
                 "norm": lobby_driver._normalise_ocr(
                     hi_text if r == 5 else (rows[r] if r < len(rows) else "")
                 )}
                for r in range(10)
            ]

        return [
            mock.patch.object(lobby_driver, "set_opponent_civ_by_index"),
            mock.patch.object(lobby_driver, "open_opponent_picker"),
            mock.patch.object(lobby_driver, "cancel_civ_picker"),
            mock.patch.object(lobby_driver, "_shot_lobby",
                              side_effect=lambda p: Path(p)),
            mock.patch.object(lobby_driver, "_ocr_picker_rows",
                              side_effect=fake_ocr_picker_rows),
            # Force OCR-fallback path; fast-path tests live separately.
            mock.patch.object(lobby_driver, "get_cache_entry",
                              return_value=None),
            mock.patch("time.sleep"),
        ]

    def _make_patches(self, ocr_sequence):
        patches = self._patch_io(ocr_sequence)

        class _All:
            def __enter__(_self):
                _self.entered = [p.__enter__() for p in patches]
                return _self.entered

            def __exit__(_self, *args):
                for p in reversed(patches):
                    p.__exit__(*args)

        return _All()

    def test_invalid_slot_returns_fail(self):
        with self._make_patches([("anything", [""] * 10)]):
            r = lobby_driver.set_opponent_civ_by_token_verified(
                self.coords, 0, "ANWBritish", FAKE_REF, max_attempts=2,
            )
        self.assertFalse(r["ok"])
        self.assertIn("opponent slot", r.get("error", ""))

    def test_unknown_civ_returns_fail(self):
        with self._make_patches([("anything", [""] * 10)]):
            r = lobby_driver.set_opponent_civ_by_token_verified(
                self.coords, 1, "ANWNotARealCiv", FAKE_REF, max_attempts=2,
            )
        self.assertFalse(r["ok"])
        self.assertEqual(r["attempts"], 0)
        self.assertIn("unknown", r.get("error", ""))

    def test_first_try_match_returns_ok(self):
        with self._make_patches([
            ("Britain (London)", ["row0"] * 10),
        ]):
            r = lobby_driver.set_opponent_civ_by_token_verified(
                self.coords, 3, "ANWBritish", FAKE_REF, max_attempts=4,
            )
        self.assertTrue(r["ok"])
        self.assertEqual(r["attempts"], 1)
        self.assertEqual(r["slot"], 3)

    def test_mismatch_then_match_on_retry(self):
        with self._make_patches([
            ("(LISBON)", ["row0"] * 10),
            ("(LONDON)", ["row0"] * 10),
        ]):
            r = lobby_driver.set_opponent_civ_by_token_verified(
                self.coords, 2, "ANWBritish", FAKE_REF, max_attempts=4,
            )
        self.assertTrue(r["ok"])
        self.assertEqual(r["attempts"], 2)


class TestSetAnw8CivLobby(unittest.TestCase):
    """End-to-end retry-loop wrapper that drives all 8 slots. Mocks the
    per-slot verifiers to assert the helper aggregates results correctly."""

    def setUp(self):
        self.coords = {"diff_thresholds": {"noise_floor": 30000,
                                           "significant_change": 100000},
                       "civ_picker": {"row_y_start": 296, "row_spacing": 64}}

    def test_requires_exactly_8_civs(self):
        with self.assertRaises(ValueError):
            lobby_driver.set_anw_8civ_lobby(
                self.coords, ["ANWBritish"] * 7, FAKE_REF,
            )

    def test_all_slots_pass(self):
        roster = [
            "ANWBritish", "ANWPortuguese", "ANWAztecs",
            "ANWBritish", "ANWPortuguese", "ANWAztecs",
            "ANWBritish", "ANWPortuguese",
        ]
        with mock.patch.object(
            lobby_driver, "set_civ_by_token_verified",
            return_value={"ok": True, "civ": roster[0], "attempts": 1},
        ), mock.patch.object(
            lobby_driver, "set_opponent_civ_by_token_verified",
            side_effect=lambda c, s, ct, r, max_attempts=8: {
                "ok": True, "civ": ct, "slot": s, "attempts": 1,
            },
        ):
            res = lobby_driver.set_anw_8civ_lobby(self.coords, roster, FAKE_REF)
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["opponents"]), 7)
        self.assertEqual([o["slot"] for o in res["opponents"]], list(range(1, 8)))

    def test_one_opponent_fail_propagates(self):
        roster = ["ANWBritish"] * 8
        opp_returns = [
            {"ok": True, "civ": "ANWBritish", "slot": 1, "attempts": 1},
            {"ok": False, "civ": "ANWBritish", "slot": 2, "attempts": 8,
             "actual_token": "ANWPortuguese"},
        ] + [{"ok": True, "civ": "ANWBritish", "slot": s, "attempts": 1}
             for s in range(3, 8)]
        with mock.patch.object(
            lobby_driver, "set_civ_by_token_verified",
            return_value={"ok": True, "civ": roster[0], "attempts": 1},
        ), mock.patch.object(
            lobby_driver, "set_opponent_civ_by_token_verified",
            side_effect=opp_returns,
        ):
            res = lobby_driver.set_anw_8civ_lobby(self.coords, roster, FAKE_REF)
        self.assertFalse(res["ok"])
        # P1 still ok individually
        self.assertTrue(res["p1"]["ok"])
        # The bad slot is reported
        bad = [o for o in res["opponents"] if not o["ok"]]
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["slot"], 2)


class TestCivOrderCache(unittest.TestCase):
    """The picker_civ_order.json cache + load helpers."""

    def test_derive_cache_has_all_civs(self):
        cache = lobby_driver.derive_civ_order_cache()
        self.assertIn("entries", cache)
        # All 46 ANW civ tokens should resolve except possibly Texas/USA/etc
        # whose alphabetical-table indices may exceed scroll_to_top_idx range.
        # We require >= 40 to catch egregious regressions.
        self.assertGreaterEqual(len(cache["entries"]), 40)
        # Sanity: ANWBritish should map to civ_index 7 (alphabetical "Britain")
        self.assertIn("ANWBritish", cache["entries"])
        self.assertEqual(cache["entries"]["ANWBritish"]["civ_index"], 7)

    def test_get_cache_entry_known_token(self):
        # force-reload to pick up real file. Schema v6 (live-walk) has only
        # scroll_count + click_row + raw_ocr; civ_index from old derived
        # schema is gone (was stale per-profile data anyway).
        lobby_driver.load_civ_order_cache(force_reload=True)
        e = lobby_driver.get_cache_entry("ANWBritish")
        self.assertIsNotNone(e)
        self.assertIn("scroll_count", e)
        self.assertIn("click_row", e)
        self.assertIsInstance(e["scroll_count"], int)
        self.assertIsInstance(e["click_row"], int)

    def test_get_cache_entry_unknown_token_returns_none(self):
        lobby_driver.load_civ_order_cache(force_reload=True)
        self.assertIsNone(lobby_driver.get_cache_entry("ANWNotARealCiv"))


class TestFastPathSelection(unittest.TestCase):
    """set_civ_by_token_fast() — cache-driven, no OCR. Mocks I/O fully."""

    def setUp(self):
        self.coords = lobby_driver.load_coords()

    def _patches(self):
        return [
            mock.patch.object(lobby_driver, "_ensure_window_focus"),
            mock.patch.object(lobby_driver, "click_fast"),
            mock.patch.object(lobby_driver, "scroll_down_fast"),
            mock.patch.object(lobby_driver, "scroll_up_fast"),
            mock.patch.object(lobby_driver, "xdo"),
            # 2026-05-08: _open_picker_for_slot now consults is_picker_open
            # (idempotency guard); mock to False so the click path is exercised.
            mock.patch.object(lobby_driver, "is_picker_open", return_value=False),
            mock.patch("time.sleep"),
        ]

    def _ctx(self, patches):
        class _All:
            def __enter__(_self):
                _self.entered = [p.__enter__() for p in patches]
                return _self.entered
            def __exit__(_self, *args):
                for p in reversed(patches):
                    p.__exit__(*args)
        return _All()

    def test_fast_path_known_civ_p1(self):
        with self._ctx(self._patches()):
            res = lobby_driver.set_civ_by_token_fast(
                self.coords, "ANWBritish", slot=0,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["civ"], "ANWBritish")
        self.assertEqual(res["slot"], 0)
        self.assertEqual(res["method"], "fast")
        self.assertIn("scroll_count", res)
        self.assertIn("click_row", res)

    def test_fast_path_unknown_civ_returns_fail(self):
        with self._ctx(self._patches()):
            res = lobby_driver.set_civ_by_token_fast(
                self.coords, "ANWNotARealCiv", slot=0,
            )
        self.assertFalse(res["ok"])
        self.assertIn("error", res)

    def test_fast_path_opponent_slot(self):
        with self._ctx(self._patches()):
            res = lobby_driver.set_civ_by_token_fast(
                self.coords, "ANWAztecs", slot=3,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["slot"], 3)

    def test_fast_path_invalid_slot_raises_or_fails(self):
        with self._ctx(self._patches()):
            try:
                res = lobby_driver.set_civ_by_token_fast(
                    self.coords, "ANWBritish", slot=99,
                )
                # Either it errored cleanly or raised; both acceptable
                self.assertFalse(res.get("ok", True))
            except (ValueError, IndexError):
                pass  # also acceptable


class TestVerifiedTakesFastPathFirst(unittest.TestCase):
    """When a civ IS in the cache, set_civ_by_token_verified should hit the
    fast path and return on attempt 1 with matched_on='cache'."""

    def setUp(self):
        self.coords = lobby_driver.load_coords()

    def test_p1_verified_uses_cache_when_available(self):
        # Ensure cache is loaded fresh from disk
        lobby_driver.load_civ_order_cache(force_reload=True)
        with mock.patch.object(
            lobby_driver, "set_civ_by_token_fast",
            return_value={"ok": True, "method": "fast",
                          "scroll_count": 3, "click_row": 4,
                          "civ": "ANWBritish", "slot": 0, "elapsed": 1.5},
        ):
            res = lobby_driver.set_civ_by_token_verified(
                self.coords, "ANWBritish", FAKE_REF, max_attempts=4,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["attempts"], 1)
        self.assertEqual(res["matched_on"], "cache")

    def test_opp_verified_uses_cache_when_available(self):
        lobby_driver.load_civ_order_cache(force_reload=True)
        with mock.patch.object(
            lobby_driver, "set_civ_by_token_fast",
            return_value={"ok": True, "method": "fast",
                          "scroll_count": 3, "click_row": 4,
                          "civ": "ANWBritish", "slot": 2, "elapsed": 1.5},
        ):
            res = lobby_driver.set_opponent_civ_by_token_verified(
                self.coords, 2, "ANWBritish", FAKE_REF, max_attempts=4,
            )
        self.assertTrue(res["ok"])
        self.assertEqual(res["attempts"], 1)
        self.assertEqual(res["matched_on"], "cache")
        self.assertEqual(res["slot"], 2)


if __name__ == "__main__":
    unittest.main()
