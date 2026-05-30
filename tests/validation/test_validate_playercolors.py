"""Tests for the playercolors.xml validator."""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path
import unittest

from tools.validation.validate_playercolors import validate_playercolors


GOOD_CIVMODS = textwrap.dedent(
    """\
    <civmods>
      <Civ>
        <Name>ANWExample</Name>
      </Civ>
    </civmods>
    """
)

GOOD_COLORS = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="utf-8"?>
    <PlayerColors>
      <Color civ="French" leader="Louis XVIII" r="0" g="51" b="102" />
      <Color civ="ANWExample" leader="Example Leader" r="100" g="100" b="100" />
    </PlayerColors>
    """
)


class ValidatePlayercolorsTests(unittest.TestCase):
    def make_repo(self, civmods: str | None, colors: str | None) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo_root = Path(temp_dir.name)
        data_root = repo_root / "data"
        data_root.mkdir(parents=True, exist_ok=True)
        if civmods is not None:
            (data_root / "civmods.xml").write_text(civmods, encoding="utf-8")
        if colors is not None:
            (data_root / "playercolors.xml").write_text(colors, encoding="utf-8")
        return repo_root

    def test_accepts_good_repo(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, GOOD_COLORS)
        self.assertEqual(validate_playercolors(repo_root), [])

    def test_reports_missing_file(self) -> None:
        repo_root = self.make_repo(GOOD_CIVMODS, None)
        issues = validate_playercolors(repo_root)
        self.assertEqual(len(issues), 1)
        self.assertIn("file not found", issues[0])

    def test_reports_duplicate_civ(self) -> None:
        colors = textwrap.dedent(
            """\
            <PlayerColors>
              <Color civ="French" leader="A" r="0" g="0" b="0" />
              <Color civ="French" leader="B" r="0" g="0" b="0" />
              <Color civ="ANWExample" leader="C" r="0" g="0" b="0" />
            </PlayerColors>
            """
        )
        repo_root = self.make_repo(GOOD_CIVMODS, colors)
        issues = validate_playercolors(repo_root)
        self.assertIn("playercolors: duplicate civ entry 'French'", issues)

    def test_reports_duplicate_leader(self) -> None:
        colors = textwrap.dedent(
            """\
            <PlayerColors>
              <Color civ="French" leader="Alice" r="0" g="0" b="0" />
              <Color civ="British" leader="Alice" r="0" g="0" b="0" />
              <Color civ="ANWExample" leader="Bob" r="0" g="0" b="0" />
            </PlayerColors>
            """
        )
        repo_root = self.make_repo(GOOD_CIVMODS, colors)
        issues = validate_playercolors(repo_root)
        self.assertIn("playercolors: duplicate leader entry 'Alice'", issues)

    def test_reports_missing_civmods_civ_color(self) -> None:
        colors = textwrap.dedent(
            """\
            <PlayerColors>
              <Color civ="French" leader="Louis" r="0" g="0" b="0" />
            </PlayerColors>
            """
        )
        repo_root = self.make_repo(GOOD_CIVMODS, colors)
        issues = validate_playercolors(repo_root)
        self.assertIn(
            "playercolors: missing color entry for civmods civ 'ANWExample'",
            issues,
        )

    def test_reports_invalid_channel(self) -> None:
        colors = textwrap.dedent(
            """\
            <PlayerColors>
              <Color civ="French" leader="Louis" r="999" g="0" b="0" />
              <Color civ="ANWExample" leader="X" r="0" g="0" b="0" />
            </PlayerColors>
            """
        )
        repo_root = self.make_repo(GOOD_CIVMODS, colors)
        issues = validate_playercolors(repo_root)
        self.assertIn("playercolors[French]: invalid r channel '999' (must be int 0..255)", issues)

    def test_reports_missing_attributes(self) -> None:
        colors = textwrap.dedent(
            """\
            <PlayerColors>
              <Color civ="French" r="0" g="0" b="0" />
              <Color civ="ANWExample" leader="X" r="0" g="0" b="0" />
            </PlayerColors>
            """
        )
        repo_root = self.make_repo(GOOD_CIVMODS, colors)
        issues = validate_playercolors(repo_root)
        self.assertIn("playercolors[French]: missing leader attribute", issues)

    def test_real_repo_passes(self) -> None:
        from tools.validation.common import REPO_ROOT

        self.assertEqual(validate_playercolors(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()
