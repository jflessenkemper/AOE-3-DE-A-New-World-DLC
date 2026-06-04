//==============================================================================
// tooManyBuildingsCheck
// This function will tell us if we have sufficient space to continue building.
//==============================================================================
bool tooManyBuildingsCheck(vector currentLocation = cInvalidVector)
{
    int currentLocationGroupId = kbAreaGroupGetIDByPosition(currentLocation);
    int currentNumBuildings = getUnitCountByAreaGroups(cUnitTypeBuilding, cPlayerRelationAny, cUnitStateABQ, currentLocation);
    int areaCount = kbAreaGroupGetNumberAreas(currentLocationGroupId);

    if (currentNumBuildings > 3 * areaCount)
    {
        return true;
    }
    return false;
}
//==============================================================================
// archipelagoGo
// Check if we need to island hop due to space and other conditions.
//==============================================================================
rule archipelagoGo
inactive
minInterval 10
{
    vector myBaseLoc = kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID));
    vector newBase = getRandomIslandToBuildOn();
    int newBaseId = -1;
    int myBaseAreaID = kbAreaGetIDByPosition(myBaseLoc);
    int myBaseAreaGroupID = kbAreaGroupGetIDByPosition(myBaseLoc);

    // Check if the main base has too many buildings...
    bool isOvercrowded = tooManyBuildingsCheck(myBaseLoc);

    // Move main base if so, so we do not overcrowd it...
    if (isOvercrowded == true && gVillagersTransportPlanID == -1 && newBase != cInvalidVector) {
        // Create the transport plan...
        if (gVillagersTransportPlanID == -1) {
            gVillagersTransportPlanID = createColonizationTransportPlan(kbBaseGetMilitaryGatherPoint(cMyID, 
            kbBaseGetMainID(cMyID)), newBase, 100, false);
        }
        addUnitsToTransportPlan(gVillagersTransportPlanID, myBaseLoc);
        aiPlanSetActive(gVillagersTransportPlanID, true);
        createSettlementBase(newBase);
        newBaseId = kbBaseGetMainID(cMyID);
        kbBaseSetActive(cMyID, newBaseId, true);
        anwVerboseEcho("New Base Active Status: " + kbBaseGetActive(cMyID, newBaseId) + "!");
        //sendStatement(1, cAICommPromptToAllyConfirm, newBase);
        gGatherPlansUpdated = false;
    }

    // It's time to Archipelago-Go!
    int availableUnits = createSimpleUnitQuery(gEconUnit, cMyID, cUnitStateAlive, 
    kbBaseGetLocation(cMyID, kbBaseGetMainID(cMyID)), 150.0);
        anwVerboseEcho("Waiting to add more gather plans... Is Overcrowded: " +isOvercrowded+ 
        "Available Villagers: " +availableUnits+ "Gather Plans Updated: " +gGatherPlansUpdated+ "");
    if (availableUnits > 0 && gGatherPlansUpdated == false) {
        int numberOfBases = kbBaseGetNumber(cMyID);
        float newBasePercentage = (1.0 / numberOfBases) * 100.0;
        anwVerboseEcho("Second check. Is Overcrowded: " +isOvercrowded+ "Available Villagers: " +availableUnits+ "");
        for (i = 0; < numberOfBases)
        {
            int currentBaseId = kbBaseGetIDByIndex(cMyID, i);
            vector currentBaseLoc = kbBaseGetLocation(cMyID, currentBaseId);
            // Create gather plans at the base.
            createGatherPlan(currentBaseLoc, currentBaseId, cResourceFood, 95);
            createGatherPlan(currentBaseLoc, currentBaseId, cResourceWood, 95);
            createGatherPlan(currentBaseLoc, currentBaseId, cResourceGold, 95);
            anwVerboseEcho("Base Gather Info: " + currentBaseId + "");
            //sendStatement(1, cAICommPromptToAllyConfirm, currentBaseLoc);
        }
        createSimpleBuildPlan(cUnitTypeTownCenter, 1, 99, true, cEconomyEscrowID, kbBaseGetMainID(cMyID), 1, -1, true);
        gVillagersTransportPlanID = -1;
        gGatherPlansUpdated = true;
    }
}