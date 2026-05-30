//==============================================================================
/* aiHeader.xs
   
   This file contains all Behavior trait and control variable definitions.
   It is included by the loader file, above the inclusion of aiMain.xs.
   
   This file is intended primarily as a reference for the variables that can be safely set by the loader file.
   
   IMPORTANT: once you have your loader file you can set the variables inside of preInit().
   Do not set any of these variables inside of postInit() please.
   Now something to keep in mind especially for people who don't usually program.
   Take for example cvMaxAge, its default value is cAge5.
   If you want your AI to be capped at the Imperial Age you don't have to do anything anymore.
   You don't need to put "cvMaxAge = cAge5;" in your preInit again.
   You could do it so you remind yourself of what the default value was of course.
   Same goes for all other variables, assigning it the default value inside of your loader does nothing.
   
   READ ME: most of the cv**** variables below are meant to be set only ONCE.
   For example if you put cvOkToAttack to false then the AI will never attack.
   Setting cvOkToAttack to true later has no effect since the attack manager is already off.
   Thus if you want to be able to switch these "one time" things around you MUST have an 
   understanding of the real AI complex and how to enable/disable stuff again.
   
   There are some variables in this file that you CAN change later on and it will work on its own.
   This includes resetting them to their original value and restoring original behaviour.
   Those are:
   - All bt*** (Behavior Traits) variables.
   - cvOkToBuildConsulate.
   - cvOkToGatherFood/Wood/Gold.
   - cvMaxArmyPop / cvMaxCivPop, adjusting these after the AI has reached its cvMaxAge has no use though.
   - cvPrimaryArmyUnit / Secondary / Tertiary.
   - cvNumArmyUnitTypes.
   - cvMaxTowers.
   - cvDefenseReflexRadiusActive / Passive / Radius.
   - cvCreateBaseAttackRoute.
   
   If you want to give your AI a custom handicap that can be done in either
   preInit or postInit, that doesn't matter at all.
   Example: kbSetPlayerHandicap(cMyID, kbGetPlayerHandicap(cMyID) * 0.75);
*/
//==============================================================================


//==============================================================================
// Behavior Traits.
//
// These variables all range from -1.0 to +1.0, with 0.0 as a neutral value.
// All names start with bt for Behavior Trait, followed by two words that are opposites. 
// IMPORTANT: A value above zero emphasizes the first word, a negative value emphasizes the second word. 
// For example: setting btRushBoom to 1.0 would create an extreme rusher, setting it to -1.0 would create an extreme boomer.

extern float   btRushBoom = 0.0;       /* Positive value so a rusher means:
                                          > 0.0 :
                                          More maximum allowed army population in Commerce to potentially have biger waves early on.
                                          We only make an age up plan for the Fortress Age after being 10 minutes in the Commerce Age.
                                          We will try to instantly scout the enemy base so we have a target to rush.
                                          We will get an extra resource crate in Commerce at the expense of an upgrade.
                                          
                                          Negative value so a boomer means:
                                          < 0.0 : A higher resource priority on economic upgrades.
                                          
                                          <= 0.0 :
                                          Less maximum allowed army population in Commerce so easier to age up to Fortress.
                                          More likely to build an extra Bank / Market early on.
                                          Chance to start fishing very early when possible.
                                          When playing on hardest+ and we're in Commerce we only attack after 5 minutes have passed since age up.
                                          We create some extra navy when we're also in the Fortress Age or above.
                                          
                                          <= -0.5 :
                                          Less maximum allowed army population in Commerce and Fortress so easier to age up to Industrial.
                                          When playing on hardest+ and we're in Commerce/Fortress we only attack after 5 minutes have passed since age up.
                                          
                                          If the main base isn't under attach a lower value means a lower priority for sending unit shipments.
                                       */
                                       
extern float   btOffenseDefense = 0.0; /* Positive value so offensively orientated means:
                                          >= 0.0 : forces Fort Wagons to make a forward base if the difficulty is moderate and above.
                                          
                                          Negative value so defensively orientated means:
                                          <= 0.0 : European AI have a 20% chance to put a Fort Wagon into their deck.
                                          
                                          < 0.0 : More Towers early on.
                                       */

extern float   btBiasNative = 0.0;     /* A higher value means the AI will build Minor Native TPs in quicker succession.
                                          A higher value means more % of our military will be made up of Minor Natives.
                                          
                                          Positive value so Native orientated means:
                                          >= 0.5 : Higher chance to put minor Native cards into the deck.
                                          
                                          Negative value so staying away from Natives means:
                                          < -0.5 : Lower chance to put minor Native cards into the deck.
                                       */
                                       
extern float   btBiasTrade = 0.0;      /* A higher value means the AI will build Trade Route TPs in quicker succession.
                                          A higher value means the AI will assign a higher resource priority to Trade Route upgrades.
                                          
                                          Positive value so Trade orientated means:
                                          >= 0.5 : Higher chance to put Trade cards into the deck.
                                          
                                          Negative value so staying away from Trade means:
                                          < -0.5 : Lower chance to put Trade cards into the deck.
                                       */

/* For the 3 values below to make sense you must know something about a thing called the "unitpicker".
   Basically this is an algorithm that determines which unit would be best suited for us to build.
   Oversimplified this means that if the enemy we're currently attacking (cvPlayerToAttack or random)
   has a lot of cavalry we will make a lot of Pikemen. Because the algorithm detects we need to make units that counter cavalry.
   The values below can influence the final calculations done by this unitpicker.
   EXAMPLE: The algorithm decides Pikemen have a priority of 0.5 but btBiasInf is set to 1.0 their final priority will be 1.5.
   The calculation for this is as follows: Algorithm result (0.5) + 0.5 + (btBiasInf / 2.0) = 1.5.
   So if we had a btBiasInf of 0.0 in this example the final priority of the Pikemen would be 1.0.
   NOTEWORTHY: If you assign -1.0 to any of these that unit type will completely be exempted from being trained.
*/                                       
extern float   btBiasCav = 0.0;
extern float   btBiasArt = 0.0;
extern float   btBiasInf = 0.0;

//==============================================================================
// Control Variables.
//
// Control variables are set in the loader file's preInit() function.
// You can use these variables to limit the AI from doing certain things.
//==============================================================================

// Permission-oriented control variables:
extern bool    cvInactiveAI = false;         // Setting this to true will cause the AI to only micro its existing units, nothing else. This is often used for AIs entirely ran by triggers.
extern bool    cvOkToAttack = true;          // False prohibits attacking enemies and defending allies both on the land and on the water.
extern bool    gDelayAttacks = false;        // Standard(difficulty) AI will be blocked from attacking until they're attacked themselves or they reach the Industrial Age.
                                             // If you want your standard(difficulty) AI to just instantly attack specifically assign this value false in preInit() since it will be put to true
                                             // inside of the main script for the standard AI.
extern bool    cvOkToTrainArmy = true;       // False prohibits the training of land military units. But it doesn't prevent the choosing of age-ups which give units or sending unit shipments.
extern bool    cvOkToTrainNavy = true;       // False prohibits training naval units. But it doesn't prevent the choosing of age-ups which give ships or sending ship shipments.
extern bool    cvOkToTaunt = true;           // False prohibits routine ambience (personality development) chats. NOTE that this defaults to FALSE in SPC (scenarios) games so put it to true yourself.
extern bool    cvOkToAllyNatives = true;     // False prohibits the building of Trading Posts on Native Settlements.
extern bool    cvOkToClaimTrade = true;      // False prohibits the building of Trading Posts on Trade Routes.
extern bool    cvOkToBuild = true;           // False prohibits buildings alltogether, including using Wagons.
extern bool    cvOkToFortify = true;         // False prohibits constructing Tower like buildings. (Outposts / War Huts / Castles etc)
extern bool    cvOkToBuildForts = true;      // False prohibits sending and using Fort Wagons.
                                             // If you put both cvOkToFortify and cvOkToBuildForts to false then Incas won't build Strongholds either.

extern bool    cvOkToBuildConsulate = true;  // False prevents the construction of the Asian Consulate building.

extern bool    cvOkToResign = true;          // AI can offer to resign when it feels overwhelmed. This automatically defaults to false in SPC games, so set it to true if you want it for your scenario.
extern bool    cvOkToExplore = true;         // Setting this false will disable all AI explore plans.
extern bool    cvOkToFish = true;            // Setting it false will prevent the AI from building dock and fishing boats, and from
                                             // using the starting ship (if any) for fishing.
                                             // If you wish for the AI to actually fish in your mission you need to also
                                             // need to mark your scenario as an AIFishingUseful type, otherwise 0 fishing will take place regardless.
extern bool    cvOkToGatherFood = true;      // Setting it false will turn off food gathering. True turns it on.
extern bool    cvOkToGatherGold = true;      // Setting it false will turn off gold gathering. True turns it on.
extern bool    cvOkToGatherWood = true;      // Setting it false will turn off wood gathering. True turns it on.

extern bool    cvOkToGatherNuggets = true;   // Setting it false will prevent the land explore plan from nugget hunting.
extern bool    cvOkToBuildDeck = false;      // Setting it false will prevent deck building, this is always set to true in RM games automatically.

// Limit control variables
extern int     cvMaxArmyPop = -1;            // -1 means the AI decides himself. 0 means don't train anything.
extern int     cvMaxCivPop = -1;             // -1 means the AI decides himself. 0 means don't train anything.
extern int     cvMaxAge = cAge5;             // Set this to cAge1..cAge4 to cap age upgrades. cvMaxAge = cAge3 will let the AI go age 3, but not age 4.
extern int     cvMaxTowers = -1;             // The AI will try to create this many Towers.
extern int     cvMinNumVills = -1;           // Floor on villager count the AI should reach before diverting to military. -1 lets the AI decide.

// Non-boolean control variables
                                                   // To make the AI train mostly hussars and some musketeers, set cvNumArmyUnitTypes = 2; cvPrimaryArmyUnit = cUnitTypeHussar;
                                                   // and cvSecondaryArmyUnitType = cUnitTypeMusketeer;
extern int     cvPrimaryArmyUnit = -1;             // This sets the AI's primary land military unit type. -1 lets the AI decide on its own.
extern int     cvSecondaryArmyUnit = -1;           // This sets the AI's secondary land military unit type, applies only if cvNumArmyUnitTypes is > 2 or set to -1.
extern int     cvTertiaryArmyUnit = -1;            // This sets the AI's tertiary land military unit type, applies only if cvNumArmyUnitTypes is > 3 or set to -1.
extern int     cvNumArmyUnitTypes = -1;            // The AI will not use more than this number of unit types. (May be less if not available). -1 means AI can decide.

extern int     cvPlayerToAttack = -1;     // Leaving this at -1 will let the AI choose its own targets. Setting it to an enemy player ID will make it focus
                                          // on that player and never attempt to attack anybody else.
                                          
extern float   cvDefenseReflexRadiusActive = 60.0;    // When the AI is in a defense reflex, this is the engage range from that base's center.
extern float   cvDefenseReflexRadiusPassive = 30.0;   // When the AI is in a defense reflex, but hiding in its main base to regain strength, this is the main base attack range.
extern float   cvDefenseReflexSearchRadius = 60.0;    // How far out from a base to look before triggering a defense reflex. THIS MUST NOT BE GREATER THAN 'RadiusActive' ABOVE!

// Legendary Leaders build-style identifiers and placement knobs.
extern int     cLLBuildStyleCompactFortifiedCore = 1;
extern int     cLLBuildStyleDistributedEconomicNetwork = 2;
extern int     cLLBuildStyleForwardOperationalLine = 3;
extern int     cLLBuildStyleMobileFrontierScatter = 4;
extern int     cLLBuildStyleShrineTradeNodeSpread = 5;
extern int     cLLBuildStyleCivicMilitiaCenter = 6;
extern int     cLLBuildStyleSteppeCavalryWedge = 7;          // dispersed mobile; minimal walls; cavalry-led raiding bases.
extern int     cLLBuildStyleNavalMercantileCompound = 8;     // coastal bank/dock cluster; eco-heavy; deep harbour.
extern int     cLLBuildStyleSiegeTrainConcentration = 9;     // clustered military; heavy artillery park; forward grand battery.
extern int     cLLBuildStyleJungleGuerrillaNetwork = 10;     // scattered war huts; ambush approaches; no perimeter wall.
extern int     cLLBuildStyleHighlandCitadel = 11;            // multi-ring high-walled mountain fortress; defensive masterpiece.
extern int     cLLBuildStyleCossackVoisko = 12;              // massed barracks + blockhouse net; forward host muster.
extern int     cLLBuildStyleRepublicanLevee = 13;            // citizen-army compound; militia centers; civic spine.
extern int     cLLBuildStyleAndeanTerraceFortress = 14;      // terraced highland fort; tight core; tower-heavy ring.

extern int     gLLBuildStyle = 0;
extern int     gLLWallLevel = 1;
extern bool    gLLEarlyWallingEnabled = true;
extern bool    gLLLateWallingEnabled = true;

// Walling strategies (per-leader historical doctrine for wall placement).
// Selects which routine in aiBuildingsWalls.xs plans the Age-1 fortification.
extern int     cLLWallStrategyFortressRing        = 0;  // Full double ring, all sides — Valette/Pachacuti/Frederick/Suleiman/Catherine/Bourbon
extern int     cLLWallStrategyChokepointSegments  = 1;  // Segment walls at terrain pinches — Shivaji/Menelik/Kangxi/Andean civs
extern int     cLLWallStrategyCoastalBatteries    = 2;  // Land-side ring, gun towers at coast — Wellington/Henry/Maurice/Barbary
extern int     cLLWallStrategyFrontierPalisades   = 3;  // Quick wooden ring + blockhouses — Washington/Jefferson/Brock/Kruger/Mannerheim/etc.
extern int     cLLWallStrategyUrbanBarricade      = 4;  // Tight compact inner ring + towers — Robespierre/Garibaldi
extern int     cLLWallStrategyMobileNoWalls       = 5;  // Scouts + outposts, no walls — Napoleon/Crazy Horse/Hiawatha/Montezuma/Usman/Isabella/Gustavus

extern int     gLLWallStrategy = 0;  // default = FortressRing

// ----- Per-civ wall tuning knobs (read by aiBuildingsWalls.xs) -----------
// Defaults selected so behaviour is identical to pre-knob code when every
// leader leaves them at default. Leaders override these in their personality
// files (game/ai/leaders/leader_<name>.xs or leaderCommon.xs branches).
// Each knob fires a one-time probe at first read so validators can confirm
// per-civ values reached the engine: [LLP v=2] wall.tune key=<knob> val=<v>
extern int     gLLWallRadius                = 18;     // ring/segment radius in tiles  (Pachacuti 14, Wellington 22)
extern int     gLLWallGateCount             = 3;      // gates per ring  (Bourbon 2, Suleiman 4)
extern bool    gLLWallTierAge2Stone         = false;  // true=jump to stone at Colonial, false=stay palisade
extern int     gLLWallTriggerAge            = 2;      // first age that lays a wall  (Robespierre 3, Pachacuti 2)
extern int     gLLWallSegmentLength         = 12;     // chokepoint segment length in tiles  (Shivaji 8, Menelik 16)
extern int     gLLWallTowerInterleave       = 6;      // tower every N pieces (0=none)  (Maltese 4, Frederick 8, Crazy Horse 0)
extern int     gLLWallSecondaryStrategy     = -1;     // fallback strategy if primary impossible (-1=none, else cLLWallStrategy*)
extern int     gLLWallVillagerCount         = 4;      // vils dispatched to wall plan  (Bourbon turtle 10, Napoleon 2)
extern float   gLLWallForwardBiasFraction   = 0.5;    // 0.0=hug TC, 1.0=push to choke  (Napoleon 0.8, Pachacuti 0.2)
extern int     gLLWallOuterRingDelta        = 0;      // outer-ring offset (0=single ring)  (Frederick 8, Suleiman 6)
extern int     gLLWallEarlyOutpostCount     = 1;      // outposts to plant before first wall  (Lakota/Hauden 4, EU 1)
extern int     gLLWallRepairAggressiveness  = 1;      // 0=ignore, 1=lazy, 2=normal, 3=instant  (Bourbon 3, Crazy Horse 0)
extern int     gLLWallClosurePctTarget      = 60;     // closure % counted as "done"  (Frederick 85, FrontierPalisade 55)
extern bool    gLLWallNoWaterBuild          = true;   // refuse to build into water tiles (true for all by default after water-fix)

extern float   gLLHouseDistanceMultiplier = 1.0;
extern float   gLLEconomicDistanceMultiplier = 1.0;
extern float   gLLMilitaryDistanceMultiplier = 1.0;
extern float   gLLTownCenterDistanceMultiplier = 1.0;
extern int     gLLTowerLevel = 1;
extern int     gLLFortLevel = 1;
extern int     gLLForwardBaseTowerCount = 2;
extern bool    gLLPreferForwardFortifiedBase = false;

// Per-doctrine military building placement preference. Engine accepts 0..3
// (Front/Back/Left/Right) via cBuildPlanLocationPreference. -1 = legacy
// random (the engine default). Set per build-style in leaderCommon.xs so
// barracks/stables/foundry land where the doctrine wants them, not in a
// random cardinal each time.
extern int     gLLMilitaryPlacementPreference = -1;

// When > 0, lowers the gate that delays AI forward-base creation. Engine
// default in aiBuildings.xs is "Expert difficulty AND time >= 20 min". For
// expansionist doctrines (ForwardOperationalLine, SiegeTrainConcentration,
// CossackVoisko, RepublicanLevee) we drop the time gate and remove the
// difficulty gate so the AI actually expands within a normal-length match.
extern int     gLLForwardBaseEarliestMs = 1200000;  // engine default
extern bool    gLLForwardBaseAnyDifficulty = false; // require Expert by default

// ---------------------------------------------------------------------------
// Legendary Leaders — terrain + expansion-heading enforcement.
//
// These are the "EXACTLY how the AI plays" knobs. Each standard/revolution
// nation receives one primary and one secondary terrain preference plus a
// compass heading for expansion. The placement pipeline in aiBuildings.xs
// reads these to bias the influence-gradient center so that houses, eco,
// and secondary TCs actually land on the historically correct feature.
//
// Terrain primitives (8 + Any):
//   Coast       — shoreline clusters (Royal Navy, Portuguese feitoria, Dutch,
//                 Barbary, Japanese, British, Baja Californian mission ports).
//   River       — near fresh water / inland river plains (Swedish Göta Älv,
//                 Russian Volga, Hausa Niger, Indian Ganges, Ethiopian
//                 Abbay, Ottoman Danube, French Seine, Italian Po).
//   ForestEdge  — woodland skirt (Iroquois confederacy, Canadian St Lawrence,
//                 Finnish taiga, Maya Petén, Haitian colline).
//   Plain       — open grassland / steppe (Lakota, Hungarian puszta,
//                 Argentine pampas, Rio Grande, Texian prairie,
//                 Californian valley).
//   Highland    — mountain / citadel (Inca Sacsayhuamán, Peruvian altiplano,
//                 Chilean Andes, Maltese St Elmo, Egyptian citadel,
//                 Ethiopian Entoto, Indian Western Ghats, Swiss/Romanian).
//   Wetland     — marsh/delta (Aztec chinampas, Dutch polder, South
//                 African Drakensberg foothill wetlands).
//   DesertOasis — arid oasis (Spanish Reconquista flank, Mexican Bajío,
//                 Central American dry corridor).
//   Jungle      — tropical canopy (Yucatec, Brazilian Mata Atlântica,
//                 Indonesian Java, Columbian, Mayan Caste War).
extern int     cLLTerrainAny          = 0;
extern int     cLLTerrainCoast        = 1;
extern int     cLLTerrainRiver        = 2;
extern int     cLLTerrainForestEdge   = 3;
extern int     cLLTerrainPlain        = 4;
extern int     cLLTerrainHighland     = 5;
extern int     cLLTerrainWetland      = 6;
extern int     cLLTerrainDesertOasis  = 7;
extern int     cLLTerrainJungle       = 8;

// Expansion headings (7):
//   AlongCoast       — secondary TC/dock string hugs the shore
//                      (Naval Mercantile compounds, Portuguese, Dutch,
//                      British, Japanese, Barbary, South African).
//   Upriver          — march inland along rivers (Russian, Swedish,
//                      Hausa, French, Italian, Chinese).
//   FrontierPush     — outward along a single compass axis, enemy-ward
//                      (Napoleonic France, Texian, Argentine, Bolivarian,
//                      Mexican insurgent, Spanish Reconquista, Hungarian).
//   IslandHop        — leapfrog bases across water chokes (Maltese,
//                      Indonesian, Baja Californian, Barbary).
//   OutwardRings     — concentric expansion around a fortified core
//                      (Inca, Aztec, Chinese, Maltese, Finnish, Egyptian,
//                      Ottoman, Kangxi, Pachacuti).
//   FollowTradeRoute — along a mercantile axis (Dutch VOC,
//                      Portuguese Carrack, Iroquois Haudenosaunee trail,
//                      Hausa trans-Saharan, Tokugawa Nakasendō,
//                      Californian gold camps).
//   Defensive        — no expansion, consolidate inside perimeter
//                      (Valette 1565, Menelik Magdala, Mannerheim
//                      Line, Robespierre Paris, Gall post-1876).
extern int     cLLHeadingAny              = 0;
extern int     cLLHeadingAlongCoast       = 1;
extern int     cLLHeadingUpriver          = 2;
extern int     cLLHeadingFrontierPush     = 3;
extern int     cLLHeadingIslandHop        = 4;
extern int     cLLHeadingOutwardRings     = 5;
extern int     cLLHeadingFollowTradeRoute = 6;
extern int     cLLHeadingDefensive        = 7;

extern int     gLLPreferredTerrainPrimary   = 0;  // cLLTerrainAny
extern int     gLLPreferredTerrainSecondary = 0;  // cLLTerrainAny
extern int     gLLExpansionHeading          = 0;  // cLLHeadingAny
extern bool    gLLCenterAnchorCivic         = false;  // if true, markets/churches snap tight to TC
extern float   gLLTerrainBiasStrength       = 0.35; // 0.0=off, 1.0=full drag to feature
extern float   gLLHeadingBiasStrength       = 0.30; // 0.0=off, 1.0=full drag along heading

// Set true at the very end of postInit() so gameOverHandler can distinguish a
// real end-of-match fire from the engine's spurious early-fire during lobby
// load (where identity is still stale). Avoids the 60s wall-clock fudge that
// blocked --observe-seconds=10 smoke runs from ever flushing probes.
extern bool    gLLPostInitFired             = false;

int createInvalidBaseAttackRoute(int playerID = -1, int baseID = -1) { return(-1); }
extern int(int, int) cvCreateBaseAttackRoute = createInvalidBaseAttackRoute; // Creates an attack route used by attack plans, if this is not set, we let the plan automatically manage it.
                                                                             // Look inside of age3zHB11p06.xs to see how it's used (AI for Historical Battle Grito de Dolores).



// DEPRECATED VARIABLES THAT DO NOTHING ANYMORE:
extern bool    cvOkToSelectMissions = true;  // False prevents the AI from activating any missions.
extern bool    cvOkToChat = true;            // False prohibits all planning-oriented comms, like requests for defense, joint ops, tribute requests, etc.
extern bool    cvDoAutoSaves = true;         // Setting this false will over-ride the normal auto-save setting (for scenario use)

// Walls have been turned off currently for the AI since the algorithm to determine the placement isn't good enough.
extern bool    cvOkToBuildWalls = true;      // False prohibits any wall-building.