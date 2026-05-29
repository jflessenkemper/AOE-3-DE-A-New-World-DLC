//==============================================================================
/* aiCore.xs

   This file includes all other files in the core folder, and will be included
   by aiMain.xs.

   This file also contains functions and rules that don't belong to other files.

*/
//==============================================================================

//==============================================================================
// Function forward declarations.
//==============================================================================
// Used in loader file to override default values, called at start of main().
mutable void preInit(void) {}

// Used in loader file to override initialization decisions, called at end of main().
mutable void postInit(void) {}

// Utilities.
mutable vector getStartingLocation(void) { return (kbGetPlayerStartingPosition(cMyID)); }

// Buildings.
mutable void selectTowerBuildPlanPosition(int buildPlan = -1, int baseID = -1) {}
mutable void selectShrineBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectTorpBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectTCBuildPlanPosition(int buildPlan = -1, int baseID = -1) {}
mutable void selectTeepeeBuildPlanPosition(int buildPlan = -1, int baseID = -1) {}
mutable bool selectTribalMarketplaceBuildPlanPosition(int buildPlan = -1, int baseID = -1) { return (false); }
mutable bool selectFieldBuildPlanPosition(int planID = -1, int baseID = -1) { return (false); }
mutable void selectMountainMonasteryBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectGranaryBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectClosestBuildPlanPosition(int planID = -1, int baseID = -1, int puid = -1) {}
mutable bool selectBuildPlanPosition(int planID = -1, int puid = -1, int baseID = -1) { return (false); }
mutable bool addBuilderToPlan(int planID = -1, int puid = -1, int numberBuilders = 1) { return (false); }

// Economy.
mutable void econMaster(int mode = -1, int value = -1) {}

// Military.
mutable int initUnitPicker(string name = "BUG", int numberTypes = 1, int minUnits = 10, int maxUnits = 20,
   int minPop = -1, int maxPop = -1, int numberBuildings = 1, bool guessEnemyUnitType = false)
{
   return (-1);
}
mutable void setUnitPickerCommon(int upID = -1) {}
mutable void setUnitPickerPreference(int upID = -1) {}
mutable void endDefenseReflex(void) {}
mutable void addUnitsToMilitaryPlan(int planID = -1) {}
mutable float getMilitaryUnitStrength(int puid = -1) { return (0.0); }
mutable bool llIsCommanderAvailableForMajorAttack(void) { return (true); }
mutable void llCancelCommanderlessMajorAttacks(void) {}
mutable bool llEnsureCommanderRecovery(void) { return (false); }
mutable void llDestroyCommanderRecoveryPlan(void) {}

// Home City cards.
mutable void shipGrantedHandler(int parm = -1) {}

// Chats.
mutable void sendStatement(int playerIDorRelation = -1, int commPromptID = -1, vector vec = cInvalidVector) {}
mutable void sendChatLine(int playerIDorRelation = -1, string message = "") {}
mutable string llGetLegendaryLeaderInsult(void) { return (""); }
mutable string llGetLegendaryLeaderCompliment(void) { return (""); }
mutable void llSendLegendaryLeaderInsultLine(int playerIDorRelation = -1, int quoteInterval = 90000) {}
mutable void llSendLegendaryLeaderComplimentLine(int playerIDorRelation = -1, int quoteInterval = 90000) {}
mutable void llMaybeFollowStatementWithQuote(int playerID = -1, int commPromptID = -1) {}
mutable void enableLegendaryLeaderQuoteRules(void) {}

// Setup.
mutable void deathMatchStartupBegin(void) {}
mutable void initCeylonNomadStart(void) {}
mutable void init(void) {}
mutable int llGetWantedFortCount(void) { return (0); }

// Core.
mutable void updateSettlersAndPopManager() {}
mutable void transportShipmentArrive(int techID = -1) {}
mutable void revoltedHandler(int techID = -1) {}

//==============================================================================
// Includes.
//==============================================================================
include "core\aiGlobals.xs";
include "core\aiUtilities.xs";
include "core\aiUtilitiesNew.xs";
include "core\aiNavalUtilities.xs";
include "core\aiBuildings.xs";
include "core\aiTechs.xs";
include "core\aiExploration.xs";
include "core\aiEconomyNew.xs";
include "core\aiEconomy.xs";
include "core\aiLeaderQuotes.xs";
include "core\aiMilitaryNew.xs";
include "core\aiMilitary.xs";
include "core\aiHCCards.xs";
include "core\aiChats.xs";
include "core\aiSetup.xs";

// Ehanced Includes
//include "core\aiUtilitiesNew.xs"; // This was moved above for functionality reasons...
//include "core\aiNavalUtilities.xs";
//include "core\aiEconomyNew.xs";
//include "core\aiMilitaryNew.xs";
include "core\aiBuildingsWalls.xs";
include "core\aiDoctrineProbes.xs";
include "core\aiChatsNew.xs";
include "core\aiEliteTactics.xs";
include "core\aiMiscNew.xs";
include "core\aiNavalVillagersUtilities.xs";
include "core\aiNavalVillagers.xs";
include "core\aiNavalInvasion.xs"; // For splitting up the invasion code...
include "core\aiNavalNew.xs";
include "core\aiArchipelago.xs";
include "core\aiSpecialNew.xs"; // For special scenario-related code...
include "core\aiKingOfTheHill.xs";

//==============================================================================
// updateSettlerCounts
// Set the Settler maintain plan using the gTargetSettlerCounts array.
//==============================================================================
void updateSettlerCounts(void)
{
   int age = kbGetAge();

   // Go through all ages later than we are currently at, update our settler count to that age if the first player is already 5 minutes in.
   for (i = age + 1; i <= cAge5; i++)
   {
      if (xsArrayGetInt(gFirstAgeTime, i) + 5 * 60 * 1000 >= xsGetTime())
      {
         break;
      }
      age += 1;
      debugCore("Updating settler count to limit at age "+age+" because we are behind for too long");
   }

   bool autoSpawningSettlers = ((cMyCiv == cCivOttomans) && (gRevolutionType == 0)) ||
                               (kbTechGetStatus(cTechDEHCFedGoldRush) == cTechStatusActive);
   int wantedSettlersThisAge = xsArrayGetInt(gTargetSettlerCounts, age);

   // If we're capped at the current age train our full complement of Settlers.
   // This is only here for if cvMaxAge is set to the Commerce Age basically.
   if (age == cvMaxAge)
   {
      wantedSettlersThisAge = xsArrayGetInt(gTargetSettlerCounts, cAge5);
   }

   if (autoSpawningSettlers == true)
   {
      debugCore("Economy" + kbGetProtoUnitName(gEconUnit) + "Maintain plan is set to 0 since we're automatically spawning");
      debugCore("We will stop spawning at " + wantedSettlersThisAge + " " + kbGetProtoUnitName(gEconUnit));
      // We need to null out the settler maintain plan for auto spawning civs.
      aiPlanSetVariableInt(gSettlerMaintainPlan, cTrainPlanNumberToMaintain, 0, 0);
   }
   else
   {
      // Prevent the AI from filling its population with settlers...
      if (wantedSettlersThisAge > 80) {
         wantedSettlersThisAge = 80;
      }
      debugCore("Adjusting Economy" + kbGetProtoUnitName(gEconUnit) + "Maintain plan to: " +
         wantedSettlersThisAge + " " + kbGetProtoUnitName(gEconUnit));
      aiPlanSetVariableInt(gSettlerMaintainPlan, cTrainPlanNumberToMaintain, 0, wantedSettlersThisAge);
   }
   aiSetEconomyPop(wantedSettlersThisAge);

   if (kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) >= (wantedSettlersThisAge * 0.8))
   {
      aiPlanSetDesiredResourcePriority(gSettlerMaintainPlan, 50);
   }
   else
   {
      aiPlanSetDesiredResourcePriority(gSettlerMaintainPlan, 70);
   }
}

//==============================================================================
/* accountForOutlawsMilitaryPop
   Outlaws take a lot of pop space and this can be an issue.
   Let's say we have 40 military pop which normally gives us about 20 units.
   But if we made Outlaws that gives us about 10 units which is too few.
   So in this rule we increase our military population if we have Outlaws to account for this.
*/
//==============================================================================
rule accountForOutlawsMilitaryPop
inactive
minInterval 30
{
   int militaryPopLimit = aiGetMilitaryPop();
   // We've reached maximum military pop so we can't increase it.
   if (gMaxPop - xsArrayGetInt(gTargetSettlerCounts, cAge5) == militaryPopLimit)
   {
      xsDisableSelf();
      return;
   }

   int outlawQuery = createSimpleUnitQuery(cUnitTypeAbstractOutlaw, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(outlawQuery);
   // Compensate for the additional pop Outlaws used.
   if (numberFound > 0)
   {
      int puid = -1;
      int unitID = -1;
      float totalAdditionalPop = 0.0;
      float additionalPop = 0.0;
      float buildBounty = 0.0;
      float puidPopCount = 0.0;

      for (i = 0; < numberFound)
      {
         unitID = kbUnitQueryGetResult(outlawQuery, i);
         puid = kbUnitGetProtoUnitID(unitID);
         buildBounty = kbProtoUnitGetBuildBounty(puid);
         puidPopCount = kbGetProtoUnitPopCount(puid);
         additionalPop = puidPopCount - (buildBounty / 10.0);
         if (additionalPop > 0.0) // Don't do anything if negative because we would just lower our max army pop for no reason.
         {
            totalAdditionalPop += additionalPop;
         }
      }
      int newMilitaryPopLimit = militaryPopLimit + totalAdditionalPop;
      if (((cvMaxArmyPop > -1) && (newMilitaryPopLimit > cvMaxArmyPop)) || (aiGetEconomyPop() + newMilitaryPopLimit > gMaxPop))
      {
         return;
      }

      aiSetMilitaryPop(newMilitaryPopLimit);
      debugCore("Adjusting our military pop limit from " + militaryPopLimit + " to " +
         newMilitaryPopLimit + " because of the " + numberFound + " Outlaws found");
   }
   else
   {
      debugCore("No Outlaws found to take into account");
   }
}

//==============================================================================
// setMilPopLimit
// Calculates how many military population we want in the current age.
//==============================================================================
void setMilPopLimit(int age1Limit = 10, int age2Limit = 30, int age3Limit = 130,
                    int age4Limit = 130, int age5Limit = 130)
{
   int age = kbGetAge();
   // We use treatyCheckStartMakingArmy to call setMilPopLimit when it's time to make army.
   // We start making army in treaty 10 minutes before the treaty ends.
   if (aiTreatyGetEnd() > xsGetTime() + 10 * 60 * 1000)
   {
      aiSetMilitaryPop(0);
      debugCore("Treaty is not yet 10 minutes away from being over so our military population is set to 0");
      return;
   }

   int militaryPopLimit = -1;
   if (age == cvMaxAge)
   {
      age = cAge5; // If we're at the highest allowed age, go for our full mil pop.
   }               // This is done so if we're capped at an age we can at least go full out.
   switch (age)
   {
   case cAge1:
   {
         militaryPopLimit = age1Limit;
      break;
   }
   case cAge2:
   {
         militaryPopLimit = age2Limit;
      break;
   }
   case cAge3:
   {
         militaryPopLimit = age3Limit;
      break;
   }
   case cAge4:
   {
         militaryPopLimit = age4Limit;
      break;
   }
   case cAge5:
   {
         militaryPopLimit = age5Limit;
      break;
   }
   }

   if ((cvMaxArmyPop > -1) && (militaryPopLimit > cvMaxArmyPop))
   // Our calculated militaryPopLimit is higher than our cvMaxArmyPop which is not allowed to happen.
   {
      militaryPopLimit = cvMaxArmyPop;
      debugCore("CV We've decided that: " + militaryPopLimit + " should be our military population for now");
   }
   else
   {
      debugCore("We've decided that: " + militaryPopLimit + " should be our military population for now");
   }
   // Set the military population to its maximum potential...
   // int spaceLeftForMilitary = kbGetPopCap() - aiGetEconomyPop();
   // militaryPopLimit = spaceLeftForMilitary;
   // llVerboseEcho("MilitaryPop:"+kbUnitCount(cMyID, cUnitTypeAbstractVillager, cUnitStateAlive)+"");
   aiSetMilitaryPop(militaryPopLimit);
}

//==============================================================================
// popManager
// Set population limits based on age, difficulty and control variable settings.
//==============================================================================
void popManager(bool revoltedMilitary = false, bool revoltedEconomic = false)
{
   int age = kbGetAge();
   int maxMil = -1;

   debugCore("gMaxPop: " + gMaxPop);
   // Easy, Typically 20 econ, 20 mil
   // Standard, Typically 35 econ, 35 mil.
   // Moderate, Typically 60 econ, 60 mil.
   // Hard / Hardest / Extreme Typically 99 econ, 101 mil.
   if (revoltedMilitary == true)
   {
      maxMil = gMaxPop;
      debugCore("We've revolted with a military revolt, use our full gMaxPop for military now");
   }
   else if (revoltedEconomic == true)
   { // We assume that all revolts are done in Industrial so we take cAge5.
     // If we let MX revolt we need to look at this again.
      maxMil = gMaxPop - xsArrayGetInt(gTargetSettlerCounts, cAge5);
      debugCore("We've revolted with an Economic revolt, using gTargetSettlerCounts cAge5 to determine our maxMil: " +
          xsArrayGetInt(gTargetSettlerCounts, cAge5));
   }
   else if (age == cvMaxAge)
   { // Make sure everybody gets their full military potential in the last age using their real wanted Settler counts.
      maxMil = gMaxPop - xsArrayGetInt(gTargetSettlerCounts, cAge5);
      debugCore("We're in the maximum age, using gTargetSettlerCounts cAge5 to determine our maxMil: " +
          xsArrayGetInt(gTargetSettlerCounts, cAge5));
   }
   else
   {
      maxMil = gMaxPop - xsArrayGetInt(gTargetSettlerCountsDefault, age);
      debugCore("We're not in the maximum age, using gTargetSettlerCountsDefault at index 'current age' to determine " + 
         "our maxMil: " + xsArrayGetInt(gTargetSettlerCountsDefault, age));
   }

   debugCore("Maximum potential Military: " + maxMil + ", this may be reduced because of Age restrictions");

   // Limit the amount of military units we train if we haven't reached the minimum age we want.
   // If the max age was set below Industrial the function setMilPopLimit will take care of it and assign us the our full
   // military potential anyway.
   if (cDifficultyCurrent >= cDifficultyHard) // Enhanced - Lowered from Expert...
   {
      if (btRushBoom <= -0.5) // Fast Industrial which means lower army pop in Commerce / Fortress.
      {
         setMilPopLimit(maxMil / 6, maxMil / 6, maxMil / 6, maxMil, maxMil);
      }
      else if (btRushBoom <= 0.0) // Fast Fortress which means lower army pop in Commerce.
      {
         setMilPopLimit(maxMil / 6, maxMil / 6, maxMil / 2, maxMil, maxMil);
      }
      else // Stay longer in Commerce so higher army pop there.
      {
         setMilPopLimit(maxMil / 6, maxMil / 2, maxMil / 2, maxMil, maxMil);
      }
   }
   else // On lower difficulties we just ignore the bt settings altogether.
   {
      setMilPopLimit(maxMil / 6, maxMil / 3, maxMil / 2, maxMil, maxMil); 
   }

   gGoodArmyPop = aiGetMilitaryPop() / 3; // Used inside of the defense reflex system.
}

//==============================================================================
// updateSettlersAndPopManager
// Something happened in the game that forces us to update our Settler logic, like age ups.
// In this func we analyse the state of the game and based on that decide how to update everything.
//==============================================================================
void updateSettlersAndPopManager()
{
   // Handle the revolutions first then regular play.
   if ((gRevolutionType & cRevolutionMilitary) != 0)
   {
      popManager(true); // Tell the pop manager we don't need Settlers anymore and go full military.
                        // Our Settler maintain plan is already nulled out at this point.
      return;
   }
   if ((gRevolutionType & cRevolutionEconomic) != 0)
   { // We have revolted with an economic revolution or we sent a card to enable Settlers again, restore our Settler maintain
     // stuff.
      for (i = cAge1; <= cvMaxAge)
      {
         xsArraySetInt(gTargetSettlerCounts, i, xsArrayGetInt(gTargetSettlerCountsDefault, i));
      }
      // We have restored our array back to our default values but if our newly obtained gEconUnit has a lower bl than we saved
      // in our default array we need to adapt. For example the Dutch have >50 in their default array in cAge5 while their now
      // obtained Settler will have a 50 BL again. Also let's take our cvMaxCivPop into account here again because the array we
      // just took our values from hasn't been adjusted with those (intended).
      int buildLimit = kbGetBuildLimit(cMyID, gEconUnit);
      for (i = cAge1; <= cvMaxAge)
      {
         if (cvMaxCivPop > -1)
         {
            if (xsArrayGetInt(gTargetSettlerCounts, i) > cvMaxCivPop)
            {
               xsArraySetInt(gTargetSettlerCounts, i, cvMaxCivPop);
            }
         }
         if (xsArrayGetInt(gTargetSettlerCounts, i) > buildLimit)
         {
            xsArraySetInt(gTargetSettlerCounts, i, buildLimit);
         }
      }
      updateSettlerCounts();
      popManager(false, true);
      return;
   }

   // On easy we never increase the amount of Settlers we want so don't need to update it either.
   if (cDifficultyCurrent != cDifficultySandbox)
   {
      updateSettlerCounts();
   }
   popManager();
}

//==============================================================================
// treatyCheckStartMakingArmy
// We need to call popManager once when the treaty is 10 minutes away from being over so we can set a valid military pop.
// The minInterval number set here is not used but is overwritten in townCenterComplete.
//==============================================================================
rule treatyCheckStartMakingArmy
inactive
minInterval 30
{
   popManager();
   xsDisableSelf();
}

//==============================================================================
// toggleSpawning
// Used in toggleAutomaticSettlerSpawning to actually toggle the spawning.
//==============================================================================
void toggleSpawning(bool shouldSpawn = false)
{
   int queryID = createSimpleUnitQuery(cUnitTypeAgeUpBuilding);
   int numberResults = kbUnitQueryExecute(queryID);
   int townCenterID = -1;
   int numActions = -1;
   if (numberResults < 0)
   {
      return;
   }

   for (i = 0; < numberResults)
   {
      townCenterID = kbUnitQueryGetResult(queryID, i);
      numActions = kbUnitGetNumberActions(townCenterID);
      for (j = 0; < numActions)
      {
         if (kbUnitGetActionTypeByIndex(townCenterID, j) == cActionTypeMaintain)
         {
            if (kbUnitGetActionPausedByIndex(townCenterID, j) == true) // Paused.
            {
               // We want to spawn and this Town Center is not spawning so toggle it.
               if (shouldSpawn == true)
               {
                  aiTaskUnitCancel(townCenterID, kbUnitGetActionIDByIndex(townCenterID, j));
               }
            }
            else // Unpaused.
            {
               if (shouldSpawn == false)
               {
                  // We don't want to spawn and this Town Center is spawning so toggle it.
                  aiTaskUnitCancel(townCenterID, kbUnitGetActionIDByIndex(townCenterID, j));
               }
            }
         }
      }
   }
}

//==============================================================================
/* toggleAutomaticSettlerSpawning
   The mechanic where Town Centers automatically spawn Settlers completely ignores aiSetEconomyPop().
   Thus Ottomans and USA with Gold Rush card completely ignore the Settler limits sets for them and just keep spawning.
   This rule keeps checking if we're at our maximum allowed Settlers and
   depending on the result turns the spawning off / on.
*/
//==============================================================================
rule toggleAutomaticSettlerSpawning
inactive
minInterval 30
{
   int wantedExtraSettlers = getSettlerShortfall();
   // We want more economic units than we have now, turn spawning on.
   if (wantedExtraSettlers > 0)
   {
      debugCore("We want more economic units than we have, turn spawning on");
      toggleSpawning(true);
   }
   // We want as much or less economic units than we have now, turn spawning off.
   else if (wantedExtraSettlers <= 0)
   {
      debugCore("We want as much or less economic units than we have, turn spawning off");
      toggleSpawning(false);
   }
}

//==============================================================================
// transportShipmentArrive()
// This is an event handler that gets called each time a HC shipment arrives.
//==============================================================================
void transportShipmentArrive(int techID = -1)
{
   debugCore("We've received a shipment with the name: " + kbGetTechName(techID));
   switch (techID)
   {
   case cTechDEHCREVDhimma:
   case cTechDEHCREVCitizenship:
   case cTechDEHCREVCitizenshipOutpost:
   case cTechDEHCREVMinasGerais:
   case cTechDEHCREVSalitrera:
   case cTechDEHCREVAcehExports:
   {
      cvOkToGatherFood = true;
      cvOkToGatherWood = true;
      cvOkToGatherGold = true;
      gRevolutionType = cRevolutionEconomic;
      gEconUnit = cUnitTypeSettler;
      if (gFishingBoatMaintainPlan > 0)
      {
         xsEnableRule("fishManager");
      }
      updateSettlersAndPopManager();
      break;
   }
   case cTechDEHCREVNothernWilderness:
   {
      cvOkToGatherFood = true;
      cvOkToGatherGold = true;
      break;
   }
   case cTechHCBanks1:
   case cTechHCBanks2: // These cards increases our Settler build limit by 5.
   {
      for (i = cAge1; <= cvMaxAge)
      {
         xsArraySetInt(gTargetSettlerCounts, i, xsArrayGetInt(gTargetSettlerCounts, i) + 5);
      }
      updateSettlersAndPopManager();
      break;
   }
   case cTechDEHCFedGoldRush: // USA Federal card that turns their Settler spawning into the Ottoman mechanic.
   {
      updateSettlersAndPopManager();
      // It only makes sense to enable this spawning tracker if we're not allowed to reach the build limit of our gEconUnit.
      int comparisonDifficulty = gSPC == true ? cDifficultyExpert : cDifficultyHard;
      if ((cDifficultyCurrent < comparisonDifficulty) || (cvMaxCivPop > -1))
      {
            debugCore("Turning on Rule 'toggleAutomaticSettlerSpawning' because we sent the Gold Rush card" +
            " and still have build limits to take into account");
         xsEnableRule("toggleAutomaticSettlerSpawning");
      }
      break;
   }
   case cTechHCGermantownFarmers:
   {
         createSimpleMaintainPlan(cUnitTypeSettlerWagon, kbGetBuildLimit(cMyID, cUnitTypeSettlerWagon), true,
            kbBaseGetMainID(cMyID), 1);
      break;
   }
   case cTechHCXPNewWaysSioux:    // Lakota New Ways card.
   case cTechHCXPNewWaysIroquois: // Haudenosaunee New Ways card.
   {
      xsEnableRule("arsenalUpgradeMonitor");
      break;
   }
   case cTechHCAdvancedArsenalGerman:
   case cTechHCAdvancedArsenal:
   {
      xsEnableRule("advancedArsenalUpgradeMonitor");
      xsEnableRule("ArsenalUpgradeMonitor"); // In case we get this card in Age2 we need to enable this rule now since otherwise
      break;                                 // it won't be enabled until Age 3.
   }
   case cTechHCUnlockFactory:
   case cTechHCRobberBarons:
   case cTechHCUnlockFactoryGerman:
   case cTechHCRobberBaronsGerman:
   case cTechHCXPIndustrialRevolution:
   case cTechHCXPIndustrialRevolutionGerman:
   case cTechDEHCREVUnlockFactory:
   case cTechDEHCREVIndustrialRevolution:
   case cTechDEHCREVRobberBarons:
   case cTechDEHCFedNewHampshireManufacturing:
   case cTechDEHCPorfiriato:
   case cTechDEHCREVMXRobberBarons2:
   case cTechDEHCREVMXUnlockFactory:
   case cTechDEHCREVMXCaliforniaRobberBarons:
   {
      if (cDifficultyCurrent >= cDifficultyHard)
      {
         if (xsIsRuleEnabled("factoryUpgradeMonitor") == false)
         {
            xsEnableRule("factoryUpgradeMonitor");
         }
         if (xsIsRuleEnabled("factoryTacticMonitor") == false)
         {
            xsEnableRule("factoryTacticMonitor");
         }
      }
      break;
   }
   case cTechDEHCFedBearFlagRevolt:
   {
      // US HC card which is a revolt but doesn't disable train villagers.
      revoltedHandler(techID);
      break;
   }
   case cTechHCUnlockFort:
   case cTechHCUnlockFortGerman:
   case cTechHCUnlockFortVauban:
   case cTechHCREVShipFortWagon:
   case cTechHCXPUnlockFort2:
   case cTechHCXPUnlockFort2German:
   case cTechDEHCREVShipFortWagonOutpost:
   case cTechDEHCKalmarCastle:
   case cTechDEHCImmigrantsRussian:
   case cTechDEHCFedPutnamEngineering:
   case cTechDEHCFedMXTriasFortifications:
   case cTechDEHCChapultepecCastle:
   case cTechDEHCREVMXShipFortWagon2:
   {
      forwardBaseManager(); // Make sure our Fort Wagons are handled.
      break;
   }
   }
}

//==============================================================================
/* Native Dance Monitor

   Manage the number of natives dancing, and the 'tactic' they're dancing for.

const int cTacticFertilityDance=12;   Faster training
const int cTacticGiftDance=13;         Faster XP trickle
const int cTacticCityDance=14;
const int cTacticWaterDance=15;       Increases navy HP/attack
const int cTacticAlarmDance=16;        Town defense...
const int cTacticFounderDance=17;      xpBuilder units - Iroquois
const int cTacticMorningWarsDance=18;
const int cTacticEarthMotherDance=19;
const int cTacticHealingDance=20;
const int cTacticFireDance=21;
const int cTacticWarDanceSong=22;
const int cTacticGarlandWarDance=23;
const int cTacticWarChiefDance=24;    new war chief
const int cTacticHolyDance=25;

*/
//==============================================================================
rule danceMonitor
inactive
minInterval 20
{
   static int lastTactic = -1;
   static int lastTacticTime = 0;
   static int danceTactics = -1;
   static int lastVillagerTime = 0;
   int time = xsGetTime();

   if (danceTactics < 0) // First run.
   {
      // Setup dance tactics we want to use.
      switch (cMyCiv)
      {
      case cCivXPAztec:
      {
         danceTactics = xsArrayCreateInt(7, -1, "Dance tactics");

         // Shared
         xsArraySetInt(danceTactics, 0, cTacticFertilityDance);
         xsArraySetInt(danceTactics, 1, cTacticGiftDance);
         xsArraySetInt(danceTactics, 2, cTacticAlarmDance);
         xsArraySetInt(danceTactics, 3, cTacticWarDance);

         xsArraySetInt(danceTactics, 4, cTacticWarChiefDanceAztec);
         xsArraySetInt(danceTactics, 5, cTacticHolyDanceAztec);
         xsArraySetInt(danceTactics, 6, cTacticGarlandWarDance);
         break;
      }
      case cCivXPIroquois:
      {
         danceTactics = xsArrayCreateInt(5, -1, "Dance tactics");

         // Shared
         xsArraySetInt(danceTactics, 0, cTacticFertilityDance);
         xsArraySetInt(danceTactics, 1, cTacticGiftDance);
         xsArraySetInt(danceTactics, 2, cTacticAlarmDance);
         xsArraySetInt(danceTactics, 3, cTacticWarDance);

         xsArraySetInt(danceTactics, 4, cTacticWarChiefDance);
         break;
      }
      case cCivXPSioux:
      {
         danceTactics = xsArrayCreateInt(6, -1, "Dance tactics");

         // Shared
         xsArraySetInt(danceTactics, 0, cTacticFertilityDance);
         xsArraySetInt(danceTactics, 1, cTacticGiftDance);
         xsArraySetInt(danceTactics, 2, cTacticAlarmDance);
         xsArraySetInt(danceTactics, 3, cTacticWarDance);

         xsArraySetInt(danceTactics, 4, cTacticWarChiefDanceSioux);
         xsArraySetInt(danceTactics, 5, cTacticWarDanceSong);
         break;
      }
      case cCivDEInca:
      {
         danceTactics = xsArrayCreateInt(6, -1, "Dance tactics");

         // Shared
         xsArraySetInt(danceTactics, 0, cTacticFertilityDance);
         xsArraySetInt(danceTactics, 1, cTacticGiftDance);
         xsArraySetInt(danceTactics, 2, cTacticAlarmDance);
         xsArraySetInt(danceTactics, 3, cTacticWarDance);

         xsArraySetInt(danceTactics, 4, cTacticdeWarChiefDanceInca);
         xsArraySetInt(danceTactics, 5, cTacticdeMoonDance);
         break;
      }
      }
   }

   if (gNativeDancePlan < 0)
   {
      gNativeDancePlan = createNativeResearchPlan(cTacticNormal, 85, 1, 1, 1);
      lastTactic = cTacticNormal;
      lastTacticTime = time;
   }

   int numWarPriests = 0;
   int limitWarPriests = 0;
   int numPriestesses = 0;
   int numLlamas = 0;
   int numEconUnits = 0;

   int totalBonusDancers = 0;
   int mainBaseID = kbBaseGetMainID(cMyID);
   // If not in defense reflex use up to 25 available warrior priests as dancers
   if (gDefenseReflexBaseID != mainBaseID)
   {
      // War priest.
      numWarPriests = kbUnitCount(cMyID, cUnitTypexpMedicineManAztec, cUnitStateAlive);
      // Don't defend with warrior priests when there are no villagers dancing as we can produce warriors from the plaza.
      if (gDefenseReflexBaseID != mainBaseID || (numWarPriests > 0 && aiPlanGetNumberUnits(gNativeDancePlan, gEconUnit) == 0))
      {
         if (cMyCiv == cCivXPAztec)
         {
            limitWarPriests = kbGetBuildLimit(cMyID, cUnitTypexpMedicineManAztec);
            if (limitWarPriests < numWarPriests)
            {
               limitWarPriests = numWarPriests;
         }
         }
         else
         {
            limitWarPriests = numWarPriests;
         }
         totalBonusDancers = numWarPriests;
         if (totalBonusDancers > 25)
         {
            totalBonusDancers = 25;
      }
   }
   }

   // Priestess.
   if (totalBonusDancers < 25)
   {
      numPriestesses = kbUnitCount(cMyID, cUnitTypedePriestess, cUnitStateAlive);
      if ((totalBonusDancers + numPriestesses) > 25)
      {
         numPriestesses = 25 - totalBonusDancers;
         totalBonusDancers = 25;
      }
      else
      {
         totalBonusDancers = totalBonusDancers + numPriestesses;
      }
   }

   // Llama.
   if ((cMyCiv == cCivDEInca) && (totalBonusDancers < 25))
   {
      numLlamas = kbUnitCount(cMyID, cUnitTypeLlama, cUnitStateAlive);
      if ((totalBonusDancers + numLlamas) > 25)
      {
         numLlamas = 25 - totalBonusDancers;
         totalBonusDancers = 25;
      }
      else
      {
         totalBonusDancers = totalBonusDancers + numLlamas;
      }
   }

   aiPlanAddUnitType(gNativeDancePlan, cUnitTypexpMedicineManAztec, numWarPriests, numWarPriests, limitWarPriests);
   aiPlanAddUnitType(gNativeDancePlan, cUnitTypedePriestess, numPriestesses, numPriestesses, numPriestesses);
   if (cMyCiv == cCivDEInca)
   {
      aiPlanAddUnitType(gNativeDancePlan, cUnitTypeLlama, numLlamas, numLlamas, numLlamas);
   }

   int numDanceTactics = xsArrayGetSize(danceTactics);
   int tacticID = -1;
   int tacticPriority = 0;
   int bestTacticID = -1;
   int bestTacticPriority = 0;
   int planID = -1;
   const int cMinDancePriorityVillager = 3;
   int maxMilitaryPop = 0;
   float militaryPercentage = 0.0;
   int numPlazas = kbUnitCount(cMyID, cUnitTypeCommunityPlaza, cUnitStateAlive);
   bool warriorLimitReached = kbUnitCount(cMyID, cUnitTypexpWarrior, cUnitStateAlive) >=
                              kbGetBuildLimit(cMyID, cUnitTypexpWarrior);

   // Go through all tactics and find the best one.
   for (i = 0; < numDanceTactics)
   {
      tacticID = xsArrayGetInt(danceTactics, i);
      tacticPriority = 0;

      switch (tacticID)
      {
      case cTacticFertilityDance: // Speed up unit production.
      {
         if (kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) > 60 && (aiGetAvailableMilitaryPop() >= 50) &&
             ((kbGetPopCap() - kbGetPop()) >= 50))
               {
            tacticPriority = 94;
               }
         break;
      }
      case cTacticGiftDance: // Generates XP.
      {
         // Defaults to gift dance.
         tacticPriority = cMinDancePriorityVillager - 2;
         break;
      }
      case cTacticAlarmDance: // Spawn warriors.
      {
         if (numPlazas > 0 && gDefenseReflexBaseID == mainBaseID && warriorLimitReached == false)
            {
            tacticPriority = 99;
            }
         break;
      }
      case cTacticWarDance: // Increase attack.
      {
         planID = aiPlanGetIDByTypeAndVariableType(cPlanCombat, cCombatPlanCombatType, cCombatPlanCombatTypeAttack);
         if (numPlazas > 0 &&
             ((planID >= 0 && aiPlanGetVariableBool(planID, cCombatPlanInCombat, 0) == true) ||
              (gDefenseReflexBaseID == mainBaseID && warriorLimitReached == true &&
               kbGetPopulationSlotsByUnitTypeID(cMyID, cUnitTypeLogicalTypeLandMilitary) >= (0.3 * aiGetMilitaryPop()))))
               {
            tacticPriority = 98;
               }
         break;
      }
      case cTacticWarChiefDanceAztec: // Rescue Aztec warchief.
      {
         if (aiGetFallenExplorerID() >= 0)
            {
            tacticPriority = cMinDancePriorityVillager - 1;
            }
         break;
      }
      case cTacticWarChiefDance: // Rescue Iroquois warchief.
      {
         if (aiGetFallenExplorerID() >= 0)
            {
            tacticPriority = cMinDancePriorityVillager - 1;
            }
         break;
      }
      case cTacticWarChiefDanceSioux: // Rescue Sioux warchief.
      {
         if (aiGetFallenExplorerID() >= 0)
            {
            tacticPriority = cMinDancePriorityVillager - 1;
            }
         break;
      }
      case cTacticdeWarChiefDanceInca: // Rescue Inca warchief.
      {
         if (aiGetFallenExplorerID() >= 0)
            {
            tacticPriority = cMinDancePriorityVillager - 1;
            }
         break;
      }
      case cTacticHolyDanceAztec: // Spawn warrior priests.
      {
         if (kbUnitCount(cMyID, cUnitTypexpMedicineManAztec, cUnitStateAlive) <
             kbGetBuildLimit(cMyID, cUnitTypexpMedicineManAztec))
         {
            if (totalBonusDancers > 1 || (xsArrayGetFloat(gResourceNeeds, cResourceFood) <= -1000.0 &&
                                          xsArrayGetFloat(gResourceNeeds, cResourceWood) <= -1000.0 &&
                                          xsArrayGetFloat(gResourceNeeds, cResourceGold) <= -1000.0))
                  {
               // We spent at least 30 seconds into spawning this unit, avoid switching.
               if (lastTactic == cTacticHolyDanceAztec && (time - lastTacticTime) >= 30000 && (time - lastTacticTime) < 90000)
                     {
                  tacticPriority = 99;
                     }
               else
                     {
                  tacticPriority = 96;
         }
                  }
            }
         break;
      }
      // No skull knights, should prefer ranged units. Why not? Enhanced
      case cTacticGarlandWarDance: // Spawn skull knights.
      {
         if ((numPlazas > 0) && (kbGetAge() >= cAge4) && (aiGetAvailableMilitaryPop() >= 10) &&
             ((kbGetPopCap() - kbGetPop()) >= 10))
         {
            // We spent at least 30 seconds into spawning this unit, avoid switching.
            if (lastTactic == cTacticGarlandWarDance && (time - lastTacticTime) >= 30000 &&
                (time - lastTacticTime) < 90000)
               tacticPriority = 99;
            else
               tacticPriority = 95;
         }
         break;
      }
      case cTacticWarDanceSong: // Spawn dog soldiers.
      {
         if ((numPlazas > 0) && (kbGetAge() >= cAge4) && (aiGetAvailableMilitaryPop() >= 10) &&
             ((kbGetPopCap() - kbGetPop()) >= 10))
         {
            // We spent at least 30 seconds into spawning this unit, avoid switching.
            if (lastTactic == cTacticWarDanceSong && (time - lastTacticTime) >= 30000 && (time - lastTacticTime) < 90000)
               {
               tacticPriority = 99;
               }
            else
               {
               tacticPriority = 95;
         }
            }
         break;
      }
      case cTacticdeMoonDance: // Wood trickle.
      {
         // When we run out of wood.
            if ((((gDepletedResources & (1 << cResourceWood)) != 0) && time > 120000 && xsArrayGetFloat(gResourceNeeds, cResourceWood) > 0.0) ||
             // Don't switch for at least 60 seconds.
             (lastTactic == cTacticdeMoonDance && (time - lastTacticTime) < 60000))
            {
            tacticPriority = 97;
            }
         break;
      }
      }

      if (bestTacticPriority < tacticPriority)
      {
         bestTacticID = tacticID;
         bestTacticPriority = tacticPriority;
      }
   }

   if (bestTacticPriority < cMinDancePriorityVillager && totalBonusDancers < 2)
   {
      aiPlanAddUnitType(gNativeDancePlan, gEconUnit, 0, 0, 0);
      return;
   }

   // Build community plaza if there isn't one.
   if (numPlazas < 1)
   {
      planID = aiPlanGetIDByTypeAndVariableType(cPlanBuild, cBuildPlanBuildingTypeID, cUnitTypeCommunityPlaza);
      if (planID < 0)
      {
         planID = createSimpleBuildPlan(cUnitTypeCommunityPlaza, 1, 92, false, cEconomyEscrowID, mainBaseID, 1);
      }
      aiPlanSetDesiredResourcePriority(planID, 60);
      aiPlanAddUnitType(gNativeDancePlan, gEconUnit, 0, 0, 0);
      return;
   }

   if (bestTacticPriority >= cMinDancePriorityVillager && (time - lastVillagerTime) >= 60000)
   {
      numEconUnits = kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) / 10;

      switch (bestTacticID)
      {
      case cTacticWarDance:
      {
         // Scale by military pop.
         maxMilitaryPop = aiGetMilitaryPop();
         if (maxMilitaryPop > 0)
            {
            militaryPercentage = kbGetPopulationSlotsByUnitTypeID(cMyID, cUnitTypeLogicalTypeLandMilitary) / maxMilitaryPop;
            }
         numEconUnits = militaryPercentage * numEconUnits * 2 - totalBonusDancers;
         if (numEconUnits > 25)
            {
            numEconUnits = 25;
            }
         if (numEconUnits < 0)
            {
            numEconUnits = 0;
            }
         aiPlanAddUnitType(gNativeDancePlan, gEconUnit, numEconUnits, numEconUnits * 2, numEconUnits * 2);
         break;
      }
      case cTacticdeMoonDance:
      {
         // Need more dancers as we are out of wood.
         numEconUnits = numEconUnits * 2 - totalBonusDancers;
         if (numEconUnits > 25)
            {
            numEconUnits = 25;
            }
         if (numEconUnits < 0)
            {
            numEconUnits = 0;
            }
         aiPlanAddUnitType(gNativeDancePlan, gEconUnit, numEconUnits, numEconUnits * 2, numEconUnits * 2);
         break;
      }
      default:
      {
         // Add a number of dancers equivalent to 1/10 of settler pop, rounded down
         // Make sure no more than 25 units are assigned in total
         numEconUnits = numEconUnits - totalBonusDancers;
         if (numEconUnits > 25)
            {
            numEconUnits = 25;
            }
         if (numEconUnits < 0)
            {
            numEconUnits = 0;
            }
         aiPlanAddUnitType(gNativeDancePlan, gEconUnit, numEconUnits / 2, numEconUnits, numEconUnits * 2);
         break;
      }
      }

      lastVillagerTime = time;
   }

   aiPlanSetVariableInt(gNativeDancePlan, cNativeResearchPlanTacticID, 0, bestTacticID);
   lastTactic = bestTacticID;
   lastTacticTime = time;
}

//==============================================================================
// llWritePersonalityProbe — write probe data to the AI's personality file.
//
// 2026-04-29 BREAKTHROUGH:  AoE3-DE's personality serialiser silently drops
// ANY <uservars> entry whose key is not on a hardcoded engine whitelist.
// Verified empirically: after a clean game-over with `aiPersonalitySetPlayerUserVar`
// calls for both whitelisted keys (`iWonLastGame`) and our custom keys
// (`ll_pid`, `ll_preinit_marker`, etc.), only the whitelisted keys appear in
// the .personality file.  The whitelist (gleaned from a real flushed file):
//
//    iWonLastGame, iBeatHimLastTime, heBeatMeLastTime, iCarriedHimLastTime,
//    heCarriedMeLastTime, lastGameDifficulty, myAllyCount, myEnemyCount,
//    wasMyAllyLastGame, lastMapID
//
// Workaround: bit-pack our probe data into the *numeric* whitelisted slots.
// Side-effect — these values are read by the engine on the NEXT match start
// (taunts, "we played here last time" prompts, ally-team-up logic).  The
// matrix runner wipes Game/AI personality files between runs to keep behaviour
// clean; for one-off play this would corrupt taunts until next clean save.
//
// Pack layout (each slot is one float, IEEE-754 32-bit, 23-bit safe mantissa):
//
//   myAllyCount        bit  23     = sentinel = 1   (probe-written marker)
//                      bits 22..18 = pid            (5 bits, 0..31)
//                      bits 17..13 = style          (5 bits, 0..31)
//                      bits 12..09 = walls          (4 bits, 0..15)
//                      bits 08..06 = wall_strat     (3 bits, 0..7)
//                      bits 05..00 = terr_p         (5 bits in 6-bit field)
//
//   myEnemyCount       bits 20..16 = terr_s         (5 bits)
//                      bits 15..11 = heading        (5 bits)
//                      bits 10..08 = age            (3 bits, 0..4, 0=Discovery)
//                      bits 07..00 = civ            (8 bits, 0..255)
//
//   lastMapID          score, clamped to 0..(2^23 - 1) = ~8.3M
//
//   lastGameDifficulty match_seconds = match_ms / 1000, clamped to 0..2^23
//
//   wasMyAllyLastGame  bits 15..08 = terr_bias_q8   (uint8, 0..255 = 0.0..1.0)
//                      bits 07..00 = head_bias_q8   (uint8, 0..255 = 0.0..1.0)
//
// Sentinel: bit 23 (= 8388608) of myAllyCount is set whenever our probe
// wrote.  Engine never produces values that high for myAllyCount (max ~8 in
// 8-player matches), so the reader uses this to distinguish a probe write
// from engine-native data.
//==============================================================================
void llWritePersonalityProbe(int nothing = 0)
{
   // Probe-disable shortcut.
   if (cLLReplayProbes == false)
   {
      return;
   }

   // ── Bit-pack the probe state into engine-whitelisted numeric uservars ────
   // (See header block above for the canonical layout.)  All masks bound the
   // values to the field width so an out-of-range global never spills bits.

   int pid_b     = cMyID                          & 31;     // 5 bits
   int style_b   = gLLBuildStyle                  & 31;     // 5 bits
   int walls_b   = gLLWallLevel                   & 15;     // 4 bits
   int wstrat_b  = gLLWallStrategy                & 7;      // 3 bits
   int terrp_b   = gLLPreferredTerrainPrimary     & 31;     // 5 bits in 6-bit slot
   int terrs_b   = gLLPreferredTerrainSecondary   & 31;     // 5 bits
   int heading_b = gLLExpansionHeading            & 31;     // 5 bits
   int age_b     = kbGetAge()                     & 7;      // 3 bits
   int civ_b     = kbGetCiv()                     & 255;    // 8 bits

   int sentinel  = 1 << 23;
   int allyPack  = sentinel
                 | (pid_b    << 18)
                 | (style_b  << 13)
                 | (walls_b  << 9)
                 | (wstrat_b << 6)
                 |  terrp_b;

   int enemyPack = (terrs_b   << 16)
                 | (heading_b << 11)
                 | (age_b     << 8)
                 |  civ_b;

   // 23-bit safe mantissa clamp (~8.3M) so float storage is lossless.
   int score_b = aiGetScore(cMyID);
   if (score_b < 0)        score_b = 0;
   if (score_b > 8388607)  score_b = 8388607;

   int secs_b = xsGetTime() / 1000;
   if (secs_b < 0)         secs_b = 0;
   if (secs_b > 8388607)   secs_b = 8388607;

   // Quantise float biases [0..1] -> uint8 [0..255].  XS truncates float
   // assignment to int, so multiply then assign.
   int tbias_q8 = gLLTerrainBiasStrength * 255.0;
   if (tbias_q8 < 0)   tbias_q8 = 0;
   if (tbias_q8 > 255) tbias_q8 = 255;
   int hbias_q8 = gLLHeadingBiasStrength * 255.0;
   if (hbias_q8 < 0)   hbias_q8 = 0;
   if (hbias_q8 > 255) hbias_q8 = 255;
   int biasPack = (tbias_q8 << 8) | hbias_q8;

   debugCore("llWritePersonalityProbe: ally=" + allyPack +
      " enemy=" + enemyPack + " score=" + score_b +
      " secs=" + secs_b + " bias=" + biasPack);

   // Write the packed values to every opponent's player-history record.
   // Whichever .personality file the post-match parser opens, it'll find
   // exactly one block carrying the sentinel bit (cf. probes_from_replay.py).
   for (pid = 1; < cNumberPlayers)
   {
      if (pid == cMyID)
      {
         continue;
      }
      string playerName = kbGetPlayerName(pid);
      int playerHistoryID = aiPersonalityGetPlayerHistoryIndex(playerName);
      if (playerHistoryID == -1)
      {
         playerHistoryID = aiPersonalityCreatePlayerHistory(playerName);
      }
      if (playerHistoryID == -1)
      {
         continue;
      }
      aiPersonalitySetPlayerUserVar(playerHistoryID, "myAllyCount",        allyPack);
      aiPersonalitySetPlayerUserVar(playerHistoryID, "myEnemyCount",       enemyPack);
      aiPersonalitySetPlayerUserVar(playerHistoryID, "lastMapID",          score_b);
      aiPersonalitySetPlayerUserVar(playerHistoryID, "lastGameDifficulty", secs_b);
      aiPersonalitySetPlayerUserVar(playerHistoryID, "wasMyAllyLastGame",  biasPack);
   }
}

//==============================================================================
void gameOverHandler(int nothing = 0)
{
   debugCore("GG, Game Over!");
   bool iWon = kbHasPlayerLost(cMyID);
   // LL-GAMEOVER probe — final state. Variable 'iWon' is base-game and
   // confusingly named (it actually receives kbHasPlayerLost), so emit the
   // raw kbHasPlayerLost value instead for unambiguous outcome parsing.
   //
   // Guard against spurious early firings: we observed gameOverHandler
   // running at t=20s with stale pre-init identity (DEHausa/Usman for a
   // Napoleonic slot). The engine invokes this on any game-state reset,
   // including lobby leaver replay. Skip emission inside the first 60s
   // and skip when neither win nor loss is flagged — no legitimate match
   // ends that early and parseable gameover needs a real outcome.
   // Suppression gate: skip while the AI is still mid-load. gLLPostInitFired
   // flips true at the tail of postInit(), so any earlier engine-driven
   // self-fire (lobby load, identity still stale) gets dropped here.
   // The earlier 60s wall-clock guard blocked legitimate observe<60s smoke
   // runs from ever flushing probes — this gate is identity-correct without
   // that side effect.
   if (gLLPostInitFired == false)
   {
      debugCore("gameOverHandler: suppressing pre-postInit fire (t=" +
         xsGetTime() + " lost=" + kbHasPlayerLost(cMyID) +
         " score=" + aiGetScore(cMyID) + ")");
      return;
   }
   llProbe("meta.gameover",
      "lost=" + kbHasPlayerLost(cMyID) +
      " finalAge=" + kbGetAge() +
      " score=" + aiGetScore(cMyID));

   for (pid = 1; < cNumberPlayers)
   {
      if (pid == cMyID)
      {
         continue;
      }

      string playerName = kbGetPlayerName(pid);
      debugCore("PlayerName: " + playerName);

      // Does a record exist?
      int playerHistoryID = aiPersonalityGetPlayerHistoryIndex(playerName);
      if (playerHistoryID == -1) // This should never fire since we checked for this during setup too.
      {
         debugCore("WARNING: We somehow don't have a player history at the end of the game???" +
            " What happened in the startup code?");
         // Let's make a new player history.
         playerHistoryID = aiPersonalityCreatePlayerHistory(playerName);
      }

      /* Store the following user vars:
            heBeatMeLastTime
            iBeatHimLastTime
            iCarriedHimLastTime
            heCarriedMeLastTime
            iWonLastGame
      */
      
      if (iWon == true)
      {
         aiPersonalitySetPlayerUserVar(playerHistoryID, "iWonLastGame", 1.0);
         if (kbIsPlayerEnemy(pid) == true)
         {
            aiPersonalitySetPlayerUserVar(playerHistoryID, "iBeatHimLastTime", 1.0);
            aiPersonalitySetPlayerUserVar(playerHistoryID, "heBeatMeLastTime", 0.0);
            debugCore("I won and this player was my enemy");
         }
      }
      else // We lost.
      {
         aiPersonalitySetPlayerUserVar(playerHistoryID, "iWonLastGame", 0.0);
         if (kbIsPlayerEnemy(pid) == true)
         {
            aiPersonalitySetPlayerUserVar(playerHistoryID, "iBeatHimLastTime", 0.0);
            aiPersonalitySetPlayerUserVar(playerHistoryID, "heBeatMeLastTime", 1.0);
            debugCore("I lost and this player was my enemy");
         }
      }
      
      if (kbIsPlayerAlly(pid) == true)
      {
         if (aiGetScore(cMyID) > (1.5 * aiGetScore(pid))) // I caried my ally.
         { 
            aiPersonalitySetPlayerUserVar(playerHistoryID, "iCarriedHimLastTime", 1.0);
            debugCore("I carried this allied player");
         }
         else
         {
            aiPersonalitySetPlayerUserVar(playerHistoryID, "iCarriedHimLastTime", 0.0);
         }
         if (aiGetScore(pid) > (1.5 * aiGetScore(cMyID))) // My ally carried me.
         { 
            debugCore("This allied player carried me");
            aiPersonalitySetPlayerUserVar(playerHistoryID, "heCarriedMeLastTime", 1.0);
         }
         else
         {
            aiPersonalitySetPlayerUserVar(playerHistoryID, "heCarriedMeLastTime", 0.0);
            debugCore("I neither carried this allied player nor did he carry me");
         }
      }
      else // We were enemies so we couldn't have carried each other.
      {
         aiPersonalitySetPlayerUserVar(playerHistoryID, "iCarriedHimLastTime", 0.0);
         aiPersonalitySetPlayerUserVar(playerHistoryID, "heCarriedMeLastTime", 0.0);
      }
   }

   // ── Personality probe channel (non-dev-mode side channel) ─────────────────
   // aiEcho() is stripped in FINAL_RELEASE builds, but personality uservars ARE
   // written to Game/AI/<leader>.personality without dev mode.  We write key
   // diagnostic fields here so the post-match Python parser can read them even
   // when Age3Log.txt yields zero probe lines.
   //
   // Encoding: every field is a float stored under a descriptive key.
   // The parser reads the <uservars> block of the SELF player's personality
   // file (keyed by "Flessenkemper" or whoever the human opponent is).
   // Keys prefixed "ll_" are Legendary Leaders probe fields.
   //
   // Fields written:
   //   ll_pid          – cMyID (player slot 2..8 for AI)
   //   ll_style        – gLLBuildStyle (int 0..14)
   //   ll_walls        – gLLWallLevel (int)
   //   ll_wall_strat   – gLLWallStrategy (int 0..5)
   //   ll_terr_p       – gLLPreferredTerrainPrimary (int)
   //   ll_terr_s       – gLLPreferredTerrainSecondary (int)
   //   ll_terr_bias    – gLLTerrainBiasStrength (float)
   //   ll_heading      – gLLExpansionHeading (int)
   //   ll_head_bias    – gLLHeadingBiasStrength (float)
   //   ll_civ          – kbGetCiv() (engine civ ID int)
   //   ll_age          – kbGetAge() at game end
   //   ll_score        – aiGetScore(cMyID) at game end
   //   ll_match_ms     – xsGetTime() at game end (ms)
   //
   // NOTE: personality uservars are per-opponent-player.  We write to the
   // first opponent slot so there is always exactly one record per AI per
   // match regardless of how many opponents exist.
   llWritePersonalityProbe();
}

//==============================================================================
// ShouldIResign
//==============================================================================
rule ShouldIResign
minInterval 7
inactive
{
   // Don't resign during treaty since that looks dumb.
   // Don't resign too soon.
   // Don't resign if we have over 30 active pop slots.
   if ((aiTreatyActive() == true) || (kbGetPop() >= 30) || (xsGetTime() < 10 * 60 * 1000))
   {
      return;
   }

   bool humanAlly = false; // Set true if we have a surviving human ally.
   // Look for human allies.
   for (i = 1; <= cNumberPlayers)
   {
      if ((kbIsPlayerAlly(i) == true) && (kbHasPlayerLost(i) == false) && (kbIsPlayerHuman(i) == true))
      {
         humanAlly = true;    // Don't return just yet, let's see if we should chat.
      }
   }

   // Resign if the known enemy pop is > 10x mine.
   int enemyPopTotal = 0;
   int enemyCount = 0;
   int myPopTotal = 0;

   for (i = 1; < cNumberPlayers)
   {
      if (kbHasPlayerLost(i) == false)
      {
         if (i == cMyID)
         {
            myPopTotal += kbUnitCount(i, cUnitTypeUnit, cUnitStateAlive);
         }
         if (kbIsPlayerEnemy(i) == true)
         {
            enemyPopTotal += kbUnitCount(i, cUnitTypeUnit, cUnitStateAlive);
            enemyCount++;
         }
      }
   }

   if (enemyCount < 1)
   {
      enemyCount = 1; // Avoid div by 0.
   }

   float enemyRatio = (enemyPopTotal / enemyCount) / myPopTotal;

   // My pop is 1/3 the average known pop of enemies so I'm going to whine to my human ally.
   if ((enemyRatio > 3) && (humanAlly == true)) 
   {
      sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyImReadyToQuit);
         xsEnableRule("resignRetry");
         xsDisableSelf();
      return; // Never resign if we still have a human ally.
      }
   
   // My pop is 1/4 the average known pop of enemies.
   // I have no TC.
   // I have no human ally that I want to stay in the game for so try to resign.
   if ((enemyRatio > 4) && (kbUnitCount(cMyID, cUnitTypeAgeUpBuilding, cUnitStateAlive) < 1) && (humanAlly == false)) 
   {
      debugCore("Attempting to resign since I'm heavily outnumbered and have no Town Center left");
         aiAttemptResign(cAICommPromptToEnemyMayIResign);
         xsDisableSelf();
   }
}

rule resignRetry
inactive
minInterval 240
{
   xsEnableRule("ShouldIResign");
   xsDisableSelf();
}

//==============================================================================
// resignHandler
// We've asked the enemy player if we could resign, here we handle his answer (result).
//==============================================================================
void resignHandler(int result = -1)
{
   if (result == 0)
   {
      debugCore("Enemy player rejected our resign request, we must play on");
      xsEnableRule("resignRetry");
   }
   else
   {
      debugCore("Enemy player accepted our resign request, we now kill ourselves");
      aiResign();
   }

}

//==============================================================================
// abilityManager
// Use abilities when appropriate.
//==============================================================================
rule abilityManager
inactive
minInterval 12
{
   vector myBaseLocation = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
   int closestBaseID = kbFindClosestBase(cPlayerRelationEnemy, myBaseLocation);
   vector targetLocation = cInvalidVector;
   
   // Inspiration.
   if (cMyCiv == cCivIndians)
   {
      // Check if we have a Tower of Victory.
      int towerOfVictoryID = getUnit(gTowerOfVictoryPUID, cMyID, cUnitStateAlive);
      
      if (towerOfVictoryID >= 0)
      {
         // Check if the ability is off cooldown.
         if (aiCanUseAbility(towerOfVictoryID, cProtoPowerypPowerAttackBlessing) == true)
         {
            int firstAttackPlanID = aiPlanGetIDByTypeAndVariableType(cPlanCombat, cCombatPlanCombatType, 
            cCombatPlanCombatTypeAttack); 
            // Go through all the relevant plans and see if any of them are in combat.
            if ((aiPlanGetVariableBool(firstAttackPlanID, cCombatPlanInCombat, 0) == true) ||
                (aiPlanGetVariableBool(gLandDefendPlan0, cCombatPlanInCombat, 0) == true) ||
                (aiPlanGetVariableBool(gLandReservePlan, cCombatPlanInCombat, 0) == true))
            {
               aiTaskUnitSpecialPower(towerOfVictoryID, cProtoPowerypPowerAttackBlessing, -1, cInvalidVector);
            }
         }
      }
   }
   // Cease Fire.
   if (cMyCiv == cCivIndians)
   {
      // Check if we have a Taj Mahal.
      int tajMahalID = getUnit(gTajMahalPUID, cMyID, cUnitStateAlive);

      if (tajMahalID >= 0)
      {
         // Check if the ability is off cooldown.
         if (aiCanUseAbility(tajMahalID, cProtoPowerypPowerCeaseFire) == true)
         {
            // Check if we're under attack.
            if (gDefenseReflexBaseID == kbBaseGetMainID(cMyID))
            {
               aiTaskUnitSpecialPower(tajMahalID, cProtoPowerypPowerCeaseFire, -1, cInvalidVector);
            }
         }
      }
   }
   // Transcendence.
   if (cMyCiv == cCivChinese)
   {
      // Check if we have a Temple of Heaven.
      int templeOfHeavenID = getUnit(gTempleOfHeavenPUID, cMyID, cUnitStateAlive);
      
      if (templeOfHeavenID >= 0)
      {
         // Check if the ability is off cooldown.
         if (aiCanUseAbility(templeOfHeavenID, cProtoPowerypPowerGoodFortune) == true)
         {
            // Check if our land military is missing 50% of their HP or more.
            float armyMaxHP = getPlayerArmyHPs(cMyID, false);
            float armyCurrentHP = getPlayerArmyHPs(cMyID, true);
            float hpRatio = armyCurrentHP / armyMaxHP;
            if (hpRatio < 0.5)
            {
               aiTaskUnitSpecialPower(templeOfHeavenID, cProtoPowerypPowerGoodFortune, -1, cInvalidVector);
            }
         }
      }
   }
   // Informers.
   if (cMyCiv == cCivJapanese)
   {
      // Check if we have a Great Buddha.
      int greatBuddhaID = getUnit(gGreatBuddhaPUID, cMyID, cUnitStateAlive);
 
      if (greatBuddhaID >= 0)
      {
         // Check if the ability is off cooldown.
         if (aiCanUseAbility(greatBuddhaID, cProtoPowerypPowerInformers) == true)
         {
            aiTaskUnitSpecialPower(greatBuddhaID, cProtoPowerypPowerInformers, -1, cInvalidVector);
         }
      }
   }
   // Spyglass.
   if (cMyCiv == cCivPortuguese)
   {
      int explorerIDSpyglass = getUnit(cUnitTypeExplorer, cMyID, cUnitStateAlive);
      
      if (explorerIDSpyglass >= 0)
      {
         // Check if the ability is off cooldown.
         if (aiCanUseAbility(explorerIDSpyglass, cProtoPowerPowerLOS) == true)
         {
            if (closestBaseID == -1)
            { // If not yet visible, search for the enemy on the mirror position of my base.
               targetLocation = guessEnemyLocation();
            }
            if ((targetLocation == cInvalidVector) || 
                (kbLocationVisible(targetLocation) == true) || 
                (closestBaseID != -1))
            { // Otherwise reveal the closest enemy base for new information.
               targetLocation = kbBaseGetLocation(kbBaseGetOwner(closestBaseID), closestBaseID);
            }
            if (targetLocation != cInvalidVector)
            {
               aiTaskUnitSpecialPower(explorerIDSpyglass, cProtoPowerPowerLOS, -1, targetLocation);
            }
         }
      }
   }
   // Hot Air Balloon.
   if (civIsEuropean() == true)
   {
      int explorerIDBalloon = getUnit(cUnitTypeExplorer, cMyID, cUnitStateAlive);
      
      if (explorerIDBalloon >= 0)
      {
         if (aiCanUseAbility(explorerIDBalloon, cProtoPowerPowerBalloon) == true)
         {
            if (closestBaseID == -1)
            { // If not yet visible, search for the enemy on the mirror position of my base.
               targetLocation = guessEnemyLocation();
            }
            if ((targetLocation == cInvalidVector) || (kbLocationVisible(targetLocation) == true) || (closestBaseID != -1))
            { // Otherwise reveal the closest enemy base for new information.
               targetLocation = kbBaseGetLocation(kbBaseGetOwner(closestBaseID), closestBaseID);
            }
            if (targetLocation != cInvalidVector)
            {
               aiTaskUnitSpecialPower(explorerIDBalloon, cProtoPowerPowerBalloon, -1, targetLocation);
               int balloonExplore = aiPlanCreate("Balloon Explore", cPlanExplore);
               aiPlanSetDesiredPriority(balloonExplore, 75);
               aiPlanAddUnitType(balloonExplore, cUnitTypeHotAirBalloon, 0, 1, 1);
               aiPlanSetBaseID(balloonExplore, kbBaseGetMainID(cMyID));
               aiPlanSetVariableBool(balloonExplore, cExplorePlanDoLoops, 0, false);
               aiPlanSetActive(balloonExplore);
            }
         }
      }
   }
   /* Combat plans can already use abilities and the bombard logic below is quite bad.
   // Long-range Bombardment Attack
   if (civIsNative() == false)
   {
      int monitorID = getUnit(gMonitorUnit, cMyID, cUnitStateAlive);
      if (monitorID >= 0)
      {
         // Check if the ability is off cooldown.
         if (aiCanUseAbility(monitorID, cProtoPowerPowerLongRange) == true)
         {
            vector monitorLocation = kbUnitGetPosition(monitorID);
            int targetIDmonitor = getUnitByLocation(
               cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, cUnitStateAlive, monitorLocation, 100.0);
            if (targetIDmonitor != -1)
            {
               aiTaskUnitSpecialPower(monitorID, cProtoPowerPowerLongRange, targetIDmonitor, cInvalidVector);
            }
         }
      
   }
   */
   /* This upgrade is currently not being researched by the AI thus this logic below is unneeded.
   // Heal
   if ((cMyCiv == cCivXPIroquois) && (kbTechGetStatus(cTechBigFirepitSecretSociety) == cTechStatusActive))
   {
      int warchiefIDHeal = -1;
      warchiefIDHeal = getUnit(cUnitTypexpIroquoisWarChief, cMyID, cUnitStateAlive);
      if ((warchiefIDHeal >= 0) && aiCanUseAbility(warchiefIDHeal, cProtoPowerPowerHeal) == true &&
          (kbUnitGetHealth(warchiefIDHeal) < 0.8))
      {
         vector warchiefLocation = kbUnitGetPosition(warchiefIDHeal);
         aiTaskUnitSpecialPower(warchiefIDHeal, cProtoPowerPowerHeal, -1, warchiefLocation);
      }
   }
   */
   // Minor native Somali Lighthouse ability.
   if (isMinorNativePresent(cCivSomali) == true)
   {
      if (kbTechGetStatus(cTechDENatSomaliLighthouses) == cTechStatusActive)
      {
         int tradingPostID = checkAliveSuitableTradingPost(cCivSomali);
         if (tradingPostID > -1)
         { // Must target this ability on itself.
            aiTaskUnitSpecialPower(tradingPostID, cProtoPowerdeNatSomaliLighthouse, tradingPostID, cInvalidVector);
         }
      }
   }
}

//==============================================================================
// transportMonitor
//==============================================================================
rule transportMonitor
inactive
minInterval 10
{
   if (aiPlanGetIDByIndex(cPlanTransport, -1, true, 0) >= 0)
   {
      return;
   }

   // Find idle units away from our base.
   int baseAreaGroupID = kbAreaGroupGetIDByPosition(kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID)));
   int areaGroupID = -1;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeGarrisonInShips, cMyID, cUnitStateAlive); // Was cUnitTypeLogicalTypeGarrisonInShips...
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int unitID = -1;
   int planID = -1;
   vector position = cInvalidVector;
   bool transportRequired = false;
   for (i = 0; < numberFound)
   {
      unitID = kbUnitQueryGetResult(unitQueryID, i);
      // Avoid transporting island explore scout back to our base.
      if (unitID == gIslandExploreTransportScoutID)
      {
         continue;
      }
      position = kbUnitGetPosition(unitID);
      areaGroupID = kbAreaGroupGetIDByPosition(position);
      if (areaGroupID == baseAreaGroupID)
      {
         continue;
      }
      if (kbAreaGroupGetType(areaGroupID) == cAreaGroupTypeWater)
      {
         // If units are inside a water area(likely on a shore), make sure it does not border our main base area group.
         int areaID = kbAreaGetIDByPosition(position);
         int numberBorders = kbAreaGetNumberBorderAreas(areaID);
         bool inMainBase = false;
         for (j = 0; < numberBorders)
         {
            if (kbAreaGroupGetIDByPosition(kbAreaGetCenter(kbAreaGetBorderAreaID(areaID, j))) == baseAreaGroupID)
            {
               inMainBase = true;
               break;
            }
         }
         if (inMainBase == true)
         {
            continue;
      }
      }
      planID = kbUnitGetPlanID(unitID);
      if (planID >= 0 && aiPlanGetDesiredPriority(planID) >= 25)
      {
         continue;
      }
      transportRequired = true;
      debugCore("Tranporting " + kbGetUnitTypeName(kbUnitGetProtoUnitID(unitID)) + " and its nearby units back to main base");
      break;
   }

   if (transportRequired == false)
   {
      return;
   }

   // once we started transporting, make sure no one can steal units from us
   int transportPlanID = createTransportPlan(position, kbBaseGetMilitaryGatherPoint(cMyID, kbBaseGetMainID(cMyID)), 100, false);

   if (transportPlanID < 0)
   {
      return;
   }

   unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeGarrisonInShips, cMyID, cUnitStateAlive, position, 30.0);
   numberFound = kbUnitQueryExecute(unitQueryID);
   aiPlanAddUnitType(transportPlanID, cUnitTypeLogicalTypeGarrisonInShips, numberFound, numberFound, numberFound);
   for (i = 0; < numberFound)
   {
      unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (aiPlanAddUnit(transportPlanID, unitID) == false)
      {
         aiPlanDestroy(transportPlanID);
         return;
      }
   }
   aiPlanSetNoMoreUnits(transportPlanID, true);
}

//==============================================================================
// revoltedHandler
//==============================================================================
void revoltedHandler(int techID = -1)
{
   xsDisableRule("ageUpgradeMonitor"); // If we implement Mexican revolutions this needs to be changed.
   xsDisableRule("age5Monitor");
   debugCore("We revolted with " + kbGetTechName(techID));

   if (cMyCiv == cCivOttomans)
   {
      debugCore("DISABLING Rule: 'toggleAutomaticSettlerSpawning' because we revolted so it no longer applies to us");
      xsDisableRule("toggleAutomaticSettlerSpawning");
   }

   if ((techID == cTechDERevolutionSouthAfrica) || (techID == cTechDERevolutionCanadaBritish) ||
       (techID == cTechDERevolutionCanadaFrench))
   {
      gRevolutionType = cRevolutionEconomic;
      // Delete the Trek Wagons we get from this revolution since we don't use them.
      if (techID == cTechDERevolutionSouthAfrica)
      {
         int trekWagonQueryID = createSimpleUnitQuery(cUnitTypedeREVStarTrekWagon, cMyID, cUnitStateAlive);
         int numberFound = kbUnitQueryExecute(trekWagonQueryID);
         for (i = 0; < numberFound)
         {
            aiTaskUnitDelete(kbUnitQueryGetResult(trekWagonQueryID, i));
         }
      }
   }
   else
   {
      gRevolutionType = cRevolutionMilitary;
   }

   if (gRevolutionType == cRevolutionMilitary)
   {
      int numPlans = aiPlanGetActiveCount();
      int planID = -1;

      if (techID == cTechDERevolutionFinland)
      {
         gRevolutionType = gRevolutionType | cRevolutionEconomic | cRevolutionFinland;
         cvOkToGatherWood = true;
         cvOkToGatherFood = false;
         cvOkToGatherGold = false;
         gEconUnit = cUnitTypeSkirmisher;
         aiPlanSetVariableInt(gSettlerMaintainPlan, cTrainPlanUnitType, 0, gEconUnit);
         // Skirmisher does not count as villager, inform the AI we can use it as villager.
         aiAddGathererType(gEconUnit);
         gTowerUnit = cUnitTypeBlockhouse;
         gTimeToFarm = false;
         gTimeForPlantations = false;
         updateResourceDistribution();
      }
      else if (techID == cTechDEHCFedBearFlagRevolt)
      {
         // US HC card revolt, just proceed with destroying plans.
         // Unset revolution flag, we aren't disabling things.
         gRevolutionType = 0;
      }
      else
      { // Set all Settler related stuff to 0 but leave the default array to potentially restore everything. If cards arrive
        // that re-enable economy we handle that in transportShipmentArrive.
         aiPlanSetVariableInt(gSettlerMaintainPlan, cTrainPlanNumberToMaintain, 0, 0);
         for (i = cAge1; <= cvMaxAge)
         {
            xsArraySetInt(gTargetSettlerCounts, i, 0);
         }
      }

      // Destroy all build and gather plans when our settlers transformed into military units.
      // This will also destroy the plans for the Finnish revolution while their Jaegers can still build/gather.
      // But they have new/changed options so better be safe and start over.
      for (i = 0; < numPlans)
      {
         planID = aiPlanGetIDByActiveIndex(i);
         switch (aiPlanGetType(planID))
         {
         case cPlanBuild:
         {
            // Avoid destroying plans when it is built by wagons.
            if ((aiPlanGetNumberUnits(planID, cUnitTypeAbstractWagon) == 0) &&
                ((aiPlanGetState(planID) != cPlanStateBuild) || (gRevolutionType & cRevolutionFinland) == 0))
            {
               aiPlanDestroy(planID);
            }
            break;
         }
         case cPlanGather:
         {
            aiPlanDestroy(planID);
            break;
         }
         }
      }

      // Disable resource gathering because we have no units anymore which can do that.
      if ((gRevolutionType & cRevolutionFinland) == 0)
      {
         cvOkToGatherFood = false;
         cvOkToGatherWood = false;
         cvOkToGatherGold = false;
      }
      // Military revolts can't train Fishing Boats so null out the maintain plan and disable the manager.
      // Enable it all again in transportShipmentArrive when appropriate.
      if (gFishingBoatMaintainPlan > 0 && techID != cTechDEHCFedBearFlagRevolt)
      {
         xsDisableRule("fishManager");
         aiPlanSetVariableInt(gFishingBoatMaintainPlan, cTrainPlanNumberToMaintain, 0, 0);
      }
   }
   updateSettlersAndPopManager();
}

//==============================================================================
// ageTransitionManager
// Run military and building manager early to update resources we need.
//==============================================================================
rule ageTransitionManager
inactive
minInterval 1
{
   static int counter = 0;

   switch (counter)
   {
   case 0:
   {
      if ((xsIsRuleEnabled("militaryManager") == false) &&
          (cvOkToTrainArmy == true))
      {
         xsEnableRule("militaryManager");
         militaryManager(); // Call instantly to get started.
      }
      break;
   }
   case 1:
   {
         if (cvOkToBuild == true)
         {
      buildingMonitor();
         }
      break;
   }
   case 2:
   {
      updateResourceDistribution(true);
      break;
   }
   }

   counter++;
   if (counter >= 3)
   {
      xsDisableSelf();
      counter = 0;
   }
}

//==============================================================================
// ageUpHandler
//==============================================================================
void ageUpHandler(int playerID = -1)
{
   debugCore("ageUpHandler is called, player " + playerID + " aged up!");
   int age = kbGetAgeForPlayer(playerID);
   bool firstToAge = true; // Set true if this player is the first to reach that age, false otherwise.
   bool lastToAge = true;  // Set true if this player is the last to reach this age, false otherwise.
   int slowestPlayer = -1;
   int lowestAge = 100000;
   int lowestCount = 0; // How many players are still in the lowest age?
   static int foundFirstInAge = 0;

   if ((foundFirstInAge & (1 << age)) == 0)
   {
      foundFirstInAge |= 1 << age;
   }
   else
   {
      firstToAge = false;
   }

   for (index = 1; < cNumberPlayers)
   {
      if (index != playerID)
      {
         if (kbGetAgeForPlayer(index) < age)
         {
            lastToAge = false; // Someone is still behind playerID.
         }
      }
      if (kbGetAgeForPlayer(index) < lowestAge)
      {
         lowestAge = kbGetAgeForPlayer(index);
         slowestPlayer = index;
         lowestCount = 1;
      }
      else
      {
         if (kbGetAgeForPlayer(index) == lowestAge)
         {
            lowestCount = lowestCount + 1;
         }
      }
   }
   
   if ((firstToAge == true) && (age >= cAge3))
   {
      switch (age) // We don't save times for first to Commerce since we don't use that info.
      {
      case cAge3:
      {
         xsArraySetInt(gFirstAgeTime, cAge3, xsGetTime());
         debugCore("Time the first player reached the Fortress Age: " + xsArrayGetInt(gFirstAgeTime, cAge3));
         break;
      }
      case cAge4:
      {
         xsArraySetInt(gFirstAgeTime, cAge4, xsGetTime());
         debugCore("Time the first player reached the Industrial Age: " + xsArrayGetInt(gFirstAgeTime, cAge4));
         break;
      }
      case cAge5:
      {
         xsArraySetInt(gFirstAgeTime, cAge5, xsGetTime());
         debugCore("Time the first player reached the Imperial Age: " + xsArrayGetInt(gFirstAgeTime, cAge5));
         break;
      }
      }

      // If we are behind the first player, setup a timer to update settler count 5 minutes later.
      if (age > kbGetAgeForPlayer(cMyID))
      {
         xsEnableRule("updateSettlerCountsWhenBehind");
         debugCore("We are "+(age - kbGetAgeForPlayer(cMyID))+" ages behind the first player, queuing a timer to update settler count in 5 minutes.");
      }
   }

   if ((firstToAge == true) && (age == cAge2))
   {
      if ((kbIsPlayerAlly(playerID) == true) && (playerID != cMyID))
      {
         sendStatement(playerID, cAICommPromptToAllyHeReachesAge2First);
      }
      if (kbIsPlayerEnemy(playerID) == true)
      {
         sendStatement(playerID, cAICommPromptToEnemyHeReachesAge2First);
      }
      return;
   }
   if ((lastToAge == true) && (age == cAge2))
   {
      if ((kbIsPlayerAlly(playerID) == true) && (playerID != cMyID))
      {
         sendStatement(playerID, cAICommPromptToAllyHeReachesAge2Last);
      }
      if (kbIsPlayerEnemy(playerID) == true)
      {
         sendStatement(playerID, cAICommPromptToEnemyHeReachesAge2Last);
      }
      return;
   }

   // Check to see if there is a lone player that is behind everyone else
   if ((lowestCount == 1) && (slowestPlayer != cMyID))
   {
      // This player is slowest, nobody else is still in that age, and it's not me,
      // so set the globals and activate the rule...unless it's already active.
      // This will cause a chat to fire later (currently 120 sec mininterval) if
      // this player is still lagging behind.
      if (gLateInAgePlayerID < 0)
      {
         if (xsIsRuleEnabled("lateInAge") == false)
         {
            gLateInAgePlayerID = slowestPlayer;
            gLateInAgeAge = lowestAge;
            xsEnableRule("lateInAge");
            return;
         }
      }
   }

   // Check to see if either an ally or an enemy advanced before me.
   if (age > kbGetAgeForPlayer(cMyID))
   {
      if (kbIsPlayerAlly(playerID) == true)
      {
         sendStatement(playerID, cAICommPromptToAllyHeAdvancesAhead);
      }
      else if (kbIsPlayerEnemy(playerID) == true)
      {
         sendStatement(playerID, cAICommPromptToEnemyHeAdvancesAhead);
      }
   }
}

//==============================================================================
// updateSettlerCountsWhenBehind
//==============================================================================
rule updateSettlerCountsWhenBehind
inactive
minInterval 300 // 5 minutes
{
   updateSettlersAndPopManager();
   xsDisableSelf();
}

//==============================================================================
// ageUpEventHandler
//==============================================================================
void ageUpEventHandler(int planID = -1)
{
   int state = aiPlanGetState(planID);
   // We save the Wonder we are going to construct in this variable.
   static int buildingPUID = -1;

   if (state == -1)
   {
      // Also make sure this building exists, because invalid state could also mean the plan failed.
      if ((civIsAsian() == true) && (getUnit(buildingPUID, cMyID, cUnitStateAlive) >= 0))
      {
         if ((cMyCiv == cCivChinese) || (cMyCiv == cCivSPCChinese))
         {
            switch (buildingPUID)
            {
            case cUnitTypeypWCWhitePagoda2:
            case cUnitTypeypWCWhitePagoda3:
            case cUnitTypeypWCWhitePagoda4:
            case cUnitTypeypWCWhitePagoda5:
            {
               gWhitePagodaPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gWhitePagodaPUID));
               break;
            }
            case cUnitTypeypWCSummerPalace2:
            case cUnitTypeypWCSummerPalace3:
            case cUnitTypeypWCSummerPalace4:
            case cUnitTypeypWCSummerPalace5:
            {
               gSummerPalacePUID = buildingPUID;
               xsEnableRule("summerPalaceTacticMonitor");
               debugCore("Wonder I built: " + kbGetProtoUnitName(gSummerPalacePUID));
               break;
            }
            case cUnitTypeypWCConfucianAcademy2:
            case cUnitTypeypWCConfucianAcademy3:
            case cUnitTypeypWCConfucianAcademy4:
            case cUnitTypeypWCConfucianAcademy5:
            {
               gConfucianAcademyPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gConfucianAcademyPUID));
               break;
            }
            case cUnitTypeypWCTempleOfHeaven2:
            case cUnitTypeypWCTempleOfHeaven3:
            case cUnitTypeypWCTempleOfHeaven4:
            case cUnitTypeypWCTempleOfHeaven5:
            {
               gTempleOfHeavenPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gTempleOfHeavenPUID));
               break;
            }
            case cUnitTypeypWCPorcelainTower2:
            case cUnitTypeypWCPorcelainTower3:
            case cUnitTypeypWCPorcelainTower4:
            case cUnitTypeypWCPorcelainTower5:
            {
               gPorcelainTowerPUID = buildingPUID;
               xsEnableRule("porcelainTowerTacticMonitor");
               debugCore("Wonder I built: " + kbGetProtoUnitName(gPorcelainTowerPUID));
               break;
            }
            }
         }
         else if ((cMyCiv == cCivIndians) || (cMyCiv == cCivSPCIndians))
         {
            switch (buildingPUID)
            {
            case cUnitTypeypWIAgraFort2:
            case cUnitTypeypWIAgraFort3:
            case cUnitTypeypWIAgraFort4:
            case cUnitTypeypWIAgraFort5:
            {
               gAgraFortPUID = buildingPUID;
               xsEnableRule("agraFortUpgradeMonitor");
               debugCore("Wonder I built: " + kbGetProtoUnitName(gAgraFortPUID));
               break;
            }
            case cUnitTypeypWICharminarGate2:
            case cUnitTypeypWICharminarGate3:
            case cUnitTypeypWICharminarGate4:
            case cUnitTypeypWICharminarGate5:
            {
               gCharminarGatePUID = buildingPUID;
               xsEnableRule("mansabdarMonitor");
               debugCore("Wonder I built: " + kbGetProtoUnitName(gCharminarGatePUID));
               break;
            }
            case cUnitTypeypWIKarniMata2:
            case cUnitTypeypWIKarniMata3:
            case cUnitTypeypWIKarniMata4:
            case cUnitTypeypWIKarniMata5:
            {
               gKarniMataPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gKarniMataPUID));
               break;
            }
            case cUnitTypeypWITajMahal2:
            case cUnitTypeypWITajMahal3:
            case cUnitTypeypWITajMahal4:
            case cUnitTypeypWITajMahal5:
            {
               gTajMahalPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gTajMahalPUID));
               break;
            }
            case cUnitTypeypWITowerOfVictory2:
            case cUnitTypeypWITowerOfVictory3:
            case cUnitTypeypWITowerOfVictory4:
            case cUnitTypeypWITowerOfVictory5:
            {
               gTowerOfVictoryPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gTowerOfVictoryPUID));
               break;
            }
            }
         }
         else // We're Japanese.
         {
            switch (buildingPUID)
            {
            case cUnitTypeypWJGiantBuddha2:
            case cUnitTypeypWJGiantBuddha3:
            case cUnitTypeypWJGiantBuddha4:
            case cUnitTypeypWJGiantBuddha5:
            {
               gGreatBuddhaPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gGreatBuddhaPUID));
               break;
            }
            case cUnitTypeypWJGoldenPavillion2:
            case cUnitTypeypWJGoldenPavillion3:
            case cUnitTypeypWJGoldenPavillion4:
            case cUnitTypeypWJGoldenPavillion5:
            {
               gGoldenPavilionPUID = buildingPUID;
               // The default tactic of the Golden Pavilion is good otherwise (ranged damage).
               if (cDifficultyCurrent < gDifficultyExpert)
               {
                  int goldenPavilionID = getUnit(gGoldenPavilionPUID, cMyID, cUnitStateAlive);
                  // It's nearly impossible that this fails of course.
                  if (goldenPavilionID >= 0)
                  {
                     aiUnitSetTactic(goldenPavilionID, cTacticUnitHitpoints);
                  }
               }
               xsEnableRule("advancedArsenalUpgradeMonitor");
               debugCore("Wonder I built: " + kbGetProtoUnitName(gGoldenPavilionPUID));
               break;
            }
            case cUnitTypeypWJShogunate2:
            case cUnitTypeypWJShogunate3:
            case cUnitTypeypWJShogunate4:
            case cUnitTypeypWJShogunate5:
            {
               gTheShogunatePUID = buildingPUID;
               xsEnableRule("daimyoMonitor");
               debugCore("Wonder I built: " + kbGetProtoUnitName(gTheShogunatePUID));
               break;
            }
            case cUnitTypeypWJToriiGates2:
            case cUnitTypeypWJToriiGates3:
            case cUnitTypeypWJToriiGates4:
            case cUnitTypeypWJToriiGates5:
            {
               gToriiGatesPUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gToriiGatesPUID));
               break;
            }
            case cUnitTypeypWJToshoguShrine2:
            case cUnitTypeypWJToshoguShrine3:
            case cUnitTypeypWJToshoguShrine4:
            case cUnitTypeypWJToshoguShrine5:
            {
               gToshoguShrinePUID = buildingPUID;
               debugCore("Wonder I built: " + kbGetProtoUnitName(gToshoguShrinePUID));
               break;
            }
            }
         }
      }

      gAgeUpResearchPlan = -1;
      // event.age_up — pacing-budget probe; records the wall-clock time
      // (ms) at which this AI completed aging up to the new age.
      llProbe("event.age_up",
         "age=" + kbGetAge() +
         " t=" + xsGetTime());
      // LL-AGED probe — pairs with LL-AGE. Includes full resource + pop
      // snapshot so post-match timelines can chart economic state at each
      // age transition per AI.
      llProbe("econ.aged",
         "now=" + kbGetAge() +
         " food=" + kbResourceGet(cResourceFood) +
         " wood=" + kbResourceGet(cResourceWood) +
         " gold=" + kbResourceGet(cResourceGold) +
         " pop=" + kbGetPop() +
         " vills=" + kbUnitCount(cMyID, gEconUnit, cUnitStateAlive) +
         " armyPop=" + aiGetMilitaryPop() +
         " score=" + aiGetScore(cMyID));
   }
   else if (civIsAsian() == true)
   {
      buildingPUID = aiPlanGetVariableInt(planID, cBuildPlanBuildingTypeID, 0);
      debugCore("We are planning to construct this Wonder : " + kbGetProtoUnitName(buildingPUID));
   }

   // Force an update of resource distribution to prepare for stuffs after aging up.
   if (cDifficultyCurrent < cDifficultyHard) // Enhanced
   {
      return;
   }
   if ((state == cPlanStateResearch) || (state == cPlanStateBuild))
   {
      if (xsIsRuleEnabled("ageTransitionManager") == false)
      {
         xsEnableRule("ageTransitionManager");
         // Potential performance drop here, don't execute in the same run.
         //ageTransitionManager();
      }
   }
}

//==============================================================================
// updateChosenAfricanAlliances
//==============================================================================
void updateChosenAfricanAlliances()
{
   switch (kbGetAge())
   {
   case cAge2:
   {
      if (cMyCiv == cCivDEHausa)
      {
         if (kbTechGetStatus(cTechDEAllegianceBerber2) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceBerbersIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceBerbersIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceHausa2) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceHausaIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceHausaIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceSonghai2) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSonghaiIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSonghaiIndex, false);
         }
         break;
      }
      else
      {
         if (kbTechGetStatus(cTechDEAllegianceSomali2) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSomalisIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSomalisIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegiancePortuguese2) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAlliancePortugueseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAlliancePortugueseIndex, false);
            xsEnableRule("arsenalUpgradeMonitor");
         }
         else if (kbTechGetStatus(cTechDEAllegianceSudanese2) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSudaneseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSudaneseIndex, false);
         }
         break;
      }
   }
   case cAge3:
   {
      if (cMyCiv == cCivDEHausa)
      {
         if (kbTechGetStatus(cTechDEAllegianceBerber3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceBerbersIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceBerbersIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceHausa3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceHausaIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceHausaIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceSonghai3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSonghaiIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSonghaiIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceAkan3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceAkanIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceAkanIndex, false);
         }
         break;
      }
      else
      {
         if (kbTechGetStatus(cTechDEAllegianceSomali3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSomalisIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSomalisIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegiancePortuguese3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAlliancePortugueseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAlliancePortugueseIndex, false);
            xsEnableRule("arsenalUpgradeMonitor");
         }
         else if (kbTechGetStatus(cTechDEAllegianceSudanese3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSudaneseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSudaneseIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceJesuit3) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceJesuitIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceJesuitIndex, false);
            xsEnableRule("churchUpgradeMonitor");
         }
         break;
      }
   }
   case cAge4:
   {
      if (cMyCiv == cCivDEHausa)
      {
         if (kbTechGetStatus(cTechDEAllegianceBerber4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceBerbersIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceBerbersIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceHausa4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceHausaIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceHausaIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceSonghai4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSonghaiIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSonghaiIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceAkan4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceAkanIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceAkanIndex, false);
         }
         break;
      }
      else
      {
         if (kbTechGetStatus(cTechDEAllegianceSomali4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSomalisIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSomalisIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegiancePortuguese4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAlliancePortugueseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAlliancePortugueseIndex, false);
            xsEnableRule("arsenalUpgradeMonitor");
         }
         else if (kbTechGetStatus(cTechDEAllegianceSudanese4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSudaneseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSudaneseIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceJesuit4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceJesuitIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceJesuitIndex, false);
            xsEnableRule("churchUpgradeMonitor");
         }
         else if (kbTechGetStatus(cTechDEAllegianceOromo4) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceOromoIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceOromoIndex, false);
         }
         break;
      }
   }
   case cAge5:
   {
      if (cMyCiv == cCivDEHausa)
      {
         if (kbTechGetStatus(cTechDEAllegianceBerber5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceBerbersIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceBerbersIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceHausa5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceHausaIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceHausaIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceSonghai5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSonghaiIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSonghaiIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceAkan5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceAkanIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceAkanIndex, false);
         }
            // We don't get any upgrades from the British so don't set the bool to false.
            else if (kbTechGetStatus(cTechDEAllegianceBritish5) == cTechStatusActive) 
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceBritishIndex, true);
            xsEnableRule("arsenalUpgradeMonitor");
         }
         break;
      }
      else if (cMyCiv == cCivDEEthiopians)
      {
         if (kbTechGetStatus(cTechDEAllegianceSomali5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSomalisIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSomalisIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegiancePortuguese5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAlliancePortugueseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAlliancePortugueseIndex, false);
            xsEnableRule("arsenalUpgradeMonitor");
         }
         else if (kbTechGetStatus(cTechDEAllegianceSudanese5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceSudaneseIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceSudaneseIndex, false);
         }
         else if (kbTechGetStatus(cTechDEAllegianceJesuit5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceJesuitIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceJesuitIndex, false);
            xsEnableRule("churchUpgradeMonitor");
         }
         else if (kbTechGetStatus(cTechDEAllegianceOromo5) == cTechStatusActive)
         {
            xsArraySetBool(gAfricanAlliancesAgedUpWith, cAllianceOromoIndex, true);
            xsArraySetBool(gAfricanAlliancesUpgrades, cAllianceOromoIndex, false);
         }
         break;
      }
   }
   }
}

//==============================================================================
// age2Monitor
// Watch for us reaching age 2.
//==============================================================================
rule age2Monitor
inactive
group tcComplete
minInterval 5
{
   int age = kbGetAge();
   if (age >= cAge2) // We're in age 2
   {
      debugCore("");
      debugCore("*** We're in age 2!!!");
      gAgeUpTime = xsGetTime();
      gAgeUpPlanTime = 0;

      // These numbers belonged to the now deprecated eco system
      // They're just used by other eco plans not being the main gathering.
      kbSetTargetSelectorFactor(cTSFactorDistance, -40.0);
      kbSetTargetSelectorFactor(cTSFactorPoint, 10.0);
      kbSetTargetSelectorFactor(cTSFactorTimeToDone, 0.0);
      kbSetTargetSelectorFactor(cTSFactorBase, 100.0);
      kbSetTargetSelectorFactor(cTSFactorDanger, -40.0);
      
      aiPopulatePoliticianList(); // Update the list of possible age-up choices we have now.
      updateSettlersAndPopManager();
      updateWantedTowers();

      if ((xsIsRuleEnabled("militaryManager") == false) &&
          (cvOkToTrainArmy == true))
      {
         xsEnableRule("militaryManager");
         xsEnableRule("accountForOutlawsMilitaryPop");
         militaryManager(); // Call instantly to get started.
      }

      // If Florence Nightingale is available, use it.
      if (cMyCiv == cCivBritish)
      {
         xsEnableRule("florenceNightingaleMonitor");
      }

      if (cMyCiv == cCivXPSioux) {
         xsEnableRule("lakotaTeePeeManager");
      }
      
      if (cvOkToAttack == true)
      {
         if ((cDifficultyCurrent == cDifficultyEasy) &&
             (gDelayAttacks == true))
         {
            xsEnableRule("delayAttackMonitor"); // Wait until I am attacked or we've reached Age4, then let slip the hounds of war.
      }
         else if (cDifficultyCurrent != cDifficultySandbox) // We never attack on Easy.
         {
            xsEnableRule("mostHatedEnemy"); // Picks a target for us to attack.
            mostHatedEnemy(); // Instantly get a target so our managers have something to work with.
            xsEnableRule("attackManager"); // Land attacking / defending allies.
            if (gNavyMap == true)
            {
               xsEnableRule("waterAttack"); // Water attacking.
            }
         }
      }
      
      if (gNavyMap == true)
      {
         xsEnableRule("waterDefend");
      }
      
      if (gIslandMap == true)
      {
         xsEnableRule("transportMonitor");
      }
      
      if ((gGoodFishingMap == true) &&
          (cDifficultyCurrent >= cDifficultyModerate))
      {
         xsEnableRule("fishingBoatUpgradeMonitor");
      }
      
      if (cvOkToTrainNavy == true)
      {
         //xsEnableRule("navyManager");
      }
      
      setupNativeUpgrades();

      if (getGaiaUnitCount(cUnitTypeSocketCree) > 0)
      {
         xsEnableRule("maintainCreeCoureurs");
      }

      if (getGaiaUnitCount(cUnitTypedeSocketBerbers) > 0)
      {
         xsEnableRule("maintainBerberNomads");
      }

      if (civIsEuropean() == true)
      {
         xsEnableRule("ransomExplorer");
      }

      xsEnableRule("commanderRecoveryMonitor");
      
      if ((cvOkToTrainArmy == true) && (civIsNative() == true))
      {
         if (cMyCiv != cCivXPSioux)
         {
            xsEnableRule("useWarParties");
         }
         else if (cDifficultyCurrent >= cDifficultyModerate)
         {
            xsEnableRule("useWarPartiesLakota");
         }
      }
      
      // Africans handle their native warriors inside of influenceManager.
      if ((civIsAfrican() == false) &&
          (cvOkToTrainArmy == true))
      {
         xsEnableRule("nativeMonitor");
      }

      if (gNumberTradeRoutes > 0)
      {
         xsEnableRule("tradeRouteUpgradeMonitor");
         if (cDifficultyCurrent >= cDifficultyEasy)
         {
            xsEnableRule("tradeRouteTacticMonitor");
      }
      }

      // Don't activate the big button monitors on easy(sandbox) since we won't have enough Villagers to pass the initial check.

      if ((cMyCiv == cCivXPAztec) && (cDifficultyCurrent >= cDifficultyEasy))
      {
         xsEnableRule("bigButtonAztecMonitor");
      }

      if ((cMyCiv == cCivXPSioux) && (cDifficultyCurrent >= cDifficultyEasy))
      {
         xsEnableRule("bigButtonLakotaMonitor");
      }

      if ((cMyCiv == cCivXPIroquois) && (cDifficultyCurrent >= cDifficultyEasy))
      {
         xsEnableRule("bigButtonHaudenosauneeMonitor");
      }

      xsEnableRule("settlerUpgradeMonitor");

      if (cMyCiv == cCivDESwedish)
      {
         xsEnableRule("arsenalUpgradeMonitor");
         xsEnableRule("advancedArsenalUpgradeMonitor");
      }
      if (civIsAsian() == true && cvOkToBuildConsulate == true)
      {
         xsEnableRule("consulateMonitor");
      }

      // Enable training units and researching techs with influence resource.
      if (civIsAfrican() == true)
      {
         if (cvOkToTrainArmy == true)
         {
            xsEnableRule("influenceManager");
         }
         xsEnableRule("allianceUpgradeMonitor");
         updateChosenAfricanAlliances();
      }

      // Allow Abuns to gather from Mountain Monasteries and switch the MM tactic to 50% Influence/Coin.
      if (cMyCiv == cCivDEEthiopians)
      {
         aiAddGathererType(cUnitTypedeAbun);
         xsEnableRule("setMountainMonasteryTactic");
      }

      if (cDifficultyCurrent >= cDifficultyHard) // Enhanced - changed from gDifficultyExpert
      {
         // Avoid planning for age upgrades until 10 minutes passed after aging up. -- Now 2
         if ((btRushBoom > 0.0) && (age == cAge2))
         {
            gAgeUpPlanTime = xsGetTime() + 2 * 60 * 1000; // Enhanced age up!
         }
      }

      if (gLastAttackMissionTime < 0)
      {
         // Pretend they all fired 3 minutes ago, even if that's a negative number.
         gLastAttackMissionTime = xsGetTime() - 180000;
      }
      if (gLastDefendMissionTime < 0)
      {
         // Actually, start defense ratings at 100% charge, i.e. 5 minutes since last one.
         gLastDefendMissionTime = xsGetTime() - 300000;
      }

      updateResourceDistribution(true);
      setUnitPickerPreference(gLandUnitPicker);

      if (cvOkToFortify == true)
      {
         xsEnableRule("towerManager");
      }
      
      if (cvOkToExplore == true)
      {
         findEnemyBase(); // Create a one-off explore plan to probe the likely enemy base location.
         
         if ((gIslandMap == true) && (gSPC == false))
         {
            xsEnableRule("islandExploreMonitor");
         }
      }
      
      xsEnableRule("rescueExplorer");
      xsEnableRule("settlerUpgradeMonitor");
      xsEnableRule("healerMonitor");
      xsEnableRule("legendaryEliteGuardMonitor");

      if (cRandomMapName == "euitalianwars")
      {
         xsEnableRule("cityStateMonitor");
         xsEnableRule("cityTowerUpgradeMonitor");
      }
      
      xsEnableRule("age3Monitor");
      xsDisableSelf();
      debugCore("*** End of age2Monitor rule");
      debugCore("");
   }
}

//==============================================================================
// age3Monitor
// Watch for us reaching age 3.
//==============================================================================
rule age3Monitor
inactive
minInterval 10
{
   if (kbGetAge() >= cAge3)
   {
      debugCore("");
      debugCore("*** We're in age 3!!!");
      gAgeUpTime = xsGetTime();
      gAgeUpPlanTime = 0;
      
      // Walls rules: enable late-game walling in Fortress so walls actually
      // complete before the match ends (was only triggered at Age 4, too
      // late — replay showed walls barely progressing by Industrial).
      xsEnableRule("delayWallsNew");
      //xsEnableRule("enhancedWalls");
      xsEnableRule("forwardBaseWall");
      //xsEnableRule("getBackToWork");
      xsEnableRule("fortManager");

      // if (gIslandMap == true)
      // {
      //    xsEnableRule("warShipManager");
      //    llVerboseEcho("Enabling the new Navy Manager.");
      // }

      // Make sure Germans build settler wagons...
      if (cMyCiv == cCivGermans) {
         xsEnableRule("germanVillagerManager");
      }
      // Make sure Spanish maintain Missionaries and War Dogs...
      if (cMyCiv == cCivSpanish) {
         xsEnableRule("missionaryManager");
         xsEnableRule("warDogManager");
      }
      // Make sure Italians maintain Architects...
      if (cMyCiv == cCivDEItalians) {
         xsEnableRule("architectManager");
      }
      // Make sure Aztecs maintain Eagle Scouts...
      if (cMyCiv == cCivXPAztec) {
         xsEnableRule("eagleScoutManager");
      }
      // Make sure Chinese maintain disciples...
      if (cMyCiv == cCivChinese) {
         xsEnableRule("chineseDiscipleManager");
      }

      xsEnableRule("livestockMonitor");
      xsEnableRule("slaughterMonitor");

      aiPopulatePoliticianList(); // Update the list of possible age-up choices we have now.
      updateSettlersAndPopManager();
      updateWantedTowers();

      if (cMyCiv == cCivOttomans)
      {
         // It only makes sense to keep this spawning tracker enabled if we're not allowed to reach the build limit of our
         // gEconUnit.
         int comparisonDifficulty = gSPC == true ? cDifficultyExpert : cDifficultyHard;
         if ((cDifficultyCurrent >= comparisonDifficulty) && (cvMaxCivPop == -1))
         {
            debugCore("DISABLING Rule: 'toggleAutomaticSettlerSpawning' because we're allowed to reach " +
               "the build limit of gEconUnit");
            xsDisableRule("toggleAutomaticSettlerSpawning");
         }
      }

      // Enable the Tower upgrade monitor for everybody apart from Lakota, they only use the War Hut monitor.
      if (cMyCiv != cCivXPSioux)
      {
         xsEnableRule("towerUpgradeMonitor");
      }

      // Enable the rule to upgrade the War Huts, this is done separately from the other Towers.
      if ((cMyCiv == cCivXPSioux) || (cMyCiv == cCivXPAztec))
      {
         xsEnableRule("warHutUpgradeMonitor");
      }

      // Switch from war hut to nobles hut.
      if (cMyCiv == cCivXPAztec)
      {
         gTowerUnit = cUnitTypeNoblesHut;
      }

      if (cMyCiv == cCivDEInca)
      {
         // The Stronghold can be considered as both a Tower and a Fort, if we're allowed to make one enable it.
         if ((cvOkToBuildForts == true) || (cvOkToFortify == true)) 
         {
            xsEnableRule("strongholdConstructionMonitor");
         }
         xsEnableRule("strongholdUpgradeMonitor");
         if (cDifficultyCurrent >= cDifficultyEasy)
         {
            xsEnableRule("bigButtonIncaMonitor"); // We only research techs locked behind Fortress so enable it here.
         }
      }

      // Enable Arsenal upgrades for Europeans and Japanese (Dutch Consulate Arsenal).
      if ((civIsEuropean() == true) ||
          ((cMyCiv == cCivJapanese) || (cMyCiv == cCivSPCJapanese) || (cMyCiv == cCivSPCJapaneseEnemy)))
      {
         xsEnableRule("arsenalUpgradeMonitor");
      }
      
      if (civIsEuropean() == true)
      {
         //xsEnableRule("advancedArsenalUpgradeMonitor");
         //xsEnableRule("millUpgradeMonitor");
         //xsEnableRule("estateUpgradeMonitor");
         if ((cvOkToBuild == true) && 
             (cvOkToBuildForts == true))
         {
            xsEnableRule("forwardBaseManager");
         }
      }

      // Enable the baseline Church (Cathedral) upgrade monitor.
      if (cMyCiv == cCivDEMexicans)
      {
         xsEnableRule("churchUpgradeMonitor");
      }

      // // Enable Monastery upgrades.
      // if (civIsAsian() == true)
      // {
      //    xsEnableRule("monasteryUpgradeMonitor");
      //    xsEnableRule("ricePaddyUpgradeMonitor");	
      // }

      // // Enable some native upgrades...
      // if (civIsNative() == true) {
      //    xsEnableRule("nativeEstateUpgradeMonitor");
      //    xsEnableRule("farmUpgradeMonitor");
      //    xsEnableRule("nativeFarmUpgradeMonitor");
      // }

      // Enable navy upgrades
      if ((gNavyMap == true) &&
          (cvOkToTrainNavy == true) &&
          (civIsNative() == false))
      {
      xsEnableRule("navyUpgradeMonitor");
      if ((cRandomMapName == "amazonia") || (cRandomMapName == "amazonialarge") || (cRandomMapName == "caribbean") || (cRandomMapName == "caribbeanlarge") ||
		(cRandomMapName == "ceylon") || (cRandomMapName == "ceylonlarge") ||
		(cRandomMapName == "honshu") || (cRandomMapName == "honshularge") || (cRandomMapName == "euarchipelago") ||
		(cRandomMapName == "euarchipelagolarge") || (cRandomMapName == "eusardiniacorsica")|| 
		(cRandomMapName == "eusardiniacorsicalarge") || (cRandomMapName == "eumediterranean")|| 
		(cRandomMapName == "eumediterraneanlarge")) {
         xsEnableRule("transportMilitaryNaval");
         xsEnableRule("dockManager");
      }
      }

      if (civIsAfrican() == true)
      {
         updateChosenAfricanAlliances();
      }

      xsEnableRule("age4Monitor");
      xsDisableSelf();
      debugCore("*** End of age3Monitor rule");
      debugCore("");
   }
}

//==============================================================================
// age4Monitor
// Watch for us reaching age 4.
//==============================================================================
rule age4Monitor
inactive
minInterval 10
{
   if (kbGetAge() >= cAge4)
   {
      debugCore("");
      debugCore("*** We're in age 4!!!");
      gAgeUpTime = xsGetTime();
      gAgeUpPlanTime = 0;

      aiPopulatePoliticianList(); // Update the list of possible age-up choices we have now.
      updateSettlersAndPopManager();
      updateWantedTowers();
      xsEnableRule("delayWallsNew");
      //xsEnableRule("enhancedWalls");
      // xsEnableRule("forwardBaseWall");
      xsEnableRule("establishTradePostsWithNatives");
      xsEnableRule("millManager");
      //xsEnableRule("healInjuredUnits");
	  
	  // Enhanced rules...

      // Enable the baseline Church upgrade monitor.
      if ((civIsEuropean() == true) && (cMyCiv != cCivDEMexicans))
      {
         xsEnableRule("churchUpgradeMonitor");
      }

      if ((civIsEuropean() == true))
      {
         xsEnableRule("millUpgradeMonitor");
         xsEnableRule("estateUpgradeMonitor");
         xsEnableRule("advancedArsenalUpgradeMonitor");
         // Spanish already have their own custom logic for Missionaries.
         if (cMyCiv != cCivSpanish) {
            xsEnableRule("priestMonkManager");
         }
      }
      
      if (cvOkToExplore == true)
      {
         xsEnableRule("balloonMonitor");
      }

      if (cMyCiv == cCivPortuguese) {
         xsEnableRule("feitoriaTCMonitor");
      }

      if (cMyCiv == cCivJapanese) {
         xsEnableRule("japaneseShinobiManager");
      }
      
      // Enable sacred field handling for Indians
      if (cMyCiv == cCivIndians)
      {
         xsEnableRule("sacredFieldMonitor");
      }

      if (cMyCiv == cCivDEInca)
      {
         xsEnableRule("tamboUpgradeMonitor");
      }

      if (cDifficultyCurrent >= cDifficultyModerate)
      { 
         // Enable shrine upgrade for Japanese.
         if ((cMyCiv == cCivJapanese) || (cMyCiv == cCivSPCJapanese) || (cMyCiv == cCivSPCJapaneseEnemy))
         {
            xsEnableRule("shrineUpgradeMonitor");
         }
      }

      // Enable Monastery upgrades.
      if (civIsAsian() == true)
      {
         xsEnableRule("monasteryUpgradeMonitor");
         xsEnableRule("ricePaddyUpgradeMonitor");	
      }

      // Enable some native upgrades...
      if (civIsNative() == true) {
         xsEnableRule("nativeEstateUpgradeMonitor");
         xsEnableRule("farmUpgradeMonitor");
         xsEnableRule("nativeFarmUpgradeMonitor");
      }

      if (civIsAfrican() == true)
      {
         updateChosenAfricanAlliances();
      }

      xsEnableRule("age5Monitor");
      xsDisableSelf();
      debugCore("*** End of age4Monitor rule");
      debugCore("");
   }
}

//==============================================================================
// age5Monitor
// Watch for us reaching age 5.
//==============================================================================
rule age5Monitor
inactive
minInterval 10
{
   if (kbGetAge() >= cAge5)
   {
      debugCore("");
      debugCore("*** We're in age 5!!!");
      gAgeUpTime = xsGetTime();
      gAgeUpPlanTime = 0;

      updateSettlersAndPopManager();
      updateWantedTowers();
      xsEnableRule("royalDecreeMonitor");
      xsEnableRule("maxOutThatMilitaryBaby");
      xsEnableRule("maxOutVillagers");
      //xsEnableRule("getBackToWork");
      xsEnableRule("factoryUpgradeMonitorNew");
	   xsEnableRule("fortUpgradeMonitor");
      xsEnableRule("maxTowerManager");
      xsEnableRule("militaryBuildingsManager");
      // Wait five minutes if we started the game in Age 5.
      // if (xsGetTime() > 5 * 60 * 1000) {
      //    xsEnableRule("enhancedWalls");
      // } 
      //xsEnableRule("forwardBaseWall");
      //xsEnableRule("factoryWall");

      // Make sure Germans build settler wagons...
      if (cMyCiv == cCivGermans) {
         xsEnableRule("germanVillagerManager");
      }

	   if (xsIsRuleEnabled("fortManager") == false)
      {
         xsEnableRule("fortManager");
         llVerboseEcho("Enabling the new Fort Manager.");
      }
      // Maintain the maximum number of forts...
      if (civIsEuropean() == true) {
         xsEnableRule("rebuildLostForts");
      }
	  
	  // Walls rules...
     if (kbTechGetStatus(cTechBastion) != cTechStatusActive) {
	      xsEnableRule("bastionUpgradeMonitor");
     }

      if (gIslandMap == true && xsIsRuleEnabled("transportMilitaryNaval") == false)
      {
         if ((cRandomMapName == "amazonia") || (cRandomMapName == "amazonialarge") || (cRandomMapName == "caribbean") || (cRandomMapName == "caribbeanlarge") ||
         (cRandomMapName == "ceylon") || (cRandomMapName == "ceylonlarge") ||
         (cRandomMapName == "honshu") || (cRandomMapName == "honshularge") || (cRandomMapName == "euarchipelago") ||
         (cRandomMapName == "euarchipelagolarge") || (cRandomMapName == "eusardiniacorsica")|| 
         (cRandomMapName == "eusardiniacorsicalarge") || (cRandomMapName == "eumediterranean")|| 
         (cRandomMapName == "eumediterraneanlarge")) {
            xsEnableRule("transportMilitaryNaval");
         }
         llVerboseEcho("Enabling the new Island Invasion logic.");
      }

      if (civIsEuropean() == true)
      {
         xsEnableRule("capitolConstructionMonitor");
         xsEnableRule("capitolUpgradeMonitor");
      }

      // Upgrade Native Capitol Upgrades	  
      if (civIsNative() == true) {
         xsEnableRule("nativeCapitolUpgradeMonitor");
      }

      // Enable Upgrade Asian Capitol Upgrades
      if (civIsAsian() == true) {
         xsEnableRule("asianCapitolUpgradeMonitor");
         xsEnableRule("monasteryMonitor");
      }

      if (civIsAfrican() == true)
      {
         updateChosenAfricanAlliances();
      }

      xsDisableSelf();
      debugCore("*** End of age5Monitor rule");
      debugCore("");
   }
}

//==============================================================================
// regicideMonitor
// Pop the regent in the castle.
//==============================================================================
rule regicideMonitor
inactive
minInterval 10
{
   // If the castle is up, put the guy in it

   if (kbUnitCount(cMyID, cUnitTypeypCastleRegicide, cUnitStateAlive) > 0)
   {
      // Gotta find the castle.
      static int castleQueryID = -1;
      // If we don't have the query yet, create one.
      if (castleQueryID < 0)
      {
         castleQueryID = kbUnitQueryCreate("castleGetUnitQuery");
         kbUnitQuerySetIgnoreKnockedOutUnits(castleQueryID, true);
      }
      // Define a query to get all matching units.
      if (castleQueryID != -1)
      {
         kbUnitQuerySetPlayerRelation(castleQueryID, -1);
         kbUnitQuerySetPlayerID(castleQueryID, cMyID);
         kbUnitQuerySetUnitType(castleQueryID, cUnitTypeypCastleRegicide);
         kbUnitQuerySetState(castleQueryID, cUnitStateAlive);
      }
      else
      {
         return;
      }

      // Gotta find the regent.
      static int regentQueryID = -1;
      if (regentQueryID < 0) // First run.
      {
         regentQueryID = kbUnitQueryCreate("regentGetUnitQuery");
         kbUnitQuerySetIgnoreKnockedOutUnits(regentQueryID, true);
      }
      // Define a query to get all matching units.
      if (regentQueryID != -1)
      {
         kbUnitQuerySetPlayerRelation(regentQueryID, -1);
         kbUnitQuerySetPlayerID(regentQueryID, cMyID);
         kbUnitQuerySetUnitType(regentQueryID, cUnitTypeypDaimyoRegicide);
         kbUnitQuerySetState(regentQueryID, cUnitStateAlive);
      }
      else
      {
         return;
      }

      kbUnitQueryResetResults(castleQueryID);
      kbUnitQueryResetResults(regentQueryID);

      kbUnitQueryExecute(castleQueryID);
      kbUnitQueryExecute(regentQueryID);

      aiTaskUnitWork(kbUnitQueryGetResult(regentQueryID, 0), kbUnitQueryGetResult(castleQueryID, 0));
   }
   else
   {
      xsDisableSelf();
   }
}