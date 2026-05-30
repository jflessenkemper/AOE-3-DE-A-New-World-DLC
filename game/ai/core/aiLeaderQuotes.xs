//==============================================================================
/* aiLeaderQuotes.xs

   Shared leader quote runtime for Legendary Leaders personalities.
*/
//==============================================================================

int gLLLeaderEnemyQuoteTime = -600000;
int gLLLeaderAllyQuoteTime = -600000;
int gLLLeaderTacticalQuoteTime = -600000;

bool llHasLegendaryLeaderQuotes(void)
{
   return (llGetLegendaryLeaderInsult() != "");
}

bool llShouldAppendQuoteForStatement(int commPromptID = -1)
{
   switch (commPromptID)
   {
      case cAICommPromptToAllyRequestFood:
      case cAICommPromptToAllyRequestWood:
      case cAICommPromptToAllyRequestCoin:
      {
         return (false);
      }
   }

   return (true);
}

int llGetQuoteIntervalForStatement(int commPromptID = -1)
{
   switch (commPromptID)
   {
      case cAICommPromptToAllyLull:
      case cAICommPromptToEnemyLull:
      case cAICommPromptToAllyWhenWeGetMonopoly:
      case cAICommPromptToEnemyWhenWeGetMonopoly:
      case cAICommPromptToAllyWhenEnemiesGetMonopoly:
      case cAICommPromptToEnemyWhenTheyGetMonopoly:
      case cAICommPromptToAllyEnemyDestroyedMonopoly:
      case cAICommPromptToEnemyTheyDestroyedMonopoly:
      case cAICommPromptToEnemyIDestroyedMonopoly:
      case cAICommPromptToAlly1MinuteLeftOurMonopoly:
      case cAICommPromptToEnemy1MinuteLeftOurMonopoly:
      case cAICommPromptToAlly1MinuteLeftEnemyMonopoly:
      case cAICommPromptToEnemy1MinuteLeftEnemyMonopoly:
      {
         return (240000);
      }
      case cAICommPromptToAllyWeAreWinning:
      case cAICommPromptToAllyWeAreWinningHeIsStronger:
      case cAICommPromptToAllyWeAreWinningHeIsWeaker:
      case cAICommPromptToAllyWeShouldResign1:
      case cAICommPromptToAllyWeShouldResign2:
      case cAICommPromptToAllyWeShouldResign3:
      case cAICommPromptToAllyWeAreLosingHeIsStronger:
      case cAICommPromptToAllyWeAreLosingHeIsWeaker:
      case cAICommPromptToAllyImReadyToQuit:
      {
         return (300000);
      }
   }

   return (120000);
}

void llSendLegendaryLeaderInsultLine(int playerIDorRelation = -1, int quoteInterval = 90000)
{
   if (xsGetTime() < gLLLeaderEnemyQuoteTime + quoteInterval)
   {
      debugLegendaryLeaders("enemy quote throttled for target " + playerIDorRelation + " with interval " + quoteInterval);
      return;
   }

   string message = llGetLegendaryLeaderInsult();
   if (message == "")
   {
      debugLegendaryLeaders("enemy quote skipped because no insult is defined for " + kbGetCivName(cMyCiv));
      return;
   }

   sendChatLine(playerIDorRelation, message);
   gLLLeaderEnemyQuoteTime = xsGetTime();
   debugLegendaryLeaders("enemy quote sent to " + playerIDorRelation + ": " + message);
}

void llSendLegendaryLeaderComplimentLine(int playerIDorRelation = -1, int quoteInterval = 90000)
{
   if (xsGetTime() < gLLLeaderAllyQuoteTime + quoteInterval)
   {
      debugLegendaryLeaders("ally quote throttled for target " + playerIDorRelation + " with interval " + quoteInterval);
      return;
   }

   string message = llGetLegendaryLeaderCompliment();
   if (message == "")
   {
      debugLegendaryLeaders("ally quote skipped because no compliment is defined for " + kbGetCivName(cMyCiv));
      return;
   }

   sendChatLine(playerIDorRelation, message);
   gLLLeaderAllyQuoteTime = xsGetTime();
   debugLegendaryLeaders("ally quote sent to " + playerIDorRelation + ": " + message);
}

void llSendLegendaryLeaderTacticalLine(int playerIDorRelation = -1, string message = "", int quoteInterval = 90000)
{
   if ((playerIDorRelation < 0) || (message == ""))
   {
      return;
   }

   if (xsGetTime() < gLLLeaderTacticalQuoteTime + quoteInterval)
   {
      debugLegendaryLeaders("tactical quote throttled for target " + playerIDorRelation + " with interval " + quoteInterval);
      return;
   }

   sendChatLine(playerIDorRelation, message);
   gLLLeaderTacticalQuoteTime = xsGetTime();
   debugLegendaryLeaders("tactical quote sent to " + playerIDorRelation + ": " + message);
}

string llGetLegendaryLeaderRetreatLine(void)
{
   return ("Fall back and close ranks. Our leader will not be lost today.");
}

string llGetLegendaryLeaderRoutLine(void)
{
   return ("Your broken soldiers are in full retreat now.");
}

string llGetLegendaryLeaderBulkAssaultLine(void)
{
   return ("Break their main line first. The army is the real prize.");
}

string llGetLegendaryLeaderDecapitationLine(void)
{
   return ("Ignore the rabble. Bring down their leader.");
}

void llSendLegendaryLeaderRetreatLine(int playerIDorRelation = -1, int quoteInterval = 150000)
{
   llSendLegendaryLeaderTacticalLine(playerIDorRelation, llGetLegendaryLeaderRetreatLine(), quoteInterval);
}

void llSendLegendaryLeaderRoutLine(int playerIDorRelation = -1, int quoteInterval = 120000)
{
   llSendLegendaryLeaderTacticalLine(playerIDorRelation, llGetLegendaryLeaderRoutLine(), quoteInterval);
}

void llSendLegendaryLeaderBulkAssaultLine(int playerIDorRelation = -1, int quoteInterval = 120000)
{
   llSendLegendaryLeaderTacticalLine(playerIDorRelation, llGetLegendaryLeaderBulkAssaultLine(), quoteInterval);
}

void llSendLegendaryLeaderDecapitationLine(int playerIDorRelation = -1, int quoteInterval = 120000)
{
   llSendLegendaryLeaderTacticalLine(playerIDorRelation, llGetLegendaryLeaderDecapitationLine(), quoteInterval);
}

void llMaybeFollowStatementWithQuote(int playerID = -1, int commPromptID = -1)
{
   if ((playerID < 0) || (llHasLegendaryLeaderQuotes() == false))
   {
      return;
   }

   if (llShouldAppendQuoteForStatement(commPromptID) == false)
   {
      debugLegendaryLeaders("statement " + commPromptID + " skipped for quote follow-up.");
      return;
   }

   int interval = llGetQuoteIntervalForStatement(commPromptID);
   debugLegendaryLeaders("statement " + commPromptID + " evaluating quote follow-up for player " + playerID + " with interval " + interval);

   if (kbIsPlayerEnemy(playerID) == true)
   {
      llSendLegendaryLeaderInsultLine(playerID, interval);
      return;
   }

   if (kbIsPlayerAlly(playerID) == true)
   {
      llSendLegendaryLeaderComplimentLine(playerID, interval);
   }
}

rule legendaryLeaderOpeningQuote
inactive
minInterval 10
{
   llLogRuleTick("legendaryLeaderOpeningQuote");
   if (llHasLegendaryLeaderQuotes() == false)
   {
      xsDisableSelf();
      return;
   }

   if (xsGetTime() < 25000)
   {
      return;
   }

   debugLegendaryLeaders("opening quotes firing for " + kbGetCivName(cMyCiv));
   // LL-QUOTE probe — ensures the per-leader opening compliment/insult pair
   // fires at ~25s and only once. Miss = legendary quote wiring broken.
   llProbe("chat.quote", "kind=opening");
   llSendLegendaryLeaderComplimentLine(cPlayerRelationAllyExcludingSelf, 0);
   llSendLegendaryLeaderInsultLine(cPlayerRelationEnemyNotGaia, 0);
   xsDisableSelf();
}

void enableLegendaryLeaderQuoteRules(void)
{
   if (llHasLegendaryLeaderQuotes() == false)
   {
      return;
   }

   llLogEvent("RULE", "enabling legendary leader opening quote rule");
   xsEnableRule("legendaryLeaderOpeningQuote");
}

// Map kbGetCivName() internal strings (e.g. "XPIroquois", "DEMaltese") to
// the display-name branches used by the insult/compliment tables. Without
// this, leaders for XP/DE-prefixed civs silently get no quote, and the
// opening-quote rule disables itself (bug observed in replay: Hiawatha/Jean
// missing opening quotes).
string llNormalizeCivName(string raw = "")
{
   if (raw == "XPIroquois")   return ("Haudenosaunee");
   if (raw == "XPAztec")      return ("Aztecs");
   if (raw == "XPSioux")      return ("Lakota");
   if (raw == "DEMaltese")    return ("Maltese");
   if (raw == "DEAmericans")  return ("UnitedStates");
   if (raw == "DEMexicans")   return ("Mexicans");
   if (raw == "DEItalians")   return ("Italians");
   if (raw == "DEEthiopians") return ("Ethiopians");
   if (raw == "DEHausa")      return ("Hausa");
   if (raw == "DEInca")       return ("Inca");
   if (raw == "DESwedish")    return ("Swedes");
   return (raw);
}

string llGetLegendaryLeaderInsult(void)
{
   string civName = llNormalizeCivName(kbGetCivName(cMyCiv));
   int quoteIndex = aiRandInt(2);

   if (civName == "Aztecs")
   {
      if (quoteIndex == 0)
      {
         return ("The omens condemn such disorder.");
      }
      return ("Even Tenochtitlan deserved a better foe.");
   }
   else if (civName == "British")
   {
      if (quoteIndex == 0)
      {
         return ("That advance would die nameless on a ridge in Spain.");
      }
      return ("You confuse obstinacy with discipline.");
   }
   else if (civName == "Chinese")
   {
      if (quoteIndex == 0)
      {
         return ("You bring disorder to a field that demands harmony.");
      }
      return ("Even frontier rebels show firmer order.");
   }
   else if (civName == "Dutch")
   {
      if (quoteIndex == 0)
      {
         return ("Your volley is late and your drill worse.");
      }
      return ("A republic deserves firmer drill than this.");
   }
   else if (civName == "Ethiopians")
   {
      if (quoteIndex == 0)
      {
         return ("You climb these heights without judgment.");
      }
      return ("Adwa would have buried such ambition.");
   }
   else if (civName == "French")
   {
      if (quoteIndex == 0)
      {
         return ("You maneuver like a clerk and expect empire to follow.");
      }
      return ("Even at Austerlitz I saw less confusion.");
   }
   else if (civName == "Germans")
   {
      if (quoteIndex == 0)
      {
         return ("Your line offends both reason and powder.");
      }
      return ("Leuthen required more nerve than this.");
   }
   else if ((civName == "Haudenosaunee") || (civName == "XPIroquois"))
   {
      if (quoteIndex == 0)
      {
         return ("You break ranks as easily as broken councils.");
      }
      return ("A careless warrior shames his people twice.");
   }
   else if (civName == "Hausa")
   {
      if (quoteIndex == 0)
      {
         return ("You advance without justice or discipline.");
      }
      return ("A ruler without justice invites his own ruin.");
   }
   else if (civName == "Inca")
   {
      if (quoteIndex == 0)
      {
         return ("You cannot build victory on such loose stones.");
      }
      return ("The mountain road would reject this army.");
   }
   else if (civName == "Indians")
   {
      if (quoteIndex == 0)
      {
         return ("You guard no flank and deserve none.");
      }
      return ("Even a hill fort sees through this plan.");
   }
   else if (civName == "Italians")
   {
      if (quoteIndex == 0)
      {
         return ("You march like ceremony, not revolution.");
      }
      return ("Italy is not made by men who wait.");
   }
   else if (civName == "Japanese")
   {
      if (quoteIndex == 0)
      {
         return ("The impatient commander defeats himself first.");
      }
      return ("Sekigahara was won with more patience than this.");
   }
   else if (civName == "Lakota")
   {
      if (quoteIndex == 0)
      {
         return ("You ride as if the plains forgive weakness.");
      }
      return ("A slow hunter does not return.");
   }
   else if ((civName == "Maltese") || (civName == "DEMaltese"))
   {
      if (quoteIndex == 0)
      {
         return ("You break on stone and call it valor.");
      }
      return ("Malta endured fiercer men than you.");
   }
   else if (civName == "Mexicans")
   {
      if (quoteIndex == 0)
      {
         return ("A people do not stay quiet forever.");
      }
      return ("Your authority sounds louder than it stands.");
   }
   else if (civName == "Ottomans")
   {
      if (quoteIndex == 0)
      {
         return ("You bring neither law nor strength.");
      }
      return ("Belgrade demanded more order than this.");
   }
   else if (civName == "Portuguese")
   {
      if (quoteIndex == 0)
      {
         return ("You mistake horizon for mastery.");
      }
      return ("Such seamanship would shame Sagres.");
   }
   else if (civName == "Russians")
   {
      if (quoteIndex == 0)
      {
         return ("You have breadth but no design.");
      }
      return ("Even the frontier deserves a sharper will.");
   }
   else if (civName == "Spanish")
   {
      if (quoteIndex == 0)
      {
         return ("You squander zeal as well as steel.");
      }
      return ("Granada required sterner resolve than this.");
   }
   else if (civName == "Swedes")
   {
      if (quoteIndex == 0)
      {
         return ("You are too slow for modern war.");
      }
      return ("Breitenfeld punished lesser confusion.");
   }
   else if (civName == "UnitedStates")
   {
      if (quoteIndex == 0)
      {
         return ("Liberty is not defended by blundering in plain sight.");
      }
      return ("You would not survive a winter at Valley Forge.");
   }
   else if (civName == "ANWNapoleonicFrance")
   {
      if (quoteIndex == 0)
      {
         return ("Europe did not fear me for such maneuvers.");
      }
      return ("You waste the moment and the map.");
   }
   else if (civName == "ANWAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("A republic cannot survive such command.");
      }
      return ("Your cause buckles under poor leadership.");
   }
   else if (civName == "ANWMexicans")
   {
      if (quoteIndex == 0)
      {
         return ("The people owe no loyalty to weakness.");
      }
      return ("Your rule shakes before a single volley.");
   }
   else if (civName == "ANWCanadians")
   {
      if (quoteIndex == 0)
      {
         return ("This frontier has broken louder men than you.");
      }
      return ("You rush the woods and call it strategy.");
   }
   else if (civName == "ANWBrazil")
   {
      if (quoteIndex == 0)
      {
         return ("Empires are not born from such hesitation.");
      }
      return ("You bring pomp without vigor.");
   }
   else if (civName == "ANWArgentines")
   {
      if (quoteIndex == 0)
      {
         return ("The Andes would laugh at such a march.");
      }
      return ("You spend men where nerve would suffice.");
   }
   else if (civName == "ANWChileans")
   {
      if (quoteIndex == 0)
      {
         return ("A wavering hand cannot found a republic.");
      }
      return ("You attack without endurance.");
   }
   else if (civName == "ANWPeruvians")
   {
      if (quoteIndex == 0)
      {
         return ("You campaign without altitude or vision.");
      }
      return ("The Andes grant no pardon to such noise.");
   }
   else if (civName == "ANWColumbians")
   {
      if (quoteIndex == 0)
      {
         return ("You dream of empire and cannot hold a ridge.");
      }
      return ("History does not wait for weaker men.");
   }
   else if (civName == "ANWHaitians")
   {
      if (quoteIndex == 0)
      {
         return ("No army stands long upon the whip.");
      }
      return ("You command fear and mistake it for loyalty.");
   }
   else if (civName == "ANWIndonesians")
   {
      if (quoteIndex == 0)
      {
         return ("You occupy land you do not understand.");
      }
      return ("Java has buried stronger arrogance than this.");
   }
   else if (civName == "ANWSouthAfricans")
   {
      if (quoteIndex == 0)
      {
         return ("You spend strength like a man with borrowed land.");
      }
      return ("Noise is not resolve.");
   }
   else if (civName == "ANWFinnish")
   {
      if (quoteIndex == 0)
      {
         return ("You waste terrain as if it were free.");
      }
      return ("Such a line would not survive a winter.");
   }
   else if (civName == "ANWHungarians")
   {
      if (quoteIndex == 0)
      {
         return ("A nation is not led by hesitation.");
      }
      return ("You bow to events before the battle is decided.");
   }
   else if (civName == "ANWRomanians")
   {
      if (quoteIndex == 0)
      {
         return ("You confuse disorder with liberty.");
      }
      return ("Your command lacks both nerve and order.");
   }
   else if (civName == "ANWBarbary")
   {
      if (quoteIndex == 0)
      {
         return ("You sail and march with equal confusion.");
      }
      return ("The sea would have judged you already.");
   }
   else if (civName == "ANWEgyptians")
   {
      if (quoteIndex == 0)
      {
         return ("You inherit strength and waste it.");
      }
      return ("Ambition without administration is just noise.");
   }
   else if (civName == "ANWCentralAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("A divided command defeats itself.");
      }
      return ("You split what you are too weak to govern.");
   }
   else if (civName == "ANWBajaCalifornians")
   {
      if (quoteIndex == 0)
      {
         return ("The frontier swallows slower men than you.");
      }
      return ("You ride hard and think late.");
   }
   else if (civName == "ANWYucatan")
   {
      if (quoteIndex == 0)
      {
         return ("You rule without listening and fight the same way.");
      }
      return ("Even victory would not clean this disorder.");
   }
   else if (civName == "ANWRioGrande")
   {
      if (quoteIndex == 0)
      {
         return ("You were too slow for this border.");
      }
      return ("Your retreat started before your charge.");
   }
   else if (civName == "ANWMayans")
   {
      if (quoteIndex == 0)
      {
         return ("Old ground does not honor cowards.");
      }
      return ("You mistake dominion for permanence.");
   }
   else if (civName == "ANWCalifornians")
   {
      if (quoteIndex == 0)
      {
         return ("You threaten the province more than you command it.");
      }
      return ("That advance has no staying power.");
   }
   else if (civName == "ANWTexians")
   {
      if (quoteIndex == 0)
      {
         return ("A loud charge is still a bad plan.");
      }
      return ("You forgot the ending before the first shot.");
   }

   return ("");
}

string llGetLegendaryLeaderCompliment(void)
{
   string civName = llNormalizeCivName(kbGetCivName(cMyCiv));
   int quoteIndex = aiRandInt(2);

   if (civName == "Aztecs")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the causeway and let them shatter on it.");
      }
      return ("Fight with ceremony and with teeth.");
   }
   else if (civName == "British")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the line. After that, the rest is arithmetic.");
      }
      return ("Steady now. Disorder loses battles.");
   }
   else if (civName == "Chinese")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the banners aligned and the field is ours.");
      }
      return ("Discipline first. Triumph follows.");
   }
   else if (civName == "Dutch")
   {
      if (quoteIndex == 0)
      {
         return ("Dress the line and trust the drill.");
      }
      return ("Measure, volley, advance.");
   }
   else if (civName == "Ethiopians")
   {
      if (quoteIndex == 0)
      {
         return ("Stand firm and let the high ground judge them.");
      }
      return ("Order the line. Let them spend themselves.");
   }
   else if (civName == "French")
   {
      if (quoteIndex == 0)
      {
         return ("Take the ground quickly, then make it ours.");
      }
      return ("Momentum, not hesitation, wins empires.");
   }
   else if (civName == "Germans")
   {
      if (quoteIndex == 0)
      {
         return ("Dress the ranks and fire by measure.");
      }
      return ("Speed and precision, nothing else.");
   }
   else if (civName == "Haudenosaunee")
   {
      if (quoteIndex == 0)
      {
         return ("Stand together. A strong confederacy does not bend.");
      }
      return ("Let wisdom guide the first blow.");
   }
   else if (civName == "Hausa")
   {
      if (quoteIndex == 0)
      {
         return ("Keep faith and order, and the day will answer.");
      }
      return ("Discipline first. Victory after.");
   }
   else if (civName == "Inca")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the heights and let them climb to ruin.");
      }
      return ("Build the field as you would an empire.");
   }
   else if (civName == "Indians")
   {
      if (quoteIndex == 0)
      {
         return ("Strike fast, vanish faster.");
      }
      return ("Guard every pass. Yield none.");
   }
   else if (civName == "Italians")
   {
      if (quoteIndex == 0)
      {
         return ("Forward. Italy is made by those who move.");
      }
      return ("Keep the pressure. Do not give them breath.");
   }
   else if (civName == "Japanese")
   {
      if (quoteIndex == 0)
      {
         return ("Step slow and steady, then strike to finish it.");
      }
      return ("Keep order. Let them waste themselves.");
   }
   else if (civName == "Lakota")
   {
      if (quoteIndex == 0)
      {
         return ("Hit fast and keep moving.");
      }
      return ("Let the plains carry our courage.");
   }
   else if (civName == "Maltese")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the walls and let faith harden them.");
      }
      return ("Make every step cost them blood.");
   }
   else if (civName == "Mexicans")
   {
      if (quoteIndex == 0)
      {
         return ("Stand for the cause and the people will answer.");
      }
      return ("Let conviction hold where powder cannot.");
   }
   else if (civName == "Ottomans")
   {
      if (quoteIndex == 0)
      {
         return ("Advance with order and with law.");
      }
      return ("Make the empire look inevitable.");
   }
   else if (civName == "Portuguese")
   {
      if (quoteIndex == 0)
      {
         return ("Chart the field, then claim it.");
      }
      return ("Let patience guide the expedition.");
   }
   else if (civName == "Russians")
   {
      if (quoteIndex == 0)
      {
         return ("Press on. Empire is not built timidly.");
      }
      return ("Stretch them until they break.");
   }
   else if (civName == "Spanish")
   {
      if (quoteIndex == 0)
      {
         return ("Press the matter and do not relent.");
      }
      return ("Faith and order. Keep both.");
   }
   else if (civName == "Swedes")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the pace and the guns close.");
      }
      return ("Speed and discipline will break them.");
   }
   else if (civName == "UnitedStates")
   {
      if (quoteIndex == 0)
      {
         return ("Stand steady. Let the line prove the cause.");
      }
      return ("Hold fast. Resolve carries free men through.");
   }
   else if (civName == "ANWNapoleonicFrance")
   {
      if (quoteIndex == 0)
      {
         return ("Take the center and dictate the day.");
      }
      return ("Push hard. Let them live in reaction.");
   }
   else if (civName == "ANWAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("Hold firm. The line is our argument.");
      }
      return ("Resolve first. Victory after.");
   }
   else if (civName == "ANWMexicans")
   {
      if (quoteIndex == 0)
      {
         return ("Give them courage and they will give you a nation.");
      }
      return ("Push on. Let the cry for liberty answer with powder.");
   }
   else if (civName == "ANWCanadians")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the frontier and let them come on.");
      }
      return ("Steady fire. Waste nothing.");
   }
   else if (civName == "ANWBrazil")
   {
      if (quoteIndex == 0)
      {
         return ("Advance with confidence. The crown must look certain.");
      }
      return ("Push on. Let them see a nation rising.");
   }
   else if (civName == "ANWArgentines")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the column lean and relentless.");
      }
      return ("Forward. The Andes taught us not to linger.");
   }
   else if (civName == "ANWChileans")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the republic together with steel.");
      }
      return ("Stay stubborn. Let them tire first.");
   }
   else if (civName == "ANWPeruvians")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the line measured and the heights ours.");
      }
      return ("Advance with order, and let the heights favor us.");
   }
   else if (civName == "ANWColumbians")
   {
      if (quoteIndex == 0)
      {
         return ("Strike hard. Let liberty outrun fatigue.");
      }
      return ("Carry the fire forward.");
   }
   else if (civName == "ANWHaitians")
   {
      if (quoteIndex == 0)
      {
         return ("Stand unbroken. Liberty remembers courage.");
      }
      return ("Hold your ground with dignity and fire.");
   }
   else if (civName == "ANWIndonesians")
   {
      if (quoteIndex == 0)
      {
         return ("Fight with patience and conviction.");
      }
      return ("Let the land fight beside us.");
   }
   else if (civName == "ANWSouthAfricans")
   {
      if (quoteIndex == 0)
      {
         return ("Save your powder and make it count.");
      }
      return ("Hold steady. Stubborn men outlast empires.");
   }
   else if (civName == "ANWFinnish")
   {
      if (quoteIndex == 0)
      {
         return ("Make the ground do half the work.");
      }
      return ("Order, cold nerve, and exact fire.");
   }
   else if (civName == "ANWHungarians")
   {
      if (quoteIndex == 0)
      {
         return ("Fight as if the nation is watching.");
      }
      return ("Let resolve outrun their numbers.");
   }
   else if (civName == "ANWRomanians")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the line ordered and the state intact.");
      }
      return ("Method first. Glory later.");
   }
   else if (civName == "ANWBarbary")
   {
      if (quoteIndex == 0)
      {
         return ("Strike boldly and leave them no harbor.");
      }
      return ("Let speed and nerve carry the day.");
   }
   else if (civName == "ANWEgyptians")
   {
      if (quoteIndex == 0)
      {
         return ("Build pressure carefully and keep it there.");
      }
      return ("Advance in order. Let discipline carry the day.");
   }
   else if (civName == "ANWCentralAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("Stand together. Federation is strength.");
      }
      return ("Keep formation and keep faith.");
   }
   else if (civName == "ANWBajaCalifornians")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the saddle and the initiative.");
      }
      return ("Raid cleanly. Vanish quickly.");
   }
   else if (civName == "ANWYucatan")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the people close and the line closer.");
      }
      return ("Stand firm. The land remembers loyalty.");
   }
   else if (civName == "ANWRioGrande")
   {
      if (quoteIndex == 0)
      {
         return ("Hit first and keep them guessing.");
      }
      return ("Keep the border moving under them.");
   }
   else if (civName == "ANWMayans")
   {
      if (quoteIndex == 0)
      {
         return ("Stand for the old ground and strike hard.");
      }
      return ("Hold the line with pride and fury.");
   }
   else if (civName == "ANWCalifornians")
   {
      if (quoteIndex == 0)
      {
         return ("Conserve strength and strike when it matters.");
      }
      return ("Hold the province together.");
   }
   else if (civName == "ANWTexians")
   {
      if (quoteIndex == 0)
      {
         return ("Wait for the opening and hit hard.");
      }
      return ("Make one blow decide it.");
   }

   return ("");
}