//==============================================================================
/* getRandomLandPoint
   Finds a random location on the map that is land.
*/
//==============================================================================
vector getRandomLandPoint()
{
   vector startingLoc = kbGetPlayerStartingPosition(cMyID);
   int startingAreaID = kbAreaGetIDByPosition(startingLoc);
   int startingAreaGroupID = kbAreaGroupGetIDByPosition(startingLoc);
   vector landLoc = cInvalidVector;
   vector landAreaCentralPoint = cInvalidVector;
   int landAreaID = -1;
   int landAreaGroupID = -1;
   float xFloat = 0.0;
   float zFloat = 0.0;
   float mapWidth = kbGetMapXSize();
   float mapHeight = kbGetMapZSize();

   for (i = 0; < 90)
   {
      // Get a random vector on the map...
      xFloat = aiRandFloat(150.0, kbGetMapXSize());
      zFloat = aiRandFloat(150.0, kbGetMapZSize());
      landLoc = xsVectorSet(xFloat, 0.0, zFloat);
      
      landAreaID = kbAreaGetIDByPosition(landLoc);
      landAreaGroupID = kbAreaGroupGetIDByPosition(landLoc);
      landAreaCentralPoint = kbAreaGroupGetCenter(landAreaGroupID);

      if ((kbAreaGroupGetType(landAreaGroupID) != cAreaGroupTypeWater) &&
            distance(startingLoc, landAreaCentralPoint) > 120.0)
      {
         //sendStatement(1, cAICommPromptToAllyConfirm, landLoc);
         return landLoc;
      }
   }
   return cInvalidVector;
}
//==============================================================================
// createSimpleRadialUnitQuery
// Finds units within a certain radius of another unit.
// This method was created to overcome the fact that aiPlanAddUnit() does not work properly.
//==============================================================================
int createSimpleRadialUnitQuery(int unitTypeID = -1, int playerRelationOrID = cMyID, int state = cUnitStateAlive,
                          int unitID = -1, float radius = 1.0)
{
   static int unitQueryID = -1;

   // If we don't have the query yet, create one.
   if (unitQueryID < 0)
   {
      unitQueryID = kbUnitQueryCreate("miscSimpleUnitQuery");
   }

   // Define a query to get all matching units
   if (unitQueryID != -1)
   {
      if (playerRelationOrID > 1000) // Too big for player ID number
      {
         kbUnitQuerySetPlayerID(unitQueryID, -1); // Clear the player ID, so playerRelation takes precedence.
         kbUnitQuerySetPlayerRelation(unitQueryID, playerRelationOrID);
      }
      else
      {
         kbUnitQuerySetPlayerRelation(unitQueryID, -1);
         kbUnitQuerySetPlayerID(unitQueryID, playerRelationOrID);
      }
      kbUnitQuerySetUnitType(unitQueryID, unitTypeID);
      kbUnitQuerySetState(unitQueryID, state);
      
      // If a unitID is provided, set the position to the unit's position
      if (unitID != -1) {
         vector unitPos = kbUnitGetPosition(unitID);
         kbUnitQuerySetPosition(unitQueryID, unitPos);
      }
      
      kbUnitQuerySetMaximumDistance(unitQueryID, radius);
      kbUnitQuerySetIgnoreKnockedOutUnits(unitQueryID, true);
   }
   else
   {
      return (-1);
   }

   kbUnitQueryResetResults(unitQueryID);
   return (unitQueryID);
}
//==============================================================================
// findPassableLandUnits
// Finds units within a certain radius of another unit on the same island.
//==============================================================================
int findPassableLandUnits(int unitTypeID = -1, int playerRelationOrID = cMyID, int state = cUnitStateAlive,
                          int unitID = -1, float radius = 1.0, int enemyAreaGroupID = -1)
{
   static int unitQueryID = -1;

   // If we don't have the query yet, create one.
   if (unitQueryID < 0)
   {
      unitQueryID = kbUnitQueryCreate("miscSimpleUnitQuery");
   }

   // Define a query to get all matching units
   if (unitQueryID != -1)
   {
      if (playerRelationOrID > 1000) // Too big for player ID number
      {
         kbUnitQuerySetPlayerID(unitQueryID, -1); // Clear the player ID, so playerRelation takes precedence.
         kbUnitQuerySetPlayerRelation(unitQueryID, playerRelationOrID);
      }
      else
      {
         kbUnitQuerySetPlayerRelation(unitQueryID, -1);
         kbUnitQuerySetPlayerID(unitQueryID, playerRelationOrID);
      }
      kbUnitQuerySetUnitType(unitQueryID, unitTypeID);
      kbUnitQuerySetState(unitQueryID, state);
      
      // If a unitID is provided, set the position to the unit's position
      if (unitID != -1) {
         vector unitPos = kbUnitGetPosition(unitID);
         kbUnitQuerySetPosition(unitQueryID, unitPos);
      }
      
      kbUnitQuerySetMaximumDistance(unitQueryID, radius);
      kbUnitQuerySetIgnoreKnockedOutUnits(unitQueryID, true);
   }
   else
   {
      return (-1);
   }

   kbUnitQueryResetResults(unitQueryID);

   // Loop through the found units
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int numberOnIsland = 0;
   for (int i = 0; i < numberFound; i++) {
      // Get the ID of the unit
      int unitQueryResultID = kbUnitQueryGetResult(unitQueryID, i);

      // Get the area group ID of the unit's position
      int unitAreaGroupID = kbAreaGroupGetIDByPosition(kbUnitGetPosition(unitQueryResultID));

      // Check if the unit's area group is passable by land to the enemy area group
      if (kbAreAreaGroupsPassableByLand(unitAreaGroupID, enemyAreaGroupID) == false) {
         // This unit is not in an area group passable by land to the enemy area group
         // Remove it from the query results
         //kbUnitQueryRemoveResult(unitQueryID, i);
         //i--; // Decrement the counter since we removed an element
         //numberFound--; // Decrement the total number of found units
      } else {
         numberOnIsland = numberOnIsland + 1;
      }
   }

   return numberOnIsland;
}
//==============================================================================
// getClosestIslandUnitByLocation
// Will return a random island unit matching the parameters.
//==============================================================================
int getClosestIslandUnitByLocation(int unitTypeID = -1, int playerRelationOrID = cMyID, int state = cUnitStateAlive,
                             vector location = cInvalidVector, float radius = 800.0)
{
   int unitQueryID = kbUnitQueryCreate("miscGetColonizationUnitLocationQuery");
   int unitID = -1;
   vector unitLocation = cInvalidVector;
   int unitLocationId = -1;
   int unitLocationGroupId = -1;
   int currentLocationId = kbAreaGetIDByPosition(location);
   int currentLocationGroupId = kbAreaGroupGetIDByPosition(location);

   // Define a query to get all matching units
   if (unitQueryID != -1)
   {
      if (playerRelationOrID > 1000) // Too big for player ID number
      {
         kbUnitQuerySetPlayerID(unitQueryID, -1);
         kbUnitQuerySetPlayerRelation(unitQueryID, playerRelationOrID);
      }
      else
      {
         kbUnitQuerySetPlayerRelation(unitQueryID, -1);
         kbUnitQuerySetPlayerID(unitQueryID, playerRelationOrID);
      }
      kbUnitQuerySetUnitType(unitQueryID, unitTypeID);
      kbUnitQuerySetState(unitQueryID, state);
      kbUnitQuerySetPosition(unitQueryID, location);
      kbUnitQuerySetMaximumDistance(unitQueryID, radius);
      kbUnitQuerySetIgnoreKnockedOutUnits(unitQueryID, true);
      kbUnitQuerySetAscendingSort(unitQueryID, true);
   }
   else
   {
      return (-1);
   }

   int numberFound = kbUnitQueryExecute(unitQueryID);
   for (i = 0; < numberFound)
   {
      unitID = kbUnitQueryGetResult(unitQueryID, i);
      unitLocation = kbUnitGetPosition(unitID);
      unitLocationId = kbAreaGetIDByPosition(unitLocation);
      unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      if (kbAreAreaGroupsPassableByLand(currentLocationGroupId, unitLocationGroupId) == true) {
         return (kbUnitQueryGetResult(unitQueryID, i));
      }
   }
   return (-1);
}
//==============================================================================
// getUnitCountByAreaGroups
// Returns the number of matching units in the point/radius specified within an area group.
//==============================================================================
int getUnitCountByAreaGroups(int unitTypeID = -1, int playerRelationOrID = cMyID, int state = cUnitStateAlive,
                           vector location = cInvalidVector, float radius = 20.0)
{
   int unitQueryID = kbUnitQueryCreate("miscGetUnitLocationQuery");

   // Define a query to get all matching units
   if (unitQueryID != -1)
   {
      if (playerRelationOrID > 1000) // Too big for player ID number
      {
         kbUnitQuerySetPlayerID(unitQueryID, -1);
         kbUnitQuerySetPlayerRelation(unitQueryID, playerRelationOrID);
      }
      else
      {
         kbUnitQuerySetPlayerRelation(unitQueryID, -1);
         kbUnitQuerySetPlayerID(unitQueryID, playerRelationOrID);
      }
      kbUnitQuerySetUnitType(unitQueryID, unitTypeID);
      kbUnitQuerySetState(unitQueryID, state);
      kbUnitQuerySetPosition(unitQueryID, location);
      kbUnitQuerySetAreaGroupID(unitQueryID, kbAreaGroupGetIDByPosition(location));
      kbUnitQuerySetMaximumDistance(unitQueryID, radius);
      kbUnitQuerySetIgnoreKnockedOutUnits(unitQueryID, true);
   }
   else
   {
      return (-1);
   }

   kbUnitQueryResetResults(unitQueryID);
   return (kbUnitQueryExecute(unitQueryID));
}
//==============================================================================
// getNavalTargetPlayerId
// Returns an enemy's Id by searching for enemy naval units.
//==============================================================================
int getNavalTargetPlayerId()
{
   int count = 0;
   int enemyPlayerId = -1;
   static int unitQueryID = -1;

   // Create a new query if it does not exist.
   if (unitQueryID < 0)
   {
      unitQueryID = kbUnitQueryCreate("Naval Target Query");
      kbUnitQuerySetIgnoreKnockedOutUnits(unitQueryID, true);
      kbUnitQuerySetPlayerRelation(unitQueryID, cPlayerRelationEnemyNotGaia);
      kbUnitQuerySetSeeableOnly(unitQueryID, false);
      kbUnitQuerySetMaximumDistance(unitQueryID, kbGetMapXSize() + kbGetMapZSize());
      kbUnitQuerySetIgnoreKnockedOutUnits(unitQueryID, true);
   }
   
   kbUnitQuerySetUnitType(unitQueryID, gFishingUnit);
   kbUnitQuerySetState(unitQueryID, cUnitStateABQ);
   kbUnitQueryResetResults(unitQueryID);
	count = kbUnitQueryExecute(unitQueryID);
   //anwVerboseEcho("Enemy fishing boats: "+ count);
   
   kbUnitQuerySetUnitType(unitQueryID, cUnitTypeAbstractWarShip);
   kbUnitQuerySetState(unitQueryID, cUnitStateABQ);
	count = kbUnitQueryExecute(unitQueryID); // This value is cumulative.
   //anwVerboseEcho("Enemy fishing boats and warships: "+ count);
   
   kbUnitQuerySetUnitType(unitQueryID, gDockUnit);
   kbUnitQuerySetState(unitQueryID, cUnitStateABQ);
	count = kbUnitQueryExecute(unitQueryID); // This value is cumulative.
   //anwVerboseEcho("Enemy fishing boats, warships and docks: "+ count);
   
   if (count > 0) {
      enemyPlayerId = kbUnitGetPlayerID(kbUnitQueryGetResult(unitQueryID, 0));
   } 
   anwVerboseEcho("Enemy Unit Owner: "+enemyPlayerId+" Unit Count: "+count+"");
   
   return(enemyPlayerId);
}
//==============================================================================
// createIdleUnitQuery
//==============================================================================
int createIdleUnitQuery(int unitTypeID = -1, int playerRelationOrID = cMyID, int state = cUnitStateAlive,
                          vector position = cInvalidVector, float radius = -1.0)
{
   static int unitQueryID = -1;

   // If we don't have the query yet, create one.
   if (unitQueryID < 0)
   {
      unitQueryID = kbUnitQueryCreate("miscSimpleUnitQuery");
   }

   // Define a query to get all matching units
   if (unitQueryID != -1)
   {
      if (playerRelationOrID > 1000) // Too big for player ID number
      {
         kbUnitQuerySetPlayerID(unitQueryID, -1); // Clear the player ID, so playerRelation takes precedence.
         kbUnitQuerySetPlayerRelation(unitQueryID, playerRelationOrID);
      }
      else
      {
         kbUnitQuerySetPlayerRelation(unitQueryID, -1);
         kbUnitQuerySetPlayerID(unitQueryID, playerRelationOrID);
      }
      kbUnitQuerySetUnitType(unitQueryID, unitTypeID);
      kbUnitQuerySetState(unitQueryID, state);
      kbUnitQuerySetActionType(unitQueryID, cActionTypeIdle);
      kbUnitQuerySetPosition(unitQueryID, position);
      kbUnitQuerySetMaximumDistance(unitQueryID, radius);
      kbUnitQuerySetIgnoreKnockedOutUnits(unitQueryID, true);
   }
   else
   {
      return (-1);
   }

   kbUnitQueryResetResults(unitQueryID);
   return (unitQueryID);
}
//==============================================================================
// createGatherPlan
//==============================================================================
int createGatherPlan(vector mainVec = cInvalidVector, int baseId = -1, int resourceType = -1, int pri = 95)
{
   int gatherPlanId = aiPlanCreate("Main Base Crate", cPlanGather);
   int availableUnits = kbBaseGetNumberUnits(cMyID, baseId, cPlayerRelationSelf, gEconUnit);
   aiPlanSetBaseID(gatherPlanId, kbBaseGetMainID(cMyID));
   //aiPlanSetVariableInt(gatherPlanId, cGatherPlanResourceUnitTypeFilter, 0, resourceType);
   aiPlanSetVariableInt(gatherPlanId, cGatherPlanResourceType, 0, resourceType);
   // aiPlanSetVariableInt(cratePlanID, cGatherPlanFindNewResourceTimeOut, 0, 20000);
   aiPlanAddUnitType(gatherPlanId, gEconUnit, 1, availableUnits, availableUnits);
   aiPlanSetDesiredPriority(gatherPlanId, pri);
   aiPlanSetActive(gatherPlanId);
   debugEconomy("Activated base gather plan " + gatherPlanId);

   return gatherPlanId;
}
// Create a second base at a given position without overriding the main base
int createSecondaryBase(vector pos = cInvalidVector)
{
    // Create the base (radius 50.0 is typical for a TC footprint + buffer)
    int baseID = kbBaseCreate(cMyID, "SecondaryBase" + kbBaseGetNextID(), pos, 50.0);
    if (baseID < 0)
        return (-1);

    // Mark it as a settlement so the AI treats it like a town
    kbBaseSetSettlement(cMyID, baseID, true);

    // Enable both economy and military logic for this base
    kbBaseSetEconomy(cMyID, baseID, true);
    kbBaseSetMilitary(cMyID, baseID, true);

    // Give it a reasonable resource search radius
    kbBaseSetMaximumResourceDistance(cMyID, baseID, 750.0);

    // Set a military rally point (here: 30m forward toward map center)
    vector frontVec = xsVectorNormalize(kbGetMapCenter() - pos);
    kbBaseSetMilitaryGatherPoint(cMyID, baseID, pos + (frontVec * 30.0));

    // Anchor the TC if one exists nearby (Alive preferred, fallback to ABQ)
    int tcQuery = createSimpleUnitQuery(cUnitTypeTownCenter, cMyID, cUnitStateAlive, pos, 70.0);
    int tcCount = kbUnitQueryExecute(tcQuery);
    if (tcCount <= 0)
    {
        tcQuery = createSimpleUnitQuery(cUnitTypeTownCenter, cMyID, cUnitStateABQ, pos, 70.0);
        tcCount = kbUnitQueryExecute(tcQuery);
    }
    if (tcCount > 0)
    {
        int tcID = kbUnitQueryGetResult(tcQuery, 0);
        kbBaseAddUnit(cMyID, baseID, tcID);
    }

    // Activate last — so it starts “live” with all settings in place
    kbBaseSetActive(cMyID, baseID, true);

    return (baseID);
}
// Helper: check if a building type already exists or is queued in the base
bool buildingExistsOrQueued(int baseId = -1, int unitType = -1)
{
    if (baseId < 0 || unitType < 0)
        return(false);

    // Check completed buildings in base
    if (kbBaseGetNumberUnits(cMyID, baseId, unitType) > 0)
        return(true);

    // Check active build plans in base
    int planCount = aiPlanGetNumber(cPlanBuild, cMyID);
    for (int i = 0; i < planCount; i++)
    {
        int planId = aiPlanGetIDByIndex(cPlanBuild, i);
        if (aiPlanGetVariableInt(planId, cBuildPlanBuildingTypeID, 0) == unitType &&
            aiPlanGetBaseID(planId) == baseId)
        {
            return(true);
        }
    }

    return(false);
}
//==============================================================================
// createSettlementBase
//==============================================================================
int createSettlementBase(vector mainVec = cInvalidVector, bool overrideMain = true)
{
   debugBuildings("Creating settlement base at: " + mainVec);
   if (mainVec == cInvalidVector)
   {
      return (-1);
   }

   int oldMainID = kbBaseGetMainID(cMyID);

   // Also destroy bases nearby that can overlap with our radius.
   for (i = 0; < kbBaseGetNumber(cMyID))
   {
      int baseID = kbBaseGetIDByIndex(cMyID, i);

      // Skip the old main and any base already flagged as settlement.
      if ((baseID == oldMainID) || (kbBaseGetSettlement(cMyID, baseID) == true))
         continue;

      if (distance(kbBaseGetLocation(cMyID, baseID), mainVec) < kbBaseGetDistance(cMyID, baseID))
         kbBaseDestroy(cMyID, baseID);
   }

   //kbBaseFindCreateResourceBase(-1, -1, oldMainID);
   int newBaseID = kbBaseCreate(cMyID, "Base" + kbBaseGetNextID(), mainVec, 50.0);
   debugBuildings("New settlement base ID is: " + newBaseID);
   if (newBaseID > -1)
   {
      // Figure out the front vector.
      vector baseFront = xsVectorNormalize(kbGetMapCenter() - mainVec);
      kbBaseSetFrontVector(cMyID, newBaseID, baseFront);
      debugBuildings("Setting front vector to: " + baseFront);
      // Military gather point.
      float milDist = 40.0;
      int mainAreaGroupID = kbAreaGroupGetIDByPosition(mainVec);
      while (kbAreaGroupGetIDByPosition(mainVec + (baseFront * milDist)) != mainAreaGroupID)
      {
         milDist = milDist - 5.0;
         if (milDist < 6.0)
         {
            break;
      }
      }
      vector militaryGatherPoint = mainVec + (baseFront * milDist);

      kbBaseSetMilitaryGatherPoint(cMyID, newBaseID, militaryGatherPoint);
      // Set the other flags.
      kbBaseSetMilitary(cMyID, newBaseID, true);
      kbBaseSetEconomy(cMyID, newBaseID, true);

      // Set the resource percentage for this new base.
      int numberOfBases = kbBaseGetNumber(cMyID);
      float newBasePercentage = (1.0 / numberOfBases) * 100.0;
      for (i = 0; < numberOfBases)
      {
         int currentBaseId = kbBaseGetIDByIndex(cMyID, i);

         // Set resource breakdowns amongst all existing bases.
         aiSetResourceBreakdown(cResourceFood, cAIResourceSubTypeEasy, gGatherPlanNumBerryPlans, 
         gGatherPlanPriorityBerry, newBasePercentage, currentBaseId);
         aiSetResourceBreakdown(cResourceFood, cAIResourceSubTypeHunt, gGatherPlanNumHuntPlans, 
         gGatherPlanPriorityHunt, newBasePercentage, currentBaseId);
         aiSetResourceBreakdown(cResourceFood, cAIResourceSubTypeHerdable, gGatherPlanNumMillPlans, 
         gGatherPlanPriorityMill, newBasePercentage, currentBaseId);
         aiSetResourceBreakdown(cResourceFood, cAIResourceSubTypeFish, gGatherPlanNumFishPlans, 
         gGatherPlanPriorityFish, newBasePercentage, currentBaseId);
         aiSetResourceBreakdown(cResourceFood, cAIResourceSubTypeFarm, gGatherPlanNumEstatePlans, 
         gGatherPlanPriorityEstate, newBasePercentage, currentBaseId);
         aiSetResourceBreakdown(cResourceWood, cAIResourceSubTypeEasy, gGatherPlanNumWoodPlans, 
         gGatherPlanPriorityWood, newBasePercentage, currentBaseId);
         aiSetResourceBreakdown(cResourceGold, cAIResourceSubTypeEasy, gGatherPlanNumMinePlans, 
         gGatherPlanPriorityMine, newBasePercentage, currentBaseId);

         // Create gather plans at the base.
         // if (overrideMain == false) {
         //    createGatherPlan(mainVec, currentBaseId, cResourceFood, 95);
         //    createGatherPlan(mainVec, currentBaseId, cResourceWood, 95);
         //    createGatherPlan(mainVec, currentBaseId, cResourceGold, 95);
         // }
      }

      // Set the resource distance limit.
      float dist = distance(kbGetMapCenter(), kbBaseGetLocation(cMyID, newBaseID));
      // Limit our distance, don't go pass the center of the map
      if (dist < 150.0)
      {
         kbBaseSetMaximumResourceDistance(cMyID, newBaseID, dist);
      }
      else
      {
         kbBaseSetMaximumResourceDistance(cMyID, newBaseID, 120.0);
      }

      kbBaseSetSettlement(cMyID, oldMainID, true);
      kbBaseSetSettlement(cMyID, newBaseID, true);
      // Set the main-ness of the base.
      if (overrideMain == true) {
         kbBaseSetMain(cMyID, oldMainID, false);
         kbBaseSetMain(cMyID, newBaseID, true);
      }

      //kbBaseSetMaximumResourceDistance(cMyID, newBaseID, kbGetMapXSize() * 2);

      // Add the TC, if any.
      int tcQuery = createSimpleUnitQuery(cUnitTypeTownCenter, cMyID, cUnitStateAlive, mainVec, 70.0);
      int tcCount = kbUnitQueryExecute(tcQuery);
      if (tcCount <= 0)
      {
         tcQuery = createSimpleUnitQuery(cUnitTypeTownCenter, cMyID, cUnitStateABQ, mainVec, 70.0);
         tcCount = kbUnitQueryExecute(tcQuery);
      }
      if (tcCount > 0)
      {
         int tcID = kbUnitQueryGetResult(tcQuery, 0);
         kbBaseAddUnit(cMyID, newBaseID, tcID);
      }
   }

   // Move the defend plan and reserve plan.
   xsEnableRule("endDefenseReflexDelay");

   return (newBaseID);
}
//==============================================================================
// createMilitaryBase
//==============================================================================
int createMilitaryBase(vector mainVec = cInvalidVector, bool overrideMain = true)
{
   debugBuildings("Creating military base at: " + mainVec);
   if (mainVec == cInvalidVector)
   {
      return (-1);
   }

   int oldMainID = kbBaseGetMainID(cMyID);

   // Also destroy bases nearby that can overlap with our radius.
   for (i = 0; < kbBaseGetNumber(cMyID))
   {
      int baseID = kbBaseGetIDByIndex(cMyID, i);
      if (distance(kbBaseGetLocation(cMyID, baseID), mainVec) < kbBaseGetDistance(cMyID, baseID) &&
         baseID != oldMainID)
      {
         kbBaseDestroy(cMyID, baseID);
   }
   }

   int newBaseID = kbBaseCreate(cMyID, "Base" + kbBaseGetNextID(), mainVec, 50.0);
   debugBuildings("New military base ID is: " + newBaseID);
   if (newBaseID > -1)
   {
      // Figure out the front vector.
      vector baseFront = xsVectorNormalize(kbGetMapCenter() - mainVec);
      kbBaseSetFrontVector(cMyID, newBaseID, baseFront);
      debugBuildings("Setting front vector to: " + baseFront);
      // Military gather point.
      float milDist = 40.0;
      int mainAreaGroupID = kbAreaGroupGetIDByPosition(mainVec);
      while (kbAreaGroupGetIDByPosition(mainVec + (baseFront * milDist)) != mainAreaGroupID)
      {
         milDist = milDist - 5.0;
         if (milDist < 6.0)
         {
            break;
      }
      }
      vector militaryGatherPoint = mainVec + (baseFront * milDist);

      kbBaseSetMilitaryGatherPoint(cMyID, newBaseID, militaryGatherPoint);
      // Set the other flags.
      kbBaseSetMilitary(cMyID, newBaseID, true);
      kbBaseSetEconomy(cMyID, newBaseID, false);
      kbBaseSetSettlement(cMyID, newBaseID, false);
      kbBaseSetForward(cMyID, newBaseID, true);
      // Set the main-ness of the base.
      if (overrideMain == true) {
         kbBaseSetMain(cMyID, oldMainID, false);
         kbBaseSetMain(cMyID, newBaseID, true);
      }
   }

   // Move the defend plan and reserve plan.
   //xsEnableRule("endDefenseReflexDelay");

   return (newBaseID);
}
//==============================================================================
// createSpacedLocationBuildPlan
//==============================================================================
int createSpacedLocationBuildPlan(int puid = -1, int number = 1, int pri = 100, bool economy = true,
                            int escrowID = -1, vector position = cInvalidVector, int numberBuilders = 1,
                            float buildingRadius = 10.0)
{
   if (cvOkToBuild == false)
   {
      return (-1);
   }
   // Create the right number of plans.
   for (i = 0; < number)
   {
      int planID = aiPlanCreate("Location Build Plan, " + number + " " + kbGetUnitTypeName(puid), cPlanBuild);
      if (planID < 0)
      {
         return (-1);
      }
      // What to build
      aiPlanSetVariableInt(planID, cBuildPlanBuildingTypeID, 0, puid);

      aiPlanSetVariableVector(planID, cBuildPlanCenterPosition, 0, position);
      aiPlanSetVariableFloat(planID, cBuildPlanCenterPositionDistance, 0, 30.0);

      // Set the buffer space to the building radius, ensuring a gap between buildings
      aiPlanSetVariableFloat(planID, cBuildPlanBuildingBufferSpace, 0, buildingRadius);
      if (puid == gFarmUnit)
      {
         aiPlanSetVariableFloat(planID, cBuildPlanBuildingBufferSpace, 0, 8.0);
      }

      // Priority.
      aiPlanSetDesiredPriority(planID, pri);

      // Builders.
      if (numberBuilders > 0 && addBuilderToPlan(planID, puid, numberBuilders) == false)
      {
         aiPlanDestroy(planID);
         return (-1);
      }

      aiPlanSetVariableVector(planID, cBuildPlanInfluencePosition, 0, position);              // Influence toward position
      aiPlanSetVariableFloat(planID, cBuildPlanInfluencePositionDistance, 0, 100.0);          // 100m range.
      aiPlanSetVariableFloat(planID, cBuildPlanInfluencePositionValue, 0, 200.0);             // 200 points max
      aiPlanSetVariableInt(planID, cBuildPlanInfluencePositionFalloff, 0, cBPIFalloffLinear); // Linear slope falloff

      debugBuildings("Created a Location Build Plan for: " + kbGetUnitTypeName(puid) + " with plan number: " + planID);
      aiPlanSetActive(planID);
   }
   return (planID); // Only really useful if number == 1, otherwise returns last value.
}
//==============================================================================
// createSpacedBuildPlan
// An extension of createSimpleBuildPlan for spacing out buildings.
//==============================================================================
int createSpacedBuildPlan(int puid = -1, int numberWanted = 1, int pri = 100, bool economy = true,
                          int escrowID = -1, int baseID = -1, int numberBuilders = 1, int parentPlanID = -1,
                          bool noQueue = false, float buildingRadius = 10.0) // Added buildingRadius parameter
{
   if (cvOkToBuild == false)
   {
      return -1; // Return invalid plan ID.
   }

   int planID = -1;

   // Create the right number of plans.
   for (i = 0; < numberWanted)
   {
      // Check for existing buildings of the same type within the specified radius
      int buildingQuery = createSimpleUnitQuery(puid, cMyID, cUnitStateAlive, kbBaseGetLocation(cMyID, baseID), buildingRadius);
      int numberFound = kbUnitQueryExecute(buildingQuery);

      if (numberFound > 0) {
         // There are already buildings of the same type within the radius, so don't create a new plan
         debugBuildings("Skipping build plan for " + kbGetUnitTypeName(puid) + " because there are already " + numberFound + " nearby.");
         continue;
      }

      planID = aiPlanCreate("Simple Build Plan for " + numberWanted + " " + kbGetUnitTypeName(puid), cPlanBuild, parentPlanID);
      if (planID < 0) // We somehow failed to create a plan.
      {
         debugBuildings("Failed to create a Simple Build Plan for " + kbGetUnitTypeName(puid));
         return -1;
      }
      // What to build.
      aiPlanSetVariableInt(planID, cBuildPlanBuildingTypeID, 0, puid);

      // Set the buffer space to the building radius, ensuring a gap between buildings
      aiPlanSetVariableFloat(planID, cBuildPlanBuildingBufferSpace, 0, buildingRadius);

      // 3 Meter separation between buildings, this can still be overwritten in selectBuildPlanPosition.
      //aiPlanSetVariableFloat(planID, cBuildPlanBuildingBufferSpace, 0, 6.0);
      if (puid == gFarmUnit || puid == gPlantationUnit || puid == cUnitTypedeBasilica)
      {
         aiPlanSetVariableFloat(planID, cBuildPlanBuildingBufferSpace, 0, 12.0);
      }

      // Set the priority.
      aiPlanSetDesiredPriority(planID, pri);

      // Add builders to the plan if that is requested.
      // This only adds the needed/wanted/minimum variables of the unittype to the plan not the actual builders.
      if (numberBuilders > 0)
      {
         if (addBuilderToPlan(planID, puid, numberBuilders) == false)
         {
            aiPlanDestroy(planID);
            return (-1);
         }
      }

      // If we don't create a queue all the plans will take builders instantly.
      // If those builders are Settlers for example you will suddenly have a lot less gathering.
      if (noQueue == true)
      {
         selectBuildPlanPosition(planID, puid, baseID);
      }
      else
      {
         bool queue = (i > 0);
         if (queue == false)
         {
            // Position.
            if (selectBuildPlanPosition(planID, puid, baseID) == false)
            {
               queue = true;
            }
         }

         if (queue == true)
         {
            // Queue this building.
            aiPlanSetActive(planID, false);
            // Save the base ID.
            aiPlanSetBaseID(planID, baseID);

            int queueSize = xsArrayGetSize(gQueuedBuildPlans);

            queue = false;

            for (j = 0; < queueSize)
            {
               if (xsArrayGetInt(gQueuedBuildPlans, j) >= 0)
               {
                  continue;
               }
               xsArraySetInt(gQueuedBuildPlans, j, planID);
               queue = true;
               break;
            }

            if (queue == false)
            {
               xsArrayResizeInt(gQueuedBuildPlans, queueSize + 1);
               xsArraySetInt(gQueuedBuildPlans, queueSize, planID);
            }

            continue;
         }
      }

      debugBuildings("Created a Simple Build Plan for: " + numberWanted + " " + kbGetUnitTypeName(puid) +
         " with plan number: " + planID);
      aiPlanSetActive(planID, true);
   }

   return planID; // Only really useful if numberWanted == 1, otherwise returns last plan ID.
}
//==============================================================================
// createDetailedBuildPlan
// An extension of createSimpleBuildPlan.
//==============================================================================
int createDetailedBuildPlan(int puid = -1, int numberWanted = 1, int pri = 100, bool economy = true,
                          int escrowID = -1, int baseID = -1, int numberBuilders = 1, int parentPlanID = -1,
                          bool noQueue = false, float centerDistance = 15.0, float influence = 1.0)
{
   vector centerOfBase = kbAreaGetCenter(kbAreaGroupGetIDByPosition(kbBaseGetLocation(cMyID, baseID)));
   if (cvOkToBuild == false)
   {
      return (-1); // Return invalid plan ID.
   }

   int planID = -1;

   // Create the right number of plans.
   for (i = 0; < numberWanted)
   {
      planID = aiPlanCreate("Detailed Build Plan for " + numberWanted + " " + kbGetUnitTypeName(puid), cPlanBuild, parentPlanID);
      if (planID < 0) // We somehow failed to create a plan.
      {
         debugBuildings("Failed to create a Detailed Build Plan for " + kbGetUnitTypeName(puid));
         return (-1);
      }
      // What to build.
      aiPlanSetVariableInt(planID, cBuildPlanBuildingTypeID, 0, puid);

      // Set the Escrow Id.
      aiPlanSetEscrowID(planID, escrowID);

      // 3 Meter separation between buildings, this can still be overwritten in selectBuildPlanPosition.
      aiPlanSetVariableFloat(planID, cBuildPlanBuildingBufferSpace, 0, 6.0);
      if (puid == gFarmUnit || puid == gPlantationUnit || puid == cUnitTypedeBasilica)
      {
         aiPlanSetVariableFloat(planID, cBuildPlanBuildingBufferSpace, 0, 12.0);
      }

      // Set the priority.
      aiPlanSetDesiredPriority(planID, pri);

      // Add builders to the plan if that is requested.
      // This only adds the needed/wanted/minimum variables of the unittype to the plan not the actual builders.
      if (numberBuilders > 0)
      {
         if (addBuilderToPlan(planID, puid, numberBuilders) == false)
         {
            aiPlanDestroy(planID);
            return (-1);
         }
      }

      // If we don't create a queue all the plans will take builders instantly.
      // If those builders are Settlers for example you will suddenly have a lot less gathering.
      if (noQueue == true)
      {
         selectBuildPlanPosition(planID, puid, baseID);
      }
      else
      {
         bool queue = (i > 0);
         if (queue == false)
         {
            // Position.
            if (selectBuildPlanPosition(planID, puid, baseID) == false)
            {
               queue = true;
            }
         }

         if (queue == true)
         {
            // Queue this building.
            aiPlanSetActive(planID, false);
            // Save the base ID.
            aiPlanSetBaseID(planID, baseID);

            int queueSize = xsArrayGetSize(gQueuedBuildPlans);

            queue = false;

            for (j = 0; < queueSize)
            {
               if (xsArrayGetInt(gQueuedBuildPlans, j) >= 0)
               {
                  continue;
               }
               xsArraySetInt(gQueuedBuildPlans, j, planID);
               queue = true;
               break;
            }

            if (queue == false)
            {
               xsArrayResizeInt(gQueuedBuildPlans, queueSize + 1);
               xsArraySetInt(gQueuedBuildPlans, queueSize, planID);
            }

            continue;
         }
      }

      aiPlanSetVariableVector(planID, cBuildPlanCenterPosition, 0, centerOfBase);
      aiPlanSetVariableFloat(planID, cBuildPlanCenterPositionDistance, 0, centerDistance);
      aiPlanSetVariableInt(planID, cBuildPlanInfluenceUnitTypeID, 0, puid);
      aiPlanSetVariableFloat(planID, cBuildPlanInfluenceUnitDistance, 0, influence);
      aiPlanSetVariableFloat(planID, cBuildPlanInfluenceUnitValue, 0, -20.0);             // -20 points per tower
      aiPlanSetVariableInt(planID, cBuildPlanInfluenceUnitFalloff, 0, cBPIFalloffLinear); // Linear slope falloff
      aiPlanSetVariableBool(planID, cBuildPlanInfluenceAtBuilderPosition, 0, true);
      aiPlanSetVariableFloat(planID, cBuildPlanInfluenceBuilderPositionValue, 0, 145.0);    // 45m range.
      aiPlanSetVariableFloat(planID, cBuildPlanInfluenceBuilderPositionDistance, 0, 200.0); // 200 points max
      aiPlanSetVariableInt(planID, cBuildPlanInfluenceBuilderPositionFalloff, 0, cBPIFalloffLinear); // Linear slope falloff

      debugBuildings("Created a Detailed Build Plan for: " + numberWanted + " " + kbGetUnitTypeName(puid) +
         " with plan number: " + planID);
      aiPlanSetActive(planID, true);
   }

   return (planID); // Only really useful if numberWanted == 1, otherwise returns last plan ID.
}
//==============================================================================
// findNearbyEnemyBuildings
// Finds nearby enemy buildings...
//==============================================================================
vector findNearbyEnemyBuildings(vector originLocation = cInvalidVector)
{
   int enemyBuildings = createSimpleUnitQuery(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, 
   cUnitStateAlive, originLocation, kbGetMapXSize() * 2);
   int buildingId = -1;
   vector buildingLocation = cInvalidVector;
   int buildingLocationId = -1;
   int buildingLocationGroupId = -1;
   int numberFound = kbUnitQueryExecute(enemyBuildings);

   for (i = 0; < numberFound) {
      buildingId = kbUnitQueryGetResult(enemyBuildings, i);
      buildingLocation = kbUnitGetPosition(buildingId);
      buildingLocationId = kbAreaGetIDByPosition(buildingLocation);
      buildingLocationGroupId = kbAreaGroupGetIDByPosition(buildingLocation);
      if ((buildingLocation != cInvalidVector) && 
      kbAreAreaGroupsPassableByLand(kbAreaGroupGetIDByPosition(originLocation), 
      kbAreaGroupGetIDByPosition(buildingLocation)) == true)
      {
         float xError = kbGetMapXSize() * 0.1;
         float zError = kbGetMapZSize() * 0.1;
         xsVectorSetX(buildingLocation, xsVectorGetX(buildingLocation) + aiRandFloat(0.0 - xError, xError));
         xsVectorSetZ(buildingLocation, xsVectorGetZ(buildingLocation) + aiRandFloat(0.0 - zError, zError));
         return (buildingLocation);
      }
   }

   return (buildingLocation);
}
//==============================================================================
// checkMilitarySize
// Returns a boolean to determine if our military strength is near it's maximum potential.
//==============================================================================
bool checkMilitarySize() {
   // Check build limit...
   int limit = kbGetBuildLimit(cMyID, cUnitTypeLogicalTypeLandMilitary);
   int availableUnits = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   
   if (availableUnits >= (limit * .95)) {
      return true;
   }
   return false;
}
//==============================================================================
// setHealingUnitType
// Sets the healing unit type based on the civilization.
//==============================================================================
void setHealingUnitType() {
    if (cMyCiv == cCivDEEthiopians) {
        gHealingUnitType = cUnitTypedeAbun;
    } else if (cMyCiv == cCivIndians) {
        gHealingUnitType = cUnitTypeypSPCBrahminHealer;
    } else if (cMyCiv == cCivDEHausa) {
        gHealingUnitType = cUnitTypedeGriot;
    } else if (cMyCiv == cCivXPIroquois || cMyCiv == cCivXPSioux) {
        gHealingUnitType = cUnitTypeAbstractHealer;
    } else if (cMyCiv == cCivOttomans) {
        gHealingUnitType = cUnitTypeImam;
    } else if ((cMyCiv == cCivBritish || cMyCiv == cCivFrench || cMyCiv == cCivGermans || 
               cMyCiv == cCivPortuguese || cMyCiv == cCivRussians || cMyCiv == cCivDutch || 
               cMyCiv == cCivDESwedish || cMyCiv == cCivDEMaltese || cMyCiv == cCivDEItalians) && 
               cMyCiv != cCivSpanish) {
        gHealingUnitType = cUnitTypePriest;
    } else if (cMyCiv == cCivSpanish) {
        gHealingUnitType = cUnitTypeMissionary;
    } else if (cMyCiv == cCivDEMexicans) {
        gHealingUnitType = cUnitTypedePadre;
    } else if (cMyCiv == cCivDEInca) {
        gHealingUnitType = cUnitTypedePriestess;
    } else if (cMyCiv == cCivChinese) {
        gHealingUnitType = cUnitTypeypMonkChinese2;
    } else if (cMyCiv == cCivJapanese) {
        gHealingUnitType = cUnitTypeypNatSohei;
    } else if (cMyCiv == cCivXPAztec) {
        gHealingUnitType = cUnitTypexpMedicineManAztec;
    } else {
        gHealingUnitType = cUnitTypePriest;
    }
}
//==============================================================================
// trainFromIslandBase
// Setup training from an island military base.
//==============================================================================
void trainFromIslandBase() {
   int limit = 0;
   int randomInteger = aiRandInt(2);

   limit = kbGetBuildLimit(cMyID, cUnitTypeLogicalTypeLandMilitary);
   // limit = limit;
   // if (limit < 1 || gIslandBaseID < 1)
   //    return;

   for (i = 0; i < gNumArmyUnitTypes; i++) {
      int candidate = kbUnitPickGetResult(gLandUnitPicker, i);
      if (candidate < 0) continue;

      if (kbProtoUnitIsType(candidate, cUnitTypeAbstractInfantry) && gIslandBaseLandUnit < 1) {
         gIslandBaseLandUnit = candidate;
         anwVerboseEcho("Land Unit To Train: " + kbGetProtoUnitName(gIslandBaseLandUnit));
      } else if (i == randomInteger) {
         gIslandBaseArtilleryUnit = candidate;
      }
   }

   if (kbBaseGetActive(cMyID, gIslandBaseID) == true && 
      (gIslandBaseMaintainPlan < 0 || aiPlanGetActive(gIslandBaseMaintainPlan) == false)) //cUnitTypeLogicalTypeLandMilitary
   {
      aiPlanDestroy(gIslandBaseMaintainPlan);
      gIslandBaseMaintainPlan = createSimpleMaintainPlan(gIslandBaseLandUnit, limit, false, gIslandBaseID, 1);
      aiPlanSetDesiredPriority(gIslandBaseMaintainPlan, 100);
      aiPlanSetVariableInt(gIslandBaseMaintainPlan, cTrainPlanBuildFromType, 0, cUnitTypeBarracks);
      //aiPlanSetVariableVector(gIslandBaseMaintainPlan, cTrainPlanGatherPoint, 0, gIslandBaseLocation);
      //aiPlanSetVariableInt(gIslandBaseMaintainPlan, cTrainPlanBuildFromType, 0, cUnitTypeBarracks);
      //aiPlanSetVariableInt(gIslandBaseMaintainPlan, cTrainPlanBuildFromType, 1, cUnitTypeStable);
      aiPlanSetActive(gIslandBaseMaintainPlan, true);
      
      anwVerboseEcho("Island base training initiated!");
   }
   else
   {
      aiPlanSetVariableInt(gIslandBaseMaintainPlan, cTrainPlanNumberToMaintain, 0, limit);
      aiPlanSetActive(gIslandBaseMaintainPlan, true);
   }
}
//==============================================================================
/* isDefending
   This function only checks to see if the AI is currently under attack.
*/
//==============================================================================
bool isDefending()
{
   int numPlans = aiPlanGetActiveCount();
   int existingPlanID = -1;
   
   for (int i = 0; i < numPlans; i++)
   {
      existingPlanID = aiPlanGetIDByActiveIndex(i);
      if (aiPlanGetType(existingPlanID) != cPlanCombat)
      {
         continue;
      }
      if (aiPlanGetVariableInt(existingPlanID, cCombatPlanCombatType, 0) == cCombatPlanCombatTypeDefend)
      {
         if ((existingPlanID != gExplorerControlPlan) &&
             (existingPlanID != gLandDefendPlan0) && 
             (existingPlanID != gLandReservePlan) && 
             (existingPlanID != gHealerPlan) && 
             (existingPlanID != gNavyRepairPlan) && 
             (existingPlanID != gNavyDefendPlan))
         {
            debugUtilities("isDefending: don't create another combat plan because we already have one named: "
               + aiPlanGetName(existingPlanID));
            return (true);
         }
      }
   }

   return (false);
}
