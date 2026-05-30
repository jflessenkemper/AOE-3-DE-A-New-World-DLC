from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from tools.validation.validate_civ_crossrefs import validate_civ_crossrefs


GOOD_CIVMODS = """<civmods>
  <Civ>
    <Name>ANWExample</Name>
    <DisplayNameID>490001</DisplayNameID>
    <RolloverNameID>490002</RolloverNameID>
    <AgeTech>
      <Age>Age0</Age>
      <Tech>ANWAge0Example</Tech>
    </AgeTech>
    <PostIndustrialTech>ANWPostIndustrialExample</PostIndustrialTech>
  </Civ>
</civmods>
"""

GOOD_TECHTREE = """<techtreemods>
  <tech name='ANWAge0Example'><dbid>1</dbid></tech>
  <tech name='ANWPostIndustrialExample'><dbid>2</dbid></tech>
</techtreemods>
"""

GOOD_STRINGS = """<root><StringTable><Language name='english'>
  <String _locID='490001'>Example</String>
  <String _locID='490002'>Example rollover</String>
</Language></StringTable></root>
"""


class ValidateCivCrossrefsTests(unittest.TestCase):
    def make_repo(self, civmods: str, techtree: str, strings: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        repo_root = Path(temp_dir.name)
        data_root = repo_root / "data"
        (data_root / "strings" / "english").mkdir(parents=True, exist_ok=True)
        (data_root / "civmods.xml").write_text(civmods, encoding="utf-8")
        (data_root / "techtreemods.xml").write_text(techtree, encoding="utf-8")
        (data_root / "strings" / "english" / "stringmods.xml").write_text(strings, encoding="utf-8")
        return repo_root

    def test_accepts_valid_string_and_tech_references(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, GOOD_TECHTREE, GOOD_STRINGS)
        self.assertEqual(validate_civ_crossrefs(repo_root), [])

    def test_reports_missing_string_ids_and_custom_techs(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, "<techtreemods></techtreemods>", GOOD_STRINGS)
        issues = validate_civ_crossrefs(repo_root)
        self.assertEqual(
            issues,
            [
                "ANWExample: AgeTech references missing tech 'ANWAge0Example'",
                "ANWExample: PostIndustrialTech references missing tech 'ANWPostIndustrialExample'",
            ],
        )

    def test_reports_missing_string_locids(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, GOOD_TECHTREE, "<root><StringTable><Language name='english'></Language></StringTable></root>")
        issues = validate_civ_crossrefs(repo_root)
        self.assertEqual(
            issues,
            [
                "ANWExample: RolloverNameID references missing string ID 490002",
            ],
        )

    def test_can_optionally_require_display_name_ids(self) -> None:
      repo_root = self.make_repo(GOOD_CIVMODS, GOOD_TECHTREE, "<root><StringTable><Language name='english'><String _locID='490002'>Example rollover</String></Language></StringTable></root>")
      issues = validate_civ_crossrefs(repo_root, validate_display_name_ids=True)
      self.assertEqual(
        issues,
        ["ANWExample: DisplayNameID references missing string ID 490001"],
      )

    def test_allows_profile_specific_missing_string_ids(self) -> None:
      repo_root = self.make_repo(GOOD_CIVMODS, GOOD_TECHTREE, "<root><StringTable><Language name='english'></Language></StringTable></root>")
      issues = validate_civ_crossrefs(repo_root, allowed_missing_string_ids={"490002"})
      self.assertEqual(issues, [])
