#!/usr/bin/env python3
"""Unit tests for tools.validation.scenario_trigger_writer.

Run via:

    python3 -m unittest discover -s tools/validation -p "scenario_*tests.py" -v
or
    python3 tools/validation/scenario_trigger_writer_tests.py

Tests cover:
  1. Round-trip noop equality  — _test_template, ANEWWORLD, Bombard_Brawl
  2. Empty-template injection  — add 1 trigger, re-parse, verify name+xs
  3. Group consistency invariants after injection
  4. Container invariants after injection (validate_scenario_binary.validate)
  5. lpu8 / lpu16 encoding unit tests
  6. value_type==22 extra u32 quirk
"""
from __future__ import annotations

import hashlib
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.validation.scenario_trigger_parser import (  # noqa: E402
    parse_trigger_section,
)
from tools.validation.scenario_emitter import load_scenario, pack_scenario  # noqa: E402
from tools.validation import validate_scenario_binary as vsb  # noqa: E402
import tools.validation.scenario_trigger_writer as stw  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TEMPLATE = REPO / "Scenario" / "_test_template.age3Yscn"
ANEWWORLD = REPO / "Scenario" / "ANEWWORLD.age3Yscn"
BOMBARD_BRAWL = Path(
    Path.home()
    / ".local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/ScoreChallenges"
    / "Bombard_Brawl.age3Yscn"
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _tr_bytes(scn_path: Path) -> bytes:
    """Return the raw TR payload bytes from a scenario file."""
    _raw, body = load_scenario(scn_path)
    sec = parse_trigger_section(body)
    return sec.raw


def _tr_bytes_from_body(body: bytes) -> bytes:
    sec = parse_trigger_section(body)
    return sec.raw


# ---------------------------------------------------------------------------
# 1. Round-trip noop equality
# ---------------------------------------------------------------------------


class RoundTripTests(unittest.TestCase):

    def _check_roundtrip(self, path: Path, label: str) -> None:
        """Parse -> serialize -> must produce identical TR payload bytes."""
        if not path.exists():
            self.skipTest(f"{label} not found: {path}")
        _raw, body = load_scenario(path)
        sec = parse_trigger_section(body)
        reencoded = stw.serialize_tr_payload(sec)
        self.assertEqual(
            reencoded,
            sec.raw,
            f"{label}: TR re-encode differs from original "
            f"(orig={len(sec.raw)}B new={len(reencoded)}B)",
        )

    def test_roundtrip_test_template(self) -> None:
        """_test_template.age3Yscn TR payload round-trips exactly."""
        self._check_roundtrip(TEMPLATE, "_test_template")

    def test_roundtrip_anewworld(self) -> None:
        """ANEWWORLD.age3Yscn TR payload round-trips exactly."""
        self._check_roundtrip(ANEWWORLD, "ANEWWORLD")

    def test_roundtrip_bombard_brawl(self) -> None:
        """Bombard_Brawl.age3Yscn TR payload round-trips exactly (104 triggers)."""
        if not BOMBARD_BRAWL.exists():
            self.skipTest(f"Bombard_Brawl not found: {BOMBARD_BRAWL}")
        _raw, body = load_scenario(BOMBARD_BRAWL)
        sec = parse_trigger_section(body)
        reencoded = stw.serialize_tr_payload(sec)
        orig_sha = hashlib.sha256(sec.raw).hexdigest()
        new_sha = hashlib.sha256(reencoded).hexdigest()
        self.assertEqual(
            orig_sha, new_sha,
            "Bombard_Brawl TR sha256 mismatch: "
            f"orig={orig_sha} new={new_sha}",
        )


# ---------------------------------------------------------------------------
# 2. Empty-template injection
# ---------------------------------------------------------------------------


class InjectionTests(unittest.TestCase):

    def setUp(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_inject_one_trigger(self) -> None:
        """Inject 1 trigger into _test_template, re-parse, verify name + xs."""
        xs = stw.make_xs_block('trChatSend(0,"hello");')
        effect = stw.make_action(
            "Script Call",
            "Script Call",
            is_effect=True,
            xs_blocks=[xs],
        )
        cond = stw.make_action(
            "Always",
            "Always",
            is_effect=False,
            eval_expr="true",
        )
        t = stw.make_trigger(
            "TestProbeBoot",
            conditions=[cond],
            effects=[effect],
        )
        out = self.tmp_dir / "injected.age3Yscn"
        stw.inject_triggers(TEMPLATE, [t], out)

        # Re-parse
        _raw, body = load_scenario(out)
        sec = parse_trigger_section(body)
        self.assertEqual(sec.trigger_count, 1,
                         "trigger_count should be 1 after injection")
        self.assertEqual(len(sec.triggers), 1,
                         "parsed trigger list should have 1 entry")
        self.assertEqual(sec.triggers[0].name, "TestProbeBoot",
                         "injected trigger name must match")
        self.assertEqual(len(sec.triggers[0].effects), 1)
        self.assertEqual(len(sec.triggers[0].conditions), 1)
        xs_text = sec.triggers[0].effects[0].xs_blocks[0].text
        self.assertEqual(xs_text, 'trChatSend(0,"hello");',
                         "XS code string must survive round-trip")

    def test_inject_preserves_existing_triggers(self) -> None:
        """Injecting into a 0-trigger template should yield exactly 1 trigger."""
        t = stw.make_trigger("probe")
        out = self.tmp_dir / "probe.age3Yscn"
        stw.inject_triggers(TEMPLATE, [t], out)
        _raw, body = load_scenario(out)
        sec = parse_trigger_section(body)
        self.assertEqual(len(sec.triggers), 1)


# ---------------------------------------------------------------------------
# 3. Group consistency invariants
# ---------------------------------------------------------------------------


class GroupConsistencyTests(unittest.TestCase):

    def setUp(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_group_trig_ids_updated(self) -> None:
        """After injection, group[0].trig_ids must contain the new trigger's id."""
        t = stw.make_trigger("InGroup")
        out = self.tmp_dir / "group_check.age3Yscn"
        stw.inject_triggers(TEMPLATE, [t], out, group_index=0)
        _raw, body = load_scenario(out)
        sec = parse_trigger_section(body)
        new_tid = sec.triggers[0].trigger_id
        self.assertIn(
            new_tid,
            sec.groups[0].trigger_ids,
            "new trigger id must be in groups[0].trig_ids",
        )

    def test_header_trigger_count_bumped(self) -> None:
        """TR_header.trigger_count must equal len(sec.triggers) after injection."""
        t = stw.make_trigger("CountCheck")
        out = self.tmp_dir / "count_check.age3Yscn"
        stw.inject_triggers(TEMPLATE, [t], out)
        _raw, body = load_scenario(out)
        sec = parse_trigger_section(body)
        self.assertEqual(
            sec.trigger_count,
            len(sec.triggers),
            "header trigger_count must match actual trigger list length",
        )

    def test_next_id_is_greater_than_all_trigger_ids(self) -> None:
        """next_id must be > all trigger ids after injection."""
        t = stw.make_trigger("NextIdCheck")
        out = self.tmp_dir / "nextid.age3Yscn"
        stw.inject_triggers(TEMPLATE, [t], out)
        _raw, body = load_scenario(out)
        sec = parse_trigger_section(body)
        max_id = max(tr.trigger_id for tr in sec.triggers)
        self.assertGreater(
            sec.next_id,
            max_id,
            f"next_id={sec.next_id} must be > max trigger id {max_id}",
        )


# ---------------------------------------------------------------------------
# 4. Container invariants preserved
# ---------------------------------------------------------------------------


class ContainerInvariantTests(unittest.TestCase):

    def setUp(self) -> None:
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_validate_after_noop_roundtrip_template(self) -> None:
        """Noop round-trip of _test_template must pass validate_scenario_binary."""
        out = self.tmp_dir / "tt_roundtrip.age3Yscn"
        stw.inject_triggers(TEMPLATE, [], out)
        issues = vsb.validate(out)
        self.assertEqual(issues, [],
                         "validate must pass after noop re-emit of template: "
                         + ", ".join(issues))

    def test_validate_after_injection(self) -> None:
        """Scenario with injected trigger must pass validate_scenario_binary."""
        t = stw.make_trigger("ValidateMe")
        out = self.tmp_dir / "validate_inject.age3Yscn"
        stw.inject_triggers(TEMPLATE, [t], out)
        issues = vsb.validate(out)
        self.assertEqual(issues, [],
                         "validate must pass after trigger injection: "
                         + ", ".join(issues))

    def test_validate_after_roundtrip_bb(self) -> None:
        """Noop round-trip of Bombard_Brawl must pass validate_scenario_binary."""
        if not BOMBARD_BRAWL.exists():
            self.skipTest(f"Bombard_Brawl not found: {BOMBARD_BRAWL}")
        out = self.tmp_dir / "bb_rt.age3Yscn"
        _raw, body = load_scenario(BOMBARD_BRAWL)
        sec = parse_trigger_section(body)
        new_tr = stw.serialize_tr_payload(sec)
        new_body = stw.replace_tr_section(body, new_tr)
        out.write_bytes(pack_scenario(new_body))
        issues = vsb.validate(out)
        self.assertEqual(issues, [],
                         "validate must pass after BB noop round-trip: "
                         + ", ".join(issues))

    def test_inner_and_outer_size_correct_after_injection(self) -> None:
        """outer_size and inner_size must be correct after writing."""
        t = stw.make_trigger("SizeCheck")
        out = self.tmp_dir / "size_check.age3Yscn"
        stw.inject_triggers(TEMPLATE, [t], out)
        raw = out.read_bytes()
        outer_size = struct.unpack_from("<I", raw, 4)[0]
        body = zlib.decompress(raw[8:])
        self.assertEqual(outer_size, len(body),
                         "outer_size must equal decompressed body length")
        inner_size = struct.unpack_from("<I", body, 2)[0]
        self.assertEqual(inner_size, len(body) - 7,
                         "inner_size must equal body_len - 7")


# ---------------------------------------------------------------------------
# 5. lpu8 / lpu16 encoding unit tests
# ---------------------------------------------------------------------------


class EncodingTests(unittest.TestCase):

    def test_lpu8_hello(self) -> None:
        """lpu8('Hello') -> u32(6) + b'Hello\\x00'"""
        result = stw.encode_lpu8("Hello")
        expected = struct.pack("<I", 6) + b"Hello\x00"
        self.assertEqual(result, expected,
                         f"lpu8('Hello') got {result.hex()}, want {expected.hex()}")

    def test_lpu8_empty_canonical(self) -> None:
        """lpu8('') -> u32(0) only (canonical form)."""
        result = stw.encode_lpu8("")
        expected = struct.pack("<I", 0)
        self.assertEqual(result, expected,
                         "empty lpu8 must be u32(0) only")

    def test_lpu16_hi(self) -> None:
        """lpu16('Hi') -> u32(2) + b'H\\x00i\\x00' (char count, no terminator)."""
        result = stw.encode_lpu16("Hi")
        expected = struct.pack("<I", 2) + "Hi".encode("utf-16-le")
        self.assertEqual(result, expected,
                         f"lpu16('Hi') got {result.hex()}, want {expected.hex()}")

    def test_lpu16_empty(self) -> None:
        """lpu16('') -> u32(0) only."""
        result = stw.encode_lpu16("")
        expected = struct.pack("<I", 0)
        self.assertEqual(result, expected,
                         "empty lpu16 must be u32(0) only")

    def test_lpu8_length_includes_null(self) -> None:
        """lpu8 length prefix includes the null terminator."""
        for s in ("a", "hello", "trigger"):
            result = stw.encode_lpu8(s)
            declared_len = struct.unpack_from("<I", result, 0)[0]
            self.assertEqual(declared_len, len(s) + 1,
                             f"lpu8({s!r}) length prefix {declared_len} != len+1={len(s)+1}")

    def test_lpu16_length_is_char_count(self) -> None:
        """lpu16 length prefix is char count (not byte count, no null)."""
        for s in ("a", "hi", "hello"):
            result = stw.encode_lpu16(s)
            declared_len = struct.unpack_from("<I", result, 0)[0]
            self.assertEqual(declared_len, len(s),
                             f"lpu16({s!r}) length prefix {declared_len} != len={len(s)}")
            self.assertEqual(len(result), 4 + 2 * len(s),
                             "lpu16 wire size must be 4 + 2*char_count (no terminator)")

    def test_lpu8_non_canonical_empty(self) -> None:
        """lpu8 writer emits 01 00 00 00 00 when raw_len hint is 1."""
        w = stw.Writer()
        w.lp_utf8("", raw_len=1)
        result = w.bytes()
        expected = b"\x01\x00\x00\x00\x00"
        self.assertEqual(result, expected,
                         "non-canonical empty lpu8 (raw_len=1) must emit 01 00 00 00 00")


# ---------------------------------------------------------------------------
# 6. value_type==22 quirk
# ---------------------------------------------------------------------------


class ValueType22Tests(unittest.TestCase):

    def test_param_vtype22_extra_u32(self) -> None:
        """A Param with value_type=22 must include the extra u32 0 between vcount and value."""
        p = stw.make_param(
            "StringID",
            "String ID",
            value_type=22,
            values=["{81108}"],
        )
        # Serialize just this param
        w = stw.Writer()
        stw._write_param(w, p)
        result = w.bytes()

        # The layout should be:
        # u32 type_tag=2, lpu8 "StringID", lpu8 "String ID",
        # u32 value_type=22, u32 vcount=1, u32 extra=0, lpu16 "{81108}"
        # Let's manually parse to verify the extra u32 is present
        pos = 0
        type_tag = struct.unpack_from("<I", result, pos)[0]; pos += 4
        self.assertEqual(type_tag, 2)
        # Skip lpu8 "StringID"
        n = struct.unpack_from("<I", result, pos)[0]; pos += 4 + n
        # Skip lpu8 "String ID"
        n = struct.unpack_from("<I", result, pos)[0]; pos += 4 + n
        vtype = struct.unpack_from("<I", result, pos)[0]; pos += 4
        self.assertEqual(vtype, 22)
        vcount = struct.unpack_from("<I", result, pos)[0]; pos += 4
        self.assertEqual(vcount, 1)
        extra = struct.unpack_from("<I", result, pos)[0]; pos += 4
        self.assertEqual(extra, 0, "value_type==22 must have extra u32 0 between vcount and value")
        # lpu16 "{81108}"
        char_count = struct.unpack_from("<I", result, pos)[0]; pos += 4
        self.assertEqual(char_count, len("{81108}"))
        val_bytes = result[pos:pos + 2 * char_count]
        self.assertEqual(val_bytes.decode("utf-16-le"), "{81108}")

    def test_param_vtype22_roundtrip_via_parser(self) -> None:
        """A Param with value_type=22 constructed + serialized + re-parsed must match."""
        if not TEMPLATE.exists():
            self.skipTest(f"template not found: {TEMPLATE}")
        p = stw.make_param(
            "Text",
            "Text",
            type_tag=4,
            value_type=22,
            values=["{12345}"],
        )
        xs = stw.make_xs_block('trObjectiveSetString("{Text}");', deps=["Text"])
        effect = stw.make_action(
            "Objective",
            "Objective",
            is_effect=True,
            params=[p],
            xs_blocks=[xs],
        )
        t = stw.make_trigger("VT22Test", effects=[effect])

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "vt22.age3Yscn"
            stw.inject_triggers(TEMPLATE, [t], out)
            _raw, body = load_scenario(out)
            sec = parse_trigger_section(body)
            self.assertEqual(len(sec.triggers), 1)
            re_effect = sec.triggers[0].effects[0]
            self.assertEqual(len(re_effect.params), 1)
            rp = re_effect.params[0]
            self.assertEqual(rp.value_type, 22)
            self.assertEqual(rp.values, ["{12345}"])
            # extra should be the 4-byte u32 0
            self.assertEqual(rp.extra, b"\x00\x00\x00\x00",
                             "parsed value_type==22 extra must be 4-byte u32 0")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
