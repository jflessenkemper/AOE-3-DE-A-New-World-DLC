//==============================================================================
/* aiGlobals.xs

   This file contains all global constants and variables.

*/
//==============================================================================

//==============================================================================
// Utilities.
//==============================================================================

extern const float PI = 3.1415926;
extern const int cTileBlack = 1;
extern const int cTileFog = 2;
extern const int cTileVisible = 4;

//==============================================================================
// Buildings.
//==============================================================================

extern int gTCBuildPlanID = -1;
extern vector gTCSearchVector = cInvalidVector; // Used to define the center of the TC building placement search.
extern int gTCStartTime = 10000;                // Used to define when the TC build plan can go active.  In ms.
extern const int cForwardBaseStateNone = -1;    // None exists, none in progress
extern const int cForwardBaseStateBuilding = 0; // Fort wagon exists, but no fort yet.
extern const int cForwardBaseStateActive = 1;   // Base is active, defend and train plans there.
extern int gForwardBaseState = cForwardBaseStateNone;
extern int gForwardBaseID = -1;                      // Set when state goes to Active
extern vector gForwardBaseLocation = cInvalidVector; // Set when state goes to 'building' or earlier.
extern int gForwardBaseBuildPlan = -1;
extern int gForwardBaseUpTime = -600000;
extern bool gForwardBaseShouldDefend = false;
extern int gMainBase = -1;
extern bool gBuildWalls = true;         // Global indicating if we're walling up or not.
extern int gNumTowers = 0;               // How many towers do we want to build?
extern int gNumForts = 0;               // How many forts do we want to build?
extern bool gTowerCommandActive = false; // This is set by commHandler and used to determine which Tower amount to build.
extern bool gFortCommandActive = false; // This is set by commHandler and used to determine which Tower amount to build.
extern int gCommandNumTowers = 0;        // Set inside of commHandler and used when we build Towers based on a command.
extern int gCommandNumForts = 0;        // Set inside of commHandler and used when we build Forts based on a command.
extern vector gTorpPosition = cInvalidVector;
extern int gTorpPositionsToAvoid = -1;
extern int gMilitaryBuildings = -1;
extern int gArmyUnitBuildings = -1;
extern int gFullGranaries = -1;  // List of granaries surrounded by fields
extern int gFieldGranaryID = -1; // The current granary chosen to build a field nearby
extern int gQueuedBuildPlans = -1;

extern vector gIslandBaseLocation = cInvalidVector;
extern int gIslandBaseBuildPlan = -1;
extern int gIslandBaseState = 0;
extern int gIslandBaseID = -1;
extern int gIslandBaseTransportTime = -1;
extern int gIslandBaseUpTime = -1;
extern int gIslandBaseBuildersPlan = -1;
extern int gIslandBaseMaintainPlan = -1;
extern int gIslandBaseLandUnit = -1;
extern int gIslandBaseArtilleryUnit = -1;
extern int gIslandBaseBarracksPlan = -1;
extern int gIslandBasePatrolPlan = -1;

extern int gIslandBaseBuildingPlan1 = -1;
extern int gIslandBaseBuildingPlan2 = -1;
extern int gIslandBaseBuildingPlan3 = -1;
extern int gIslandBaseBuildingPlan4 = -1;

extern int gColonialBaseId = -1;
extern vector gColonialBasePosition = cInvalidVector;
extern int gColonialFoodGatherPlan = -1;
extern int gColonialWoodGatherPlan = -1;
extern int gColonialGoldGatherPlan = -1;

extern int gHouseUnit = cUnitTypeHouse;
extern int gTowerUnit = cUnitTypeOutpost;
extern int gFortUnit = cUnitTypeFortFrontier;
extern int gFarmUnit = cUnitTypeMill;
extern int gPlantationUnit = cUnitTypePlantation;
extern int gLivestockPenUnit = cUnitTypeLivestockPen;
extern int gMarketUnit = cUnitTypeMarket;
extern int gDockUnit = cUnitTypeDock;

//==============================================================================
/*  Runtime-resolved abstract proto-type IDs (moved here from
    aiLoaderStandard.xs 2026-05-31).

    These MUST be declared before the probe files that reference them
    (core\aiDoctrineProbes.xs, core\aiStateSnapshot.xs) are parsed. They
    used to live in aiLoaderStandard.xs *after* `include "aiMain.xs"`, so
    by the time aiCore.xs -> aiDoctrineProbes.xs was parsed they did not yet
    exist and the eager function-body parse failed with
    "gANWAbstractWarShip is not a valid operator" (XS Error 0172), aborting
    the whole AI compile. aiGlobals.xs is parsed before those probe files
    (gFortUnit/gDockUnit above are used in aiDoctrineProbes without error),
    so this is the correct home. The resolver anwResolveAbstractTypes()
    that assigns these via kbGetProtoUnitID() stays in aiLoaderStandard.xs
    and runs at preInit(). */
//==============================================================================
extern int gANWAbstractWarShip            = -1;
extern int gANWAbstractStables            = -1;
extern int gANWAbstractArtilleryFoundry   = -1;
extern int gANWAbstractWall               = -1;
extern int gANWAbstractTradingPost        = -1;
extern int gANWAbstractMonastery          = -1;
extern int gANWAbstractInfantry           = -1;
extern int gANWAbstractCavalry            = -1;
extern int gANWAbstractArtillery          = -1;
extern int gANWAbstractNativeWarrior      = -1;
extern int gANWMercenary                  = -1;
extern int gANWHero                       = -1;

// Test-harness auto-resign threshold (game-ms). 0 = disabled (released
// builds). The matrix/test tooling sed-rewrites this literal before a test
// sync and resets it to 0 afterwards; see tools/aoe3_automation/matrix_runner.py
// (--auto-resign-ms) and tools/aoe3_automation/test_mode_xs.py. MUST stay
// declared here (parsed early, before aiLoaderStandard.xs's postInit body
// references it) or the AI compile aborts with XS Error 0172. Re-homed here
// 2026-05-31 after a refactor dropped the original declaration.
extern const int cANWTestModeAutoResignMs = 0;

extern int gForwardBaseStablesPlan = -1;
extern int gForwardBaseBarracksPlan = -1;
extern int gForwardBaseTowersPlan = -1;

//==============================================================================
// Global variables for wall building
//==============================================================================
extern int gWallBuilderID = -1;
extern int gWallPlanIDs = -1;
extern int gCurrentWallPlanIndex = 0;
extern int gActiveWallPlan = -1;

//==============================================================================
// Wall section data storage
//==============================================================================
extern int gWallSectionStarts = -1;
extern int gWallSectionEnds = -1;
extern int gWallSectionGates = -1;
extern int gWallSectionCount = 0;
extern int gWallBaseID = -1;
extern int gWallPriority = 100;

//==============================================================================
// Techs.
//==============================================================================

extern int gConsulateFlagTechID = -1;     // the consulate flag tech we are going to research.
extern bool gConsulateFlagChosen = false; // need to make sure they only build one
extern int gAgeUpResearchPlan = -1; // Plan used to send politician from HC, used to detect if an age upgrade is in progress.
extern int gAgeUpTime = 0;          // Time we entered this age
extern int gAgeUpPlanTime = 0;      // Time to plan for next age up.
extern int gCurrentDecreeTech = -1;

// Trade Route Array Constants.
extern const int cTradeRouteNorthAmerica = 0;
extern const int cTradeRouteSouthAmerica = 1;
extern const int cTradeRouteAsia = 2;
extern const int cTradeRouteAfrica = 3;
extern const int cTradeRouteNaval = 4;
extern const int cTradeRouteAll =
    5; // This is used for maps where upgrading one route also upgrades others, textures default to NA ones.
extern const int cTradeRouteCapturableAsia = 6;
extern const int cTradeRouteCapturableAfrica = 7; // If ever more Capturable routes are added this needs to be updated.
extern const int cTradeRouteFirstUpgrade = 0;
extern const int cTradeRouteSecondUpgrade = 1;
extern int gNumberTradeRoutes = -1; // Saves how many Trade Routes there are on the map via kbGetNumberTradeRoutes(), this never
                                    // changes so can just be a global sort of constant.

// Trade Route Arrays
// This saves how many Trade Routes there are on the map (index in the array is also the index of the TR at the same time)
// and what type these TRs are (land(continent)/naval).
extern int gTradeRouteIndexAndType = -1;
// This will be a bool array and false means the specific TR isn't fully upgraded and true means it is.
extern int gTradeRouteIndexMaxUpgraded = -1;
// Here we store what crates are actually delivered by each trade route so we can correctly
// set the tactic in tradeRouteTacticMonitor.
extern int gTradeRouteCrates = -1;
// Index 0 will be the first upgrade on the Route and 1 the second upgrade on the Route.
extern int gTradeRouteUpgrades = -1;

// In these variables we save the IDs of the minor native civs that are present on the map.
// We use these in the setupNativeUpgrades logic.
// We have 3 of these variables because the maximum amount of minor native civs you can get on a regular map is 3.
// This means that if you for example have a map with 4 different natives the 4th native will be ignored.
extern int gNativeTribeCiv1 = -1;
extern int gNativeTribeCiv2 = -1;
extern int gNativeTribeCiv3 = -1;
// We use these function pointers to research minor native upgrades via setupNativeUpgrades.
bool nativeResearchTechsEmpty(int tradingPostID = -1) { return (false); }
extern bool(int) gNativeTribeResearchTechs1 = nativeResearchTechsEmpty;
extern bool(int) gNativeTribeResearchTechs2 = nativeResearchTechsEmpty;
extern bool(int) gNativeTribeResearchTechs3 = nativeResearchTechsEmpty;

extern int gAfricanAlliancesAgedUpWith = 1; // Array of Alliances we've aged up with so far this game.
// Array of statuses of upgrades gained via Alliances. True is researched false is not researched.
extern int gAfricanAlliancesUpgrades =1;

// Hausa Alliance Constants.
extern const int cAllianceBerbersIndex = 0;
extern const int cAllianceHausaIndex = 1;
extern const int cAllianceSonghaiIndex = 2;
extern const int cAllianceAkanIndex = 3;
extern const int cAllianceBritishIndex = 4;

// Ethiopia Alliance Constants.
extern const int cAllianceSomalisIndex = 0;
extern const int cAlliancePortugueseIndex = 1;
extern const int cAllianceSudaneseIndex = 2;
extern const int cAllianceJesuitIndex = 3;
extern const int cAllianceOromoIndex = 4;

extern int gRevolutionList = -1; // List of Revolutions.
// ANW design: the nation you start with is the nation you play the whole game.
// Mid-game revolting is DISABLED — every revoltable nation is instead its own
// lobby-selectable civ. Set true only to restore vanilla mid-game revolutions.
extern bool gANWAllowRevolt = false;
extern int gAfricanAlliances = -1;     // Array used to select from the different African alliances
extern int gMexicanFederalStates = -1; // Array used to select from the different Mexican Federal States.
extern int gAmericanFederalStates = -1; // Array used to select from the different United States Federal States.

// We save at what time the first person in the game advanced to Fortress/Industrial/Imperial in this array.
// In ageUpgradeMonitor we determine how badly we need to age up taking this into account.
extern int gFirstAgeTime = -1;

//==============================================================================
// Exploration.
//==============================================================================

extern int gWaterExplorePlan = -1;    // Plan ID for ocean exploration plan
extern int gExplorerControlPlan = -1; // Defend plan set up to control the explorer's location
extern int gLandExplorePlan = -1;     // Primary land exploration
extern int gIslandExploreTransportScoutID = -1;
extern bool gIslandMap = false; // Does this map have lands with waters in between?
extern bool gActiveIslandInvasion = false;
extern bool gActiveVillagersTransport = false;
extern vector gProbableEnemyIsland = cInvalidVector;
extern int gProbableEnemyIslandAreaId = -1;
extern int gProbableEnemyIslandGroupId = -1;
extern int gNumberTransported = 0;
extern vector gIslandCenterPoint = cInvalidVector;
extern float gProbableEnemyIslandX = 0.0;
extern float gProbableEnemyIslandZ = 0.0;
extern float gDistanceToCoast = 0.0;
extern string gInvasionPlan = "";
extern int gMilitaryTransportMode = 0;
extern bool gIslandFound = false;
extern int gInvasionResetWaitTime = -1;
extern int gInvasionInitialTime = -1;
extern vector gVillagersIsland = cInvalidVector;
extern int gVillagersIslandAreaId = -1;
extern int gVillagersIslandGroupId = -1;
extern float gVillagersIslandX = 0.0;
extern float gVillagersIslandZ = 0.0;
extern vector gVillagersIslandCenterPoint = cInvalidVector;
extern int gVillagersIslandBaseId = -1;
extern int gVillagersTransportMode = 0;
extern int gLandPatrolPlan = -1;
extern int gWaterPatrolPlan = -1;
extern int gWaterDockAttackPlan = -1;

// Global plans necessary for tracking units involved in the invasion...
extern int gIslandAssaultTransportPlanID = -1;
extern int gIslandAssaultTransportPlan2ID = -1;
extern int gIslandAssaultPlanID = -1;
extern bool gAssaultExploreDone = false;
extern bool gAssaultingIsland = false;
extern int gIslandSearchPlanID = -1;
extern int gIslandReturnTransportPlanID = -1;
extern int gForgottenMilitaryAssaultPlanID = -1;

// Global plans necessary for tracking units involved in the colonization of islands...
extern int gVillagersTransportPlanID = -1;
extern int gIslandVillagersBuildPlanID = -1;
extern bool gVillagersExploreDone = false;
extern bool gVillagersIslandFound = false;
extern int gIslandVillagersSearchPlanID = -1;
extern int gIslandVillagersReturnTransportPlanID = -1;

// Trade post build plans.
extern int gTradePostBuildingPlan = -1;

//==============================================================================
// Economy.
//==============================================================================

extern int cMaxSettlersPerFarm = 10;
extern int cMaxSettlersPerPlantation = 10;
extern const int cMinResourcePerGatherer = 100; // When our supply gets below this level, start farming/plantations.
extern bool gTimeToFarm = false;                // Set to true when we start to run out of cheap early food.
extern bool gTimeForPlantations = false;        // Set to true when we start to run out of mine-able gold.
extern bool gPrioritizeFarms = false;           // Set to true when we should prioritize farms.
extern bool gPrioritizeEstates = false;         // Set to true when we should prioritze estates.
extern bool gCountBerries = false;              // Set to true when we should count berries as calculating natural resources we have left.

extern int gEconUpgradePlan = -1;
extern bool gGoodFishingMap = false;      // Set in init(), can be overridden in postInit() if desired.  True indicates that
                                          // fishing is a good idea on this map.
extern int gFishingPlan = -1;             // Plan ID for main fishing plan.
extern int gFishingBoatMaintainPlan = -1; // Fishing boats to maintain
extern bool gTimeToFish = false;          // Set to true when we want to start fishing.
extern int gHerdPlanID = -1;
extern int gResourceNeeds = -1;
extern int gExtraResourceNeeds = -1;
extern bool gLowOnResources = false;
extern bool gExcessResources = true;

extern int gGatherPlanPriorityHunt = 80;
extern int gGatherPlanPriorityBerry = 81;
extern int gGatherPlanPriorityMill = 82;
extern int gGatherPlanPriorityWood = 81;
extern int gGatherPlanPriorityMine = 78;
extern int gGatherPlanPriorityEstate = 83;
extern int gGatherPlanPriorityFish = 20;
extern int gGatherPlanPriorityWhale = 19;

extern int gGatherPlanNumHuntPlans = 0;
extern int gGatherPlanNumBerryPlans = 0;
extern int gGatherPlanNumMillPlans = 0;
extern int gGatherPlanNumWoodPlans = 0;
extern int gGatherPlanNumMinePlans = 0;
extern int gGatherPlanNumEstatePlans = 0;
extern int gGatherPlanNumFishPlans = 0;
extern int gGatherPlanNumWhalePlans = 0;

extern int gAdjustBreakdownAttempts = -1;

extern int gDepletedResources = 0; // Depleted resources mask.
extern const int cMarketBuyFoodWithGold = 0;
extern const int cMarketBuyWoodWithGold = 1;
extern const int cMarketSellFoodForGold = 2;
extern const int cMarketSellWoodForGold = 3;
extern int gMarketBuySellTypes = 0; // Market buy sell type mask.
extern int gMarketBuySellPercentages = -1; // Array of resource percentages to exchange to another one.
extern int gRawResourcePercentages = -1; // Raw resource percentages before market buy sell adjustments.
extern int gFarmFoodTactic = -1;
extern int gFarmGoldTactic = -1;

extern int gFishingUnit = cUnitTypeFishingBoat;
extern const int cResourceCanExceedMaxDistanceFood = 1;
extern const int cResourceCanExceedMaxDistanceWood = 2;
extern const int cResourceCanExceedMaxDistanceGold = 4;
extern int gResourceCanExceedMaxDistance = 0;
extern bool gResourceSearchAllAreaGroups = false;

extern int gMaxHerdablesMaintain = -1;
extern bool gGatherPlansUpdated = false;

//==============================================================================
// Military.
//==============================================================================
extern int gLastTribSentTime = 0;

extern int gLandDefendPlan0 = -1; // Primary land defend plan
extern int gLandReservePlan = -1; // Reserve defend plan, gathers units for use in the next military mission
extern int gHealerPlan = -1;      // Defend plan that controls our healers in our base.

extern bool gDefenseReflex = false; // Set true when a defense reflex is overriding normal ops.
extern bool gDefenseReflexPaused =
    false; // Set true when we're in a defense reflex, but overwhelmed, so we're hiding to rebuild an army.
extern int gDefenseReflexBaseID = -1;                  // Set to the base ID that we're defending in this emergency
extern vector gDefenseReflexLocation = cInvalidVector; // Location we're defending in this emergency
extern int gDefenseReflexTimeout = 0;

extern int gLandUnitPicker = -1; // Picks the best land military units to train.

extern int gCaravelMaintain = -1; // Maintain plans for naval units.
extern int gGalleonMaintain = -1;
extern int gFrigateMaintain = -1;
extern int gMonitorMaintain = -1;
extern int gBattleshipMaintain = -1;

extern int gMaxInfantryMaintain = -1;
extern int gMaxCavalryMaintain = -1;
extern int gArtilleryMaintain = -1;
extern int gMaxVillagersMaintain = -1;
extern int gNativeScoutLimit = -1;

extern int gTransportUnit = cUnitTypeAbstractWarShip;
extern bool gWaterMap = false;               // True when we are on a water map
// ** BEGIN ENHANCED NAVY **
extern int  gWaterExploreMaintain = -1;
extern int gNavyEnhancedAttackPlan = -1; // Saves the ID of the naval attack combat plan to manage land/navy interactions for the Enhanced AI.
extern int gGalleonTrainingPlan = -1;
extern int gGalleonArtilleryTrainingPlan = -1;
extern int gGalleonLandUnit = -1;
extern int gGalleonArtilleryUnit = -1;
extern vector gNavalInvasionCoastalPoint = cInvalidVector;
// Dock wagon globals
extern int gDockRandomTries = 0;
extern vector gDockBaseCoastalEdge = cInvalidVector;
// Warship and dock globals
extern int gWarshipExplorePlan = -1;
extern int gNavalNuggetShipIds = -1;
extern int gNavalNuggetQuery = -1;
extern int gNumberNavalNuggets = -1;
extern int gClosestNuggetId = -1;
extern int gDockWagonPlan = -1;
extern int gDockWagonCounter = -1;
extern vector gClosestNuggetPosition = cInvalidVector;
// ** END ENHANCED NAVY **
extern float gNetNavyValue = -1; // Saves the power balance on the water.
extern int gNavyRepairPlan = -1; // Saves the ID of the naval defend combat (hijacked for repair) plan to manage land/navy interactions. 
extern int gNavyDefendPlan = -1; // Persistent naval defend plan.
extern int gNavyAttackPlan = -1; // Saves the ID of the naval attack combat plan to manage land/navy interactions.
extern vector gNavyVec = cInvalidVector; // The center of the navy's operations.
extern bool gHaveWaterSpawnFlag = false;
extern int gWaterSpawnFlagID = -1;
extern bool gNavyMap = false; // Setting this false prevents navies

extern int gNumArmyUnitTypes = 3; // How many land unit types do we want to train?

extern int gGoodArmyPop =
    -1; // This number is updated by the pop manager, only used to calculate stuff in the defence reflex logic.

extern int gUnitPickSource = cOpportunitySourceAutoGenerated; // Indicates who decides which units are being
                                                              // trained...self, trigger, or ally player.

extern int gLastClaimTradeMissionTime = -1;
extern int gLastNavalAttackTime = -1;
extern int gLastAttackMissionTime = -1;
extern int gLastDefendMissionTime = -1;
extern int gAttackMissionInterval =
    180000; // 2-3 minutes depending on difficulty level.  Suppresses attack scores (linearly) for 2-3 minutes after one
            // launches.  Attacks will usually happen before this period is over.
extern int gDefendMissionInterval = 300000; // 5 minutes.   Makes the AI less likely to do another defend right after doing one.
extern int gClaimTradeMissionInterval = 300000;  // 5 minutes.
extern int gClaimNativeMissionInterval = 600000; // 10 minutes.
extern int gLastClaimNativeMissionTime = -1;

extern int gNumEnemies = -1;             // Used to pick a target to attack.
extern int gArrayEnemyPlayerIDs = -1;    // Used to pick a target to attack.
extern int gStartingPosDistances = -1;   // Used to sort enemies from closest to furthest away for target picking in FFA.

extern bool gIAmCaptain = false;
extern int gCaptainPlayerNumber = -1;

extern bool gIsMonopolyRunning = false; // Set true while a monopoly countdown is in effect.
extern int gMonopolyTeam = -1;          // TeamID of team that will win if the monopoly timer completes.

extern bool gIsKOTHRunning = false; // Set true while a KOTH countdown is in effect.
extern int gKOTHTeam = -1;          // TeamID of team that will win if the KOTH timer completes.
extern int gKOTHCombatPlan = -1;
extern int gKOTHBasePlan = -1;
extern int gKOTHGuardPlan = -1;

extern int gArmyUnitMaintainPlans = -1;

extern int gCaravelUnit = cUnitTypeCaravel;
extern int gGalleonUnit = cUnitTypeGalleon;
extern int gFrigateUnit = cUnitTypeFrigate;
extern int gMonitorUnit = cUnitTypeMonitor;
// Enhanced AI, added the Battleship - 8-20-2023
extern int gBattleShipUnit = cUnitTypedeMercBattleship;

extern int gFlorenceNightingaleHouseId = -1;
extern int gFortRebuildPlan = -1;
extern int gMaxTowersPlan = -1;
// Healing Units
extern int gHealingUnitType = -1;
// For Lakota TeePees
extern int gTeePeeRebuildPlan = -1;
extern int gWallBuilderIds = -1; // Array for storing Wall Builder Ids...
extern int gWallPlanParentId = -1;
extern bool gWallBuildingSuccess = false;

// Maintain plans for Native ally boats/ships
extern int gPrivateerMaintain = -1;
extern int gCanoeMaintain = -1;
extern int gCatamaranMaintain = -1;

// Enhanced AI - Are we going to rush?
extern bool gEarlyRushAttempt = false;

//==============================================================================
// Home City cards.
//==============================================================================

extern int gDefaultDeck = -1; // Home city deck used by each AI

//==============================================================================
// Chats.
//==============================================================================

extern int gFeedGoldTo = -1; // If set, this indicates which player we need to be supplying with regular gold shipments.
extern int gFeedWoodTo = -1; // See commHandler and monitorFeeding rule.
extern int gFeedFoodTo = -1;
extern int gMapNames = -1; // An array of random map names, so we can store ID numbers in player histories
extern int gWaterPatrol = -1; // An array of boat names for the Enhanced AI. 8-21-2023

extern int gLateInAgePlayerID = -1;
extern int gLateInAgeAge = -1;

//==============================================================================
// Setup.
//==============================================================================
// Start mode constants.
extern int gStartMode = -1;                   // See start mode constants, above.  This variable is set
                                              // in main() and is used to decide which cascades of rules
                                              // should be used to start the AI.
extern const int cStartModeScenarioNoTC = 0;  // Scenario, wait for aiStart unit, then play without a TC
extern const int cStartModeScenarioTC = 1;    // Scenario, wait for aiStart unit, then play with starting TC
extern const int cStartModeScenarioWagon = 2; // Scenario, wait for aiStart unit, then start TC build plan.
extern const int cStartModeLandTC = 3;        // RM or GC game, starting with a TC...just go.
extern const int cStartModeLandWagon = 4;     // RM or GC game, starting with a wagon.  Explore, start TC build plan.
extern const int cStartModeLandResources = 5; // RM or GC game, starting with enough resources to build a TC.
extern int gUnknownRMStartupDelayAttempts = 0;

extern vector gStartingLocationOverride = cInvalidVector;
extern bool gStartOnDifferentIslands = false; // Does this map have players starting on different islands?

//==============================================================================
// All other stuffs.
//==============================================================================

extern int gMaxPop = 200; // Absolute hard limit pop cap for game...will be set lower on some difficulty levels
extern int gNativeDancePlan = -1;
extern bool gSPC = false; // Set true in main if this is an spc or campaign game

extern const int cRevolutionMilitary = 1;
extern const int cRevolutionEconomic = 2;
extern const int cRevolutionFinland = 4;
extern int gRevolutionType = 0;

// Save which age variant of Asian Wonder we aged up with to be used instead of kbUnitCount checks.
// Chinese.
extern int gWhitePagodaPUID = -1;
extern int gSummerPalacePUID = -1;
extern int gConfucianAcademyPUID = -1;
extern int gTempleOfHeavenPUID = -1;
extern int gPorcelainTowerPUID = -1;

// Indians.
extern int gAgraFortPUID = -1;
extern int gCharminarGatePUID = -1;
extern int gKarniMataPUID = -1;
extern int gTajMahalPUID = -1;
extern int gTowerOfVictoryPUID = -1;

// Japanese.
extern int gGreatBuddhaPUID = -1;
extern int gGoldenPavilionPUID = -1;
extern int gTheShogunatePUID = -1;
extern int gToriiGatesPUID = -1;
extern int gToshoguShrinePUID = -1;

extern int gEconUnit = cUnitTypeSettler;
extern int gSettlerMaintainPlan = -1; // Main plan to control settler population
extern int gTargetSettlerCounts = -1; // How many settlers do we want in a given age?
                                      // We call aiSetEconomyPop with a number calculated with this array since that takes all
                                      // eco units into account and this array only our gEconUnit.
extern int gTargetSettlerCountsDefault = -1; // This array stores the values the non special Settler civs have.
                                             // It is then used to calculate a proper military population.

extern int gDifficultyExpert = cDifficultyExpert; // Equivalent of expert difficulty, hard for SPC content.

// XP Point Values
// TODO: Investigate if there is a cleaner way to do this in XS scripting. Such as a keyed dictionary, object array, etc...
extern int gXpValuePlayer1 = -1;
extern int gXpValuePlayer2 = -1;
extern int gXpValuePlayer3 = -1;
extern int gXpValuePlayer4 = -1;
extern int gXpValuePlayer5 = -1;
extern int gXpValuePlayer6 = -1;
extern int gXpValuePlayer7 = -1;
extern int gXpValuePlayer8 = -1;

//==============================================================================
// Debug variables.
//==============================================================================
extern const bool cANWRuntimeTelemetry = true;
extern const bool cANWVerboseDiagnostics = false;
// Master switch for replay-capturable chat probes. When true, anwProbe() emits
// an unthrottled aiChat broadcast tagged "[LL-PROBE]" so community replay
// parsers (e.g. @canyougiant/aoe3de-replay-parser) record every AI's boot,
// wall dispatch, age-up, chatset-fire, rout, explorer-escort, and economy
// snapshot events in the .age3Yrec chat stream.
extern const bool cANWReplayProbes = true;
// When true, anwProbe() ALSO mirrors each probe line to the human host (P1)
// on-screen chat box. That is handy for live spectating but it FLOODS the
// chat box and buries AI personality quotes/taunts. Default false: probes
// still emit via aiEcho (dev builds) and a self-addressed aiChat (recorded in
// the replay/log chat stream — parsers read every aiChat record regardless of
// recipient), so probe/log DATA capture is unaffected while your on-screen
// chat stays clean for quote/taunt testing. Flip true only when you want the
// probe firehose visible live on the host screen.
extern const bool cANWProbeToHostChat = false;
extern const bool cANWProbeToSelfChat = false;
// Phase-3 firehose: when true, every anwLogRuleTick() also emits a per-rule
// `rule.fired` probe. Enables fine-grained per-rule timeline reconstruction
// from replays at the cost of high chat-stream volume — keep off for
// release builds, flip on only when chasing a specific rule-firing bug.
extern const bool cANWDebugRuleFires = false;
// Per-AI leader identity string set by each initLeader*() in preInit(). Used
// by the LL-BOOT probe so the replay tells us which leader module each AI
// actually loaded — catches "Barbary blank leader" / wrong-personality
// regressions directly.
extern string gANWLeaderKey = "unassigned";
// Per-AI chatset name (matches chatsetsmods.xml <Chatset name="...">). Set by
// each initLeader*(); used in the LL-BOOT probe so we can verify the chat
// portrait / quote wiring routed to the right chatset at runtime.
extern string gANWChatsetKey = "unassigned";
extern const bool cDebugUtilities = false;
extern const bool cDebugBuildings = false;
extern const bool cDebugTechs = false;
extern const bool cDebugExploration = false;
extern const bool cDebugEconomy = false;
extern const bool cDebugMilitary = false;
extern const bool cDebugHCCards = false;
extern const bool cDebugChats = false;
extern const bool cDebugSetup = false;
extern const bool cDebugCore = false;
extern const bool cANWDebug = false;
extern const bool cANWDebugVisible = false;
extern const int cANWDebugVisibleCooldown = 12000;
extern int gANWDebugVisiblePlayer = -1;
extern int gANWDebugVisibleTime = -60000;