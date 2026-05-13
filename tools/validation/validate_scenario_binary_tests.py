#!/usr/bin/env python3
"""Unit tests for ``tools.validation.validate_scenario_binary``.

Run via:

    python3 -m unittest tools.validation.validate_scenario_binary_tests -v
or
    python3 tools/validation/validate_scenario_binary_tests.py
"""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.validation import validate_scenario_binary as v  # noqa: E402

# 2026-05-11: was Scenario/legendary-leaders-ai.age3Yscn; that file was
# removed in favour of Scenario/ANEWWORLD.age3Yscn as the canonical
# AI-testing scenario, but these emitter tests assert byte-level
# round-trip identity and are tightly coupled to this template's zlib
# parameters. Kept as a test fixture under a neutral name.
LL_TEMPLATE = REPO / "Scenario" / "_test_template.age3Yscn"
PASSTHRU = REPO / "artifacts" / "emitted_scenarios" / "_passthrough_LL.age3Yscn"
PASSTHRU_TR = REPO / "artifacts" / "emitted_scenarios" / "_passthrough_LL_with_trailer.age3Yscn"


def _make_dummy_scenario(body_size: int = 64,
                         trailer: bytes = b"",
                         level: int = 6,
                         break_outer: int = 0,
                         break_inner: int = 0,
                         break_magic: bool = False) -> bytes:
    """Build a minimal but valid l33t/zlib container for tests."""
    body = bytearray(b"BG\x00\x00\x00\x00" + struct.pack("<I", 105) + b"FH")
    body += b"\x00" * (body_size - len(body))
    struct.pack_into("<I", body, 2, len(body) - 7 + break_inner)
    body = bytes(body)
    if break_magic:
        body = b"XX" + body[2:]
    out = bytearray()
    out += b"l33t"
    out += struct.pack("<I", len(body) + break_outer)
    out += zlib.compress(body, level)
    out += trailer
    return bytes(out)


class ParseTests(unittest.TestCase):
    def setUp(self) -> None:
        if not LL_TEMPLATE.exists():
            self.skipTest(f"template missing: {LL_TEMPLATE}")

    def test_parse_known_good_template(self) -> None:
        sf = v.parse(LL_TEMPLATE)
        self.assertEqual(sf.body[:2], b"BG")
        self.assertEqual(sf.body[10:12], b"FH")
        self.assertTrue(sf.outer_size_ok)
        self.assertTrue(sf.inner_size_ok)
        self.assertEqual(len(sf.trailer), 4)
        self.assertEqual(sf.trailer.hex(), "b7383381")
        self.assertEqual(sf.version, 105)

    def test_validate_known_good_template_no_issues(self) -> None:
        self.assertEqual(v.validate(LL_TEMPLATE), [])

    def test_validate_strict_known_good(self) -> None:
        self.assertEqual(v.validate(LL_TEMPLATE, strict=True), [])

    def test_parse_dummy_scenario(self) -> None:
        raw = _make_dummy_scenario()
        sf = v.parse_bytes(raw)
        self.assertTrue(sf.outer_size_ok)
        self.assertTrue(sf.inner_size_ok)
        self.assertFalse(sf.has_trailer)


class ValidateBrokenTests(unittest.TestCase):
    def test_bad_magic(self) -> None:
        bad = b"XYZW" + b"\x00" * 16
        self.assertTrue(any("bad magic" in x for x in v.validate(_write_tmp(bad))))

    def test_outer_size_off_by(self) -> None:
        raw = _make_dummy_scenario(break_outer=10)
        with tempfile.NamedTemporaryFile(suffix=".age3Yscn", delete=False) as fh:
            fh.write(raw)
            p = Path(fh.name)
        try:
            issues = v.validate(p)
            self.assertTrue(any("outer_size mismatch" in x for x in issues),
                            f"issues={issues}")
        finally:
            p.unlink()

    def test_inner_size_off_by(self) -> None:
        raw = _make_dummy_scenario(break_inner=5)
        with tempfile.NamedTemporaryFile(suffix=".age3Yscn", delete=False) as fh:
            fh.write(raw)
            p = Path(fh.name)
        try:
            issues = v.validate(p)
            self.assertTrue(any("inner_size mismatch" in x for x in issues),
                            f"issues={issues}")
        finally:
            p.unlink()

    def test_strict_no_trailer(self) -> None:
        raw = _make_dummy_scenario(trailer=b"")
        with tempfile.NamedTemporaryFile(suffix=".age3Yscn", delete=False) as fh:
            fh.write(raw)
            p = Path(fh.name)
        try:
            issues_lax = v.validate(p, strict=False)
            issues_strict = v.validate(p, strict=True)
            self.assertEqual(issues_lax, [])
            self.assertTrue(any("no 4-byte trailer" in x for x in issues_strict))
        finally:
            p.unlink()


class DiffTests(unittest.TestCase):
    def setUp(self) -> None:
        if not LL_TEMPLATE.exists():
            self.skipTest(f"template missing: {LL_TEMPLATE}")

    def test_diff_template_against_self(self) -> None:
        report = v.diff(LL_TEMPLATE, LL_TEMPLATE)
        self.assertTrue(report.bodies_identical)
        self.assertEqual(report.differing_regions, [])
        self.assertEqual(report.file_size_delta, 0)

    def test_diff_passthru_same_body_different_zlib(self) -> None:
        if not PASSTHRU.exists():
            self.skipTest(f"missing: {PASSTHRU}")
        report = v.diff(LL_TEMPLATE, PASSTHRU)
        self.assertTrue(report.bodies_identical,
                        f"expected identical bodies; report={report}")
        # File size delta exists because zlib re-encoder produced different bytes
        self.assertNotEqual(report.file_size_delta, 0)

    def test_diff_modified_body(self) -> None:
        # Build a scenario where one byte deep in the body has been flipped.
        ref_raw = _make_dummy_scenario(body_size=128)
        cand_body = bytearray(zlib.decompress(ref_raw[8:]))
        cand_body[64] ^= 0xFF
        cand_raw = bytearray()
        cand_raw += b"l33t"
        cand_raw += struct.pack("<I", len(cand_body))
        cand_raw += zlib.compress(bytes(cand_body), 6)
        report = v.diff(_write_tmp(ref_raw), _write_tmp(bytes(cand_raw)))
        self.assertFalse(report.bodies_identical)
        # Should report exactly one differing region
        self.assertGreaterEqual(len(report.differing_regions), 1)
        # First differing region covers offset 64
        first_off, first_len = report.differing_regions[0]
        self.assertLessEqual(first_off, 64)
        self.assertGreaterEqual(first_off + first_len, 65)


class RoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        if not LL_TEMPLATE.exists():
            self.skipTest(f"template missing: {LL_TEMPLATE}")

    def test_round_trip_template(self) -> None:
        # Round-trip MUST decompress to the same body. It is NOT expected to
        # produce byte-identical files (Python zlib != engine zlib).
        report = v.validate_round_trip(LL_TEMPLATE)
        self.assertTrue(report.bodies_identical,
                        f"bodies must be byte-identical after re-pack; report={report}")


# --- helpers --------------------------------------------------------------


_TMP_FILES: list[Path] = []


def _write_tmp(data: bytes) -> Path:
    fh = tempfile.NamedTemporaryFile(suffix=".age3Yscn", delete=False)
    fh.write(data)
    fh.close()
    p = Path(fh.name)
    _TMP_FILES.append(p)
    return p


def tearDownModule() -> None:  # noqa: N802
    for p in _TMP_FILES:
        try:
            p.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
