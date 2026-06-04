// New logic to be added in the future.
//==============================================================================
// getNearestAlliedIslandBase
// This function finds the nearest allied base on the same landmass.
//==============================================================================
vector getNearestAlliedIslandBase(vector origin = cInvalidVector)
{
   int nearestBaseID = kbFindClosestBase(cPlayerRelationAlly, origin);
   int originGroupId = kbAreaGroupGetIDByPosition(origin);
   
   if (nearestBaseID != -1)
   {
      vector baseCenterLocation = kbBaseGetLocation(cPlayerRelationAlly, nearestBaseID);
      int allyGroupId = kbAreaGroupGetIDByPosition(baseCenterLocation);
      if (kbAreAreaGroupsPassableByLand(originGroupId, allyGroupId) == true) {
        return baseCenterLocation;
      }
   }

   int townCenterQuery = createSimpleUnitQuery(cUnitTypeTownCenter, cPlayerRelationAlly, cUnitStateAlive);
   kbUnitQuerySetPosition(townCenterQuery, origin);
   kbUnitQuerySetMaximumDistance(townCenterQuery, 1200);
   kbUnitQuerySetAscendingSort(townCenterQuery, true);
   int numberTownCenters = kbUnitQueryExecute(townCenterQuery);

   if (numberTownCenters > 0)
   {
      int closestTownCenterID = kbUnitQueryGetResult(townCenterQuery, 0);
      vector townCenterLocation = kbUnitGetPosition(closestTownCenterID);
      int townCenterGroupId = kbAreaGroupGetIDByPosition(townCenterLocation);
      if (kbAreAreaGroupsPassableByLand(originGroupId, townCenterGroupId) == true) {
        return townCenterLocation;
      }
   }

   int buildingQuery = createSimpleUnitQuery(cUnitTypeBuilding, cPlayerRelationAlly, cUnitStateAlive);
   kbUnitQuerySetPosition(buildingQuery, origin);
   kbUnitQuerySetMaximumDistance(buildingQuery, 1200);
   kbUnitQuerySetAscendingSort(buildingQuery, true);
   int numberBuildings = kbUnitQueryExecute(buildingQuery);

   if (numberBuildings > 0)
   {
      int closestBuildingID = kbUnitQueryGetResult(buildingQuery, 0);
      vector buildingLocation = kbUnitGetPosition(closestBuildingID);
      int buildingGroupId = kbAreaGroupGetIDByPosition(buildingLocation);
      if (kbAreAreaGroupsPassableByLand(originGroupId, buildingGroupId) == true) {
        return buildingLocation;
      }
   }

   return origin;
}
//==============================================================================
// smallIslandMigration
// This logic helps maps like Ceylon function.
//==============================================================================
rule smallIslandMigration
inactive
minInterval 40
{
    vector myBaseLoc = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
    vector newBase = getRandomIslandToBuildOn();
    vector alliedBaseOnIsland = getNearestAlliedIslandBase(newBase);

    if (alliedBaseOnIsland != cInvalidVector) {
        newBase = alliedBaseOnIsland;
    }

    int currentNumDocks = kbUnitQueryExecute(createSimpleUnitQuery(gDockUnit, cMyID, 
    cUnitStateABQ, myBaseLoc, 100));
    int newBaseId = -1;
    if (tooManyBuildingsCheck() == true && currentNumDocks > 0) {
        createSettlementBase(newBase);
        newBaseId = kbBaseGetMainID(cMyID);
        kbBaseSetActive(cMyID, newBaseId, true);
        anwVerboseEcho("New Base Active Status: " + kbBaseGetActive(cMyID, newBaseId) + "!");
        gGatherPlansUpdated = false;
    }
}