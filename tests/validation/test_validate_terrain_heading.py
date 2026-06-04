from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from tools.validation.validate_terrain_heading import (
    ANW_CIVS,
    BASE_CIVS,
    REVOLUTION_CIVS,
    validate_terrain_heading,
)


HEADER_FIXTURE = """
extern int     cANWTerrainAny          = 0;
extern int     cANWTerrainCoast        = 1;
extern int     cANWTerrainRiver        = 2;
extern int     cANWTerrainPlain        = 4;
extern int     cANWHeadingAny          = 0;
extern int     cANWHeadingAlongCoast   = 1;
extern int     cANWHeadingFrontierPush = 3;
"""


def _all_civs_apply_body() -> str:
    """Synthesize a minimal but complete anwApplyBuildStyleForActiveCiv()
    body that covers every civ the validator expects.
    """
    parts: list[str] = []
    is_first = True
    for civ in BASE_CIVS:
        keyword = "if" if is_first else "else if"
        is_first = False
        parts.append(
            dedent(
                f"""\
                {keyword} (cMyCiv == {civ})
                {{
                   anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.30);
                   anwSetExpansionHeading(cANWHeadingFrontierPush, 0.25);
                }}"""
            )
        )
    for rvlt in REVOLUTION_CIVS:
        parts.append(
            dedent(
                f"""\
                else if (rvltName == "{rvlt}")
                {{
                   anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainPlain, 0.40);
                   anwSetExpansionHeading(cANWHeadingAlongCoast, 0.30);
                }}"""
            )
        )
    for anw in ANW_CIVS:
        parts.append(
            dedent(
                f"""\
                else if (rvltName == "{anw}")
                {{
                   anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.30);
                   anwSetExpansionHeading(cANWHeadingFrontierPush, 0.25);
                }}"""
            )
        )
    return "\n".join(parts)


def _wrap_apply_body(body: str) -> str:
    return dedent(
        f"""\
        void anwApplyBuildStyleForActiveCiv(void)
        {{
           string rvltName = kbGetCivName(cMyCiv);
           anwResetBuildStyleProfile();

        {body}
        }}
        """
    )


class ValidateTerrainHeadingTests(unittest.TestCase):
    def make_repo(self, header: str, leader_common: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "game" / "ai").mkdir(parents=True)
        (root / "game" / "ai" / "leaders").mkdir(parents=True)
        (root / "game" / "ai" / "aiHeader.xs").write_text(header, encoding="utf-8")
        (root / "game" / "ai" / "leaders" / "leaderCommon.xs").write_text(
            leader_common, encoding="utf-8"
        )
        return root

    def test_accepts_complete_wiring(self) -> None:
        repo = self.make_repo(HEADER_FIXTURE, _wrap_apply_body(_all_civs_apply_body()))
        self.assertEqual(validate_terrain_heading(repo), [])

    def test_reports_missing_civ_branch(self) -> None:
        # Drop the first base-civ branch (cCivBritish) entirely.
        body = _all_civs_apply_body()
        # Locate the cCivBritish if-block and excise it.
        marker = "if (cMyCiv == cCivBritish)"
        start = body.index(marker)
        # Find the matching closing brace for this block.
        brace_open = body.index("{", start)
        depth = 1
        i = brace_open + 1
        while depth > 0:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
            i += 1
        # i is now one past the closing brace.
        body = body[:start] + body[i:].lstrip("\n")
        # The next branch (cCivChinese) was an `else if` — promote it to `if`.
        body = body.replace("else if (cMyCiv == cCivChinese)", "if (cMyCiv == cCivChinese)", 1)
        repo = self.make_repo(HEADER_FIXTURE, _wrap_apply_body(body))
        issues = validate_terrain_heading(repo)
        self.assertIn(
            "cCivBritish: no branch in anwApplyBuildStyleForActiveCiv()",
            issues,
        )

    def test_reports_unknown_terrain_constant(self) -> None:
        # Replace the FIRST anwSetPreferredTerrain — that lives inside the
        # cCivBritish branch (first base-civ in BASE_CIVS).
        body = _all_civs_apply_body().replace(
            "anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.30)",
            "anwSetPreferredTerrain(cANWTerrainTundra, cANWTerrainRiver, 0.30)",
            1,
        )
        repo = self.make_repo(HEADER_FIXTURE, _wrap_apply_body(body))
        issues = validate_terrain_heading(repo)
        self.assertTrue(
            any("cCivBritish" in i and "cANWTerrainTundra" in i for i in issues),
            f"expected unknown-terrain finding, got {issues!r}",
        )

    def test_reports_out_of_range_strength(self) -> None:
        body = _all_civs_apply_body().replace(
            "anwSetExpansionHeading(cANWHeadingFrontierPush, 0.25)",
            "anwSetExpansionHeading(cANWHeadingFrontierPush, 1.5)",
            1,
        )
        repo = self.make_repo(HEADER_FIXTURE, _wrap_apply_body(body))
        issues = validate_terrain_heading(repo)
        self.assertTrue(
            any("strength 1.5 outside" in i for i in issues),
            f"expected out-of-range finding, got {issues!r}",
        )


if __name__ == "__main__":
    unittest.main()
