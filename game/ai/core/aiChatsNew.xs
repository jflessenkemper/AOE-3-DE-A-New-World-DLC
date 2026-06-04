// New Chats from references found in data files...
//ToAllyThanksForReinforcementsDefense
//ToAllyAdviceUseMoreCav
//ToAllyIFailedToDestroyNativeSite
//ToAllyYourMPRatingIsUp
//ToAllyYourXPHasGoneUp
//ToAllyBattleFourOrMorePlayers
//ToEnemy1MinuteLeftOur4OfKind
//ToAllyConfirmInfArt
//ToAllyBattleStartMyFavor
//ToAllyIDestroyedTown
//ToAllyIDestroyedTown
//ToEnemyIDestroyedHisTC
//ToAllyIDestroyed4OfKind - four trade posts
//ToAllyIDestroyedTradeSite
//ToAllyIWillDefendLocation
//ToAllyISeeEnemyTCNoArmy
//==============================================================================
/* manyPlayersComment
   Notice that we have many players in the game.
*/
//==============================================================================
rule manyPlayersComment
inactive
minInterval 5
{
   anwLogRuleTick("manyPlayersComment");
   if (cNumberPlayers >= 4) {
      sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyBattleFourOrMorePlayers);
      sendStatement(cPlayerRelationEnemyNotGaia, cAICommPromptToEnemyBattleFourOrMorePlayers);
   }
   xsDisableSelf();
}
//==============================================================================
/* myWallChat
   Tell my friend about my wall.
*/
//==============================================================================
rule myWallChat
inactive
minInterval 5
{
   anwLogRuleTick("myWallChat");
   int buildingId = getUnit(cUnitTypeAbstractWall, cMyID, cUnitStateAlive);

   if (buildingId >= 0)
   {
      sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyWhenIWallIn, kbUnitGetPosition(buildingId));
      xsDisableSelf();
   }
}
//==============================================================================
/* enemyWallTaunt
   Tell my enemy what I think about his wall.
*/
//==============================================================================
rule enemyWallTaunt
inactive
minInterval 5
{
   anwLogRuleTick("enemyWallTaunt");
   int buildingId = getUnit(cUnitTypeAbstractWall, cPlayerRelationEnemyNotGaia, cUnitStateAlive);

   if (buildingId >= 0)
   {
      if (getUnitByLocation(cUnitTypeUnit, cMyID, cUnitStateAlive, kbUnitGetPosition(buildingId), 70.0) >= 0)
      {
         sendStatement(cPlayerRelationEnemyNotGaia, cAICommPromptToEnemyWhenHeWallsIn);
         xsDisableSelf();
      }
   }
}
//==============================================================================
/* boringChatter
   Tell everyone I am bored.
*/
//==============================================================================
rule boringChatter
inactive
minInterval 50
{
   anwLogRuleTick("boringChatter");
   int currentTime = xsGetTime();
   int interval = aiRandInt(15) * 60 * 1000;

   if (currentTime > 15 * 60 * 1000)
   {
      if ((currentTime > gLastAttackMissionTime + interval) && 
      (currentTime > gLastDefendMissionTime + interval))
      {
         sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyLull);
         sendStatement(cPlayerRelationEnemyNotGaia, cAICommPromptToEnemyLull);
         anwSendLeaderComplimentLine(cPlayerRelationAllyExcludingSelf, interval);
         anwSendLeaderInsultLine(cPlayerRelationEnemyNotGaia, interval);
         xsSetRuleMinIntervalSelf(interval);
      }
   }
}
//==============================================================================
/* giveAdviceAndComments
   Give advice and comments to the other players. - Were these chats removed?
*/
//==============================================================================
// rule giveAdviceAndComments
// inactive
// minInterval 10
// {
//    int cavalryCount = createSimpleUnitQuery(cUnitTypeAbstractCavalry, cPlayerRelationAllyExcludingSelf, 
//    cUnitStateAlive, kbGetMapCenter(), kbGetMapXSize());
//    int infantryCount = createSimpleUnitQuery(cUnitTypeAbstractInfantry, cPlayerRelationAllyExcludingSelf, 
//    cUnitStateAlive, kbGetMapCenter(), kbGetMapXSize());
//    int artilleryCount = createSimpleUnitQuery(cUnitTypeAbstractArtillery, cPlayerRelationAllyExcludingSelf, 
//    cUnitStateAlive, kbGetMapCenter(), kbGetMapXSize());
//    int allyMilitaryCount = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cPlayerRelationAllyExcludingSelf, 
//    cUnitStateAlive, kbGetMapCenter(), kbGetMapXSize());
//    // int enemyMilitaryCount = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cPlayerRelationEnemyNotGaia, 
//    // cUnitStateAlive, kbGetMapCenter(), kbGetMapXSize());

//    if (cavalryCount < 10 && (allyMilitaryCount > 60)) {
//       sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyAdviceUseMoreCavalry);
//    }
//    if (infantryCount < 20 && (allyMilitaryCount > 60)) {
//       sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyAdviceUseMoreInfantry);
//    }
//    if (artilleryCount < 3 && (allyMilitaryCount > 60)) {
//       sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyAdviceUseMoreArtillery);
//    }

//    for (int player = 1; player < cNumberPlayers; player++) {
//       int currentPlayerXP = kbResourceGetXP(player);

//       // TODO: Investigate if there is a cleaner way to do this in XS scripting. Such as a keyed dictionary, object array, etc...
//       if (kbIsPlayerAlly(player) == true) {
//          if (player == 1 && (currentPlayerXP > (gXpValuePlayer1 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer1 = currentPlayerXP; }
//          if (player == 2 && (currentPlayerXP > (gXpValuePlayer2 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer2 = currentPlayerXP; }
//          if (player == 3 && (currentPlayerXP > (gXpValuePlayer3 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer3 = currentPlayerXP; }
//          if (player == 4 && (currentPlayerXP > (gXpValuePlayer4 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer4 = currentPlayerXP; }
//          if (player == 5 && (currentPlayerXP > (gXpValuePlayer5 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer5 = currentPlayerXP; }
//          if (player == 6 && (currentPlayerXP > (gXpValuePlayer6 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer6 = currentPlayerXP; }
//          if (player == 7 && (currentPlayerXP > (gXpValuePlayer7 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer7 = currentPlayerXP; }
//          if (player == 8 && (currentPlayerXP > (gXpValuePlayer8 + 20000))) { sendStatement(player, cAICommPromptToAllyYourXPHasGoneUp); 
//          gXpValuePlayer8 = currentPlayerXP; }
//          // if (allyMilitaryCount < (enemyMilitaryCount - 30)) {
//          //    sendStatement(cPlayerRelationAllyExcludingSelf, cAICommPromptToAllyAdviceWithdrawFromBattle);
//          // }
//       }
//    }
// }