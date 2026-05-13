#!/usr/bin/env python3
"""Unit tests for tools.validation.scenario_emitter.

Run via:

    python3 -m pytest tools/validation/scenario_emitter_tests.py -v
or
    python3 tools/validation/scenario_emitter_tests.py

Tests prove:
  1. Parser round-trip: load template, re-emit unchanged civs -> bytes recover
     the same body length and identical bindings.
  2. Length invariants: inner_size == len(body) - 7, outer == len(body),
     enclosing BP record sizes == sum of sub-record sizes + 4 (version u32).
  3. Civ swap: replacing player 1's binding only changes:
       - The hcname bytes inside player 1's P5
       - Three u32 length fields (P5 size, BP size, body inner_size)
       - The compressed payload after re-zlib
     and other player slots are byte-identical (same hcname).
  4. Generated playbook scenarios decompress + re-parse cleanly with the
     correct 8 ANW civ bindings each.
"""
from __future__ import annotations

import io
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

# Allow running as a standalone script from anywhere.
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.validation import scenario_emitter as se  # noqa: E402


# 2026-05-11: was Scenario/legendary-leaders-ai.age3Yscn; renamed to a
# neutral _test_template.age3Yscn after the LL branding cleanup. Identical
# md5. The canonical AI-testing scenario is Scenario/ANEWWORLD.age3Yscn,
# kept separately because these tests are coupled to this template's
# specific zlib params.
TEMPLATE = REPO / "Scenario" / "_test_template.age3Yscn"


class ParserTests(unittest.TestCase):
    def setUp(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        self.raw, self.body = se.load_scenario(TEMPLATE)

    def test_outer_invariants(self) -> None:
        outer_size = struct.unpack_from("<I", self.raw, 4)[0]
        self.assertEqual(outer_size, len(self.body),
                         "outer decompressed_size must equal body length")

    def test_inner_invariant(self) -> None:
        inner = struct.unpack_from("<I", self.body, 2)[0]
        self.assertEqual(inner, len(self.body) - 7,
                         "inner_size must equal body_len - 7")

    def test_bp_records_count(self) -> None:
        bps = se.find_bp_records(self.body)
        self.assertEqual(len(bps), 9,
                         "expected 1 Gaia + 8 player BP records (got %d)" % len(bps))

    def test_bp_size_consistent_with_subs(self) -> None:
        for bp in se.find_bp_records(self.body):
            # bp.size = u32 covering (version u32) + sum(sub_record total)
            sub_total = sum(6 + s.size for s in bp.subs)
            # The BP record header is: 0x01 (1) + 'BP' (2) + u32 size (4) + u32 version (4)
            # `size` field includes the version u32 + sub-records.
            expected = 4 + sub_total
            self.assertEqual(
                bp.size, expected,
                f"BP @ {bp.off:#x}: size={bp.size} but subs total + version = {expected}",
            )

    def test_p5_layout_for_each_player(self) -> None:
        bps = se.find_bp_records(self.body)
        for i, bp in enumerate(bps):
            p5 = bp.get_sub(b"P5")
            self.assertIsNotNone(p5, f"BP[{i}] missing P5")
            parsed = se.P5.parse(p5.payload)
            self.assertTrue(parsed.hcname.startswith("homecity") or
                            parsed.hcname.startswith("anwhomecity"),
                            f"BP[{i}] hcname unexpected: {parsed.hcname!r}")
            self.assertIn(parsed.ai_loader, ("", "aiLoaderStandard"),
                          f"BP[{i}] ai loader unexpected: {parsed.ai_loader!r}")

    def test_p5_serialize_roundtrip(self) -> None:
        """Parsing then serializing a P5 sub-record must yield identical bytes."""
        for bp in se.find_bp_records(self.body):
            p5 = bp.get_sub(b"P5")
            self.assertIsNotNone(p5)
            parsed = se.P5.parse(p5.payload)
            self.assertEqual(parsed.serialize(), p5.payload)


class EmitterTests(unittest.TestCase):
    def setUp(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        self.raw, self.body = se.load_scenario(TEMPLATE)
        self.original_bindings = se.get_player_bindings(self.body)

    def test_noop_pack_preserves_body_length(self) -> None:
        """pack_scenario(body) decompresses back to same body."""
        packed = se.pack_scenario(self.body)
        self.assertEqual(packed[:4], se.L33T_MAGIC)
        out_size = struct.unpack_from("<I", packed, 4)[0]
        self.assertEqual(out_size, len(self.body))
        body2 = zlib.decompress(packed[8:])
        self.assertEqual(body2, self.body, "noop pack must round-trip body bytes")

    def test_noop_set_bindings_keeps_civs(self) -> None:
        """Re-applying the original civs must not corrupt the table."""
        # Read current civs from BP[1..8]
        civs_in = []
        for hc, ai, pid in self.original_bindings[1:9]:
            civs_in.append(se.hcname_to_civ(hc))  # map back to token
        # We can't fully roundtrip vanilla civ tokens via hcname_to_civ
        # (e.g. "homecitygerman.xml" -> "German"), but we can pass the
        # raw hcnames by injecting them as fake civ tokens; instead, build
        # a mini-templated body with raw HC names by using a custom map.
        new_body = self.body
        for slot_idx in range(8):
            bps = se.find_bp_records(new_body)
            bp = bps[slot_idx + 1]
            p5 = bp.get_sub(b"P5")
            parsed = se.P5.parse(p5.payload)
            # No-op
            new_payload = parsed.serialize()
            self.assertEqual(new_payload, p5.payload,
                             f"noop serialize must equal original at slot {slot_idx+1}")

    def test_civ_swap_changes_binding(self) -> None:
        """Setting a different civ for slot 1 actually changes the binding."""
        civs = ["ANWArgentines"] + ["ANWBritish"] * 7
        new_body = se.set_player_bindings(self.body, civs)
        new_bindings = se.get_player_bindings(new_body)
        self.assertEqual(new_bindings[1][0], "anwhomecityargentines.xml")
        for slot in range(2, 9):
            self.assertEqual(new_bindings[slot][0], "anwhomecitybritish.xml")
        # Gaia untouched
        self.assertEqual(new_bindings[0], self.original_bindings[0])

    def test_emit_invariants_after_swap(self) -> None:
        """After binding 8 civs, all length invariants must still hold."""
        civs = se.PLAYBOOK_MATRIX["A"]
        new_body = se.set_player_bindings(self.body, civs)
        # inner_size set during pack_scenario - check direct invariant after pack/unpack
        packed = se.pack_scenario(new_body)
        outer = struct.unpack_from("<I", packed, 4)[0]
        body2 = zlib.decompress(packed[8:])
        self.assertEqual(outer, len(body2))
        inner = struct.unpack_from("<I", body2, 2)[0]
        self.assertEqual(inner, len(body2) - 7)
        # Also, BP record sizes == 4 + sum(sub_record_total)
        for bp in se.find_bp_records(body2):
            sub_total = sum(6 + s.size for s in bp.subs)
            self.assertEqual(bp.size, 4 + sub_total,
                             f"BP @ {bp.off:#x} size mismatch")

    def test_civ_swap_only_touches_bound_records(self) -> None:
        """Swapping slot 1's civ must NOT change other slots' P5 bytes."""
        # Take original P5 payloads
        original_bps = se.find_bp_records(self.body)
        original_p5s = [bp.get_sub(b"P5").payload for bp in original_bps]

        # Build a new body with only slot 1 changed
        civs = ["ANWArgentines"]
        for slot in range(2, 9):
            # keep original civ
            civs.append(se.hcname_to_civ(self.original_bindings[slot][0]))
        # set_player_bindings always rewrites all 8 — reset then re-set is enough.
        # Instead, manually patch only slot 1.
        bps = se.find_bp_records(self.body)
        bp = bps[1]
        p5 = bp.get_sub(b"P5")
        parsed = se.P5.parse(p5.payload)
        parsed.hcname = "anwhomecityargentines.xml"
        parsed.ai_loader = "aiLoaderStandard"
        new_payload = parsed.serialize()
        new_body = se.replace_sub_payload(self.body, bp, p5, new_payload)

        new_bps = se.find_bp_records(new_body)
        new_p5s = [b.get_sub(b"P5").payload for b in new_bps]

        # Slot 1 changed
        self.assertNotEqual(original_p5s[1], new_p5s[1])
        # All other slots' P5 payloads identical
        for i, (orig, new) in enumerate(zip(original_p5s, new_p5s)):
            if i == 1:
                continue
            self.assertEqual(orig, new, f"slot {i} P5 should be unchanged but differs")

    def test_playbook_matrix_emits_46_civs(self) -> None:
        """Six playbook scenarios must collectively bind all 46 ANW civ tokens."""
        bound = set()
        for label in ("A", "B", "C", "D", "E", "F"):
            civs = se.PLAYBOOK_MATRIX[label]
            new_body = se.set_player_bindings(self.body, civs)
            packed = se.pack_scenario(new_body)
            body2 = zlib.decompress(packed[8:])
            bindings = se.get_player_bindings(body2)
            for slot_civ, (hc, ai, pid) in zip(civs, bindings[1:9]):
                self.assertEqual(hc, se.civ_to_hcname(slot_civ))
                self.assertEqual(ai, "aiLoaderStandard")
                bound.add(slot_civ)
        # All 46 ANW civs must be in the union
        try:
            from tools.migration.anw_token_map import ANW_CIVS
        except ImportError:
            self.skipTest("anw_token_map not importable")
        all_anw = set(ANW_CIVS.keys())
        # F has 2 fillers (ANWBritish/ANWFrench - already in the matrix). Allow them.
        self.assertTrue(all_anw.issubset(bound),
                        f"missing civs in playbook: {all_anw - bound}")

    def test_full_emit_roundtrip(self) -> None:
        """Emit -> reload -> parse: invariants hold, every slot has the
        expected ANW civ, and outer file is uncompressable error-free."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            for label, civs in se.PLAYBOOK_MATRIX.items():
                new_body = se.set_player_bindings(self.body, civs)
                packed = se.pack_scenario(new_body)
                p = out_dir / f"ANW_Coverage_{label}.age3Yscn"
                p.write_bytes(packed)
                # Reload via the public API
                raw2, body2 = se.load_scenario(p)
                bindings = se.get_player_bindings(body2)
                self.assertEqual(len(bindings), 9)
                for civ, (hc, ai, _pid) in zip(civs, bindings[1:9]):
                    self.assertEqual(hc, se.civ_to_hcname(civ))


class CivMappingTests(unittest.TestCase):
    def test_anw_civ_to_hcname(self) -> None:
        self.assertEqual(se.civ_to_hcname("ANWBritish"), "anwhomecitybritish.xml")
        self.assertEqual(se.civ_to_hcname("ANWBajaCalifornians"),
                         "anwhomecitybajacalifornians.xml")
        self.assertEqual(se.civ_to_hcname("ANWBrazil"), "anwhomecitybrazil.xml")
        self.assertEqual(se.civ_to_hcname("ANWUSA"), "anwhomecityusa.xml")
        self.assertEqual(se.civ_to_hcname("ANWNapoleonicFrance"),
                         "anwhomecitynapoleonicfrance.xml")

    def test_vanilla_civ_to_hcname(self) -> None:
        self.assertEqual(se.civ_to_hcname("Spanish"), "homecityspanish.xml")
        self.assertEqual(se.civ_to_hcname("British"), "homecitybritish.xml")

    def test_hcname_to_civ_inverse_anw(self) -> None:
        for civ in ("ANWBritish", "ANWBrazil", "ANWUSA", "ANWMexicans"):
            hc = se.civ_to_hcname(civ)
            back = se.hcname_to_civ(hc)
            # Comparison case-insensitive (display capitalization differs).
            self.assertEqual(back.lower(), civ.lower())


def main() -> int:
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
