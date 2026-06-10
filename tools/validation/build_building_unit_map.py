"""
build_building_unit_map.py
--------------------------
Extract a "which building trains which unit" mapping from proto.xml.

Output: artifacts/unit_index/building_unit_map.json

Run:
    python3 tools/validation/build_building_unit_map.py
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTO_XML = REPO_ROOT / "artifacts" / "roster_audit" / "base_data" / "proto.xml"
OUT_DIR = REPO_ROOT / "artifacts" / "unit_index"
OUT_FILE = OUT_DIR / "building_unit_map.json"

# ---------------------------------------------------------------------------
# Friendly-name mapping for well-known building proto names.
# Keys are exact proto names; values are what the website should display.
# ---------------------------------------------------------------------------
KNOWN_BUILDING_NAMES: dict[str, str] = {
    # Standard European buildings
    "Barracks": "Barracks",
    "Blockhouse": "Blockhouse",
    "Stable": "Stable",
    "ArtilleryDepot": "Artillery Foundry",
    "Dock": "Dock",
    "Church": "Church",
    "TownCenter": "Town Center",
    "FortFrontier": "Fort",
    "TradingPost": "Trading Post",
    "NativeEmbassy": "Native Embassy",
    "Saloon": "Saloon",
    "Embassy": "Embassy",
    "MercenaryHut": "Mercenary Contractor",
    "NoblesHut": "Nobles' Hut",
    "Corral": "Corral",
    "Farm": "Farm",
    "Manor": "Manor",
    "LivestockPen": "Livestock Pen",
    "FieldHospital": "Field Hospital",
    "IGCTownCenter": "Town Center (IGC)",
    # Asian civs (yp = "Warchiefs" / "Asian Dynasties" prefix)
    "YPBarracksIndian": "Barracks (Indian)",
    "ypBarracksJapanese": "Barracks (Japanese)",
    "YPDockAsian": "Dock (Asian)",
    "ypStableJapanese": "Stable (Japanese)",
    "ypDojo": "Dojo",
    "ypCastle": "Castle",
    "ypCastleIndians": "Castle (Indian)",
    "ypCastleJapanese": "Castle (Japanese)",
    "ypWarAcademy": "War Academy",
    "ypMonastery": "Monastery",
    "ypChurch": "Church (Asian)",
    "ypConsulate": "Consulate",
    "ypTradingPostAsian": "Trading Post (Asian)",
    "ypTradingPostCapture": "Trading Post (Capture)",
    "ypCaravanserai": "Caravanserai",
    "ypVillage": "Village",
    "ypSacredField": "Sacred Field",
    "ypYPLivestockPenAsian": "Livestock Pen (Asian)",
    "YPLivestockPenAsian": "Livestock Pen (Asian)",
    "ypSPCAztecFarm": "Aztec Farm (SPC)",
    # Wonders / unique structures
    "ypWIAgraFort2": "Agra Fort II",
    "ypWIAgraFort3": "Agra Fort III",
    "ypWIAgraFort4": "Agra Fort IV",
    "ypWIAgraFort5": "Agra Fort V",
    "ypWICharminarGate2": "Charminar Gate II",
    "ypWICharminarGate3": "Charminar Gate III",
    "ypWICharminarGate4": "Charminar Gate IV",
    "ypWICharminarGate5": "Charminar Gate V",
    "ypWJShogunate2": "Shogunate II",
    "ypWJShogunate3": "Shogunate III",
    "ypWJShogunate4": "Shogunate IV",
    "ypWJShogunate5": "Shogunate V",
    # DE (Definitive Edition) new civs/buildings  (de prefix)
    "deTavern": "Tavern",
    "deLombard": "Lombard",
    "deCathedral": "Cathedral",
    "dePalace": "Palace",
    "dePort": "Port",
    "deCommandery": "Commandery",
    "deHospital": "Hospital",
    "deWarCamp": "War Camp",
    "deIncaStronghold": "Inca Stronghold",
    "deKallanka": "Kallanka",
    "deMayaCastle": "Maya Castle",
    "deStateCapitol": "State Capitol",
    "deUniqueTower": "Unique Tower",
    "deTower": "Tower",
    "deHouseAfrican": "African House",
    "deHouseInca": "Inca House",
    "deTradingPostCaptureAfrican": "Trading Post (African Capture)",
    "deTradingPostCaptureEuropean": "Trading Post (European Capture)",
    # SPC (single-player campaign) buildings — keep for completeness
    "deSPCCommandPost": "Command Post (SPC)",
    "deSPCFarmAfrican": "African Farm (SPC)",
    "deSPCGreatBank": "Great Bank (SPC)",
    "deSPCPapalEmbassy": "Papal Embassy (SPC)",
    "deSPCSupplyDepot": "Supply Depot (SPC)",
    "SPCXPBaker": "Baker (SPC)",
    "SPCXPFeedStore": "Feed Store (SPC)",
    "SPCXPMiningCamp": "Mining Camp (SPC)",
    "SPCXPMiningCampClone1": "Mining Camp Clone (SPC)",
    # Miscellaneous
    "WarHut": "War Hut",
    "Shrine": "Shrine",
    "euNuggetLombardReward": "Lombard (Reward)",
}

# Prefixes to strip when generating fallback display names
_STRIP_PREFIXES = ("yp", "xp", "de", "ypWI", "ypWJ")


def _fallback_display(proto_name: str) -> str:
    """Convert an unrecognized proto name to a spaced display name."""
    name = proto_name
    # Strip known prefixes
    for prefix in sorted(_STRIP_PREFIXES, key=len, reverse=True):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    # Insert spaces before capital letters (CamelCase → "Camel Case")
    spaced = re.sub(r"([A-Z])", r" \1", name).strip()
    return spaced


def friendly_name(proto_name: str) -> str:
    """Return the display name for a building proto."""
    if proto_name in KNOWN_BUILDING_NAMES:
        return KNOWN_BUILDING_NAMES[proto_name]
    return _fallback_display(proto_name)


def is_building(unit_elem: ET.Element) -> bool:
    """Return True if the proto unit is a building."""
    for ut in unit_elem.findall("unittype"):
        if ut.text in ("Building", "BuildingClass"):
            return True
    return False


def extract(proto_xml_path: Path) -> tuple[dict, dict, dict]:
    """
    Parse proto.xml and return:
      (building_display_names, building_to_units, unit_to_buildings)
    """
    if not proto_xml_path.exists():
        print(f"ERROR: proto.xml not found at {proto_xml_path}", file=sys.stderr)
        sys.exit(1)

    tree = ET.parse(str(proto_xml_path))
    root = tree.getroot()

    building_display_names: dict[str, str] = {}
    building_to_units: dict[str, list[str]] = {}
    unit_to_buildings: dict[str, list[str]] = {}

    for unit in root.findall("unit"):
        train_elems = unit.findall("train")
        if not train_elems:
            continue
        if not is_building(unit):
            continue

        proto = unit.get("name", "")
        if not proto:
            continue

        display = friendly_name(proto)
        building_display_names[proto] = display

        units_trained: list[str] = []
        for t in train_elems:
            unit_proto = (t.text or "").strip()
            if unit_proto:
                units_trained.append(unit_proto)

        # Deduplicate preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for u in units_trained:
            if u not in seen:
                seen.add(u)
                deduped.append(u)

        building_to_units[display] = deduped

        for u in deduped:
            unit_to_buildings.setdefault(u, [])
            if display not in unit_to_buildings[u]:
                unit_to_buildings[u].append(display)

    # Sort unit_to_buildings values for stability
    for k in unit_to_buildings:
        unit_to_buildings[k] = sorted(unit_to_buildings[k])

    return building_display_names, building_to_units, unit_to_buildings


def main() -> None:
    building_display_names, building_to_units, unit_to_buildings = extract(PROTO_XML)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "building_display_names": building_display_names,
        "building_to_units": building_to_units,
        "unit_to_buildings": unit_to_buildings,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    n_buildings = len(building_to_units)
    n_units = len(unit_to_buildings)
    print(f"Done. {n_buildings} buildings, {n_units} units mapped.")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
