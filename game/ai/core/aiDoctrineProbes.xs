//==============================================================================
// aiDoctrineProbes.xs — runtime probes that the playstyle-spec validator
// (tools/validation/validate_doctrine_compliance.py) consumes to confirm
// the AI's actual behaviour matches the claims in
// LEGENDARY_LEADERS_TREE.html.
//
// Two flavours of probe:
//
//   1) milestone.first_<thing>  — fired exactly once per match per AI, the
//      first tick we observe ≥1 owned building of that abstract type.
//      Lets the validator assert "Naval Mercantile civs build a Dock
//      before 6 minutes of game time", "Forward Operational Line civs
//      build a Barracks-or-Stable before 6 minutes", etc.
//
//      Tags emitted (each at most once):
//        milestone.first_dock          atMs=<int>
//        milestone.first_barracks      atMs=<int>
//        milestone.first_stable        atMs=<int>
//        milestone.first_wall_segment  atMs=<int>
//        milestone.first_fort          atMs=<int>
//        milestone.first_trading_post  atMs=<int>
//        milestone.first_artillery     atMs=<int>   (any owned artillery unit)
//        milestone.first_forward_base  atMs=<int> baseID=<int>
//                                       (gForwardBaseState == Active)
//
//   2) wall.closure / wall.escalate / wall.reemit — fired every 60s by the
//      verifyWallClosure rule (aiBuildingsWalls.xs) while any wall plan is
//      active. Lets the validator confirm closure progress and detect
//      half-wall stall conditions.
//
//      Tags emitted (every 60s while wall plan active):
//        wall.closure   pct=<int> radius=<float> expected=<int> placed=<int>
//                       closure=<float> strategy=<int> elapsed=<int> age=<int>
//                         — pct is integer percentage (0-100+). radius is the
//                           ring radius used. expected is 2*PI*radius/4
//                           (4-unit segment length). placed is actual owned
//                           wall segments (kbUnitCount ABQ). closure=placed/expected.
//                           strategy matches the cANWWallStrategy* enum.
//                           elapsed is game-time seconds.
//        wall.escalate  plan=<int> closure=<float>
//                         — fired when coverage < 0.60 after 4 min and the
//                           plan is still alive. Priority bumped to 95,
//                           villager pool bumped to 4-16.
//        wall.reemit    closure=<float>
//                         — fired when coverage < 0.60 after 4 min and the
//                           plan was destroyed; a fresh plan is emitted.
//        wall.water_fix orig=<vec> final=<vec> steps=<int> fixed=<bool>
//                         — fired by anwGetForwardBiasedWallCenter whenever a
//                           water/cliff fixup is attempted (steps=0 and
//                           fixed=false on flat inland maps).
//        wall.chokepoint vec=<vec> tiles=<int> cached=<0|1> [fallback=<tag>]
//                         — fired by anwDetectChokepointVector; tiles is the
//                           narrowest border area's tile count (0 on cache hits
//                           or flat-map fallback). cached=1 means a previously
//                           computed vector was reused.
//        wall.coast      vec=<vec> waterBorders=<int> cached=<0|1>
//                         — fired by anwDetectCoastVector; waterBorders is the
//                           count of water-typed border areas found.
//        wall.perimeter_gaps  land=<int> water=<int> radius=<float>
//                         — fired by anwCountPerimeterGaps (Track 1.2a); land
//                           is the count of the 8 ring sample points that are
//                           NOT water-typed (0–8). water is the complement.
//                           Emitted from delayWallsNew before every ring plan
//                           for telemetry. If land==0 the plan is skipped.
//        wall.skip        reason=<tag> center=<vec> radius=<float>
//                         strategy=<int>
//                         — fired when a wall plan is suppressed. Currently
//                           only reason=noLandPerimeter (all 8 sample points
//                           are water or unmappable).
//        wall.threat_vector  vec=<vec> enemies=<int>
//                         — fired by anwComputeThreatVector (Track 1.2b) on
//                           every 60s cache-miss recompute. vec is the
//                           centroid of all visible enemy land-military units
//                           (cInvalidVector when none spotted). enemies is
//                           the raw unit count fed into the centroid.
//        wall.adaptive_radius  base=<float> ratio=<float> result=<float>
//                              age=<int> strategy=<int>
//                         — fired by anwComputeAdaptiveRadius (Track 1.2c) on
//                           every call. base is anwGetWallRadius(),
//                           ratio is vilCount/popCap, result is the clamped
//                           scaled radius actually used.
//
//   3) comp.snapshot / posture.snapshot — fired every 60s (game time) to
//      give the validator a rolling view. comp.snapshot reports unit
//      composition (cavalry/infantry/artillery counts + villager count
//      so we can compute army%); posture.snapshot reports the
//      doctrine-level state (wallStrategy / buildStyle / mil-distance
//      multiplier / wall+fort+dock counts / age).
//
//      Tags emitted (every 60s):
//        comp.snapshot     ageMs=… vil=… inf=… cav=… arty=… warship=…
//        posture.snapshot  ageMs=… age=… ws=<wallStrategy> bs=<buildStyle>
//                          mdist=<float> walls=… forts=… docks=… tposts=…
//                          heading=… terr=…
//
// All emission goes through anwProbe() so the global cANWReplayProbes kill
// switch in aiGlobals.xs disables every line at once for release builds.
//
// Performance: all queries are kbUnitCount with cached abstract type
// constants — cheap. The rule fires every 30s game time (so a 30-min
// match generates at most ~60 probe lines per AI from this file, on top
// of the ≤7 milestone lines).
//==============================================================================

// Per-milestone "already-fired" flags. Initialised false on script load
// (XS reloads per match), so the first observation each match emits the
// probe and sets the flag.
extern bool gANWMilestoneFiredDock         = false;
extern bool gANWMilestoneFiredBarracks     = false;
extern bool gANWMilestoneFiredStable       = false;
extern bool gANWMilestoneFiredWall         = false;
extern bool gANWMilestoneFiredFort         = false;
extern bool gANWMilestoneFiredTradingPost  = false;
extern bool gANWMilestoneFiredArtillery    = false;
// Forward-base milestone — fires the first tick gForwardBaseState flips to
// cForwardBaseStateActive (a forward base/operating point has been chosen
// AND construction has begun). Lets the validator close the
// `expects_forward` claim for Forward Operational Line / Plains Cavalry
// Wedge / Mobile Frontier Scatter / Steppe Cavalry Wedge / Jungle
// Guerrilla Network civs without UNKNOWN stubs.
extern bool gANWMilestoneFiredForwardBase  = false;

// Last time we emitted a snapshot pair, in game ms. -1 = never.
extern int  gANWLastDoctrineSnapshotMs = -1;

// Snapshot interval — 60s of game time. Rule itself fires every 30s, so
// snapshots emit every other tick; milestones are checked every tick.
extern const int cANWDoctrineSnapshotIntervalMs = 60000;


//------------------------------------------------------------------------------
// anwCheckMilestone — emit "milestone.first_<tag>" once when count ≥ 1.
// Returns true if the milestone was just fired this call (the caller
// flips the global), false otherwise.
//------------------------------------------------------------------------------
bool anwCheckMilestone(string tag = "", int abstractType = -1, bool alreadyFired = false)
{
   if (alreadyFired == true)  return(false);
   if (abstractType < 0)      return(false);

   int n = kbUnitCount(cMyID, abstractType, cUnitStateABQ);
   if (n < 1) return(false);

   anwProbe("milestone.first_" + tag,
      "atMs=" + xsGetTime() + " count=" + n + " age=" + kbGetAge());
   return(true);
}


//------------------------------------------------------------------------------
// Per-tick snapshot helpers — kept tiny so the rule body stays readable.
//------------------------------------------------------------------------------
void anwEmitCompositionSnapshot(int ageMs = 0)
{
   int vil   = kbUnitCount(cMyID, cUnitTypeAbstractVillager, cUnitStateAlive);
   int inf   = kbUnitCount(cMyID, cUnitTypeAbstractInfantry,  cUnitStateAlive);
   int cav   = kbUnitCount(cMyID, cUnitTypeAbstractCavalry,   cUnitStateAlive);
   int arty  = kbUnitCount(cMyID, cUnitTypeAbstractArtillery, cUnitStateAlive);
   int land  = kbUnitCount(cMyID, cUnitTypeLogicalTypeLandMilitary, cUnitStateAlive);
   // Warship count uses gANWAbstractWarShip when the civ has one; otherwise 0.
   // (Matches the existing pattern in aiNavalUtilities.xs.)
   int navy  = 0;
   if (gANWAbstractWarShip > 0)
   {
      navy = kbUnitCount(cMyID, gANWAbstractWarShip, cUnitStateAlive);
   }

   anwProbe("comp.snapshot",
      "ageMs=" + ageMs +
      " vil=" + vil +
      " inf=" + inf +
      " cav=" + cav +
      " arty=" + arty +
      " landmil=" + land +
      " warship=" + navy);
}


void anwEmitPostureSnapshot(int ageMs = 0)
{
   int walls  = kbUnitCount(cMyID, cUnitTypeAbstractWall,    cUnitStateABQ);
   int forts  = 0;
   if (gFortUnit > 0) forts = kbUnitCount(cMyID, gFortUnit,  cUnitStateABQ);
   int docks  = 0;
   if (gDockUnit > 0) docks = kbUnitCount(cMyID, gDockUnit,  cUnitStateABQ);
   int tposts = kbUnitCount(cMyID, cUnitTypeTradingPost,     cUnitStateABQ);

   anwProbe("posture.snapshot",
      "ageMs=" + ageMs +
      " age="  + kbGetAge() +
      " ws="   + gANWWallStrategy +
      " bs="   + gANWBuildStyle +
      " mdist=" + gANWMilitaryDistanceMultiplier +
      " edist=" + gANWEconomicDistanceMultiplier +
      " walls=" + walls +
      " forts=" + forts +
      " docks=" + docks +
      " tposts=" + tposts +
      " heading=" + gANWExpansionHeading +
      " terrP=" + gANWPreferredTerrainPrimary +
      " terrS=" + gANWPreferredTerrainSecondary);
}


//==============================================================================
// anwDoctrineProbes — periodic milestone + snapshot rule. Enabled from
// aiCore.xs at game start (alongside other always-on probes). We keep
// minInterval at 30s — fine-grained enough to catch a "first dock by
// 6:00" claim without spamming chat (≤2 lines per AI per minute).
//
// The rule never disables itself: even after every milestone fires, the
// snapshot half keeps streaming so the validator can sanity-check
// late-game composition (e.g. confirm Plains Cavalry Wedge actually
// keeps cavalry > infantry through Age 4).
//==============================================================================
rule anwDoctrineProbes
inactive
minInterval 30
{
   // Bail cheaply when the global probe channel is off — a release build
   // ships with cANWReplayProbes=false, so the rule body becomes a single
   // boolean check per tick.
   if (cANWReplayProbes == false)
   {
      xsDisableSelf();
      return;
   }

   int nowMs = xsGetTime();

   // ── milestones (each once per match) ─────────────────────────────────
   if (anwCheckMilestone("dock",          cUnitTypeAbstractDock,    gANWMilestoneFiredDock))
      gANWMilestoneFiredDock = true;
   if (anwCheckMilestone("barracks",      cUnitTypeBarracks,        gANWMilestoneFiredBarracks))
      gANWMilestoneFiredBarracks = true;
   if (anwCheckMilestone("stable",        cUnitTypeAbstractStables, gANWMilestoneFiredStable))
      gANWMilestoneFiredStable = true;
   if (anwCheckMilestone("wall_segment",  cUnitTypeAbstractWall,    gANWMilestoneFiredWall))
      gANWMilestoneFiredWall = true;
   if (anwCheckMilestone("fort",          cUnitTypeAbstractFort,    gANWMilestoneFiredFort))
      gANWMilestoneFiredFort = true;
   if (anwCheckMilestone("trading_post",  cUnitTypeTradingPost,     gANWMilestoneFiredTradingPost))
      gANWMilestoneFiredTradingPost = true;
   if (anwCheckMilestone("artillery",     cUnitTypeAbstractArtillery, gANWMilestoneFiredArtillery))
      gANWMilestoneFiredArtillery = true;

   // Forward base milestone — gated on the global state machine in
   // aiBuildingsWalls.xs flipping to Active. We don't use anwCheckMilestone
   // here because the predicate is a state-int, not a unit count.
   if (gANWMilestoneFiredForwardBase == false &&
       gForwardBaseState == cForwardBaseStateActive)
   {
      anwProbe("milestone.first_forward_base",
         "atMs=" + nowMs + " age=" + kbGetAge() +
         " baseID=" + gForwardBaseID);
      gANWMilestoneFiredForwardBase = true;
   }

   // ── snapshots (every cANWDoctrineSnapshotIntervalMs) ──────────────────
   if (gANWLastDoctrineSnapshotMs < 0 ||
      (nowMs - gANWLastDoctrineSnapshotMs) >= cANWDoctrineSnapshotIntervalMs)
   {
      anwEmitCompositionSnapshot(nowMs);
      anwEmitPostureSnapshot(nowMs);
      gANWLastDoctrineSnapshotMs = nowMs;
   }
}
