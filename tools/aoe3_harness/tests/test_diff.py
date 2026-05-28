"""Unit tests for tools/aoe3_harness/diff.py.

All tests generate synthetic in-memory PIL images saved to a temporary
directory — no external files or game assets required.

Run with::

    cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
    python3 -m pytest tools/aoe3_harness/tests/test_diff.py -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage

# Ensure the repo root is on sys.path so the package can be imported directly.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pil_available() -> bool:
    """Return True if Pillow is installed."""
    try:
        import PIL  # noqa: F401
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def _save_image(img: "PILImage.Image", path: Path) -> None:
    """Save a PIL Image to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestDiffIdentical(unittest.TestCase):
    """Identical images produce 0% changed, zero delta, no bbox."""

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_identical_same_file(self) -> None:
        """Comparing a file to itself should produce zero change."""
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            img = Image.new("RGB", (100, 100), color=(128, 64, 32))
            p = Path(tmp) / "img.png"
            _save_image(img, p)

            result = compare_screenshots(p, p)

        self.assertAlmostEqual(result.pct_pixels_changed, 0.0)
        self.assertEqual(result.max_color_delta, 0)
        self.assertIsNone(result.bbox)
        self.assertIsNone(result.output_path)

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_identical_copies(self) -> None:
        """Two pixel-identical images should produce zero change."""
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            img = Image.new("RGB", (50, 50), color=(200, 100, 50))
            p1 = Path(tmp) / "a.png"
            p2 = Path(tmp) / "b.png"
            _save_image(img, p1)
            _save_image(img.copy(), p2)

            result = compare_screenshots(p1, p2)

        self.assertAlmostEqual(result.pct_pixels_changed, 0.0)
        self.assertEqual(result.max_color_delta, 0)
        self.assertIsNone(result.bbox)


class TestDiffBlackVsWhite(unittest.TestCase):
    """All-black vs all-white → 100% changed, max delta 255, full-image bbox."""

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_full_change(self) -> None:
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            black = Image.new("RGB", (50, 50), color=(0, 0, 0))
            white = Image.new("RGB", (50, 50), color=(255, 255, 255))
            p_black = Path(tmp) / "black.png"
            p_white = Path(tmp) / "white.png"
            _save_image(black, p_black)
            _save_image(white, p_white)

            result = compare_screenshots(p_black, p_white)

        self.assertAlmostEqual(result.pct_pixels_changed, 1.0)
        self.assertEqual(result.max_color_delta, 255)
        self.assertIsNotNone(result.bbox)
        # bbox should span the full 50x50 image (exclusive end = 50)
        self.assertEqual(result.bbox, (0, 0, 50, 50))

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_reverse_order(self) -> None:
        """white vs black should also give 100% changed (abs delta is symmetric)."""
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            black = Image.new("RGB", (20, 20), color=(0, 0, 0))
            white = Image.new("RGB", (20, 20), color=(255, 255, 255))
            p_b = Path(tmp) / "b.png"
            p_w = Path(tmp) / "w.png"
            _save_image(black, p_b)
            _save_image(white, p_w)

            result = compare_screenshots(p_w, p_b)

        self.assertAlmostEqual(result.pct_pixels_changed, 1.0)


class TestDiffSmallRegion(unittest.TestCase):
    """Small changed region — bbox correctly identifies it, ~1% changed."""

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_10x10_block_in_100x100(self) -> None:
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots, CHANNEL_DELTA_THRESHOLD

        with tempfile.TemporaryDirectory() as tmp:
            # 100×100 uniform grey
            before = Image.new("RGB", (100, 100), color=(100, 100, 100))
            after  = before.copy()

            # Change a 10×10 block at columns 20–29, rows 30–39
            # Delta must exceed CHANNEL_DELTA_THRESHOLD (default 5) per channel
            delta_value = CHANNEL_DELTA_THRESHOLD + 10   # safely above threshold
            changed_color = (
                100 + delta_value,
                100 + delta_value,
                100 + delta_value,
            )
            for y in range(30, 40):
                for x in range(20, 30):
                    after.putpixel((x, y), changed_color)

            p_before = Path(tmp) / "before.png"
            p_after  = Path(tmp) / "after.png"
            _save_image(before, p_before)
            _save_image(after,  p_after)

            p_heatmap = Path(tmp) / "heatmap.png"
            result = compare_screenshots(p_before, p_after, output_path=p_heatmap)

            # 10×10 = 100 pixels changed out of 100×100 = 10000 → 1%
            self.assertAlmostEqual(result.pct_pixels_changed, 0.01)
            # bbox: left=20, top=30, right=30, bottom=40 (exclusive ends)
            self.assertIsNotNone(result.bbox)
            self.assertEqual(result.bbox, (20, 30, 30, 40))
            # Heatmap was written (check inside 'with' so tmp dir still exists)
            self.assertIsNotNone(result.output_path)
            self.assertTrue(result.output_path.exists())
            self.assertGreater(result.output_path.stat().st_size, 0)

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_single_pixel_change(self) -> None:
        """A single changed pixel should have a 1-pixel bbox."""
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots, CHANNEL_DELTA_THRESHOLD

        with tempfile.TemporaryDirectory() as tmp:
            before = Image.new("RGB", (10, 10), color=(0, 0, 0))
            after  = before.copy()
            after.putpixel((5, 5), (255, 255, 255))   # single pixel at (5,5)

            p1 = Path(tmp) / "b.png"
            p2 = Path(tmp) / "a.png"
            _save_image(before, p1)
            _save_image(after,  p2)

            result = compare_screenshots(p1, p2)

        self.assertIsNotNone(result.bbox)
        # Single pixel: left=5, top=5, right=6, bottom=6
        self.assertEqual(result.bbox, (5, 5, 6, 6))
        expected_pct = 1.0 / 100.0
        self.assertAlmostEqual(result.pct_pixels_changed, expected_pct)


class TestDiffHeatmapOutput(unittest.TestCase):
    """Heatmap PNG is created when output_path is provided."""

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_heatmap_created(self) -> None:
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            black = Image.new("RGB", (20, 20), color=(0, 0, 0))
            white = Image.new("RGB", (20, 20), color=(255, 255, 255))
            p_b = Path(tmp) / "b.png"
            p_w = Path(tmp) / "w.png"
            _save_image(black, p_b)
            _save_image(white, p_w)

            # Nested output dir to verify mkdir -p behaviour
            p_out = Path(tmp) / "subdir" / "heatmap.png"
            result = compare_screenshots(p_b, p_w, output_path=p_out)

            # Check inside 'with' so the tmp dir still exists
            self.assertIsNotNone(result.output_path)
            self.assertTrue(result.output_path.exists())
            self.assertGreater(result.output_path.stat().st_size, 0)

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_no_heatmap_when_output_none(self) -> None:
        """output_path=None should not create any file."""
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            img = Image.new("RGB", (10, 10), color=(0, 0, 0))
            p = Path(tmp) / "img.png"
            _save_image(img, p)

            result = compare_screenshots(p, p, output_path=None)

        self.assertIsNone(result.output_path)


class TestDiffBelowThreshold(unittest.TestCase):
    """Pixels whose delta is <= CHANNEL_DELTA_THRESHOLD are NOT counted as changed."""

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_sub_threshold_delta_not_counted(self) -> None:
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots, CHANNEL_DELTA_THRESHOLD

        with tempfile.TemporaryDirectory() as tmp:
            base_val = 100
            before = Image.new("RGB", (10, 10), color=(base_val, base_val, base_val))
            # Delta exactly at threshold (not strictly greater) → should NOT be changed
            after  = Image.new("RGB", (10, 10),
                                color=(base_val + CHANNEL_DELTA_THRESHOLD,
                                       base_val,
                                       base_val))
            p1 = Path(tmp) / "b.png"
            p2 = Path(tmp) / "a.png"
            _save_image(before, p1)
            _save_image(after,  p2)

            result = compare_screenshots(p1, p2)

        # delta == threshold → NOT > threshold → zero changed pixels
        self.assertAlmostEqual(result.pct_pixels_changed, 0.0)
        self.assertIsNone(result.bbox)

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_above_threshold_delta_counted(self) -> None:
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots, CHANNEL_DELTA_THRESHOLD

        with tempfile.TemporaryDirectory() as tmp:
            base_val = 100
            before = Image.new("RGB", (10, 10), color=(base_val, base_val, base_val))
            # Delta one above threshold → all pixels should be changed
            after  = Image.new("RGB", (10, 10),
                                color=(base_val + CHANNEL_DELTA_THRESHOLD + 1,
                                       base_val,
                                       base_val))
            p1 = Path(tmp) / "b.png"
            p2 = Path(tmp) / "a.png"
            _save_image(before, p1)
            _save_image(after,  p2)

            result = compare_screenshots(p1, p2)

        self.assertAlmostEqual(result.pct_pixels_changed, 1.0)


class TestDiffFileNotFound(unittest.TestCase):
    """FileNotFoundError raised for missing input files."""

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_missing_before(self) -> None:
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            img = Image.new("RGB", (10, 10))
            p_exists = Path(tmp) / "exists.png"
            _save_image(img, p_exists)
            p_missing = Path(tmp) / "missing.png"

            with self.assertRaises(FileNotFoundError):
                compare_screenshots(p_missing, p_exists)

    @unittest.skipUnless(_pil_available(), "Pillow + numpy not installed")
    def test_missing_after(self) -> None:
        from PIL import Image
        from tools.aoe3_harness.diff import compare_screenshots

        with tempfile.TemporaryDirectory() as tmp:
            img = Image.new("RGB", (10, 10))
            p_exists = Path(tmp) / "exists.png"
            _save_image(img, p_exists)
            p_missing = Path(tmp) / "missing.png"

            with self.assertRaises(FileNotFoundError):
                compare_screenshots(p_exists, p_missing)


if __name__ == "__main__":
    unittest.main()
