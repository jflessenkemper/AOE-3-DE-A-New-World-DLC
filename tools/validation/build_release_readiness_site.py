#!/usr/bin/env python3
"""Build the consolidated release-readiness site — one HTML page that
aggregates everything a mod developer would want when reviewing the mod
for release: validator status, per-civ doctrine, art surfaces, screenshots,
linked deep-dives, and verification commands.

Reads from:
  - tools/validation/run_all_validators_report.json
  - playstyle_spec.json
  - artifacts/validation/ai_behaviour_map.json
  - artifacts/validation/visual_art/<civ>/manifest.json
  - artifacts/validation/visual_art/<civ>/thumbs/*.webp

Writes:
  - artifacts/validation/release_readiness_site.html
  - artifacts/validation/release_readiness_site_index.json (machine-readable index)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import defaultdict
from html import unescape as _html_unescape
from pathlib import Path

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PILImage = None
    _PIL_AVAILABLE = False

# Shared perceptual-hash helpers — imported from image_utils if available;
# fall back to the local inline definitions below for environments where the
# aoe3_automation package is not on sys.path (e.g. standalone site-builder runs).
try:
    import sys as _sys
    import os as _os
    _this_dir = _os.path.dirname(_os.path.abspath(__file__))
    _repo_root = _os.path.dirname(_this_dir)
    if _repo_root not in _sys.path:
        _sys.path.insert(0, _repo_root)
    from tools.aoe3_automation.image_utils import avg_hash as _iu_avg_hash, hamming as _iu_hamming
    _IMAGE_UTILS_AVAILABLE = True
except Exception:
    _IMAGE_UTILS_AVAILABLE = False

# Quote-extractor module — surfaces every AI insult / compliment / chatset
# line per civ so they can be rendered under each civ card. See
# ``tools/validation/extract_civ_quotes.py`` for the parser.
try:
    from extract_civ_quotes import (
        extract_chatset_lines as _ecq_extract_chatset_lines,
        extract_insults_compliments as _ecq_extract_insults_compliments,
        extract_shared_tactical_lines as _ecq_extract_shared_tactical_lines,
        quotes_for_spec_token as _ecq_quotes_for_spec_token,
    )
except ImportError:  # pragma: no cover — defensive; module ships alongside us
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_civ_quotes import (  # type: ignore[no-redef]
        extract_chatset_lines as _ecq_extract_chatset_lines,
        extract_insults_compliments as _ecq_extract_insults_compliments,
        extract_shared_tactical_lines as _ecq_extract_shared_tactical_lines,
        quotes_for_spec_token as _ecq_quotes_for_spec_token,
    )


def _safe_text(s: object) -> str:
    """HTML-escape a value safely even if it already contains entities.

    The playstyle spec stores some prose with pre-escaped HTML entities
    (e.g. ``map&#x27;s`` for ``map's``). Calling ``html.escape`` directly
    re-escapes the ``&``, producing ``&amp;#x27;``. Unescaping first
    canonicalises the input so the final escape pass is correct whether
    the source was raw or pre-escaped.
    """
    if s is None:
        return ""
    return html.escape(_html_unescape(str(s)))


# Prefix to strip from a repo-relative path to make it relative to the
# site's location. The site is emitted to
# ``artifacts/validation/release_readiness_site.html`` and the local HTTP
# server (``python3 -m http.server --bind 127.0.0.1 8765``) is rooted at
# that same directory, so paths starting with ``artifacts/validation/``
# need that prefix stripped to be reachable as both ``file://`` AND
# ``http://127.0.0.1:8765/``.
_SITE_ROOT_PREFIX = "artifacts/validation/"


def _site_relative(rel: str) -> str:
    """Convert a repo-relative path to a site-relative path.

    Examples::

        "artifacts/validation/visual_art/ANWFrench/thumbs/x.webp"
        ->  "visual_art/ANWFrench/thumbs/x.webp"

        "artifacts/validation/ai_behaviour_per_civ/argentines.md"
        ->  "ai_behaviour_per_civ/argentines.md"

    Paths that don't live under ``artifacts/validation/`` are returned
    with a ``../../`` traversal so they still resolve relative to the
    site's location for ``file://``; the local HTTP server can't reach
    those (out of root), but at least the file:// fallback works.
    """
    rel = rel.replace("\\", "/")
    if rel.startswith(_SITE_ROOT_PREFIX):
        return rel[len(_SITE_ROOT_PREFIX):]
    return "../../" + rel

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

GATE_REPORT = REPO_ROOT / "tools" / "validation" / "run_all_validators_report.json"
SPEC_PATH = REPO_ROOT / "playstyle_spec.json"
ART_DIR = REPO_ROOT / "artifacts" / "validation" / "visual_art"
BEHAVIOUR_MAP = REPO_ROOT / "artifacts" / "validation" / "ai_behaviour_map.json"
REVOLUTION_PATHS_JSON = HERE / "revolution_paths.json"
PER_CIV_AI_DIR = REPO_ROOT / "artifacts" / "validation" / "ai_behaviour_per_civ"
ANW_HTML = REPO_ROOT / "a_new_world.html"
ANW_COLUMNS = REPO_ROOT / "a_new_world_columns.html"
ANW_REVIEW = REPO_ROOT / "a_new_world_review.html"

OUT_HTML = REPO_ROOT / "artifacts" / "validation" / "release_readiness_site.html"
OUT_INDEX = REPO_ROOT / "artifacts" / "validation" / "release_readiness_site_index.json"

STRATEGY_NAMES: dict[int, str] = {
    0: "FortressRing",
    1: "ChokepointSegments",
    2: "CoastalBatteries",
    3: "FrontierPalisades",
    4: "UrbanBarricade",
    5: "MobileNoWalls",
}

STRATEGY_COLOR: dict[int, str] = {
    0: "#8b6f47",  # warm stone
    1: "#5d7a4a",  # mountain green
    2: "#3d6b8c",  # naval blue
    3: "#7d6b4f",  # frontier brown
    4: "#7a4a5d",  # urban red
    5: "#a08050",  # nomadic tan
}


# ── Display-only civ_label overrides ────────────────────────────────────────
#
# Some spec civ_labels read awkwardly when joined with the leader_label in the
# card title (e.g. ``French Louis — Louis XVIII`` reads as if "Louis" is part
# of the nation name and then the leader is also "Louis"). This map renames
# the *display* label only — spec data, validators, exhibition_runner, and
# all data plumbing keep using the spec value (``French Louis``) untouched.
# The rev-block also consults this map so the revolution-paths text stays in
# sync with the card titles the user reads.
CIV_LABEL_DISPLAY_OVERRIDE: dict[str, str] = {
    "French Louis": "French",
}


# ── Visual-confirmation surface order (used by per-civ card render) ─────────
#
# 2026-05-27: Promoted from inside main() to module scope so the per-civ
# card renderer can reuse the same surface list and label dict. Per user
# feedback the standalone "Art surfaces" / "In-game screenshots" sections
# are gone — every civ now gets its own inline art + screenshot strip
# directly under the home-city deck block, with broken-image placeholders
# for surfaces that haven't been captured yet.

ART_SURFACE_ORDER: list[str] = [
    "lobby_portrait",
    "loading_flag",
    "home_city_button",
    "hud_flag_corner",
    "home_city_scene",
    "tech_tree_overview",
    "diplomacy_panel",
    "scoreboard_player_row",
    "esc_menu_player_summary",
    "endgame_flag",
]

ART_SURFACE_LABELS: dict[str, str] = {
    "lobby_portrait": "Lobby portrait",
    "loading_flag": "Loading flag",
    "home_city_button": "HC button",
    "hud_flag_corner": "HUD flag",
    "home_city_scene": "HC scene",
    "tech_tree_overview": "Tech tree",
    "diplomacy_panel": "Diplomacy",
    "scoreboard_player_row": "Scoreboard row",
    "esc_menu_player_summary": "ESC summary",
    "endgame_flag": "Endgame flag",
}

# In-game screenshot strip: canonical column slots. Each tuple is
# ``(label, [candidate_filenames_in_priority_order])``. The renderer
# tries each candidate in the civ's batch folder
# (``visual_art/batch_NN_ANW<civ>/``) AND the per-civ folder
# (``visual_art/ANW<civ>/full/``), taking the first hit.
#
# Two different capture runners produced files under slightly different
# names — the batch runner emits ``02_hud_default.png`` while the per-civ
# runner emits ``03_hud.png`` for the same surface. We unify them here
# so a civ card displays a populated column regardless of which runner
# captured it.
#
# Files that don't match any canonical column show up in the "extras"
# strip below the canonical row (see ``_render_civ_screenshots_block``).
SCREENSHOT_COLUMNS: list[tuple[str, list[str]]] = [
    ("lobby",      ["01_lobby.png"]),
    ("loading",    ["02_loading.png"]),
    ("HUD",        ["02_hud_default.png", "03_hud.png"]),
    # Hero/Explorer selected in the HUD — the selection panel shows the
    # unit's name, letting the user visually confirm each nation's hero
    # name is correct.  Captured by recapture.py surface "hero".
    ("hero",       ["09_hero_selected.png", "10_hero_selected.png",
                    "hero_selected.png"]),
    ("scoreboard", ["03_scoreboard.png", "07_scoreboard_with_banter.png", "02_scoreboard.png"]),
    ("diplomacy",  ["04_diplomacy.png", "06_diplomacy.png", "01_diplomacy.png"]),
    ("home city",  ["05_homecity_panel.png", "04_homecity_panel.png", "03_homecity.png"]),
    ("tech tree",  ["05_tech_tree.png"]),
    ("ally HC",    ["06b_ai_homecity_via_diplo.png", "04_ally_homecity.png"]),
    ("esc menu",   ["06_esc_menu.png", "08_esc_menu.png"]),
    ("endgame",    ["07_endgame_screen.png", "09_postgame_results.png", "05_postgame.png"]),
    ("abandon",    ["07a_abandon_screen.png"]),
    ("awards",     ["20_postgame_awards.png"]),
    ("Age-Up II",  ["08_ageup_age2.png"]),
    ("Age-Up III", ["08_ageup_age3.png"]),
    ("Age-Up IV",  ["08_ageup_age4.png"]),
    ("Age-Up V",   ["08_ageup_age5.png"]),
]

# AI-round canonical columns (the round where the AI plays the nation).
# Filenames are fixed — no multi-candidate aliases needed.
AI_SCREENSHOT_COLUMNS: list[tuple[str, list[str]]] = [
    ("AI: Chat Portrait", ["ai_01_chat_portrait.png"]),
    ("AI: Home City",     ["ai_02_homecity.png"]),
    ("AI: Deck",          ["ai_03_deck.png"]),
]

# Map each column label -> the surface key understood by
# ``tools/aoe3_automation/recapture.py`` so each screenshot cell can show
# the one-liner that re-grabs exactly that surface. Lets the user copy a
# ready-to-run command straight off the site when a shot looks wrong.
RECAPTURE_SURFACE_KEY: dict[str, str] = {
    "lobby": "lobby",
    "loading": "loading",
    "HUD": "hud",
    "hero": "hero",
    "scoreboard": "scoreboard",
    "diplomacy": "diplomacy",
    "home city": "homecity",
    "tech tree": "techtree",
    "ally HC": "allyhc",
    "esc menu": "escmenu",
    "endgame": "endgame",
    "abandon": "abandon",
    "awards": "awards",
    "Age-Up II": "ageup2",
    "Age-Up III": "ageup3",
    "Age-Up IV": "ageup4",
    "Age-Up V": "ageup5",
    "AI: Chat Portrait": "ai_chat",
    "AI: Home City": "ai_homecity",
    "AI: Deck": "ai_deck",
}


def _recapture_cmd(anw_token: str, label: str) -> str:
    """Return the recapture.py one-liner for a civ/column, or '' if unmapped."""
    key = RECAPTURE_SURFACE_KEY.get(label)
    if not key:
        return ""
    return f"python3 tools/aoe3_automation/recapture.py {anw_token} {key}"


# All canonical filenames (any column candidate). Files NOT in this set
# but present in a civ's capture folder are rendered as "extras" so age-up
# shots, AI base shots, etc. don't get hidden.
_CANONICAL_SCREENSHOT_NAMES: set[str] = {
    fname
    for _label, candidates in SCREENSHOT_COLUMNS
    for fname in candidates
} | {
    fname
    for _label, candidates in AI_SCREENSHOT_COLUMNS
    for fname in candidates
}

# Backwards compat alias retained for any external caller; the renderer
# uses ``SCREENSHOT_COLUMNS`` directly.
SCREENSHOT_FILES: list[tuple[str, str]] = [
    (candidates[0], label) for label, candidates in SCREENSHOT_COLUMNS
]


# Spec tokens whose ANW art-folder name isn't ``ANW<first-word>``. These
# are multi-word civ stems that the naive first-word mapper can't reach.
_CIV_TOKEN_TO_ANW_ALIAS: dict[str, str] = {
    "United States Washington": "ANWUSA",
    "Napoleonic France Napoleon Bonaparte Revolution": "ANWNapoleonicFrance",
    "Revolutionary France Robespierre Revolution": "ANWRevFrance",
    "South Africans Kruger Boer Revolution": "ANWSouthAfricans",
}


def _civ_token_to_anw(token: str) -> str:
    """'Argentines San Martin Revolution' -> 'ANWArgentines' (best effort).

    Multi-word civ stems (e.g. 'United States Washington' -> 'ANWUSA')
    are resolved via ``_CIV_TOKEN_TO_ANW_ALIAS``.
    """
    if token in _CIV_TOKEN_TO_ANW_ALIAS:
        return _CIV_TOKEN_TO_ANW_ALIAS[token]
    first = token.split()[0]
    return "ANW" + first.replace("(", "").replace(")", "")


# ── Leader avatar resolution + site-side copy ───────────────────────────────
#
# The actual leader-avatar PNGs the game ships (and the user iterates on via
# tools/rebuild_portraits.py) live at
# ``resources/images/icons/singleplayer/cpai_avatar_*.png``. The local HTTP
# server (``python3 -m http.server --bind 127.0.0.1 8765``) is rooted at
# ``artifacts/validation/`` and therefore **cannot reach** files outside that
# tree. So when building the site we resolve each civ's avatar PNG via a
# naming-pattern search and copy the chosen file into
# ``artifacts/validation/leader_avatars/<slug>.png`` where the served HTML
# can reference it via a relative path.
#
# Why patterns and not a hard-coded map: the cpai_avatar filenames are
# stable in shape (``cpai_avatar_<civ_slug>[_<leader_slug>].png``) but the
# specific civ/leader slug used varies — some files drop ``_republic`` from
# ``French Republic``, some use ``anw<civ>``, some omit the leader first
# name. A small ordered candidate list catches all 41 civs cleanly without
# a brittle handwritten table.

_SINGLEPLAYER_AVATAR_DIR = REPO_ROOT / "resources" / "images" / "icons" / "singleplayer"
_SITE_AVATAR_DIR = REPO_ROOT / "artifacts" / "validation" / "leader_avatars"
# 2026-05-27: card icons (resources/images/icons/cards/*.png) live outside
# the served tree and can't be reached via ../../ from http://127.0.0.1:8765
# (the server only serves artifacts/validation/). Stage them into
# artifacts/validation/card_icons/ at build time and reference via a clean
# site-relative path.
_CARDS_SOURCE_DIR = REPO_ROOT / "resources" / "images" / "icons" / "cards"
_SITE_CARD_ICONS_DIR = REPO_ROOT / "artifacts" / "validation" / "card_icons"
_UNITS_SOURCE_DIR = REPO_ROOT / "resources" / "images" / "icons" / "units"
_SITE_UNIT_ICONS_DIR = REPO_ROOT / "artifacts" / "validation" / "unit_icons"

# Manual mapping from unique-unit display name (as in anw_civ_blurbs.json)
# to the icon filename under resources/images/icons/units/.  Only entries
# where the simple slug + "_icon.png" doesn't resolve directly are listed;
# the _resolve_unit_icon() helper falls back to the slug for the rest.
_UNIT_NAME_TO_ICON: dict[str, str] = {
    # Every unit maps to its OWN authentic in-game portrait icon, extracted from
    # the AoE3 DE game bars (UIResources*/ArtUnits) via tools/bar_extract.py.
    # NO approximations: each entry below is the unit's real, dedicated icon.
    # Units lacking a square portrait but with authentic encyclopedia-card art
    # are cropped from that card (still real game art). Units with no authentic
    # art at all are flagged BOGUS-DATA (see BOGUS_UNIT_NAMES.md) and given a
    # temporary non-authentic stand-in only to avoid a placeholder.
    # --- Authentic dedicated unit icons --------------------------------------
    "Abus Gun": "abus_gun_icon.png",
    "Aenna": "aenna_icon.png",
    "Arquebusier": "arquebusier_icon.png",
    "Arrow Knight": "arrow_knight_icon.png",
    "Artillery": "artillery_icon.png",
    "Ashigaru": "ashigaru_icon.png",
    "Axe Rider": "axe_rider_icon.png",
    "Azap": "azap_icon.png",
    "Barbary Warrior": "barbary_warrior_icon.png",
    "Bedouin Horse Archer": "bedouin_horse_archer_icon.png",
    "Bersagliere": "bersagliere_icon.png",
    "Bolas Warrior": "bolas_warrior_icon.png",
    "Bow Rider": "bow_rider_icon.png",
    "Camel Riders": "camel_riders_icon.png",
    "Cannon Crews": "cannon_crews_icon.png",
    "Carolean": "carolean_icon.png",
    "Cassador": "cassador_icon.png",
    "Cavalry Archer": "cavalry_archer_icon.png",
    "Cetbang Cannon": "cetbang_cannon_icon.png",
    "Changdao": "changdao_icon.png",
    "Chasqui": "chasqui_icon.png",
    "Chinaco": "chinaco_icon.png",
    "Chu Ko Nu": "chu_ko_nu_icon.png",
    "Club Warrior": "club_warrior_icon.png",
    "Colonial Militia": "colonial_militia_icon.png",
    "Congreve Rocket": "congreve_rocket_icon.png",
    "Corsair Infantry": "corsair_infantry_icon.png",
    "Corsair Marksman": "corsair_marksman_icon.png",
    "Cossack": "cossack_icon.png",
    "Coureur des Bois": "coureur_des_bois_icon.png",
    "Coyote Runner": "coyote_runner_icon.png",
    "Crossbowman": "crossbowman_icon.png",
    "Cruzob Avenger": "cruzob_avenger_icon.png",
    "Cruzob Infantry": "cruzob_infantry_icon.png",
    "Cuirassier": "cuirassier_icon.png",
    "Culverin": "culverin_icon.png",
    "Deli": "deli_icon.png",
    "Desert Archer": "desert_archer_icon.png",
    "Dog Soldier": "dog_soldier_icon.png",
    "Doppelsoldner": "doppelsoldner_icon.png",
    "Dorabant": "dorabant_icon.png",
    "Dorobant": "dorobant_icon.png",
    "Dragoon": "dragoon_icon.png",
    "Eagle Runner": "eagle_runner_icon.png",
    "Eagle Runner Knight": "eagle_runner_knight_icon.png",
    "Emboscador": "emboscador_icon.png",
    "Falconet": "falconet_icon.png",
    "Field Guns": "field_guns_icon.png",
    "Finnish Rider": "finnish_rider_icon.png",
    "Fire Thrower": "fire_thrower_icon.png",
    "Flamethrower": "flamethrower_icon.png",
    "Flaming Arrow": "flaming_arrow_icon.png",
    "Fluyt": "fluyt_icon.png",
    "Flying Crow": "flying_crow_icon.png",
    "Forest Prowler": "forest_prowler_icon.png",
    "Fula Warrior": "fula_warrior_icon.png",
    "Gascenya": "gascenya_icon.png",
    "Gatling Gun": "gatling_gun_icon.png",
    "Granadero a Caballo": "granadero_a_caballo_icon.png",
    "Great Bombard": "great_bombard_icon.png",
    "Grenadier": "grenadier_icon.png",
    "Gunner Levy": "gunner_levy_icon.png",
    "Gurkha": "gurkha_icon.png",
    "Hajduk": "hajduk_icon.png",
    "Hakkapelit": "hakkapelit_icon.png",
    "Halberdier": "halberdier_icon.png",
    "Heavy Cannon": "heavy_cannon_icon.png",
    "Holcan Javelineer": "holcan_javelineer_icon.png",
    "Hoop Thrower": "hoop_thrower_icon.png",
    "Horse Artillery": "horse_artillery_icon.png",
    "Hospitaller": "hospitaller_icon.png",
    "Hospitaller Knight": "hospitaller_knight_icon.png",
    "Howdah": "howdah_icon.png",
    "Humbaraci": "humbaraci_icon.png",
    "Hussar": "hussar_icon.png",
    "Insurgente": "insurgente_icon.png",
    "Insurgentes": "insurgentes_icon.png",
    "Iron Flail": "iron_flail_icon.png",
    "Jaguar Knight": "jaguar_knight_icon.png",
    "Janissary": "janissary_icon.png",
    "Javanese Spearman": "javanese_spearman_icon.png",
    "Javelin Rider": "javelin_rider_icon.png",
    "Jungle Bowman": "jungle_bowman_icon.png",
    "Karelian Jaeger": "karelian_jaeger_icon.png",
    "Kensei": "kensei_icon.png",
    "Keshik": "keshik_icon.png",
    "Lancer": "lancer_icon.png",
    "Leather Cannon": "leather_cannon_icon.png",
    "Lifidi Knight": "lifidi_knight_icon.png",
    "Light Cannon": "light_cannon_icon.png",
    "Line Infantry": "line_infantry_icon.png",
    "Llanero": "llanero_icon.png",
    "Longbowman": "longbowman_icon.png",
    "Macehualtin": "macehualtin_icon.png",
    "Maceman": "maceman_icon.png",
    "Mahout": "mahout_icon.png",
    "Maigadi": "maigadi_icon.png",
    "Mameluke": "mameluke_icon.png",
    "Mantlet": "mantlet_icon.png",
    "Maroon": "maroon_icon.png",
    "Meteor Hammer": "meteor_hammer_icon.png",
    "Metis Pathfinder": "metis_pathfinder_icon.png",
    "Metis Voyageur": "metis_voyageur_icon.png",
    "Militia": "militia_icon.png",
    "Minuteman": "minuteman_icon.png",
    "Missionary": "missionary_icon.png",
    "Mohawk Warrior": "mohawk_warrior_icon.png",
    "Monk Disciple": "monk_disciple_icon.png",
    "Mortar": "mortar_icon.png",
    "Mortar Crews": "mortar_crews_icon.png",
    "Morutaru": "morutaru_icon.png",
    "Mounted Infantry": "mounted_infantry_icon.png",
    "Musket Rider": "musket_rider_icon.png",
    "Musketeer": "musketeer_icon.png",
    "Musketeer (Jarma)": "musketeer_icon.png",
    "Naginata Rider": "naginata_rider_icon.png",
    "Neftenya": "neftenya_icon.png",
    "Nizam Fusilier": "nizam_fusilier_icon.png",
    "Old Guard": "old_guard_icon.png",
    "Oprichnik": "oprichnik_icon.png",
    "Organ Gun": "organ_gun_icon.png",
    "Oromo Warrior": "oromo_warrior_icon.png",
    "Padre": "padre_icon.png",
    "Pandour": "pandour_icon.png",
    "Papal Guard": "papal_guard_icon.png",
    "Papal Lancer": "papal_lancer_icon.png",
    "Papal Zouave": "papal_zouave_icon.png",
    "Pavisier": "pavisier_icon.png",
    "Pikeman": "pikeman_icon.png",
    "Pirate": "pirate_icon.png",
    "Plumed Spearman": "plumed_spearman_icon.png",
    "Puma Spearman": "puma_spearman_icon.png",
    "Raider": "raider_icon.png",
    "Rajput": "rajput_icon.png",
    "Ranger": "ranger_icon.png",
    "Regular": "regular_icon.png",
    "Revolutionaries": "revolutionaries_icon.png",
    "Rifle Rider": "rifle_rider_icon.png",
    "Rifleman": "rifleman_icon.png",
    "Rodelero": "rodelero_icon.png",
    "Rosior Dragoon": "rosior_dragoon_icon.png",
    "Ruyter": "ruyter_icon.png",
    "Samurai": "samurai_icon.png",
    "Sans Culottes": "sans_culottes_icon.png",
    "Schiavone": "schiavone_icon.png",
    "Sebastopol Mortar": "sebastopol_mortar_icon.png",
    "Sentinel": "sentinel_icon.png",
    "Sepoy": "sepoy_icon.png",
    "Shotel Warrior": "shotel_warrior_icon.png",
    "Siege Elephant": "siege_elephant_icon.png",
    "Siege Elephant Mansabdar": "siege_elephant_mansabdar_icon.png",
    "Skirmisher": "skirmisher_icon.png",
    "Skull Knight": "skull_knight_icon.png",
    "Soldado": "soldado_icon.png",
    "Soldados": "soldados_icon.png",
    "Sowar": "sowar_icon.png",
    "Spahi": "spahi_icon.png",
    "State Militia": "state_militia_icon.png",
    "Steppe Rider": "steppe_rider_icon.png",
    "Strelet": "strelet_icon.png",
    "Streltsy": "streltsy_icon.png",
    "Tokala Soldier": "tokala_soldier_icon.png",
    "Tomahawk": "tomahawk_icon.png",
    "Trek Wagon": "trek_wagon_icon.png",
    "Tribal Horseman": "tribal_horseman_icon.png",
    "US Cavalry": "us_cavalry_icon.png",
    "Uhlan": "uhlan_icon.png",
    "Urumi": "urumi_icon.png",
    "Urumi Swordsman": "urumi_swordsman_icon.png",
    "Voltigeur": "voltigeur_icon.png",
    "Voluntario Da Patria": "voluntario_da_patria_icon.png",
    "Volunteer": "volunteer_icon.png",
    "War Dog": "war_dog_icon.png",
    "War Wagon": "war_wagon_icon.png",
    "Yabusame": "yabusame_icon.png",
    "Yucateco Insurgente": "yucateco_insurgente_icon.png",
    "Yumi": "yumi_icon.png",
    "Yumi Archer": "yumi_archer_icon.png",
    "Zamburak": "zamburak_icon.png",
    # --- Authentic encyclopedia-card art (cropped from the game's own 600x1320
    #     in-game history/encyclopedia illustration in UIResources2.bar, squared
    #     to 128x128). Still 100% authentic game art for that exact unit. --------
    # --- VERIFIED REAL UNITS with their own authentic art (foreign-language or
    #     ethnonym display names that resolve to a real trainable proto). These
    #     are NOT bogus: each maps to its OWN authentic unit icon. -------------
    "Eclaireur": "revolutionary_scout_icon.png",  # REAL: French "scout" = RevFrance revolution proto deRevolutionaryScout (resolved_rosters ANWRevFrance, src=revolution); authentic art
    "Fulani Archer": "fula_warrior_icon.png",  # REAL: Hausa proto deFulaWarrior (core_unique); Fula/Fulani are the same people, the Fula Warrior is their archer; authentic art resources\\art\\units\\africans\\hausa\\fula_warrior\\fula_warrior_icon.png
    "Carbine Cavalry": "carbine_cavalry_icon.png",  # cropped from m_carbine_cavalry card art
    "Cetan Bow": "cetan_bow_icon.png",  # cropped from "m_i_cetan bow" card art
    "Chimu Runner": "chimu_runner_icon.png",  # cropped from "m_i_chimu runner" card art
    "Huaraca": "huaraca_icon.png",  # cropped from m_i_huaraca card art
    "Kanya Horseman": "kanya_horseman_icon.png",  # cropped from "m_c_kanya horseman" card art
    "Sharpshooter": "sharpshooter_icon.png",  # cropped from m_sharpshooter card art
    "Wakina Rifle": "wakina_rifle_icon.png",  # cropped from "m_i_wakina rifle" card art
    # --- BOGUS / VAGUE DATA: previously stand-in mapped, now eliminated from the
    #     data files (see artifacts/roster_audit/BOGUS_UNIT_NAMES_VERIFIED.md).
    #     The bogus display names Grenzer, Grensers, Gunpowder Troops,
    #     Khevite Fusilier, and Support Infantry were replaced/removed in
    #     data/anw_standard_units.json and data/anw_civ_blurbs.json, so their
    #     temporary stand-in icon entries have been deleted from this table.
}


def _resolve_unit_icon(display_name: str) -> str | None:
    """Return the icon filename for a unit display name, or None if unknown.

    Resolution order:
      1. Manual override table (_UNIT_NAME_TO_ICON)
      2. Slug: lower-case, non-alnum collapsed to '_', + '_icon.png'
    The returned filename is the basename only — callers prepend the source
    or staging path.
    """
    if display_name in _UNIT_NAME_TO_ICON:
        candidate = _UNIT_NAME_TO_ICON[display_name]
    else:
        slug = re.sub(r"[^a-z0-9]+", "_",
                      display_name.lower()).strip("_")
        candidate = f"{slug}_icon.png"
    return candidate if (_UNITS_SOURCE_DIR / candidate).is_file() else None


def _ascii_slug(s: str) -> str:
    """Lowercase ascii-folded snake_case slug used to build avatar filenames."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


_LEADER_NAME_FILLERS = {
    "of", "de", "von", "van", "the",
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix",
    "x", "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii",
}


def _avatar_candidates(token: str, civ_label: str, leader_label: str) -> list[str]:
    """Return ordered candidate ``cpai_avatar_*.png`` filenames for a civ.

    The ordering moves from most specific (civ + full leader name) to most
    generic (civ alone, ANW-prefixed civ alone). The first existing file
    wins; missing entries are silently skipped by ``_resolve_leader_avatar``.
    """
    civ_s = _ascii_slug(civ_label)
    lead_s = _ascii_slug(leader_label) if leader_label else ""
    lead_parts = [p for p in lead_s.split("_") if p and p not in _LEADER_NAME_FILLERS]
    lead_last = lead_parts[-1] if lead_parts else ""
    lead_two = "_".join(lead_parts[-2:]) if len(lead_parts) >= 2 else lead_last
    token_parts = [_ascii_slug(p) for p in token.split() if p.lower() != "revolution"]
    token_first = token_parts[0] if token_parts else ""
    token_last = token_parts[-1] if token_parts else ""
    civ_first = civ_s.split("_")[0] if civ_s else ""

    out: list[str] = []
    if lead_s:
        out.append(f"cpai_avatar_{civ_s}_{lead_s}.png")
        if lead_two and lead_two != lead_s:
            out.append(f"cpai_avatar_{civ_s}_{lead_two}.png")
        if lead_last and lead_last != lead_two:
            out.append(f"cpai_avatar_{civ_s}_{lead_last}.png")
    # token-last alt (e.g. 'French Louis XVIII Bourbon' -> french_bourbon)
    if token_last and token_first and token_last != civ_s and token_last != token_first:
        out.append(f"cpai_avatar_{token_first}_{token_last}.png")
    # civ-only fallbacks
    if civ_s:
        out.append(f"cpai_avatar_{civ_s}.png")
        out.append(f"cpai_avatar_anw{civ_s.replace('_','')}.png")
    if token_first and token_first != civ_s:
        out.append(f"cpai_avatar_{token_first}.png")
    if civ_first and civ_first != civ_s:
        out.append(f"cpai_avatar_{civ_first}.png")
        if lead_last:
            out.append(f"cpai_avatar_{civ_first}_{lead_last}.png")
    return out


def _resolve_leader_avatar(token: str, civ_label: str, leader_label: str,
                           portrait_path: str | None = None) -> Path | None:
    """Find the singleplayer cpai_avatar PNG for a civ, or None.

    Priority: spec's explicit ``portrait_path`` first (user-curated, points
    at the *correct* in-game base-game leader portrait), then the pattern
    candidate list as fallback. Without this, the resolver's token-last
    fallback picks the wrong leader for legacy spec keys (e.g. spec key
    ``Russians Catherine`` would surface ``cpai_avatar_russians_catherine``
    even when leader_label says ``Ivan the Terrible`` and portrait_path
    correctly points at ``cpai_avatar_russians_ivan.png``).
    """
    if portrait_path:
        p = REPO_ROOT / portrait_path
        if p.is_file():
            return p
    for name in _avatar_candidates(token, civ_label, leader_label):
        p = _SINGLEPLAYER_AVATAR_DIR / name
        if p.is_file():
            return p
    return None


def _stage_card_icons(decks: dict, cards_db: dict) -> set[str]:
    """Copy every card icon referenced by any civ's deck into the served tree.

    Returns the set of icon filenames that were staged so callers can verify
    coverage. The icons live at ``resources/images/icons/cards/<icon>`` which
    is OUTSIDE the http.server root at ``artifacts/validation/``; without
    this staging step every ``<img src="../../resources/images/icons/cards/
    *.png">`` returns 404 in the browser.
    """
    _SITE_CARD_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    # Collect every icon basename referenced by any deck card.
    wanted: set[str] = set()
    for deck in decks.values():
        for age_key, card_list in deck.items():
            if not isinstance(card_list, list):
                continue
            for cname in card_list:
                card = cards_db.get(cname, {})
                icon = card.get("icon")
                if icon:
                    wanted.add(icon)
    staged: set[str] = set()
    missing: list[str] = []
    for icon in sorted(wanted):
        src = _CARDS_SOURCE_DIR / icon
        if not src.is_file():
            missing.append(icon)
            continue
        dst = _SITE_CARD_ICONS_DIR / icon
        try:
            shutil.copy2(src, dst)
            staged.add(icon)
        except OSError as exc:
            print(f"  [warn] failed to stage card icon {icon}: {exc}",
                  file=sys.stderr)
    if missing:
        print(f"  [warn] {len(missing)} card icons missing from source: "
              f"{', '.join(missing[:6])}"
              f"{'...' if len(missing) > 6 else ''}")
    return staged


def _load_civ_blurbs() -> dict:
    """Load data/anw_civ_blurbs.json. Returns {} on error.

    Structure: {ANWCivToken: {"unique_units": [...display names...], ...}}
    """
    path = REPO_ROOT / "data" / "anw_civ_blurbs.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [warn] could not load anw_civ_blurbs.json: {exc}",
              file=sys.stderr)
        return {}


def _load_anw_standard_units() -> dict[str, list[str]]:
    """Load data/anw_standard_units.json. Returns {} on missing/parse error.

    Structure: {ANWCivToken: [unit_display_name, ...]}
    Hand-curated standard (non-unique) military roster per civ.
    """
    path = REPO_ROOT / "data" / "anw_standard_units.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [warn] could not load anw_standard_units.json: {exc}",
              file=sys.stderr)
        return {}


def _load_explorer_resolution() -> dict[str, dict]:
    """Load artifacts/retreat_design/explorer_resolution.json. {} on error.

    Structure: {ANWCivToken: {"proto", "displaynameid", "unit_type_name",
    "icon_filename"}}. This is the AUTHORITATIVE explorer/hero per civ for
    the "A New World" mod — the proto named in the civ's first
    <startingunit> (data/civmods.xml), its in-game unit-type display name
    (proto <displaynameid> resolved against the base string table), and its
    extracted unit icon. Used by _render_hero_explorer_row to show the real
    in-game explorer (e.g. British → "Explorer", Haudenosaunee → "War Chief",
    India → "Brahmin", Malta → "Grand Master") instead of a leader portrait.
    """
    path = REPO_ROOT / "artifacts" / "retreat_design" / "explorer_resolution.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [warn] could not load explorer_resolution.json: {exc}",
              file=sys.stderr)
        return {}


# ── Hero / Explorer unit display names per civ ──────────────────────────────
# Source for revolution civs: HTML explorer-block entries in a_new_world.html.
# Source for standard civs: AoE3 DE base game / DLC known explorer unit names.
# All suppression of nearby-unit retreat (per AI rout system) is triggered by
# the presence of a unit of cUnitTypeExplorer within 18m — these are the
# display-name labels for that unit per civ.
_ANW_HERO_EXPLORER: dict[str, list[str]] = {
    # ── Revolution civs (HTML explorer-block verified) ──────────────────────
    "ANWArgentines":       ["José de San Martín"],
    "ANWBarbary":          ["Hayreddin Barbarossa"],
    "ANWBrazil":           ["Pedro I"],
    "ANWCanadians":        ["Isaac Brock"],
    "ANWChileans":         ["Bernardo O'Higgins"],
    "ANWColumbians":       ["Simón Bolívar"],
    "ANWEgyptians":        ["Muhammad Ali Pasha"],
    "ANWFinnish":          ["Carl Gustaf Emil Mannerheim"],
    "ANWFrench":           ["Louis XVIII"],
    "ANWHaitians":         ["Toussaint L'Ouverture"],
    "ANWHungarians":       ["Lajos Kossuth"],
    "ANWIndonesians":      ["Prince Diponegoro"],
    "ANWMayans":           ["Jacinto Canek"],
    "ANWMexicans":         ["Miguel Hidalgo"],
    "ANWNapoleonicFrance": ["Napoleon Bonaparte"],
    "ANWPeruvians":        ["Andrés de Santa Cruz"],
    "ANWRevFrance":        ["Maximilien Robespierre"],
    "ANWRomanians":        ["Alexandru Ioan Cuza"],
    "ANWSouthAfricans":    ["Paul Kruger"],
    "ANWTexians":          ["Sam Houston"],
    # ── Standard / base-game civs (AoE3 DE known explorer unit names) ───────
    "ANWAztecs":           ["Nahuatl Warrior Priest"],
    "ANWBritish":          ["Explorer"],
    "ANWChinese":          ["Shaolin Monk"],
    "ANWDutch":            ["Explorer"],
    "ANWEthiopians":       ["Abun"],
    "ANWGermans":          ["Explorer"],
    "ANWHaudenosaunee":    ["War Chief"],
    "ANWHausa":            ["Mallam"],
    "ANWInca":             ["Chasqui Scout"],
    "ANWIndians":          ["Brahmin"],
    "ANWItalians":         ["Explorer"],
    "ANWJapanese":         ["Daimyo"],
    "ANWLakota":           ["War Chief"],
    "ANWMaltese":          ["Explorer"],
    "ANWOttomans":         ["Explorer"],
    "ANWPortuguese":       ["Explorer"],
    "ANWRussians":         ["Explorer"],
    "ANWSpanish":          ["Explorer"],
    "ANWSwedes":           ["Explorer"],
    "ANWUSA":              ["Explorer"],
}

# NOTE: the former ``_ANW_HERO_ICON_MAP`` (token → leader_avatars/anw<token>.png)
# was removed 2026-06-02. Those anw<token>.png files never existed (the staged
# avatars are slug-named, e.g. british_elizabeth.png), so every hero portrait
# 404'd. The HERO/EXPLORER row now reuses the authoritative ``avatars`` dict
# returned by _stage_leader_avatars() (keyed by spec token), the same source
# the card header uses — see _render_hero_explorer_row().


def _load_anw_unit_rosters() -> dict[str, list[str]]:
    """Parse a_new_world.html to extract per-civ military unit lists.

    The HTML embeds a ``data-search`` attribute on each nation node with the
    format ``"NationName Leader · Unit1 · Unit2 · ... · CardName — desc · ..."``.
    Units appear before the first card (cards contain " — " or start with TEAM).
    Items starting with a digit (e.g. "16 Musketeers") are shipment quantities,
    not unit types, and are excluded.

    Returns {ANWToken: [unit_display_name, ...]} — empty list if the HTML is
    missing or unparseable.
    """
    html_path = REPO_ROOT / "a_new_world.html"
    if not html_path.is_file():
        print("  [warn] a_new_world.html not found — retreat-units rows will be empty",
              file=sys.stderr)
        return {}

    html_text = html_path.read_text(encoding="utf-8")
    nation_searches = re.findall(r'data-name="([^"]+)" data-search="([^"]+)"',
                                 html_text)

    # Known ANW tokens for lookup (populated lazily from blurbs keys)
    _known = set(_ANW_HERO_EXPLORER.keys())

    def _to_anw_token(html_name: str) -> str | None:
        first = html_name.split()[0].lower()
        _overrides = {
            "haudenosaunee": "ANWHaudenosaunee",
            "revolutionary":  "ANWRevFrance",
            "napoleonic":     "ANWNapoleonicFrance",
            "south":          "ANWSouthAfricans",
            "united":         "ANWUSA",
        }
        if first in _overrides:
            return _overrides[first]
        candidate = "ANW" + html_name.split()[0]
        return candidate if candidate in _known else None

    result: dict[str, list[str]] = {}
    for html_name, search in nation_searches:
        tok = _to_anw_token(html_name)
        if not tok:
            continue
        parts = search.split(" · ")
        units: list[str] = []
        for part in parts[1:]:   # skip first (nation+leader string)
            part = part.strip()
            if " \u2014 " in part or part.startswith("TEAM "):
                break            # reached home-city cards section
            if part and not part[0].isdigit():
                units.append(part)
        result[tok] = units
    return result


def _stage_unit_icons(blurbs: dict,
                      rosters: dict[str, list[str]] | None = None,
                      standard_units: dict[str, list[str]] | None = None) -> set[str]:
    """Copy every unit icon referenced by any civ into the served tree.

    Covers unique-units (from blurbs), hero/explorer units (_ANW_HERO_EXPLORER),
    retreat-units (from rosters derived from a_new_world.html), and curated
    standard-unit rosters (from data/anw_standard_units.json).

    Mirrors the pattern of _stage_card_icons(): source files come from
    resources/images/icons/units/, destination is
    artifacts/validation/unit_icons/.

    Returns the set of icon filenames successfully staged.
    """
    _SITE_UNIT_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    wanted: set[str] = set()
    # Unique units (blurbs)
    for civ_info in blurbs.values():
        for unit_name in (civ_info.get("unique_units") or []):
            icon = _resolve_unit_icon(unit_name)
            if icon:
                wanted.add(icon)
    # Hero / Explorer units
    for unit_names in _ANW_HERO_EXPLORER.values():
        for unit_name in unit_names:
            icon = _resolve_unit_icon(unit_name)
            if icon:
                wanted.add(icon)
    # Curated standard units (data/anw_standard_units.json)
    if standard_units:
        for tok, unit_list in standard_units.items():
            for unit_name in unit_list:
                icon = _resolve_unit_icon(unit_name)
                if icon:
                    wanted.add(icon)
    # Retreat units (from HTML rosters)
    if rosters:
        for tok, all_units in rosters.items():
            unique_set = set((blurbs.get(tok) or {}).get("unique_units") or [])
            for unit_name in all_units:
                if unit_name not in unique_set:
                    icon = _resolve_unit_icon(unit_name)
                    if icon:
                        wanted.add(icon)
    staged: set[str] = set()
    missing: list[str] = []
    for icon in sorted(wanted):
        src = _UNITS_SOURCE_DIR / icon
        if not src.is_file():
            missing.append(icon)
            continue
        dst = _SITE_UNIT_ICONS_DIR / icon
        try:
            shutil.copy2(src, dst)
            staged.add(icon)
        except OSError as exc:
            print(f"  [warn] failed to stage unit icon {icon}: {exc}",
                  file=sys.stderr)
    if missing:
        print(f"  [warn] {len(missing)} unit icons missing from source: "
              f"{', '.join(missing[:6])}"
              f"{'...' if len(missing) > 6 else ''}")
    return staged


def _render_unit_row(title: str, unit_names: list[str],
                     css_block: str = "unique-units-block",
                     css_label: str = "unique-units-label",
                     css_row: str = "unique-units-row",
                     tooltip_prefix: str = "") -> str:
    """Render a labeled horizontal strip of unit icon chips.

    Generic helper used by _render_unique_units_row, _render_hero_explorer_row,
    and _render_retreat_units_row.  Each chip shows an icon + caption; units
    without a resolvable icon render as a dashed placeholder chip.

    Args:
        title:      Row label (e.g. "UNIQUE UNITS").
        unit_names: Ordered list of display-name strings.
        css_block/css_label/css_row: CSS class names for the wrapper elements.

    Returns an HTML fragment, or a "none / data unavailable" notice row if
    ``unit_names`` is empty.
    """
    if not unit_names:
        return (
            f'<div class="{css_block}">'
            f'<div class="{css_label}">{html.escape(title)}</div>'
            f'<div class="{css_row}">'
            f'<span style="font-size:11px;color:#6e7681;padding:4px 6px;">'
            f'(none / data unavailable)</span>'
            f'</div>'
            f'</div>'
        )

    cells: list[str] = []
    for unit_name in unit_names:
        icon = _resolve_unit_icon(unit_name)
        safe_name = html.escape(unit_name)
        # Hover tooltip: optionally role-prefixed (e.g. "Explorer: …") so the
        # user can confirm each nation's hero/explorer name on hover.
        tip = html.escape(f"{tooltip_prefix}{unit_name}") if tooltip_prefix \
            else safe_name
        if icon:
            icon_url = f"unit_icons/{html.escape(icon)}"
            cells.append(
                f'<div class="unit-cell">'
                f'<img src="{icon_url}" '
                f'alt="{safe_name}" '
                f'title="{tip}" '
                f'loading="lazy">'
                f'<div class="unit-caption">{safe_name}</div>'
                f'</div>'
            )
        else:
            cells.append(
                f'<div class="unit-cell unit-cell-missing" title="{tip}">'
                f'<div class="unit-placeholder">?</div>'
                f'<div class="unit-caption">{safe_name}</div>'
                f'</div>'
            )

    return (
        f'<div class="{css_block}">'
        f'<div class="{css_label}">{html.escape(title)}</div>'
        f'<div class="{css_row}">{"".join(cells)}</div>'
        f'</div>'
    )


def _render_unique_units_row(anw_token: str, blurbs: dict) -> str:
    """Render the UNIQUE UNITS strip for one civ (10% retreat tier).

    Data from data/anw_civ_blurbs.json unique_units lists.  Returns "" if the
    civ has no unique_units entry in blurbs (renders as unavailable notice via
    _render_unit_row when the list is empty).
    """
    civ_info = blurbs.get(anw_token)
    if not civ_info:
        return _render_unit_row("UNIQUE UNITS", [])
    unit_names = list(civ_info.get("unique_units") or [])
    return _render_unit_row("UNIQUE UNITS", unit_names)


def _render_hero_explorer_row(anw_token: str,
                              explorer_map: dict[str, dict] | None = None) -> str:
    """Render the HERO / EXPLORER strip for one civ.

    "A New World" uses the stock AoE3 explorer/hero system, so this shows the
    civ's actual in-game explorer/hero by NAME — e.g. Argentines → "William
    Brown", British → "Walter Raleigh", Haudenosaunee → "Raven", Inca →
    "Manco Inca". The proper name comes from the in-game name pools
    (``primary_name`` in artifacts/retreat_design/explorer_resolution.json —
    resolved from data/strings + base randomnames, or curated where the base
    pool is generic/empty). The hero's unit-type (Explorer / War Chief /
    Brahmin / Grand Master / General …) is shown in the tooltip, and the
    unit's own extracted icon is used. ``explorer_map`` is loaded via
    _load_explorer_resolution().

    Falls back to the curated ``_ANW_HERO_EXPLORER`` name + ``_resolve_unit_icon``
    only when the resolution file lacks the civ.
    """
    entry = (explorer_map or {}).get(anw_token) or {}
    # Caption = the explorer/hero's proper NAME; unit-type goes in the tooltip.
    name = (entry.get("primary_name") or "").strip()
    unit_type = (entry.get("unit_type_name") or "").strip()
    icon_url: str | None = None
    icon_fn = entry.get("icon_filename")
    if icon_fn:
        icon_url = f"unit_icons/{icon_fn}"
    if not name:
        name = unit_type
    if not name:
        names = list(_ANW_HERO_EXPLORER.get(anw_token) or [])
        name = names[0] if names else ""
    if not name:
        return _render_unit_row("HERO / EXPLORER", [])

    safe_name = html.escape(name)
    tip_text = f"Hero / Explorer: {name}"
    if unit_type and unit_type.lower() != name.lower():
        tip_text += f" ({unit_type})"
    tip = html.escape(tip_text)
    if not icon_url:
        resolved = _resolve_unit_icon(unit_type or name)
        icon_url = f"unit_icons/{resolved}" if resolved else None
    if icon_url:
        cell = (
            f'<div class="unit-cell">'
            f'<img src="{html.escape(icon_url)}" '
            f'alt="{safe_name}" '
            f'title="{tip}" '
            f'loading="lazy">'
            f'<div class="unit-caption">{safe_name}</div>'
            f'</div>'
        )
    else:
        cell = (
            f'<div class="unit-cell unit-cell-missing" title="{tip}">'
            f'<div class="unit-placeholder">?</div>'
            f'<div class="unit-caption">{safe_name}</div>'
            f'</div>'
        )
    return (
        f'<div class="unique-units-block">'
        f'<div class="unique-units-label">HERO / EXPLORER</div>'
        f'<div class="unique-units-row">{cell}</div>'
        f'</div>'
    )


def _render_retreat_units_row(anw_token: str, blurbs: dict,
                               rosters: dict[str, list[str]],
                               standard_units: dict[str, list[str]] | None = None) -> str:
    """Render the RETREAT UNITS strip for one civ (25% retreat tier).

    Retreat units = standard-unit roster for the civ (from curated
    data/anw_standard_units.json when non-empty, else HTML-derived rosters)
    MINUS the civ's unique_units (which retreat at 10% instead) AND minus
    the civ's hero/explorer units (which never retreat; they suppress nearby
    retreats).
    Source: data/anw_standard_units.json (curated) or a_new_world.html
    data-search attributes (fallback), filtered against blurbs unique_units
    + _ANW_HERO_EXPLORER.
    """
    curated = (standard_units or {}).get(anw_token)
    all_units = curated if curated else (rosters.get(anw_token) or [])
    exclude = set((blurbs.get(anw_token) or {}).get("unique_units") or [])
    exclude |= set(_ANW_HERO_EXPLORER.get(anw_token) or [])
    # Case-insensitive exclusion
    exclude_lower = {e.lower() for e in exclude}
    retreat = [u for u in all_units if u.lower() not in exclude_lower]
    return _render_unit_row("RETREAT UNITS", retreat)


def _load_civmods_leader_portraits() -> dict[str, str]:
    """Map each ANW civ token to its ACTUAL in-game leader portrait filename.

    Authoritative source: ``data/civmods.xml`` ``<homecitypreviewwpf>`` — the
    home-city leader preview portrait the GAME itself shows for that civ. This
    is the base-game leader for base civs (e.g. ANWBritish →
    ``cpai_avatar_british.png``, ANWSpanish → ``cpai_avatar_spanish_isabella.png``)
    and the new-nation leader for the custom civs (e.g. ANWArgentines →
    ``cpai_avatar_argentines_san_martin.png``, ANWHaudenosaunee →
    ``cpai_avatar_haudenosaunee_hiawatha.png``).

    Returns ``{ANWToken: basename.png}`` (basename only; the file lives in
    ``resources/images/icons/singleplayer/``). Empty dict on read error.
    """
    path = REPO_ROOT / "data" / "civmods.xml"
    out: dict[str, str] = {}
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"  [warn] could not read civmods.xml: {exc}", file=sys.stderr)
        return out
    for blk in txt.split("<civ>"):
        m = re.search(r"<name>(ANW[A-Za-z]+)</name>", blk)
        if not m:
            continue
        pv = re.search(r"<homecitypreviewwpf>([^<]+)</homecitypreviewwpf>", blk)
        if not pv:
            continue
        base = pv.group(1).strip().replace("\\", "/").rsplit("/", 1)[-1]
        out[m.group(1)] = base
    return out


# Leader-portrait art surfaces (in priority order) whose captured crop is the
# in-game leader portrait. Sourcing the card-header circle from the first
# available one keeps the circle identical to the per-civ "Art surfaces"
# portrait shown on the same card.
_PORTRAIT_CROP_SURFACES = (
    "lobby_portrait",
    "scoreboard_player_row",
    "diplomacy_panel",
    "esc_menu_player_summary",
)


def _load_portrait_overrides() -> dict[str, str]:
    """Map ANW civ token -> hand-picked canonical leader-portrait path.

    Source: ``artifacts/retreat_design/leader_portrait_choice.json`` —
    ``{ANWToken: repo_relative_png_path}``. Used when a civ's auto-detected
    in-game crop is a BAD capture (e.g. ANWBritish's lobby_portrait crop is a
    harbor scene, not Queen Elizabeth). This override is the highest-priority
    circle source and also drives the leader-portrait art surface, so both
    match. Empty dict if the file is absent.
    """
    path = REPO_ROOT / "artifacts" / "retreat_design" / "leader_portrait_choice.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _best_portrait_crop(anw_token: str) -> Path | None:
    """Return the best captured in-game leader-portrait crop for a civ, or None.

    Looks in ``artifacts/validation/visual_art/<ANWtoken>/crops/`` for the
    leader-portrait surfaces in priority order, skipping any flagged
    ``*.needs_recapture.png`` (stale/wrong captures). Returns the first match
    so the card-header circle is the SAME image the card's Art-surfaces strip
    displays for that nation.
    """
    crops_dir = ART_DIR / anw_token / "crops"
    if not crops_dir.is_dir():
        return None
    for surf in _PORTRAIT_CROP_SURFACES:
        cand = crops_dir / f"{surf}.png"
        if cand.is_file():
            return cand
    return None


def _stage_leader_avatars(spec: dict) -> dict[str, str]:
    """Copy each civ's actual in-game leader portrait into the site tree.

    Returns ``{civ_token: site_relative_path}`` where ``site_relative_path``
    is e.g. ``leader_avatars/argentines_san_martin_revolution.png`` — already
    in the form the locally hosted HTML can use.

    The portrait source is the AUTHORITATIVE in-game leader portrait declared
    in ``data/civmods.xml`` (<homecitypreviewwpf>, via
    _load_civmods_leader_portraits) — the same image the game shows for that
    nation's leader. Falls back to the legacy pattern-based
    ``_resolve_leader_avatar`` only if civmods has no entry / the file is
    absent.

    Files are copied (not symlinked) so the http.server in
    ``artifacts/validation/`` can serve them without needing follow-symlinks
    semantics, and so the directory is self-contained for archive/upload.
    """
    _SITE_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    portrait_map = _load_civmods_leader_portraits()
    portrait_overrides = _load_portrait_overrides()
    out: dict[str, str] = {}
    unresolved: list[str] = []
    for token, civ in (spec.get("civs") or {}).items():
        civ_label = civ.get("civ_label") or token
        leader_label = civ.get("leader_label") or ""
        portrait_path = civ.get("portrait_path") or None
        src: Path | None = None
        anw_token = _civ_token_to_anw(token)
        # 1) Hand-picked override (for civs whose base art / capture is wrong).
        ov = portrait_overrides.get(anw_token)
        if ov:
            cand = REPO_ROOT / ov
            if cand.is_file():
                src = cand
        # 2) BASE GAME ART: the official cpai_avatar leader portrait declared
        #    in civmods.xml <homecitypreviewwpf> (e.g. ANWBritish →
        #    cpai_avatar_british.png = Queen Elizabeth). Per user preference,
        #    use the clean base-game portrait rather than a screenshot crop.
        if src is None:
            base = portrait_map.get(anw_token)
            if base:
                cand = _SINGLEPLAYER_AVATAR_DIR / base
                if cand.is_file():
                    src = cand
        # 3) Fall back to a captured in-game leader-portrait crop (skips
        #    ``.needs_recapture``) only when no base-game portrait exists.
        if src is None:
            src = _best_portrait_crop(anw_token)
        # 4) Last resort: legacy pattern-based avatar resolver.
        if src is None:
            src = _resolve_leader_avatar(token, civ_label, leader_label,
                                         portrait_path=portrait_path)
        if src is None:
            unresolved.append(token)
            continue
        slug = _civ_token_slug(token)
        dst = _SITE_AVATAR_DIR / f"{slug}.png"
        # Always copy — the user is iterating on portraits (Hiawatha being
        # the immediate driver), so a stale cache here would defeat the
        # whole point of refreshing the site.
        try:
            shutil.copy2(src, dst)
        except OSError as exc:
            print(f"  [warn] failed to copy avatar for {token}: {exc}",
                  file=sys.stderr)
            continue
        out[token] = f"leader_avatars/{slug}.png"
    if unresolved:
        print(f"  [warn] {len(unresolved)} civs without a resolved avatar: "
              f"{', '.join(sorted(unresolved)[:6])}"
              f"{'...' if len(unresolved) > 6 else ''}")
    return out


# civmods <homecityflagtexture> basenames whose name doesn't match the
# Flag_*.png icon filename directly (prefixes / singular-plural / spelling).
_FLAG_TEXTURE_ALIAS: dict[str, str] = {
    "canadian": "Flag_Canadians.png", "romanian": "Flag_Romanians.png",
    "spc_barbary": "Flag_barbary.png", "egyptian": "Flag_Egyptians.png",
    "mx_mayan": "Flag_mayan.png", "us_texan": "Flag_texan.png",
    "china": "Flag_Chinese.png", "spc_ethiopians": "Flag_Ethiopian.png",
    "germans": "Flag_German.png", "inca": "Flag_Incan.png",
    "india": "Flag_Indian.png", "japan": "Flag_Japanese.png",
    "malta": "Flag_Maltese.png", "ottomans": "Flag_Ottoman.png",
    "russians": "Flag_Russian.png", "spc_americans": "Flag_American.png",
}

_FLAGS_SRC_DIR = REPO_ROOT / "resources" / "images" / "icons" / "flags"
_SITE_FLAG_DIR = REPO_ROOT / "artifacts" / "validation" / "flags"


def _load_flag_map() -> dict[str, str]:
    """{ANWtoken: Flag_*.png} from the authoritative civmods
    <homecityflagtexture> (the flag the game actually shows for that nation)."""
    try:
        txt = (REPO_ROOT / "data" / "civmods.xml").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return {}
    pngs = {p.stem.lower().removeprefix("flag_"): p.name
            for p in _FLAGS_SRC_DIR.glob("Flag_*.png")}
    out: dict[str, str] = {}
    for blk in txt.split("<civ>"):
        m = re.search(r"<name>(ANW[A-Za-z]+)</name>", blk)
        fm = re.search(r"<homecityflagtexture>([^<]+)</homecityflagtexture>", blk)
        if not (m and fm):
            continue
        base = fm.group(1).strip().replace("\\", "/").rsplit("/", 1)[-1].lower()
        png = _FLAG_TEXTURE_ALIAS.get(base) or pngs.get(base)
        if png:
            out[m.group(1)] = png
    return out


def _stage_flags(flag_map: dict[str, str]) -> dict[str, str]:
    """Copy each nation's flag into the served tree. Returns {ANWtoken: rel}."""
    _SITE_FLAG_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    for anw_token, png in flag_map.items():
        src = _FLAGS_SRC_DIR / png
        if not src.is_file():
            continue
        dst = _SITE_FLAG_DIR / f"{anw_token}.png"
        try:
            shutil.copy2(src, dst)
        except OSError:
            continue
        out[anw_token] = f"flags/{anw_token}.png"
    return out


# ── Home-city deck rendering (per-civ doctrine area) ────────────────────────

_AGE_LABELS = {
    "0": "Disc.",   # Age 1 / Discovery
    "1": "Col.",    # Age 2 / Colonial
    "2": "For.",    # Age 3 / Fortress
    "3": "Ind.",    # Age 4 / Industrial
    # 2026-05-27: Imperial-age row dropped — per user feedback ("there are
    # no imperial age card decks"). Only 9 of 82 decks even have a slot-4
    # entry and each is a single ``HCXPIndustrialRevolution`` placeholder;
    # the row was dead space on every other civ card. We now render four
    # rows (Disc./Col./For./Ind.) and skip slot 4 entirely.
}


def _load_deck_data() -> tuple[dict, dict]:
    """Return (decks_dict, cards_dict).

    ``decks_dict`` is the merged view of ``data/decks_anw.json`` (canonical
    home of the 40 ANW-prefixed revolutionary / ANW civ decks) overlaid on
    top of ``data/decks.json`` (which has the bare-name decks like
    ``RioGrande`` that ``decks_anw.json`` doesn't carry). Bare-name decks
    are looked up via the alias map / fallback in ``_render_civ_deck_html``.
    """
    decks: dict = {}
    cards: dict = {}
    base_decks_path = REPO_ROOT / "data" / "decks.json"
    anw_decks_path = REPO_ROOT / "data" / "decks_anw.json"
    cards_path = REPO_ROOT / "data" / "cards.json"
    try:
        with open(base_decks_path) as fh:
            decks.update(json.load(fh))
    except Exception:
        pass
    try:
        with open(anw_decks_path) as fh:
            decks.update(json.load(fh))  # ANW entries take precedence
    except Exception:
        pass
    try:
        with open(cards_path) as fh:
            cards = json.load(fh)
    except Exception:
        pass
    return decks, cards


# Civ tokens whose deck key in ``data/decks*.json`` isn't ``ANW<first-word>``.
# This is separate from ``_CIV_TOKEN_TO_ANW_ALIAS`` (used for art folders);
# the deck JSON sometimes uses a bare PascalCase compound name like
# ``RioGrande`` rather than the ANW-prefixed art-folder name.
_CIV_TOKEN_TO_DECK_KEY: dict[str, str] = {
    "Rio Grande Canales Rosillo Revolution": "RioGrande",
}


def _render_civ_deck_html(
    anw_token: str, decks: dict, cards: dict, spec_token: str = ""
) -> str:
    """Render the per-civ deck section: 5 age-rows of card icons with hover
    labels showing the card's name + description. Returns empty string if no
    deck is found for this civ.

    Lookup order:
      1. ``_CIV_TOKEN_TO_DECK_KEY[spec_token]`` (explicit alias)
      2. ``anw_token`` (e.g. ``ANWArgentines``)
      3. ``anw_token`` with the ``ANW`` prefix stripped (e.g. ``RioGrande``)
    """
    deck = None
    if spec_token and spec_token in _CIV_TOKEN_TO_DECK_KEY:
        deck = decks.get(_CIV_TOKEN_TO_DECK_KEY[spec_token])
    if not deck:
        deck = decks.get(anw_token)
    if not deck and anw_token.startswith("ANW"):
        deck = decks.get(anw_token[3:])
    if not deck:
        return ""
    # 2026-05-27: Was ``range(5)`` — see ``_AGE_LABELS`` comment. Slot 4
    # (Imperial) is no longer rendered, so the per-civ card count and the
    # iteration both stop at slot 3 (Industrial).
    total_cards = sum(len(deck.get(str(age), [])) for age in range(4))
    if total_cards == 0:
        return ""

    rows: list[str] = []
    for age in ("0", "1", "2", "3"):
        card_names = deck.get(age, [])
        age_label = _AGE_LABELS.get(age, age)
        if not card_names:
            rows.append(
                f'<div class="age-row">'
                f'<div class="age-label">{html.escape(age_label)}</div>'
                f'<div class="age-empty">— no cards —</div>'
                f'</div>'
            )
            continue
        icons: list[str] = []
        for cname in card_names:
            card = cards.get(cname, {})
            disp_name = card.get("name") or cname
            desc = card.get("desc") or ""
            icon = card.get("icon") or ""
            # Tooltip: "Name — description (truncated)"
            tip = disp_name
            if desc:
                # Trim long descriptions; keep ~180 chars for tooltip clarity
                trimmed = desc.strip().replace("\n", " ")
                if len(trimmed) > 220:
                    trimmed = trimmed[:217] + "…"
                tip = f"{disp_name} — {trimmed}"
            if icon:
                # 2026-05-27: was ``../../resources/images/icons/cards/...``
                # which 404s under the local HTTP server (rooted at
                # artifacts/validation/). Card icons are now staged into
                # artifacts/validation/card_icons/ by _stage_card_icons()
                # so a clean site-relative path resolves under both
                # file:// and http://127.0.0.1:8765/.
                icon_url = f"card_icons/{icon}"
                icons.append(
                    f'<img src="{html.escape(icon_url)}" '
                    f'alt="{html.escape(disp_name)}" '
                    f'title="{html.escape(tip)}" '
                    f'loading="lazy">'
                )
            else:
                # No icon mapping — render the card name as a small chip so
                # the card is at least visible / hoverable.
                icons.append(
                    f'<span title="{html.escape(tip)}" '
                    f'style="display:inline-block;padding:3px 6px;'
                    f'background:#21262d;border:1px solid #30363d;'
                    f'border-radius:3px;font-size:9px;color:#8b949e">'
                    f'{html.escape(disp_name[:18])}</span>'
                )
        rows.append(
            f'<div class="age-row">'
            f'<div class="age-label">{html.escape(age_label)}</div>'
            f'<div class="age-cards">{"".join(icons)}</div>'
            f'</div>'
        )

    # 2026-05-27: was a `<details>` collapsible — per user feedback the
    # home-city deck should be exposed automatically on every civ card.
    # Render as a plain titled section so all decks are always visible.
    return (
        f'<div class="deck"><div class="deck-title">'
        f'Home-city deck ({total_cards} cards across 4 ages)'
        f'</div><div class="deck-body">'
        + "".join(rows)
        + '</div></div>'
    )


def _civ_token_slug(token: str) -> str:
    """Snake-case slug used by ai_behaviour_per_civ markdown files."""
    return re.sub(r"[^a-z0-9]+", "_", token.lower()).strip("_")


# ── Wall-doctrine knob loading + per-civ rendering ─────────────────────────
#
# The 15 wall tuning knobs (gLLWall*) live in
# ``tools/ai_design/wall_knob_calibration.py``. We import its ``CALIBRATION``
# dict so the per-civ card can show the actual knobs the engine will fire
# for that civ — strategy enum, ring radius, gate count, age-2 stone,
# trigger age, closure %, forward bias, etc. — directly under the per-age
# strategy block, without sending the user off to a separate page.

def _load_wall_calibration() -> dict:
    """Load the 40-civ wall-knob calibration table.

    Returns ``{}`` if the calibration module can't be imported (e.g.
    user runs the site builder before the calibration script lands).
    """
    try:
        import importlib.util
        path = REPO_ROOT / "tools" / "ai_design" / "wall_knob_calibration.py"
        spec = importlib.util.spec_from_file_location("wall_knob_calibration", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return dict(getattr(mod, "CALIBRATION", {}))
    except Exception as exc:
        print(f"  [warn] wall_knob_calibration not loadable: {exc}",
              file=sys.stderr)
        return {}


# Spec-token → calibration engine-key map. The calibration keys are the
# engine civ tokens used by ``kbGetCivName(cMyCiv)`` (e.g. ``French``,
# ``DEInca``, ``XPAztec``, ``ANWFrenchCanadians``); the spec keys are the
# user-facing leader-tagged tokens (e.g. ``French Louis XVIII Bourbon``,
# ``Inca Pachacuti``, ``Aztecs Montezuma``, ``Canadians Brock Revolution``).
# Building this once at module level keeps the per-civ render path O(1).
_SPEC_TO_CALIB_KEY: dict[str, str] = {
    # Base civs
    "French Louis XVIII Bourbon": "French",
    "Germans Frederick Great": "Germans",
    "Ottomans Suleiman": "Ottomans",
    "Chinese Kangxi": "Chinese",
    "Russians Ivan the Terrible": "Russians",
    "Russians Catherine": "Russians",  # legacy spec key compat
    "British Elizabeth": "British",
    "Portuguese Henry Navigator": "Portuguese",
    "Dutch Maurice Nassau": "Dutch",
    "Spanish Isabella Castile": "Spanish",
    "Japanese Tokugawa Ieyasu": "Japanese",
    # DE / XP civs
    "Inca Pachacuti": "DEInca",
    "Maltese Valette": "DEMaltese",
    "Ethiopians Menelik": "DEEthiopians",
    "Indians Akbar": "Indians",
    "Indians Shivaji": "Indians",
    "Hausa Usman dan Fodio": "DEHausa",
    "Italians Garibaldi": "DEItalians",
    "Mexicans Hidalgo Standard": "DEMexicans",
    "United States Washington": "DEAmericans",
    "Swedes Gustavus Adolphus Swedish": "DESwedish",
    "Aztecs Montezuma": "XPAztec",
    "Haudenosaunee Hiawatha Iroquois": "XPIroquois",
    "Lakota Crazy Horse": "XPSioux",
    "Lakota Gall": "XPSioux",
    # ANW (revolutionary) civs
    "Canadians Brock Revolution": "ANWCanadians",
    "Chileans OHiggins Revolution": "ANWChileans",
    "Peruvians Santa Cruz Peru Revolution": "ANWPeruvians",
    "Egyptians Muhammad Ali Revolution": "ANWEgyptians",
    "Finnish Mannerheim Revolution": "ANWFinnish",
    "Haitians Louverture Revolution": "ANWHaitians",
    "Indonesians Diponegoro Revolution": "ANWIndonesians",
    "Mayans Canek Maya Revolution": "ANWMayans",
    "Barbary Barbarossa Corsair Revolution": "ANWBarbary",
    "South Africans Kruger Boer Revolution": "ANWSouthAfricans",
    "Brazil Pedro Revolution": "ANWBrazil",
    "Romanians Cuza Revolution": "ANWRomanians",
    "Revolutionary France Robespierre Revolution": "ANWRevFrance",
    "Napoleonic France Napoleon Bonaparte Revolution": "ANWNapoleonicFrance",
    "Argentines San Martin Revolution": "ANWArgentines",
    "Columbians Bolivar Colombia Revolution": "ANWColumbians",
    "Hungarians Kossuth Revolution": "ANWHungarians",
    "Texians Sam Houston Texas Revolution": "ANWTexians",
}


_WALL_SECONDARY_NAMES = {
    -1: "none",
    0: "FortressRing",
    1: "Chokepoint",
    2: "Coastal",
    3: "Frontier",
    4: "Urban",
    5: "Mobile",
}


def _spec_token_to_calib_key(token: str) -> str | None:
    """Map a spec token (e.g. ``Brazil Pedro Revolution``) to the calibration
    engine-key (e.g. ``ANWBrazil``)."""
    return _SPEC_TO_CALIB_KEY.get(token)


def _capture_date(p) -> str:
    """YYYY-MM-DD the screenshot file was captured (file mtime); '' on error."""
    try:
        import datetime as _dt
        return _dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
    except (OSError, ValueError, AttributeError):
        return ""


_AGE_NAMES_NUM = {"1": "Discovery", "2": "Colonial", "3": "Fortress",
                  "4": "Industrial", "5": "Imperial"}


def _fmt_pct_band(b) -> str:
    if isinstance(b, list) and len(b) == 2:
        return f"{int(round(b[0] * 100))}\u2013{int(round(b[1] * 100))}%"
    return "\u2013"


def _fmt_ms_window(w) -> str:
    if not (isinstance(w, list) and len(w) == 2):
        return "\u2013"
    def mmss(ms):
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"
    return f"{mmss(w[0])}\u2013{mmss(w[1])}"


def _render_per_age_doctrine_block(claims: dict) -> str:
    """Testable per-age doctrine: posture + composition bands + age-up window,
    with the difficulty-scaling model. Bands are Expert-level; the engine
    (anwDifficultyScale.xs) scales execution intensity by difficulty."""
    pa = (claims or {}).get("per_age") or {}
    rows = []
    for an in ("1", "2", "3", "4", "5"):
        a = pa.get(an)
        if not a:
            continue
        comp = a.get("comp", {})
        post = a.get("posture", "\u2013")
        rows.append(
            f'<div class="pad-row">'
            f'<span class="pad-age">{_AGE_NAMES_NUM.get(an, an)}</span>'
            f'<span class="pad-post pad-{post}">{post}</span>'
            f'<span class="pad-comp">inf {_fmt_pct_band(comp.get("inf"))} '
            f'&middot; cav {_fmt_pct_band(comp.get("cav"))} '
            f'&middot; art {_fmt_pct_band(comp.get("art"))}</span>'
            f'<span class="pad-ageup">{_fmt_ms_window(a.get("ageup_by_ms"))}</span>'
            f'</div>'
        )
    if not rows:
        return ""
    diff = (
        '<div class="pad-diff"><b>Difficulty scaling:</b> Sandbox&nbsp;25% '
        '&rarr; Easy&nbsp;45% &rarr; Moderate&nbsp;65% &rarr; Hard&nbsp;85% '
        '&rarr; Expert&nbsp;100% intensity. The bands above are the Expert '
        'doctrine; lower difficulty scales execution down (closure&nbsp;%, '
        'wall villagers, army size, forward aggression). Style never changes '
        '\u2014 only how completely the nation executes it.</div>'
    )
    return (
        '<div class="pad-block">'
        '<div class="pad-head">Per-age doctrine '
        '<span class="pad-sub">verifiable &middot; Expert bands, difficulty-scaled</span></div>'
        '<div class="pad-cols"><span>Age</span><span>Posture</span>'
        '<span>Composition&nbsp;(inf&middot;cav&middot;art)</span><span>Age-up</span></div>'
        + "".join(rows) + diff + '</div>'
    )


def _load_farm_results() -> dict:
    """{engine_civ: grade} from the latest sim-farm run; {} if not yet run.

    grade = {intensity, overall, checks:[[name, verdict, detail], ...]} written
    by tools/sim_farm/driver.py to artifacts/sim_farm/results.json.
    """
    path = REPO_ROOT / "artifacts" / "sim_farm" / "results.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for r in rows:
        eng, g = r.get("engine_civ"), r.get("grade")
        if eng and g:
            out[eng] = g   # latest wins
    return out


def _render_tested_block(engine_civ: str | None, farm_results: dict) -> str:
    """Observed (tested) behaviour beside the designed doctrine. Shows the farm's
    PASS/WARN/FAIL per check, or a 'not yet tested' note before the farm runs."""
    g = farm_results.get(engine_civ or "")
    if not g:
        return (
            '<div class="tested-block tested-empty-block">'
            '<div class="tested-head">Tested behaviour '
            '<span class="tested-sub">designed vs. observed</span></div>'
            '<div class="tested-empty">Not yet tested \u2014 run the sim farm to '
            'populate (<code>python3 -m tools.sim_farm.driver</code>).</div></div>'
        )
    overall = g.get("overall", "?")
    inten = g.get("intensity", "")
    rows = []
    for chk in g.get("checks", []):
        name, verdict, detail = (list(chk) + ["", "", ""])[:3]
        rows.append(
            f'<div class="tested-row tested-{verdict}">'
            f'<span class="tested-check">{html.escape(str(name))}</span>'
            f'<span class="tested-verdict">{html.escape(str(verdict))}</span>'
            f'<span class="tested-detail">{html.escape(str(detail))}</span></div>'
        )
    return (
        '<div class="tested-block">'
        '<div class="tested-head">Tested behaviour '
        f'<span class="tested-sub">observed @ {inten}% intensity \u2014 '
        f'<b class="tested-{overall}">{overall}</b></span></div>'
        + "".join(rows) + '</div>'
    )


def _render_wall_doctrine_block(token: str, calib: dict,
                                 ws: int | None) -> str:
    """Render the per-civ wall doctrine block: 15-knob compact summary +
    doctrine rationale string. Empty string if no calibration row exists.

    Rendered directly under the per-age strategy block on the civ card.
    """
    key = _spec_token_to_calib_key(token)
    if not key or key not in calib:
        return ""
    kn = calib[key]
    is_mobile = (kn.get("strategy") == 5)
    sec_name = _WALL_SECONDARY_NAMES.get(kn.get("secondary"), "?")
    age2stone = "yes" if kn.get("age2stone") else "no"
    no_water = "yes" if kn.get("no_water") else "no"

    # Each knob renders on its OWN line: fixed-width label · value · a
    # plain-English explanation to the right of what that knob actually
    # does (descriptions mirror the canonical comments in aiHeader.xs).
    def _krow(label: str, val, desc: str, emph: bool = False) -> str:
        cls = "wall-knob-row wk-emph" if emph else "wall-knob-row"
        return (
            f'<div class="{cls}">'
            f'<span class="wk-label">{label}</span>'
            f'<span class="wk-val">{val}</span>'
            f'<span class="wk-desc">{desc}</span>'
            f'</div>'
        )

    # Mobile civs get a short "no walls — outpost screen" block; everyone
    # else gets the full 15-knob list so the user can sanity-check the
    # actual gANWWall* values that fire for that civ.
    if is_mobile:
        rows = [
            _krow("Strategy", "Mobile (s5)",
                  "No perimeter walls — relies on army, scouts and outposts"),
            _krow("Outposts", kn.get("outposts", 0),
                  "Outposts planted as a detection / defensive screen"),
            _krow("Secondary fallback", sec_name,
                  "Wall strategy used only if forced onto the defensive"),
            _krow("No-water build", no_water,
                  "Refuse to place wall pieces on water tiles"),
        ]
    else:
        rows = [
            _krow("Radius", kn.get("radius", 0),
                  "Ring / segment radius in tiles"),
            _krow("Gates", kn.get("gates", 0),
                  "Number of gates left in the ring for traffic / sorties"),
            _krow("Age 2 stone", age2stone,
                  "Upgrade palisade &rarr; stone at Colonial (Age II) vs. staying wood"),
            _krow("Triggers age", kn.get("trigger_age", 0),
                  "First age in which the AI starts laying walls"),
            _krow("Segment len", kn.get("seg_len", 0),
                  "Length (tiles) of each chokepoint wall segment"),
            _krow("Towers", kn.get("towers", 0),
                  "Place a defensive tower every N wall pieces (0 = none)"),
            _krow("Secondary", sec_name,
                  "Fallback strategy if the primary is impossible on this map"),
            _krow("Vils", kn.get("vils", 0),
                  "Villagers dispatched to build the wall plan"),
            _krow("Fwd bias", kn.get("fwd_bias", 0),
                  "0.0 = hug Town Center &middot; 1.0 = push out to the chokepoint"),
            _krow("Outer ring", kn.get("outer_ring", 0),
                  "Offset for a second outer ring (0 = single ring)"),
            _krow("Outposts", kn.get("outposts", 0),
                  "Outposts planted before the first wall goes up"),
            _krow("Repair", kn.get("repair", 0),
                  "Repair urgency: 0 ignore &middot; 1 lazy &middot; 2 normal &middot; 3 instant"),
            _krow("Closure target", f'{kn.get("closure_pct", 0)}%',
                  "Ring coverage % the AI counts as &ldquo;walled in / done&rdquo;",
                  emph=True),
            _krow("No-water build", no_water,
                  "Refuse to place wall pieces on water tiles"),
        ]
    body = '<div class="wall-knobs">' + "".join(rows) + '</div>'
    doctrine = _safe_text(kn.get("doctrine") or "")
    ws_name = STRATEGY_NAMES.get(ws, "?") if ws is not None else "?"
    return (
        '<div class="wall-block">'
        f'<div class="wall-block-header">Walling doctrine '
        f'<span class="wall-block-strat">{_safe_text(ws_name)}</span></div>'
        f'<div class="wall-block-prose">{doctrine}</div>'
        f'{body}'
        '</div>'
    )


# Site-side English fallback for chatset lines that were authored in the
# leader's native language (Spanish for San Martín / Hidalgo / Pedro I,
# French for Napoleon / Robespierre, etc.). Per user feedback (2026-05-27)
# the release readiness site must surface every voice line in English.
# Keys are the exact `<String>` text from chatsetsmods.xml; values are the
# English rendering used at site-render time.
#
# This is a *display* layer only — the XML still ships the native-language
# strings so the leader keeps their authentic in-game voice. A separate
# pass translates the XML itself for the production audio subtitles.
_QUOTE_EN_OVERRIDES: dict[str, str] = {
    # anw_argentines — San Martín
    "Seamos libres, lo demás no importa. Avanzamos juntos.":
        "Let us be free, all else is secondary. We march together.",
    "He cruzado los Andes. Un campo de batalla no me detendrá.":
        "I have crossed the Andes. A single battlefield will not stop me.",
    "Los fortines de la frontera. No ciudadelas — solo vigías.":
        "Frontier blockhouses. Not citadels — only watchtowers.",
    "Se esconde. El gaucho no teme paredes.":
        "He hides. The gaucho fears no walls.",
    "Un patriota de la Pampa. Los Andes lo recuerdan.":
        "A patriot of the Pampas. The Andes will remember him.",
    "Como en Chacabuco: los Andes en la espalda, la victoria en el puño.":
        "Like at Chacabuco — the Andes at our back, victory in our fist.",
    # anw_bajacalifornians — Vicente Guerrero / mission-era
    "El presidio de Loreto. Adobe y torre. La misión es fortaleza.":
        "The Loreto presidio. Adobe and tower. The mission is a fortress.",
    # anw_mexicans / anw_mexicansrev — Hidalgo
    "¡Viva la Virgen de Guadalupe! Caminamos juntos.":
        "Long live the Virgin of Guadalupe! We march together.",
    "¡El Grito de Dolores! Spain will hear us from the pulpit itself.":
        "The Cry of Dolores! Spain will hear us from the pulpit itself.",
    "La Alhóndiga stands. The iglesias become fortresses when the Republic calls.":
        "The Alhóndiga stands. The churches become fortresses when the Republic calls.",
    "A gachupín hides. Our machetes do not tire.":
        "A Spaniard hides. Our machetes do not tire.",
    "Un hijo de Dolores ha caído. La República le honra.":
        "A son of Dolores has fallen. The Republic honors him.",
    "Un hijo de Dolores ha caído. The Republic honors him.":
        "A son of Dolores has fallen. The Republic honors him.",
    "¡Por la independencia! The parish rises, the viceroy's men fall.":
        "For independence! The parish rises, the viceroy's men fall.",
    # anw_spanish — Isabella
    "The alcázar holds. No Moor, no heretic shall pass.":
        "The royal citadel holds. No invader, no heretic shall pass.",
    # anw_french — Napoleon
    "Marshal, field fortifications only. The Grande Armée advances, not hides.":
        "Marshal, field fortifications only. The Grand Army advances, it does not hide.",
    "Un officier brave est tombé. We avenge him with French arms.":
        "A brave officer has fallen. We avenge him with French arms.",
    # anw_inca — Pachacuti
    "The stones of Sacsayhuamán fit without mortar. As the land itself.":
        "The stones of Sacsayhuaman fit without mortar — as the land itself.",
}


def _english_quote(s: str) -> str:
    """Translate a single chatset line to English when an override exists.

    Falls back to the original string so already-English lines pass
    through unchanged. The override table is keyed on the exact
    chatset string so unsupervised drift in the XML won't silently
    re-introduce native-language lines on the site without us noticing.
    """
    return _QUOTE_EN_OVERRIDES.get(s, s)


def _render_civ_quotes_block(token: str, calib_key: str | None,
                             ic: dict, shared: dict,
                             chatsets: dict) -> str:
    """Render the per-civ quote block: every voice line this civ speaks,
    in English, in a single flat list. Per user feedback (2026-05-27):
    no <details> dropdown, no per-category split, no shared-tactical
    section — just *one* list of quotes per nation so the user can
    eyeball them at a glance.

    The list is composed of:
      - 6 engine chatset lines (translated to English if needed)
      - 2 leader insults
      - 2 leader compliments
      - 4 shared tactical lines (retreat / rout / bulk-assault / decap)

    Returns "" if no calib key resolves (e.g. token not yet in spec).
    """
    if not calib_key:
        return ""
    bundle = _ecq_quotes_for_spec_token(token, calib_key, ic, shared,
                                        chatsets)
    insults = bundle.get("insults") or []
    compliments = bundle.get("compliments") or []
    chatset_rows = bundle.get("chatset") or []
    tac = bundle.get("shared_tactical") or {}

    if not insults and not compliments and not chatset_rows:
        return ""

    # Build the combined list. Each entry is (kind_label, english_text).
    lines: list[tuple[str, str]] = []
    for row in chatset_rows:
        tag = (row.get("tag") or "").strip()
        sline = _english_quote((row.get("string") or "").strip())
        if sline:
            lines.append((tag, sline))
    for ln in insults:
        lines.append(("Insult", _english_quote(ln)))
    for ln in compliments:
        lines.append(("Compliment", _english_quote(ln)))
    for k, lbl in (("retreat", "Retreat"), ("rout", "Rout"),
                   ("bulk_assault", "Bulk assault"),
                   ("decapitation", "Decapitation")):
        ln = (tac.get(k) or "").strip()
        if ln:
            lines.append((lbl, _english_quote(ln)))

    if not lines:
        return ""

    parts: list[str] = []
    parts.append('<div class="quote-block">')
    parts.append('<div class="quote-block-title">Voice lines '
                 f'<span class="qb-meta">({len(lines)} lines)</span>'
                 '</div>')
    parts.append('<ul class="qb-flat">')
    for kind, txt in lines:
        parts.append(
            '<li>'
            f'<span class="qb-kind">{_safe_text(kind)}</span>'
            f'<span class="qb-text">&ldquo;{_safe_text(txt)}&rdquo;</span>'
            '</li>'
        )
    parts.append('</ul>')
    parts.append('</div>')
    return "".join(parts)


def _load_revolution_paths() -> dict:
    """Load the canonical parent↔target revolution map from
    ``tools/validation/revolution_paths.json``. Returns ``{}`` if the
    file is missing so the site still builds during early bootstrap.

    The file ships two views — ``parent_to_targets`` (e.g. Spanish →
    [Mexicans, Argentines, …]) and ``target_to_parents`` (e.g. Mexicans
    → [Spanish]) — plus an optional ``doctrine_notes`` dict that
    annotates each target with its leader doctrine. Edit that JSON to
    fix the data; do not touch this loader.
    """
    if not REVOLUTION_PATHS_JSON.exists():
        return {}
    try:
        return json.loads(REVOLUTION_PATHS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[build_release_readiness_site] revolution_paths.json "
              f"parse error: {exc}", file=sys.stderr)
        return {}


# Revolution targets that aren't full ANW civs but have a flag icon.
_REV_TARGET_FLAG_EXTRA: dict[str, str] = {
    "Baja Californians": "Flag_baja_californian.png",
    "Californians": "Flag_californian.png",
    "Central Americans": "Flag_Central_American.png",
    "Rio Grande": "Flag_rio_grande.png",
    "Yucatan": "Flag_yucatan.png",
}


def _stage_revolution_target_flags(spec: dict, staged_flags: dict,
                                   revolution_paths: dict) -> dict[str, str]:
    """{target_label: flag_rel} for every revolution target (roster + extras)."""
    civs = spec.get("civs", spec)
    label2anw = {(c.get("civ_label") or ""): _civ_token_to_anw(tok)
                 for tok, c in civs.items()}
    out: dict[str, str] = {}
    targets = {t for v in (revolution_paths.get("parent_to_targets") or {}).values()
               for t in v}
    for t in targets:
        anw = label2anw.get(t)
        if anw and anw in staged_flags:
            out[t] = staged_flags[anw]
        elif t in _REV_TARGET_FLAG_EXTRA:
            src = _FLAGS_SRC_DIR / _REV_TARGET_FLAG_EXTRA[t]
            if src.is_file():
                slug = re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")
                _SITE_FLAG_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, _SITE_FLAG_DIR / f"rev_{slug}.png")
                    out[t] = f"flags/rev_{slug}.png"
                except OSError:
                    pass
    return out


def _render_revolt_into_header(civ_label: str, revolution_paths: dict,
                                target_flags: dict) -> str:
    """Header chips listing the nations this civ can revolt INTO (flag + name).
    Empty string for civs that are not revolution parents."""
    targets = (revolution_paths.get("parent_to_targets") or {}).get(civ_label) or []
    if not targets:
        return ""
    chips = []
    for t in targets:
        disp = CIV_LABEL_DISPLAY_OVERRIDE.get(t, t)
        fr = target_flags.get(t)
        flag = (f'<img class="rev-into-flag" src="{html.escape(fr)}" alt="">'
                if fr else '')
        chips.append(
            f'<span class="rev-into-chip" title="{_safe_text(disp)}">'
            f'{flag}<span class="rev-into-name">{_safe_text(disp)}</span></span>'
        )
    return ('<div class="rev-into">'
            '<span class="rev-into-label">Revolts&nbsp;into</span>'
            + "".join(chips) + '</div>')


def _render_civ_revolution_block(civ_label: str,
                                  revolution_paths: dict) -> str:
    """Render the revolution-paths block for one civ.

    Two cases:

    1. The civ is a PARENT (e.g. Spanish): show
       "Revolution paths → [Mexicans · Argentines · …]" with optional
       per-target doctrine notes so the user can see at a glance which
       revolutions are available from this civ.

    2. The civ is a TARGET (e.g. Argentines): show
       "Revolts from → Spanish" — the historical parent(s) this
       revolution civ derives from.

    Returns "" if the civ appears in neither map.
    """
    if not revolution_paths:
        return ""
    parents_to_targets = revolution_paths.get("parent_to_targets") or {}
    targets_to_parents = revolution_paths.get("target_to_parents") or {}
    doctrine_notes = revolution_paths.get("doctrine_notes") or {}

    targets = parents_to_targets.get(civ_label) or []
    parents = targets_to_parents.get(civ_label) or []

    if not targets and not parents:
        return ""

    parts: list[str] = []
    parts.append('<div class="rev-block">')
    if targets:
        parts.append('<div class="rev-block-title">Revolution paths '
                     f'<span class="rev-meta">({len(targets)} '
                     f'target{"s" if len(targets) != 1 else ""})</span>'
                     '</div>')
        parts.append('<ul class="rev-targets">')
        for t in targets:
            note = doctrine_notes.get(t, "")
            t_display = CIV_LABEL_DISPLAY_OVERRIDE.get(t, t)
            if note:
                parts.append(
                    f'<li><span class="rev-target">{_safe_text(t_display)}</span>'
                    f'<span class="rev-note">{_safe_text(note)}</span></li>'
                )
            else:
                parts.append(
                    f'<li><span class="rev-target">{_safe_text(t_display)}</span></li>'
                )
        parts.append('</ul>')
    if parents:
        # A revolution target may itself appear under parents (e.g. some
        # civs in the spec are reachable via *another* revolution civ).
        # Render both rows when both exist so the user sees the full
        # context.
        if targets:
            parts.append('<div class="rev-block-sep"></div>')
        parts.append('<div class="rev-block-title">Revolts from '
                     f'<span class="rev-meta">'
                     f'({len(parents)} parent'
                     f'{"s" if len(parents) != 1 else ""})</span></div>')
        parts.append('<div class="rev-parents">')
        for p in parents:
            p_display = CIV_LABEL_DISPLAY_OVERRIDE.get(p, p)
            parts.append(
                f'<span class="rev-parent">{_safe_text(p_display)}</span>'
            )
        parts.append('</div>')
    parts.append('</div>')
    return "".join(parts)


def _render_civ_art_surfaces_block(anw_token: str,
                                    art_info: dict | None,
                                    avatar_rel: str | None = None) -> str:
    """Render a horizontal strip of every art surface for one civ.

    Per user feedback (2026-05-27) the standalone "Art surfaces" section
    was removed — every civ instead gets its 10 art-surface thumbs
    embedded directly under the home-city deck block. Surfaces that
    haven't been captured render as a dashed broken-image placeholder
    so the user can spot coverage gaps without leaving the civ card.

    ``art_info`` is the entry from ``collect_art_surfaces()`` for this
    civ (or None if no folder exists yet).

    The ``lobby_portrait`` (leader portrait) surface is rendered from the
    civ's staged card-header avatar (``avatar_rel``) rather than the raw
    capture, so the art-surfaces leader portrait is GUARANTEED to be the
    same image as the little circle in the card header (the user requires
    these to match, and some raw lobby captures are bad — e.g. a harbor
    scene instead of the leader).
    """
    thumb_map: dict[str, str] = {}
    if art_info:
        for name, rel in art_info.get("thumbs", []) or []:
            thumb_map[name] = rel
    parts: list[str] = []
    parts.append('<div class="civ-art-block">')
    captured = sum(1 for s in ART_SURFACE_ORDER
                   if s in thumb_map or (s == "lobby_portrait" and avatar_rel))
    parts.append('<div class="civ-art-title">Art surfaces '
                 f'<span class="civ-art-meta">'
                 f'({captured}/{len(ART_SURFACE_ORDER)} captured)</span></div>')
    parts.append('<div class="civ-art-row">')
    for surf in ART_SURFACE_ORDER:
        label = ART_SURFACE_LABELS.get(surf, surf)
        rel = thumb_map.get(surf)
        # Leader portrait: always mirror the card-header circle so the two match.
        if surf == "lobby_portrait" and avatar_rel:
            parts.append(
                '<div class="civ-art-cell">'
                f'<img src="{html.escape(avatar_rel)}" '
                f'alt="lobby_portrait" '
                f'title="{html.escape(anw_token)} — Leader portrait" '
                f'data-civ="{html.escape(anw_token)}" data-title="Leader portrait" '
                f'onclick="showImg(this)">'
                f'<div class="civ-art-label">Leader portrait</div>'
                '</div>'
            )
            continue
        if rel:
            rel_from_site = _site_relative(rel)
            parts.append(
                '<div class="civ-art-cell">'
                f'<img src="{html.escape(rel_from_site)}" '
                f'alt="{html.escape(surf)}" '
                f'title="{html.escape(anw_token)} — {html.escape(label)}" '
                f'data-civ="{html.escape(anw_token)}" data-title="{html.escape(label)}" '
                f'onclick="showImg(this)">'
                f'<div class="civ-art-label">{html.escape(label)}</div>'
                '</div>'
            )
        else:
            parts.append(
                '<div class="civ-art-cell">'
                '<div class="civ-art-missing" '
                f'title="{html.escape(anw_token)} — {html.escape(label)} '
                'not yet captured">—</div>'
                f'<div class="civ-art-label civ-art-label-missing">'
                f'{html.escape(label)}</div>'
                '</div>'
            )
    parts.append('</div></div>')
    return "".join(parts)


def _build_screenshot_index() -> dict[str, list[Path]]:
    """Walk ``ART_DIR`` once and return ``{ANW<civ>: [search_dirs]}``.

    Two capture runners landed screenshots in two different folder
    layouts:
      * The batch runner uses ``batch_NN_ANW<civ>/`` (e.g.
        ``batch_01_ANWBritish/01_lobby.png``).
      * The per-civ runner uses ``ANW<civ>/full/`` (e.g.
        ``ANWFrench/full/01_lobby.png``).

    The renderer needs to search BOTH for each civ — batch wins when
    present (it covers the canonical eight surfaces), and the per-civ
    ``full/`` directory backstops everything else (and is the only
    coverage source for the 40+ civs the batch runner didn't reach).
    Search order: batch first, then per-civ ``full/``.
    """
    out: dict[str, list[Path]] = {}
    if not ART_DIR.exists():
        return out
    for civ_dir in sorted(ART_DIR.iterdir()):
        if not civ_dir.is_dir():
            continue
        # batch_NN_ANWFoo  ->  ANWFoo
        m = re.match(r"^batch_\d+_(ANW.+)$", civ_dir.name)
        if m:
            out.setdefault(m.group(1), []).append(civ_dir)
            continue
        # ANWFoo/full/     ->  ANWFoo
        if civ_dir.name.startswith("ANW"):
            full = civ_dir / "full"
            if full.is_dir():
                out.setdefault(civ_dir.name, []).append(full)
            # Also search the civ root dir itself — the ANW capture
            # runner drops in-game screenshots directly under ANWFoo/
            # with names like 01_diplomacy.png, 02_scoreboard.png, etc.
            out.setdefault(civ_dir.name, []).append(civ_dir)
    return out


# ---------------------------------------------------------------------------
# Perceptual-duplicate guard for in-game screenshot columns
#
# Problem: the ANW capture pipeline can fire every shot during the AoE3
# "Asset Preloading" splash screen.  For the British civ, ~7 canonical
# column slots resolved to visually identical splash copies, so the site
# reported "10/12 captured" with wrong images in most HUD/diplomacy/etc.
# slots.
#
# Guard: after resolving per-column hits, group columns whose avg-hash
# values are within INGAME_DUP_HAMMING bits of each other.  Any group
# spanning >= INGAME_DUP_GROUP_MIN distinct column slots is treated as a
# stuck/splash capture and those slots are demoted to "missing".
#
# Calibration: good civs have 7-8 source PNGs that collapse into 3-5
# distinct perceptual groups, with the LARGEST group spanning at most 2-3
# column slots.  The British splash group spans 7+ slots.  A threshold of
# 4 slots cleanly separates the two populations.
# ---------------------------------------------------------------------------
INGAME_DUP_HAMMING: int = 10   # max Hamming distance to consider two shots identical
INGAME_DUP_GROUP_MIN: int = 4  # a group spanning this many slots → stuck/splash capture

# Module-level cache so we never re-hash the same file twice per run.
_avg_hash_cache: dict[Path, int | None] = {}


def _avg_hash(path: Path) -> int | None:
    """16×16 average-hash of *path* as a 256-bit integer, or None on failure.

    Delegates to tools.aoe3_automation.image_utils.avg_hash when available;
    falls back to an identical inline implementation otherwise so the site
    builder works in environments where the aoe3_automation package is absent.
    """
    if path in _avg_hash_cache:
        return _avg_hash_cache[path]
    result: int | None = None
    if _IMAGE_UTILS_AVAILABLE:
        result = _iu_avg_hash(path)
    elif _PIL_AVAILABLE:
        try:
            with _PILImage.open(path) as img:
                img = img.convert("L").resize((16, 16), _PILImage.LANCZOS)
                pixels = list(img.getdata())
                mean = sum(pixels) / len(pixels)
                bits = 0
                for p in pixels:
                    bits = (bits << 1) | (1 if p > mean else 0)
                result = bits
        except Exception:
            result = None
    _avg_hash_cache[path] = result
    return result


def _hamming(a: int | None, b: int | None) -> int:
    """Hamming distance between two 256-bit avg-hashes.  Returns 999 if either is None.

    Delegates to tools.aoe3_automation.image_utils.hamming when available.
    """
    if _IMAGE_UTILS_AVAILABLE:
        return _iu_hamming(a, b)
    if a is None or b is None:
        return 999
    return bin(a ^ b).count("1")


def _find_screenshot(search_dirs: list[Path],
                     candidates: list[str]) -> Path | None:
    """First (dir, candidate) hit wins. Returns None if no match."""
    for d in search_dirs:
        for fname in candidates:
            fpath = d / fname
            if fpath.exists():
                return fpath
    return None


def _render_civ_screenshots_block(
        anw_token: str,
        screenshot_index: dict[str, list[Path]]) -> str:
    """Render the in-game screenshot strip for one civ.

    Renders two rows:
      1. Canonical columns (``SCREENSHOT_COLUMNS``) — fixed-width grid
         so coverage gaps are visually obvious. Missing cells render
         as a dashed broken-image placeholder.
      2. Extras — any captured file in the civ's search dirs that
         isn't a canonical column candidate (age-up shots, AI base
         shots, awards screen, etc.). Only rendered if extras exist.
    """
    search_dirs = screenshot_index.get(anw_token, [])
    n_present = 0
    cell_rows: list[str] = []
    seen_paths: set[Path] = set()

    # --- Pass 1: resolve per-column file hits ---
    column_hits: list[tuple[str, Path | None]] = []
    for label, candidates in SCREENSHOT_COLUMNS:
        hit = _find_screenshot(search_dirs, candidates)
        column_hits.append((label, hit))

    # --- Pass 2: perceptual-duplicate guard ---
    # If a single perceptual group (avg-hash, Hamming <= INGAME_DUP_HAMMING)
    # spans >= INGAME_DUP_GROUP_MIN distinct column slots, all slots in that
    # group are demoted to "missing" (stuck/splash capture, e.g. British
    # "Asset Preloading" splash filling 7 canonical slots).
    resolved_hits: list[Path | None] = [h for _, h in column_hits]
    hashes = [_avg_hash(h) if h is not None else None for h in resolved_hits]

    # Build groups: each hit slot gets assigned to the earliest slot whose
    # hash is within INGAME_DUP_HAMMING of it.
    group_id: list[int | None] = [None] * len(resolved_hits)
    for i, hi in enumerate(hashes):
        if resolved_hits[i] is None:
            continue
        if group_id[i] is None:
            group_id[i] = i  # start a new group anchored at i
        for j in range(i + 1, len(resolved_hits)):
            if resolved_hits[j] is None:
                continue
            if group_id[j] is not None:
                continue
            if _hamming(hi, hashes[j]) <= INGAME_DUP_HAMMING:
                group_id[j] = group_id[i]

    # Count how many distinct column slots each group spans.
    from collections import Counter as _Counter
    group_sizes = _Counter(g for g in group_id if g is not None)
    # Slots belonging to groups that are too large → treat as missing.
    bogus_indices: set[int] = {
        idx for idx, g in enumerate(group_id)
        if g is not None and group_sizes[g] >= INGAME_DUP_GROUP_MIN
    }

    # --- Pass 3: render ---
    for col_idx, (label, hit) in enumerate(column_hits):
        if hit is not None and col_idx not in bogus_indices:
            seen_paths.add(hit)
            n_present += 1
            try:
                rel = hit.relative_to(REPO_ROOT)
            except ValueError:
                rel = hit
            rel_from_site = _site_relative(str(rel))
            _cmd = _recapture_cmd(anw_token, label)
            _tip = (f"{anw_token} — {label} ({hit.name})"
                    + (f"\nRe-grab: {_cmd}" if _cmd else ""))
            cell_rows.append(
                '<div class="civ-shot-cell">'
                f'<img src="{html.escape(rel_from_site)}" '
                f'alt="{html.escape(label)}" '
                f'title="{html.escape(_tip)}" '
                f'data-civ="{html.escape(anw_token)}" data-title="{html.escape(label)}" '
                f'data-date="{_capture_date(hit)}" '
                f'onclick="showImg(this)">'
                f'<div class="civ-shot-label">{html.escape(label)}</div>'
                '</div>'
            )
        else:
            _cmd = _recapture_cmd(anw_token, label)
            _tip = (f"{anw_token} — {label} not yet captured"
                    + (f"\nCapture: {_cmd}" if _cmd else ""))
            cell_rows.append(
                '<div class="civ-shot-cell">'
                '<div class="civ-shot-missing" '
                f'title="{html.escape(_tip)}">missing</div>'
                f'<div class="civ-shot-label civ-shot-label-missing">'
                f'{html.escape(label)}</div>'
                '</div>'
            )
        # Track seen_paths for extras dedup (even bogus hits should be excluded
        # from extras so they don't re-appear there).
        if hit is not None and col_idx in bogus_indices:
            seen_paths.add(hit)

    # Extras: any PNG in the civ's search dirs that isn't a canonical
    # candidate AND wasn't already shown above. Deduplicate by basename
    # in case batch + per-civ have the same extra file.
    extras: list[Path] = []
    seen_names: set[str] = set()
    for d in search_dirs:
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            if entry in seen_paths:
                continue
            if entry.name in _CANONICAL_SCREENSHOT_NAMES:
                # Canonical column candidate that simply wasn't selected
                # because an earlier candidate already filled the slot.
                continue
            if entry.name in seen_names:
                continue
            seen_names.add(entry.name)
            extras.append(entry)

    # --- AI round row ---
    ai_cell_rows: list[str] = []
    n_ai_present = 0
    for label, candidates in AI_SCREENSHOT_COLUMNS:
        hit = _find_screenshot(search_dirs, candidates)
        if hit is not None:
            seen_paths.add(hit)
            n_ai_present += 1
            try:
                rel = hit.relative_to(REPO_ROOT)
            except ValueError:
                rel = hit
            rel_from_site = _site_relative(str(rel))
            _cmd = _recapture_cmd(anw_token, label)
            _tip = (f"{anw_token} — {label} ({hit.name})"
                    + (f"\nRe-grab: {_cmd}" if _cmd else ""))
            ai_cell_rows.append(
                '<div class="civ-shot-cell">'
                f'<img src="{html.escape(rel_from_site)}" '
                f'alt="{html.escape(label)}" '
                f'title="{html.escape(_tip)}" '
                f'data-civ="{html.escape(anw_token)}" data-title="{html.escape(label)}" '
                f'data-date="{_capture_date(hit)}" '
                f'onclick="showImg(this)">'
                f'<div class="civ-shot-label">{html.escape(label)}</div>'
                '</div>'
            )
        else:
            _cmd = _recapture_cmd(anw_token, label)
            _tip = (f"{anw_token} — {label} not yet captured"
                    + (f"\nCapture: {_cmd}" if _cmd else ""))
            ai_cell_rows.append(
                '<div class="civ-shot-cell">'
                '<div class="civ-shot-missing" '
                f'title="{html.escape(_tip)}">missing</div>'
                f'<div class="civ-shot-label civ-shot-label-missing">'
                f'{html.escape(label)}</div>'
                '</div>'
            )

    # Single unified group (user request 2026-06-02): all surfaces — player
    # round + AI round — in ONE wrapped row with no "HUMAN ROUND" / "AI ROUND"
    # / "Additional captures" sub-headings. The redundant "extras" (alternate
    # captures of surfaces already shown as canonical columns) are intentionally
    # NOT rendered, so the strip never shows duplicate images of the same
    # surface. ``extras`` is still computed above only to mark those paths seen.
    _ = extras  # intentionally unused in the merged single-group layout
    total_present = n_present + n_ai_present
    total_slots = len(SCREENSHOT_COLUMNS) + len(AI_SCREENSHOT_COLUMNS)
    parts: list[str] = []
    parts.append('<div class="civ-shot-block">')
    parts.append('<div class="civ-shot-title">In-game screenshots '
                 f'<span class="civ-shot-meta">'
                 f'({total_present}/{total_slots} captured)'
                 '</span></div>')
    parts.append('<div class="civ-shot-row">')
    parts.extend(cell_rows)
    parts.extend(ai_cell_rows)
    parts.append('</div>')
    parts.append('</div>')
    return "".join(parts)


def collect_validator_results() -> dict:
    if not GATE_REPORT.exists():
        return {"overall": "MISSING", "results": [], "counts": {},
                "total": 0, "run_id": None}
    return json.loads(GATE_REPORT.read_text(encoding="utf-8"))


def collect_spec_data() -> dict:
    if not SPEC_PATH.exists():
        return {"civs": {}}
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def collect_per_age_strategies() -> dict[str, dict[str, str]]:
    """Extract ``window.NATION_PLAYSTYLE`` from ``a_new_world.html`` and return
    a mapping ``{spec_token: {"Discovery": text, "Colonial": text, ...}}``.

    The site's per-civ card uses this in place of the old
    ``first build / expects / distance / deadlines`` claim block —
    five short historical, DLC-aware strategy paragraphs per civ, one per
    age. Authored centrally in ``a_new_world.html`` so the modal and the
    release-readiness site share a single source of truth.

    Returns ``{}`` if the HTML can't be parsed (build still completes,
    site just falls back to the claim block).
    """
    html_path = REPO_ROOT / "a_new_world.html"
    if not html_path.exists():
        return {}
    text = html_path.read_text(encoding="utf-8")
    m = re.search(r"window\.NATION_PLAYSTYLE\s*=\s*(\{.*?\});", text, re.DOTALL)
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}
    out: dict[str, dict[str, str]] = {}
    AGES = ("Discovery", "Colonial", "Fortress", "Industrial", "Imperial")
    for key, entry in data.items():
        ages = entry.get("ages") if isinstance(entry, dict) else None
        if not isinstance(ages, dict):
            continue
        # Decode any HTML entities (&mdash; etc.) so the resulting text
        # renders cleanly inside the release-readiness HTML.
        decoded: dict[str, str] = {}
        for a in AGES:
            v = ages.get(a)
            if isinstance(v, str) and v.strip():
                decoded[a] = html.unescape(v)
        if decoded:
            out[key] = decoded
    return out


def collect_behaviour_map() -> dict:
    if not BEHAVIOUR_MAP.exists():
        return {}
    return json.loads(BEHAVIOUR_MAP.read_text(encoding="utf-8"))


def collect_art_surfaces() -> dict[str, dict]:
    """Map of ANW-token -> {label, thumbs: [(name, rel_path)], manifest_path}."""
    out: dict[str, dict] = {}
    if not ART_DIR.exists():
        return out
    for civ_dir in sorted(ART_DIR.iterdir()):
        if not civ_dir.is_dir():
            continue
        if not civ_dir.name.startswith("ANW"):
            continue
        manifest = civ_dir / "manifest.json"
        thumbs_dir = civ_dir / "thumbs"
        info: dict = {"token": civ_dir.name, "label": civ_dir.name.replace("ANW", "")}
        if manifest.exists():
            try:
                mf = json.loads(manifest.read_text(encoding="utf-8"))
                info["label"] = mf.get("civ_label") or info["label"]
                info["captured_at"] = mf.get("captured_at")
                info["status"] = mf.get("status")
            except Exception:
                pass
        thumbs: list[tuple[str, str]] = []
        if thumbs_dir.exists():
            for thumb in sorted(thumbs_dir.iterdir()):
                if thumb.suffix.lower() in (".webp", ".png", ".jpg"):
                    rel = thumb.relative_to(REPO_ROOT)
                    thumbs.append((thumb.stem, str(rel)))
        info["thumbs"] = thumbs
        out[civ_dir.name] = info
    return out


def get_git_meta() -> dict:
    """Best-effort git context for the release readiness header."""
    out = {}
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5).decode().strip()
        out["sha"] = sha
    except Exception:
        out["sha"] = "unknown"
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5).decode().strip()
        out["branch"] = branch
    except Exception:
        out["branch"] = "unknown"
    try:
        dirty = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "status", "--short"],
            stderr=subprocess.DEVNULL, timeout=10).decode().strip()
        out["dirty"] = bool(dirty)
        out["dirty_count"] = len(dirty.splitlines()) if dirty else 0
    except Exception:
        out["dirty"] = False
        out["dirty_count"] = 0
    return out


# ============================================================
# RENDERING
# ============================================================

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{max-width:100%;overflow-x:hidden}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#0e1117;color:#c9d1d9;line-height:1.5;padding:0;
     overflow-wrap:break-word;word-break:break-word}
header{background:linear-gradient(135deg,#0d4429 0%,#0a3621 100%);
       padding:32px 48px;border-bottom:1px solid #21262d}
header h1{font-size:32px;color:#f0f6fc;margin-bottom:8px}
header .meta{color:#8b949e;font-size:14px}
header .meta strong{color:#c9d1d9}
.badge{display:inline-block;padding:4px 10px;border-radius:4px;font-size:12px;
       font-weight:600;margin-right:8px}
.badge-pass{background:#1f6f43;color:#fff}
.badge-fail{background:#a4332a;color:#fff}
.badge-skip{background:#7d5e1a;color:#fff}
.badge-warn{background:#a37c25;color:#fff}
.badge-info{background:#2b3a55;color:#cce}

nav{background:#161b22;padding:12px 48px;border-bottom:1px solid #21262d;
    position:sticky;top:0;z-index:100;display:flex;gap:24px;
    flex-wrap:wrap}
nav a{color:#8b949e;text-decoration:none;font-size:14px;padding:6px 0}
nav a:hover{color:#58a6ff}
nav .tag{color:#3fb950;margin-left:4px;font-size:11px}
nav.related-reports-nav{background:#1a1f26;padding:8px 48px;border-bottom:1px solid #21262d;
    gap:12px;align-items:center}
nav.related-reports-nav .nav-label{color:#6e7681;font-size:12px;font-weight:600;
    text-transform:uppercase;letter-spacing:0.04em;margin-right:4px}
nav.related-reports-nav a{font-size:13px;color:#79c0ff;padding:4px 0}
nav.related-reports-nav a:hover{color:#58a6ff}

main{max-width:1800px;margin:0 auto;padding:32px 48px}
section{margin-bottom:48px;background:#161b22;border:1px solid #30363d;
        border-radius:6px;overflow:hidden}
section h2{font-size:22px;padding:16px 24px;background:#21262d;
           border-bottom:1px solid #30363d;color:#f0f6fc}
section .content{padding:24px}

/* Validator grid */
.validator-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
                gap:8px;margin-top:8px}
.validator-card{background:#0d1117;border:1px solid #30363d;border-radius:4px;
                padding:12px 14px;display:flex;justify-content:space-between;
                align-items:center;gap:8px;font-size:13px}
.validator-card.pass{border-left:3px solid #3fb950}
.validator-card.fail{border-left:3px solid #f85149}
.validator-card.skip{border-left:3px solid #d29922}
.validator-card .name{font-family:'SF Mono','Monaco',monospace;font-size:12px;
                      color:#c9d1d9;overflow:hidden;text-overflow:ellipsis}
.validator-card .verdict{font-weight:600;font-size:11px;letter-spacing:0.5px}
.validator-card .duration{color:#6e7681;font-size:10px}

/* Civ cards */
/* 2026-05-28: Single-column layout per user request — every civ card
   spans the full content width so all art assets + screenshot strips
   render at full size without horizontal scrolling inside the card.
   Was: repeat(auto-fill,minmax(420px,1fr)) which produced 2-3 columns
   depending on viewport width. */
.civ-grid{display:grid;grid-template-columns:1fr;
          gap:20px;margin-top:8px}
.civ-card{background:#0d1117;border:1px solid #30363d;border-radius:6px;
          padding:0;overflow:hidden}
.civ-card-header{padding:12px 16px;border-bottom:1px solid #21262d;
                 display:flex;justify-content:space-between;align-items:center;gap:12px}
.civ-card-header .leader-avatar{width:48px;height:48px;border-radius:50%;
                                object-fit:cover;object-position:center top;
                                border:2px solid #30363d;
                                background:#0d1117;flex-shrink:0;cursor:pointer;
                                transition:border-color 0.15s ease}
.civ-card-header .leader-avatar:hover{border-color:#58a6ff}
/* Nation flag in the card header (replaces the circular leader portrait). */
.civ-card-header .civ-flag{height:42px;width:auto;max-width:72px;
                           object-fit:contain;border:1px solid #30363d;
                           border-radius:3px;background:#0d1117;flex-shrink:0;
                           padding:2px;box-shadow:0 1px 3px rgba(0,0,0,0.4)}
.civ-card-header .civ-flag-missing{display:flex;align-items:center;
                           justify-content:center;height:42px;width:56px;
                           color:#484f58;font-size:20px}
/* "Revolts into" chips in the header (flag + name of each revolution target). */
.civ-card-header .rev-into{display:flex;align-items:center;gap:6px;
                           flex-wrap:wrap;flex:1 1 auto;margin:0 4px}
.civ-card-header .rev-into-label{font-size:9px;text-transform:uppercase;
                           letter-spacing:0.05em;color:#6e7681;font-weight:700}
.civ-card-header .rev-into-chip{display:inline-flex;align-items:center;gap:4px;
                           background:#161b22;border:1px solid #30363d;
                           border-radius:10px;padding:2px 8px 2px 3px;
                           font-size:10.5px;color:#c9d1d9}
.civ-card-header .rev-into-flag{height:14px;width:auto;border-radius:2px;
                           border:1px solid #30363d;flex-shrink:0}
.civ-card-header .rev-into-name{white-space:nowrap}
.civ-card-header .title-block{flex:1;min-width:0}
.civ-card-header h3{font-size:15px;color:#f0f6fc;
                    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.civ-card-header .strategy{font-size:11px;font-weight:600;padding:3px 8px;
                           border-radius:3px;color:#fff;white-space:nowrap}
.civ-card .body{padding:14px 16px;font-size:13px}
.civ-card .body p{margin-bottom:8px}
.civ-card .body .doctrine-label{font-weight:600;color:#58a6ff;margin-bottom:4px}
.civ-card .body .doctrine-summary{font-style:italic;color:#a3b3c2;margin-bottom:8px}
.civ-card .body .claim{font-size:12px;color:#8b949e}
.civ-card .body .claim strong{color:#c9d1d9}
.civ-card .per-age-strategy{margin-top:10px;border-top:1px solid #21262d;
  padding-top:10px;display:flex;flex-direction:column;gap:6px}
.civ-card .per-age-strategy .age-row{display:grid;grid-template-columns:78px 1fr;
  gap:8px;align-items:start}
.civ-card .per-age-strategy .age-key{font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.06em;color:#58a6ff;
  padding-top:1px}
.civ-card .per-age-strategy .age-text{font-size:11.5px;color:#c9d1d9;
  line-height:1.55}

/* Wall doctrine block — rendered directly under the per-age strategy
   block on each civ card. Surfaces the 15 gLLWall* knobs that fire
   for that civ plus the doctrine rationale string. Per user feedback
   (2026-05-27) the walling strategy is exposed inline on every card
   rather than hidden in a separate section. */
.civ-card .wall-block{margin-top:10px;border-top:1px solid #21262d;
  padding-top:10px}
.civ-card .wall-block-header{font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.06em;color:#d29922;
  margin-bottom:4px;display:flex;justify-content:space-between;
  align-items:center;gap:8px}
.civ-card .wall-block-strat{font-size:10px;font-weight:600;
  background:#1f4d7a;color:#fff;padding:2px 7px;border-radius:3px;
  letter-spacing:0.04em}
.civ-card .wall-block-prose{font-size:11.5px;color:#a3b3c2;
  line-height:1.55;font-style:italic;margin-bottom:6px}
/* Per-age doctrine block: testable posture/composition/age-up + difficulty. */
.civ-card .pad-block{margin-top:10px;border-top:1px solid #21262d;padding-top:10px}
.civ-card .pad-head{font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.06em;color:#58a6ff;margin-bottom:5px}
.civ-card .pad-sub{font-size:9.5px;font-weight:600;color:#6e7681;
  text-transform:none;letter-spacing:0;margin-left:6px}
.civ-card .pad-cols,.civ-card .pad-row{display:grid;
  grid-template-columns:74px 78px 1fr 64px;column-gap:8px;align-items:baseline}
.civ-card .pad-cols{font-size:9px;text-transform:uppercase;letter-spacing:0.04em;
  color:#6e7681;padding-bottom:3px;border-bottom:1px solid #1b2129}
.civ-card .pad-row{font-size:11px;padding:3px 0;border-bottom:1px solid #1b2129}
.civ-card .pad-age{color:#c9d1d9;font-weight:600}
.civ-card .pad-post{font-weight:700;font-size:10px;text-transform:uppercase}
.civ-card .pad-offensive{color:#f0883e}
.civ-card .pad-defensive{color:#58a6ff}
.civ-card .pad-balanced{color:#8b98a5}
.civ-card .pad-comp{color:#a3b3c2;font-variant-numeric:tabular-nums}
.civ-card .pad-ageup{color:#8b98a5;text-align:right;font-variant-numeric:tabular-nums}
.civ-card .pad-diff{margin-top:6px;font-size:10.5px;color:#8b98a5;line-height:1.5;
  background:#0d1117;border:1px solid #21262d;border-radius:4px;padding:6px 8px}
.civ-card .pad-diff b{color:#58a6ff}

/* Observed/tested behaviour block (designed vs observed, from the sim farm). */
.civ-card .tested-block{margin-top:10px;border-top:1px solid #21262d;padding-top:10px}
.civ-card .tested-head{font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.06em;color:#a371f7;margin-bottom:5px}
.civ-card .tested-sub{font-size:9.5px;font-weight:600;color:#6e7681;
  text-transform:none;letter-spacing:0;margin-left:6px}
.civ-card .tested-empty{font-size:10.5px;color:#6e7681;font-style:italic;
  background:#0d1117;border:1px dashed #30363d;border-radius:4px;padding:6px 8px}
.civ-card .tested-empty code{color:#8b98a5;font-size:10px}
.civ-card .tested-row{display:grid;grid-template-columns:120px 52px 1fr;
  column-gap:8px;align-items:baseline;font-size:10.5px;padding:2px 0;
  border-bottom:1px solid #1b2129}
.civ-card .tested-check{color:#c9d1d9;font-weight:600}
.civ-card .tested-verdict{font-weight:700;font-size:10px}
.civ-card .tested-detail{color:#8b98a5;font-variant-numeric:tabular-nums}
.civ-card .tested-PASS .tested-verdict,.civ-card b.tested-PASS{color:#3fb950}
.civ-card .tested-WARN .tested-verdict,.civ-card b.tested-WARN{color:#d29922}
.civ-card .tested-FAIL .tested-verdict,.civ-card b.tested-FAIL{color:#f85149}

/* One knob per line: fixed-width label · value · explanation. */
.civ-card .wall-knobs{display:flex;flex-direction:column;gap:0;
  font-size:11px;margin-top:4px}
.civ-card .wall-knob-row{display:grid;
  grid-template-columns:104px 52px 1fr;align-items:baseline;
  column-gap:10px;padding:3px 0;border-bottom:1px solid #1b2129}
.civ-card .wall-knob-row:last-child{border-bottom:none}
.civ-card .wk-label{color:#c9d1d9;font-weight:600;font-size:10px;
  text-transform:uppercase;letter-spacing:0.04em}
.civ-card .wk-val{color:#e6edf3;font-weight:700;text-align:right;
  font-variant-numeric:tabular-nums}
.civ-card .wk-desc{color:#8b98a5;font-size:10.5px;line-height:1.4}
.civ-card .wall-knob-row.wk-emph .wk-val{color:#3fb950}
.civ-card .wall-knob-row.wk-emph .wk-label{color:#3fb950}

/* Quote / chat-line block — every AI voice line this civ speaks, in
   English, in one flat list. Per user feedback (2026-05-27): no
   <details> dropdown; just show all the quotes inline so the user
   can read them at a glance. */
.civ-card .quote-block{margin-top:10px;border-top:1px solid #21262d;
  padding-top:10px;font-size:11.5px}
.civ-card .quote-block .quote-block-title{font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.06em;color:#79c0ff;
  margin-bottom:6px;display:flex;align-items:center;gap:8px}
.civ-card .quote-block .qb-meta{font-weight:400;color:#6e7681;
  font-size:10px;text-transform:none;letter-spacing:0}
.civ-card .quote-block .qb-flat{list-style:none;margin:0;padding:0;
  display:flex;flex-direction:column;gap:3px}
.civ-card .quote-block .qb-flat li{display:grid;
  grid-template-columns:130px 1fr;gap:8px;align-items:start;
  padding:3px 0;border-top:1px solid #161b22;line-height:1.45}
.civ-card .quote-block .qb-flat li:first-child{border-top:none}
.civ-card .quote-block .qb-kind{color:#8b949e;font-size:10px;
  font-weight:600;text-transform:uppercase;letter-spacing:0.04em;
  padding-top:1px;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.civ-card .quote-block .qb-text{color:#e6edf3;font-style:italic;
  font-size:11.5px}

/* Revolution-path block — for parent civs, lists every revolution
   target they can age-up into; for revolution civs, lists the
   historical parent(s) they derive from. Data is curated in
   tools/validation/revolution_paths.json. Per user request
   (2026-05-27): "add a revolution path for each nation that have
   revolution paths, so I can see which nations can revolt into what". */
.civ-card .rev-block{margin-top:10px;border-top:1px solid #21262d;
  padding-top:10px;font-size:11.5px}
.civ-card .rev-block .rev-block-title{font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.06em;color:#f0883e;
  margin-bottom:6px;display:flex;align-items:center;gap:8px}
.civ-card .rev-block .rev-meta{font-weight:400;color:#6e7681;
  font-size:10px;text-transform:none;letter-spacing:0}
.civ-card .rev-block .rev-block-sep{height:6px}
.civ-card .rev-block .rev-targets{list-style:none;margin:0;padding:0;
  display:flex;flex-direction:column;gap:3px}
.civ-card .rev-block .rev-targets li{display:grid;
  grid-template-columns:160px 1fr;gap:8px;align-items:start;
  padding:3px 0;border-top:1px solid #161b22;line-height:1.45}
.civ-card .rev-block .rev-targets li:first-child{border-top:none}
.civ-card .rev-block .rev-target{color:#ffa657;font-weight:600;
  font-size:11.5px}
.civ-card .rev-block .rev-note{color:#a3b3c2;font-size:11px;
  font-style:italic;line-height:1.4}
.civ-card .rev-block .rev-parents{display:flex;flex-wrap:wrap;gap:4px}
.civ-card .rev-block .rev-parent{background:#2a1f0e;
  border:1px solid #5a3d1a;border-radius:3px;padding:2px 8px;
  color:#ffa657;font-size:11px;font-weight:600}

/* Per-civ art surfaces strip — rendered inline under the home-city deck
   on every civ card per user feedback (2026-05-27). 10 surfaces in a
   horizontal flex row; missing surfaces show a dashed broken-image
   placeholder so coverage gaps are visible at a glance. */
.civ-card .civ-art-block{padding:10px 16px;border-top:1px solid #21262d;
  background:#0a0e14}
.civ-card .civ-art-title{font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.06em;color:#79c0ff;
  margin-bottom:6px;display:flex;align-items:center;gap:8px}
.civ-card .civ-art-meta{font-weight:400;color:#6e7681;font-size:10px;
  text-transform:none;letter-spacing:0}
.civ-card .civ-art-row{display:flex;gap:6px;flex-wrap:wrap;
  padding-bottom:2px}
.civ-card .civ-art-cell{flex-shrink:0;text-align:center;width:56px}
.civ-card .civ-art-cell img{height:56px;width:56px;object-fit:cover;
  border:1px solid #30363d;border-radius:3px;cursor:pointer;
  background:#0d1117;display:block;transition:border-color 0.12s ease}
.civ-card .civ-art-cell img:hover{border-color:#58a6ff}
.civ-card .civ-art-missing{height:56px;width:56px;background:#0d1117;
  border:1px dashed #30363d;border-radius:3px;display:flex;
  align-items:center;justify-content:center;color:#484f58;font-size:18px}
.civ-card .civ-art-label{font-size:9px;color:#8b949e;margin-top:2px;
  line-height:1.2;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.civ-card .civ-art-label-missing{color:#484f58}

/* Per-civ in-game screenshot strip — rendered inline under the art
   strip on every civ card per user feedback (2026-05-27). Every civ
   shows all 8 columns (lobby/HUD/scoreboard/diplomacy/HC/esc/endgame/
   abandon) even if the runner hasn't reached that civ yet — missing
   captures show a dashed "missing" placeholder. */
.civ-card .civ-shot-block{padding:10px 16px;border-top:1px solid #21262d;
  background:#0a0e14}
.civ-card .civ-shot-title{font-size:11px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.06em;color:#d29922;
  margin-bottom:6px;display:flex;align-items:center;gap:8px}
.civ-card .civ-shot-meta{font-weight:400;color:#6e7681;font-size:10px;
  text-transform:none;letter-spacing:0}
.civ-card .civ-shot-row{display:flex;gap:6px;flex-wrap:wrap;
  padding-bottom:2px}
.civ-card .civ-shot-cell{flex-shrink:0;text-align:center;width:110px}
.civ-card .civ-shot-cell img{height:62px;width:110px;object-fit:cover;
  border:1px solid #30363d;border-radius:3px;cursor:pointer;
  background:#0d1117;display:block;transition:border-color 0.12s ease}
.civ-card .civ-shot-cell img:hover{border-color:#58a6ff}
.civ-card .civ-shot-missing{height:62px;width:110px;background:#0d1117;
  border:1px dashed #30363d;border-radius:3px;display:flex;
  align-items:center;justify-content:center;color:#484f58;font-size:10px;
  font-style:italic}
.civ-card .civ-shot-label{font-size:9px;color:#8b949e;margin-top:2px;
  line-height:1.2;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.civ-card .civ-shot-label-missing{color:#484f58}
.civ-card .civ-shot-extras-title{font-size:10px;font-weight:600;
  color:#8b949e;text-transform:uppercase;letter-spacing:0.05em;
  margin:8px 0 4px;opacity:0.75}
.civ-card .civ-shot-row-extras{opacity:0.92}
.civ-card .civ-shot-row-label{font-size:9px;font-weight:700;color:#8b949e;
  text-transform:uppercase;letter-spacing:0.08em;margin:6px 0 2px;
  padding:2px 4px;background:#161b22;border-left:2px solid #30363d;display:inline-block}
.civ-card .civ-shot-row-label-ai{color:#58a6ff;border-left-color:#1f6feb}

/* Deck (per-civ home-city cards, grouped by age) — always-open since
   2026-05-27 (was a <details> collapsible; user feedback wanted decks
   exposed automatically on every civ card). */
.civ-card .deck{padding:10px 16px 10px;border-top:1px solid #21262d;background:#0a0e14}
.civ-card .deck .deck-title{font-size:12px;color:#8b949e;
                            padding:2px 0;text-transform:uppercase;
                            letter-spacing:0.5px;font-weight:600}
.civ-card .deck .deck-body{margin-top:8px}
/* 2026-05-27: Card thumbnails sized at 40px — bumped from the original
   28px (unreadable) and trimmed back from a 52px first pass that the
   user said felt too big. 40px is a comfortable middle ground; hover
   still zooms to 2× for full-detail preview. */
.civ-card .deck .age-row{display:flex;align-items:flex-start;gap:7px;
                         margin-bottom:5px;font-size:12px;line-height:1}
.civ-card .deck .age-label{flex-shrink:0;width:44px;color:#8b949e;
                           font-size:11px;font-weight:600;padding-top:10px;
                           text-align:right;text-transform:uppercase}
.civ-card .deck .age-cards{display:flex;gap:4px;flex-wrap:wrap;flex:1}
.civ-card .deck .age-cards img{height:40px;width:40px;object-fit:cover;
                               border:1px solid #30363d;border-radius:3px;
                               background:#21262d;cursor:help;
                               transition:transform 0.12s ease}
.civ-card .deck .age-cards img:hover{border-color:#58a6ff;
                                     transform:scale(2);
                                     position:relative;z-index:10;
                                     box-shadow:0 6px 18px rgba(0,0,0,0.7)}
.civ-card .deck .age-empty{color:#484f58;font-size:11px;font-style:italic;
                           padding-top:10px}

/* Unique units strip */
.unique-units-block{margin:0;padding:8px 12px 10px;
                    background:#0d1117;border-top:1px solid #21262d}
.unique-units-label{font-size:10px;font-weight:700;color:#8b949e;
                    text-transform:uppercase;letter-spacing:0.8px;
                    margin-bottom:6px}
.unique-units-row{display:flex;flex-wrap:wrap;gap:6px}
.unit-cell{display:flex;flex-direction:column;align-items:center;
           width:54px;text-align:center}
.unit-cell img{height:40px;width:40px;object-fit:cover;
               border:1px solid #30363d;border-radius:3px;
               background:#21262d;cursor:help;
               transition:transform 0.12s ease}
.unit-cell img:hover{border-color:#58a6ff;transform:scale(2);
                     position:relative;z-index:10;
                     box-shadow:0 6px 18px rgba(0,0,0,0.7)}
.unit-caption{font-size:9px;color:#8b949e;margin-top:3px;
              line-height:1.2;word-break:break-word;max-width:54px}
.unit-cell-missing .unit-placeholder{height:40px;width:40px;
                                     display:flex;align-items:center;
                                     justify-content:center;
                                     border:1px dashed #30363d;border-radius:3px;
                                     background:#0d1117;color:#484f58;
                                     font-size:18px}

/* Counters */
.counters{display:flex;gap:16px;flex-wrap:wrap}
.counter{background:#0d1117;border:1px solid #30363d;border-radius:6px;
         padding:16px 24px;flex:1;min-width:140px;text-align:center}
.counter .value{font-size:32px;font-weight:700;color:#f0f6fc;margin-bottom:4px}
.counter .value.green{color:#3fb950}
.counter .value.red{color:#f85149}
.counter .value.yellow{color:#d29922}
.counter .label{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:0.5px}

/* Strategy distribution */
.strategy-bar{display:flex;height:32px;border-radius:4px;overflow:hidden;
              border:1px solid #30363d}
.strategy-bar .seg{display:flex;align-items:center;justify-content:center;
                   color:#fff;font-size:11px;font-weight:600}

/* Tables */
table{width:100%;border-collapse:collapse;font-size:13px}
table th, table td{padding:8px 12px;border-bottom:1px solid #21262d;text-align:left}
table th{background:#21262d;color:#c9d1d9;font-weight:600;font-size:12px}
table td{color:#a3b3c2}
table tr:hover td{background:#0d1117}
table a{color:#58a6ff;text-decoration:none}

/* Modal for image preview — opens at NATIVE pixel size so the user
   can inspect the full-resolution source. Modal is scrollable when the
   image overflows the viewport (e.g. 1829×2074 leader portraits on a
   1080p screen). Clicking the dim background or pressing Esc closes. */
#imgModal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;
          background:rgba(0,0,0,0.92);z-index:1000;cursor:pointer;
          overflow:auto;padding:20px;text-align:center}
#imgModal img{display:inline-block;margin:0 auto;border:1px solid #30363d;
              border-radius:4px;box-shadow:0 8px 32px rgba(0,0,0,0.5);
              /* image_orientation:from-image lets browser honour EXIF
                 orientation for JPEGs that the synthesiser copied verbatim */
              image-orientation:from-image}
#imgModalCaption{position:fixed;top:10px;left:50%;transform:translateX(-50%);
                 color:#f0f6fc;font-size:15px;font-weight:600;text-align:center;
                 background:rgba(13,17,23,0.9);padding:8px 18px;border-radius:6px;
                 border:1px solid #30363d;pointer-events:none;z-index:1001;max-width:82%}
#imgModalCaption .img-cap-title{font-size:15px;font-weight:600}
#imgModalCaption .img-cap-date{font-size:11.5px;font-weight:500;color:#8b98a5;
                 margin-top:3px;letter-spacing:0.02em}
.img-nav{position:fixed;top:50%;transform:translateY(-50%);z-index:1001;
         background:rgba(22,27,34,0.85);color:#f0f6fc;border:1px solid #30363d;
         border-radius:50%;width:56px;height:56px;font-size:34px;line-height:1;
         cursor:pointer;align-items:center;justify-content:center;user-select:none;
         padding:0}
.img-nav:hover{background:#1f6f43;border-color:#3fb950}
#imgPrev{left:18px}
#imgNext{right:18px}
.complete-check{flex:none;margin-left:8px;cursor:pointer;display:flex;
                align-items:center}
.complete-check input{display:none}
.complete-check .cc-box{width:30px;height:30px;border:2px solid #484f58;
                border-radius:6px;display:flex;align-items:center;
                justify-content:center;color:transparent;font-size:19px;
                font-weight:900;line-height:1;transition:all .12s}
.complete-check:hover .cc-box{border-color:#58a6ff}
.complete-check input:checked + .cc-box{background:#1f6f43;border-color:#3fb950;
                color:#fff}
.civ-card.complete{border-color:#3fb950;box-shadow:0 0 0 2px rgba(63,185,80,0.45)}
.civ-card.complete .civ-card-header{background:#0e2a1d}

code{background:#21262d;color:#7fd1ff;padding:1px 6px;border-radius:3px;
     font-family:'SF Mono','Monaco',monospace;font-size:12px}
pre{background:#010409;color:#c9d1d9;padding:14px;border-radius:6px;
    border:1px solid #30363d;font-family:'SF Mono','Monaco',monospace;
    font-size:12px;line-height:1.5;white-space:pre-wrap;
    overflow-wrap:break-word;word-break:break-word;margin:8px 0}

.footnote{padding:12px 24px;font-size:11px;color:#6e7681}
footer{padding:32px 48px;font-size:12px;color:#6e7681;text-align:center;
       border-top:1px solid #21262d;margin-top:32px}
"""


def render_page(gate: dict, spec: dict, art: dict, behaviour_map: dict,
                git_meta: dict,
                avatars: dict[str, str] | None = None,
                flags: dict[str, str] | None = None) -> str:
    avatars = avatars or {}
    flags = flags or {}
    civs = spec.get("civs", {})
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    # Home-city deck data for the per-civ doctrine cards. Loaded once here
    # so the per-civ loop can resolve card icons + descriptions cheaply.
    decks, cards_db = _load_deck_data()
    # Stage every referenced card icon into the served tree so the deck
    # rows can resolve them at card_icons/<basename>.png (relative URL).
    # The source dir is outside artifacts/validation/ and therefore not
    # reachable via the http.server, so we must copy them in.
    _stage_card_icons(decks, cards_db)
    # Unit-row data + icon staging for the three per-civ unit strips:
    # Hero/Explorer (suppresses retreat), Unique Units (10% tier),
    # Retreat Units (25% tier).
    # Sources: data/anw_civ_blurbs.json, _ANW_HERO_EXPLORER constant,
    # and a_new_world.html data-search unit rosters.
    civ_blurbs = _load_civ_blurbs()
    anw_unit_rosters = _load_anw_unit_rosters()
    anw_standard_units = _load_anw_standard_units()
    explorer_map = _load_explorer_resolution()
    _stage_unit_icons(civ_blurbs, rosters=anw_unit_rosters,
                      standard_units=anw_standard_units)
    # Per-age strategy text, keyed by spec token. Replaces the old
    # ``first build / expects / distance / deadlines`` claim block in
    # the per-civ card with five short DLC-aware strategy paragraphs
    # (Discovery / Colonial / Fortress / Industrial / Imperial).
    per_age = collect_per_age_strategies()
    # Wall-knob calibration (15 knobs × 40 civs) for the inline walling
    # block under each civ card. Sourced from
    # ``tools/ai_design/wall_knob_calibration.py``.
    wall_calib = _load_wall_calibration()
    # Latest sim-farm verdicts (observed behaviour) — empty until the farm runs.
    farm_results = _load_farm_results()

    # Per-civ AI quote bundles — script-driven insults / compliments
    # (``game/ai/core/aiLeaderQuotes.xs``), engine chatset lines
    # (``game/ai/chatsetsmods.xml``), and the 4 shared tactical lines.
    # Loaded once and passed into the per-civ render path so the user
    # can audit every voice line a civ speaks from the release-readiness
    # site without diffing two source files.
    _quotes_xs_path = REPO_ROOT / "game" / "ai" / "core" / "aiLeaderQuotes.xs"
    _quotes_xml_path = REPO_ROOT / "game" / "ai" / "chatsetsmods.xml"
    try:
        quote_ic = _ecq_extract_insults_compliments(_quotes_xs_path)
        quote_shared = _ecq_extract_shared_tactical_lines(_quotes_xs_path)
        quote_chatsets = _ecq_extract_chatset_lines(_quotes_xml_path)
    except Exception as e:  # pragma: no cover — defensive
        print(f"[build_release_readiness_site] quote extraction failed: {e}",
              file=sys.stderr)
        quote_ic, quote_shared, quote_chatsets = {}, {}, {}

    # In-game screenshot batch folders (``batch_NN_ANW<civ>``) — pre-walked
    # once so the per-civ renderer can look up the folder in O(1).
    screenshot_index = _build_screenshot_index()

    # Revolution-path map (curated JSON at
    # ``tools/validation/revolution_paths.json``). Used by
    # ``_render_civ_revolution_block`` to surface which nations can
    # revolt into which on every civ card.
    revolution_paths = _load_revolution_paths()
    # Flags for the "Revolts into" header chips (roster civs + non-roster targets).
    rev_target_flags = _stage_revolution_target_flags(spec, flags, revolution_paths)

    counts = gate.get("counts", {})
    n_pass = counts.get("PASS", 0)
    n_fail = counts.get("FAIL", 0)
    n_skip = counts.get("SKIP", 0)
    n_total = gate.get("total", 0)
    overall = gate.get("overall", "UNKNOWN")
    overall_class = "pass" if overall == "PASS" else (
        "fail" if overall == "FAIL" else "skip")

    # Wall strategy distribution
    ws_dist: dict[int, int] = defaultdict(int)
    for token, civ in civs.items():
        ws = (civ.get("claims") or {}).get("wall_strategy")
        if ws is not None:
            ws_dist[ws] += 1

    # ============== HTML ==============
    parts: list[str] = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>A New World — Release Readiness Site</title>
<style>{CSS}</style>
</head>
<body>

<header>
<h1>A New World — Release Readiness Site</h1>
<div class="meta">
  <span class="badge badge-{overall_class}">{html.escape(overall)}</span>
  <strong>{n_pass}/{n_total}</strong> validators passing
  &nbsp;·&nbsp; <strong>{len(civs)}</strong> civs
  &nbsp;·&nbsp; git <code>{html.escape(git_meta.get('sha','?'))}</code>
  on branch <code>{html.escape(git_meta.get('branch','?'))}</code>
  &nbsp;·&nbsp; generated <strong>{now}</strong>
</div>
</header>

<nav class="internal-nav">
  <a href="#summary">Summary</a>
  <a href="#validators">Validators <span class="tag">{n_pass}/{n_total}</span></a>
  <a href="#civs">Civs <span class="tag">{len(civs)}</span></a>
  <a href="#known">Known scope</a>
</nav>

<nav class="related-reports-nav">
  <span class="nav-label">Related reports:</span>
  <a href="ai_behaviour_map.html">AI behaviour map</a>
  <a href="per_civ_wall_doctrine_report.html">Per-civ wall doctrine</a>
  <a href="visual_art/static_contact_sheet.html">Art contact sheet</a>
</nav>

<main>
""")

    # ============= SUMMARY =============
    parts.append('<section id="summary"><h2>Release readiness summary</h2><div class="content">')
    parts.append('<div class="counters">')
    parts.append(f'<div class="counter"><div class="value green">{n_pass}</div>'
                 f'<div class="label">Validators passing</div></div>')
    parts.append(f'<div class="counter"><div class="value {"red" if n_fail else "green"}">{n_fail}</div>'
                 f'<div class="label">Validators failing</div></div>')
    parts.append(f'<div class="counter"><div class="value {"yellow" if n_skip else "green"}">{n_skip}</div>'
                 f'<div class="label">Validators skipped</div></div>')
    parts.append(f'<div class="counter"><div class="value">{len(civs)}</div>'
                 f'<div class="label">Civs in spec</div></div>')
    parts.append(f'<div class="counter"><div class="value">{len(art)}</div>'
                 f'<div class="label">Civs with art capture</div></div>')
    if git_meta.get("dirty"):
        parts.append(f'<div class="counter"><div class="value yellow">{git_meta["dirty_count"]}</div>'
                     f'<div class="label">Uncommitted file changes</div></div>')
    parts.append('</div>')

    parts.append('<h3 style="margin-top:24px;margin-bottom:8px;color:#f0f6fc;font-size:16px">'
                 'Wall-strategy distribution</h3>')
    parts.append('<div class="strategy-bar">')
    total_ws = sum(ws_dist.values()) or 1
    for ws, n in sorted(ws_dist.items()):
        pct = n / total_ws * 100
        color = STRATEGY_COLOR.get(ws, "#444")
        name = STRATEGY_NAMES.get(ws, "?")
        parts.append(f'<div class="seg" style="background:{color};width:{pct:.1f}%"'
                     f' title="{html.escape(name)}: {n} civs">{name} {n}</div>')
    parts.append('</div>')
    parts.append('</div></section>')

    # ============= VALIDATORS =============
    parts.append('<section id="validators"><h2>Validators ('
                 f'{n_pass}/{n_total} passing)</h2><div class="content">')
    parts.append('<div class="validator-grid">')
    for r in gate.get("results", []):
        v = r.get("verdict", "UNKNOWN")
        klass = v.lower()
        dur = r.get("duration_s", 0.0)
        parts.append(
            f'<div class="validator-card {klass}">'
            f'<span class="name">{html.escape(r.get("name","?"))}</span>'
            f'<span class="verdict">{html.escape(v)}'
            f' <span class="duration">{dur:.1f}s</span></span>'
            f'</div>'
        )
    parts.append('</div>')
    parts.append(
        f'<div class="footnote">Run ID <code>{html.escape(gate.get("run_id","?"))}</code>'
        f' · raw JSON: <code>tools/validation/run_all_validators_report.json</code>'
        f' · per-validator stdout: <code>artifacts/validation_runs/</code></div>'
    )
    parts.append('</div></section>')

    # ============= CIVS =============
    parts.append(f'<section id="civs"><h2>Per-civ doctrine ({len(civs)} civs)</h2>'
                 '<div class="content">')
    parts.append('<div class="civ-grid">')
    for token in sorted(civs.keys()):
        civ = civs[token]
        claims = civ.get("claims") or {}
        ws = claims.get("wall_strategy")
        ws_name = STRATEGY_NAMES.get(ws, "?") if ws is not None else "—"
        ws_color = STRATEGY_COLOR.get(ws, "#444") if ws is not None else "#444"
        label = civ.get("doctrine_label") or ""
        summary = civ.get("doctrine_summary") or ""
        prose = civ.get("doctrine_prose") or ""

        # Art lookup
        # 2026-05-27: per user feedback the 6-thumb in-game screenshot strip
        # (age_up_*, ai_deck_view, ai_home_city_scene) was removed from every
        # civ card. The screenshots pulled from the in-game ANW<civ> capture
        # folder; for base-game civs like ANWFrench this surfaced Napoleon-
        # era art on the Bourbon-Restoration Louis-XVIII card (visual lie).
        # The thumbnails are still reachable via the "Art folder →" link in
        # the card footer and the deep-dive page; they just no longer live
        # inside the civ card itself.
        anw_token = _civ_token_to_anw(token)
        art_info = art.get(anw_token)
        thumbs_html = ""

        # Per-age strategy block — replaces the old claim lines per user
        # feedback (2026-05-27). For each of Discovery/Colonial/Fortress/
        # Industrial/Imperial we show the civ's authored historical
        # strategy with their unique units/buildings/DLC content. Falls
        # back to claim lines only if the HTML modal data is missing.
        # NATION_PLAYSTYLE in a_new_world.html is keyed by ``data_name``
        # (e.g. ``Russians Ivan Terrible``) which doesn't always equal the
        # spec dict key (``Russians Catherine`` is a legacy spec key) — so
        # we look up by data_name first, fall back to the raw spec token.
        ages_block = ""
        data_name = civ.get("data_name") or token
        ages_data = per_age.get(data_name) or per_age.get(token)
        if ages_data:
            age_rows = []
            for age_key in ("Discovery", "Colonial", "Fortress",
                            "Industrial", "Imperial"):
                txt = ages_data.get(age_key, "")
                if not txt:
                    continue
                age_rows.append(
                    f'<div class="age-row">'
                    f'<div class="age-key">{age_key}</div>'
                    f'<div class="age-text">{_safe_text(txt)}</div>'
                    f'</div>'
                )
            if age_rows:
                ages_block = (
                    '<div class="per-age-strategy">' + "".join(age_rows) +
                    '</div>'
                )
        # Walling-doctrine block (15 wall knobs + rationale). Rendered
        # directly under the per-age strategy block per user feedback
        # (2026-05-27: "put the walling strategy underneath the each
        # age strategy for the nations").
        wall_block = _render_wall_doctrine_block(token, wall_calib, ws)
        # Testable per-age doctrine (posture/composition/age-up + difficulty
        # scaling) from the v2 spec claims. Shows what the AI is asserted to
        # do per age and how it scales by difficulty.
        per_age_doctrine_block = _render_per_age_doctrine_block(claims)
        # Observed/tested behaviour from the sim farm (designed vs observed).
        tested_block = _render_tested_block(
            _spec_token_to_calib_key(token), farm_results)
        # Per-civ quote / chat block — every AI voice line this civ speaks
        # (engine chatset + leader script insults/compliments + the 4
        # shared tactical lines). Rendered under the wall block per user
        # request (2026-05-27: "put all the quotes under the cards for
        # each nation in the localhost site for me to look at").
        quotes_block = _render_civ_quotes_block(
            token, _spec_token_to_calib_key(token),
            quote_ic, quote_shared, quote_chatsets,
        )
        # Revolution-paths block — for parent civs ("which targets can
        # this civ revolt into") and for revolution civs ("which parent
        # is this derived from"). Surfaces the same info from both
        # directions so the user can read either down or up from any
        # civ card. Curated data in tools/validation/revolution_paths.json.
        civ_label_for_rev = civ.get("civ_label") or ""
        # "Revolts into" now lives in the card header (flag + name of each
        # revolution this nation can become), replacing the old rev section.
        revolt_into_header = _render_revolt_into_header(
            civ_label_for_rev, revolution_paths, rev_target_flags)
        # Deep-dive links removed per user feedback (2026-05-27): the
        # "Art folder →" and "AI behaviour deep-dive →" links exposed
        # raw scratch directories that confused the release-readiness
        # narrative. All visual-confirmation art is surfaced via the
        # "Art surfaces" section instead.
        slug = _civ_token_slug(token)

        # Home-city deck (per-age card grid with icon thumbnails + hover
        # tooltips). Returns "" if no deck is mapped for this civ.
        deck_html = _render_civ_deck_html(anw_token, decks, cards_db,
                                          spec_token=token)

        # Three-row unit strip — vertically ordered: Hero/Explorer (top),
        # Unique Units (middle, 10% retreat tier), Retreat Units (bottom,
        # 25% tier). All rows rendered for every civ; empty rows show an
        # explicit "(none / data unavailable)" notice rather than being
        # silently omitted. Icons staged into artifacts/validation/unit_icons/
        # by _stage_unit_icons(); units without a resolved icon get a dashed
        # placeholder chip so we never emit a broken src= path.
        unique_units_html   = _render_unique_units_row(anw_token, civ_blurbs)
        retreat_units_html  = _render_retreat_units_row(
                                  anw_token, civ_blurbs, anw_unit_rosters,
                                  standard_units=anw_standard_units)

        # Per-civ in-game screenshot strip — inlined under the deck. The
        # art-surfaces strip is rendered later (after avatar_rel is resolved)
        # so its leader-portrait cell can mirror the card-header circle.
        shots_block = _render_civ_screenshots_block(anw_token,
                                                    screenshot_index)

        prose_short = prose[:280] + ("…" if len(prose) > 280 else "")
        # Card title: ``<civ_label> — <leader_label>`` so revolution tokens
        # (e.g. ``Argentines San Martin Revolution``) become a clean nation
        # name and leader. Fall back to raw token if the spec is incomplete.
        civ_label = civ.get("civ_label") or token
        leader_label = civ.get("leader_label") or ""
        # Display-only override: spec civ_labels like "French Louis" read
        # awkwardly in the card title alongside the leader name. The data
        # plumbing (spec, validators, exhibition_runner) keeps the spec
        # value — only the user-visible string is renamed.
        civ_label_display = CIV_LABEL_DISPLAY_OVERRIDE.get(civ_label,
                                                          civ_label)
        # "A New World" is a nation-identity mod (NOT named Legendary
        # Leaders), so the card title is the NATION name only — the per-civ
        # leader name (e.g. "Elizabeth", "Frederick the Great") is dropped
        # from all user-visible strings. leader_label is still read above for
        # data plumbing but no longer shown.
        display_name = civ_label_display
        # Leader avatar — the actual cpai_avatar PNG the game ships, copied
        # into ``artifacts/validation/leader_avatars/`` so the locally-hosted
        # http.server (rooted at ``artifacts/validation/``) can serve it.
        # This is the canonical visual confirmation that portrait-rebuilds
        # (e.g. tools/rebuild_portraits.py for Hiawatha) actually landed.
        avatar_rel = avatars.get(token)
        if avatar_rel:
            avatar_img = (
                f'<img class="leader-avatar" '
                f'src="{html.escape(avatar_rel)}" '
                f'alt="{_safe_text(civ_label_display)} portrait" '
                f'title="{_safe_text(display_name)}" '
                f'data-civ="{html.escape(anw_token)}" data-title="Leader portrait" '
                f'onclick="showImg(this)">'
            )
        else:
            avatar_img = (
                '<div class="leader-avatar" '
                'style="display:flex;align-items:center;justify-content:center;'
                'color:#484f58;font-size:18px" title="no avatar resolved">·</div>'
            )
        # Nation flag for the card header (replaces the circular leader
        # portrait, per user request). Authoritative source: civmods.xml
        # <homecityflagtexture> -> resources/images/icons/flags/Flag_*.png.
        flag_rel = flags.get(anw_token)
        if flag_rel:
            flag_img = (
                f'<img class="civ-flag" src="{html.escape(flag_rel)}" '
                f'alt="{_safe_text(civ_label_display)} flag" '
                f'title="{_safe_text(display_name)}">'
            )
        else:
            flag_img = '<div class="civ-flag civ-flag-missing">&#9873;</div>'
        # Hero/Explorer row — the civ's actual in-game explorer UNIT
        # (proto + unit-type name + icon) from explorer_resolution.json.
        hero_explorer_html = _render_hero_explorer_row(anw_token, explorer_map)
        # Art-surfaces strip REMOVED (2026-06-05): every art surface
        # (lobby portrait, scoreboard row, diplomacy, esc summary, HC button,
        # endgame flag, …) is already shown by the in-game screenshot section
        # below, which the strip was merely cropping. No separate strip needed.
        parts.append(f'''
<div class="civ-card" id="card-{html.escape(anw_token)}" data-civ="{html.escape(anw_token)}">
  <div class="civ-card-header">
    {flag_img}
    <div class="title-block"><h3>{_safe_text(display_name)}</h3></div>
    {revolt_into_header}
    <span class="strategy" style="background:{ws_color}">{ws_name}</span>
    <label class="complete-check" title="Mark {_safe_text(display_name)} complete">
      <input type="checkbox" onchange="toggleComplete(this,'{html.escape(anw_token)}')">
      <span class="cc-box">&#10003;</span>
    </label>
  </div>
  <div class="body">
    <p class="doctrine-label">{_safe_text(label)}</p>
    <p class="doctrine-summary">{_safe_text(summary)}</p>
    <p style="font-size:12px;color:#8b949e;margin-bottom:10px;line-height:1.6">{_safe_text(prose_short)}</p>
    {ages_block}
    {per_age_doctrine_block}
    {tested_block}
    {wall_block}
    {quotes_block}
    </div>
  {deck_html}
  {hero_explorer_html}
  {unique_units_html}
  {retreat_units_html}
  {shots_block}
</div>''')
    parts.append('</div></div></section>')

    # 2026-05-27: standalone "Per-nation wall doctrine" section removed
    # per user feedback — the walling strategy is now rendered inline on
    # each per-civ card directly under the per-age strategy block, so a
    # separate global section just duplicated content. Companion release
    # pillars (doctrine-claim enrichment, hub-test roster, wall pillar
    # release status) are reachable via the validator-status section and
    # the file listing in artifacts/validation/.

    # 2026-05-27: standalone "Art surfaces" section removed per user
    # feedback — every civ now renders its own 10-surface art strip
    # inline under the home-city deck block on the civ card itself.
    # See ``_render_civ_art_surfaces_block``.

    # 2026-05-27: standalone "In-game screenshots", "Public-facing site"
    # and "How to re-verify" sections were all removed per user feedback.
    # Per-civ in-game screenshot strip is now rendered inline on each civ
    # card via ``_render_civ_screenshots_block``; the showcase-site link
    # and verification commands lived in the README / docs anyway.

    # ============= KNOWN SCOPE =============
    parts.append('<section id="known"><h2>Known scope &amp; intentional gaps</h2>'
                 '<div class="content">')
    parts.append("""
<table><thead><tr><th>Item</th><th>Status</th><th>Notes</th></tr></thead><tbody>
<tr><td>Live in-game playstyle audit</td>
    <td><span class="badge badge-info">Operator-driven</span></td>
    <td>The static gate verifies XS↔spec doctrine alignment exhaustively.
        Live exhibition with <code>tools/validation/exhibition_runner.py</code>
        and the <code>anwHubTest</code> random-map script
        (<code>tools/aoe3_automation/anw_hub_coverage_matrix.py</code>) covers
        real-game behaviour on demand.</td></tr>
<tr><td>Realism-mode toggle</td>
    <td><span class="badge badge-info">Post-v1.0</span></td>
    <td>Design captured in <code>docs/REALISM_MODE_DESIGN.md</code>; not on
        the v1.0 release path.</td></tr>
</tbody></table>
""")
    parts.append('</div></section>')

    # ============= FOOTER =============
    parts.append("""
</main>

<div id="imgModal" onclick="if(event.target.id==='imgModal')closeModal()">
  <div id="imgModalCaption"></div>
  <button id="imgPrev" class="img-nav" title="Previous (←)"
          onclick="event.stopPropagation();modalNav(-1)">&#8249;</button>
  <img id="modalImg" onclick="event.stopPropagation()">
  <button id="imgNext" class="img-nav" title="Next (→)"
          onclick="event.stopPropagation();modalNav(1)">&#8250;</button>
</div>
<script>
// Lightbox is scoped to ONE nation: the group is every image sharing the
// clicked image's data-civ, so prev/next can never cross into another
// nation's screenshots. Caption shows the surface title ("what it should
// show") plus position and native resolution.
var modalGroup = [], modalIdx = 0;
function showImg(el){
  var civ = el.getAttribute('data-civ');
  if (civ){
    modalGroup = Array.prototype.slice.call(
      document.querySelectorAll('img[data-civ="' + civ + '"]'));
  } else {
    modalGroup = [el];
  }
  modalIdx = modalGroup.indexOf(el);
  if (modalIdx < 0){ modalGroup = [el]; modalIdx = 0; }
  document.getElementById('imgModal').style.display = 'block';
  renderModal();
}
function renderModal(){
  var el = modalGroup[modalIdx];
  var img = document.getElementById('modalImg');
  var cap = document.getElementById('imgModalCaption');
  var src = el.src;
  // Prefer the higher-resolution crops/X.png over thumbs/X.webp; full
  // screenshots have no /thumbs/ segment so the replace is a no-op for them.
  var hiRes = src.replace('/thumbs/', '/crops/').replace(/\\.webp$/, '.png');
  var title = el.getAttribute('data-title') || el.title || el.alt || '';
  var date = el.getAttribute('data-date') || '';
  var pos = modalGroup.length > 1
    ? '  (' + (modalIdx + 1) + ' / ' + modalGroup.length + ')' : '';
  function setCap(suffix){
    cap.innerHTML = '';
    var t = document.createElement('div');
    t.className = 'img-cap-title';
    t.textContent = title + pos + suffix;
    cap.appendChild(t);
    if (date){
      var d = document.createElement('div');
      d.className = 'img-cap-date';
      d.textContent = 'Captured ' + date;
      cap.appendChild(d);
    }
  }
  setCap('  —  loading…');
  img.onerror = function(){ img.onerror = null; img.src = src; };
  img.onload = function(){
    setCap('  —  ' + img.naturalWidth + '×' + img.naturalHeight);
  };
  img.src = hiRes;
  document.getElementById('imgModal').scrollTop = 0;
  var disp = modalGroup.length > 1 ? 'flex' : 'none';
  document.getElementById('imgPrev').style.display = disp;
  document.getElementById('imgNext').style.display = disp;
}
function modalNav(d){
  if (modalGroup.length < 2) return;
  modalIdx = (modalIdx + d + modalGroup.length) % modalGroup.length;
  renderModal();
}
function closeModal(){
  document.getElementById('imgModal').style.display = 'none';
}
document.addEventListener('keydown', function(e){
  var modal = document.getElementById('imgModal');
  if (!modal || modal.style.display !== 'block') return;
  if (e.key === 'Escape') closeModal();
  else if (e.key === 'ArrowLeft'){ e.preventDefault(); modalNav(-1); }
  else if (e.key === 'ArrowRight'){ e.preventDefault(); modalNav(1); }
});

// Per-nation completion checkbox — turns the card green; persisted in
// localStorage (survives reloads and site regenerations).
function toggleComplete(cb, civ){
  var card = document.getElementById('card-' + civ);
  if (!card) return;
  if (cb.checked){
    card.classList.add('complete');
    try { localStorage.setItem('anwcomplete:' + civ, '1'); } catch(e){}
  } else {
    card.classList.remove('complete');
    try { localStorage.removeItem('anwcomplete:' + civ); } catch(e){}
  }
}
document.addEventListener('DOMContentLoaded', function(){
  var cards = document.querySelectorAll('.civ-card[data-civ]');
  for (var i = 0; i < cards.length; i++){
    var civ = cards[i].getAttribute('data-civ');
    if (!civ) continue;
    var done = false;
    try { done = localStorage.getItem('anwcomplete:' + civ) === '1'; } catch(e){}
    if (done){
      cards[i].classList.add('complete');
      var cb = cards[i].querySelector('.complete-check input');
      if (cb) cb.checked = true;
    }
  }
});
</script>

<footer>
A New World mod release readiness · generated by
<code>tools/validation/build_release_readiness_site.py</code> ·
this page aggregates the gate JSON, spec, AI behaviour map, and per-civ art
captures into one review surface.
</footer>

</body></html>
""")
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_HTML,
                    help="Output HTML path (default: artifacts/validation/release_readiness_site.html)")
    args = ap.parse_args()

    print("=" * 60)
    print("BUILDING RELEASE READINESS SITE")
    print("=" * 60)

    gate = collect_validator_results()
    spec = collect_spec_data()
    art = collect_art_surfaces()
    behaviour_map = collect_behaviour_map()
    git_meta = get_git_meta()
    # Stage leader avatars from resources/images/icons/singleplayer into the
    # served artifacts tree. Done here (not inside render_page) so the
    # filesystem mutation stays explicit and visible in the build log.
    avatars = _stage_leader_avatars(spec)
    # Stage nation flags (the card-header now shows the flag, not the portrait).
    flags = _stage_flags(_load_flag_map())

    print(f"  Gate: {gate.get('overall','?')}  "
          f"({gate.get('counts',{}).get('PASS',0)}/{gate.get('total',0)} passing)")
    print(f"  Civs in spec: {len(spec.get('civs',{}))}")
    print(f"  Civs with art capture: {len(art)}")
    print(f"  Civs with leader avatar: {len(avatars)}")
    print(f"  Civs with nation flag: {len(flags)}")
    print(f"  Git: {git_meta.get('branch')}@{git_meta.get('sha')}"
          f"{' (dirty)' if git_meta.get('dirty') else ''}")
    print()

    html_text = render_page(gate, spec, art, behaviour_map, git_meta,
                            avatars=avatars, flags=flags)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_text, encoding="utf-8")
    print(f"  Wrote: {args.out}  ({len(html_text):,} bytes)")

    # Machine-readable index
    index = {
        "generated_at": _dt.datetime.now().isoformat(),
        "gate": {"overall": gate.get("overall"),
                 "counts": gate.get("counts", {}),
                 "total": gate.get("total", 0)},
        "spec": {"civ_count": len(spec.get("civs", {}))},
        "art": {"civs_captured": len(art),
                "civs": sorted(art.keys())},
        "git": git_meta,
        "outputs": {"html": str(args.out.relative_to(REPO_ROOT))},
    }
    OUT_INDEX.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"  Wrote: {OUT_INDEX}  ({OUT_INDEX.stat().st_size:,} bytes)")
    print()
    print(f"Open in browser:  file://{args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
