//==============================================================================
/* aiHumanAssists.xs

   Create an AI for Definitive Edition that just prepares the kb & sets up some basic plans for the Human players to use for things like auto-scout and managing resource gatherers.

*/
//==============================================================================

mutable vector getStartingLocation(void) { return (kbGetPlayerStartingPosition(cMyID)); }

mutable void selectTowerBuildPlanPosition(int buildPlan = -1, int baseID = -1) {}
mutable void selectShrineBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectTorpBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectTCBuildPlanPosition(int buildPlan = -1, int baseID = -1) {}
mutable void selectTeepeeBuildPlanPosition(int buildPlan = -1, int baseID = -1) {}
mutable bool selectTribalMarketplaceBuildPlanPosition(int buildPlan = -1, int baseID = -1) { return (false); }
mutable bool selectFieldBuildPlanPosition(int planID = -1, int baseID = -1) { return (false); }
mutable void selectMountainMonasteryBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectGranaryBuildPlanPosition(int planID = -1, int baseID = -1) {}
mutable void selectClosestBuildPlanPosition(int planID = -1, int baseID = -1, int puid = -1) {}
mutable bool selectBuildPlanPosition(int planID = -1, int puid = -1, int baseID = -1) { return (false); }
mutable bool addBuilderToPlan(int planID = -1, int puid = -1, int numberBuilders = 1) { return (false); }
mutable void sendStatement(int playerIDorRelation = -1, int commPromptID = -1, vector vec = cInvalidVector) {}
mutable void sendChatLine(int playerIDorRelation = -1, string message = "") {}

include "aiHeader.xs";
include "core\aiGlobals.xs";
include "core\aiUtilities.xs";

extern float gTSFactorDistance = -200.0;  // negative is good
extern float gTSFactorPoint = 10.0;			// positive is good
extern float gTSFactorTimeToDone = 0.0;	// positive is good
extern float gTSFactorBase = 100.0;			// positive is good
extern float gTSFactorDanger = -10.0;		// negative is good

//==============================================================================
// main
//==============================================================================
void main(void)
{
   anwVerboseEcho("Human player assists AI startup.");
   anwVerboseEcho("Game type is " + aiGetGameType() + ", 0=Scn, 1=Saved, 2=Rand, 3=GC, 4=Cmpgn");
   anwVerboseEcho("Map name is " + cRandomMapName);

   aiRandSetSeed(-1);         // Set our random seed.  "-1" is a random init.
   kbAreaCalculate();         // Analyze the map, create area matrix
   aiSetEscrowsDisabled(true); // Disable escrows so we can have full control of our resources

   //-- set the default Resource Selector factor.
   kbSetTargetSelectorFactor(cTSFactorDistance, gTSFactorDistance);
   kbSetTargetSelectorFactor(cTSFactorPoint, gTSFactorPoint);
   kbSetTargetSelectorFactor(cTSFactorTimeToDone, gTSFactorTimeToDone);
   kbSetTargetSelectorFactor(cTSFactorBase, gTSFactorBase);
   kbSetTargetSelectorFactor(cTSFactorDanger, gTSFactorDanger);

   anwLogEvent("RULE", "human assist AI startup complete; player-controlled units keep manual control");
}
