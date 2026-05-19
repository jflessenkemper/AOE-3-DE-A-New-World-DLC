//==============================================================================
/* leader_suleiman.xs

   Suleiman I "Kanuni" / "the Magnificent" - Ottoman gunpowder-empire
   personality at the height of imperial expansion.

   Historical doctrine:
     - Janissary corps: drilled musket infantry, the elite of every Ottoman
       campaign from Mohacs (1526) to the Siege of Vienna (1529). Mapped
       to a heavy infantry bias from Colonial on, with the elite Abus Gun
       and Janissary as the axis.
     - Imperial siege train: the Ottoman bombard park was the largest in
       Europe through the 16th century. Mapped to the highest artillery
       weight of any standard nation by Industrial.
     - Sipahi cavalry on the wings: timar-holding feudal cavalry as
       maneuver wing, not a primary hammer. Mapped to a real but secondary
       cavalry share.
     - Topkapi statecraft: passive villager generation (Ottoman civ) plus
       trade-route emphasis means a slow opener that pays off massively.
       Mapped to a Compact Fortified Core build (Constantinople-style)
       with a strong trade lean.
     - No native treaty: Suleiman ruled rayah, not allied, and the Ottoman
       army was state-owned. Mapped to a slightly negative native bias.
*/
//==============================================================================

bool gSuleimanRulesEnabled = false;

void initLeaderSuleiman(void)
{
   llVerboseEcho("A New World: activating Suleiman the Magnificent personality.");

   llSetBalancedPersonality();
   btRushBoom = -0.15;            // Ottoman vill auto-spawn lets us rush less hard.
   btOffenseDefense = 0.45;
   btBiasTrade = 0.4;             // Imperial trade chains.
   btBiasNative = -0.2;
   llSetMilitaryFocus(0.65, 0.25, 0.55);  // Janissary + Abus Gun axis.

   // LL-BUILD-STYLE-BEGIN
   llUseSiegeTrainConcentrationStyle(3);
   gLLEconomicDistanceMultiplier = 1.05;
   llSetBuildStrongpointProfile(2, 2, 2, true);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.8, 0.2, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 6;               // Topkapi-style fortification.
   cvMaxArmyPop = 115;

   gSuleimanRulesEnabled = true;
   llLogLeaderState("Suleiman initialized");
   llProbe("meta.leader_init", "leader=suleiman");
}

//------------------------------------------------------------------------------
// Discovery: Topkapi mosque boom. Settler push is mostly automatic; the
// Caliphate prefers to plan the campaign.
//------------------------------------------------------------------------------
rule suleimanTopkapiBoom
inactive
minInterval 60
{
   llLogRuleTick("suleimanTopkapiBoom");
   if (gSuleimanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.4;
      btBiasTrade = 0.55;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Janissary muster. Janissary musket line and Spahi screen;
// Abus Gun appears as soon as the second age permits.
//------------------------------------------------------------------------------
rule suleimanJanissaryMuster
inactive
minInterval 50
{
   llLogRuleTick("suleimanJanissaryMuster");
   if (gSuleimanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.05;
      btOffenseDefense = 0.55;
      btBiasInf = 0.85;            // Janissary mass.
      btBiasCav = 0.4;             // Spahi wing.
      btBiasArt = 0.0;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Gunpowder Empire. Janissary + Abus Gun core, Spahi wing,
// Great Bombard support. The classic Mohacs army.
//------------------------------------------------------------------------------
rule suleimanGunpowderEmpire
inactive
minInterval 55
{
   llLogRuleTick("suleimanGunpowderEmpire");
   if (gSuleimanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.75;
      btBiasInf = 0.95;
      btBiasCav = 0.5;
      btBiasArt = 0.7;             // Imperial bombard park.
      cvMaxArmyPop = 130;
   }
}

//------------------------------------------------------------------------------
// Industrial: Sublime Porte campaign. Heavy Cannon and Great Bombard
// share rises further; Janissary mass continues. The empire pushes
// outward.
//------------------------------------------------------------------------------
rule suleimanSublimePorteCampaign
inactive
minInterval 70
{
   llLogRuleTick("suleimanSublimePorteCampaign");
   if (gSuleimanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.55;
      btBiasArt = 0.85;            // Highest artillery share of any standard nation.
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Caliphate host - maximum Janissary / Abus Gun / Heavy Cannon
// mass with full bombard park; trade lines saturate.
//------------------------------------------------------------------------------
rule suleimanCaliphateHost
inactive
minInterval 90
{
   llLogRuleTick("suleimanCaliphateHost");
   if (gSuleimanRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.6;
      btBiasArt = 1.0;
      btBiasTrade = 0.55;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderSuleimanRules(void)
{
   if (gSuleimanRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("suleimanTopkapiBoom");
   xsEnableRule("suleimanJanissaryMuster");
   xsEnableRule("suleimanGunpowderEmpire");
   xsEnableRule("suleimanSublimePorteCampaign");
   xsEnableRule("suleimanCaliphateHost");
}
