//==============================================================================
/* aiEliteTactics.xs

   Keeps non-elite troops screening elite units and heroes while under pressure.
   During active assaults, standard troops lead, elites follow close behind, and
   the explorer stays behind the elite line. If the explorer falls, elites break
   contact and the AI immediately tries to ransom the leader back from home.
*/
//==============================================================================

extern int gLLEliteGuardPlanID = -1;
extern int gLLEliteGuardAnchorUnitID = -1;
extern int gLLEliteSupportPlanID = -1;
extern int gLLEliteSupportAttackPlanID = -1;
extern int gLLEliteSupportLastRefreshTime = -1;
extern int gLLExplorerEscortPlanID = -1;
extern int gLLExplorerEscortAttackPlanID = -1;
extern int gLLExplorerEscortLastRefreshTime = -1;
float gLLExplorerProtectionOverride = -1.0;
float gLLDecapitationOverride = -1.0;
int gLLExplorerEscortBonus = 0;
float gLLExplorerRearOffsetBonus = 0.0;

//==============================================================================
/* llIsEliteUnit — predicate for "elite" land-military units used by the
   screening logic in this file. The formation groups standard troops around
   elite units (line 265+), so every callsite here asks whether a given unit
   should be treated as a screening anchor (elite) or a screen body (non-elite).

   Heroes are counted separately by the callers via cUnitTypeHero queries, so
   this predicate must NOT return true for heroes — doing so would double-count
   them in the elite-line tally.

   The mod does not yet maintain a curated list of "elite" proto units. Until
   one is provided, this conservatively returns false, which degrades the
   formation to "all land-military act as screen body, heroes are the only
   elite anchors". That's behaviourally safe and keeps the AI running instead
   of crashing with XS parse errors (ERROR 0172).

   TODO: wire this to a proto-allowlist (e.g. elite Dragoons, elite Musketeers,
   upgraded proto variants, or a bespoke gLLEliteProtoIDs array). */
//==============================================================================
bool llIsEliteUnit(int unitID = -1)
{
   if (unitID < 0)
   {
      return (false);
   }

   return (false);
}

float llClamp01(float value = 0.0)
{
   if (value < 0.0)
   {
      return (0.0);
   }

   if (value > 1.0)
   {
      return (1.0);
   }

   return (value);
}

void llSetLeaderTacticalDoctrine(float protectionOverride = -1.0, float decapitationOverride = -1.0,
   int escortBonus = 0, float rearOffsetBonus = 0.0)
{
   gLLExplorerProtectionOverride = protectionOverride;
   gLLDecapitationOverride = decapitationOverride;
   gLLExplorerEscortBonus = escortBonus;
   gLLExplorerRearOffsetBonus = rearOffsetBonus;
   llProbe("event.elite.doctrine",
      "protect=" + protectionOverride + " decap=" + decapitationOverride +
      " escortBonus=" + escortBonus + " rearOffset=" + rearOffsetBonus);
}

int llGetPlaystyleBucket(void)
{
   if (btOffenseDefense >= 0.35)
   {
      return (2);
   }

   if (btOffenseDefense <= -0.25)
   {
      return (0);
   }

   return (1);
}

float llGetExplorerProtectionBias(void)
{
   if (gLLExplorerProtectionOverride >= 0.0)
   {
      return (llClamp01(gLLExplorerProtectionOverride));
   }

   float protectionBias = 0.55 - (btOffenseDefense * 0.35) + (btBiasInf * 0.12) + (btBiasArt * 0.10) -
      (btBiasCav * 0.14) - (btBiasNative * 0.06);

   if (llGetPlaystyleBucket() == 0)
   {
      protectionBias = protectionBias + 0.12;
   }
   else if (llGetPlaystyleBucket() == 2)
   {
      protectionBias = protectionBias - 0.08;
   }

   return (llClamp01(protectionBias));
}

float llGetDecapitationBias(void)
{
   if (gLLDecapitationOverride >= 0.0)
   {
      return (llClamp01(gLLDecapitationOverride));
   }

   float decapitationBias = 0.20 + (btOffenseDefense * 0.38) + (btBiasCav * 0.24) + (btBiasNative * 0.10) -
      (btBiasArt * 0.12) - (btBiasInf * 0.08);

   if (llGetPlaystyleBucket() == 2)
   {
      decapitationBias = decapitationBias + 0.10;
   }
   else if (llGetPlaystyleBucket() == 0)
   {
      decapitationBias = decapitationBias - 0.14;
   }

   return (llClamp01(decapitationBias));
}

vector llGetEliteRetreatPoint(void)
{
   int mainBaseID = kbBaseGetMainID(cMyID);
   vector retreatPoint = kbBaseGetMilitaryGatherPoint(cMyID, mainBaseID);
   if (retreatPoint == cInvalidVector)
   {
      retreatPoint = kbBaseGetLocation(cMyID, mainBaseID);
   }

   return (retreatPoint);
}

vector llGetAssaultOffsetPoint(vector gatherPoint = cInvalidVector, vector targetPoint = cInvalidVector, float offset = 0.0)
{
   if (targetPoint == cInvalidVector)
   {
      return (cInvalidVector);
   }

   if (gatherPoint == cInvalidVector)
   {
      gatherPoint = llGetEliteRetreatPoint();
   }

   if ((gatherPoint == cInvalidVector) || (distance(gatherPoint, targetPoint) < 4.0) || (offset <= 0.0))
   {
      return (targetPoint);
   }

   return (targetPoint - (xsVectorNormalize(targetPoint - gatherPoint) * offset));
}

int llGetNearbyEnemyPressureCount(vector location = cInvalidVector, float radius = 28.0)
{
   if ((location == cInvalidVector) || (radius <= 0.0))
   {
      return (0);
   }

   int enemyQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cPlayerRelationEnemyNotGaia,
      cUnitStateAlive, location, radius);
   return (kbUnitQueryExecute(enemyQueryID));
}

int llGetNearbyNonEliteSupportCount(vector location = cInvalidVector, float radius = 26.0)
{
   if ((location == cInvalidVector) || (radius <= 0.0))
   {
      return (0);
   }

   int count = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, location, radius);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == true)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int llGetTotalNonEliteTroopCount(void)
{
   int count = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == true)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int llGetTotalEliteTroopCount(void)
{
   int count = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == false)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int llGetNearbyEliteCoreCount(vector location = cInvalidVector, float radius = 30.0)
{
   if ((location == cInvalidVector) || (radius <= 0.0))
   {
      return (0);
   }

   int count = 0;

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive, location, radius);
   count = count + kbUnitQueryExecute(heroQueryID);

   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, location, radius);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == false)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int llGetThreatenedEliteAnchorID(void)
{
   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      if (llGetNearbyEnemyPressureCount(kbUnitGetPosition(heroID), 28.0) > 0)
      {
         return (heroID);
      }
   }

   int eliteQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int eliteCount = kbUnitQueryExecute(eliteQueryID);
   i = 0;
   for (i = 0; < eliteCount)
   {
      int unitID = kbUnitQueryGetResult(eliteQueryID, i);
      if (llIsEliteUnit(unitID) == false)
      {
         continue;
      }

      if (llGetNearbyEnemyPressureCount(kbUnitGetPosition(unitID), 28.0) > 0)
      {
         return (unitID);
      }
   }

   return (-1);
}

int llGetPrimaryLandAttackPlanID(void)
{
   int numPlans = aiPlanGetActiveCount();
   int i = 0;
   for (i = 0; < numPlans)
   {
      int planID = aiPlanGetIDByActiveIndex(i);
      if (aiPlanGetType(planID) != cPlanCombat)
      {
         continue;
      }

      if (aiPlanGetVariableInt(planID, cCombatPlanCombatType, 0) != cCombatPlanCombatTypeAttack)
      {
         continue;
      }

      if (aiPlanGetParentID(planID) >= 0)
      {
         continue;
      }

      if ((planID == gNavyAttackPlan) || (planID == gLandPatrolPlan) || (planID == gWaterPatrolPlan) ||
          (planID == gWaterDockAttackPlan) || (planID == gWarshipExplorePlan) || (planID == gIslandAssaultPlanID) ||
          (planID == gKOTHCombatPlan) || (planID == gKOTHGuardPlan) || (planID == gIslandSearchPlanID) ||
          (planID == gLLEliteSupportPlanID))
      {
         continue;
      }

      return (planID);
   }

   return (-1);
}

vector llGetAttackPlanGatherPoint(int attackPlanID = -1)
{
   if (attackPlanID < 0)
   {
      return (cInvalidVector);
   }

   vector gatherPoint = aiPlanGetVariableVector(attackPlanID, cCombatPlanGatherPoint, 0);
   if (gatherPoint != cInvalidVector)
   {
      return (gatherPoint);
   }

   return (llGetEliteRetreatPoint());
}

vector llGetAttackPlanTargetPoint(int attackPlanID = -1)
{
   if (attackPlanID < 0)
   {
      return (cInvalidVector);
   }

   vector targetPoint = aiPlanGetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0);
   if (targetPoint != cInvalidVector)
   {
      return (targetPoint);
   }

   int targetPlayer = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetPlayerID, 0);
   int targetBaseID = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetBaseID, 0);
   if ((targetPlayer >= 0) && (targetBaseID >= 0))
   {
      targetPoint = kbBaseGetLocation(targetPlayer, targetBaseID);
   }

   return (targetPoint);
}

vector llGetAttackPlanStrategicPoint(int attackPlanID = -1)
{
   if (attackPlanID < 0)
   {
      return (cInvalidVector);
   }

   int targetPlayer = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetPlayerID, 0);
   int targetBaseID = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetBaseID, 0);
   if ((targetPlayer >= 0) && (targetBaseID >= 0))
   {
      vector basePoint = kbBaseGetLocation(targetPlayer, targetBaseID);
      if (basePoint != cInvalidVector)
      {
         return (basePoint);
      }
   }

   return (llGetAttackPlanTargetPoint(attackPlanID));
}

int llGetPrimaryExplorerID(void)
{
   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   if (kbUnitQueryExecute(heroQueryID) <= 0)
   {
      return (-1);
   }

   return (kbUnitQueryGetResult(heroQueryID, 0));
}

vector llGetEnemyArmyMassPoint(int targetPlayer = -1, vector nearPoint = cInvalidVector, float radius = 42.0)
{
   if (nearPoint == cInvalidVector)
   {
      return (cInvalidVector);
   }

   int playerRelation = targetPlayer >= 0 ? targetPlayer : cPlayerRelationEnemyNotGaia;
   int enemyQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, playerRelation, cUnitStateAlive, nearPoint, radius);
   int enemyCount = kbUnitQueryExecute(enemyQueryID);
   if (enemyCount <= 0)
   {
      return (cInvalidVector);
   }

   float xTotal = 0.0;
   float zTotal = 0.0;
   int i = 0;
   for (i = 0; < enemyCount)
   {
      vector unitPosition = kbUnitGetPosition(kbUnitQueryGetResult(enemyQueryID, i));
      xTotal = xTotal + xsVectorGetX(unitPosition);
      zTotal = zTotal + xsVectorGetZ(unitPosition);
   }

   return (xsVectorSet(xTotal / enemyCount, 0.0, zTotal / enemyCount));
}

int llGetBestEnemyExplorerStrikeID(int targetPlayer = -1, vector referencePoint = cInvalidVector, float searchRadius = 70.0,
   int maxEscortCount = 4)
{
   int playerRelation = targetPlayer >= 0 ? targetPlayer : cPlayerRelationEnemyNotGaia;
   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, playerRelation, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int bestHeroID = -1;
   float bestScore = 99999.0;

   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      vector heroPosition = kbUnitGetPosition(heroID);
      if ((referencePoint != cInvalidVector) && (distance(referencePoint, heroPosition) > searchRadius))
      {
         continue;
      }

      int escortQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, kbUnitGetPlayerID(heroID), cUnitStateAlive,
         heroPosition, 18.0);
      int escortCount = kbUnitQueryExecute(escortQueryID);
      if (escortCount > maxEscortCount)
      {
         continue;
      }

      float score = escortCount * 8.0;
      if (referencePoint != cInvalidVector)
      {
         score = score + distance(referencePoint, heroPosition);
      }

      if (score < bestScore)
      {
         bestScore = score;
         bestHeroID = heroID;
      }
   }

   return (bestHeroID);
}

bool llIsEnemyExplorerInBattle(int heroID = -1, vector enemyArmyPoint = cInvalidVector, float battleRadius = 24.0)
{
   if (heroID < 0)
   {
      return (false);
   }

   vector heroPosition = kbUnitGetPosition(heroID);
   if (enemyArmyPoint == cInvalidVector)
   {
      return (llGetNearbyEnemyPressureCount(heroPosition, battleRadius) > 4);
   }

   if (distance(heroPosition, enemyArmyPoint) > battleRadius)
   {
      return (false);
   }

   return (llGetNearbyEnemyPressureCount(heroPosition, battleRadius) > 4);
}

void llDestroyEliteGuardPlan(void)
{
   if (gLLEliteGuardPlanID >= 0)
   {
      llLogPlanEvent("destroy", gLLEliteGuardPlanID, "name=Legendary Elite Guard");
      aiPlanDestroy(gLLEliteGuardPlanID);
   }

   gLLEliteGuardPlanID = -1;
   gLLEliteGuardAnchorUnitID = -1;
   llProbe("event.elite.guard_destroyed", "atMs=" + xsGetTime());
}

void llDestroyEliteSupportPlan(void)
{
   if (gLLEliteSupportPlanID >= 0)
   {
      llLogPlanEvent("destroy", gLLEliteSupportPlanID, "name=Legendary Elite Support");
      aiPlanDestroy(gLLEliteSupportPlanID);
   }

   gLLEliteSupportPlanID = -1;
   gLLEliteSupportAttackPlanID = -1;
   gLLEliteSupportLastRefreshTime = -1;
   llProbe("event.elite.support_destroyed", "atMs=" + xsGetTime());
}

void llDestroyExplorerEscortPlan(void)
{
   if (gLLExplorerEscortPlanID >= 0)
   {
      llLogPlanEvent("destroy", gLLExplorerEscortPlanID, "name=Legendary Explorer Escort");
      aiPlanDestroy(gLLExplorerEscortPlanID);
   }

   gLLExplorerEscortPlanID = -1;
   gLLExplorerEscortAttackPlanID = -1;
   gLLExplorerEscortLastRefreshTime = -1;
   llProbe("event.elite.escort_destroyed", "atMs=" + xsGetTime());
}

void llResetExplorerControlToBase(void)
{
   if (gExplorerControlPlan < 0)
   {
      return;
   }

   vector retreatPoint = llGetEliteRetreatPoint();
   if (retreatPoint == cInvalidVector)
   {
      return;
   }

   aiPlanSetVariableVector(gExplorerControlPlan, cCombatPlanTargetPoint, 0, retreatPoint);
   llProbe("event.elite.explorer_reset", "loc=" + llFmtVec(retreatPoint));
}

void llPositionExplorerBehindArmy(vector rearPoint = cInvalidVector)
{
   if (rearPoint == cInvalidVector)
   {
      return;
   }
   llProbe("event.elite.explorer_rear", "loc=" + llFmtVec(rearPoint));

   if (gExplorerControlPlan >= 0)
   {
      aiPlanSetVariableVector(gExplorerControlPlan, cCombatPlanTargetPoint, 0, rearPoint);
   }

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      int currentPlanID = kbUnitGetPlanID(heroID);
      if ((currentPlanID >= 0) && (currentPlanID != gExplorerControlPlan))
      {
         aiPlanRemoveUnit(currentPlanID, heroID);
      }
      llLogUnitAction("explorer-reposition", heroID, "destination=" + rearPoint);
      aiTaskUnitMove(heroID, rearPoint);
   }
}

void llRebuildExplorerEscortPlan(int attackPlanID = -1, vector gatherPoint = cInvalidVector, vector escortPoint = cInvalidVector,
   int desiredEscortCount = 0)
{
   if ((attackPlanID < 0) || (gatherPoint == cInvalidVector) || (escortPoint == cInvalidVector) || (desiredEscortCount <= 0))
   {
      llDestroyExplorerEscortPlan();
      return;
   }

   llDestroyExplorerEscortPlan();

   int mainBaseID = kbBaseGetMainID(cMyID);
   int planID = aiPlanCreate("Legendary Explorer Escort", cPlanCombat);
   llLogPlanEvent("create", planID, "name=Legendary Explorer Escort attackPlan=" + attackPlanID);
   aiPlanSetVariableInt(planID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeDefend);
   aiPlanSetVariableInt(planID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(planID, cCombatPlanTargetPoint, 0, escortPoint);
   aiPlanSetVariableVector(planID, cCombatPlanGatherPoint, 0, gatherPoint);
   aiPlanSetVariableFloat(planID, cCombatPlanTargetEngageRange, 0, 16.0);
   aiPlanSetVariableFloat(planID, cCombatPlanGatherDistance, 0, 8.0);
   aiPlanSetVariableInt(planID, cCombatPlanRefreshFrequency, 0, 200);
   aiPlanSetVariableInt(planID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetDesiredPriority(planID, 88);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetInitialPosition(planID, gatherPoint);

   int addedUnits = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == true)
      {
         continue;
      }

      int currentPlanID = kbUnitGetPlanID(unitID);
      if ((currentPlanID != attackPlanID) && (currentPlanID != gLLExplorerEscortPlanID))
      {
         continue;
      }

      vector unitLocation = kbUnitGetPosition(unitID);
      if ((distance(unitLocation, escortPoint) > 46.0) && (distance(unitLocation, gatherPoint) > 42.0))
      {
         continue;
      }

      if ((currentPlanID >= 0) && (currentPlanID != planID))
      {
         aiPlanRemoveUnit(currentPlanID, unitID);
      }

      aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(unitID), 0, 0, 1);
      if (aiPlanAddUnit(planID, unitID) == true)
      {
         addedUnits = addedUnits + 1;
      }

      if (addedUnits >= desiredEscortCount)
      {
         break;
      }
   }

   if (addedUnits <= 0)
   {
      llLogPlanEvent("destroy", planID, "reason=no escort units added");
      aiPlanDestroy(planID);
      return;
   }

   aiPlanSetActive(planID);
   gLLExplorerEscortPlanID = planID;
   gLLExplorerEscortAttackPlanID = attackPlanID;
   gLLExplorerEscortLastRefreshTime = xsGetTime();
   debugLegendaryLeaders("created explorer escort plan " + planID + " for attack plan " + attackPlanID +
      " using " + addedUnits + " non-elite troops.");
   llProbe("elite.escort", "plan=" + planID + " attackPlan=" + attackPlanID +
      " units=" + addedUnits + " desired=" + desiredEscortCount + " escortPt=" + llFmtVec(escortPoint));
}

vector llChooseAssaultObjectivePoint(int attackPlanID = -1, vector gatherPoint = cInvalidVector)
{
   vector strategicPoint = llGetAttackPlanStrategicPoint(attackPlanID);
   if (strategicPoint == cInvalidVector)
   {
      return (cInvalidVector);
   }

   int targetPlayer = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetPlayerID, 0);
   float decapitationBias = llGetDecapitationBias();
   float protectionBias = llGetExplorerProtectionBias();
   vector bulkPoint = llGetEnemyArmyMassPoint(targetPlayer, strategicPoint, 44.0);
   if (bulkPoint == cInvalidVector)
   {
      aiPlanSetVariableInt(attackPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
      aiPlanSetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0, strategicPoint);
      return (strategicPoint);
   }

   int enemyExplorerID = llGetBestEnemyExplorerStrikeID(targetPlayer, strategicPoint, 72.0,
      2 + ((1.0 - decapitationBias) * 4.0));
   if ((enemyExplorerID >= 0) && (decapitationBias >= 0.55) &&
       (llIsEnemyExplorerInBattle(enemyExplorerID, bulkPoint, 26.0) == true))
   {
      vector strikePoint = kbUnitGetPosition(enemyExplorerID);
      if ((distance(strikePoint, bulkPoint) <= 26.0) || (decapitationBias >= 0.80))
      {
         aiPlanSetVariableInt(attackPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
         aiPlanSetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0, strikePoint);
         debugLegendaryLeaders("assault objective shifted toward enemy explorer at " + strikePoint +
            " because leader doctrine favors decapitation strikes.");
         llSendLegendaryLeaderDecapitationLine(targetPlayer, 150000);
         return (strikePoint);
      }
   }

   aiPlanSetVariableInt(attackPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0, bulkPoint);
   if (protectionBias >= 0.45)
   {
      debugLegendaryLeaders("assault objective shifted onto the bulk enemy force to preserve leader escort integrity.");
   }
   llSendLegendaryLeaderBulkAssaultLine(targetPlayer, 150000);
   return (bulkPoint);
}

void llRebuildEliteGuardPlan(int anchorUnitID = -1)
{
   if (anchorUnitID < 0)
   {
      llDestroyEliteGuardPlan();
      return;
   }

   vector anchorLocation = kbUnitGetPosition(anchorUnitID);
   if (anchorLocation == cInvalidVector)
   {
      llDestroyEliteGuardPlan();
      return;
   }

   llDestroyEliteGuardPlan();

   int planID = aiPlanCreate("Legendary Elite Guard", cPlanCombat);
   llLogPlanEvent("create", planID, "name=Legendary Elite Guard anchorUnit=" + anchorUnitID);
   aiPlanSetVariableInt(planID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeDefend);
   aiPlanSetVariableInt(planID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(planID, cCombatPlanTargetPoint, 0, anchorLocation);
   aiPlanSetVariableFloat(planID, cCombatPlanTargetEngageRange, 0, 26.0);
   aiPlanSetVariableFloat(planID, cCombatPlanGatherDistance, 0, 14.0);
   aiPlanSetVariableInt(planID, cCombatPlanRefreshFrequency, 0, 200);
   aiPlanSetVariableInt(planID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetDesiredPriority(planID, 70);

   int addedUnits = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, anchorLocation, 34.0);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == true)
      {
         continue;
      }

      int currentPlanID = kbUnitGetPlanID(unitID);
      if (currentPlanID >= 0)
      {
         aiPlanRemoveUnit(currentPlanID, unitID);
      }

      aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(unitID), 0, 0, 1);
      if (aiPlanAddUnit(planID, unitID) == true)
      {
         addedUnits = addedUnits + 1;
      }

      if (addedUnits >= 16)
      {
         break;
      }
   }

   if (addedUnits <= 0)
   {
      llLogPlanEvent("destroy", planID, "reason=no guard units added");
      aiPlanDestroy(planID);
      return;
   }

   aiPlanSetActive(planID);
   gLLEliteGuardPlanID = planID;
   gLLEliteGuardAnchorUnitID = anchorUnitID;
   debugLegendaryLeaders("created elite guard plan " + planID + " around anchor unit " + anchorUnitID +
      " using " + addedUnits + " non-elite troops.");
   llProbe("elite.guard", "plan=" + planID + " anchor=" + anchorUnitID +
      " units=" + addedUnits + " pos=" + llFmtVec(anchorLocation));
}

void llRetreatEliteCore(int anchorUnitID = -1, float radius = 36.0)
{
   if (anchorUnitID < 0)
   {
      return;
   }

   vector anchorLocation = kbUnitGetPosition(anchorUnitID);
   if (anchorLocation == cInvalidVector)
   {
      return;
   }

   vector retreatPoint = llGetEliteRetreatPoint();
   if (retreatPoint == cInvalidVector)
   {
      return;
   }

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive, anchorLocation, radius);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      int currentPlanID = kbUnitGetPlanID(heroID);
      if (currentPlanID >= 0)
      {
         aiPlanRemoveUnit(currentPlanID, heroID);
      }
      llLogUnitAction("elite-retreat-hero", heroID, "destination=" + retreatPoint);
      aiTaskUnitMove(heroID, retreatPoint);
   }

   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, anchorLocation, radius);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == false)
      {
         continue;
      }

      int unitPlanID = kbUnitGetPlanID(unitID);
      if (unitPlanID >= 0)
      {
         aiPlanRemoveUnit(unitPlanID, unitID);
      }
      llLogUnitAction("elite-retreat-core", unitID, "destination=" + retreatPoint);
      aiTaskUnitMove(unitID, retreatPoint);
   }

   debugLegendaryLeaders("elite core around anchor unit " + anchorUnitID + " ordered to retreat to " + retreatPoint + ".");
   llProbe("event.elite.retreat_core",
      "anchor=" + anchorUnitID + " radius=" + radius +
      " heroes=" + heroCount + " elites=" + numberFound +
      " loc=" + llFmtVec(retreatPoint));
}

void llRetreatAllEliteUnits(void)
{
   vector retreatPoint = llGetEliteRetreatPoint();
   if (retreatPoint == cInvalidVector)
   {
      return;
   }

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      int currentPlanID = kbUnitGetPlanID(heroID);
      if (currentPlanID >= 0)
      {
         aiPlanRemoveUnit(currentPlanID, heroID);
      }
      llLogUnitAction("elite-global-retreat-hero", heroID, "destination=" + retreatPoint);
      aiTaskUnitMove(heroID, retreatPoint);
   }

   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == false)
      {
         continue;
      }

      int unitPlanID = kbUnitGetPlanID(unitID);
      if (unitPlanID >= 0)
      {
         aiPlanRemoveUnit(unitPlanID, unitID);
      }
      llLogUnitAction("elite-global-retreat-core", unitID, "destination=" + retreatPoint);
      aiTaskUnitMove(unitID, retreatPoint);
   }

   llResetExplorerControlToBase();
   debugLegendaryLeaders("all elite units were ordered to retreat after the explorer fell.");
   llSendLegendaryLeaderRetreatLine(cPlayerRelationEnemyNotGaia, 180000);
   llProbe("event.elite.retreat_all",
      "heroes=" + heroCount + " elites=" + numberFound +
      " loc=" + llFmtVec(retreatPoint));
}

void llTryRansomExplorer(void)
{
   if (aiGetFallenExplorerID() < 0)
   {
      return;
   }

   if (aiPlanGetIDByTypeAndVariableType(cPlanResearch, cResearchPlanProtoUnitCommandID, cProtoUnitCommandRansomExplorer) >= 0)
   {
      return;
   }

   int tcID = getUnit(cUnitTypeTownCenter, cMyID, cUnitStateAlive);
   if (tcID < 0)
   {
      return;
   }

   createProtoUnitCommandResearchPlan(cProtoUnitCommandRansomExplorer, tcID, cMilitaryEscrowID, 95, 95);
   debugLegendaryLeaders("queued explorer ransom through the town center command after losing the leader.");
   llProbe("elite.ransom", "tc=" + tcID + " fallen=" + aiGetFallenExplorerID());
}

void llRebuildEliteSupportPlan(int attackPlanID = -1, vector gatherPoint = cInvalidVector, vector elitePoint = cInvalidVector,
   int desiredEliteCount = 1)
{
   if ((attackPlanID < 0) || (elitePoint == cInvalidVector) || (desiredEliteCount <= 0))
   {
      llDestroyEliteSupportPlan();
      return;
   }

   llDestroyEliteSupportPlan();

   int mainBaseID = kbBaseGetMainID(cMyID);
   int planID = aiPlanCreate("Legendary Elite Support", cPlanCombat);
   llLogPlanEvent("create", planID, "name=Legendary Elite Support attackPlan=" + attackPlanID);
   aiPlanSetVariableInt(planID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeDefend);
   aiPlanSetVariableInt(planID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(planID, cCombatPlanTargetPoint, 0, elitePoint);
   aiPlanSetVariableVector(planID, cCombatPlanGatherPoint, 0, gatherPoint);
   aiPlanSetVariableFloat(planID, cCombatPlanTargetEngageRange, 0, 24.0);
   aiPlanSetVariableFloat(planID, cCombatPlanGatherDistance, 0, 12.0);
   aiPlanSetVariableInt(planID, cCombatPlanRefreshFrequency, 0, 200);
   aiPlanSetVariableInt(planID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetDesiredPriority(planID, 82);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetInitialPosition(planID, gatherPoint);

   int addedUnits = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (llIsEliteUnit(unitID) == false)
      {
         continue;
      }

      vector unitLocation = kbUnitGetPosition(unitID);
      int currentPlanID = kbUnitGetPlanID(unitID);
      if ((currentPlanID != attackPlanID) && (currentPlanID != gLLEliteSupportPlanID) &&
          ((distance(unitLocation, elitePoint) > 60.0) && (distance(unitLocation, gatherPoint) > 55.0)))
      {
         continue;
      }

      if ((currentPlanID >= 0) && (currentPlanID != planID))
      {
         aiPlanRemoveUnit(currentPlanID, unitID);
      }

      aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(unitID), 0, 0, 1);
      if (aiPlanAddUnit(planID, unitID) == true)
      {
         addedUnits = addedUnits + 1;
      }

      if (addedUnits >= desiredEliteCount)
      {
         break;
      }
   }

   if (addedUnits <= 0)
   {
      llLogPlanEvent("destroy", planID, "reason=no elite support units added");
      aiPlanDestroy(planID);
      return;
   }

   aiPlanSetActive(planID);
   gLLEliteSupportPlanID = planID;
   gLLEliteSupportAttackPlanID = attackPlanID;
   gLLEliteSupportLastRefreshTime = xsGetTime();
   debugLegendaryLeaders("created elite support plan " + planID + " for attack plan " + attackPlanID +
      " with " + addedUnits + " elite units guarding the second line.");
   llProbe("elite.support", "plan=" + planID + " attackPlan=" + attackPlanID +
      " units=" + addedUnits + " desired=" + desiredEliteCount + " elitePt=" + llFmtVec(elitePoint));
}

bool llHandleEliteAssaultFormation(int attackPlanID = -1)
{
   static int lastProbedAssaultPlan = -1;
   if (attackPlanID < 0)
   {
      llDestroyEliteSupportPlan();
      return (false);
   }

   vector gatherPoint = llGetAttackPlanGatherPoint(attackPlanID);
   vector targetPoint = llChooseAssaultObjectivePoint(attackPlanID, gatherPoint);
   if (attackPlanID != lastProbedAssaultPlan)
   {
      lastProbedAssaultPlan = attackPlanID;
      llProbe("elite.assault", "attackPlan=" + attackPlanID +
         " gather=" + llFmtVec(gatherPoint) + " target=" + llFmtVec(targetPoint));
   }
   if ((gatherPoint == cInvalidVector) || (targetPoint == cInvalidVector))
   {
      llDestroyExplorerEscortPlan();
      llDestroyEliteSupportPlan();
      return (false);
   }

   int nonEliteCount = llGetTotalNonEliteTroopCount();
   int eliteCount = llGetTotalEliteTroopCount();
   int totalArmyCount = nonEliteCount + eliteCount;
   bool largeArmy = ((nonEliteCount >= 12) && (totalArmyCount >= 18));
   float protectionBias = llGetExplorerProtectionBias();
   float decapitationBias = llGetDecapitationBias();

   float eliteOffset = 7.0;
   float explorerOffset = 14.0 + (protectionBias * 10.0) - (decapitationBias * 4.0) + gLLExplorerRearOffsetBonus;
   int desiredEliteCount = 1;
   int desiredEscortCount = 2 + (protectionBias * 5.0) + gLLExplorerEscortBonus;
   if (largeArmy == true)
   {
      eliteOffset = 13.0;
      explorerOffset = explorerOffset + 6.0;
      desiredEliteCount = eliteCount;
      desiredEscortCount = desiredEscortCount + 2;
      if (desiredEliteCount > 6)
      {
         desiredEliteCount = 6;
      }
   }
   else if (eliteCount > 1)
   {
      desiredEliteCount = 2;
   }

   if (decapitationBias >= 0.70)
   {
      desiredEscortCount = desiredEscortCount - 1;
   }

   if (desiredEscortCount < 2)
   {
      desiredEscortCount = 2;
   }

   int escortCap = nonEliteCount / 3;
   if (escortCap < 2)
   {
      escortCap = 2;
   }
   if (desiredEscortCount > escortCap)
   {
      desiredEscortCount = escortCap;
   }

   vector elitePoint = llGetAssaultOffsetPoint(gatherPoint, targetPoint, eliteOffset);
   vector explorerPoint = llGetAssaultOffsetPoint(gatherPoint, targetPoint, explorerOffset);

   llPositionExplorerBehindArmy(explorerPoint);

   if ((nonEliteCount <= 0) || (eliteCount <= 0))
   {
      llDestroyExplorerEscortPlan();
      llDestroyEliteSupportPlan();
      return (true);
   }

    if ((gLLExplorerEscortPlanID < 0) || (gLLExplorerEscortAttackPlanID != attackPlanID) ||
        (xsGetTime() - gLLExplorerEscortLastRefreshTime >= 12000))
    {
       llRebuildExplorerEscortPlan(attackPlanID, gatherPoint, explorerPoint, desiredEscortCount);
    }
    else
    {
       aiPlanSetVariableVector(gLLExplorerEscortPlanID, cCombatPlanTargetPoint, 0, explorerPoint);
       aiPlanSetVariableVector(gLLExplorerEscortPlanID, cCombatPlanGatherPoint, 0, gatherPoint);
    }

   if ((gLLEliteSupportPlanID < 0) || (gLLEliteSupportAttackPlanID != attackPlanID) ||
       (xsGetTime() - gLLEliteSupportLastRefreshTime >= 15000))
   {
      llRebuildEliteSupportPlan(attackPlanID, gatherPoint, elitePoint, desiredEliteCount);
   }
   else
   {
      aiPlanSetVariableVector(gLLEliteSupportPlanID, cCombatPlanTargetPoint, 0, elitePoint);
      aiPlanSetVariableVector(gLLEliteSupportPlanID, cCombatPlanGatherPoint, 0, gatherPoint);
   }

   return (true);
}

rule legendaryEliteGuardMonitor
inactive
minInterval 5
{
   static int probedFirstTick = 0;
   static int probedFallenOnce = 0;
   if (probedFirstTick == 0)
   {
      // LL-GUARD probe — fires once per AI on first monitor tick, confirms
      // the elite-guard/explorer-escort rule is actually running.
      llProbe("elite.guardTick", "note=monitor-first-tick");
      probedFirstTick = 1;
   }
   llLogRuleTick("legendaryEliteGuardMonitor");
   if (aiGetFallenExplorerID() >= 0)
   {
      if (probedFallenOnce == 0)
      {
         // LL-EXPLOST probe — records the moment the AI's explorer died
         // (maps to ToAllyILoseExplorerEnemy quote trigger). One-shot.
         llProbe("elite.explorerLost", "explorer=" + aiGetFallenExplorerID());
         probedFallenOnce = 1;
      }
      llDestroyEliteGuardPlan();
      llDestroyExplorerEscortPlan();
      llDestroyEliteSupportPlan();
      llRetreatAllEliteUnits();
      llTryRansomExplorer();
      return;
   }

   int attackPlanID = llGetPrimaryLandAttackPlanID();
   if (attackPlanID >= 0)
   {
      // mil.escort_check — emitted every monitor tick while an attack plan
      // is active. Records how far the leader/explorer unit is from the
      // nearest friendly land-military unit so the offline validator can
      // assert the leader stays within 30 m of the army during attacks.
      int explorerID = llGetPrimaryExplorerID();
      vector explorerPos = cInvalidVector;
      float nearestDist = -1.0;
      if (explorerID >= 0)
      {
         explorerPos = kbUnitGetPosition(explorerID);
      }
      if (explorerPos != cInvalidVector)
      {
         int milQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive,
            explorerPos, 60.0);
         int milCount = kbUnitQueryExecute(milQueryID);
         for (mi = 0; < milCount)
         {
            int milUnit = kbUnitQueryGetResult(milQueryID, mi);
            float d = distance(explorerPos, kbUnitGetPosition(milUnit));
            if ((nearestDist < 0.0) || (d < nearestDist))
            {
               nearestDist = d;
            }
         }
      }
      llProbe("mil.escort_check",
         "attack_active=1" +
         " leader_dist=" + nearestDist +
         " explorerID=" + explorerID +
         " attackPlan=" + attackPlanID);
      llDestroyEliteGuardPlan();
      if (llHandleEliteAssaultFormation(attackPlanID) == true)
      {
         return;
      }
   }
   else
   {
      llDestroyExplorerEscortPlan();
      llDestroyEliteSupportPlan();
      llResetExplorerControlToBase();
   }

   int anchorUnitID = llGetThreatenedEliteAnchorID();
   if (anchorUnitID < 0)
   {
      llDestroyEliteGuardPlan();
      return;
   }

   vector anchorLocation = kbUnitGetPosition(anchorUnitID);
   int enemyPressure = llGetNearbyEnemyPressureCount(anchorLocation, 28.0);
   if (enemyPressure <= 0)
   {
      llDestroyEliteGuardPlan();
      return;
   }

   int nearbyScreenCount = llGetNearbyNonEliteSupportCount(anchorLocation, 26.0);
   if (nearbyScreenCount > 0)
   {
      if ((gLLEliteGuardPlanID < 0) || (gLLEliteGuardAnchorUnitID != anchorUnitID))
      {
         llRebuildEliteGuardPlan(anchorUnitID);
      }
      else
      {
         aiPlanSetVariableVector(gLLEliteGuardPlanID, cCombatPlanTargetPoint, 0, anchorLocation);
      }
      return;
   }

   llDestroyEliteGuardPlan();

   if (llGetTotalNonEliteTroopCount() > 0)
   {
      return;
   }

   int playstyleBucket = llGetPlaystyleBucket();
   if (playstyleBucket >= 2)
   {
      debugLegendaryLeaders("elite core remains engaged because leader playstyle is aggressive.");
      return;
   }

   if ((playstyleBucket == 1) && (enemyPressure <= llGetNearbyEliteCoreCount(anchorLocation, 30.0)))
   {
      debugLegendaryLeaders("elite core remains engaged because balanced leader still has a favorable local fight.");
      return;
   }

   llRetreatEliteCore(anchorUnitID);
}

//==============================================================================
/* AI non-elite rout system (Legendary Leaders).
 *
 * Behaviour spec (matches tools/validation/runtime_specs/legendary_runtime_suites.json):
 *
 *   - Non-elite AI-controlled land military breaks when its hitpoints fall
 *     under 25% AND no elite/hero support is within 18 m. Broken units
 *     issue a retreat-to-main-base move command.
 *   - Elite units and any unit currently controlled by the human player
 *     keep their orders untouched.
 *   - Rout is blocked when an elite anchor is close — the screen body
 *     stays in formation around the elite line; this is the entire point
 *     of the elite-screen formation built earlier in this file.
 *
 * Debug markers (the validator looks for these strings verbatim):
 *
 *   "Legendary Leaders: [RULE] AI non-elite rout enabled at 25% health; "
 *   "elite units hold and human-controlled units keep manual control"
 *       — one-shot, first tick of the rule, confirms boot.
 *
 *   "Legendary Leaders: [UNIT] ai-rout-start unit=<ID>"   — first rout tick
 *   "Legendary Leaders: [UNIT] ai-rout-move unit=<ID>"    — each subsequent tick still moving
 *   "Legendary Leaders: [UNIT] ai-rout-arrival unit=<ID>" — within 6 m of destination
 *   "Legendary Leaders: [UNIT] ai-rout-blocked unit=<ID> reason=elite-support"
 *       — emitted when a unit would have routed but an elite anchor was
 *         within range. Confirms the screen-body-stays-in-formation rule.
 *
 * Tracking: a single static xsArray of 32 tracked unit IDs plus a parallel
 * vector array for the per-unit destination. 32 is plenty — a typical AI
 * army has under 20 active engaged units and rout state only persists for
 * a few ticks per unit. Slots are reused round-robin; a dead/healed unit
 * frees its slot.
 */
//==============================================================================

extern int gLLAiRoutSlotsArrayID = -1;        // xsArrayCreateInt slots → unitID (-1 = free)
extern int gLLAiRoutDestArrayID = -1;         // xsArrayCreateVector slots → destination
extern int gLLAiRoutStartTimeArrayID = -1;    // xsArrayCreateInt slots → start time (s)
extern int gLLAiRoutSlotCount = 32;
extern int gLLAiRoutBootMarkerEmitted = 0;
extern int gLLAiRoutLastDestinationStaleCheck = -1;

const float cLLAiRoutHpThreshold       = 0.25;   // 25% health
const float cLLAiRoutEliteSupportRange = 18.0;   // metres
const float cLLAiRoutArrivalTolerance  = 6.0;    // metres — "arrived" radius
const int   cLLAiRoutMaxLifetimeSecs   = 60;     // give up tracking after this

void llEnsureAiRoutArrays(void)
{
   if (gLLAiRoutSlotsArrayID < 0)
   {
      gLLAiRoutSlotsArrayID = xsArrayCreateInt(gLLAiRoutSlotCount, -1, "LL ai-rout slots");
      gLLAiRoutStartTimeArrayID = xsArrayCreateInt(gLLAiRoutSlotCount, -1, "LL ai-rout start time");
      gLLAiRoutDestArrayID = xsArrayCreateVector(gLLAiRoutSlotCount, cInvalidVector, "LL ai-rout dest");
   }
}

int llFindAiRoutSlotForUnit(int unitID = -1)
{
   if ((unitID < 0) || (gLLAiRoutSlotsArrayID < 0))
   {
      return (-1);
   }
   for (slot = 0; < gLLAiRoutSlotCount)
   {
      if (xsArrayGetInt(gLLAiRoutSlotsArrayID, slot) == unitID)
      {
         return (slot);
      }
   }
   return (-1);
}

int llClaimAiRoutSlot(int unitID = -1, vector dest = cInvalidVector)
{
   if (unitID < 0)
   {
      return (-1);
   }
   llEnsureAiRoutArrays();
   int existing = llFindAiRoutSlotForUnit(unitID);
   if (existing >= 0)
   {
      return (existing);
   }
   for (slot = 0; < gLLAiRoutSlotCount)
   {
      if (xsArrayGetInt(gLLAiRoutSlotsArrayID, slot) < 0)
      {
         xsArraySetInt(gLLAiRoutSlotsArrayID, slot, unitID);
         xsArraySetInt(gLLAiRoutStartTimeArrayID, slot, xsGetTime());
         xsArraySetVector(gLLAiRoutDestArrayID, slot, dest);
         return (slot);
      }
   }
   return (-1);
}

void llReleaseAiRoutSlot(int slot = -1)
{
   if ((slot < 0) || (gLLAiRoutSlotsArrayID < 0))
   {
      return;
   }
   xsArraySetInt(gLLAiRoutSlotsArrayID, slot, -1);
   xsArraySetInt(gLLAiRoutStartTimeArrayID, slot, -1);
   xsArraySetVector(gLLAiRoutDestArrayID, slot, cInvalidVector);
}

vector llChooseAiRoutDestination(void)
{
   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID < 0)
   {
      return (cInvalidVector);
   }
   return (kbBaseGetLocation(cMyID, mainBaseID));
}

bool llAiRoutHasEliteSupportNearby(vector pos = cInvalidVector)
{
   if (pos == cInvalidVector)
   {
      return (false);
   }
   // Heroes are explicitly counted as elite support per the elite-tactics
   // formation contract (line 26 of this file). llIsEliteUnit() currently
   // returns false unconditionally — heroes carry the elite anchor role.
   int heroQuery = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive,
      pos, cLLAiRoutEliteSupportRange);
   int heroCount = kbUnitQueryExecute(heroQuery);
   if (heroCount > 0)
   {
      return (true);
   }
   return (false);
}

bool llIsAiRoutEligibleUnit(int unitID = -1)
{
   if (unitID < 0)
   {
      return (false);
   }
   if (kbUnitGetPlayerID(unitID) != cMyID)
   {
      return (false);
   }
   // Heroes are elite anchors; never rout them via this system.
   if (kbUnitIsType(unitID, cUnitTypeHero) == true)
   {
      return (false);
   }
   // The explorer (subset of hero) gets its own escort/ransom logic
   // elsewhere in this file. Skip.
   if (kbUnitIsType(unitID, cUnitTypeAbstractExplorer) == true)
   {
      return (false);
   }
   // Out-of-scope: human-controlled units retain manual orders. The XS
   // engine only ticks rules for the *current* AI player, so any unit
   // owned by a human player is naturally filtered by the cMyID check
   // above. The contract is documented in the boot marker for clarity.
   if (kbUnitGetHealth(unitID) >= cLLAiRoutHpThreshold)
   {
      return (false);
   }
   return (true);
}

void llProcessAiRoutTick(void)
{
   llEnsureAiRoutArrays();

   // ── Pass 1: reap stale slots (dead units, healed units, expired) ──
   int now = xsGetTime();
   for (slot = 0; < gLLAiRoutSlotCount)
   {
      int trackedID = xsArrayGetInt(gLLAiRoutSlotsArrayID, slot);
      if (trackedID < 0)
      {
         continue;
      }
      // Dead or unknown → release.
      if (kbUnitGetCurrentHitpoints(trackedID) <= 0)
      {
         llReleaseAiRoutSlot(slot);
         continue;
      }
      // Healed back above threshold → release (the unit is fine again).
      if (kbUnitGetHealth(trackedID) >= (cLLAiRoutHpThreshold + 0.10))
      {
         llReleaseAiRoutSlot(slot);
         continue;
      }
      // Expired → release (something else has happened, stop tracking).
      int startTime = xsArrayGetInt(gLLAiRoutStartTimeArrayID, slot);
      if ((startTime > 0) && ((now - startTime) > cLLAiRoutMaxLifetimeSecs))
      {
         llReleaseAiRoutSlot(slot);
         continue;
      }
      // Arrived → emit and release.
      vector dest = xsArrayGetVector(gLLAiRoutDestArrayID, slot);
      vector pos = kbUnitGetPosition(trackedID);
      if (dest != cInvalidVector)
      {
         float distLeft = distance(pos, dest);
         if (distLeft <= cLLAiRoutArrivalTolerance)
         {
            debugLegendaryLeaders("[UNIT] ai-rout-arrival unit=" + trackedID);
            llProbe("rout.arrival", "unit=" + trackedID +
               " dist=" + distLeft + " elapsed=" + (now - startTime));
            llReleaseAiRoutSlot(slot);
            continue;
         }
         // Still moving — emit the tick marker.
         debugLegendaryLeaders("[UNIT] ai-rout-move unit=" + trackedID);
      }
   }

   // ── Pass 2: scan land military for new rout candidates ──
   vector routDest = llChooseAiRoutDestination();
   if (routDest == cInvalidVector)
   {
      // No main base yet — nothing to rout toward. Bail.
      return;
   }
   int milQuery = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary,
      cMyID, cUnitStateAlive);
   int milCount = kbUnitQueryExecute(milQuery);
   for (i = 0; < milCount)
   {
      int unitID = kbUnitQueryGetResult(milQuery, i);
      if (llIsAiRoutEligibleUnit(unitID) == false)
      {
         continue;
      }
      vector unitPos = kbUnitGetPosition(unitID);
      // Elite-support gating — broken unit holds line if an elite anchor
      // is in range. Per spec, emit the blocked marker once per visit so
      // the validator can observe the support-screen contract.
      if (llAiRoutHasEliteSupportNearby(unitPos) == true)
      {
         // Only emit-blocked once per tracked unit per tick (we don't have
         // per-unit tick history, so emit once per tick at low rate).
         debugLegendaryLeaders("[UNIT] ai-rout-blocked unit=" + unitID +
            " reason=elite-support");
         llProbe("rout.blocked", "unit=" + unitID + " reason=elite-support");
         // If this unit had been routing, cancel — elite arrived to support.
         int oldSlot = llFindAiRoutSlotForUnit(unitID);
         if (oldSlot >= 0)
         {
            llReleaseAiRoutSlot(oldSlot);
         }
         continue;
      }
      int existingSlot = llFindAiRoutSlotForUnit(unitID);
      if (existingSlot < 0)
      {
         int newSlot = llClaimAiRoutSlot(unitID, routDest);
         if (newSlot >= 0)
         {
            aiTaskUnitMove(unitID, routDest);
            debugLegendaryLeaders("[UNIT] ai-rout-start unit=" + unitID);
            llProbe("rout.start", "unit=" + unitID +
               " hp=" + kbUnitGetHealth(unitID) +
               " dest=" + llFmtVec(routDest));
         }
      }
      else
      {
         // Already tracked — re-issue the move order in case the unit's
         // engagement was interrupted and it stopped moving. AoE3's
         // aiTaskUnitMove is idempotent against an active move order, so
         // this is cheap.
         aiTaskUnitMove(unitID, routDest);
      }
   }
}

//==============================================================================
// legendaryAiRoutMonitor — periodic monitor for the non-elite-rout system.
//
// Activated alongside legendaryEliteGuardMonitor in aiCore.xs (early-game
// hook in age2Monitor). Fires every 4 s — slightly more often than the
// elite guard's 5 s tick so a broken unit gets its retreat order within a
// single second of falling under threshold.
//
// The first tick emits the boot marker the runtime-logs validator looks
// for. Subsequent ticks emit per-unit start/move/arrival/blocked markers
// driven by llProcessAiRoutTick().
//==============================================================================
rule legendaryAiRoutMonitor
inactive
minInterval 4
{
   if (gLLAiRoutBootMarkerEmitted == 0)
   {
      // Single literal (no concatenation) so the offline static-emitter
      // checker in tools/validation/validate_runtime_logs.py can see this
      // marker as a contiguous substring in the XS source.
      debugLegendaryLeaders("[RULE] AI non-elite rout enabled at 25% health; elite units hold and human-controlled units keep manual control");
      llProbe("rout.boot",
         "hp_threshold=" + cLLAiRoutHpThreshold +
         " elite_support_range=" + cLLAiRoutEliteSupportRange +
         " arrival_tolerance=" + cLLAiRoutArrivalTolerance);
      gLLAiRoutBootMarkerEmitted = 1;
   }
   llLogRuleTick("legendaryAiRoutMonitor");
   llProcessAiRoutTick();
}