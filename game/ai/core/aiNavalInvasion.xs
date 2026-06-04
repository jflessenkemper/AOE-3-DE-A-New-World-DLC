vector findIslandBuildings(vector originPoint = cInvalidVector) {

   int buildingQueryId = createSimpleUnitQuery(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(buildingQueryId);
   int originPointGroupId = kbAreaGroupGetIDByPosition(originPoint);
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;
   int unitID = -1;

   for (i = 0; < numberFound) {
      unitID = kbUnitQueryGetResult(buildingQueryId, i);
      unitLocation = kbUnitGetPosition(unitID);
      unitLocationId = kbAreaGetIDByPosition(unitLocation);
      unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      if (kbAreAreaGroupsPassableByLand(originPointGroupId, unitLocationGroupId) == true) {
         return unitLocation;
      }
   }
   
   return cInvalidVector;
}
//==============================================================================
// assignCoastalUnitsToAssault
// Finds units near the coastal landing point and assigns them to the assault
//==============================================================================
void assignCoastalUnitsToAssault()
{
   if (gNavalInvasionCoastalPoint == cInvalidVector) {
      return;
   }
   
   // Only assign if we have an active assault or search plan
   int targetPlan = -1;
   if (gIslandAssaultPlanID >= 0 && aiPlanGetActive(gIslandAssaultPlanID)) {
      targetPlan = gIslandAssaultPlanID;
   } else if (gIslandSearchPlanID >= 0 && aiPlanGetActive(gIslandSearchPlanID)) {
      targetPlan = gIslandSearchPlanID;
   }
   
   if (targetPlan < 0) {
      return;
   }
   
   // Query units near the coastal point
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, 
      gNavalInvasionCoastalPoint, 50.0);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   
   int unitsAssigned = 0;
   
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      
      // Skip heroes
      if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
         continue;
      }
      
      int currentPlan = kbUnitGetPlanID(unitID);
      
      // Skip if already in target plan
      if (currentPlan == targetPlan) {
         continue;
      }
      
      // Check if unit is idle or in low priority plan
      bool shouldAssign = false;
      if (currentPlan < 0) {
         shouldAssign = true;
      } else if (aiPlanGetActive(currentPlan) == false) {
         shouldAssign = true;
      } else if (aiPlanGetDesiredPriority(currentPlan) < 80) {
         shouldAssign = true;
      }
      
      if (shouldAssign) {
         if (currentPlan >= 0) {
            aiPlanRemoveUnit(currentPlan, unitID);
         }
         aiPlanAddUnit(targetPlan, unitID);
         unitsAssigned++;
      }
   }
   
   if (unitsAssigned > 0) {
      anwVerboseEcho("Assigned " + unitsAssigned + " coastal units to invasion plan");
   }
}
//==============================================================================
// createInvasionTransportPlan
// Creates a transport plan for moving units across water
//==============================================================================
int createInvasionTransportPlan(vector gatherPoint = cInvalidVector, vector targetPoint = cInvalidVector,
                        int pri = 100, bool returnWhenDone = false)
{
   int shipQueryID = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
   int unitQueryID = -1;
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;
   int unitID = -1;
   int numberFound = kbUnitQueryExecute(shipQueryID);
   int gatherPointId = kbAreaGetIDByPosition(gatherPoint);
   int gatherPointGroupId = kbAreaGroupGetIDByPosition(gatherPoint);
   int shipID = -1;
   float shipHitpoints = 0.0;
   int unitPlanID = -1;
   int transportID = -1;
   float transportHitpoints = 0.0;

   // First, find a valid transport ship BEFORE doing dock avoidance queries
   for (i = 0; < numberFound)
   {
      shipID = kbUnitQueryGetResult(shipQueryID, i);
      unitPlanID = kbUnitGetPlanID(shipID);
      if ((unitPlanID >= 0) && ((aiPlanGetDesiredPriority(unitPlanID) > pri) || (aiPlanGetType(unitPlanID) == cPlanTransport)) ||
         kbUnitGetProtoUnitID(shipID) == cUnitTypedeMercBattleship)
      {
         continue;
      }
      shipHitpoints = kbUnitGetCurrentHitpoints(shipID);
      if (shipHitpoints > transportHitpoints)
      {
         transportID = shipID;
         transportHitpoints = shipHitpoints;
      }
   }

   if (transportID < 0)
   {
      return (-1);
   }

   // === Find a gather point that avoids docks ===
   // Now safe to run queries since we already have our transportID
   vector adjustedGatherPoint = gatherPoint;
   vector baseLocation = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
   float minDockDistance = 25.0;
   
   // Check if current gather point is too close to a dock
   int dockQueryID = createSimpleUnitQuery(cUnitTypeAbstractDock, cPlayerRelationAny, cUnitStateABQ, gatherPoint, minDockDistance);
   int numDocks = kbUnitQueryExecute(dockQueryID);
   
   if (numDocks > 0) {
      anwVerboseEcho("Gather point too close to dock, searching for alternative...");
      
      bool foundValidPoint = false;
      vector directionToTarget = cInvalidVector;
      vector perpendicular = cInvalidVector;
      float offsetDistance = 0.0;
      vector offsetBase = cInvalidVector;
      vector testCoastalPoint = cInvalidVector;
      vector offsetTarget = cInvalidVector;
      int testDockQuery = -1;
      int testNumDocks = 0;
      int testGroupId = -1;
      
      // Try different offsets from base to find a coastal edge away from docks
      for (j = 1; <= 20)
      {
         // Calculate offset vectors perpendicular to the base-target direction
         directionToTarget = xsVectorNormalize(targetPoint - baseLocation);
         perpendicular = xsVectorSet(xsVectorGetZ(directionToTarget), 0.0, 0.0 - xsVectorGetX(directionToTarget));
         
         // Alternate between positive and negative offsets
         offsetDistance = ((j + 1) / 2) * 15.0;  // 15, 15, 30, 30, 45, 45...
         if (j % 2 == 0) {
            offsetDistance = 0.0 - offsetDistance;
         }
         
         offsetBase = baseLocation + (perpendicular * offsetDistance);
         testCoastalPoint = coastalEdgeVector(offsetBase, targetPoint);
         
         if (testCoastalPoint == cInvalidVector) {
            continue;
         }
         
         // Check if this point is far enough from docks
         testDockQuery = createSimpleUnitQuery(cUnitTypeAbstractDock, cPlayerRelationAny, cUnitStateABQ, testCoastalPoint, minDockDistance);
         testNumDocks = kbUnitQueryExecute(testDockQuery);
         
         if (testNumDocks == 0) {
            // Verify it's on the same landmass
            testGroupId = kbAreaGroupGetIDByPosition(testCoastalPoint);
            if (kbAreAreaGroupsPassableByLand(gatherPointGroupId, testGroupId) == true) {
               adjustedGatherPoint = testCoastalPoint;
               foundValidPoint = true;
               anwVerboseEcho("Found dock-free gather point at offset " + offsetDistance);
               break;
            }
         }
      }
      
      // If perpendicular offsets didn't work, try along the coastline direction
      if (foundValidPoint == false) {
         for (j = 1; <= 10)
         {
            // Move along the coast by offsetting the target point
            directionToTarget = xsVectorNormalize(targetPoint - baseLocation);
            perpendicular = xsVectorSet(xsVectorGetZ(directionToTarget), 0.0, 0.0 - xsVectorGetX(directionToTarget));
            
            offsetDistance = j * 20.0;
            
            // Try positive offset
            offsetTarget = targetPoint + (perpendicular * offsetDistance);
            testCoastalPoint = coastalEdgeVector(baseLocation, offsetTarget);
            
            if (testCoastalPoint != cInvalidVector) {
               testDockQuery = createSimpleUnitQuery(cUnitTypeAbstractDock, cPlayerRelationAny, cUnitStateABQ, testCoastalPoint, minDockDistance);
               testNumDocks = kbUnitQueryExecute(testDockQuery);
               
               if (testNumDocks == 0) {
                  testGroupId = kbAreaGroupGetIDByPosition(testCoastalPoint);
                  if (kbAreAreaGroupsPassableByLand(gatherPointGroupId, testGroupId) == true) {
                     adjustedGatherPoint = testCoastalPoint;
                     foundValidPoint = true;
                     anwVerboseEcho("Found dock-free gather point along coast (positive)");
                     break;
                  }
               }
            }
            
            // Try negative offset
            offsetTarget = targetPoint + (perpendicular * (0.0 - offsetDistance));
            testCoastalPoint = coastalEdgeVector(baseLocation, offsetTarget);
            
            if (testCoastalPoint != cInvalidVector) {
               testDockQuery = createSimpleUnitQuery(cUnitTypeAbstractDock, cPlayerRelationAny, cUnitStateABQ, testCoastalPoint, minDockDistance);
               testNumDocks = kbUnitQueryExecute(testDockQuery);
               
               if (testNumDocks == 0) {
                  testGroupId = kbAreaGroupGetIDByPosition(testCoastalPoint);
                  if (kbAreAreaGroupsPassableByLand(gatherPointGroupId, testGroupId) == true) {
                     adjustedGatherPoint = testCoastalPoint;
                     foundValidPoint = true;
                     anwVerboseEcho("Found dock-free gather point along coast (negative)");
                     break;
                  }
               }
            }
         }
      }
      
      if (foundValidPoint == false) {
         anwVerboseEcho("Warning: Could not find dock-free gather point, using original");
      }
   }
   // === END ===

   int planID = aiPlanCreate(kbGetUnitTypeName(kbUnitGetProtoUnitID(transportID)) + " Invasion Transport Plan", cPlanTransport);

   if (planID < 0)
   {
      return (-1);
   }

   aiPlanSetVariableInt(planID, cTransportPlanTransportID, 0, transportID);
   aiPlanSetVariableInt(planID, cTransportPlanTransportTypeID, 0, kbUnitGetProtoUnitID(transportID));
   aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(transportID), 1, 1, 1);
   if (aiPlanAddUnit(planID, transportID) == false)
   {
      aiPlanDestroy(planID);
      return (-1);
   }

   // Use the adjusted gather point that avoids docks
   aiPlanSetVariableVector(planID, cTransportPlanGatherPoint, 0, adjustedGatherPoint);
   aiPlanSetVariableVector(planID, cTransportPlanTargetPoint, 0, targetPoint);
   aiPlanSetVariableBool(planID, cTransportPlanReturnWhenDone, 0, returnWhenDone);
   aiPlanSetVariableBool(planID, cTransportPlanPersistent, 0, false);
   aiPlanSetVariableBool(planID, cTransportPlanMaximizeXportMovement, 0, true);
   aiPlanSetVariableBool(planID, cTransportPlanTakeMoreUnits, 0, true);
   aiPlanSetAttack(planID, true);
   aiPlanSetRequiresAllNeedUnits(planID, true);
   aiPlanSetVariableInt(planID, cTransportPlanPathType, 0, cTransportPathTypePoints);
   aiPlanSetDesiredPriority(planID, pri);

   return (planID);
}
//==============================================================================
// createIslandAssaultPlan
// Creates an assault plan to attack a known enemy position
//==============================================================================
void createIslandAssaultPlan(vector gatherPoint = cInvalidVector, vector targetPoint = cInvalidVector)
{
   if (anwIsCommanderAvailableForMajorAttack() == false) {
      anwVerboseEcho("createIslandAssaultPlan: Waiting for commander to return before assaulting");
      return;
   }

   // Destroy old plan if exists
   if (gIslandAssaultPlanID >= 0) {
      aiPlanDestroy(gIslandAssaultPlanID);
      gIslandAssaultPlanID = -1;
   }
   
   // Validate inputs
   if (gatherPoint == cInvalidVector) {
      gatherPoint = gNavalInvasionCoastalPoint;
   }
   if (targetPoint == cInvalidVector) {
      targetPoint = gIslandCenterPoint;
   }
   if (targetPoint == cInvalidVector) {
      anwVerboseEcho("createIslandAssaultPlan: No valid target point!");
      return;
   }
   
   int gatherPointGroupId = kbAreaGroupGetIDByPosition(gatherPoint);
   
   gIslandAssaultPlanID = aiPlanCreate("Island Assault Plan", cPlanCombat);
   
   if (gIslandAssaultPlanID < 0) {
      anwVerboseEcho("Failed to create assault plan!");
      return;
   }
   
   // Find and add units on the island
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int numberInPlan = 0;
   
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      vector unitLocation = kbUnitGetPosition(unitID);
      int unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      
      // Skip heroes
      if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
         continue;
      }
      
      // Check if unit is on the target island
      if (kbAreAreaGroupsPassableByLand(gatherPointGroupId, unitLocationGroupId) == true) {
         // Remove from existing plan first
         int existingPlan = kbUnitGetPlanID(unitID);
         if (existingPlan >= 0 && existingPlan != gIslandAssaultPlanID) {
            aiPlanRemoveUnit(existingPlan, unitID);
         }
         aiPlanAddUnit(gIslandAssaultPlanID, unitID);
         numberInPlan = numberInPlan + 1;
      }
   }
   
   // Set flexible unit requirements
   int minUnits = numberInPlan / 2;
   if (minUnits < 2) {
      minUnits = 2;
   }
   aiPlanAddUnitType(gIslandAssaultPlanID, cUnitTypeLogicalTypeLandMilitary, minUnits, numberInPlan, 200);
   
   // Configure the combat plan
   aiPlanSetVariableInt(gIslandAssaultPlanID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeAttack);
   aiPlanSetVariableInt(gIslandAssaultPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(gIslandAssaultPlanID, cCombatPlanTargetPoint, 0, targetPoint);
   aiPlanSetVariableVector(gIslandAssaultPlanID, cCombatPlanGatherPoint, 0, gatherPoint);
   aiPlanSetVariableFloat(gIslandAssaultPlanID, cCombatPlanGatherDistance, 0, 800.0);
   aiPlanSetVariableInt(gIslandAssaultPlanID, cCombatPlanAttackRoutePattern, 0, cCombatPlanAttackRoutePatternBest);
   aiPlanSetVariableBool(gIslandAssaultPlanID, cCombatPlanAllowMoreUnitsDuringAttack, 0, true);
   aiPlanSetVariableInt(gIslandAssaultPlanID, cCombatPlanRefreshFrequency, 0, 5);
   aiPlanSetVariableInt(gIslandAssaultPlanID, cCombatPlanDoneMode, 0, cCombatPlanDoneModeNoTarget);
   aiPlanSetVariableInt(gIslandAssaultPlanID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetVariableInt(gIslandAssaultPlanID, cCombatPlanNoTargetTimeout, 0, 60000);
   aiPlanSetInitialPosition(gIslandAssaultPlanID, gatherPoint);
   aiPlanSetDesiredPriority(gIslandAssaultPlanID, 100);
   aiPlanSetNoMoreUnits(gIslandAssaultPlanID, false);
   aiPlanSetRequiresAllNeedUnits(gIslandAssaultPlanID, false);  // Don't wait for all units
   aiPlanSetActive(gIslandAssaultPlanID, true);
   
   anwVerboseEcho("Assault plan created with " + numberInPlan + " units, target: " + targetPoint);
}

//==============================================================================
// createIslandSearchPlan - NEW SIMPLIFIED FUNCTION
// Creates a search/explore plan when enemy location is unknown
//==============================================================================
void createIslandSearchPlan(vector gatherPoint = cInvalidVector, vector targetPoint = cInvalidVector)
{
   // Destroy old plan if exists
   if (gIslandSearchPlanID >= 0) {
      aiPlanDestroy(gIslandSearchPlanID);
      gIslandSearchPlanID = -1;
   }
   
   // Validate inputs
   if (gatherPoint == cInvalidVector) {
      gatherPoint = gNavalInvasionCoastalPoint;
   }
   if (targetPoint == cInvalidVector) {
      targetPoint = gIslandCenterPoint;
   }
   if (targetPoint == cInvalidVector) {
      targetPoint = gProbableEnemyIsland;
   }
   if (targetPoint == cInvalidVector) {
      anwVerboseEcho("createIslandSearchPlan: No valid target point!");
      return;
   }
   
   int targetLocationGroupId = kbAreaGroupGetIDByPosition(targetPoint);
   int gatherPointGroupId = kbAreaGroupGetIDByPosition(gatherPoint);
   
   // Use combat plan so units will attack enemies they find
   gIslandSearchPlanID = aiPlanCreate("Island Search Plan", cPlanCombat);
   
   if (gIslandSearchPlanID < 0) {
      anwVerboseEcho("Failed to create search plan!");
      return;
   }
   
   // Find and add units on the island
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int numberInPlan = 0;
   
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      vector unitLocation = kbUnitGetPosition(unitID);
      int unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      
      // Skip heroes
      if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
         continue;
      }
      
      // Check if unit is on the target island
      if (kbAreAreaGroupsPassableByLand(targetLocationGroupId, unitLocationGroupId) == true) {
         // Remove from existing plan first
         int existingPlan = kbUnitGetPlanID(unitID);
         if (existingPlan >= 0 && existingPlan != gIslandSearchPlanID) {
            aiPlanRemoveUnit(existingPlan, unitID);
         }
         aiPlanAddUnit(gIslandSearchPlanID, unitID);
         numberInPlan = numberInPlan + 1;
      }
   }

   // Set flexible unit requirements
   int minUnits = numberInPlan / 2;
   if (minUnits < 2) {
      minUnits = 2;
   }
   aiPlanAddUnitType(gIslandSearchPlanID, cUnitTypeLogicalTypeLandMilitary, minUnits, numberInPlan, 200);
   
   // Configure as roaming attack - will engage any enemies found
   aiPlanSetVariableInt(gIslandSearchPlanID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeAttack);
   aiPlanSetVariableInt(gIslandSearchPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(gIslandSearchPlanID, cCombatPlanTargetPoint, 0, targetPoint);
   aiPlanSetVariableVector(gIslandSearchPlanID, cCombatPlanGatherPoint, 0, gatherPoint);
   aiPlanSetVariableFloat(gIslandSearchPlanID, cCombatPlanGatherDistance, 0, 800.0);
   aiPlanSetVariableInt(gIslandSearchPlanID, cCombatPlanAttackRoutePattern, 0, cCombatPlanAttackRoutePatternRandom);
   aiPlanSetVariableBool(gIslandSearchPlanID, cCombatPlanAllowMoreUnitsDuringAttack, 0, true);
   aiPlanSetVariableInt(gIslandSearchPlanID, cCombatPlanRefreshFrequency, 0, 5);
   aiPlanSetVariableInt(gIslandSearchPlanID, cCombatPlanDoneMode, 0, cCombatPlanDoneModeNoTarget);
   aiPlanSetVariableInt(gIslandSearchPlanID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetVariableInt(gIslandSearchPlanID, cCombatPlanNoTargetTimeout, 0, 180000);  // 3 minute timeout for searching
   aiPlanSetInitialPosition(gIslandSearchPlanID, gatherPoint);
   aiPlanSetDesiredPriority(gIslandSearchPlanID, 100);
   aiPlanSetNoMoreUnits(gIslandSearchPlanID, false);
   aiPlanSetRequiresAllNeedUnits(gIslandSearchPlanID, false);
   aiPlanSetActive(gIslandSearchPlanID, true);
   
   anwVerboseEcho("Search plan created with " + numberInPlan + " units, targeting island center");
}
//==============================================================================
// getStrandedUnitsLocation
// Returns the average position of our military units stranded on the enemy island
// Returns cInvalidVector if no units found
//==============================================================================
vector getStrandedUnitsLocation()
{
   if (gIslandCenterPoint == cInvalidVector && gProbableEnemyIsland == cInvalidVector) {
      return (cInvalidVector);
   }
   
   int islandGroupId = kbAreaGroupGetIDByPosition(gIslandCenterPoint);
   if (islandGroupId < 0) {
      islandGroupId = kbAreaGroupGetIDByPosition(gProbableEnemyIsland);
   }
   if (islandGroupId < 0) {
      return (cInvalidVector);
   }
   
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   
   float totalX = 0.0;
   float totalZ = 0.0;
   int unitsOnIsland = 0;
   
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      
      // Skip heroes
      if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
         continue;
      }
      
      vector unitLocation = kbUnitGetPosition(unitID);
      int unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      
      // Check if unit is on the target island
      if (kbAreAreaGroupsPassableByLand(islandGroupId, unitLocationGroupId) == true) {
         totalX = totalX + xsVectorGetX(unitLocation);
         totalZ = totalZ + xsVectorGetZ(unitLocation);
         unitsOnIsland++;
      }
   }
   
   if (unitsOnIsland < 1) {
      return (cInvalidVector);
   }
   
   // Calculate average position
   float avgX = totalX / unitsOnIsland;
   float avgZ = totalZ / unitsOnIsland;
   
   return (xsVectorSet(avgX, 0.0, avgZ));
}

//==============================================================================
// checkAndRecreateStrandedUnitPlans
// Checks if assault/search plans died but units are still on island
// If so, recreates the appropriate plan with gather point at stranded units
//==============================================================================
void checkAndRecreateStrandedUnitPlans(int currentMode = -1, bool hasTarget = false)
{
   // Count units on island
   int islandGroupId = kbAreaGroupGetIDByPosition(gIslandCenterPoint);
   if (islandGroupId < 0) {
      islandGroupId = kbAreaGroupGetIDByPosition(gProbableEnemyIsland);
   }
   if (islandGroupId < 0) {
      return;
   }
   
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int numberOnIsland = 0;
   
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
         continue;
      }
      vector unitLocation = kbUnitGetPosition(unitID);
      int unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      if (kbAreAreaGroupsPassableByLand(islandGroupId, unitLocationGroupId) == true) {
         numberOnIsland++;
      }
   }
   
   // No units on island, nothing to do
   if (numberOnIsland < 2) {
      return;
   }
   
   // Check if we need to recreate plans
   bool assaultPlanDead = (gIslandAssaultPlanID < 0) || (aiPlanGetActive(gIslandAssaultPlanID) == false);
   bool searchPlanDead = (gIslandSearchPlanID < 0) || (aiPlanGetActive(gIslandSearchPlanID) == false);
   
   // If plans are dead and we have units, recreate
   if ((assaultPlanDead == true && currentMode == 1) || (searchPlanDead == true && currentMode == 2)) {
      vector strandedLocation = getStrandedUnitsLocation();
      
      if (strandedLocation == cInvalidVector) {
         strandedLocation = gNavalInvasionCoastalPoint;
      }
      
      anwVerboseEcho("Plans died but " + numberOnIsland + " units still on island, recreating at " + strandedLocation);
      
      // Determine which plan to create based on mode and target
      if (hasTarget == true || currentMode == 1) {
         // Assault mode - find enemy target
         int enemyBuildingId = getClosestIslandUnitByLocation(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, 
            cUnitStateABQ, strandedLocation, 5000);
         
         if (enemyBuildingId > 0) {
            vector enemyLocation = kbUnitGetPosition(enemyBuildingId);
            anwVerboseEcho("Recreating assault plan targeting enemy at " + enemyLocation);
            createIslandAssaultPlan(strandedLocation, enemyLocation);
         } else {
            // No enemy found, create search plan instead
            anwVerboseEcho("No enemy found, recreating search plan");
            createIslandSearchPlan(strandedLocation, gIslandCenterPoint);
         }
      } else {
         // Search mode
         anwVerboseEcho("Recreating search plan");
         createIslandSearchPlan(strandedLocation, gIslandCenterPoint);
      }
   }
}
//==============================================================================
// addUnitsToInvasionPlan
// Now properly removes units from old plans and handles idle units
//==============================================================================
void addUnitsToInvasionPlan(int planId = -1) {
   if (planId < 0 || aiPlanGetActive(planId) == false) {
      return;
   }
   
   int unitID = -1;
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;
   int islandGroupId = kbAreaGroupGetIDByPosition(gIslandCenterPoint);
   int unitsAdded = 0;
   
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   
   for (i = 0; < numberFound)
   {
      unitID = kbUnitQueryGetResult(unitQueryID, i);
      unitLocation = kbUnitGetPosition(unitID);
      unitLocationId = kbAreaGetIDByPosition(unitLocation);
      unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      
      // Skip heroes
      if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
         continue;
      }
      
      // Check if unit is on the target island
      if (kbAreAreaGroupsPassableByLand(islandGroupId, unitLocationGroupId) == false) {
         continue;
      }
      
      // Check if already in this plan
      int currentPlan = kbUnitGetPlanID(unitID);
      if (currentPlan == planId) {
         continue;
      }
      
      // Check if unit is idle or in a lower priority plan
      bool shouldAdd = false;
      if (currentPlan < 0) {
         shouldAdd = true;  // No plan, definitely add
      } else if (aiPlanGetActive(currentPlan) == false) {
         shouldAdd = true;  // Plan inactive
      } else if (aiPlanGetDesiredPriority(currentPlan) < aiPlanGetDesiredPriority(planId)) {
         shouldAdd = true;  // Lower priority plan
      } else if (aiPlanGetType(currentPlan) == cPlanDefend && aiPlanGetDesiredPriority(currentPlan) < 60) {
         shouldAdd = true;  // Low priority defend plan
      }
      
      if (shouldAdd) {
         // Remove from current plan first
         if (currentPlan >= 0) {
            aiPlanRemoveUnit(currentPlan, unitID);
         }
         aiPlanAddUnit(planId, unitID);
         unitsAdded++;
      }
   }
   
   if (unitsAdded > 0) {
      // Update the plan's unit type counts
      int currentInPlan = aiPlanGetNumberUnits(planId, cUnitTypeLogicalTypeLandMilitary);
      aiPlanAddUnitType(planId, cUnitTypeLogicalTypeLandMilitary, currentInPlan / 2, currentInPlan, 200);
      anwVerboseEcho("Added " + unitsAdded + " units to invasion plan, total: " + currentInPlan);
   }
}

//==============================================================================
// warshipTraining
// Trains units from War Ships that are capable of doing so during active island invasions.
//==============================================================================
void warshipTraining()
{
   int trainingShipQuery = kbUnitQueryCreate("Training Ship Query");
   kbUnitQuerySetPlayerRelation(trainingShipQuery, cPlayerRelationSelf);
   kbUnitQuerySetUnitType(trainingShipQuery, gGalleonUnit);
   int numberOfTrainingShips = kbUnitQueryExecute(trainingShipQuery);
   int limit = kbGetBuildLimit(cMyID, cUnitTypeLogicalTypeLandMilitary);
   int unitID = -1;
   int unitPlanID = -1;
   vector galleonPosition = cInvalidVector;
   vector coastalTargetPoint = cInvalidVector;
   
   // Don't run if no galleons
   if (numberOfTrainingShips <= 0) {
      return;
   }

   // Create maintain plans if not already active
   if (gGalleonTrainingPlan < 0)
   {
      for (i = 0; < gNumArmyUnitTypes)
      {
         int pickedUnit = kbUnitPickGetResult(gLandUnitPicker, i);
         if (kbProtoUnitIsType(pickedUnit, cUnitTypeAbstractArtillery) == false && gGalleonLandUnit == -1)
            gGalleonLandUnit = pickedUnit;
         else if (gGalleonArtilleryUnit == -1)
            gGalleonArtilleryUnit = pickedUnit;
      }
      
      // Validate we have units to train
      if (gGalleonLandUnit == -1) {
         anwVerboseEcho("warshipTraining: No land unit found to train");
         return;
      }
      
      gGalleonTrainingPlan = createSimpleMaintainPlan(gGalleonLandUnit, limit, false, -1, 5);
      aiPlanSetDesiredResourcePriority(gGalleonTrainingPlan, 100);
      aiPlanSetDesiredPriority(gGalleonTrainingPlan, 99);
      aiPlanSetVariableInt(gGalleonTrainingPlan, cTrainPlanBuildFromType, 0, gGalleonUnit);
      aiPlanSetVariableInt(gGalleonTrainingPlan, cTrainPlanBatchSize, 0, 5);
      aiPlanSetVariableVector(gGalleonTrainingPlan, cTrainPlanGatherPoint, 0, gNavalInvasionCoastalPoint);
      
      if (gGalleonArtilleryUnit != -1) {
         gGalleonArtilleryTrainingPlan = createSimpleMaintainPlan(gGalleonArtilleryUnit, limit, false, -1, 5);
         aiPlanSetDesiredResourcePriority(gGalleonArtilleryTrainingPlan, 99);
         aiPlanSetDesiredPriority(gGalleonArtilleryTrainingPlan, 98);
         aiPlanSetVariableInt(gGalleonArtilleryTrainingPlan, cTrainPlanBuildFromType, 0, gGalleonUnit);
         aiPlanSetVariableInt(gGalleonArtilleryTrainingPlan, cTrainPlanBatchSize, 0, 5);
         aiPlanSetVariableVector(gGalleonArtilleryTrainingPlan, cTrainPlanGatherPoint, 0, gNavalInvasionCoastalPoint);
      }
      
      anwVerboseEcho("Galleon Maintain Plans Created!");
   }
   
   // Active invasion sequence - manually control ships
   if (gMilitaryTransportMode > 0 && gMilitaryTransportMode < 3)
   {
      for (i = 0; < numberOfTrainingShips)
      {
         unitID = kbUnitQueryGetResult(trainingShipQuery, i);
         
         // Skip ships in transport plans - don't interfere with invasion
         unitPlanID = kbUnitGetPlanID(unitID);
         if (unitPlanID >= 0 && aiPlanGetType(unitPlanID) == cPlanTransport) {
            continue;
         }
         
         // Don't remove from high-priority combat plans
         if (unitPlanID >= 0 && aiPlanGetDesiredPriority(unitPlanID) >= 80) {
            continue;
         }
         
         // Remove from other plans so our commands work
         if (unitPlanID >= 0) {
            aiPlanRemoveUnit(unitPlanID, unitID);
         }
         
         galleonPosition = kbUnitGetPosition(unitID);
         
         // Better coastal point calculation
         // Find a water point near the enemy coast
         vector landCoast = gNavalInvasionCoastalPoint;
         if (landCoast == cInvalidVector) {
            landCoast = coastalEdgeVector(galleonPosition, gProbableEnemyIsland);
         }
         
         // Calculate direction from coast back toward water (toward our base)
         vector myBase = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
         vector directionToWater = xsVectorNormalize(myBase - landCoast);
         // Stay 20 meters off the coast (in water) - increased from 15
         coastalTargetPoint = landCoast + (directionToWater * 20.0);
         
         // Verify the target point is actually in water
         if (kbAreaGetType(kbAreaGetIDByPosition(coastalTargetPoint)) != cAreaTypeWater) {
            // Try the opposite direction or adjust
            coastalTargetPoint = landCoast + (directionToWater * 30.0);
         }
         
         float distToCoast = distance(galleonPosition, coastalTargetPoint);
         
         // If far from coast, move first
         if (distToCoast > 40.0)
         {
            aiTaskUnitMove(unitID, coastalTargetPoint);
            continue;
         }
         
         // Check for units that need to be ejected (units inside the ship)
         // Use a smaller radius to only detect units actually onboard
         int unitsOnboard = getUnitCountByLocation(cUnitTypeLogicalTypeLandMilitary, cPlayerRelationSelf,
               cUnitStateAlive, galleonPosition, 3.0);
         
         if (unitsOnboard > 0)
         {
            anwVerboseEcho("Galleon " + unitID + " ejecting " + unitsOnboard + " units");
            aiTaskUnitEject(unitID);
            
            // After ejecting, assign ejected units to assault plan
            // Give a small delay for units to actually eject
            continue;
         }
         
         // If idle and at coast, train units
         int actionType = kbUnitGetActionType(unitID);
         if (actionType == cActionTypeIdle)
         {
            bool trainArtillery = ((i % 2) == 1) && (gGalleonArtilleryUnit != -1);
            int unitToTrain = trainArtillery ? gGalleonArtilleryUnit : gGalleonLandUnit;
            anwVerboseEcho("Galleon " + unitID + " training: " + kbGetUnitTypeName(unitToTrain));
            aiTaskUnitTrain(unitID, unitToTrain);
         }
      }
      
      // Assign newly spawned/ejected units near the coast to the assault plan
      assignCoastalUnitsToAssault();
   }
}

//==============================================================================
// homeIslandUnderAttack - Send troops home if we are under attack...
//==============================================================================
bool homeIslandUnderAttack() {
   vector startingLoc = kbGetPlayerStartingPosition(cMyID);
   int enemyUnitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cPlayerRelationEnemyNotGaia, cUnitStateAlive, startingLoc, 125);
   int enemyNumberFound = kbUnitQueryExecute(enemyUnitQueryID);
   if (enemyNumberFound > 15) {
      //anwVerboseEcho("Clear a path, I'm going home!");
      return true;
   }

   return false;
}
//==============================================================================
// resetInvasionSequence - Necessarily resets the invasion sequence...
//==============================================================================
void resetInvasionSequence() {
   anwVerboseEcho("Could not do something that was necessary, resetting!");
   aiPlanDestroy(gIslandAssaultTransportPlanID);
   aiPlanDestroy(gIslandAssaultTransportPlan2ID);
   aiPlanDestroy(gIslandAssaultPlanID);
   aiPlanDestroy(gIslandSearchPlanID);
   aiPlanDestroy(gIslandReturnTransportPlanID);
   aiPlanDestroy(gGalleonTrainingPlan);
   aiPlanDestroy(gGalleonArtilleryTrainingPlan);
   gActiveIslandInvasion = false;
   gActiveVillagersTransport = false;
   gProbableEnemyIsland = cInvalidVector;
   gNavalInvasionCoastalPoint = cInvalidVector;
   gProbableEnemyIslandAreaId = -1;
   gProbableEnemyIslandGroupId = -1;
   gNumberTransported = 0;
   gIslandCenterPoint = cInvalidVector;
   gProbableEnemyIslandX = 0.0;
   gProbableEnemyIslandZ = 0.0;
   gDistanceToCoast = 0.0;
   gInvasionPlan = "";
   gMilitaryTransportMode = 0;
   gIslandFound = false;
   gIslandAssaultTransportPlanID = -1;
   gIslandAssaultTransportPlan2ID = -1;
   gIslandAssaultPlanID = -1;
   gAssaultExploreDone = false;
   gAssaultingIsland = false;
   gIslandSearchPlanID = -1;
   gIslandReturnTransportPlanID = -1;
   gGalleonTrainingPlan = -1;
   gGalleonArtilleryTrainingPlan = -1;
   return;
}