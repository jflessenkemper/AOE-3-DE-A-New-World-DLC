//==============================================================================
// createColonizationTransportPlan
//==============================================================================
int createColonizationTransportPlan(vector gatherPoint = cInvalidVector, vector targetPoint = cInvalidVector,
                        int pri = 95, bool returnWhenDone = false)
{
   int shipQueryID = createSimpleUnitQuery(cUnitTypeTransport, cMyID, cUnitStateAlive);
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
   anwVerboseEcho("Ships: "+numberFound+"");
   for (i = 0; < numberFound)
   {
      shipID = kbUnitQueryGetResult(shipQueryID, i);
      unitPlanID = kbUnitGetPlanID(shipID);
      if ((unitPlanID >= 0) && ((aiPlanGetDesiredPriority(unitPlanID) > pri) || (aiPlanGetType(unitPlanID) == cPlanTransport)))
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

   int planID = aiPlanCreate(kbGetUnitTypeName(kbUnitGetProtoUnitID(transportID)) + " Colonization Transport Plan, ", cPlanTransport);

   if (planID < 0)
   {
      return (-1);
   }

   aiPlanSetVariableInt(planID, cTransportPlanTransportID, 0, transportID);
   aiPlanSetVariableInt(planID, cTransportPlanTransportTypeID, 0, kbUnitGetProtoUnitID(transportID));
   // We must add the transport unit otherwise other plans might try to use this unit...
   aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(transportID), 1, 1, 1);
   if (aiPlanAddUnit(planID, transportID) == false)
   {
      aiPlanDestroy(planID);
      return (-1);
   }

    aiPlanSetVariableVector(planID, cTransportPlanGatherPoint, 0, gatherPoint);
    aiPlanSetVariableVector(planID, cTransportPlanTargetPoint, 0, targetPoint);
    aiPlanSetVariableBool(planID, cTransportPlanReturnWhenDone, 0, returnWhenDone);
    aiPlanSetVariableBool(planID, cTransportPlanPersistent, 0, false);
    aiPlanSetVariableBool(planID, cTransportPlanMaximizeXportMovement, 0, true);
    aiPlanSetVariableBool(planID, cTransportPlanPersistent, 0, false);
    aiPlanSetVariableBool(planID, cTransportPlanTakeMoreUnits, 0, false);
    aiPlanSetNoMoreUnits(planID, true);
    //aiPlanSetVariableBool(planID, cTransportPlanReturnWhenDone, 3, false);
    aiPlanSetAttack(planID, true);
    aiPlanSetRequiresAllNeedUnits(planID, true);
    aiPlanSetVariableInt(planID, cTransportPlanPathType, 0, cTransportPathTypePoints);
    aiPlanSetDesiredPriority(planID, pri);

   return (planID);
}
//==============================================================================
// addUnitsToTransportPlan
//==============================================================================
void addUnitsToTransportPlan(int transportPlanId = -1, vector originLocation = cInvalidVector) {
    int unitQueryID = createSimpleUnitQuery(cUnitTypeAbstractVillager, cMyID, cUnitStateAlive, originLocation, 150.0);
    int numberFound = kbUnitQueryExecute(unitQueryID);
    int unitID = -1;
    vector unitLocation = cInvalidVector;
    int unitLocationId = -1;
    int unitLocationGroupId = -1;

    aiPlanAddUnitType(transportPlanId, cUnitTypeAbstractVillager, 1, 2, 4);

    for (i = 0; < 4)
    {
        unitID = kbUnitQueryGetResult(unitQueryID, i);
        unitLocation = kbUnitGetPosition(unitID);
        unitLocationId = kbAreaGetIDByPosition(unitLocation);
        unitLocationGroupId = kbAreaGroupGetIDByPosition(unitLocation);
        if (kbAreAreaGroupsPassableByLand(kbAreaGroupGetIDByPosition(originLocation), unitLocationGroupId) == true) {
            kbBaseRemoveUnit(cMyID, kbBaseGetMainID(cMyID), unitID);
            // kbBaseAddUnit(cMyID, gVillagersIslandBaseId, unitID);
            aiPlanAddUnit(transportPlanId, unitID);
        }
    }
}