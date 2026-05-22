//==============================================================================
/* leaderCommon.xs

   Shared helper functions for Legendary Leaders personalities.
*/
//==============================================================================

void llResetLeaderBiases(void)
{
   btRushBoom = 0.0;
   btOffenseDefense = 0.0;
   btBiasNative = 0.0;
   btBiasTrade = 0.0;
   btBiasCav = 0.0;
   btBiasArt = 0.0;
   btBiasInf = 0.0;
   llLogEvent("LEADER", "reset leader biases to neutral defaults.");
   llProbe("event.personality.applied", "kind=reset rush=0.0 offDef=0.0");
}

void llSetBalancedPersonality(void)
{
   llResetLeaderBiases();
   btRushBoom = 0.0;
   btOffenseDefense = 0.0;
   llLogLeaderState("balanced personality applied");
   llProbe("event.personality.applied", "kind=balanced rush=" + btRushBoom + " offDef=" + btOffenseDefense);
}

void llSetAggressivePersonality(void)
{
   llResetLeaderBiases();
   btRushBoom = 0.8;
   btOffenseDefense = 0.8;
   llLogLeaderState("aggressive personality applied");
   llProbe("event.personality.applied", "kind=aggressive rush=" + btRushBoom + " offDef=" + btOffenseDefense);
}

void llSetDefensivePersonality(void)
{
   llResetLeaderBiases();
   btRushBoom = -0.4;
   btOffenseDefense = -0.6;
   llLogLeaderState("defensive personality applied");
   llProbe("event.personality.applied", "kind=defensive rush=" + btRushBoom + " offDef=" + btOffenseDefense);
}

void llSetMilitaryFocus(float infantryBias = 0.0, float cavalryBias = 0.0, float artilleryBias = 0.0)
{
   btBiasInf = infantryBias;
   btBiasCav = cavalryBias;
   btBiasArt = artilleryBias;
   llLogLeaderState("military focus updated");
   llProbe("event.personality.applied", "kind=military inf=" + infantryBias + " cav=" + cavalryBias + " art=" + artilleryBias);
}

void llEnableForwardBaseStyle(void)
{
   btOffenseDefense = 1.0;
   cvDefenseReflexRadiusActive = 75.0;
   cvDefenseReflexSearchRadius = 75.0;
   llLogLeaderState("forward-base style enabled");
   llProbe("event.style.feature", "kind=forwardBase reflexRadius=75.0");
}

void llEnableDeepDefenseStyle(void)
{
   btOffenseDefense = -0.5;
   cvMaxTowers = 7;
   cvDefenseReflexRadiusPassive = 40.0;
   llLogLeaderState("deep-defense style enabled");
   llProbe("event.style.feature", "kind=deepDefense maxTowers=" + cvMaxTowers + " passiveRadius=40.0");
}

void llResetBuildStyleProfile(void)
{
   gLLBuildStyle = 0;
   gLLWallLevel = 1;
   gLLEarlyWallingEnabled = true;
   gLLLateWallingEnabled = true;
   gLLHouseDistanceMultiplier = 1.0;
   gLLEconomicDistanceMultiplier = 1.0;
   gLLMilitaryDistanceMultiplier = 1.0;
   gLLTownCenterDistanceMultiplier = 1.0;
   gLLTowerLevel = 1;
   gLLFortLevel = 1;
   gLLForwardBaseTowerCount = 2;
   gLLPreferForwardFortifiedBase = false;
   gLLPreferredTerrainPrimary = cLLTerrainAny;
   gLLPreferredTerrainSecondary = cLLTerrainAny;
   gLLExpansionHeading = cLLHeadingAny;
   gLLCenterAnchorCivic = false;
   gLLTerrainBiasStrength = 0.35;
   gLLHeadingBiasStrength = 0.30;
   cvOkToBuildWalls = true;
}

// Terrain / expansion enforcement helpers.
//
// llSetPreferredTerrain — primary is the dominant feature (coast for naval
// civs, river for inland riparian, highland for citadel civs, etc.). The
// placement pipeline in aiBuildings.xs drags the influence center toward
// the nearest instance of that feature when selecting a build position,
// so houses / eco / secondary TCs actually land on the historical terrain.
// Secondary is a fallback used when the primary isn't reachable.
void llSetPreferredTerrain(int primary = 0, int secondary = 0, float strength = 0.35)
{
   gLLPreferredTerrainPrimary = primary;
   gLLPreferredTerrainSecondary = secondary;
   gLLTerrainBiasStrength = strength;
   llProbe("event.terrain.preference",
      "primary=" + primary + " secondary=" + secondary + " strength=" + strength);
}

// llSetExpansionHeading — compass/vector bias for secondary-TC and forward-
// military plans. "AlongCoast" follows the coastline vector, "Upriver"
// pushes inland away from coast, "FrontierPush" heads enemy-ward,
// "IslandHop" targets the far-shore spawn vector, "OutwardRings" keeps
// concentric around the main TC, "FollowTradeRoute" hugs trade-route
// sockets, "Defensive" explicitly refuses secondary expansion.
void llSetExpansionHeading(int heading = 0, float strength = 0.30)
{
   gLLExpansionHeading = heading;
   gLLHeadingBiasStrength = strength;
   llProbe("event.heading.preference", "heading=" + heading + " strength=" + strength);
}

// llEnableCenterAnchoredCivic — some civs (Aztec, Inca, Ottoman, Kangxi,
// Maltese, Tokugawa, Isabella) historically anchor their market, temple,
// and civic buildings tight to the TC plaza rather than scattering them
// to build-plan radius. When set, llApplyLegendaryBaseInfluence reduces
// the center-distance clamp for non-military, non-house plans.
void llEnableCenterAnchoredCivic(bool enabled = true)
{
   gLLCenterAnchorCivic = enabled;
   llProbe("event.style.feature", "kind=civicAnchor enabled=" + enabled);
}

void llConfigureBuildStyleProfile(int style = 0, int wallLevel = 1, bool earlyWalls = false,
   float houseDistanceMultiplier = 1.0, float economicDistanceMultiplier = 1.0,
   float militaryDistanceMultiplier = 1.0, float townCenterDistanceMultiplier = 1.0,
   int towerLevel = 1, int fortLevel = 1, int forwardBaseTowerCount = 2,
   bool preferForwardFortifiedBase = false)
{
   gLLBuildStyle = style;
   gLLWallLevel = wallLevel;
   // Honor caller's earlyWalls preference (was hardcoded to true). Mobile/
   // guerrilla styles that want to skirmish instead of wall early can pass
   // earlyWalls=false via their style helper (SteppeCavalryWedge,
   // MobileFrontierScatter, JungleGuerrillaNetwork) and get a pure mobile
   // opening. Defensive leaders pass earlyWalls=true for ring-walls at Age 1.
   gLLEarlyWallingEnabled = earlyWalls && (wallLevel > 0);
   gLLLateWallingEnabled = (wallLevel > 0);
   gLLHouseDistanceMultiplier = houseDistanceMultiplier;
   gLLEconomicDistanceMultiplier = economicDistanceMultiplier;
   gLLMilitaryDistanceMultiplier = militaryDistanceMultiplier;
   gLLTownCenterDistanceMultiplier = townCenterDistanceMultiplier;
   gLLTowerLevel = towerLevel;
   gLLFortLevel = fortLevel;
   gLLForwardBaseTowerCount = forwardBaseTowerCount;
   gLLPreferForwardFortifiedBase = preferForwardFortifiedBase;
   cvOkToBuildWalls = true;
   // Reset placement preference; specific style helpers below set it. -1 keeps
   // the engine's legacy random-cardinal behaviour for any style that does
   // not assert a doctrine.
   gLLMilitaryPlacementPreference = -1;
   gLLForwardBaseEarliestMs = 1200000;
   gLLForwardBaseAnyDifficulty = false;
   llProbe("event.style.applied",
      "style=" + style + " wallLevel=" + wallLevel +
      " earlyWalls=" + gLLEarlyWallingEnabled +
      " hMul=" + houseDistanceMultiplier +
      " eMul=" + economicDistanceMultiplier +
      " mMul=" + militaryDistanceMultiplier +
      " tcMul=" + townCenterDistanceMultiplier +
      " towerL=" + towerLevel + " fortL=" + fortLevel +
      " fwdTowers=" + forwardBaseTowerCount +
      " preferFwd=" + preferForwardFortifiedBase);
}

// Helper: every doctrine that "expands forward" calls this so we don't
// duplicate the gate-lowering line in every style.
void llEnableEarlyForwardBase(int earliestMs = 360000)
{
   gLLForwardBaseEarliestMs = earliestMs;       // default: 6 min instead of 20
   gLLForwardBaseAnyDifficulty = true;          // remove Expert-only gate
   gLLPreferForwardFortifiedBase = true;
   llProbe("event.style.feature", "kind=earlyFwdBase earliestMs=" + earliestMs);
}

void llUseCompactFortifiedCoreStyle(int wallLevel = 3, bool earlyWalls = true)
{
   // Bourbon France — Vauban-school star-fort doctrine. Full fortress ring.
   llConfigureBuildStyleProfile(cLLBuildStyleCompactFortifiedCore, wallLevel, earlyWalls, 0.75, 0.85, 0.85, 0.85, 3, 2, 2, false);
   gLLWallStrategy = cLLWallStrategyFortressRing;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;  // tight core
}

void llUseDistributedEconomicNetworkStyle(int wallLevel = 1)
{
   // Morazán / Central American federation — frontier palisade on scattered nodes.
   llConfigureBuildStyleProfile(cLLBuildStyleDistributedEconomicNetwork, wallLevel, false, 1.15, 1.35, 1.0, 1.35, 1, 1, 1, false);
   gLLWallStrategy = cLLWallStrategyFrontierPalisades;
   gLLMilitaryPlacementPreference = -1;  // genuine spread
   llEnableEarlyForwardBase(420000);     // 7 min — distributed nodes need time
}

void llUseForwardOperationalLineStyle(int wallLevel = 1)
{
   // Napoleon — no early walls, move fast. Field fortifications only in Age 3+.
   llConfigureBuildStyleProfile(cLLBuildStyleForwardOperationalLine, wallLevel, false, 1.0, 1.05, 0.95, 1.1, 1, 2, 3, true);
   gLLWallStrategy = cLLWallStrategyMobileNoWalls;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // forward line
   llEnableEarlyForwardBase(300000);     // 5 min — Napoleonic operational tempo
}

void llUseMobileFrontierScatterStyle(int wallLevel = 0)
{
   // Crazy Horse / Plains mobile — never wall, scout + intercept.
   llConfigureBuildStyleProfile(cLLBuildStyleMobileFrontierScatter, wallLevel, false, 1.35, 1.45, 1.1, 1.5, 1, 0, 1, false);
   gLLWallStrategy = cLLWallStrategyMobileNoWalls;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;
   llEnableEarlyForwardBase(360000);
}

void llUseShrineTradeNodeSpreadStyle(int wallLevel = 1)
{
   // Tokugawa — sakoku-era redoubts at approaches, no perimeter wall.
   llConfigureBuildStyleProfile(cLLBuildStyleShrineTradeNodeSpread, wallLevel, false, 1.0, 1.5, 0.95, 1.2, 1, 1, 1, false);
   gLLWallStrategy = cLLWallStrategyMobileNoWalls;
   gLLMilitaryPlacementPreference = -1;  // shrines/trade post spread
   llEnableEarlyForwardBase(480000);
}

void llUseCivicMilitiaCenterStyle(int wallLevel = 1)
{
   // Washington / Jefferson / Brock / Papineau — colonial frontier palisades.
   llConfigureBuildStyleProfile(cLLBuildStyleCivicMilitiaCenter, wallLevel, false, 0.95, 1.05, 0.95, 1.15, 2, 1, 2, false);
   gLLWallStrategy = cLLWallStrategyFrontierPalisades;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // militia at frontier
   llEnableEarlyForwardBase(420000);
}

// ── Bespoke historical archetypes ────────────────────────────────────────
// Steppe Cavalry Wedge — Lakota / Hungarian hussar doctrine: dispersed mobile
// camps, no perimeter, fast raiding cavalry from forward muster points.
void llUseSteppeCavalryWedgeStyle(int wallLevel = 0)
{
   // Hiawatha / Crazy Horse / steppe raiders — no walls, raid mobility.
   llConfigureBuildStyleProfile(cLLBuildStyleSteppeCavalryWedge, wallLevel, false,
      1.40, 1.50, 1.15, 1.55, 1, 0, 1, false);
   gLLWallStrategy = cLLWallStrategyMobileNoWalls;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // forward muster
   llEnableEarlyForwardBase(300000);
}

// Naval Mercantile Compound — Dutch / British / Portuguese commercial empire:
// coastal bank-and-dock spine, deep harbour batteries, money before muskets.
// Wellington's Torres Vedras doctrine — land-side ring-wall + naval batteries.
void llUseNavalMercantileCompoundStyle(int wallLevel = 2)
{
   llConfigureBuildStyleProfile(cLLBuildStyleNavalMercantileCompound, wallLevel, true,
      1.10, 1.30, 1.00, 1.25, 2, 2, 1, false);
   gLLWallStrategy = cLLWallStrategyCoastalBatteries;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;  // tucked behind harbor
}

// Siege Train Concentration — Ottoman / Prussian / Swedish cannon doctrine:
// Vauban-style bastions + clustered military quarter + forward line.
void llUseSiegeTrainConcentrationStyle(int wallLevel = 2)
{
   llConfigureBuildStyleProfile(cLLBuildStyleSiegeTrainConcentration, wallLevel, true,
      0.90, 1.00, 0.85, 0.95, 2, 2, 3, true);
   gLLWallStrategy = cLLWallStrategyFortressRing;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // grand battery line
   llEnableEarlyForwardBase(360000);
}

// Jungle Guerrilla Network — Maya / Haitian / Aztec scout-and-ambush doctrine:
// scattered war huts hidden in terrain, no perimeter wall, fluid response.
void llUseJungleGuerrillaNetworkStyle(int wallLevel = 0)
{
   llConfigureBuildStyleProfile(cLLBuildStyleJungleGuerrillaNetwork, wallLevel, false,
      1.10, 1.30, 0.95, 1.30, 1, 0, 2, true);
   gLLWallStrategy = cLLWallStrategyMobileNoWalls;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;
   llEnableEarlyForwardBase(360000);
}

// Highland Citadel — Maltese / Egyptian Mameluk / mountain fortress: tight
// core, multi-ring high walls, maximum towers and forts.
// Valette's Great Siege of Malta 1565 doctrine — triple fortress ring.
void llUseHighlandCitadelStyle(int wallLevel = 5)
{
   llConfigureBuildStyleProfile(cLLBuildStyleHighlandCitadel, wallLevel, true,
      0.65, 0.90, 0.80, 0.70, 4, 3, 2, false);
   gLLWallStrategy = cLLWallStrategyFortressRing;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;  // citadel core
}

// Cossack Voisko — Russian / Ukrainian host muster: massed barracks and
// Blockhouse net, forward host camp, swarm production.
// Catherine's Kremlin perimeter model.
void llUseCossackVoiskoStyle(int wallLevel = 1)
{
   llConfigureBuildStyleProfile(cLLBuildStyleCossackVoisko, wallLevel, false,
      0.90, 1.00, 0.80, 0.95, 2, 2, 3, true);
   gLLWallStrategy = cLLWallStrategyFortressRing;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // host muster forward
   llEnableEarlyForwardBase(360000);
}

// Republican Levee — French Revolution / American / Mexican citizen-army:
// civic spine of militia centers, town-center decentralised, militia first.
// Robespierre's Paris barricades; tight inner defense only.
void llUseRepublicanLeveeStyle(int wallLevel = 1)
{
   llConfigureBuildStyleProfile(cLLBuildStyleRepublicanLevee, wallLevel, false,
      0.95, 1.05, 0.90, 1.10, 2, 1, 3, true);
   gLLWallStrategy = cLLWallStrategyUrbanBarricade;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // levee marches outward
   llEnableEarlyForwardBase(360000);
}

// Andean Terrace Fortress — Inca / Peruvian / Chilean highland doctrine:
// walls at natural cliff edges and valley chokepoints only.
void llUseAndeanTerraceFortressStyle(int wallLevel = 3)
{
   llConfigureBuildStyleProfile(cLLBuildStyleAndeanTerraceFortress, wallLevel, true,
      0.80, 0.95, 0.90, 0.90, 3, 2, 2, false);
   gLLWallStrategy = cLLWallStrategyChokepointSegments;
   gLLMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;
}

void llSetBuildStrongpointProfile(int towerLevel = 1, int fortLevel = 1, int forwardBaseTowerCount = 2,
   bool preferForwardFortifiedBase = false)
{
   gLLTowerLevel = towerLevel;
   gLLFortLevel = fortLevel;
   gLLForwardBaseTowerCount = forwardBaseTowerCount;
   gLLPreferForwardFortifiedBase = preferForwardFortifiedBase;
   llProbe("event.strongpoint.profile",
      "towerL=" + towerLevel + " fortL=" + fortLevel +
      " fwdTowers=" + forwardBaseTowerCount +
      " preferFwd=" + preferForwardFortifiedBase);
}

int llGetWantedFortCount(void)
{
   int age = kbGetAge();
   int buildLimit = kbGetBuildLimit(cMyID, gFortUnit);
   int fortsWanted = 0;

   if ((cvOkToBuildForts == false) || (buildLimit < 1))
   {
      return (0);
   }

   if (gLLFortLevel <= 0)
   {
      fortsWanted = 0;
   }
   else if (gLLFortLevel == 1)
   {
      fortsWanted = age >= cAge4 ? 1 : 0;
   }
   else if (gLLFortLevel == 2)
   {
      fortsWanted = age >= cAge3 ? 1 : 0;
      if ((age >= cAge4) && (buildLimit > 1) && (gLLPreferForwardFortifiedBase == true))
      {
         fortsWanted = 2;
      }
   }
   else
   {
      fortsWanted = age >= cAge3 ? 1 : 0;
      if ((age >= cAge4) && (buildLimit > 1))
      {
         fortsWanted = 2;
      }
      if ((age >= cvMaxAge) && (buildLimit > fortsWanted))
      {
         fortsWanted = buildLimit;
      }
   }

   if (fortsWanted > buildLimit)
   {
      fortsWanted = buildLimit;
   }

   return (fortsWanted);
}

string llGetBuildStyleName(int style = 0)
{
   if (style == cLLBuildStyleCompactFortifiedCore)
   {
      return ("Compact Fortified Core");
   }
   if (style == cLLBuildStyleDistributedEconomicNetwork)
   {
      return ("Distributed Economic Network");
   }
   if (style == cLLBuildStyleForwardOperationalLine)
   {
      return ("Forward Operational Line");
   }
   if (style == cLLBuildStyleMobileFrontierScatter)
   {
      return ("Mobile Frontier Scatter");
   }
   if (style == cLLBuildStyleShrineTradeNodeSpread)
   {
      return ("Shrine or Trade Node Spread");
   }
   if (style == cLLBuildStyleCivicMilitiaCenter)
   {
      return ("Civic Militia Center");
   }
   if (style == cLLBuildStyleSteppeCavalryWedge)
   {
      return ("Steppe Cavalry Wedge");
   }
   if (style == cLLBuildStyleNavalMercantileCompound)
   {
      return ("Naval Mercantile Compound");
   }
   if (style == cLLBuildStyleSiegeTrainConcentration)
   {
      return ("Siege Train Concentration");
   }
   if (style == cLLBuildStyleJungleGuerrillaNetwork)
   {
      return ("Jungle Guerrilla Network");
   }
   if (style == cLLBuildStyleHighlandCitadel)
   {
      return ("Highland Citadel");
   }
   if (style == cLLBuildStyleCossackVoisko)
   {
      return ("Cossack Voisko");
   }
   if (style == cLLBuildStyleRepublicanLevee)
   {
      return ("Republican Levee");
   }
   if (style == cLLBuildStyleAndeanTerraceFortress)
   {
      return ("Andean Terrace Fortress");
   }
   return ("Unassigned");
}

//==============================================================================
/* llAssignLeaderIdentity
   Populate gLLLeaderKey and gLLChatsetKey so LL-PROBE events carry the leader
   identity into the replay chat stream. Keys match chatsetsmods.xml
   <Chatset name="..."> so post-match parsing can cross-reference directly.
*/
//==============================================================================
void llAssignLeaderIdentity(void)
{
   string rvltName = kbGetCivName(cMyCiv);

   // Base civs (22)
   if (cMyCiv == cCivFrench)            { gLLLeaderKey = "bourbon";     gLLChatsetKey = "bourbon"; }
   else if (cMyCiv == cCivBritish)      { gLLLeaderKey = "wellington";  gLLChatsetKey = "wellington"; }
   else if (cMyCiv == cCivGermans)      { gLLLeaderKey = "frederick";   gLLChatsetKey = "frederick"; }
   else if (cMyCiv == cCivRussians)     { gLLLeaderKey = "catherine";   gLLChatsetKey = "catherine"; }
   else if (cMyCiv == cCivSpanish)      { gLLLeaderKey = "isabella";    gLLChatsetKey = "isabella"; }
   else if (cMyCiv == cCivOttomans)     { gLLLeaderKey = "suleiman";    gLLChatsetKey = "suleiman"; }
   else if (cMyCiv == cCivPortuguese)   { gLLLeaderKey = "henry";       gLLChatsetKey = "henry"; }
   else if (cMyCiv == cCivDutch)        { gLLLeaderKey = "maurice";     gLLChatsetKey = "maurice"; }
   else if (cMyCiv == cCivDEAmericans)  { gLLLeaderKey = "washington";  gLLChatsetKey = "washington"; }
   else if (cMyCiv == cCivDEMexicans)   { gLLLeaderKey = "hidalgo";     gLLChatsetKey = "hidalgo"; }
   else if (cMyCiv == cCivDEItalians)   { gLLLeaderKey = "garibaldi";   gLLChatsetKey = "garibaldi"; }
   else if (cMyCiv == cCivDEMaltese)    { gLLLeaderKey = "jean";        gLLChatsetKey = "jean"; }
   else if (cMyCiv == cCivXPAztec)      { gLLLeaderKey = "montezuma";   gLLChatsetKey = "montezuma"; }
   else if (cMyCiv == cCivChinese)      { gLLLeaderKey = "kangxi";      gLLChatsetKey = "kangxi"; }
   else if (cMyCiv == cCivDEEthiopians) { gLLLeaderKey = "menelik";     gLLChatsetKey = "menelik"; }
   else if (cMyCiv == cCivXPIroquois)   { gLLLeaderKey = "hiawatha";    gLLChatsetKey = "hiawatha"; }
   else if (cMyCiv == cCivDEHausa)      { gLLLeaderKey = "usman";       gLLChatsetKey = "usman"; }
   else if (cMyCiv == cCivDEInca)       { gLLLeaderKey = "pachacuti";   gLLChatsetKey = "pachacuti"; }
   else if (cMyCiv == cCivIndians)      { gLLLeaderKey = "shivaji";     gLLChatsetKey = "shivaji"; }
   else if (cMyCiv == cCivJapanese)     { gLLLeaderKey = "tokugawa";    gLLChatsetKey = "tokugawa"; }
   else if (cMyCiv == cCivXPSioux)      { gLLLeaderKey = "crazyhorse";  gLLChatsetKey = "crazyhorse"; }
   else if (cMyCiv == cCivDESwedish)    { gLLLeaderKey = "gustav";      gLLChatsetKey = "gustav"; }
   // Revolution civs (26)
   else if (rvltName == "RvltModAmericans")          { gLLLeaderKey = "rvltmodamericans";          gLLChatsetKey = "rvltmodamericans"; }
   else if (rvltName == "RvltModArgentines")         { gLLLeaderKey = "rvltmodargentines";         gLLChatsetKey = "rvltmodargentines"; }
   else if (rvltName == "RvltModBajaCalifornians")   { gLLLeaderKey = "rvltmodbajacalifornians";   gLLChatsetKey = "rvltmodbajacalifornians"; }
   else if (rvltName == "RvltModBarbary")            { gLLLeaderKey = "rvltmodbarbary";            gLLChatsetKey = "rvltmodbarbary"; }
   else if (rvltName == "RvltModBrazil")             { gLLLeaderKey = "rvltmodbrazil";             gLLChatsetKey = "rvltmodbrazil"; }
   else if (rvltName == "RvltModCalifornians")       { gLLLeaderKey = "rvltmodcalifornians";       gLLChatsetKey = "rvltmodcalifornians"; }
   else if (rvltName == "RvltModCanadians")          { gLLLeaderKey = "rvltmodcanadians";          gLLChatsetKey = "rvltmodcanadians"; }
   else if (rvltName == "RvltModCentralAmericans")   { gLLLeaderKey = "rvltmodcentralamericans";   gLLChatsetKey = "rvltmodcentralamericans"; }
   else if (rvltName == "RvltModChileans")           { gLLLeaderKey = "rvltmodchileans";           gLLChatsetKey = "rvltmodchileans"; }
   else if (rvltName == "RvltModColumbians")         { gLLLeaderKey = "rvltmodcolumbians";         gLLChatsetKey = "rvltmodcolumbians"; }
   else if (rvltName == "RvltModEgyptians")          { gLLLeaderKey = "rvltmodegyptians";          gLLChatsetKey = "rvltmodegyptians"; }
   else if (rvltName == "RvltModFinnish")            { gLLLeaderKey = "rvltmodfinnish";            gLLChatsetKey = "rvltmodfinnish"; }
   else if (rvltName == "RvltModFrenchCanadians")    { gLLLeaderKey = "rvltmodfrenchcanadians";    gLLChatsetKey = "rvltmodfrenchcanadians"; }
   else if (rvltName == "RvltModHaitians")           { gLLLeaderKey = "rvltmodhaitians";           gLLChatsetKey = "rvltmodhaitians"; }
   else if (rvltName == "RvltModHungarians")         { gLLLeaderKey = "rvltmodhungarians";         gLLChatsetKey = "rvltmodhungarians"; }
   else if (rvltName == "RvltModIndonesians")        { gLLLeaderKey = "rvltmodindonesians";        gLLChatsetKey = "rvltmodindonesians"; }
   else if (rvltName == "RvltModMayans")             { gLLLeaderKey = "rvltmodmayans";             gLLChatsetKey = "rvltmodmayans"; }
   else if (rvltName == "RvltModMexicans")           { gLLLeaderKey = "rvltmodmexicans";           gLLChatsetKey = "rvltmodmexicans"; }
   else if (rvltName == "RvltModNapoleonicFrance")   { gLLLeaderKey = "napoleon";                  gLLChatsetKey = "napoleon"; }
   else if (rvltName == "RvltModPeruvians")          { gLLLeaderKey = "rvltmodperuvians";          gLLChatsetKey = "rvltmodperuvians"; }
   else if (rvltName == "RvltModRevolutionaryFrance"){ gLLLeaderKey = "rvltmodrevolutionaryfrance"; gLLChatsetKey = "rvltmodrevolutionaryfrance"; }
   else if (rvltName == "RvltModRioGrande")          { gLLLeaderKey = "rvltmodriogrande";          gLLChatsetKey = "rvltmodriogrande"; }
   else if (rvltName == "RvltModRomanians")          { gLLLeaderKey = "rvltmodromanians";          gLLChatsetKey = "rvltmodromanians"; }
   else if (rvltName == "RvltModSouthAfricans")      { gLLLeaderKey = "rvltmodsouthafricans";      gLLChatsetKey = "rvltmodsouthafricans"; }
   else if (rvltName == "RvltModTexians")            { gLLLeaderKey = "rvltmodtexians";            gLLChatsetKey = "rvltmodtexians"; }
   else if (rvltName == "RvltModYucatan")            { gLLLeaderKey = "rvltmodyucatan";            gLLChatsetKey = "rvltmodyucatan"; }
   // ANW revolution civs (19)
   else if (rvltName == "ANWArgentines")          { gLLLeaderKey = "anw_argentines";          gLLChatsetKey = "anw_argentines"; }
   else if (rvltName == "ANWBarbary")             { gLLLeaderKey = "anw_barbary";             gLLChatsetKey = "anw_barbary"; }
   else if (rvltName == "ANWBrazil")              { gLLLeaderKey = "anw_brazil";              gLLChatsetKey = "anw_brazil"; }
   else if (rvltName == "ANWCanadians")           { gLLLeaderKey = "anw_canadians";           gLLChatsetKey = "anw_canadians"; }
   else if (rvltName == "ANWChileans")            { gLLLeaderKey = "anw_chileans";            gLLChatsetKey = "anw_chileans"; }
   else if (rvltName == "ANWColumbians")          { gLLLeaderKey = "anw_columbians";          gLLChatsetKey = "anw_columbians"; }
   else if (rvltName == "ANWEgyptians")           { gLLLeaderKey = "anw_egyptians";           gLLChatsetKey = "anw_egyptians"; }
   else if (rvltName == "ANWFinnish")             { gLLLeaderKey = "anw_finnish";             gLLChatsetKey = "anw_finnish"; }
   else if (rvltName == "ANWHaitians")            { gLLLeaderKey = "anw_haitians";            gLLChatsetKey = "anw_haitians"; }
   else if (rvltName == "ANWHungarians")          { gLLLeaderKey = "anw_hungarians";          gLLChatsetKey = "anw_hungarians"; }
   else if (rvltName == "ANWIndonesians")         { gLLLeaderKey = "anw_indonesians";         gLLChatsetKey = "anw_indonesians"; }
   else if (rvltName == "ANWMayans")              { gLLLeaderKey = "anw_mayans";              gLLChatsetKey = "anw_mayans"; }
   else if (rvltName == "ANWMexicans")            { gLLLeaderKey = "anw_mexicans";            gLLChatsetKey = "anw_mexicans"; }
   else if (rvltName == "ANWNapoleonicFrance")    { gLLLeaderKey = "anw_napoleonicfrance";    gLLChatsetKey = "anw_napoleonicfrance"; }
   else if (rvltName == "ANWPeruvians")           { gLLLeaderKey = "anw_peruvians";           gLLChatsetKey = "anw_peruvians"; }
   else if (rvltName == "ANWRevFrance")           { gLLLeaderKey = "anw_revfrance";           gLLChatsetKey = "anw_revfrance"; }
   else if (rvltName == "ANWRomanians")           { gLLLeaderKey = "anw_romanians";           gLLChatsetKey = "anw_romanians"; }
   else if (rvltName == "ANWSouthAfricans")       { gLLLeaderKey = "anw_southafricans";       gLLChatsetKey = "anw_southafricans"; }
   else if (rvltName == "ANWTexians")             { gLLLeaderKey = "anw_texians";             gLLChatsetKey = "anw_texians"; }
   else
   {
      gLLLeaderKey = "unassigned-" + rvltName;
      gLLChatsetKey = "unassigned-" + rvltName;
      // Loud, replay-parseable failure marker so a missing dispatch entry is
      // never silent. Emitted before llProbe() below so the probe also flags
      // it via the leader= field carrying the "unassigned-" prefix.
      llLogEvent("LEADER", "UNASSIGNED civ=" + rvltName + " - add a dispatch entry to llAssignLeaderIdentity().");
   }

   // Replay probe: one atomic line per AI captured into the .age3Yrec chat
   // stream. Lets the post-match validator confirm every CPU loaded the
   // expected leader key for its civ.
   llProbe("meta.leader_assigned",
      "civ_id=" + cMyCiv + " civ_name=" + rvltName +
      " leader=" + gLLLeaderKey + " chatset=" + gLLChatsetKey);
}

void llApplyBuildStyleForActiveCiv(void)
{
   string rvltName = kbGetCivName(cMyCiv);

   llResetBuildStyleProfile();

   // ── STANDARD NATIONS (22) — bespoke per-civ profiles ─────────────────
   if (cMyCiv == cCivXPAztec)
   {
      // Montezuma — Flower War tribute aggression. Hidden war huts, no perimeter.
      llUseJungleGuerrillaNetworkStyle(0);
      gLLHouseDistanceMultiplier = 0.85;
      // Tenochtitlan chinampa: plaza-anchored, jungle-wetland bias.
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainWetland, 0.30);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivBritish)
   {
      // Queen Elizabeth I — Tudor naval, Sea Dogs, coastal Manor economy.
      llUseNavalMercantileCompoundStyle(2);
      gLLEconomicDistanceMultiplier = 1.30;
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainPlain, 0.55);
      llSetExpansionHeading(cLLHeadingAlongCoast, 0.45);
   }
   else if (cMyCiv == cCivChinese)
   {
      // Kangxi — High-walled Forbidden City. Compact, multi-ring fortress.
      llUseCompactFortifiedCoreStyle(4, true);
      gLLHouseDistanceMultiplier = 0.70;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.15);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivDutch)
   {
      // Maurice of Nassau — Dutch trade republic. Bank-and-dock spine.
      llUseNavalMercantileCompoundStyle(2);
      gLLEconomicDistanceMultiplier = 1.40;
      gLLHouseDistanceMultiplier = 1.05;
      // Low Countries: coast + polder wetland, VOC trade-route heading.
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainWetland, 0.60);
      llSetExpansionHeading(cLLHeadingFollowTradeRoute, 0.40);
   }
   else if (cMyCiv == cCivDEEthiopians)
   {
      // Menelik II — Highland citadel of Entoto / Magdala.
      llUseHighlandCitadelStyle(3);
      gLLHouseDistanceMultiplier = 0.80;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingDefensive, 0.0);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivFrench)
   {
      // Louis XVIII Bourbon — Vauban star-fort doctrine, compact fortified core.
      // Per LEGENDARY_LEADERS_TREE.html: "Compact Fortified Core" not Forward
      // Operational Line (that's Napoleon's revolution variant).
      llUseCompactFortifiedCoreStyle(2);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(2, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainPlain, 0.35);
      llSetExpansionHeading(cLLHeadingUpriver, 0.30);
   }
   else if (cMyCiv == cCivGermans)
   {
      // Frederick the Great — Prussian republican-levee + oblique-order march.
      // HTML reference promises Republican Levee (citizen-soldier brigade), not
      // Siege Train; the doctrine still gets its signature heavy guns through
      // gLLMilitaryDistanceMultiplier and strongpoint profile below.
      llUseRepublicanLeveeStyle(2);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(2, 2, 2, true);
      // Oder/Elbe plain — river-and-plain advance, enemy-ward.
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (cMyCiv == cCivXPIroquois)
   {
      // Hiawatha — Confederation longhouse and trade. Woodland + Great Lakes.
      llUseShrineTradeNodeSpreadStyle(1);
      gLLEconomicDistanceMultiplier = 1.20;
      llSetPreferredTerrain(cLLTerrainForestEdge, cLLTerrainRiver, 0.40);
      llSetExpansionHeading(cLLHeadingFollowTradeRoute, 0.35);
   }
   else if (cMyCiv == cCivDEHausa)
   {
      // Muhammadu Kanta of Kebbi — Hausa Surame-fortress doctrine, riding
      // the trans-Saharan caravan lattice. (Engine key remains "usman" for
      // dispatch stability; lore is Kanta — see leader_usman.xs header.)
      llUseDistributedEconomicNetworkStyle(2);
      gLLEconomicDistanceMultiplier = 1.30;
      llSetPreferredTerrain(cLLTerrainDesertOasis, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingFollowTradeRoute, 0.40);
   }
   else if (cMyCiv == cCivDEInca)
   {
      // Pachacuti — Sacsayhuamán terraced fortress.
      llUseAndeanTerraceFortressStyle(4);
      gLLHouseDistanceMultiplier = 0.75;
      llSetBuildStrongpointProfile(3, 3, 2, false);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainPlain, 0.20);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.15);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivIndians)
   {
      // Shivaji — Maratha hill-fort citadel doctrine. HTML reference promises
      // Highland Citadel (gad-fort network on the Sahyadri spurs), not Shrine
      // Trade Node; the Sacred Field economy is preserved via the strongpoint
      // profile and heading bias below.
      llUseHighlandCitadelStyle(5);
      gLLEconomicDistanceMultiplier = 1.10;
      llSetBuildStrongpointProfile(2, 1, 2, false);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainJungle, 0.30);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.15);
   }
   else if (cMyCiv == cCivDEItalians)
   {
      // Garibaldi — Risorgimento volunteer Redshirts marching north.
      llUseRepublicanLeveeStyle(2);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainRiver, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.40);
   }
   else if (cMyCiv == cCivJapanese)
   {
      // Tokugawa — Sankin-kōtai shrine network and castle towns, coast + river.
      llUseShrineTradeNodeSpreadStyle(3);
      gLLEconomicDistanceMultiplier = 1.25;
      llSetBuildStrongpointProfile(2, 2, 1, false);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainRiver, 0.45);
      llSetExpansionHeading(cLLHeadingFollowTradeRoute, 0.30);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivXPSioux)
   {
      // Chief Gall — Lakota wedge, plains horse archers, buffalo hunt mobility.
      llUseSteppeCavalryWedgeStyle(0);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.15);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.50);
   }
   else if (cMyCiv == cCivDEMaltese)
   {
      // Jean de Valette — Hospitaller fortress of Birgu and Senglea, 1565 siege.
      llUseHighlandCitadelStyle(5);
      llSetBuildStrongpointProfile(4, 3, 2, false);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainHighland, 0.35);
      llSetExpansionHeading(cLLHeadingDefensive, 0.0);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivDEMexicans)
   {
      // Hidalgo (standard) — Insurgent town-civic militia across the Bajío.
      llUseRepublicanLeveeStyle(1);
      gLLEconomicDistanceMultiplier = 1.15;
      llSetBuildStrongpointProfile(2, 1, 2, false);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainDesertOasis, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.35);
   }
   else if (cMyCiv == cCivOttomans)
   {
      // Suleiman the Magnificent — Ottoman siege at Vienna and Rhodes.
      llUseSiegeTrainConcentrationStyle(3);
      gLLEconomicDistanceMultiplier = 1.05;
      llSetBuildStrongpointProfile(2, 2, 2, true);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainCoast, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.40);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivPortuguese)
   {
      // Henry the Navigator — Carrack-and-feitoria Atlantic mercantile network.
      llUseNavalMercantileCompoundStyle(2);
      gLLEconomicDistanceMultiplier = 1.30;
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainRiver, 0.60);
      llSetExpansionHeading(cLLHeadingAlongCoast, 0.50);
   }
   else if (cMyCiv == cCivRussians)
   {
      // Ivan the Terrible — Streltsy corps, Kazan/Astrakhan siege, Volga push.
      llUseCossackVoiskoStyle(1);
      llSetBuildStrongpointProfile(2, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainForestEdge, 0.35);
      llSetExpansionHeading(cLLHeadingUpriver, 0.40);
   }
   else if (cMyCiv == cCivSpanish)
   {
      // Isabella — Reconquista forward operational line, Iberian plain.
      llUseForwardOperationalLineStyle(2);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainCoast, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
      llEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivDESwedish)
   {
      // Gustavus Adolphus — Lion of the North. HTML reference promises Forward
      // Operational Line (the famous Swedish thin-line tercio + drive-the-front
      // assault), not Siege Train; mobile field artillery is still expressed via
      // gLLMilitaryDistanceMultiplier (0.85) and the FrontierPush heading.
      llUseForwardOperationalLineStyle(1);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(2, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainForestEdge, 0.35);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.40);
   }
   else if (cMyCiv == cCivDEAmericans)
   {
      // Washington (standard) — Continental Army republican compound, tidewater.
      llUseRepublicanLeveeStyle(1);
      gLLTownCenterDistanceMultiplier = 1.10;
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainForestEdge, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.35);
   }

   // ── REVOLUTION NATIONS (26) — bespoke per-nation profiles ────────────
   else if (rvltName == "RvltModAmericans")
   {
      // Jefferson — Continental Congress republican civic spine, tidewater farms.
      llUseRepublicanLeveeStyle(0);
      gLLEconomicDistanceMultiplier = 1.05;
      gLLTownCenterDistanceMultiplier = 1.15;
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainForestEdge, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.35);
   }
   else if (rvltName == "RvltModArgentines")
   {
      // San Martin — Army of the Andes liberation column across the pampas.
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(1, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainHighland, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "RvltModBajaCalifornians")
   {
      // Baja Californians — Mission scatter on a long Pacific peninsula.
      llUseMobileFrontierScatterStyle(0);
      gLLHouseDistanceMultiplier = 1.40;
      gLLEconomicDistanceMultiplier = 1.50;
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainDesertOasis, 0.45);
      llSetExpansionHeading(cLLHeadingAlongCoast, 0.50);
   }
   else if (rvltName == "RvltModBarbary")
   {
      // Barbary — Corsair coastal compound, fortified harbour of Algiers/Tunis.
      llUseNavalMercantileCompoundStyle(2);
      gLLEconomicDistanceMultiplier = 1.20;
      llSetBuildStrongpointProfile(2, 2, 2, true);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainDesertOasis, 0.55);
      llSetExpansionHeading(cLLHeadingIslandHop, 0.40);
   }
   else if (rvltName == "RvltModBrazil")
   {
      // Brazil — Empire of Pedro II, sugar economy across Mata Atlântica coast.
      llUseDistributedEconomicNetworkStyle(2);
      gLLEconomicDistanceMultiplier = 1.35;
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainJungle, 0.40);
      llSetExpansionHeading(cLLHeadingAlongCoast, 0.35);
   }
   else if (rvltName == "RvltModCalifornians")
   {
      // Californians — Gold Rush boom across Sierra foothills & central valley.
      llUseDistributedEconomicNetworkStyle(1);
      gLLHouseDistanceMultiplier = 1.15;
      gLLEconomicDistanceMultiplier = 1.40;
      llSetBuildStrongpointProfile(2, 1, 1, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainHighland, 0.35);
      llSetExpansionHeading(cLLHeadingFollowTradeRoute, 0.40);
   }
   else if (rvltName == "RvltModCanadians")
   {
      // Canadians — Loyalist garrison along the St Lawrence / Great Lakes.
      llUseCompactFortifiedCoreStyle(2, false);
      gLLEconomicDistanceMultiplier = 0.95;
      llSetBuildStrongpointProfile(2, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainForestEdge, 0.40);
      llSetExpansionHeading(cLLHeadingUpriver, 0.35);
   }
   else if (rvltName == "RvltModCentralAmericans")
   {
      // Morazán — Federal Republic of Central America trade league on isthmus.
      llUseDistributedEconomicNetworkStyle(1);
      gLLEconomicDistanceMultiplier = 1.25;
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainCoast, 0.30);
      llSetExpansionHeading(cLLHeadingFollowTradeRoute, 0.35);
   }
   else if (rvltName == "RvltModChileans")
   {
      // O'Higgins — Andean column on the Pacific coast.
      llUseAndeanTerraceFortressStyle(2);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainCoast, 0.35);
      llSetExpansionHeading(cLLHeadingAlongCoast, 0.30);
   }
   else if (rvltName == "RvltModColumbians")
   {
      // Bolívar — Gran Colombia liberation drive across Andes and Llanos.
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(1, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainJungle, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "RvltModEgyptians")
   {
      // Muhammad Ali — Mameluke citadel of Cairo, Nile-anchored.
      llUseHighlandCitadelStyle(4);
      gLLHouseDistanceMultiplier = 0.75;
      llSetBuildStrongpointProfile(3, 3, 2, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainDesertOasis, 0.45);
      llSetExpansionHeading(cLLHeadingUpriver, 0.35);
      llEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "RvltModFinnish")
   {
      // Mannerheim — Winter War line across Karelian taiga.
      llUseCompactFortifiedCoreStyle(3, true);
      gLLHouseDistanceMultiplier = 0.80;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainForestEdge, cLLTerrainWetland, 0.35);
      llSetExpansionHeading(cLLHeadingDefensive, 0.0);
      llEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "RvltModFrenchCanadians")
   {
      // French Canadians — Patriote militia of Lower Canada, riverine parish.
      llUseCivicMilitiaCenterStyle(1);
      gLLEconomicDistanceMultiplier = 1.05;
      llSetBuildStrongpointProfile(2, 1, 2, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainForestEdge, 0.35);
      llSetExpansionHeading(cLLHeadingUpriver, 0.30);
   }
   else if (rvltName == "RvltModHaitians")
   {
      // Toussaint / Dessalines — Haitian Revolution jungle ambush, mountain.
      llUseJungleGuerrillaNetworkStyle(0);
      gLLEconomicDistanceMultiplier = 1.40;
      gLLTownCenterDistanceMultiplier = 1.40;
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainHighland, 0.35);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.15);
   }
   else if (rvltName == "RvltModHungarians")
   {
      // Kossuth — Hungarian hussar wedge of the 1848 Honvéd across the puszta.
      llUseSteppeCavalryWedgeStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "RvltModIndonesians")
   {
      // Diponegoro — Java War jungle-guerrilla campaign (Perang Diponegoro,
      // 1825-1830). HTML reference promises Jungle Guerrilla Network, not
      // Shrine Trade; the pesantren-village character is still encoded in
      // gLLEconomicDistanceMultiplier (1.40) + IslandHop heading.
      llUseJungleGuerrillaNetworkStyle(0);
      gLLEconomicDistanceMultiplier = 1.40;
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainCoast, 0.40);
      llSetExpansionHeading(cLLHeadingIslandHop, 0.35);
   }
   else if (rvltName == "RvltModMayans")
   {
      // Caste War — Maya jungle guerrilla, Yucatán bush huts on limestone shelf.
      llUseJungleGuerrillaNetworkStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainForestEdge, 0.40);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "RvltModMexicans")
   {
      // Hidalgo (revolution) — Grito de Dolores citizen army across Bajío.
      llUseRepublicanLeveeStyle(0);
      gLLEconomicDistanceMultiplier = 1.10;
      llSetBuildStrongpointProfile(1, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainDesertOasis, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.40);
   }
   else if (rvltName == "RvltModRevolutionaryFrance")
   {
      // Revolutionary France — Levée en masse of the Year II, Paris radiating.
      llUseRepublicanLeveeStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(1, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainPlain, 0.30);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "RvltModNapoleonicFrance")
   {
      // Napoleon Bonaparte (post-1804 Emperor) — Grande Armée operational manoeuvre.
      llUseForwardOperationalLineStyle(1);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(2, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.55);
   }
   else if (rvltName == "RvltModPeruvians")
   {
      // Túpac Amaru — Andean terrace fortress above the altiplano.
      llUseAndeanTerraceFortressStyle(3);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainPlain, 0.30);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
      llEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "RvltModRioGrande")
   {
      // Rio Grande — Republic-on-the-frontier ranching scatter, plains.
      llUseMobileFrontierScatterStyle(0);
      gLLHouseDistanceMultiplier = 1.35;
      gLLTownCenterDistanceMultiplier = 1.50;
      llSetBuildStrongpointProfile(1, 0, 2, false);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.35);
   }
   else if (rvltName == "RvltModRomanians")
   {
      // Cuza — Romanian unification civic militia, Carpathian-Danube axis.
      llUseCivicMilitiaCenterStyle(2);
      gLLEconomicDistanceMultiplier = 1.10;
      llSetBuildStrongpointProfile(2, 1, 2, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainHighland, 0.30);
      llSetExpansionHeading(cLLHeadingUpriver, 0.25);
   }
   else if (rvltName == "RvltModSouthAfricans")
   {
      // Boer Voortrekker — Laager-and-port colonial compound, Cape inland.
      llUseNavalMercantileCompoundStyle(1);
      gLLEconomicDistanceMultiplier = 1.25;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainPlain, 0.40);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.35);
   }
   else if (rvltName == "RvltModTexians")
   {
      // Houston — Texan revolution forward line at San Jacinto across prairie.
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "RvltModYucatan")
   {
      // Yucatán — Caste War jungle guerrilla on the limestone peninsula.
      llUseJungleGuerrillaNetworkStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainCoast, 0.40);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
   }

   // ── ANW NATIONS (19) — bespoke per-civ profiles ───────────────────────
   else if (rvltName == "ANWArgentines")
   {
      // San Martín — Army of the Andes liberation column across the pampas.
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(1, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainHighland, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWBarbary")
   {
      // Barbary — Corsair coastal compound, fortified harbour of Algiers/Tunis.
      llUseNavalMercantileCompoundStyle(2);
      gLLEconomicDistanceMultiplier = 1.20;
      llSetBuildStrongpointProfile(2, 2, 2, true);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainDesertOasis, 0.55);
      llSetExpansionHeading(cLLHeadingIslandHop, 0.40);
   }
   else if (rvltName == "ANWBrazil")
   {
      // Brazil — Empire of Pedro II, sugar economy across Mata Atlântica coast.
      llUseDistributedEconomicNetworkStyle(2);
      gLLEconomicDistanceMultiplier = 1.35;
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainJungle, 0.40);
      llSetExpansionHeading(cLLHeadingAlongCoast, 0.35);
   }
   else if (rvltName == "ANWCanadians")
   {
      // Canadians — Loyalist garrison along the St Lawrence / Great Lakes.
      llUseCompactFortifiedCoreStyle(2, false);
      gLLEconomicDistanceMultiplier = 0.95;
      llSetBuildStrongpointProfile(2, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainForestEdge, 0.40);
      llSetExpansionHeading(cLLHeadingUpriver, 0.35);
   }
   else if (rvltName == "ANWChileans")
   {
      // O'Higgins — Andean column on the Pacific coast.
      llUseAndeanTerraceFortressStyle(2);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainCoast, 0.35);
      llSetExpansionHeading(cLLHeadingAlongCoast, 0.30);
   }
   else if (rvltName == "ANWColumbians")
   {
      // Bolívar — Gran Colombia liberation drive across Andes and Llanos.
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(1, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainJungle, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWEgyptians")
   {
      // Muhammad Ali — Mameluke citadel of Cairo, Nile-anchored.
      llUseHighlandCitadelStyle(4);
      gLLHouseDistanceMultiplier = 0.75;
      llSetBuildStrongpointProfile(3, 3, 2, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainDesertOasis, 0.45);
      llSetExpansionHeading(cLLHeadingUpriver, 0.35);
      llEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWFinnish")
   {
      // Mannerheim — Winter War line across Karelian taiga.
      llUseCompactFortifiedCoreStyle(3, true);
      gLLHouseDistanceMultiplier = 0.80;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainForestEdge, cLLTerrainWetland, 0.35);
      llSetExpansionHeading(cLLHeadingDefensive, 0.0);
      llEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWHaitians")
   {
      // Toussaint / Dessalines — Haitian Revolution jungle ambush, mountain.
      llUseJungleGuerrillaNetworkStyle(0);
      gLLEconomicDistanceMultiplier = 1.40;
      gLLTownCenterDistanceMultiplier = 1.40;
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainHighland, 0.35);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.15);
      // spec: wall_strategy = ChokepointSegments — jungle terrain confines walls
      // to natural pinch points rather than the open-field sweep MobileNoWalls implies.
      gLLWallStrategy = cLLWallStrategyChokepointSegments;
   }
   else if (rvltName == "ANWHungarians")
   {
      // Kossuth — Hungarian hussar wedge of the 1848 Honvéd across the puszta.
      llUseSteppeCavalryWedgeStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWIndonesians")
   {
      // Diponegoro — Java War jungle-guerrilla campaign across the archipelago.
      llUseJungleGuerrillaNetworkStyle(0);
      gLLEconomicDistanceMultiplier = 1.40;
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainCoast, 0.40);
      llSetExpansionHeading(cLLHeadingIslandHop, 0.35);
   }
   else if (rvltName == "ANWMayans")
   {
      // Caste War — Maya jungle guerrilla, Yucatán bush huts on limestone shelf.
      llUseJungleGuerrillaNetworkStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      llSetPreferredTerrain(cLLTerrainJungle, cLLTerrainForestEdge, 0.40);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "ANWMexicans")
   {
      // Hidalgo — Insurgent town-civic militia across the Bajío.
      llUseRepublicanLeveeStyle(0);
      gLLEconomicDistanceMultiplier = 1.10;
      llSetBuildStrongpointProfile(1, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainDesertOasis, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.40);
   }
   else if (rvltName == "ANWNapoleonicFrance")
   {
      // Napoleon Bonaparte — Grande Armée operational manoeuvre, rivers and plains.
      llUseForwardOperationalLineStyle(1);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(2, 2, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.25);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.55);
   }
   else if (rvltName == "ANWPeruvians")
   {
      // Túpac Amaru / Santa Cruz — Andean terrace fortress above the altiplano.
      llUseAndeanTerraceFortressStyle(3);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      llSetPreferredTerrain(cLLTerrainHighland, cLLTerrainPlain, 0.30);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
      llEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWRevFrance")
   {
      // Robespierre — Levée en masse of the Year II, Paris-radiating republican line.
      llUseRepublicanLeveeStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(1, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainPlain, 0.30);
      llSetExpansionHeading(cLLHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "ANWRomanians")
   {
      // Cuza — Romanian unification civic militia, Carpathian-Danube axis.
      llUseCivicMilitiaCenterStyle(2);
      gLLEconomicDistanceMultiplier = 1.10;
      llSetBuildStrongpointProfile(2, 1, 2, false);
      llSetPreferredTerrain(cLLTerrainRiver, cLLTerrainHighland, 0.30);
      llSetExpansionHeading(cLLHeadingUpriver, 0.25);
   }
   else if (rvltName == "ANWSouthAfricans")
   {
      // Boer Voortrekker — Laager-and-port colonial compound, Cape inland.
      llUseNavalMercantileCompoundStyle(1);
      gLLEconomicDistanceMultiplier = 1.25;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      llSetPreferredTerrain(cLLTerrainCoast, cLLTerrainPlain, 0.40);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.35);
      // spec: wall_strategy = CoastalBatteries — harbour-anchored laager with
      // gun towers at the waterline; explicit override keeps the probe in sync
      // when probe data pre-dates this branch.
      gLLWallStrategy = cLLWallStrategyCoastalBatteries;
   }
   else if (rvltName == "ANWTexians")
   {
      // Sam Houston — Texan revolution forward line at San Jacinto across prairie.
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 3, true);
      llSetPreferredTerrain(cLLTerrainPlain, cLLTerrainRiver, 0.30);
      llSetExpansionHeading(cLLHeadingFrontierPush, 0.45);
   }

   llLogEvent("BUILDSTYLE", kbGetCivName(cMyCiv) + " -> " + llGetBuildStyleName(gLLBuildStyle) +
      " walls=" + gLLWallLevel + " earlyWalls=" + gLLEarlyWallingEnabled +
      " house=" + gLLHouseDistanceMultiplier + " eco=" + gLLEconomicDistanceMultiplier +
      " mil=" + gLLMilitaryDistanceMultiplier + " tc=" + gLLTownCenterDistanceMultiplier +
      " towerLevel=" + gLLTowerLevel + " fortLevel=" + gLLFortLevel +
      " forwardBaseTowers=" + gLLForwardBaseTowerCount + " forwardFortified=" + gLLPreferForwardFortifiedBase +
      " terrainPrimary=" + gLLPreferredTerrainPrimary + " terrainSecondary=" + gLLPreferredTerrainSecondary +
      " heading=" + gLLExpansionHeading + " terrainBias=" + gLLTerrainBiasStrength +
      " headingBias=" + gLLHeadingBiasStrength + " civicAnchor=" + gLLCenterAnchorCivic);

   // Replay probe: structured snapshot of the resolved build profile. Same
   // information as the BUILDSTYLE event log, but in the v=2 schema so the
   // post-match validator can tokenise it without parsing free-form text.
   llProbe("meta.buildstyle",
      "style=" + gLLBuildStyle +
      " walls=" + gLLWallLevel +
      " terrain_primary=" + gLLPreferredTerrainPrimary +
      " terrain_secondary=" + gLLPreferredTerrainSecondary +
      " terrain_bias=" + gLLTerrainBiasStrength +
      " heading=" + gLLExpansionHeading +
      " heading_bias=" + gLLHeadingBiasStrength +
      " civic_anchor=" + gLLCenterAnchorCivic);
}
