//==============================================================================
/* leader_frederick.xs

   Friedrich II "der Grosse" (Frederick the Great) - Prussian Hohenzollern
   personality.

   Historical doctrine:
     - Oblique order: refuse one wing, mass the other, hit the enemy flank
       at point-blank with a sudden hammer attack (Leuthen 1757). Mapped
       to a strong cavalry+infantry timing push at Fortress, supported by
       fast Doppelsoldner-style line infantry.
     - Drilled musketry: Prussian line infantry fired the fastest volleys
       in Europe. Mapped to high infantry bias from Fortress on, with the
       elite Skirmisher (Voltigeur analogue) and Uhlan as the sharpest
       wing units.
     - War-economy state: Prussia was an army with a country, not the
       reverse. Mapped to a low Trade Route bias and a heavy mercenary /
       War Wagon investment - Hessian mercenaries helped fund the wars.
     - Mobile cabinet warfare: short, decisive campaigns rather than long
       attrition. Mapped to a Distributed Economic Network build style
       (mercenary-friendly sprawl, not turtle).
     - Late-war Reformation: by the Industrial age the Prussian army shifts
       to artillery-and-cavalry deep operations.
*/
//==============================================================================

bool gFrederickRulesEnabled = false;

void initLeaderFrederick(void)
{
   llVerboseEcho("A New World: activating Frederick the Great personality.");

   llSetBalancedPersonality();
   btRushBoom = 0.05;             // Light boom; campaign begins early.
   btOffenseDefense = 0.55;
   btBiasTrade = -0.25;           // Prussia is an army with a country.
   btBiasNative = -0.2;
   llSetMilitaryFocus(0.6, 0.45, 0.3);  // Inf-cav-art weighted toward cavalry strike.

   // LL-BUILD-STYLE-BEGIN
   // Spec doctrine = Republican Levee (UrbanBarricade walls). Prussian
   // line-infantry musketeer mass fits the Levee helper better than the
   // Siege Train one (which is reserved for Suleiman's cannon doctrine).
   // earlyWalls=true honours spec first_wall_before_ms=900000 (Levee default
   // is false for revolutionary mobile civs; Frederick is a static-base civ).
   llUseRepublicanLeveeStyle(2, true);
   gLLMilitaryDistanceMultiplier = 0.85;
   llSetBuildStrongpointProfile(2, 2, 2, true);
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.74, 0.26, 2, 4.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 115;

   gFrederickRulesEnabled = true;
   llLogLeaderState("Frederick initialized");
   llProbe("meta.leader_init", "leader=frederick");
}

//------------------------------------------------------------------------------
// Discovery: Settler push and shipment-cycle priority. Frederick wants the
// army funded, not the eco maximized.
//------------------------------------------------------------------------------
rule frederickKabinettsBoom
inactive
minInterval 60
{
   llLogRuleTick("frederickKabinettsBoom");
   if (gFrederickRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.2;          // Lighter boom than the defensive personalities.
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Crossbowman / Skirmisher screen and a War Wagon push. Frederick
// commits to the field as soon as a small army exists.
//------------------------------------------------------------------------------
rule frederickWagonPush
inactive
minInterval 50
{
   llLogRuleTick("frederickWagonPush");
   if (gFrederickRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.1;
      btOffenseDefense = 0.65;
      btBiasInf = 0.7;
      btBiasCav = 0.45;            // Uhlan and War Wagon early commitment.
      btBiasArt = -0.2;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: oblique order. Doppelsoldner backbone, Uhlan hammer wing,
// Falconet flank fire. The classic Prussian timing.
//------------------------------------------------------------------------------
rule frederickObliqueOrder
inactive
minInterval 55
{
   llLogRuleTick("frederickObliqueOrder");
   if (gFrederickRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.8;
      btBiasInf = 0.85;
      btBiasCav = 0.7;             // Strongest cavalry weight of any standard nation.
      btBiasArt = 0.4;
      cvMaxArmyPop = 130;
   }
}

//------------------------------------------------------------------------------
// Industrial: Prussian Reformation. Hessian mercenary drops, Heavy Cannon
// share rises, Uhlan mass continues. Frederick fights deep, not wide.
//------------------------------------------------------------------------------
rule frederickPrussianReformation
inactive
minInterval 70
{
   llLogRuleTick("frederickPrussianReformation");
   if (gFrederickRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 0.95;
      btBiasCav = 0.75;
      btBiasArt = 0.65;
      cvMaxArmyPop = 145;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Hohenzollern shock army. Massive Uhlan / Doppelsoldner core,
// Heavy Cannon and Mortar, mercenary line infantry from the Saloon.
//------------------------------------------------------------------------------
rule frederickHohenzollernShock
inactive
minInterval 90
{
   llLogRuleTick("frederickHohenzollernShock");
   if (gFrederickRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.85;
      btBiasArt = 0.75;
      cvMaxArmyPop = 160;
   }
}

void enableLeaderFrederickRules(void)
{
   if (gFrederickRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("frederickKabinettsBoom");
   xsEnableRule("frederickWagonPush");
   xsEnableRule("frederickObliqueOrder");
   xsEnableRule("frederickPrussianReformation");
   xsEnableRule("frederickHohenzollernShock");
}
