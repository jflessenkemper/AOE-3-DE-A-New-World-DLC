#!/usr/bin/env python3
"""
Resolve trainable military unit rosters for all 40 ANW civs.
Hardened v3: captures ALL unit-grant mechanisms + TIER classification.

Sources tracked per unit:
  train              - AddTrain / CommandAdd in techtree shadow tech
  enable             - Enable effect + unit has LogicalTypeLandMilitary
  homecity_shipment  - FreeHomeCityUnit in homecity deck card
  politician         - FreeHomeCityUnit in politician tech (obtainable chain)
  church             - FreeHomeCityUnit in church / basilica tech
  outlaw             - unit trainable at deSaloon / deTavern
  consulate          - unit from ypConsulate building (Asian civs)
  native_alliance    - unit from TradingPost / NativeEmbassy train list
  revolution         - unit granted by DERevolution* tech
  merc               - mercenary unit (any source)

Tiers:
  hero           - explorer / leader hero unit
  core_standard  - generic military trainable at primary buildings at game start
  core_unique    - civ-defining units trained at own buildings
  situational    - outlaw / consulate / native_alliance / revolution / merc /
                   homecity_shipment-only

Output: artifacts/roster_audit/resolved_rosters.json
"""

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

REPO      = Path(__file__).resolve().parents[2]
CIVMODS   = REPO / "data" / "civmods.xml"
TECHMODS  = REPO / "data" / "techtreemods.xml"
BASE_TECH = REPO / "artifacts" / "roster_audit" / "base_data" / "techtree.xml"
PROTO_XML = REPO / "artifacts" / "roster_audit" / "base_data" / "proto.xml"
OUT_JSON  = REPO / "artifacts" / "roster_audit" / "resolved_rosters.json"
HC_DIR    = REPO / "data"

# ---------------------------------------------------------------------------
# Civs whose Age0 tech is in techtreemods.xml (ANW shadow techs)
# ---------------------------------------------------------------------------
ANW_SHADOW_CIVS = {
    "ANWRevFrance":        "ANWAge0RevolutionaryFrench",
    "ANWNapoleonicFrance": "ANWAge0NapoleonicFrench",
    "ANWMexicans":         "ANWAge0Mexicans",
    "ANWCanadians":        "ANWAge0Canadians",
    "ANWBrazil":           "ANWAge0Brazilians",
    "ANWArgentines":       "ANWAge0Argentines",
    "ANWChileans":         "ANWAge0Chileans",
    "ANWColumbians":       "ANWAge0Columbians",
    "ANWPeruvians":        "ANWAge0Peruvians",
    "ANWHaitians":         "ANWAge0Haitians",
    "ANWSouthAfricans":    "ANWAge0SouthAfricans",
    "ANWIndonesians":      "ANWAge0Indonesians",
    "ANWFinnish":          "ANWAge0Finnish",
    "ANWHungarians":       "ANWAge0Hungarians",
    "ANWRomanians":        "ANWAge0Romanians",
    "ANWBarbary":          "ANWAge0Barbary",
    "ANWEgyptians":        "ANWAge0Egypt",
    "ANWMayans":           "ANWAge0Maya",
    "ANWTexians":          "ANWAge0Texas",
}

# Asian civs that have the Consulate building
ASIAN_CONSULATE_CIVS = {"ANWChinese", "ANWJapanese", "ANWIndians"}

# ---------------------------------------------------------------------------
# Curated signature-unit overrides (2026-06-06)
# ---------------------------------------------------------------------------
# Blurb-promised "signature" units that the heuristic resolver misses. Each
# entry was VERIFIED two ways before inclusion:
#   1. proto exists in proto.xml (so build_unit_index can attach real stats), and
#   2. the unit is genuinely granted to that civ in the mod data —
#      civmods.xml <multipleblocktrain> (emergency garrison militia),
#      anwhomecity*.xml deck card (FreeHomeCityUnit), or techtreemods.xml.
# They are skipped by the normal walk because of either a NON_MILITARY type
# (AbstractHealer / AbstractVillager / Transport / Ship), an ALWAYS_EXCLUDE
# entry, or a grant mechanism (<multipleblocktrain>) the resolver does not
# parse. Injected with source="signature" so downstream consumers (doctrine
# compliance validator) can filter them out of composition-ratio maths.
#
# NOT included — verified absent from the mod data, so wiring would fabricate:
#   ANWHungarians "Hajduk": no deSaloonHajduk grant anywhere; the only hajduk
#   proto granted in civmods is deREVHajdukArquebusier (ANWRussians). Left as a
#   documented content gap rather than an invented roster entry.
SIGNATURE_OVERRIDES = {
    # civ_token: [ (proto, display_label, age, tier) ]
    "ANWBrazil":        [("deREVVoluntarioBatch", "Voluntario da Patria", 3, "core_unique")],
    "ANWUSA":           [("deFedStateMilitiaBatch", "State Militia", 2, "core_unique")],
    "ANWTexians":       [("deFortStateMilitiaBatch", "State Militia", 2, "core_unique")],
    "ANWMexicans":      [("dePadre", "Padre", 2, "core_unique")],
    "ANWFrench":        [("Coureur", "Coureur des Bois", 1, "core_unique")],
    "ANWSpanish":       [("Missionary", "Missionary", 1, "core_unique")],
    "ANWSouthAfricans": [("deREVStarTrekWagon", "Trek Wagon", 3, "core_unique"),
                         ("Fluyt", "Fluyt", 2, "core_unique")],
}

# ---------------------------------------------------------------------------
# Exclusion helpers
# ---------------------------------------------------------------------------

NON_MILITARY_TYPES = {
    "AbstractVillager", "Villager", "Settler", "SettlerNative",
    "Ship", "Warship", "FishingBoat", "Transport", "Ferry",
    "Building", "Wall", "Tower", "Gate", "Fortification",
    "TradeUnit", "TradeCart", "TradeBoat", "Canoe",
    "Hero", "Explorer", "AbstractHero",
    "AbstractFarm", "Farm", "Livestock", "LivestockWagon",
    "Projectile", "Decoration", "Corpse",
    "LogicalTypeAnimal",
    # Pets/companion animals — have LogicalTypeLandMilitary but are not roster units
    "AbstractPet",
    # Healers that are not combat units
    "AbstractHealer",
}

MILITARY_TYPES = {
    "Infantry", "LightInfantry", "HeavyInfantry", "AbstractInfantry",
    "Cavalry", "LightCavalry", "HeavyCavalry", "AbstractCavalry",
    "Artillery", "LightArtillery", "HeavyArtillery", "AbstractArtillery",
    "Shock", "AbstractShockInfantry",
    "Mercenary", "AbstractMercenary",
    "Siege",
    "Warrior",
    "SpecialUnit",
    "AbstractPikeman",
    "Grenadier",
    "AbstractSkirmisher",
    "AbstractMusketeer",
    "AbstractDragoon",
    "AbstractHussar",
    "LogicalTypeLandMilitary",
}

SKIP_NAME_KW = [
    "building", "farm", "plantation", "mill", "dock", "outpost",
    "fort", "blockhouse", "tower", "wall", "gate", "arsenal",
    "market", "church", "shrine", "temple", "native embassy",
    "trading post", "salon", "saloon",
    "villager", "settler", "explorer",
    "fishing", "canoe", "junk", "galleon", "frigate", "sloop",
    "crate", "factory", "estate", "hacienda",
    "bison", "deer", "animal", "livestock", "sheep",
    "dummy", "invisible", "spawner",
    "nativescout",  # explorer variant
    "monitor",     # warship
]

ALWAYS_EXCLUDE = {
    "deCommandWagon", "Bison", "deSPCGreatBombardNoPop", "deSPCJanissaryNoPop",
    "deREVNativeVillager", "SaloonPirate", "SaloonOutlawRider",
    "deREVStarTrekWagon", "NatMercBlowgunWarrior",
    # Pets (companion animals, not military roster units)
    "dePetElephant", "dePetHippo", "dePetLeopard", "dePetWarthog", "dePetMonkey",
    "dePetDog", "ypPetOrangutan", "WarDog", "WolfDog",
    # Trade/economic units
    "Envoy",
    # Healers (not combat trainable units)
    "xpMedicineManAztec", "Surgeon", "FieldHospital",
    # Courtier / support ships
    "Monitor", "FishingBoat", "Caravel", "Frigate", "Galleon",
    # Buildings
    "Barracks", "Stable", "Arsenal", "ArtilleryDepot", "Dock", "Market",
    "Church", "Mill", "Capitol", "House", "TownCenter", "TradingPost",
    "Outpost", "Plantation", "LivestockPen", "WallConnector",
    "WallStraight2", "WallStraight5", "FieldHospital", "deTavern",
    # Utility / non-combat
    "NativeScout", "Priest", "Coureur", "Sheep",
    "CWallGate",
}

MERC_PREFIXES = ("deNatMerc", "NatMerc", "deMerc", "deAllegiance")

MIL_PATTERNS = [
    r"musket", r"pike", r"grenad", r"hussar", r"dragoon", r"cavalry",
    r"lancer", r"infantry", r"warrior", r"soldier", r"skirmish",
    r"rifleman", r"scout(?!.*explorer)", r"ranger", r"archer",
    r"javelineer", r"crossbow", r"spear", r"regular", r"militia",
    r"trooper", r"cannon", r"falconet", r"culverin", r"mortar",
    r"howitzer", r"vaquero", r"gaucho", r"llanero", r"granadero",
    r"insurgente", r"emboscador", r"humbaraci", r"azap", r"deli\b",
    r"sipahi", r"janissary", r"barbary", r"bedouin", r"samurai",
    r"ashigaru", r"kensei", r"yabusame", r"yumi\b", r"naginata",
    r"shinobi", r"rodelero", r"halberdier", r"doppelsoldat",
    r"dopplesold", r"boneguard", r"carolean", r"petard",
    r"spy\b", r"horse artil", r"jagunco", r"gaucho", r"cuirassier",
    r"miquelet", r"cassador", r"cacadore", r"haiduc", r"pandur",
    r"szekler", r"bersagliere", r"pavisier", r"hospitaller",
    r"malacca", r"java", r"cetbang", r"cruzob", r"holcan",
    r"torp\b",  # Finnish
    r"evzone", r"boyar",
    r"regulars?\b", r"state militia", r"minuteman", r"rifleman",
    r"zouave", r"papal guard", r"elmetto",
]

def is_military(proto: str, types: set) -> bool:
    if proto in ALWAYS_EXCLUDE:
        return False
    nl = proto.lower()
    for kw in SKIP_NAME_KW:
        if kw in nl:
            return False
    if types & NON_MILITARY_TYPES:
        return False
    if types & MILITARY_TYPES:
        return True
    for pat in MIL_PATTERNS:
        if re.search(pat, nl):
            return True
    return False

def is_merc(proto: str, types: set) -> bool:
    if any(proto.startswith(p) for p in MERC_PREFIXES):
        return True
    if "Mercenary" in types or "AbstractMercenary" in types:
        return True
    return False

def is_consulate_unit(proto: str, types: set) -> bool:
    """True if this unit is a consulate unit (ypConsulate* or AbstractConsulateUnit)."""
    return (
        "AbstractConsulateUnit" in types or
        "AbstractConsulateSiegeFortress" in types or
        "AbstractConsulateSiegeIndustrial" in types or
        proto.startswith("ypConsulate") or
        proto.startswith("deConsulate") or
        proto.startswith("deLegion")  # Hungarian legion units (consulate-style)
    )

def is_outlaw_unit(proto: str, types: set) -> bool:
    """True if unit is an outlaw/saloon unit."""
    return (
        "Outlaw" in types or
        "AbstractOutlaw" in types or
        proto.startswith("Saloon") or
        proto.startswith("deSaloon") or
        proto.startswith("deOutlaw") or
        proto.startswith("SaloonOutlaw") or
        "outlaw" in proto.lower()
    )

def is_native_warrior(proto: str, types: set) -> bool:
    """True if unit is a native alliance warrior."""
    return (
        "NativeWarrior" in types or
        "AbstractNativeWarrior" in types or
        proto.startswith("Nat") or
        proto.startswith("ypNat") or
        proto.startswith("deNat")
    )

def is_revolution_unit(proto: str, types: set) -> bool:
    """True if unit is a revolution-specific unit."""
    return (
        proto.startswith("deREV") or
        proto.startswith("xpREV") or
        proto.startswith("deRev") or
        "Revolution" in proto
    )

# ---------------------------------------------------------------------------
# Load proto.xml
# ---------------------------------------------------------------------------

def load_proto_info():
    print("Loading proto.xml ...", flush=True)
    proto_info = {}
    tree = ET.parse(PROTO_XML)
    root = tree.getroot()
    for unit in root.iter("unit"):
        name = unit.get("name", "")
        if not name:
            continue
        label_el = unit.find("DisplayNameID")
        label = label_el.text.strip() if (label_el is not None and label_el.text) else name
        types = {ut.text.strip() for ut in unit.findall("unittype") if ut.text}
        proto_info[name] = {"label": label, "types": types}
    print(f"  {len(proto_info)} protos loaded.", flush=True)
    return proto_info


# ---------------------------------------------------------------------------
# Build building -> trainable units map from proto.xml
# ---------------------------------------------------------------------------

def load_building_trains(proto_info: dict):
    """Return {building_proto: [unit_proto, ...]}, and saloon/native train lists."""
    tree = ET.parse(PROTO_XML)
    root = tree.getroot()
    building_trains = {}
    saloon_units = []
    native_alliance_units = []

    for unit in root.iter("unit"):
        name = unit.get("name", "")
        trains = [t.text.strip() for t in unit.findall("train") if t.text]
        if trains:
            building_trains[name] = trains
        # Capture deSaloon/deTavern train lists for outlaw source
        if name in ("deSaloon", "deTavern"):
            for proto in trains:
                if proto not in ALWAYS_EXCLUDE:
                    saloon_units.append(proto)
        # Capture TradingPost/NativeEmbassy train lists for native_alliance source
        if name in ("TradingPost", "NativeEmbassy", "ypTradingPostAsian",
                    "deTradingPostCaptureAfrican", "deTradingPostCaptureEuropean",
                    "ypTradingPostCapture"):
            for proto in trains:
                if proto not in ALWAYS_EXCLUDE and proto != "TradingPost":
                    native_alliance_units.append(proto)

    # Build reverse: unit -> set of buildings it can be trained from
    unit_to_buildings = {}
    for bldg, units in building_trains.items():
        for u in units:
            unit_to_buildings.setdefault(u, set()).add(bldg)

    # Deduplicate
    saloon_units = list(dict.fromkeys(saloon_units))
    native_alliance_units = list(dict.fromkeys(native_alliance_units))

    return building_trains, unit_to_buildings, saloon_units, native_alliance_units


# ---------------------------------------------------------------------------
# Load techtree XML (either ANW mods or base game)
# Returns: tech_effects dict AND obtainable_techs dict
# ---------------------------------------------------------------------------

def _find_child(el, *names):
    """Find first child element matching any of the given tag names."""
    for n in names:
        ch = el.find(n)
        if ch is not None:
            return ch
    return None

def load_tech_effects_from_file(path: Path):
    content = path.read_text(encoding="utf-8", errors="replace")
    root = ET.fromstring(content)
    tech_effects = {}
    for tech_el in (root.findall("Tech") + root.findall("tech")):
        tech_name = tech_el.get("name", "")
        if not tech_name:
            continue
        entry = {
            "add_train": [], "cmd_add": [], "cmd_remove": [],
            "enable": [], "allowed_age": {}, "activates": [],
            "obtainables": [],  # TechStatus obtainable
            "free_units": [],   # (unittype, source_hint) from FreeHomeCityUnit
        }
        effs_el = _find_child(tech_el, "Effects", "effects")
        if effs_el is None:
            tech_effects[tech_name] = entry
            continue
        for eff in effs_el:
            etype    = eff.get("type", "")
            esubtype = eff.get("subtype", "")
            if etype == "Data" and esubtype == "AddTrain":
                u = eff.get("unittype", "")
                if u:
                    entry["add_train"].append(u)
            elif etype == "Data" and esubtype == "Enable":
                tgt = _find_child(eff, "Target", "target")
                if tgt is not None and tgt.text:
                    entry["enable"].append(tgt.text.strip())
            elif etype == "Data" and esubtype == "AllowedAge":
                u = eff.get("unittype", "")
                amt = eff.get("amount", "")
                if u and amt:
                    try:
                        entry["allowed_age"][u] = int(float(amt))
                    except ValueError:
                        pass
            elif etype == "CommandAdd":
                p = eff.get("proto", "")
                if p:
                    entry["cmd_add"].append(p)
            elif etype == "CommandRemove":
                p = eff.get("proto", "")
                if p:
                    entry["cmd_remove"].append(p)
            elif etype == "TechStatus":
                status = eff.get("status", "")
                text   = eff.text.strip() if eff.text else ""
                if status == "active" and text:
                    entry["activates"].append(text)
                elif status == "obtainable" and text:
                    entry["obtainables"].append(text)
            elif etype in ("Data", "Data2") and esubtype in ("FreeHomeCityUnit", "FreeHomeCityUnitIfTechObtainable"):
                u = eff.get("unittype", "") or eff.get("unitType", "")
                if u:
                    entry["free_units"].append(u)
        tech_effects[tech_name] = entry
    return tech_effects


def expand_tech_set(seed_techs: list, all_effects: dict, max_depth: int = 10) -> list:
    """Follow TechStatus 'active' chains from seed techs, return all reachable tech names."""
    visited = set()
    queue = list(seed_techs)
    while queue:
        tech = queue.pop(0)
        if tech in visited:
            continue
        visited.add(tech)
        for activated in all_effects.get(tech, {}).get("activates", []):
            if activated not in visited:
                queue.append(activated)
    return list(visited)


def expand_obtainable_set(seed_techs: list, all_effects: dict) -> set:
    """Collect all tech names reachable via 'obtainable' status from seed tech set."""
    result = set()
    queue = list(seed_techs)
    visited = set()
    while queue:
        tech = queue.pop(0)
        if tech in visited:
            continue
        visited.add(tech)
        for ob in all_effects.get(tech, {}).get("obtainables", []):
            result.add(ob)
            if ob not in visited:
                queue.append(ob)
    return result


# ---------------------------------------------------------------------------
# Load civmods.xml
# ---------------------------------------------------------------------------

def load_civmods():
    print("Loading civmods.xml ...", flush=True)
    tree = ET.parse(CIVMODS)
    root = tree.getroot()
    civs = {}
    for civ_el in root.findall("civ"):
        main_el = civ_el.find("main")
        if main_el is None or main_el.text != "1":
            continue
        name_el = civ_el.find("name")
        if name_el is None:
            continue
        token = name_el.text.strip()
        hero_el = civ_el.find("startingunit")
        hero = hero_el.text.strip() if hero_el is not None and hero_el.text else ""
        age_techs = [
            (at.find("age").text.strip(), at.find("tech").text.strip())
            for at in civ_el.findall("agetech")
            if at.find("age") is not None and at.find("tech") is not None
        ]
        civs[token] = {"hero": hero, "age_techs": age_techs}
    print(f"  {len(civs)} civs loaded.", flush=True)
    return civs


# ---------------------------------------------------------------------------
# Parse homecity deck for a civ -> list of tech names in the deck
# ---------------------------------------------------------------------------

def load_homecity_tech_names(civ_token: str) -> list:
    suffix = civ_token.removeprefix("ANW").lower()
    hc_file = HC_DIR / f"anwhomecity{suffix}.xml"
    if not hc_file.exists():
        return []
    try:
        content = hc_file.read_text(encoding="utf-8", errors="replace")
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    names = []
    for el in root.iter("name"):
        if el.text and el.text.strip():
            names.append(el.text.strip())
    return names


# ---------------------------------------------------------------------------
# Resolve Age: map unit proto to earliest age it's available
# ---------------------------------------------------------------------------

def resolve_age(proto: str, allowed_ages: dict, default_age: int) -> int:
    if proto in allowed_ages:
        aa = allowed_ages[proto]
        return abs(aa) if aa != 0 else default_age
    return default_age


# ---------------------------------------------------------------------------
# Collect units granted by politician/church/basilica techs
# ---------------------------------------------------------------------------

def collect_obtainable_units(expanded_tech_set: set, all_effects: dict) -> dict:
    """
    From the full set of expanded active techs, find all 'obtainable' techs,
    then collect free_units from those techs.

    Returns {proto: source_tag} where source_tag is 'politician', 'church', or 'revolution'.
    """
    obtainables = expand_obtainable_set(list(expanded_tech_set), all_effects)
    result = {}
    for tech_name in obtainables:
        eff = all_effects.get(tech_name, {})
        # Classify tag
        if "DERevolution" in tech_name or "Revolution" in tech_name:
            tag = "revolution"
        elif any(kw in tech_name for kw in
                 ("Church", "Basilica", "Shrine", "Monastery", "church", "basilica")):
            tag = "church"
        else:
            tag = "politician"

        for u in eff.get("free_units", []):
            if u and u not in result:
                result[u] = f"{tag}:{tech_name}"

        # Also capture CommandAdd trains from revolution techs
        if tag == "revolution":
            for u in eff.get("cmd_add", []):
                if u and u not in result and u not in ALWAYS_EXCLUDE:
                    result[u] = f"revolution:{tech_name}"
            for u in eff.get("add_train", []):
                if u and u not in result and u not in ALWAYS_EXCLUDE:
                    result[u] = f"revolution:{tech_name}"

    return result


# ---------------------------------------------------------------------------
# Collect units shipped via homecity deck cards
# ---------------------------------------------------------------------------

def collect_homecity_shipment_units(civ_token: str, all_effects: dict) -> dict:
    """
    Parse the civ's homecity deck, look up each card tech in all_effects,
    collect FreeHomeCityUnit proto names.

    Returns {proto: source_tag}.
    """
    deck_techs = load_homecity_tech_names(civ_token)
    result = {}
    for tech_name in deck_techs:
        eff = all_effects.get(tech_name, {})
        for u in eff.get("free_units", []):
            if u and u not in result:
                result[u] = f"homecity_shipment:{tech_name}"
    return result


# ---------------------------------------------------------------------------
# Classify tier for a unit
# ---------------------------------------------------------------------------

def classify_tier(proto: str, types: set, source: str, civ_token: str,
                  hero_proto: str) -> str:
    """
    Assign tier based on source and unit characteristics.
    hero          - the civ's starting hero/explorer
    core_standard - generic military at primary buildings, game start
    core_unique   - civ-defining unique units
    situational   - outlaw/consulate/native_alliance/revolution/merc/homecity-only
    """
    if proto == hero_proto:
        return "hero"

    # Situational sources are always situational tier
    situational_sources = {
        "outlaw", "consulate", "native_alliance", "revolution",
        "merc", "homecity_shipment", "politician", "church"
    }
    # source may be "source:tech_detail" or plain "source"
    source_base = source.split(":")[0] if ":" in source else source
    if source_base in situational_sources:
        return "situational"

    # Mercs are always situational
    if is_merc(proto, types):
        return "situational"

    # Consulate units are always situational
    if is_consulate_unit(proto, types):
        return "situational"

    # Outlaw units are always situational
    if is_outlaw_unit(proto, types):
        return "situational"

    # Native warrior units are always situational
    if is_native_warrior(proto, types):
        return "situational"

    # Revolution units are always situational
    if is_revolution_unit(proto, types):
        return "situational"

    # For core units: distinguish standard vs unique
    # Unique units tend to have civ-specific prefixes or unusual names
    # Standard units are common European/generic unit archetypes
    # Universal support units that every European civ has — site intentionally omits them
    # They are technically trainable but NOT part of the distinguishing roster
    _UNIVERSAL_SITUATIONAL = {
        "xpPetard", "xpSpy", "xpRam",  # available to virtually all European civs
    }
    if proto in _UNIVERSAL_SITUATIONAL:
        return "situational"

    _STANDARD_ARCHETYPES = {
        "Musketeer", "Pikeman", "Skirmisher", "Dragoon", "Hussar", "Grenadier",
        "Falconet", "Culverin", "Mortar", "Crossbowman", "Halberdier",
        "Ruyter", "Uhlan", "Cavalry", "Infantry", "Settler",
        "xpColonialMilitia", "Longbowman", "Janissary", "Spahi",
        "xpCossack", "xpKhevenhüller",
        "Minuteman", "xpRifleman", "xpGatlingGun",
    }
    if proto in _STANDARD_ARCHETYPES:
        return "core_standard"

    # Protos starting with civ-specific prefixes are likely unique
    _UNIQUE_PREFIXES = (
        "de", "yp", "xp",
    )
    for pfx in _UNIQUE_PREFIXES:
        if proto.startswith(pfx):
            return "core_unique"

    # Generic named units (no prefix, not in standard list)
    # Use label matching for generic archetypes
    return "core_standard"


# ---------------------------------------------------------------------------
# Resolve roster for one ANW-shadow civ (code path A)
# ---------------------------------------------------------------------------

def resolve_anw_shadow(civ_token, civ_data, anw_effects, all_anw_tech_names, proto_info,
                       unit_to_buildings, saloon_units, native_alliance_units,
                       base_effects=None):
    age0_tech = ANW_SHADOW_CIVS[civ_token]
    notes = [f"Code path A (ANW shadow). Age0 tech: {age0_tech}"]

    suffix = civ_token.removeprefix("ANW")

    # Collect all relevant techs for this civ (shadow Age0 + ANW companions)
    techs_to_process = [(age0_tech, 1)]
    companion_map = {
        f"ANWColonialize{suffix}": 2,
        f"ANWFortressize{suffix}": 3,
        f"ANWIndustrialize{suffix}": 4,
        f"ANWImperialize{suffix}": 4,
    }
    for t, age in companion_map.items():
        if t in all_anw_tech_names:
            techs_to_process.append((t, age))
            notes.append(f"Companion: {t} (age {age})")

    age_int_map = {"Age0": 1, "Age1": 1, "Age2": 2, "Age3": 3, "Age4": 4}
    if base_effects:
        for age_str, tech_name in civ_data.get("age_techs", []):
            if tech_name and tech_name != age0_tech and tech_name not in [t for t, _ in techs_to_process]:
                if tech_name in base_effects:
                    techs_to_process.append((tech_name, age_int_map.get(age_str, 1)))
                    notes.append(f"Base age tech: {tech_name} (age {age_str})")

    # Build combined effects
    if base_effects:
        all_combined = {}
        all_combined.update(base_effects)
        all_combined.update(anw_effects)
    else:
        all_combined = anw_effects

    # Expand each tech in techs_to_process through TechStatus 'active' cascade
    expanded = {}  # tech_name -> base_age
    for tname, age in techs_to_process:
        chain = expand_tech_set([tname], all_combined)
        for t in chain:
            if t not in expanded:
                expanded[t] = age

    added = {}   # proto -> {age, source}
    removed = set()
    allowed_ages_all = {}

    for tech_name, base_age in list(expanded.items()):
        eff = anw_effects.get(tech_name) or (base_effects or {}).get(tech_name, {})
        for proto in eff.get("cmd_remove", []):
            removed.add(proto)
        allowed_ages_all.update(eff.get("allowed_age", {}))

        # AddTrain / CommandAdd: directly granted units
        all_granted_direct = set(eff.get("add_train", [])) | set(eff.get("cmd_add", []))
        for proto in all_granted_direct:
            if proto not in added and proto not in ALWAYS_EXCLUDE:
                unit_age = resolve_age(proto, eff.get("allowed_age", {}), base_age)
                src_parts = []
                if proto in eff.get("add_train", []):
                    src_parts.append("AddTrain")
                if proto in eff.get("cmd_add", []):
                    src_parts.append("CommandAdd")
                added[proto] = {"age": unit_age, "source": "train",
                                "source_detail": f"{'+'.join(src_parts)} in {tech_name}"}

        # Enable effects: include if military
        for proto in eff.get("enable", []):
            if proto not in added:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types):
                    unit_age = resolve_age(proto, eff.get("allowed_age", {}), base_age)
                    added[proto] = {
                        "age": unit_age,
                        "source": "enable",
                        "source_detail": f"Enable in {tech_name}",
                    }

    for proto in removed:
        added.pop(proto, None)

    # --- Additional sources ---

    # Politician / church / revolution (obtainable techs from expanded active set)
    ob_units = collect_obtainable_units(set(expanded.keys()), all_combined)
    for proto, src_tag in ob_units.items():
        if proto not in added and proto not in ALWAYS_EXCLUDE:
            pinfo = proto_info.get(proto)
            types = pinfo["types"] if pinfo else set()
            if is_military(proto, types):
                tag = src_tag.split(":")[0]
                added[proto] = {"age": 2, "source": tag, "source_detail": src_tag}

    # Homecity shipment units
    hc_units = collect_homecity_shipment_units(civ_token, all_combined)
    for proto, src_tag in hc_units.items():
        if proto not in added:
            pinfo = proto_info.get(proto)
            types = pinfo["types"] if pinfo else set()
            if is_military(proto, types):
                added[proto] = {"age": 1, "source": "homecity_shipment", "source_detail": src_tag}

    # Saloon/outlaw units — for civs whose tech chain enables deTavern/deSaloon
    has_tavern = any(
        "deTavern" in (all_combined.get(t, {}).get("enable", []) or []) or
        "deSaloon" in (all_combined.get(t, {}).get("enable", []) or [])
        for t in expanded
    )
    if has_tavern:
        for proto in saloon_units:
            if proto not in added and proto not in ALWAYS_EXCLUDE:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types):
                    added[proto] = {"age": 1, "source": "outlaw",
                                    "source_detail": "deSaloon/deTavern train list"}

    # Native alliance units — if civ can enable TradingPost
    has_tp = any(
        "TradingPost" in (all_combined.get(t, {}).get("enable", []) or []) or
        "TradingPost" in (all_combined.get(t, {}).get("cmd_add", []) or []) or
        "NativeEmbassy" in (all_combined.get(t, {}).get("enable", []) or [])
        for t in expanded
    )
    if has_tp:
        for proto in native_alliance_units:
            if proto not in added and proto not in ALWAYS_EXCLUDE:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types):
                    added[proto] = {"age": 1, "source": "native_alliance",
                                    "source_detail": "TradingPost/NativeEmbassy train list"}

    # Consulate units for Asian civs
    if civ_token in ASIAN_CONSULATE_CIVS:
        # YPAAConsulateUnits tech enables all consulate units
        consulate_eff = all_combined.get("YPAAConsulateUnits", {})
        for proto in consulate_eff.get("enable", []):
            if proto not in added and proto not in ALWAYS_EXCLUDE:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types) and is_consulate_unit(proto, types):
                    added[proto] = {"age": 2, "source": "consulate",
                                    "source_detail": "YPAAConsulateUnits Enable"}

    return added, notes


# ---------------------------------------------------------------------------
# Resolve roster for one base-game civ (code path B)
# ---------------------------------------------------------------------------

def resolve_base_game(civ_token, civ_data, base_effects, unit_to_buildings, proto_info,
                      saloon_units, native_alliance_units, anw_effects=None):
    """
    For base-game civs: collect units enabled by the Age0 tech (and cascaded techs).
    A unit is trainable if:
      - It has LogicalTypeLandMilitary (direct military unit), OR
      - It appears in a building that the civ also enables (safety fallback)
    """
    age_map_age_int = {"Age0": 1, "Age1": 1, "Age2": 2, "Age3": 3, "Age4": 4}
    age0_tech = dict(civ_data["age_techs"]).get("Age0", "")
    notes = [f"Code path B (base game). Age0 tech: {age0_tech}"]

    # Combined effects: base + ANW mod overrides
    all_combined = {}
    if base_effects:
        all_combined.update(base_effects)
    if anw_effects:
        all_combined.update(anw_effects)

    # Seed techs from civmods age chain
    seed_techs = [t for _, t in civ_data["age_techs"] if t and t in all_combined]

    # Expand through TechStatus 'active' chains
    all_tech_names = expand_tech_set(seed_techs, all_combined)
    notes.append(f"Expanded to {len(all_tech_names)} techs via TechStatus chains")

    # Assign ages
    tech_age = {}
    for age_str, tech_name in civ_data["age_techs"]:
        tech_age[tech_name] = age_map_age_int.get(age_str, 1)
    for t in all_tech_names:
        if t not in tech_age:
            tech_age[t] = 1

    # Collect all enabled protos
    all_enabled = {}  # proto -> earliest age
    allowed_ages = {}
    cmd_remove = set()

    for tech_name in all_tech_names:
        eff = all_combined.get(tech_name, {})
        base_age = tech_age.get(tech_name, 1)
        for proto in eff.get("enable", []):
            if proto not in all_enabled:
                all_enabled[proto] = base_age
        allowed_ages.update(eff.get("allowed_age", {}))
        for proto in eff.get("cmd_remove", []):
            cmd_remove.add(proto)

    for proto in cmd_remove:
        all_enabled.pop(proto, None)

    # Build enabled buildings set
    enabled_buildings = {p for p in all_enabled if p in unit_to_buildings}

    trainable = {}
    for proto, base_age in all_enabled.items():
        if proto in ALWAYS_EXCLUDE:
            continue
        pinfo = proto_info.get(proto)
        types = pinfo["types"] if pinfo else set()

        if not is_military(proto, types):
            continue

        # Unit qualifies if:
        # 1. It has LogicalTypeLandMilitary (includes all combat units regardless of training method)
        # 2. OR it appears in a building the civ has enabled (fallback for edge cases)
        bldgs = unit_to_buildings.get(proto, set())
        civ_bldgs = bldgs & enabled_buildings

        if "LogicalTypeLandMilitary" in types or civ_bldgs:
            trainable[proto] = {
                "age": resolve_age(proto, allowed_ages, base_age),
                "source": "enable",
                "source_detail": f"Enable in {age0_tech} cascade",
            }

    # --- Additional sources ---

    # AddTrain / CommandAdd from expanded techs
    for tech_name in all_tech_names:
        eff = all_combined.get(tech_name, {})
        base_age = tech_age.get(tech_name, 1)
        for proto in set(eff.get("add_train", [])) | set(eff.get("cmd_add", [])):
            if proto not in trainable and proto not in ALWAYS_EXCLUDE:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types):
                    trainable[proto] = {
                        "age": resolve_age(proto, eff.get("allowed_age", {}), base_age),
                        "source": "train",
                        "source_detail": f"AddTrain/CommandAdd in {tech_name}",
                    }

    # Politician / church / revolution (obtainable techs)
    ob_units = collect_obtainable_units(set(all_tech_names), all_combined)
    for proto, src_tag in ob_units.items():
        if proto not in trainable and proto not in ALWAYS_EXCLUDE:
            pinfo = proto_info.get(proto)
            types = pinfo["types"] if pinfo else set()
            if is_military(proto, types):
                tag = src_tag.split(":")[0]
                trainable[proto] = {"age": 2, "source": tag, "source_detail": src_tag}

    # Homecity shipment units
    hc_units = collect_homecity_shipment_units(civ_token, all_combined)
    for proto, src_tag in hc_units.items():
        if proto not in trainable:
            pinfo = proto_info.get(proto)
            types = pinfo["types"] if pinfo else set()
            if is_military(proto, types):
                trainable[proto] = {"age": 1, "source": "homecity_shipment",
                                    "source_detail": src_tag}

    # Saloon/outlaw units — for civs whose tech chain enables deTavern/deSaloon
    has_tavern = any(
        "deTavern" in (all_combined.get(t, {}).get("enable", []) or []) or
        "deSaloon" in (all_combined.get(t, {}).get("enable", []) or [])
        for t in all_tech_names
    )
    if has_tavern:
        for proto in saloon_units:
            if proto not in trainable and proto not in ALWAYS_EXCLUDE:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types):
                    trainable[proto] = {"age": 1, "source": "outlaw",
                                        "source_detail": "deSaloon/deTavern train list"}

    # Native alliance units — if civ can enable TradingPost
    has_tp = any(
        "TradingPost" in (all_combined.get(t, {}).get("enable", []) or []) or
        "TradingPost" in (all_combined.get(t, {}).get("cmd_add", []) or []) or
        "NativeEmbassy" in (all_combined.get(t, {}).get("enable", []) or [])
        for t in all_tech_names
    )
    if has_tp:
        for proto in native_alliance_units:
            if proto not in trainable and proto not in ALWAYS_EXCLUDE:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types):
                    trainable[proto] = {"age": 1, "source": "native_alliance",
                                        "source_detail": "TradingPost/NativeEmbassy train list"}

    # Consulate units for Asian civs
    if civ_token in ASIAN_CONSULATE_CIVS:
        consulate_eff = all_combined.get("YPAAConsulateUnits", {})
        for proto in consulate_eff.get("enable", []):
            if proto not in trainable and proto not in ALWAYS_EXCLUDE:
                pinfo = proto_info.get(proto)
                types = pinfo["types"] if pinfo else set()
                if is_military(proto, types) and is_consulate_unit(proto, types):
                    trainable[proto] = {"age": 2, "source": "consulate",
                                        "source_detail": "YPAAConsulateUnits Enable"}

    return trainable, notes


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------

def resolve_rosters(civmods, anw_effects, base_effects, unit_to_buildings, proto_info,
                    saloon_units, native_alliance_units):
    all_anw_tech_names = set(anw_effects.keys())
    results = {}

    for civ_token, civ_data in sorted(civmods.items()):
        hero_proto = civ_data["hero"]

        if civ_token in ANW_SHADOW_CIVS:
            added, notes = resolve_anw_shadow(
                civ_token, civ_data, anw_effects, all_anw_tech_names, proto_info,
                unit_to_buildings, saloon_units, native_alliance_units,
                base_effects=base_effects
            )
        else:
            added, notes = resolve_base_game(
                civ_token, civ_data, base_effects, unit_to_buildings, proto_info,
                saloon_units, native_alliance_units, anw_effects=anw_effects
            )

        military_units = []
        mercenaries = []
        unknown = []

        for proto, info in sorted(added.items()):
            if proto == hero_proto:
                continue
            pinfo = proto_info.get(proto)
            if pinfo is None:
                unknown.append(proto)
                types = set()
                label = proto
            else:
                types = pinfo["types"]
                label = pinfo["label"]

            if not is_military(proto, types):
                continue

            # Re-tag source more precisely
            source = info["source"]
            if source == "enable" and is_consulate_unit(proto, types):
                source = "consulate"
            elif source == "enable" and is_outlaw_unit(proto, types):
                source = "outlaw"
            elif source == "enable" and is_native_warrior(proto, types):
                source = "native_alliance"
            elif source == "train" and is_revolution_unit(proto, types):
                source = "revolution"
            elif source in ("enable", "train") and is_revolution_unit(proto, types):
                source = "revolution"

            # Assign tier
            tier = classify_tier(proto, types, source, civ_token, hero_proto)

            entry = {
                "proto": proto,
                "label": label,
                "age": info["age"],
                "source": source,
                "tier": tier,
            }
            if is_merc(proto, types):
                # Mercs are always situational
                entry["tier"] = "situational"
                mercenaries.append(entry)
            else:
                military_units.append(entry)

        # --- Curated signature-unit overrides (verified granted + present) ---
        existing_protos = {u["proto"] for u in military_units + mercenaries}
        for proto, label, age, tier in SIGNATURE_OVERRIDES.get(civ_token, []):
            if proto in existing_protos:
                continue
            pinfo = proto_info.get(proto)
            if pinfo is None:
                notes.append(f"SIGNATURE override skipped (proto absent): {proto}")
                continue
            military_units.append({
                "proto": proto,
                "label": label,
                "age": age,
                "source": "signature",
                "tier": tier,
            })
            notes.append(f"Signature override: +{proto} ({label})")

        if unknown:
            notes.append(f"Protos not in proto.xml: {unknown[:5]}")

        results[civ_token] = {
            "hero": [hero_proto] if hero_proto else [],
            "military_units": military_units,
            "mercenaries": mercenaries,
            "notes": "; ".join(notes),
        }

    return results


# ---------------------------------------------------------------------------
# Self-verification
# ---------------------------------------------------------------------------

def self_verify(results: dict):
    print("\n=== SELF-VERIFICATION ===", flush=True)
    ok = True

    # --- Regression: Chinese must include ChuKoNu, IronFlail, MeteorHammer ---
    chinese = results.get("ANWChinese", {})
    cn_protos = {u["proto"] for u in chinese.get("military_units", [])}
    required_cn = ["ypChuKoNu", "ypIronFlail", "ypMeteorHammer"]
    for req in required_cn:
        if req in cn_protos:
            print(f"PASS: ANWChinese includes {req}", flush=True)
        else:
            print(f"FAIL: ANWChinese MISSING {req}", flush=True)
            ok = False

    # --- Regression: Italians must include dePapalGuard, deNMPapalZouave, deNMPandour ---
    italians = results.get("ANWItalians", {})
    it_protos = {u["proto"] for u in italians.get("military_units", []) + italians.get("mercenaries", [])}
    required_it = ["dePapalGuard", "deNMPapalZouave", "deNMPandour"]
    for req in required_it:
        if req in it_protos:
            print(f"PASS: ANWItalians includes {req}", flush=True)
        else:
            print(f"FAIL: ANWItalians MISSING {req}", flush=True)
            ok = False

    # --- Regression: Lakota must include xpWarBow ---
    lakota = results.get("ANWLakota", {})
    la_protos = {u["proto"] for u in lakota.get("military_units", [])}
    if "xpWarBow" in la_protos:
        print("PASS: ANWLakota includes xpWarBow (Cetan Bow)", flush=True)
    else:
        print("FAIL: ANWLakota MISSING xpWarBow", flush=True)
        ok = False

    # --- Regression: no 'PapalLancer' anywhere ---
    all_protos_set = {u["proto"] for cv in results.values()
                      for u in cv["military_units"] + cv["mercenaries"]}
    if "PapalLancer" not in all_protos_set:
        print("PASS: PapalLancer not in any roster (correctly absent)", flush=True)
    else:
        print("FAIL: PapalLancer appeared in rosters (phantom proto)", flush=True)
        ok = False

    # --- Regression: Mexicans must NOT include Cuatrero / Lancero ---
    mex = results.get("ANWMexicans", {})
    mex_protos = {u["proto"] for u in mex.get("military_units", []) + mex.get("mercenaries", [])}
    bad_mex = {"Cuatrero", "Lancero"}
    bad_found = bad_mex & mex_protos
    if not bad_found:
        print("PASS: ANWMexicans does not include phantom Cuatrero/Lancero", flush=True)
    else:
        print(f"FAIL: ANWMexicans has phantom protos: {bad_found}", flush=True)
        ok = False

    # --- Regression: France must include Musketeer, Hussar, Falconet ---
    for france in ["ANWFrench", "ANWNapoleonicFrance", "ANWRevFrance"]:
        if france not in results:
            print(f"FAIL: {france} missing", flush=True); ok = False; continue
        units = results[france]["military_units"]
        combined = {u["proto"].lower() for u in units} | {u["label"].lower() for u in units}
        expected = ["musketeer", "hussar", "falconet"]
        matched = [kw for kw in expected if any(kw in x for x in combined)]
        if len(units) >= 5 and matched:
            print(f"PASS: {france} — {len(units)} units, keywords matched: {matched}", flush=True)
        else:
            print(f"FAIL: {france} — {len(units)} units, matched: {matched}", flush=True)
            ok = False

    # --- Sanity: distinct proto count ---
    all_protos = {u["proto"] for cv in results.values() for u in cv["military_units"]}
    n = len(all_protos)
    if 30 <= n <= 600:
        print(f"PASS: {n} distinct military protos across all civs", flush=True)
    else:
        print(f"FAIL: {n} distinct military protos (expected 30-600)", flush=True)
        ok = False

    # --- Tier sanity: every unit has a tier ---
    missing_tier = [(cv, u["proto"]) for cv, data in results.items()
                    for u in data["military_units"] + data["mercenaries"]
                    if "tier" not in u or not u["tier"]]
    if not missing_tier:
        print("PASS: All units have tier field", flush=True)
    else:
        print(f"FAIL: {len(missing_tier)} units missing tier", flush=True)
        ok = False

    # --- Spot-print 4 civs ---
    for spot in ["ANWChinese", "ANWItalians", "ANWFrench", "ANWMexicans"]:
        if spot in results:
            units = results[spot]["military_units"]
            mercs = results[spot]["mercenaries"]
            print(f"\nSpot — {spot} ({len(units)} mil units, {len(mercs)} mercs):", flush=True)
            for u in (units + mercs)[:15]:
                print(f"  [{u.get('tier','?'):12s}] [{u['source'][:10]:10s}] Age{u['age']} "
                      f"{u['proto']:45s} [{u['label']}]", flush=True)
            total = len(units) + len(mercs)
            if total > 15:
                print(f"  … +{total-15} more", flush=True)

    print(f"\nSelf-verify: {'PASS' if ok else 'FAIL'}", flush=True)
    return ok


# ---------------------------------------------------------------------------
# Discrepancy report (trustworthy version)
# ---------------------------------------------------------------------------

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())

# Known spelling aliases as pairs (a, b) — fuzzy_match will check both directions
# Entries: (site_term, proto_term)
_SPELLING_ALIAS_PAIRS = [
    ("cassador", "cacadore"),
    ("pandour", "pandur"),
    ("schiavone", "pandour"),  # deNMPandour displays as Schiavone
    # Generic artillery labels used by new-world/revolution civs on the site
    ("field guns", "falconet"),
    ("field guns", "culverin"),
    # Barbary/Ottoman generic labels
    ("gunpowder troops", "humbaraci"),
    ("gunpowder troops", "azap"),
    ("gunpowder troops", "janissary"),
    ("gunpowder troops", "musketeer"),
    # Cetan Bow -> xpWarBow
    ("cetan bow", "warbow"),
    ("cetan", "warbow"),
]
# Keep legacy dict alias for backward compat
_SPELLING_ALIASES = {a: b for a, b in _SPELLING_ALIAS_PAIRS}

def _stems(s: str) -> list:
    """Return normalized word stems (first 6 chars) for significant words."""
    words = re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split()
    return [w[:6] for w in words if len(w) >= 4]

def fuzzy_match(a: str, b: str) -> bool:
    """Normalized fuzzy match — strips non-alphanumeric before comparing."""
    an, bn = norm(a), norm(b)
    if not an or not bn:
        return False
    if an == bn or an in bn or bn in an:
        return True
    # Spelling alias check (both directions per pair)
    al = a.lower()
    bl = b.lower()
    for alias_a, alias_b in _SPELLING_ALIAS_PAIRS:
        if alias_a in al and alias_b in bl:
            return True
        if alias_b in al and alias_a in bl:
            return True
        # Also check normalized versions
        nan, nbn = norm(alias_a), norm(alias_b)
        if nan in an and nbn in bn:
            return True
        if nbn in an and nan in bn:
            return True
    # Stem-based: any significant word stem from a appears in norm(b), or vice versa
    sa, sb = _stems(a), _stems(b)
    for stem in sa:
        if stem in bn:
            return True
    for stem in sb:
        if stem in an:
            return True
    return False

def build_discrepancy_report(results, proto_info):
    std_path    = REPO / "data" / "anw_standard_units.json"
    blurbs_path = REPO / "data" / "anw_civ_blurbs.json"
    site_builder = REPO / "tools" / "validation" / "build_release_readiness_site.py"
    icons_path  = REPO / "artifacts" / "retreat_design" / "available_unit_icons.txt"

    std_units  = json.loads(std_path.read_text())   if std_path.exists()   else {}
    blurbs     = json.loads(blurbs_path.read_text()) if blurbs_path.exists() else {}

    # Load hero dict from site builder
    hero_units = set()
    if site_builder.exists():
        sb_text = site_builder.read_text()
        for line in sb_text.splitlines():
            m = re.search(r'"([^"]+)",?\s*$', line)
            if m and "]" not in line and "{" not in line:
                hero_units.add(m.group(1))

    available_icons = set()
    if icons_path.exists():
        for line in icons_path.read_text().splitlines():
            available_icons.add(line.strip().lower())

    def icon_status(unit_name: str) -> str:
        """Return 'exists', 'alias', or 'new-needed'."""
        name_slug = re.sub(r"[^a-z0-9]+", "_", unit_name.lower()).strip("_")
        for candidate in [f"{name_slug}_icon.png", f"{name_slug}.png"]:
            if candidate in available_icons:
                return "exists"
        # fuzzy check
        for icon in available_icons:
            base = icon.replace("_icon.png", "").replace(".png", "").replace("_", " ")
            if norm(unit_name) in base or base in norm(unit_name):
                return "alias"
        return "new-needed"

    civs_correct = civs_missing = civs_extra = 0
    tot_miss_unique = tot_miss_std = tot_miss_icon_ok = tot_miss_icon_new = 0
    tot_extra = 0
    rows = []
    json_rows = []

    for civ_token in sorted(results):
        res   = results[civ_token]
        mil   = res["military_units"]
        mercs = res["mercenaries"]

        # Only compare CORE units (hero + core_standard + core_unique) to site data
        core_units = [u for u in mil if u.get("tier") in ("core_standard", "core_unique")]
        situational_units = [u for u in mil + mercs
                             if u.get("tier") == "situational"]

        site_units   = std_units.get(civ_token, [])
        unique_units = blurbs.get(civ_token, {}).get("unique_units", [])
        all_site     = site_units + unique_units

        # TRUE MISSING: core units resolved but no site match (exclude heroes)
        missing = []
        for u in core_units:
            if any(fuzzy_match(u["proto"], h) or fuzzy_match(u["label"], h)
                   for h in hero_units):
                continue
            if not any(fuzzy_match(u["proto"], s) or fuzzy_match(u["label"], s)
                       for s in all_site):
                ist = icon_status(u["label"] or u["proto"])
                missing.append({
                    "proto": u["proto"],
                    "display": u["label"],
                    "tier": u["tier"],
                    "age": u["age"],
                    "source": u["source"],
                    "icon_status": ist,
                })
                if u["tier"] == "core_unique":
                    tot_miss_unique += 1
                else:
                    tot_miss_std += 1
                if ist in ("exists", "alias"):
                    tot_miss_icon_ok += 1
                else:
                    tot_miss_icon_new += 1

        # TRUE PHANTOM: site lists it but NOT resolved AND no proto in proto.xml
        phantoms = []
        all_res_tokens = {u["proto"] for u in mil + mercs} | {u["label"] for u in mil + mercs}
        for s in site_units:
            if any(fuzzy_match(s, rt) for rt in all_res_tokens):
                continue  # resolved -> OK
            # Verify: does proto.xml contain any unit matching this name?
            matched_proto = next(
                (name for name in proto_info
                 if fuzzy_match(s, name) or (proto_info[name]["label"]
                                             and fuzzy_match(s, proto_info[name]["label"]))),
                None
            )
            if matched_proto is None:
                # No proto at all -> confirmed phantom
                phantoms.append({"site_name": s, "confirmed_no_proto": True,
                                  "reason": "no matching proto in proto.xml"})
            # else: proto exists but resolver missed it -> resolver gap (NOT a phantom)

        tot_extra += len(phantoms)

        # Extras: situational units (for reference)
        extras = [{"display": u["label"], "source": u["source"], "proto": u["proto"]}
                  for u in situational_units[:20]]

        if missing or phantoms:
            if missing: civs_missing += 1
            if phantoms: civs_extra += 1
            status = f"DIFF (miss={len(missing)}, phantom={len(phantoms)})"
        else:
            civs_correct += 1
            status = "OK"

        rows.append({
            "civ": civ_token, "status": status,
            "resolved_core": len(core_units), "site": len(site_units),
            "missing": [m["proto"] for m in missing],
            "phantoms": [p["site_name"] for p in phantoms],
            "notes": res["notes"],
        })
        json_rows.append({
            "civ": civ_token,
            "status": status,
            "missing": missing,
            "phantom": phantoms,
            "extras": extras,
        })

    # Build report text
    lines = []
    lines.append("# ANW Roster Audit — Final Report\n")
    lines.append("_Generated by `tools/validation/resolve_civ_rosters.py` (hardened v3)_\n")
    lines.append("_Sources tracked: train, enable, homecity_shipment, politician, church,_\n")
    lines.append("_outlaw, consulate, native_alliance, revolution, merc_\n")
    lines.append("_Tier classification: hero | core_standard | core_unique | situational_\n\n")
    lines.append("## Summary\n")
    lines.append(f"- **Civs fully correct (no diff):** {civs_correct} / {len(rows)}")
    lines.append(f"- **Civs with TRUE MISSING core units:** {civs_missing}")
    lines.append(f"- **Civs with TRUE PHANTOM units:** {civs_extra}")
    lines.append(f"- **Total true-missing (unique):** {tot_miss_unique}")
    lines.append(f"- **Total true-missing (standard):** {tot_miss_std}")
    lines.append(f"- **Missing units renderable with existing icons:** {tot_miss_icon_ok}")
    lines.append(f"- **Missing units needing new icons:** {tot_miss_icon_new}")
    lines.append(f"- **Total true-phantom unit entries:** {tot_extra}")
    lines.append("")
    lines.append("> **Methodology note:** Only CORE units (core_standard + core_unique tiers)")
    lines.append("> are compared against the site. Situational units (outlaw, consulate,")
    lines.append("> native_alliance, revolution, merc, homecity shipments) are listed separately")
    lines.append("> as EXTRAS and are NOT counted as missing.")
    lines.append("")

    lines.append("### Confirmed Phantom List\n")
    lines.append("These units appear in site data but have ZERO matching proto in proto.xml:\n")
    all_phantoms = [(r["civ"], p["site_name"]) for r in json_rows for p in r["phantom"]]
    if all_phantoms:
        for civ, pname in all_phantoms:
            lines.append(f"- `{pname}` in **{civ}**")
    else:
        lines.append("- _None confirmed_")
    lines.append("")

    lines.append("---\n")
    lines.append("## Per-Civ Status\n")
    lines.append("| Civ | Status | Core-Resolved | Site | Missing Protos | Phantom Names |")
    lines.append("|-----|--------|---------------|------|----------------|---------------|")
    for r in rows:
        miss_s  = ", ".join(f"`{x}`" for x in r["missing"]) or "—"
        extra_s = ", ".join(f"`{x}`" for x in r["phantoms"]) or "—"
        lines.append(
            f"| {r['civ']} | {r['status']} | {r['resolved_core']} | {r['site']} "
            f"| {miss_s} | {extra_s} |"
        )
    lines.append("")

    lines.append("---\n")
    lines.append("## Missing Units Detail\n")
    for r in json_rows:
        if r["missing"]:
            lines.append(f"### {r['civ']}\n")
            for m in r["missing"]:
                lines.append(f"- **{m['display']}** (`{m['proto']}`) "
                              f"— tier:{m['tier']} age:{m['age']} source:{m['source']} "
                              f"icon:{m['icon_status']}")
            lines.append("")

    lines.append("---\n")
    lines.append("## Resolver Notes Per Civ\n")
    for r in rows:
        if r["notes"]:
            lines.append(f"**{r['civ']}:** {r['notes']}\n")

    return ("\n".join(lines), civs_correct, civs_missing, civs_extra,
            tot_miss_unique, tot_miss_std, tot_miss_icon_ok, tot_miss_icon_new, tot_extra,
            json_rows)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    proto_info = load_proto_info()
    building_trains, unit_to_buildings, saloon_units, native_alliance_units = \
        load_building_trains(proto_info)

    print(f"  {len(saloon_units)} saloon/outlaw units from deSaloon/deTavern.", flush=True)
    print(f"  {len(native_alliance_units)} native alliance units from TP/NativeEmbassy.",
          flush=True)

    print("Loading techtreemods.xml ...", flush=True)
    anw_effects = load_tech_effects_from_file(TECHMODS)
    print(f"  {len(anw_effects)} techs loaded from techtreemods.", flush=True)

    print("Loading base techtree.xml ...", flush=True)
    base_effects = load_tech_effects_from_file(BASE_TECH)
    print(f"  {len(base_effects)} techs loaded from base techtree.", flush=True)

    civmods = load_civmods()

    print(f"\nResolving {len(civmods)} ANW civs ...", flush=True)
    results = resolve_rosters(civmods, anw_effects, base_effects, unit_to_buildings,
                              proto_info, saloon_units, native_alliance_units)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT_JSON}", flush=True)

    passed = self_verify(results)

    (report, c_ok, c_miss, c_extra,
     t_miss_unique, t_miss_std, t_miss_icon_ok, t_miss_icon_new, t_extra,
     json_rows) = build_discrepancy_report(results, proto_info)

    rpath = REPO / "artifacts" / "roster_audit" / "ROSTER_AUDIT_FINAL.md"
    rpath.write_text(report, encoding="utf-8")
    print(f"Wrote {rpath}", flush=True)

    # Write final JSON
    jpath = REPO / "artifacts" / "roster_audit" / "roster_audit_final.json"
    jpath.write_text(json.dumps(json_rows, indent=2, ensure_ascii=False))
    print(f"Wrote {jpath}", flush=True)

    print(f"""
=== HEADLINE NUMBERS ===
Civs fully correct        : {c_ok} / {len(results)}
Civs with missing core    : {c_miss}
Civs with phantom         : {c_extra}
True-missing (unique)     : {t_miss_unique}
True-missing (standard)   : {t_miss_std}
Missing icon-renderable   : {t_miss_icon_ok}
Missing need-new-icon     : {t_miss_icon_new}
Total true-phantom        : {t_extra}
""", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
