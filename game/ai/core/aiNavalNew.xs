//==============================================================================
/*
   waterPatrol
   This makes ships explore the seas and attack enemies if they encounter them.
*/
//==============================================================================
rule waterPatrol
inactive
minInterval 60
{
   if((gWaterMap == true && cvOkToExplore == true) && (kbGetAge() > cAge1))
   {  
      int boatUnit =-1;
      if(kbUnitCount(cMyID, cUnitTypeAbstractWarShip, cUnitStateAlive) >= 1)
      { boatUnit = cUnitTypeAbstractWarShip; }

      if(kbUnitCount(cMyID, boatUnit, cUnitStateAlive) >= 5 && aiPlanGetActive(gWaterPatrolPlan) == false)
      {
         if (gWaterPatrolPlan != -1) {
            aiPlanDestroy(gWaterPatrolPlan);
            gWaterPatrolPlan = -1;
         }
         vector centerOffset = kbGetMapCenter() - kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
         vector targetLocation = getRandomWaterPoint(); // aiRandLocation();
         gWaterPatrolPlan = aiPlanCreate("Sail the Seas", cPlanCombat);

         // Add units
         int shipQueryID = createIdleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
         int numberFound = kbUnitQueryExecute(shipQueryID);
         // int unitID = -1;
         // int unitPlanID = -1;

         // // We want a maximum of five ships.
         // for (i = 0; < 5)
         // {
         //    unitID = kbUnitQueryGetResult(shipQueryID, i);
         //    aiPlanAddUnit(gWaterPatrolPlan, unitID);
         // }

         if (numberFound > 2) {
            aiPlanAddUnitType(gWaterPatrolPlan, cUnitTypeAbstractWarShip, 2, 3, 5);
            aiPlanSetVariableInt(gWaterPatrolPlan, cCombatPlanCombatType, 0, cCombatPlanCombatTypeAttack);
            aiPlanSetVariableInt(gWaterPatrolPlan, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
            aiPlanSetVariableVector(gWaterPatrolPlan, cCombatPlanTargetPoint, 0, targetLocation);
            aiPlanSetVariableVector(gWaterPatrolPlan, cCombatPlanGatherPoint, 0, gNavyVec);
            aiPlanSetVariableFloat(gWaterPatrolPlan, cCombatPlanGatherDistance, 0, 80.0);
            aiPlanSetVariableInt(gWaterPatrolPlan, cCombatPlanAttackRoutePattern, 0, cCombatPlanAttackRoutePatternRandom);
            aiPlanSetVariableBool(gWaterPatrolPlan, cCombatPlanAllowMoreUnitsDuringAttack, 0, true);
            aiPlanSetVariableInt(gWaterPatrolPlan, cCombatPlanRefreshFrequency, 0, cDifficultyCurrent >= cDifficultyHard ? 300 : 1000);

            aiPlanSetVariableInt(gWaterPatrolPlan, cCombatPlanDoneMode, 0, cCombatPlanDoneModeRetreat | cCombatPlanDoneModeNoTarget);
            aiPlanSetVariableInt(gWaterPatrolPlan, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeOutnumbered);
            aiPlanSetVariableInt(gWaterPatrolPlan, cCombatPlanNoTargetTimeout, 0, 30000);
            aiPlanSetBaseID(gWaterPatrolPlan, kbUnitGetBaseID(getUnit(gDockUnit, cMyID, cUnitStateAlive)));
            aiPlanSetInitialPosition(gWaterPatrolPlan, gNavyVec);

            aiPlanSetDesiredPriority(gWaterPatrolPlan, 65);
            anwLogCombatPlanConfig("create", gWaterPatrolPlan, "water-patrol");
            aiPlanSetActive(gWaterPatrolPlan);
            anwVerboseEcho("Sailing the seas, looking for adventure!");
         }
      }
   }
}
//==============================================================================
/*
   waterWarShipPlans
   A rule for creating naval attack and defense plans.
*/
//==============================================================================
rule waterWarShipPlans
inactive
minInterval 15
{
   int warshipQueryId = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(warshipQueryId);

   // Return if there are no warships.
   if (numberFound < 0) {
      return;
   }  
   
   int flagUnit = getUnit(cUnitTypeHomeCityWaterSpawnFlag, cMyID);
   if (flagUnit >= 0) {
      gNavyVec = kbUnitGetPosition(flagUnit);
   }
   
   if (gNavyDefendPlan < 0)
   {
      gNavyDefendPlan = aiPlanCreate("Naval Defense Plan", cPlanDefend);
      aiPlanAddUnitType(gNavyDefendPlan, cUnitTypeAbstractWarShip , 1, 1, 200);
      
      aiPlanSetVariableVector(gNavyDefendPlan, cDefendPlanDefendPoint, 0, gNavyVec);
      aiPlanSetVariableFloat(gNavyDefendPlan, cDefendPlanEngageRange, 0, 100.0);
      aiPlanSetVariableBool(gNavyDefendPlan, cDefendPlanPatrol, 0, false);
      aiPlanSetVariableFloat(gNavyDefendPlan, cDefendPlanGatherDistance, 0, 40.0);
      aiPlanSetInitialPosition(gNavyDefendPlan, gNavyVec);
      aiPlanSetUnitStance(gNavyDefendPlan, cUnitStanceDefensive);
      aiPlanSetVariableInt(gNavyDefendPlan, cDefendPlanRefreshFrequency, 0, 20);
      aiPlanSetVariableInt(gNavyDefendPlan, cDefendPlanAttackTypeID, 0, cUnitTypeUnit);
      aiPlanSetDesiredPriority(gNavyDefendPlan, 20); // Very low priority.
      aiPlanSetActive(gNavyDefendPlan); 
      anwVerboseEcho("Creating Naval Defense Plan at: " + gNavyVec);
      anwLogPlanEvent("create", gNavyDefendPlan, "naval-defend defendPoint=" + gNavyVec + " engageRange=100 gatherDistance=40 refresh=20");
      anwProbe("navy.defend", "plan=" + gNavyDefendPlan + " pos=" + anwFmtVec(gNavyVec) +
         " warships=" + numberFound + " age=" + kbGetAge());
   }

   if (((numberFound >= 3 ) && (civIsNative() == false)) ||
       ((numberFound >= 6 ) && (civIsNative() == true))) 
   {
      if (getNavalTargetPlayerId() > 0 && aiPlanGetActive(gNavyEnhancedAttackPlan) == false)
      {
         aiPlanDestroy(gNavyEnhancedAttackPlan);
         gNavyEnhancedAttackPlan = aiPlanCreate("Naval Attack Plan", cPlanAttack);
         aiPlanSetVariableInt(gNavyEnhancedAttackPlan, cAttackPlanPlayerID, 0, getNavalTargetPlayerId());
         aiPlanSetNumberVariableValues(gNavyEnhancedAttackPlan, cAttackPlanTargetTypeID, 2, true);
         aiPlanSetVariableInt(gNavyEnhancedAttackPlan, cAttackPlanTargetTypeID, 0, cUnitTypeUnit);
         aiPlanSetVariableInt(gNavyEnhancedAttackPlan, cAttackPlanTargetTypeID, 1, gDockUnit);
         aiPlanSetVariableVector(gNavyEnhancedAttackPlan, cAttackPlanGatherPoint, 0, gNavyVec);
         aiPlanSetVariableFloat(gNavyEnhancedAttackPlan, cAttackPlanGatherDistance, 0, 50.0);
         aiPlanSetVariableInt(gNavyEnhancedAttackPlan, cAttackPlanRefreshFrequency, 0, 5);
         aiPlanSetDesiredPriority(gNavyEnhancedAttackPlan, 65); // Above defend and fishing, but below explore.
         aiPlanAddUnitType(gNavyEnhancedAttackPlan, cUnitTypeAbstractWarShip, 1, 10, 200); 
         aiPlanSetInitialPosition(gNavyEnhancedAttackPlan, gNavyVec);
         anwLogPlanEvent("create", gNavyEnhancedAttackPlan, "naval-attack targetPlayer=" + getNavalTargetPlayerId() +
            " gatherPoint=" + gNavyVec + " gatherDistance=50 refresh=5 priority=65");
         anwVerboseEcho("***** LAUNCHING NAVAL ATTACK, plan ID is " + gNavyEnhancedAttackPlan);
         anwProbe("navy.attack", "plan=" + gNavyEnhancedAttackPlan + " target=p" + getNavalTargetPlayerId() +
            " warships=" + numberFound + " age=" + kbGetAge());
         anwSendLeaderInsultLine(getNavalTargetPlayerId(), 150000);
         aiPlanSetActive(gNavyEnhancedAttackPlan, true);
      }
   }   
}
//==============================================================================
// warShipManager
// Manages how we handle warships and their interaction with docks.
//==============================================================================
rule warShipManager
inactive
minInterval 10
maxInterval 20
{
   // Check build limit...
   //int limit = kbGetBuildLimit(cMyID, cUnitTypeAbstractWarShip); // This does not work properly for some reason.
   int age = kbGetAge();
   int mainBaseId = kbBaseGetMainID(cMyID);
   int warshipPriority = 90;
   int caravelLimit = kbGetBuildLimit(cMyID, gCaravelUnit);
   int galleonLimit = kbGetBuildLimit(cMyID, gGalleonUnit);
   int frigateLimit = kbGetBuildLimit(cMyID, gFrigateUnit);
   int monitorLimit = kbGetBuildLimit(cMyID, gMonitorUnit);
   int battleShipLimit = kbGetBuildLimit(cMyID, gBattleShipUnit);

   int flagUnit = getUnit(cUnitTypeHomeCityWaterSpawnFlag, cMyID);
   gNavyVec = kbUnitGetPosition(flagUnit);
   // Create/update maintain plan
   // if (limit < 1) {
   //    return;
   // }

   if (age < cAge4) {
      warshipPriority = 60;
   } else if (age == cAge4) {
      warshipPriority = 65;
   }

   if (gBattleshipMaintain < 0)
   {  
      // Override the default plans.
      aiPlanDestroy(gCaravelMaintain);
      aiPlanDestroy(gGalleonMaintain);
      aiPlanDestroy(gFrigateMaintain);
      aiPlanDestroy(gMonitorMaintain);
      aiPlanDestroy(gBattleshipMaintain);

      if (civIsNative() == true)
      {
         gCaravelMaintain = createSimpleMaintainPlan(gCaravelUnit, caravelLimit, false, -1, 1);
         gGalleonMaintain = createSimpleMaintainPlan(gGalleonUnit, galleonLimit, false, -1, 1);
      }
      else if ((kbGetCiv() == cCivChinese) || (kbGetCiv() == cCivSPCChinese))
      {
         gCaravelMaintain = createSimpleMaintainPlan(gCaravelUnit, caravelLimit, false, -1, 1);
         gGalleonMaintain = createSimpleMaintainPlan(gGalleonUnit, galleonLimit, false, -1, 1);
         gMonitorMaintain = createSimpleMaintainPlan(cUnitTypeMonitor, monitorLimit, false, -1, 1);
      }
      else
      {
         gCaravelMaintain = createSimpleMaintainPlan(gCaravelUnit, caravelLimit, false, -1, 1);
         gGalleonMaintain = createSimpleMaintainPlan(gGalleonUnit, galleonLimit, false, -1, 1);
         gFrigateMaintain = createSimpleMaintainPlan(gFrigateUnit, frigateLimit, false, -1, 1);
         gMonitorMaintain = createSimpleMaintainPlan(cUnitTypeMonitor, monitorLimit, false, -1, 1);
		   gBattleshipMaintain = createSimpleMaintainPlan(gBattleShipUnit, battleShipLimit, false, -1, 1);
      }
      aiPlanSetDesiredPriority(gCaravelMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gGalleonMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gFrigateMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gMonitorMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gBattleshipMaintain, warshipPriority);
      aiPlanSetActive(gCaravelMaintain, true);
      aiPlanSetActive(gGalleonMaintain, true);
      aiPlanSetActive(gFrigateMaintain, true);
      aiPlanSetActive(gMonitorMaintain, true);
      aiPlanSetActive(gBattleshipMaintain, true);
      anwVerboseEcho("**** ACTIVATING NAVAL TRAIN PLANS ****");
   } else {
      // Check and update the build limits if the plans already exist.
      aiPlanSetVariableInt(gCaravelMaintain, cTrainPlanNumberToMaintain, 0, caravelLimit);
      aiPlanSetVariableInt(gGalleonMaintain, cTrainPlanNumberToMaintain, 0, galleonLimit);
      aiPlanSetVariableInt(gFrigateMaintain, cTrainPlanNumberToMaintain, 0, frigateLimit);
      aiPlanSetVariableInt(gMonitorMaintain, cTrainPlanNumberToMaintain, 0, monitorLimit);
      aiPlanSetVariableInt(gBattleshipMaintain, cTrainPlanNumberToMaintain, 0, battleShipLimit);
      aiPlanSetDesiredPriority(gCaravelMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gGalleonMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gFrigateMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gMonitorMaintain, warshipPriority);
      aiPlanSetDesiredPriority(gBattleshipMaintain, warshipPriority);
      // Check if we can train any native naval units.
      if (kbProtoUnitAvailable(cUnitTypeCanoe) == true && civIsNative() == false && gCanoeMaintain == -1)
      {
         gCanoeMaintain = createSimpleMaintainPlan(cUnitTypeCanoe, 20, false, -1, 1);
         aiPlanSetDesiredPriority(gCanoeMaintain, warshipPriority);
         aiPlanSetActive(gCanoeMaintain, true);
      } 
      else if (kbProtoUnitAvailable(cUnitTypeypCatamaran) == true && gCatamaranMaintain == -1)
      {
         gCatamaranMaintain = createSimpleMaintainPlan(cUnitTypeypCatamaran, kbGetBuildLimit(cMyID, cUnitTypeypCatamaran), false, -1, 1);
         aiPlanSetDesiredPriority(gCatamaranMaintain, warshipPriority);
         aiPlanSetActive(gCatamaranMaintain, true);
      }
      else if (kbProtoUnitAvailable(cUnitTypeypMarathanCatamaran) == true && gCatamaranMaintain == -1)
      {
         gCatamaranMaintain = createSimpleMaintainPlan(cUnitTypeypMarathanCatamaran, 
         kbGetBuildLimit(cMyID, cUnitTypeypMarathanCatamaran), false, -1, 1);
         aiPlanSetDesiredPriority(gCatamaranMaintain, warshipPriority);
         aiPlanSetActive(gCatamaranMaintain, true);
      }
      else if (kbProtoUnitAvailable(cUnitTypedeAfricanCatamaran) == true && gCatamaranMaintain == -1)
      {
         gCatamaranMaintain = createSimpleMaintainPlan(cUnitTypedeAfricanCatamaran, 
         kbGetBuildLimit(cMyID, cUnitTypedeAfricanCatamaran), false, -1, 1);
         aiPlanSetDesiredPriority(gCatamaranMaintain, warshipPriority);
         aiPlanSetActive(gCatamaranMaintain, true);
      }
      if (kbProtoUnitAvailable(cUnitTypePrivateer) == true && gPrivateerMaintain == -1)
      {
         gPrivateerMaintain = createSimpleMaintainPlan(cUnitTypePrivateer, kbGetBuildLimit(cMyID, cUnitTypePrivateer), false, -1, 1);
         aiPlanSetDesiredPriority(gPrivateerMaintain, warshipPriority);
         aiPlanSetActive(gPrivateerMaintain, true);
      } else if (kbProtoUnitAvailable(cUnitTypedeSPCPrivateer) == true && gPrivateerMaintain == -1)
      {
         gPrivateerMaintain = createSimpleMaintainPlan(cUnitTypedeSPCPrivateer, kbGetBuildLimit(cMyID, cUnitTypedeSPCPrivateer), false, -1, 1);
         aiPlanSetDesiredPriority(gPrivateerMaintain, warshipPriority);
         aiPlanSetActive(gPrivateerMaintain, true);
      }
      // Safety check to make sure the plans stay active.
      if (aiPlanGetActive(gCaravelMaintain) == false || aiPlanGetActive(gGalleonMaintain) == false ||
         aiPlanGetActive(gFrigateMaintain) == false || aiPlanGetActive(gMonitorMaintain) == false ||
         aiPlanGetActive(gBattleshipMaintain) == false) {
         aiPlanSetActive(gCaravelMaintain, true);
         aiPlanSetActive(gGalleonMaintain, true);
         aiPlanSetActive(gFrigateMaintain, true);
         aiPlanSetActive(gMonitorMaintain, true);
         aiPlanSetActive(gBattleshipMaintain, true);
         // if (kbGetBuildLimit(cMyID, cUnitTypedeSPCPrivateer) > 0) {
         //    aiPlanSetActive(gCatamaranMaintain, true);
         // }
         // if (kbGetBuildLimit(cMyID, cUnitTypedeSPCPrivateer) > 0) {
         //    aiPlanSetActive(gPrivateerMaintain, true);
         // }
      }
   }
/***********************************************************************************************************************
                                                      DOCK SECTION
************************************************************************************************************************/
   if (kbUnitCount(cMyID, gDockUnit, cUnitStateABQ) < 4 && kbGetAge() > cAge3)
   {  
      //anwVerboseEcho("Dock Build Check");
      vector baseVec = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
      vector dockPos = gNavyVec; // Start at the base location
      int dockPlan = createLocationBuildPlan(gDockUnit, 1, 100, true, cEconomyEscrowID, dockPos, 1);
      //anwVerboseEcho("Dock Plan Id: " +dockPlan+ " Is Active: " +aiPlanGetActive(dockPlan)+ "");
      anwVerboseEcho("NAVY DOCK BUILD PLAN, plan ID "+dockPlan);
   }
/***********************************************************************************************************************
                                                      REPAIR SECTION
************************************************************************************************************************/
   int ownDockID = getUnit(gDockUnit, cMyID, cUnitStateAlive);
   vector ownDockPosition = kbUnitGetPosition(ownDockID);
   int unitID = -1;
   if (ownDockID < 0) // Destroy the repair plan as soon as we have no Docks left.
   {
      if (gNavyRepairPlan >= 0)
      {
         aiPlanDestroy(gNavyRepairPlan);
         gNavyRepairPlan = -1;
      }
   }
   else
   {
      if (gNavyRepairPlan < 0)
      {
         gNavyRepairPlan = aiPlanCreate("Navy Repair", cPlanCombat);

         aiPlanSetVariableInt(gNavyRepairPlan, cCombatPlanCombatType, 0, cCombatPlanCombatTypeDefend);
         aiPlanSetVariableInt(gNavyRepairPlan, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
         aiPlanSetVariableInt(gNavyRepairPlan, cCombatPlanTargetPlayerID, 0, cMyID);
         aiPlanSetVariableFloat(gNavyRepairPlan, cCombatPlanGatherDistance, 0, 10.0);
         aiPlanSetVariableInt(gNavyRepairPlan, cCombatPlanRefreshFrequency, 0, cDifficultyCurrent >= cDifficultyHard ? 300 : 1000);
         aiPlanAddUnitType(gNavyRepairPlan, cUnitTypeAbstractWarShip, 0, 0, 0); // Up later.
         
         debugMilitary("Creating primary navy repair plan at: " + ownDockPosition);
         aiPlanSetActive(gNavyRepairPlan);
         anwProbe("navy.repair", "plan=" + gNavyRepairPlan + " dock=" + ownDockID +
            " pos=" + anwFmtVec(ownDockPosition));
      }
      aiPlanSetVariableVector(gNavyRepairPlan, cCombatPlanTargetPoint, 0, ownDockPosition);
      aiPlanSetInitialPosition(gNavyRepairPlan, ownDockPosition);
      aiPlanSetVariableVector(gNavyRepairPlan, cCombatPlanGatherPoint, 0, ownDockPosition);

      int bestUnitID = -1;
      unitID = aiPlanGetUnitByIndex(gNavyRepairPlan, 0);
      if (kbUnitGetHealth(unitID) > 0.95)
      {
         aiTaskUnitMove(unitID, gNavyVec);
         aiPlanAddUnit(gNavyDefendPlan, unitID);
      }

      // Look for a ship to repair.
      float unitHitpoints = 0.0;
      int unitPlanID = -1;
      float bestUnitHitpoints = 9999.0;
      int shipQueryID = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
      int numberFound = kbUnitQueryExecute(shipQueryID);
      for (i = 0; < numberFound)
      {
         unitID = kbUnitQueryGetResult(shipQueryID, i);
         unitPlanID = kbUnitGetPlanID(unitID);
         if ((aiPlanGetDesiredPriority(unitPlanID) > 22) || 
             (aiPlanGetType(unitPlanID) == cPlanTransport) ||
             (kbUnitGetHealth(unitID) > 0.95))
         {
            continue;
         }
         unitHitpoints = kbUnitGetCurrentHitpoints(unitID);
         if (unitHitpoints < bestUnitHitpoints)
         {
            bestUnitID = unitID;
            bestUnitHitpoints = unitHitpoints;
         }
      }

      if (bestUnitID >= 0)
      {
         aiPlanAddUnitType(gNavyRepairPlan, cUnitTypeAbstractWarShip, 1, 1, 1);
         aiPlanAddUnit(gNavyRepairPlan, bestUnitID);
      }
      else
      {
         aiPlanAddUnitType(gNavyRepairPlan, cUnitTypeAbstractWarShip, 0, 0, 0);
      }
   }
   // if (gMaxWarShipsMaintain < 0)
   // {
   //    gMaxWarShipsMaintain = createSimpleMaintainPlan(cUnitTypeAbstractWarShip, limit, true, -1, 1);
   //    if (age == cAge2) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 60);
   //    } else if (age == cAge3) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 75);
   //    } else if (age == cAge4) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 85);
   //    } else if (age == cAge5) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 85);
   //    }
   //    aiPlanSetVariableInt(gMaxWarShipsMaintain, cTrainPlanBuildFromType, 0, gDockUnit);
   //    anwVerboseEcho("Maxed out military training!");
   // }
   // else
   // {
   //    if (age == cAge2) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 60);
   //    } else if (age == cAge3) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 75);
   //    } else if (age == cAge4) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 85);
   //    } else if (age == cAge5) {
   //       aiPlanSetDesiredPriority(gMaxWarShipsMaintain, 85);
   //    }
   //    aiPlanSetVariableInt(gMaxWarShipsMaintain, cTrainPlanNumberToMaintain, 0, limit);
   // }
}
//==============================================================================
/* transportMilitaryNaval
   Transport large armies across water to engage the enemy at their island base.
*/
//==============================================================================
rule transportMilitaryNaval
inactive
minInterval 10
{
   const int transportMilitaryTravel = 0;  // Initial setting for when we want to get military units to transport to another island...
   const int transportMilitaryAssault = 1; // Now that we are on the island, it's time to attack the enemy!
   const int transportMilitarySearch = 2;  // We have completely destroyed the enemy's town or do not know where it is, now we need to conduct a search.
   const int transportMilitaryReturn = 3;  // Nothing was found during the search, we can return to base now...
   
   vector myBaseLocation = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
   static int transportMilitaryMode = transportMilitaryTravel;
   static int militaryUnitQuery = -1;
   // Track transport plan creation times
   static int gTransportPlan1CreationTime = -1;
   static int gTransportPlan2CreationTime = -1;
   static int gReturnTransportCreationTime = -1;
   
   vector localIslandVector = cInvalidVector;
   vector coastLine = cInvalidVector;
   vector targetLocation = cInvalidVector;
   int targetLocationId = -1;
   int targetLocationGroupId = -1;
   int enemyBuildingId = -1;
   vector enemyBuildingLocation = cInvalidVector;
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;
   int numberOnIsland = 0;
   vector myBaseLoc = kbGetPlayerStartingPosition(cMyID);
   int myBaseAreaID = kbAreaGetIDByPosition(myBaseLoc);
   int myBaseAreaGroupID = kbAreaGroupGetIDByPosition(myBaseLoc);
   int currentLocalTime = xsGetTime();

   float nearbyPointX = 0.0;
   float nearbyPointZ = 0.0;
   float xFloat = 0.0;
   float zFloat = 0.0;
   
   int transportStallTimeout = 120000;  // 2 minutes in milliseconds

   // Check for stalled transport plans lacking units
   if (gIslandAssaultTransportPlanID >= 0 && gTransportPlan1CreationTime > 0) {
      int plan1Age = currentLocalTime - gTransportPlan1CreationTime;
      int plan1Units = aiPlanGetNumberUnits(gIslandAssaultTransportPlanID, cUnitTypeLogicalTypeLandMilitary);
      
      if (plan1Age > transportStallTimeout && plan1Units < 1) {
         anwVerboseEcho("Transport plan 1 has no units after 2 minutes, destroying...");
         aiPlanDestroy(gIslandAssaultTransportPlanID);
         gIslandAssaultTransportPlanID = -1;
         gTransportPlan1CreationTime = -1;
      }
   }
   
   if (gIslandAssaultTransportPlan2ID >= 0 && gTransportPlan2CreationTime > 0) {
      int plan2Age = currentLocalTime - gTransportPlan2CreationTime;
      int plan2Units = aiPlanGetNumberUnits(gIslandAssaultTransportPlan2ID, cUnitTypeLogicalTypeLandMilitary);
      
      if (plan2Age > transportStallTimeout && plan2Units < 1) {
         anwVerboseEcho("Transport plan 2 has no units after 2 minutes, destroying...");
         aiPlanDestroy(gIslandAssaultTransportPlan2ID);
         gIslandAssaultTransportPlan2ID = -1;
         gTransportPlan2CreationTime = -1;
      }
   }
   
   if (gIslandReturnTransportPlanID >= 0 && gReturnTransportCreationTime > 0) {
      int returnPlanAge = currentLocalTime - gReturnTransportCreationTime;
      int returnPlanUnits = aiPlanGetNumberUnits(gIslandReturnTransportPlanID, cUnitTypeLogicalTypeLandMilitary);
      
      if (returnPlanAge > transportStallTimeout && returnPlanUnits < 1) {
         anwVerboseEcho("Return transport plan has no units after 2 minutes, destroying...");
         aiPlanDestroy(gIslandReturnTransportPlanID);
         gIslandReturnTransportPlanID = -1;
         gReturnTransportCreationTime = -1;
      }
   }

   // Sync local mode with global mode
   if (gMilitaryTransportMode == 0) {
      transportMilitaryMode = transportMilitaryTravel;
   } else if (gMilitaryTransportMode == 1) {
      transportMilitaryMode = transportMilitaryAssault;
   } else if (gMilitaryTransportMode == 2) {
      transportMilitaryMode = transportMilitarySearch;
   } else if (gMilitaryTransportMode == 3) {
      transportMilitaryMode = transportMilitaryReturn;
   }

   // If no island has been found, we need to find one...
   if (gIslandFound == false) {
      localIslandVector = getRandomIslandToAttack();
      if (localIslandVector != cInvalidVector) {
         gProbableEnemyIsland = localIslandVector;
         gNavalInvasionCoastalPoint = coastalEdgeVector(myBaseLocation, gProbableEnemyIsland);
      } else {
         return;
      }
   } else {
      gNavalInvasionCoastalPoint = coastalEdgeVector(myBaseLocation, gProbableEnemyIsland);
   }

   // Validate coastal point
   if (gNavalInvasionCoastalPoint == cInvalidVector) {
      anwVerboseEcho("Invalid coastal point, resetting...");
      resetInvasionSequence();
      return;
   }

   // Check if we have seen the enemy base
   int closestBaseID = kbFindClosestBase(cPlayerRelationEnemyNotGaia, myBaseLocation);
   vector closestBaseLocation = kbBaseGetLocation(kbBaseGetOwner(closestBaseID), closestBaseID);
   int closestBaseAreaGroupID = kbAreaGroupGetIDByPosition(closestBaseLocation);

   // Find out if we have transports
   int transportUnitQueryID = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
   int transportNumberFound = kbUnitQueryExecute(transportUnitQueryID);
   int unitID = -1;
   int planID = -1;
   vector position = cInvalidVector;
   vector enemyBaseToAttack = cInvalidVector;
   bool transportRequired = false;

   if (transportNumberFound <= 0) {
      return;
   }

   // Find the units we want to transport
   int baseAreaGroupID = kbAreaGroupGetIDByPosition(kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID)));
   int areaGroupID = -1;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);

   // Abort if home is under attack
   if (transportMilitaryMode != transportMilitaryReturn && homeIslandUnderAttack() == true) {
      unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, gProbableEnemyIsland, 350.0);
      numberFound = kbUnitQueryExecute(unitQueryID);

      for (i = 0; < numberFound)
      {
         unitID = kbUnitQueryGetResult(unitQueryID, i);
         unitLocation = kbUnitGetPosition(unitID);
         unitLocationId = kbAreaGetIDByPosition(unitLocation);
         unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
         if (kbAreAreaGroupsPassableByLand(myBaseAreaGroupID, unitLocationGroupId) == false &&
            kbAreAreaGroupsPassableByLand(gProbableEnemyIslandGroupId, unitLocationGroupId) == true) {
               aiPlanDestroy(gIslandAssaultTransportPlanID);
               aiPlanDestroy(gIslandAssaultPlanID);
               aiPlanDestroy(gIslandSearchPlanID);
               gIslandAssaultTransportPlanID = -1;
               gTransportPlan1CreationTime = -1;
               gMilitaryTransportMode = 3;
               transportMilitaryMode = transportMilitaryReturn;
         }
      }
      return;
   }

   // Look for enemy buildings on the target island (use island center, larger search radius)
   enemyBuildingId = getClosestIslandUnitByLocation(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, 
      cUnitStateABQ, gIslandCenterPoint, 5000);
   
   if (enemyBuildingId > 0) {
      enemyBuildingLocation = kbUnitGetPosition(enemyBuildingId);
   }

   // Count units on the island
   int islandGroupForCount = kbAreaGroupGetIDByPosition(gIslandCenterPoint);
   if (islandGroupForCount < 0) {
      islandGroupForCount = kbAreaGroupGetIDByPosition(gProbableEnemyIsland);
   }
   
   unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   numberFound = kbUnitQueryExecute(unitQueryID);
   for (i = 0; < numberFound) {
      unitID = kbUnitQueryGetResult(unitQueryID, i);
      unitLocation = kbUnitGetPosition(unitID);
      unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      if (kbAreAreaGroupsPassableByLand(islandGroupForCount, unitLocationGroupId) == true &&
         kbUnitIsType(unitID, cUnitTypeHero) == false) {
         numberOnIsland++;
      }
   }
   anwVerboseEcho("Number on Island: " + numberOnIsland);

   // Transition to assault if enough units landed
   if (transportMilitaryMode == transportMilitaryTravel && 
      gActiveIslandInvasion == true && numberOnIsland > 5) {
      gMilitaryTransportMode = 1;
      transportMilitaryMode = transportMilitaryAssault;
   }

   anwVerboseEcho("Naval logic running! Current Mode: " + transportMilitaryMode);

   switch (transportMilitaryMode) {
      case transportMilitaryTravel: {
         // Clear unrelated transport plans
         if (aiPlanGetIDByIndex(cPlanTransport, -1, true, 0) >= 0 && gActiveIslandInvasion == false && gActiveVillagersTransport == false)
         {
            int planToDelete = aiPlanGetIDByIndex(cPlanTransport, -1, true, 0);
            if (planToDelete >= 0 &&
               planToDelete != gIslandAssaultTransportPlanID &&
               planToDelete != gIslandAssaultTransportPlan2ID) {
               aiPlanDestroy(planToDelete);
            }
         }

         // Need at least 2 ships
         if (transportNumberFound <= 1) {
            return;
         }
         
         // Check for stalled transport plan
         if (gIslandAssaultTransportPlanID >= 0) {
            int transportPlanState = aiPlanGetState(gIslandAssaultTransportPlanID);
            int unitsInPlan = aiPlanGetNumberUnits(gIslandAssaultTransportPlanID, cUnitTypeLogicalTypeLandMilitary);
            int elapsedTime = xsGetTime() - gInvasionInitialTime;
            
            // Timeout after 3 minutes with no progress
            if (elapsedTime > 180000 && numberOnIsland < 3) {
               anwVerboseEcho("Transport timed out after 3 minutes, resetting...");
               resetInvasionSequence();
               gTransportPlan1CreationTime = -1;
               gTransportPlan2CreationTime = -1;
               gReturnTransportCreationTime = -1;
               return;
            }
            
            // Plan became invalid
            if (transportPlanState == -1) {
               anwVerboseEcho("Transport plan state invalid, resetting...");
               resetInvasionSequence();
               gTransportPlan1CreationTime = -1;
               gTransportPlan2CreationTime = -1;
               gReturnTransportCreationTime = -1;
               return;
            }
            
            // Plan has no units and it's been a while
            if (unitsInPlan < 1 && elapsedTime > 30000) {
               anwVerboseEcho("Transport plan has no units, resetting...");
               resetInvasionSequence();
               gTransportPlan1CreationTime = -1;
               gTransportPlan2CreationTime = -1;
               gReturnTransportCreationTime = -1;
               return;
            }
         }
         
         // Create transport plan if needed
         if (gIslandAssaultTransportPlanID < 0) {
            gInvasionInitialTime = xsGetTime();
            
            for (i = 0; < numberFound)
            {
               unitID = kbUnitQueryGetResult(unitQueryID, i);
               position = kbUnitGetPosition(unitID);
               areaGroupID = kbAreaGroupGetIDByPosition(position);
               planID = kbUnitGetPlanID(unitID);
               transportRequired = true;
               break;
            }

            if (transportRequired == false) {
               return;
            }

            gIslandCenterPoint = kbAreaGroupGetCenter(kbAreaGroupGetIDByPosition(gProbableEnemyIsland));

            if (closestBaseID != -1) {
               gProbableEnemyIsland = kbBaseGetLocation(kbBaseGetOwner(closestBaseID), closestBaseID);
            } else {
               gProbableEnemyIsland = gIslandCenterPoint;
            }
            
            anwVerboseEcho("Creating transport plan");
            // Calculate coastal point on HOME island (facing the enemy island)
            vector homeCoastalPickup = coastalEdgeVector(gProbableEnemyIsland, myBaseLocation);
            //sendStatement(1, cAICommPromptToAllyConfirm, homeCoastalPickup);
            gIslandAssaultTransportPlanID = createInvasionTransportPlan(homeCoastalPickup, gNavalInvasionCoastalPoint, 100, false);

            if (gIslandAssaultTransportPlanID == -1) {
               anwVerboseEcho("Failed to create transport plan, resetting...");
               resetInvasionSequence();
               return;
            }
            
            // Track creation time
            gTransportPlan1CreationTime = xsGetTime();
            
            // Query units near base for transport
            unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, myBaseLoc, 150.0);
            numberFound = kbUnitQueryExecute(unitQueryID);
            
            // Use flexible unit requirements - min is half, not exact count
            int minUnits = numberFound / 2;
            if (minUnits < 5) {
               minUnits = 5;
            }
            if (minUnits > numberFound) {
               minUnits = numberFound;
            }
            aiPlanAddUnitType(gIslandAssaultTransportPlanID, cUnitTypeLogicalTypeLandMilitary, minUnits, numberFound, numberFound);

            int unitsAdded = 0;
            for (i = 0; < numberFound)
            {
               unitID = kbUnitQueryGetResult(unitQueryID, i);
               unitLocation = kbUnitGetPosition(unitID);
               unitLocationId = kbAreaGetIDByPosition(unitLocation);
               unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
               if (kbAreAreaGroupsPassableByLand(myBaseAreaGroupID, unitLocationGroupId) &&
                   kbUnitIsType(unitID, cUnitTypeHero) == false) {
                  aiPlanAddUnit(gIslandAssaultTransportPlanID, unitID);
                  unitsAdded++;
               }
            }

            aiPlanSetActive(gIslandAssaultTransportPlanID);

            anwVerboseEcho("Transporting military!");
            gNumberTransported = aiPlanGetNumberUnits(gIslandAssaultTransportPlanID, cUnitTypeLogicalTypeLandMilitary);
            anwVerboseEcho("Units in transport plan: " + gNumberTransported);
            gActiveIslandInvasion = true;
            gMilitaryTransportMode = 1;
         }
         break;
      }
      case transportMilitaryAssault: {
         closestBaseID = kbFindClosestBase(cPlayerRelationEnemyNotGaia, gProbableEnemyIsland);
         closestBaseLocation = kbBaseGetLocation(kbBaseGetOwner(closestBaseID), closestBaseID);
         closestBaseAreaGroupID = kbAreaGroupGetIDByPosition(closestBaseLocation);

         if (aiPlanGetActive(gIslandAssaultTransportPlanID) == false && 
             aiPlanGetActive(gIslandAssaultTransportPlan2ID) == false && numberOnIsland < 5) {
            anwVerboseEcho("Assault failed - not enough units landed, resetting...");
            resetInvasionSequence();
            gTransportPlan1CreationTime = -1;
            gTransportPlan2CreationTime = -1;
            gReturnTransportCreationTime = -1;
            return;
         }

         // Wait for initial force to land (at least 30% or minimum 3 units)
         int minLanded = gNumberTransported * 0.3;
         if (minLanded < 3) {
            minLanded = 3;
         }
         if (numberOnIsland < minLanded) {
            anwVerboseEcho("Waiting for more units to land: " + numberOnIsland + "/" + minLanded);
            return;
         }

         anwVerboseEcho("Assault mode - OnIsland: " + numberOnIsland + " BaseID: " + closestBaseID + " Building: " + enemyBuildingId);
         
         // === REINFORCEMENT LOGIC ===
         if (aiPlanGetActive(gIslandAssaultTransportPlanID) == false && gIslandAssaultTransportPlan2ID == -1) {
            
            // Query military units at home base
            int homeUnitQuery = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, myBaseLoc, 1450.0);
            int homeUnitsFound = kbUnitQueryExecute(homeUnitQuery);
            
            // First pass: just count eligible units
            int availableReinforcements = 0;
            
            for (i = 0; < homeUnitsFound)
            {
               unitID = kbUnitQueryGetResult(homeUnitQuery, i);
               unitLocation = kbUnitGetPosition(unitID);
               unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
               
               if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
                  continue;
               }
               if (kbAreAreaGroupsPassableByLand(myBaseAreaGroupID, unitLocationGroupId) == false) {
                  continue;
               }
               
               availableReinforcements++;
            }
            
            anwVerboseEcho("Available reinforcements: " + availableReinforcements);
            
            if (availableReinforcements >= 10) {
               
               homeCoastalPickup = coastalEdgeVector(gProbableEnemyIsland, myBaseLocation);
               gIslandAssaultTransportPlan2ID = createInvasionTransportPlan(homeCoastalPickup, gNavalInvasionCoastalPoint, 99, false);
               
               if (gIslandAssaultTransportPlan2ID >= 0) {
                  
                  // Track creation time
                  gTransportPlan2CreationTime = xsGetTime();
                  
                  // RE-EXECUTE the query - createInvasionTransportPlan's internal queries invalidated results
                  homeUnitQuery = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, myBaseLoc, 1450.0);
                  homeUnitsFound = kbUnitQueryExecute(homeUnitQuery);
                  
                  anwVerboseEcho("Re-queried units: " + homeUnitsFound);
                  
                  int minReinforcements = availableReinforcements / 2;
                  if (minReinforcements < 5) {
                     minReinforcements = 5;
                  }
                  
                  aiPlanAddUnitType(gIslandAssaultTransportPlan2ID, cUnitTypeLogicalTypeLandMilitary, minReinforcements, availableReinforcements, availableReinforcements);
                  
                  int reinforcementsAdded = 0;
                  for (i = 0; < homeUnitsFound)
                  {
                     unitID = kbUnitQueryGetResult(homeUnitQuery, i);
                     unitLocation = kbUnitGetPosition(unitID);
                     unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
                     
                     if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
                        continue;
                     }
                     if (kbAreAreaGroupsPassableByLand(myBaseAreaGroupID, unitLocationGroupId) == false) {
                        continue;
                     }
                     
                     // Remove from any existing plan
                     int existingPlan = kbUnitGetPlanID(unitID);
                     if (existingPlan >= 0) {
                        aiPlanRemoveUnit(existingPlan, unitID);
                     }
                     
                     // Add to transport
                     if (aiPlanAddUnit(gIslandAssaultTransportPlan2ID, unitID)) {
                        reinforcementsAdded++;
                     }
                  }
                  
                  anwVerboseEcho("Reinforcements added: " + reinforcementsAdded);
                  
                  if (reinforcementsAdded < 5) {
                     anwVerboseEcho("Insufficient reinforcements available: " + reinforcementsAdded);
                     aiPlanDestroy(gIslandAssaultTransportPlan2ID);
                     gIslandAssaultTransportPlan2ID = -1;
                     gTransportPlan2CreationTime = -1;
                  } else {
                     aiPlanSetActive(gIslandAssaultTransportPlan2ID);
                     gNumberTransported = gNumberTransported + reinforcementsAdded;
                  }
               }
            }
         }

         // Check if reinforcement transport completed
         if (gIslandAssaultTransportPlan2ID >= 0 && aiPlanGetActive(gIslandAssaultTransportPlan2ID) == false) {
            aiPlanDestroy(gIslandAssaultTransportPlan2ID);
            gIslandAssaultTransportPlan2ID = -1;
            gTransportPlan2CreationTime = -1;
            anwVerboseEcho("Reinforcement transport completed");
         }
         // === END REINFORCEMENT LOGIC ===
         
         // === SIMPLIFIED PLAN CREATION LOGIC ===
         bool hasActivePlan = false;
         if (gIslandAssaultPlanID >= 0 && aiPlanGetActive(gIslandAssaultPlanID) == true) {
            hasActivePlan = true;
         }
         if (gIslandSearchPlanID >= 0 && aiPlanGetActive(gIslandSearchPlanID) == true) {
            hasActivePlan = true;
         }
         
         bool hasTarget = (enemyBuildingId > 0);
         
         // If we have a target, we should be in assault mode
         if (hasTarget == true) {
            // Destroy search plan if it exists - we found the enemy
            if (gIslandSearchPlanID >= 0) {
               aiPlanDestroy(gIslandSearchPlanID);
               gIslandSearchPlanID = -1;
            }
            
            // Create assault plan if we don't have one
            if (gIslandAssaultPlanID < 0 || aiPlanGetActive(gIslandAssaultPlanID) == false) {
               anwVerboseEcho("Creating Assault Plan - enemy found at " + enemyBuildingLocation);
               warshipTraining();
               createIslandAssaultPlan(gNavalInvasionCoastalPoint, enemyBuildingLocation);
            } else {
               // Plan exists, just add more units
               warshipTraining();
               addUnitsToInvasionPlan(gIslandAssaultPlanID);
            }
         } else {
            // No target found - use search mode
            if (gIslandSearchPlanID < 0 || aiPlanGetActive(gIslandSearchPlanID) == false) {
               anwVerboseEcho("Creating Search Plan - no enemy found yet");
               createIslandSearchPlan(gNavalInvasionCoastalPoint, gIslandCenterPoint);
            } else {
               addUnitsToInvasionPlan(gIslandSearchPlanID);
            }
         }
         
         // Always try to assign idle units
         if (gIslandAssaultPlanID >= 0) {
            assignIdleIslandUnitsToAssault();
         } else if (gIslandSearchPlanID >= 0) {
            assignIdleIslandUnitsToSearch();
         }
         
         // Check if plans died but units are still stranded - recreate plans at their location
         checkAndRecreateStrandedUnitPlans(1, hasTarget);
         
         // Check for failure conditions
         if (hasActivePlan == false && numberOnIsland < 3) {
            anwVerboseEcho("No active plan and too few units, resetting...");
            resetInvasionSequence();
            gTransportPlan1CreationTime = -1;
            gTransportPlan2CreationTime = -1;
            gReturnTransportCreationTime = -1;
            return;
         }
         break;
      }
      case transportMilitarySearch: {
         anwVerboseEcho("Search mode active... Transport Active: "+aiPlanGetActive(gIslandAssaultTransportPlanID)+"");

         if (aiPlanGetActive(gIslandAssaultTransportPlanID) == false && numberOnIsland < 3) {
            anwVerboseEcho("Search failed, resetting...");
            resetInvasionSequence();
            gTransportPlan1CreationTime = -1;
            gTransportPlan2CreationTime = -1;
            gReturnTransportCreationTime = -1;
            return;
         }

         // Check for enemy buildings and transition back to assault if found
         if (enemyBuildingId > 0) {
            anwVerboseEcho("Enemy found during search, switching to assault!");
            aiPlanDestroy(gIslandSearchPlanID);
            gIslandSearchPlanID = -1;
            gMilitaryTransportMode = 1;
            transportMilitaryMode = transportMilitaryAssault;
            return;
         }

         int minUnitsForSearch = gNumberTransported / 3;
         if (minUnitsForSearch < 2) {
            minUnitsForSearch = 2;
         }

         if (gIslandSearchPlanID < 0 || aiPlanGetActive(gIslandSearchPlanID) == false) {
            if (numberOnIsland >= minUnitsForSearch) {
               aiPlanDestroy(gIslandAssaultTransportPlanID);
               gIslandAssaultTransportPlanID = -1;
               gTransportPlan1CreationTime = -1;
               createIslandSearchPlan(gNavalInvasionCoastalPoint, gIslandCenterPoint);
            }
         } else {
            addUnitsToInvasionPlan(gIslandSearchPlanID);
            assignIdleIslandUnitsToSearch();
         }
         
         // Check if plans died but units are still stranded - recreate plans at their location
         checkAndRecreateStrandedUnitPlans(2, false);

         // Only transition to return if both plans are inactive/missing
         if ((gIslandAssaultPlanID < 0 || aiPlanGetActive(gIslandAssaultPlanID) == false) &&
             (gIslandSearchPlanID < 0 || aiPlanGetActive(gIslandSearchPlanID) == false)) {
            gMilitaryTransportMode = 3;
            transportMilitaryMode = transportMilitaryReturn;
         }
         break;
      }
      case transportMilitaryReturn: {
         anwVerboseEcho("Return mode active...");
         
         if (aiPlanGetIDByIndex(cPlanTransport, -1, true, 0) >= 0 && gIslandReturnTransportPlanID == -1) {
            int planToDeleteFinal = aiPlanGetIDByIndex(cPlanTransport, -1, true, 0);
            aiPlanDestroy(planToDeleteFinal);
         }

         if (transportNumberFound <= 0) {
            return;
         }
         
         if (gIslandReturnTransportPlanID == -1 && transportNumberFound > 0) {
            gIslandReturnTransportPlanID = createInvasionTransportPlan(gProbableEnemyIsland, coastalEdgeVector(gProbableEnemyIsland, myBaseLocation), 100, false);
            
            if (gIslandReturnTransportPlanID == -1) {
               anwVerboseEcho("Failed to create return transport, resetting...");
               resetInvasionSequence();
               gTransportPlan1CreationTime = -1;
               gTransportPlan2CreationTime = -1;
               gReturnTransportCreationTime = -1;
               return;
            }
            
            // Track creation time
            gReturnTransportCreationTime = xsGetTime();
            
            unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, gProbableEnemyIsland, 150.0);
            numberFound = kbUnitQueryExecute(unitQueryID);
            
            // Flexible return requirements
            int minReturn = numberFound / 2;
            if (minReturn < 1) {
               minReturn = 1;
            }
            aiPlanAddUnitType(gIslandReturnTransportPlanID, cUnitTypeLogicalTypeLandMilitary, minReturn, numberFound, numberFound);

            for (i = 0; < numberFound)
            {
               unitID = kbUnitQueryGetResult(unitQueryID, i);
               unitLocation = kbUnitGetPosition(unitID);
               unitLocationId = kbAreaGetIDByPosition(unitLocation);
               unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
               if (kbAreAreaGroupsPassableByLand(myBaseAreaGroupID, unitLocationGroupId) == false &&
                  kbAreAreaGroupsPassableByLand(gProbableEnemyIslandGroupId, unitLocationGroupId) == true) {
                  aiPlanAddUnit(gIslandReturnTransportPlanID, unitID);
               }
            }

            aiPlanSetActive(gIslandReturnTransportPlanID);
            gInvasionResetWaitTime = xsGetTime();
         }
         
         // Timeout for return as well
         if (gIslandReturnTransportPlanID >= 0) {
            int returnElapsed = xsGetTime() - gInvasionResetWaitTime;
            if (returnElapsed > 120000) {
               anwVerboseEcho("Return transport timed out, resetting...");
               resetInvasionSequence();
               gTransportPlan1CreationTime = -1;
               gTransportPlan2CreationTime = -1;
               gReturnTransportCreationTime = -1;
               return;
            }
         }

         if (gIslandReturnTransportPlanID == -1 || 
            (aiPlanGetActive(gIslandReturnTransportPlanID) == false && (xsGetTime() - gInvasionResetWaitTime) > 30000)) {
            anwVerboseEcho("Return complete, resetting for next invasion...");
            resetInvasionSequence();
            gTransportPlan1CreationTime = -1;
            gTransportPlan2CreationTime = -1;
            gReturnTransportCreationTime = -1;
         }
         break;
      }
   }
   return;
}
//==============================================================================
// Island Base Manager
//
// Purpose: Establish and manage an island base.
// Steps:
// 1) Validate treaty and island conditions.
// 2) Select a suitable island location.
// 3) Create a build plan using an available fort wagon to build an island fort.
// 4) Transition state once the fort is built and the base is active.
//==============================================================================
rule islandBaseManager
inactive
minInterval 20
maxInterval 20
{
   const int cIslandBaseStateNone = 0;
   const int cIslandBaseStateBuilding = 1;
   const int cIslandBaseStateActive = 2;

   int unitID = -1;
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;

   // Find out if we have transports yet...
   int transportUnitQueryID = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
   int transportNumberFound = kbUnitQueryExecute(transportUnitQueryID);

   // First check to just return if there are no transports...
   if (transportNumberFound <= 0) {
      return;
   }

   if (aiTreatyActive() == true) {
      return;
   }

   if (gStartOnDifferentIslands == false) {
      xsDisableSelf();
      return;
   }

   switch (gIslandBaseState) {
      case cIslandBaseStateNone: {
         // If we don't have an island base location yet, try to find one from gProbableEnemyIsland
         if (gIslandBaseLocation == cInvalidVector) {
            if (gProbableEnemyIsland != cInvalidVector) {
               // Get our home base location as the origin
               vector homeBase = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
               
               // Find the coastal edge on the enemy island closest to our home base
               // Walking from enemy island toward our base, get the last land point before water
               gIslandBaseLocation = coastalEdgeVector(homeBase, gProbableEnemyIsland, true, false, false);
               
               if (gIslandBaseLocation != cInvalidVector) {
                  anwVerboseEcho("Island base location set: " + gIslandBaseLocation);
               } else {
                  anwVerboseEcho("Failed to find coastal location on enemy island.");
                  return;
               }
            } else {
               // No valid enemy island location yet
               return;
            }
         }
         
         // Now we have a valid gIslandBaseLocation, create the base
         if (gIslandBaseLocation != cInvalidVector && gIslandBaseID < 0) {
            gIslandBaseID = createSettlementBase(gIslandBaseLocation, false);
            kbBaseSetActive(cMyID, gIslandBaseID, true);
            gIslandBaseState = cIslandBaseStateBuilding;
            anwVerboseEcho("Island base created at: " + gIslandBaseLocation);
         }

         break;
      }
      case cIslandBaseStateBuilding: {
         anwVerboseEcho("Building island base! " + kbBaseGetActive(cMyID, gIslandBaseID));
         
         if (kbBaseGetActive(cMyID, gIslandBaseID) == false && gIslandBaseID >= 0) {
            kbBaseDestroy(cMyID, gIslandBaseID);
            gIslandBaseID = -1;
         }

         int buildingsAtLocation = kbUnitQueryExecute(createSimpleUnitQuery(
               cUnitTypeLogicalTypeBuildingsNotWalls, 
               cMyID, 
               cUnitStateAlive,  // Changed to Alive - only count finished buildings
               gIslandBaseLocation, 
               75));

         // Create build plans if we haven't yet
         if (gIslandBaseBarracksPlan < 0) {
            if (gIslandBaseID < 0) {
               gIslandBaseID = createMilitaryBase(gIslandBaseLocation, false);
               kbBaseSetActive(cMyID, gIslandBaseID, true);
            }
            gIslandBaseBarracksPlan = createSpacedLocationBuildPlan(cUnitTypeBarracks, 1, 100, true, cMilitaryEscrowID, gIslandBaseLocation, 1);
            createSpacedLocationBuildPlan(cUnitTypeStable, 1, 100, true, cMilitaryEscrowID, gIslandBaseLocation, 1);
            createSpacedLocationBuildPlan(gTowerUnit, 1, 100, true, cEconomyEscrowID, gIslandBaseLocation, 1);
            createSpacedLocationBuildPlan(cUnitTypeArtilleryDepot, 1, 100, true, cEconomyEscrowID, gIslandBaseLocation, 1);
            anwVerboseEcho("Island base build plans created.");
         }
         
         // Only transition to Active once we have at least one finished building
         if (buildingsAtLocation >= 1) {
            gIslandBaseState = cIslandBaseStateActive;
            anwVerboseEcho("Island base has buildings, transitioning to Active.");
         }
         
         break;
      }
      case cIslandBaseStateActive: {
         int islandBaseUnitQueryID = createSimpleUnitQuery(
            cUnitTypeLogicalTypeBuildingsNotWalls, 
            cMyID, 
            cUnitStateABQ, 
            gIslandBaseLocation, 
            150.0);
         int islandBaseBuildingsFound = kbUnitQueryExecute(islandBaseUnitQueryID);
         int islandBaseBuilding = -1;
         
         anwVerboseEcho("Active island Base! " + kbBaseGetActive(cMyID, gIslandBaseID) + "");
         
         if (kbBaseGetActive(cMyID, gIslandBaseID) == true) {
            // Assign any buildings at this location to the base.
            for (i = 0; i < islandBaseBuildingsFound; i++) {
               islandBaseBuilding = kbUnitQueryGetResult(islandBaseUnitQueryID, i);
               if (kbUnitGetBaseID(islandBaseBuilding) != gIslandBaseID) {
                  kbBaseAddUnit(cMyID, gIslandBaseID, islandBaseBuilding);
               }
            }
            aiPlanSetActive(gIslandBaseMaintainPlan, true);
            updateSecondaryBaseMilitaryTrainPlans(gIslandBaseID);
            
            // Manage troops created at island base
            manageIslandBaseTroops();
         }
         else if (kbBaseGetActive(cMyID, gIslandBaseID) == false && islandBaseBuildingsFound > 0) {
            // If the base is not active but there are buildings, recreate the base.
            kbBaseDestroy(cMyID, gIslandBaseID);
            gIslandBaseID = createMilitaryBase(gIslandBaseLocation, false);
            for (i = 0; i < islandBaseBuildingsFound; i++) {
               islandBaseBuilding = kbUnitQueryGetResult(islandBaseUnitQueryID, i);
               kbBaseAddUnit(cMyID, gIslandBaseID, islandBaseBuilding);
               if (gActiveIslandInvasion == true) {
                  aiTaskUnitTrain(islandBaseBuilding, gIslandBaseLandUnit);
               }
            }
            kbBaseSetActive(cMyID, gIslandBaseID, true);
            updateSecondaryBaseMilitaryTrainPlans(gIslandBaseID);
         }

         break;
      }
   }
}
//==============================================================================
/* colonyCreationManager
   Creates a secondary base.
*/
//==============================================================================
rule colonyCreationManager
inactive
minInterval 20
{
   int unitID = -1;
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;
   int colonialAreaGroupID = -1;
   
   // Only run on water maps with different starting islands
   if (gStartOnDifferentIslands == false || gWaterMap == false) {
      return;
   }
   
   // Find out if we have transports
   int transportUnitQueryID = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
   int transportNumberFound = kbUnitQueryExecute(transportUnitQueryID);

   // Need transports to establish a colony
   if (transportNumberFound <= 0 && gColonialBasePosition == cInvalidVector) {
      return;
   }
   
   // Find an island to colonize if we haven't yet
   if (gColonialBasePosition == cInvalidVector) {
      gColonialBasePosition = getRandomIslandToColonize();
      if (gColonialBasePosition != cInvalidVector) {
         anwVerboseEcho("Found island to colonize!");
         createSpacedLocationBuildPlan(cUnitTypeTownCenter, 1, 100, true, cEconomyEscrowID, gColonialBasePosition, 1);
      } else {
         return;
      }
   }
   
   colonialAreaGroupID = kbAreaGroupGetIDByPosition(gColonialBasePosition);
   
   // Check if we have buildings on the colonial island
   int colonialBuildingQuery = createSimpleUnitQuery(cUnitTypeLogicalTypeBuildingsNotWalls, cMyID, cUnitStateAlive, gColonialBasePosition, 150.0);
   int colonialBuildingsFound = kbUnitQueryExecute(colonialBuildingQuery);
   
   if (colonialBuildingsFound <= 0) {
      // No buildings yet, wait for TC to be built
      return;
   }
   
   // Create the colonial base if it doesn't exist
   if (gColonialBaseId < 1) {
      gColonialBaseId = createSettlementBase(gColonialBasePosition, false);
      kbBaseSetEconomy(cMyID, gColonialBaseId, true);
      kbBaseSetMaximumResourceDistance(cMyID, gColonialBaseId, 100.0);
      kbBaseSetMilitaryGatherPoint(cMyID, gColonialBaseId, gColonialBasePosition);
      kbBaseSetActive(cMyID, gColonialBaseId, true);

      // Create gather plans for this base
      gColonialFoodGatherPlan = createGatherPlan(gColonialBasePosition, gColonialBaseId, cResourceFood, 95);
      gColonialWoodGatherPlan = createGatherPlan(gColonialBasePosition, gColonialBaseId, cResourceWood, 95);
      gColonialGoldGatherPlan = createGatherPlan(gColonialBasePosition, gColonialBaseId, cResourceGold, 95);

      anwVerboseEcho("Colonial base created! ID: " + gColonialBaseId);
      return;
   }
   
   // Ensure base stays active
   if (kbBaseGetActive(cMyID, gColonialBaseId) == false) {
      kbBaseSetMaximumResourceDistance(cMyID, gColonialBaseId, 750.0);
      kbBaseSetEconomy(cMyID, gColonialBaseId, true);
      kbBaseSetActive(cMyID, gColonialBaseId, true);
      updateMilitaryTrainPlanBuildings(gColonialBaseId);
   }
   
   // Query buildings under construction ONCE, outside the loop
   int constructionQuery = createSimpleUnitQuery(cUnitTypeLogicalTypeBuildingsNotWalls, cMyID, cUnitStateBuilding, gColonialBasePosition, 100.0);
   int buildingsUnderConstruction = kbUnitQueryExecute(constructionQuery);
   int buildingId = -1;
   if (buildingsUnderConstruction > 0) {
      buildingId = kbUnitQueryGetResult(constructionQuery, 0);
   }
   
   // Query villagers that are ACTUALLY ON the colonial island
   int islandVillagerQuery = createSimpleUnitQuery(gEconUnit, cMyID, cUnitStateAlive);
   int totalVillagersFound = kbUnitQueryExecute(islandVillagerQuery);
   
   int villagersOnIsland = 0;
   int buildersAssigned = 0;
   int maxBuilders = 3;  // Limit builders so others can gather
   
   // Count and assign villagers on the island
   for (i = 0; < totalVillagersFound)
   {
      unitID = kbUnitQueryGetResult(islandVillagerQuery, i);
      unitLocation = kbUnitGetPosition(unitID);
      unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      
      // Check if villager is actually on the colonial island
      if (kbAreAreaGroupsPassableByLand(colonialAreaGroupID, unitLocationGroupId) == false) {
         continue;
      }
      
      villagersOnIsland++;
      
      // Make sure they're assigned to this base
      int currentBaseID = kbUnitGetBaseID(unitID);
      if (currentBaseID != gColonialBaseId) {
         kbBaseRemoveUnit(cMyID, currentBaseID, unitID);
         kbBaseAddUnit(cMyID, gColonialBaseId, unitID);
      }
      
      // Only assign a limited number of villagers to construction
      if (buildingId >= 0 && buildersAssigned < maxBuilders) {
         int existingPlan = kbUnitGetPlanID(unitID);
         if (existingPlan >= 0) {
            aiPlanRemoveUnit(existingPlan, unitID);
         }
         aiTaskUnitWork(unitID, buildingId);
         buildersAssigned++;
         continue;
      }
      
      // Assign remaining villagers to gather plans
      int currentPlan = kbUnitGetPlanID(unitID);
      if (currentPlan != gColonialFoodGatherPlan && 
          currentPlan != gColonialWoodGatherPlan && 
          currentPlan != gColonialGoldGatherPlan) {
         
         // Remove from any existing plan first
         if (currentPlan >= 0) {
            aiPlanRemoveUnit(currentPlan, unitID);
         }
         
         // Assign to a colonial gather plan
         int r = aiRandInt(3);
         if (r == 0) {
            aiPlanAddUnit(gColonialFoodGatherPlan, unitID);
         } else if (r == 1) {
            aiPlanAddUnit(gColonialWoodGatherPlan, unitID);
         } else {
            aiPlanAddUnit(gColonialGoldGatherPlan, unitID);
         }
      }
   }
   
   anwVerboseEcho("Colonial base - Villagers on island: " + villagersOnIsland + ", Builders: " + buildersAssigned);
   
   // Queue buildings if needed
   if (buildingExistsOrQueued(gColonialBaseId, gFarmUnit) == false) {
      createSpacedLocationBuildPlan(gFarmUnit, 1, 100, true, cEconomyEscrowID, gColonialBasePosition, 1);
   }
   
   if (buildingExistsOrQueued(gColonialBaseId, gPlantationUnit) == false) {
      createSpacedLocationBuildPlan(gPlantationUnit, 1, 100, true, cEconomyEscrowID, gColonialBasePosition, 1);
   }

   if (buildingExistsOrQueued(gColonialBaseId, cUnitTypeBarracks) == false) {
      createSpacedLocationBuildPlan(cUnitTypeBarracks, 1, 100, true, cMilitaryEscrowID, gColonialBasePosition, 1);
   }

   if (buildingExistsOrQueued(gColonialBaseId, cUnitTypeStable) == false) {
      createSpacedLocationBuildPlan(cUnitTypeStable, 1, 100, true, cMilitaryEscrowID, gColonialBasePosition, 1);
   }

   if (buildingExistsOrQueued(gColonialBaseId, gTowerUnit) == false) {
      createSpacedLocationBuildPlan(gTowerUnit, 1, 100, true, cMilitaryEscrowID, gColonialBasePosition, 1);
   }

   if (buildingExistsOrQueued(gColonialBaseId, cUnitTypeArtilleryDepot) == false) {
      createSpacedLocationBuildPlan(cUnitTypeArtilleryDepot, 1, 100, true, cMilitaryEscrowID, gColonialBasePosition, 1);
   }
}
//==============================================================================
/* getRandomDockToAttack
   Finds a random enemy dock to attack if we have seen one.
*/
//==============================================================================
rule getRandomDockToAttack
inactive
minInterval 10
{
   vector startingLoc = kbGetPlayerStartingPosition(cMyID);
   vector enemyDockVector = enemyDockTarget(startingLoc);
   int shipQueryId = createIdleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(shipQueryId);
//sendStatement(1, cAICommPromptToAllyConfirm, enemyDockVector);
   if (enemyDockVector != cInvalidVector && 
   (numberFound > 6 && gWaterDockAttackPlan == -1 || numberFound > 6 && 
      aiPlanGetActive(gWaterDockAttackPlan) == false)) {
      gWaterDockAttackPlan = aiPlanCreate("Dock Destroyer Plan", cPlanCombat);
      aiPlanAddUnitType(gWaterDockAttackPlan, cUnitTypeAbstractWarShip, 5, numberFound * .8, numberFound);
      aiPlanSetVariableInt(gWaterDockAttackPlan, cCombatPlanCombatType, 0, cCombatPlanCombatTypeAttack);
      aiPlanSetVariableInt(gWaterDockAttackPlan, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
      aiPlanSetVariableVector(gWaterDockAttackPlan, cCombatPlanTargetPoint, 0, enemyDockVector);
      aiPlanSetVariableVector(gWaterDockAttackPlan, cCombatPlanGatherPoint, 0, gNavyVec);
      aiPlanSetVariableFloat(gWaterDockAttackPlan, cCombatPlanGatherDistance, 0, 1500.0);
      aiPlanSetVariableInt(gWaterDockAttackPlan, cCombatPlanAttackRoutePattern, 0, cCombatPlanAttackRoutePatternRandom);
      aiPlanSetVariableBool(gWaterDockAttackPlan, cCombatPlanAllowMoreUnitsDuringAttack, 0, true);
      aiPlanSetVariableInt(gWaterDockAttackPlan, cCombatPlanRefreshFrequency, 0, cDifficultyCurrent >= cDifficultyHard ? 300 : 1000);

      aiPlanSetVariableInt(gWaterDockAttackPlan, cCombatPlanDoneMode, 0, cCombatPlanDoneModeRetreat | cCombatPlanDoneModeNoTarget);
      aiPlanSetVariableInt(gWaterDockAttackPlan, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeOutnumbered);
      aiPlanSetVariableInt(gWaterDockAttackPlan, cCombatPlanNoTargetTimeout, 0, 30000);
      aiPlanSetBaseID(gWaterDockAttackPlan, kbUnitGetBaseID(getUnit(gDockUnit, cMyID, cUnitStateAlive)));
      aiPlanSetInitialPosition(gWaterDockAttackPlan, gNavyVec);

      aiPlanSetDesiredPriority(gWaterDockAttackPlan, 86);
      anwLogCombatPlanConfig("create", gWaterDockAttackPlan, "dock-destroyer");
      aiPlanSetActive(gWaterDockAttackPlan);
      anwVerboseEcho("Let's go destroy some docks!");
   }
}