#!/usr/bin/env python3
"""
ai_behaviour_map.py — derive per-civ AI behaviour map from XS source.

Goal: review how each civ's AI will actually play **without playing**.
Inputs are static — leader XS files + playstyle_spec.json — so the
output is reproducible and reviewable side-by-side.

Outputs:
  artifacts/validation/ai_behaviour_map.json
  artifacts/validation/ai_behaviour_map.html

Each civ row contains:
  - source_file        : leader XS file path
  - spec_key           : key in playstyle_spec.json
  - leader_label       : display name (e.g. "Pachacuti")
  - personality        : Defensive / Aggressive / Balanced
  - bt.rush_boom       : -1 (boom) to +1 (rush)
  - bt.offense_defense : -1 (def) to +1 (off)
  - bt.bias_trade      : -1 .. +1
  - bt.bias_native     : -1 .. +1
  - mil_focus.{inf,cav,art}
  - build_style        : llUse*Style enum + intensity
  - wall_strategy      : final gLLWallStrategy after helper + override
  - wall_strategy_default : what the build style helper sets
  - wall_strategy_override : if a per-civ override exists
  - distance_multipliers : house/eco/mil/tc
  - strongpoint_profile  : (towerLevel, fortLevel, fwdBaseTowers, preferFwd)
  - tactical_doctrine    : (protection, decapitation, ?, ?)
  - cv.ok_forts, cv.max_towers, cv.max_army_pop
  - spec_claims          : the playstyle_spec.json "claims" block
  - mismatches           : list of (claim, derived, spec) where they disagree
  - age_rules            : optional list of per-age policy snippets
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LEADERS_DIR = ROOT / "game" / "ai" / "leaders"
SPEC_FILE   = ROOT / "playstyle_spec.json"
ART_DIR     = ROOT / "artifacts" / "validation"
HEADER_FILE = ROOT / "game" / "ai" / "aiHeader.xs"
COMMON_FILE = LEADERS_DIR / "leaderCommon.xs"

# ── Default wall strategy implied by each build-style helper ─────────────
# Source: game/ai/leaders/leaderCommon.xs llUse*Style helpers (verified
# inline at build time).
STYLE_DEFAULT_WALL = {
    "llUseCompactFortifiedCoreStyle":      "FortressRing",
    "llUseDistributedEconomicNetworkStyle":"FrontierPalisades",
    "llUseForwardOperationalLineStyle":    "MobileNoWalls",
    "llUseMobileFrontierScatterStyle":     "MobileNoWalls",
    "llUseShrineTradeNodeSpreadStyle":     "MobileNoWalls",
    "llUseCivicMilitiaCenterStyle":        "FrontierPalisades",
    "llUseSteppeCavalryWedgeStyle":        "MobileNoWalls",
    "llUseNavalMercantileCompoundStyle":   "CoastalBatteries",
    "llUseSiegeTrainConcentrationStyle":   "FortressRing",
    "llUseJungleGuerrillaNetworkStyle":    "MobileNoWalls",
    "llUseHighlandCitadelStyle":           "FortressRing",
    "llUseCossackVoiskoStyle":             "FortressRing",
    "llUseRepublicanLeveeStyle":           "UrbanBarricade",
    "llUseAndeanTerraceFortressStyle":     "ChokepointSegments",
}

# Default earliest-forward-base ms baked into each style helper.
# None = style does NOT call llEnableEarlyForwardBase.
# Source: game/ai/leaders/leaderCommon.xs (verified line-by-line).
STYLE_FORWARD_BASE_MS = {
    "llUseCompactFortifiedCoreStyle":      None,
    "llUseDistributedEconomicNetworkStyle":420000,
    "llUseForwardOperationalLineStyle":    300000,
    "llUseMobileFrontierScatterStyle":     360000,
    "llUseShrineTradeNodeSpreadStyle":     480000,
    "llUseCivicMilitiaCenterStyle":        420000,
    "llUseSteppeCavalryWedgeStyle":        300000,
    "llUseNavalMercantileCompoundStyle":   None,
    "llUseSiegeTrainConcentrationStyle":   360000,
    "llUseJungleGuerrillaNetworkStyle":    360000,
    "llUseHighlandCitadelStyle":           None,
    "llUseCossackVoiskoStyle":             360000,
    "llUseRepublicanLeveeStyle":           360000,
    "llUseAndeanTerraceFortressStyle":     None,
}

WALL_STRATEGY_NAMES = {
    0: "FortressRing",
    1: "ChokepointSegments",
    2: "CoastalBatteries",
    3: "FrontierPalisades",
    4: "UrbanBarricade",
    5: "MobileNoWalls",
}
WALL_NAME_TO_ID = {v: k for k, v in WALL_STRATEGY_NAMES.items()}

PERSONALITY_FUNCS = {
    "llSetBalancedPersonality":  "Balanced",
    "llSetAggressivePersonality":"Aggressive",
    "llSetDefensivePersonality": "Defensive",
}

# Civ → leader file & key (for the 24 hard-coded leaders).
# Reference: game/ai/aiLoaderStandard.xs lines 122-216.
NAMED_LEADER_DISPATCH = {
    # cMyCiv check → (leader file, function name, spec key)
    "cCivFrench":       ("leader_bourbon.xs",     "initLeaderBourbon",     "French Louis XVIII Bourbon"),
    "cCivBritish":      ("leader_wellington.xs",  "initLeaderWellington",  "British Elizabeth"),
    "cCivGermans":      ("leader_frederick.xs",   "initLeaderFrederick",   "Germans Frederick Great"),
    "cCivRussians":     ("leader_catherine.xs",   "initLeaderCatherine",   "Russians Catherine"),
    "cCivSpanish":      ("leader_isabella.xs",    "initLeaderIsabella",    "Spanish Isabella Castile"),
    "cCivOttomans":     ("leader_suleiman.xs",    "initLeaderSuleiman",    "Ottomans Suleiman"),
    "cCivPortuguese":   ("leader_henry.xs",       "initLeaderHenry",       "Portuguese Henry Navigator"),
    "cCivDutch":        ("leader_maurice.xs",     "initLeaderMaurice",     "Dutch Maurice Nassau"),
    "cCivDEAmericans":  ("leader_washington.xs",  "initLeaderWashington",  "United States Washington"),
    "cCivDEMexicans":   ("leader_hidalgo.xs",     "initLeaderHidalgo",     "Mexicans Hidalgo Standard"),
    "cCivDEItalians":   ("leader_garibaldi.xs",   "initLeaderGaribaldi",   "Italians Garibaldi"),
    "cCivDEMaltese":    ("leader_valette.xs",     "initLeaderValette",     "Maltese Valette"),
    "cCivXPAztec":      ("leader_montezuma.xs",   "initLeaderMontezuma",   "Aztecs Montezuma"),
    "cCivChinese":      ("leader_kangxi.xs",      "initLeaderKangxi",      "Chinese Kangxi"),
    "cCivDEEthiopians": ("leader_menelik.xs",     "initLeaderMenelik",     "Ethiopians Menelik"),
    "cCivXPIroquois":   ("leader_hiawatha.xs",    "initLeaderHiawatha",    "Haudenosaunee Hiawatha Iroquois"),
    "cCivDEHausa":      ("leader_usman.xs",       "initLeaderUsman",       "Hausa Usman dan Fodio"),
    "cCivDEInca":       ("leader_pachacuti.xs",   "initLeaderPachacuti",   "Inca Pachacuti"),
    "cCivIndians":      ("leader_shivaji.xs",     "initLeaderShivaji",     "Indians Akbar"),
    "cCivJapanese":     ("leader_tokugawa.xs",    "initLeaderTokugawa",    "Japanese Tokugawa Ieyasu"),
    "cCivXPSioux":      ("leader_crazy_horse.xs", "initLeaderCrazyHorse",  "Lakota Crazy Horse"),
    "cCivDESwedish":    ("leader_gustavus.xs",    "initLeaderGustavus",    "Swedes Gustavus Adolphus Swedish"),
    # Napoleonic France is gated through rvlt check first.
    "RvltModNapoleonicFrance": ("leader_napoleon.xs", "initLeaderNapoleon", "Napoleonic France Napoleon Bonaparte Revolution"),
}

# Revolution civs handled in leader_revolution_commanders.xs.
# Reference: game/ai/leaders/leader_revolution_commanders.xs.
# Map rvltName → spec key.
REV_LEADER_SPEC = {
    "RvltModCanadians":            "Canadians Brock Revolution",
    "RvltModRevolutionaryFrance":  "Revolutionary France Robespierre Revolution",
    "RvltModFrenchCanadians":      "French Canadians Papineau Revolution",
    "RvltModBrazil":               "Brazil Pedro Revolution",
    "RvltModArgentines":           "Argentines San Martin Revolution",
    "RvltModChileans":             "Chileans OHiggins Revolution",
    "RvltModPeruvians":            "Peruvians Santa Cruz Peru Revolution",
    "RvltModColumbians":           "Columbians Bolivar Colombia Revolution",
    "RvltModHaitians":             "Haitians Louverture Revolution",
    "RvltModIndonesians":          "Indonesians Diponegoro Revolution",
    "RvltModSouthAfricans":        "South Africans Kruger Boer Revolution",
    "RvltModFinnish":              "Finnish Mannerheim Revolution",
    "RvltModHungarians":           "Hungarians Kossuth Revolution",
    "RvltModRomanians":            "Romanians Cuza Revolution",
    "RvltModEgyptians":            "Egyptians Muhammad Ali Revolution",
    "RvltModBarbary":              "Barbary Barbarossa Corsair Revolution",
    "RvltModYucatan":              "Yucatan Pat Revolution",
    "RvltModMayans":               "Mayans Canek Maya Revolution",
    "RvltModTexians":              "Texians Sam Houston Texas Revolution",
    "RvltModRioGrande":            "Rio Grande Canales Rosillo Revolution",
    "RvltModCalifornians":         "Californians Vallejo Revolution",
    "RvltModBajaCalifornians":     None,  # may not be in spec
    "RvltModCentralAmericans":     "Central Americans Morazan Revolution",
}

# ── Block-level parser ───────────────────────────────────────────────────

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def find_rule_blocks(src: str) -> list[tuple[str, str]]:
    """Return [(rule_name, body)] for every `rule X ... { ... }` block."""
    out = []
    for m in re.finditer(r"^rule\s+(\w+)", src, re.MULTILINE):
        body = slice_braces(src, m)
        if body:
            out.append((m.group(1), body))
    return out

def extract_age_policies(src: str) -> list[dict]:
    """Find per-age branches inside any rule and extract assignments.

    Returns [{age:1, name:"pachacutiMitaEconomy", assignments:{btRushBoom:-0.55, ...}}, ...]
    """
    age_pat = re.compile(r"if\s*\(\s*kbGetAge\(\)\s*(==|<=|>=|<|>)\s*cAge(\d)\s*\)")
    policies = []
    for rule_name, rbody in find_rule_blocks(src):
        for am in age_pat.finditer(rbody):
            op = am.group(1)
            age_n = int(am.group(2))
            branch_body = slice_braces(rbody, am)
            if not branch_body:
                continue
            assigns: dict[str, Any] = {}
            for k in ("btRushBoom","btOffenseDefense","btBiasTrade","btBiasNative",
                      "btBiasInf","btBiasCav","btBiasArt",
                      "cvMinNumVills","cvMaxArmyPop","cvMaxTowers","cvMaxAge"):
                m = re.search(rf"\b{k}\s*=\s*(-?\d+(?:\.\d+)?|true|false)\s*;", branch_body)
                if m:
                    raw = m.group(1)
                    if raw in ("true","false"):
                        assigns[k] = raw == "true"
                    elif "." in raw:
                        assigns[k] = float(raw)
                    else:
                        assigns[k] = int(raw)
            if assigns:
                policies.append({
                    "rule": rule_name,
                    "age": age_n,
                    "op": op,
                    "assignments": assigns,
                })
    return policies

def slice_braces(src: str, header_match: re.Match) -> str:
    """Return the text between the first '{' after header_match and its matching '}'."""
    i = src.find("{", header_match.end())
    if i < 0: return ""
    depth = 0
    j = i
    while j < len(src):
        c = src[j]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[i+1:j]
        j += 1
    return ""

@dataclass
class CivBehaviour:
    spec_key: str
    leader_label: str = ""
    source_file: str = ""
    personality: str = ""
    bt: dict = field(default_factory=dict)
    mil_focus: dict = field(default_factory=dict)
    build_style: dict = field(default_factory=dict)
    wall_strategy: str = ""
    wall_strategy_default: str = ""
    wall_strategy_override: str = ""
    distance_multipliers: dict = field(default_factory=dict)
    strongpoint: dict = field(default_factory=dict)
    tactical_doctrine: dict = field(default_factory=dict)
    cv: dict = field(default_factory=dict)
    forward_base: dict = field(default_factory=dict)
    spec_claims: dict = field(default_factory=dict)
    spec_doctrine_label: str = ""
    spec_doctrine_summary: str = ""
    mismatches: list = field(default_factory=list)
    age_rules: list = field(default_factory=list)
    parse_warnings: list = field(default_factory=list)

# Helper: pull all assignments / calls from a block body.
def parse_block(body: str) -> dict:
    """Extract behaviour knobs from an init block body."""
    out: dict[str, Any] = {
        "personality": "",
        "bt": {},
        "mil_focus": {},
        "build_style": {},
        "wall_strategy_default": "",
        "wall_strategy_override": "",
        "distance_multipliers": {},
        "strongpoint": {},
        "tactical_doctrine": {},
        "cv": {},
        "forward_base": {},
    }
    # Personality.
    for fn, label in PERSONALITY_FUNCS.items():
        if re.search(rf"\b{fn}\s*\(\s*\)", body):
            out["personality"] = label
            break
    # Behaviour-tree biases.
    bt_keys = ("btRushBoom", "btOffenseDefense", "btBiasTrade", "btBiasNative",
               "btBiasInf", "btBiasCav", "btBiasArt")
    for k in bt_keys:
        m = re.search(rf"\b{k}\s*=\s*(-?\d+(?:\.\d+)?)\s*;", body)
        if m:
            out["bt"][k] = float(m.group(1))
    # Military focus.
    m = re.search(r"llSetMilitaryFocus\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)", body)
    if m:
        out["mil_focus"] = {"infantry": float(m.group(1)),
                            "cavalry":  float(m.group(2)),
                            "artillery":float(m.group(3))}
    # Build style.
    m = re.search(r"\b(llUse\w+Style)\s*\(\s*(-?\d+)?\s*(?:,\s*(true|false))?\s*\)", body)
    if m:
        fn = m.group(1)
        intensity = int(m.group(2)) if m.group(2) else None
        early = m.group(3)
        out["build_style"] = {
            "function":  fn,
            "intensity": intensity,
            "early_walls_arg": (early == "true") if early else None,
        }
        out["wall_strategy_default"] = STYLE_DEFAULT_WALL.get(fn, "")
        # Forward base ms implied by the style helper.
        style_fwd = STYLE_FORWARD_BASE_MS.get(fn)
        if style_fwd is not None:
            out["forward_base"]["earliest_ms_from_style"] = style_fwd
    # Explicit wall strategy override.
    m = re.search(r"gLLWallStrategy\s*=\s*cLLWallStrategy(\w+)", body)
    if m:
        out["wall_strategy_override"] = m.group(1)
    # Distance multipliers.
    dm_keys = (
        ("house",   "gLLHouseDistanceMultiplier"),
        ("economic","gLLEconomicDistanceMultiplier"),
        ("military","gLLMilitaryDistanceMultiplier"),
        ("tc",      "gLLTownCenterDistanceMultiplier"),
    )
    for label, glob in dm_keys:
        m = re.search(rf"\b{glob}\s*=\s*(-?\d+(?:\.\d+)?)\s*;", body)
        if m:
            out["distance_multipliers"][label] = float(m.group(1))
    # Strongpoint profile.
    m = re.search(r"llSetBuildStrongpointProfile\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(true|false)\s*\)", body)
    if m:
        out["strongpoint"] = {
            "tower_level":          int(m.group(1)),
            "fort_level":           int(m.group(2)),
            "fwd_base_tower_count": int(m.group(3)),
            "prefer_forward_base":  m.group(4) == "true",
        }
    # Tactical doctrine.
    m = re.search(r"llSetLeaderTacticalDoctrine\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)", body)
    if m:
        out["tactical_doctrine"] = {
            "protection":    float(m.group(1)),
            "decapitation":  float(m.group(2)),
            "param3":        int(m.group(3)),
            "param4":        float(m.group(4)),
        }
    # cv* knobs.
    for k in ("cvOkToBuildForts", "cvMaxTowers", "cvMaxArmyPop", "cvMaxAge", "cvMaxCivPop"):
        m = re.search(rf"\b{k}\s*=\s*(true|false|-?\d+)\s*;", body)
        if m:
            v = m.group(1)
            out["cv"][k] = (v == "true") if v in ("true","false") else int(v)
    # Forward base config.
    m = re.search(r"llEnableEarlyForwardBase\s*\(\s*(-?\d+)\s*\)", body)
    if m:
        out["forward_base"]["earliest_ms"] = int(m.group(1))
    m = re.search(r"gLLForwardBaseEarliestMs\s*=\s*(-?\d+)", body)
    if m:
        out["forward_base"]["earliest_ms"] = int(m.group(1))
    return out

# Find revolution-civ blocks inside leader_revolution_commanders.xs.
def parse_rev_blocks(src: str) -> dict[str, dict]:
    """Split commanders file into per-civ branches.

    Each branch returns parsed knobs plus the integer gRvltCivId it assigns
    (so we can later attribute per-age rules that use `gRvltCivId == N`).
    """
    blocks: dict[str, dict] = {}
    pat = re.compile(r"(?:else\s+if|if)\s*\(\s*rvltName\s*==\s*\"([^\"]+)\"\s*\)")
    matches = list(pat.finditer(src))
    for m in matches:
        body = slice_braces(src, m)
        if body:
            parsed = parse_block(body)
            cidm = re.search(r"gRvltCivId\s*=\s*(\d+)\s*;", body)
            if cidm:
                parsed["rvlt_civ_id"] = int(cidm.group(1))
            blocks[m.group(1)] = parsed
    return blocks

def extract_rev_age_policies(src: str, target_civ_id: int) -> list[dict]:
    """Pull per-age branches that match `gRvltCivId == target_civ_id`.

    Format in source:
        rule rvltAge1Discovery
        {
           ...
           if (gRvltCivId == 1)        { btRushBoom = -0.5; ... }
           else if (gRvltCivId == 2)   { btRushBoom = -0.1; ... }
           ...
        }
    The rule name typically encodes the age (rvltAge1*, rvltAge2*, ...).
    """
    policies: list[dict] = []
    rule_hdrs = list(re.finditer(r"^rule\s+(\w+)", src, re.MULTILINE))
    for rh in rule_hdrs:
        rule_name = rh.group(1)
        rbody = slice_braces(src, rh)
        if not rbody:
            continue
        # Try to read age from rule name (rvltAge1*, rvltAge2*…).
        age_in_name = re.search(r"Age(\d)", rule_name)
        age_n = int(age_in_name.group(1)) if age_in_name else None
        # Find the per-civ branch.
        pat = re.compile(
            rf"(?:else\s+if|if)\s*\(\s*gRvltCivId\s*==\s*{target_civ_id}\s*\)\s*\{{([^}}]*)\}}",
            re.DOTALL,
        )
        for bm in pat.finditer(rbody):
            branch_body = bm.group(1)
            assigns: dict[str, Any] = {}
            for k in ("btRushBoom","btOffenseDefense","btBiasTrade","btBiasNative",
                      "btBiasInf","btBiasCav","btBiasArt",
                      "cvMinNumVills","cvMaxArmyPop","cvMaxTowers"):
                am = re.search(rf"\b{k}\s*=\s*(-?\d+(?:\.\d+)?|true|false)\s*;", branch_body)
                if am:
                    raw = am.group(1)
                    if raw in ("true","false"):
                        assigns[k] = raw == "true"
                    elif "." in raw:
                        assigns[k] = float(raw)
                    else:
                        assigns[k] = int(raw)
            if assigns:
                policies.append({
                    "rule": rule_name,
                    "age": age_n,
                    "assignments": assigns,
                })
    return policies

# Parse support-file shared defaults that always apply to revolutions.
def parse_rev_support(src: str) -> dict[str, dict]:
    """Per-rvltName extra biases applied in the support layer."""
    out: dict[str, dict] = {}
    # Find each `if (...)` branch that contains rvltName checks.
    pat = re.compile(r"if\s*\(\s*((?:\(rvltName\s*==\s*\"[^\"]+\"\)\s*\|\|\s*)*\(?rvltName\s*==\s*\"[^\"]+\"\)?)\s*\)")
    for m in pat.finditer(src):
        cond = m.group(1)
        names = re.findall(r"\"([^\"]+)\"", cond)
        body = slice_braces(src, m)
        if not body: continue
        parsed = parse_block(body)
        for n in names:
            existing = out.setdefault(n, {"bt": {}, "cv": {}})
            for k, v in parsed.get("bt", {}).items():
                existing["bt"][k] = v
            for k, v in parsed.get("cv", {}).items():
                existing["cv"][k] = v
    return out

def merge(base: dict, overlay: dict) -> dict:
    """Shallow per-key merge — overlay wins."""
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out[k])
            merged.update(v)
            out[k] = merged
        elif v not in (None, "", {}, []):
            out[k] = v
    return out

def compute_final_wall(behaviour: dict) -> str:
    override = behaviour.get("wall_strategy_override")
    default  = behaviour.get("wall_strategy_default")
    return override or default or ""

def check_claims(spec_claims: dict, behaviour: dict) -> list[dict]:
    """Compare spec claims to derived behaviour."""
    mm = []
    final_wall = compute_final_wall(behaviour)
    final_wall_id = WALL_NAME_TO_ID.get(final_wall, -1)
    if "wall_strategy" in spec_claims:
        if spec_claims["wall_strategy"] != final_wall_id:
            mm.append({
                "claim": "wall_strategy",
                "spec":  spec_claims["wall_strategy"],
                "spec_name": WALL_STRATEGY_NAMES.get(spec_claims["wall_strategy"], "?"),
                "derived": final_wall_id,
                "derived_name": final_wall or "?",
                "severity": "high",
            })
    # expects_forward → prefer_forward_base, explicit llEnableEarlyForwardBase,
    # or the build style helper enables it.
    if spec_claims.get("expects_forward"):
        fb = behaviour.get("forward_base", {})
        sp = behaviour.get("strongpoint", {})
        eff_ms = fb.get("earliest_ms") or fb.get("earliest_ms_from_style")
        fwd_enabled = (eff_ms is not None and eff_ms <= 480000) or sp.get("prefer_forward_base")
        if not fwd_enabled:
            mm.append({
                "claim": "expects_forward",
                "spec":  True,
                "derived": False,
                "severity": "medium",
            })
    # expects_naval — heuristic: build style includes Naval or wall strategy is CoastalBatteries
    if spec_claims.get("expects_naval"):
        bs = behaviour.get("build_style", {}).get("function", "")
        naval_style = "Naval" in bs or final_wall == "CoastalBatteries"
        if not naval_style:
            mm.append({
                "claim": "expects_naval",
                "spec":  True,
                "derived_build_style": bs,
                "derived_wall": final_wall,
                "severity": "medium",
            })
    # expects_treaty — check effective boom-phase rushBoom: the lower of
    # init value and any age 1/2 rule override. Aggressive personality only
    # truly contradicts treaty if BOTH init and age 1 stay non-negative.
    if spec_claims.get("expects_treaty"):
        init_rb = behaviour.get("bt", {}).get("btRushBoom")
        pers    = behaviour.get("personality", "")
        # Walk age_rules looking for age 1 / age 2 overrides.
        early_rb_overrides = []
        for ar in behaviour.get("age_rules", []):
            if ar.get("age") in (1, 2) and "btRushBoom" in ar.get("assignments", {}):
                early_rb_overrides.append(ar["assignments"]["btRushBoom"])
        candidates = [init_rb] + early_rb_overrides if init_rb is not None else early_rb_overrides
        eff_rb = min(candidates) if candidates else None
        if eff_rb is None:
            pass
        elif pers == "Aggressive" and eff_rb >= 0:
            mm.append({
                "claim": "expects_treaty",
                "spec":  True,
                "derived_eff_rushBoom": eff_rb,
                "derived_personality": pers,
                "severity": "medium",
                "note": "Aggressive personality stays at rush bias in age 1-2 — contradicts treaty",
            })
        elif eff_rb > 0.0:
            mm.append({
                "claim": "expects_treaty",
                "spec":  True,
                "derived_eff_rushBoom": eff_rb,
                "derived_personality": pers,
                "severity": "low",
                "note": "Mild rush bias in age 1-2 — review whether civ should boom harder",
            })
    return mm

# ── Main pass ────────────────────────────────────────────────────────────

def derive_all() -> dict:
    spec = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
    civs_spec = spec["civs"]

    # Parse named leaders.
    by_spec_key: dict[str, CivBehaviour] = {}
    for civ_token, (xs_name, fn_name, spec_key) in NAMED_LEADER_DISPATCH.items():
        xs_path = LEADERS_DIR / xs_name
        if not xs_path.exists():
            continue
        src = read_text(xs_path)
        m = re.search(rf"void\s+{fn_name}\s*\(\s*void\s*\)", src)
        body = slice_braces(src, m) if m else ""
        if not body:
            continue
        parsed = parse_block(body)
        cb = CivBehaviour(spec_key=spec_key, source_file=str(xs_path.relative_to(ROOT)))
        for k, v in parsed.items():
            if hasattr(cb, k):
                setattr(cb, k, v)
        cb.wall_strategy = compute_final_wall(parsed)
        cb.leader_label  = civs_spec.get(spec_key, {}).get("leader_label", "")
        cb.spec_claims   = civs_spec.get(spec_key, {}).get("claims", {})
        cb.spec_doctrine_label   = civs_spec.get(spec_key, {}).get("doctrine_label", "")
        cb.spec_doctrine_summary = civs_spec.get(spec_key, {}).get("doctrine_summary", "")
        # Per-age policy from rule blocks inside this leader file.
        cb.age_rules = extract_age_policies(src)
        # Mismatches need age_rules to compute effective boom-phase rb.
        parsed_with_ages = dict(parsed)
        parsed_with_ages["age_rules"] = cb.age_rules
        cb.mismatches = check_claims(cb.spec_claims, parsed_with_ages)
        by_spec_key[spec_key] = cb

    # Parse revolution commanders.
    rev_src     = read_text(LEADERS_DIR / "leader_revolution_commanders.xs")
    rev_blocks  = parse_rev_blocks(rev_src)
    sup_src     = read_text(LEADERS_DIR / "leader_revolution_support.xs")
    sup_blocks  = parse_rev_support(sup_src)
    # Also pull the shared init block defaults.
    m_init      = re.search(r"void\s+initLegendaryRevolutionSupport\s*\(\s*void\s*\)", sup_src)
    sup_defaults = parse_block(slice_braces(sup_src, m_init)) if m_init else {}

    for rvlt_name, spec_key in REV_LEADER_SPEC.items():
        if not spec_key:
            continue
        commander_parsed = rev_blocks.get(rvlt_name, {})
        if not commander_parsed:
            # Spec mentions this civ but no commander block exists.
            cb = CivBehaviour(spec_key=spec_key,
                              source_file="leader_revolution_commanders.xs (MISSING)")
            cb.parse_warnings.append(f"No commander block for {rvlt_name}")
            cb.spec_claims = civs_spec.get(spec_key, {}).get("claims", {})
            by_spec_key[spec_key] = cb
            continue
        sup_specific = sup_blocks.get(rvlt_name, {})
        merged_bt = dict(sup_defaults.get("bt", {}))
        merged_bt.update(sup_specific.get("bt", {}))
        merged_bt.update(commander_parsed.get("bt", {}))
        merged_cv = dict(sup_defaults.get("cv", {}))
        merged_cv.update(sup_specific.get("cv", {}))
        merged_cv.update(commander_parsed.get("cv", {}))
        commander_parsed["bt"] = merged_bt
        commander_parsed["cv"] = merged_cv

        cb = CivBehaviour(spec_key=spec_key,
                          source_file="game/ai/leaders/leader_revolution_commanders.xs")
        for k, v in commander_parsed.items():
            if hasattr(cb, k):
                setattr(cb, k, v)
        cb.wall_strategy = compute_final_wall(commander_parsed)
        cb.leader_label  = civs_spec.get(spec_key, {}).get("leader_label", "")
        cb.spec_claims   = civs_spec.get(spec_key, {}).get("claims", {})
        cb.spec_doctrine_label   = civs_spec.get(spec_key, {}).get("doctrine_label", "")
        cb.spec_doctrine_summary = civs_spec.get(spec_key, {}).get("doctrine_summary", "")
        cidn = commander_parsed.get("rvlt_civ_id")
        if cidn is not None:
            cb.age_rules = extract_rev_age_policies(rev_src, cidn)
        commander_with_ages = dict(commander_parsed)
        commander_with_ages["age_rules"] = cb.age_rules
        cb.mismatches = check_claims(cb.spec_claims, commander_with_ages)
        by_spec_key[spec_key] = cb

    # Spec keys without any derivation → flag.
    for spec_key in civs_spec:
        if spec_key not in by_spec_key:
            cb = CivBehaviour(spec_key=spec_key, source_file="(no dispatch found)")
            cb.parse_warnings.append("Spec entry has no leader dispatch")
            cb.leader_label  = civs_spec[spec_key].get("leader_label", "")
            cb.spec_claims   = civs_spec[spec_key].get("claims", {})
            by_spec_key[spec_key] = cb

    return {"civs": {k: asdict(v) for k, v in sorted(by_spec_key.items())}}

# ── HTML renderer ─────────────────────────────────────────────────────────

def fmt_cell(v):
    if v is None or v == "": return "—"
    if isinstance(v, bool): return "✓" if v else "✗"
    if isinstance(v, float): return f"{v:.2f}"
    return str(v)

def fmt_bias(v):
    if v is None: return "—"
    bar = ""
    nudge = round(abs(v) * 10)
    side = "+" if v > 0 else "−"
    return f"{side}{abs(v):.2f}"

def render_age_timeline(rules: list[dict]) -> str:
    """Render the per-age policy timeline as a compact 5-cell strip."""
    by_age: dict[int, list[str]] = {1:[],2:[],3:[],4:[],5:[]}
    for r in rules:
        a = r.get("age")
        if a is None or a not in by_age:
            continue
        items = []
        for k, v in r.get("assignments", {}).items():
            short_k = (k.replace("btRushBoom","rb")
                        .replace("btOffenseDefense","od")
                        .replace("btBiasTrade","trd")
                        .replace("btBiasNative","ntv")
                        .replace("btBiasInf","inf")
                        .replace("btBiasCav","cav")
                        .replace("btBiasArt","art")
                        .replace("cvMinNumVills","vill")
                        .replace("cvMaxArmyPop","pop")
                        .replace("cvMaxTowers","twr"))
            if isinstance(v, float):
                items.append(f"{short_k}={v:+.1f}" if abs(v) < 10 else f"{short_k}={v:.0f}")
            else:
                items.append(f"{short_k}={v}")
        by_age[a].append(" ".join(items))
    cells = []
    for age in (1,2,3,4,5):
        body = "<br>".join(by_age[age]) if by_age[age] else "<small class='nil'>—</small>"
        cells.append(f"<div class='age age-{age}'><b>A{age}</b> {body}</div>")
    return "<div class='age-strip'>" + "".join(cells) + "</div>"

def render_html(data: dict) -> str:
    civs = data["civs"]
    rows = []
    for k, cb in civs.items():
        bt = cb.get("bt", {})
        mf = cb.get("mil_focus", {})
        bs = cb.get("build_style", {})
        sp = cb.get("strongpoint", {})
        td = cb.get("tactical_doctrine", {})
        cv = cb.get("cv", {})
        dm = cb.get("distance_multipliers", {})
        fb = cb.get("forward_base", {})
        mms = cb.get("mismatches", [])
        warns = cb.get("parse_warnings", [])
        mm_html = "".join(
            f"<li class='mm-{m.get('severity','low')}'>{m['claim']}: spec={m.get('spec_name', m.get('spec'))} vs derived={m.get('derived_name', m.get('derived'))}</li>"
            for m in mms
        )
        warn_html = "".join(f"<li class='warn'>{w}</li>" for w in warns)
        mm_block = f"<ul class='mm'>{mm_html}{warn_html}</ul>" if (mm_html or warn_html) else "<span class='ok'>OK</span>"
        rows.append(f"""
<tr class='civ-row' data-personality='{cb.get("personality","")}' data-wall='{cb.get("wall_strategy","")}'>
  <td class='spec-key'><b>{cb.get("leader_label","")}</b><br><small>{k}</small></td>
  <td class='personality p-{cb.get("personality","").lower()}'>{cb.get("personality","—")}</td>
  <td class='bt'>
    <div>rushBoom <span>{fmt_bias(bt.get("btRushBoom"))}</span></div>
    <div>offDef <span>{fmt_bias(bt.get("btOffenseDefense"))}</span></div>
    <div>trade <span>{fmt_bias(bt.get("btBiasTrade"))}</span></div>
    <div>native <span>{fmt_bias(bt.get("btBiasNative"))}</span></div>
    <div>inf/cav/art <span>{fmt_cell(bt.get("btBiasInf"))}/{fmt_cell(bt.get("btBiasCav"))}/{fmt_cell(bt.get("btBiasArt"))}</span></div>
  </td>
  <td class='mil-focus'>
    INF {fmt_cell(mf.get("infantry"))}<br>
    CAV {fmt_cell(mf.get("cavalry"))}<br>
    ART {fmt_cell(mf.get("artillery"))}
  </td>
  <td class='build-style'>
    <b>{bs.get("function","—")}</b><br>
    <small>intensity={fmt_cell(bs.get("intensity"))}</small>
  </td>
  <td class='wall ws-{cb.get("wall_strategy","").lower()}'>
    <b>{cb.get("wall_strategy","—")}</b><br>
    <small>default: {cb.get("wall_strategy_default","—")}<br>
    override: {cb.get("wall_strategy_override","—") or "—"}</small>
  </td>
  <td class='strong'>
    twr={fmt_cell(sp.get("tower_level"))}, fort={fmt_cell(sp.get("fort_level"))}<br>
    fwdTwr={fmt_cell(sp.get("fwd_base_tower_count"))}<br>
    preferFwd={fmt_cell(sp.get("prefer_forward_base"))}
  </td>
  <td class='doctrine'>
    prot={fmt_cell(td.get("protection"))}<br>
    decap={fmt_cell(td.get("decapitation"))}
  </td>
  <td class='dist'>
    h={fmt_cell(dm.get("house"))}<br>
    e={fmt_cell(dm.get("economic"))}<br>
    m={fmt_cell(dm.get("military"))}<br>
    tc={fmt_cell(dm.get("tc"))}
  </td>
  <td class='caps'>
    forts={fmt_cell(cv.get("cvOkToBuildForts"))}<br>
    mxTwr={fmt_cell(cv.get("cvMaxTowers"))}<br>
    mxPop={fmt_cell(cv.get("cvMaxArmyPop"))}<br>
    fwdMs={fmt_cell(fb.get("earliest_ms"))}
  </td>
  <td class='ages'>{render_age_timeline(cb.get("age_rules",[]))}</td>
  <td class='mismatches'>{mm_block}</td>
  <td class='source'><small>{cb.get("source_file","")}</small></td>
</tr>""")

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>ANW · AI Behaviour Map</title>
<style>
body {{ font: 13px/1.35 -apple-system,sans-serif; background:#0b0e14; color:#e6e9ef; margin:0; padding:14px; }}
h1 {{ font-size:18px; margin:4px 0 12px; }}
table {{ border-collapse: collapse; width:100%; }}
th, td {{ padding: 6px 8px; border:1px solid #232936; vertical-align: top; text-align: left; }}
th {{ background:#1c2128; position:sticky; top:0; cursor:pointer; user-select:none; z-index:5; }}
tr.civ-row:nth-child(even) td {{ background:#0e1218; }}
tr.civ-row:hover td {{ background:#1a2030; }}
td.spec-key {{ min-width:170px; }}
td.spec-key b {{ font-size:14px; color:#9ec5ff; }}
td.spec-key small {{ color:#697089; }}
td.personality {{ font-weight:600; text-align:center; }}
.p-defensive {{ color:#7ec896; }}
.p-aggressive {{ color:#ff9966; }}
.p-balanced {{ color:#d3c9a8; }}
.ws-fortressring   {{ background:#26342a; }}
.ws-chokepointsegments {{ background:#363426; }}
.ws-coastalbatteries {{ background:#26333d; }}
.ws-frontierpalisades {{ background:#322a2a; }}
.ws-urbanbarricade {{ background:#3a2638; }}
.ws-mobilenowalls {{ background:#2e2a3d; }}
ul.mm {{ margin:0; padding-left:14px; }}
li.mm-high {{ color:#ff6b6b; }}
li.mm-medium {{ color:#ffd566; }}
li.warn {{ color:#999; }}
span.ok {{ color:#7ec896; font-weight:600; }}
td.bt, td.mil-focus, td.dist, td.caps, td.strong, td.doctrine, td.ages {{ font-family: ui-monospace,monospace; font-size:11px; }}
td.bt div {{ display:flex; justify-content:space-between; gap:6px; }}
td.bt div span {{ color:#9ec5ff; }}
div.age-strip {{ display:flex; flex-direction:column; gap:3px; }}
div.age {{ padding:3px 5px; border-radius:3px; }}
div.age-1 {{ background:#1f2530; }}
div.age-2 {{ background:#1f2d2e; }}
div.age-3 {{ background:#2c2d1f; }}
div.age-4 {{ background:#2d231f; }}
div.age-5 {{ background:#2d1f2a; }}
div.age b {{ color:#9ec5ff; }}
small.nil {{ color:#444; }}
input.filter {{ padding:6px 10px; font-size:13px; background:#1c2128; color:#e6e9ef; border:1px solid #2d3340; border-radius:4px; width:280px; }}
.legend {{ display:flex; gap:14px; font-size:12px; margin:6px 0 12px; flex-wrap:wrap; }}
.legend span {{ padding:3px 8px; border:1px solid #2d3340; border-radius:3px; }}
</style></head>
<body>
<h1>ANW · AI Behaviour Map <small style="color:#697089; font-weight:normal;">— 46 civs, static derivation from leader XS files</small></h1>
<div class="legend">
  <span class="ws-fortressring">FortressRing</span>
  <span class="ws-chokepointsegments">ChokepointSegments</span>
  <span class="ws-coastalbatteries">CoastalBatteries</span>
  <span class="ws-frontierpalisades">FrontierPalisades</span>
  <span class="ws-urbanbarricade">UrbanBarricade</span>
  <span class="ws-mobilenowalls">MobileNoWalls</span>
</div>
<input class="filter" placeholder="filter: type civ name, personality, wall strategy…" oninput="filterRows(this.value)">
<p><small>{len(civs)} civs · sortable by column header click · row colour = wall strategy · mismatch column lists where derived behaviour diverges from playstyle_spec.json claims</small></p>
<table id="map">
<thead><tr>
  <th data-col="0">Civ / Leader</th>
  <th data-col="1">Personality</th>
  <th data-col="2">BT biases</th>
  <th data-col="3">Mil focus</th>
  <th data-col="4">Build style</th>
  <th data-col="5">Wall strategy</th>
  <th data-col="6">Strongpoint</th>
  <th data-col="7">Tactical</th>
  <th data-col="8">Dist mults</th>
  <th data-col="9">Caps / FwdBase</th>
  <th data-col="10">Age timeline (A1→A5 policy drift)</th>
  <th data-col="11">Spec mismatches</th>
  <th data-col="12">Source</th>
</tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<script>
function filterRows(q) {{
  q = q.toLowerCase().trim();
  document.querySelectorAll('tr.civ-row').forEach(r => {{
    r.style.display = !q || r.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
document.querySelectorAll('th[data-col]').forEach(th => {{
  th.onclick = () => {{
    const col = +th.dataset.col;
    const tb = document.querySelector('tbody');
    const rows = [...tb.querySelectorAll('tr')];
    rows.sort((a,b) => a.cells[col].innerText.localeCompare(b.cells[col].innerText));
    if (th.dataset.sorted === 'asc') {{ rows.reverse(); th.dataset.sorted = 'desc'; }} else {{ th.dataset.sorted = 'asc'; }}
    rows.forEach(r => tb.appendChild(r));
  }};
}});
</script>
</body></html>"""

def render_markdown(data: dict) -> str:
    """Compact markdown roll-up suitable for committing alongside the validator."""
    civs = data["civs"]
    n = len(civs)
    mm_by_civ = {k: cb["mismatches"] for k, cb in civs.items() if cb["mismatches"]}
    pers = {}
    walls = {}
    for cb in civs.values():
        pers[cb.get("personality") or "?"]  = pers.get(cb.get("personality") or "?",0)+1
        walls[cb.get("wall_strategy") or "?"] = walls.get(cb.get("wall_strategy") or "?",0)+1
    lines = [
        "# ANW · AI Behaviour Map (static derivation)",
        "",
        f"- Civs scored: **{n}**",
        f"- Spec mismatches: **{len(mm_by_civ)}**",
        f"- Personality distribution: " + ", ".join(f"{k}={v}" for k,v in sorted(pers.items())),
        f"- Wall strategy distribution: " + ", ".join(f"{k}={v}" for k,v in sorted(walls.items())),
        "",
        "## Mismatches",
        "",
    ]
    if not mm_by_civ:
        lines.append("_None — every civ's static behaviour matches its playstyle_spec.json claim._")
    else:
        for spec_key, mms in mm_by_civ.items():
            lines.append(f"- **{spec_key}**")
            for m in mms:
                lines.append(f"   - `{m['claim']}` ({m.get('severity','?')}): {m.get('note','')}")
    lines += [
        "",
        "## Per-civ behaviour (one-row summary)",
        "",
        "| Civ | Leader | Personality | Wall | Build style | Mil focus (I/C/A) | Init bt.rb / od |",
        "|---|---|---|---|---|---|---|",
    ]
    for spec_key, cb in sorted(civs.items()):
        mf = cb.get("mil_focus", {})
        bt = cb.get("bt", {})
        bs = cb.get("build_style", {})
        lines.append("| {} | {} | {} | {} | {} | {}/{}/{} | rb={} od={} |".format(
            spec_key, cb.get("leader_label","—"), cb.get("personality","—"),
            cb.get("wall_strategy","—"),
            (bs.get("function","—") or "—").replace("llUse","").replace("Style",""),
            mf.get("infantry","—"), mf.get("cavalry","—"), mf.get("artillery","—"),
            bt.get("btRushBoom","—"), bt.get("btOffenseDefense","—"),
        ))
    return "\n".join(lines) + "\n"

def render_per_civ_md(spec_key: str, cb: dict) -> str:
    """One reviewable Markdown sheet per civ — feed back into iteration loop."""
    bt = cb.get("bt", {}); mf = cb.get("mil_focus", {})
    bs = cb.get("build_style", {}); sp = cb.get("strongpoint", {})
    td = cb.get("tactical_doctrine", {}); cv = cb.get("cv", {})
    dm = cb.get("distance_multipliers", {}); fb = cb.get("forward_base", {})
    sc = cb.get("spec_claims", {})
    lines = [
        f"# {cb.get('leader_label','—')} — {spec_key}",
        "",
        f"- **Source**: `{cb.get('source_file','—')}`",
        f"- **Personality**: {cb.get('personality','—')}",
        f"- **Doctrine label (spec)**: {cb.get('spec_doctrine_label','—')}",
        f"- **Doctrine summary (spec)**: {cb.get('spec_doctrine_summary','—')}",
        "",
        "## Init-time behaviour (from leader_*.xs)",
        "",
        f"- Behaviour-tree biases: rushBoom={bt.get('btRushBoom','—')}, offenseDefense={bt.get('btOffenseDefense','—')}, biasTrade={bt.get('btBiasTrade','—')}, biasNative={bt.get('btBiasNative','—')}",
        f"- Military focus: infantry={mf.get('infantry','—')}, cavalry={mf.get('cavalry','—')}, artillery={mf.get('artillery','—')}",
        f"- Build style: `{bs.get('function','—')}` (intensity={bs.get('intensity','—')})",
        f"- Wall strategy: **{cb.get('wall_strategy','—')}** (default from style: {cb.get('wall_strategy_default','—')}, explicit override: {cb.get('wall_strategy_override','—') or 'none'})",
        f"- Distance multipliers: house={dm.get('house','—')}, eco={dm.get('economic','—')}, mil={dm.get('military','—')}, tc={dm.get('tc','—')}",
        f"- Strongpoint: towers={sp.get('tower_level','—')}, forts={sp.get('fort_level','—')}, fwdBaseTowers={sp.get('fwd_base_tower_count','—')}, preferFwd={sp.get('prefer_forward_base','—')}",
        f"- Tactical doctrine: protection={td.get('protection','—')}, decapitation={td.get('decapitation','—')}",
        f"- Caps: forts={cv.get('cvOkToBuildForts','—')}, maxTowers={cv.get('cvMaxTowers','—')}, maxArmyPop={cv.get('cvMaxArmyPop','—')}",
        f"- Forward base earliest ms: {fb.get('earliest_ms') or fb.get('earliest_ms_from_style') or '—'}",
        "",
        "## Per-age policy drift",
        "",
        "| Age | Rule | Assignments |",
        "|---|---|---|",
    ]
    for ar in cb.get("age_rules", []):
        ag = ar.get("age", "?")
        rn = ar.get("rule", "?")
        ass = ", ".join(f"{k}={v}" for k, v in ar.get("assignments", {}).items())
        lines.append(f"| A{ag} | `{rn}` | {ass} |")
    lines += [
        "",
        "## Spec claims (from playstyle_spec.json)",
        "",
    ]
    for k, v in sc.items():
        lines.append(f"- **{k}**: `{v}`")
    if cb.get("mismatches"):
        lines += ["", "## Mismatches", ""]
        for m in cb["mismatches"]:
            lines.append(f"- ⚠️ **{m['claim']}** (severity={m.get('severity','?')}): {m.get('note','')}")
            for kk, vv in m.items():
                if kk not in ("claim", "severity", "note"):
                    lines.append(f"   - {kk}: `{vv}`")
    else:
        lines += ["", "## Spec verdict", "", "✅ All claims align with derived static behaviour."]
    lines += [
        "",
        "## How to iterate",
        "",
        "1. Edit the dispatch in `" + cb.get('source_file','—') + "` (init block or age-N rule).",
        "2. Re-run `python3 tools/validation/ai_behaviour_map.py`.",
        "3. Diff this file against the new output to see what changed.",
        "4. Open `artifacts/validation/ai_behaviour_map.html` to compare side-by-side.",
    ]
    return "\n".join(lines) + "\n"

def main():
    ART_DIR.mkdir(parents=True, exist_ok=True)
    data = derive_all()
    out_json = ART_DIR / "ai_behaviour_map.json"
    out_html = ART_DIR / "ai_behaviour_map.html"
    out_md   = ART_DIR / "ai_behaviour_map.md"
    per_civ_dir = ART_DIR / "ai_behaviour_per_civ"
    per_civ_dir.mkdir(exist_ok=True)
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    out_html.write_text(render_html(data), encoding="utf-8")
    out_md.write_text(render_markdown(data), encoding="utf-8")
    for spec_key, cb in data["civs"].items():
        slug = re.sub(r"[^a-z0-9]+", "_", spec_key.lower()).strip("_")
        (per_civ_dir / f"{slug}.md").write_text(render_per_civ_md(spec_key, cb), encoding="utf-8")
    # Summary line.
    n_civs = len(data["civs"])
    n_mm   = sum(1 for cb in data["civs"].values() if cb["mismatches"])
    n_warn = sum(1 for cb in data["civs"].values() if cb["parse_warnings"])
    print(f"derived {n_civs} civs · {n_mm} have spec mismatches · {n_warn} parse warnings")
    print(f"json: {out_json}")
    print(f"html: {out_html}")
    print(f"markdown: {out_md}")
    severity_count = {"high":0,"medium":0,"low":0}
    for cb in data["civs"].values():
        for mm in cb["mismatches"]:
            severity_count[mm.get("severity","low")] = severity_count.get(mm.get("severity","low"),0)+1
    print(f"mismatches by severity: {severity_count}")
    # Non-zero high-severity = exit 1 so validator suite can gate on this.
    return 1 if severity_count["high"] > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
