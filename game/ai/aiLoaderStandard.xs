//==============================================================================
/* aiLoaderStandard.xs
   
   Create a new loader file for each personality.  Always specify loader
   file names (not the main or header files) in scenarios.
*/
//==============================================================================



include "aiHeader.xs";     // Gets global vars, function forward declarations
include "aiMain.xs";       // The bulk of the AI
include "leaders\leaderCommon.xs";
include "leaders\leader_revolution_support.xs";
include "leaders\leader_revolution_commanders.xs";
include "leaders\leader_bourbon.xs";
include "leaders\leader_napoleon.xs";
include "leaders\leader_wellington.xs";
include "leaders\leader_frederick.xs";
include "leaders\leader_catherine.xs";
include "leaders\leader_isabella.xs";
include "leaders\leader_suleiman.xs";
include "leaders\leader_henry.xs";
include "leaders\leader_maurice.xs";
include "leaders\leader_washington.xs";
include "leaders\leader_hidalgo.xs";
include "leaders\leader_garibaldi.xs";
include "leaders\leader_valette.xs";
include "leaders\leader_montezuma.xs";
include "leaders\leader_kangxi.xs";
include "leaders\leader_menelik.xs";
include "leaders\leader_hiawatha.xs";
include "leaders\leader_usman.xs";
include "leaders\leader_pachacuti.xs";
include "leaders\leader_shivaji.xs";
include "leaders\leader_tokugawa.xs";
include "leaders\leader_crazy_horse.xs";
include "leaders\leader_gustavus.xs";

// ── Per-civ wall-knob dispatch (auto-generated from
//    tools/ai_design/wall_knob_calibration.py).
//    Defines void anwSetWallKnobsForCiv(void) which sets all 14
//    gANWWall* tuning knobs for the active civ. Called from preInit()
//    AFTER initLeader<Name>() so it overrides leader-set defaults.
include "core\aiWallKnobsByCiv.xs";


//==============================================================================
/*  Runtime-resolved abstract proto-type IDs.

    The XS engine exposes only a fixed enum of cUnitType* identifiers (e.g.
    cUnitTypeBarracks, cUnitTypeTownCenter). Many "Abstract*" proto types
    that appear in protoy.xml (AbstractStables, AbstractArtilleryFoundry,
    AbstractInfantry, etc.) are NOT in that enum, so referring to them as
    cUnitTypeAbstractXxx is a parse error: "X is not a valid operator"
    (XS Error 0172).

    Workaround: at preInit() we look each proto up by NAME via
    kbGetProtoUnitID("AbstractXxx") and cache the int ID in a global.
    All probe call-sites use the cached g* below. If the engine doesn't
    know a name, kbGetProtoUnitID returns -1; kbUnitCount with proto=-1
    returns 0, so probes degrade gracefully instead of crashing.

    NOTE: this is a probe/diagnostic concern only. The core/ AI files
    (aiTechs.xs, aiMilitary.xs, etc.) reference the same Abstract*
    constants but live in conditionally-compiled scopes (rules / func
    bodies that the parser only resolves when invoked) — they don't blow
    up at load time. The compliance probes in this file are at top-level
    rule scope and DO get parsed eagerly.

    The `extern int gANWAbstract*` declarations now live in
    core\aiGlobals (moved there 2026-05-31). They MUST be declared before
    the probe files aiDoctrineProbes and aiStateSnapshot are parsed;
    aiGlobals.xs is parsed early in the aiMain include chain, whereas the
    declarations previously sat here in aiLoaderStandard.xs *after*
    `include "aiMain.xs"` — too late, so the eager probe-function parse hit
    "gANWAbstractWarShip is not a valid operator" (XS Error 0172) and the
    whole AI compile aborted. The resolver below still owns the
    kbGetProtoUnitID() lookups and runs at preInit().
*/
//==============================================================================
void anwResolveAbstractTypes(void)
{
   gANWAbstractWarShip          = kbGetProtoUnitID("AbstractWarShip");
   gANWAbstractStables          = kbGetProtoUnitID("AbstractStables");
   gANWAbstractArtilleryFoundry = kbGetProtoUnitID("AbstractArtilleryFoundry");
   gANWAbstractWall             = kbGetProtoUnitID("AbstractWall");
   gANWAbstractTradingPost      = kbGetProtoUnitID("AbstractTradingPost");
   gANWAbstractMonastery        = kbGetProtoUnitID("AbstractMonastery");
   gANWAbstractInfantry         = kbGetProtoUnitID("AbstractInfantry");
   gANWAbstractCavalry          = kbGetProtoUnitID("AbstractCavalry");
   gANWAbstractArtillery        = kbGetProtoUnitID("AbstractArtillery");
   gANWAbstractNativeWarrior    = kbGetProtoUnitID("AbstractNativeWarrior");
   gANWMercenary                = kbGetProtoUnitID("Mercenary");
   gANWHero                     = kbGetProtoUnitID("Hero");
}


//==============================================================================
/*	preInit()

	This function is called in main() before any of the normal initialization 
	happens.  Use it to override default values of variables as needed for 
	personality or scenario effects.
*/
//==============================================================================
void preInit(void)
{
   anwVerboseEcho("preInit() starting.");

   // Resolve Abstract* proto IDs that aren't exposed as cUnitType* enum
   // values. Must run BEFORE any rule/probe that uses the gLL* cache.
   anwResolveAbstractTypes();

   // ── DIAGNOSTIC: bulletproof load-marker. Write to AI's OWN slot (history
   // index 0), before any other XS code that could fail. If this var ever
   // appears in <leader>.personality, AI loaded + flush works. If not, the
   // AI never even reaches preInit (XS compile error or earlier fault).
   aiPersonalitySetPlayerUserVar(0, "anw_preinit_marker", 1.0);
   aiPersonalitySetPlayerUserVar(0, "anw_preinit_t",      xsGetTime());

   string anwLeaderCivName = kbGetCivName(cMyCiv);

   anwInitRevolutionSupport();

   if (cMyCiv == cCivFrench)
   {
      initLeaderBourbon();
   }
   else if (anwLeaderCivName == "ANWNapoleonicFrance")
   {
      initLeaderNapoleon();
   }
   else if (cMyCiv == cCivBritish)
   {
      initLeaderWellington();
   }
   else if (cMyCiv == cCivGermans)
   {
      initLeaderFrederick();
   }
   else if (cMyCiv == cCivRussians)
   {
      initLeaderCatherine();
   }
   else if (cMyCiv == cCivSpanish)
   {
      initLeaderIsabella();
   }
   else if (cMyCiv == cCivOttomans)
   {
      initLeaderSuleiman();
   }
   else if (cMyCiv == cCivPortuguese)
   {
      initLeaderHenry();
   }
   else if (cMyCiv == cCivDutch)
   {
      initLeaderMaurice();
   }
   else if (cMyCiv == cCivDEAmericans)
   {
      initLeaderWashington();
   }
   else if (cMyCiv == cCivDEMexicans)
   {
      initLeaderHidalgo();
   }
   else if (cMyCiv == cCivDEItalians)
   {
      initLeaderGaribaldi();
   }
   else if (cMyCiv == cCivDEMaltese)
   {
      initLeaderValette();
   }
   else if (cMyCiv == cCivXPAztec)
   {
      initLeaderMontezuma();
   }
   else if (cMyCiv == cCivChinese)
   {
      initLeaderKangxi();
   }
   else if (cMyCiv == cCivDEEthiopians)
   {
      initLeaderMenelik();
   }
   else if (cMyCiv == cCivXPIroquois)
   {
      initLeaderHiawatha();
   }
   else if (cMyCiv == cCivDEHausa)
   {
      initLeaderUsman();
   }
   else if (cMyCiv == cCivDEInca)
   {
      initLeaderPachacuti();
   }
   else if (cMyCiv == cCivIndians)
   {
      initLeaderShivaji();
   }
   else if (cMyCiv == cCivJapanese)
   {
      initLeaderTokugawa();
   }
   else if (cMyCiv == cCivXPSioux)
   {
      initLeaderCrazyHorse();
   }
   else if (cMyCiv == cCivDESwedish)
   {
      initLeaderGustavus();
   }
   else if (civIsRevolution() == true)
   {
      anwInitRevolutionCommander();
   }

   anwAssignLeaderIdentity();
   anwApplyBuildStyleForActiveCiv();

   // Per-civ wall-knob calibration (overrides leader-file strategy when
   // the per-age doctrine table in tools/ai_design/wall_knob_calibration.py
   // disagrees with the historical leader file).
   anwSetWallKnobsForCiv();

   if (aiGetGameMode() == cGameModeEconomyMode)
   {
      anwVerboseEcho("Economy mode setup");

      btRushBoom = -1.0; // boom
      btOffenseDefense = -1.0; // defend
      cvOkToAttack = false;
      cvOkToTrainArmy = false;
      cvOkToTrainNavy = false;
      cvOkToAllyNatives = false;
   }
}




//==============================================================================
/*	postInit()

	This function is called in main() after the normal initialization is 
	complete.  Use it to override settings and decisions made by the startup logic.
*/
//==============================================================================
void postInit(void)
{
   anwVerboseEcho("postInit() starting.");

   // Per-nation walling: enable the Age-1 ring-wall rule for every leader.
   // The rule itself checks anwShouldBuildWalls(true) which respects
   // gANWEarlyWallingEnabled and gANWWallLevel per leader — aggressive styles
   // (SteppeCavalryWedge / MobileFrontierScatter / JungleGuerrillaNetwork)
   // opt out via earlyWalls=false in their style helpers, so the rule
   // effectively no-ops for them. Defensive leaders (Wellington, Valette,
   // Pachacuti, Frederick) get an early ring-wall around the TC.
   xsEnableRule("explorationAgeWalling");
   // Watchdog: destroy stalled wall plans so held villagers free up.
   xsEnableRule("wallPlanStallWatchdog");

   if (cANWReplayProbes == true)
   {
      xsEnableRule("anwHeartbeat");
      xsEnableRule("anwPlanSnapshot");
      xsEnableRule("anwComplianceSnapshot");
      xsEnableRule("anwAgeUpProbe");
      // Coverage-push family — combat / econ / shipments / placement /
      // wall geometry / diplomacy / rule-health. Each runs on its own
      // 60–120s interval, so total probe overhead stays bounded.
      xsEnableRule("anwCombatComplianceSnapshot");
      xsEnableRule("anwEconComplianceSnapshot");
      xsEnableRule("anwShipmentComplianceSnapshot");
      xsEnableRule("anwPlacementDeepSnapshot");
      xsEnableRule("anwWallGeometrySnapshot");
      xsEnableRule("anwDiplomacyComplianceSnapshot");
      xsEnableRule("anwRuleHealthSnapshot");
      xsEnableRule("anwTacticsComplianceSnapshot");
      xsEnableRule("anwEventDeltaSnapshot");
      // Per-civ playstyle-fidelity probes (milestones + comp/posture
      // snapshots) consumed by tools/validation/validate_doctrine_compliance.py.
      xsEnableRule("anwDoctrineProbes");
   }

   anwEnableRevolutionSupportRules();
   anwEnableRevolutionCommanderRules();
   enableLeaderBourbonRules();
   enableLeaderNapoleonRules();
   enableLeaderWellingtonRules();
   enableLeaderFrederickRules();
   enableLeaderCatherineRules();
   enableLeaderIsabellaRules();
   enableLeaderSuleimanRules();
   enableLeaderHenryRules();
   enableLeaderMauriceRules();
   enableLeaderWashingtonRules();
   enableLeaderHidalgoRules();
   enableLeaderGaribaldiRules();
   enableLeaderValetteRules();
   enableLeaderMontezumaRules();
   enableLeaderKangxiRules();
   enableLeaderMenelikRules();
   enableLeaderHiawathaRules();
   enableLeaderUsmanRules();
   enableLeaderPachacutiRules();
   enableLeaderShivajiRules();
   enableLeaderTokugawaRules();
   enableLeaderCrazyHorseRules();
   enableLeaderGustavusRules();

   // ── LL-BOOT probe ───────────────────────────────────────────────────────
   // One-shot broadcast of this AI's identity so the replay parser records
   // leader/chatset/doctrine/wall-strategy wiring at t=0 for every AI in the
   // match. Catches Barbary-blank, Napoleon-wrong-name, wrong-chatset
   // regressions immediately without needing in-match screenshots.
   anwProbe("meta.boot",
      "chatset=" + gANWChatsetKey +
      " wallStrategy=" + gANWWallStrategy +
      " buildStyle=" + anwGetBuildStyleName(gANWBuildStyle) +
      " wallLevel=" + gANWWallLevel +
      " earlyWalls=" + gANWEarlyWallingEnabled +
      " rush=" + btRushBoom +
      " off=" + btOffenseDefense +
      " inf=" + btBiasInf +
      " cav=" + btBiasCav +
      " art=" + btBiasArt);

   // ── LL-SETUP probe ──────────────────────────────────────────────────────
   // Match-level context: game mode, difficulty, team, player count. Shared
   // context for every AI's probes so post-match analysis can normalise
   // across Supremacy/Deathmatch/Treaty/Empire-Wars runs.
   anwProbe("meta.setup",
      "gameMode=" + aiGetGameMode() +
      " difficulty=" + cDifficultyCurrent +
      " team=" + kbGetPlayerTeam(cMyID) +
      " players=" + cNumberPlayers +
      " startAge=" + kbGetAge() +
      " okAttack=" + cvOkToAttack +
      " okTaunt=" + cvOkToTaunt);

   // ── LL-ECOSNAP probe ────────────────────────────────────────────────────
   // Initial economic state snapshot — DEFERRED: postInit runs before the
   // engine seeds starting resources/villagers, so an immediate snapshot
   // captures all-zero garbage (verified in replay). anwInitialEconSnapshot
   // fires once after 5s when the starting bundle is populated.
   if (cANWReplayProbes == true)
   {
      xsEnableRule("anwInitialEconSnapshot");
   }

   // ── LL-TEST-AUTO-RESIGN ────────────────────────────────────────────────
   // When the harness sets cANWTestModeAutoResignMs > 0 (via sed before sync),
   // arm a rule that resigns this AI as soon as the wall-clock threshold
   // hits. Bounds match length so 47-civ coverage runs in minutes, not hours.
   if (cANWTestModeAutoResignMs > 0)
   {
      xsEnableRule("anwTestModeAutoResign");
      anwProbe("test.armed", "resignAtMs=" + cANWTestModeAutoResignMs);
   }

   // ── LL-PERSONALITY-PROBE (early write) ──────────────────────────────────
   // aiEcho()→Age3Log path is dead in retail FINAL_RELEASE builds. The
   // personality-uservar channel does NOT need dev mode and persists writes
   // to Game/AI/<leader>.personality. We write at AI init (here) so the
   // probe lands even on human-resign matches where gameOverHandler may not
   // fire its disk flush. gameOverHandler() also calls this with end-state
   // values when it does fire — last writer wins.
   anwWritePersonalityProbe();

   // Mark post-init complete. gameOverHandler() reads this flag instead of a
   // wall-clock threshold so probe writes still fire on observe<60s smoke runs.
   gANWPostInitFired = true;
}




//==============================================================================
/*	Rules

	Add personality-specific or scenario-specific rules in the section below.
*/
//==============================================================================

//==============================================================================
// anwHeartbeat
// Periodic time-series probe. Emits age, resources, pop, army, score every
// 60s so replay analysis can chart economic/military trajectory without
// relying on spiky event-driven probes alone.
//==============================================================================
rule anwHeartbeat
inactive
minInterval 60
{
   anwProbe("telem.heartbeat",
      "age=" + kbGetAge() +
      " food=" + kbResourceGet(cResourceFood) +
      " wood=" + kbResourceGet(cResourceWood) +
      " gold=" + kbResourceGet(cResourceGold) +
      " pop=" + kbGetPop() +
      " vills=" + kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) +
      " armyPop=" + aiGetMilitaryPop() +
      " score=" + aiGetScore(cMyID));
}

//==============================================================================
// anwTestModeAutoResign
// Test-harness rule. When cANWTestModeAutoResignMs > 0 and the wall-clock
// crosses that threshold, dump a final state snapshot then call aiResign().
// Released builds (cANWTestModeAutoResignMs == 0) never enable this rule.
//==============================================================================
rule anwTestModeAutoResign
inactive
minInterval 5
{
   if (xsGetTime() < cANWTestModeAutoResignMs)
   {
      return;
   }
   anwProbe("test.resign",
      "atMs=" + xsGetTime() +
      " age=" + kbGetAge() +
      " pop=" + kbGetPop() +
      " vills=" + kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) +
      " armyPop=" + aiGetMilitaryPop() +
      " score=" + aiGetScore(cMyID) +
      " food=" + kbResourceGet(cResourceFood) +
      " wood=" + kbResourceGet(cResourceWood) +
      " gold=" + kbResourceGet(cResourceGold));
   aiResign();
   xsDisableSelf();
}

//==============================================================================
// anwPlanSnapshot
// Phase-2 periodic snapshot of the AI's active plan inventory. Fires every
// 60s alongside the heartbeat. Three probes per tick:
//   * mil.plan_snap   — combat plan count (offense + defense)
//   * plan.build_snap — build plans (incl. wall plans), repair, gather
//   * navy.fleet_snap — naval unit and transport-plan inventory
// We use periodic snapshots rather than instrumenting all 91 aiPlanCreate
// call sites — equivalent ground truth, far less integration risk.
//==============================================================================
rule anwPlanSnapshot
inactive
minInterval 60
{
   int combatPlans = aiPlanGetNumber(cPlanCombat, -1, true);
   int attackPlans = aiPlanGetNumber(cPlanAttack, -1, true);
   int defendPlans = aiPlanGetNumber(cPlanDefend, -1, true);
   int buildPlans = aiPlanGetNumber(cPlanBuild, -1, true);
   int wallPlans = aiPlanGetNumber(cPlanBuildWall, -1, true);
   int repairPlans = aiPlanGetNumber(cPlanRepair, -1, true);
   int gatherPlans = aiPlanGetNumber(cPlanGather, -1, true);
   int researchPlans = aiPlanGetNumber(cPlanResearch, -1, true);
   int transportPlans = aiPlanGetNumber(cPlanTransport, -1, true);
   int explorePlans = aiPlanGetNumber(cPlanExplore, -1, true);

   anwProbe("mil.plan_snap",
      "combat=" + combatPlans +
      " attack=" + attackPlans +
      " defend=" + defendPlans +
      " explore=" + explorePlans +
      " militaryPop=" + aiGetMilitaryPop());

   anwProbe("plan.build_snap",
      "build=" + buildPlans +
      " walls=" + wallPlans +
      " repair=" + repairPlans +
      " gather=" + gatherPlans +
      " research=" + researchPlans +
      " tcs=" + kbUnitCount(cMyID, cUnitTypeTownCenter, cUnitStateABQ) +
      " houses=" + kbUnitCount(cMyID, gHouseUnit, cUnitStateABQ));

   anwProbe("navy.fleet_snap",
      "transports=" + transportPlans +
      " warships=" + kbUnitCount(cMyID, gANWAbstractWarShip, cUnitStateAlive) +
      " fishing=" + kbUnitCount(cMyID, gFishingUnit, cUnitStateAlive) +
      " docks=" + kbUnitCount(cMyID, gDockUnit, cUnitStateABQ));
}

//==============================================================================
// anwPersonalitySnapshot
// Periodic re-fire of the personality-channel probe so the .personality
// file on disk reflects mid-game / end-of-observe state instead of just
// the postInit init-time snapshot. Crucial for the matrix's deep-mode
// axes (combat_engaged, age_up_fired, walls_built, etc.) which need
// behavioural ground truth captured AFTER the AI has had time to run.
//
// Pairs with the postInit + gameOverHandler writes already in place:
//   * postInit       — t≈3 s,  initial bias / map / difficulty fields.
//   * anwPersonalitySnapshot — t = 60, 120, 180, …, current state each time.
//   * gameOverHandler — final write at resign / defeat with outcome flags.
//
// Last writer wins on disk, so the matrix harvester (which reads the file
// post-run) sees the most recent behavioural snapshot — exactly what the
// deep axes want. Enabled unconditionally because anwWritePersonalityProbe
// is cheap and gated internally on gANWPostInitFired.
//==============================================================================
rule anwPersonalitySnapshot
active
minInterval 60
{
   if (gANWPostInitFired == false) return;
   anwWritePersonalityProbe();
}

//==============================================================================
// anwInitialEconSnapshot
// Fires once after starting resources/villagers seed. Deferred from postInit
// because immediate emission captures zero-state garbage before the engine
// grants the starting bundle.
//==============================================================================
rule anwInitialEconSnapshot
inactive
minInterval 5
{
   // Wait until either starting resources or starting villagers have been
   // granted — whichever comes first signals seeding is complete.
   if ((kbResourceGet(cResourceFood) <= 0.0) &&
       (kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) <= 0))
   {
      return;
   }
   anwProbe("econ.snap",
      "age=" + kbGetAge() +
      " food=" + kbResourceGet(cResourceFood) +
      " wood=" + kbResourceGet(cResourceWood) +
      " gold=" + kbResourceGet(cResourceGold) +
      " pop=" + kbGetPop() +
      " vills=" + kbUnitCount(cMyID, gEconUnit, cUnitStateAlive));

   // One-shot terrain-anchor resolution probe. Records the actual feature
   // vectors the placement pipeline will steer toward, so post-match we can
   // confirm e.g. an Iroquois AI's ForestEdge anchor is over real woods and
   // not the water center. Uses the same lookups as anwGetPlacementBiasedCenter.
   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID >= 0)
   {
      vector basePos     = kbBaseGetLocation(cMyID, mainBaseID);
      vector terrPrimVec = anwGetTerrainFeatureVector(gANWPreferredTerrainPrimary, basePos);
      vector terrSecVec  = anwGetTerrainFeatureVector(gANWPreferredTerrainSecondary, basePos);
      vector headingVec  = anwGetHeadingFeatureVector(gANWExpansionHeading, basePos);
      anwProbe("compliance.anchor",
         "base=" + anwFmtVec(basePos) +
         " navyVec=" + anwFmtVec(gNavyVec) +
         " terrPrim=" + gANWPreferredTerrainPrimary + ":" + anwFmtVec(terrPrimVec) +
         " terrSec=" + gANWPreferredTerrainSecondary + ":" + anwFmtVec(terrSecVec) +
         " heading=" + gANWExpansionHeading + ":" + anwFmtVec(headingVec) +
         " biasT=" + gANWTerrainBiasStrength +
         " biasH=" + gANWHeadingBiasStrength);
   }

   xsDisableSelf();
}

//==============================================================================
// anwComplianceSnapshot
// Per-civ doctrine compliance snapshot. Fires every 60s and emits FIVE probe
// lines so post-match analysis can confirm each AI is playing per its
// LEGENDARY_LEADERS_TREE.html spec:
//
//   compliance.profile  — current static doctrine state (style/wall/terrain/
//                         heading/distance multipliers/wall level/etc.)
//   compliance.bldg     — building census by category (military/economic/
//                         defensive/wall/naval/religious) with per-type counts
//   compliance.army     — unit composition by abstract type (cav/inf/art/nav/
//                         merc/native) — verifies "siege train" civs actually
//                         build artillery, "cossack voisko" civs cavalry, etc.
//   compliance.placement — for the most recent N military buildings, classify
//                         their offset from base center as front/back/left/
//                         right vs base front vector. Verifies the doctrine
//                         placement preference is actually being honoured.
//   compliance.terrain  — main base + military buildings: count of buildings
//                         in water-adjacent vs inland area groups. Verifies
//                         coastal/river civs actually cluster near water.
//==============================================================================
rule anwComplianceSnapshot
inactive
minInterval 60
{
   // ── 1. Doctrine profile (echo of static state every tick — handy for
   //       cross-checking against meta.buildstyle which only fires once.)
   anwProbe("compliance.profile",
      "style=" + gANWBuildStyle +
      " wallStrat=" + gANWWallStrategy +
      " wallLevel=" + gANWWallLevel +
      " earlyWalls=" + gANWEarlyWallingEnabled +
      " terrPrim=" + gANWPreferredTerrainPrimary +
      " terrSec=" + gANWPreferredTerrainSecondary +
      " heading=" + gANWExpansionHeading +
      " milPlace=" + gANWMilitaryPlacementPreference +
      " milDist=" + gANWMilitaryDistanceMultiplier +
      " ecoDist=" + gANWEconomicDistanceMultiplier +
      " houseDist=" + gANWHouseDistanceMultiplier);

   // ── 2. Building census ─────────────────────────────────────────────────
   int milBarracks  = kbUnitCount(cMyID, cUnitTypeBarracks, cUnitStateABQ);
   int milStables   = kbUnitCount(cMyID, gANWAbstractStables, cUnitStateABQ);
   int milArtillery = kbUnitCount(cMyID, gANWAbstractArtilleryFoundry, cUnitStateABQ);
   int defOutposts  = kbUnitCount(cMyID, gTowerUnit, cUnitStateABQ);
   int defForts     = kbUnitCount(cMyID, gFortUnit, cUnitStateABQ);
   int wallSegs     = kbUnitCount(cMyID, gANWAbstractWall, cUnitStateABQ);
   int navDocks     = kbUnitCount(cMyID, gDockUnit, cUnitStateABQ);
   int ecoMills     = kbUnitCount(cMyID, gFarmUnit, cUnitStateABQ);
   int ecoMarkets   = kbUnitCount(cMyID, gMarketUnit, cUnitStateABQ);
   int ecoTPosts    = kbUnitCount(cMyID, gANWAbstractTradingPost, cUnitStateABQ);
   int civHouses    = kbUnitCount(cMyID, gHouseUnit, cUnitStateABQ);
   int civTCs       = kbUnitCount(cMyID, cUnitTypeTownCenter, cUnitStateABQ);
   int civMonast    = kbUnitCount(cMyID, gANWAbstractMonastery, cUnitStateABQ);

   anwProbe("compliance.bldg",
      "barracks=" + milBarracks +
      " stables=" + milStables +
      " foundry=" + milArtillery +
      " outposts=" + defOutposts +
      " forts=" + defForts +
      " wallSegs=" + wallSegs +
      " docks=" + navDocks +
      " mills=" + ecoMills +
      " markets=" + ecoMarkets +
      " tposts=" + ecoTPosts +
      " houses=" + civHouses +
      " tcs=" + civTCs +
      " monasteries=" + civMonast);

   // ── 3. Army composition ────────────────────────────────────────────────
   int armyInf   = kbUnitCount(cMyID, gANWAbstractInfantry, cUnitStateAlive);
   int armyCav   = kbUnitCount(cMyID, gANWAbstractCavalry, cUnitStateAlive);
   int armyArt   = kbUnitCount(cMyID, gANWAbstractArtillery, cUnitStateAlive);
   int armyNav   = kbUnitCount(cMyID, gANWAbstractWarShip, cUnitStateAlive);
   int armyMerc  = kbUnitCount(cMyID, gANWMercenary, cUnitStateAlive);
   int armyNat   = kbUnitCount(cMyID, gANWAbstractNativeWarrior, cUnitStateAlive);
   int armyHero  = kbUnitCount(cMyID, gANWHero, cUnitStateAlive);

   anwProbe("compliance.army",
      "inf=" + armyInf +
      " cav=" + armyCav +
      " art=" + armyArt +
      " navy=" + armyNav +
      " merc=" + armyMerc +
      " native=" + armyNat +
      " hero=" + armyHero +
      " milPop=" + aiGetMilitaryPop() +
      " totalPop=" + kbGetPop());

   // ── 4. Placement compliance ────────────────────────────────────────────
   // Count military buildings in each cardinal quadrant relative to base
   // front vector. Quadrant assignment matches engine's
   // cBuildingPlacementPreferenceFront/Back/Left/Right semantics:
   //   front:  dot(offset, frontVec)  > |perp(offset, frontVec)|
   //   back :  dot(offset, frontVec)  < -|perp...|
   //   right:  perp > 0 (cross-product sign)
   //   left :  perp < 0
   int mainBaseID = kbBaseGetMainID(cMyID);
   int frontC = 0; int backC = 0; int leftC = 0; int rightC = 0;
   if (mainBaseID >= 0)
   {
      vector basePos  = kbBaseGetLocation(cMyID, mainBaseID);
      vector frontVec = kbBaseGetFrontVector(cMyID, mainBaseID);
      if ((basePos != cInvalidVector) && (frontVec != cInvalidVector) &&
          ((xsVectorGetX(frontVec) != 0.0) || (xsVectorGetZ(frontVec) != 0.0)))
      {
         float fx = xsVectorGetX(frontVec);
         float fz = xsVectorGetZ(frontVec);
         int q = createSimpleUnitQuery(cUnitTypeBarracks, cMyID, cUnitStateABQ);
         int n = kbUnitQueryExecute(q);
         for (i = 0; < n)
         {
            int uid = kbUnitQueryGetResult(q, i);
            vector p = kbUnitGetPosition(uid);
            float ox = xsVectorGetX(p) - xsVectorGetX(basePos);
            float oz = xsVectorGetZ(p) - xsVectorGetZ(basePos);
            float dot   = ox * fx + oz * fz;
            float perp  = ox * fz - oz * fx;  // 2D cross sign
            float adot  = dot;  if (adot < 0.0) { adot = -1.0 * adot; }
            float aperp = perp; if (aperp < 0.0) { aperp = -1.0 * aperp; }
            if (adot >= aperp)
            {
               if (dot >= 0.0) { frontC = frontC + 1; } else { backC = backC + 1; }
            }
            else
            {
               if (perp >= 0.0) { rightC = rightC + 1; } else { leftC = leftC + 1; }
            }
         }
         kbUnitQueryDestroy(q);
      }
   }
   anwProbe("compliance.placement",
      "front=" + frontC +
      " back=" + backC +
      " left=" + leftC +
      " right=" + rightC +
      " expectedPref=" + gANWMilitaryPlacementPreference);

   // ── 5. Terrain compliance ──────────────────────────────────────────────
   // For each barracks, classify the area-group of its position. Compare
   // against a navy-vec area-group lookup to count buildings that landed in
   // water-adjacent regions vs inland. Doesn't need elevation; just water/
   // not-water — which is what the HTML reference's coastal/river/inland
   // distinction reduces to in the engine.
   int waterAdj = 0;
   int inland   = 0;
   int qB = createSimpleUnitQuery(cUnitTypeBarracks, cMyID, cUnitStateABQ);
   int nB = kbUnitQueryExecute(qB);
   for (i = 0; < nB)
   {
      int bid = kbUnitQueryGetResult(qB, i);
      vector bp = kbUnitGetPosition(bid);
      int areaID = kbAreaGetIDByPosition(bp);
      // Adjacent water means a near-by area is water. Engine has no direct
      // "is shoreline" — proxy: is the building's area-group not the same
      // as the dominant land group? That's expensive, so simpler proxy:
      // is the building within ~30m of gNavyVec?
      if (gNavyVec != cInvalidVector)
      {
         float dxw = xsVectorGetX(bp) - xsVectorGetX(gNavyVec);
         float dzw = xsVectorGetZ(bp) - xsVectorGetZ(gNavyVec);
         float distSq = dxw * dxw + dzw * dzw;
         if (distSq < (60.0 * 60.0)) { waterAdj = waterAdj + 1; }
         else                         { inland   = inland   + 1; }
      }
      else
      {
         inland = inland + 1;
      }
   }
   kbUnitQueryDestroy(qB);
   anwProbe("compliance.terrain",
      "barracksWaterAdj=" + waterAdj +
      " barracksInland=" + inland +
      " navyVec=" + anwFmtVec(gNavyVec));
}

//==============================================================================
// anwAgeUpProbe
// Stamps a probe whenever the AI advances to a new age. Lets analysis chart
// each civ's age-up tempo against its doctrine (e.g., Naval Mercantile is
// supposed to push Age 2 fast, Compact Fortified Core ages slower).
//==============================================================================
rule anwAgeUpProbe
inactive
minInterval 5
{
   static int lastAge = 0;
   int age = kbGetAge();
   if (age != lastAge)
   {
      anwProbe("compliance.age",
         "from=" + lastAge +
         " to=" + age +
         " atMs=" + xsGetTime() +
         " food=" + kbResourceGet(cResourceFood) +
         " wood=" + kbResourceGet(cResourceWood) +
         " gold=" + kbResourceGet(cResourceGold) +
         " vills=" + kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) +
         " milPop=" + aiGetMilitaryPop());
      lastAge = age;
   }
}

//==============================================================================
// anwCombatComplianceSnapshot
// Periodic poll of combat-plan health: how many active combat / attack /
// defend plans, current military stance, total mil pop vs current cap, total
// army value (HP * count proxy via unit counts × type weights), and recent
// attack-plan churn (created vs destroyed delta since last tick).
//
// Coverage rationale:
//   - validates that doctrines that should attack early (Forward Operational
//     Line, Mobile No Walls) actually have attack plans dispatched by Age 2-3
//   - validates defensive doctrines (Compact Fortified Core, Citadel) keep
//     defend plans active
//   - flags AIs whose army population stagnates (a sign settlerless rules or
//     trainPlan starvation went sideways)
//==============================================================================
rule anwCombatComplianceSnapshot
inactive
minInterval 60
{
   static int lastAttackTotal = 0;
   static int lastMilPop      = 0;

   // aiPlanGetActiveCount() takes 0 args in this engine; use aiPlanGetNumber
   // with -1 to get a per-type live count.
   int attackPlans  = aiPlanGetNumber(cPlanCombat,   -1, true);
   int defendPlans  = aiPlanGetNumber(cPlanDefend,   -1, true);
   int reservePlans = aiPlanGetNumber(cPlanReserve,  -1, true);
   int trainPlans   = aiPlanGetNumber(cPlanTrain,    -1, true);
   int researchPlns = aiPlanGetNumber(cPlanResearch, -1, true);

   int milPop  = aiGetMilitaryPop();
   int milDelta = milPop - lastMilPop;
   int atkDelta = attackPlans - lastAttackTotal;

   // Hatred ranking — which enemy this AI currently considers the primary
   // threat. Useful to confirm aggressive doctrines don't get distracted.
   int hatedEnemy = aiGetMostHatedPlayerID();

   anwProbe("compliance.combat",
      "attackPlans=" + attackPlans +
      " defendPlans=" + defendPlans +
      " reservePlans=" + reservePlans +
      " trainPlans=" + trainPlans +
      " researchPlans=" + researchPlns +
      " milPop=" + milPop +
      " milDelta=" + milDelta +
      " atkDelta=" + atkDelta +
      " hatedEnemy=" + hatedEnemy +
      " defenseReflex=" + gDefenseReflexBaseID);

   lastAttackTotal = attackPlans;
   lastMilPop      = milPop;
}

//==============================================================================
// anwEconComplianceSnapshot
// Periodic poll of villager allocation per resource. Compares actual
// gatherer % against the doctrine's expected emphasis. Doctrines like
// "Manor Boom" should bias food/wood; "Naval Mercantile" should push wood
// for docks then gold via fishing; "Hussite Faith Militia" should normalise
// food + wood early. The probe also samples idle villager count, a proxy
// for plan-starvation bugs.
//==============================================================================
rule anwEconComplianceSnapshot
inactive
minInterval 60
{
   float pctFood = aiGetResourceGathererPercentage(cResourceFood);
   float pctWood = aiGetResourceGathererPercentage(cResourceWood);
   float pctGold = aiGetResourceGathererPercentage(cResourceGold);

   int villsAlive  = kbUnitCount(cMyID, gEconUnit, cUnitStateAlive);
   // No portable cUnitStateWorking constant — use econPop accounting as a
   // proxy. aiGetEconomyPop is the engine's count of vills in gather plans;
   // delta vs alive is "vills not assigned to a gather plan" ≈ idle.
   int villsIdle   = villsAlive - aiGetEconomyPop();
   if (villsIdle < 0) { villsIdle = 0; }
   int popCap      = kbGetPopCap();
   int currentPop  = kbGetPop();
   float foodNet   = kbGetAmountValidResources(0, cResourceFood, cAIResourceSubTypeEasy, 99999.0);
   float woodNet   = kbGetAmountValidResources(0, cResourceWood, cAIResourceSubTypeEasy, 99999.0);
   float goldNet   = kbGetAmountValidResources(0, cResourceGold, cAIResourceSubTypeEasy, 99999.0);

   anwProbe("compliance.econ",
      "pctFood=" + pctFood +
      " pctWood=" + pctWood +
      " pctGold=" + pctGold +
      " vills=" + villsAlive +
      " villsIdle=" + villsIdle +
      " pop=" + currentPop +
      " popCap=" + popCap +
      " foodValid=" + foodNet +
      " woodValid=" + woodNet +
      " goldValid=" + goldNet);
}

//==============================================================================
// anwShipmentComplianceSnapshot
// Tracks shipment economy. Reports shipments available now, total XP,
// current age (so the analyser can correlate shipment cadence with age-up
// tempo). The shipGrantedHandler hook in aiHCCards.xs emits per-ship
// `tech.shipment` events for the actual cards chosen.
//==============================================================================
rule anwShipmentComplianceSnapshot
inactive
minInterval 90
{
   float shipsReady = kbResourceGet(cResourceShips);
   float xp         = kbResourceGet(cResourceXP);
   int   age        = kbGetAge();

   anwProbe("compliance.ship",
      "shipsReady=" + shipsReady +
      " xp=" + xp +
      " age=" + age);
}

//==============================================================================
// anwPlacementDeepSnapshot
// Extends compliance.placement to ALL major building types — TC, market,
// dock, mill, monastery — each tallied per cardinal quadrant. Lets the
// validator confirm civic vs military buildings cluster differently per
// doctrine (e.g., Compact Fortified Core: civic at back, military mixed;
// Naval Mercantile: docks at front-toward-water, military at back).
//
// One probe per building type, so the parser can index by `bldg=<type>`.
//==============================================================================
// `label` is a reserved keyword in XS (goto-style label syntax) — using
// it as a parameter name parses as `parseExpression2 → 'LABEL' is not a
// valid operator` at the first reference. Renamed to `bldgLabel`.
void anwTallyBuildingQuadrants(int bldgType = -1, string bldgLabel = "?")
{
   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID < 0) { return; }

   vector basePos  = kbBaseGetLocation(cMyID, mainBaseID);
   vector frontVec = kbBaseGetFrontVector(cMyID, mainBaseID);
   if ((basePos == cInvalidVector) || (frontVec == cInvalidVector)) { return; }
   if ((xsVectorGetX(frontVec) == 0.0) && (xsVectorGetZ(frontVec) == 0.0)) { return; }

   float fx = xsVectorGetX(frontVec);
   float fz = xsVectorGetZ(frontVec);

   int q = createSimpleUnitQuery(bldgType, cMyID, cUnitStateABQ);
   int n = kbUnitQueryExecute(q);
   int frontC = 0; int backC = 0; int leftC = 0; int rightC = 0;
   for (i = 0; < n)
   {
      int uid = kbUnitQueryGetResult(q, i);
      vector p = kbUnitGetPosition(uid);
      float ox = xsVectorGetX(p) - xsVectorGetX(basePos);
      float oz = xsVectorGetZ(p) - xsVectorGetZ(basePos);
      float dot   = ox * fx + oz * fz;
      float perp  = ox * fz - oz * fx;
      float adot  = dot;  if (adot  < 0.0) { adot  = -1.0 * adot;  }
      float aperp = perp; if (aperp < 0.0) { aperp = -1.0 * aperp; }
      if (adot >= aperp)
      {
         if (dot >= 0.0) { frontC = frontC + 1; } else { backC = backC + 1; }
      }
      else
      {
         if (perp >= 0.0) { rightC = rightC + 1; } else { leftC = leftC + 1; }
      }
   }
   kbUnitQueryDestroy(q);

   if ((frontC + backC + leftC + rightC) == 0) { return; }

   anwProbe("compliance.placeAll",
      "bldg=" + bldgLabel +
      " front=" + frontC +
      " back=" + backC +
      " left=" + leftC +
      " right=" + rightC);
}

rule anwPlacementDeepSnapshot
inactive
minInterval 90
{
   anwTallyBuildingQuadrants(cUnitTypeTownCenter,            "tc");
   anwTallyBuildingQuadrants(gMarketUnit,                    "market");
   anwTallyBuildingQuadrants(gDockUnit,                      "dock");
   anwTallyBuildingQuadrants(gFarmUnit,                      "mill");
   anwTallyBuildingQuadrants(gANWAbstractMonastery,     "monastery");
   anwTallyBuildingQuadrants(gTowerUnit,                     "outpost");
   anwTallyBuildingQuadrants(gANWAbstractStables,       "stables");
   anwTallyBuildingQuadrants(gANWAbstractArtilleryFoundry, "foundry");
   anwTallyBuildingQuadrants(gANWAbstractTradingPost,   "tpost");
}

//==============================================================================
// anwWallGeometrySnapshot
// Wall ring health: count of segments, wall plan IDs active, and the
// minimum / maximum distance of any wall segment from the main base. Big
// gap between min and max distance is a sign the ring tried to close but
// had to detour; tightly clustered = unfinished partial ring.
//==============================================================================
rule anwWallGeometrySnapshot
inactive
minInterval 90
{
   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID < 0) { return; }
   vector basePos = kbBaseGetLocation(cMyID, mainBaseID);
   if (basePos == cInvalidVector) { return; }

   int q = createSimpleUnitQuery(gANWAbstractWall, cMyID, cUnitStateAlive);
   int n = kbUnitQueryExecute(q);
   float minDist = 99999.0;
   float maxDist = 0.0;
   float sumDist = 0.0;
   for (i = 0; < n)
   {
      int uid = kbUnitQueryGetResult(q, i);
      vector p = kbUnitGetPosition(uid);
      float dx = xsVectorGetX(p) - xsVectorGetX(basePos);
      float dz = xsVectorGetZ(p) - xsVectorGetZ(basePos);
      float d  = sqrt(dx * dx + dz * dz);
      if (d < minDist) { minDist = d; }
      if (d > maxDist) { maxDist = d; }
      sumDist = sumDist + d;
   }
   kbUnitQueryDestroy(q);

   float avgDist = 0.0;
   if (n > 0) { avgDist = sumDist / n; } else { minDist = 0.0; }

   int wallPlans = aiPlanGetNumber(cPlanBuildWall, -1, true);

   anwProbe("compliance.wallGeom",
      "segments=" + n +
      " plans=" + wallPlans +
      " minDist=" + minDist +
      " maxDist=" + maxDist +
      " avgDist=" + avgDist +
      " strategy=" + gANWWallStrategy);
}

//==============================================================================
// anwDiplomacyComplianceSnapshot
// Diplomatic posture: tribute received/sent (via aiResourceGetTribute*),
// allied native count (TPs on native sites), revolution state if any.
// Captures the kind of strategic decision that the HTML reference cares
// about — e.g., Lakota's "Native Confederation" doctrine should ally with
// natives early, Bourbon France should not rush revolution.
//==============================================================================
rule anwDiplomacyComplianceSnapshot
inactive
minInterval 90
{
   int  tposts      = kbUnitCount(cMyID, gANWAbstractTradingPost, cUnitStateABQ);
   int  nativeWar   = kbUnitCount(cMyID, gANWAbstractNativeWarrior, cUnitStateAlive);
   int  age         = kbGetAge();
   // Revolution detection without civIsRevolted(): post-revolt players hit
   // age 5 with cvMaxAge==cAge5; we proxy via "did we reach an age past
   // cAge4?". Not perfect but visible in the probe stream alongside
   // meta.leader_init which fires the revolution-commander branch.
   bool likelyRevolted = (age >= cAge5);

   int enemy     = aiGetMostHatedPlayerID();

   anwProbe("compliance.diplo",
      "tposts=" + tposts +
      " nativeWar=" + nativeWar +
      " age=" + age +
      " likelyRevolted=" + likelyRevolted +
      " enemy=" + enemy);
}

//==============================================================================
// anwRuleHealthSnapshot
// Reports active vs inactive count of LL-managed rules (anything starting
// with "ll"). Quickly answers "did postInit's xsEnableRule calls actually
// stick?" — a class of bug we've hit before.
//==============================================================================
rule anwRuleHealthSnapshot
inactive
minInterval 120
{
   int hb = 0; int plan = 0; int build = 0; int navy = 0;
   int prof = 0; int bldg = 0; int army = 0; int place = 0; int terr = 0;
   int comb = 0; int econ = 0; int ship = 0; int placeD = 0; int wall = 0;
   int diplo = 0; int age = 0; int tac = 0; int evt = 0;

   if (xsIsRuleEnabled("anwHeartbeat"))                  hb = 1;
   if (xsIsRuleEnabled("anwPlanSnapshot"))               plan = 1;
   if (xsIsRuleEnabled("anwComplianceSnapshot"))         prof = 1;
   if (xsIsRuleEnabled("anwCombatComplianceSnapshot"))   comb = 1;
   if (xsIsRuleEnabled("anwEconComplianceSnapshot"))     econ = 1;
   if (xsIsRuleEnabled("anwShipmentComplianceSnapshot")) ship = 1;
   if (xsIsRuleEnabled("anwPlacementDeepSnapshot"))      placeD = 1;
   if (xsIsRuleEnabled("anwWallGeometrySnapshot"))       wall = 1;
   if (xsIsRuleEnabled("anwDiplomacyComplianceSnapshot")) diplo = 1;
   if (xsIsRuleEnabled("anwAgeUpProbe"))                 age = 1;
   if (xsIsRuleEnabled("wallPlanStallWatchdog"))        build = 1;
   if (xsIsRuleEnabled("anwTacticsComplianceSnapshot"))  tac = 1;
   if (xsIsRuleEnabled("anwEventDeltaSnapshot"))         evt = 1;

   anwProbe("compliance.rules",
      "hb=" + hb +
      " planSnap=" + plan +
      " profile=" + prof +
      " combat=" + comb +
      " econ=" + econ +
      " ship=" + ship +
      " placeDeep=" + placeD +
      " wallGeom=" + wall +
      " diplo=" + diplo +
      " ageUp=" + age +
      " wallStall=" + build +
      " tactics=" + tac +
      " eventDelta=" + evt);
}

//==============================================================================
// anwTacticsComplianceSnapshot
// Bundles per-AI tactical state that doesn't fit elsewhere: treaty status,
// base count, forward-base ID + state, hero alive/idle, exploration plan
// counts, total bases, total villager-on-trade-route gather. This is the
// snapshot that closes the "what is the AI doing right now overall" gap.
//==============================================================================
rule anwTacticsComplianceSnapshot
inactive
minInterval 60
{
   bool treaty   = aiTreatyActive();
   int  treatyEnd = aiTreatyGetEnd();
   int  bases    = kbBaseGetNumber(cMyID);
   int  fwdBase  = gForwardBaseID;
   int  fwdState = gForwardBaseState;
   int  heroes   = kbUnitCount(cMyID, gANWHero, cUnitStateAlive);
   int  explore  = aiPlanGetNumber(cPlanExplore, -1, true);
   int  transp   = aiPlanGetNumber(cPlanTransport, -1, true);
   int  repair   = aiPlanGetNumber(cPlanRepair, -1, true);
   int  defReflex = gDefenseReflexBaseID;

   anwProbe("compliance.tactics",
      "treaty=" + treaty +
      " treatyEnd=" + treatyEnd +
      " bases=" + bases +
      " fwdBase=" + fwdBase +
      " fwdState=" + fwdState +
      " heroes=" + heroes +
      " explorePlans=" + explore +
      " transportPlans=" + transp +
      " repairPlans=" + repair +
      " defReflexBase=" + defReflex);
}

//==============================================================================
// anwEventDeltaSnapshot
// Delta-detector. Polls counters that increment on key events and emits a
// probe whenever any moved since the last tick. Lets us reconstruct an
// event log without per-call-site hooks for: shipment grants, TPs built,
// natives allied, attack-plan churn, base births/deaths.
//==============================================================================
rule anwEventDeltaSnapshot
inactive
minInterval 30
{
   static int lastTPosts      = 0;
   static int lastBases       = 0;
   static int lastFwdBase     = -1;
   static int lastAttackPlans = 0;
   static int lastShipsTotal  = 0;
   static int lastHeroes      = 0;

   int tposts = kbUnitCount(cMyID, gANWAbstractTradingPost, cUnitStateABQ);
   int bases  = kbBaseGetNumber(cMyID);
   int fwd    = gForwardBaseID;
   int atk    = aiPlanGetNumber(cPlanCombat, -1, true);
   // Shipments-total proxy: sum of "ships sent" if engine exposes; otherwise
   // approximate by current XP (monotonic) — simpler is just to record the
   // count of distinct tech.ship probes via heartbeat counter.
   int heroes = kbUnitCount(cMyID, gANWHero, cUnitStateAlive);

   bool moved = false;
   int  dTP   = tposts - lastTPosts;
   int  dBase = bases  - lastBases;
   int  dAtk  = atk    - lastAttackPlans;
   int  dHero = heroes - lastHeroes;

   if (dTP   != 0) { moved = true; }
   if (dBase != 0) { moved = true; }
   if (dAtk  != 0) { moved = true; }
   if (dHero != 0) { moved = true; }
   if (fwd != lastFwdBase) { moved = true; }

   if (moved == true)
   {
      anwProbe("event.delta",
         "dTP=" + dTP +
         " dBases=" + dBase +
         " dAttacks=" + dAtk +
         " dHeroes=" + dHero +
         " fwdBaseFrom=" + lastFwdBase +
         " fwdBaseTo=" + fwd +
         " atMs=" + xsGetTime());
   }

   lastTPosts      = tposts;
   lastBases       = bases;
   lastFwdBase     = fwd;
   lastAttackPlans = atk;
   lastHeroes      = heroes;
}