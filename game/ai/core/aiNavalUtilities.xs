//==============================================================================
/* getRandomWaterPoint
   Finds a random location on the map that is water.
*/
//==============================================================================
vector getRandomWaterPoint()
{
   vector startingLoc = kbGetPlayerStartingPosition(cMyID);
   int startingAreaID = kbAreaGetIDByPosition(startingLoc);
   int startingAreaGroupID = kbAreaGroupGetIDByPosition(startingLoc);
   vector waterLoc = cInvalidVector;
   vector waterAreaCentralPoint = cInvalidVector;
   int waterAreaID = -1;
   int waterAreaGroupID = -1;
   float xFloat = 0.0;
   float zFloat = 0.0;
   float mapWidth = kbGetMapXSize();
   float mapHeight = kbGetMapZSize();

   for (i = 0; < 90)
   {
      // Get a random vector on the map...
      xFloat = aiRandFloat(150.0, kbGetMapXSize());
      zFloat = aiRandFloat(150.0, kbGetMapZSize());
      waterLoc = xsVectorSet(xFloat, 0.0, zFloat);
      
      waterAreaID = kbAreaGetIDByPosition(waterLoc);
      waterAreaGroupID = kbAreaGroupGetIDByPosition(waterLoc);
      waterAreaCentralPoint = kbAreaGroupGetCenter(waterAreaGroupID);

      if ((kbAreaGroupGetType(waterAreaGroupID) == cAreaGroupTypeWater))
      {
         //sendStatement(1, cAICommPromptToAllyConfirm, waterLoc);
         return waterLoc;
      }
   }
   return cInvalidVector;
}
//==============================================================================
// invasionMilitaryManager
// This rule reminds the AI it has troops on an island and needs to use them.
//==============================================================================
rule invasionMilitaryManager
inactive
minInterval 20
{
   int enemyBuildingId = getClosestIslandUnitByLocation(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, 
   cUnitStateABQ, gNavalInvasionCoastalPoint, 1500);
   vector enemyBuildingLocation = kbUnitGetPosition(enemyBuildingId);
   int islandUnitsFound = findPassableLandUnits(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive,
                          -1, 1200.0, kbAreaGroupGetIDByPosition(enemyBuildingLocation));
   if (aiPlanGetActive(gForgottenMilitaryAssaultPlanID) == true || gActiveIslandInvasion == false ||
      islandUnitsFound > 5) {
      return;
   }

   // anwVerboseEcho("Island Invasion Manager!");
   // sendStatement(1, cAICommPromptToAllyConfirm, gNavalInvasionCoastalPoint);

   aiPlanDestroy(gForgottenMilitaryAssaultPlanID);
   aiPlanSetVariableInt(gForgottenMilitaryAssaultPlanID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeAttack);
   aiPlanSetVariableInt(gForgottenMilitaryAssaultPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(gForgottenMilitaryAssaultPlanID, cCombatPlanTargetPoint, 0, enemyBuildingLocation);
   aiPlanSetVariableVector(gForgottenMilitaryAssaultPlanID, cCombatPlanGatherPoint, 0, gNavalInvasionCoastalPoint);
   aiPlanSetVariableFloat(gForgottenMilitaryAssaultPlanID, cCombatPlanGatherDistance, 0, 500.0);
   aiPlanSetVariableInt(gForgottenMilitaryAssaultPlanID, cCombatPlanAttackRoutePattern, 0, cCombatPlanAttackRoutePatternBest);
   aiPlanSetVariableBool(gForgottenMilitaryAssaultPlanID, cCombatPlanAllowMoreUnitsDuringAttack, 0, true);
   aiPlanSetVariableInt(gForgottenMilitaryAssaultPlanID, cCombatPlanRefreshFrequency, 0, cDifficultyCurrent >= cDifficultyHard ? 300 : 1000);
   aiPlanSetVariableInt(gForgottenMilitaryAssaultPlanID, cCombatPlanDoneMode, 0, cCombatPlanDoneModeRetreat | cCombatPlanDoneModeNoTarget);
   aiPlanSetVariableInt(gForgottenMilitaryAssaultPlanID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetVariableInt(gForgottenMilitaryAssaultPlanID, cCombatPlanNoTargetTimeout, 0, 30000);
   aiPlanSetInitialPosition(gForgottenMilitaryAssaultPlanID, gNavalInvasionCoastalPoint);
   aiPlanSetDesiredPriority(gForgottenMilitaryAssaultPlanID, 99);
   aiPlanSetActive(gForgottenMilitaryAssaultPlanID);
}
//==============================================================================
// warshipNuggetCollector
// This rule enables the AI to gather naval nuggets.
//==============================================================================
rule warshipNuggetCollector
inactive
minInterval 10
{
   //anwVerboseEcho("There be treasures in these waters!");

   if (gDefenseReflex == true) {
      aiPlanDestroy(gWarshipExplorePlan);
      return;
   }

   int nuggetQuery = createSimpleUnitQuery(cUnitTypeAbstractNuggetWater, cPlayerRelationAny, cUnitStateAlive);
   kbUnitQuerySetPosition(nuggetQuery, gNavyVec);
   kbUnitQuerySetMaximumDistance(nuggetQuery, kbGetMapXSize() * 2);
   kbUnitQuerySetAscendingSort(nuggetQuery, true);
   int numberNuggets = kbUnitQueryExecute(nuggetQuery);
   int closestNuggetID = kbUnitQueryGetResult(nuggetQuery, 0);
   vector closestNuggetPosition = kbUnitGetPosition(closestNuggetID);
   int shipQueryId = createIdleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(shipQueryId);

   if (gClosestNuggetId == -1) {
      gClosestNuggetId = closestNuggetID;
   }

   int guardianQuery = createSimpleUnitQuery(cUnitTypeGuardian, 0, cUnitStateAlive, closestNuggetPosition, 10.0);
   kbUnitQuerySetAscendingSort(guardianQuery, true);
   int numberGuardians = kbUnitQueryExecute(guardianQuery);

   if ((gWarshipExplorePlan == -1 || aiPlanGetNumberUnits(gWarshipExplorePlan, cUnitTypeAbstractWarShip) < 1) && numberFound > 3) // || aiPlanGetActive(gWarshipExplorePlan) == false)
   {
      aiPlanDestroy(gWarshipExplorePlan);

      if (numberGuardians > 0) {
         gWarshipExplorePlan = aiPlanCreate("Explore Water For Treasures", cPlanAttack);
         aiPlanAddUnitType(gWarshipExplorePlan, cUnitTypeAbstractWarShip, 2, 3, 4);
         aiPlanSetVariableVector(gWarshipExplorePlan, cAttackPlanAttackPoint, 0, closestNuggetPosition);
         aiPlanSetVariableVector(gWarshipExplorePlan, cAttackPlanGatherPoint, 0, gNavyVec);
         aiPlanSetVariableInt(gWarshipExplorePlan, cAttackPlanSpecificTargetID, 0, kbUnitQueryGetResult(guardianQuery, 0) > 0 ? 
         kbUnitQueryGetResult(guardianQuery, 0) : closestNuggetID);
         aiPlanSetVariableInt(gWarshipExplorePlan, cAttackPlanPlayerID, 0, 0);
         aiPlanSetVariableInt(gWarshipExplorePlan, cAttackPlanTargetTypeID, 0, cUnitTypeGuardian);
         aiPlanSetVariableFloat(gWarshipExplorePlan, cAttackPlanGatherDistance, 0, kbGetMapXSize());
         aiPlanSetVariableInt(gWarshipExplorePlan, cAttackPlanRefreshFrequency, 0, cDifficultyCurrent >= cDifficultyHard ? 30000 : 10000);
         aiPlanSetVariableInt(gWarshipExplorePlan, cAttackPlanAttackRoutePattern, 0, cAttackPlanAttackRoutePatternBest);
         aiPlanSetBaseID(gWarshipExplorePlan, kbUnitGetBaseID(getUnit(gDockUnit, cMyID, cUnitStateAlive)));
         aiPlanSetVariableInt(gWarshipExplorePlan, cAttackPlanAttackPointEngageRange, 0, 50.0);
         aiPlanSetDesiredPriority(gWarshipExplorePlan, 99);
         aiPlanSetInitialPosition(gWarshipExplorePlan, gNavyVec);
         aiPlanSetActive(gWarshipExplorePlan, true);
      } else {
         gWarshipExplorePlan = aiPlanCreate("Explore Water For Treasures", cPlanGatherNuggets);
         aiPlanSetDesiredPriority(gWarshipExplorePlan, 100);
         aiPlanSetInitialPosition(gWarshipExplorePlan, gNavyVec);
         aiPlanSetRequiresAllNeedUnits(gWarshipExplorePlan, true);
         aiPlanSetUnitStance(gWarshipExplorePlan, cUnitStanceAggressive);
         aiPlanSetAttack(gWarshipExplorePlan, true);
         aiPlanAddUnitType(gWarshipExplorePlan, cUnitTypeAbstractWarShip, 2, 3, 3);
         aiPlanSetVariableVector(gWarshipExplorePlan, cNuggetPlanTargetGatherPosition, 0, gNavyVec);
         aiPlanSetVariableFloat(gWarshipExplorePlan, cNuggetPlanGatherDistance, 0, kbGetMapXSize());
         aiPlanSetVariableInt(gWarshipExplorePlan, cNuggetPlanMaxGuardianStrength, 0, 100.0);
         aiPlanSetVariableInt(gWarshipExplorePlan, cNuggetPlanTargetNuggetID, 0, closestNuggetID);
         aiPlanSetBaseID(gWarshipExplorePlan, kbUnitGetBaseID(getUnit(gDockUnit, cMyID, cUnitStateAlive)));
         aiPlanSetActive(gWarshipExplorePlan, true);
      }
   } else if (aiPlanGetNumberUnits(gWarshipExplorePlan, cUnitTypeAbstractWarShip) < 1) {
      int allShipsQuery = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive);
      int numberShips = kbUnitQueryExecute(allShipsQuery);
      for (i = 0; i < numberShips; i++)
      {
         aiPlanAddUnit(gWarshipExplorePlan, kbUnitQueryGetResult(allShipsQuery, i) );
         if (i > 2) {
            break;
         }
      }
   }

   int closeShipQueryId = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive, closestNuggetPosition, 20.0);
   kbUnitQuerySetAscendingSort(closeShipQueryId, true);
   int closeNumberFound = kbUnitQueryExecute(closeShipQueryId);

   //sendStatement(1, cAICommPromptToAllyConfirm, closestNuggetPosition);
   //anwVerboseEcho("Number in Plan: "+aiPlanGetNumberUnits(gWarshipExplorePlan, cUnitTypeAbstractWarShip)+"");

   if ((numberNuggets > 0 && numberGuardians == 0) && (closeNumberFound < 1 || 
        aiPlanGetNumberUnits(gWarshipExplorePlan, cUnitTypeAbstractWarShip) < 1))
   {
      int anyShipQueryId = createSimpleUnitQuery(cUnitTypeAbstractWarShip, cMyID, cUnitStateAlive, closestNuggetPosition, kbGetMapXSize());
      kbUnitQuerySetAscendingSort(anyShipQueryId, true);
      int anyNumberFound = kbUnitQueryExecute(anyShipQueryId);
      for (i = 0; i < anyNumberFound; i++)
      {
         aiTaskUnitWork(kbUnitQueryGetResult(anyShipQueryId, i), closestNuggetID, true);
         if (i > 5) {
            break;
         }
      }
   }
   if (numberNuggets > 0 && closeNumberFound > 0)
   {
      if (numberGuardians > 0)
      {
         for (i = 0; i < aiPlanGetNumberUnits(gWarshipExplorePlan, cUnitTypeAbstractWarShip); i++)
         {
            aiTaskUnitWork(aiPlanGetUnitByIndex(gWarshipExplorePlan, i), kbUnitQueryGetResult(guardianQuery, 0), true);
            aiTaskUnitWork(aiPlanGetUnitByIndex(gWarshipExplorePlan, 0), kbUnitQueryGetResult(guardianQuery, 0), true);
         }
      } else if (numberGuardians < 1) {
         for (i = 0; i < aiPlanGetNumberUnits(gWarshipExplorePlan, cUnitTypeAbstractWarShip); i++)
         {
            aiTaskUnitWork(aiPlanGetUnitByIndex(gWarshipExplorePlan, i), closestNuggetID, true);
         }
      }
   }

   if (getUnit(cUnitTypeAbstractNuggetWater, cPlayerRelationAny, cUnitStateAlive) < 1) {
      xsDisableSelf();
   }
}
//==============================================================================
// galleonTrainingManager
// This rule helps warships train units.
//==============================================================================
rule galleonTrainingManager
inactive
minInterval 40
{
   static int galleonTrainingPlan = -1;
   int villagerPlan = -1;
   int limit = 0;

   limit = kbGetBuildLimit(cMyID, cUnitTypeLogicalTypeLandMilitary);
   if (limit < 1)
      return;

   if (galleonTrainingPlan < 0)
   {
      galleonTrainingPlan = createSimpleMaintainPlan(cUnitTypeLogicalTypeLandMilitary, limit, true, -1, 1);
      aiPlanSetDesiredPriority(galleonTrainingPlan, 85);
      aiPlanSetVariableInt(galleonTrainingPlan, cTrainPlanBuildFromType, 0, gGalleonUnit);
      anwVerboseEcho("Galleon training!");
   }
   else
   {
      aiPlanSetVariableInt(galleonTrainingPlan, cTrainPlanNumberToMaintain, 0, limit);
   }
}
//==============================================================================
/* getRandomPatrolPoint
   Finds a point on the main island to patrol.
*/
//==============================================================================
vector getRandomPatrolPoint()
{
   vector startingLoc = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
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

   for (i = 0; < 20)
   {
      // Get a random vector on the map...
      xFloat = aiRandFloat(150.0, kbGetMapXSize());
      zFloat = aiRandFloat(150.0, kbGetMapZSize());
      landLoc = xsVectorSet(xFloat, 0.0, zFloat);
      
      landAreaID = kbAreaGetIDByPosition(landLoc);
      landAreaGroupID = kbAreaGroupGetIDByPosition(landLoc);
      landAreaCentralPoint = kbAreaGroupGetCenter(landAreaGroupID);

      if ((kbAreaGroupGetType(landAreaGroupID) != cAreaGroupTypeWater) &&
          (kbAreAreaGroupsPassableByLand(landAreaGroupID, startingAreaGroupID) == true))
      {
         //sendStatement(1, cAICommPromptToAllyConfirm, landLoc);
         return landLoc;
      }
   }
   return cInvalidVector;
}
//==============================================================================
/* getRandomIslandToAttack
   Finds an island to invade...
*/
//==============================================================================
vector getRandomIslandToAttack()
{
   vector startingLoc = kbGetPlayerStartingPosition(cMyID);
   int startingAreaID = kbAreaGetIDByPosition(startingLoc);
   int startingAreaGroupID = kbAreaGroupGetIDByPosition(startingLoc);
   vector islandLoc = cInvalidVector;
   vector islandAreaCentralPoint = cInvalidVector;
   int islandAreaID = -1;
   int islandAreaGroupID = -1;
   float xFloat = 0.0;
   float zFloat = 0.0;
   int numEnemyBuildings = -1;

   // Check if we have seen the enemy base, if so, this is our destination, not just some island...
   int closestBaseID = kbFindClosestBase(cPlayerRelationEnemy, startingLoc);
   vector closestBaseLocation = kbBaseGetLocation(kbBaseGetOwner(closestBaseID), closestBaseID);
   int closestBaseAreaGroupID = kbAreaGroupGetIDByPosition(closestBaseLocation);
   int enemyUnitQueryID = createSimpleUnitQuery(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, cUnitStateABQ);
   int enemyNumberFound = kbUnitQueryExecute(enemyUnitQueryID);
   int enemyAreaGroupID = -1;
   int areaGroupID = -1;
   int unitID = -1;
   for (i = 0; < enemyNumberFound)
   {
      unitID = kbUnitQueryGetResult(enemyUnitQueryID, i);
      if (kbHasPlayerLost(kbUnitGetPlayerID(unitID)) == true)
      {
         continue;
      }
      areaGroupID = kbAreaGroupGetIDByPosition(kbUnitGetPosition(unitID));
      if (areaGroupID == startingAreaGroupID)
      {
         continue;
      }
      enemyAreaGroupID = areaGroupID;
      break;
   }

   float mapWidth = kbGetMapXSize();
   float mapHeight = kbGetMapZSize();

   for (i = 0; < 90)
   {
      // Get a random vector on the map...
      xFloat = aiRandFloat(150.0, kbGetMapXSize());
      zFloat = aiRandFloat(150.0, kbGetMapZSize());
      islandLoc = xsVectorSet(xFloat, 0.0, zFloat);
      
      islandAreaID = kbAreaGetIDByPosition(islandLoc);
      islandAreaGroupID = kbAreaGroupGetIDByPosition(islandLoc);
      islandAreaCentralPoint = kbAreaGroupGetCenter(islandAreaGroupID);

      if ((kbAreaGroupGetType(islandAreaGroupID) == cAreaGroupTypeLand) &&
          (kbAreAreaGroupsPassableByLand(islandAreaGroupID, enemyAreaGroupID) == true) &&
          (kbAreAreaGroupsPassableByLand(islandAreaGroupID, startingAreaGroupID) == false))
      {
         gProbableEnemyIslandX = xFloat;
         gProbableEnemyIslandZ = zFloat;
         //sendStatement(1, cAICommPromptToAllyConfirm, islandLoc);
         gProbableEnemyIslandAreaId = kbAreaGetIDByPosition(islandLoc);
         gProbableEnemyIslandGroupId = kbAreaGroupGetIDByPosition(islandLoc);
         gIslandFound = true;
         return islandLoc;
      }
   }
   return cInvalidVector;
}
//==============================================================================
/* getRandomIslandToColonize
   Finds an island to invade...
*/
//==============================================================================
vector getRandomIslandToColonize()
{
   vector startingLoc = kbGetPlayerStartingPosition(cMyID);
   int startingAreaID = kbAreaGetIDByPosition(startingLoc);
   int startingAreaGroupID = kbAreaGroupGetIDByPosition(startingLoc);
   vector islandLoc = cInvalidVector;
   vector islandAreaCentralPoint = cInvalidVector;
   int islandAreaID = -1;
   int islandAreaGroupID = -1;
   float xFloat = 0.0;
   float zFloat = 0.0;
   int numEnemyBuildings = -1;

   // Check if we have seen the enemy base, if so, this is our destination, not just some island...
   int closestBaseID = kbFindClosestBase(cPlayerRelationEnemy, startingLoc);
   vector closestBaseLocation = kbBaseGetLocation(kbBaseGetOwner(closestBaseID), closestBaseID);
   int closestBaseAreaGroupID = kbAreaGroupGetIDByPosition(closestBaseLocation);
   int enemyUnitQueryID = createSimpleUnitQuery(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, cUnitStateABQ);
   int enemyNumberFound = kbUnitQueryExecute(enemyUnitQueryID);
   int enemyAreaGroupID = -1;
   int areaGroupID = -1;
   int unitID = -1;
   for (i = 0; < enemyNumberFound)
   {
      unitID = kbUnitQueryGetResult(enemyUnitQueryID, i);
      if (kbHasPlayerLost(kbUnitGetPlayerID(unitID)) == true)
      {
         continue;
      }
      areaGroupID = kbAreaGroupGetIDByPosition(kbUnitGetPosition(unitID));
      if (areaGroupID == startingAreaGroupID)
      {
         continue;
      }
      enemyAreaGroupID = areaGroupID;
      break;
   }

   float mapWidth = kbGetMapXSize();
   float mapHeight = kbGetMapZSize();

   for (i = 0; < 90)
   {
      // Get a random vector on the map...
      xFloat = aiRandFloat(150.0, kbGetMapXSize());
      zFloat = aiRandFloat(150.0, kbGetMapZSize());
      islandLoc = xsVectorSet(xFloat, 0.0, zFloat);
      
      islandAreaID = kbAreaGetIDByPosition(islandLoc);
      islandAreaGroupID = kbAreaGroupGetIDByPosition(islandLoc);
      islandAreaCentralPoint = kbAreaGroupGetCenter(islandAreaGroupID);

      if ((kbAreaGroupGetType(islandAreaGroupID) == cAreaGroupTypeLand) &&
          (kbAreAreaGroupsPassableByLand(islandAreaGroupID, enemyAreaGroupID) == false) &&
          (kbAreAreaGroupsPassableByLand(islandAreaGroupID, startingAreaGroupID) == false))
      {
         gProbableEnemyIslandX = xFloat;
         gProbableEnemyIslandZ = zFloat;
         //sendStatement(1, cAICommPromptToAllyConfirm, islandLoc);
         gProbableEnemyIslandAreaId = kbAreaGetIDByPosition(islandLoc);
         gProbableEnemyIslandGroupId = kbAreaGroupGetIDByPosition(islandLoc);
         gIslandFound = true;
         return islandLoc;
      }
   }
   return cInvalidVector;
}
//==============================================================================
// getCoastline
// Finds a coastal point on an island.
//==============================================================================
vector getCoastline(vector centerOrigin = cInvalidVector)
{
   //vector startingLoc = kbGetPlayerStartingPosition(cMyID);
   int startingAreaID = kbAreaGetIDByPosition(centerOrigin);
   int coastlineAreaID = -1;
   int islandAreaGroupID = kbAreaGroupGetIDByPosition(centerOrigin);
   vector islandCenter = kbAreaGroupGetCenter(islandAreaGroupID);
   vector coastlineCheck = cInvalidVector;
   // vector directionVector = xsVectorNormalize(centerOrigin - islandCenter);
   // int distance = distance(centerOrigin, islandCenter);
   int coastlineCheckID = -1;
   float xFloat = 0.0;
   float zFloat = 0.0;

   for (i = 0; < 20)
   {
      xFloat = i * kbGetMapXSize() / 150.0;
      zFloat = i * kbGetMapZSize() / 150.0;
      centerOrigin = xsVectorSet(xsVectorGetX(islandCenter) + aiRandFloat(0.0 - xFloat, xFloat), 0.0, 
                     xsVectorGetZ(islandCenter) + aiRandFloat(0.0 - zFloat, zFloat));

      coastlineAreaID = kbAreaGetIDByPosition(centerOrigin);
      int numberBorders = kbAreaGetNumberBorderAreas(coastlineAreaID);
      bool inMainBase = false;
      for (j = 0; < numberBorders)
      {
         coastlineCheckID = kbAreaGroupGetIDByPosition(kbAreaGetCenter(kbAreaGetBorderAreaID(coastlineAreaID, j)));
         if (kbAreaGroupGetType(coastlineCheckID) == cAreaGroupTypeWater)
         {
            return centerOrigin;
         }
      }
      // if (kbAreaGetType(coastlineAreaID) != cAreaTypeWater)
      // {
      //    return centerOrigin;
      // }
   }
   return cInvalidVector;
}
//==============================================================================
// coastalEdgeVector
// Find a vector that is on the edge of the coast of an island.
//==============================================================================
vector coastalEdgeVector(vector origin = cInvalidVector, vector destination = cInvalidVector,
                        bool awayFromBuildings = false, bool coastalBuilding = false, bool getLand = false)
{
	vector directionVector = cInvalidVector;
   vector currentVector = destination;
	vector landVector = currentVector;
   int distanceInt = distance(origin, destination);
   int closestBuilding = getClosestIslandUnitByLocation(cUnitTypeBuilding, cPlayerRelationAny, cUnitStateABQ, origin, 120);

   if (coastalBuilding == true) {
      directionVector = xsVectorNormalize(destination - origin);
   } else {
      directionVector = xsVectorNormalize(origin - destination);
   }
   
	for (i = 0; i < distanceInt; i++)
	{
		currentVector = currentVector + directionVector;

		if (kbAreaGetType(kbAreaGetIDByPosition(currentVector)) == cAreaTypeWater &&
         awayFromBuildings == false && getLand == false)
		{
			return landVector;
		} else if (kbAreaGetType(kbAreaGetIDByPosition(currentVector)) == cAreaTypeWater &&
                awayFromBuildings == true && distance(landVector, kbUnitGetPosition(closestBuilding)) > 20.0
                && getLand == false) {
         return landVector;
      } else if (kbAreaGetType(kbAreaGetIDByPosition(currentVector)) != cAreaTypeWater &&
         getLand == true) {
         return landVector;
      }

		landVector = currentVector;
		landVector = landVector - directionVector;
	}
	return cInvalidVector;
}
vector coastalDockEdgeVector(vector origin = cInvalidVector, vector destination = cInvalidVector,
                        bool awayFromBuildings = false, bool coastalBuilding = false, bool getLand = false)
{
    vector directionVector = xsVectorNormalize(destination - origin);
    vector currentVector = origin;
    vector lastLand = origin;

    int closestBuilding = getClosestIslandUnitByLocation(cUnitTypeBuilding, cPlayerRelationAny, cUnitStateABQ, origin, 120);

    for (i = 0; i < 200; i++) // fixed max search distance
    {
        currentVector = currentVector + directionVector;

        int areaType = kbAreaGetType(kbAreaGetIDByPosition(currentVector));

        if (areaType == cAreaTypeWater && getLand == false) {
            if (awayFromBuildings == false || distance(lastLand, kbUnitGetPosition(closestBuilding)) > 20.0) {
                return lastLand;
            }
        }
        else if (areaType != cAreaTypeWater && getLand) {
            return lastLand;
        }

        lastLand = currentVector;
    }
    return cInvalidVector;
}


//==============================================================================
// enemyDockTarget
// Find a vector that has an enemy dock.
//==============================================================================
vector enemyDockTarget(vector origin = cInvalidVector)
{
   int dockQuery = createSimpleUnitQuery(cUnitTypeAbstractDock, cPlayerRelationEnemyNotGaia, cUnitStateABQ);
   int numberFound = kbUnitQueryExecute(dockQuery);
   int randomDockIndex = aiRandInt(numberFound);
   int unitId = -1;
   vector dockLocation = cInvalidVector;

	for (i = 0; < numberFound)
	{
      if (i == randomDockIndex) {
         unitId = kbUnitQueryGetResult(dockQuery, i);
         dockLocation = kbUnitGetPosition(unitId);
         return dockLocation;
      }
	}
	return cInvalidVector;
}
//==============================================================================
// dockWagonBuildPlanManager
// Checks for the existence of dock wagons and, if any exist, immediately
// creates a build plan to produce more or utilize them.
//==============================================================================
rule dockWagonBuildPlanManager
inactive
minInterval 2
maxInterval 2
{
    // --- STOP CONDITIONS ---
    if (kbUnitCount(cMyID, gDockUnit, cUnitStateABQ) > 0) {
        gDockRandomTries = 0;
        xsDisableSelf();
        return;
    }

    // --- FIND WAGON ---
    int wagonQueryID = -1;
    int wagonID = -1;
    int wagonType = -1;
    
    if (kbUnitCount(cMyID, cUnitTypeYPDockWagon, cUnitStateAlive) > 0) {
        wagonQueryID = createSimpleUnitQuery(cUnitTypeYPDockWagon, cMyID, cUnitStateAlive);
        wagonType = cUnitTypeYPDockWagon;
    }
    else if (kbUnitCount(cMyID, cUnitTypedeDockWagon, cUnitStateAlive) > 0) {
        wagonQueryID = createSimpleUnitQuery(cUnitTypedeDockWagon, cMyID, cUnitStateAlive);
        wagonType = cUnitTypedeDockWagon;
    }
    else {
        xsDisableSelf();
        return;
    }

    if (wagonQueryID < 0 || kbUnitQueryExecute(wagonQueryID) < 1) {
        return;
    }

    wagonID = kbUnitQueryGetResult(wagonQueryID, 0);

    // --- CHECK IF WAGON IS ALREADY IN A PLAN ---
    int wagonPlanID = kbUnitGetPlanID(wagonID);
    if (wagonPlanID >= 0)
    {
        // Wagon is in a plan, wait.
        return;
    }

    // --- BASE LOCATION ---
    vector baseLoc = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));

    // --- EXHAUSTION CHECK ---
    if (gDockRandomTries >= 180) {
        // Destroy wagon and assign villager dock
        aiTaskUnitDelete(wagonID);

        vector fallbackEdge = coastalDockEdgeVector(baseLoc, gNavyVec, false, true, true);

        int vPlan = createLocationBuildPlan(
            gDockUnit,
            1,
            50,
            true,
            cEconomyEscrowID,
            fallbackEdge,
            1
        );
        aiPlanAddUnitType(vPlan, cUnitTypeAbstractVillager, 1, 1, 1);

        gDockRandomTries = 0;
        xsDisableSelf();
        return;
    }

    // --- TRY BUILD PLAN APPROACH ---
    vector searchVec = getRandomWaterPoint();
    gDockBaseCoastalEdge = coastalDockEdgeVector(baseLoc, searchVec, false, false, false);

    vector tryPoint = gDockBaseCoastalEdge;
    
    int dir = aiRandInt(5);
    int dist = aiRandInt(60) + 1;
    
    if (dir == 1) {
        tryPoint = tryPoint + xsVectorSet(dist * 1.0, 0.0, 0.0);
    }
    else if (dir == 2) {
        tryPoint = tryPoint + xsVectorSet(dist * -1.0, 0.0, 0.0);
    }
    else if (dir == 3) {
        tryPoint = tryPoint + xsVectorSet(0.0, 0.0, dist * 1.0);
    }
    else if (dir == 4) {
        tryPoint = tryPoint + xsVectorSet(0.0, 0.0, dist * -1.0);
    }

    // Create a build plan for the dock wagon
    int dockPlan = aiPlanCreate("Dock Wagon Build Plan", cPlanBuild);
    aiPlanSetVariableInt(dockPlan, cBuildPlanBuildingTypeID, 0, gDockUnit);
    aiPlanSetDesiredPriority(dockPlan, 100);
    aiPlanSetDesiredResourcePriority(dockPlan, 100);
    aiPlanSetMilitary(dockPlan, false);
    aiPlanSetEconomy(dockPlan, true);
    aiPlanSetEscrowID(dockPlan, cEconomyEscrowID);

    // Use dock placement points
    aiPlanSetNumberVariableValues(dockPlan, cBuildPlanDockPlacementPoint, 2, true);
    aiPlanSetVariableVector(dockPlan, cBuildPlanDockPlacementPoint, 0, baseLoc);
    aiPlanSetVariableVector(dockPlan, cBuildPlanDockPlacementPoint, 1, tryPoint);
    
    aiPlanAddUnitType(dockPlan, wagonType, 1, 1, 1);
    aiPlanAddUnit(dockPlan, wagonID);
    aiPlanSetNoMoreUnits(dockPlan, true);
    
    aiPlanSetActive(dockPlan);
    
    gDockRandomTries = gDockRandomTries + 1;
}
//==============================================================================
// assignIdleIslandUnitsToAssault
// Find idle units on the island and add them to assault plan
//==============================================================================
void assignIdleIslandUnitsToAssault()
{
   if (gIslandAssaultPlanID < 0) {
      return;
   }
   
   int myBaseAreaGroupID = kbAreaGroupGetIDByPosition(kbGetPlayerStartingPosition(cMyID));
   int islandAreaGroupID = kbAreaGroupGetIDByPosition(gIslandCenterPoint);
   
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   
   int unitsAssigned = 0;
   
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
      if (kbAreAreaGroupsPassableByLand(islandAreaGroupID, unitLocationGroupId) == false) {
         continue;
      }
      
      // Check if unit is idle or in a low-priority plan
      int currentPlanID = kbUnitGetPlanID(unitID);
      if (currentPlanID == gIslandAssaultPlanID) {
         continue; // Already in assault plan
      }
      
      // Check if unit is idle (no plan or inactive plan)
      bool isIdle = (currentPlanID < 0) || (aiPlanGetActive(currentPlanID) == false);
      bool isLowPriority = (currentPlanID >= 0) && (aiPlanGetDesiredPriority(currentPlanID) < 50);
      
      if (isIdle || isLowPriority) {
         // Remove from current plan if any
         if (currentPlanID >= 0) {
            aiPlanRemoveUnit(currentPlanID, unitID);
         }
         
         // Add to assault plan
         aiPlanAddUnit(gIslandAssaultPlanID, unitID);
         unitsAssigned++;
      }
   }
   
   if (unitsAssigned > 0) {
      anwVerboseEcho("Assigned " + unitsAssigned + " idle units to assault plan");
   }
}

//==============================================================================
// assignIdleIslandUnitsToSearch
// Find idle units on the island and add them to search plan
//==============================================================================
void assignIdleIslandUnitsToSearch()
{
   if (gIslandSearchPlanID < 0) {
      return;
   }
   
   int myBaseAreaGroupID = kbAreaGroupGetIDByPosition(kbGetPlayerStartingPosition(cMyID));
   int islandAreaGroupID = kbAreaGroupGetIDByPosition(gIslandCenterPoint);
   
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   
   int unitsAssigned = 0;
   
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
      if (kbAreAreaGroupsPassableByLand(islandAreaGroupID, unitLocationGroupId) == false) {
         continue;
      }
      
      // Check if unit is idle or in a low-priority plan
      int currentPlanID = kbUnitGetPlanID(unitID);
      if (currentPlanID == gIslandSearchPlanID) {
         continue; // Already in search plan
      }
      
      // Check if unit is idle (no plan or inactive plan)
      bool isIdle = (currentPlanID < 0) || (aiPlanGetActive(currentPlanID) == false);
      bool isLowPriority = (currentPlanID >= 0) && (aiPlanGetDesiredPriority(currentPlanID) < 50);
      
      if (isIdle || isLowPriority) {
         // Remove from current plan if any
         if (currentPlanID >= 0) {
            aiPlanRemoveUnit(currentPlanID, unitID);
         }
         
         // Add to search plan
         aiPlanAddUnit(gIslandSearchPlanID, unitID);
         unitsAssigned++;
      }
   }
   
   if (unitsAssigned > 0) {
      anwVerboseEcho("Assigned " + unitsAssigned + " idle units to search plan");
   }
}
//==============================================================================
// createIslandBasePatrolPlan
// Creates a patrol plan for troops at the island base when enemy location unknown
//==============================================================================
void createIslandBasePatrolPlan()
{
   if (gIslandBaseLocation == cInvalidVector) {
      return;
   }
   
   // Destroy old patrol plan if exists
   if (gIslandBasePatrolPlan >= 0) {
      aiPlanDestroy(gIslandBasePatrolPlan);
      gIslandBasePatrolPlan = -1;
   }
   
   // Get island center for patrol target
   int islandAreaGroupID = kbAreaGroupGetIDByPosition(gIslandBaseLocation);
   vector islandCenter = kbAreaGroupGetCenter(islandAreaGroupID);
   
   // Create a defend plan that patrols the island
   gIslandBasePatrolPlan = aiPlanCreate("Island Base Patrol", cPlanDefend);
   
   if (gIslandBasePatrolPlan < 0) {
      return;
   }
   
   aiPlanAddUnitType(gIslandBasePatrolPlan, cUnitTypeLogicalTypeLandMilitary, 1, 5, 50);
   aiPlanSetVariableVector(gIslandBasePatrolPlan, cDefendPlanDefendPoint, 0, islandCenter);
   aiPlanSetVariableFloat(gIslandBasePatrolPlan, cDefendPlanEngageRange, 0, 150.0);
   aiPlanSetVariableBool(gIslandBasePatrolPlan, cDefendPlanPatrol, 0, true);
   aiPlanSetVariableFloat(gIslandBasePatrolPlan, cDefendPlanGatherDistance, 0, 50.0);
   aiPlanSetInitialPosition(gIslandBasePatrolPlan, gIslandBaseLocation);
   aiPlanSetUnitStance(gIslandBasePatrolPlan, cUnitStanceAggressive);
   aiPlanSetVariableInt(gIslandBasePatrolPlan, cDefendPlanRefreshFrequency, 0, 30);
   aiPlanSetVariableInt(gIslandBasePatrolPlan, cDefendPlanAttackTypeID, 0, cUnitTypeUnit);
   aiPlanSetDesiredPriority(gIslandBasePatrolPlan, 55);
   aiPlanSetActive(gIslandBasePatrolPlan, true);
   
   anwVerboseEcho("Created island base patrol plan");
}
//==============================================================================
// manageIslandBaseTroops
// Manage troops created at the island base
// Assigns them to assault/search plans or creates patrol if no enemy known
//==============================================================================
void manageIslandBaseTroops()
{
   if (gIslandBaseID < 0 || gIslandBaseLocation == cInvalidVector) {
      return;
   }
   
   int islandBaseAreaGroupID = kbAreaGroupGetIDByPosition(gIslandBaseLocation);
   
   // Query military units near the island base
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, gIslandBaseLocation, 200.0);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   
   if (numberFound < 1) {
      return;
   }
   
   // Check if we have an active assault or search plan
   bool hasActiveCombatPlan = (gIslandAssaultPlanID >= 0 && aiPlanGetActive(gIslandAssaultPlanID)) ||
                              (gIslandSearchPlanID >= 0 && aiPlanGetActive(gIslandSearchPlanID));
   
   // Check if we know where the enemy is
   int enemyBuildingId = getClosestIslandUnitByLocation(cUnitTypeBuilding, cPlayerRelationEnemyNotGaia, 
      cUnitStateABQ, gIslandBaseLocation, 2000);
   bool enemyKnown = (enemyBuildingId > 0);
   
   int unitsAssigned = 0;
   
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      vector unitLocation = kbUnitGetPosition(unitID);
      int unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
      
      // Skip heroes
      if (kbUnitIsType(unitID, cUnitTypeHero) == true) {
         continue;
      }
      
      // Verify unit is actually on the island
      if (kbAreAreaGroupsPassableByLand(islandBaseAreaGroupID, unitLocationGroupId) == false) {
         continue;
      }
      
      // Assign unit to the island base
      if (kbUnitGetBaseID(unitID) != gIslandBaseID) {
         int oldBase = kbUnitGetBaseID(unitID);
         if (oldBase >= 0) {
            kbBaseRemoveUnit(cMyID, oldBase, unitID);
         }
         kbBaseAddUnit(cMyID, gIslandBaseID, unitID);
      }
      
      // Check current plan
      int currentPlanID = kbUnitGetPlanID(unitID);
      
      // Skip if already in a good combat plan
      if (currentPlanID == gIslandAssaultPlanID || currentPlanID == gIslandSearchPlanID) {
         continue;
      }
      if (currentPlanID == gIslandBasePatrolPlan && hasActiveCombatPlan == false && enemyKnown == false) {
         continue;
      }
      
      // Check if unit is idle or in low-priority plan
      bool isIdle = (currentPlanID < 0) || (aiPlanGetActive(currentPlanID) == false);
      bool isLowPriority = (currentPlanID >= 0) && (aiPlanGetDesiredPriority(currentPlanID) < 60);
      
      if (isIdle == false && isLowPriority == false) {
         continue;
      }
      
      // Remove from current plan
      if (currentPlanID >= 0) {
         aiPlanRemoveUnit(currentPlanID, unitID);
      }
      
      // Assign to appropriate plan
      if (hasActiveCombatPlan) {
         // Add to existing combat plan
         if (gIslandAssaultPlanID >= 0 && aiPlanGetActive(gIslandAssaultPlanID)) {
            aiPlanAddUnit(gIslandAssaultPlanID, unitID);
            unitsAssigned++;
         } else if (gIslandSearchPlanID >= 0 && aiPlanGetActive(gIslandSearchPlanID)) {
            aiPlanAddUnit(gIslandSearchPlanID, unitID);
            unitsAssigned++;
         }
      } else if (enemyKnown) {
         // Enemy known but no active plan - create one or task directly
         vector enemyLocation = kbUnitGetPosition(enemyBuildingId);
         aiTaskUnitMove(unitID, enemyLocation);
         unitsAssigned++;
      } else {
         // No enemy known - assign to patrol plan
         if (gIslandBasePatrolPlan < 0 || aiPlanGetActive(gIslandBasePatrolPlan) == false) {
            createIslandBasePatrolPlan();
         }
         if (gIslandBasePatrolPlan >= 0) {
            aiPlanAddUnit(gIslandBasePatrolPlan, unitID);
            unitsAssigned++;
         }
      }
   }
   
   if (unitsAssigned > 0) {
      anwVerboseEcho("Managed " + unitsAssigned + " island base troops");
   }
}





