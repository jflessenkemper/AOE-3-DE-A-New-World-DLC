//==============================================================================
/* leader_hiawatha.xs

   Hiawatha - Haudenosaunee (Iroquois Confederacy) personality.

   Historical doctrine:
     - Great Law of Peace: the Confederacy unified five (later six) nations
       under one council. Mapped to a strong Native Treaty bias and a
       genuine native-allied force composition rather than a token one.
     - Forest warfare: ambush, encirclement, and broken-ground volleys -
       not European-style line infantry. Mapped to Tomahawk + Forest Prowler
       skirmish bias and an aggressive Colonial commitment.
     - Travois mobility: the Iroquois civ trades fixed Town Centres for
       mobile Travois economy. Mapped to the Mobile Frontier Scatter style.
     - Light artillery (Mantlet, Light Cannon): present but never the
       centerpiece. The army is infantry-driven.
     - Confederacy diplomacy: native warriors fight alongside, not as
       mercenaries. Native Trade Posts are a primary objective from age 1.
*/
//==============================================================================

bool gHiawathaRulesEnabled = false;

void initLeaderHiawatha(void)
{
   llVerboseEcho("A New World: activating Hiawatha personality.");

   llSetBalancedPersonality();
   btRushBoom = 0.1;              // Light boom; the warpath opens early.
   btOffenseDefense = 0.5;
   btBiasTrade = -0.15;
   btBiasNative = 0.7;            // Native Treaty is the spine of the strategy.
   llSetMilitaryFocus(0.7, 0.1, 0.1);

   // LL-BUILD-STYLE-BEGIN
   llUseShrineTradeNodeSpreadStyle(1);
   gLLEconomicDistanceMultiplier = 1.20;
   // Spec override: military_distance_band [1.0, 1.3]; ShrineTradeNodeSpread
   // default is 0.95 which falls below the band floor.
   gLLMilitaryDistanceMultiplier = 1.05;
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 115;

   gHiawathaRulesEnabled = true;
   llLogLeaderState("Hiawatha initialized");
   llProbe("meta.leader_init", "leader=hiawatha");
}

//------------------------------------------------------------------------------
// Discovery: Travois sprawl. Native Trade Posts and Settler push come first.
//------------------------------------------------------------------------------
rule hiawathaTravoisSprawl
inactive
minInterval 60
{
   llLogRuleTick("hiawathaTravoisSprawl");
   if (gHiawathaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.15;
      btBiasNative = 0.85;
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Confederacy warbands. Tomahawk + Aenna pressure on enemy
// villagers and trade lines, native allies forward.
//------------------------------------------------------------------------------
rule hiawathaConfederacyWarbands
inactive
minInterval 50
{
   llLogRuleTick("hiawathaConfederacyWarbands");
   if (gHiawathaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.0;
      btOffenseDefense = 0.4;        // Spec expects_treaty=true: keep Colonial moderate, no llEnableForwardBaseStyle (forward-base sets btOffenseDefense=1.0 which contradicts treaty posture).
      btBiasInf = 0.8;
      btBiasCav = 0.1;
      btBiasArt = -0.4;
      btBiasNative = 0.8;
   }
}

//------------------------------------------------------------------------------
// Fortress: Forest Prowler ambush. Mantlet shields, Musket Rider chase
// cavalry, mass infantry from the longhouse.
//------------------------------------------------------------------------------
rule hiawathaForestProwler
inactive
minInterval 55
{
   llLogRuleTick("hiawathaForestProwler");
   if (gHiawathaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.75;
      btBiasInf = 0.95;
      btBiasCav = 0.35;            // Musket Rider for chasing artillery.
      btBiasArt = 0.15;
      cvMaxArmyPop = 130;
   }
}

//------------------------------------------------------------------------------
// Industrial: War Rifle line. Forest Prowlers transition into War Rifles,
// Light Cannon makes a measurable appearance, native warbands continue.
//------------------------------------------------------------------------------
rule hiawathaWarRifleLine
inactive
minInterval 70
{
   llLogRuleTick("hiawathaWarRifleLine");
   if (gHiawathaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.4;
      btBiasArt = 0.45;
      cvMaxArmyPop = 145;
      // Spec expects_treaty=true, no expects_forward: hold the Confederacy line; spread of TPs is the doctrine, not forward camps.
   }
}

//------------------------------------------------------------------------------
// Imperial: Confederacy host - maximum mass of Tomahawks, Forest Prowlers,
// and War Rifles, supported by Light Cannon parks and full native treaty.
//------------------------------------------------------------------------------
rule hiawathaConfederacyHost
inactive
minInterval 90
{
   llLogRuleTick("hiawathaConfederacyHost");
   if (gHiawathaRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.45;
      btBiasArt = 0.55;
      btBiasNative = 0.85;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderHiawathaRules(void)
{
   if (gHiawathaRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("hiawathaTravoisSprawl");
   xsEnableRule("hiawathaConfederacyWarbands");
   xsEnableRule("hiawathaForestProwler");
   xsEnableRule("hiawathaWarRifleLine");
   xsEnableRule("hiawathaConfederacyHost");
}
