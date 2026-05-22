//==============================================================================
// aiBuildingsWalls.xs — SMART WALLS implementation
//
// Track 1.1a  llDetectChokepointVector      — real chokepoint detection via
//             kbAreaGetNumberBorderAreas / kbAreaGetBorderAreaID, cached once
//             per match. Falls back to forward-biased center on flat maps.
//
// Track 1.1b  llGetForwardBiasedWallCenter  — water/cliff AVOIDANCE: samples
//             kbAreaGetType after biasing; walks inland 8-unit steps (up to 5)
//             if the proposed center lands in water or a 0-tile area.
//
// Track 1.1b+ llDetectCoastVector           — water/cliff EXPLOITATION:
//             scans the AI base area's borders for water-typed neighbours,
//             computes the seaward centroid, and returns a wall center
//             pushed inland by ~30% of the ring radius. Used by
//             llPlanCoastalBatteriesWall to make the doctrine actually
//             coastal-aware (vs cosmetic naming). Returns cInvalidVector
//             on inland maps; caller falls back to forward-bias. Cached
//             per-AI per-match like the chokepoint detector.
//
// Track 1.1c  llSelectWallType              — wall-tier wrapper. All ages
//             currently return cBuildWallPlanWallTypeRing; radius + gate-count
//             callers (llGetLegendaryWallRadius / llGetLegendaryWallGateCount)
//             provide the actual age-based tier differentiation.
//
// Track 1.1d  rule verifyWallClosure        — gap-closure watchdog firing
//             every 60s once a ring plan is active. Escalates priority and
//             villager pool when coverage < 60% after 4 min; re-emits a fresh
//             plan if the original was destroyed.
//
// Track 1.1e  Smart gate placement          — SKIPPED / not supported.
//             cBuildWallPlanGate0Position and cBuildWallPlanGate1Position do
//             not appear anywhere in the engine surface or any .xs file in
//             this codebase. Attempting to pass them via aiPlanSetVariableVector
//             would reference an undefined constant and crash the script
//             validator. Gate count is controlled via cBuildWallPlanNumberOfGates;
//             gate placement remains engine-determined.
//             If a future engine patch exposes these constants, wire them in
//             here (bias gate 0 toward our TC, gate 1 at the flank) and remove
//             this notice.
//==============================================================================
// RULE explorationAgeWalling
// Start a basic ring wall around the main base in the Exploration Age.
//==============================================================================
bool llShouldBuildLegendaryWalls(bool earlyGame = false)
{
   if (cvOkToBuildWalls == false)
   {
      return (false);
   }

   // Doctrine veto: MobileNoWalls (Napoleon / Crazy Horse / Hiawatha /
   // Montezuma / Usman) overrides everything. No early walls, no late walls,
   // no gap fills, no upgrades. Their playstyle is open-field manoeuvre.
   if (gLLWallStrategy == cLLWallStrategyMobileNoWalls)
   {
      return (false);
   }

   if (earlyGame == true)
   {
      return (gLLEarlyWallingEnabled);
   }

   if (gLLWallLevel <= 0)
   {
      return (false);
   }

   return (gLLLateWallingEnabled);
}

float llGetLegendaryWallRadius(bool lateGame = false)
{
   float wallRadius = 42.0;

   if (lateGame == true)
   {
      wallRadius = 75.0;
   }
   if (gIslandMap == true)
   {
      wallRadius = lateGame == true ? 95.0 : 55.0;
   }

   if (gLLWallLevel == 1)
   {
      wallRadius = wallRadius - 6.0;
   }
   else if (gLLWallLevel == 3)
   {
      wallRadius = wallRadius + 6.0;
   }
   else if (gLLWallLevel >= 4)
   {
      wallRadius = wallRadius + 10.0;
   }

   if (gLLBuildStyle == cLLBuildStyleCompactFortifiedCore)
   {
      wallRadius = wallRadius - 4.0;
   }
   else if (gLLBuildStyle == cLLBuildStyleMobileFrontierScatter)
   {
      wallRadius = wallRadius + 8.0;
   }

   return (wallRadius);
}

int llGetLegendaryWallGateCount(bool lateGame = false)
{
   // Raised from 4/15 to 6/18. More gates = better sally routes and the
   // engine lays down more wall pieces per plan (each gate anchors an arc).
   int gateCount = lateGame == true ? 18 : 6;

   if (gLLWallLevel == 1)
   {
      gateCount = gateCount + 2;
   }
   else if (gLLWallLevel == 3)
   {
      gateCount = gateCount - 1;
   }
   else if (gLLWallLevel >= 4)
   {
      gateCount = gateCount - 2;
   }

   if (gateCount < 3)
   {
      gateCount = 3;
   }

   return (gateCount);
}

// Shift the wall ring center slightly along the base's front vector (toward
// the likely enemy arc). A full ring still surrounds the base, but the
// extra bias thickens wall coverage on the contested side where it matters
// most. Returns the input unchanged if no front vector is registered.
//
// SMART WALLS — Track 1.1b: water/cliff fixup. After biasing, sample the
// area type. If we land in water (or a 0-tile area), walk backwards along
// the inverse front vector in 8-unit steps (up to 5) trying to find land.
// If we never find land, return baseCenter unchanged (safer than ocean).
vector llGetForwardBiasedWallCenter(vector baseCenter = cInvalidVector,
                                    int mainBaseID = -1,
                                    float biasFactor = 0.25)
{
   if ((baseCenter == cInvalidVector) || (mainBaseID < 0))
   {
      return (baseCenter);
   }
   vector frontVec = kbBaseGetFrontVector(cMyID, mainBaseID);
   if ((frontVec == cInvalidVector) ||
       ((xsVectorGetX(frontVec) == 0.0) && (xsVectorGetZ(frontVec) == 0.0)))
   {
      return (baseCenter);
   }
   float radius = llGetLegendaryWallRadius(false);
   float shift = radius * biasFactor;
   float nx = xsVectorGetX(baseCenter) + xsVectorGetX(frontVec) * shift;
   float nz = xsVectorGetZ(baseCenter) + xsVectorGetZ(frontVec) * shift;
   vector biased = xsVectorSet(nx, xsVectorGetY(baseCenter), nz);

   // Water/cliff fixup. Sample the biased center's area; if it's water or
   // a 0-tile area, step inland (opposite of frontVec) 8 units at a time
   // up to 5 times. Each step is re-sampled. First valid land wins.
   int areaID = kbAreaGetIDByPosition(biased);
   int areaType = -1;
   int areaTiles = 0;
   if (areaID >= 0)
   {
      areaType = kbAreaGetType(areaID);
      areaTiles = kbAreaGetNumberTiles(areaID);
   }
   if ((areaID < 0) || (areaType == cAreaTypeWater) || (areaTiles <= 0))
   {
      vector corrected = biased;
      int steps = 0;
      bool fixed = false;
      for (i = 1; <= 5)
      {
         float bx = nx - xsVectorGetX(frontVec) * 8.0 * i;
         float bz = nz - xsVectorGetZ(frontVec) * 8.0 * i;
         vector candidate = xsVectorSet(bx, xsVectorGetY(baseCenter), bz);
         int candID = kbAreaGetIDByPosition(candidate);
         if (candID < 0) { continue; }
         int candType = kbAreaGetType(candID);
         int candTiles = kbAreaGetNumberTiles(candID);
         if ((candType != cAreaTypeWater) && (candTiles > 0))
         {
            corrected = candidate;
            steps = i;
            fixed = true;
            break;
         }
      }
      llProbe("wall.water_fix", "orig=" + llFmtVec(biased) +
         " final=" + llFmtVec(corrected) + " steps=" + steps +
         " fixed=" + fixed);
      if (fixed == true)
      {
         return (corrected);
      }
      // Every step still in water/invalid — fall back to baseCenter
      // (safer than placing a ring centered in the ocean).
      return (baseCenter);
   }
   // SMART WALLS — Track 1.1b (Defect 2 fix): always emit a wall.water_fix
   // probe so flat inland maps register the feature as "ran, no fix needed"
   // rather than "feature absent". orig==final and steps=0 on this path.
   llProbe("wall.water_fix", "orig=" + llFmtVec(biased) +
      " final=" + llFmtVec(biased) + " steps=0 fixed=false");
   return (biased);
}

//==============================================================================
// SMART WALLS — Track 1.1a: chokepoint detection.
//
// Walks the AI's base area and its border areas once per match (cached) to
// find the narrowest "gap" between two impassable-style neighbours. The
// gap area's center is returned as the chokepoint vector. Fall back to
// llGetForwardBiasedWallCenter() on flat maps (no water/impassable borders).
//
// NOTE: the engine's area-type vocabulary in this codebase is only
// confirmed to expose cAreaTypeWater. No cAreaTypeImpassableLand /
// cAreaTypeCliff constants are referenced anywhere in the mod or the
// surrounding files. We therefore approximate "impassable" via a
// tile-count heuristic: a border area whose tile count is < 25% of the
// AI base area's tile count is treated as a non-traversable shoulder
// (cliff face, terrain wall, small water inlet). Combined with the
// hard cAreaTypeWater check, this gives us "narrowest gap" on real maps.
//==============================================================================
vector llDetectChokepointVector(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   // Per-AI cache: compute once per match, reuse thereafter.
   static int chokepointCached = 0;
   static vector chokepointVec = cInvalidVector;
   if (chokepointCached == 1)
   {
      // SMART WALLS — Track 1.1a (Defect 3 fix): keep the schema numeric
      // for tiles (`tiles=<int>`). The cached-hit path emits 0 to signal
      // "no fresh tile-count was computed this tick"; cached=1 distinguishes
      // from a true zero-tile measurement.
      llProbe("wall.chokepoint", "vec=" + llFmtVec(chokepointVec) +
         " tiles=0 cached=1");
      return (chokepointVec);
   }

   if ((baseCenter == cInvalidVector) || (mainBaseID < 0))
   {
      return (llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.35));
   }

   int baseAreaID = kbAreaGetIDByPosition(baseCenter);
   if (baseAreaID < 0)
   {
      return (llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.35));
   }
   int baseTiles = kbAreaGetNumberTiles(baseAreaID);
   int numBorders = kbAreaGetNumberBorderAreas(baseAreaID);
   if (numBorders <= 0)
   {
      // No border areas at all -> open map, no chokepoint to detect.
      vector fallbackNoBorders = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.35);
      chokepointVec = fallbackNoBorders;
      chokepointCached = 1;
      llProbe("wall.chokepoint", "vec=" + llFmtVec(fallbackNoBorders) +
         " tiles=0 cached=0 fallback=noBorders");
      return (fallbackNoBorders);
   }

   // First pass: tag each border area as "impassable-ish" (water OR very
   // few tiles vs. base). Then scan for the narrowest border with at
   // least one impassable-ish neighbour adjacent — that's the choke.
   int narrowestID = -1;
   int narrowestTiles = 999999;
   int impassableThreshold = baseTiles / 4;  // < 25% of base area
   if (impassableThreshold < 8) { impassableThreshold = 8; }

   for (i = 0; < numBorders)
   {
      int borderID = kbAreaGetBorderAreaID(baseAreaID, i);
      if (borderID < 0) { continue; }
      int btype = kbAreaGetType(borderID);
      int btiles = kbAreaGetNumberTiles(borderID);
      // Skip water borders themselves — we want LAND chokepoints
      // (the engine can't path through water for walling).
      if (btype == cAreaTypeWater) { continue; }
      // Skip "fat" borders — these are open ground, not chokes.
      if (btiles >= baseTiles) { continue; }

      // Does this border have at least one impassable-ish neighbour
      // (water OR a tiny area)? If yes, it's a candidate chokepoint.
      bool hasImpassableNeighbour = false;
      int neighbourCount = kbAreaGetNumberBorderAreas(borderID);
      for (j = 0; < neighbourCount)
      {
         int neighbourID = kbAreaGetBorderAreaID(borderID, j);
         if (neighbourID < 0) { continue; }
         if (neighbourID == baseAreaID) { continue; }
         int ntype = kbAreaGetType(neighbourID);
         int ntiles = kbAreaGetNumberTiles(neighbourID);
         if ((ntype == cAreaTypeWater) || (ntiles <= impassableThreshold))
         {
            hasImpassableNeighbour = true;
            break;
         }
      }
      if (hasImpassableNeighbour == false) { continue; }

      if (btiles < narrowestTiles)
      {
         narrowestTiles = btiles;
         narrowestID = borderID;
      }
   }

   if (narrowestID < 0)
   {
      // Flat map: nothing pinched. Use forward-biased fallback.
      vector fallbackFlatMap = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.35);
      chokepointVec = fallbackFlatMap;
      chokepointCached = 1;
      llProbe("wall.chokepoint", "vec=" + llFmtVec(fallbackFlatMap) +
         " tiles=0 cached=0 fallback=flatMap");
      return (fallbackFlatMap);
   }

   vector chokeCenter = kbAreaGetCenter(narrowestID);
   chokepointVec = chokeCenter;
   chokepointCached = 1;
   llProbe("wall.chokepoint", "vec=" + llFmtVec(chokeCenter) +
      " tiles=" + narrowestTiles + " cached=0");
   return (chokeCenter);
}

//==============================================================================
// SMART WALLS — Track 1.1c: wall-type / tier dispatch.
//
// Only cBuildWallPlanWallTypeRing is confirmed in the engine vocabulary
// referenced by this codebase — no cBuildWallPlanWallTypeSegment or
// cBuildWallPlanWallTypeFortified is documented anywhere we can see.
// Engine wall-type vocabulary not fully documented; using Ring at all ages
// with radius/gate variation as the tier knob (see llGetLegendaryWallRadius
// and llGetLegendaryWallGateCount, both already age-aware).
//
// Returns the wall-type constant to feed into cBuildWallPlanWallType.
// All ages return cBuildWallPlanWallTypeRing today; the dispatch is
// here so once additional constants are confirmed they can be slotted
// in without touching every strategy function.
//==============================================================================
int llSelectWallType(int wallStrategy = -1, int age = 1)
{
   // Age 1 -> light palisade-style ring (small radius handled by callers).
   // Age 2-3 -> normal stone ring.
   // Age 4+ -> fortified ring + outer supplement (already handled in
   //          delayWallsNew's outerRingPlaced branch).
   // All three currently map to the same engine wall-type constant; the
   // radius/gate-count callers apply on top of this is the actual tier
   // differentiator.
   return (cBuildWallPlanWallTypeRing);
}

//==============================================================================
// Per-doctrine wall strategy dispatch. Each strategy plans its Age-1
// fortifications in a historically-grounded way.
//==============================================================================

// FortressRing: full 360-degree ring wall with extra thickness/gates.
// Valette, Pachacuti, Frederick, Suleiman, Catherine, Bourbon France.
// Keeps symmetric center — fortress doctrine is all-around defense.
int llPlanFortressRingWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llGetLegendaryWallRadius(false);
   int planID = aiPlanCreate("FortressRing Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   // Heavy villager commitment — a ~264-unit perimeter at radius 42 needs a
   // sustained pool, not a 3–5 starter crew that finishes its first segment
   // and goes home. Bumped 3,5 -> 6,12 so the ring actually closes.
   // min=2 (was 6): a stalled plan only locks 2 villagers idle, not 6.
   // max=12: still scales up when there are wall pieces to place.
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, 12);
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, baseCenter);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   // Fewer gates = fewer gaps. Fortress doctrine wants a dense wall.
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, 4);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 88);  // raised 75 -> 88 so wall wins over barracks/houses
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=FortressRing radius=" + radius +
      " gates=4 vils=6-12 priority=88 plan=" + planID);
   return (planID);
}

// ChokepointSegments: walls only at natural terrain pinches (Andes/Alps/passes).
// Shivaji (Maratha hill forts), Pachacuti (valley mouths), Kangxi (Great Wall).
// Fallback to a tighter ring if chokepoint detection fails on flat maps —
// biased forward toward enemy since chokepoints always face outward.
int llPlanChokepointWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llGetLegendaryWallRadius(false) - 4.0;
   // SMART WALLS — Track 1.1a: real chokepoint detection rather than
   // the misnamed forward-biased fallback. Detector itself falls back
   // to forward-biased on flat maps.
   vector center = llDetectChokepointVector(mainBaseID, baseCenter);
   int planID = aiPlanCreate("Chokepoint Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, 10);  // min=2 to release idlers when plan stalls
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, 3);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 85);
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=Chokepoint radius=" + radius +
      " gates=3 vils=5-10 priority=85 plan=" + planID);
   return (planID);
}

//==============================================================================
// SMART WALLS — Track 1.1b EXTENSION: coastline exploitation.
//
// llGetForwardBiasedWallCenter handles AVOIDANCE (walks inland if biased
// center lands in water). This helper handles EXPLOITATION: detects the
// direction from baseCenter toward water-bordering areas, then returns a
// wall center pushed INLAND (opposite of the coast centroid). The seaward
// arc of the resulting ring backs up onto the shoreline — the coast itself
// acts as a natural barrier, freeing wall pieces to thicken the landward
// perimeter. This is what makes "CoastalBatteries" actually doctrinal on
// real coastal/island maps instead of cosmetic.
//
// Returns cInvalidVector when no water borders are detected (inland map);
// caller must fall back to llGetForwardBiasedWallCenter() in that case.
//
// Per-AI cached: computed once per match.
//==============================================================================
vector llDetectCoastVector(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   static int coastCached = 0;
   static vector coastVec = cInvalidVector;
   if (coastCached == 1)
   {
      llProbe("wall.coast", "vec=" + llFmtVec(coastVec) +
         " waterBorders=0 cached=1");
      return (coastVec);
   }

   if ((baseCenter == cInvalidVector) || (mainBaseID < 0))
   {
      coastCached = 1;
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=invalidArgs");
      return (cInvalidVector);
   }

   int baseAreaID = kbAreaGetIDByPosition(baseCenter);
   if (baseAreaID < 0)
   {
      coastCached = 1;
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=noBaseArea");
      return (cInvalidVector);
   }

   int numBorders = kbAreaGetNumberBorderAreas(baseAreaID);
   if (numBorders <= 0)
   {
      coastCached = 1;
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=noBorders");
      return (cInvalidVector);
   }

   // Sum the centers of all water-typed border areas, then average to get
   // the coastline centroid. The vector FROM baseCenter TO that centroid
   // points seaward; inverting it pulls the wall ring inland.
   float sumX = 0.0;
   float sumZ = 0.0;
   int waterCount = 0;
   for (i = 0; < numBorders)
   {
      int borderID = kbAreaGetBorderAreaID(baseAreaID, i);
      if (borderID < 0) { continue; }
      if (kbAreaGetType(borderID) != cAreaTypeWater) { continue; }
      vector bcenter = kbAreaGetCenter(borderID);
      sumX = sumX + xsVectorGetX(bcenter);
      sumZ = sumZ + xsVectorGetZ(bcenter);
      waterCount = waterCount + 1;
   }

   if (waterCount <= 0)
   {
      // No water borders on this base area — inland map. Caller falls back.
      coastCached = 1;
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=inlandMap");
      return (cInvalidVector);
   }

   float waterX = sumX / waterCount;
   float waterZ = sumZ / waterCount;
   vector waterCentroid = xsVectorSet(waterX, xsVectorGetY(baseCenter), waterZ);
   vector seaward = waterCentroid - baseCenter;
   float mag = xsVectorLength(seaward);
   if (mag <= 0.0)
   {
      coastCached = 1;
      coastVec = baseCenter;
      llProbe("wall.coast", "vec=" + llFmtVec(baseCenter) +
         " waterBorders=" + waterCount + " cached=0 fallback=zeroMagnitude");
      return (baseCenter);
   }
   vector inlandUnit = xsVectorNormalize(0.0 - seaward);
   float radius = llGetLegendaryWallRadius(false);
   // Inland push of ~30% of wall radius — same scale as forward bias but
   // anchored to the coast geometry rather than the front vector. Matches
   // historical peninsular doctrine: wall the landward face thick, leave
   // the seaward face to the navy / shore guns.
   float shift = radius * 0.30;
   vector coastBiased = baseCenter + inlandUnit * shift;
   coastVec = coastBiased;
   coastCached = 1;
   llProbe("wall.coast", "vec=" + llFmtVec(coastBiased) +
      " waterBorders=" + waterCount + " cached=0 shift=" + shift);
   return (coastBiased);
}

// CoastalBatteries: land-side partial ring (Wellington Torres Vedras, Henry Elmina).
// Ring center pushed inland (away from the coast arc) so the wall covers
// the landward approach more thickly — matches real peninsular doctrine.
//
// 2026-05-13 (Track 1.1b extension): on coastal/island maps we now use
// llDetectCoastVector() to push the ring center AWAY from the water-border
// centroid. Falls back to llGetForwardBiasedWallCenter (the old behaviour)
// on inland maps where no water border is detected — keeps the doctrine
// graceful on flat terrain instead of NaN-ing the plan.
int llPlanCoastalBatteriesWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llGetLegendaryWallRadius(false);
   vector coastCenter = llDetectCoastVector(mainBaseID, baseCenter);
   vector center = cInvalidVector;
   string centerSrc = "";
   if (coastCenter == cInvalidVector)
   {
      // Inland map — fall back to forward-biased (front-vector) center.
      center = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.20);
      centerSrc = "frontBias";
   }
   else
   {
      center = coastCenter;
      centerSrc = "coastInland";
   }
   int planID = aiPlanCreate("CoastalBatteries Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, 10);  // min=2 to release idlers when plan stalls
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, 4);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 86);
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=CoastalBatteries radius=" + radius +
      " gates=4 vils=6-10 priority=86 plan=" + planID +
      " centerSrc=" + centerSrc);
   return (planID);
}

// FrontierPalisades: quick lighter ring, many gates, less stone.
// Washington, Jefferson, Brock, Papineau, Houston, Kruger, Mannerheim, Morazán.
int llPlanFrontierPalisadeWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llGetLegendaryWallRadius(false) + 2.0;
   vector center = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.15);
   int planID = aiPlanCreate("FrontierPalisade Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, 8);   // min=2 to release idlers when plan stalls
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, 5);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 82);  // wood-cheap palisades, complete first
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=FrontierPalisade radius=" + radius +
      " gates=5 vils=4-8 priority=82 plan=" + planID);
   return (planID);
}

// UrbanBarricade: tight compact inner ring (Robespierre Paris, Garibaldi cities).
int llPlanUrbanBarricadeWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llGetLegendaryWallRadius(false) - 8.0;
   vector center = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.15);
   int planID = aiPlanCreate("UrbanBarricade Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, 8);   // min=2 to release idlers when plan stalls
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, 3);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 84);
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=UrbanBarricade radius=" + radius +
      " gates=3 vils=4-8 priority=84 plan=" + planID);
   return (planID);
}

// MobileNoWalls: no walls at all, leaner strategy built elsewhere.
// Returns -1 to signal "skip entirely".
int llPlanMobileNoWalls(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   return (-1);  // intentionally no wall plan
}

// Strategy dispatch — called from the rule.
int llPlanExplorationAgeWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   // LL-WALL probe — records which doctrine branch ran and the base center.
   // One emission per AI per match (rule self-disables after first dispatch),
   // so the replay parser can map leader → actual wall strategy exercised.
   llProbe("plan.wall", "strategy=" + gLLWallStrategy + " base=" + mainBaseID +
      " center=" + llFmtVec(baseCenter) + " wallLevel=" + gLLWallLevel +
      " earlyWalls=" + gLLEarlyWallingEnabled);

   if (gLLWallStrategy == cLLWallStrategyFortressRing)       return (llPlanFortressRingWall(mainBaseID, baseCenter));
   if (gLLWallStrategy == cLLWallStrategyChokepointSegments) return (llPlanChokepointWall(mainBaseID, baseCenter));
   if (gLLWallStrategy == cLLWallStrategyCoastalBatteries)   return (llPlanCoastalBatteriesWall(mainBaseID, baseCenter));
   if (gLLWallStrategy == cLLWallStrategyFrontierPalisades)  return (llPlanFrontierPalisadeWall(mainBaseID, baseCenter));
   if (gLLWallStrategy == cLLWallStrategyUrbanBarricade)     return (llPlanUrbanBarricadeWall(mainBaseID, baseCenter));
   if (gLLWallStrategy == cLLWallStrategyMobileNoWalls)      return (llPlanMobileNoWalls(mainBaseID, baseCenter));
   // Fallback — FortressRing if unknown.
   llProbe("plan.wall", "fallback=FortressRing unknownStrategy=" + gLLWallStrategy);
   return (llPlanFortressRingWall(mainBaseID, baseCenter));
}

// PERPETUAL WALLING MODEL
// =======================
// Walls are top-priority protection and the AI dedicates villagers to them
// every age. We do NOT disable these rules after placing a plan — we keep
// them ticking so:
//   (a) if the engine evicts / completes the wall plan, we replace it;
//   (b) if the base expands or walls are destroyed, gap-fill + new rings
//       kick in automatically;
//   (c) villager allocation on the standing plan stays topped up.
// Anti-spam is enforced by aiPlanGetIDByTypeAndVariableType dedup: we never
// create a second ring plan while one is active. MobileNoWalls doctrines
// opt out cleanly via xsDisableSelf at rule entry.
rule explorationAgeWalling
inactive
group tcComplete
minInterval 20
{
   // LL-WALL-GATE probe — fires every tick of the rule, so the replay parser
   // sees exactly which gate causes the rule to bail. Compact tag because
   // this can fire many times per match per AI.
   static int gateTickProbe = 0;
   gateTickProbe = gateTickProbe + 1;

   if (cvOkToBuild == false)
   {
      llProbe("wall.gate", "tick=" + gateTickProbe + " bail=cvOkToBuild");
      llLogDecision("WALL", "exploration walling disabled by config (cvOkToBuild)");
      xsDisableSelf();
      return;
   }
   if (llShouldBuildLegendaryWalls(true) == false)
   {
      llProbe("wall.gate", "tick=" + gateTickProbe +
         " bail=llShould early=" + gLLEarlyWallingEnabled +
         " level=" + gLLWallLevel +
         " okWalls=" + cvOkToBuildWalls);
      llLogDecision("WALL", "exploration walling disabled by config (llShould)");
      xsDisableSelf();
      return;
   }

   // Hand off to delayWallsNew (which is perpetual from Age 3 onward) once
   // we're past Exploration — keeps responsibilities clean.
   if (kbGetAge() > cAge1)
   {
      llProbe("wall.gate", "tick=" + gateTickProbe + " bail=ageOver age=" + kbGetAge());
      xsDisableSelf();
      return;
   }

   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID < 0)
   {
      llProbe("wall.gate", "tick=" + gateTickProbe + " bail=noMainBase");
      return;
   }

   // Anti-spam: skip while any ring plan is active or while existing walls
   // already surround the base (gap-fill owns that case).
   int existingRingPlan = aiPlanGetIDByTypeAndVariableType(cPlanBuildWall, cBuildWallPlanWallType, cBuildWallPlanWallTypeRing, true);
   if (existingRingPlan >= 0)
   {
      llProbe("wall.gate", "tick=" + gateTickProbe + " skip=ringActive plan=" + existingRingPlan);
      xsEnableRule("fillInWallGapsNew");
      return;
   }

   int existingWalls = kbUnitCount(cMyID, cUnitTypeAbstractWall, cUnitStateABQ);
   if (existingWalls > 0)
   {
      llProbe("wall.gate", "tick=" + gateTickProbe + " skip=wallsExist count=" + existingWalls);
      xsEnableRule("fillInWallGapsNew");
      // Don't disable — if the plan disappears later and all walls die,
      // we want this rule to recreate the ring instead of going silent.
      return;
   }

   float wood = kbResourceGet(cResourceWood);
   if (wood < 75.0)
   {
      llProbe("wall.gate", "tick=" + gateTickProbe + " wait=lowWood wood=" + wood);
      return;
   }

   vector baseCenter = kbBaseGetLocation(cMyID, mainBaseID);
   if (baseCenter == cInvalidVector)
   {
      return;
   }

   int wallPlanID = llPlanExplorationAgeWall(mainBaseID, baseCenter);
   if (wallPlanID < 0)
   {
      // MobileNoWalls doctrine decision is permanent.
      llLogDecision("WALL", "strategy=" + gLLWallStrategy + " declined to build walls (MobileNoWalls)");
      xsDisableSelf();
      return;
   }

   llLogPlanEvent("create", wallPlanID, "exploration-wall strategy=" + gLLWallStrategy + " center=" + baseCenter);
   xsEnableRule("fillInWallGapsNew");
   // SMART WALLS — Track 1.1d: arm the closure watchdog so it can
   // escalate / re-emit if the plan stalls at <60% closure.
   xsEnableRule("verifyWallClosure");
   // Stay active: anti-spam dedup above prevents duplicate plans, but if
   // this plan ever dies we want to place a fresh one.
}

//==============================================================================
// RULE enhancedWalls
//==============================================================================
rule enhancedWalls
inactive
minInterval 10
{
   vector myBaseLoc = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
   vector mainBaseCenter = kbAreaGetCenter(kbAreaGetIDByPosition(myBaseLoc));
   vector mainBaseFront = kbBaseGetFrontVector(cMyID, kbBaseGetMainID(cMyID));
   float woodAmount = kbResourceGet(cResourceWood);

   //buildSquareWall(mainBaseCenter, kbBaseGetMainID(cMyID), 100, 9);

   if (gWallBuildingSuccess == true) {
      xsDisableSelf();
   }
}
//==============================================================================
// RULE delayWallsNew
//==============================================================================
// Persistent Fortress+ walling. Fires every 30s from Age 3 onward for the
// rest of the match. Anti-spam dedup prevents multiple ring plans on the
// same base. Outer ring supplement kicks in at Age 4 so the defended
// perimeter expands as the base grows — but only one outer ring, ever.
rule delayWallsNew
inactive
minInterval 30
{
   if (llShouldBuildLegendaryWalls(false) == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() < cAge3)
   {
      return;
   }

   if (gLLWallStrategy == cLLWallStrategyMobileNoWalls)
   {
      llLogDecision("WALL", "late walling declined - MobileNoWalls doctrine");
      xsDisableSelf();
      return;
   }

   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID < 0)
   {
      return;
   }
   vector baseCenter = kbBaseGetLocation(cMyID, mainBaseID);
   if (baseCenter == cInvalidVector)
   {
      return;
   }

   // Anti-spam: is there ALREADY an active ring plan on this base?
   // If yes we leave it alone — no duplicate ring spam. The plan stays
   // alive and the engine keeps placing pieces as wood allows.
   bool ringActive = (aiPlanGetIDByTypeAndVariableType(
      cPlanBuildWall, cBuildWallPlanWallType, cBuildWallPlanWallTypeRing, true) >= 0);

   // Wider outer ring for late-game walls; more gates for sally options.
   // SMART WALLS — Track 1.1 (Defect 1 fix): late-game walls must respect
   // the per-doctrine strategy the same way the Age-1 dispatch in
   // llPlanExplorationAgeWall does. Previously this path forward-biased
   // for everyone except FortressRing and never called
   // llDetectChokepointVector(), so Pachacuti / Shivaji / Kangxi late-game
   // walls would ring a forward-biased point rather than the actual valley
   // mouth that defines the doctrine.
   float wallRadius = llGetLegendaryWallRadius(true);
   vector wallCenter = baseCenter;
   if (gLLWallStrategy == cLLWallStrategyFortressRing)
   {
      // Symmetric all-around ring; baseCenter is correct.
   }
   else if (gLLWallStrategy == cLLWallStrategyChokepointSegments)
   {
      // Real chokepoint detection (cached). Falls back to forward-bias
      // on flat maps with no impassable borders.
      wallCenter = llDetectChokepointVector(mainBaseID, baseCenter);
   }
   else
   {
      // CoastalBatteries, FrontierPalisades, MobileNoWalls (skipped earlier
      // via llShouldBuildLegendaryWalls), HiddenForts, etc. — bias toward
      // the enemy arc.
      wallCenter = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.18);
   }

   // Static flag so the outer supplement only ever fires once.
   static int outerRingPlaced = 0;
   bool placingOuter = false;

   if (ringActive == true)
   {
      // Main ring is already active. Consider placing the OUTER supplement
      // when we hit Age 4 (Industrial) — a single wider ring that doubles
      // the defended perimeter. Only once per match per AI.
      if ((kbGetAge() >= cAge4) && (outerRingPlaced == 0))
      {
         placingOuter = true;
         wallRadius = wallRadius * 1.35;  // 35% wider outer ring
      }
      else
      {
         // Nothing to do this tick — ring alive, no supplement needed yet.
         return;
      }
   }

   int wallPlanID = aiPlanCreate(placingOuter ? "OuterWallRing" : "WallInBase", cPlanBuildWall);
   if (wallPlanID < 0)
   {
      return;
   }

   // SMART WALLS — Track 1.1 (Defect 1 fix): use the strategy/age dispatch
   // wrapper instead of hardcoding Ring, so future tier constants flow
   // through this path automatically. Today this resolves to Ring at every
   // age, but the call site is now correct.
   aiPlanSetVariableInt(wallPlanID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   // 3–5 dedicated villagers — walls are top-priority protection.
   aiPlanAddUnitType(wallPlanID, gEconUnit, 0, 3, 5);
   aiPlanSetVariableVector(wallPlanID, cBuildWallPlanWallRingCenterPoint, 0, wallCenter);
   aiPlanSetVariableFloat(wallPlanID, cBuildWallPlanWallRingRadius, 0.0, wallRadius);
   aiPlanSetVariableInt(wallPlanID, cBuildWallPlanNumberOfGates, 0, llGetLegendaryWallGateCount(true));
   aiPlanSetBaseID(wallPlanID, mainBaseID);
   aiPlanSetEscrowID(wallPlanID, cEconomyEscrowID);
   // Priority 75 for primary ring, 70 for outer supplement (don't starve
   // the main ring if wood contention arises).
   aiPlanSetDesiredPriority(wallPlanID, placingOuter ? 70 : 75);
   aiPlanSetActive(wallPlanID, true);
   xsEnableRule("fillInWallGapsNew");
   // SMART WALLS — Track 1.1d: arm the closure watchdog for late-game
   // walls too. It self-disables when llShouldBuildLegendaryWalls flips
   // false.
   xsEnableRule("verifyWallClosure");

   if (placingOuter == true)
   {
      outerRingPlaced = 1;
   }

   llLogPlanEvent("create", wallPlanID,
      (placingOuter ? "outer-wall" : "late-wall") +
      " strategy=" + gLLWallStrategy +
      " center=" + llFmtVec(wallCenter) +
      " radius=" + wallRadius +
      " gates=" + llGetLegendaryWallGateCount(true));
   llProbe("plan.wall",
      "phase=" + (placingOuter ? "outer" : "late") +
      " strategy=" + gLLWallStrategy +
      " base=" + mainBaseID +
      " center=" + llFmtVec(wallCenter) +
      " radius=" + wallRadius +
      " wallLevel=" + gLLWallLevel);
   // Stay active: if this plan ever dies, re-create it next tick.
}
//==============================================================================
// RULE verifyWallClosure
// SMART WALLS — Track 1.1d: closure verification + escalation.
//
// The engine reports a wall plan SUCCESS even when only ~40% of pieces got
// placed ("half walls"). This rule recomputes expected wall-piece count
// from circumference / piece-length and compares to kbUnitCount of owned
// wall segments. If we're under 60% closure after 4 minutes of game time
// we bump priority + villager pool on the live plan, or re-emit a plan
// if the previous one was destroyed by the engine.
//==============================================================================
rule verifyWallClosure
inactive
minInterval 60
{
   if (llShouldBuildLegendaryWalls(false) == false)
   {
      xsDisableSelf();
      return;
   }
   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID < 0) { return; }
   vector baseCenter = kbBaseGetLocation(cMyID, mainBaseID);
   if (baseCenter == cInvalidVector) { return; }

   // expected wall pieces = circumference / piece-length (~4 tiles per
   // wall segment in AoE3 DE)
   float radius = llGetLegendaryWallRadius(kbGetAge() >= cAge3);
   int expectedPieces = 1 + (2.0 * 3.14159 * radius / 4.0);
   int actualPieces = kbUnitCount(cMyID, cUnitTypeAbstractWall, cUnitStateABQ);
   float closure = 0.0;
   if (expectedPieces > 0)
   {
      // 2026-05-12 fix: XS performs integer division on `int / int` BEFORE
      // assigning to a float, so any closure ratio < 1.0 truncated to 0
      // and tripped the spurious-escalation branch every 60s. Multiplying
      // by 1.0 forces float arithmetic.
      closure = (1.0 * actualPieces) / expectedPieces;
   }
   int elapsedSec = xsGetTime() / 1000;
   llProbe("wall.closure", "expected=" + expectedPieces +
      " actual=" + actualPieces +
      " closure=" + closure +
      " strategy=" + gLLWallStrategy +
      " elapsed=" + elapsedSec +
      " age=" + kbGetAge());

   // <60% closure after 4 minutes of game time -> escalate.
   if ((closure < 0.6) && (xsGetTime() >= 240000))
   {
      int planID = aiPlanGetIDByTypeAndVariableType(cPlanBuildWall,
         cBuildWallPlanWallType, cBuildWallPlanWallTypeRing, true);
      if (planID >= 0)
      {
         // Plan is still alive but slow — bump priority and feed it
         // more villagers.
         aiPlanSetDesiredPriority(planID, 95);
         aiPlanAddUnitType(planID, gEconUnit, 0, 4, 16);
         llProbe("wall.escalate", "plan=" + planID + " closure=" + closure);
      }
      else
      {
         // Plan died — re-emit through the normal dispatch.
         llPlanExplorationAgeWall(mainBaseID, baseCenter);
         llProbe("wall.reemit", "closure=" + closure);
      }
   }
}
//==============================================================================
// RULE fillInWallGapsNew
//==============================================================================
rule fillInWallGapsNew
  minInterval 51
  inactive
{
   float wallRadius = llGetLegendaryWallRadius(true); //kbGetMapXSize() / 7.0;

   if (llShouldBuildLegendaryWalls(false) == false)
   {
      xsDisableSelf();
      return;
   }

   // Doctrine gate: MobileNoWalls leaders (Napoleon, Crazy Horse, Hiawatha,
   // Montezuma, Usman) must NEVER build walls. delayWallsNew already honours
   // this; fillInWallGapsNew used to leak through and that's what produced
   // Napoleon's walls in the 16:27 replay.
   if (gLLWallStrategy == cLLWallStrategyMobileNoWalls)
   {
      llLogDecision("WALL", "gap-fill declined - MobileNoWalls doctrine");
      xsDisableSelf();
      return;
   }

  if(aiPlanGetIDByTypeAndVariableType(cPlanBuildWall, cBuildWallPlanWallType, cBuildWallPlanWallTypeRing, true) >= 1)
      return;

   int wallPlanID=aiPlanCreate("fillInWallGapsNew", cPlanBuildWall);
   if (wallPlanID != -1)
   {
         aiPlanSetVariableInt(wallPlanID, cBuildWallPlanWallType, 0, cBuildWallPlanWallTypeRing);
         aiPlanAddUnitType(wallPlanID, gEconUnit, 0, 1, 2);
         aiPlanSetVariableVector(wallPlanID, cBuildWallPlanWallRingCenterPoint, 0, kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID)));
         aiPlanSetVariableFloat(wallPlanID, cBuildWallPlanWallRingRadius, 0.0, wallRadius);
         aiPlanSetVariableInt(wallPlanID, cBuildWallPlanNumberOfGates, 0, llGetLegendaryWallGateCount(true));
         aiPlanSetBaseID(wallPlanID, kbBaseGetMainID(cMyID));
         aiPlanSetEscrowID(wallPlanID, cEconomyEscrowID);
         aiPlanSetDesiredPriority(wallPlanID, 65);
         aiPlanSetActive(wallPlanID, true);
   }
}
//==============================================================================
// RULE wallPlanStallWatchdog
// Wall plans hold gEconUnit villagers exclusively. When a plan can't make
// progress (no buildable arc, wood-starved, base relocated), the held
// villagers go IDLE — that's the bug the user observed in the 16:27 replay.
// This rule walks every active wall plan, ages it via a static map, and
// destroys plans that haven't completed in `cWallPlanMaxAgeSec`. The next
// walling rule tick will recreate a fresh plan with a fresh layout.
//==============================================================================
const int cWallPlanMaxAgeSec = 240;  // 4 min — enough for a normal ring to complete

rule wallPlanStallWatchdog
inactive
minInterval 30
{
   int planID = aiPlanGetIDByTypeAndVariableType(cPlanBuildWall,
                    cBuildWallPlanWallType, cBuildWallPlanWallTypeRing, true);
   if (planID < 0) { return; }

   // User-variable slot 0 holds the creation timestamp (ms). aiPlan user
   // vars default to 0, so a never-stamped plan reads back 0 — we stamp on
   // first sight, then evaluate stall on subsequent ticks.
   int created = aiPlanGetUserVariableInt(planID, 0, 0);
   int now     = xsGetTime();

   if (created == 0)
   {
      aiPlanSetUserVariableInt(planID, 0, 0, now);
      return;
   }

   int ageMs = now - created;
   if (ageMs < (cWallPlanMaxAgeSec * 1000)) { return; }

   // Stalled. Destroy so the held villagers free up and the perpetual
   // rule recreates a fresh plan with a recomputed layout.
   llProbe("plan.wall.stall", "plan=" + planID + " ageMs=" + ageMs +
      " strategy=" + gLLWallStrategy);
   llLogPlanEvent("destroy-stalled", planID,
      "ageSec=" + (ageMs / 1000) + " strategy=" + gLLWallStrategy);
   aiPlanDestroy(planID);
}

//==============================================================================
// RULE bastionUpgradeMonitor
// Make sure we research bastion so our walls are stronger.
//==============================================================================
rule bastionUpgradeMonitor
inactive
minInterval 90
{
   int upgradePlanID = -1;
   int myWallId = getUnit(cUnitTypeAbstractWall, cMyID);

   if ((kbTechGetStatus(cTechBastion) == cTechStatusActive))
   {
      xsDisableSelf();
      return;
   }

   researchSimpleTechByCondition(cTechBastion, 
   []() -> bool { return (kbTechGetStatus(cTechBastion) == cTechStatusObtainable); },
   cUnitTypeAbstractWall, myWallId, 70);
}
//==============================================================================
// factoryWall
// Wall-in the first factory we find.
//==============================================================================
rule factoryWall
inactive
minInterval 10
{
   int factoriesQuery = createSimpleUnitQuery(cUnitTypeFactory, cMyID, cUnitStateABQ);
   int factoriesFound = kbUnitQueryExecute(factoriesQuery);

   if (factoriesFound > 0) {
      vector factoryPos = kbUnitGetPosition(kbUnitQueryGetResult(factoriesQuery, 0));
      kbUnitQueryDestroy(factoriesQuery);

      int wallPlanID = aiPlanCreate("Factory Wall", cPlanBuildWall);
      int numberOfGates = 4;
      float baseWallRadius = 12.0;
      vector baseWallCenter = factoryPos; // Set the center to the factory position

      if (wallPlanID != -1)
      {
         aiPlanSetVariableInt(wallPlanID, cBuildWallPlanWallType, 0, cBuildWallPlanWallTypeRing);
         aiPlanAddUnitType(wallPlanID, cUnitTypeAbstractVillager, 1, 1, 1);
         aiPlanSetVariableVector(wallPlanID, cBuildWallPlanWallRingCenterPoint, 0, baseWallCenter);
         aiPlanSetVariableInt(wallPlanID, cBuildPlanLocationPreference, 0, cBuildingPlacementPreferenceFront);
         aiPlanSetVariableFloat(wallPlanID, cBuildWallPlanWallRingRadius, 0, baseWallRadius);
         aiPlanSetVariableInt(wallPlanID, cBuildWallPlanNumberOfGates, 0, numberOfGates);
         aiPlanSetBaseID(wallPlanID, kbBaseGetMainID(cMyID));
         aiPlanSetEscrowID(wallPlanID, cEconomyEscrowID);
         aiPlanSetDesiredPriority(wallPlanID, 75);
         aiPlanSetActive(wallPlanID, true);
         debugBuildings("Enabling Factory Wall Plan for Base ID: " + kbBaseGetMainID(cMyID));
         xsDisableSelf();
      }
   }
}
//==============================================================================
// RULE rebuildLostForts
// Make sure we maintain the maximum number of forts.
//==============================================================================
rule rebuildLostForts
minInterval 10
inactive
{
   int fortsWanted = llGetWantedFortCount();

   if (fortsWanted < 1)
   {
      if (gFortRebuildPlan >= 0)
      {
         aiPlanDestroy(gFortRebuildPlan);
         gFortRebuildPlan = -1;
      }
      return;
   }

   llVerboseEcho("Fort Limit: "+kbGetBuildLimit(cMyID, gFortUnit)+"Forts We Have: "
   +kbUnitCount(cMyID, gFortUnit, cUnitStateABQ)+"");
if (fortsWanted > kbUnitCount(cMyID, gFortUnit, cUnitStateABQ)) {
		llVerboseEcho("I need to rebuild forts now!");
      // Nobody is making a fort, let's start a plan.
      if (gFortRebuildPlan == -1) {
         gFortRebuildPlan = aiPlanCreate("Fortress Build Plan", cPlanBuild);
         int heroQuery = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
         int numberHeroesFound = kbUnitQueryExecute(heroQuery);
         int heroPlanID = -1;
         int heroID = -1;
         int unitID = -1;

         if (numberHeroesFound < 1) {
            return;
         }

         aiPlanSetVariableInt(gFortRebuildPlan, cBuildPlanBuildingTypeID, 0, gFortUnit);
         // Priority.
         aiPlanSetDesiredPriority(gFortRebuildPlan, 100);
         aiPlanSetDesiredResourcePriority(gFortRebuildPlan, 100);
         // Mil vs. Econ.
         aiPlanSetMilitary(gFortRebuildPlan, true);
         aiPlanSetEconomy(gFortRebuildPlan, false);
         // Escrow.
         aiPlanSetEscrowID(gFortRebuildPlan, cMilitaryEscrowID);
         // Builders.
         for (int n = 0; n < numberHeroesFound; n++)
         {
            unitID = kbUnitQueryGetResult(heroQuery, n);
            if (unitID < 0)
            {
               continue;
            }
            // if (kbProtoUnitCanTrain(kbUnitGetProtoUnitID(unitID), cUnitTypeTradingPost) == false)
            // {
            //    continue;
            // }
            heroPlanID = kbUnitGetPlanID(heroID);
            if ((heroPlanID < 0))
            {
               heroID = unitID;
               break;
            }
         }
         if (heroID != -1) // We have found a suitable Hero, so we will add him to the plan.
         {
            debugBuildings("We are adding 1 " + kbGetProtoUnitName(kbUnitGetProtoUnitID(heroID)) + " with ID: " +
               heroID + " to our Fort build plan.");
            aiPlanAddUnitType(gFortRebuildPlan, cUnitTypeHero, 1, 1, 1);
            aiPlanAddUnit(gFortRebuildPlan, heroID);
            aiPlanSetNoMoreUnits(gFortRebuildPlan, true);
            int forwardBaseFortQuery = createSimpleUnitQuery(gFortUnit, cMyID, cUnitStateABQ);
            kbUnitQuerySetMaximumDistance(forwardBaseFortQuery, 50.0);
            kbUnitQuerySetPosition(forwardBaseFortQuery, gForwardBaseLocation);
            if ((gLLPreferForwardFortifiedBase == true) && (gForwardBaseLocation != cInvalidVector) &&
               (kbUnitQueryExecute(forwardBaseFortQuery) < 1)) {
               aiPlanSetVariableVector(gFortRebuildPlan, cBuildPlanCenterPosition, 0, gForwardBaseLocation);
               aiPlanSetVariableFloat(gFortRebuildPlan, cBuildPlanCenterPositionDistance, 0, 30.0);
            }
         } else {
            aiPlanDestroy(gFortRebuildPlan);
            return;
         }
      
         aiPlanSetActive(gFortRebuildPlan);
         llVerboseEcho("Fort building activated!");
         llVerboseEcho("**** STARTING FORT PLAN, plan ID "+gFortRebuildPlan);
      }
	} else {
      aiPlanDestroy(gFortRebuildPlan);
      gFortRebuildPlan = -1;
   }

   // Start training at the forward base...
   if (kbBaseGetActive(cMyID, gIslandBaseID) == true) {
      updateSecondaryBaseMilitaryTrainPlans(gIslandBaseID);
   } else {
      updateSecondaryBaseMilitaryTrainPlans(gForwardBaseID);
   }

	return;
}
//==============================================================================
// RULE fortUpgradeMonitor
// Make sure we upgrade those forts!
//==============================================================================
rule fortUpgradeMonitor
inactive
minInterval 90
{
   int upgradePlanID = -1;
   int myFortId = getUnit(cUnitTypeFortFrontier, cMyID);

   if ((kbTechGetStatus(cTechRevetment) == cTechStatusActive) && (kbTechGetStatus(cTechStarFort) == cTechStatusActive))
   {
      xsDisableSelf();
      return;
   }

   researchSimpleTechByCondition(cTechRevetment, 
   []() -> bool { return (kbTechGetStatus(cTechRevetment) == cTechStatusObtainable); },
   cUnitTypeFortFrontier, myFortId, 60);
   researchSimpleTechByCondition(cTechStarFort, 
   []() -> bool { return (kbTechGetStatus(cTechStarFort) == cTechStatusObtainable); },
   cUnitTypeFortFrontier, myFortId, 60);
}
//==============================================================================
// forwardBaseWall
// Wall-in the forward base.
//==============================================================================
rule forwardBaseWall
inactive
minInterval 10
{
   if (gForwardBaseState == cForwardBaseStateNone || gForwardBaseID == -1)
   {
      return;
   } else if (distance(kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID)), 
               kbBaseGetLocation(cMyID, gForwardBaseID)) < 20.0) {
      xsDisableSelf();
   }
   
   int wallPlanID = aiPlanCreate("Forward base wall", cPlanBuildWall);
   int numberOfGates = 4;
   float baseWallRadius = 27.0;
   vector baseWallCenter = gForwardBaseLocation;

   //(gForwardBaseLocation, gForwardBaseID, 95, 4);
   //buildPentagonWall(gForwardBaseLocation, gForwardBaseID, 95, 5);
   //buildPentagonWall(gForwardBaseLocation, -1, 95, 5);

   if (wallPlanID != -1)
   {
      aiPlanSetVariableInt(wallPlanID, cBuildWallPlanWallType, 0, cBuildWallPlanWallTypeRing);
      aiPlanAddUnitType(wallPlanID, cUnitTypeAbstractVillager, 1, 1, 1);
      aiPlanSetVariableVector(wallPlanID, cBuildWallPlanWallRingCenterPoint, 0, baseWallCenter);
      aiPlanSetVariableInt(wallPlanID, cBuildPlanLocationPreference, 0, cBuildingPlacementPreferenceFront);
      aiPlanSetVariableFloat(wallPlanID, cBuildWallPlanWallRingRadius, 0, baseWallRadius);
      aiPlanSetVariableInt(wallPlanID, cBuildWallPlanNumberOfGates, 0, numberOfGates);
      aiPlanSetBaseID(wallPlanID, kbBaseGetMainID(cMyID));
      aiPlanSetEscrowID(wallPlanID, cMilitaryEscrowID);
      aiPlanSetDesiredPriority(wallPlanID, 75);
      aiPlanSetActive(wallPlanID, true);
      //sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyWhenIWallIn);
      debugBuildings("Enabling Wall Plan for Base ID: " + kbBaseGetMainID(cMyID));
   }
   xsEnableRule("forwardBaseStables");
   xsEnableRule("forwardBaseTowers");
   xsDisableSelf();
}
//==============================================================================
// forwardBaseStables
// Build stables and barracks at the forward base.
//==============================================================================
rule forwardBaseStables
inactive
minInterval 10
{
   int forwardBaseStablesVal = kbUnitQueryExecute(createSimpleUnitQuery(cUnitTypeAbstractStables, cMyID, 
   cUnitStateABQ, gForwardBaseLocation, 40.0));
   int forwardBaseBarracksVal = kbUnitQueryExecute(createSimpleUnitQuery(cUnitTypeBarracks, cMyID, 
   cUnitStateABQ, gForwardBaseLocation, 40.0));
   llVerboseEcho("Stables: "+forwardBaseStablesVal+" Base State: "+gForwardBaseState+"");
   if (gForwardBaseState == cForwardBaseStateNone)
   {
      return;
   } 
   
   if (gForwardBaseState == cForwardBaseStateActive && forwardBaseStablesVal < 1
      && aiPlanGetActive(gForwardBaseStablesPlan) == false) {
      aiPlanDestroy(gForwardBaseStablesPlan);
      gForwardBaseStablesPlan = createSpacedLocationBuildPlan(cUnitTypeStable, 1, 45, true, cMilitaryEscrowID, gForwardBaseLocation, 1);
      llVerboseEcho("Stables Plan created!");
   } else if (gForwardBaseState == cForwardBaseStateActive && forwardBaseStablesVal > 0) {
      // Start training at the forward base...
      if (kbBaseGetActive(cMyID, gIslandBaseID) == true) {
         updateSecondaryBaseMilitaryTrainPlans(gIslandBaseID);
      } else {
         updateSecondaryBaseMilitaryTrainPlans(gForwardBaseID);
      }
   }
   if (gForwardBaseState == cForwardBaseStateActive && forwardBaseBarracksVal < 1
      && aiPlanGetActive(gForwardBaseBarracksPlan) == false) {
      aiPlanDestroy(gForwardBaseBarracksPlan);
      gForwardBaseBarracksPlan = createSpacedLocationBuildPlan(cUnitTypeBarracks, 1, 45, true, cMilitaryEscrowID, gForwardBaseLocation, 1);
      llVerboseEcho("Barracks Plan created!");
   } else if (gForwardBaseState == cForwardBaseStateActive && forwardBaseBarracksVal > 0) {
      // Start training at the forward base...
      if (kbBaseGetActive(cMyID, gIslandBaseID) == true) {
         updateSecondaryBaseMilitaryTrainPlans(gIslandBaseID);
      } else {
         updateSecondaryBaseMilitaryTrainPlans(gForwardBaseID);
      }
   }
}
//==============================================================================
// forwardBaseTowers
// Build three towers at the forward base if we can.
//==============================================================================
rule forwardBaseTowers
inactive
minInterval 10
{
   int forwardBaseTowersVal = kbUnitQueryExecute(createSimpleUnitQuery(gTowerUnit, cMyID, cUnitStateABQ, 
   gForwardBaseLocation, 40.0));
   int additionalTowersAvailable = kbGetBuildLimit(cMyID, gTowerUnit) - kbUnitQueryExecute(createSimpleUnitQuery(gTowerUnit, cMyID, cUnitStateABQ));
   int desiredForwardBaseTowers = gLLForwardBaseTowerCount;
   if (gForwardBaseState == cForwardBaseStateNone)
   {
      return;
   }

   if (desiredForwardBaseTowers < 0)
   {
      desiredForwardBaseTowers = 0;
   }

   if (additionalTowersAvailable > desiredForwardBaseTowers) {
      additionalTowersAvailable = desiredForwardBaseTowers;
   }

   if ((gForwardBaseState == cForwardBaseStateActive) && (desiredForwardBaseTowers > 0) &&
      (forwardBaseTowersVal < desiredForwardBaseTowers) && (additionalTowersAvailable > 0)) {
      createSpacedLocationBuildPlan(gTowerUnit, additionalTowersAvailable, 50, true, cMilitaryEscrowID, gForwardBaseLocation, 1);
   }
}
//==============================================================================
// maxFortManager
// Maintain the maximum number of forts at all times.
//==============================================================================
// rule maxFortManager
// inactive
// minInterval 40
// {
//    static int fortPlan = -1;
//    int villagerPlan = -1;
//    int limit = 0;

//    limit = kbGetBuildLimit(cMyID, gFortUnit);
//    if (limit < 1)
//       return;

//    if (fortPlan < 0)
//    {
//       fortPlan = createSimpleMaintainPlan(gFortUnit, limit, true, -1, 1);
//       aiPlanSetDesiredPriority(fortPlan, 85);
//       //aiPlanSetVariableInt(missionaryPlan, cTrainPlanBuildFromType, 0, cUnitTypeChurch);
//       llVerboseEcho("Fort maintain plan!");
//    }
//    else
//    {
//       aiPlanSetVariableInt(fortPlan, cTrainPlanNumberToMaintain, 0, limit);
//    }
// }
//==============================================================================
// maxTowerManager
// Maintain the maximum number of towers at all times.
//==============================================================================
rule maxTowerManager
inactive
minInterval 10
{
   int limit = kbGetBuildLimit(cMyID, gTowerUnit);
   int unitQuery = createSimpleUnitQuery(gTowerUnit, cMyID, cUnitStateABQ);
   int numberFound = kbUnitQueryExecute(unitQuery);
   int age = kbGetAge();
//aiPlanGetIDByTypeAndVariableType(cPlanBuild, cBuildPlanBuildingTypeID, gTowerUnit) < 0
   if (numberFound < limit && age >= cAge4)
   {
      createSimpleBuildPlan(gTowerUnit, 1, 75, false, cMilitaryEscrowID, kbBaseGetMainID(cMyID), 1);
   }
   updateWantedTowers();
}
//==============================================================================
// establishTradePostsWithNatives
// Double-check to make sure we are trying to maintain native alliances.
//==============================================================================
rule establishTradePostsWithNatives
inactive
minInterval 10
{
   int unitQuery = createSimpleUnitQuery(cUnitTypeSocket, cPlayerRelationAny, cUnitStateAny);
   int numberFound = kbUnitQueryExecute(unitQuery);
   vector mainBaseVec = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
   int mainBaseGroupId = kbAreaGroupGetIDByPosition(mainBaseVec);
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;
   int unitID = -1;

   for (i = 0; < numberFound) {
      unitID = kbUnitQueryGetResult(unitQuery, i);
      unitLocation = kbUnitGetPosition(unitID);
      unitLocationId = kbAreaGetIDByPosition(unitLocation);
      unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      if (getUnitByLocation(cUnitTypeTradingPost, cPlayerRelationAny, cUnitStateABQ, unitLocation, 10.0) > 0)
      {
         continue;
      } else if (kbAreAreaGroupsPassableByLand(mainBaseGroupId, unitLocationGroupId) == true) {
         unitLocation = kbUnitGetPosition(unitID);
      }
   }
   
   if (unitLocation != cInvalidVector && aiPlanGetActive(gTradePostBuildingPlan) == false) {
      aiPlanDestroy(gTradePostBuildingPlan);
      gTradePostBuildingPlan = aiPlanCreate("Trading Post Build Plan", cPlanBuild);
      aiPlanSetVariableInt(gTradePostBuildingPlan, cBuildPlanBuildingTypeID, 0, cUnitTypeTradingPost);
      aiPlanSetVariableInt(gTradePostBuildingPlan, cBuildPlanSocketID, 0, unitID);

      int villagerQuery = createSimpleUnitQuery(cUnitTypeAbstractVillager, cMyID, cUnitStateAlive);
      aiPlanAddUnitType(gTradePostBuildingPlan, cUnitTypeAbstractVillager, 1, 1, 1);
      aiPlanAddUnit(gTradePostBuildingPlan, kbUnitQueryGetResult(villagerQuery, 0));
      aiPlanSetDesiredPriority(gTradePostBuildingPlan, 60);
      aiPlanSetActive(gTradePostBuildingPlan);
   }
}
//==============================================================================
// lakotaTeePeeManager
// Maintain the maximum number of teepees at all times.
//==============================================================================
rule lakotaTeePeeManager
active
minInterval 10
{
   if (cMyCiv != cCivXPSioux)
   {
      xsDisableSelf();
      return;
   }
   int limit = kbGetBuildLimit(cMyID, cUnitTypeTeepee);
   int unitQuery = createSimpleUnitQuery(cUnitTypeTeepee, cMyID, cUnitStateABQ);
   int numberFound = kbUnitQueryExecute(unitQuery);
   int age = kbGetAge();

   if (age == cAge1) {
      limit = 1;
   } else if (age == cAge2) {
      limit = 3;
   } else if (age == cAge3) {
      limit = 7;
   }

   if (numberFound < limit && aiPlanGetIDByTypeAndVariableType(cPlanBuild, cBuildPlanBuildingTypeID, cUnitTypeTeepee) < 0)
   {
      createSimpleBuildPlan(cUnitTypeTeepee, 1, 75, false, cEconomyEscrowID, kbBaseGetMainID(cMyID), 1);
   }
}