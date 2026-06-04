//==============================================================================
/* leaderCommon.xs

   Shared helper functions for A New World personalities.
*/
//==============================================================================

void anwResetLeaderBiases(void)
{
   btRushBoom = 0.0;
   btOffenseDefense = 0.0;
   btBiasNative = 0.0;
   btBiasTrade = 0.0;
   btBiasCav = 0.0;
   btBiasArt = 0.0;
   btBiasInf = 0.0;
   anwLogEvent("LEADER", "reset leader biases to neutral defaults.");
   anwProbe("event.personality.applied", "kind=reset rush=0.0 offDef=0.0");
}

void anwSetBalancedPersonality(void)
{
   anwResetLeaderBiases();
   btRushBoom = 0.0;
   btOffenseDefense = 0.0;
   anwLogLeaderState("balanced personality applied");
   anwProbe("event.personality.applied", "kind=balanced rush=" + btRushBoom + " offDef=" + btOffenseDefense);
}

void anwSetAggressivePersonality(void)
{
   anwResetLeaderBiases();
   btRushBoom = 0.8;
   btOffenseDefense = 0.8;
   anwLogLeaderState("aggressive personality applied");
   anwProbe("event.personality.applied", "kind=aggressive rush=" + btRushBoom + " offDef=" + btOffenseDefense);
}

void anwSetDefensivePersonality(void)
{
   anwResetLeaderBiases();
   btRushBoom = -0.4;
   btOffenseDefense = -0.6;
   anwLogLeaderState("defensive personality applied");
   anwProbe("event.personality.applied", "kind=defensive rush=" + btRushBoom + " offDef=" + btOffenseDefense);
}

void anwSetMilitaryFocus(float infantryBias = 0.0, float cavalryBias = 0.0, float artilleryBias = 0.0)
{
   btBiasInf = infantryBias;
   btBiasCav = cavalryBias;
   btBiasArt = artilleryBias;
   anwLogLeaderState("military focus updated");
   anwProbe("event.personality.applied", "kind=military inf=" + infantryBias + " cav=" + cavalryBias + " art=" + artilleryBias);
}

void anwEnableForwardBaseStyle(void)
{
   btOffenseDefense = 1.0;
   cvDefenseReflexRadiusActive = 75.0;
   cvDefenseReflexSearchRadius = 75.0;
   anwLogLeaderState("forward-base style enabled");
   anwProbe("event.style.feature", "kind=forwardBase reflexRadius=75.0");
}

void anwEnableDeepDefenseStyle(void)
{
   btOffenseDefense = -0.5;
   cvMaxTowers = 7;
   cvDefenseReflexRadiusPassive = 40.0;
   anwLogLeaderState("deep-defense style enabled");
   anwProbe("event.style.feature", "kind=deepDefense maxTowers=" + cvMaxTowers + " passiveRadius=40.0");
}

void anwResetBuildStyleProfile(void)
{
   gANWBuildStyle = 0;
   gANWWallLevel = 1;
   gANWEarlyWallingEnabled = true;
   gANWLateWallingEnabled = true;
   gANWHouseDistanceMultiplier = 1.0;
   gANWEconomicDistanceMultiplier = 1.0;
   gANWMilitaryDistanceMultiplier = 1.0;
   gANWTownCenterDistanceMultiplier = 1.0;
   gANWTowerLevel = 1;
   gANWFortLevel = 1;
   gANWForwardBaseTowerCount = 2;
   gANWPreferForwardFortifiedBase = false;
   gANWPreferredTerrainPrimary = cANWTerrainAny;
   gANWPreferredTerrainSecondary = cANWTerrainAny;
   gANWExpansionHeading = cANWHeadingAny;
   gANWCenterAnchorCivic = false;
   gANWTerrainBiasStrength = 0.35;
   gANWHeadingBiasStrength = 0.30;
   cvOkToBuildWalls = true;
}

// Terrain / expansion enforcement helpers.
//
// anwSetPreferredTerrain — primary is the dominant feature (coast for naval
// civs, river for inland riparian, highland for citadel civs, etc.). The
// placement pipeline in aiBuildings.xs drags the influence center toward
// the nearest instance of that feature when selecting a build position,
// so houses / eco / secondary TCs actually land on the historical terrain.
// Secondary is a fallback used when the primary isn't reachable.
void anwSetPreferredTerrain(int primary = 0, int secondary = 0, float strength = 0.35)
{
   gANWPreferredTerrainPrimary = primary;
   gANWPreferredTerrainSecondary = secondary;
   gANWTerrainBiasStrength = strength;
   anwProbe("event.terrain.preference",
      "primary=" + primary + " secondary=" + secondary + " strength=" + strength);
}

// anwSetExpansionHeading — compass/vector bias for secondary-TC and forward-
// military plans. "AlongCoast" follows the coastline vector, "Upriver"
// pushes inland away from coast, "FrontierPush" heads enemy-ward,
// "IslandHop" targets the far-shore spawn vector, "OutwardRings" keeps
// concentric around the main TC, "FollowTradeRoute" hugs trade-route
// sockets, "Defensive" explicitly refuses secondary expansion.
void anwSetExpansionHeading(int heading = 0, float strength = 0.30)
{
   gANWExpansionHeading = heading;
   gANWHeadingBiasStrength = strength;
   anwProbe("event.heading.preference", "heading=" + heading + " strength=" + strength);
}

// anwEnableCenterAnchoredCivic — some civs (Aztec, Inca, Ottoman, Kangxi,
// Maltese, Tokugawa, Isabella) historically anchor their market, temple,
// and civic buildings tight to the TC plaza rather than scattering them
// to build-plan radius. When set, anwApplyBaseInfluence reduces
// the center-distance clamp for non-military, non-house plans.
void anwEnableCenterAnchoredCivic(bool enabled = true)
{
   gANWCenterAnchorCivic = enabled;
   anwProbe("event.style.feature", "kind=civicAnchor enabled=" + enabled);
}

void anwConfigureBuildStyleProfile(int style = 0, int wallLevel = 1, bool earlyWalls = false,
   float houseDistanceMultiplier = 1.0, float economicDistanceMultiplier = 1.0,
   float militaryDistanceMultiplier = 1.0, float townCenterDistanceMultiplier = 1.0,
   int towerLevel = 1, int fortLevel = 1, int forwardBaseTowerCount = 2,
   bool preferForwardFortifiedBase = false)
{
   gANWBuildStyle = style;
   gANWWallLevel = wallLevel;
   // Honor caller's earlyWalls preference (was hardcoded to true). Mobile/
   // guerrilla styles that want to skirmish instead of wall early can pass
   // earlyWalls=false via their style helper (SteppeCavalryWedge,
   // MobileFrontierScatter, JungleGuerrillaNetwork) and get a pure mobile
   // opening. Defensive leaders pass earlyWalls=true for ring-walls at Age 1.
   gANWEarlyWallingEnabled = earlyWalls && (wallLevel > 0);
   gANWLateWallingEnabled = (wallLevel > 0);
   gANWHouseDistanceMultiplier = houseDistanceMultiplier;
   gANWEconomicDistanceMultiplier = economicDistanceMultiplier;
   gANWMilitaryDistanceMultiplier = militaryDistanceMultiplier;
   gANWTownCenterDistanceMultiplier = townCenterDistanceMultiplier;
   gANWTowerLevel = towerLevel;
   gANWFortLevel = fortLevel;
   gANWForwardBaseTowerCount = forwardBaseTowerCount;
   gANWPreferForwardFortifiedBase = preferForwardFortifiedBase;
   cvOkToBuildWalls = true;
   // Reset placement preference; specific style helpers below set it. -1 keeps
   // the engine's legacy random-cardinal behaviour for any style that does
   // not assert a doctrine.
   gANWMilitaryPlacementPreference = -1;
   gANWForwardBaseEarliestMs = 1200000;
   gANWForwardBaseAnyDifficulty = false;
   anwProbe("event.style.applied",
      "style=" + style + " wallLevel=" + wallLevel +
      " earlyWalls=" + gANWEarlyWallingEnabled +
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
void anwEnableEarlyForwardBase(int earliestMs = 360000)
{
   gANWForwardBaseEarliestMs = earliestMs;       // default: 6 min instead of 20
   gANWForwardBaseAnyDifficulty = true;          // remove Expert-only gate
   gANWPreferForwardFortifiedBase = true;
   anwProbe("event.style.feature", "kind=earlyFwdBase earliestMs=" + earliestMs);
}

void anwUseCompactFortifiedCoreStyle(int wallLevel = 3, bool earlyWalls = true)
{
   // Bourbon France — Vauban-school star-fort doctrine. Full fortress ring.
   anwConfigureBuildStyleProfile(cANWBuildStyleCompactFortifiedCore, wallLevel, earlyWalls, 0.75, 0.85, 0.85, 0.85, 3, 2, 2, false);
   gANWWallStrategy = cANWWallStrategyFortressRing;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;  // tight core
}

void anwUseDistributedEconomicNetworkStyle(int wallLevel = 1)
{
   // Morazán / Central American federation — frontier palisade on scattered nodes.
   // Note: do NOT call anwEnableEarlyForwardBase here. Treaty-leaning civs that
   // use this style (Hausa Usman, Brazil Pedro) have spec expects_treaty=true
   // and must not be forced into early forward-base posture. Leaders that
   // genuinely want a forward base (e.g. Morazán himself) can call
   // anwEnableForwardBaseStyle() explicitly from their leader init or rule.
   anwConfigureBuildStyleProfile(cANWBuildStyleDistributedEconomicNetwork, wallLevel, false, 1.15, 1.35, 1.0, 1.35, 1, 1, 1, false);
   gANWWallStrategy = cANWWallStrategyFrontierPalisades;
   gANWMilitaryPlacementPreference = -1;  // genuine spread
}

void anwUseForwardOperationalLineStyle(int wallLevel = 1)
{
   // Napoleon — no early walls, move fast. Field fortifications only in Age 3+.
   anwConfigureBuildStyleProfile(cANWBuildStyleForwardOperationalLine, wallLevel, false, 1.0, 1.05, 0.95, 1.1, 1, 2, 3, true);
   gANWWallStrategy = cANWWallStrategyMobileNoWalls;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // forward line
   anwEnableEarlyForwardBase(300000);     // 5 min — Napoleonic operational tempo
}

void anwUseMobileFrontierScatterStyle(int wallLevel = 0)
{
   // Crazy Horse / Plains mobile — never wall, scout + intercept.
   anwConfigureBuildStyleProfile(cANWBuildStyleMobileFrontierScatter, wallLevel, false, 1.35, 1.45, 1.1, 1.5, 1, 0, 1, false);
   gANWWallStrategy = cANWWallStrategyMobileNoWalls;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;
   anwEnableEarlyForwardBase(360000);
}

void anwUseShrineTradeNodeSpreadStyle(int wallLevel = 1)
{
   // Tokugawa — sakoku-era redoubts at approaches, no perimeter wall.
   anwConfigureBuildStyleProfile(cANWBuildStyleShrineTradeNodeSpread, wallLevel, false, 1.0, 1.5, 0.95, 1.2, 1, 1, 1, false);
   gANWWallStrategy = cANWWallStrategyMobileNoWalls;
   gANWMilitaryPlacementPreference = -1;  // shrines/trade post spread
   anwEnableEarlyForwardBase(480000);
}

void anwUseCivicMilitiaCenterStyle(int wallLevel = 1)
{
   // Washington / Jefferson / Brock — colonial frontier palisades.
   anwConfigureBuildStyleProfile(cANWBuildStyleCivicMilitiaCenter, wallLevel, false, 0.95, 1.05, 0.95, 1.15, 2, 1, 2, false);
   gANWWallStrategy = cANWWallStrategyFrontierPalisades;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // militia at frontier
   anwEnableEarlyForwardBase(420000);
}

// ── Bespoke historical archetypes ────────────────────────────────────────
// Steppe Cavalry Wedge — Lakota / Hungarian hussar doctrine: dispersed mobile
// camps, no perimeter, fast raiding cavalry from forward muster points.
void anwUseSteppeCavalryWedgeStyle(int wallLevel = 0)
{
   // Hiawatha / Crazy Horse / steppe raiders — no walls, raid mobility.
   anwConfigureBuildStyleProfile(cANWBuildStyleSteppeCavalryWedge, wallLevel, false,
      1.40, 1.50, 1.15, 1.55, 1, 0, 1, false);
   gANWWallStrategy = cANWWallStrategyMobileNoWalls;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // forward muster
   anwEnableEarlyForwardBase(300000);
}

// Naval Mercantile Compound — Dutch / British / Portuguese commercial empire:
// coastal bank-and-dock spine, deep harbour batteries, money before muskets.
// Wellington's Torres Vedras doctrine — land-side ring-wall + naval batteries.
void anwUseNavalMercantileCompoundStyle(int wallLevel = 2)
{
   anwConfigureBuildStyleProfile(cANWBuildStyleNavalMercantileCompound, wallLevel, true,
      1.10, 1.30, 1.00, 1.25, 2, 2, 1, false);
   gANWWallStrategy = cANWWallStrategyCoastalBatteries;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;  // tucked behind harbor
}

// Siege Train Concentration — Ottoman / Prussian / Swedish cannon doctrine:
// Vauban-style bastions + clustered military quarter + forward line.
void anwUseSiegeTrainConcentrationStyle(int wallLevel = 2)
{
   anwConfigureBuildStyleProfile(cANWBuildStyleSiegeTrainConcentration, wallLevel, true,
      0.90, 1.00, 0.85, 0.95, 2, 2, 3, true);
   gANWWallStrategy = cANWWallStrategyFortressRing;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // grand battery line
   anwEnableEarlyForwardBase(360000);
}

// Jungle Guerrilla Network — Maya / Haitian / Aztec scout-and-ambush doctrine:
// scattered war huts hidden in terrain, no perimeter wall, fluid response.
void anwUseJungleGuerrillaNetworkStyle(int wallLevel = 0)
{
   anwConfigureBuildStyleProfile(cANWBuildStyleJungleGuerrillaNetwork, wallLevel, false,
      1.10, 1.30, 0.95, 1.30, 1, 0, 2, true);
   gANWWallStrategy = cANWWallStrategyMobileNoWalls;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;
   anwEnableEarlyForwardBase(360000);
}

// Highland Citadel — Maltese / Egyptian Mameluk / mountain fortress: tight
// core, multi-ring high walls, maximum towers and forts.
// Valette's Great Siege of Malta 1565 doctrine — triple fortress ring.
void anwUseHighlandCitadelStyle(int wallLevel = 5)
{
   anwConfigureBuildStyleProfile(cANWBuildStyleHighlandCitadel, wallLevel, true,
      0.65, 0.90, 0.80, 0.70, 4, 3, 2, false);
   gANWWallStrategy = cANWWallStrategyFortressRing;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;  // citadel core
}

// Cossack Voisko — Russian / Ukrainian host muster: massed barracks and
// Blockhouse net, forward host camp, swarm production.
// Catherine's Kremlin perimeter model.
void anwUseCossackVoiskoStyle(int wallLevel = 1)
{
   anwConfigureBuildStyleProfile(cANWBuildStyleCossackVoisko, wallLevel, false,
      0.90, 1.00, 0.80, 0.95, 2, 2, 3, true);
   gANWWallStrategy = cANWWallStrategyFortressRing;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // host muster forward
   anwEnableEarlyForwardBase(360000);
}

// Republican Levee — French Revolution / American / Mexican citizen-army:
// civic spine of militia centers, town-center decentralised, militia first.
// Robespierre's Paris barricades; tight inner defense only.
void anwUseRepublicanLeveeStyle(int wallLevel = 1, bool earlyWalls = false)
{
   // earlyWalls defaults false to preserve the mobile civic-uprising opening
   // for revolutionary civs (Robespierre, Washington, Hidalgo). Static-base
   // republican-levee civs that the spec gates with first_wall_before_ms
   // (Frederick=900s, Garibaldi=900s) pass earlyWalls=true to ensure the
   // engine emits a palisade ring well inside the deadline.
   anwConfigureBuildStyleProfile(cANWBuildStyleRepublicanLevee, wallLevel, earlyWalls,
      0.95, 1.05, 0.90, 1.10, 2, 1, 3, true);
   gANWWallStrategy = cANWWallStrategyUrbanBarricade;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceFront;  // levee marches outward
   anwEnableEarlyForwardBase(360000);
}

// Andean Terrace Fortress — Inca / Peruvian / Chilean highland doctrine:
// walls at natural cliff edges and valley chokepoints only.
void anwUseAndeanTerraceFortressStyle(int wallLevel = 3)
{
   anwConfigureBuildStyleProfile(cANWBuildStyleAndeanTerraceFortress, wallLevel, true,
      0.80, 0.95, 0.90, 0.90, 3, 2, 2, false);
   gANWWallStrategy = cANWWallStrategyChokepointSegments;
   gANWMilitaryPlacementPreference = cBuildingPlacementPreferenceBack;
}

void anwSetBuildStrongpointProfile(int towerLevel = 1, int fortLevel = 1, int forwardBaseTowerCount = 2,
   bool preferForwardFortifiedBase = false)
{
   gANWTowerLevel = towerLevel;
   gANWFortLevel = fortLevel;
   gANWForwardBaseTowerCount = forwardBaseTowerCount;
   gANWPreferForwardFortifiedBase = preferForwardFortifiedBase;
   anwProbe("event.strongpoint.profile",
      "towerL=" + towerLevel + " fortL=" + fortLevel +
      " fwdTowers=" + forwardBaseTowerCount +
      " preferFwd=" + preferForwardFortifiedBase);
}

int anwGetWantedFortCount(void)
{
   int age = kbGetAge();
   int buildLimit = kbGetBuildLimit(cMyID, gFortUnit);
   int fortsWanted = 0;

   if ((cvOkToBuildForts == false) || (buildLimit < 1))
   {
      return (0);
   }

   if (gANWFortLevel <= 0)
   {
      fortsWanted = 0;
   }
   else if (gANWFortLevel == 1)
   {
      fortsWanted = age >= cAge4 ? 1 : 0;
   }
   else if (gANWFortLevel == 2)
   {
      fortsWanted = age >= cAge3 ? 1 : 0;
      if ((age >= cAge4) && (buildLimit > 1) && (gANWPreferForwardFortifiedBase == true))
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

string anwGetBuildStyleName(int style = 0)
{
   if (style == cANWBuildStyleCompactFortifiedCore)
   {
      return ("Compact Fortified Core");
   }
   if (style == cANWBuildStyleDistributedEconomicNetwork)
   {
      return ("Distributed Economic Network");
   }
   if (style == cANWBuildStyleForwardOperationalLine)
   {
      return ("Forward Operational Line");
   }
   if (style == cANWBuildStyleMobileFrontierScatter)
   {
      return ("Mobile Frontier Scatter");
   }
   if (style == cANWBuildStyleShrineTradeNodeSpread)
   {
      return ("Shrine or Trade Node Spread");
   }
   if (style == cANWBuildStyleCivicMilitiaCenter)
   {
      return ("Civic Militia Center");
   }
   if (style == cANWBuildStyleSteppeCavalryWedge)
   {
      return ("Steppe Cavalry Wedge");
   }
   if (style == cANWBuildStyleNavalMercantileCompound)
   {
      return ("Naval Mercantile Compound");
   }
   if (style == cANWBuildStyleSiegeTrainConcentration)
   {
      return ("Siege Train Concentration");
   }
   if (style == cANWBuildStyleJungleGuerrillaNetwork)
   {
      return ("Jungle Guerrilla Network");
   }
   if (style == cANWBuildStyleHighlandCitadel)
   {
      return ("Highland Citadel");
   }
   if (style == cANWBuildStyleCossackVoisko)
   {
      return ("Cossack Voisko");
   }
   if (style == cANWBuildStyleRepublicanLevee)
   {
      return ("Republican Levee");
   }
   if (style == cANWBuildStyleAndeanTerraceFortress)
   {
      return ("Andean Terrace Fortress");
   }
   return ("Unassigned");
}

//==============================================================================
/* anwAssignLeaderIdentity
   Populate gANWLeaderKey and gANWChatsetKey so LL-PROBE events carry the leader
   identity into the replay chat stream. Keys match chatsetsmods.xml
   <Chatset name="..."> so post-match parsing can cross-reference directly.
*/
//==============================================================================
void anwAssignLeaderIdentity(void)
{
   string rvltName = kbGetCivName(cMyCiv);

   // Base civs (22)
   if (cMyCiv == cCivFrench)            { gANWLeaderKey = "bourbon";     gANWChatsetKey = "bourbon"; }
   else if (cMyCiv == cCivBritish)      { gANWLeaderKey = "wellington";  gANWChatsetKey = "wellington"; }
   else if (cMyCiv == cCivGermans)      { gANWLeaderKey = "frederick";   gANWChatsetKey = "frederick"; }
   else if (cMyCiv == cCivRussians)     { gANWLeaderKey = "catherine";   gANWChatsetKey = "catherine"; }
   else if (cMyCiv == cCivSpanish)      { gANWLeaderKey = "isabella";    gANWChatsetKey = "isabella"; }
   else if (cMyCiv == cCivOttomans)     { gANWLeaderKey = "suleiman";    gANWChatsetKey = "suleiman"; }
   else if (cMyCiv == cCivPortuguese)   { gANWLeaderKey = "henry";       gANWChatsetKey = "henry"; }
   else if (cMyCiv == cCivDutch)        { gANWLeaderKey = "maurice";     gANWChatsetKey = "maurice"; }
   else if (cMyCiv == cCivDEAmericans)  { gANWLeaderKey = "washington";  gANWChatsetKey = "washington"; }
   else if (cMyCiv == cCivDEMexicans)   { gANWLeaderKey = "hidalgo";     gANWChatsetKey = "hidalgo"; }
   else if (cMyCiv == cCivDEItalians)   { gANWLeaderKey = "garibaldi";   gANWChatsetKey = "garibaldi"; }
   else if (cMyCiv == cCivDEMaltese)    { gANWLeaderKey = "jean";        gANWChatsetKey = "jean"; }
   else if (cMyCiv == cCivXPAztec)      { gANWLeaderKey = "montezuma";   gANWChatsetKey = "montezuma"; }
   else if (cMyCiv == cCivChinese)      { gANWLeaderKey = "kangxi";      gANWChatsetKey = "kangxi"; }
   else if (cMyCiv == cCivDEEthiopians) { gANWLeaderKey = "menelik";     gANWChatsetKey = "menelik"; }
   else if (cMyCiv == cCivXPIroquois)   { gANWLeaderKey = "hiawatha";    gANWChatsetKey = "hiawatha"; }
   else if (cMyCiv == cCivDEHausa)      { gANWLeaderKey = "usman";       gANWChatsetKey = "usman"; }
   else if (cMyCiv == cCivDEInca)       { gANWLeaderKey = "pachacuti";   gANWChatsetKey = "pachacuti"; }
   else if (cMyCiv == cCivIndians)      { gANWLeaderKey = "shivaji";     gANWChatsetKey = "shivaji"; }
   else if (cMyCiv == cCivJapanese)     { gANWLeaderKey = "tokugawa";    gANWChatsetKey = "tokugawa"; }
   else if (cMyCiv == cCivXPSioux)      { gANWLeaderKey = "crazyhorse";  gANWChatsetKey = "crazyhorse"; }
   else if (cMyCiv == cCivDESwedish)    { gANWLeaderKey = "gustav";      gANWChatsetKey = "gustav"; }
   // ANW revolution civs (19)
   else if (rvltName == "ANWArgentines")          { gANWLeaderKey = "anw_argentines";          gANWChatsetKey = "anw_argentines"; }
   else if (rvltName == "ANWBarbary")             { gANWLeaderKey = "anw_barbary";             gANWChatsetKey = "anw_barbary"; }
   else if (rvltName == "ANWBrazil")              { gANWLeaderKey = "anw_brazil";              gANWChatsetKey = "anw_brazil"; }
   else if (rvltName == "ANWCanadians")           { gANWLeaderKey = "anw_canadians";           gANWChatsetKey = "anw_canadians"; }
   else if (rvltName == "ANWChileans")            { gANWLeaderKey = "anw_chileans";            gANWChatsetKey = "anw_chileans"; }
   else if (rvltName == "ANWColumbians")          { gANWLeaderKey = "anw_columbians";          gANWChatsetKey = "anw_columbians"; }
   else if (rvltName == "ANWEgyptians")           { gANWLeaderKey = "anw_egyptians";           gANWChatsetKey = "anw_egyptians"; }
   else if (rvltName == "ANWFinnish")             { gANWLeaderKey = "anw_finnish";             gANWChatsetKey = "anw_finnish"; }
   else if (rvltName == "ANWHaitians")            { gANWLeaderKey = "anw_haitians";            gANWChatsetKey = "anw_haitians"; }
   else if (rvltName == "ANWHungarians")          { gANWLeaderKey = "anw_hungarians";          gANWChatsetKey = "anw_hungarians"; }
   else if (rvltName == "ANWIndonesians")         { gANWLeaderKey = "anw_indonesians";         gANWChatsetKey = "anw_indonesians"; }
   else if (rvltName == "ANWMayans")              { gANWLeaderKey = "anw_mayans";              gANWChatsetKey = "anw_mayans"; }
   else if (rvltName == "ANWMexicans")            { gANWLeaderKey = "anw_mexicans";            gANWChatsetKey = "anw_mexicans"; }
   else if (rvltName == "ANWNapoleonicFrance")    { gANWLeaderKey = "anw_napoleonicfrance";    gANWChatsetKey = "anw_napoleonicfrance"; }
   else if (rvltName == "ANWPeruvians")           { gANWLeaderKey = "anw_peruvians";           gANWChatsetKey = "anw_peruvians"; }
   else if (rvltName == "ANWRevFrance")           { gANWLeaderKey = "anw_revfrance";           gANWChatsetKey = "anw_revfrance"; }
   else if (rvltName == "ANWRomanians")           { gANWLeaderKey = "anw_romanians";           gANWChatsetKey = "anw_romanians"; }
   else if (rvltName == "ANWSouthAfricans")       { gANWLeaderKey = "anw_southafricans";       gANWChatsetKey = "anw_southafricans"; }
   else if (rvltName == "ANWTexians")             { gANWLeaderKey = "anw_texians";             gANWChatsetKey = "anw_texians"; }
   // ── ANW CANONICAL NATIONS (21) — unique mod-added civs, name-dispatched ─
   else if (rvltName == "ANWAztecs")         { gANWLeaderKey = "anw_aztecs";         gANWChatsetKey = "anw_aztecs"; }
   else if (rvltName == "ANWBritish")        { gANWLeaderKey = "anw_british";        gANWChatsetKey = "anw_british"; }
   else if (rvltName == "ANWChinese")        { gANWLeaderKey = "anw_chinese";        gANWChatsetKey = "anw_chinese"; }
   else if (rvltName == "ANWDutch")          { gANWLeaderKey = "anw_dutch";          gANWChatsetKey = "anw_dutch"; }
   else if (rvltName == "ANWEthiopians")     { gANWLeaderKey = "anw_ethiopians";     gANWChatsetKey = "anw_ethiopians"; }
   else if (rvltName == "ANWFrench")         { gANWLeaderKey = "anw_french";         gANWChatsetKey = "anw_french"; }
   else if (rvltName == "ANWGermans")        { gANWLeaderKey = "anw_germans";        gANWChatsetKey = "anw_germans"; }
   else if (rvltName == "ANWHaudenosaunee")  { gANWLeaderKey = "anw_haudenosaunee";  gANWChatsetKey = "anw_haudenosaunee"; }
   else if (rvltName == "ANWHausa")          { gANWLeaderKey = "anw_hausa";          gANWChatsetKey = "anw_hausa"; }
   else if (rvltName == "ANWInca")           { gANWLeaderKey = "anw_inca";           gANWChatsetKey = "anw_inca"; }
   else if (rvltName == "ANWIndians")        { gANWLeaderKey = "anw_indians";        gANWChatsetKey = "anw_indians"; }
   else if (rvltName == "ANWItalians")       { gANWLeaderKey = "anw_italians";       gANWChatsetKey = "anw_italians"; }
   else if (rvltName == "ANWJapanese")       { gANWLeaderKey = "anw_japanese";       gANWChatsetKey = "anw_japanese"; }
   else if (rvltName == "ANWLakota")         { gANWLeaderKey = "anw_lakota";         gANWChatsetKey = "anw_lakota"; }
   else if (rvltName == "ANWMaltese")        { gANWLeaderKey = "anw_maltese";        gANWChatsetKey = "anw_maltese"; }
   else if (rvltName == "ANWOttomans")       { gANWLeaderKey = "anw_ottomans";       gANWChatsetKey = "anw_ottomans"; }
   else if (rvltName == "ANWPortuguese")     { gANWLeaderKey = "anw_portuguese";     gANWChatsetKey = "anw_portuguese"; }
   else if (rvltName == "ANWRussians")       { gANWLeaderKey = "anw_russians";       gANWChatsetKey = "anw_russians"; }
   else if (rvltName == "ANWSpanish")        { gANWLeaderKey = "anw_spanish";        gANWChatsetKey = "anw_spanish"; }
   else if (rvltName == "ANWSwedes")         { gANWLeaderKey = "anw_swedes";         gANWChatsetKey = "anw_swedes"; }
   else if (rvltName == "ANWUSA")            { gANWLeaderKey = "anw_usa";            gANWChatsetKey = "anw_usa"; }
   else
   {
      gANWLeaderKey = "unassigned-" + rvltName;
      gANWChatsetKey = "unassigned-" + rvltName;
      // Loud, replay-parseable failure marker so a missing dispatch entry is
      // never silent. Emitted before anwProbe() below so the probe also flags
      // it via the leader= field carrying the "unassigned-" prefix.
      anwLogEvent("LEADER", "UNASSIGNED civ=" + rvltName + " - add a dispatch entry to anwAssignLeaderIdentity().");
   }

   // Replay probe: one atomic line per AI captured into the .age3Yrec chat
   // stream. Lets the post-match validator confirm every CPU loaded the
   // expected leader key for its civ.
   anwProbe("meta.leader_assigned",
      "civ_id=" + cMyCiv + " civ_name=" + rvltName +
      " leader=" + gANWLeaderKey + " chatset=" + gANWChatsetKey);
}

void anwApplyBuildStyleForActiveCiv(void)
{
   string rvltName = kbGetCivName(cMyCiv);

   anwResetBuildStyleProfile();

   // ── STANDARD NATIONS (22) — bespoke per-civ profiles ─────────────────
   if (cMyCiv == cCivXPAztec)
   {
      // Montezuma — Flower War tribute aggression. Hidden war huts, no perimeter.
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWHouseDistanceMultiplier = 0.85;
      // Tenochtitlan chinampa: plaza-anchored, jungle-wetland bias.
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainWetland, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivBritish)
   {
      // Queen Elizabeth I — Tudor naval, Sea Dogs, coastal Manor economy.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.30;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainPlain, 0.55);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.45);
   }
   else if (cMyCiv == cCivChinese)
   {
      // Kangxi — High-walled Forbidden City. Compact, multi-ring fortress.
      anwUseCompactFortifiedCoreStyle(4, true);
      gANWHouseDistanceMultiplier = 0.70;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivDutch)
   {
      // Maurice of Nassau — Dutch trade republic. Bank-and-dock spine.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.40;
      gANWHouseDistanceMultiplier = 1.05;
      // Low Countries: coast + polder wetland, VOC trade-route heading.
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainWetland, 0.60);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.40);
   }
   else if (cMyCiv == cCivDEEthiopians)
   {
      // Menelik II — Highland citadel of Entoto / Magdala.
      anwUseHighlandCitadelStyle(3);
      gANWHouseDistanceMultiplier = 0.80;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingDefensive, 0.0);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivFrench)
   {
      // Louis XVIII Bourbon — Vauban star-fort doctrine, compact fortified core.
      // Per LEGENDARY_LEADERS_TREE.html: "Compact Fortified Core" not Forward
      // Operational Line (that's Napoleon's revolution variant).
      // wallLevel=3 matches leader_bourbon.xs init so applyBuildStyle does not
      // silently downgrade Bourbon's wall investment after leader init runs.
      anwUseCompactFortifiedCoreStyle(3, true);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainPlain, 0.35);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.30);
   }
   else if (cMyCiv == cCivGermans)
   {
      // Frederick the Great — Prussian republican-levee + oblique-order march.
      // HTML reference promises Republican Levee (citizen-soldier brigade), not
      // Siege Train; the doctrine still gets its signature heavy guns through
      // gANWMilitaryDistanceMultiplier and strongpoint profile below.
      // earlyWalls=true to honour spec first_wall_before_ms=900000 (audit v2 WARN).
      anwUseRepublicanLeveeStyle(2, true);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 2, true);
      // Oder/Elbe plain — river-and-plain advance, enemy-ward.
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (cMyCiv == cCivXPIroquois)
   {
      // Hiawatha — Confederation longhouse and trade. Woodland + Great Lakes.
      anwUseShrineTradeNodeSpreadStyle(1);
      gANWEconomicDistanceMultiplier = 1.20;
      anwSetPreferredTerrain(cANWTerrainForestEdge, cANWTerrainRiver, 0.40);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.35);
   }
   else if (cMyCiv == cCivDEHausa)
   {
      // Muhammadu Kanta of Kebbi — Hausa Surame-fortress doctrine, riding
      // the trans-Saharan caravan lattice. (Engine key remains "usman" for
      // dispatch stability; lore is Kanta — see leader_usman.xs header.)
      anwUseDistributedEconomicNetworkStyle(2);
      gANWEconomicDistanceMultiplier = 1.30;
      anwSetPreferredTerrain(cANWTerrainDesertOasis, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.40);
   }
   else if (cMyCiv == cCivDEInca)
   {
      // Pachacuti — Sacsayhuamán terraced fortress.
      anwUseAndeanTerraceFortressStyle(4);
      // Spec override: Inca Pachacuti doctrine wants concentric FortressRing
      // walls (matching ANWInca/ANWChileans/ANWPeruvians). AndeanTerraceFortress
      // helper defaults to ChokepointSegments(1); explicit override required so
      // anwApplyBuildStyleForActiveCiv (called after initLeaderPachacuti) does
      // not silently revert the leader's explicit FortressRing choice.
      gANWWallStrategy = cANWWallStrategyFortressRing;
      gANWHouseDistanceMultiplier = 0.75;
      anwSetBuildStrongpointProfile(3, 3, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainPlain, 0.20);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivIndians)
   {
      // Shivaji — Maratha hill-fort citadel doctrine. HTML reference promises
      // Highland Citadel (gad-fort network on the Sahyadri spurs), not Shrine
      // Trade Node; the Sacred Field economy is preserved via the strongpoint
      // profile and heading bias below.
      anwUseHighlandCitadelStyle(5);
      anwEnableEarlyForwardBase(360000);
      gANWEconomicDistanceMultiplier = 1.10;
      anwSetBuildStrongpointProfile(2, 1, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainJungle, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
   }
   else if (cMyCiv == cCivDEItalians)
   {
      // Garibaldi — Risorgimento volunteer Redshirts marching north.
      // earlyWalls=true to honour spec first_wall_before_ms=900000 (audit v2 WARN parity with Frederick).
      anwUseRepublicanLeveeStyle(2, true);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainRiver, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
   }
   else if (cMyCiv == cCivJapanese)
   {
      // Tokugawa — Sankin-kōtai shrine network and castle towns, coast + river.
      anwUseShrineTradeNodeSpreadStyle(3);
      gANWEconomicDistanceMultiplier = 1.25;
      anwSetBuildStrongpointProfile(2, 2, 1, false);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainRiver, 0.45);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.30);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivXPSioux)
   {
      // Chief Gall — Lakota wedge, plains horse archers, buffalo hunt mobility.
      anwUseSteppeCavalryWedgeStyle(0);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.15);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.50);
   }
   else if (cMyCiv == cCivDEMaltese)
   {
      // Jean de Valette — Hospitaller fortress of Birgu and Senglea, 1565 siege.
      anwUseHighlandCitadelStyle(5);
      anwSetBuildStrongpointProfile(4, 3, 2, false);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainHighland, 0.35);
      anwSetExpansionHeading(cANWHeadingDefensive, 0.0);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivDEMexicans)
   {
      // Hidalgo (standard) — Insurgent town-civic militia across the Bajío.
      anwUseRepublicanLeveeStyle(1);
      gANWEconomicDistanceMultiplier = 1.15;
      anwSetBuildStrongpointProfile(2, 1, 2, false);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainDesertOasis, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.35);
   }
   else if (cMyCiv == cCivOttomans)
   {
      // Suleiman the Magnificent — Ottoman siege at Vienna and Rhodes.
      anwUseSiegeTrainConcentrationStyle(3);
      gANWEconomicDistanceMultiplier = 1.05;
      anwSetBuildStrongpointProfile(2, 2, 2, true);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainCoast, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivPortuguese)
   {
      // Henry the Navigator — Carrack-and-feitoria Atlantic mercantile network.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.30;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainRiver, 0.60);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.50);
   }
   else if (cMyCiv == cCivRussians)
   {
      // Ivan the Terrible — Streltsy corps, Kazan/Astrakhan siege, Volga push.
      anwUseCossackVoiskoStyle(1);
      gANWWallStrategy = cANWWallStrategyFrontierPalisades;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainForestEdge, 0.35);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.40);
   }
   else if (cMyCiv == cCivSpanish)
   {
      // Isabella — Reconquista forward operational line, Iberian plain.
      anwUseForwardOperationalLineStyle(2);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainCoast, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (cMyCiv == cCivDESwedish)
   {
      // Gustavus Adolphus — Lion of the North. HTML reference promises Forward
      // Operational Line (the famous Swedish thin-line tercio + drive-the-front
      // assault), not Siege Train; mobile field artillery is still expressed via
      // gANWMilitaryDistanceMultiplier (0.85) and the FrontierPush heading.
      anwUseForwardOperationalLineStyle(1);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainForestEdge, 0.35);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
   }
   else if (cMyCiv == cCivDEAmericans)
   {
      // Washington (standard) — Continental Army republican compound, tidewater.
      anwUseRepublicanLeveeStyle(1);
      gANWTownCenterDistanceMultiplier = 1.10;
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainForestEdge, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.35);
   }

   // ── REVOLUTION NATIONS (26) — bespoke per-nation profiles ────────────
   else if (rvltName == "ANWAmericans")
   {
      // Jefferson — Continental Congress republican civic spine, tidewater farms.
      anwUseRepublicanLeveeStyle(0);
      gANWEconomicDistanceMultiplier = 1.05;
      gANWTownCenterDistanceMultiplier = 1.15;
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainForestEdge, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.35);
   }
   else if (rvltName == "ANWArgentines")
   {
      // San Martin — Army of the Andes liberation column across the pampas.
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(1, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainHighland, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWBajaCalifornians")
   {
      // Baja Californians — Mission scatter on a long Pacific peninsula.
      anwUseMobileFrontierScatterStyle(0);
      gANWHouseDistanceMultiplier = 1.40;
      gANWEconomicDistanceMultiplier = 1.50;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainDesertOasis, 0.45);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.50);
   }
   else if (rvltName == "ANWBarbary")
   {
      // Barbary — Corsair coastal compound, fortified harbour of Algiers/Tunis.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.20;
      anwSetBuildStrongpointProfile(2, 2, 2, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainDesertOasis, 0.55);
      anwSetExpansionHeading(cANWHeadingIslandHop, 0.40);
   }
   else if (rvltName == "ANWBrazil")
   {
      // Brazil — Empire of Pedro II, sugar economy across Mata Atlântica coast.
      anwUseDistributedEconomicNetworkStyle(2);
      gANWEconomicDistanceMultiplier = 1.35;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainJungle, 0.40);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.35);
   }
   else if (rvltName == "ANWCalifornians")
   {
      // Californians — Gold Rush boom across Sierra foothills & central valley.
      anwUseDistributedEconomicNetworkStyle(1);
      gANWHouseDistanceMultiplier = 1.15;
      gANWEconomicDistanceMultiplier = 1.40;
      anwSetBuildStrongpointProfile(2, 1, 1, false);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainHighland, 0.35);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.40);
   }
   else if (rvltName == "ANWCanadians")
   {
      // Canadians — Loyalist garrison along the St Lawrence / Great Lakes.
      anwUseCompactFortifiedCoreStyle(2, true);  // earlyWalls=true to meet spec first_wall_before_ms=600000.
      gANWEconomicDistanceMultiplier = 0.95;
      anwSetBuildStrongpointProfile(2, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainForestEdge, 0.40);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.35);
   }
   else if (rvltName == "ANWCentralAmericans")
   {
      // Morazán — Federal Republic of Central America trade league on isthmus.
      anwUseDistributedEconomicNetworkStyle(1);
      gANWEconomicDistanceMultiplier = 1.25;
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainCoast, 0.30);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.35);
   }
   else if (rvltName == "ANWChileans")
   {
      // O'Higgins — Andean column on the Pacific coast.
      anwUseAndeanTerraceFortressStyle(2);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainCoast, 0.35);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.30);
   }
   else if (rvltName == "ANWColumbians")
   {
      // Bolívar — Gran Colombia liberation drive across Andes and Llanos.
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(1, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainJungle, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWEgyptians")
   {
      // Muhammad Ali — Mameluke citadel of Cairo, Nile-anchored.
      anwUseHighlandCitadelStyle(4);
      gANWHouseDistanceMultiplier = 0.75;
      anwSetBuildStrongpointProfile(3, 3, 2, false);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainDesertOasis, 0.45);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.35);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWFinnish")
   {
      // Mannerheim — Winter War line across Karelian taiga.
      anwUseCompactFortifiedCoreStyle(3, true);
      gANWHouseDistanceMultiplier = 0.80;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainForestEdge, cANWTerrainWetland, 0.35);
      anwSetExpansionHeading(cANWHeadingDefensive, 0.0);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWHaitians")
   {
      // Toussaint / Dessalines — Haitian Revolution jungle ambush, mountain.
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWEconomicDistanceMultiplier = 1.40;
      gANWTownCenterDistanceMultiplier = 1.40;
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainHighland, 0.35);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
   }
   else if (rvltName == "ANWHungarians")
   {
      // Kossuth — Hungarian hussar wedge of the 1848 Honvéd across the puszta.
      anwUseSteppeCavalryWedgeStyle(1);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWIndonesians")
   {
      // Diponegoro — Java War jungle-guerrilla campaign (Perang Diponegoro,
      // 1825-1830). HTML reference promises Jungle Guerrilla Network, not
      // Shrine Trade; the pesantren-village character is still encoded in
      // gANWEconomicDistanceMultiplier (1.40) + IslandHop heading.
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWEconomicDistanceMultiplier = 1.40;
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainCoast, 0.40);
      anwSetExpansionHeading(cANWHeadingIslandHop, 0.35);
   }
   else if (rvltName == "ANWMayans")
   {
      // Caste War — Maya jungle guerrilla, Yucatán bush huts on limestone shelf.
      anwUseJungleGuerrillaNetworkStyle(1);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 2, true);
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainForestEdge, 0.40);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "ANWMexicans")
   {
      // Hidalgo (revolution) — Grito de Dolores citizen army across Bajío.
      anwUseRepublicanLeveeStyle(0);
      gANWEconomicDistanceMultiplier = 1.10;
      anwSetBuildStrongpointProfile(1, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainDesertOasis, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
   }
   else if (rvltName == "ANWRevFrance")
   {
      // Revolutionary France — Levée en masse of the Year II, Paris radiating.
      anwUseRepublicanLeveeStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(1, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainPlain, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "ANWNapoleonicFrance")
   {
      // Napoleon Bonaparte (post-1804 Emperor) — Grande Armée operational manoeuvre.
      anwUseForwardOperationalLineStyle(1);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.55);
   }
   else if (rvltName == "ANWPeruvians")
   {
      // Túpac Amaru — Andean terrace fortress above the altiplano.
      anwUseAndeanTerraceFortressStyle(3);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainPlain, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWRioGrande")
   {
      // Rio Grande — Republic-on-the-frontier ranching scatter, plains.
      anwUseMobileFrontierScatterStyle(0);
      gANWHouseDistanceMultiplier = 1.35;
      gANWTownCenterDistanceMultiplier = 1.50;
      anwSetBuildStrongpointProfile(1, 0, 2, false);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.35);
   }
   else if (rvltName == "ANWRomanians")
   {
      // Cuza — Romanian unification civic militia, Carpathian-Danube axis.
      anwUseCivicMilitiaCenterStyle(2);
      gANWEconomicDistanceMultiplier = 1.10;
      anwSetBuildStrongpointProfile(2, 1, 2, false);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainHighland, 0.30);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.25);
   }
   else if (rvltName == "ANWSouthAfricans")
   {
      // Boer Voortrekker — Laager-and-port colonial compound, Cape inland.
      anwUseNavalMercantileCompoundStyle(2);  // wallLevel=2 for full Boer laager / Cape harbor ring (was 1).
      gANWEconomicDistanceMultiplier = 1.25;
      anwSetBuildStrongpointProfile(2, 1, 2, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainPlain, 0.40);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.35);
   }
   else if (rvltName == "ANWTexians")
   {
      // Houston — Texan revolution forward line at San Jacinto across prairie.
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWYucatan")
   {
      // Yucatán — Caste War jungle guerrilla on the limestone peninsula.
      anwUseJungleGuerrillaNetworkStyle(1);
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 2, true);
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainCoast, 0.40);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
   }

   // ── ANW NATIONS (19) — bespoke per-civ profiles ───────────────────────
   else if (rvltName == "ANWArgentines")
   {
      // San Martín — Army of the Andes liberation column across the pampas.
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(1, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainHighland, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWBarbary")
   {
      // Barbary — Corsair coastal compound, fortified harbour of Algiers/Tunis.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.20;
      anwSetBuildStrongpointProfile(2, 2, 2, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainDesertOasis, 0.55);
      anwSetExpansionHeading(cANWHeadingIslandHop, 0.40);
   }
   else if (rvltName == "ANWBrazil")
   {
      // Brazil — Empire of Pedro II, sugar economy across Mata Atlântica coast.
      anwUseDistributedEconomicNetworkStyle(2);
      gANWEconomicDistanceMultiplier = 1.35;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainJungle, 0.40);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.35);
   }
   else if (rvltName == "ANWCanadians")
   {
      // Canadians — Loyalist garrison along the St Lawrence / Great Lakes.
      anwUseCompactFortifiedCoreStyle(2, true);  // earlyWalls=true to meet spec first_wall_before_ms=600000.
      gANWEconomicDistanceMultiplier = 0.95;
      anwSetBuildStrongpointProfile(2, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainForestEdge, 0.40);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.35);
   }
   else if (rvltName == "ANWChileans")
   {
      // O'Higgins — Andean column on the Pacific coast.
      anwUseAndeanTerraceFortressStyle(2);
      gANWWallStrategy = cANWWallStrategyFortressRing;
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainCoast, 0.35);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.30);
   }
   else if (rvltName == "ANWColumbians")
   {
      // Bolívar — Gran Colombia liberation drive across Andes and Llanos.
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(1, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainJungle, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWEgyptians")
   {
      // Muhammad Ali — Mameluke citadel of Cairo, Nile-anchored.
      anwUseHighlandCitadelStyle(4);
      gANWHouseDistanceMultiplier = 0.75;
      anwSetBuildStrongpointProfile(3, 3, 2, false);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainDesertOasis, 0.45);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.35);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWFinnish")
   {
      // Mannerheim — Winter War line across Karelian taiga.
      anwUseCompactFortifiedCoreStyle(3, true);
      gANWHouseDistanceMultiplier = 0.80;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainForestEdge, cANWTerrainWetland, 0.35);
      anwSetExpansionHeading(cANWHeadingDefensive, 0.0);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWHaitians")
   {
      // Toussaint / Dessalines — Haitian Revolution jungle ambush, mountain.
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWEconomicDistanceMultiplier = 1.40;
      gANWTownCenterDistanceMultiplier = 1.40;
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainHighland, 0.35);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
      // spec: wall_strategy = ChokepointSegments — jungle terrain confines walls
      // to natural pinch points rather than the open-field sweep MobileNoWalls implies.
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
   }
   else if (rvltName == "ANWHungarians")
   {
      // Kossuth — Hungarian hussar wedge of the 1848 Honvéd across the puszta.
      anwUseSteppeCavalryWedgeStyle(1);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWIndonesians")
   {
      // Diponegoro — Java War jungle-guerrilla campaign across the archipelago.
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
      gANWEconomicDistanceMultiplier = 1.40;
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainCoast, 0.40);
      anwSetExpansionHeading(cANWHeadingIslandHop, 0.35);
   }
   else if (rvltName == "ANWMayans")
   {
      // Caste War — Maya jungle guerrilla, Yucatán bush huts on limestone shelf.
      anwUseJungleGuerrillaNetworkStyle(1);
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 2, true);
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainForestEdge, 0.40);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "ANWMexicans")
   {
      // Hidalgo — Insurgent town-civic militia across the Bajío.
      anwUseRepublicanLeveeStyle(0);
      gANWEconomicDistanceMultiplier = 1.10;
      anwSetBuildStrongpointProfile(1, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainDesertOasis, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
   }
   else if (rvltName == "ANWNapoleonicFrance")
   {
      // Napoleon Bonaparte — Grande Armée operational manoeuvre, rivers and plains.
      anwUseForwardOperationalLineStyle(1);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.55);
   }
   else if (rvltName == "ANWPeruvians")
   {
      // Túpac Amaru / Santa Cruz — Andean terrace fortress above the altiplano.
      anwUseAndeanTerraceFortressStyle(3);
      gANWWallStrategy = cANWWallStrategyFortressRing;
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainPlain, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWRevFrance")
   {
      // Robespierre — Levée en masse of the Year II, Paris-radiating republican line.
      anwUseRepublicanLeveeStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(1, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainPlain, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
   }
   else if (rvltName == "ANWRomanians")
   {
      // Cuza — Romanian unification civic militia, Carpathian-Danube axis.
      anwUseCivicMilitiaCenterStyle(2);
      gANWForwardBaseEarliestMs = 1200000;
      gANWEconomicDistanceMultiplier = 1.10;
      anwSetBuildStrongpointProfile(2, 1, 2, false);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainHighland, 0.30);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.25);
   }
   else if (rvltName == "ANWSouthAfricans")
   {
      // Boer Voortrekker — Laager-and-port colonial compound, Cape inland.
      anwUseNavalMercantileCompoundStyle(2);  // wallLevel=2 for full Boer laager / Cape harbor ring (was 1).
      gANWEconomicDistanceMultiplier = 1.25;
      anwSetBuildStrongpointProfile(2, 1, 2, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainPlain, 0.40);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.35);
      // spec: wall_strategy = CoastalBatteries — harbour-anchored laager with
      // gun towers at the waterline; explicit override keeps the probe in sync
      // when probe data pre-dates this branch.
      gANWWallStrategy = cANWWallStrategyCoastalBatteries;
   }
   else if (rvltName == "ANWTexians")
   {
      // Sam Houston — Texan revolution forward line at San Jacinto across prairie.
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }

   // ── ANW CANONICAL NATIONS (21) — mirror parent-civ build profiles ────────
   // kbGetCivName(cMyCiv) returns "ANWBritish" etc. for these mod-added civs;
   // cMyCiv does NOT equal any cCivXxx constant, so they cannot match above.
   else if (rvltName == "ANWAztecs")
   {
      // Montezuma — Flower War tribute aggression. Hidden war huts, no perimeter.
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
      gANWHouseDistanceMultiplier = 0.85;
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainWetland, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.20);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWBritish")
   {
      // Elizabeth I — Tudor naval, Sea Dogs, coastal Manor economy.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.30;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainPlain, 0.55);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.45);
   }
   else if (rvltName == "ANWChinese")
   {
      // Kangxi — High-walled Forbidden City. Compact, multi-ring fortress.
      anwUseCompactFortifiedCoreStyle(4, true);
      gANWHouseDistanceMultiplier = 0.70;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWDutch")
   {
      // Maurice of Nassau — Dutch trade republic. Bank-and-dock spine.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.40;
      gANWHouseDistanceMultiplier = 1.05;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainWetland, 0.60);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.40);
   }
   else if (rvltName == "ANWEthiopians")
   {
      // Menelik II — Highland citadel of Entoto / Magdala.
      anwUseHighlandCitadelStyle(3);
      gANWHouseDistanceMultiplier = 0.80;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingDefensive, 0.0);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWFrench")
   {
      // Louis XVIII Bourbon — compact fortified core, Restoration defensive posture.
      // wallLevel=3 matches leader_bourbon.xs (single source of truth).
      anwUseCompactFortifiedCoreStyle(3, true);
      gANWWallStrategy = cANWWallStrategyFortressRing;
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.55);
   }
   else if (rvltName == "ANWGermans")
   {
      // Frederick the Great — Prussian republican-levee + oblique-order march.
      // earlyWalls=true honours spec first_wall_before_ms=900000.
      anwUseRepublicanLeveeStyle(2, true);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 2, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
   }
   else if (rvltName == "ANWHaudenosaunee")
   {
      // Hiawatha — Confederation longhouse and trade. Woodland + Great Lakes.
      anwUseShrineTradeNodeSpreadStyle(1);
      gANWEconomicDistanceMultiplier = 1.20;
      anwSetPreferredTerrain(cANWTerrainForestEdge, cANWTerrainRiver, 0.40);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.35);
   }
   else if (rvltName == "ANWHausa")
   {
      // Muhammadu Kanta — Hausa Surame-fortress, trans-Saharan caravan lattice.
      anwUseDistributedEconomicNetworkStyle(2);
      gANWEconomicDistanceMultiplier = 1.30;
      anwSetPreferredTerrain(cANWTerrainDesertOasis, cANWTerrainRiver, 0.25);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.40);
   }
   else if (rvltName == "ANWInca")
   {
      // Pachacuti — Sacsayhuamán terraced fortress.
      anwUseAndeanTerraceFortressStyle(4);
      gANWWallStrategy = cANWWallStrategyFortressRing;
      gANWHouseDistanceMultiplier = 0.75;
      anwSetBuildStrongpointProfile(3, 3, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainPlain, 0.20);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWIndians")
   {
      // Shivaji — Maratha hill-fort citadel, Sahyadri spur network.
      anwUseHighlandCitadelStyle(5);
      anwEnableEarlyForwardBase(360000);
      gANWEconomicDistanceMultiplier = 1.10;
      anwSetBuildStrongpointProfile(2, 1, 2, false);
      anwSetPreferredTerrain(cANWTerrainHighland, cANWTerrainJungle, 0.30);
      anwSetExpansionHeading(cANWHeadingOutwardRings, 0.15);
   }
   else if (rvltName == "ANWItalians")
   {
      // Garibaldi — Risorgimento volunteer Redshirts marching north.
      // earlyWalls=true honours spec first_wall_before_ms=900000.
      anwUseRepublicanLeveeStyle(2, true);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainRiver, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
   }
   else if (rvltName == "ANWJapanese")
   {
      // Tokugawa — Sankin-kōtai shrine network and castle towns.
      anwUseShrineTradeNodeSpreadStyle(3);
      gANWEconomicDistanceMultiplier = 1.25;
      anwSetBuildStrongpointProfile(2, 2, 1, false);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainRiver, 0.45);
      anwSetExpansionHeading(cANWHeadingFollowTradeRoute, 0.30);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWLakota")
   {
      // Chief Gall — Lakota wedge, plains horse archers, buffalo hunt mobility.
      anwUseSteppeCavalryWedgeStyle(0);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainRiver, 0.15);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.50);
   }
   else if (rvltName == "ANWMaltese")
   {
      // Jean de Valette — Hospitaller fortress of Birgu and Senglea, 1565 siege.
      anwUseHighlandCitadelStyle(5);
      anwSetBuildStrongpointProfile(4, 3, 2, false);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainHighland, 0.35);
      anwSetExpansionHeading(cANWHeadingDefensive, 0.0);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWOttomans")
   {
      // Suleiman the Magnificent — Ottoman siege at Vienna and Rhodes.
      anwUseSiegeTrainConcentrationStyle(3);
      gANWEconomicDistanceMultiplier = 1.05;
      anwSetBuildStrongpointProfile(2, 2, 2, true);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainCoast, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWPortuguese")
   {
      // Henry the Navigator — Carrack-and-feitoria Atlantic mercantile network.
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.30;
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainRiver, 0.60);
      anwSetExpansionHeading(cANWHeadingAlongCoast, 0.50);
   }
   else if (rvltName == "ANWRussians")
   {
      // Ivan the Terrible / Catherine — Streltsy corps, Kazan/Astrakhan siege.
      anwUseCossackVoiskoStyle(1);
      gANWWallStrategy = cANWWallStrategyFrontierPalisades;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainForestEdge, 0.35);
      anwSetExpansionHeading(cANWHeadingUpriver, 0.40);
   }
   else if (rvltName == "ANWSpanish")
   {
      // Isabella — Reconquista forward operational line, Iberian plain.
      anwUseForwardOperationalLineStyle(2);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainPlain, cANWTerrainCoast, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.45);
      anwEnableCenterAnchoredCivic(true);
   }
   else if (rvltName == "ANWSwedes")
   {
      // Gustavus Adolphus — Lion of the North, Swedish thin-line tercio.
      anwUseForwardOperationalLineStyle(1);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(2, 2, 3, true);
      anwSetPreferredTerrain(cANWTerrainCoast, cANWTerrainForestEdge, 0.35);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.40);
   }
   else if (rvltName == "ANWUSA")
   {
      // Washington — Continental Army republican compound, tidewater.
      anwUseRepublicanLeveeStyle(1);
      gANWTownCenterDistanceMultiplier = 1.10;
      anwSetPreferredTerrain(cANWTerrainRiver, cANWTerrainForestEdge, 0.30);
      anwSetExpansionHeading(cANWHeadingFrontierPush, 0.35);
   }

   anwLogEvent("BUILDSTYLE", kbGetCivName(cMyCiv) + " -> " + anwGetBuildStyleName(gANWBuildStyle) +
      " walls=" + gANWWallLevel + " earlyWalls=" + gANWEarlyWallingEnabled +
      " house=" + gANWHouseDistanceMultiplier + " eco=" + gANWEconomicDistanceMultiplier +
      " mil=" + gANWMilitaryDistanceMultiplier + " tc=" + gANWTownCenterDistanceMultiplier +
      " towerLevel=" + gANWTowerLevel + " fortLevel=" + gANWFortLevel +
      " forwardBaseTowers=" + gANWForwardBaseTowerCount + " forwardFortified=" + gANWPreferForwardFortifiedBase +
      " terrainPrimary=" + gANWPreferredTerrainPrimary + " terrainSecondary=" + gANWPreferredTerrainSecondary +
      " heading=" + gANWExpansionHeading + " terrainBias=" + gANWTerrainBiasStrength +
      " headingBias=" + gANWHeadingBiasStrength + " civicAnchor=" + gANWCenterAnchorCivic);

   // Replay probe: structured snapshot of the resolved build profile. Same
   // information as the BUILDSTYLE event log, but in the v=2 schema so the
   // post-match validator can tokenise it without parsing free-form text.
   anwProbe("meta.buildstyle",
      "style=" + gANWBuildStyle +
      " walls=" + gANWWallLevel +
      " terrain_primary=" + gANWPreferredTerrainPrimary +
      " terrain_secondary=" + gANWPreferredTerrainSecondary +
      " terrain_bias=" + gANWTerrainBiasStrength +
      " heading=" + gANWExpansionHeading +
      " heading_bias=" + gANWHeadingBiasStrength +
      " civic_anchor=" + gANWCenterAnchorCivic);
}
