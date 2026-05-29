#!/usr/bin/env python3
"""Unit tests for the pixel-perfect art verifier.

Run::

    python3 -m unittest tools.validation.validate_art_pixel_perfect_tests -v
    python3 tools/validation/validate_art_pixel_perfect_tests.py

These exercise the smaller utilities (header check, sha256, normalisation,
section-to-civ resolution) and a tiny synthetic mini-repo end-to-end.
"""
from __future__ import annotations

import io
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import art_inventory as inv_mod  # noqa: E402
import validate_art_pixel_perfect as vp  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — tiny PNG / JPEG bytes
# ---------------------------------------------------------------------------

def _tiny_png(w: int = 1, h: int = 1, color: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    """Hand-roll a 1x1 PNG (or larger solid PNG) without Pillow."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(typ: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + typ + data + struct.pack(
            ">I", zlib.crc32(typ + data) & 0xFFFFFFFF
        )

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(h):
        raw += b"\x00" + bytes(color) * w
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _tiny_jpeg() -> bytes:
    """A bare-minimum JPEG SOI/EOI marker — Pillow may not decode but
    headers will pass the magic check."""
    # In practice we use this only for the header check, not the decode path.
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


# ---------------------------------------------------------------------------
# Tests for primitives
# ---------------------------------------------------------------------------

class TestHeaderCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_missing(self):
        self.assertEqual(vp._check_header(self.dir / "nope.png"), "missing")

    def test_empty(self):
        p = self.dir / "empty.png"
        p.write_bytes(b"")
        self.assertEqual(vp._check_header(p), "empty")

    def test_good_png(self):
        p = self.dir / "ok.png"
        p.write_bytes(_tiny_png())
        self.assertIsNone(vp._check_header(p))

    def test_jpeg_in_png_extension(self):
        p = self.dir / "fake.png"
        p.write_bytes(_tiny_jpeg())
        self.assertEqual(vp._check_header(p), "bad PNG magic")

    def test_good_jpeg(self):
        p = self.dir / "ok.jpg"
        p.write_bytes(_tiny_jpeg())
        self.assertIsNone(vp._check_header(p))


class TestSha256(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_identical_bytes_same_hash(self):
        a = self.dir / "a.bin"; b = self.dir / "b.bin"
        a.write_bytes(b"hello world"); b.write_bytes(b"hello world")
        self.assertEqual(vp._sha256(a), vp._sha256(b))

    def test_diff_bytes_diff_hash(self):
        a = self.dir / "a.bin"; b = self.dir / "b.bin"
        a.write_bytes(b"hello world"); b.write_bytes(b"hello world!")
        self.assertNotEqual(vp._sha256(a), vp._sha256(b))


class TestNormalise(unittest.TestCase):
    def test_backslashes(self):
        self.assertEqual(vp._normalise("a\\b\\c.png"), "a/b/c.png")

    def test_leading_dot_slash(self):
        self.assertEqual(vp._normalise("./resources/x.png"), "resources/x.png")


class TestInventoryParsing(unittest.TestCase):
    def test_parse_html_imgs_picks_class_and_section(self):
        text = (
            '<!-- ── Argentines ── -->\n'
            '<img class="flag-img" src="resources/images/icons/flags/Flag_X.png" alt="x">\n'
            '<img class="portrait-img" src="resources/images/icons/leaders/y.png" alt="y">\n'
            '<img class="card-icon" src="resources/images/icons/cards/z.png" alt="z">\n'
            '<!-- ── British ── -->\n'
            '<img class="flag-img" src="resources/images/icons/flags/Flag_GB.png" alt="">\n'
        )
        rows = inv_mod.parse_html_imgs(text)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["civ_section"], "Argentines")
        self.assertIn("flag-img", rows[0]["class"])
        self.assertEqual(rows[3]["civ_section"], "British")

    def test_parse_civmods_extracts_wpf(self):
        xml = (
            "<civmods>"
            "<Civ><Name>ANWFoo</Name>"
            "<HomeCityFlagIconWPF>resources\\images\\icons\\flags\\Flag_Foo.png</HomeCityFlagIconWPF>"
            "<HomeCityPreviewWPF>resources/images/icons/singleplayer/cpai_avatar_foo_bar.png</HomeCityPreviewWPF>"
            "</Civ>"
            "<Civ><Name>ANWBar</Name></Civ>"
            "</civmods>"
        )
        out = inv_mod.parse_civmods(xml)
        self.assertEqual(out["ANWFoo"]["flag_wpf"],
                          "resources/images/icons/flags/Flag_Foo.png")
        self.assertEqual(out["ANWFoo"]["portrait_wpf"],
                          "resources/images/icons/singleplayer/cpai_avatar_foo_bar.png")
        # Missing fields default to ""
        self.assertEqual(out["ANWBar"]["flag_wpf"], "")
        self.assertEqual(out["ANWBar"]["portrait_wpf"], "")

    def test_section_to_civ(self):
        self.assertEqual(inv_mod.section_to_civ("Argentines"), "ANWArgentines")
        self.assertEqual(inv_mod.section_to_civ("British"), "ANWBritish")
        self.assertIsNone(inv_mod.section_to_civ("Bogus"))
        self.assertIsNone(inv_mod.section_to_civ(None))


# ---------------------------------------------------------------------------
# End-to-end with a synthetic mini-repo
# ---------------------------------------------------------------------------

class TestEndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp())
        self.deployed = Path(tempfile.mkdtemp())
        self._build_repo(self.repo)
        # Make deployed bytes match source.
        shutil.copytree(self.repo / "art", self.deployed / "art")
        shutil.copytree(self.repo / "resources", self.deployed / "resources")

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.deployed, ignore_errors=True)

    def _build_repo(self, root: Path) -> None:
        flag = root / "resources/images/icons/flags/Flag_Foo.png"
        portrait = root / "resources/images/icons/singleplayer/cpai_avatar_foo_bar.png"
        hires = root / "art/ui/leaders/bar.png"
        for p in (flag, portrait, hires):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_tiny_png(2, 2))
        (root / "a_new_world.html").write_text(
            "<!-- ── Foos ── -->\n"
            '<img class="flag-img" src="resources/images/icons/flags/Flag_Foo.png" alt="">\n'
            '<img class="portrait-img" src="resources/images/icons/singleplayer/cpai_avatar_foo_bar.png" alt="">\n',
            encoding="utf-8",
        )
        (root / "data").mkdir(parents=True, exist_ok=True)
        (root / "data/civmods.xml").write_text(
            "<civmods><Civ>"
            "<Name>ANWFoos</Name>"
            "<HomeCityFlagIconWPF>resources/images/icons/flags/Flag_Foo.png</HomeCityFlagIconWPF>"
            "<HomeCityPreviewWPF>resources/images/icons/singleplayer/cpai_avatar_foo_bar.png</HomeCityPreviewWPF>"
            "</Civ></civmods>",
            encoding="utf-8",
        )
        # Plug a synthetic civ name into the section override map at runtime
        inv_mod._SECTION_OVERRIDES["Foos"] = "ANWFoos"

    def test_inventory_includes_civ(self):
        inv = inv_mod.build_inventory(self.repo, self.deployed)
        self.assertIn("ANWFoos", inv["civs"])
        rec = inv["civs"]["ANWFoos"]
        self.assertEqual(rec["html_flag"],
                          "resources/images/icons/flags/Flag_Foo.png")
        self.assertEqual(rec["civmods_portrait_wpf"],
                          "resources/images/icons/singleplayer/cpai_avatar_foo_bar.png")
        self.assertTrue(rec["art_portrait_hires"].endswith("/bar.png"))

    def test_run_all_passes_clean_repo(self):
        report = vp.run_all(self.repo, self.deployed, civ_filter=None)
        self.assertEqual(report["civ_count"], 1)
        # Should pass: header, civmods match, source-vs-deployed, hires linkage
        self.assertEqual(report["summary"]["FAIL"], 0,
                          msg="\n".join(str(r) for r in report["rows"] if r["status"] == "FAIL"))

    def test_html_civmods_mismatch_is_FAIL(self):
        # Mutate civmods to point at a different file
        path = self.repo / "data/civmods.xml"
        path.write_text(
            path.read_text(encoding="utf-8").replace("Flag_Foo", "Flag_Bar"),
            encoding="utf-8",
        )
        report = vp.run_all(self.repo, self.deployed, civ_filter=None)
        flag_rows = [r for r in report["rows"] if r["check"] == "html_vs_civmods.flag"]
        self.assertTrue(any(r["status"] == "FAIL" for r in flag_rows))

    def test_deployed_drift_detected(self):
        # Mutate the deployed flag bytes
        df = self.deployed / "resources/images/icons/flags/Flag_Foo.png"
        df.write_bytes(_tiny_png(3, 3, color=(255, 0, 0)))
        report = vp.run_all(self.repo, self.deployed, civ_filter=None)
        drift = [r for r in report["rows"]
                 if r["check"] == "source_vs_deployed" and r["status"] == "FAIL"]
        self.assertTrue(drift, msg="should have detected drift")

    def test_jpeg_disguised_as_png_is_FAIL(self):
        bad = self.repo / "resources/images/icons/flags/Flag_Foo.png"
        bad.write_bytes(_tiny_jpeg())
        # Same in deployed too so source_vs_deployed still passes
        (self.deployed / "resources/images/icons/flags/Flag_Foo.png").write_bytes(_tiny_jpeg())
        report = vp.run_all(self.repo, self.deployed, civ_filter=None)
        bad_rows = [r for r in report["rows"]
                     if r["check"] == "html_exists" and r["status"] == "FAIL"]
        self.assertTrue(any("PNG magic" in r["detail"] for r in bad_rows))

    def test_civ_filter_limits_scope(self):
        report = vp.run_all(self.repo, self.deployed, civ_filter="ANWFoos")
        civs = {r.get("civ") for r in report["rows"] if r.get("civ")}
        self.assertEqual(civs - {None}, {"ANWFoos"})

    def test_civ_filter_unknown_civ_returns_empty(self):
        report = vp.run_all(self.repo, self.deployed, civ_filter="ANWBogus")
        per_civ = [r for r in report["rows"] if r.get("civ")]
        self.assertEqual(per_civ, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
