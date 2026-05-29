"""Phase 6 canonical mappings for unified 46-ANW validator path.

Single source of truth for validators and tools that need to:
- Iterate all 46 ANW civs uniformly
- Map ANW stems ↔ homecity filenames
- Identify deferred civs (those without HTML sections)

Replaces fragmented dicts like CIV_TO_HOMECITY, _BASE_CIV_HOMECITY, CIV_FILES.

2026-05-09 fix: ``ANW_CIVS`` in ``anw_token_map`` was refactored from a list
of dataclass objects to a ``dict[token, {display, leader}]``. This module
adapts to that shape by building lightweight ``AnwCiv`` namedtuples.

2026-05-10 extension: re-add ``is_revolution`` and ``old_civ_token`` namedtuple
fields. The legacy dataclass-shape `ANW_CIVS` exposed these for downstream
code (notably tools/playtest/expectations.py); the dict-shape refactor lost
them and broke ~50 pytest cases. Both are derivable from ``BASE_CIVS`` /
``REVOLUTION_CIVS`` in ``tools/validation/validate_terrain_heading.py``:
- Base civs: dict-key matches a ``cCiv<Token>`` entry. ``old_civ_token`` is
  the dict-key (e.g. ``British``, ``DEAmericans``).
- Revolution civs: dict-key starts with ``ANW`` and maps to a ``ANW<...>``
  entry. ``old_civ_token`` is the matching ``ANW<...>`` form.
The mapping table below covers all 24 ANW-prefixed revolution civs.
"""
from __future__ import annotations

from collections import namedtuple

from tools.migration.anw_token_map import ANW_CIVS as _ANW_CIVS_DICT


AnwCiv = namedtuple(
    "AnwCiv",
    ["anw_token", "anw_stem", "slug", "display", "leader",
     "new_homecity_filename", "is_revolution", "old_civ_token"],
)


# Map ANW-prefixed revolution token → matching ANW<...> token used in
# leaderCommon.xs / leader_revolution_commanders.xs. The names diverge in
# a handful of cases (e.g. ANWRevFrance → ANWRevFrance); the
# rest are a literal "ANW" → "ANW" prefix swap. Verified against
# BASE_CIVS/REVOLUTION_CIVS in tools/validation/validate_terrain_heading.py.
_ANW_TO_RVLT_OVERRIDES: dict[str, str] = {
    "ANWRevFrance": "ANWRevFrance",
}


def _derive_rvlt_token(anw_token: str) -> str:
    if anw_token in _ANW_TO_RVLT_OVERRIDES:
        return _ANW_TO_RVLT_OVERRIDES[anw_token]
    if anw_token.startswith("ANW"):
        return "ANW" + anw_token[3:]
    return anw_token


# Canonical short-slug map for HTML cross-references. Keys are the civ tokens
# from `ANW_CIVS` in `anw_token_map.py`; values are the slugs that appear in the
# `<!-- ─── {slug} ─── -->` headers in `a_new_world.html`. These match the
# original (pre-dict-refactor) `slug` field on `AnwCiv`. Tools like
# `validate_html_reference.py`, `refresh_dev_subtrees.py`, and `expectations.py`
# look civs up by these slugs, so they MUST match the HTML headers verbatim.
#
# Audit order:
#   - 22 base civs (alphabetical by HTML section)
#   - 24 ANW-prefixed revolution civs with HTML sections
#   - 2 deferred revolution civs (Americans, Mexicans (Revolution)) — listed
#     in `ANW_DEFERRED_SLUGS` so the HTML validator skips section-header checks
_TOKEN_TO_SLUG: dict[str, str] = {
    # Base civs (22)
    "XPAztec":         "Aztecs",
    "British":         "British",
    "Chinese":         "Chinese",
    "Dutch":           "Dutch",
    "DEEthiopians":    "Ethiopians",
    "French":          "French",
    "Germans":         "Germans",
    "XPIroquois":      "Haudenosaunee",
    "DEHausa":         "Hausa",
    "DEInca":          "Inca",
    "Indians":         "Indians",
    "DEItalians":      "Italians",
    "Japanese":        "Japanese",
    "XPSioux":         "Lakota",
    "DEMaltese":       "Maltese",
    "DEMexicans":      "Mexicans",
    "Ottomans":        "Ottomans",
    "Portuguese":      "Portuguese",
    "Russians":        "Russians",
    "Spanish":         "Spanish",
    "DESwedish":       "Swedes",
    "DEAmericans":     "United States",
    # Revolution civs with HTML sections (19)
    "ANWArgentines":         "Argentines",
    "ANWBarbary":            "Barbary",
    "ANWBrazil":             "Brazil",
    "ANWCanadians":          "Canadians",
    "ANWChileans":           "Chileans",
    "ANWColumbians":         "Columbians",
    "ANWEgyptians":          "Egyptians",
    "ANWFinnish":            "Finnish",
    "ANWHaitians":           "Haitians",
    "ANWHungarians":         "Hungarians",
    "ANWIndonesians":        "Indonesians",
    "ANWMayans":             "Mayans",
    "ANWNapoleonicFrance":   "Napoleonic France",
    "ANWPeruvians":          "Peruvians",
    "ANWRevFrance":          "French Republic",
    "ANWRomanians":          "Romanians",
    "ANWSouthAfricans":      "South Africans",
    "ANWTexians":            "Texians",
    # Deferred revolution civs (2) — no HTML section yet, but still first-class
    "ANWAmericans":          "Americans",
    "ANWMexicans":           "Mexicans (Revolution)",
}


def _build_civs() -> list[AnwCiv]:
    """Build AnwCiv namedtuples from the new dict-shape ANW_CIVS."""
    out: list[AnwCiv] = []
    for token, info in _ANW_CIVS_DICT.items():
        # Stem: lowercase suffix after "ANW" prefix
        stem = info.get('file_stem') or (token[3:].lower() if token.startswith('ANW') else token.lower())
        # Slug: short HTML section name. Falls back to display for any token
        # that's missing from the explicit map (defensive — should not happen).
        slug = _TOKEN_TO_SLUG.get(token, info.get("display", token))
        # Revolution civs are those that didn't get a file_stem from the
        # base-civ section of ANW_CIVS_DICT. Concretely: every ANW-prefixed
        # token in the dict is a revolution.
        is_revolution = token.startswith("ANW")
        old_civ_token = _derive_rvlt_token(token) if is_revolution else token
        out.append(AnwCiv(
            anw_token=token,
            anw_stem=stem,
            slug=slug,
            display=info.get("display", slug),
            leader=info.get("leader", ""),
            new_homecity_filename=f"anwhomecity{stem}.xml",
            is_revolution=is_revolution,
            old_civ_token=old_civ_token,
        ))
    return out


ANW_CIVS: list[AnwCiv] = _build_civs()

# All 46 ANW civs in canonical order, indexed by anw_stem
ANW_CIVS_BY_STEM = {c.anw_stem: c for c in ANW_CIVS}

# Homecity filename map: anw_stem → anwhomecity{stem}.xml
ANW_HOMECITY_MAP = {c.anw_stem: c.new_homecity_filename for c in ANW_CIVS}

# All 46 ANW tokens in canonical order
ANW_ALL_TOKENS = [c.anw_token for c in ANW_CIVS]

# All 46 ANW stems in canonical order
ANW_ALL_STEMS = [c.anw_stem for c in ANW_CIVS]

# Slug → AnwCiv lookup for HTML-based validators
ANW_CIVS_BY_SLUG = {c.slug: c for c in ANW_CIVS}

# Slugs of civs deferred from HTML (no nation-node in a_new_world.html)
# These civs ARE first-class in civmods + personalities + decks; they just
# lack HTML sections. Validators exclude them from expected-section validation
# but process them in all other contexts.
ANW_DEFERRED_SLUGS: set[str] = {"Americans", "Mexicans (Revolution)"}

# Tokens deferred from skirmish-picker registration. These civs exist as
# revolution-mechanic variants triggered via in-game political choice (the
# AI handler is in game/ai/leaders/leader_revolution_commanders.xs); they
# are NOT directly pickable in the Skirmish lobby and therefore have no
# civmods.xml entry, no decks_anw.json deck, and no portrait/flag in the
# picker. Picker-side validators must skip these tokens to avoid spurious
# FAILs. Adding any of these to civmods + decks_anw.json would promote
# them to first-class pickable civs and they should be removed from this
# set at the same time.
ANW_NON_PICKER_TOKENS: set[str] = {
    "ANWAmericans",         # American Revolution — base DEAmericans variant
    "ANWMexicans",          # Mexican Revolution — base DEMexicans variant
    # Mexican cluster revolutions (merged 2026-05-17 — no longer lobby picks)
}


# Canonical ANW token → engine-truth token used in civmods.xml `<name>`
# entries and decks_anw.json keys.
#
# 2026-05-20: The mod now ADDS the 22 base ANW civs alongside base game
# civs (rather than overriding them). civmods.xml `<name>` entries use the
# ANW-prefixed token directly. The legacy "override base civ" mapping below
# is retained empty for compatibility — every ANW token now maps to itself.
ANW_TOKEN_TO_ENGINE_TOKEN: dict[str, str] = {}


def engine_token_for(anw_token: str) -> str:
    """Return the engine-truth token (used in civmods.xml + decks_anw.json)
    for a canonical ANW token. Falls through to the input for ANW-prefixed
    mod-introduced civs that map 1:1.
    """
    return ANW_TOKEN_TO_ENGINE_TOKEN.get(anw_token, anw_token)
