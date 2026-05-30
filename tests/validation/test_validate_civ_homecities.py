from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from tools.validation.validate_civ_homecities import validate_civ_homecities


GOOD_CIVMODS = """<civmods>
  <Civ>
    <Name>ANWExample</Name>
    <HomeCityFilename>anwhomecityexample.xml</HomeCityFilename>
  </Civ>
</civmods>
"""

GOOD_HOMECITY = """<homecity>
  <civ>ANWExample</civ>
</homecity>
"""

LOWERCASE_CIVMODS = """<civsmods>
    <civ>
        <name>zpExample</name>
        <homecityfilename>homecityexample.xml</homecityfilename>
    </civ>
</civsmods>
"""

LOWERCASE_HOMECITY = """<homecity>
    <civ>zpExample</civ>
</homecity>
"""

MISMATCHED_HOMECITY = """<homecity>
  <civ>ANWOther</civ>
</homecity>
"""


class ValidateCivHomecitiesTests(unittest.TestCase):
    def make_repo(self, civmods_xml: str, homecities: dict[str, str]) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        repo_root = Path(temp_dir.name)
        data_root = repo_root / "data"
        data_root.mkdir(parents=True, exist_ok=True)
        (data_root / "civmods.xml").write_text(civmods_xml, encoding="utf-8")
        for relative_name, content in homecities.items():
            (data_root / relative_name).write_text(content, encoding="utf-8")
        return repo_root

    def test_accepts_matching_homecity_binding(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, {"anwhomecityexample.xml": GOOD_HOMECITY})
        self.assertEqual(validate_civ_homecities(repo_root), [])

    def test_reports_missing_homecity_file(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, {})
        issues = validate_civ_homecities(repo_root)
        self.assertEqual(
            issues,
            ["ANWExample: HomeCityFilename references missing file data/anwhomecityexample.xml"],
        )

    def test_reports_mismatched_homecity_binding(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, {"anwhomecityexample.xml": MISMATCHED_HOMECITY})
        issues = validate_civ_homecities(repo_root)
        self.assertEqual(
            issues,
            ["ANWExample: data/anwhomecityexample.xml binds to 'ANWOther' instead"],
        )

    def test_reports_orphan_homecity_files(self) -> None:
        repo_root = self.make_repo(
            GOOD_CIVMODS,
            {
                "anwhomecityexample.xml": GOOD_HOMECITY,
                "anwhomecityorphan.xml": GOOD_HOMECITY,
            },
        )
        issues = validate_civ_homecities(repo_root)
        self.assertEqual(
            issues,
            ["Orphan custom home city file not referenced by civmods: data/anwhomecityorphan.xml"],
        )

    def test_supports_lowercase_civ_tags_for_external_repos(self) -> None:
        repo_root = self.make_repo(LOWERCASE_CIVMODS, {"homecityexample.xml": LOWERCASE_HOMECITY})
        self.assertEqual(
            validate_civ_homecities(
                repo_root,
                name_prefixes=None,
                homecity_glob="homecity*.xml",
                allow_missing_homecity_files=True,
            ),
            [],
        )

