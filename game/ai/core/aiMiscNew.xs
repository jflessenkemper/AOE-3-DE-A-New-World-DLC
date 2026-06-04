//==============================================================================
/* enhancedInit()
   This function is called before the loader file's preInit() function is 
   called in order to setup necessary naval logic and other enhancements.
*/
//==============================================================================
void enhancedInit(void)
{
   // Reference the starting XP values for each player.
   // TODO: Investigate if there is a cleaner way to do this in XS scripting. Such as a keyed dictionary, object array, etc...
   // if (gXpValuePlayer1 == -1) {
   //    for (int player = 1; player < cNumberPlayers; player++) {
   //       int xpValue = kbResourceGetXP(player);
   //       if (player == 1) { gXpValuePlayer1 = xpValue; }
   //       if (player == 2) { gXpValuePlayer2 = xpValue; }
   //       if (player == 3) { gXpValuePlayer3 = xpValue; }
   //       if (player == 4) { gXpValuePlayer4 = xpValue; }
   //       if (player == 5) { gXpValuePlayer5 = xpValue; }
   //       if (player == 6) { gXpValuePlayer6 = xpValue; }
   //       if (player == 7) { gXpValuePlayer7 = xpValue; }
   //       if (player == 8) { gXpValuePlayer8 = xpValue; }
   //    }
   // }

   // Set early rush attempt based on civilization
   int rushRoll = aiRandInt(100);  // 0-99

   if ((cMyCiv == cCivXPAztec) ||
      (cMyCiv == cCivXPIroquois) ||
      (cMyCiv == cCivFrench) ||
      (cMyCiv == cCivRussians) ||
      (cMyCiv == cCivOttomans) ||
      (cMyCiv == cCivIndians) ||
      (cMyCiv == cCivDEMexicans))
   {
      // Top tier rush civs: 75% chance
      if (rushRoll < 75)
      {
         gEarlyRushAttempt = true;
         anwVerboseEcho("Early rush attempt ENABLED (top tier rush civ, rolled " + rushRoll + " < 75)");
      }
      else
      {
         gEarlyRushAttempt = false;
         anwVerboseEcho("Early rush attempt DISABLED (top tier rush civ, rolled " + rushRoll + " >= 75)");
      }
   }
   else
   {
      // Other civs: 40% chance
      if (rushRoll < 40)
      {
         gEarlyRushAttempt = true;
         anwVerboseEcho("Early rush attempt ENABLED (standard civ, rolled " + rushRoll + " < 40)");
      }
      else
      {
         gEarlyRushAttempt = false;
         anwVerboseEcho("Early rush attempt DISABLED (standard civ, rolled " + rushRoll + " >= 40)");
      }
   }

   if (gEarlyRushAttempt == true) {
      btRushBoom = btRushBoom + 0.2;
   }

   if (aiIsKOTHAllowed() == true) {
      xsEnableRule("kothManager");
      xsEnableRule("kothBaseManager");
      //xsEnableRule("checkEnemyNearKOTH");
   }

   // Enable new chats...
   xsEnableRule("myWallChat");
   xsEnableRule("enemyWallTaunt");
   //xsEnableRule("giveAdviceAndComments");
   xsEnableRule("boringChatter");
   xsEnableRule("manyPlayersComment");
   anwEnableLeaderQuoteRules();
   // Set the healing unit type.
   setHealingUnitType();
   xsEnableRule("healInjuredUnits");

   if ((cRandomMapName == "amazonia") || (cRandomMapName == "amazonialarge") || (cRandomMapName == "caribbean") || (cRandomMapName == "caribbeanlarge") ||
		(cRandomMapName == "ceylon") || (cRandomMapName == "ceylonlarge") || (cRandomMapName == "borneo") || (cRandomMapName == "borneolarge") ||
		(cRandomMapName == "honshu") || (cRandomMapName == "honshularge") || (cRandomMapName == "euarchipelago") ||
		(cRandomMapName == "euarchipelagolarge") || (cRandomMapName == "eusardiniacorsica")|| 
		(cRandomMapName == "eusardiniacorsicalarge") || (cRandomMapName == "eumediterranean")|| 
		(cRandomMapName == "eumediterraneanlarge") || (cRandomMapName == "eubaltic")|| 
		(cRandomMapName == "eubalticlarge") || (cRandomMapName == "indonesia") ||
		(cRandomMapName == "indonesialarge") || (cRandomMapName == "panama") ||
		(cRandomMapName == "panamalarge") || (cRandomMapName == "afswahilicoast") || (cRandomMapName == "afswahilicoastlarge"))
   {
      aiSetWaterMap(true);
      gWaterMap = true;
	   gNavyMap = true;
      gIslandMap = true;
      gGoodFishingMap = true;
      xsEnableRule("dockWagonBuildPlanManager");
      xsEnableRule("newNavyManager");
      xsEnableRule("waterPatrol");
      xsEnableRule("waterWarShipPlans");
      xsEnableRule("warShipManager");
      xsEnableRule("getRandomDockToAttack");
      xsEnableRule("maintainFishingBoats");
      xsEnableRule("islandBaseManager");
      //xsEnableRule("colonyCreationManager");
      //dockWagonHandler();
      if (getUnit(cUnitTypeAbstractNuggetWater, cPlayerRelationAny, cUnitStateAlive) > 0) {
         xsEnableRule("warshipNuggetCollector");
      }
      if ((cRandomMapName == "amazonia") || (cRandomMapName == "amazonialarge") || (cRandomMapName == "caribbean") || (cRandomMapName == "caribbeanlarge") ||
		(cRandomMapName == "ceylon") || (cRandomMapName == "ceylonlarge") ||
		(cRandomMapName == "honshu") || (cRandomMapName == "honshularge") || (cRandomMapName == "euarchipelago") ||
		(cRandomMapName == "euarchipelagolarge") || (cRandomMapName == "eusardiniacorsica")|| 
		(cRandomMapName == "eusardiniacorsicalarge") || (cRandomMapName == "eumediterranean")|| 
		(cRandomMapName == "eumediterraneanlarge")) {
         xsEnableRule("transportMilitaryNaval");
         xsEnableRule("invasionMilitaryManager");
      }
      if ((cRandomMapName == "euarchipelago") || (cRandomMapName == "euarchipelagolarge")) {
         xsEnableRule("archipelagoGo");
      }
      if ((cRandomMapName == "ceylon") || (cRandomMapName == "ceylonlarge") || (cRandomMapName == "afswahilicoast") ||
          (cRandomMapName == "afswahilicoastlarge")) {
         xsEnableRule("smallIslandMigration");
      }
   } else {
      gWaterMap = false;
	   gNavyMap = false;
      gIslandMap = false;
      gGoodFishingMap = false;
   }
   if ((cRandomMapName != "euarchipelago") && (cRandomMapName != "euarchipelagolarge")) {
      xsEnableRule("landPatrol");
   }
}
//==============================================================================
/* Monastery monitor
   Let's make sure we research those monastery techs!
*/
//==============================================================================
rule monasteryMonitor
inactive
minInterval 60
{
   int upgradePlanID = -1;
   int myMonasteryId = getUnit(cUnitTypeypMonastery, cMyID);

   if ((kbTechGetStatus(cTechypMonasteryCompunction) == cTechStatusActive) &&
       (((kbTechGetStatus(cTechypMonasteryJapaneseCombat) == cTechStatusActive) &&
       (kbTechGetStatus(cTechypMonasteryKillingBlowUpgrade) == cTechStatusActive) && 
       (kbTechGetStatus(cTechypMonasteryJapaneseHealing) == cTechStatusActive) &&
       (kbTechGetStatus(cTechypMonasteryRangedSplash) == cTechStatusActive) &&
       cMyCiv == cCivJapanese) ||
       ((kbTechGetStatus(cTechypMonasteryAttackSpeed) == cTechStatusActive) &&
       (kbTechGetStatus(cTechypMonasteryCriticalUpgrade) == cTechStatusActive) && 
       (kbTechGetStatus(cTechypMonasteryShaolinWarrior) == cTechStatusActive) &&
       (kbTechGetStatus(cTechypMonasteryDiscipleAura) == cTechStatusActive) &&
       cMyCiv == cCivChinese) ||
       ((kbTechGetStatus(cTechypMonasteryStompUpgrade) == cTechStatusActive) &&
       (kbTechGetStatus(cTechypMonasteryIndianSpeed) == cTechStatusActive) && 
       (kbTechGetStatus(cTechypMonasteryPetAura) == cTechStatusActive) &&
       (kbTechGetStatus(cTechypMonasteryImprovedHealing) == cTechStatusActive) &&
       cMyCiv == cCivIndians))
   )
   {
      xsDisableSelf();
      return;
   }

   if (civIsAsian() == false)
   {
      xsDisableSelf();
      return;
   }

   // Build a monastery if one does not exist...
   if ( (kbUnitCount(cMyID, cUnitTypeypMonastery, cUnitStateABQ) < 1) && (aiPlanGetIDByTypeAndVariableType(cPlanBuild, cBuildPlanBuildingTypeID, cUnitTypeypMonastery) < 0) ) 
   {
      createSimpleBuildPlan(cUnitTypeypMonastery, 1, 80, true, cEconomyEscrowID, kbBaseGetMainID(cMyID), 1);
      anwVerboseEcho("Starting a new monastery build plan.");
   }
   
   // All
   researchSimpleTechByCondition(cTechypMonasteryCompunction, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryCompunction) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);

   // Japanese
   researchSimpleTechByCondition(cTechypMonasteryJapaneseHealing, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryJapaneseHealing) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryJapaneseCombat, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryJapaneseCombat) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryKillingBlowUpgrade, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryKillingBlowUpgrade) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryRangedSplash, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryRangedSplash) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);

   // Chinese
   researchSimpleTechByCondition(cTechypMonasteryAttackSpeed, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryAttackSpeed) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryCriticalUpgrade, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryCriticalUpgrade) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryShaolinWarrior, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryShaolinWarrior) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryDiscipleAura, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryDiscipleAura) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);

   // Indians
   researchSimpleTechByCondition(cTechypMonasteryStompUpgrade, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryStompUpgrade) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryIndianSpeed, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryIndianSpeed) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryPetAura, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryPetAura) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
   researchSimpleTechByCondition(cTechypMonasteryImprovedHealing, 
   []() -> bool { return (kbTechGetStatus(cTechypMonasteryImprovedHealing) == cTechStatusObtainable); },
   cUnitTypeypMonastery, myMonasteryId, 75);
}
//==============================================================================
/* factoryUpgradeMonitorNew
   Let's make sure we research factory upgrades!
*/
//==============================================================================
rule factoryUpgradeMonitorNew
inactive
minInterval 45
{
   int upgradePlanID = -1;
   int myFactoryId = getUnit(cUnitTypeFactory, cMyID);

   if (kbUnitCount(cMyID, cUnitTypeFactory, cUnitStateABQ) < 1)
   {
      return;
   }

   if ((kbTechGetStatus(cTechFactorySteamPower) == cTechStatusActive) &&
       (kbTechGetStatus(cTechFactoryMassProduction) == cTechStatusActive) &&
       ((kbTechGetStatus(cTechImperialBombard) == cTechStatusActive) ||
        (kbTechGetStatus(cTechImperialCannon) == cTechStatusActive) ||
        (kbTechGetStatus(cTechImperialRocket) == cTechStatusActive)))
   {
      xsDisableSelf();
      return;
   }

   researchSimpleTechByCondition(cTechFactoryMassProduction, 
   []() -> bool { return (kbTechGetStatus(cTechFactoryMassProduction) == cTechStatusObtainable); },
   cUnitTypeFactory, myFactoryId, 75);
   researchSimpleTechByCondition(cTechFactorySteamPower, 
   []() -> bool { return (kbTechGetStatus(cTechFactorySteamPower) == cTechStatusObtainable); },
   cUnitTypeFactory, myFactoryId, 75);
   researchSimpleTechByCondition(cTechImperialBombard, 
   []() -> bool { return (kbTechGetStatus(cTechImperialBombard) == cTechStatusObtainable); },
   cUnitTypeFactory, myFactoryId, 75);
   researchSimpleTechByCondition(cTechFactoryMassProduction, 
   []() -> bool { return (kbTechGetStatus(cTechFactoryMassProduction) == cTechStatusObtainable); },
   cUnitTypeFactory, myFactoryId, 75);
   researchSimpleTechByCondition(cTechImperialCannon, 
   []() -> bool { return (kbTechGetStatus(cTechImperialCannon) == cTechStatusObtainable); },
   cUnitTypeFactory, myFactoryId, 75);
   researchSimpleTechByCondition(cTechImperialRocket, 
   []() -> bool { return (kbTechGetStatus(cTechImperialRocket) == cTechStatusObtainable); },
   cUnitTypeFactory, myFactoryId, 75);
}

//==============================================================================
// fortManager
// Tries to maintain as many gFortUnit as gNumForts says.
//==============================================================================
rule fortManager
inactive
minInterval 10
{
   int numberOfForts = kbUnitCount(cMyID, gFortUnit, cUnitStateABQ);
   int buildLimit = kbGetBuildLimit(cMyID, gFortUnit);
   int fortsWanted = anwGetWantedFortCount();

   if (buildLimit < 1 || fortsWanted < 1)
   {
      return;
   }

   // Don't make any more Fort build plans if we're already at our calculated limit.
   if (kbUnitCount(cMyID, gFortUnit, cUnitStateABQ) >= fortsWanted)
   {
      return;
   }
   anwVerboseEcho("Waiting to build a fort! Desired: "+fortsWanted+" Fort Limit: "+buildLimit+" Forts Constructed: "+numberOfForts+"");
   if ((aiPlanGetIDByTypeAndVariableType(cPlanBuild, cBuildPlanBuildingTypeID, gFortUnit) < 0) 
      && (numberOfForts < fortsWanted))
   {
      int fortBuildPlan = createSimpleBuildPlan(gFortUnit, 1, 100, false, cMilitaryEscrowID, kbBaseGetMainID(cMyID));
      //addBuilderToPlan(fortBuildPlan, cBuildPlanBuildingTypeID, 1);
      aiPlanAddUnitType(fortBuildPlan, cUnitTypeHero, 1, 1, 1);
      //aiTaskUnitWork(cUnitTypeExplorer, gFortUnit);
      anwVerboseEcho("Time to build a fort!");
   }
}
//==============================================================================
// dockManager
// Tries to maintain gDockUnits on naval maps.
//==============================================================================
rule dockManager
inactive
minInterval 10
{
   int numberOfDocks = kbUnitCount(cMyID, gDockUnit, cUnitStateABQ);
   int buildLimit = 7;//kbGetBuildLimit(cMyID, gDockUnit); Hard coded for now...

   // Don't make any more Dock build plans if we're already at our calculated limit.
   if (kbUnitCount(cMyID, gDockUnit, cUnitStateABQ) >= buildLimit)
   {
      return;
   }
   anwVerboseEcho("Waiting to build a dock! Dock Limit: "+buildLimit+"Docks Constructed: "+numberOfDocks+"");
   if ((aiPlanGetIDByTypeAndVariableType(cPlanBuild, cBuildPlanBuildingTypeID, gDockUnit) < 0) 
      && (numberOfDocks < buildLimit) && (kbGetAge() > cAge3) &&
      (gExcessResources == true))
   {
      int dockBuildPlan = createSpacedBuildPlan(gDockUnit, 1, 80, false, cMilitaryEscrowID, kbBaseGetMainID(cMyID),
      1, -1, true, 7.0);
      // int dockBuildPlan = createDetailedBuildPlan(gDockUnit, 1, 80, false, cMilitaryEscrowID, kbBaseGetMainID(cMyID)
      // , 1, -1, true, -1, 15.0);
      //addBuilderToPlan(dockBuildPlan, cBuildPlanBuildingTypeID, 1);
      //aiTaskUnitWork(cUnitTypeExplorer, gDockUnit);
      anwVerboseEcho("Time to build a dock!");
   }
}
//==============================================================================
// germanVillagerManager
// This rule intends to force Germans to make their unique villagers.
//==============================================================================
rule germanVillagerManager
inactive
minInterval 40
{
   static int settlerWagonPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypeSettlerWagon);
   if (limit < 1)
      return;

   if (settlerWagonPlan < 0 && (kbTechGetStatus(cTechHCGermantownFarmers) == cTechStatusActive))
   {
      settlerWagonPlan = createSimpleMaintainPlan(cUnitTypeSettlerWagon, limit, true, kbBaseGetMainID(cMyID), 1);
      aiPlanSetDesiredPriority(settlerWagonPlan, 80);
      xsDisableSelf();
   } else if (settlerWagonPlan > 0) {
      aiPlanSetVariableInt(settlerWagonPlan, cTrainPlanNumberToMaintain, 0, limit);
   }

   // Settler wagons gather quicker, so we want them instead.
   if ((kbTechGetStatus(cTechHCGermantownFarmers) == cTechStatusActive) && aiPlanGetActive(settlerWagonPlan)) {
      int villagerQuery = createSimpleUnitQuery(cUnitTypeSettler, cMyID, cUnitStateAlive);
      int wagonQuery = createSimpleUnitQuery(cUnitTypeSettlerWagon, cMyID, cUnitStateAlive);
      int numberFound = kbUnitQueryExecute(wagonQuery);
      int numberVillagersFound = kbUnitQueryExecute(villagerQuery);
      if (numberFound < limit && 
         (kbTechGetStatus(cTechHCGermantownFarmers) == cTechStatusActive)) {
         int numberAdjustment = limit - numberFound;
         for (i = 0; i < (numberAdjustment * 2); i++)
         {
            if (i >= numberVillagersFound) {
               return;
            }
            int unit = kbUnitQueryGetResult(villagerQuery, i);
            if (kbUnitGetProtoUnitID(unit) != cUnitTypeSettlerWagon && 
                kbUnitCount(cMyID, gFarmUnit, cUnitStateABQ) > 0) {
               aiTaskUnitDelete(kbUnitQueryGetResult(villagerQuery, i));
            }
         }
      }
   }
}
//==============================================================================
// chineseDiscipleManager
// This rule intends to force the Chinese to maintain disciples.
//==============================================================================
rule chineseDiscipleManager
inactive
minInterval 40
{
   static int disciplePlan = -1;
   int villagerPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypeypMonkDisciple);
   if (limit < 1)
      return;

   if (disciplePlan < 0)
   {
      disciplePlan = createSimpleMaintainPlan(cUnitTypeypMonkDisciple, limit, true, -1, 1);
      aiPlanSetDesiredPriority(disciplePlan, 85);
      aiPlanSetVariableInt(disciplePlan, cTrainPlanBuildFromType, 0, cUnitTypeHero);
      anwVerboseEcho("Disciples training!");
   }
   else
   {
      aiPlanSetVariableInt(disciplePlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
// japaneseShinobiManager
// This rule intends to force the Chinese to maintain disciples.
//==============================================================================
rule japaneseShinobiManager
inactive
minInterval 40
{
   static int shinobiPlan = -1;
   int villagerPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypeypShinobiHorse);
   if (limit < 1)
      return;

   if (shinobiPlan < 0)
   {
      shinobiPlan = createSimpleMaintainPlan(cUnitTypeypShinobiHorse, 10, true, -1, 1);
      aiPlanSetDesiredPriority(shinobiPlan, 85);
      aiPlanSetVariableInt(shinobiPlan, cTrainPlanBuildFromType, 0, cUnitTypeypShogunTokugawa);
      anwVerboseEcho("Shinobi training!");
   }
   else
   {
      aiPlanSetVariableInt(shinobiPlan, cTrainPlanNumberToMaintain, 0, 10);
   }
}
//==============================================================================
// eagleScoutManager
// This rule intends to force the Aztecs to maintain eagle scouts.
//==============================================================================
rule eagleScoutManager
inactive
minInterval 40
{
   static int eagleScoutPlan = -1;
   int villagerPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypedeEagleScout);
   if (limit < 1)
      return;

   if (eagleScoutPlan < 0)
   {
      eagleScoutPlan = createSimpleMaintainPlan(cUnitTypedeEagleScout, limit, true, -1, 1);
      aiPlanSetDesiredPriority(eagleScoutPlan, 85);
      aiPlanSetVariableInt(eagleScoutPlan, cTrainPlanBuildFromType, 0, cUnitTypeHero);
      anwVerboseEcho("Eagle Scout training!");
   }
   else
   {
      aiPlanSetVariableInt(eagleScoutPlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
// missionaryManager
// This rule intends to force the Spanish to maintain war dogs.
//==============================================================================
rule missionaryManager
inactive
minInterval 40
{
   static int missionaryPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypeMissionary);
   if (limit < 1)
      return;

   if (missionaryPlan < 0)
   {
      missionaryPlan = createSimpleMaintainPlan(cUnitTypeMissionary, limit, true, -1, 1);
      aiPlanSetDesiredPriority(missionaryPlan, 85);
      aiPlanSetVariableInt(missionaryPlan, cTrainPlanBuildFromType, 0, cUnitTypeChurch);
      anwVerboseEcho("Missionary training!");
   }
   else
   {
      aiPlanSetVariableInt(missionaryPlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
// priestMonkManager
// This rule allows the AI to maintain a couple of healers.
//==============================================================================
rule priestMonkManager
inactive
minInterval 40
{
   static int priestMonkPlan = -1;
   int limit = 2;
   int priestMonkPriority = 70;
   int age = kbGetAge();

   int priestBuildLimit = kbGetBuildLimit(cMyID, cUnitTypePriest);
   if (priestBuildLimit < 1)
      return;

   if (priestMonkPlan < 0)
   {
      priestMonkPlan = createSimpleMaintainPlan(cUnitTypePriest, limit, true, -1, 1);
      aiPlanSetDesiredPriority(priestMonkPlan, priestMonkPriority);
      aiPlanSetVariableInt(priestMonkPlan, cTrainPlanBuildFromType, 0, cUnitTypeChurch);
      anwVerboseEcho("Priest and Monk training!");
   }
   else
   {
      aiPlanSetDesiredPriority(priestMonkPlan, priestMonkPriority);
      aiPlanSetVariableInt(priestMonkPlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
// healInjuredUnits
// Find injured land military units and assign priests/monks to heal them.
//==============================================================================
rule healInjuredUnits
inactive
minInterval 20
{
   int unitQuery = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberUnits = kbUnitQueryExecute(unitQuery);

   int priestQuery = createSimpleUnitQuery(gHealingUnitType, cMyID, cUnitStateAlive); // cUnitTypePriest
   kbUnitQuerySetActionType(priestQuery, cActionTypeIdle);
   int numberPriests = kbUnitQueryExecute(priestQuery);

   for (int i = 0; i < numberUnits; i++)
   {
      int unitID = kbUnitQueryGetResult(unitQuery, i);
      //float unitHP = kbUnitGetCurrentHitpoints(unitID);

      // If the unit's health is less than 100%, it's injured.
      if (kbUnitGetHealth(unitID) < 1.0)
      {
         if (numberPriests > 0)
         {
            int priestID = kbUnitQueryGetResult(priestQuery, numberPriests - 1);
            aiTaskUnitSpecialPower(priestID, cProtoPowerPowerHeal, unitID);
            numberPriests--;
         } else {
            break;
         }
      }
   }
}
//==============================================================================
// feitoriaTCMonitor
// Portuguese should build maximum Town Centers when Feitoria is active.
//==============================================================================
rule feitoriaTCMonitor
inactive
maxInterval 60
{
   // Only for Portuguese.
   if (cMyCiv != cCivPortuguese)
   {
      xsDisableSelf();
      return;
   }

   // Check if Feitoria tech is active.
   if (kbTechGetStatus(cTechDEHCFeitorias) != cTechStatusActive)
   {
      return;
   }
   
   int limit = kbGetBuildLimit(cMyID, cUnitTypeTownCenter);
   int unitQuery = createSimpleUnitQuery(cUnitTypeTownCenter, cMyID, cUnitStateABQ);
   int numberFound = kbUnitQueryExecute(unitQuery);
   int age = kbGetAge();

   //anwVerboseEcho("Feitorias Activity: "+kbTechGetStatus(cTechDEHCFeitorias)+" Limit, numberFound:"+limit+""+numberFound+"");

   if ((numberFound < limit) && (age >= cAge4))
   {
      //anwVerboseEcho("Feitorias Creation: "+kbTechGetStatus(cTechDEHCFeitorias)+"");
      createSimpleBuildPlan(cUnitTypeTownCenter, 1, 100, false, cEconomyEscrowID, kbBaseGetMainID(cMyID), 1);
   }
}
//==============================================================================
// warDogManager
// This rule intends to force the Spanish to maintain war dogs.
//==============================================================================
rule warDogManager
inactive
minInterval 40
{
   static int warDogPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypeWarDog);
   if (limit < 1)
      return;

   if (warDogPlan < 0)
   {
      warDogPlan = createSimpleMaintainPlan(cUnitTypeWarDog, limit, true, -1, 1);
      aiPlanSetDesiredPriority(warDogPlan, 85);
      aiPlanSetVariableInt(warDogPlan, cTrainPlanBuildFromType, 0, cUnitTypeHero);
      anwVerboseEcho("War Dog training!");
   }
   else
   {
      aiPlanSetVariableInt(warDogPlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
// architectManager
// This rule intends to force the Italians to maintain architects.
//==============================================================================
rule architectManager
inactive
minInterval 40
{
   static int architectPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypedeArchitect);
   if (limit < 1)
      return;

   if (architectPlan < 0)
   {
      architectPlan = createSimpleMaintainPlan(cUnitTypedeArchitect, limit, true, -1, 1);
      aiPlanSetDesiredPriority(architectPlan, 85);
      aiPlanSetVariableInt(architectPlan, cTrainPlanBuildFromType, 0, cUnitTypeTownCenter);
      anwVerboseEcho("Architect training!");
   }
   else
   {
      aiPlanSetVariableInt(architectPlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
// royalDecreeMonitor
// This rule makes the AI research their unique church technologies and use
// their unique church units.
//==============================================================================
rule royalDecreeMonitor
inactive
minInterval 45
{
   int decreePlanID = -1;
   int myChurchId = getUnit(cUnitTypeChurch, cMyID);
   bool canDisableSelf = false;

   if ((civIsNative() == true) || (civIsAsian() == true))
   {
      xsDisableSelf();
      return;
   }

   switch(kbGetCiv())
   {
      case cCivBritish:
      {
         if ((kbTechGetStatus(cTechChurchThinRedLine) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchBlackWatch) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchRogersRangers) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEChurchRogersRangers) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchThinRedLine, 
         []() -> bool { return (kbTechGetStatus(cTechChurchThinRedLine) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchBlackWatch, 
         []() -> bool { return (kbTechGetStatus(cTechChurchBlackWatch) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchRogersRangers, 
         []() -> bool { return (kbTechGetStatus(cTechChurchRogersRangers) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEChurchRogersRangers, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchRogersRangers) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivDutch:
      {
         if ((kbTechGetStatus(cTechChurchCoffeeTrade) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchWaardgelders) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchStadholders) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEHCBlueGuards) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchCoffeeTrade, 
         []() -> bool { return (kbTechGetStatus(cTechChurchCoffeeTrade) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchWaardgelders, 
         []() -> bool { return (kbTechGetStatus(cTechChurchWaardgelders) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchStadholders, 
         []() -> bool { return (kbTechGetStatus(cTechChurchStadholders) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEHCBlueGuards, 
         []() -> bool { return (kbTechGetStatus(cTechDEHCBlueGuards) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivFrench:
      {
         if ((kbTechGetStatus(cTechChurchCodeNapoleon) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchGardeImperial1) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchGardeImperial2) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchGardeImperial3) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchCodeNapoleon, 
         []() -> bool { return (kbTechGetStatus(cTechChurchCodeNapoleon) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchGardeImperial1, 
         []() -> bool { return (kbTechGetStatus(cTechChurchGardeImperial1) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchGardeImperial2, 
         []() -> bool { return (kbTechGetStatus(cTechChurchGardeImperial2) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchGardeImperial3, 
         []() -> bool { return (kbTechGetStatus(cTechChurchGardeImperial3) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivGermans:
      {
         if ((kbTechGetStatus(cTechChurchTillysDiscipline) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchZweihander) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchWallensteinsContracts) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchTillysDiscipline, 
         []() -> bool { return (kbTechGetStatus(cTechChurchTillysDiscipline) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchWallensteinsContracts, 
         []() -> bool { return (kbTechGetStatus(cTechChurchWallensteinsContracts) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchZweihander, 
         []() -> bool { return (kbTechGetStatus(cTechChurchZweihander) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivOttomans:
      {
         if ((kbTechGetStatus(cTechChurchTufanciCorps) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchTopcuCorps) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchKapikuluCorps) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchTufanciCorps, 
         []() -> bool { return (kbTechGetStatus(cTechChurchTufanciCorps) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchKapikuluCorps, 
         []() -> bool { return (kbTechGetStatus(cTechChurchKapikuluCorps) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchTopcuCorps, 
         []() -> bool { return (kbTechGetStatus(cTechChurchTopcuCorps) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivPortuguese:
      {
         if ((kbTechGetStatus(cTechChurchBestieros) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchTowerAndSword) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchEconmediaManor) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchBestieros, 
         []() -> bool { return (kbTechGetStatus(cTechChurchBestieros) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchEconmediaManor, 
         []() -> bool { return (kbTechGetStatus(cTechChurchEconmediaManor) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchTowerAndSword, 
         []() -> bool { return (kbTechGetStatus(cTechChurchTowerAndSword) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivRussians:
      {
         if ((kbTechGetStatus(cTechChurchWesternization) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchPetrineReforms) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchKalmucks) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchBashkirPonies) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchWesternization, 
         []() -> bool { return (kbTechGetStatus(cTechChurchWesternization) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchPetrineReforms, 
         []() -> bool { return (kbTechGetStatus(cTechChurchPetrineReforms) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchKalmucks, 
         []() -> bool { return (kbTechGetStatus(cTechChurchKalmucks) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchBashkirPonies, 
         []() -> bool { return (kbTechGetStatus(cTechChurchBashkirPonies) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivSpanish:
      {
         if ((kbTechGetStatus(cTechChurchCorsolet) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchQuatrefage) == cTechStatusActive) &&
             (kbTechGetStatus(cTechChurchWildGeeseSpanish) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechChurchCorsolet, 
         []() -> bool { return (kbTechGetStatus(cTechChurchCorsolet) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchQuatrefage, 
         []() -> bool { return (kbTechGetStatus(cTechChurchQuatrefage) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchWildGeeseSpanish, 
         []() -> bool { return (kbTechGetStatus(cTechChurchWildGeeseSpanish) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechChurchWalloonGuards, 
         []() -> bool { return (kbTechGetStatus(cTechChurchWalloonGuards) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivDESwedish:
      {
         if ((kbTechGetStatus(cTechDEChurchGustavianGuards) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEChurchPikePush) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEChurchSavolaxJaegers) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechDEChurchGustavianGuards, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchGustavianGuards) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEChurchPikePush, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchPikePush) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEChurchSavolaxJaegers, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchSavolaxJaegers) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivDEItalians:
      {
         if ((kbTechGetStatus(cTechDEChurchCarabinieri) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEChurchRisorgimento) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEChurchPapacy) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechDEChurchCarabinieri, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchCarabinieri) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEChurchRisorgimento, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchRisorgimento) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEChurchPapacy, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchPapacy) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
      case cCivDEMaltese:
      {
         if ((kbTechGetStatus(cTechDEChurchTeutonicKnights) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEChurchRisorgimento) == cTechStatusActive) &&
             (kbTechGetStatus(cTechDEChurchPapacy) == cTechStatusActive))
         {
            xsDisableSelf();
            return;
         }

         researchSimpleTechByCondition(cTechDEChurchTeutonicKnights, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchTeutonicKnights) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEChurchKnightsHospital, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchKnightsHospital) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);

         researchSimpleTechByCondition(cTechDEChurchCrusaderKnights, 
         []() -> bool { return (kbTechGetStatus(cTechDEChurchCrusaderKnights) == cTechStatusObtainable); },
         cUnitTypeChurch, myChurchId, 75);
         break;
      }
   }
}
//==============================================================================
// florenceNightingaleMonitor
// We want our military to heal by a house while idle if we have this technology,
// so we need to set the military gather point near a house.
//==============================================================================
rule florenceNightingaleMonitor
inactive
minInterval 30 
{
   int upgradePlanID = -1;
   gFlorenceNightingaleHouseId = getUnit(cUnitTypeHouse, cMyID);
   vector militaryGatherPoint = cInvalidVector;
   int unitQueryID = -1;
   int numberFound = -1;
   int unitID = -1;
   vector unitLocation = cInvalidVector;
   vector mainBaseLoc = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));

   if (cMyCiv != cCivBritish)
   {
       xsDisableSelf();
       return;
   }

   if (((kbTechGetStatus(cTechHCXPFlorenceNightingale) == cTechStatusActive) && gFlorenceNightingaleHouseId < 0) ||
      ((kbTechGetStatus(cTechHCXPFlorenceNightingale) == cTechStatusActive) && 
      kbUnitGetCurrentHitpoints(gFlorenceNightingaleHouseId) < 1))
   {
      anwVerboseEcho("Florence Nightingale conditional hit!");
      kbBaseSetMilitaryGatherPoint(cMyID, kbBaseGetMainID(cMyID), militaryGatherPoint);
      unitQueryID = createSimpleUnitQuery(cUnitTypeAbstractHouse, cMyID, cUnitStateABQ, mainBaseLoc,
      100);
      numberFound = kbUnitQueryExecute(unitQueryID);
      unitID = kbUnitQueryGetResult(unitQueryID, 0);
      unitLocation = kbUnitGetPosition(unitID);
      gFlorenceNightingaleHouseId = unitID;
      kbBaseSetMilitaryGatherPoint(cMyID, kbBaseGetMainID(cMyID), unitLocation);
   }
}
//==============================================================================
// capitolUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule capitolUpgradeMonitor
inactive
minInterval 30 
{
   int upgradePlanID = -1;
   int myCapitolId = getUnit(cUnitTypeCapitol, cMyID);

   if ((kbTechGetStatus(cTechImpExcessiveTaxation) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpDeforestation) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechImpLargeScaleAgriculture) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpKnighthood) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpImmigrants) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpPeerage) == cTechStatusActive))
   {
       xsDisableSelf();
       return;
   }
  
   researchSimpleTechByCondition(cTechImpExcessiveTaxation, 
   []() -> bool { return (kbTechGetStatus(cTechImpExcessiveTaxation) == cTechStatusObtainable); },
   cUnitTypeCapitol, myCapitolId, 85);
   researchSimpleTechByCondition(cTechImpDeforestation, 
   []() -> bool { return (kbTechGetStatus(cTechImpDeforestation) == cTechStatusObtainable); },
   cUnitTypeCapitol, myCapitolId, 85);
   researchSimpleTechByCondition(cTechImpLargeScaleAgriculture, 
   []() -> bool { return (kbTechGetStatus(cTechImpLargeScaleAgriculture) == cTechStatusObtainable); },
   cUnitTypeCapitol, myCapitolId, 85);
   researchSimpleTechByCondition(cTechImpKnighthood, 
   []() -> bool { return (kbTechGetStatus(cTechImpKnighthood) == cTechStatusObtainable); },
   cUnitTypeCapitol, myCapitolId, 55);
   researchSimpleTechByCondition(cTechImpImmigrants, 
   []() -> bool { return (kbTechGetStatus(cTechImpImmigrants) == cTechStatusObtainable); },
   cUnitTypeCapitol, myCapitolId, 55);
   researchSimpleTechByCondition(cTechImpPeerage, 
   []() -> bool { return (kbTechGetStatus(cTechImpPeerage) == cTechStatusObtainable); },
   cUnitTypeCapitol, myCapitolId, 75);

}
//==============================================================================
// nativeCapitolUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule nativeCapitolUpgradeMonitor
inactive
minInterval 30 
{
   int upgradePlanID = -1;
   int myEstateId = getUnit(cUnitTypePlantation, cMyID);
   int myMarketId = getUnit(cUnitTypeMarket, cMyID);
   int myFarmId = getUnit(cUnitTypeFarm, cMyID);
   int myTownCenterId = getUnit(cUnitTypeTownCenter, cMyID);

   if ((kbTechGetStatus(cTechImpExcessiveTributeNative) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpDeforestationNative) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechImpLargeScaleGathering) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpImmigrantsNative) == cTechStatusActive))
   {
       xsDisableSelf();
       return;
   }
  
   researchSimpleTechByCondition(cTechImpExcessiveTributeNative, 
   []() -> bool { return (kbTechGetStatus(cTechImpExcessiveTributeNative) == cTechStatusObtainable); },
   cUnitTypePlantation, myEstateId, 85);
   researchSimpleTechByCondition(cTechImpDeforestationNative, 
   []() -> bool { return (kbTechGetStatus(cTechImpDeforestation) == cTechStatusObtainable); },
   cUnitTypeMarket, myMarketId, 85);
   researchSimpleTechByCondition(cTechImpLargeScaleGathering, 
   []() -> bool { return (kbTechGetStatus(cTechImpLargeScaleGathering) == cTechStatusObtainable); },
   cUnitTypeFarm, myFarmId, 85);
   researchSimpleTechByCondition(cTechImpImmigrantsNative, 
   []() -> bool { return (kbTechGetStatus(cTechImpImmigrantsNative) == cTechStatusObtainable); },
   cUnitTypeTownCenter, myTownCenterId, 55);
}
//==============================================================================
// asianCapitolUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule asianCapitolUpgradeMonitor
inactive
minInterval 30 
{
   int upgradePlanID = -1;
   int myEstateId = getUnit(cUnitTypeypRicePaddy, cMyID);
   int myMarketId = getUnit(cUnitTypeypTradeMarketAsian, cMyID);
   int myFarmId = getUnit(cUnitTypeFarm, cMyID);
   int myTownCenterId = getUnit(cUnitTypeTownCenter, cMyID);

   if ((kbTechGetStatus(cTechypImpExcessiveTributeAsian) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpDeforestationNative) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechypImpLargeScaleAgricultureAsian) == cTechStatusActive) &&
       (kbTechGetStatus(cTechImpImmigrantsNative) == cTechStatusActive))
   {
       xsDisableSelf();
       return;
   }

   researchSimpleTechByCondition(cTechypImpExcessiveTributeAsian, 
   []() -> bool { return (kbTechGetStatus(cTechypImpExcessiveTributeAsian) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myEstateId, 85);
   researchSimpleTechByCondition(cTechypImpDeforestationAsian, 
   []() -> bool { return (kbTechGetStatus(cTechypImpDeforestationAsian) == cTechStatusObtainable); },
   cUnitTypeypTradeMarketAsian, myMarketId, 85);
   researchSimpleTechByCondition(cTechypImpLargeScaleAgricultureAsian, 
   []() -> bool { return (kbTechGetStatus(cTechypImpLargeScaleAgricultureAsian) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myEstateId, 85);
   researchSimpleTechByCondition(cTechImpImmigrantsNative, 
   []() -> bool { return (kbTechGetStatus(cTechImpImmigrantsNative) == cTechStatusObtainable); },
   cUnitTypeTownCenter, myTownCenterId, 55);
}
//==============================================================================
// millUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule millUpgradeMonitor
inactive
minInterval 5 
{
   int upgradePlanID = -1;
   int myMillId = getUnit(cUnitTypeMill, cMyID);

   if ((kbTechGetStatus(cTechSeedDrill) == cTechStatusActive) && 
       (kbTechGetStatus(cTechArtificialFertilizer) == cTechStatusActive))    
   {
       xsDisableSelf();
       return;
   }

   researchSimpleTechByCondition(cTechSeedDrill, 
   []() -> bool { return (kbTechGetStatus(cTechSeedDrill) == cTechStatusObtainable); },
   cUnitTypeMill, myMillId, 90);
   researchSimpleTechByCondition(cTechArtificialFertilizer, 
   []() -> bool { return (kbTechGetStatus(cTechArtificialFertilizer) == cTechStatusObtainable); },
   cUnitTypeMill, myMillId, 90);
}
//==============================================================================
// nativeFarmUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule nativeFarmUpgradeMonitor
inactive
minInterval 5 
{
   int upgradePlanID = -1;
   int myFarmId = getUnit(cUnitTypeFarm, cMyID);
    
   if ((kbTechGetStatus(cTechGreatFeast) == cTechStatusActive) && 
       (kbTechGetStatus(cTechHarvestCeremony) == cTechStatusActive) &&
       (kbTechGetStatus(cTechGreenCornCeremony) == cTechStatusActive)) 
   {
       xsDisableSelf();
       return;
   }

   researchSimpleTechByCondition(cTechGreatFeast, 
   []() -> bool { return (kbTechGetStatus(cTechGreatFeast) == cTechStatusObtainable); },
   cUnitTypeFarm, myFarmId, 90);
   researchSimpleTechByCondition(cTechHarvestCeremony, 
   []() -> bool { return (kbTechGetStatus(cTechHarvestCeremony) == cTechStatusObtainable); },
   cUnitTypeFarm, myFarmId, 90);
   researchSimpleTechByCondition(cTechGreenCornCeremony, 
   []() -> bool { return (kbTechGetStatus(cTechGreenCornCeremony) == cTechStatusObtainable); },
   cUnitTypeFarm, myFarmId, 90);
}
//==============================================================================
// ricePaddyUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule ricePaddyUpgradeMonitor
inactive
minInterval 5
{
   int upgradePlanID = -1;
   int myRicePaddyId = getUnit(cUnitTypeypRicePaddy, cMyID);

   if ((kbTechGetStatus(cTechypCropMarket) == cTechStatusActive) &&
       (kbTechGetStatus(cTechypCultivateWasteland) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechypWaterConservancy) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechypIrrigationSystems) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechypSharecropping) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechypLandRedistribution) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechypCooperative) == cTechStatusActive))
   {
       xsDisableSelf();
       return;
   }
  
   researchSimpleTechByCondition(cTechypCropMarket, 
   []() -> bool { return (kbTechGetStatus(cTechypCropMarket) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myRicePaddyId, 90);
   researchSimpleTechByCondition(cTechypCultivateWasteland, 
   []() -> bool { return (kbTechGetStatus(cTechypCultivateWasteland) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myRicePaddyId, 90);
   researchSimpleTechByCondition(cTechypWaterConservancy, 
   []() -> bool { return (kbTechGetStatus(cTechypWaterConservancy) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myRicePaddyId, 90);
   researchSimpleTechByCondition(cTechypIrrigationSystems, 
   []() -> bool { return (kbTechGetStatus(cTechypIrrigationSystems) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myRicePaddyId, 90);
   researchSimpleTechByCondition(cTechypSharecropping, 
   []() -> bool { return (kbTechGetStatus(cTechypSharecropping) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myRicePaddyId, 90);
   researchSimpleTechByCondition(cTechypLandRedistribution, 
   []() -> bool { return (kbTechGetStatus(cTechypLandRedistribution) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myRicePaddyId, 90);
   researchSimpleTechByCondition(cTechypCooperative, 
   []() -> bool { return (kbTechGetStatus(cTechypCooperative) == cTechStatusObtainable); },
   cUnitTypeypRicePaddy, myRicePaddyId, 90);
}
//==============================================================================
// estateUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule estateUpgradeMonitor
inactive
minInterval 5 
{
   int upgradePlanID = -1;
   int myEstateId = getUnit(cUnitTypePlantation, cMyID);

   if ((kbTechGetStatus(cTechBookkeeping) == cTechStatusActive) && 
       (kbTechGetStatus(cTechHomesteading) == cTechStatusActive) &&       
       (kbTechGetStatus(cTechOreRefining) == cTechStatusActive))    
   {
       xsDisableSelf();
       return;
   }

   researchSimpleTechByCondition(cTechBookkeeping, 
   []() -> bool { return (kbTechGetStatus(cTechBookkeeping) == cTechStatusObtainable); },
   cUnitTypePlantation, myEstateId, 90);
   researchSimpleTechByCondition(cTechHomesteading, 
   []() -> bool { return (kbTechGetStatus(cTechHomesteading) == cTechStatusObtainable); },
   cUnitTypePlantation, myEstateId, 90);
   researchSimpleTechByCondition(cTechOreRefining, 
   []() -> bool { return (kbTechGetStatus(cTechOreRefining) == cTechStatusObtainable); },
   cUnitTypePlantation, myEstateId, 90);
}
//==============================================================================
// nativeEstateUpgradeMonitor
// Make sure we research technologies at this building.
//==============================================================================
rule nativeEstateUpgradeMonitor
inactive
minInterval 5 
{
   int upgradePlanID = -1;
   int myEstateId = getUnit(cUnitTypePlantation, cMyID);

   if ((kbTechGetStatus(cTechEarthCeremony) == cTechStatusActive) && 
       (kbTechGetStatus(cTechEarthGiftCeremony) == cTechStatusActive))    
   {
       xsDisableSelf();
       return;
   }

   researchSimpleTechByCondition(cTechEarthCeremony, 
   []() -> bool { return (kbTechGetStatus(cTechEarthCeremony) == cTechStatusObtainable); },
   cUnitTypePlantation, myEstateId, 90);
   researchSimpleTechByCondition(cTechEarthGiftCeremony, 
   []() -> bool { return (kbTechGetStatus(cTechEarthGiftCeremony) == cTechStatusObtainable); },
   cUnitTypePlantation, myEstateId, 90);
}
//==============================================================================
/*
   landPatrol
   This makes military units explore land areas and attack enemies if they encounter them.
*/
//==============================================================================
rule landPatrol
inactive
minInterval 20
{
   if(kbGetAge() > cAge3)
   {  
      vector mainBaseLoc = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
      int militaryUnit =-1;
      if(kbUnitCount(cMyID, cUnitTypeLogicalTypeLandMilitary, cUnitStateAlive) >= 1)
      { militaryUnit = cUnitTypeLogicalTypeLandMilitary; }

      if (gDefenseReflexBaseID == kbBaseGetMainID(cMyID)) {
         aiPlanDestroy(gLandPatrolPlan);
         return;
      }

      if(kbUnitCount(cMyID, militaryUnit, cUnitStateAlive) >= 5 && aiPlanGetActive(gLandPatrolPlan) == false)
      {
         if (gLandPatrolPlan != -1) {
            aiPlanDestroy(gLandPatrolPlan);
            gLandPatrolPlan = -1;
         }
         vector centerOffset = kbGetMapCenter() - kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
         vector targetLocation = cInvalidVector;
         if (gIslandMap == false) {
            targetLocation = getRandomLandPoint();
         } else {
            targetLocation = getRandomPatrolPoint();
         }
         gLandPatrolPlan = aiPlanCreate("Patrol the Lands", cPlanCombat);

         // Add units
         int militaryQueryID = createIdleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
         int numberFound = kbUnitQueryExecute(militaryQueryID);

         if (numberFound > 30) {
            if (gIslandMap == false) {
               aiPlanAddUnitType(gLandPatrolPlan, cUnitTypeLogicalTypeLandMilitary, 10, 15, 20);
            } else {
               aiPlanAddUnitType(gLandPatrolPlan, cUnitTypeLogicalTypeLandMilitary, 8, 10, 12);
            }
            aiPlanSetVariableInt(gLandPatrolPlan, cCombatPlanCombatType, 0, cCombatPlanCombatTypeAttack);
            aiPlanSetVariableInt(gLandPatrolPlan, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
            aiPlanSetVariableVector(gLandPatrolPlan, cCombatPlanTargetPoint, 0, targetLocation);
            aiPlanSetVariableVector(gLandPatrolPlan, cCombatPlanGatherPoint, 0, mainBaseLoc);
            aiPlanSetVariableFloat(gLandPatrolPlan, cCombatPlanGatherDistance, 0, 100.0);
            aiPlanSetVariableInt(gLandPatrolPlan, cCombatPlanAttackRoutePattern, 0, cCombatPlanAttackRoutePatternRandom);
            aiPlanSetVariableBool(gLandPatrolPlan, cCombatPlanAllowMoreUnitsDuringAttack, 0, true);
            aiPlanSetVariableInt(gLandPatrolPlan, cCombatPlanRefreshFrequency, 0, cDifficultyCurrent >= cDifficultyHard ? 300 : 1000);

            aiPlanSetVariableInt(gLandPatrolPlan, cCombatPlanDoneMode, 0, cCombatPlanDoneModeRetreat | cCombatPlanDoneModeNoTarget);
            aiPlanSetVariableInt(gLandPatrolPlan, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeOutnumbered);
            aiPlanSetVariableInt(gLandPatrolPlan, cCombatPlanNoTargetTimeout, 0, 30000);
            aiPlanSetBaseID(gLandPatrolPlan, kbBaseGetMainID(cMyID));
            aiPlanSetInitialPosition(gLandPatrolPlan, mainBaseLoc);

            aiPlanSetDesiredPriority(gLandPatrolPlan, 45);
            aiPlanSetActive(gLandPatrolPlan);
            anwVerboseEcho("Patrolling the lands, looking for enemies and settlements to destroy!");
         }
      }
   }
}
//==============================================================================
// getBackToWork
// An attempt to take care of idle villagers.
//==============================================================================
rule getBackToWork
inactive
//group tcComplete
minInterval 20
maxInterval 30
{
   int age = kbGetAge();
   int villagerQuery = createSimpleUnitQuery(gEconUnit, cMyID, cUnitStateAlive);
   kbUnitQuerySetActionType(villagerQuery, cActionTypeIdle);
   int numberFound = kbUnitQueryExecute(villagerQuery);
   int numPlans = aiPlanGetActiveCount();
   // float goldPercentage = aiGetResourcePercentage(cResourceGold);
   // float woodPercentage = aiGetResourcePercentage(cResourceWood);
   // float foodPercentage = aiGetResourcePercentage(cResourceFood);
   float goldAmount = kbResourceGet(cResourceGold);
   float woodAmount = kbResourceGet(cResourceWood);
   float foodAmount = kbResourceGet(cResourceFood);
   int resource = getMostNeededResource();

   // Gather the resource with the least amount.
   // if (foodAmount < woodAmount && foodAmount < goldAmount) {
   //    resource = cResourceFood;
   // } else if (woodAmount < foodAmount && woodAmount < goldAmount) {
   //    resource = cResourceWood;
   // } else if (goldAmount < foodAmount && goldAmount < woodAmount) {
   //    resource = cResourceGold;
   // }

   if (age < cAge4 && resource == cResourceWood) {
      if (foodAmount < goldAmount) { // xsRandInt(2) == 0
         resource = cResourceFood;
      } else {
         resource = cResourceGold;
      }
   }
   //anwVerboseEcho("Chosen Resource: "+resource+"");
   for (int i = 0; i < numberFound; i++)
   {
      int unitID = kbUnitQueryGetResult(villagerQuery, i);
      if (kbUnitGetPlanID(unitID) >= 0 && aiPlanGetActive(kbUnitGetPlanID(unitID)) == true)
      {
         continue;
      }

      for (int j = 0; j < numPlans; j++)
      {
         int planID = aiPlanGetIDByActiveIndex(j);
         if (aiPlanGetType(planID) != cPlanGather)
         {
            continue;
         }
         if ((aiPlanGetVariableInt(planID, cGatherPlanResourceType, 0) != resource)) //||
             //(aiPlanGetVariableInt(planID, cGatherPlanResourceSubType, 0) != subType))
         {
            continue;
         } else if ((aiPlanGetVariableInt(planID, cGatherPlanResourceType, 0) == resource)) {
            aiPlanAddUnit(planID, unitID);
            break;
         }
      }

      // Added in case this is causing performance issues on older systems...
      if (i > 10) {
         return;
      }
   }
}
//==============================================================================
// maxOutThatMilitaryBaby
// Tries to maintain as many military units as possible while leaving room for villagers.
//==============================================================================
rule maxOutThatMilitaryBaby
active
maxInterval 20
{
   int limit = kbGetBuildLimit(cMyID, cUnitTypeLogicalTypeLandMilitary);
   int age = kbGetAge();
   int militaryCount = kbUnitCount(cMyID, cUnitTypeLogicalTypeLandMilitary, cUnitStateAlive);
   int ecoCount = kbUnitCount(cMyID, cUnitTypeAbstractVillager, cUnitStateAlive);
   if (age < cAge2) {
      return;
   }

   // Randomize percentages within ranges
   int infantryPercent = 58 + aiRandInt(3);  // 58-60%
   int cavalryPercent = 30 + aiRandInt(11);   // 30-40%
   int artilleryPercent = 2;                 // 2% fixed

   // Normalize to ensure we don't exceed 100%
   int totalPercent = infantryPercent + cavalryPercent + artilleryPercent;
   float infantryRatio = infantryPercent * 1.0 / totalPercent;
   float cavalryRatio = cavalryPercent * 1.0 / totalPercent;
   float artilleryRatio = artilleryPercent * 1.0 / totalPercent;

   // Calculate unit type limits
   int infantryLimit = limit * infantryRatio;
   int cavalryLimit = limit * cavalryRatio;
   int artilleryLimit = limit * artilleryRatio;

   // Ensure at least 1 of each if limit allows
   if (infantryLimit < 1 && limit >= 1)
      infantryLimit = 1;
   if (cavalryLimit < 1 && limit >= 3)
      cavalryLimit = 1;
   if (artilleryLimit < 1 && limit >= 10)
      artilleryLimit = 1;

   int militaryPriority = 70;
   
   // Early rush attempt maxes out priority
   if (gEarlyRushAttempt == true && (age == cAge2 || age == cAge3))
   {
      militaryPriority = 100;
   } else if (gEarlyRushAttempt == false && age == cAge2) {
      militaryPriority = 70;
   } else if (gEarlyRushAttempt == false && age == cAge3) {
      militaryPriority = 75;
   } else if (age == cAge4) {
      militaryPriority = 85;
   } else if (age == cAge5) {
      militaryPriority = 100;
   }

   // Infantry maintain plan
   if (gMaxInfantryMaintain < 0)
   {
      gMaxInfantryMaintain = createSimpleMaintainPlan(cUnitTypeAbstractInfantry, infantryLimit, true, -1, 1);
      aiPlanSetDesiredPriority(gMaxInfantryMaintain, militaryPriority);
      aiPlanSetVariableInt(gMaxInfantryMaintain, cTrainPlanBuildFromType, 0, gMilitaryBuildings);
      anwVerboseEcho("Infantry maintain plan created, limit: " + infantryLimit);
   }
   else
   {
      if (aiPlanGetActive(gMaxInfantryMaintain) == false)
         aiPlanSetActive(gMaxInfantryMaintain, true);
      aiPlanSetDesiredPriority(gMaxInfantryMaintain, militaryPriority);
      aiPlanSetVariableInt(gMaxInfantryMaintain, cTrainPlanNumberToMaintain, 0, infantryLimit);
   }

   // Cavalry maintain plan
   if (gMaxCavalryMaintain < 0)
   {
      gMaxCavalryMaintain = createSimpleMaintainPlan(cUnitTypeAbstractCavalry, cavalryLimit, true, -1, 1);
      aiPlanSetDesiredPriority(gMaxCavalryMaintain, militaryPriority);
      aiPlanSetVariableInt(gMaxCavalryMaintain, cTrainPlanBuildFromType, 0, gMilitaryBuildings);
      anwVerboseEcho("Cavalry maintain plan created, limit: " + cavalryLimit);
   }
   else
   {
      if (aiPlanGetActive(gMaxCavalryMaintain) == false)
         aiPlanSetActive(gMaxCavalryMaintain, true);
      aiPlanSetDesiredPriority(gMaxCavalryMaintain, militaryPriority);
      aiPlanSetVariableInt(gMaxCavalryMaintain, cTrainPlanNumberToMaintain, 0, cavalryLimit);
   }

   // Artillery maintain plan
   if (gArtilleryMaintain < 0)
   {
      gArtilleryMaintain = createSimpleMaintainPlan(cUnitTypeAbstractArtillery, artilleryLimit, true, -1, 1);
      aiPlanSetDesiredPriority(gArtilleryMaintain, militaryPriority);
      aiPlanSetVariableInt(gArtilleryMaintain, cTrainPlanBuildFromType, 0, gMilitaryBuildings);
      anwVerboseEcho("Artillery maintain plan created, limit: " + artilleryLimit);
   }
   else
   {
      if (aiPlanGetActive(gArtilleryMaintain) == false)
         aiPlanSetActive(gArtilleryMaintain, true);
      aiPlanSetDesiredPriority(gArtilleryMaintain, militaryPriority);
      aiPlanSetVariableInt(gArtilleryMaintain, cTrainPlanNumberToMaintain, 0, artilleryLimit);
   }
   
   // Get current military unit counts
   int currentInfantry = kbUnitCount(cMyID, cUnitTypeAbstractInfantry, cUnitStateAlive);
   int currentCavalry = kbUnitCount(cMyID, cUnitTypeAbstractCavalry, cUnitStateAlive);
   int currentArtillery = kbUnitCount(cMyID, cUnitTypeAbstractArtillery, cUnitStateAlive);
   int totalMilitary = currentInfantry + currentCavalry + currentArtillery;

   // Get pop cap info
   int popCap = kbGetPopCap();
   int popUsed = kbGetPop();

   anwVerboseEcho("Military limits - Inf: " + infantryLimit + " (" + infantryPercent + "%) Cav: " + cavalryLimit + " (" + cavalryPercent + "%) Art: " + artilleryLimit + " (" + artilleryPercent + "%)");
   anwVerboseEcho("Current military - Inf: " + currentInfantry + " Cav: " + currentCavalry + " Art: " + currentArtillery + " Total: " + totalMilitary);
   anwVerboseEcho("Population - Used: " + popUsed + " / Cap: " + popCap + " | Current Military Units: " + militaryCount + "Military Priority: " + militaryPriority + " | Current Economy Units: " + ecoCount);
   if (gEarlyRushAttempt == true)
      anwVerboseEcho("EARLY RUSH ACTIVE - Military priority maxed to 100");
}
//==============================================================================
// maxOutVillagers
// Tries to maintain as many villagers as possible while leaving room for military units.
//==============================================================================
rule maxOutVillagers
active
minInterval 20
{
   // Set build limit...
   int limit = 80;
   int age = kbGetAge();
   
   // Get current villager count
   int villagerCount = kbUnitCount(cMyID, cUnitTypeAbstractVillager, cUnitStateAlive);
   
   // Determine base priority for current age
   int basePriority = 90;
   if (age < cAge2) {
      limit = 12;
   } else if (age == cAge2) {
      limit = 22;
   } else if (age == cAge3) {
      limit = 30;
   } else if (age == cAge4) {
      basePriority = 80;
   } else if (age == cAge5) {
      basePriority = 85;
   }
   
   // Adjust priority based on villager count
   if (villagerCount >= 75) {
      basePriority = 40;
   }
   
   // Create/update maintain plan
   if (limit < 1)
      return;
      
   if (gMaxVillagersMaintain < 0)
   {
      gMaxVillagersMaintain = createSimpleMaintainPlan(cUnitTypeAbstractVillager, limit, true, -1, 1);
      aiPlanSetDesiredPriority(gMaxVillagersMaintain, basePriority);
      aiPlanSetVariableInt(gMaxVillagersMaintain, cTrainPlanBuildFromType, 0, cUnitTypeAgeUpBuilding);
      anwVerboseEcho("Maxed out villagers!");
   }
   else
   {
      if (aiPlanGetActive(gMaxVillagersMaintain) == false) {
         aiPlanSetActive(gMaxVillagersMaintain, true);
      }
      aiPlanSetDesiredPriority(gMaxVillagersMaintain, basePriority);
      aiPlanSetVariableInt(gMaxVillagersMaintain, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
// maintainFishingBoats
// Maintains a number of fishing boats...
//==============================================================================
rule maintainFishingBoats
inactive
minInterval 20
{
   // Set build limit...
   int limit = 16;
   int age = kbGetAge();

   if (age == cAge1) {
      limit = 2;
   } else if (age == cAge2) {
      limit = 5;
   } else if (age == cAge3) {
      limit = 7;
   }

   // Create/update maintain plan
   if (limit < 1)
      return;

   if (gFishingBoatMaintainPlan < 0)
   {
      gFishingBoatMaintainPlan = createSimpleMaintainPlan(gFishingUnit, limit, true, -1, 1);
      if (age < cAge2) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 25);
      } else if (age == cAge2 || age == cAge3) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 45);
      } else if (age == cAge4) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 60);
      } else if (age == cAge5) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 64);
      }
      aiPlanSetVariableInt(gFishingBoatMaintainPlan, cTrainPlanBuildFromType, 0, gDockUnit);
      anwVerboseEcho("Fishing boats!");
   }
   else
   {
      if (aiPlanGetActive(gFishingBoatMaintainPlan) == false) {
         aiPlanSetActive(gFishingBoatMaintainPlan, true);
      }
      if (age <= cAge2) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 55);
      } else if (age == cAge3) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 55);
      } else if (age == cAge4) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 60);
      } else if (age == cAge5) {
         aiPlanSetDesiredPriority(gFishingBoatMaintainPlan, 64);
      }
      aiPlanSetVariableInt(gFishingBoatMaintainPlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}