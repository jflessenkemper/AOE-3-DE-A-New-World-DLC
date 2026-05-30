"""Tests for the home-city visual/pathdata namespace validator.

Regression guard for the "floating citizens" bug. The shipped repo must
always pass; the synthetic fixtures here exercise the failure paths so the
validator's behaviour is locked in.
"""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path
import unittest

from tools.validation.validate_homecity_visuals import (
    first_segment,
    validate_homecity_visuals,
)


def _homecity_xml(
    *,
    civ: str = "ANWExample",
    visual: str = "british\\british_homecity.xml",
    watervisual: str = "british\\british_homecity_water.xml",
    backgroundvisual: str = "british\\british_background.xml",
    pathdata: str = "british\\pathable_area_object.gr2",
    camera: str = "british\\british_homecity_camera.cam",
    widescreencamera: str = "british\\british_homecity_widescreencamera.cam",
) -> str:
    return textwrap.dedent(
        f"""\
        <?xml version='1.0' encoding='utf-8'?>
        <homecity>
          <civ>{civ}</civ>
          <visual>{visual}</visual>
          <watervisual>{watervisual}</watervisual>
          <backgroundvisual>{backgroundvisual}</backgroundvisual>
          <pathdata>{pathdata}</pathdata>
          <camera>{camera}</camera>
          <widescreencamera>{widescreencamera}</widescreencamera>
        </homecity>
        """
    )


class FirstSegmentTests(unittest.TestCase):
    def test_strips_backslash_path(self) -> None:
        self.assertEqual(first_segment("british\\british_homecity.xml"), "british")

    def test_strips_forward_slash_path(self) -> None:
        self.assertEqual(first_segment("revolution/pathable_area.gr2"), "revolution")

    def test_lowercases(self) -> None:
        self.assertEqual(first_segment("British\\Asset.xml"), "british")

    def test_empty(self) -> None:
        self.assertEqual(first_segment(""), "")


class ValidateHomecityVisualsTests(unittest.TestCase):
    def make_repo(self, files: dict[str, str]) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo_root = Path(temp_dir.name)
        data_root = repo_root / "data"
        data_root.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (data_root / name).write_text(content, encoding="utf-8")
        return repo_root

    def test_accepts_consistent_namespace(self) -> None:
        repo_root = self.make_repo({"anwhomecityexample.xml": _homecity_xml()})
        self.assertEqual(validate_homecity_visuals(repo_root), [])

    def test_accepts_revolution_consistent_namespace(self) -> None:
        repo_root = self.make_repo(
            {
                "anwhomecitymexicans.xml": _homecity_xml(
                    civ="ANWMexicans",
                    visual="revolution\\revolution_homecity.xml",
                    watervisual="revolution\\revolution_homecity_water.xml",
                    backgroundvisual="revolution\\revolution_background.xml",
                    pathdata="revolution\\pathable_area.gr2",
                    camera="revolution\\revolution_homecity_camera.cam",
                    widescreencamera="revolution\\revolution_homecity_camera.cam",
                )
            }
        )
        self.assertEqual(validate_homecity_visuals(repo_root), [])

    def test_detects_floating_citizens_bug(self) -> None:
        # Classic floating-citizens scenario: British visual + revolution pathdata.
        repo_root = self.make_repo(
            {
                "anwhomecityexample.xml": _homecity_xml(
                    pathdata="revolution\\pathable_area.gr2",
                )
            }
        )
        issues = validate_homecity_visuals(repo_root)
        self.assertEqual(len(issues), 1)
        self.assertIn("citizens will float", issues[0])
        self.assertIn("'revolution'", issues[0])
        self.assertIn("'british'", issues[0])

    def test_detects_camera_namespace_mismatch(self) -> None:
        repo_root = self.make_repo(
            {
                "anwhomecityexample.xml": _homecity_xml(
                    camera="spanish\\spanish_homecity_camera.cam",
                )
            }
        )
        issues = validate_homecity_visuals(repo_root)
        self.assertEqual(len(issues), 1)
        self.assertIn("<camera>", issues[0])
        self.assertIn("'spanish'", issues[0])

    def test_reports_missing_pathdata(self) -> None:
        repo_root = self.make_repo(
            {
                "anwhomecitybroken.xml": (
                    "<?xml version='1.0' encoding='utf-8'?>\n"
                    "<homecity><civ>X</civ><visual>british\\british_homecity.xml</visual></homecity>\n"
                )
            }
        )
        issues = validate_homecity_visuals(repo_root)
        self.assertEqual(issues, ["data/anwhomecitybroken.xml: missing <pathdata>"])

    def test_reports_missing_visual(self) -> None:
        repo_root = self.make_repo(
            {
                "anwhomecitybroken.xml": (
                    "<?xml version='1.0' encoding='utf-8'?>\n"
                    "<homecity><civ>X</civ><pathdata>british\\pathable_area_object.gr2</pathdata></homecity>\n"
                )
            }
        )
        issues = validate_homecity_visuals(repo_root)
        self.assertEqual(issues, ["data/anwhomecitybroken.xml: missing <visual>"])

    def test_reports_xml_parse_error(self) -> None:
        repo_root = self.make_repo({"anwhomecitybroken.xml": "<not valid"})
        issues = validate_homecity_visuals(repo_root)
        self.assertEqual(len(issues), 1)
        self.assertIn("XML parse error", issues[0])

    def test_real_repo_passes(self) -> None:
        # Lock-in: the actual mod must always pass this validator.
        from tools.validation.common import REPO_ROOT

        self.assertEqual(validate_homecity_visuals(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
