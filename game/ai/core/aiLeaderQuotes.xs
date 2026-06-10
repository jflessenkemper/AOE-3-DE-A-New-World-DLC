//==============================================================================
/* aiLeaderQuotes.xs

   Shared leader quote runtime for A New World personalities.
*/
//==============================================================================

int gANWLeaderEnemyQuoteTime = -600000;
int gANWLeaderAllyQuoteTime = -600000;
int gANWLeaderTacticalQuoteTime = -600000;

bool anwHasLeaderQuotes(void)
{
   return (anwGetLeaderInsult() != "");
}

bool anwShouldAppendQuoteForStatement(int commPromptID = -1)
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

int anwGetQuoteIntervalForStatement(int commPromptID = -1)
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

void anwSendLeaderInsultLine(int playerIDorRelation = -1, int quoteInterval = 90000)
{
   if (xsGetTime() < gANWLeaderEnemyQuoteTime + quoteInterval)
   {
      debugANW("enemy quote throttled for target " + playerIDorRelation + " with interval " + quoteInterval);
      return;
   }

   string message = anwGetLeaderInsult();
   if (message == "")
   {
      debugANW("enemy quote skipped because no insult is defined for " + kbGetCivName(cMyCiv));
      return;
   }

   sendChatLine(playerIDorRelation, message);
   gANWLeaderEnemyQuoteTime = xsGetTime();
   debugANW("enemy quote sent to " + playerIDorRelation + ": " + message);
}

void anwSendLeaderComplimentLine(int playerIDorRelation = -1, int quoteInterval = 90000)
{
   if (xsGetTime() < gANWLeaderAllyQuoteTime + quoteInterval)
   {
      debugANW("ally quote throttled for target " + playerIDorRelation + " with interval " + quoteInterval);
      return;
   }

   string message = anwGetLeaderCompliment();
   if (message == "")
   {
      debugANW("ally quote skipped because no compliment is defined for " + kbGetCivName(cMyCiv));
      return;
   }

   sendChatLine(playerIDorRelation, message);
   gANWLeaderAllyQuoteTime = xsGetTime();
   debugANW("ally quote sent to " + playerIDorRelation + ": " + message);
}

void anwSendLeaderTacticalLine(int playerIDorRelation = -1, string message = "", int quoteInterval = 90000)
{
   if ((playerIDorRelation < 0) || (message == ""))
   {
      return;
   }

   if (xsGetTime() < gANWLeaderTacticalQuoteTime + quoteInterval)
   {
      debugANW("tactical quote throttled for target " + playerIDorRelation + " with interval " + quoteInterval);
      return;
   }

   sendChatLine(playerIDorRelation, message);
   gANWLeaderTacticalQuoteTime = xsGetTime();
   debugANW("tactical quote sent to " + playerIDorRelation + ": " + message);
}

string anwGetLeaderRetreatLine(void)
{
   return ("Order the withdrawal. A disciplined retreat is not defeat.");
}

string anwGetLeaderRoutLine(void)
{
   return ("Their line has broken. Press the advantage before they can reform.");
}

string anwGetLeaderBulkAssaultLine(void)
{
   return ("Strike the main body. Scatter the wings and the center collapses.");
}

string anwGetLeaderDecapitationLine(void)
{
   return ("Bypass their foot. Take their commander and the army dissolves.");
}

void anwSendLeaderRetreatLine(int playerIDorRelation = -1, int quoteInterval = 150000)
{
   anwSendLeaderTacticalLine(playerIDorRelation, anwGetLeaderRetreatLine(), quoteInterval);
}

void anwSendLeaderRoutLine(int playerIDorRelation = -1, int quoteInterval = 120000)
{
   anwSendLeaderTacticalLine(playerIDorRelation, anwGetLeaderRoutLine(), quoteInterval);
}

void anwSendLeaderBulkAssaultLine(int playerIDorRelation = -1, int quoteInterval = 120000)
{
   anwSendLeaderTacticalLine(playerIDorRelation, anwGetLeaderBulkAssaultLine(), quoteInterval);
}

void anwSendLeaderDecapitationLine(int playerIDorRelation = -1, int quoteInterval = 120000)
{
   anwSendLeaderTacticalLine(playerIDorRelation, anwGetLeaderDecapitationLine(), quoteInterval);
}

void anwMaybeFollowStatementWithQuote(int playerID = -1, int commPromptID = -1)
{
   if ((playerID < 0) || (anwHasLeaderQuotes() == false))
   {
      return;
   }

   if (anwShouldAppendQuoteForStatement(commPromptID) == false)
   {
      debugANW("statement " + commPromptID + " skipped for quote follow-up.");
      return;
   }

   int interval = anwGetQuoteIntervalForStatement(commPromptID);
   debugANW("statement " + commPromptID + " evaluating quote follow-up for player " + playerID + " with interval " + interval);

   if (kbIsPlayerEnemy(playerID) == true)
   {
      anwSendLeaderInsultLine(playerID, interval);
      return;
   }

   if (kbIsPlayerAlly(playerID) == true)
   {
      anwSendLeaderComplimentLine(playerID, interval);
   }
}

rule anwLeaderOpeningQuote
inactive
minInterval 10
{
   anwLogRuleTick("anwLeaderOpeningQuote");
   if (anwHasLeaderQuotes() == false)
   {
      xsDisableSelf();
      return;
   }

   if (xsGetTime() < 25000)
   {
      return;
   }

   debugANW("opening quotes firing for " + kbGetCivName(cMyCiv));
   // LL-QUOTE probe  --  ensures the per-leader opening compliment/insult pair
   // fires at ~25s and only once. Miss = ANW leader quote wiring broken.
   anwProbe("chat.quote", "kind=opening");
   anwSendLeaderComplimentLine(cPlayerRelationAllyExcludingSelf, 0);
   anwSendLeaderInsultLine(cPlayerRelationEnemyNotGaia, 0);
   xsDisableSelf();
}

void anwEnableLeaderQuoteRules(void)
{
   if (anwHasLeaderQuotes() == false)
   {
      return;
   }

   anwLogEvent("RULE", "enabling ANW leader opening quote rule");
   xsEnableRule("anwLeaderOpeningQuote");
}

// Map kbGetCivName() internal strings (e.g. "XPIroquois", "DEMaltese") to
// the display-name branches used by the insult/compliment tables. Without
// this, leaders for XP/DE-prefixed civs silently get no quote, and the
// opening-quote rule disables itself (bug observed in replay: Hiawatha/Jean
// missing opening quotes).
string anwNormalizeCivName(string raw = "")
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

string anwGetLeaderInsult(void)
{
   string civName = anwNormalizeCivName(kbGetCivName(cMyCiv));
   int quoteIndex = aiRandInt(2);

   if (civName == "Aztecs")
   {
      if (quoteIndex == 0)
      {
         return ("The omens condemn such disorder.");
      }
      return ("The smoking mirror of Tezcatlipoca shows me your end. Come and meet Tenochtitlan.");
   }
   else if (civName == "British")
   {
      if (quoteIndex == 0)
      {
         return ("I have the heart and stomach of a king, and of a King of England too. Your threat is nothing.");
      }
      return ("I will have here but one mistress and no master. Yield, or be swept from this field.");
   }
   else if (civName == "Chinese")
   {
      if (quoteIndex == 0)
      {
         return ("You bring disorder to a field that demands harmony.");
      }
      return ("Even the Dzungars showed firmer order before Zunghar fell.");
   }
   else if (civName == "Dutch")
   {
      if (quoteIndex == 0)
      {
         return ("Your volley is late and your drill worse.");
      }
      return ("A republic that cannot drill its musketeers will not long remain one.");
   }
   else if (civName == "Ethiopians")
   {
      if (quoteIndex == 0)
      {
         return ("You climb these heights without judgment.");
      }
      return ("At Adwa, Italy learned what judgment means. You have not yet learned it.");
   }
   else if (civName == "French")
   {
      if (quoteIndex == 0)
      {
         return ("A throne is only a bench covered with velvet. Learn to fight, not to sit.");
      }
      return ("Soldiers, I am satisfied with you. In the battle of Austerlitz you have justified all my hopes.");
   }
   else if (civName == "Germans")
   {
      if (quoteIndex == 0)
      {
         return ("Your line offends both reason and powder.");
      }
      return ("God is on the side not of the heavy battalions, but the best shots. Be better.");
   }
   else if ((civName == "Haudenosaunee") || (civName == "XPIroquois"))
   {
      if (quoteIndex == 0)
      {
         return ("You break ranks as easily as broken councils.");
      }
      return ("The Great Law binds us. What binds you together? Nothing I can see.");
   }
   else if (civName == "Hausa")
   {
      if (quoteIndex == 0)
      {
         return ("You advance without justice or discipline.");
      }
      return ("He who conceals injustice in his heart will find it revealed on the battlefield.");
   }
   else if (civName == "Inca")
   {
      if (quoteIndex == 0)
      {
         return ("You cannot build victory on such loose stones.");
      }
      return ("Sacsayhuaman was raised without mortar and has outlasted every conqueror. You will not.");
   }
   else if (civName == "Indians")
   {
      if (quoteIndex == 0)
      {
         return ("You guard no flank and deserve none.");
      }
      return ("The Sahyadri hills taught me to strike and vanish. You have learned neither.");
   }
   else if (civName == "Italians")
   {
      if (quoteIndex == 0)
      {
         return ("You march like ceremony, not revolution.");
      }
      return ("I offer neither pay, nor quarters, nor provisions. I offer hunger, thirst, and death. Any who love their country, follow me.");
   }
   else if (civName == "Japanese")
   {
      if (quoteIndex == 0)
      {
         return ("The impatient commander defeats himself first.");
      }
      return ("One who is hasty cannot govern. Sekigahara required twenty years of patience to win.");
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
      return ("Rhodes and Belgrade bowed to my Kanun. Your disorder will bow to my cannon.");
   }
   else if (civName == "Portuguese")
   {
      if (quoteIndex == 0)
      {
         return ("You mistake horizon for mastery.");
      }
      return ("Sagres charts the world. You cannot chart this field.");
   }
   else if (civName == "Russians")
   {
      if (quoteIndex == 0)
      {
         return ("I am not a tsar of Moscow  --  I am tsar of all Rus. You will learn the difference.");
      }
      return ("To show mercy to the treacherous is to show cruelty to the loyal.");
   }
   else if (civName == "Spanish")
   {
      if (quoteIndex == 0)
      {
         return ("You squander zeal as well as steel.");
      }
      return ("Granada fell after ten years of resolve. Your courage has not lasted ten minutes.");
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
         return ("Discipline is the soul of an army. Washington knew it. You have not learned it.");
      }
      return ("The Continental Line held at Yorktown under fire. You have not shown their resolve.");
   }
   else if (civName == "ANWNapoleonicFrance")
   {
      if (quoteIndex == 0)
      {
         return ("Europe did not fear me for such maneuvers.");
      }
      return ("You waste the moment and the map.");
   }
   else if (civName == "ANWRevFrance")
   {
      if (quoteIndex == 0)
      {
         return ("The virtue of the Republic is terror. Yours is merely cowardice.");
      }
      return ("Citizens must arm themselves with the severity of truth. Show some.");
   }
   else if (civName == "ANWAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("Even a militia deserves better direction than this.");
      }
      return ("Bunker Hill was lost but cost them dear. You have not yet made them pay at all.");
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
         return ("Most of the men were cut down at Queenston Heights. We held. You will not.");
      }
      return ("You rush the woods and call it strategy. The frontier calls it folly.");
   }
   else if (civName == "ANWBrazil")
   {
      if (quoteIndex == 0)
      {
         return ("Independence or death. You have chosen neither, so I will decide for you.");
      }
      return ("You bring pomp without vigor. Brazil needs blood and iron, not theater.");
   }
   else if (civName == "ANWArgentines")
   {
      if (quoteIndex == 0)
      {
         return ("The Andes would laugh at such a march.");
      }
      return ("I crossed the Cordillera to liberate a continent. You cannot cross this field.");
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
      return ("Peru and Bolivia stand as one Confederation. Your confusion stands alone.");
   }
   else if (civName == "ANWColumbians")
   {
      if (quoteIndex == 0)
      {
         return ("You dream of empire and cannot hold a ridge.");
      }
      return ("Carabobo was fought by men who did not know retreat. You have not met such men before.");
   }
   else if (civName == "ANWHaitians")
   {
      if (quoteIndex == 0)
      {
         return ("No army stands long upon the whip.");
      }
      return ("In overthrowing me, you have done no more than cut down the trunk of the tree of liberty. It will spring back from the roots.");
   }
   else if (civName == "ANWIndonesians")
   {
      if (quoteIndex == 0)
      {
         return ("You occupy land you do not understand.");
      }
      return ("The VOC is gone and the Dutch still do not understand Java. Neither do you.");
   }
   else if (civName == "ANWSouthAfricans")
   {
      if (quoteIndex == 0)
      {
         return ("You spend strength like a man with borrowed land.");
      }
      return ("Majuba showed the Empire that a Boer does not yield. You will learn the same lesson.");
   }
   else if (civName == "ANWFinnish")
   {
      if (quoteIndex == 0)
      {
         return ("You waste terrain as if it were free.");
      }
      return ("The Mannerheim Line held what your line cannot. Sisu is not given  --  it is earned.");
   }
   else if (civName == "ANWHungarians")
   {
      if (quoteIndex == 0)
      {
         return ("A nation is not led by hesitation.");
      }
      return ("Magyarok! The cause of liberty requires that you not bend until the last cannon is spent.");
   }
   else if (civName == "ANWRomanians")
   {
      if (quoteIndex == 0)
      {
         return ("You confuse disorder with liberty.");
      }
      return ("Unirea Principatelor was achieved by law, not by chaos. Learn the difference.");
   }
   else if (civName == "ANWBarbary")
   {
      if (quoteIndex == 0)
      {
         return ("You sail and march with equal confusion.");
      }
      return ("Charles V came to Algiers with fifty thousand men. The sea and I sent them back. You have fewer men.");
   }
   else if (civName == "ANWEgyptians")
   {
      if (quoteIndex == 0)
      {
         return ("You inherit strength and waste it.");
      }
      return ("I destroyed the Mamluks at the Citadel because they were disorder dressed as power. So are you.");
   }
   else if (civName == "ANWCentralAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("A divided command defeats itself.");
      }
      return ("The conservatives have always feared a united isthmus. You are no different.");
   }
   else if (civName == "ANWBajaCalifornians")
   {
      if (quoteIndex == 0)
      {
         return ("The frontier swallows slower men than you.");
      }
      return ("Las Californias stretches from Loreto to Sonoma. You cannot even hold this field.");
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
         return ("The Republic of Rio Grande was carved from two empires. You are less than either.");
      }
      return ("Canales held this river against Santa Anna himself. You will not hold it against us.");
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
      return ("I governed California from Sonoma. You cannot govern this engagement.");
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

string anwGetLeaderCompliment(void)
{
   string civName = anwNormalizeCivName(kbGetCivName(cMyCiv));
   int quoteIndex = aiRandInt(2);

   if (civName == "Aztecs")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the causeway. Tenochtitlan was built on water and held by will.");
      }
      return ("Fight with ceremony and with teeth. That is the xochiyaoyotl  --  the flower war.");
   }
   else if (civName == "British")
   {
      if (quoteIndex == 0)
      {
         return ("Though I be a woman, I have as good a courage as ever my father had. Your valor is worthy of England.");
      }
      return ("England has defeated the Armada and will not falter here. You fight well  --  press the advantage.");
   }
   else if (civName == "Chinese")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the Eight Banners aligned and the field is ours.");
      }
      return ("Discipline first. The Qing did not conquer from the Amur to Tibet by carelessness.");
   }
   else if (civName == "Dutch")
   {
      if (quoteIndex == 0)
      {
         return ("Dress the line and trust the drill. Maurice of Nassau invented the countermarch for a reason.");
      }
      return ("Measure, volley, advance. The Republic built its army on discipline, not inspiration.");
   }
   else if (civName == "Ethiopians")
   {
      if (quoteIndex == 0)
      {
         return ("Stand firm. At Adwa, the high ground judged Italy. Let it judge them here.");
      }
      return ("Order the line. Let them spend themselves on our shields, as Menelik planned.");
   }
   else if (civName == "French")
   {
      if (quoteIndex == 0)
      {
         return ("Soldiers of France, forty centuries look down upon you from those heights.");
      }
      return ("The moral is to the physical as three is to one. Keep faith and press on.");
   }
   else if (civName == "Germans")
   {
      if (quoteIndex == 0)
      {
         return ("Dress the ranks and fire by measure. Leuthen was won by exactly this.");
      }
      return ("Speed and precision. At Rossbach I beat the French in ninety minutes. Set the same pace.");
   }
   else if (civName == "Haudenosaunee")
   {
      if (quoteIndex == 0)
      {
         return ("Stand together. The Great Law binds the six fires  --  let that strength guide you.");
      }
      return ("Let the wisdom of the longhouse guide the first blow and the last.");
   }
   else if (civName == "Hausa")
   {
      if (quoteIndex == 0)
      {
         return ("Keep faith and order. The Sokoto Caliphate was built on both.");
      }
      return ("Discipline first. The walls of Kano stood because discipline held them. So must you.");
   }
   else if (civName == "Inca")
   {
      if (quoteIndex == 0)
      {
         return ("Hold the heights and let them climb to ruin. Sacsayhuaman was never taken from above.");
      }
      return ("Build the field as Pachacuti built the empire  --  each stone set so none can be moved.");
   }
   else if (civName == "Indians")
   {
      if (quoteIndex == 0)
      {
         return ("Strike fast, vanish faster. That is the Ganimi Kava of the Maratha.");
      }
      return ("Guard every pass through the Sahyadri. Yield none  --  Shivaji never did.");
   }
   else if (civName == "Italians")
   {
      if (quoteIndex == 0)
      {
         return ("Forward. Italy is made by those who move. The Thousand proved it.");
      }
      return ("Keep the pressure. Garibaldi marched from Sicily to Naples. Do not give them breath.");
   }
   else if (civName == "Japanese")
   {
      if (quoteIndex == 0)
      {
         return ("Step slow and steady, then strike to finish it. Sekigahara was won in one day after twenty years.");
      }
      return ("Keep order. Let them waste themselves, as Ieyasu waited for Hideyoshi's heirs to fall.");
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
         return ("Advance with order and with Kanun. The law of Suleiman is the strength of the empire.");
      }
      return ("Make the empire look inevitable. It is  --  from the Danube to the Euphrates.");
   }
   else if (civName == "Portuguese")
   {
      if (quoteIndex == 0)
      {
         return ("Chart the field, then claim it. The caravel does not wait for permission.");
      }
      return ("Let patience and science guide the expedition. Sagres trained navigators, not wanderers.");
   }
   else if (civName == "Russians")
   {
      if (quoteIndex == 0)
      {
         return ("Press on. The Tsardom of Rus does not stop until the frontier is answered.");
      }
      return ("Stretch them until they break. Russia is wider than their resolve.");
   }
   else if (civName == "Spanish")
   {
      if (quoteIndex == 0)
      {
         return ("Press the matter and do not relent. God and Granada taught us what persistence wins.");
      }
      return ("Faith and order. Isabella did not take the New World by one or the other  --  she kept both.");
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
         return ("Stand steady. Let the line prove the cause. Valley Forge proved ours.");
      }
      return ("Hold fast. It is not our numbers that win liberty  --  it is resolve.");
   }
   else if (civName == "ANWNapoleonicFrance")
   {
      if (quoteIndex == 0)
      {
         return ("Take the center and dictate the day.");
      }
      return ("Push hard. Let them live in reaction.");
   }
   else if (civName == "ANWRevFrance")
   {
      if (quoteIndex == 0)
      {
         return ("The Republic is virtue. Advance  --  do not waver before the enemies of the people.");
      }
      return ("Death is nothing. To live defeated and inglorious is to die daily. Hold the line.");
   }
   else if (civName == "ANWAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("Hold firm. The line is our argument.");
      }
      return ("Valley Forge tested the resolve of this army. That test was not in vain.");
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
         return ("Hold the frontier. Brock held Queenston Heights with far fewer. You can hold this.");
      }
      return ("Steady fire. The forest fights for those who know it.");
   }
   else if (civName == "ANWBrazil")
   {
      if (quoteIndex == 0)
      {
         return ("Advance with confidence. Independencia ou morte  --  there is no other road.");
      }
      return ("Push on. The empire of Brazil rises with each step you hold.");
   }
   else if (civName == "ANWArgentines")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the column lean and relentless. San Martin did not cross the Andes to linger.");
      }
      return ("Forward. Let each step be worthy of those who climbed the Cordillera.");
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
         return ("Keep the line measured and the heights ours. The Confederation demands no less.");
      }
      return ("Advance with order. Peru and Bolivia stand as one  --  let them feel our weight.");
   }
   else if (civName == "ANWColumbians")
   {
      if (quoteIndex == 0)
      {
         return ("Strike hard. At Carabobo the day was won by men who did not count the cost.");
      }
      return ("Carry the fire of Bolivar forward. Gran Colombia does not stop here.");
   }
   else if (civName == "ANWHaitians")
   {
      if (quoteIndex == 0)
      {
         return ("Stand unbroken. The liberty of Saint-Domingue was not given  --  it was seized.");
      }
      return ("Hold your ground. Toussaint did not retreat from Crete-a-Pierrot. Neither will you.");
   }
   else if (civName == "ANWIndonesians")
   {
      if (quoteIndex == 0)
      {
         return ("Fight with patience and conviction. Diponegoro held the Java War for five years against the Dutch.");
      }
      return ("Let the land fight beside us. Java knows where to hide and when to strike.");
   }
   else if (civName == "ANWSouthAfricans")
   {
      if (quoteIndex == 0)
      {
         return ("Save your powder and make it count. Majuba was won with careful aim.");
      }
      return ("Hold steady. A Boer behind a kopje outlasts any empire that marches in the open.");
   }
   else if (civName == "ANWFinnish")
   {
      if (quoteIndex == 0)
      {
         return ("Make the ground do half the work. The Mannerheim Line proved the principle.");
      }
      return ("Sisu. Cold nerve and exact fire. Finland has never fought any other way.");
   }
   else if (civName == "ANWHungarians")
   {
      if (quoteIndex == 0)
      {
         return ("Fight as if Hungary is watching. She is.");
      }
      return ("The cause of freedom outlasts every army that opposes it. Press on.");
   }
   else if (civName == "ANWRomanians")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the line ordered. Unirea was built on discipline, not on luck.");
      }
      return ("Method first. The Principalities were united by law and will be defended by it.");
   }
   else if (civName == "ANWBarbary")
   {
      if (quoteIndex == 0)
      {
         return ("Strike boldly and leave them no harbor. Algiers never gives quarter to hesitation.");
      }
      return ("Speed and nerve carry the Barbary fleet. They carry us today as well.");
   }
   else if (civName == "ANWEgyptians")
   {
      if (quoteIndex == 0)
      {
         return ("Build pressure carefully. Egypt is built by discipline, not by impulse.");
      }
      return ("Advance in order. The Nizam Jedid is the army that mastered the Mamluks. Be worthy of it.");
   }
   else if (civName == "ANWCentralAmericans")
   {
      if (quoteIndex == 0)
      {
         return ("Stand together. The Federal Republic of Central America stands or falls as one.");
      }
      return ("Keep formation. Morazan unified the isthmus against those who said it could not be done.");
   }
   else if (civName == "ANWBajaCalifornians")
   {
      if (quoteIndex == 0)
      {
         return ("Keep the saddle and the initiative. From Loreto to the frontier, California rides fast.");
      }
      return ("Raid cleanly. Vanish quickly. The Californias owe their survival to exactly that.");
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
         return ("Conserve strength and strike when it matters. Sonoma was taken without a drop of blood.");
      }
      return ("Hold the province together. California kept her own counsel when empires quarreled over her.");
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