"""Tests for tools.validation.extract_html_reference (Phase 1)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation.extract_html_reference import (  # noqa: E402
    BLOCKER,
    MAJOR,
    MINOR,
    Divergence,
    _exit_code,
    _normalize_civ_token,
    build_matrix,
    canonical_civ_id,
    parse_html,
    slugify,
)

HTML_PATH = REPO / "a_new_world.html"
REQUIRES_HTML = pytest.mark.skipif(
    not HTML_PATH.exists(),
    reason="a_new_world.html missing; cannot run live HTML tests.",
)


def test_slugify_normalizes_punctuation() -> None:
    assert slugify("French Louis XVIII Bourbon") == "french-louis-xviii-bourbon"
    assert slugify("Russians \u2014 Ivan Terrible") == "russians-ivan-terrible"
    assert slugify("") == ""


def test_canonical_civ_id_uses_data_name() -> None:
    assert canonical_civ_id("British Elizabeth") == "british-elizabeth"


@pytest.mark.parametrize(
    "engine,expected",
    [
        ("XPAztec", "aztecs"),
        ("ANWAztecs", "aztecs"),
        ("DEAmericans", "usa"),
        ("ANWUSA", "usa"),
        ("XPSioux", "lakota"),
        ("ANWLakota", "lakota"),
        ("XPIroquois", "haudenosaunee"),
        ("ANWHaudenosaunee", "haudenosaunee"),
        ("DESwedish", "swedes"),
        ("ANWSwedes", "swedes"),
        ("", ""),
    ],
)
def test_normalize_civ_token_collapses_variants(engine: str, expected: str) -> None:
    assert _normalize_civ_token(engine) == expected


def test_exit_code_priority_blocker_over_major() -> None:
    findings = [
        Divergence(MAJOR, "doctrine", "x", "m"),
        Divergence(BLOCKER, "civmods", None, "m"),
    ]
    assert _exit_code(findings, strict=False) == 1


def test_exit_code_major_only() -> None:
    findings = [Divergence(MAJOR, "doctrine", "x", "m")]
    assert _exit_code(findings, strict=False) == 2


def test_exit_code_strict_minor() -> None:
    findings = [Divergence(MINOR, "lobby_picker", None, "m")]
    assert _exit_code(findings, strict=False) == 0
    assert _exit_code(findings, strict=True) == 3


def test_exit_code_clean() -> None:
    assert _exit_code([], strict=True) == 0


@REQUIRES_HTML
def test_parse_html_finds_all_46_civs() -> None:
    civs, warnings = parse_html(HTML_PATH)
    assert len(civs) == 46, f"Expected 46 civs, got {len(civs)}; warnings={warnings}"
    # No duplicates
    ids = [c.canonical_id for c in civs]
    assert len(ids) == len(set(ids))


@REQUIRES_HTML
def test_parse_html_extracts_known_civ() -> None:
    civs, _ = parse_html(HTML_PATH)
    by_id = {c.canonical_id: c for c in civs}
    aztec = by_id["aztecs-montezuma"]
    assert aztec.civ_token == "XPAztec"
    assert "Jaguar Knight" in aztec.elite_units
    assert aztec.playstyle_doctrine == "Jungle Guerrilla Network"
    assert aztec.walling_doctrine == "Mobile - No Walls" or aztec.walling_doctrine.startswith("Mobile")


@REQUIRES_HTML
def test_build_matrix_doctrine_index_consistent() -> None:
    civs, _ = parse_html(HTML_PATH)
    matrix = build_matrix(civs, HTML_PATH, leader_xs_index={})
    # Every doctrine entry's civ_ids should refer to civs that exist.
    for slug, entry in matrix["doctrines"].items():
        for civ_id in entry["civ_ids"]:
            assert civ_id in matrix["civs"]
    # And each civ's doctrine_id (if non-empty) must appear in the doctrines map.
    for civ_id, civ in matrix["civs"].items():
        slug = civ["doctrine_id"]
        if slug:
            assert slug in matrix["doctrines"]


@REQUIRES_HTML
def test_build_matrix_json_serializable() -> None:
    civs, _ = parse_html(HTML_PATH)
    matrix = build_matrix(civs, HTML_PATH, leader_xs_index={})
    blob = json.dumps(matrix, ensure_ascii=False)
    assert "Aztecs Montezuma" in blob
    assert matrix["civ_count"] == len(matrix["civs"])
