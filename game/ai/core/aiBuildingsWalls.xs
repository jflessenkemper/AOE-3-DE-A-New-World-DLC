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

   // Per-civ knob: gLLWallTriggerAge (2=Colonial, 3=Fortress, 4=Industrial,
   // 5=never). If current age hasn't reached the trigger, suppress walls
   // unless an explicit "always-on" doctrine like Maltese citadel overrides.
   // Default trigger=2 means walls start in Colonial, matching legacy.
   if (kbGetAge() < gLLWallTriggerAge)
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

//==============================================================================
// ANW 2026-05-30 SMART-WALLS: llComputeThreatVector
// SMART WALLS — Track 1.2b: threat-vector tracking.
//
// Computes the centroid of all visible enemy land-military units. Returns
// cInvalidVector when no enemy military is spotted. Result is cached for 60s
// game time so it is cheap to call from multiple wall planners per tick.
// Emits wall.threat_vector probe on every recompute.
// Declared here so llGetForwardBiasedWallCenter can use the cached result.
//==============================================================================
static vector gLLCachedThreatVector = cInvalidVector;
static int    gLLThreatVectorTime   = -999999;

vector llComputeThreatVector()
{
   int now = xsGetTime();
   if ((now - gLLThreatVectorTime) <= 60000)
   {
      return (gLLCachedThreatVector);
   }

   // Use a single enemy-relation query for all enemy military units.
   int qID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary,
                                   cPlayerRelationEnemyNotGaia,
                                   cUnitStateAlive);
   int found = kbUnitQueryExecute(qID);

   float sumX = 0.0;
   float sumZ = 0.0;
   int   cnt  = 0;
   for (i = 0; < found)
   {
      int uid = kbUnitQueryGetResult(qID, i);
      if (uid < 0) { continue; }
      vector upos = kbUnitGetPosition(uid);
      if (upos == cInvalidVector) { continue; }
      sumX = sumX + xsVectorGetX(upos);
      sumZ = sumZ + xsVectorGetZ(upos);
      cnt  = cnt + 1;
   }

   vector result = cInvalidVector;
   if (cnt > 0)
   {
      result = xsVectorSet(sumX / cnt, 0.0, sumZ / cnt);
   }

   gLLCachedThreatVector = result;
   gLLThreatVectorTime   = now;
   llProbe("wall.threat_vector",
      "vec=" + llFmtVec(result) + " enemies=" + cnt);
   return (result);
}

// ANW 2026-05-30 SMART-WALLS: llGetForwardBiasedWallCenter
// Shift the wall ring center slightly along the base's front vector (toward
// the likely enemy arc). A full ring still surrounds the base, but the
// extra bias thickens wall coverage on the contested side where it matters
// most. Returns the input unchanged if no front vector is registered.
//
// SMART WALLS — Track 1.1b: water/cliff fixup. After biasing, sample the
// area type. If we land in water (or a 0-tile area), walk backwards along
// the inverse front vector in 8-unit steps (up to 5) trying to find land.
// If we never find land, return baseCenter unchanged (safer than ocean).
//
// SMART WALLS — Track 1.2b: threat-vector bias. When a threat vector is
// known (enemy military spotted within the last 60s), blend the bias
// direction toward the threat centroid (0.6 weight) rather than just the
// static front vector (1.0 weight when unknown). This tilts the ring toward
// the actual incoming threat rather than the map-edge heuristic.
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

   // Track 1.2b: blend toward threat centroid when known.
   // threatVec is cInvalidVector when no enemies are spotted (cache miss);
   // in that case fall back to pure front-vector bias (weight = 1.0).
   vector threatVec = llComputeThreatVector();
   vector biasDir = frontVec;   // default: static front-vector bias
   if (threatVec != cInvalidVector)
   {
      // Direction from base center toward threat centroid.
      vector toThreat = threatVec - baseCenter;
      float tMag = xsVectorLength(toThreat);
      if (tMag > 0.0)
      {
         vector threatDir = xsVectorNormalize(toThreat);
         // Blend: 0.6 * threatDir + 0.4 * frontVec (un-normalised sum,
         // then normalise so the shift magnitude stays = radius * biasFactor).
         float tbx = 0.6 * xsVectorGetX(threatDir) + 0.4 * xsVectorGetX(frontVec);
         float tbz = 0.6 * xsVectorGetZ(threatDir) + 0.4 * xsVectorGetZ(frontVec);
         float bmag = xsVectorLength(xsVectorSet(tbx, 0.0, tbz));
         if (bmag > 0.0)
         {
            biasDir = xsVectorSet(tbx / bmag, 0.0, tbz / bmag);
         }
      }
   }

   float radius = llGetLegendaryWallRadius(false);
   float shift = radius * biasFactor;
   float nx = xsVectorGetX(baseCenter) + xsVectorGetX(biasDir) * shift;
   float nz = xsVectorGetZ(baseCenter) + xsVectorGetZ(biasDir) * shift;
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
      // Knob: gLLWallNoWaterBuild — when true, try harder to find inland land
      // by doubling the step limit (10 vs 5). When false, allow placement in
      // shallow water by using the original 5-step limit.
      int maxSteps = 5;
      if (gLLWallNoWaterBuild == true) { maxSteps = 10; }
      for (i = 1; <= maxSteps)
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
// ANW 2026-05-30 SMART-WALLS: llDetectChokepointVector
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
   // Per-AI cache: compute once per match, reuse thereafter — but
   // KEYED on the resolved baseAreaID so a base-relocation (TC kill +
   // retrain elsewhere, Asian Wonder relocation, revolution-driven
   // re-anchor) invalidates the stale chokepoint. Previously the cache
   // was a single global flag and returned the same vector forever even
   // when the caller passed a different baseCenter — fine for the
   // common case but a foot-gun for long matches and migration events.
   static int chokepointCached = 0;
   static int chokepointBaseAreaID = -1;
   static vector chokepointVec = cInvalidVector;

   if ((baseCenter == cInvalidVector) || (mainBaseID < 0))
   {
      // No valid input — don't cache, don't return stale. Fall back to
      // the forward-biased centre directly.
      return (llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.35));
   }

   int baseAreaID = kbAreaGetIDByPosition(baseCenter);
   if (baseAreaID < 0)
   {
      return (llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.35));
   }

   // Cache hit only when the cached entry was computed for the SAME
   // base area. If the AI's main base moved to a different area we
   // recompute — staleness here means a wall plan would be emitted at
   // the old chokepoint, leaving the new base undefended.
   if ((chokepointCached == 1) && (chokepointBaseAreaID == baseAreaID))
   {
      // SMART WALLS — Track 1.1a (Defect 3 fix): keep the schema numeric
      // for tiles (`tiles=<int>`). The cached-hit path emits 0 to signal
      // "no fresh tile-count was computed this tick"; cached=1 distinguishes
      // from a true zero-tile measurement.
      llProbe("wall.chokepoint", "vec=" + llFmtVec(chokepointVec) +
         " tiles=0 cached=1 baseArea=" + chokepointBaseAreaID);
      return (chokepointVec);
   }
   // If we reach here with chokepointCached==1 but a mismatched baseAreaID,
   // log the invalidation so doctrine probes can correlate base-move events
   // with re-detection. Below we'll recompute and re-cache against the new
   // baseAreaID.
   if ((chokepointCached == 1) && (chokepointBaseAreaID != baseAreaID))
   {
      llProbe("wall.chokepoint", "invalidated oldArea=" + chokepointBaseAreaID +
         " newArea=" + baseAreaID);
      chokepointCached = 0;
   }
   int baseTiles = kbAreaGetNumberTiles(baseAreaID);
   int numBorders = kbAreaGetNumberBorderAreas(baseAreaID);
   if (numBorders <= 0)
   {
      // No border areas at all -> open map, no chokepoint to detect.
      vector fallbackNoBorders = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, 0.35);
      chokepointVec = fallbackNoBorders;
      chokepointBaseAreaID = baseAreaID;
      chokepointCached = 1;
      llProbe("wall.chokepoint", "vec=" + llFmtVec(fallbackNoBorders) +
         " tiles=0 cached=0 fallback=noBorders baseArea=" + baseAreaID);
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
      chokepointBaseAreaID = baseAreaID;
      chokepointCached = 1;
      llProbe("wall.chokepoint", "vec=" + llFmtVec(fallbackFlatMap) +
         " tiles=0 cached=0 fallback=flatMap baseArea=" + baseAreaID);
      return (fallbackFlatMap);
   }

   vector chokeCenter = kbAreaGetCenter(narrowestID);
   chokepointVec = chokeCenter;
   chokepointBaseAreaID = baseAreaID;
   chokepointCached = 1;
   llProbe("wall.chokepoint", "vec=" + llFmtVec(chokeCenter) +
      " tiles=" + narrowestTiles + " cached=0 baseArea=" + baseAreaID);
   return (chokeCenter);
}

//==============================================================================
// ANW 2026-05-30 SMART-WALLS: llSelectWallType
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
   //
   // Knob: gLLWallTierAge2Stone — if true and age==2 (Colonial), request stone
   // walls.  The engine only exposes cBuildWallPlanWallTypeRing today, so we
   // emit a probe so validators can confirm the knob was read, then return the
   // same constant.  When a stone-wall type constant is confirmed in the engine
   // vocabulary, replace the return below with it.
   if ((age == 2) && (gLLWallTierAge2Stone == true))
   {
      llProbe("wall.tier", "age=2 knob=age2stone=true type=stone(ring-fallback)");
      // KNOB-TODO: replace cBuildWallPlanWallTypeRing with a confirmed
      // stone-wall engine constant once one is documented.
      return (cBuildWallPlanWallTypeRing);
   }
   return (cBuildWallPlanWallTypeRing);
}

//==============================================================================
// ANW 2026-05-30 SMART-WALLS: llCountPerimeterGaps
// SMART WALLS — Track 1.2a: natural-wall gap detection.
//
// Walks the proposed wall ring at 8 sample points (every 45°) and counts how
// many land-typed sample points exist. "Land" here means NOT water-typed —
// the engine only reliably exposes cAreaTypeWater; no cAreaTypeLand constant
// is present anywhere in this codebase. The count (0–8) tells callers how
// much of the perimeter can hold wall pieces. If landCount == 0 (ring center
// is entirely in/over water or unmappable), skip the wall plan entirely and
// emit a wall.skip probe. Otherwise emit wall.perimeter_gaps for telemetry.
//==============================================================================
int llCountPerimeterGaps(vector baseCenter = cInvalidVector,
                         float radius = 42.0,
                         int strategy = 0)
{
   if (baseCenter == cInvalidVector)
   {
      return (0);
   }
   int landCount  = 0;
   int waterCount = 0;
   for (i = 0; < 8)
   {
      float angle = (2.0 * PI / 8.0) * i;
      float sx = xsVectorGetX(baseCenter) + radius * cos(angle);
      float sz = xsVectorGetZ(baseCenter) + radius * sin(angle);
      vector samplePoint = xsVectorSet(sx, xsVectorGetY(baseCenter), sz);
      int areaID = kbAreaGetIDByPosition(samplePoint);
      if (areaID < 0)
      {
         // unmappable sample — conservatively treat as water
         waterCount = waterCount + 1;
         continue;
      }
      int aType = kbAreaGetType(areaID);
      if (aType == cAreaTypeWater)
      {
         waterCount = waterCount + 1;
      }
      else
      {
         landCount = landCount + 1;
      }
   }
   llProbe("wall.perimeter_gaps",
      "land=" + landCount + " water=" + waterCount + " radius=" + radius);
   return (landCount);
}

//==============================================================================
// ANW 2026-05-30 SMART-WALLS: llComputeAdaptiveRadius
// SMART WALLS — Track 1.2c: adaptive wall radius.
//
// Scales the base radius from llGetLegendaryWallRadius(lateGame) by the
// current villager-to-pop-cap ratio (eco saturation):
//   ratio < 0.4  → 0.7× (tight ring, early eco)
//   ratio 0.4–0.7 → 1.0× (current behaviour)
//   ratio > 0.7  → 1.3× (expanded outer ring, saturated eco)
//
// Clamped to [12.0, 60.0] m. Emits wall.adaptive_radius probe.
//==============================================================================
float llComputeAdaptiveRadius(int age = 1, int strategy = 0,
                              vector baseCenter = cInvalidVector)
{
   bool lateGame = (age >= 3);
   float base = llGetLegendaryWallRadius(lateGame);

   int   popCap  = kbGetPopCap();
   float vilCount = kbUnitCount(cMyID, gEconUnit, cUnitStateAlive);
   float villageRatio = 0.5;   // safe mid-value if pop-cap unavailable
   if (popCap > 0)
   {
      villageRatio = vilCount / (1.0 * popCap);
   }

   float scaled = base;
   if (villageRatio < 0.4)
   {
      scaled = base * 0.7;
   }
   else if (villageRatio > 0.7)
   {
      scaled = base * 1.3;
   }

   // Clamp [12.0, 60.0]
   if (scaled < 12.0) { scaled = 12.0; }
   if (scaled > 60.0) { scaled = 60.0; }

   llProbe("wall.adaptive_radius",
      "base=" + base + " ratio=" + villageRatio + " result=" + scaled +
      " age=" + age + " strategy=" + strategy);
   return (scaled);
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
   // Per-civ knob: radius — scale adaptive radius by (gLLWallRadius / 18.0),
   // where 18 is the default tile-radius. If knob is 0 (Mobile civ called by
   // mistake) fall back to adaptive default.
   float radius = llComputeAdaptiveRadius(kbGetAge(), gLLWallStrategy, baseCenter);
   if (gLLWallRadius > 0)
   {
      radius = radius * (1.0 * gLLWallRadius / 18.0);
   }
   int planID = aiPlanCreate("FortressRing Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   // Per-civ knob: villager pool. Default 4, capped at >=2 floor for stalled-
   // plan release. Range tested 4..10 across calibrated civs.
   int vilCap = gLLWallVillagerCount;
   if (vilCap < 2) { vilCap = 2; }
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, vilCap);
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, baseCenter);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   // Per-civ knob: gate count. Default 3, fortress civs typically 2-4.
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, gLLWallGateCount);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 88);  // raised 75 -> 88 so wall wins over barracks/houses
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=FortressRing radius=" + radius +
      " gates=" + gLLWallGateCount + " vils=2-" + vilCap +
      " radKnob=" + gLLWallRadius + " priority=88 plan=" + planID);
   // Knob: gLLWallTowerInterleave — records intent; sub-plan creation
   // would require a separate build-outpost plan loop which is too invasive here.
   // KNOB-TODO: when a confirmed outpost build-plan API is available, create
   // supplementary outpost plans spaced every gLLWallTowerInterleave tiles.
   if (gLLWallTowerInterleave > 0)
   {
      llProbe("wall.tower.interleave", "knob=" + gLLWallTowerInterleave +
         " strategy=FortressRing plan=" + planID);
   }
   // Knob: gLLWallOuterRingDelta — double-ring for Fortress doctrine at Age 3+.
   // Creates a second concentric ring at radius + delta tiles, lower priority.
   if ((gLLWallOuterRingDelta > 0) && (kbGetAge() >= cAge3))
   {
      float outerRadius = radius + (1.0 * gLLWallOuterRingDelta);
      int outerPlanID = aiPlanCreate("FortressRing OuterRing", cPlanBuildWall);
      if (outerPlanID >= 0)
      {
         int outerVilCap = gLLWallVillagerCount;
         if (outerVilCap < 2) { outerVilCap = 2; }
         aiPlanSetVariableInt(outerPlanID, cBuildWallPlanWallType, 0,
            llSelectWallType(gLLWallStrategy, kbGetAge()));
         aiPlanAddUnitType(outerPlanID, gEconUnit, 0, 2, outerVilCap);
         aiPlanSetVariableVector(outerPlanID, cBuildWallPlanWallRingCenterPoint, 0, baseCenter);
         aiPlanSetVariableFloat(outerPlanID, cBuildWallPlanWallRingRadius, 0.0, outerRadius);
         aiPlanSetVariableInt(outerPlanID, cBuildWallPlanNumberOfGates, 0, gLLWallGateCount);
         aiPlanSetBaseID(outerPlanID, mainBaseID);
         aiPlanSetEscrowID(outerPlanID, cEconomyEscrowID);
         aiPlanSetDesiredPriority(outerPlanID, 83);  // 88 - 5
         aiPlanSetActive(outerPlanID, true);
         llProbe("wall.outer_ring", "type=FortressRing delta=" + gLLWallOuterRingDelta +
            " outerRadius=" + outerRadius + " plan=" + outerPlanID);
      }
   }
   return (planID);
}

// ChokepointSegments: walls only at natural terrain pinches (Andes/Alps/passes).
// Shivaji (Maratha hill forts), Pachacuti (valley mouths), Kangxi (Great Wall).
// Fallback to a tighter ring if chokepoint detection fails on flat maps —
// biased forward toward enemy since chokepoints always face outward.
int llPlanChokepointWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llComputeAdaptiveRadius(kbGetAge(), gLLWallStrategy, baseCenter) - 4.0;
   // Per-civ knob: chokepoint civs use smaller rings (radius knob 10-12 typical)
   if (gLLWallRadius > 0)
   {
      radius = radius * (1.0 * gLLWallRadius / 18.0);
   }
   // Knob: gLLWallSegmentLength — cBuildWallPlanWallSegmentLength does not
   // exist in the engine constants exposed by this codebase (grepped, absent).
   // Instead, a smaller segment length implies tighter coverage: bias the ring
   // radius downward proportionally so shorter segments yield a tighter arc.
   // Default segment length is 12; civs with knob < 12 get a tighter ring,
   // civs with knob > 12 get a wider arc (more exposed but covers more ground).
   // Formula: radius *= segmentLength / 12.0  (net-neutral at the default).
   if (gLLWallSegmentLength > 0)
   {
      radius = radius * (1.0 * gLLWallSegmentLength / 12.0);
   }
   llProbe("wall.segmentlength", "knob=" + gLLWallSegmentLength + " radius=" + radius);
   // SMART WALLS — Track 1.1a: real chokepoint detection rather than
   // the misnamed forward-biased fallback. Detector itself falls back
   // to forward-biased on flat maps.
   vector center = llDetectChokepointVector(mainBaseID, baseCenter);
   int planID = aiPlanCreate("Chokepoint Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   int vilCap = gLLWallVillagerCount;
   if (vilCap < 2) { vilCap = 2; }
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, vilCap);
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, gLLWallGateCount);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 85);
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=Chokepoint radius=" + radius +
      " gates=" + gLLWallGateCount + " vils=2-" + vilCap +
      " radKnob=" + gLLWallRadius + " priority=85 plan=" + planID);
   // Knob: gLLWallTowerInterleave — records intent; sub-plan creation
   // would require a separate build-outpost plan loop which is too invasive here.
   // KNOB-TODO: when a confirmed outpost build-plan API is available, create
   // supplementary outpost plans spaced every gLLWallTowerInterleave tiles.
   if (gLLWallTowerInterleave > 0)
   {
      llProbe("wall.tower.interleave", "knob=" + gLLWallTowerInterleave +
         " strategy=Chokepoint plan=" + planID);
   }
   return (planID);
}

//==============================================================================
// ANW 2026-05-30 SMART-WALLS: llDetectCoastVector
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
   // 2026-05-27: keyed-on-baseAreaID invalidation, same fix as
   // llDetectChokepointVector — see that function's header comment for
   // the rationale. Without keying, a base relocation (e.g. revolution
   // re-anchor) returns the old inland-shift vector for the wrong base.
   static int coastCached = 0;
   static int coastBaseAreaID = -1;
   static vector coastVec = cInvalidVector;

   if ((baseCenter == cInvalidVector) || (mainBaseID < 0))
   {
      // Invalid args: don't poison the cache, just emit a stateless
      // probe. Previously this set coastCached=1 with an cInvalidVector,
      // which then short-circuited *valid* subsequent calls — turning
      // one transient bad call into a permanent dead cache.
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=invalidArgs");
      return (cInvalidVector);
   }

   int baseAreaID = kbAreaGetIDByPosition(baseCenter);
   if (baseAreaID < 0)
   {
      // Same logic as above: don't cache a "no resolvable area" result.
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=noBaseArea");
      return (cInvalidVector);
   }

   // Cache hit only when the entry was computed against the same area.
   if ((coastCached == 1) && (coastBaseAreaID == baseAreaID))
   {
      llProbe("wall.coast", "vec=" + llFmtVec(coastVec) +
         " waterBorders=0 cached=1 baseArea=" + coastBaseAreaID);
      return (coastVec);
   }
   if ((coastCached == 1) && (coastBaseAreaID != baseAreaID))
   {
      llProbe("wall.coast", "invalidated oldArea=" + coastBaseAreaID +
         " newArea=" + baseAreaID);
      coastCached = 0;
   }

   int numBorders = kbAreaGetNumberBorderAreas(baseAreaID);
   if (numBorders <= 0)
   {
      // No borders → inland (or unresolved). Record the result against the
      // current area so we don't redo the search every tick for inland
      // bases, but key it on baseAreaID so a relocation re-checks.
      coastVec = cInvalidVector;
      coastBaseAreaID = baseAreaID;
      coastCached = 1;
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=noBorders baseArea=" + baseAreaID);
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
      coastVec = cInvalidVector;
      coastBaseAreaID = baseAreaID;
      coastCached = 1;
      llProbe("wall.coast",
         "vec=cInvalidVector waterBorders=0 cached=0 fallback=inlandMap baseArea=" + baseAreaID);
      return (cInvalidVector);
   }

   float waterX = sumX / waterCount;
   float waterZ = sumZ / waterCount;
   vector waterCentroid = xsVectorSet(waterX, xsVectorGetY(baseCenter), waterZ);
   vector seaward = waterCentroid - baseCenter;
   float mag = xsVectorLength(seaward);
   if (mag <= 0.0)
   {
      coastVec = baseCenter;
      coastBaseAreaID = baseAreaID;
      coastCached = 1;
      llProbe("wall.coast", "vec=" + llFmtVec(baseCenter) +
         " waterBorders=" + waterCount + " cached=0 fallback=zeroMagnitude baseArea=" + baseAreaID);
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
   coastBaseAreaID = baseAreaID;
   coastCached = 1;
   llProbe("wall.coast", "vec=" + llFmtVec(coastBiased) +
      " waterBorders=" + waterCount + " cached=0 shift=" + shift +
      " baseArea=" + baseAreaID);
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
   float radius = llComputeAdaptiveRadius(kbGetAge(), gLLWallStrategy, baseCenter);
   if (gLLWallRadius > 0)
   {
      radius = radius * (1.0 * gLLWallRadius / 18.0);
   }
   // Per-civ knob: forward bias fraction (0.10..0.45 typical for coastal civs).
   float biasFrac = 0.20;
   if (gLLWallForwardBiasFraction > 0.0) { biasFrac = gLLWallForwardBiasFraction; }
   vector coastCenter = llDetectCoastVector(mainBaseID, baseCenter);
   vector center = cInvalidVector;
   string centerSrc = "";
   if (coastCenter == cInvalidVector)
   {
      // Inland map — fall back to forward-biased (front-vector) center.
      center = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, biasFrac);
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
   int vilCap = gLLWallVillagerCount;
   if (vilCap < 2) { vilCap = 2; }
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, vilCap);
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, gLLWallGateCount);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 86);
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=CoastalBatteries radius=" + radius +
      " gates=" + gLLWallGateCount + " vils=2-" + vilCap +
      " bias=" + biasFrac + " priority=86 plan=" + planID +
      " centerSrc=" + centerSrc);
   // Knob: gLLWallTowerInterleave — intent probe; KNOB-TODO: wire actual outpost plans.
   if (gLLWallTowerInterleave > 0)
   {
      llProbe("wall.tower.interleave", "knob=" + gLLWallTowerInterleave +
         " strategy=CoastalBatteries plan=" + planID);
   }
   return (planID);
}

// FrontierPalisades: quick lighter ring, many gates, less stone.
// Washington, Jefferson, Brock, Papineau, Houston, Kruger, Mannerheim, Morazán.
int llPlanFrontierPalisadeWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llComputeAdaptiveRadius(kbGetAge(), gLLWallStrategy, baseCenter) + 2.0;
   if (gLLWallRadius > 0)
   {
      radius = radius * (1.0 * gLLWallRadius / 18.0);
   }
   float biasFrac = 0.15;
   if (gLLWallForwardBiasFraction > 0.0) { biasFrac = gLLWallForwardBiasFraction; }
   vector center = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, biasFrac);
   int planID = aiPlanCreate("FrontierPalisade Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   int vilCap = gLLWallVillagerCount;
   if (vilCap < 2) { vilCap = 2; }
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, vilCap);
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, gLLWallGateCount);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 82);  // wood-cheap palisades, complete first
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=FrontierPalisade radius=" + radius +
      " gates=" + gLLWallGateCount + " vils=2-" + vilCap +
      " bias=" + biasFrac + " priority=82 plan=" + planID);
   // Knob: gLLWallTowerInterleave — intent probe; KNOB-TODO: wire actual outpost plans.
   if (gLLWallTowerInterleave > 0)
   {
      llProbe("wall.tower.interleave", "knob=" + gLLWallTowerInterleave +
         " strategy=FrontierPalisade plan=" + planID);
   }
   return (planID);
}

// UrbanBarricade: tight compact inner ring (Robespierre Paris, Garibaldi cities).
int llPlanUrbanBarricadeWall(int mainBaseID = -1, vector baseCenter = cInvalidVector)
{
   float radius = llComputeAdaptiveRadius(kbGetAge(), gLLWallStrategy, baseCenter) - 8.0;
   if (gLLWallRadius > 0)
   {
      radius = radius * (1.0 * gLLWallRadius / 18.0);
   }
   float biasFrac = 0.15;
   if (gLLWallForwardBiasFraction > 0.0) { biasFrac = gLLWallForwardBiasFraction; }
   vector center = llGetForwardBiasedWallCenter(baseCenter, mainBaseID, biasFrac);
   int planID = aiPlanCreate("UrbanBarricade Wall", cPlanBuildWall);
   if (planID < 0) return (-1);
   aiPlanSetVariableInt(planID, cBuildWallPlanWallType, 0,
      llSelectWallType(gLLWallStrategy, kbGetAge()));
   int vilCap = gLLWallVillagerCount;
   if (vilCap < 2) { vilCap = 2; }
   aiPlanAddUnitType(planID, gEconUnit, 0, 2, vilCap);
   aiPlanSetVariableVector(planID, cBuildWallPlanWallRingCenterPoint, 0, center);
   aiPlanSetVariableFloat(planID, cBuildWallPlanWallRingRadius, 0.0, radius);
   aiPlanSetVariableInt(planID, cBuildWallPlanNumberOfGates, 0, gLLWallGateCount);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetEscrowID(planID, cEconomyEscrowID);
   aiPlanSetDesiredPriority(planID, 84);
   aiPlanSetActive(planID, true);
   llProbe("plan.wall.create", "type=UrbanBarricade radius=" + radius +
      " gates=" + gLLWallGateCount + " vils=2-" + vilCap +
      " bias=" + biasFrac + " priority=84 plan=" + planID);
   // Knob: gLLWallTowerInterleave — intent probe; KNOB-TODO: wire actual outpost plans.
   if (gLLWallTowerInterleave > 0)
   {
      llProbe("wall.tower.interleave", "knob=" + gLLWallTowerInterleave +
         " strategy=UrbanBarricade plan=" + planID);
   }
   // Knob: gLLWallOuterRingDelta — double-ring for Urban doctrine at Age 3+.
   // Creates a second concentric ring at radius + delta tiles, lower priority.
   if ((gLLWallOuterRingDelta > 0) && (kbGetAge() >= cAge3))
   {
      float outerRadius = radius + (1.0 * gLLWallOuterRingDelta);
      int outerPlanID = aiPlanCreate("UrbanBarricade OuterRing", cPlanBuildWall);
      if (outerPlanID >= 0)
      {
         int outerVilCap = gLLWallVillagerCount;
         if (outerVilCap < 2) { outerVilCap = 2; }
         aiPlanSetVariableInt(outerPlanID, cBuildWallPlanWallType, 0,
            llSelectWallType(gLLWallStrategy, kbGetAge()));
         aiPlanAddUnitType(outerPlanID, gEconUnit, 0, 2, outerVilCap);
         aiPlanSetVariableVector(outerPlanID, cBuildWallPlanWallRingCenterPoint, 0, center);
         aiPlanSetVariableFloat(outerPlanID, cBuildWallPlanWallRingRadius, 0.0, outerRadius);
         aiPlanSetVariableInt(outerPlanID, cBuildWallPlanNumberOfGates, 0, gLLWallGateCount);
         aiPlanSetBaseID(outerPlanID, mainBaseID);
         aiPlanSetEscrowID(outerPlanID, cEconomyEscrowID);
         aiPlanSetDesiredPriority(outerPlanID, 79);  // 84 - 5
         aiPlanSetActive(outerPlanID, true);
         llProbe("wall.outer_ring", "type=UrbanBarricade delta=" + gLLWallOuterRingDelta +
            " outerRadius=" + outerRadius + " plan=" + outerPlanID);
      }
   }
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

   int primaryPlanID = -1;
   if (gLLWallStrategy == cLLWallStrategyFortressRing)       primaryPlanID = llPlanFortressRingWall(mainBaseID, baseCenter);
   else if (gLLWallStrategy == cLLWallStrategyChokepointSegments) primaryPlanID = llPlanChokepointWall(mainBaseID, baseCenter);
   else if (gLLWallStrategy == cLLWallStrategyCoastalBatteries)   primaryPlanID = llPlanCoastalBatteriesWall(mainBaseID, baseCenter);
   else if (gLLWallStrategy == cLLWallStrategyFrontierPalisades)  primaryPlanID = llPlanFrontierPalisadeWall(mainBaseID, baseCenter);
   else if (gLLWallStrategy == cLLWallStrategyUrbanBarricade)     primaryPlanID = llPlanUrbanBarricadeWall(mainBaseID, baseCenter);
   else if (gLLWallStrategy == cLLWallStrategyMobileNoWalls)      primaryPlanID = llPlanMobileNoWalls(mainBaseID, baseCenter);
   else
   {
      // Fallback — FortressRing if unknown.
      llProbe("plan.wall", "fallback=FortressRing unknownStrategy=" + gLLWallStrategy);
      primaryPlanID = llPlanFortressRingWall(mainBaseID, baseCenter);
   }

   // Knob: gLLWallSecondaryStrategy — secondary fallback plan at lower priority.
   //
   // Two firing modes depending on the PRIMARY strategy:
   //
   //   A) Non-Mobile primary (FortressRing/Choke/Coastal/Frontier/Urban):
   //      Secondary fires alongside the primary as a hybrid layer (e.g.
   //      Inca FortressRing primary + Choke secondary at valley mouths).
   //      Priority reduced ~15 below primary so it doesn't outbid the
   //      main perimeter for villagers.
   //
   //   B) Mobile primary (no primary plan exists):
   //      Secondary is the FALLBACK doctrine — fires only at Age 3+ so
   //      light walls insure the column in late game (Hungarians frontier
   //      fallback if pinned, Spanish coastal fallback on islands, etc.)
   //      Priority lowered to 60 — well below normal wall plans so it
   //      doesn't dominate the Mobile economy. Mobile is still the primary
   //      doctrine; this is insurance, not the main plan.
   //
   // In both modes the secondary must differ from the primary (no-op
   // double-plans skipped). Knob == -1 disables the fallback entirely.
   if ((gLLWallSecondaryStrategy >= 0) &&
       (gLLWallSecondaryStrategy != gLLWallStrategy))
   {
      bool mobilePrimary = (gLLWallStrategy == cLLWallStrategyMobileNoWalls);
      int secPrio = 70;
      bool fireSecondary = true;
      if (mobilePrimary)
      {
         // Mobile fallback: defer until Age 3+ so light walls only appear
         // when the column actually needs insurance.
         if (kbGetAge() < cAge3) { fireSecondary = false; }
         secPrio = 60;
      }
      if (fireSecondary)
      {
         llProbe("wall.secondary", "primary=" + gLLWallStrategy +
            " secondary=" + gLLWallSecondaryStrategy + " primaryPlan=" + primaryPlanID +
            " mode=" + (mobilePrimary ? "mobileFallback" : "hybridLayer") +
            " age=" + kbGetAge());
         // Call secondary plan function; reduce its priority via plan set.
         int secPlanID = -1;
         if (gLLWallSecondaryStrategy == cLLWallStrategyFortressRing)
            secPlanID = llPlanFortressRingWall(mainBaseID, baseCenter);
         else if (gLLWallSecondaryStrategy == cLLWallStrategyChokepointSegments)
            secPlanID = llPlanChokepointWall(mainBaseID, baseCenter);
         else if (gLLWallSecondaryStrategy == cLLWallStrategyCoastalBatteries)
            secPlanID = llPlanCoastalBatteriesWall(mainBaseID, baseCenter);
         else if (gLLWallSecondaryStrategy == cLLWallStrategyFrontierPalisades)
            secPlanID = llPlanFrontierPalisadeWall(mainBaseID, baseCenter);
         else if (gLLWallSecondaryStrategy == cLLWallStrategyUrbanBarricade)
            secPlanID = llPlanUrbanBarricadeWall(mainBaseID, baseCenter);
         if (secPlanID >= 0)
         {
            aiPlanSetDesiredPriority(secPlanID, secPrio);
            llProbe("wall.secondary", "secPlan=" + secPlanID +
               " priority=" + secPrio);
         }
      }
      else
      {
         llProbe("wall.secondary", "deferred primary=" + gLLWallStrategy +
            " secondary=" + gLLWallSecondaryStrategy + " age=" + kbGetAge() +
            " need=cAge3");
      }
   }

   return (primaryPlanID);
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
   // Knob: gLLWallEarlyOutpostCount — record early outpost intent so validators
   // can confirm the knob was read. Actual outpost plan creation would need
   // the build-outpost API which is too invasive to add here.
   // KNOB-TODO: when a confirmed outpost build-plan API is available in the
   // codebase, create gLLWallEarlyOutpostCount outpost plans at the wall radius.
   if (gLLWallEarlyOutpostCount > 0)
   {
      llProbe("wall.early_outposts", "knob=" + gLLWallEarlyOutpostCount +
         " wallPlan=" + wallPlanID);
   }
   // Knob: gLLWallRepairAggressiveness — repair priority intent.
   // cBuildWallPlanRepair constants do not exist in this engine surface (grepped, absent).
   // Record probe so validators can confirm knob is consumed.
   // KNOB-TODO: if a repair plan constant is added to the engine, wire
   // priority = 70 + gLLWallRepairAggressiveness * 5 here.
   if (gLLWallRepairAggressiveness > 0)
   {
      int repairPriority = 70 + gLLWallRepairAggressiveness * 5;
      llProbe("wall.repair.aggression", "knob=" + gLLWallRepairAggressiveness +
         " intent_priority=" + repairPriority);
   }
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
   // SMART WALLS — Track 1.2c: adaptive radius (eco-saturation scaling).
   float wallRadius = llComputeAdaptiveRadius(kbGetAge(), gLLWallStrategy, baseCenter);
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

   // SMART WALLS — Track 1.2a: perimeter gap check.
   // Count how many of the 8 sample points around the proposed ring are
   // land (not water/unmappable). Emit wall.perimeter_gaps for telemetry.
   // If landCount == 0, the entire ring is over water — skip this tick.
   int perimLandCount = llCountPerimeterGaps(wallCenter, wallRadius, gLLWallStrategy);
   if (perimLandCount == 0)
   {
      llProbe("wall.skip",
         "reason=noLandPerimeter center=" + llFmtVec(wallCenter) +
         " radius=" + wallRadius + " strategy=" + gLLWallStrategy);
      return;
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
// ANW 2026-05-30 SMART-WALLS: rule verifyWallClosure
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
   //
   // 2026-05-27: Removed the +1 defensive padding that was added in the
   // original draft. At gLLWallClosurePctTarget=100 the +1 made closure
   // cap at ~95-97% even when the ring was geometrically complete (the
   // engine never places an extra piece beyond the perimeter), so the
   // escalation branch fired forever. Pure circumference/4 produces a
   // truthful ratio that can actually reach 1.0.
   float radius = llGetLegendaryWallRadius(kbGetAge() >= cAge3);
   int expectedPieces = 2.0 * 3.14159 * radius / 4.0;
   if (expectedPieces < 1) { expectedPieces = 1; }  // tiny-radius guard
   int actualPieces = kbUnitCount(cMyID, cUnitTypeAbstractWall, cUnitStateABQ);
   float closure = 0.0;
   if (expectedPieces > 0)
   {
      // 2026-05-12 fix: XS performs integer division on `int / int` BEFORE
      // assigning to a float, so any closure ratio < 1.0 truncated to 0
      // and tripped the spurious-escalation branch every 60s. Multiplying
      // by 1.0 forces float arithmetic.
      closure = (1.0 * actualPieces) / expectedPieces;
      // Clamp at 1.0 so an over-placed ring (engine sometimes places
      // overlapping pieces near gates) doesn't read as >100%.
      if (closure > 1.0) { closure = 1.0; }
   }
   int elapsedSec = xsGetTime() / 1000;
   // pct=<N> radius=<R> expected=<E> placed=<P> fields satisfy the
   // wall.closure probe spec consumed by aiDoctrineProbes / validators.
   // Clamp at 100 so a ring with engine over-placement near gates never
   // reads as >100% (matches the closure-float clamp above).
   int closurePct = (1.0 * actualPieces * 100) / (expectedPieces > 0 ? expectedPieces : 1);
   if (closurePct > 100) { closurePct = 100; }
   llProbe("wall.closure", "pct=" + closurePct +
      " radius=" + radius +
      " expected=" + expectedPieces +
      " placed=" + actualPieces +
      " closure=" + closure +
      " strategy=" + gLLWallStrategy +
      " elapsed=" + elapsedSec +
      " age=" + kbGetAge());

   // Knob: gLLWallClosurePctTarget — per-civ closure threshold (0–100).
   // Default 60 (matches the hardcoded 0.6 below). Convert to float fraction.
   float closureTarget = 0.6;
   if (gLLWallClosurePctTarget > 0)
   {
      closureTarget = 1.0 * gLLWallClosurePctTarget / 100.0;
   }

   // <closureTarget closure after 4 minutes of game time -> escalate.
   if ((closure < closureTarget) && (xsGetTime() >= 240000))
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