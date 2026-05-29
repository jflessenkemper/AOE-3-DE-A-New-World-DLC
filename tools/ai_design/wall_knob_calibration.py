#!/usr/bin/env python3
"""ANW per-civ wall-knob calibration — single source of truth.

For each of 40 civs we set 14 wall tuning knobs (gLLWall* in aiHeader.xs).
Calibration anchors:
  1. wall_strategy (from playstyle_spec.json claims) — picks the topology
  2. per-age strategy (from NATION_PLAYSTYLE.ages in a_new_world.html)
  3. historical doctrine + terrain label hint

The 14 knobs and their semantic ranges:

  radius             8..28     ring radius in tiles
  gates              1..5      gate count
  age2stone          0|1       jump straight to stone at Colonial
  trigger_age        2..4      first age that lays a wall (5=never)
  seg_len            6..20     chokepoint segment length
  towers             0..8      tower every N pieces (0=none)
  secondary          0..5,-1   fallback strategy (-1=none)
  vils               0..12     villagers dispatched to wall plan
  fwd_bias           0.0..1.0  forward bias: 0=hug TC, 1=push to choke
  outer_ring         0..12     double-ring outer offset (0=single)
  outposts           0..6      outposts before first wall
  repair             0..3      repair aggressiveness
  closure_pct        0..100    closure % counted as "done" (100 = no holes)
  no_water           0|1       refuse water-tile wall pieces

Run:
    python3 tools/ai_design/wall_knob_calibration.py --emit-xs > game/ai/core/aiWallKnobsByCiv.xs
    python3 tools/ai_design/wall_knob_calibration.py --audit
"""
from __future__ import annotations
import argparse, json, sys, pathlib

# ---------------------------------------------------------------------------
# 40-civ calibration table.
#
# Key = engine civ token (matches kbGetCivName or cCiv* enum).
# rev_token = ANW* name for revolution-spawn civs (None for base civs).
# Each row also includes free-text 'doctrine' for review without launching.
# ---------------------------------------------------------------------------

CALIBRATION = {

    # ============================================================
    # FORTRESS RING (13 civs) — all-sides defense, dense walls.
    # Inca, Ottomans, Maltese, Chinese, French, Ethiopians, Indians,
    # Canadians, Chileans, Peruvians, Egyptians, Finnish, Brazil
    # ============================================================

    "DEInca": dict(  # Pachacuti — Andean Terrace Fortress
        rev_token=None, strategy=0,
        radius=14, gates=2, age2stone=1, trigger_age=2, seg_len=20,
        towers=4, secondary=1, vils=8, fwd_bias=0.20, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Tight terraced core, early stone, valley-mouth chokes secondary"),

    "Germans": dict(  # Frederick — UrbanBarricade actually per spec (4) ... wait, spec=4 (Urban) for Frederick? Let me re-check
        rev_token=None, strategy=4,   # per spec wall_strategy=4 Urban
        radius=14, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=8, secondary=0, vils=7, fwd_bias=0.25, outer_ring=8,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Prussian double-ring around drillyard, tower-dense, strict closure"),

    "Ottomans": dict(  # Suleiman — Fortress double ring (engineer corps)
        rev_token=None, strategy=0,
        radius=20, gates=4, age2stone=1, trigger_age=2, seg_len=20,
        towers=6, secondary=4, vils=8, fwd_bias=0.30, outer_ring=6,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Janissary-engineer double ring, open gate count for trade, outer ring for siege absorption"),

    "DEMaltese": dict(  # Valette — siege-survivor multi-line
        rev_token=None, strategy=0,
        radius=16, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=8, secondary=2, vils=10, fwd_bias=0.15, outer_ring=6,
        outposts=1, repair=3, closure_pct=100, no_water=1,  # coast OK if needed
        doctrine="Order of St John siege doctrine, tower spam, double ring, coastal Coastal fallback"),

    "Chinese": dict(  # Kangxi — Great Wall doctrine = Choke primary, Fortress fallback
        rev_token=None, strategy=0,  # per spec
        radius=18, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=5, secondary=1, vils=7, fwd_bias=0.40, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Wall doctrine: long defensive spine with watchtowers, choke fallback for hills"),

    "French": dict(  # Louis XVIII Bourbon — court army stone fortress
        rev_token=None, strategy=0,
        radius=18, gates=2, age2stone=1, trigger_age=2, seg_len=20,
        towers=7, secondary=2, vils=9, fwd_bias=0.20, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Vauban-style star fort, narrow gates, royal court depth"),

    "Indians": dict(  # Shivaji — Maratha hill-fort (HighlandCitadel → FortressRing)
        rev_token=None, strategy=0,  # HTML: "hill-fort line locks down ground" = HighlandCitadel = FortressRing
        radius=16, gates=2, age2stone=1, trigger_age=2, seg_len=20,
        towers=7, secondary=1, vils=7, fwd_bias=0.35, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Maratha hill-fort citadel, dense tower interleave, ghat-pass choke fallback"),

    "DEEthiopians": dict(  # Menelik — fortress (per spec 0) but called Choke historically; spec wins
        rev_token=None, strategy=0,
        radius=20, gates=3, age2stone=0, trigger_age=2, seg_len=20,
        towers=4, secondary=1, vils=5, fwd_bias=0.40, outer_ring=4,
        outposts=3, repair=3, closure_pct=100, no_water=1,
        doctrine="Highland fortress with long sparse defensive lines, late stone-tier (resource-scarce)"),

    "ANWCanadians": dict(  # Brock — Fortress per spec
        rev_token="ANWCanadians", strategy=0,
        radius=18, gates=3, age2stone=0, trigger_age=2, seg_len=20,
        towers=5, secondary=3, vils=6, fwd_bias=0.35, outer_ring=4,
        outposts=3, repair=3, closure_pct=100, no_water=1,
        doctrine="Lake-and-river defensive line, staying palisade till Fortress for cost, Frontier fallback"),

    "ANWChileans": dict(  # OHiggins — Fortress per spec
        rev_token="ANWChileans", strategy=0,
        radius=16, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=5, secondary=1, vils=6, fwd_bias=0.30, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Andes-flank pocket fort, stone Colonial, choke fallback for cordillera pass"),

    "ANWPeruvians": dict(  # Santa Cruz — Fortress per spec
        rev_token="ANWPeruvians", strategy=0,
        radius=16, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=6, secondary=1, vils=6, fwd_bias=0.30, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Andean defensive Confederation pocket, similar to Chileans but tower-heavier"),

    "ANWEgyptians": dict(  # Muhammad Ali — Fortress per spec, modernizer
        rev_token="ANWEgyptians", strategy=0,
        radius=22, gates=4, age2stone=1, trigger_age=2, seg_len=20,
        towers=5, secondary=2, vils=7, fwd_bias=0.25, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Modernized Cairo citadel, Nile-bank with coastal supplement"),

    "ANWFinnish": dict(  # Mannerheim — Fortress per spec
        rev_token="ANWFinnish", strategy=0,
        radius=18, gates=2, age2stone=0, trigger_age=2, seg_len=20,
        towers=6, secondary=3, vils=5, fwd_bias=0.45, outer_ring=4,
        outposts=4, repair=3, closure_pct=100, no_water=1,
        doctrine="Mannerheim Line — palisade-tier forward, dense outpost net, frontier fallback"),

    # ============================================================
    # CHOKEPOINT SEGMENTS (4 civs) — terrain pinches only.
    # Aztecs, Haitians, Indonesians, Mayans
    # ============================================================

    "XPAztec": dict(  # Montezuma — Jungle Guerrilla; spec=1 Choke
        rev_token=None, strategy=1,
        radius=10, gates=2, age2stone=0, trigger_age=2, seg_len=20,
        towers=3, secondary=5, vils=3, fwd_bias=0.75, outer_ring=0,
        outposts=4, repair=3, closure_pct=100, no_water=1,
        doctrine="Causeway/jungle choke walls, mostly War Hut substitution, late + sparse"),

    "ANWHaitians": dict(  # Toussaint — Choke per spec
        rev_token="ANWHaitians", strategy=1,
        radius=10, gates=2, age2stone=0, trigger_age=2, seg_len=20,
        towers=4, secondary=5, vils=3, fwd_bias=0.70, outer_ring=0,
        outposts=4, repair=3, closure_pct=100, no_water=1,
        doctrine="Mountain-pass guerrilla, palisade only, fallback to mobile if dispersed"),

    "ANWIndonesians": dict(  # Diponegoro — Choke per spec
        rev_token="ANWIndonesians", strategy=1,
        radius=10, gates=2, age2stone=0, trigger_age=2, seg_len=20,
        towers=3, secondary=5, vils=3, fwd_bias=0.75, outer_ring=0,
        outposts=4, repair=3, closure_pct=100, no_water=1,
        doctrine="Java Wars jungle/volcanic chokes, palisade, mobile fallback"),

    "ANWMayans": dict(  # Canek — Choke per spec
        rev_token="ANWMayans", strategy=1,
        radius=10, gates=2, age2stone=0, trigger_age=2, seg_len=20,
        towers=3, secondary=5, vils=3, fwd_bias=0.70, outer_ring=0,
        outposts=4, repair=3, closure_pct=100, no_water=1,
        doctrine="Jungle pyramid chokes, jaguar ambush, late palisade only"),

    # ============================================================
    # COASTAL BATTERIES (5 civs) — land-side wall, gun towers at coast.
    # ============================================================

    "British": dict(  # Elizabeth — Coastal per spec (sea-power)
        rev_token=None, strategy=2,
        radius=22, gates=4, age2stone=1, trigger_age=2, seg_len=20,
        towers=6, secondary=0, vils=6, fwd_bias=0.20, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Channel-defense coastal, dense towers facing land, gates open for trade"),

    "Portuguese": dict(  # Henry the Navigator — Coastal
        rev_token=None, strategy=2,
        radius=22, gates=4, age2stone=1, trigger_age=2, seg_len=20,
        towers=5, secondary=0, vils=6, fwd_bias=0.20, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Atlantic carrack-defense coastal, gates face inland trade, water is wide-open by design"),

    "Dutch": dict(  # Maurice — Coastal + Urban hybrid (Dutch dyke)
        rev_token=None, strategy=2,
        radius=18, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=7, secondary=4, vils=7, fwd_bias=0.15, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Dutch dyke-defense, narrow gates, tower-spam, urban barricade fallback in city core"),

    "ANWBarbary": dict(  # Barbarossa — Coastal (corsair port)
        rev_token="ANWBarbary", strategy=2,
        radius=20, gates=3, age2stone=0, trigger_age=2, seg_len=20,
        towers=6, secondary=0, vils=5, fwd_bias=0.35, outer_ring=4,
        outposts=3, repair=3, closure_pct=100, no_water=1,
        doctrine="Corsair port walls land-side, gun batteries seaward, palisade-tier (raid economy)"),

    "ANWSouthAfricans": dict(  # Kruger — Coastal per spec (laager doctrine on coast)
        rev_token="ANWSouthAfricans", strategy=2,
        radius=18, gates=3, age2stone=0, trigger_age=2, seg_len=20,
        towers=5, secondary=3, vils=5, fwd_bias=0.30, outer_ring=4,
        outposts=3, repair=3, closure_pct=100, no_water=1,
        doctrine="Boer laager defense, palisade-tier, frontier fallback inland"),

    # ============================================================
    # FRONTIER PALISADES (3 civs) — quick wooden ring, more gates.
    # Hausa, Russians, Romanians
    # ============================================================

    "ANWBrazil": dict(  # Pedro I — Distributed Economic Network → FrontierPalisades
        rev_token="ANWBrazil", strategy=3,  # matches llUseDistributedEconomicNetworkStyle default + prose ("Light walling")
        radius=20, gates=4, age2stone=0, trigger_age=2, seg_len=20,
        towers=4, secondary=2, vils=6, fwd_bias=0.30, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Pedro I Imperial Court — light palisade frontier, distributed plantations, coastal Atlantic fallback"),

    "DEHausa": dict(  # Usman — Frontier per spec
        rev_token=None, strategy=3,
        radius=18, gates=5, age2stone=0, trigger_age=2, seg_len=20,
        towers=3, secondary=5, vils=4, fwd_bias=0.55, outer_ring=4,
        outposts=4, repair=3, closure_pct=100, no_water=1,
        doctrine="Hausa caravanserai frontier, palisade only, mobile fallback for jihad raids"),

    "Russians": dict(  # Ivan the Terrible — Frontier per spec (steppe palisade)
        rev_token=None, strategy=3,
        radius=22, gates=4, age2stone=0, trigger_age=2, seg_len=20,
        towers=4, secondary=0, vils=5, fwd_bias=0.45, outer_ring=4,
        outposts=4, repair=3, closure_pct=100, no_water=1,
        doctrine="Kremlin-style palisade-then-stone with sentinel towers on steppe frontier"),

    "ANWRomanians": dict(  # Cuza — Frontier per spec
        rev_token="ANWRomanians", strategy=3,
        radius=18, gates=4, age2stone=0, trigger_age=2, seg_len=20,
        towers=3, secondary=2, vils=4, fwd_bias=0.50, outer_ring=4,
        outposts=3, repair=3, closure_pct=100, no_water=1,
        doctrine="Carpathian palisade frontier, light towers, coastal fallback on Black Sea"),

    # ============================================================
    # URBAN BARRICADE (5 civs) — tight compact inner ring + towers.
    # ============================================================

    "ANWRevFrance": dict(  # Robespierre — Urban per spec
        rev_token="ANWRevFrance", strategy=4,
        radius=10, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=6, secondary=0, vils=5, fwd_bias=0.10, outer_ring=4,
        outposts=1, repair=3, closure_pct=100, no_water=1,
        doctrine="Parisian Section barricade — Industrial trigger, tight inner ring, fanatical repair"),

    "DEItalians": dict(  # Garibaldi — Urban per spec
        rev_token=None, strategy=4,
        radius=12, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=5, secondary=0, vils=4, fwd_bias=0.15, outer_ring=4,
        outposts=1, repair=3, closure_pct=100, no_water=1,
        doctrine="Risorgimento city walls, Colonial trigger, tight ring with bell-tower observation"),

    "DEMexicans": dict(  # Hidalgo — Urban per spec
        rev_token=None, strategy=4,
        radius=11, gates=3, age2stone=0, trigger_age=2, seg_len=20,
        towers=4, secondary=3, vils=4, fwd_bias=0.20, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Insurgente town barricade, palisade-tier (resource constraint), frontier fallback"),

    "DEAmericans": dict(  # Washington — Urban per spec
        rev_token=None, strategy=4,
        radius=12, gates=3, age2stone=1, trigger_age=2, seg_len=20,
        towers=5, secondary=3, vils=5, fwd_bias=0.20, outer_ring=4,
        outposts=2, repair=3, closure_pct=100, no_water=1,
        doctrine="Continental Army camp barricade, stone Colonial, frontier-palisade fallback in field"),

    # ============================================================
    # MOBILE / NO WALLS (10 civs) — scouts + outposts, no perimeter.
    # ============================================================

    "ANWNapoleonicFrance": dict(  # Napoleon — Mobile per spec
        rev_token="ANWNapoleonicFrance", strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=4, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=4, repair=0, closure_pct=0, no_water=1,
        doctrine="Grande Armée — no walls, dense outpost screen, urban barricade if forced back"),

    "ANWArgentines": dict(  # San Martín — Mobile per spec
        rev_token="ANWArgentines", strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=3, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=4, repair=0, closure_pct=0, no_water=1,
        doctrine="Andean expedition no-walls, frontier palisade if cornered"),

    "ANWColumbians": dict(  # Bolívar — Mobile per spec
        rev_token="ANWColumbians", strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=3, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=4, repair=0, closure_pct=0, no_water=1,
        doctrine="Gran Colombia liberation column, no walls, frontier fallback"),

    "XPIroquois": dict(  # Hiawatha — Mobile per spec (Iroquois)
        rev_token=None, strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=1, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=5, repair=0, closure_pct=0, no_water=1,
        doctrine="Iroquois Confederacy — longhouse village, no perimeter walls, choke fallback at portages"),

    "ANWHungarians": dict(  # Kossuth — Mobile per spec (Hussar doctrine)
        rev_token="ANWHungarians", strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=3, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=4, repair=0, closure_pct=0, no_water=1,
        doctrine="Magyar hussar — pure mobile, frontier fallback if pinned"),

    "Japanese": dict(  # Tokugawa — Mobile per spec (samurai field doctrine)
        rev_token=None, strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=4, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=3, repair=0, closure_pct=0, no_water=1,
        doctrine="Tokugawa daimyō field army, no walls, urban barricade fallback at castle"),

    "XPSioux": dict(  # Chief Gall — Mobile per spec
        rev_token=None, strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=3, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=5, repair=0, closure_pct=0, no_water=1,
        doctrine="Plains horse warrior — pure mobile, outpost screen, frontier fallback"),

    "Spanish": dict(  # Isabella — Mobile per spec (Reconquista raid)
        rev_token=None, strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=2, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=3, repair=0, closure_pct=0, no_water=1,
        doctrine="Reconquista mobile column, coastal fallback (Iberian peninsula)"),

    "DESwedish": dict(  # Gustavus Adolphus — Mobile per spec (caroline drill)
        rev_token=None, strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=4, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=3, repair=0, closure_pct=0, no_water=1,
        doctrine="Swedish Caroline — mobile field doctrine, urban barricade fallback in Baltic city"),

    "ANWTexians": dict(  # Sam Houston — Mobile per spec
        rev_token="ANWTexians", strategy=5,
        radius=0, gates=0, age2stone=0, trigger_age=5, seg_len=0,
        towers=0, secondary=3, vils=0, fwd_bias=0.0, outer_ring=0,
        outposts=5, repair=0, closure_pct=0, no_water=1,
        doctrine="Texas Ranger — pure mobile cavalry, frontier fallback"),
}


def emit_xs() -> str:
    """Emit the centralized aiWallKnobsByCiv.xs source."""
    rows = []
    rows.append("// AUTO-GENERATED by tools/ai_design/wall_knob_calibration.py")
    rows.append("// 40-civ × 14-knob calibration table.")
    rows.append("// Edit the .py file and re-emit; do not hand-edit this XS file.")
    rows.append("//")
    rows.append("// Called from aiLoaderStandard.xs::preInit() AFTER initLeader<Name>()")
    rows.append("// so per-civ knobs override any strategy defaults set in leader files.")
    rows.append("")
    rows.append("void llSetWallKnobsForCiv(void)")
    rows.append("{")
    rows.append("   // Resolve civ key — use kbGetCivName so we can distinguish")
    rows.append("   // base civs from revolution-spawn civs (ANW*).")
    rows.append("   string civKey = kbGetCivName(cMyCiv);")
    rows.append("")

    # Sort: base civs (rev_token=None) first by civ_token alphabetically,
    # then revolution civs by rev_token.
    base_civs = [(k,v) for k,v in CALIBRATION.items() if v.get("rev_token") is None]
    rev_civs  = [(k,v) for k,v in CALIBRATION.items() if v.get("rev_token") is not None]

    first = True
    for civ_token, kn in base_civs:
        kw = "if" if first else "else if"
        first = False
        # Base civs match via civ_token (ANW prefix)
        rows.append(f'   {kw} (civKey == "{civ_token}")')
        rows.append("   {")
        rows.append(f'      // {civ_token}: {kn["doctrine"]}')
        rows.extend(_emit_knob_block(kn))
        rows.append("   }")

    for civ_token, kn in rev_civs:
        rows.append(f'   else if (civKey == "{kn["rev_token"]}")')
        rows.append("   {")
        rows.append(f'      // {civ_token} ({kn["rev_token"]}): {kn["doctrine"]}')
        rows.extend(_emit_knob_block(kn))
        rows.append("   }")

    rows.append("   else")
    rows.append("   {")
    rows.append("      // Unknown civ — leave defaults from aiHeader.xs.")
    rows.append("      llProbe(\"wall.knobs\", \"civ=\" + civKey + \" status=default\");")
    rows.append("      return;")
    rows.append("   }")
    rows.append("")
    rows.append("   // One-shot probe so validators can confirm per-civ knob set reached the engine.")
    rows.append("   llProbe(\"wall.knobs\",")
    rows.append("      \"civ=\" + civKey +")
    rows.append("      \" strategy=\" + gLLWallStrategy +")
    rows.append("      \" r=\" + gLLWallRadius +")
    rows.append("      \" g=\" + gLLWallGateCount +")
    rows.append("      \" stoneA2=\" + gLLWallTierAge2Stone +")
    rows.append("      \" trig=\" + gLLWallTriggerAge +")
    rows.append("      \" segL=\" + gLLWallSegmentLength +")
    rows.append("      \" tow=\" + gLLWallTowerInterleave +")
    rows.append("      \" sec=\" + gLLWallSecondaryStrategy +")
    rows.append("      \" v=\" + gLLWallVillagerCount +")
    rows.append("      \" fwd=\" + gLLWallForwardBiasFraction +")
    rows.append("      \" outer=\" + gLLWallOuterRingDelta +")
    rows.append("      \" outp=\" + gLLWallEarlyOutpostCount +")
    rows.append("      \" rep=\" + gLLWallRepairAggressiveness +")
    rows.append("      \" clo=\" + gLLWallClosurePctTarget +")
    rows.append("      \" noW=\" + gLLWallNoWaterBuild);")
    rows.append("}")
    rows.append("")
    return "\n".join(rows)


def _emit_knob_block(kn: dict) -> list[str]:
    """Emit one assignment block for a calibrated row."""
    return [
        f"      gLLWallStrategy             = {kn['strategy']};",
        f"      gLLWallRadius               = {kn['radius']};",
        f"      gLLWallGateCount            = {kn['gates']};",
        f"      gLLWallTierAge2Stone        = {'true' if kn['age2stone'] else 'false'};",
        f"      gLLWallTriggerAge           = {kn['trigger_age']};",
        f"      gLLWallSegmentLength        = {kn['seg_len']};",
        f"      gLLWallTowerInterleave      = {kn['towers']};",
        f"      gLLWallSecondaryStrategy    = {kn['secondary']};",
        f"      gLLWallVillagerCount        = {kn['vils']};",
        f"      gLLWallForwardBiasFraction  = {kn['fwd_bias']};",
        f"      gLLWallOuterRingDelta       = {kn['outer_ring']};",
        f"      gLLWallEarlyOutpostCount    = {kn['outposts']};",
        f"      gLLWallRepairAggressiveness = {kn['repair']};",
        f"      gLLWallClosurePctTarget     = {kn['closure_pct']};",
        f"      gLLWallNoWaterBuild         = {'true' if kn['no_water'] else 'false'};",
    ]


def audit():
    """Sanity audit of the calibration table."""
    print(f"=== {len(CALIBRATION)}-civ wall-knob calibration audit ===")
    by_strategy = {}
    for civ, kn in CALIBRATION.items():
        by_strategy.setdefault(kn["strategy"], []).append(civ)
    labels = {0:"FortressRing",1:"Choke",2:"Coastal",3:"Frontier",4:"Urban",5:"Mobile"}
    for s in sorted(by_strategy):
        print(f"  strategy {s} {labels.get(s,'?'):14s} {len(by_strategy[s]):2d} civs:  {', '.join(by_strategy[s])}")

    # Range checks
    issues = []
    for civ, kn in CALIBRATION.items():
        if not (0 <= kn["radius"] <= 28): issues.append((civ, "radius", kn["radius"]))
        if not (0 <= kn["gates"] <= 5): issues.append((civ, "gates", kn["gates"]))
        if not (2 <= kn["trigger_age"] <= 5): issues.append((civ, "trigger_age", kn["trigger_age"]))
        if not (0.0 <= kn["fwd_bias"] <= 1.0): issues.append((civ, "fwd_bias", kn["fwd_bias"]))
        if not (0 <= kn["closure_pct"] <= 100): issues.append((civ, "closure_pct", kn["closure_pct"]))
        if not (0 <= kn["repair"] <= 3): issues.append((civ, "repair", kn["repair"]))
        # Mobile civs should have radius=0
        if kn["strategy"] == 5 and kn["radius"] != 0:
            issues.append((civ, "mobile-with-radius", kn["radius"]))
    if issues:
        print(f"\nRANGE ISSUES ({len(issues)}):")
        for civ, key, v in issues: print(f"  {civ}.{key} = {v}")
    else:
        print("\n  range checks: PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-xs", action="store_true")
    ap.add_argument("--audit",   action="store_true")
    args = ap.parse_args()
    if args.audit:
        audit()
        return
    if args.emit_xs:
        sys.stdout.write(emit_xs())
        return
    audit()
    print()
    print("Run with --emit-xs to print the XS source.")


if __name__ == "__main__":
    main()
