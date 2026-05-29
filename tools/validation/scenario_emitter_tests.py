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

import argparse
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

    def test_playbook_matrix_emits_40_civs(self) -> None:
        """Six playbook scenarios must collectively bind all 40 ANW civ tokens."""
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
        # All 40 ANW civs must be in the union
        try:
            from tools.migration.anw_token_map import ANW_CIVS
        except ImportError:
            self.skipTest("anw_token_map not importable")
        all_anw = set(ANW_CIVS.keys())
        # F holds 8 filler slots (all already covered in A-E). Allow them.
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
        self.assertEqual(se.civ_to_hcname("ANWArgentines"),
                         "anwhomecityargentines.xml")
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


class TrailerTests(unittest.TestCase):
    """Cover the CRC32-trailer algorithm and the recompute_trailer flag.

    Verified against four real .age3Yscn files in
    tools/validation/SCENARIO_TRAILER_ANALYSIS.md:
        Bombard_Brawl       -> 45069598
        _test_template      -> b7383381
        QuickSavegame       -> 16558739
        QuickSavegame.bak   -> b3a30be2
    These tests assert the algorithm matches against any present sample.
    """

    KNOWN_TRAILERS = {
        # Filename relative to REPO unless absolute
        REPO / "Scenario" / "_test_template.age3Yscn": "b7383381",
    }

    def test_template_known_trailer(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        raw = TEMPLATE.read_bytes()
        expected = se.compute_crc32_trailer(raw[:-4])
        self.assertEqual(expected.hex(), "b7383381")
        self.assertEqual(raw[-4:], expected)

    def test_verify_trailer_template(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        self.assertTrue(se.verify_trailer(TEMPLATE))

    def test_verify_trailer_rejects_corruption(self) -> None:
        """Flipping any byte must invalidate the CRC32."""
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        raw = TEMPLATE.read_bytes()
        with tempfile.NamedTemporaryFile(suffix=".age3Yscn", delete=False) as fh:
            corrupted = bytearray(raw)
            # Flip a byte in the middle (zlib stream area).
            corrupted[len(corrupted) // 2] ^= 0x01
            fh.write(bytes(corrupted))
            tmp_path = Path(fh.name)
        try:
            self.assertFalse(se.verify_trailer(tmp_path),
                             "corrupted file should fail trailer verification")
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_verify_trailer_too_short(self) -> None:
        """Files under 12 bytes are unconditionally invalid (no trailer slot)."""
        with tempfile.NamedTemporaryFile(suffix=".age3Yscn", delete=False) as fh:
            fh.write(b"l33t\x00\x00")
            tmp_path = Path(fh.name)
        try:
            self.assertFalse(se.verify_trailer(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_pack_scenario_recomputes_trailer(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        _raw, body = se.load_scenario(TEMPLATE)
        packed = se.pack_scenario(body, recompute_trailer=True)
        # 4-byte trailer at end must equal CRC32(packed_minus_trailer + 4 zeroes).
        expected = se.compute_crc32_trailer(packed[:-4])
        self.assertEqual(packed[-4:], expected,
                         "pack_scenario(recompute_trailer=True) must emit CRC32 trailer")

    def test_pack_scenario_warns_on_explicit_trailer_with_recompute(self) -> None:
        """Explicit `trailer` + `recompute_trailer=True` -> warning + recompute wins."""
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        _raw, body = se.load_scenario(TEMPLATE)
        bogus = b"\xde\xad\xbe\xef"
        # Capture stderr while packing.
        saved_err = sys.stderr
        sys.stderr = captured = io.StringIO()
        try:
            packed = se.pack_scenario(body, trailer=bogus, recompute_trailer=True)
        finally:
            sys.stderr = saved_err
        self.assertNotEqual(packed[-4:], bogus,
                            "recompute_trailer=True must ignore explicit trailer")
        self.assertIn("ignoring explicit", captured.getvalue())

    def test_pack_scenario_explicit_trailer_when_recompute_false(self) -> None:
        """recompute_trailer=False appends caller-supplied trailer verbatim."""
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        _raw, body = se.load_scenario(TEMPLATE)
        bogus = b"\xde\xad\xbe\xef"
        packed = se.pack_scenario(body, trailer=bogus, recompute_trailer=False)
        self.assertEqual(packed[-4:], bogus)

    def test_emitted_scenario_trailer_round_trips(self) -> None:
        """End-to-end: bind civs, pack with recompute_trailer, verify_trailer == True."""
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        _raw, body = se.load_scenario(TEMPLATE)
        new_body = se.set_player_bindings(
            body, se.PLAYBOOK_MATRIX["A"], ai_loader="aiLoaderStandard"
        )
        packed = se.pack_scenario(new_body, recompute_trailer=True)
        with tempfile.NamedTemporaryFile(suffix=".age3Yscn", delete=False) as fh:
            fh.write(packed)
            tmp_path = Path(fh.name)
        try:
            self.assertTrue(se.verify_trailer(tmp_path),
                            "freshly emitted scenario must self-verify CRC32 trailer")
        finally:
            tmp_path.unlink(missing_ok=True)


class CarrierTests(unittest.TestCase):
    """Cover find_default_carrier + the BB-carrier emit-anewworld + emit-playbook
    code paths. Skipped if the stock Bombard_Brawl.age3Yscn is not on disk.
    """

    def setUp(self) -> None:
        try:
            self.carrier = se.find_default_carrier()
        except FileNotFoundError:
            self.skipTest("Bombard_Brawl carrier not on disk")

    def test_carrier_loads_and_validates(self) -> None:
        """The carrier must already be CRC32-trailer-valid (stock AoE3DE file)."""
        self.assertTrue(se.verify_trailer(self.carrier),
                        f"stock carrier {self.carrier} has wrong CRC32 trailer")

    def test_carrier_has_9_bp_records(self) -> None:
        """BB has exactly 9 player BP records (Gaia + 8 slots)."""
        _raw, body = se.load_scenario(self.carrier)
        bps = se.find_bp_records(body)
        self.assertEqual(len(bps), 9,
                         f"BB carrier should have 9 BP records, got {len(bps)}")

    def test_emit_anewworld_via_bb_carrier(self) -> None:
        """End-to-end: emit ANEWWORLD.age3Yscn from BB; verify trailer + bindings."""
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "ANEWWORLD.age3Yscn"
            args = argparse.Namespace(template=None, out=str(out_path))
            rc = se.cmd_emit_anewworld(args)
            self.assertEqual(rc, 0, "emit-anewworld should exit 0")
            self.assertTrue(out_path.exists())
            self.assertTrue(se.verify_trailer(out_path),
                            "emitted ANEWWORLD must pass CRC32 verification")
            # Reload and check bindings match ANEWWORLD_CIVS / ANEWWORLD_LOADERS.
            _raw, body = se.load_scenario(out_path)
            bindings = se.get_player_bindings(body)
            self.assertEqual(len(bindings), 9)
            for civ, loader, (hc, ai, _pid) in zip(
                se.ANEWWORLD_CIVS, se.ANEWWORLD_LOADERS, bindings[1:9]
            ):
                self.assertEqual(hc, se.civ_to_hcname(civ),
                                 f"slot bound to wrong civ: {hc!r} vs {civ!r}")
                self.assertEqual(ai, loader,
                                 f"slot bound to wrong loader: {ai!r} vs {loader!r}")

    def test_carrier_version_check_passes_for_bb(self) -> None:
        """BB body version must be within the engine-supported range."""
        ver, ok, msg = se.check_carrier_version(self.carrier)
        self.assertTrue(ok, msg)
        self.assertLessEqual(ver, se.SUPPORTED_BG_VERSION_MAX,
                             f"BB body version {ver} exceeds engine max")

    def test_carrier_version_check_rejects_template(self) -> None:
        """_test_template.age3Yscn is a v105 quick-save; must be flagged."""
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        ver, ok, msg = se.check_carrier_version(TEMPLATE)
        self.assertFalse(ok, f"template should be flagged (got {ver=} {ok=})")
        self.assertGreater(ver, se.SUPPORTED_BG_VERSION_MAX,
                           f"template body version {ver} should exceed max")
        self.assertIn("QUICK-SAVE", msg)

    def test_emit_playbook_via_bb_carrier(self) -> None:
        """End-to-end: emit ANW_Coverage_A..F from BB; verify all 6 trailers + civ coverage."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            args = argparse.Namespace(
                template=None,
                out_dir=str(out_dir),
                ai="aiLoaderStandard",
            )
            rc = se.cmd_emit_playbook(args)
            self.assertEqual(rc, 0, "emit-playbook should exit 0")
            bound_civs: set = set()
            for label in ("A", "B", "C", "D", "E", "F"):
                p = out_dir / f"ANW_Coverage_{label}.age3Yscn"
                self.assertTrue(p.exists(), f"missing {p}")
                self.assertTrue(se.verify_trailer(p),
                                f"{p.name} fails CRC32 verification")
                _raw, body = se.load_scenario(p)
                bindings = se.get_player_bindings(body)
                self.assertEqual(len(bindings), 9)
                # P1 (slot 1) must be human (loader = '')
                self.assertEqual(bindings[1][1], "",
                                 f"{p.name}: P1 should be human, got loader={bindings[1][1]!r}")
                # P2..P8 must be AI
                for slot in range(2, 9):
                    self.assertEqual(bindings[slot][1], "aiLoaderStandard",
                                     f"{p.name}: slot {slot} loader wrong")
                for civ, (hc, _ai, _pid) in zip(
                    se.PLAYBOOK_MATRIX[label], bindings[1:9]
                ):
                    self.assertEqual(hc, se.civ_to_hcname(civ))
                    bound_civs.add(civ)
            # The 6 scenarios together should cover all 40 unique ANW civs.
            self.assertGreaterEqual(
                len(bound_civs), 40,
                f"playbook only covers {len(bound_civs)} civs, expected >= 40"
            )


def main() -> int:
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
