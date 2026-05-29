"""Single source of truth: per-civ expected runtime behaviour.

We parse the same files the static validators read (`leaderCommon.xs`,
`civmods.xml`, `data/*homecity*.xml`) and emit a flat per-civ record
that downstream verifiers compare against the actual game state.

Each `CivExpectation` carries:
  * civ_id           — the ANW token (e.g., `ANWBritish`,
                       `ANWRevFrance` for revolutions).
  * label            — human-readable display label ("British",
                       "Napoleonic France").
  * leader_key       — the `gLLLeaderKey` string the leader portrait /
                       name override is wired to.
  * deck_name        — the deck label that should appear in the in-game
                       Deck Builder for this civ.
  * terrain_primary  — `cLLTerrain*` constant, e.g. "cLLTerrainCoast".
  * terrain_secondary
  * terrain_strength — float in [0.0, 1.0]
  * heading          — `cLLHeading*` constant
  * heading_strength
  * water_bias       — derived: +1 (toward water), -1 (toward inland),
                       0 (neutral). Used by the layout verifier.
  * heading_axis     — derived: "tangent" (AlongCoast/Upriver/Trade),
                       "outward" (Frontier/IslandHop), "inward"
                       (Defensive/OutwardRings), or "none".

The module re-uses the brace-walking parser from
`tools/validation/validate_terrain_heading.py` so we don't rewrite that
logic.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.validation.validate_terrain_heading import (  # noqa: E402
    BASE_CIVS,
    REVOLUTION_CIVS,
    _extract_apply_body,
    _split_branches,
)
from tools.migration.anw_mapping import (  # noqa: E402
    ANW_CIVS,
    ANW_HOMECITY_MAP,
)

LEADER_COMMON = REPO_ROOT / "game/ai/leaders/leaderCommon.xs"
CIVMODS = REPO_ROOT / "data/civmods.xml"
DATA_DIR = REPO_ROOT / "data"

# Terrain → semantic water bias. Coast/River/Wetland gravitate toward
# the navy vector; Highland/DesertOasis push inland. Plain/Forest/Any
# don't directly imply a water relationship.
TERRAIN_WATER_BIAS = {
    "cLLTerrainCoast": +1,
    "cLLTerrainRiver": +1,
    "cLLTerrainWetland": +1,
    "cLLTerrainHighland": -1,
    "cLLTerrainDesertOasis": -1,
    "cLLTerrainPlain": 0,
    "cLLTerrainForestEdge": 0,
    "cLLTerrainJungle": 0,
    "cLLTerrainAny": 0,
}

# Heading → expected expansion axis relative to base.
HEADING_AXIS = {
    "cLLHeadingAlongCoast": "tangent",
    "cLLHeadingUpriver": "tangent",
    "cLLHeadingFollowTradeRoute": "tangent",
    "cLLHeadingFrontierPush": "outward",
    "cLLHeadingIslandHop": "outward",
    "cLLHeadingDefensive": "inward",
    "cLLHeadingOutwardRings": "inward",
    "cLLHeadingAny": "none",
}

# ANW token → display label. Originally a hand-curated dict keyed by the
# legacy cCiv*/ANW* tokens; Phase 6 migrated keys to the post-rename
# ANW tokens. Tests and replay-probe assertions reference these literal
# strings ("British (Elizabeth I)", "Aztecs", etc.), so the strings cannot
# be derived from ANW_CIVS metadata without breaking the test contract.
# 2026-05-10: re-pinned to the legacy values, re-keyed to ANW tokens, after
# the dict-shape ANW_CIVS refactor lost the original CIV_LABELS dict.
CIV_LABELS: dict[str, str] = {
    # Base civs (BASE_CIVS in validate_terrain_heading.py)
    "British": "British (Elizabeth I)",
    "Chinese": "Chinese",
    "DEAmericans": "Americans",
    "DEEthiopians": "Ethiopians",
    "DEHausa": "Hausa",
    "DEInca": "Inca",
    "DEItalians": "Italians",
    "DEMaltese": "Maltese",
    "DEMexicans": "Mexicans",
    "DESwedish": "Swedish",
    "Dutch": "Dutch",
    "French": "French (Louis XVIII)",
    "Germans": "Germans",
    "Indians": "Indians",
    "Japanese": "Japanese",
    "Ottomans": "Ottomans",
    "Portuguese": "Portuguese",
    "Russians": "Russians (Ivan IV)",
    "Spanish": "Spanish",
    "XPAztec": "Aztecs",
    "XPIroquois": "Iroquois (Haudenosaunee)",
    "XPSioux": "Lakota (Chief Gall)",
    # Revolution civs (ANW-prefixed in the new dict; mapped from the legacy
    # ANW* labels). DEAmericans above is the base USA; the Americans
    # Revolution doesn't have an ANW-prefix counterpart in the current dict.
    "ANWAmericans": "Americans (Revolution)",
    "ANWArgentines": "Argentina",
    "ANWBarbary": "Barbary States",
    "ANWBrazil": "Brazil",
    "ANWCanadians": "Canada",
    "ANWChileans": "Chile",
    "ANWColumbians": "Colombia",
    "ANWEgyptians": "Egypt",
    "ANWFinnish": "Finland",
    "ANWHaitians": "Haiti",
    "ANWHungarians": "Hungary",
    "ANWIndonesians": "Indonesia",
    "ANWMayans": "Maya",
    "ANWMexicans": "Mexico (Revolution)",
    "ANWNapoleonicFrance": "Napoleonic France",
    "ANWPeruvians": "Peru",
    "ANWRevFrance": "Revolutionary France",
    "ANWRomanians": "Romania",
    "ANWSouthAfricans": "South Africa",
    "ANWTexians": "Texas",
}


@dataclass(frozen=True)
class CivExpectation:
    civ_id: str
    label: str
    leader_key: str
    deck_name: str
    terrain_primary: str
    terrain_secondary: str
    terrain_strength: float
    heading: str
    heading_strength: float

    @property
    def water_bias(self) -> int:
        # Primary outweighs secondary 2:1.
        primary = TERRAIN_WATER_BIAS.get(self.terrain_primary, 0)
        secondary = TERRAIN_WATER_BIAS.get(self.terrain_secondary, 0)
        score = 2 * primary + secondary
        if score > 0:
            return +1
        if score < 0:
            return -1
        return 0

    @property
    def heading_axis(self) -> str:
        return HEADING_AXIS.get(self.heading, "none")

    @property
    def is_revolution(self) -> bool:
        # Look up the ANW civ to determine if it's a revolution.
        for civ in ANW_CIVS:
            if civ.anw_token == self.civ_id:
                return civ.is_revolution
        return False


# --- parsing -----------------------------------------------------------------

_TERRAIN_CALL_RE = re.compile(
    r"llSetPreferredTerrain\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)"
)
_HEADING_CALL_RE = re.compile(
    r"llSetExpansionHeading\s*\(\s*([^,]+?)\s*,\s*([^\)]+?)\s*\)"
)
_LEADER_KEY_RE = re.compile(
    r"""(?:cMyCiv\s*==\s*(?P<civ>cCiv[A-Za-z0-9_]+)
       | rvltName\s*==\s*"(?P<rvlt>[^"]+)")
       \s*\)\s*\{\s*gLLLeaderKey\s*=\s*"(?P<key>[^"]+)"\s*;""",
    re.VERBOSE,
)


def _parse_apply_branches(leader_text: str) -> dict[str, dict]:
    body = _extract_apply_body(leader_text)
    if body is None:
        raise RuntimeError("llApplyBuildStyleForActiveCiv() body not found in leaderCommon.xs")

    out: dict[str, dict] = {}
    for label, branch in _split_branches(body):
        terrain = _TERRAIN_CALL_RE.search(branch)
        heading = _HEADING_CALL_RE.search(branch)
        if not terrain or not heading:
            continue
        out[label] = {
            "terrain_primary": terrain.group(1).strip(),
            "terrain_secondary": terrain.group(2).strip(),
            "terrain_strength": float(terrain.group(3).strip()),
            "heading": heading.group(1).strip(),
            "heading_strength": float(heading.group(2).strip()),
        }
    return out


def _parse_leader_keys(leader_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _LEADER_KEY_RE.finditer(leader_text):
        label = m.group("civ") or m.group("rvlt")
        out[label] = m.group("key")
    return out


def _parse_homecity_for_civ(civmods_text: str) -> dict[str, str]:
    """Map civ Name → HomeCityFilename. Naive line-walking, sufficient
    for the very regular structure of civmods.xml.
    """
    out: dict[str, str] = {}
    current_name: str | None = None
    for line in civmods_text.splitlines():
        m_name = re.search(r"<Name>\s*(\S+?)\s*</Name>", line)
        if m_name:
            current_name = m_name.group(1)
            continue
        m_hc = re.search(r"<HomeCityFilename>\s*(\S+?)\s*</HomeCityFilename>", line)
        if m_hc and current_name:
            out[current_name] = m_hc.group(1)
            current_name = None
    return out


_DECK_NAME_RE = re.compile(
    r"<decks>(?P<body>.*?)</decks>", re.DOTALL
)
_INNER_NAME_RE = re.compile(r"<deck>\s*<name>(?P<name>[^<]+)</name>", re.DOTALL)


def _parse_deck_name(homecity_path: Path) -> str:
    """Return the first <deck>'s <name>. The mod renames every slot to
    the same string per civ, so the first slot is canonical.
    """
    if not homecity_path.exists():
        return "<missing homecity>"
    text = homecity_path.read_text(encoding="utf-8")
    decks = _DECK_NAME_RE.search(text)
    if not decks:
        return "<no <decks> block>"
    inner = _INNER_NAME_RE.search(decks.group("body"))
    if not inner:
        return "<no inner deck name>"
    return inner.group("name").strip()


# Post-Phase 6: ANW_HOMECITY_MAP (from anw_mapping) is the single source
# of truth for all 48 civs' homecity filenames, keyed by anw_stem.


def _resolve_homecity_filename(anw_token: str) -> Path | None:
    """Resolve homecity path from ANW token using ANW_HOMECITY_MAP.

    ANW_HOMECITY_MAP is keyed by anw_stem (e.g., 'anwbritish'),
    so we need to look up the ANW civ and extract its stem.

    Revolution civs that don't have their own homecity XML inherit the
    parent civ's homecity at runtime (e.g. ANWAmericans → anwhomecityusa).
    The fallback table below captures those mappings so deck-name resolution
    still produces a real string for these civs.
    """
    # Revolution-from-base-civ inheritance map. Keyed by ANW token; value is
    # the parent civ's homecity stem.
    _REVOLUTION_HC_FALLBACK = {
        "ANWAmericans": "usa",
    }
    try:
        # Find the ANW civ by token to get its stem
        for civ in ANW_CIVS:
            if civ.anw_token == anw_token:
                fname = ANW_HOMECITY_MAP.get(civ.anw_stem)
                if fname:
                    p = DATA_DIR / fname
                    if p.exists():
                        return p
                # Fall through to parent-civ fallback for revolution civs
                fallback_stem = _REVOLUTION_HC_FALLBACK.get(anw_token)
                if fallback_stem:
                    p = DATA_DIR / f"anwhomecity{fallback_stem}.xml"
                    if p.exists():
                        return p
                return None
    except (KeyError, AttributeError):
        return None
    return None


def _build_civ_const_to_anw_map() -> dict[str, str]:
    """Build mapping from BASE_CIVS constants to ANW tokens.

    BASE_CIVS has cCiv* constants that are keys in leaderCommon.xs;
    ANW_CIVS has old_civ_token fields that sometimes differ (e.g., lowercase).
    This helper finds the matching ANW civ for each constant.
    """
    const_to_anw = {}
    for const in BASE_CIVS:
        const_slug = const.replace("cCiv", "").lower()
        for civ in ANW_CIVS:
            if civ.is_revolution:
                continue
            # Direct old_civ_token match (case-insensitive for non-XP civs)
            if civ.old_civ_token.lower() == const_slug:
                const_to_anw[const] = civ.anw_token
                break
            # Handle case-sensitive XP prefixes (XPAztec, XPIroquois, XPSioux)
            if civ.old_civ_token == const.replace("cCiv", ""):
                const_to_anw[const] = civ.anw_token
                break
    return const_to_anw


def load_expectations(repo_root: Path = REPO_ROOT) -> list[CivExpectation]:
    leader_text = (repo_root / "game/ai/leaders/leaderCommon.xs").read_text(encoding="utf-8")

    apply_branches = _parse_apply_branches(leader_text)
    leader_keys = _parse_leader_keys(leader_text)

    # Map BASE_CIVS cCiv* constants to ANW tokens
    const_to_anw_token = _build_civ_const_to_anw_map()
    # Map ANW* strings directly to ANW tokens
    rvlt_to_anw_token = {civ.old_civ_token: civ.anw_token for civ in ANW_CIVS if civ.is_revolution}

    out: list[CivExpectation] = []
    # Phase 6: Iterate using old token lists (still in leaderCommon.xs),
    # but store results using ANW tokens.
    for old_civ_id in (*BASE_CIVS, *REVOLUTION_CIVS):
        if old_civ_id not in apply_branches:
            continue

        # Map old civ ID to ANW token
        anw_token = const_to_anw_token.get(old_civ_id) or rvlt_to_anw_token.get(old_civ_id)
        if not anw_token:
            continue

        b = apply_branches[old_civ_id]
        hc_path = _resolve_homecity_filename(anw_token)
        deck_name = _parse_deck_name(hc_path) if hc_path else "<no homecity mapping>"
        out.append(
            CivExpectation(
                civ_id=anw_token,
                label=CIV_LABELS.get(anw_token, anw_token),
                leader_key=leader_keys.get(old_civ_id, "<unmapped>"),
                deck_name=deck_name,
                terrain_primary=b["terrain_primary"],
                terrain_secondary=b["terrain_secondary"],
                terrain_strength=b["terrain_strength"],
                heading=b["heading"],
                heading_strength=b["heading_strength"],
            )
        )
    return out


__all__ = [
    "CivExpectation",
    "TERRAIN_WATER_BIAS",
    "HEADING_AXIS",
    "CIV_LABELS",
    "load_expectations",
]
