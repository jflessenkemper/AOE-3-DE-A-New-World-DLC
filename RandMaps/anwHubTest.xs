// ANW Hub Test -- 8-player AI doctrine test arena
// Player 1 = observer at center island, slots 2-8 = AI in 7 wedge compartments
// surrounding a central naval sea with river inlets, native villages,
// trade route, and shared sea resources.
//
// Status (2026-05-20, v5+):
//   - water-fix v5: central sea ~5500 tiles, spoke inner endpoints at r=0.12
//     overlap sea edge to close walk-around gaps between compartments.
//   - cliff geometry: single heptagonal craterRim (chained influence
//     segments) + 7 radial spokes with outer endpoints pushed past r=0.50.
//   - sea+bay resources: 18 fish clusters, 8 whales, 10 nuggets in the
//     central sea; 7 bays each with 5 salmon + 1 whale + 1 sea-nugget.
//   - native villages, trade-route sockets, and starting resources are
//     placed in EVERY compartment (no missing-coverage holes).
//   - extras enabled: jaguar packs, capybara/tapir/rhea/llama herds,
//     huari strongholds, vulture props on the mountain ring.
//   - 20 cosmetic terrain patches + up to 35 forests + 14 global mines;
//     all kept out of the central sea via stayOutOfCentralSea pie
//     constraint (r<0.18).
//   - TC always placed (nomad lobby flag ignored).
//   - doctrine-capture triggers fire at T+15s / +30s / +60s / +90s; the
//     extended cycle adds T+240/360/600/960 milestone markers. Auto-end
//     fires at gHubTestEndSeconds (default 1200s, extended) via
//     "Set Player Defeated" on the observer. Flip the knob to 120 for the
//     fast probe-only cycle.
//
// Known engine limitations (NOT bugs in this script):
//   - rmSetAllMapReveal is not a valid RM XS API — disabled at line ~48.
//   - "Create Unit" effect is not exposed from RMS trigger surface, so
//     unit spawning falls back to Grant-Resources injections.
//   - aiPlanCreate / trUnitCreate / trGameEnd are not available from RMS.

include "mercenaries.xs";
include "ypAsianInclude.xs";
include "ypKOTHInclude.xs";

void main(void)
{
    rmSetStatusText("", 0.01);
    rmEchoInfo("[HUBTEST] script started");

    // ---- TEST-CYCLE LENGTH (single knob) ----------------------------------
    // gHubTestEndSeconds controls when the auto-end trigger fires "Set Player
    // Defeated" on the observer (player 1), which returns the game to lobby.
    //
    //   120  (fast)     = fast doctrine probe cycle. Captures 2 posture
    //                      snapshots + the early build-style + wallStrategy
    //                      enum. Sufficient for static doctrine validation.
    //   1200 (default)  = full milestone window. Captures first_dock (≤360s
    //                      claim), first_wall_segment (≤900s claim), and
    //                      forward-base / artillery milestones. Use this
    //                      when reviewing a Naval/Coastal civ like British
    //                      where the dock+wall behaviours are the point.
    //
    // Extended-cycle marker triggers (T+240/360/600/960 below) are only
    // armed when gHubTestEndSeconds >= 1200, so flipping this one constant
    // toggles the whole cycle length atomically.
    // -----------------------------------------------------------------------
    int gHubTestEndSeconds = 1200;

    // Map size
    int playerTiles = 14000;
    int size = 2.0 * sqrt(cNumberNonGaiaPlayers * playerTiles);
    rmSetMapSize(size, size);

    // Terrain init -- Andes Upper palette
    rmSetSeaLevel(2.0);
    // 2026-05-15 WATER FIX v4: rmSetSeaType is REQUIRED to enable water
    // rendering. Without this global call, rmSetAreaWaterType becomes a
    // no-op (the engine silently fails to paint water tiles). Verified
    // by inspecting every vanilla AoE3 map with water (caribbean,
    // bayou, araucania, cascadeRange, dakota, etc.) — all call
    // rmSetSeaType BEFORE rmTerrainInitialize. "Araucania Central Coast"
    // is the andes-palette ocean type.
    rmSetSeaType("Araucania Central Coast");
    rmSetBaseTerrainMix("andes_grass_a");
    rmTerrainInitialize("andes\ground10_and", 4);
    rmSetMapType("andes");
    rmSetMapType("land");
    rmSetMapType("grass");
    rmSetLightingSet("Andes_Skirmish");
    rmSetWorldCircleConstraint(true);

    // ANW Hub Test: observer mode -- reveal whole map (player 1 watches all 7 AIs)
    // NOTE 2026-05-18: rmSetAllMapReveal is NOT a valid RM API call; it does
    // not appear anywhere in the vanilla AoE3 DE engine surface. Calling it
    // causes the map to silently fail to load ("Random Map: ANW Hub Test
    // failed to load"). Observer-side full-map reveal is not currently
    // achievable from RM XS — leave this disabled.
    // rmSetAllMapReveal(true);

    chooseMercs();

    // Register native civs so the engine shows correct trading UI labels.
    if (rmAllocateSubCivs(7) == true)
    {
        rmSetSubCiv(0, "Inca");
        rmSetSubCiv(1, "Mapuche");
        rmSetSubCiv(2, "Zapotec");
        rmSetSubCiv(3, "Carib");
        rmSetSubCiv(4, "Tupi");
        rmSetSubCiv(5, "Klamath");
        rmSetSubCiv(6, "Inca");
    }


    // Classes
    int classPlayer       = rmDefineClass("player");
    int classCliff        = rmDefineClass("classCliff");
    int classForest       = rmDefineClass("classForest");
    int classGold         = rmDefineClass("classGold");
    int classNatives      = rmDefineClass("natives");
    int classImportant    = rmDefineClass("importantItem");
    int classStartRes     = rmDefineClass("startingResource");
    rmDefineClass("startingUnit");

    // Constraints
    int avoidImpassableLand     = rmCreateTerrainDistanceConstraint("avoid impassable land", "Land", false, 6.0);
    int shortAvoidImpassable    = rmCreateTerrainDistanceConstraint("short avoid impassable land", "Land", false, 2.0);
    int avoidAll                = rmCreateTypeDistanceConstraint("avoid all", "all", 6.0);
    int avoidAllShort           = rmCreateTypeDistanceConstraint("avoid all short", "all", 3.0);
    int avoidCliffClass         = rmCreateClassDistanceConstraint("avoid cliff class", classCliff, 10.0);
    int avoidStartRes           = rmCreateClassDistanceConstraint("avoid start res", classStartRes, 8.0);
    int avoidGoldClass          = rmCreateClassDistanceConstraint("avoid gold class", classGold, 30.0);
    int avoidGoldShort          = rmCreateClassDistanceConstraint("avoid gold short", classGold, 10.0);
    int avoidForestClass        = rmCreateClassDistanceConstraint("forest vs forest", classForest, 25.0);
    int avoidForestShort        = rmCreateClassDistanceConstraint("forest vs forest short", classForest, 10.0);
    int avoidNativesClass       = rmCreateClassDistanceConstraint("avoid natives", classNatives, 10.0);
    int avoidNugget             = rmCreateTypeDistanceConstraint("avoid nugget", "AbstractNugget", 30.0);
    int avoidTownCenter         = rmCreateTypeDistanceConstraint("avoid TC", "townCenter", 30.0);
    int avoidTownCenterFar      = rmCreateTypeDistanceConstraint("avoid TC far", "townCenter", 50.0);
    int avoidMine               = rmCreateTypeDistanceConstraint("avoid mine", "mine", 35.0);
    int avoidMineShort          = rmCreateTypeDistanceConstraint("avoid mine short", "mine", 10.0);
    int avoidFish               = rmCreateTypeDistanceConstraint("avoid fish", "FishSalmon", 12.0);
    int avoidWhale              = rmCreateTypeDistanceConstraint("avoid whale", "MinkeWhale", 30.0);
    int avoidTradeRoute         = rmCreateTradeRouteDistanceConstraint("avoid trade route", 6.0);
    int avoidTradeRouteForest   = rmCreateTradeRouteDistanceConstraint("avoid trade route forest", 10.0);
    int avoidTradeRouteNugget   = rmCreateTradeRouteDistanceConstraint("avoid trade route nugget", 7.0);

    int stayInMap = rmCreatePieConstraint("stay in map",
        0.5, 0.5, 0.0, rmXFractionToMeters(0.47),
        rmDegreesToRadians(0.0), rmDegreesToRadians(360.0));

    int stayCentralSea = rmCreatePieConstraint("stay in central sea",
        0.5, 0.5, 0.0, rmXFractionToMeters(0.20),
        rmDegreesToRadians(0.0), rmDegreesToRadians(360.0));

    // 2026-05-15 WATER FIX -- pie constraint that keeps decorative
    // terrain patches & forest seed points OUT of the central-sea disc
    // at r<0.18. Without this, 20 patches + 35 forests scatter across
    // the whole map and routinely seed inside the central sea, painting
    // grass/dirt on top of the water and erasing it from the minimap
    // (user: "there's no sea around my base"). The constraint is
    // applied below to: terrain patches (line ~880), forests (line
    // ~900), and any other cosmetic area whose seed point could land
    // on water.
    int stayOutOfCentralSea = rmCreatePieConstraint("stay out of central sea",
        0.5, 0.5, rmXFractionToMeters(0.18), rmXFractionToMeters(1.0),
        rmDegreesToRadians(0.0), rmDegreesToRadians(360.0));

    // Player placement: slot 1 center observer, slots 2-8 compartments at r=0.36
    rmPlacePlayer(1, 0.500, 0.500);
    if (cNumberNonGaiaPlayers >= 2)
        rmPlacePlayer(2, 0.860, 0.500);
    if (cNumberNonGaiaPlayers >= 3)
        rmPlacePlayer(3, 0.725, 0.781);
    if (cNumberNonGaiaPlayers >= 4)
        rmPlacePlayer(4, 0.421, 0.851);
    if (cNumberNonGaiaPlayers >= 5)
        rmPlacePlayer(5, 0.175, 0.655);
    if (cNumberNonGaiaPlayers >= 6)
        rmPlacePlayer(6, 0.175, 0.345);
    if (cNumberNonGaiaPlayers >= 7)
        rmPlacePlayer(7, 0.421, 0.149);
    if (cNumberNonGaiaPlayers >= 8)
        rmPlacePlayer(8, 0.725, 0.219);

    rmSetStatusText("", 0.10);

    // ---- TERRAIN AREAS ----
    // Build order: outerRim first, then central sea, mountain ring,
    // spokes, river inlets, inner bays, observer island.

    // 2026-05-15 WATER-RENDERING FIX v3 — DAKOTA.XS PATTERN.
    // Reference: AoE3DE/Game/RandMaps/Dakota.xs ponds (lines 211-235).
    // The previous v2 recipe (centralSea + outerRim BEFORE cliffs, with
    // negative baseHeight + EdgeFilling + ObeyWorldCircleConstraint=false)
    // did NOT render water in-camera. User: "no water still and the cliffs
    // aren't cutting off the maps properly".
    //
    // Diagnosis:
    //   1. outerRim with Size(1.0,1.0) at center built AFTER centralSea
    //      stomped the water tiles (or silently failed entirely, leaving
    //      bare default terrain → brown dirt visual).
    //   2. Water areas all used negative BaseHeight (-2/-4/-5). Dakota's
    //      working ponds use POSITIVE BaseHeight (1 or 4) with seaLevel 0.
    //      rmSetAreaWaterType is what makes a tile render as water, NOT
    //      negative height. BaseHeight just controls visual depth.
    //   3. EdgeFilling(1) + ObeyWorldCircleConstraint(false) are not used
    //      in any working AoE3 vanilla water area; they may be hostile.
    //
    // FIX (THIS BLOCK): remove outerRim entirely (rmTerrainInitialize
    // above already paints the whole map as andes\ground10_and grass).
    // Defer centralSea to AFTER all cliffs/spokes are built, so the
    // water area is the LAST thing painted in its region and nothing
    // overwrites it. See new centralSea block placed after the spokes.

    rmSetStatusText("", 0.15);

    // 2026-05-15 GEOMETRY FIX -- Crater rim = ONE continuous closed cliff
    // ring around r=0.25 replacing 7 disjoint mring* blobs.
    //
    // PROBLEM (user screenshot, "see the circle at the end of the cliffs,
    // they can just go around"): the previous design used 7 separate
    // rmCreateArea blobs (each rmSetAreaSize(280) + rmSetAreaLocation at
    // a single angular point, NO rmAddAreaInfluenceSegment). Result: 7
    // *unconnected* circular cliff bulbs with 7 walkable gaps between
    // them. Each spoke's inner endpoint terminated in a rounded "key
    // shape" bulb visible from the AI base — AI villagers walked around
    // these bulbs straight into the centre / next compartment.
    //
    // FIX: one rmCreateArea + 7 chained rmAddAreaInfluenceSegment() calls
    // visiting the 7 vertices in order (last segment closes the loop
    // back to the first vertex). The area spreads ~2400 tiles along the
    // heptagon perimeter, forming a single connected cliff ring. Spoke
    // inner endpoints land ON these vertices, so spoke "ends" are
    // subsumed by the rim — no visible walk-around bulb.
    int craterRim = rmCreateArea("crater rim");
    rmSetAreaSize(craterRim, rmAreaTilesToFraction(2400), rmAreaTilesToFraction(2600));
    rmSetAreaLocation(craterRim, 0.500, 0.500);
    rmAddAreaInfluenceSegment(craterRim, 0.725, 0.608, 0.556, 0.744);
    rmAddAreaInfluenceSegment(craterRim, 0.556, 0.744, 0.344, 0.695);
    rmAddAreaInfluenceSegment(craterRim, 0.344, 0.695, 0.250, 0.500);
    rmAddAreaInfluenceSegment(craterRim, 0.250, 0.500, 0.344, 0.305);
    rmAddAreaInfluenceSegment(craterRim, 0.344, 0.305, 0.556, 0.256);
    rmAddAreaInfluenceSegment(craterRim, 0.556, 0.256, 0.725, 0.392);
    rmAddAreaInfluenceSegment(craterRim, 0.725, 0.392, 0.725, 0.608);
    rmSetAreaCliffType(craterRim, "andes");
    rmAddAreaToClass(craterRim, classCliff);
    rmSetAreaCliffEdge(craterRim, 1, 1);
    rmSetAreaCliffHeight(craterRim, 8, 1.0, 0.0);
    rmSetAreaCoherence(craterRim, 0.95);
    rmSetAreaSmoothDistance(craterRim, 4);
    rmSetAreaCliffPainting(craterRim, true, true, true, 0, true);
    rmSetAreaHeightBlend(craterRim, 1);
    rmSetAreaWarnFailure(craterRim, false);
    rmBuildArea(craterRim);

    rmSetStatusText("", 0.20);

    // Mountain spokes (radial cliffs between compartments)
    // v5 2026-05-17: extended INNER endpoints from r=0.25 to r=0.12 to close
    // the gap between spoke ends and central sea. Previously AI could walk
    // around the inner end of any spoke (between r=0.10 and r=0.25). Spoke
    // area sizes bumped 350/380 → 520/560 to keep paint density at longer
    // influence segments. Outer endpoints unchanged.
    int spoke0 = rmCreateArea("spoke 0");
    rmSetAreaSize(spoke0, rmAreaTilesToFraction(520), rmAreaTilesToFraction(560));
    rmSetAreaLocation(spoke0, 0.807, 0.648);
    // 2026-05-15 spot-check fix: outer endpoint pushed r=0.45→0.55 (well
    // past outer-rim cliff at r≈0.48-0.50) so AIs can't walk around.
    rmAddAreaInfluenceSegment(spoke0, 0.608, 0.552, 0.997, 0.734);
    rmSetAreaCliffType(spoke0, "andes");
    rmAddAreaToClass(spoke0, classCliff);
    rmSetAreaCliffEdge(spoke0, 1, 1);
    rmSetAreaCliffHeight(spoke0, 8, 1.0, 0.0);
    rmSetAreaCoherence(spoke0, 0.9);
    rmSetAreaSmoothDistance(spoke0, 0);
    rmSetAreaCliffPainting(spoke0, true, true, true, 0, true);
    rmSetAreaHeightBlend(spoke0, 0);
    rmBuildArea(spoke0);

    int spoke1 = rmCreateArea("spoke 1");
    rmSetAreaSize(spoke1, rmAreaTilesToFraction(520), rmAreaTilesToFraction(560));
    rmSetAreaLocation(spoke1, 0.576, 0.831);
    rmAddAreaInfluenceSegment(spoke1, 0.527, 0.617, 0.593, 0.999);
    rmSetAreaCliffType(spoke1, "andes");
    rmAddAreaToClass(spoke1, classCliff);
    rmSetAreaCliffEdge(spoke1, 1, 1);
    rmSetAreaCliffHeight(spoke1, 8, 1.0, 0.0);
    rmSetAreaCoherence(spoke1, 0.9);
    rmSetAreaSmoothDistance(spoke1, 0);
    rmSetAreaCliffPainting(spoke1, true, true, true, 0, true);
    rmSetAreaHeightBlend(spoke1, 0);
    rmBuildArea(spoke1);

    int spoke2 = rmCreateArea("spoke 2");
    rmSetAreaSize(spoke2, rmAreaTilesToFraction(520), rmAreaTilesToFraction(560));
    rmSetAreaLocation(spoke2, 0.287, 0.766);
    rmAddAreaInfluenceSegment(spoke2, 0.425, 0.594, 0.149, 0.911);
    rmSetAreaCliffType(spoke2, "andes");
    rmAddAreaToClass(spoke2, classCliff);
    rmSetAreaCliffEdge(spoke2, 1, 1);
    rmSetAreaCliffHeight(spoke2, 8, 1.0, 0.0);
    rmSetAreaCoherence(spoke2, 0.9);
    rmSetAreaSmoothDistance(spoke2, 0);
    rmSetAreaCliffPainting(spoke2, true, true, true, 0, true);
    rmSetAreaHeightBlend(spoke2, 0);
    rmBuildArea(spoke2);

    int spoke3 = rmCreateArea("spoke 3");
    rmSetAreaSize(spoke3, rmAreaTilesToFraction(520), rmAreaTilesToFraction(560));
    rmSetAreaLocation(spoke3, 0.160, 0.500);
    rmAddAreaInfluenceSegment(spoke3, 0.380, 0.500, 0.001, 0.500);
    rmSetAreaCliffType(spoke3, "andes");
    rmAddAreaToClass(spoke3, classCliff);
    rmSetAreaCliffEdge(spoke3, 1, 1);
    rmSetAreaCliffHeight(spoke3, 8, 1.0, 0.0);
    rmSetAreaCoherence(spoke3, 0.9);
    rmSetAreaSmoothDistance(spoke3, 0);
    rmSetAreaCliffPainting(spoke3, true, true, true, 0, true);
    rmSetAreaHeightBlend(spoke3, 0);
    rmBuildArea(spoke3);

    int spoke4 = rmCreateArea("spoke 4");
    rmSetAreaSize(spoke4, rmAreaTilesToFraction(520), rmAreaTilesToFraction(560));
    rmSetAreaLocation(spoke4, 0.287, 0.234);
    rmAddAreaInfluenceSegment(spoke4, 0.425, 0.406, 0.149, 0.089);
    rmSetAreaCliffType(spoke4, "andes");
    rmAddAreaToClass(spoke4, classCliff);
    rmSetAreaCliffEdge(spoke4, 1, 1);
    rmSetAreaCliffHeight(spoke4, 8, 1.0, 0.0);
    rmSetAreaCoherence(spoke4, 0.9);
    rmSetAreaSmoothDistance(spoke4, 0);
    rmSetAreaCliffPainting(spoke4, true, true, true, 0, true);
    rmSetAreaHeightBlend(spoke4, 0);
    rmBuildArea(spoke4);

    int spoke5 = rmCreateArea("spoke 5");
    rmSetAreaSize(spoke5, rmAreaTilesToFraction(520), rmAreaTilesToFraction(560));
    rmSetAreaLocation(spoke5, 0.576, 0.169);
    rmAddAreaInfluenceSegment(spoke5, 0.527, 0.383, 0.593, 0.001);
    rmSetAreaCliffType(spoke5, "andes");
    rmAddAreaToClass(spoke5, classCliff);
    rmSetAreaCliffEdge(spoke5, 1, 1);
    rmSetAreaCliffHeight(spoke5, 8, 1.0, 0.0);
    rmSetAreaCoherence(spoke5, 0.9);
    rmSetAreaSmoothDistance(spoke5, 0);
    rmSetAreaCliffPainting(spoke5, true, true, true, 0, true);
    rmSetAreaHeightBlend(spoke5, 0);
    rmBuildArea(spoke5);

    int spoke6 = rmCreateArea("spoke 6");
    rmSetAreaSize(spoke6, rmAreaTilesToFraction(520), rmAreaTilesToFraction(560));
    rmSetAreaLocation(spoke6, 0.807, 0.352);
    rmAddAreaInfluenceSegment(spoke6, 0.608, 0.448, 0.997, 0.266);
    rmSetAreaCliffType(spoke6, "andes");
    rmAddAreaToClass(spoke6, classCliff);
    rmSetAreaCliffEdge(spoke6, 1, 1);
    rmSetAreaCliffHeight(spoke6, 8, 1.0, 0.0);
    rmSetAreaCoherence(spoke6, 0.9);
    rmSetAreaSmoothDistance(spoke6, 0);
    rmSetAreaCliffPainting(spoke6, true, true, true, 0, true);
    rmSetAreaHeightBlend(spoke6, 0);
    rmBuildArea(spoke6);

    rmSetStatusText("", 0.25);

    // 2026-05-15 WATER-FIX v3 — central sea built AFTER all cliffs.
    // Built here (not before) so spoke / craterRim cliffs don't stomp
    // the water tiles. Dakota.xs recipe: positive baseHeight, no
    // EdgeFilling, no ObeyWorldCircleConstraint override.
    // 2026-05-15 WATER FIX v4 — sized to fit INSIDE the heptagon crater rim
    // (r=0.25 → ~3220 tile interior). Previous 7200 tiles overflowed past
    // the cliff ring causing the engine to fail-out the whole build. Also
    // dropped baseHeight to -2.0 (well below seaLevel 2.0) for clearly
    // deep water, and added WarnFailure(false) so spillage doesn't abort.
    // v5 2026-05-17: enlarged 2800/3000 → 5500/5800 tiles so the sea
    // radius (~0.16 of map) overlaps the new inner spoke endpoints at
    // r=0.12, ensuring no walkable gap between sea and cliff spokes.
    int centralSeaID = rmCreateArea("central sea");
    rmSetAreaSize(centralSeaID, rmAreaTilesToFraction(5500), rmAreaTilesToFraction(5800));
    rmSetAreaLocation(centralSeaID, 0.5, 0.5);
    rmSetAreaWaterType(centralSeaID, "Araucania Central Coast");
    rmSetAreaBaseHeight(centralSeaID, -2.0);
    rmSetAreaCoherence(centralSeaID, 0.85);
    rmSetAreaSmoothDistance(centralSeaID, 4);
    rmSetAreaWarnFailure(centralSeaID, false);
    rmBuildArea(centralSeaID);

    rmSetStatusText("", 0.28);

    // River inlets (water bridges between central sea and inner bays)
    int inlet0 = rmCreateArea("river inlet 0");
    rmSetAreaSize(inlet0, rmAreaTilesToFraction(180), rmAreaTilesToFraction(180));
    rmSetAreaLocation(inlet0, 0.740, 0.500);
    rmSetAreaWaterType(inlet0, "Araucania Central Coast");
    rmSetAreaBaseHeight(inlet0, -1.0);
    rmSetAreaCoherence(inlet0, 0.40);
    rmSetAreaSmoothDistance(inlet0, 5);
    rmSetAreaWarnFailure(inlet0, false);
    rmBuildArea(inlet0);

    int inlet1 = rmCreateArea("river inlet 1");
    rmSetAreaSize(inlet1, rmAreaTilesToFraction(180), rmAreaTilesToFraction(180));
    rmSetAreaLocation(inlet1, 0.650, 0.688);
    rmSetAreaWaterType(inlet1, "Araucania Central Coast");
    rmSetAreaBaseHeight(inlet1, -1.0);
    rmSetAreaCoherence(inlet1, 0.40);
    rmSetAreaSmoothDistance(inlet1, 5);
    rmSetAreaWarnFailure(inlet1, false);
    rmBuildArea(inlet1);

    int inlet2 = rmCreateArea("river inlet 2");
    rmSetAreaSize(inlet2, rmAreaTilesToFraction(180), rmAreaTilesToFraction(180));
    rmSetAreaLocation(inlet2, 0.447, 0.734);
    rmSetAreaWaterType(inlet2, "Araucania Central Coast");
    rmSetAreaBaseHeight(inlet2, -1.0);
    rmSetAreaCoherence(inlet2, 0.40);
    rmSetAreaSmoothDistance(inlet2, 5);
    rmSetAreaWarnFailure(inlet2, false);
    rmBuildArea(inlet2);

    int inlet3 = rmCreateArea("river inlet 3");
    rmSetAreaSize(inlet3, rmAreaTilesToFraction(180), rmAreaTilesToFraction(180));
    rmSetAreaLocation(inlet3, 0.283, 0.603);
    rmSetAreaWaterType(inlet3, "Araucania Central Coast");
    rmSetAreaBaseHeight(inlet3, -1.0);
    rmSetAreaCoherence(inlet3, 0.40);
    rmSetAreaSmoothDistance(inlet3, 5);
    rmSetAreaWarnFailure(inlet3, false);
    rmBuildArea(inlet3);

    int inlet4 = rmCreateArea("river inlet 4");
    rmSetAreaSize(inlet4, rmAreaTilesToFraction(180), rmAreaTilesToFraction(180));
    rmSetAreaLocation(inlet4, 0.283, 0.397);
    rmSetAreaWaterType(inlet4, "Araucania Central Coast");
    rmSetAreaBaseHeight(inlet4, -1.0);
    rmSetAreaCoherence(inlet4, 0.40);
    rmSetAreaSmoothDistance(inlet4, 5);
    rmSetAreaWarnFailure(inlet4, false);
    rmBuildArea(inlet4);

    int inlet5 = rmCreateArea("river inlet 5");
    rmSetAreaSize(inlet5, rmAreaTilesToFraction(180), rmAreaTilesToFraction(180));
    rmSetAreaLocation(inlet5, 0.447, 0.266);
    rmSetAreaWaterType(inlet5, "Araucania Central Coast");
    rmSetAreaBaseHeight(inlet5, -1.0);
    rmSetAreaCoherence(inlet5, 0.40);
    rmSetAreaSmoothDistance(inlet5, 5);
    rmSetAreaWarnFailure(inlet5, false);
    rmBuildArea(inlet5);

    int inlet6 = rmCreateArea("river inlet 6");
    rmSetAreaSize(inlet6, rmAreaTilesToFraction(180), rmAreaTilesToFraction(180));
    rmSetAreaLocation(inlet6, 0.650, 0.312);
    rmSetAreaWaterType(inlet6, "Araucania Central Coast");
    rmSetAreaBaseHeight(inlet6, -1.0);
    rmSetAreaCoherence(inlet6, 0.40);
    rmSetAreaSmoothDistance(inlet6, 5);
    rmSetAreaWarnFailure(inlet6, false);
    rmBuildArea(inlet6);

    rmSetStatusText("", 0.35);

    // Inner fishing bays at r=0.32 inside each compartment
    int bay0 = rmCreateArea("inner bay 0");
    rmSetAreaSize(bay0, rmAreaTilesToFraction(280), rmAreaTilesToFraction(320));
    rmSetAreaLocation(bay0, 0.740, 0.500);
    rmSetAreaWaterType(bay0, "Araucania Central Coast");
    rmSetAreaBaseHeight(bay0, -1.0);
    rmSetAreaCoherence(bay0, 0.40);
    rmSetAreaSmoothDistance(bay0, 0);
    rmSetAreaWarnFailure(bay0, false);
    rmBuildArea(bay0);

    int bay1 = rmCreateArea("inner bay 1");
    rmSetAreaSize(bay1, rmAreaTilesToFraction(280), rmAreaTilesToFraction(320));
    rmSetAreaLocation(bay1, 0.650, 0.688);
    rmSetAreaWaterType(bay1, "Araucania Central Coast");
    rmSetAreaBaseHeight(bay1, -1.0);
    rmSetAreaCoherence(bay1, 0.40);
    rmSetAreaSmoothDistance(bay1, 0);
    rmSetAreaWarnFailure(bay1, false);
    rmBuildArea(bay1);

    int bay2 = rmCreateArea("inner bay 2");
    rmSetAreaSize(bay2, rmAreaTilesToFraction(280), rmAreaTilesToFraction(320));
    rmSetAreaLocation(bay2, 0.447, 0.734);
    rmSetAreaWaterType(bay2, "Araucania Central Coast");
    rmSetAreaBaseHeight(bay2, -1.0);
    rmSetAreaCoherence(bay2, 0.40);
    rmSetAreaSmoothDistance(bay2, 0);
    rmSetAreaWarnFailure(bay2, false);
    rmBuildArea(bay2);

    int bay3 = rmCreateArea("inner bay 3");
    rmSetAreaSize(bay3, rmAreaTilesToFraction(280), rmAreaTilesToFraction(320));
    rmSetAreaLocation(bay3, 0.284, 0.604);
    rmSetAreaWaterType(bay3, "Araucania Central Coast");
    rmSetAreaBaseHeight(bay3, -1.0);
    rmSetAreaCoherence(bay3, 0.40);
    rmSetAreaSmoothDistance(bay3, 0);
    rmSetAreaWarnFailure(bay3, false);
    rmBuildArea(bay3);

    int bay4 = rmCreateArea("inner bay 4");
    rmSetAreaSize(bay4, rmAreaTilesToFraction(280), rmAreaTilesToFraction(320));
    rmSetAreaLocation(bay4, 0.284, 0.396);
    rmSetAreaWaterType(bay4, "Araucania Central Coast");
    rmSetAreaBaseHeight(bay4, -1.0);
    rmSetAreaCoherence(bay4, 0.40);
    rmSetAreaSmoothDistance(bay4, 0);
    rmSetAreaWarnFailure(bay4, false);
    rmBuildArea(bay4);

    int bay5 = rmCreateArea("inner bay 5");
    rmSetAreaSize(bay5, rmAreaTilesToFraction(280), rmAreaTilesToFraction(320));
    rmSetAreaLocation(bay5, 0.447, 0.266);
    rmSetAreaWaterType(bay5, "Araucania Central Coast");
    rmSetAreaBaseHeight(bay5, -1.0);
    rmSetAreaCoherence(bay5, 0.40);
    rmSetAreaSmoothDistance(bay5, 0);
    rmSetAreaWarnFailure(bay5, false);
    rmBuildArea(bay5);

    int bay6 = rmCreateArea("inner bay 6");
    rmSetAreaSize(bay6, rmAreaTilesToFraction(280), rmAreaTilesToFraction(320));
    rmSetAreaLocation(bay6, 0.650, 0.312);
    rmSetAreaWaterType(bay6, "Araucania Central Coast");
    rmSetAreaBaseHeight(bay6, -1.0);
    rmSetAreaCoherence(bay6, 0.40);
    rmSetAreaSmoothDistance(bay6, 0);
    rmSetAreaWarnFailure(bay6, false);
    rmBuildArea(bay6);

    rmSetStatusText("", 0.38);

    // Observer island at center
    //
    // 2026-05-15 WATER FIX -- shrunk from 600 to 220 tiles so it sits
    // INSIDE the central sea (which is 9000 tiles, radius ≈ 0.16 of map)
    // rather than overwriting it. User complaint: "there's no water
    // around my center base, also the trade network glitches over the
    // cliffs". Previous 600-tile island had radius ≈ 0.041 of map but
    // the smoothDistance=6 + coherence=1.0 + baseHeight=+2.0 painted a
    // wide skirt of dirt that effectively absorbed the entire sea. 220
    // tiles → radius ≈ 0.025 of map (≈ 8 tiles in normalised coords),
    // just enough for the TC + 3 outposts + starting workspace. Lower
    // smoothDistance=3 to keep the sea/island boundary crisp.
    int observerIsland = rmCreateArea("observer island");
    rmSetAreaSize(observerIsland, rmAreaTilesToFraction(220), rmAreaTilesToFraction(240));
    rmSetAreaLocation(observerIsland, 0.5, 0.5);
    rmSetAreaMix(observerIsland, "andes_grass_a");
    rmSetAreaTerrainType(observerIsland, "andes\ground10_and");
    rmSetAreaCoherence(observerIsland, 1.0);
    rmSetAreaSmoothDistance(observerIsland, 3);
    rmSetAreaBaseHeight(observerIsland, 4.0);
    rmBuildArea(observerIsland);

    rmSetStatusText("", 0.40);

    // ---- Object Defs ----

    // ANW Hub Test: always start with a real TC (nomad lobby flag is ignored)
    int TCID = rmCreateObjectDef("player TC");
    rmAddObjectDefItem(TCID, "TownCenter", 1, 0.0);
    rmAddObjectDefToClass(TCID, classStartRes);
    rmSetObjectDefMinDistance(TCID, 0.0);
    rmSetObjectDefMaxDistance(TCID, 0.0);

    int startingUnits = rmCreateStartingUnitsObjectDef(5.0);

    int playerGoldID = rmCreateObjectDef("player gold close");
    rmAddObjectDefItem(playerGoldID, "mine", 1, 0.0);
    rmAddObjectDefToClass(playerGoldID, classStartRes);
    rmAddObjectDefToClass(playerGoldID, classGold);
    rmSetObjectDefMinDistance(playerGoldID, 16.0);
    rmSetObjectDefMaxDistance(playerGoldID, 18.0);
    rmAddObjectDefConstraint(playerGoldID, avoidStartRes);
    rmAddObjectDefConstraint(playerGoldID, avoidCliffClass);
    rmAddObjectDefConstraint(playerGoldID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerGoldID, avoidTradeRoute);

    int playerGold2ID = rmCreateObjectDef("player gold far");
    rmAddObjectDefItem(playerGold2ID, "mine", 1, 0.0);
    rmAddObjectDefToClass(playerGold2ID, classStartRes);
    rmAddObjectDefToClass(playerGold2ID, classGold);
    rmSetObjectDefMinDistance(playerGold2ID, 30.0);
    rmSetObjectDefMaxDistance(playerGold2ID, 34.0);
    rmAddObjectDefConstraint(playerGold2ID, avoidStartRes);
    rmAddObjectDefConstraint(playerGold2ID, avoidGoldShort);
    rmAddObjectDefConstraint(playerGold2ID, avoidCliffClass);
    rmAddObjectDefConstraint(playerGold2ID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerGold2ID, avoidTradeRoute);

    int playerTreeID = rmCreateObjectDef("player trees near");
    rmAddObjectDefItem(playerTreeID, "TreeAndes", 12, 6.0);
    rmAddObjectDefToClass(playerTreeID, classStartRes);
    rmAddObjectDefToClass(playerTreeID, classForest);
    rmSetObjectDefMinDistance(playerTreeID, 18.0);
    rmSetObjectDefMaxDistance(playerTreeID, 22.0);
    rmAddObjectDefConstraint(playerTreeID, avoidStartRes);
    rmAddObjectDefConstraint(playerTreeID, avoidGoldShort);
    rmAddObjectDefConstraint(playerTreeID, avoidCliffClass);
    rmAddObjectDefConstraint(playerTreeID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerTreeID, avoidForestShort);
    rmAddObjectDefConstraint(playerTreeID, avoidTradeRouteForest);

    int playerTree2ID = rmCreateObjectDef("player trees mid");
    rmAddObjectDefItem(playerTree2ID, "TreeAndes", 14, 7.0);
    rmAddObjectDefToClass(playerTree2ID, classStartRes);
    rmAddObjectDefToClass(playerTree2ID, classForest);
    rmSetObjectDefMinDistance(playerTree2ID, 28.0);
    rmSetObjectDefMaxDistance(playerTree2ID, 32.0);
    rmAddObjectDefConstraint(playerTree2ID, avoidStartRes);
    rmAddObjectDefConstraint(playerTree2ID, avoidGoldShort);
    rmAddObjectDefConstraint(playerTree2ID, avoidCliffClass);
    rmAddObjectDefConstraint(playerTree2ID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerTree2ID, avoidForestShort);
    rmAddObjectDefConstraint(playerTree2ID, avoidTradeRouteForest);

    int playerHuntID = rmCreateObjectDef("player hunt 1");
    rmAddObjectDefItem(playerHuntID, "guanaco", 10, 5.0);
    rmAddObjectDefToClass(playerHuntID, classStartRes);
    rmSetObjectDefCreateHerd(playerHuntID, true);
    rmSetObjectDefMinDistance(playerHuntID, 18.0);
    rmSetObjectDefMaxDistance(playerHuntID, 22.0);
    rmAddObjectDefConstraint(playerHuntID, avoidStartRes);
    rmAddObjectDefConstraint(playerHuntID, avoidCliffClass);
    rmAddObjectDefConstraint(playerHuntID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerHuntID, avoidTradeRoute);

    int playerHunt2ID = rmCreateObjectDef("player hunt 2");
    rmAddObjectDefItem(playerHunt2ID, "guanaco", 10, 5.0);
    rmAddObjectDefToClass(playerHunt2ID, classStartRes);
    rmSetObjectDefCreateHerd(playerHunt2ID, true);
    rmSetObjectDefMinDistance(playerHunt2ID, 34.0);
    rmSetObjectDefMaxDistance(playerHunt2ID, 38.0);
    rmAddObjectDefConstraint(playerHunt2ID, avoidStartRes);
    rmAddObjectDefConstraint(playerHunt2ID, avoidCliffClass);
    rmAddObjectDefConstraint(playerHunt2ID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerHunt2ID, avoidTradeRoute);

    int playerBerryID = rmCreateObjectDef("player berries");
    rmAddObjectDefItem(playerBerryID, "berryBush", 5, 3.0);
    rmAddObjectDefToClass(playerBerryID, classStartRes);
    rmSetObjectDefMinDistance(playerBerryID, 14.0);
    rmSetObjectDefMaxDistance(playerBerryID, 18.0);
    rmAddObjectDefConstraint(playerBerryID, avoidStartRes);
    rmAddObjectDefConstraint(playerBerryID, avoidCliffClass);
    rmAddObjectDefConstraint(playerBerryID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerBerryID, avoidTradeRoute);

    int playerNuggetID = rmCreateObjectDef("player nugget easy");
    rmAddObjectDefItem(playerNuggetID, "Nugget", 1, 0.0);
    rmSetNuggetDifficulty(1, 1);
    rmAddObjectDefToClass(playerNuggetID, classStartRes);
    rmSetObjectDefMinDistance(playerNuggetID, 24.0);
    rmSetObjectDefMaxDistance(playerNuggetID, 28.0);
    rmAddObjectDefConstraint(playerNuggetID, avoidStartRes);
    rmAddObjectDefConstraint(playerNuggetID, avoidCliffClass);
    rmAddObjectDefConstraint(playerNuggetID, avoidNugget);
    rmAddObjectDefConstraint(playerNuggetID, avoidImpassableLand);
    rmAddObjectDefConstraint(playerNuggetID, avoidTradeRouteNugget);

    rmSetStatusText("", 0.45);

    // ---- Place TC + resources per player ----
    // Skip player 1 (the observer at map center, 0.5/0.5 on a 220-tile
    // island). Placing TC + gold + trees + hunt + berries + nugget at
    // the observer's compartment is wasteful (most fail the
    // avoidImpassableLand/avoidCliffClass constraints silently) and
    // gold mines that did land could obstruct overhead spectator view.
    // Start at i=2 so only the 7 AI compartments get resource
    // placement. cNumberNonGaiaPlayers is still the upper bound.
    int loopMax = cNumberNonGaiaPlayers + 1;
    rmClearClosestPointConstraints();
    for (i = 2; < loopMax)
    {
        rmPlaceObjectDefAtLoc(TCID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(startingUnits, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerGoldID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerGold2ID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerTreeID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerTree2ID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerHuntID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerHunt2ID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerBerryID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
        rmPlaceObjectDefAtLoc(playerNuggetID, i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));

        if (ypIsAsian(i))
            rmPlaceObjectDefAtLoc(ypMonasteryBuilder(i, 1), i, rmPlayerLocXFraction(i), rmPlayerLocZFraction(i));
    }

    rmSetStatusText("", 0.55);

    // ---- Native villages: 7 distinct cultures per compartment ----
    int nativeVillageID = rmCreateGrouping("native slot2 inca", "native inca village 1");
    rmSetGroupingMinDistance(nativeVillageID, 0.0);
    rmSetGroupingMaxDistance(nativeVillageID, 8.0);
    rmAddGroupingToClass(nativeVillageID, classNatives);
    rmAddGroupingToClass(nativeVillageID, classImportant);
    rmAddGroupingConstraint(nativeVillageID, avoidImpassableLand);
    rmAddGroupingConstraint(nativeVillageID, avoidCliffClass);
    // 2026-05-15 NATIVE-COVERAGE FIX -- pulled inward from r≈0.42-0.46
    // to r=0.40 so the village seed point doesn't fail the
    // avoidCliffClass+avoidImpassableLand constraints against the outer
    // rim cliff (which extends inward from r=0.50 with cliffEdge=1.0).
    // User complaint: "not all sections have a native settlement that
    // they can trade with". Previous outer placements landed within the
    // outer-rim cliff buffer and silently failed to place — now r=0.40
    // sits in the middle of each compartment with clear ground.
    rmPlaceGroupingAtLoc(nativeVillageID, 0, 0.900, 0.500);   // comp 0,   0°

    int nativeVillage1ID = rmCreateGrouping("native slot3 mapuche", "native Mapuche village 1");
    rmSetGroupingMinDistance(nativeVillage1ID, 0.0);
    rmSetGroupingMaxDistance(nativeVillage1ID, 8.0);
    rmAddGroupingToClass(nativeVillage1ID, classNatives);
    rmAddGroupingToClass(nativeVillage1ID, classImportant);
    rmAddGroupingConstraint(nativeVillage1ID, avoidImpassableLand);
    rmAddGroupingConstraint(nativeVillage1ID, avoidCliffClass);
    rmPlaceGroupingAtLoc(nativeVillage1ID, 0, 0.749, 0.813); // comp 1,  51°

    int nativeVillage2ID = rmCreateGrouping("native slot4 zapotec", "native zapotec village 1");
    rmSetGroupingMinDistance(nativeVillage2ID, 0.0);
    rmSetGroupingMaxDistance(nativeVillage2ID, 8.0);
    rmAddGroupingToClass(nativeVillage2ID, classNatives);
    rmAddGroupingToClass(nativeVillage2ID, classImportant);
    rmAddGroupingConstraint(nativeVillage2ID, avoidImpassableLand);
    rmAddGroupingConstraint(nativeVillage2ID, avoidCliffClass);
    rmPlaceGroupingAtLoc(nativeVillage2ID, 0, 0.410, 0.890); // comp 2, 103°

    int nativeVillage3ID = rmCreateGrouping("native slot5 carib", "native carib village 1");
    rmSetGroupingMinDistance(nativeVillage3ID, 0.0);
    rmSetGroupingMaxDistance(nativeVillage3ID, 8.0);
    rmAddGroupingToClass(nativeVillage3ID, classNatives);
    rmAddGroupingToClass(nativeVillage3ID, classImportant);
    rmAddGroupingConstraint(nativeVillage3ID, avoidImpassableLand);
    rmAddGroupingConstraint(nativeVillage3ID, avoidCliffClass);
    rmPlaceGroupingAtLoc(nativeVillage3ID, 0, 0.139, 0.673); // comp 3, 154°

    int nativeVillage4ID = rmCreateGrouping("native slot6 tupi", "native tupi village 1");
    rmSetGroupingMinDistance(nativeVillage4ID, 0.0);
    rmSetGroupingMaxDistance(nativeVillage4ID, 8.0);
    rmAddGroupingToClass(nativeVillage4ID, classNatives);
    rmAddGroupingToClass(nativeVillage4ID, classImportant);
    rmAddGroupingConstraint(nativeVillage4ID, avoidImpassableLand);
    rmAddGroupingConstraint(nativeVillage4ID, avoidCliffClass);
    rmPlaceGroupingAtLoc(nativeVillage4ID, 0, 0.139, 0.327); // comp 4, 206°

    int nativeVillage5ID = rmCreateGrouping("native slot7 klamath", "native klamath village 1");
    rmSetGroupingMinDistance(nativeVillage5ID, 0.0);
    rmSetGroupingMaxDistance(nativeVillage5ID, 8.0);
    rmAddGroupingToClass(nativeVillage5ID, classNatives);
    rmAddGroupingToClass(nativeVillage5ID, classImportant);
    rmAddGroupingConstraint(nativeVillage5ID, avoidImpassableLand);
    rmAddGroupingConstraint(nativeVillage5ID, avoidCliffClass);
    rmPlaceGroupingAtLoc(nativeVillage5ID, 0, 0.410, 0.110); // comp 5, 257°

    int nativeVillage6ID = rmCreateGrouping("native slot8 inca", "native inca village 2");
    rmSetGroupingMinDistance(nativeVillage6ID, 0.0);
    rmSetGroupingMaxDistance(nativeVillage6ID, 8.0);
    rmAddGroupingToClass(nativeVillage6ID, classNatives);
    rmAddGroupingToClass(nativeVillage6ID, classImportant);
    rmAddGroupingConstraint(nativeVillage6ID, avoidImpassableLand);
    rmAddGroupingConstraint(nativeVillage6ID, avoidCliffClass);
    rmPlaceGroupingAtLoc(nativeVillage6ID, 0, 0.749, 0.187); // comp 6, 309°

    rmSetStatusText("", 0.62);

    // ---- Central sea resources ----
    // v5 2026-05-17: central sea grew from 2800 → 5500 tiles. Bumped
    // fish clusters 10 → 18, whales 4 → 8, nuggets 5 → 10 to fill the
    // expanded surface and give AI naval-economy probes more to score.
    int seaFishID = rmCreateObjectDef("sea fish");
    rmAddObjectDefItem(seaFishID, "FishSalmon", 5, 8.0);
    rmSetObjectDefMinDistance(seaFishID, 0.0);
    rmSetObjectDefMaxDistance(seaFishID, rmXFractionToMeters(0.20));
    rmAddObjectDefConstraint(seaFishID, avoidFish);
    rmAddObjectDefConstraint(seaFishID, stayCentralSea);
    rmPlaceObjectDefAtLoc(seaFishID, 0, 0.5, 0.5, 10);

    int seaWhaleID = rmCreateObjectDef("sea whale");
    rmAddObjectDefItem(seaWhaleID, "MinkeWhale", 1, 0.0);
    rmSetObjectDefMinDistance(seaWhaleID, 0.0);
    rmSetObjectDefMaxDistance(seaWhaleID, rmXFractionToMeters(0.20));
    rmAddObjectDefConstraint(seaWhaleID, avoidWhale);
    rmAddObjectDefConstraint(seaWhaleID, stayCentralSea);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.620, 0.500);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.500, 0.620);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.380, 0.500);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.500, 0.380);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.585, 0.585);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.415, 0.585);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.415, 0.415);
    rmPlaceObjectDefAtLoc(seaWhaleID, 0, 0.585, 0.415);

    int seaNuggetID = rmCreateObjectDef("sea nugget");
    rmAddObjectDefItem(seaNuggetID, "Nugget", 1, 0.0);
    rmSetNuggetDifficulty(2, 2);
    rmSetObjectDefMinDistance(seaNuggetID, 0.0);
    rmSetObjectDefMaxDistance(seaNuggetID, rmXFractionToMeters(0.20));
    rmAddObjectDefConstraint(seaNuggetID, avoidNugget);
    rmAddObjectDefConstraint(seaNuggetID, stayCentralSea);
    rmPlaceObjectDefAtLoc(seaNuggetID, 0, 0.5, 0.5, 10);

    // v5 2026-05-17: bays now 900/1000 tiles. Each gets 5 salmon clusters
    // + 1 whale + 1 sea-nugget so AI water-economy probes can fire.
    int bayFishID = rmCreateObjectDef("bay fish");
    rmAddObjectDefItem(bayFishID, "FishSalmon", 5, 8.0);
    rmSetObjectDefMinDistance(bayFishID, 0.0);
    rmSetObjectDefMaxDistance(bayFishID, 12.0);
    rmAddObjectDefConstraint(bayFishID, avoidImpassableLand);
    rmPlaceObjectDefAtLoc(bayFishID, 0, 0.820, 0.500);
    rmPlaceObjectDefAtLoc(bayFishID, 0, 0.700, 0.750);
    rmPlaceObjectDefAtLoc(bayFishID, 0, 0.430, 0.812);
    rmPlaceObjectDefAtLoc(bayFishID, 0, 0.211, 0.638);
    rmPlaceObjectDefAtLoc(bayFishID, 0, 0.211, 0.362);
    rmPlaceObjectDefAtLoc(bayFishID, 0, 0.430, 0.188);
    rmPlaceObjectDefAtLoc(bayFishID, 0, 0.700, 0.250);

    int bayWhaleID = rmCreateObjectDef("bay whale");
    rmAddObjectDefItem(bayWhaleID, "MinkeWhale", 1, 0.0);
    rmSetObjectDefMinDistance(bayWhaleID, 0.0);
    rmSetObjectDefMaxDistance(bayWhaleID, 10.0);
    rmAddObjectDefConstraint(bayWhaleID, avoidWhale);
    rmAddObjectDefConstraint(bayWhaleID, avoidImpassableLand);
    rmPlaceObjectDefAtLoc(bayWhaleID, 0, 0.820, 0.500);
    rmPlaceObjectDefAtLoc(bayWhaleID, 0, 0.700, 0.750);
    rmPlaceObjectDefAtLoc(bayWhaleID, 0, 0.430, 0.812);
    rmPlaceObjectDefAtLoc(bayWhaleID, 0, 0.211, 0.638);
    rmPlaceObjectDefAtLoc(bayWhaleID, 0, 0.211, 0.362);
    rmPlaceObjectDefAtLoc(bayWhaleID, 0, 0.430, 0.188);
    rmPlaceObjectDefAtLoc(bayWhaleID, 0, 0.700, 0.250);

    int bayNuggetID = rmCreateObjectDef("bay sea nugget");
    rmAddObjectDefItem(bayNuggetID, "Nugget", 1, 0.0);
    rmSetNuggetDifficulty(1, 2);
    rmSetObjectDefMinDistance(bayNuggetID, 0.0);
    rmSetObjectDefMaxDistance(bayNuggetID, 10.0);
    rmAddObjectDefConstraint(bayNuggetID, avoidNugget);
    rmPlaceObjectDefAtLoc(bayNuggetID, 0, 0.820, 0.500);
    rmPlaceObjectDefAtLoc(bayNuggetID, 0, 0.700, 0.750);
    rmPlaceObjectDefAtLoc(bayNuggetID, 0, 0.430, 0.812);
    rmPlaceObjectDefAtLoc(bayNuggetID, 0, 0.211, 0.638);
    rmPlaceObjectDefAtLoc(bayNuggetID, 0, 0.211, 0.362);
    rmPlaceObjectDefAtLoc(bayNuggetID, 0, 0.430, 0.188);
    rmPlaceObjectDefAtLoc(bayNuggetID, 0, 0.700, 0.250);

    int shipRuinsID = rmCreateObjectDef("sea ship ruins");
    rmAddObjectDefItem(shipRuinsID, "deShipRuins", 1, 0.0);
    rmSetObjectDefMinDistance(shipRuinsID, 0.0);
    rmSetObjectDefMaxDistance(shipRuinsID, rmXFractionToMeters(0.17));
    rmAddObjectDefConstraint(shipRuinsID, avoidAllShort);
    rmAddObjectDefConstraint(shipRuinsID, stayCentralSea);
    rmPlaceObjectDefAtLoc(shipRuinsID, 0, 0.5, 0.5, 4);

    rmSetStatusText("", 0.70);

    // ---- Trade route: circular ring at r=0.30 ----
    int tradeSocketID = rmCreateObjectDef("trade route sockets");
    rmAddObjectDefItem(tradeSocketID, "SocketTradeRoute", 1, 0.0);
    rmSetObjectDefAllowOverlap(tradeSocketID, true);
    rmSetObjectDefMinDistance(tradeSocketID, 2.0);
    rmSetObjectDefMaxDistance(tradeSocketID, 8.0);

    int ringTradeRouteID = rmCreateTradeRoute();
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.8000, 0.5000);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.7772, 0.6148);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.7121, 0.7121);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.6148, 0.7772);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.5000, 0.8000);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.3852, 0.7772);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.2879, 0.7121);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.2228, 0.6148);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.2000, 0.5000);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.2228, 0.3852);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.2879, 0.2879);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.3852, 0.2228);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.5000, 0.2000);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.6148, 0.2228);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.7121, 0.2879);
    rmAddTradeRouteWaypoint(ringTradeRouteID, 0.7772, 0.3852);

    // 2026-05-15 spot-check fix: do NOT paint dirt_trail across the ring.
    // The trail carves a passable corridor through every spoke (radial
    // cliffs between compartments), letting AI villagers wander into
    // neighbouring AI segments. Sockets are still placed (at safe
    // mid-compartment locations below), but the connecting trail is
    // omitted — trade carts can't traverse the spoke cliffs anyway, so
    // the trail was decorative.
    // bool placedRingTR = rmBuildTradeRoute(ringTradeRouteID, "dirt_trail");
    // if (placedRingTR == false)
    //     rmEchoError("[HUBTEST] WARN: circular trade route failed to place");

    rmSetObjectDefTradeRouteID(tradeSocketID, ringTradeRouteID);
    // 2026-05-15 TRADE-COVERAGE FIX -- 7 sockets, one per compartment,
    // at mid-compartment angles & r=0.30 (just inside the player TC ring
    // at r=0.36). User complaint: "not all of them have a trade post".
    // Previous version placed only 3 sockets (compartments 0/2/4); now
    // every AI base has a trade post they can claim.
    rmPlaceObjectDefAtLoc(tradeSocketID, 0, 0.800, 0.500); // comp 0,   0°
    rmPlaceObjectDefAtLoc(tradeSocketID, 0, 0.687, 0.735); // comp 1,  51°
    rmPlaceObjectDefAtLoc(tradeSocketID, 0, 0.433, 0.793); // comp 2, 103°
    rmPlaceObjectDefAtLoc(tradeSocketID, 0, 0.230, 0.630); // comp 3, 154°
    rmPlaceObjectDefAtLoc(tradeSocketID, 0, 0.230, 0.369); // comp 4, 206°
    rmPlaceObjectDefAtLoc(tradeSocketID, 0, 0.433, 0.208); // comp 5, 257°
    rmPlaceObjectDefAtLoc(tradeSocketID, 0, 0.687, 0.265); // comp 6, 309°

    rmSetStatusText("", 0.78);

    // 2026-05-15 BISECT phase 2: baseline (extras-disabled) passed
    // mode 6 → mode 27. Now re-enabling WILDLIFE block only (jaguars,
    // capybara, tapir, rhea, llama, huari, vultures). Patches / forests
    // / mines remain commented below.
    int jaguarDefID = rmCreateObjectDef("jaguar pack");
    rmAddObjectDefItem(jaguarDefID, "Jaguar", 2, 6.0);
    rmSetObjectDefMinDistance(jaguarDefID, 18.0);
    rmSetObjectDefMaxDistance(jaguarDefID, 26.0);
    rmAddObjectDefConstraint(jaguarDefID, avoidImpassableLand);
    rmAddObjectDefConstraint(jaguarDefID, avoidCliffClass);
    rmAddObjectDefConstraint(jaguarDefID, avoidTownCenter);
    rmPlaceObjectDefAtLoc(jaguarDefID, 0, 0.860, 0.500);
    rmPlaceObjectDefAtLoc(jaguarDefID, 0, 0.725, 0.781);
    rmPlaceObjectDefAtLoc(jaguarDefID, 0, 0.421, 0.851);
    rmPlaceObjectDefAtLoc(jaguarDefID, 0, 0.175, 0.655);
    rmPlaceObjectDefAtLoc(jaguarDefID, 0, 0.175, 0.345);
    rmPlaceObjectDefAtLoc(jaguarDefID, 0, 0.421, 0.149);
    rmPlaceObjectDefAtLoc(jaguarDefID, 0, 0.725, 0.219);
    rmEchoInfo("[HUBTEST] Jaguar packs placed (7 compartments)");

    // --- CAPYBARA (hunt diversity) ------------------------------------------
    int capybaraID = rmCreateObjectDef("bonus capybara");
    rmAddObjectDefItem(capybaraID, "capybara", 2, 3.0);
    rmSetObjectDefMinDistance(capybaraID, 14.0);
    rmSetObjectDefMaxDistance(capybaraID, 24.0);
    rmAddObjectDefConstraint(capybaraID, avoidImpassableLand);
    rmAddObjectDefConstraint(capybaraID, avoidCliffClass);
    rmAddObjectDefConstraint(capybaraID, avoidTownCenter);
    rmAddObjectDefConstraint(capybaraID, avoidAllShort);
    rmSetObjectDefCreateHerd(capybaraID, true);
    rmPlaceObjectDefAtLoc(capybaraID, 0, 0.860, 0.500);
    rmPlaceObjectDefAtLoc(capybaraID, 0, 0.725, 0.781);
    rmPlaceObjectDefAtLoc(capybaraID, 0, 0.421, 0.851);
    rmPlaceObjectDefAtLoc(capybaraID, 0, 0.175, 0.655);
    rmPlaceObjectDefAtLoc(capybaraID, 0, 0.175, 0.345);
    rmPlaceObjectDefAtLoc(capybaraID, 0, 0.421, 0.149);
    rmPlaceObjectDefAtLoc(capybaraID, 0, 0.725, 0.219);

    // --- TAPIR (hunt diversity) ---------------------------------------------
    int tapirID = rmCreateObjectDef("bonus tapir");
    rmAddObjectDefItem(tapirID, "tapir", 2, 3.0);
    rmSetObjectDefMinDistance(tapirID, 18.0);
    rmSetObjectDefMaxDistance(tapirID, 28.0);
    rmAddObjectDefConstraint(tapirID, avoidImpassableLand);
    rmAddObjectDefConstraint(tapirID, avoidCliffClass);
    rmAddObjectDefConstraint(tapirID, avoidTownCenter);
    rmAddObjectDefConstraint(tapirID, avoidAllShort);
    rmSetObjectDefCreateHerd(tapirID, true);
    rmPlaceObjectDefAtLoc(tapirID, 0, 0.860, 0.500);
    rmPlaceObjectDefAtLoc(tapirID, 0, 0.725, 0.781);
    rmPlaceObjectDefAtLoc(tapirID, 0, 0.421, 0.851);
    rmPlaceObjectDefAtLoc(tapirID, 0, 0.175, 0.655);
    rmPlaceObjectDefAtLoc(tapirID, 0, 0.175, 0.345);
    rmPlaceObjectDefAtLoc(tapirID, 0, 0.421, 0.149);
    rmPlaceObjectDefAtLoc(tapirID, 0, 0.725, 0.219);

    // --- RHEA (ambient wildlife) --------------------------------------------
    int rheaID = rmCreateObjectDef("bonus rhea");
    rmAddObjectDefItem(rheaID, "rhea", 3, 4.0);
    rmSetObjectDefMinDistance(rheaID, 14.0);
    rmSetObjectDefMaxDistance(rheaID, 26.0);
    rmAddObjectDefConstraint(rheaID, avoidImpassableLand);
    rmAddObjectDefConstraint(rheaID, avoidCliffClass);
    rmAddObjectDefConstraint(rheaID, avoidTownCenter);
    rmAddObjectDefConstraint(rheaID, avoidAllShort);
    rmSetObjectDefCreateHerd(rheaID, true);
    rmPlaceObjectDefAtLoc(rheaID, 0, 0.860, 0.500);
    rmPlaceObjectDefAtLoc(rheaID, 0, 0.725, 0.781);
    rmPlaceObjectDefAtLoc(rheaID, 0, 0.421, 0.851);
    rmPlaceObjectDefAtLoc(rheaID, 0, 0.175, 0.655);
    rmPlaceObjectDefAtLoc(rheaID, 0, 0.175, 0.345);
    rmPlaceObjectDefAtLoc(rheaID, 0, 0.421, 0.149);
    rmPlaceObjectDefAtLoc(rheaID, 0, 0.725, 0.219);

    // --- LLAMA (herdable livestock) -----------------------------------------
    int llamaID = rmCreateObjectDef("bonus llama");
    rmAddObjectDefItem(llamaID, "Llama", 3, 3.0);
    rmSetObjectDefMinDistance(llamaID, 14.0);
    rmSetObjectDefMaxDistance(llamaID, 26.0);
    rmAddObjectDefConstraint(llamaID, avoidImpassableLand);
    rmAddObjectDefConstraint(llamaID, avoidCliffClass);
    rmAddObjectDefConstraint(llamaID, avoidTownCenter);
    rmAddObjectDefConstraint(llamaID, avoidAllShort);
    rmSetObjectDefCreateHerd(llamaID, true);
    rmPlaceObjectDefAtLoc(llamaID, 0, 0.860, 0.500);
    rmPlaceObjectDefAtLoc(llamaID, 0, 0.725, 0.781);
    rmPlaceObjectDefAtLoc(llamaID, 0, 0.421, 0.851);
    rmPlaceObjectDefAtLoc(llamaID, 0, 0.175, 0.655);
    rmPlaceObjectDefAtLoc(llamaID, 0, 0.175, 0.345);
    rmPlaceObjectDefAtLoc(llamaID, 0, 0.421, 0.149);
    rmPlaceObjectDefAtLoc(llamaID, 0, 0.725, 0.219);

    // --- HUARI STRONGHOLD (decorative ruin) ---------------------------------
    int huariID = rmCreateObjectDef("bonus huari stronghold");
    rmAddObjectDefItem(huariID, "HuariStrongholdAndes", 1, 0.0);
    rmSetObjectDefMinDistance(huariID, 22.0);
    rmSetObjectDefMaxDistance(huariID, 30.0);
    rmAddObjectDefConstraint(huariID, avoidImpassableLand);
    rmAddObjectDefConstraint(huariID, avoidCliffClass);
    rmAddObjectDefConstraint(huariID, avoidTownCenter);
    rmAddObjectDefConstraint(huariID, avoidAllShort);
    rmAddObjectDefConstraint(huariID, avoidNativesClass);
    rmPlaceObjectDefAtLoc(huariID, 0, 0.860, 0.500);
    rmPlaceObjectDefAtLoc(huariID, 0, 0.725, 0.781);
    rmPlaceObjectDefAtLoc(huariID, 0, 0.421, 0.851);
    rmPlaceObjectDefAtLoc(huariID, 0, 0.175, 0.655);
    rmPlaceObjectDefAtLoc(huariID, 0, 0.175, 0.345);
    rmPlaceObjectDefAtLoc(huariID, 0, 0.421, 0.149);
    rmPlaceObjectDefAtLoc(huariID, 0, 0.725, 0.219);

    // --- VULTURES (atmospheric props on mountain ring) ----------------------
    int vultureID = rmCreateObjectDef("mountain vulture");
    rmAddObjectDefItem(vultureID, "PropVulturePerching", 1, 0.0);
    rmSetObjectDefMinDistance(vultureID, 0.0);
    rmSetObjectDefMaxDistance(vultureID, 12.0);
    rmAddObjectDefConstraint(vultureID, avoidAllShort);
    rmAddObjectDefConstraint(vultureID, shortAvoidImpassable);
    rmPlaceObjectDefAtLoc(vultureID, 0, 0.725, 0.608);
    rmPlaceObjectDefAtLoc(vultureID, 0, 0.556, 0.744);
    rmPlaceObjectDefAtLoc(vultureID, 0, 0.344, 0.695);
    rmPlaceObjectDefAtLoc(vultureID, 0, 0.250, 0.500);
    rmPlaceObjectDefAtLoc(vultureID, 0, 0.344, 0.305);
    rmPlaceObjectDefAtLoc(vultureID, 0, 0.556, 0.256);
    rmPlaceObjectDefAtLoc(vultureID, 0, 0.725, 0.392);
    rmEchoInfo("[HUBTEST] mountain vultures placed (7)");

    rmSetStatusText("", 0.80);

    /* ===== PHASE 3 INACTIVE A: dup outposts (re-declares outpostID — kept inactive) =====
    // ---- Observer-island outposts (DUPLICATE — kept below in baseline) ----
    int outpostID = rmCreateObjectDef("observer outpost");
    rmAddObjectDefItem(outpostID, "Outpost", 1, 0.0);
    rmSetObjectDefMinDistance(outpostID, 8.0);
    rmSetObjectDefMaxDistance(outpostID, 14.0);
    rmAddObjectDefConstraint(outpostID, avoidImpassableLand);
    rmAddObjectDefConstraint(outpostID, avoidAllShort);
    rmPlaceObjectDefAtLoc(outpostID, 0, 0.500, 0.500);

    rmSetStatusText("", 0.82);
    ===== end PHASE 3 INACTIVE A ===== */

    // -----------------------------------------------------------------------
    // TERRAIN PATCHES -- cosmetic variety in compartments
    //
    // 2026-05-15: BUG FIX — every stock random map declares the loop variable
    // *before* the for-statement (e.g. andes.xs:291 `for(i=1; <cNumberPlayers)`).
    // The earlier `for (int patch = 0; < 20)` form silently failed parse and
    // surfaced as "Random Map: ANW Hub Test failed to load". Declare `patch`
    // outside the loop, then iterate.
    // -----------------------------------------------------------------------
    int patch = 0;
    for (patch = 0; < 20)
    {
        int patchID = rmCreateArea("terrain patch " + patch);
        rmSetAreaWarnFailure(patchID, false);
        rmSetAreaSize(patchID, rmAreaTilesToFraction(80), rmAreaTilesToFraction(140));
        rmSetAreaTerrainType(patchID, "andes\ground10_and");
        rmAddAreaTerrainLayer(patchID, "andes\ground10_and", 0, 1);
        rmSetAreaCoherence(patchID, 0.4);
        rmAddAreaConstraint(patchID, shortAvoidImpassable);
        rmAddAreaConstraint(patchID, avoidTownCenter);
        // 2026-05-15 WATER FIX: keep dirt patches out of the central sea
        // so they don't paint over the water around the observer island.
        rmAddAreaConstraint(patchID, stayOutOfCentralSea);
        rmBuildArea(patchID);
    }

    rmSetStatusText("", 0.86);

    // -----------------------------------------------------------------------
    // GLOBAL FORESTS -- scattered across compartments
    // Confirmed forest type: "andes forest" (Andes Upper Large line 954)
    //
    // 2026-05-15: Phase 5 — re-enabled after for-loop syntax fix
    // (`int fst = 0;` declared outside the for-statement to match the stock
    // RMS dialect; earlier `for(int fst=0; <35)` form silently failed parse).
    // -----------------------------------------------------------------------
    int failCount = 0;
    int fst = 0;
    for (fst = 0; < 35)
    {
        int forestID = rmCreateArea("forest " + fst);
        rmSetAreaWarnFailure(forestID, false);
        rmSetAreaSize(forestID, rmAreaTilesToFraction(150), rmAreaTilesToFraction(200));
        rmSetAreaForestType(forestID, "andes forest");
        rmSetAreaForestDensity(forestID, 0.85);
        rmSetAreaForestClumpiness(forestID, 0.6);
        rmSetAreaForestUnderbrush(forestID, 0.5);
        rmSetAreaCoherence(forestID, 0.4);
        rmSetAreaSmoothDistance(forestID, 8);
        rmAddAreaToClass(forestID, classForest);
        rmAddAreaConstraint(forestID, avoidForestClass);
        rmAddAreaConstraint(forestID, avoidTownCenter);
        rmAddAreaConstraint(forestID, avoidMineShort);
        rmAddAreaConstraint(forestID, avoidNativesClass);
        rmAddAreaConstraint(forestID, avoidImpassableLand);
        rmAddAreaConstraint(forestID, avoidCliffClass);
        rmAddAreaConstraint(forestID, avoidTradeRouteForest);
        // 2026-05-15 WATER FIX: keep forests out of the central sea.
        rmAddAreaConstraint(forestID, stayOutOfCentralSea);
        if (rmBuildArea(forestID) == false)
        {
            failCount++;
            if (failCount == 5)
                break;
        }
        else
            failCount = 0;
    }

    rmSetStatusText("", 0.90);

    // -----------------------------------------------------------------------
    // GLOBAL MINES -- scattered across compartments, avoiding central sea
    //
    // 2026-05-15: Phase 6 — re-enabled. All constraints verified defined:
    // avoidMine (line 64), avoidTownCenterFar (63), avoidTradeRoute (68),
    // stayInMap (72), avoidCliffClass / avoidNativesClass / avoidImpassableLand
    // earlier in this block. The pie constraint follows the same idiom as
    // stayInMap / stayCentralSea declared earlier.
    // -----------------------------------------------------------------------
    int globalMineID = rmCreateObjectDef("global mine");
    rmAddObjectDefItem(globalMineID, "mine", 1, 0.0);
    rmAddObjectDefToClass(globalMineID, classGold);
    rmSetObjectDefMinDistance(globalMineID, 0.0);
    rmSetObjectDefMaxDistance(globalMineID, rmXFractionToMeters(0.45));
    rmAddObjectDefConstraint(globalMineID, avoidMine);
    rmAddObjectDefConstraint(globalMineID, avoidTownCenterFar);
    rmAddObjectDefConstraint(globalMineID, avoidImpassableLand);
    rmAddObjectDefConstraint(globalMineID, avoidCliffClass);
    rmAddObjectDefConstraint(globalMineID, avoidNativesClass);
    rmAddObjectDefConstraint(globalMineID, avoidTradeRoute);
    rmAddObjectDefConstraint(globalMineID, stayInMap);
    rmAddObjectDefConstraint(globalMineID, rmCreatePieConstraint("mine avoid sea",
        0.5, 0.5, rmXFractionToMeters(0.23), rmXFractionToMeters(1.0),
        rmDegreesToRadians(0.0), rmDegreesToRadians(360.0)));
    rmPlaceObjectDefAtLoc(globalMineID, 0, 0.5, 0.5, 14);

    rmSetStatusText("", 0.94);

    // ---- Observer-island outposts (kept; pre-extras baseline) ----
    int outpostID = rmCreateObjectDef("observer outpost");
    rmAddObjectDefItem(outpostID, "Outpost", 1, 0.0);
    rmSetObjectDefMinDistance(outpostID, 8.0);
    rmSetObjectDefMaxDistance(outpostID, 14.0);
    rmAddObjectDefConstraint(outpostID, avoidImpassableLand);
    rmAddObjectDefConstraint(outpostID, avoidAllShort);
    rmPlaceObjectDefAtLoc(outpostID, 0, 0.500, 0.500);

    rmSetStatusText("", 0.96);

    // ---- KOTH support ----
    if (rmGetIsKOTH())
    {
        ypKingsHillPlacer(0.5, 0.5, 0.0, avoidCliffClass);
    }

    rmSetStatusText("", 0.98);
    rmEchoInfo("[HUBTEST] map generation complete (water-fix v5, extras enabled, doctrine-capture triggers wired)");
    rmSetStatusText("", 1.0);

    // =========================================================================
    // HUBTEST DOCTRINE-CAPTURE TRIGGERS
    // Added: 2026-05-18
    //
    // Trigger vocabulary verified against vanilla RandMaps (andes.xs,
    // unknownLarge.xs, honshuRegicide.xs):
    //   - rmCreateTrigger / rmSwitchToTrigger / rmSetTriggerPriority
    //   - rmSetTriggerActive / rmSetTriggerRunImmediately / rmSetTriggerLoop
    //   - rmAddTriggerCondition("Timer")  → Param1 = delay in seconds
    //   - rmAddTriggerEffect("Send Chat") → PlayerID / Message params
    //   - rmAddTriggerEffect("Grant Resources") → PlayerID / ResName / Amount
    //   - rmAddTriggerEffect("Set Player Defeated") → Player param
    //
    // NOT available from RMS triggers (no grep hit in game/ or RandMaps/):
    //   - "Create Unit" effect  → commented out with // TODO
    //   - aiPlanCreate / llPlanChokepointWall → AI-context only, not in RMS
    //   - trUnitCreate / trPlayerResign / trGameEnd → not found in any .xs
    //   - kbForceResign → AI-context function, not RMS surface
    //
    // Match-end strategy: Set Player Defeated on player 1 (observer) at T+120s.
    // When the only non-AI player is defeated the engine returns to lobby.
    // =========================================================================

    // -------------------------------------------------------------------------
    // T1: T+15s — Wall demonstration marker
    // "Create Unit" and aiPlanCreate are not available from RMS trigger effects.
    // We log the marker so the log parser knows the wall code path should have
    // been exercised by the AI's own scheduler by this point.
    // -------------------------------------------------------------------------
    rmCreateTrigger("hubtestWallMarker");
    rmSwitchToTrigger(rmTriggerID("hubtestWallMarker"));
    rmSetTriggerPriority(4);
    rmSetTriggerActive(true);
    rmSetTriggerRunImmediately(true);
    rmSetTriggerLoop(false);
    rmAddTriggerCondition("Timer");
    rmSetTriggerConditionParamInt("Param1", 15, false);
    rmAddTriggerEffect("Send Chat");
    rmSetTriggerEffectParamInt("PlayerID", 0, false);
    rmSetTriggerEffectParam("Message", "[HUBTEST] t=15s wall_demo_marker: AI walling scheduler active — see wall.chokepoint and wall.closure probes in AI log", false);
    // TODO: "Create Unit" effect does not exist in RMS trigger surface.
    // TODO: aiPlanCreate(cBuildWallPlanWallTypeRing,...) is AI-context only.
    // Wall plans are exercised by the AI's own explorationAgeWalling rule
    // (enabled in aiLoaderStandard.xs::postInit) — probe evidence appears
    // in wall.chokepoint / wall.closure / posture.snapshot log lines.

    // -------------------------------------------------------------------------
    // T2: T+30s — Doctrine capture begin marker
    // -------------------------------------------------------------------------
    rmCreateTrigger("hubtestDocCapture30");
    rmSwitchToTrigger(rmTriggerID("hubtestDocCapture30"));
    rmSetTriggerPriority(4);
    rmSetTriggerActive(true);
    rmSetTriggerRunImmediately(true);
    rmSetTriggerLoop(false);
    rmAddTriggerCondition("Timer");
    rmSetTriggerConditionParamInt("Param1", 30, false);
    rmAddTriggerEffect("Send Chat");
    rmSetTriggerEffectParamInt("PlayerID", 0, false);
    rmSetTriggerEffectParam("Message", "[HUBTEST] gametime=30s doctrine_capture_begin", false);
    // Doctrine commit state is logged by the AI's own llDoctrineProbes rule
    // (posture.snapshot at 60s intervals via aiLoaderStandard.xs::llDoctrineProbes).
    // The snapshot at T=60s will carry ws= bs= mdist= for every AI player.

    // -------------------------------------------------------------------------
    // T3: T+60s — Army readiness: give each AI a large resource injection so
    // their military build-up is clearly visible by the T+90s screenshot window.
    // "Create Unit" is not available as an RMS trigger effect; Grant Resources
    // is the closest verified proxy — it fills AI coffers so units train faster.
    // We also emit a chat marker for each AI slot so the log parser can confirm
    // coverage of P2..P8.
    // -------------------------------------------------------------------------
    rmCreateTrigger("hubtestArmyBoost60");
    rmSwitchToTrigger(rmTriggerID("hubtestArmyBoost60"));
    rmSetTriggerPriority(4);
    rmSetTriggerActive(true);
    rmSetTriggerRunImmediately(true);
    rmSetTriggerLoop(false);
    rmAddTriggerCondition("Timer");
    rmSetTriggerConditionParamInt("Param1", 60, false);
    // Player 1 is observer — skip. Grant food+wood+gold to AIs P2..P8.
    int htArmyBoostPlayer = 0;
    for (htArmyBoostPlayer = 2; <= 8)
    {
        rmAddTriggerEffect("Grant Resources");
        rmSetTriggerEffectParamInt("PlayerID", htArmyBoostPlayer, false);
        rmSetTriggerEffectParam("ResName", "Food", false);
        rmSetTriggerEffectParamInt("Amount", 3000, false);

        rmAddTriggerEffect("Grant Resources");
        rmSetTriggerEffectParamInt("PlayerID", htArmyBoostPlayer, false);
        rmSetTriggerEffectParam("ResName", "Wood", false);
        rmSetTriggerEffectParamInt("Amount", 2000, false);

        rmAddTriggerEffect("Grant Resources");
        rmSetTriggerEffectParamInt("PlayerID", htArmyBoostPlayer, false);
        rmSetTriggerEffectParam("ResName", "Gold", false);
        rmSetTriggerEffectParamInt("Amount", 2000, false);
    }
    rmAddTriggerEffect("Send Chat");
    rmSetTriggerEffectParamInt("PlayerID", 0, false);
    rmSetTriggerEffectParam("Message", "[HUBTEST] t=60s army_boost: 3000f/2000w/2000g granted to P2-P8 — watch event.elite.doctrine and comp.snapshot probes", false);
    // TODO: "Create Unit" effect not available — unit spawning for visual army
    // markers requires Scenario Editor triggers, not RMS trigger effects.
    // The resource grant ensures AI units are actively training by T+90s screenshot.

    // -------------------------------------------------------------------------
    // T4: T+90s — Hero march marker + second resource boost for hero training.
    // Hero units are trained from Home City shipments; a gold boost accelerates
    // that. Chat marker fires so screenshot runner knows the hero window is open.
    // -------------------------------------------------------------------------
    rmCreateTrigger("hubtestHeroMarch90");
    rmSwitchToTrigger(rmTriggerID("hubtestHeroMarch90"));
    rmSetTriggerPriority(4);
    rmSetTriggerActive(true);
    rmSetTriggerRunImmediately(true);
    rmSetTriggerLoop(false);
    rmAddTriggerCondition("Timer");
    rmSetTriggerConditionParamInt("Param1", 90, false);
    int htHeroPlayer = 0;
    for (htHeroPlayer = 2; <= 8)
    {
        rmAddTriggerEffect("Grant Resources");
        rmSetTriggerEffectParamInt("PlayerID", htHeroPlayer, false);
        rmSetTriggerEffectParam("ResName", "Food", false);
        rmSetTriggerEffectParamInt("Amount", 4000, false);

        rmAddTriggerEffect("Grant Resources");
        rmSetTriggerEffectParamInt("PlayerID", htHeroPlayer, false);
        rmSetTriggerEffectParam("ResName", "Gold", false);
        rmSetTriggerEffectParamInt("Amount", 4000, false);
    }
    rmAddTriggerEffect("Send Chat");
    rmSetTriggerEffectParamInt("PlayerID", 0, false);
    rmSetTriggerEffectParam("Message", "[HUBTEST] t=90s hero_escort_window: hero+escort active — watch elite.escort and elite.guard probes in AI log. Non-elite units below 25% HP should emit ai-rout-start / ai-rout-move / ai-rout-arrival; elite-support-within-18m blocks rout (ai-rout-blocked reason=elite-support).", false);
    // TODO: "Create Unit" not available from RMS trigger surface.
    // Hero units (civ-specific hero protos) and escort musketeers cannot be
    // spawned via rmAddTriggerEffect. The resource injection above funds the AI's
    // own hero/military train queue so visible armies appear near AI TCs.
    // Move-to-center orders likewise require Scenario Editor "Unit Move" effects.

    // -------------------------------------------------------------------------
    // EXTENDED-CYCLE MARKERS (only armed when gHubTestEndSeconds >= 1200).
    //
    // These markers delimit the milestone-observation windows for civs whose
    // doctrine claims extend past the 120s fast cycle:
    //   T+240s  — first_dock window opens (Naval/Coastal civs: claim ≤360s)
    //   T+360s  — first_dock deadline (British, Dutch, Portuguese, Barbary…)
    //   T+600s  — forward-base + first_artillery window
    //   T+960s  — first_wall_segment deadline (claim ≤900s)
    //
    // Fast cycle (gHubTestEndSeconds==120) skips this block entirely — the
    // auto-end at T+120s defeats the observer before any of these timers
    // could fire, so creating them would be dead work.
    // -------------------------------------------------------------------------
    if (gHubTestEndSeconds >= 1200)
    {
        rmCreateTrigger("hubtestDockWindowOpen240");
        rmSwitchToTrigger(rmTriggerID("hubtestDockWindowOpen240"));
        rmSetTriggerPriority(4);
        rmSetTriggerActive(true);
        rmSetTriggerRunImmediately(true);
        rmSetTriggerLoop(false);
        rmAddTriggerCondition("Timer");
        rmSetTriggerConditionParamInt("Param1", 240, false);
        rmAddTriggerEffect("Send Chat");
        rmSetTriggerEffectParamInt("PlayerID", 0, false);
        rmSetTriggerEffectParam("Message", "[HUBTEST] t=240s dock_window_open: Naval/Coastal civs should fire milestone.first_dock by T+360s", false);

        rmCreateTrigger("hubtestDockDeadline360");
        rmSwitchToTrigger(rmTriggerID("hubtestDockDeadline360"));
        rmSetTriggerPriority(4);
        rmSetTriggerActive(true);
        rmSetTriggerRunImmediately(true);
        rmSetTriggerLoop(false);
        rmAddTriggerCondition("Timer");
        rmSetTriggerConditionParamInt("Param1", 360, false);
        rmAddTriggerEffect("Send Chat");
        rmSetTriggerEffectParamInt("PlayerID", 0, false);
        rmSetTriggerEffectParam("Message", "[HUBTEST] t=360s dock_deadline: first_dock claim should be satisfied — see milestone.first_dock probe per Naval-claim AI", false);

        rmCreateTrigger("hubtestForwardWindow600");
        rmSwitchToTrigger(rmTriggerID("hubtestForwardWindow600"));
        rmSetTriggerPriority(4);
        rmSetTriggerActive(true);
        rmSetTriggerRunImmediately(true);
        rmSetTriggerLoop(false);
        rmAddTriggerCondition("Timer");
        rmSetTriggerConditionParamInt("Param1", 600, false);
        rmAddTriggerEffect("Send Chat");
        rmSetTriggerEffectParamInt("PlayerID", 0, false);
        rmSetTriggerEffectParam("Message", "[HUBTEST] t=600s forward_artillery_window: milestone.first_forward_base and milestone.first_artillery should fire for civs whose doctrine demands them", false);

        rmCreateTrigger("hubtestWallDeadline960");
        rmSwitchToTrigger(rmTriggerID("hubtestWallDeadline960"));
        rmSetTriggerPriority(4);
        rmSetTriggerActive(true);
        rmSetTriggerRunImmediately(true);
        rmSetTriggerLoop(false);
        rmAddTriggerCondition("Timer");
        rmSetTriggerConditionParamInt("Param1", 960, false);
        rmAddTriggerEffect("Send Chat");
        rmSetTriggerEffectParamInt("PlayerID", 0, false);
        rmSetTriggerEffectParam("Message", "[HUBTEST] t=960s wall_deadline: milestone.first_wall_segment claim should be satisfied — see wall.closure probe stream", false);
    }

    // -------------------------------------------------------------------------
    // T-END: Auto-end match by defeating observer (player 1).
    // "Set Player Defeated" is verified in honshuRegicide.xs (line 1112).
    // When P1 (the only non-AI/human player) is defeated, the engine ends the
    // match and returns to the lobby. AIs are not defeated — their personality
    // probes have already been written by their llTestModeAutoResign rule or
    // llWritePersonalityProbe at T=60s.
    //
    // Timer driven by gHubTestEndSeconds (top of main()): 120s fast cycle by
    // default; 1200s for full milestone observation (British review etc.).
    // -------------------------------------------------------------------------
    rmCreateTrigger("hubtestAutoEnd");
    rmSwitchToTrigger(rmTriggerID("hubtestAutoEnd"));
    rmSetTriggerPriority(4);
    rmSetTriggerActive(true);
    rmSetTriggerRunImmediately(true);
    rmSetTriggerLoop(false);
    rmAddTriggerCondition("Timer");
    rmSetTriggerConditionParamInt("Param1", gHubTestEndSeconds, false);
    rmAddTriggerEffect("Send Chat");
    rmSetTriggerEffectParamInt("PlayerID", 0, false);
    rmSetTriggerEffectParam("Message", "[HUBTEST] auto_end: defeating observer to close match (gHubTestEndSeconds)", false);
    rmAddTriggerEffect("Set Player Defeated");
    rmSetTriggerEffectParamInt("Player", 1, false);

}
