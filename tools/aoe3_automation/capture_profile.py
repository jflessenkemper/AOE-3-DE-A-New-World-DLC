# tools/aoe3_automation/capture_profile.py
"""Canonical per-civ capture profile for ANW Britain-parity coverage.

Single source of truth consumed by:
  - anw_visual_capture_runner.py   (knows what "complete" means)
  - supplementary capture scripts  (ageup, ai_homecity, recapture)
  - anw_building_tour.py           (knows expected building list per civ)
  - tools/validation/validate_capture_parity.py  (validator)

NEVER modify the profile without updating all four consumers.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BLURBS_PATH = _REPO_ROOT / "data" / "anw_civ_blurbs.json"

# ── Fixed core surfaces ────────────────────────────────────────────────────
# Every civ must have ALL of these in full/<label>.png.
CORE_SURFACES: list[str] = [
    "01_lobby",
    "02_loading",
    "03_hud",
    "04_homecity_panel",
    "05_tech_tree",
    "06_diplomacy",
    "07_scoreboard",
    "08_esc_menu",
    "09_endgame",
    "10_ai_homecity",
    "08_ageup_age2",
    "08_ageup_age3",
    "08_ageup_age4",
    "08_ageup_age5",
    "ai_01_chat_portrait",
    "ai_02_homecity",
    "ai_03_deck",
    "09_hero_selected",
    "17_units_inworld",
    "20_postgame_awards",
    "21_base_overview",
    "build_command_card",  # full-grid screenshot of settler build menu
]

# ── Common-core buildable structures ──────────────────────────────────────
# These are present for every civ regardless of unique_buildings.
# Derived from findings.md §3 and proto.xml page-6 analysis.
COMMON_CORE_BUILDINGS: list[str] = [
    "town_center",
    "barracks",
    "stable",
    "market",
    "mill",
    "plantation",
    "dock",
    "outpost",
    "trading_post",
    "wall",
    "church",
    "artillery_foundry",
    "arsenal",
    # Age 5 universals:
    "capitol",
    "native_embassy",
]


def _slugify(name: str) -> str:
    """'War Hut' -> 'war_hut', 'Skull Wall' -> 'skull_wall'."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _load_blurbs() -> dict:
    return json.loads(_BLURBS_PATH.read_text(encoding="utf-8"))


def expected_building_filenames(civ_token: str) -> list[str]:
    """Return sorted list of expected building_<slug>.png filenames for civ_token.

    Reads data/anw_civ_blurbs.json for the civ's unique_buildings list, combines
    with COMMON_CORE_BUILDINGS (deduplicating), and returns
    ['building_<slug>.png', ...] sorted alphabetically.

    Returns the common-core list for any civ not in the blurbs (future-safe).
    """
    blurbs = _load_blurbs()
    unique = blurbs.get(civ_token, {}).get("unique_buildings", [])
    all_slugs = list(COMMON_CORE_BUILDINGS)
    for u in unique:
        slug = _slugify(u)
        if slug not in all_slugs:
            all_slugs.append(slug)
    return sorted(f"building_{s}.png" for s in all_slugs)


def parity_profile(civ_token: str) -> dict:
    """Return the complete expected surface set for civ_token.

    Returns:
      {
        "core_surfaces": [...],           # label strings (no .png)
        "building_filenames": [...],      # filename strings (with .png)
        "total_expected": int,
      }
    """
    buildings = expected_building_filenames(civ_token)
    return {
        "core_surfaces": CORE_SURFACES,
        "building_filenames": buildings,
        "total_expected": len(CORE_SURFACES) + len(buildings),
    }


def all_active_civs() -> list[str]:
    """Return sorted list of all active civ tokens (main=1 in civmods.xml).

    Uses data/anw_civ_blurbs.json as the authoritative 44-civ list because:
    - civmods.xml requires XML parsing
    - anw_civ_blurbs.json is already the per-civ data source used everywhere
    Both sources are kept in sync; blurbs.json is the canonical runtime list.
    """
    blurbs = _load_blurbs()
    return sorted(blurbs.keys())


if __name__ == "__main__":
    # Self-test: print profiles for four reference civs so counts can be eyeballed.
    print(f"CORE_SURFACES ({len(CORE_SURFACES)}): {CORE_SURFACES}")
    print(f"COMMON_CORE_BUILDINGS ({len(COMMON_CORE_BUILDINGS)}): {COMMON_CORE_BUILDINGS}")
    print()

    civs = all_active_civs()
    print(f"Total active civs: {len(civs)}")
    print()

    for token in ("ANWBritish", "ANWFrench", "ANWAztecs", "ANWUSA"):
        p = parity_profile(token)
        print(f"--- {token} ---")
        print(f"  core surfaces : {len(p['core_surfaces'])}")
        print(f"  buildings      : {len(p['building_filenames'])}")
        print(f"  total expected : {p['total_expected']}")
        print(f"  building files : {p['building_filenames']}")
        print()
