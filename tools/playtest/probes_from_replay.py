"""Probe extractor — personality-file channel (non-dev-mode path).

Background
----------
AoE3 DE FINAL_RELEASE builds strip the ``aiEcho()`` dev-mode log channel, so
``Age3Log.txt`` never receives ``[LLP v=2 ...]`` lines.  This tool uses an
alternative channel that works without developer mode:

  ``aiPersonalitySetPlayerUserVar()`` writes float key/value pairs into the
  ``<uservars>`` section of ``Game/AI/<leader>.personality`` XML files.  The
  engine writes these files to disk at game-end (resign or victory) regardless
  of developer mode.

The XS side (``aiCore.xs::gameOverHandler()``) writes a set of ``ll_*`` keys
at the end of every match when ``cLLReplayProbes == true``.  This script reads
those keys back and reconstructs the probe summary.

Usage
-----
::

    # Dump all ll_* vars from all personality files after a match:
    python3 -m tools.playtest.probes_from_replay

    # Point at a specific personality file:
    python3 -m tools.playtest.probes_from_replay --file Wellington.personality

    # JSON output (for piping into jq or replay_probes.py):
    python3 -m tools.playtest.probes_from_replay --json

    # Validate against expectations (same checks as replay_probes.py):
    python3 -m tools.playtest.probes_from_replay --validate

    # Generate synthetic [LLP v=2 ...] lines to stdout (for match.log compat):
    python3 -m tools.playtest.probes_from_replay --emit-llp

Exit codes: 0 = OK, 1 = validation issues, 2 = no probe data found.

Notes on the encoding
---------------------
All values stored as floats.  Integer fields (pid, style, walls, etc.) are
read with ``round()``.  Float fields (bias strengths) are read as-is.

``ll_civ`` is the engine's internal civ ID integer (e.g. cCivBritish = 4).
``ll_pid`` is the player slot (2..8 for AI in skirmish).
``gLLLeaderKey`` is NOT stored here because personality uservars are floats
and XS has no float→string encoding.  The leader key is recovered by
cross-referencing ``ll_pid`` with the personality *file name* (which IS the
leader key, e.g. ``Wellington.personality`` → leader ``wellington``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Personality files live here (within the Steam/Proton prefix).
PERSONALITY_DIR: Path = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE"
    / "76561198170207043/Game/AI"
)

# Prefix used by the XS side to mark our injected probe vars.
LL_PREFIX = "ll_"

# Known civ ID → name mapping (engine integers, from aiHeader.xs constants).
# Only need the ones we actually use; update as new civs are added.
CIV_ID_TO_NAME: dict[int, str] = {
    1:  "Spanish",
    2:  "British",
    3:  "French",
    4:  "Portuguese",
    5:  "Dutch",
    6:  "Russians",
    7:  "Germans",
    8:  "Ottomans",
    9:  "Iroquois",
    10: "Sioux",
    11: "Aztec",
    12: "Japanese",
    13: "Chinese",
    14: "Indians",
    15: "Lakota",
    16: "Americans",
    17: "Mexicans",
    18: "Swedes",
    19: "Africans",
    20: "Ethiopians",
    21: "Hausa",
    22: "Incas",
    23: "Italians",
    24: "Maltese",
    # Revolution civs start ~100+ – fall back to numeric if unknown.
}

# Terrain ID → symbolic name (from aiHeader.xs cLLTerrain* constants).
TERRAIN_NAMES: dict[int, str] = {
    0: "Any",
    1: "Highland",
    2: "Plain",
    3: "River",
    4: "Coast",
    5: "Wetland",
    6: "DesertOasis",
    7: "Arctic",
    8: "Jungle",
}

# Heading ID → symbolic name (from aiHeader.xs cLLHeading* constants).
HEADING_NAMES: dict[int, str] = {
    0: "Any",
    1: "North",
    2: "South",
    3: "East",
    4: "West",
    5: "NE",
    6: "NW",
    7: "SE",
    8: "SW",
    9: "Frontier",
    10: "Outward",
    11: "Inward",
}

# Wall strategy ID → symbolic name (from aiHeader.xs cLLWallStrategy* constants).
WALL_STRATEGY_NAMES: dict[int, str] = {
    0: "FortressRing",
    1: "ChokepointSegments",
    2: "CoastalBatteries",
    3: "FrontierPalisades",
    4: "UrbanBarricade",
    5: "MobileNoWalls",
}

# Build style ID → symbolic name (from aiHeader.xs cLLBuildStyle* constants).
BUILD_STYLE_NAMES: dict[int, str] = {
    0:  "Unknown",
    1:  "CompactFortifiedCore",
    2:  "DistributedEconomicNetwork",
    3:  "ForwardOperationalLine",
    4:  "MobileFrontierScatter",
    5:  "ShrineTradeNodeSpread",
    6:  "CivicMilitiaCenter",
    7:  "SteppeCavalryWedge",
    8:  "NavalMercantileCompound",
    9:  "SiegeTrainConcentration",
    10: "JungleGuerrillaNetwork",
    11: "HighlandCitadel",
    12: "CossackVoisko",
    13: "RepublicanLevee",
    14: "AndeanTerraceFortress",
}

# First-military-building names: v2 pack collapses 5 values to 4 (barracks
# and stable share enum 2).  We expose the old-style enum (0/1/2/4) so
# downstream code (validate_personality_vs_spec.py) needs no changes.
# v2 enum 0→old 0(none), 1→old 1(dock), 2→old 2(barracks_or_stable),
# 3→old 4(trading_post).
FIRST_MIL_BUILDING_NAMES: dict[int, str] = {
    0: "none",
    1: "dock",
    2: "barracks_or_stable",
    4: "trading_post",
}

# v2 raw 2-bit enum → old-style enum used by downstream validators.
_FIRST_MIL_V2_TO_OLD: dict[int, int] = {0: 0, 1: 1, 2: 2, 3: 4}

# Spec claim string → set of old-enum values that satisfy the claim.
FIRST_MIL_CLAIM_TO_ENUM: dict[str, set[int]] = {
    "dock":                   {1},
    "barracks_or_stable":     {2},
    "trading_post_or_market": {4},
}

# Sentinel inside the 14-bit milestone-secs field meaning "never built"
# (legacy v1 pack only).
NEVER_BUILT_SECS = 16383

# Bit-0 of ll_playstyle_v2a — set ⇒ v2 playstyle pack present in custom key.
# (Previously this was bit 23 of myEnemyCount, but empirical testing proved
# that the engine truncates myEnemyCount to bits 0..20 at flush — the sentinel
# never landed.  Custom ll_* keys survive, but are stored as float32; a single
# pack ~2^28 silently lost low bits.  v2 is now split across TWO keys:
# ll_playstyle_v2a (bits 0..22, float32-exact, max 8388607) and
# ll_playstyle_v2b (wall_q5 in bits 4..0).  Bit 0 of v2a is the sentinel.)
PLAYSTYLE_V2_SENTINEL_BIT = 1  # bit 0 of ll_playstyle_v2a

# Legacy: bit-23 of iWonLastGame was the v1 playstyle sentinel.
PLAYSTYLE_SENTINEL_BIT = 1 << 23  # kept for import compat; same value


@dataclass
class PersonalityProbe:
    """Decoded probe snapshot from a single .personality file."""
    personality_file: str     # stem of the file, e.g. "Wellington"
    leader_key: str           # lower-cased stem, e.g. "wellington"
    # ll_* fields decoded from uservars:
    pid: int                  # ll_pid  — player slot (2..8)
    style: int                # ll_style
    walls: int                # ll_walls
    wall_strategy: int        # ll_wall_strat
    terrain_primary: int      # ll_terr_p
    terrain_secondary: int    # ll_terr_s
    terrain_bias: float       # ll_terr_bias
    heading: int              # ll_heading
    heading_bias: float       # ll_head_bias
    civ_id: int               # ll_civ  (engine integer)
    age: int                  # ll_age  (0=Discovery..4=Imperial)
    score: int                # ll_score
    match_ms: int             # ll_match_ms
    # ── Playstyle-extension pack v2 (2026-05-13, split into two float32-safe keys) ─
    # Populated when ll_playstyle_v2a key is present AND its bit 0 is 1 (v2), OR
    # when iWonLastGame carries the legacy v1 sentinel (bit 23).  If
    # has_playstyle is False every field below is its zero-value (do not use
    # for spec validation — fall back to wall_strategy only).
    has_playstyle: bool = False
    # Milestone fire times in ms. None ⇒ that building type never built.
    first_dock_ms: Optional[int] = None
    first_barracks_ms: Optional[int] = None
    first_wall_ms: Optional[int] = None
    first_stable_ms: Optional[int] = None
    first_trading_post_ms: Optional[int] = None
    # First military building enum (see FIRST_MIL_BUILDING_NAMES). 0 = none.
    first_military_building: int = 0
    # Forward-base milestone fired during the match.
    expects_forward_observed: bool = False
    # Quantised military distance multiplier (5 bits = 0.0..1.94 in 0.0625
    # steps). Stored as the recovered float, NOT the raw q5 int.
    military_distance: float = 0.0

    @property
    def civ_name(self) -> str:
        return CIV_ID_TO_NAME.get(self.civ_id, f"civ_{self.civ_id}")

    @property
    def terrain_primary_name(self) -> str:
        return TERRAIN_NAMES.get(self.terrain_primary, f"terrain_{self.terrain_primary}")

    @property
    def terrain_secondary_name(self) -> str:
        return TERRAIN_NAMES.get(self.terrain_secondary, f"terrain_{self.terrain_secondary}")

    @property
    def heading_name(self) -> str:
        return HEADING_NAMES.get(self.heading, f"heading_{self.heading}")

    @property
    def wall_strategy_name(self) -> str:
        return WALL_STRATEGY_NAMES.get(self.wall_strategy, f"wall_{self.wall_strategy}")

    @property
    def build_style_name(self) -> str:
        return BUILD_STYLE_NAMES.get(self.style, f"style_{self.style}")

    @property
    def first_military_building_name(self) -> str:
        return FIRST_MIL_BUILDING_NAMES.get(
            self.first_military_building,
            f"mil_{self.first_military_building}",
        )

    def to_llp_line(self) -> str:
        """Emit a synthetic [LLP v=2 ...] line compatible with replay_probes.py."""
        return (
            f"[LLP v=2 t={self.match_ms} p={self.pid}"
            f" civ={self.civ_name} ldr={self.leader_key}"
            f" tag=meta.buildstyle]"
            f" style={self.style}"
            f" walls={self.walls}"
            f" terrain_primary={self.terrain_primary_name}"
            f" terrain_secondary={self.terrain_secondary_name}"
            f" terrain_bias={self.terrain_bias:.4f}"
            f" heading={self.heading_name}"
            f" heading_bias={self.heading_bias:.4f}"
        )

    def to_llp_leader_line(self) -> str:
        """Emit a synthetic meta.leader_assigned [LLP v=2 ...] line."""
        return (
            f"[LLP v=2 t={self.match_ms} p={self.pid}"
            f" civ={self.civ_name} ldr={self.leader_key}"
            f" tag=meta.leader_assigned]"
            f" leader={self.leader_key}"
        )


def _parse_uservars(xml_text: str) -> list[dict[str, float]]:
    """Parse all <uservars> blocks in the personality XML and return one
    dict per block with float values.

    Keys are stored lower-cased so callers don't have to second-guess engine
    serialiser capitalisation (the AoE3-DE serialiser sometimes preserves
    camelCase as written via aiPersonalitySetPlayerUserVar, sometimes folds
    to lowercase — depends on whether the field came from the hardcoded
    whitelist constructor or our explicit XS write).
    """
    blocks = re.findall(r"<uservars>(.*?)</uservars>", xml_text, re.DOTALL)
    result: list[dict[str, float]] = []
    for block in blocks:
        d: dict[str, float] = {}
        for m in re.finditer(r"<([a-zA-Z_][a-zA-Z0-9_]*)>([-+.\d]+)<", block):
            try:
                d[m.group(1).lower()] = float(m.group(2))
            except ValueError:
                pass
        if d:
            result.append(d)
    return result


# ── Packed-slot decoder ───────────────────────────────────────────────────────
# 2026-04-29: AoE3-DE silently drops <uservars> entries whose key isn't on a
# hardcoded engine whitelist (iWonLastGame, lastGameDifficulty, myAllyCount,
# myEnemyCount, wasMyAllyLastGame, lastMapID, etc.). Custom ll_* keys never
# survive serialisation per original understanding.
#
# 2026-05-13 UPDATE: Empirical testing showed that (a) the engine also
# truncates the upper bits of whitelisted slots (myEnemyCount to bits 0..20,
# wasMyAllyLastGame to bits 0..15, etc.) but (b) custom ll_* keys written via
# aiPersonalitySetPlayerUserVar ARE preserved — however the engine stores them
# as float32, so integers >2^24 lose low bits.  The original single
# ll_playstyle_v2 (~2^28) silently dropped bit 0 (sentinel).  Playstyle v2
# data is now split into ll_playstyle_v2a (bits 0..22, float32-exact, max
# 8388607) and ll_playstyle_v2b (wall_q5 in bits 4..0).
# The v1 base data (ally/enemy/score/secs/bias) is still in whitelisted slots
# using only the bits the engine preserves.
SENTINEL_BIT = 1 << 23  # bit 23 of myAllyCount — set ⇒ probe wrote


def _is_probe_block(b: dict[str, float]) -> bool:
    """A block is a probe-written record iff myAllyCount carries the sentinel."""
    val = b.get("myallycount")
    if val is None:
        return False
    return int(round(val)) & SENTINEL_BIT != 0


def _find_probe_block(blocks: list[dict[str, float]]) -> Optional[dict[str, float]]:
    """Return the first uservars block whose myAllyCount carries the sentinel.

    The engine writes myAllyCount/myEnemyCount in setupAIPlayerHistory() with
    raw counts (≤8 in 8-player matches), so the sentinel bit (8388608) cannot
    appear naturally — its presence proves our packed write happened.
    """
    for b in blocks:
        if _is_probe_block(b):
            return b
    return None


def _unpack_probe(block: dict[str, float]) -> dict:
    """Reverse the bit-pack from llWritePersonalityProbe.

    Supports v2 (ll_playstyle_v2a + ll_playstyle_v2b custom keys, bit 0 of
    v2a = sentinel) and v1 legacy (iWonLastGame bit 23 sentinel).  The broken
    "bit 23 of myEnemyCount" path has been removed — empirical testing proved
    the engine truncates myEnemyCount to bits 0..20 at flush so that sentinel
    never lands.  The original single ll_playstyle_v2 was dropped because the
    engine stores uservars as float32 and ~2^28 values lose their low bits.
    Returns a dict with integer and float fields that feed the PersonalityProbe
    constructor.
    """
    ally   = int(round(block.get("myallycount",        0))) & 0x00FFFFFF
    enemy  = int(round(block.get("myenemycount",       0))) & 0x001FFFFF  # only bits 0..20 survive
    score_raw = int(round(block.get("lastmapid",          0))) & 0x0001FFFF  # only bits 0..16 survive
    secs_raw  = int(round(block.get("lastgamedifficulty", 0))) & 0x00003FFF  # only bits 0..13 survive
    bias   = int(round(block.get("wasmyallylastgame",  0))) & 0x0000FFFF  # only bits 0..15 survive

    # myAllyCount layout:
    #   sentinel(1)<<23 | pid(5)<<18 | style(5)<<13 | walls(4)<<9
    #   | wstrat(3)<<6 | terr_p(6)
    pid     = (ally >> 18) & 0x1F
    style   = (ally >> 13) & 0x1F
    walls   = (ally >>  9) & 0x0F
    wstrat  = (ally >>  6) & 0x07
    terrp   =  ally        & 0x3F
    if terrp > 31:
        terrp &= 0x1F  # safety — only 5 valid bits

    # myEnemyCount low bits: terr_s(5)<<16 | heading(5)<<11 | age(3)<<8 | civ(8)
    terrs   = (enemy >> 16) & 0x1F
    heading = (enemy >> 11) & 0x1F
    age     = (enemy >>  8) & 0x07
    civ_id  =  enemy        & 0xFF

    # wasMyAllyLastGame low bits: terr_bias_q8(8)<<8 | head_bias_q8(8)
    tbias_q8 = (bias >> 8) & 0xFF
    hbias_q8 =  bias       & 0xFF

    # ── Detect pack version ───────────────────────────────────────────────
    # v2: look for ll_playstyle_v2a custom key; bit 0 = sentinel.
    # ll_playstyle_v2b carries wall_q5 in bits 4..0 (separate key to keep
    # both values within float32-exact range, i.e. ≤2^23-1 = 8388607).
    pack_a = block.get("ll_playstyle_v2a")
    pack_b = block.get("ll_playstyle_v2b")
    v2_raw = int(round(pack_a)) if pack_a is not None else 0
    has_playstyle_v2 = pack_a is not None and bool(v2_raw & PLAYSTYLE_V2_SENTINEL_BIT)

    # Legacy v1: iWonLastGame bit 23 sentinel, only if v2 absent.
    won_raw = int(round(block.get("iwonlastgame", 0))) & 0x00FFFFFF
    has_playstyle_v1 = (not has_playstyle_v2) and bool(won_raw & PLAYSTYLE_SENTINEL_BIT)

    has_playstyle = has_playstyle_v2 or has_playstyle_v1

    first_dock_ms: Optional[int] = None
    first_barracks_ms: Optional[int] = None
    first_wall_ms: Optional[int] = None
    first_stable_ms: Optional[int] = None
    first_trading_post_ms: Optional[int] = None
    first_mil_type_old = 0  # old-style enum (0/1/2/4)
    expects_forward = False
    mdist_float = 0.0

    if has_playstyle_v2:
        # ── v2 ll_playstyle_v2a / ll_playstyle_v2b decode ─────────────────
        # ll_playstyle_v2a layout (bits 0..22; bit 23 reserved=0):
        #   bit  0     = sentinel (already checked)
        #   bits 2..1  = first_mil_type_v2
        #   bit  3     = expects_forward
        #   bits 8..4  = mdist_q5
        #   bit  9     = first_dock_built
        #   bit  10    = first_stable_built
        #   bits 17..11 = dock_q7   (127=never)
        #   bits 22..18 = barracks_q5 (31=never)
        # ll_playstyle_v2b layout (bits 4..0):
        #   bits 4..0  = wall_q5   (31=never)
        mil_type_v2  = (v2_raw >>  1) & 0x03
        fwd_bit      = (v2_raw >>  3) & 0x01
        mdist_q5     = (v2_raw >>  4) & 0x1F
        dock_built   = bool((v2_raw >>  9) & 0x01)
        stable_built = bool((v2_raw >> 10) & 0x01)
        dock_q7      = (v2_raw >> 11) & 0x7F
        barracks_q5  = (v2_raw >> 18) & 0x1F
        # wall_q5 comes from ll_playstyle_v2b bits 4..0; default 31=never if absent
        v2b_raw  = int(round(pack_b)) if pack_b is not None else 31
        wall_q5  = v2b_raw & 0x1F

        # Decode timestamps
        first_dock_ms = None if dock_q7 == 127 else dock_q7 * 4 * 1000
        first_barracks_ms = None if barracks_q5 == 31 else barracks_q5 * 32 * 1000
        first_wall_ms = None if wall_q5 == 31 else wall_q5 * 32 * 1000
        # first_stable_ms: boolean only (built-but-unknown-time sentinel = 0)
        first_stable_ms = 0 if stable_built else None
        # first_trading_post_ms: inferred from mil_type_v2 == 3
        first_trading_post_ms = 0 if mil_type_v2 == 3 else None

        # Map v2 2-bit enum → old-style enum (0/1/2/4)
        first_mil_type_old = _FIRST_MIL_V2_TO_OLD.get(mil_type_v2, 0)
        expects_forward = bool(fwd_bit)
        mdist_float = mdist_q5 / 16.0

        # Base v1 fields come from their whitelisted slots (no high-bit extension)
        # score_raw and secs_raw are already masked to their true widths above.

    elif has_playstyle_v1:
        # ── v1 legacy decode (iWon/iBeat/heBeat/iCarried/heCarried slots) ─
        beat_raw     = int(round(block.get("ibeathimlasttime",    0))) & 0x00FFFFFF
        he_beat_raw  = int(round(block.get("hebeatmelasttime",    0))) & 0x00FFFFFF
        carry_raw    = int(round(block.get("icarriedhimlasttime", 0))) & 0x00FFFFFF
        he_carry_raw = int(round(block.get("hecarriedmelasttime", 0))) & 0x00FFFFFF

        def _v1_secs_or_none(packed: int) -> Optional[int]:
            v = packed & 0x3FFF
            return None if v >= NEVER_BUILT_SECS else v

        dock_secs     = _v1_secs_or_none(won_raw)
        barracks_secs = _v1_secs_or_none(beat_raw)
        wall_secs     = _v1_secs_or_none(he_beat_raw)
        stable_secs   = _v1_secs_or_none(carry_raw)
        tp_secs       = _v1_secs_or_none(he_carry_raw)

        first_dock_ms          = None if dock_secs is None else dock_secs * 1000
        first_barracks_ms      = None if barracks_secs is None else barracks_secs * 1000
        first_wall_ms          = None if wall_secs is None else wall_secs * 1000
        first_stable_ms        = None if stable_secs is None else stable_secs * 1000
        first_trading_post_ms  = None if tp_secs is None else tp_secs * 1000

        # v1 enum: bits 16..14 of heCarriedMeLastTime
        first_mil_type_v1 = (he_carry_raw >> 14) & 0x07
        # v1 used 5 values (0=none,1=dock,2=barracks,3=stable,4=tp); remap to old-style
        _v1_to_old = {0: 0, 1: 1, 2: 2, 3: 2, 4: 4}
        first_mil_type_old = _v1_to_old.get(first_mil_type_v1, 0)
        expects_forward = bool((he_carry_raw >> 17) & 0x01)
        mdist_q5 = (he_carry_raw >> 18) & 0x1F
        mdist_float = mdist_q5 / 16.0

    return {
        "pid":             pid,
        "style":           style,
        "walls":           walls,
        "wall_strategy":   wstrat,
        "terrain_primary": terrp,
        "terrain_secondary": terrs,
        "heading":         heading,
        "age":             age,
        "civ_id":          civ_id,
        "score":           score_raw,
        "match_ms":        secs_raw * 1000,
        # quantised biases recovered as floats in [0..1]
        "terrain_bias":    tbias_q8 / 255.0,
        "heading_bias":    hbias_q8 / 255.0,
        # Playstyle-extension fields (zero/None when has_playstyle == False)
        "has_playstyle":            has_playstyle,
        "first_dock_ms":            first_dock_ms,
        "first_barracks_ms":        first_barracks_ms,
        "first_wall_ms":            first_wall_ms,
        "first_stable_ms":          first_stable_ms,
        "first_trading_post_ms":    first_trading_post_ms,
        "first_military_building":  first_mil_type_old,
        "expects_forward_observed": expects_forward,
        "military_distance":        mdist_float,
    }


def parse_personality_file(path: Path) -> Optional[PersonalityProbe]:
    """Read a .personality file and return a PersonalityProbe if our packed
    probe data is present (sentinel bit set in myAllyCount).

    Selection strategy (2026-05-13 update):
      - Collect all sentinel-tagged blocks.
      - If every block agrees on wall_strategy, return the block with the
        highest match_ms (longest real match). This upgrades cases where
        the first block is a 3s preinit record but later blocks from real
        60s+ matches carry the confirmed wall_strategy.
      - If blocks disagree on wall_strategy (e.g. a civ used different
        doctrines across different game sessions), fall back to the first
        block to preserve the existing behaviour.

    Returns None if no probe-tagged record exists in the file.
    """
    try:
        raw = path.read_bytes()
        # Handle UTF-16 LE BOM (standard AoE3 personality encoding).
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            text = raw.decode("utf-16", errors="replace")
        else:
            text = raw.decode("utf-8", errors="replace")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[warn] could not read {path.name}: {exc}", file=sys.stderr)
        return None

    blocks = _parse_uservars(text)

    # Collect all sentinel blocks.
    probe_blocks = [b for b in blocks if _is_probe_block(b)]
    if not probe_blocks:
        return None

    # Check wall_strategy consensus across all blocks.
    def _wstrat(b: dict[str, float]) -> int:
        ally = int(round(b.get("myallycount", 0))) & 0x00FFFFFF
        return (ally >> 6) & 0x07

    wstrats = {_wstrat(b) for b in probe_blocks}
    if len(wstrats) == 1:
        # All blocks agree — pick the one with the highest match_ms.
        probe_block = max(
            probe_blocks,
            key=lambda b: b.get("lastgamedifficulty", 0.0),
        )
    else:
        # Disagreement — fall back to first block (preserves old behaviour).
        probe_block = probe_blocks[0]

    fields = _unpack_probe(probe_block)
    return PersonalityProbe(
        personality_file=path.stem,
        leader_key=path.stem.lower(),
        pid=fields["pid"],
        style=fields["style"],
        walls=fields["walls"],
        wall_strategy=fields["wall_strategy"],
        terrain_primary=fields["terrain_primary"],
        terrain_secondary=fields["terrain_secondary"],
        terrain_bias=fields["terrain_bias"],
        heading=fields["heading"],
        heading_bias=fields["heading_bias"],
        civ_id=fields["civ_id"],
        age=fields["age"],
        score=fields["score"],
        match_ms=fields["match_ms"],
        has_playstyle=fields["has_playstyle"],
        first_dock_ms=fields["first_dock_ms"],
        first_barracks_ms=fields["first_barracks_ms"],
        first_wall_ms=fields["first_wall_ms"],
        first_stable_ms=fields["first_stable_ms"],
        first_trading_post_ms=fields["first_trading_post_ms"],
        first_military_building=fields["first_military_building"],
        expects_forward_observed=fields["expects_forward_observed"],
        military_distance=fields["military_distance"],
    )


def scan_personality_dir(directory: Path) -> list[PersonalityProbe]:
    """Scan all .personality files in directory and return those with ll_* data."""
    probes: list[PersonalityProbe] = []
    for path in sorted(directory.glob("*.personality")):
        p = parse_personality_file(path)
        if p is not None:
            probes.append(p)
    return probes


def validate_probes(probes: list[PersonalityProbe]) -> tuple[list[str], list[str]]:
    """Basic validation: check expected fields are sane.

    Returns (issues, summary_lines).
    """
    issues: list[str] = []
    summary: list[str] = []

    if not probes:
        issues.append("no personality probe data found — was cLLReplayProbes true and game ended normally?")
        return issues, summary

    for p in probes:
        line = f"  {p.personality_file:<24s} pid={p.pid} civ={p.civ_name:<14s} ldr={p.leader_key:<22s}"

        if p.pid <= 1:
            issues.append(f"{p.personality_file}: ll_pid={p.pid} is invalid (expected 2..8)")
        if p.civ_id <= 0:
            issues.append(f"{p.personality_file}: ll_civ={p.civ_id} is invalid")
        if p.leader_key.startswith("unassigned"):
            issues.append(f"{p.personality_file}: leader_key is unassigned-* fallback")
        if p.style == 0:
            issues.append(f"{p.personality_file}: ll_style=0 (Unknown) — buildstyle never set")
        if p.match_ms < 5000:
            issues.append(f"{p.personality_file}: ll_match_ms={p.match_ms} very small — spurious early write?")

        line += (
            f" style={p.build_style_name}"
            f" terr={p.terrain_primary_name}+{p.terrain_secondary_name}"
            f" ({p.terrain_bias:.2f})"
            f" head={p.heading_name} ({p.heading_bias:.2f})"
            f" walls={p.wall_strategy_name}"
            f" age={p.age} score={p.score}"
            f" t={p.match_ms // 1000}s"
        )
        summary.append(line)

    return issues, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--dir", type=Path, default=PERSONALITY_DIR,
        help=f"personality directory (default: {PERSONALITY_DIR})",
    )
    ap.add_argument(
        "--file", type=Path, default=None,
        help="parse a single .personality file instead of scanning the directory",
    )
    ap.add_argument(
        "--json", action="store_true",
        help="emit one JSON object per probe to stdout",
    )
    ap.add_argument(
        "--emit-llp", action="store_true",
        help="emit synthetic [LLP v=2 ...] lines compatible with replay_probes.py",
    )
    ap.add_argument(
        "--validate", action="store_true",
        help="run basic validation checks and report issues",
    )
    args = ap.parse_args()

    # Collect probes.
    if args.file is not None:
        path = args.file
        if not path.is_absolute():
            path = args.dir / path
        probe = parse_personality_file(path)
        probes = [probe] if probe is not None else []
    else:
        if not args.dir.exists():
            print(f"personality dir not found: {args.dir}", file=sys.stderr)
            return 2
        probes = scan_personality_dir(args.dir)

    if not probes:
        print("No ll_* probe data found in any personality file.", file=sys.stderr)
        print(
            "Possible causes:\n"
            "  1. The game hasn't ended yet (probes written at game-over).\n"
            "  2. cLLReplayProbes is false in aiGlobals.xs.\n"
            "  3. The match was too short (<60s) and gameOverHandler suppressed the early fire.\n"
            "  4. This is a scenario/SPC game (personality files disabled).",
            file=sys.stderr,
        )
        return 2

    # JSON mode.
    if args.json:
        for p in probes:
            d = asdict(p)
            # Add derived readable names.
            d["civ_name"] = p.civ_name
            d["terrain_primary_name"] = p.terrain_primary_name
            d["terrain_secondary_name"] = p.terrain_secondary_name
            d["heading_name"] = p.heading_name
            d["wall_strategy_name"] = p.wall_strategy_name
            d["build_style_name"] = p.build_style_name
            print(json.dumps(d, separators=(",", ":")))
        return 0

    # LLP emit mode.
    if args.emit_llp:
        for p in probes:
            print(p.to_llp_leader_line())
            print(p.to_llp_line())
        return 0

    # Human-readable summary.
    print(f"Personality probe channel — {len(probes)} AI(s) with ll_* data\n")

    if args.validate:
        issues, summary = validate_probes(probes)
        print("Per-AI snapshot:")
        for line in summary:
            print(line)
        print()
        if issues:
            print(f"FAIL — {len(issues)} issue(s):")
            for line in issues:
                print(f"  - {line}")
            return 1
        else:
            print("PASS — all personality probe fields look valid.")
            return 0
    else:
        for p in probes:
            print(
                f"  {p.personality_file:<26s}"
                f" pid={p.pid}"
                f" civ={p.civ_name:<14s}"
                f" ldr={p.leader_key:<22s}"
                f" style={p.style}({p.build_style_name})"
                f" terr={p.terrain_primary_name}+{p.terrain_secondary_name}"
                f" ({p.terrain_bias:.2f})"
                f" head={p.heading_name}({p.heading_bias:.2f})"
                f" walls={p.wall_strategy_name}"
                f" t={p.match_ms // 1000}s"
            )
        return 0


if __name__ == "__main__":
    sys.exit(main())
