"""Unit-test stub for ``anw_visual_capture``.

Monkeypatches ``screenshot()`` and ``input()`` to confirm the 5 expected
screenshot files would be written when the user walks through every step.
No game required.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Make the sibling module importable regardless of how unittest is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import anw_visual_capture as avc  # noqa: E402


class VisualCaptureFlowTests(unittest.TestCase):
    """Confirm every step prompts the user and writes the expected file."""

    EXPECTED = [
        "01_diplomacy.png",
        "02_scoreboard.png",
        "03_homecity.png",
        "04_ally_homecity.png",
        "05_postgame.png",
    ]

    def test_step_filenames_match_spec(self):
        """Guard against accidental reorder/rename of the capture sequence."""
        names = [fname for fname, _ in avc.STEPS]
        self.assertEqual(names, self.EXPECTED)

    def test_run_capture_writes_all_five(self):
        """Walking through every step writes all five PNGs."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ANWBritish"
            input_calls: list[str] = []
            shot_paths: list[Path] = []

            def fake_input(_prompt: str = "") -> str:
                input_calls.append(_prompt)
                return ""

            def fake_screenshot(path: Path, **_kw):
                path = Path(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                # Write a fake PNG header so size > 0.
                path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
                shot_paths.append(path)
                return path

            written = avc.run_capture(
                "ANWBritish", out_dir,
                input_fn=fake_input,
                screenshot_fn=fake_screenshot,
            )

        self.assertEqual(len(input_calls), 5)
        self.assertEqual(len(written), 5)
        self.assertEqual(
            [p.name for p in written],
            self.EXPECTED,
        )
        # screenshot_fn was called with the exact target paths in order
        self.assertEqual([p.name for p in shot_paths], self.EXPECTED)

    def test_list_civs_returns_46(self):
        """``list_civs()`` exposes the 46 ANW civ tokens."""
        civs = avc.list_civs()
        self.assertEqual(len(civs), 46)
        self.assertTrue(all(c.startswith("ANW") for c in civs))
        self.assertIn("ANWBritish", civs)


if __name__ == "__main__":
    unittest.main()
