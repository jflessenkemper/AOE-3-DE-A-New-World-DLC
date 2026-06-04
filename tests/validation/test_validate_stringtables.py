from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from tools.validation.validate_stringtables import validate_civ_display_names, validate_stringmods


VALID_STRINGMODS = """<root>
  <StringTable>
    <Language name='english'>
      <String _locID='400001'>Valid</String>
    </Language>
  </StringTable>
</root>
"""

INVALID_STRINGMODS = """<root>
  <StringTable>
    <Language name='english'>
      <String _locID='abc'>Bad</String>
      <String _locID='abc'></String>
    </Language>
  </StringTable>
</root>
"""

# Real-world regression: <String> entries stranded AFTER </Language> but before
# </StringTable>. Well-formed XML, but the engine never loads them so the locids
# resolve to empty (e.g. civ display names showing a blank nation title).
ORPHANED_STRINGMODS = """<root>
  <StringTable>
    <Language name='english'>
      <String _locID='400001'>Inside</String>
    </Language>
    <String _locID='410009'>Inca Empire</String>
    <String _locID='410003'>Dutch Republic</String>
  </StringTable>
</root>
"""


class ValidateStringtablesTests(unittest.TestCase):
    def make_stringmods(self, language: str, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        file_path = Path(temp_dir.name) / "data" / "strings" / language / "stringmods.xml"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_accepts_valid_stringmods(self) -> None:
        file_path = self.make_stringmods("english", VALID_STRINGMODS)
        self.assertEqual(validate_stringmods(file_path), [])

    def test_reports_invalid_locids_and_empty_strings(self) -> None:
        file_path = self.make_stringmods("english", INVALID_STRINGMODS)
        issues = validate_stringmods(file_path)
        self.assertEqual(
            issues,
            [
                "data/strings/english/stringmods.xml: invalid _locID values: abc",
                "data/strings/english/stringmods.xml: duplicate _locID values: abc",
                "data/strings/english/stringmods.xml: empty string values for locids: abc",
            ],
        )

    def test_reports_strings_outside_language_scope(self) -> None:
        file_path = self.make_stringmods("english", ORPHANED_STRINGMODS)
        issues = validate_stringmods(file_path)
        self.assertEqual(
            issues,
            [
                "data/strings/english/stringmods.xml: 2 <String> entries are outside any "
                "<Language> scope (engine will not load them): 410009, 410003",
            ],
        )


CIVMODS_XML = """<civmods>
  <civ>
    <name>ANWInca</name>
    <displaynameid>410001</displaynameid>
  </civ>
  <civ>
    <name>ANWMissing</name>
    <displaynameid>499999</displaynameid>
  </civ>
  <civ>
    <name>British</name>
  </civ>
</civmods>
"""

STRINGMODS_WITH_INCA = """<root>
  <StringTable>
    <Language name='english'>
      <String _locID='410001'>Inca Empire</String>
    </Language>
  </StringTable>
</root>
"""


class ValidateCivDisplayNamesTests(unittest.TestCase):
    def make_temp_repo(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo_root = Path(temp_dir.name)

        civmods = repo_root / "data" / "civmods.xml"
        civmods.parent.mkdir(parents=True, exist_ok=True)
        civmods.write_text(CIVMODS_XML, encoding="utf-8")

        stringmods = repo_root / "data" / "strings" / "english" / "stringmods.xml"
        stringmods.parent.mkdir(parents=True, exist_ok=True)
        stringmods.write_text(STRINGMODS_WITH_INCA, encoding="utf-8")

        return repo_root

    def test_resolving_civ_passes_missing_civ_fails(self) -> None:
        repo_root = self.make_temp_repo()
        issues = validate_civ_display_names(repo_root)
        # ANWInca resolves; ANWMissing (>=400000) does not; British has no displaynameid (skip)
        self.assertEqual(
            issues,
            [
                "data/civmods.xml: civ 'ANWMissing' displaynameid 499999 does not resolve to a non-empty string"
            ],
        )

    def test_absent_civmods_returns_empty(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        issues = validate_civ_display_names(Path(temp_dir.name))
        self.assertEqual(issues, [])
